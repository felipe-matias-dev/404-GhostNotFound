"""Fixtures compartilhadas: cada teste usa um SQLite temporário, nunca o banco local."""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from venergy_api.database import create_db_engine, get_session
from venergy_api.main import create_app


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    engine = create_db_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    yield engine
    # No Windows, o arquivo fica travado enquanto houver conexão aberta.
    engine.dispose()


@pytest.fixture
def client_for() -> Callable[[Engine], TestClient]:
    """Monta um cliente de teste cuja API usa a engine recebida no lugar da real."""

    def build(engine: Engine) -> TestClient:
        app = create_app()

        def override_get_session() -> Iterator[Session]:
            with Session(engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        return TestClient(app)

    return build


@pytest.fixture
def client(engine: Engine, client_for: Callable[[Engine], TestClient]) -> TestClient:
    return client_for(engine)
