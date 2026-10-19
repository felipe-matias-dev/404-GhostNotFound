"""O usuário do agente de IA só lê a Gold (requisito de Segurança da Informação do case).

Testa as travas criadas por infra/postgres/init/01-init.sh, conferindo o código de erro
do Postgres (SQLSTATE) para garantir que cada escrita falhou pelo motivo certo.
"""

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session

from venergy_api.database import Base, create_db_engine
from venergy_api.models import DimUc

AGENT_DATABASE_URL = os.environ.get(
    "VENERGY_API_TEST_AGENT_DATABASE_URL",
    "postgresql+psycopg://venergy_agent:troque-esta-senha-do-agente@127.0.0.1:5433/venergy_test",
)
READ_ONLY_TRANSACTION = "25006"
INSUFFICIENT_PRIVILEGE = "42501"


@pytest.fixture
def gold_with_one_uc(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add(
            DimUc(
                cod_uc="0001",
                municipio="Recife",
                bairro="Boa Viagem",
                classe="B1",
                cod_alimentador="AL-01",
                possui_gd=False,
                consumo_medio_kwh_12m=100.0,
            )
        )


@pytest.fixture
def agent_engine() -> Iterator[Engine]:
    agent_engine = create_db_engine(AGENT_DATABASE_URL)
    try:
        with agent_engine.connect():
            pass
    except OperationalError:
        pytest.fail("Usuário do agente não conecta. Recrie o banco: docker compose down -v", False)
    yield agent_engine
    agent_engine.dispose()


def sqlstate_of(error: pytest.ExceptionInfo[DBAPIError]) -> str:
    return error.value.orig.sqlstate


@pytest.mark.usefixtures("gold_with_one_uc")
def test_agent_reads_the_gold(agent_engine: Engine) -> None:
    with agent_engine.connect() as connection:
        total = connection.execute(text("SELECT count(*) FROM gold.gold_dim_uc")).scalar_one()

    assert total == 1


@pytest.mark.usefixtures("gold_with_one_uc")
@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO gold.gold_dim_uc (cod_uc) VALUES ('9999')",
        "UPDATE gold.gold_dim_uc SET bairro = 'X'",
        "DELETE FROM gold.gold_dim_uc",
        "DROP TABLE gold.gold_dim_uc",
    ],
)
def test_agent_cannot_write(agent_engine: Engine, statement: str) -> None:
    with agent_engine.connect() as connection, pytest.raises(DBAPIError) as error:
        connection.execute(text(statement))

    assert sqlstate_of(error) == READ_ONLY_TRANSACTION


@pytest.mark.usefixtures("gold_with_one_uc")
def test_permission_still_blocks_writes_if_read_only_mode_is_turned_off(
    agent_engine: Engine,
) -> None:
    # O próprio agente consegue desligar o modo somente leitura: por isso a permissão
    # (só SELECT) é a trava que realmente importa.
    autocommit = agent_engine.execution_options(isolation_level="AUTOCOMMIT")
    with autocommit.connect() as connection:
        connection.execute(text("SET default_transaction_read_only = off"))
        with pytest.raises(DBAPIError) as error:
            connection.execute(text("DELETE FROM gold.gold_dim_uc"))

    assert sqlstate_of(error) == INSUFFICIENT_PRIVILEGE


def test_agent_cannot_read_the_app_schema(engine: Engine, agent_engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE app.ordem_teste (id int)"))
    try:
        with agent_engine.connect() as connection, pytest.raises(DBAPIError) as error:
            connection.execute(text("SELECT * FROM app.ordem_teste"))
    finally:
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE app.ordem_teste"))

    assert sqlstate_of(error) == INSUFFICIENT_PRIVILEGE
