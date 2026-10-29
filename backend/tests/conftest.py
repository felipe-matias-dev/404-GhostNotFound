"""Fixtures compartilhadas: os testes usam o banco venergy_test, nunca o de desenvolvimento."""

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from venergy_api.auth import Perfil, UsuarioLogado
from venergy_api.carga import drop_agent_views
from venergy_api.config import Settings
from venergy_api.database import Base, create_db_engine, get_session
from venergy_api.main import create_app
from venergy_api.sessao import usuario_atual

FRONTEND_ORIGIN = "http://localhost:3000"
JWT_SECRET = "segredo-dos-testes-com-tamanho-suficiente-para-hs256"

# O padrão bate com o .env.example da raiz; quem mudou senha ou porta define a variável.
TEST_DATABASE_URL = os.environ.get(
    "VENERGY_API_TEST_DATABASE_URL",
    "postgresql+psycopg://venergy:troque-esta-senha@127.0.0.1:5433/venergy_test",
)


@pytest.fixture
def frontend_origin() -> str:
    return FRONTEND_ORIGIN


@pytest.fixture
def jwt_secret() -> str:
    return JWT_SECRET


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = create_db_engine(TEST_DATABASE_URL)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        pytest.fail(
            "Banco de testes indisponível. Suba com: docker compose up -d --wait db",
            pytrace=False,
        )

    # Limpa antes, para não herdar sobras de uma execução interrompida, e depois. As views do
    # agente saem primeiro: com elas, o banco não deixa apagar as tabelas da Gold.
    drop_test_database(engine)
    yield engine
    drop_test_database(engine)
    engine.dispose()


def drop_test_database(engine: Engine) -> None:
    with engine.begin() as connection:
        drop_agent_views(connection)
        Base.metadata.drop_all(connection)


@pytest.fixture
def perfil() -> Perfil:
    """Perfil do usuário que os clientes de teste fingem ser. Perdas é quem escreve nas ordens."""
    return Perfil.PERDAS


@pytest.fixture
def client_for(tmp_path: Path, perfil: Perfil) -> Callable[..., TestClient]:
    """Monta um cliente de teste cuja API usa a engine recebida no lugar da real.

    O cliente já nasce logado com o `perfil` da fixture, para os testes de cada rota não
    repetirem o login. `sem_login=True` devolve a API como ela é, para testar o login de verdade.
    Campos extras (`ai_limite_perguntas=2`, por exemplo) vão para as configurações da API.
    """

    def build(engine: Engine, *, sem_login: bool = False, **extras: Any) -> TestClient:
        # _env_file=None: os testes nunca leem o .env de quem está rodando.
        settings = Settings(
            _env_file=None,
            database_url=engine.url.render_as_string(),
            gold_dir=tmp_path / "gold",
            jwt_secret=JWT_SECRET,
            cors_origins=[FRONTEND_ORIGIN],
            **extras,
        )
        app = create_app(settings)

        def override_get_session() -> Iterator[Session]:
            with Session(engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        if not sem_login:
            usuario = UsuarioLogado(login="teste", nome="Teste", perfil=perfil)
            app.dependency_overrides[usuario_atual] = lambda: usuario
        return TestClient(app)

    return build


@pytest.fixture
def client(engine: Engine, client_for: Callable[..., TestClient]) -> TestClient:
    return client_for(engine)


@pytest.fixture(autouse=True)
def no_startup_audit_check(monkeypatch: pytest.MonkeyPatch) -> None:
    # O lifespan não mexe no banco de desenvolvimento de quem roda os testes.
    monkeypatch.setattr("venergy_api.main.garantir_colunas_na_subida", lambda *_: None)
