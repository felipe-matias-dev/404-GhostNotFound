"""Rotas do agente de IA: perguntar em linguagem natural e auditar como ele respondeu."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import SQLAlchemyError

from venergy_api.agente import AgenteDep
from venergy_api.auditoria import gravar_auditoria
from venergy_api.auth import Perfil
from venergy_api.database import SessionDep
from venergy_api.models import AiAuditoria
from venergy_api.schemas import AuditoriaIaSchema, ErroSchema, PerguntaIaSchema, RespostaIaSchema
from venergy_api.sessao import exigir_perfil

router = APIRouter(prefix="/ai", tags=["agente de IA"])

MAX_ID_AUDITORIA = 2_147_483_647

logger = logging.getLogger(__name__)


@router.post("/ask", responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErroSchema}})
async def perguntar(
    pedido: PerguntaIaSchema, agente: AgenteDep, session: SessionDep
) -> RespostaIaSchema:
    """Pergunta ao agente e grava a resposta, qualquer que seja o status, na auditoria."""
    answer = await agente.ask(pedido.question, pedido.session_id)
    try:
        # A sessão do backend é síncrona: a gravação sai do laço de eventos para não
        # travar as outras requisições enquanto o banco responde.
        auditoria = await run_in_threadpool(
            gravar_auditoria, session, pedido.question, pedido.session_id, answer
        )
    except SQLAlchemyError as error:
        # Sem auditoria, sem resposta: entregar algo que não dá para conferir depois
        # quebraria a razão de ser da trilha. Só o tipo do erro vai para o log: a mensagem
        # do SQLAlchemy traz os parâmetros do INSERT, ou seja, a pergunta e as linhas.
        logger.error(
            "Falha ao gravar a auditoria (request_id=%s): %s",
            answer.request_id,
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível gravar a auditoria, então a resposta não foi entregue.",
        ) from error
    return RespostaIaSchema.model_validate(auditoria)


@router.get(
    "/audit/{audit_id}",
    # Só a TI: a trilha guarda a pergunta e as linhas de qualquer pessoa, e pode ter dado de UC.
    dependencies=[Depends(exigir_perfil(Perfil.TI))],
    responses={
        status.HTTP_403_FORBIDDEN: {"model": ErroSchema},
        status.HTTP_404_NOT_FOUND: {"model": ErroSchema},
    },
)
def obter_auditoria(
    # O teto é o de uma coluna int4: sem ele, um id enorme viraria erro do banco (500) em
    # vez de um 422 de entrada inválida.
    audit_id: Annotated[int, Path(ge=1, le=MAX_ID_AUDITORIA)],
    session: SessionDep,
) -> AuditoriaIaSchema:
    """O registro completo de uma resposta: pergunta, SQL, views, linhas, modelo e horário."""
    auditoria = session.get(AiAuditoria, audit_id)
    if auditoria is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registro de auditoria {audit_id} não encontrado",
        )
    return AuditoriaIaSchema.model_validate(auditoria)
