"""Rotas do agente de IA: perguntar em linguagem natural e auditar como ele respondeu."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from venergy_agent.application.ports import TextToSqlAgent
from venergy_agent.domain.answer import AgentAnswer, AnswerStatus, Confidence
from venergy_agent.domain.events import AnswerEvent

from venergy_api.agente import AgenteDep
from venergy_api.auditoria import (
    contar_perguntas_recentes,
    gravar_auditoria,
    sessao_de_outro_usuario,
)
from venergy_api.auth import Perfil, UsuarioLogado
from venergy_api.database import SessionDep
from venergy_api.historico_ia import usuario_da_requisicao
from venergy_api.models import AiAuditoria
from venergy_api.schemas import AuditoriaIaSchema, ErroSchema, PerguntaIaSchema, RespostaIaSchema
from venergy_api.sessao import UsuarioDep, exigir_perfil

router = APIRouter(prefix="/ai", tags=["agente de IA"])

MAX_ID_AUDITORIA = 2_147_483_647
INTERVALO_PING_SEGUNDOS = 15
RESPOSTA_ABANDONADA = "O cliente desconectou antes da resposta."
# O FastAPI não descreve SSE sozinho: cada mensagem traz um destes objetos no campo data.
EVENTOS_SSE: dict[str, Any] = {
    "oneOf": [
        {
            "title": "StageEvent",
            "type": "object",
            "required": ["type", "stage", "label", "attempt"],
            "properties": {
                "type": {"const": "stage"},
                "stage": {"enum": ["understanding", "querying", "correcting", "writing"]},
                "label": {"type": "string"},
                "attempt": {"type": "integer"},
            },
        },
        {
            "title": "AnswerEvent",
            "type": "object",
            "required": ["type", "answer"],
            "properties": {
                "type": {"const": "answer"},
                "answer": {"$ref": "#/components/schemas/RespostaIaSchema"},
            },
        },
        {
            "title": "ErrorEvent",
            "type": "object",
            "required": ["type", "detail"],
            "properties": {"type": {"const": "error"}, "detail": {"type": "string"}},
        },
    ]
}

logger = logging.getLogger(__name__)


def trava_do_usuario(app: FastAPI, login: str) -> asyncio.Lock:
    return app.state.ai_travas.setdefault(login, asyncio.Lock())


@router.post(
    "/ask",
    responses={
        status.HTTP_403_FORBIDDEN: {"model": ErroSchema},
        status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErroSchema},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErroSchema},
    },
)
async def perguntar(
    pedido: PerguntaIaSchema,
    agente: AgenteDep,
    session: SessionDep,
    request: Request,
    usuario: UsuarioDep,
) -> RespostaIaSchema:
    """Pergunta ao agente e grava a resposta, qualquer que seja o status, na auditoria.

    Responde 403, sem chamar o agente, se o session_id já pertence a outro usuário, e 429, também
    sem chamar o agente, se o usuário já fez o máximo de perguntas na janela. O limite e o
    orçamento de tokens valem por usuário, em todas as sessões dele: omitir ou trocar o
    session_id não zera nada. O session_id só separa as conversas, e cada uma é de quem a
    começou (DEC-046).
    """
    # Uma pergunta por vez para cada usuário: sem a trava, pedidos simultâneos passariam juntos
    # pela contagem do limite, porque a auditoria só é gravada depois da resposta do modelo.
    async with trava_do_usuario(request.app, usuario.login):
        return await _responder(pedido, agente, session, request, usuario)


async def _verificar_pedido(
    session_id: str, session: Session, request: Request, usuario: UsuarioLogado
) -> None:
    """Responde 403, 429 ou 503 antes de o modelo ser chamado, como a rota documenta."""
    limite = request.app.state.settings.ai_limite_perguntas
    janela = request.app.state.settings.ai_janela_segundos
    try:
        alheia = await run_in_threadpool(
            sessao_de_outro_usuario, session, session_id, usuario.login
        )
        feitas = (
            await run_in_threadpool(contar_perguntas_recentes, session, usuario.login, janela)
            if limite > 0 and not alheia
            else 0
        )
    except SQLAlchemyError as error:
        # Só o tipo do erro vai para o log: a mensagem do SQLAlchemy traz os parâmetros.
        logger.error("Falha ao verificar a sessão e o limite (%s)", type(error).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível verificar o limite de perguntas agora. Tente de novo.",
        ) from error
    # Só as verificações usaram a transação: solta a conexão antes da chamada ao modelo, que
    # leva segundos e não deve segurar uma conexão do pool.
    await run_in_threadpool(session.rollback)
    if alheia:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta sessão pertence a outro usuário. Comece uma conversa nova.",
        )
    if feitas >= limite > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Você atingiu o limite de {limite} perguntas a cada "
                f"{janela} segundos. Aguarde um pouco e tente de novo."
            ),
            # A janela inteira é o teto da espera: o relógio só libera a pergunta mais velha.
            headers={"Retry-After": str(janela)},
        )


async def _responder(
    pedido: PerguntaIaSchema,
    agente: TextToSqlAgent,
    session: Session,
    request: Request,
    usuario: UsuarioLogado,
) -> RespostaIaSchema:
    session_id = str(pedido.session_id or uuid4())
    await _verificar_pedido(session_id, session, request, usuario)
    token = usuario_da_requisicao.set(usuario.login)
    try:
        answer = await agente.ask(pedido.question, session_id)
    finally:
        usuario_da_requisicao.reset(token)
    try:
        # A sessão do backend é síncrona: a gravação sai do laço de eventos para não
        # travar as outras requisições enquanto o banco responde.
        auditoria = await run_in_threadpool(
            gravar_auditoria, session, pedido.question, session_id, answer, usuario.login
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


def _sse(evento: str, dados: str) -> str:
    return f"event: {evento}\ndata: {dados}\n\n"


def _erro_sse(detalhe: str) -> str:
    return _sse("error", json.dumps({"type": "error", "detail": detalhe}, ensure_ascii=False))


def _gravar_abandono(session: Session, pergunta: str, session_id: str, login: str) -> None:
    """A pergunta abandonada conta no limite: sem isso, desconectar burlaria a trava de uso."""
    abandono = AgentAnswer(
        answer=RESPOSTA_ABANDONADA,
        status=AnswerStatus.FAILED,
        sql=None,
        rows=(),
        row_count=0,
        truncated=False,
        confidence=Confidence.UNKNOWN,
        sources=(),
        assumptions=(),
        clarification=None,
        refused_reason=RESPOSTA_ABANDONADA,
        request_id=uuid4().hex,
        model="nao_informado",
        prompt_version="nao_informado",
        latency_ms=0,
    )
    try:
        gravar_auditoria(session, pergunta, session_id, abandono, login)
    except SQLAlchemyError as error:
        logger.error("Falha ao gravar a pergunta abandonada: %s", type(error).__name__)


async def _eventos(
    pergunta: str,
    session_id: str,
    agente: TextToSqlAgent,
    sessao: Session,
    request: Request,
    usuario: UsuarioLogado,
) -> AsyncIterator[str]:
    # Sessão própria: a da dependência não acompanha a vida inteira da resposta em stream.
    with sessao:
        # A rota verificou antes de abrir o stream, sem segurar a trava, para responder com o
        # status HTTP. Aqui, já com a trava, a verificação repete: outro pedido pode ter passado.
        async with trava_do_usuario(request.app, usuario.login):
            try:
                await _verificar_pedido(session_id, sessao, request, usuario)
            except HTTPException as error:
                yield _erro_sse(error.detail)
                return
            answer: AgentAnswer | None = None
            token = usuario_da_requisicao.set(usuario.login)
            eventos = agente.stream(pergunta, session_id)
            proximo: asyncio.Future[Any] | None = None
            try:
                while answer is None:
                    proximo = proximo or asyncio.ensure_future(anext(eventos))
                    prontos, _ = await asyncio.wait({proximo}, timeout=INTERVALO_PING_SEGUNDOS)
                    if not prontos:
                        yield ": ping\n\n"
                        continue
                    evento = proximo.result()
                    proximo = None
                    if isinstance(evento, AnswerEvent):
                        answer = evento.answer
                    else:
                        yield _sse(evento.type, evento.model_dump_json())
            except StopAsyncIteration:
                proximo = None
            except (asyncio.CancelledError, GeneratorExit):
                _gravar_abandono(sessao, pergunta, session_id, usuario.login)
                raise
            finally:
                usuario_da_requisicao.reset(token)
                if proximo is not None:
                    proximo.cancel()
                    await asyncio.gather(proximo, return_exceptions=True)
                await eventos.aclose()
            if answer is None:
                yield _erro_sse("O agente não devolveu uma resposta. Tente de novo.")
                return
            try:
                auditoria = await run_in_threadpool(
                    gravar_auditoria, sessao, pergunta, session_id, answer, usuario.login
                )
            except SQLAlchemyError as error:
                logger.error(
                    "Falha ao gravar a auditoria (request_id=%s): %s",
                    answer.request_id,
                    type(error).__name__,
                )
                yield _erro_sse(
                    "Não foi possível gravar a auditoria, então a resposta não foi entregue."
                )
                return
            resposta = RespostaIaSchema.model_validate(auditoria)
            yield _sse(
                "answer",
                f'{{"type":"answer","answer":{resposta.model_dump_json()}}}',
            )


@router.post(
    "/ask/stream",
    response_class=StreamingResponse,
    responses={
        status.HTTP_200_OK: {
            "description": "Eventos SSE: stage, ping de comentário e, por último, answer ou error.",
            "content": {"text/event-stream": {"schema": EVENTOS_SSE}},
        },
        status.HTTP_403_FORBIDDEN: {"model": ErroSchema},
        status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErroSchema},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErroSchema},
    },
)
async def perguntar_em_stream(
    pedido: PerguntaIaSchema,
    agente: AgenteDep,
    session: SessionDep,
    request: Request,
    usuario: UsuarioDep,
) -> StreamingResponse:
    """A mesma pergunta do POST /ai/ask, com as etapas do agente até a resposta final (DEC-055).

    O texto só chega inteiro, no último evento, porque os números são conferidos antes (DEC-019).
    Erros de verificação respondem com o status HTTP, sem abrir o stream.
    """
    session_id = str(pedido.session_id or uuid4())
    async with trava_do_usuario(request.app, usuario.login):
        await _verificar_pedido(session_id, session, request, usuario)
    return StreamingResponse(
        _eventos(
            pedido.question,
            session_id,
            agente,
            Session(session.get_bind()),
            request,
            usuario,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
