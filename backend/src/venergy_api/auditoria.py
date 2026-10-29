"""Gravação da trilha de auditoria do agente de IA, separada da rota para ser reaproveitada."""

import logging
from collections.abc import Callable
from datetime import timedelta

from sqlalchemy import Connection, Engine, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from venergy_agent.domain.answer import AgentAnswer

from venergy_api.models import AiAuditoria

logger = logging.getLogger(__name__)


def gravar_auditoria(
    session: Session, pergunta: str, session_id: str, answer: AgentAnswer
) -> AiAuditoria:
    """Grava a resposta do agente como ele a devolveu e confirma a transação."""
    # mode="json": a amostra de linhas traz Decimal e date, que o JSONB não aceita. O
    # Decimal vira texto, e assim o valor exato da consulta fica guardado sem arredondar.
    # Os campos do AgentAnswer têm o mesmo nome das colunas: um campo novo no contrato do
    # agente quebra aqui e nos testes, em vez de sumir da auditoria em silêncio.
    auditoria = AiAuditoria(
        session_id=session_id, pergunta=pergunta, **answer.model_dump(mode="json")
    )
    session.add(auditoria)
    session.commit()
    # Recarrega o id e o criado_em, que o banco preenche: o commit expira o objeto.
    session.refresh(auditoria)
    return auditoria


def contar_perguntas_recentes(session: Session, session_id: str, janela_segundos: int) -> int:
    """Quantas perguntas a sessão fez na janela, contadas pelas linhas da auditoria.

    O relógio é o do banco (o mesmo que preenche `criado_em`) e o contador mora na tabela, e não
    na memória da API: não some no restart e vale com mais de um processo.
    """
    return (
        session.scalar(
            select(func.count())
            .select_from(AiAuditoria)
            .where(
                AiAuditoria.session_id == session_id,
                AiAuditoria.criado_em > func.now() - timedelta(seconds=janela_segundos),
            )
        )
        or 0
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


def garantir_colunas_na_subida(obter_engine: Callable[[], Engine]) -> None:
    """Garante as colunas na subida da API, para um banco antigo não quebrar o /ai/ask.

    Quem atualiza o código sem rodar a carga não fica com a auditoria quebrada. Banco fora do
    ar não impede a subida: só o /ai e as telas que usam o banco ficam de fora, como já ficam.
    """
    try:
        with obter_engine().begin() as connection:
            garantir_colunas_de_tokens(connection)
    except SQLAlchemyError as error:
        logger.warning(
            "Não foi possível conferir as colunas da auditoria na subida (%s). "
            "A carga da Gold também as acrescenta.",
            type(error).__name__,
        )
