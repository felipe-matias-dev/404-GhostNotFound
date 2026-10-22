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


GOLD_TABLES = (
    """CREATE TABLE gold.gold_dim_uc (
        cod_uc text PRIMARY KEY, municipio text NOT NULL, bairro text NOT NULL,
        classe text NOT NULL, cod_alimentador text NOT NULL, possui_gd boolean NOT NULL,
        consumo_medio_kwh_12m numeric(16,3) NOT NULL, cod_cliente text, subgrupo text,
        potencia_kw double precision)""",
    """CREATE TABLE gold.gold_fato_faturamento_mensal (
        cod_uc text NOT NULL, competencia text NOT NULL, kwh_faturado numeric(16,3) NOT NULL,
        receita_faturada numeric(14,2) NOT NULL, receita_arrecadada numeric(14,2),
        tarifa_media double precision, bandeira text, PRIMARY KEY (cod_uc, competencia))""",
    """CREATE TABLE gold.gold_continuidade_alimentador_mensal (
        cod_alimentador text NOT NULL, competencia text NOT NULL, dec double precision NOT NULL,
        fec double precision NOT NULL, n_uc integer NOT NULL, n_interrupcoes integer NOT NULL,
        horas_interrompidas double precision NOT NULL,
        PRIMARY KEY (cod_alimentador, competencia))""",
)
GOLD_ROWS = (
    "INSERT INTO gold.gold_dim_uc VALUES "
    "('0001','Olinda','Bairro 1','B1','AL-07',false,250.5,'C-1',NULL,NULL),"
    "('0002','Recife','Bairro 2','A4','AL-03',true,18000,'C-2',NULL,NULL),"
    "('0003','Olinda','Bairro 1','B1','AL-07',false,300,'C-3',NULL,NULL)",
    "INSERT INTO gold.gold_fato_faturamento_mensal VALUES "
    "('0001','2024-01',230,180.40,180.40,0.78,'verde'),"
    "('0001','2025-03',240,190.10,190.10,0.79,'verde'),"
    "('0002','2025-03',9000,7100.00,7100.00,0.79,'amarela'),"
    "('0003','2025-06',260,200.00,195.00,0.77,'verde')",
    "INSERT INTO gold.gold_continuidade_alimentador_mensal VALUES "
    "('AL-07','2024-03',1.2,0.4,1500,3,2.5),"
    "('AL-07','2025-03',0.8,0.3,1500,2,1.5),"
    "('AL-03','2025-01',0.0,0.0,800,0,0.0)",
)
GOLD_TABLE_NAMES = (
    "gold_dim_uc",
    "gold_fato_faturamento_mensal",
    "gold_continuidade_alimentador_mensal",
)
VIEW_NAMES = ("sem_uc", "sem_faturamento_mensal", "sem_continuidade_alimentador_mensal")


@pytest.fixture
def gold_views(owner: psycopg.Connection) -> Iterator[None]:
    from venergy_agent.config import AGENT_ROOT

    def drop() -> None:
        for view in VIEW_NAMES:
            owner.execute(f"DROP VIEW IF EXISTS gold.{view}")
        for table in GOLD_TABLE_NAMES:
            owner.execute(f"DROP TABLE IF EXISTS gold.{table} CASCADE")

    drop()
    for statement in (*GOLD_TABLES, *GOLD_ROWS):
        owner.execute(statement)
    owner.execute((AGENT_ROOT / "semantic" / "views.sql").read_text(encoding="utf-8"))
    yield
    drop()
