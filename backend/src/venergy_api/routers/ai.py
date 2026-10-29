"""Rotas do agente de IA: perguntar em linguagem natural e auditar como ele respondeu."""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import SQLAlchemyError

from venergy_api.agente import AgenteDep
from venergy_api.auditoria import contar_perguntas_recentes, gravar_auditoria
from venergy_api.database import SessionDep
from venergy_api.models import AiAuditoria
from venergy_api.schemas import AuditoriaIaSchema, ErroSchema, PerguntaIaSchema, RespostaIaSchema

router = APIRouter(prefix="/ai", tags=["agente de IA"])

MAX_ID_AUDITORIA = 2_147_483_647

logger = logging.getLogger(__name__)


@router.post(
    "/ask",
    responses={
        status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErroSchema},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErroSchema},
    },
)
async def perguntar(
    pedido: PerguntaIaSchema, agente: AgenteDep, session: SessionDep, request: Request
) -> RespostaIaSchema:
    """Pergunta ao agente e grava a resposta, qualquer que seja o status, na auditoria.

    Responde 429, sem chamar o agente, se a sessão já fez o máximo de perguntas na janela.
    """
    limite = request.app.state.ai_limite_perguntas
    janela = request.app.state.ai_janela_segundos
    if limite > 0:
        feitas = await run_in_threadpool(
            contar_perguntas_recentes, session, pedido.session_id, janela
        )
        if feitas >= limite:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Esta conversa atingiu o limite de {limite} perguntas a cada "
                    f"{janela} segundos. Aguarde um pouco e tente de novo."
                ),
                # A janela inteira é o teto da espera: o relógio só libera a pergunta mais velha.
                headers={"Retry-After": str(janela)},
            )
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


@router.get("/audit/{audit_id}", responses={status.HTTP_404_NOT_FOUND: {"model": ErroSchema}})
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
