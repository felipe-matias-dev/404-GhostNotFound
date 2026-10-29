"""Regras de autenticação: perfis, hash de senha e token de sessão. Sem rota e sem banco."""

from datetime import datetime, timedelta
from enum import StrEnum

import jwt
from pwdlib import PasswordHash
from pydantic import BaseModel

# Um turno de trabalho. Sessão guardada no banco permitiria derrubar um token na hora, mas o
# case não pede isso; o prazo curto limita o risco de um token copiado (DEC-049).
DURACAO_DA_SESSAO = timedelta(hours=8)

ALGORITMO = "HS256"

_hasher = PasswordHash.recommended()


class Perfil(StrEnum):
    DIRETORIA = "diretoria"
    ATENDIMENTO = "atendimento"
    PERDAS = "perdas"
    OPERACAO = "operacao"
    TI = "ti"


class UsuarioLogado(BaseModel):
    login: str
    nome: str
    perfil: Perfil


def gerar_hash(senha: str) -> str:
    return _hasher.hash(senha)


def conferir_senha(senha: str, hash_da_senha: str) -> bool:
    return _hasher.verify(senha, hash_da_senha)


def criar_token(usuario: UsuarioLogado, segredo: str, agora: datetime) -> str:
    carga = {
        "sub": usuario.login,
        "nome": usuario.nome,
        "perfil": usuario.perfil.value,
        "exp": agora + DURACAO_DA_SESSAO,
    }
    return jwt.encode(carga, segredo, algorithm=ALGORITMO)


def ler_token(token: str, segredo: str) -> UsuarioLogado | None:
    """Devolve o usuário do token, ou None se ele for inválido, vencido ou de outro segredo."""
    try:
        # Só o HS256 é aceito: sem a lista, um token com algoritmo "none" passaria sem assinatura.
        carga = jwt.decode(
            token,
            segredo,
            algorithms=[ALGORITMO],
            options={"require": ["exp", "sub", "nome", "perfil"]},
        )
        return UsuarioLogado(login=carga["sub"], nome=carga["nome"], perfil=carga["perfil"])
    except (jwt.PyJWTError, ValueError):
        # ValueError cobre o perfil que não existe (ValidationError do pydantic herda dele).
        return None
