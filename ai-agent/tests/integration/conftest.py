import os
from collections.abc import Iterator

import psycopg
import pytest

AGENT_DATABASE_URL = os.environ.get(
    "VENERGY_AGENT_TEST_DATABASE_URL",
    "postgresql://venergy_agent:troque-esta-senha-do-agente@127.0.0.1:5433/venergy_test",
)
OWNER_DATABASE_URL = os.environ.get(
    "VENERGY_AGENT_TEST_OWNER_DATABASE_URL",
    "postgresql://venergy:troque-esta-senha@127.0.0.1:5433/venergy_test",
)
UNAVAILABLE = "Banco de testes indisponível. Suba com: docker compose up -d --wait db"


@pytest.fixture
def agent_database_url() -> str:
    return AGENT_DATABASE_URL


@pytest.fixture
def owner() -> Iterator[psycopg.Connection]:
    try:
        connection = psycopg.connect(OWNER_DATABASE_URL, autocommit=True)
    except psycopg.OperationalError:
        pytest.fail(UNAVAILABLE, pytrace=False)
    with connection:
        yield connection


@pytest.fixture
def probe_view(owner: psycopg.Connection) -> Iterator[str]:
    owner.execute("DROP TABLE IF EXISTS gold.sem_executor_probe")
    owner.execute("CREATE TABLE gold.sem_executor_probe (cod_uc text, kwh numeric)")
    owner.execute(
        "INSERT INTO gold.sem_executor_probe VALUES ('0001', 100), ('0002', 200), ('0003', 300)"
    )
    yield "sem_executor_probe"
    owner.execute("DROP TABLE gold.sem_executor_probe")
