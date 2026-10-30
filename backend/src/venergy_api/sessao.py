"""Dependências de login: quem está na requisição e o que o perfil dele pode fazer."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyCookie

from venergy_api.auth import Perfil, UsuarioLogado, ler_token

COOKIE_SESSAO = "venergy_sessao"

# auto_error=False: o 401 sai daqui, com a mesma mensagem para cookie ausente e inválido.
# A classe só ensina o /docs a mandar o cookie.
_cookie_de_sessao = APIKeyCookie(name=COOKIE_SESSAO, auto_error=False)


def usuario_atual(
    request: Request, token: Annotated[str | None, Depends(_cookie_de_sessao)]
) -> UsuarioLogado:
    # O segredo vem das configurações do app, e não de get_settings(): os testes montam o app
    # com as próprias, sem .env.
    usuario = ler_token(token, request.app.state.settings.jwt_secret) if token else None
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Faça login para continuar")
    return usuario


UsuarioDep = Annotated[UsuarioLogado, Depends(usuario_atual)]


def exigir_perfil(*perfis: Perfil) -> Callable[[UsuarioLogado], UsuarioLogado]:
    def verificar(usuario: UsuarioDep) -> UsuarioLogado:
        if usuario.perfil not in perfis:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Seu perfil não pode fazer isso")
        return usuario

    return verificar
