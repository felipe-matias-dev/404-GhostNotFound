import logging
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.orm import Session

from venergy_api.database import Base
from venergy_api.estrutura_app import garantir_estrutura_na_subida
from venergy_api.models import OrdemEvento


def autor_login_existe(engine: Engine) -> bool:
    colunas = inspect(engine).get_columns("ordem_evento", schema="app")
    return any(coluna["name"] == "autor_login" for coluna in colunas)


@pytest.fixture
def banco_antigo(engine: Engine) -> Engine:
    # O banco de quem criou as tabelas antes da coluna: uma ordem com um evento, sem autor_login.
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE app.ordem_evento DROP COLUMN autor_login"))
        connection.execute(
            text("INSERT INTO app.ordem_inspecao (cod_uc, status) VALUES ('0001', 'GERADA')")
        )
        connection.execute(
            text(
                "INSERT INTO app.ordem_evento (ordem_id, status_novo) "
                "SELECT id, 'GERADA' FROM app.ordem_inspecao"
            )
        )
    return engine


def test_api_startup_adds_the_author_column_without_losing_events(
    banco_antigo: Engine,
    client_for: Callable[[Engine], TestClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def sem_agente(**_: object) -> None:
        return None

    monkeypatch.setattr("venergy_api.main.montar_agente", sem_agente)

    # Com o with, o TestClient executa o lifespan, como o uvicorn faz ao subir a API.
    with client_for(banco_antigo):
        pass

    assert autor_login_existe(banco_antigo)
    with Session(banco_antigo) as session:
        [evento] = session.scalars(select(OrdemEvento)).all()
        assert evento.autor_login is None


def test_startup_on_a_database_without_tables_does_not_warn(
    engine: Engine, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="venergy_api.estrutura_app"):
        garantir_estrutura_na_subida(engine.url.render_as_string(hide_password=False))

    assert caplog.text == ""


def test_startup_with_the_database_down_only_warns_without_the_credentials(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Porta 1: ninguém escuta, a conexão é recusada na hora.
    url = "postgresql+psycopg://usuario-banco:senha-secreta@127.0.0.1:1/venergy"

    with caplog.at_level(logging.WARNING, logger="venergy_api.estrutura_app"):
        garantir_estrutura_na_subida(url)

    assert "OperationalError" in caplog.text
    assert "senha-secreta" not in caplog.text
    assert "usuario-banco" not in caplog.text
