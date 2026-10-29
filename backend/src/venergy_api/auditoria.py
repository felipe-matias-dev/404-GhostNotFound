"""Gravação da trilha de auditoria do agente de IA, separada da rota para ser reaproveitada."""

import logging
from collections.abc import Callable
from datetime import timedelta

from sqlalchemy import Connection, Engine, exists, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from venergy_agent.domain.answer import AgentAnswer

from venergy_api.models import AiAuditoria

logger = logging.getLogger(__name__)


def gravar_auditoria(
    session: Session, pergunta: str, session_id: str, answer: AgentAnswer, usuario: str | None
) -> AiAuditoria:
    """Grava a resposta do agente como ele a devolveu e confirma a transação."""
    # mode="json": a amostra de linhas traz Decimal e date, que o JSONB não aceita. O
    # Decimal vira texto, e assim o valor exato da consulta fica guardado sem arredondar.
    # Os campos do AgentAnswer têm o mesmo nome das colunas: um campo novo no contrato do
    # agente quebra aqui e nos testes, em vez de sumir da auditoria em silêncio.
    auditoria = AiAuditoria(
        session_id=session_id,
        pergunta=pergunta,
        usuario=usuario,
        **answer.model_dump(mode="json"),
    )
    session.add(auditoria)
    session.commit()
    # Recarrega o id e o criado_em, que o banco preenche: o commit expira o objeto.
    session.refresh(auditoria)
    return auditoria


def contar_perguntas_recentes(session: Session, usuario: str, janela_segundos: int) -> int:
    """Quantas perguntas o usuário fez na janela, em todas as sessões, pelas linhas da auditoria.

    O relógio é o do banco (o mesmo que preenche `criado_em`) e o contador mora na tabela, e não
    na memória da API: não some no restart e vale com mais de um processo. Conta por usuário, e
    não por sessão: o cliente escolhe o session_id e trocá-lo não pode zerar o limite.
    """
    return (
        session.scalar(
            select(func.count())
            .select_from(AiAuditoria)
            .where(
                AiAuditoria.usuario == usuario,
                AiAuditoria.criado_em > func.now() - timedelta(seconds=janela_segundos),
            )
        )
        or 0
    )


def sessao_de_outro_usuario(session: Session, session_id: str, usuario: str) -> bool:
    """Se a sessão já tem registros que não são do usuário (inclusive os sem dono, de antes da
    coluna): o histórico dela não pode ser lido nem continuado por ele."""
    return bool(
        session.scalar(
            select(
                exists().where(
                    AiAuditoria.session_id == session_id,
                    AiAuditoria.usuario.is_distinct_from(usuario),
                )
            )
        )
    )


def garantir_colunas_de_tokens(connection: Connection) -> None:
    """Acrescenta as colunas de tokens à auditoria de um banco criado antes delas.

    Sem migrações, o `create_all` não acrescenta coluna em tabela que já existe, e a gravação
    (`**answer.model_dump()`) quebraria. Só acrescenta se faltar: nunca apaga nem altera dado.
    """
    connection.execute(
        text(
            "ALTER TABLE IF EXISTS app.ai_auditoria "
            "ADD COLUMN IF NOT EXISTS input_tokens integer NOT NULL DEFAULT 0, "
            "ADD COLUMN IF NOT EXISTS output_tokens integer NOT NULL DEFAULT 0"
        )
    )


def garantir_indice_da_sessao(connection: Connection) -> None:
    """Acrescenta o índice (session_id, id) à auditoria de um banco criado antes dele.

    O contador do limite, a soma de tokens e o histórico filtram por sessão a cada pergunta.
    Sem o índice, isso lê a tabela inteira, que só cresce.
    """
    connection.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_ai_auditoria_session_id "
            "ON app.ai_auditoria (session_id, id)"
        )
    )


def garantir_coluna_do_usuario(connection: Connection) -> None:
    """Acrescenta a coluna `usuario` e o índice (usuario, id) à auditoria de um banco antigo.

    O limite de perguntas e o orçamento de tokens filtram por usuário a cada pergunta. As
    linhas de antes ficam com usuário nulo. Só acrescenta: nunca apaga nem altera dado.
    """
    connection.execute(
        text("ALTER TABLE IF EXISTS app.ai_auditoria ADD COLUMN IF NOT EXISTS usuario text")
    )
    connection.execute(
        text("CREATE INDEX IF NOT EXISTS ix_ai_auditoria_usuario ON app.ai_auditoria (usuario, id)")
    )


def garantir_estrutura_da_auditoria(connection: Connection) -> None:
    garantir_colunas_de_tokens(connection)
    garantir_coluna_do_usuario(connection)
    garantir_indice_da_sessao(connection)


def garantir_colunas_na_subida(obter_engine: Callable[[], Engine]) -> None:
    """Garante as colunas na subida da API, para um banco antigo não quebrar o /ai/ask.

    Quem atualiza o código sem rodar a carga não fica com a auditoria quebrada. Banco fora do
    ar não impede a subida: só o /ai e as telas que usam o banco ficam de fora, como já ficam.
    """
    try:
        with obter_engine().begin() as connection:
            garantir_estrutura_da_auditoria(connection)
    except SQLAlchemyError as error:
        logger.warning(
            "Não foi possível conferir as colunas da auditoria na subida (%s). "
            "A carga da Gold também as acrescenta.",
            type(error).__name__,
        )
