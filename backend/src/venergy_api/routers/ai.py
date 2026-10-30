"""Rotas do agente de IA: perguntar em linguagem natural e auditar como ele respondeu."""

import asyncio
import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Request, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from venergy_agent.application.ports import TextToSqlAgent

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

router = APIRouter(prefix="/ai", tags=["agente de IA"])

MAX_ID_AUDITORIA = 2_147_483_647

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


async def _responder(
    pedido: PerguntaIaSchema,
    agente: TextToSqlAgent,
    session: Session,
    request: Request,
    usuario: UsuarioLogado,
) -> RespostaIaSchema:
    session_id = str(pedido.session_id or uuid4())
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
