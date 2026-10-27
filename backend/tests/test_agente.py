import asyncio
import logging
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from venergy_agent.config import AgentSettings

from venergy_api.agente import AgenteDep, montar_agente

DATABASE_URL = "postgresql://agente@127.0.0.1/venergy"


@pytest.fixture(autouse=True)
def no_agent_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # Quem roda os testes pode ter a chave exportada no terminal: o teste não pode depender disso.
    for name in ("GOOGLE_API_KEY", "OPENROUTER_API_KEY", "DATABASE_URL"):
        monkeypatch.delenv(f"VENERGY_AGENT_{name}", raising=False)


class AgenteFalso:
    pass


def settings_without_key() -> AgentSettings:
    # _env_file=None: os testes nunca leem o .env de quem está rodando.
    return AgentSettings(_env_file=None, database_url=DATABASE_URL)


def test_returns_none_without_a_key(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        agente = asyncio.run(montar_agente(settings_without_key))

    assert agente is None
    assert "VENERGY_AGENT_GOOGLE_API_KEY" in caplog.text


def test_log_names_the_invalid_field_but_never_its_value(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def settings_with_bad_temperature() -> AgentSettings:
        return AgentSettings(
            _env_file=None,
            database_url=DATABASE_URL,
            google_api_key="chave-secreta",
            temperature=0.77,
        )

    with caplog.at_level(logging.WARNING):
        agente = asyncio.run(montar_agente(settings_with_bad_temperature))

    assert agente is None
    assert "temperature" in caplog.text
    assert "0.77" not in caplog.text
    assert "chave-secreta" not in caplog.text


def test_builds_the_agent_once_with_a_valid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    montados = []

    async def build_agent_falso(settings: AgentSettings) -> AgenteFalso:
        montados.append(settings)
        return AgenteFalso()

    monkeypatch.setattr("venergy_api.agente.build_agent", build_agent_falso)

    def valid_settings() -> AgentSettings:
        return AgentSettings(_env_file=None, database_url=DATABASE_URL, google_api_key="chave")

    agente = asyncio.run(montar_agente(valid_settings))

    assert isinstance(agente, AgenteFalso)
    assert len(montados) == 1


def test_api_starts_with_the_agent_stored_in_the_app_state(
    engine: Engine, client_for: Callable[[Engine], TestClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    agente = AgenteFalso()

    async def montar_agente_falso() -> AgenteFalso:
        return agente

    monkeypatch.setattr("venergy_api.main.montar_agente", montar_agente_falso)

    # Com o with, o TestClient executa o lifespan, como o uvicorn faz ao subir a API.
    with client_for(engine) as client:
        assert client.app.state.agente is agente


def test_api_starts_and_serves_health_when_the_agent_is_unavailable(
    engine: Engine, client_for: Callable[[Engine], TestClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def montar_agente_ausente() -> None:
        return None

    monkeypatch.setattr("venergy_api.main.montar_agente", montar_agente_ausente)

    with client_for(engine) as client:
        assert client.get("/health").status_code == 200


def test_dependency_answers_503_when_there_is_no_agent() -> None:
    app = FastAPI()

    @app.get("/probe")
    def probe(agente: AgenteDep) -> dict[str, str]:
        return {}

    response = TestClient(app).get("/probe")

    assert response.status_code == 503
    assert "VENERGY_AGENT_GOOGLE_API_KEY" in response.json()["detail"]
