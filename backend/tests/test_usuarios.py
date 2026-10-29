"""Comando que cria os usuários de demonstração, um por perfil."""

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from venergy_api.auth import Perfil, conferir_senha
from venergy_api.models import Usuario
from venergy_api.usuarios import SenhaDemoAusenteError, criar_usuarios_demo


def _usuarios(engine: Engine) -> dict[str, Usuario]:
    with Session(engine) as session:
        return {u.login: u for u in session.scalars(select(Usuario))}


def test_cria_um_usuario_por_perfil_com_o_login_da_persona(engine: Engine):
    criar_usuarios_demo(engine, "senha-de-demonstracao")

    perfis = {login: usuario.perfil for login, usuario in _usuarios(engine).items()}
    assert perfis == {
        "henrique": Perfil.DIRETORIA,
        "camila": Perfil.ATENDIMENTO,
        "rafael": Perfil.PERDAS,
        "beatriz": Perfil.OPERACAO,
        "patricia": Perfil.TI,
    }


def test_guarda_so_o_hash_da_senha(engine: Engine):
    criar_usuarios_demo(engine, "senha-de-demonstracao")

    rafael = _usuarios(engine)["rafael"]
    assert "senha-de-demonstracao" not in rafael.senha_hash
    assert conferir_senha("senha-de-demonstracao", rafael.senha_hash)


def test_rodar_de_novo_nao_duplica_e_aplica_a_senha_nova(engine: Engine):
    criar_usuarios_demo(engine, "primeira-senha")
    criar_usuarios_demo(engine, "segunda-senha")

    usuarios = _usuarios(engine)
    assert len(usuarios) == 5
    assert conferir_senha("segunda-senha", usuarios["camila"].senha_hash)
    assert not conferir_senha("primeira-senha", usuarios["camila"].senha_hash)


@pytest.mark.parametrize("senha", [None, "", "   "])
def test_sem_senha_de_demonstracao_nao_cria_nada(engine: Engine, senha: str | None):
    with pytest.raises(SenhaDemoAusenteError):
        criar_usuarios_demo(engine, senha)

    # A tabela nem chega a ser criada: a falha vem antes de tocar no banco.
    with Session(engine) as session, pytest.raises(ProgrammingError):
        session.scalars(select(Usuario)).all()
