"""Rotas do agente de IA: perguntar em linguagem natural e auditar como ele respondeu."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID, uuid4

import anyio
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from venergy_agent.application.ports import TextToSqlAgent
from venergy_agent.domain.answer import AgentAnswer, AnswerStatus, Confidence
from venergy_agent.domain.events import AnswerEvent, StageEvent

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
from venergy_api.rastreamento import anotar_resposta_do_agente
from venergy_api.schemas import (
    AlteracaoSessaoIaSchema,
    AuditoriaIaSchema,
    ErroSchema,
    PerguntaIaSchema,
    RespostaIaSchema,
    SessaoIaSchema,
)
from venergy_api.sessao import UsuarioDep, exigir_perfil
from venergy_api.sessoes_ia import (
    alterar_sessao,
    excluir_sessao,
    listar_sessoes,
    sessao_disponivel,
    sessao_excluida,
)
from venergy_api.sse import PING, evento_sse

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
        status.HTTP_409_CONFLICT: {"model": ErroSchema},
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
    """Verifica a sessão e o limite antes de chamar o modelo."""
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
        excluida = await run_in_threadpool(sessao_excluida, session, session_id)
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
    if excluida:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta conversa foi excluída. Comece uma conversa nova.",
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
    anotar_resposta_do_agente(answer)
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


def _erro_sse(detalhe: str) -> str:
    return evento_sse("error", json.dumps({"type": "error", "detail": detalhe}, ensure_ascii=False))


def _gravar_abandono(
    session: Session,
    pergunta: str,
    session_id: str,
    login: str,
    ultima_etapa: StageEvent | None,
) -> None:
    """A pergunta abandonada conta no limite e no orçamento: sem isso, desconectar burlaria os dois.

    Os tokens são os da última etapa emitida. Os de uma chamada ao modelo ainda em curso não
    entram, porque o provedor só os informa ao terminar.
    """
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
        input_tokens=ultima_etapa.input_tokens if ultima_etapa else 0,
        output_tokens=ultima_etapa.output_tokens if ultima_etapa else 0,
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
            ultima_etapa: StageEvent | None = None
            abandonada = False
            try:
                while answer is None:
                    proximo = proximo or asyncio.ensure_future(anext(eventos))
                    prontos, _ = await asyncio.wait({proximo}, timeout=INTERVALO_PING_SEGUNDOS)
                    if not prontos:
                        yield PING
                        continue
                    evento = proximo.result()
                    proximo = None
                    if isinstance(evento, AnswerEvent):
                        answer = evento.answer
                    else:
                        ultima_etapa = evento
                        yield evento_sse(evento.type, evento.model_dump_json())
            except StopAsyncIteration:
                proximo = None
            except (asyncio.CancelledError, GeneratorExit):
                abandonada = True
                raise
            finally:
                usuario_da_requisicao.reset(token)
                # Blindado: num cliente que desconectou, todo await seria cancelado de novo.
                with anyio.CancelScope(shield=True):
                    if proximo is not None:
                        proximo.cancel()
                        await asyncio.gather(proximo, return_exceptions=True)
                    await eventos.aclose()
                    if abandonada:
                        await run_in_threadpool(
                            _gravar_abandono,
                            sessao,
                            pergunta,
                            session_id,
                            usuario.login,
                            ultima_etapa,
                        )
            if answer is None:
                yield _erro_sse("O agente não devolveu uma resposta. Tente de novo.")
                return
            anotar_resposta_do_agente(answer)
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
            yield evento_sse(
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
        status.HTTP_409_CONFLICT: {"model": ErroSchema},
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


def _exigir_sessao(session: Session, session_id: str, login: str) -> None:
    # 404 também para a sessão de outra pessoa: a resposta não revela que o id existe.
    if not sessao_disponivel(session, session_id, login):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada")


@router.get("/sessions")
def obter_sessoes(session: SessionDep, usuario: UsuarioDep) -> list[SessaoIaSchema]:
    """As conversas não excluídas do usuário: favoritas primeiro, depois as mais recentes."""
    return listar_sessoes(session, usuario.login)


@router.patch(
    "/sessions/{session_id}",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErroSchema}},
)
def patch_sessao(
    session_id: UUID,
    alteracao: AlteracaoSessaoIaSchema,
    session: SessionDep,
    usuario: UsuarioDep,
) -> SessaoIaSchema:
    """Renomeia ou favorita uma conversa do usuário."""
    _exigir_sessao(session, str(session_id), usuario.login)
    alterar_sessao(
        session, str(session_id), usuario.login, alteracao.model_dump(exclude_unset=True)
    )
    sessoes = listar_sessoes(session, usuario.login, str(session_id))
    # Um DELETE simultâneo pode ter escondido a conversa depois da verificação.
    if not sessoes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada")
    return sessoes[0]


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErroSchema}},
)
async def delete_sessao(
    session_id: UUID, session: SessionDep, request: Request, usuario: UsuarioDep
) -> None:
    """Esconde a conversa do usuário. A auditoria dela continua intacta para a TI.

    Espera a pergunta em andamento do usuário terminar: sem a trava, o turno seria gravado
    numa conversa já escondida.
    """
    async with trava_do_usuario(request.app, usuario.login):
        await run_in_threadpool(_exigir_sessao, session, str(session_id), usuario.login)
        await run_in_threadpool(excluir_sessao, session, str(session_id), usuario.login)


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
