"""Fixtures compartilhadas: os testes usam o banco venergy_test, nunca o de desenvolvimento."""

import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from venergy_api.config import Settings
from venergy_api.database import Base, create_db_engine, get_session
from venergy_api.main import create_app

FRONTEND_ORIGIN = "http://localhost:5173"

# O padrão bate com o .env.example da raiz; quem mudou senha ou porta define a variável.
TEST_DATABASE_URL = os.environ.get(
    "VENERGY_API_TEST_DATABASE_URL",
    "postgresql+psycopg://venergy:troque-esta-senha@127.0.0.1:5433/venergy_test",
)


@pytest.fixture
def frontend_origin() -> str:
    return FRONTEND_ORIGIN


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = create_db_engine(TEST_DATABASE_URL)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        pytest.fail("Banco de testes indisponível. Suba com: docker compose up -d", pytrace=False)

    # Limpa antes, para não herdar sobras de uma execução interrompida, e depois.
    Base.metadata.drop_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client_for(tmp_path: Path) -> Callable[[Engine], TestClient]:
    """Monta um cliente de teste cuja API usa a engine recebida no lugar da real."""

    def build(engine: Engine) -> TestClient:
        # _env_file=None: os testes nunca leem o .env de quem está rodando.
        settings = Settings(
            _env_file=None,
            database_url=engine.url.render_as_string(),
            gold_dir=tmp_path / "gold",
            cors_origins=[FRONTEND_ORIGIN],
        )
        app = create_app(settings)

        def override_get_session() -> Iterator[Session]:
            with Session(engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        return TestClient(app)

    return build


@pytest.fixture
def client(engine: Engine, client_for: Callable[[Engine], TestClient]) -> TestClient:
    return client_for(engine)
