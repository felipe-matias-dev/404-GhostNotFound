import asyncio
import logging
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from venergy_agent.config import AgentSettings
from venergy_agent.infrastructure.semantic_source import SemanticLayerError

from venergy_api.agente import (
    AgenteDep,
    RedatorInsightsDep,
    configurar_logs_do_agente,
    montar_agente,
    montar_redator_insights,
)
from venergy_api.historico_ia import HistoricoAuditoria

DATABASE_URL = "postgresql://agente@127.0.0.1/venergy"


@pytest.fixture(autouse=True)
def no_agent_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # Quem roda os testes pode ter a chave exportada no terminal: o teste não pode depender disso.
    for name in ("GOOGLE_API_KEY", "OPENROUTER_API_KEY", "DATABASE_URL"):
        monkeypatch.delenv(f"VENERGY_AGENT_{name}", raising=False)


@pytest.fixture(autouse=True)
def no_insight_writer(monkeypatch: pytest.MonkeyPatch) -> None:
    async def montar_redator_ausente() -> None:
        return None

    monkeypatch.setattr("venergy_api.main.montar_redator_insights", montar_redator_ausente)


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

    async def build_agent_falso(settings: AgentSettings, **portas: object) -> AgenteFalso:
        montados.append((settings, portas))
        return AgenteFalso()

    monkeypatch.setattr("venergy_api.agente.build_agent", build_agent_falso)

    def valid_settings() -> AgentSettings:
        return AgentSettings(_env_file=None, database_url=DATABASE_URL, google_api_key="chave")

    agente = asyncio.run(montar_agente(valid_settings, lambda: object()))

    assert isinstance(agente, AgenteFalso)
    assert len(montados) == 1


def test_wires_the_audit_history_into_both_agent_ports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    montados = []

    async def build_agent_falso(settings: AgentSettings, **portas: object) -> AgenteFalso:
        montados.append(portas)
        return AgenteFalso()

    monkeypatch.setattr("venergy_api.agente.build_agent", build_agent_falso)
    engine = object()

    def valid_settings() -> AgentSettings:
        return AgentSettings(_env_file=None, database_url=DATABASE_URL, google_api_key="chave")

    pedidos_de_engine = []

    def obter_engine() -> object:
        pedidos_de_engine.append(1)
        return engine

    asyncio.run(montar_agente(valid_settings, obter_engine))

    [portas] = montados
    assert isinstance(portas["history"], HistoricoAuditoria)
    assert portas["usage"] is portas["history"]
    assert pedidos_de_engine == []
    assert portas["history"]._obter_engine() is engine


def test_returns_none_and_logs_the_problems_when_the_semantic_layer_is_invalid(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def build_agent_com_camada_invalida(
        settings: AgentSettings, **portas: object
    ) -> AgenteFalso:
        raise SemanticLayerError(["view 'sem_uc': coluna 'bairro' não existe em gold_dim_uc"])

    monkeypatch.setattr("venergy_api.agente.build_agent", build_agent_com_camada_invalida)

    def valid_settings() -> AgentSettings:
        return AgentSettings(_env_file=None, database_url=DATABASE_URL, google_api_key="chave")

    with caplog.at_level(logging.WARNING):
        agente = asyncio.run(montar_agente(valid_settings, lambda: object()))

    assert agente is None
    assert "coluna 'bairro' não existe em gold_dim_uc" in caplog.text
    assert "chave" not in caplog.text.replace("chave primária", "")


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


def valid_settings() -> AgentSettings:
    return AgentSettings(_env_file=None, database_url=DATABASE_URL, google_api_key="chave")


def test_insight_writer_is_none_without_a_key(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        redator = asyncio.run(montar_redator_insights(settings_without_key))

    assert redator is None
    assert "VENERGY_AGENT_GOOGLE_API_KEY" in caplog.text
    assert "insights" in caplog.text.lower()


def test_builds_the_insight_writer_with_a_valid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    montados = []

    def build_insight_writer_falso(settings: AgentSettings) -> AgenteFalso:
        montados.append(settings)
        return AgenteFalso()

    monkeypatch.setattr("venergy_api.agente.build_insight_writer", build_insight_writer_falso)

    redator = asyncio.run(montar_redator_insights(valid_settings))

    assert isinstance(redator, AgenteFalso)
    assert len(montados) == 1


def test_insight_writer_is_none_when_the_prompt_version_does_not_exist(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def settings_with_unknown_prompt() -> AgentSettings:
        return AgentSettings(
            _env_file=None,
            database_url=DATABASE_URL,
            google_api_key="chave-secreta",
            insight_prompt_version="v99",
        )

    with caplog.at_level(logging.WARNING):
        redator = asyncio.run(montar_redator_insights(settings_with_unknown_prompt))

    assert redator is None
    assert "v99" in caplog.text
    assert "chave-secreta" not in caplog.text


def test_api_starts_with_the_insight_writer_stored_in_the_app_state(
    engine: Engine, client_for: Callable[[Engine], TestClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    redator = AgenteFalso()

    async def montar_redator_falso() -> AgenteFalso:
        return redator

    monkeypatch.setattr("venergy_api.main.montar_redator_insights", montar_redator_falso)

    with client_for(engine) as client:
        assert client.app.state.redator_insights is redator


def test_insight_dependency_answers_503_when_there_is_no_writer() -> None:
    app = FastAPI()

    @app.get("/probe")
    def probe(redator: RedatorInsightsDep) -> dict[str, str]:
        return {}

    response = TestClient(app).get("/probe")

    assert response.status_code == 503
    assert "VENERGY_AGENT_GOOGLE_API_KEY" in response.json()["detail"]


@pytest.fixture
def agent_logger() -> logging.Logger:
    logger = logging.getLogger("venergy_agent")
    handlers, level = list(logger.handlers), logger.level
    logger.handlers.clear()
    yield logger
    logger.handlers[:] = handlers
    logger.setLevel(level)


def test_agent_logs_reach_a_handler_at_info_level(agent_logger: logging.Logger) -> None:
    configurar_logs_do_agente()

    assert agent_logger.level == logging.INFO
    assert len(agent_logger.handlers) == 1


def test_configuring_the_agent_logs_twice_does_not_duplicate_lines(
    agent_logger: logging.Logger,
) -> None:
    configurar_logs_do_agente()
    configurar_logs_do_agente()

    assert len(agent_logger.handlers) == 1
