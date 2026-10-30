"""Histórico de uma sessão e consumo de tokens do usuário, lidos da trilha de auditoria."""

from collections.abc import Callable
from contextvars import ContextVar
from datetime import timedelta

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from venergy_agent.domain.answer import AnswerStatus
from venergy_agent.domain.conversation import ConversationTurn

from venergy_api.models import AiAuditoria

STATUS_DO_HISTORICO = [
    status.value for status in AnswerStatus if status is not AnswerStatus.REFUSED
]


# Quem faz a pergunta em andamento. A rota define antes de chamar o agente, cuja porta
# `SessionUsage` só recebe o session_id: o orçamento de tokens vale por usuário, em todas as
# sessões dele, e o contrato `ask(question, session_id)` do agente não muda. O contexto
# acompanha o await e o run_in_threadpool; cada pedido roda na própria tarefa.
usuario_da_requisicao: ContextVar[str | None] = ContextVar("usuario_da_requisicao", default=None)


class HistoricoAuditoria:
    """Implementa as portas `ConversationHistory` e `SessionUsage` do agente.

    O histórico vem do backend, e não do agente, porque o usuário `venergy_agent` nunca lê o
    schema `app` e o agente é somente leitura: quem já grava cada pergunta e resposta
    (DEC-034) é o backend. Cada chamada abre a sua própria sessão, em outra thread, porque as
    portas são assíncronas e a sessão do backend é síncrona.
    """

    def __init__(
        self, obter_engine: Callable[[], Engine], janela_orcamento_segundos: int = 86400
    ) -> None:
        # A engine só é pedida na primeira consulta: na subida da API, as configurações do banco
        # podem nem estar disponíveis (os testes montam o app sem .env).
        self._obter_engine = obter_engine
        # O orçamento vale numa janela de tempo, e não desde sempre: quem bate o teto volta a
        # perguntar quando o gasto mais antigo sai da janela.
        self._janela_orcamento = timedelta(seconds=janela_orcamento_segundos)

    async def recent(self, session_id: str, limit: int) -> tuple[ConversationTurn, ...]:
        return await run_in_threadpool(self._recent, session_id, limit)

    async def tokens_used(self, session_id: str) -> int:
        return await run_in_threadpool(self._tokens_used, session_id)

    def _recent(self, session_id: str, limit: int) -> tuple[ConversationTurn, ...]:
        if limit <= 0:
            return ()
        with Session(self._obter_engine()) as session:
            linhas = session.execute(
                select(
                    AiAuditoria.pergunta,
                    AiAuditoria.sql,
                    AiAuditoria.status,
                    AiAuditoria.clarification,
                )
                .where(
                    AiAuditoria.session_id == session_id,
                    # Um status que o agente não conhece fica de fora, em vez de derrubar a leitura.
                    AiAuditoria.status.in_(STATUS_DO_HISTORICO),
                )
                .order_by(AiAuditoria.id.desc())
                .limit(limit)
            ).all()
        return tuple(
            ConversationTurn(
                question=pergunta,
                sql=sql or None,
                status=AnswerStatus(status),
                clarification=clarification,
            )
            for pergunta, sql, status, clarification in reversed(linhas)
        )

    def _tokens_used(self, session_id: str) -> int:
        usuario = usuario_da_requisicao.get()
        # Sem usuário no contexto (uso fora da rota), cai para a sessão.
        dono = (
            AiAuditoria.usuario == usuario
            if usuario is not None
            else AiAuditoria.session_id == session_id
        )
        with Session(self._obter_engine()) as session:
            return int(
                session.scalar(
                    select(
                        func.coalesce(
                            func.sum(AiAuditoria.input_tokens + AiAuditoria.output_tokens), 0
                        )
                    ).where(dono, AiAuditoria.criado_em > func.now() - self._janela_orcamento)
                )
                or 0
            )
