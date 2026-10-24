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
        classe text NOT NULL, classe_cadastro text NOT NULL, cod_alimentador text NOT NULL,
        possui_gd boolean NOT NULL, consumo_medio_kwh_12m numeric(16,3),
        titular_mascarado text, documento_mascarado text, potencia_kwp double precision)""",
    """CREATE TABLE gold.gold_fato_faturamento_mensal (
        cod_uc text NOT NULL, competencia text NOT NULL, kwh_faturado numeric(16,3) NOT NULL,
        receita_faturada numeric(14,2) NOT NULL, receita_energia numeric(14,2) NOT NULL,
        tributos numeric(14,2) NOT NULL, receita_arrecadada numeric(14,2),
        tarifa_media double precision, bandeira text, PRIMARY KEY (cod_uc, competencia))""",
    """CREATE TABLE gold.gold_continuidade_alimentador_mensal (
        cod_alimentador text NOT NULL, competencia text NOT NULL, dec double precision NOT NULL,
        fec double precision NOT NULL, n_uc integer NOT NULL, n_interrupcoes integer NOT NULL,
        horas_interrompidas double precision NOT NULL,
        PRIMARY KEY (cod_alimentador, competencia))""",
    """CREATE TABLE gold.gold_kpis_mensais (
        competencia text PRIMARY KEY, kwh_faturado numeric(16,3) NOT NULL,
        receita_faturada numeric(14,2) NOT NULL, receita_energia numeric(14,2) NOT NULL,
        dec double precision, fec double precision, n_chamados integer,
        satisfacao_media double precision)""",
    """CREATE TABLE gold.gold_kpis_segmento_mensal (
        competencia text NOT NULL, municipio text NOT NULL, bairro text NOT NULL,
        classe_cadastro text NOT NULL, classe text NOT NULL, possui_gd boolean NOT NULL,
        n_uc integer NOT NULL, kwh_faturado numeric(16,3) NOT NULL,
        receita_faturada numeric(14,2) NOT NULL, receita_energia numeric(14,2) NOT NULL,
        tributos numeric(14,2) NOT NULL, receita_arrecadada numeric(14,2),
        horas_interrompidas double precision NOT NULL, n_interrupcoes integer NOT NULL,
        n_chamados integer NOT NULL, soma_notas double precision, n_notas integer NOT NULL,
        PRIMARY KEY (competencia, municipio, bairro, classe_cadastro, possui_gd))""",
    """CREATE TABLE gold.gold_receita_decomposicao (
        periodo_base text NOT NULL, periodo_atual text NOT NULL, municipio text NOT NULL,
        bairro text NOT NULL, classe text NOT NULL, possui_gd boolean NOT NULL,
        receita_base numeric(14,2) NOT NULL, receita_atual numeric(14,2) NOT NULL,
        efeito_preco numeric(14,2) NOT NULL, efeito_tarifa numeric(14,2) NOT NULL,
        efeito_bandeira numeric(14,2) NOT NULL, efeito_volume numeric(14,2) NOT NULL,
        efeito_mix numeric(14,2) NOT NULL,
        PRIMARY KEY (periodo_base, periodo_atual, municipio, bairro, classe, possui_gd))""",
)
GOLD_ROWS = (
    "INSERT INTO gold.gold_dim_uc VALUES "
    "('0001','Olinda','Bairro 1','B1','Residencial','AL-07',false,250.5,'A.S.','***-01',NULL),"
    "('0002','Recife','Bairro 2','A4','Industrial','AL-03',true,18000,'B.T.','***-02',75.0),"
    "('0003','Olinda','Bairro 1','B1','Residencial','AL-07',false,300,'C.R.','***-03',NULL)",
    "INSERT INTO gold.gold_fato_faturamento_mensal VALUES "
    "('0001','2024-01',230,180.40,160.00,20.40,180.40,0.70,'verde'),"
    "('0001','2025-03',240,190.10,170.00,20.10,190.10,0.71,'verde'),"
    "('0002','2025-03',9000,7100.00,6300.00,800.00,7100.00,0.70,'amarela'),"
    "('0003','2025-06',260,200.00,180.00,20.00,195.00,0.69,'verde')",
    "INSERT INTO gold.gold_continuidade_alimentador_mensal VALUES "
    "('AL-07','2024-03',1.2,0.4,1500,3,2.5),"
    "('AL-07','2025-03',0.8,0.3,1500,2,1.5),"
    "('AL-03','2025-01',0.0,0.0,800,0,0.0)",
    "INSERT INTO gold.gold_kpis_mensais VALUES ('2025-03',9240,7290.10,6470.00,0.8,0.3,12,4.0)",
    "INSERT INTO gold.gold_kpis_segmento_mensal VALUES "
    "('2025-01','Olinda','Bairro 1','Residencial','B1',false,100,500,400.00,350.00,50.00,"
    "400.00,30,10,4,15,4),"
    "('2025-02','Olinda','Bairro 1','Residencial','B1',false,100,500,400.00,350.00,50.00,"
    "400.00,10,5,2,8,2),"
    "('2025-02','Olinda','Bairro 1','Residencial','B1',true,100,0,0.00,0.00,0.00,"
    "NULL,20,5,0,NULL,0)",
    "INSERT INTO gold.gold_receita_decomposicao VALUES "
    "('2024-01/2024-12','2025-01/2025-12','Olinda','Bairro 1','B1',false,"
    "1000.00,1100.00,80.00,60.00,20.00,30.00,-10.00),"
    "('2024-01/2024-12','2025-01/2025-12','Olinda','Bairro 1','B1',true,"
    "500.00,420.00,40.00,30.00,10.00,-115.00,-5.00)",
)
GOLD_TABLE_NAMES = (
    "gold_dim_uc",
    "gold_fato_faturamento_mensal",
    "gold_continuidade_alimentador_mensal",
    "gold_kpis_mensais",
    "gold_kpis_segmento_mensal",
    "gold_receita_decomposicao",
)
VIEW_NAMES = (
    "sem_uc",
    "sem_faturamento_mensal",
    "sem_continuidade_alimentador_mensal",
    "sem_kpis_mensais",
    "sem_kpis_segmento_mensal",
    "sem_receita_decomposicao",
)


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
