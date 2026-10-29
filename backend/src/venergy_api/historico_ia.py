"""Histórico e consumo de tokens de uma sessão do agente, lidos da trilha de auditoria."""

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from venergy_agent.domain.answer import AnswerStatus
from venergy_agent.domain.conversation import ConversationTurn

from venergy_api.models import AiAuditoria

STATUS_DO_HISTORICO = [
    status.value for status in AnswerStatus if status is not AnswerStatus.REFUSED
]


class HistoricoAuditoria:
    """Implementa as portas `ConversationHistory` e `SessionUsage` do agente.

    O histórico vem do backend, e não do agente, porque o usuário `venergy_agent` nunca lê o
    schema `app` e o agente é somente leitura: quem já grava cada pergunta e resposta
    (DEC-034) é o backend. Cada chamada abre a sua própria sessão, em outra thread, porque as
    portas são assíncronas e a sessão do backend é síncrona.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    async def recent(self, session_id: str, limit: int) -> tuple[ConversationTurn, ...]:
        return await run_in_threadpool(self._recent, session_id, limit)

    async def tokens_used(self, session_id: str) -> int:
        return await run_in_threadpool(self._tokens_used, session_id)

    def _recent(self, session_id: str, limit: int) -> tuple[ConversationTurn, ...]:
        if limit <= 0:
            return ()
        with Session(self._engine) as session:
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
        with Session(self._engine) as session:
            return int(
                session.scalar(
                    select(
                        func.coalesce(
                            func.sum(AiAuditoria.input_tokens + AiAuditoria.output_tokens), 0
                        )
                    ).where(AiAuditoria.session_id == session_id)
                )
                or 0
            )
