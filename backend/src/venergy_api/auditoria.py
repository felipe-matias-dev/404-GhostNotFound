"""Gravação da trilha de auditoria do agente de IA, separada da rota para ser reaproveitada."""

from sqlalchemy.orm import Session
from venergy_agent.domain.answer import AgentAnswer

from venergy_api.models import AiAuditoria


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
