"""Cria os usuários de demonstração, um por perfil.

Uso: uv run python -m venergy_api.usuarios

A senha vem de VENERGY_API_SENHA_DEMO e é a mesma para todos: serve só para rodar o portal
localmente. Rodar de novo não duplica ninguém e aplica a senha que estiver no .env.
"""

from sqlalchemy import Engine
from sqlalchemy.dialects.postgresql import insert

from venergy_api.auth import Perfil, gerar_hash
from venergy_api.config import get_settings
from venergy_api.database import get_engine
from venergy_api.models import Usuario

# Uma persona do case por perfil: o nome na tela é o de quem a banca conhece.
USUARIOS_DEMO = (
    ("henrique", "Henrique", Perfil.DIRETORIA),
    ("camila", "Camila", Perfil.ATENDIMENTO),
    ("rafael", "Rafael", Perfil.PERDAS),
    ("beatriz", "Beatriz", Perfil.OPERACAO),
    ("patricia", "Patrícia", Perfil.TI),
)


class SenhaDemoAusenteError(Exception):
    """VENERGY_API_SENHA_DEMO não foi definida."""


def criar_usuarios_demo(engine: Engine, senha: str | None) -> int:
    if senha is None or not senha.strip():
        raise SenhaDemoAusenteError("defina VENERGY_API_SENHA_DEMO no backend/.env")

    # Um hash por usuário: o sal é sorteado a cada geração, então os hashes saem diferentes
    # mesmo com a senha igual.
    linhas = [
        {"login": login, "nome": nome, "perfil": perfil, "senha_hash": gerar_hash(senha)}
        for login, nome, perfil in USUARIOS_DEMO
    ]
    with engine.begin() as connection:
        # Só esta tabela: as outras do schema app ficam como estão.
        Usuario.__table__.create(connection, checkfirst=True)
        comando = insert(Usuario)
        connection.execute(
            comando.on_conflict_do_update(
                index_elements=[Usuario.login],
                set_={
                    "nome": comando.excluded.nome,
                    "perfil": comando.excluded.perfil,
                    "senha_hash": comando.excluded.senha_hash,
                },
            ),
            linhas,
        )
    return len(linhas)


def main() -> None:
    try:
        total = criar_usuarios_demo(get_engine(), get_settings().senha_demo)
    except SenhaDemoAusenteError as error:
        raise SystemExit(f"Nenhum usuário criado: {error}") from error
    print(f"{total} usuários de demonstração prontos")


if __name__ == "__main__":
    main()
