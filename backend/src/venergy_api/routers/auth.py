"""Rotas de login, sessão e logout: o token vai num cookie que o JavaScript da página não lê."""

from datetime import UTC, datetime
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Request, Response, status

from venergy_api.auth import (
    DURACAO_DA_SESSAO,
    UsuarioLogado,
    conferir_senha,
    criar_token,
    gerar_hash,
)
from venergy_api.database import SessionDep
from venergy_api.models import Usuario
from venergy_api.schemas import ErroSchema, LoginSchema
from venergy_api.sessao import COOKIE_SESSAO, UsuarioDep

router = APIRouter(prefix="/auth", tags=["autenticação"])

LOGIN_INVALIDO = "Login ou senha inválidos"

# httponly: o JavaScript da página não lê o token, então um XSS não rouba a sessão.
# samesite=lax: outro site não consegue disparar um POST ou PATCH com o cookie (CSRF).
# Sem secure: o portal roda em http no ambiente local; quem publicar com https liga o flag.
_ATRIBUTOS_DO_COOKIE = {"httponly": True, "samesite": "lax", "path": "/"}


@lru_cache
def _hash_de_ninguem() -> str:
    # Login inexistente também gasta o tempo de conferir um hash: sem isso, a resposta mais
    # rápida denunciaria quais logins existem.
    return gerar_hash("ninguem")


@router.post("/login", responses={status.HTTP_401_UNAUTHORIZED: {"model": ErroSchema}})
def entrar(
    pedido: LoginSchema, session: SessionDep, request: Request, response: Response
) -> UsuarioLogado:
    usuario = session.get(Usuario, pedido.login)
    senha_certa = conferir_senha(
        pedido.senha, usuario.senha_hash if usuario else _hash_de_ninguem()
    )
    if usuario is None or not senha_certa:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, LOGIN_INVALIDO)

    logado = UsuarioLogado(login=usuario.login, nome=usuario.nome, perfil=usuario.perfil)
    token = criar_token(logado, request.app.state.settings.jwt_secret, agora=datetime.now(UTC))
    response.set_cookie(
        COOKIE_SESSAO,
        token,
        max_age=int(DURACAO_DA_SESSAO.total_seconds()),
        **_ATRIBUTOS_DO_COOKIE,
    )
    return logado


@router.get("/me", responses={status.HTTP_401_UNAUTHORIZED: {"model": ErroSchema}})
def quem_sou_eu(usuario: UsuarioDep) -> UsuarioLogado:
    """Quem está logado. O portal chama ao abrir, para saber o perfil e montar o menu."""
    return usuario


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def sair(response: Response) -> None:
    """Apaga o cookie. Sem sessão também responde 204: sair duas vezes não é erro."""
    response.delete_cookie(COOKIE_SESSAO, **_ATRIBUTOS_DO_COOKIE)
