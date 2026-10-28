import psycopg
import pytest

from venergy_agent.domain.errors import ErrorKind, QueryExecutionError
from venergy_agent.domain.sql import ValidatedQuery
from venergy_agent.infrastructure.postgres_executor import PostgresQueryExecutor

PROBE = frozenset({"sem_executor_probe"})


@pytest.fixture
def executor(agent_database_url):
    return PostgresQueryExecutor(database_url=agent_database_url, timeout_seconds=5)


def query(sql: str, applied_limit: int = 200, limit_imposed: bool = True) -> ValidatedQuery:
    return ValidatedQuery(
        sql=sql, views=PROBE, applied_limit=applied_limit, limit_imposed=limit_imposed
    )


@pytest.mark.usefixtures("probe_view")
async def test_returns_columns_and_rows(executor):
    result = await executor.execute(
        query("SELECT cod_uc, kwh FROM gold.sem_executor_probe ORDER BY cod_uc LIMIT 200")
    )

    assert result.columns == ("cod_uc", "kwh")
    assert result.row_count == 3
    assert result.rows[0]["cod_uc"] == "0001"
    assert result.truncated is False


@pytest.mark.usefixtures("probe_view")
async def test_marks_truncated_when_rows_reach_an_imposed_limit(executor):
    result = await executor.execute(
        query("SELECT cod_uc FROM gold.sem_executor_probe ORDER BY cod_uc LIMIT 2", 2)
    )

    assert result.row_count == 2
    assert result.truncated is True


@pytest.mark.usefixtures("probe_view")
async def test_a_limit_asked_by_the_user_is_not_truncation(executor):
    result = await executor.execute(
        query("SELECT cod_uc FROM gold.sem_executor_probe LIMIT 2", 2, limit_imposed=False)
    )

    assert result.truncated is False


@pytest.mark.usefixtures("probe_view")
async def test_database_refuses_writes_even_without_the_validator(executor):
    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        await executor.execute(query("INSERT INTO gold.sem_executor_probe VALUES ('9', 1)"))


@pytest.mark.parametrize("timeout_seconds", [0.2, 0.0001])
async def test_slow_query_times_out(agent_database_url, timeout_seconds):
    executor = PostgresQueryExecutor(
        database_url=agent_database_url, timeout_seconds=timeout_seconds
    )

    with pytest.raises(QueryExecutionError) as error:
        await executor.execute(query("SELECT pg_sleep(2)"))

    assert error.value.kind is ErrorKind.TIMEOUT


@pytest.mark.usefixtures("probe_view")
@pytest.mark.parametrize(
    ("sql", "kind"),
    [
        ("SELECT nope FROM gold.sem_executor_probe", ErrorKind.UNKNOWN_OBJECT),
        ("SELECT 1 FROM gold.sem_executor_missing", ErrorKind.UNKNOWN_OBJECT),
        ("SELECT 1 FROM gold.sem_executor_probe WHERE cod_uc = 1", ErrorKind.TYPE_MISMATCH),
        ("SELECT FROM WHERE", ErrorKind.SYNTAX),
    ],
)
async def test_classifies_errors_for_the_correction_loop(executor, sql, kind):
    with pytest.raises(QueryExecutionError) as error:
        await executor.execute(query(sql))

    assert error.value.kind is kind


async def test_permission_errors_are_not_classified(executor, owner):
    owner.execute("CREATE TABLE IF NOT EXISTS app.ordem_executor_probe (id int)")
    try:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            await executor.execute(query("SELECT id FROM app.ordem_executor_probe"))
    finally:
        owner.execute("DROP TABLE app.ordem_executor_probe")


@pytest.mark.usefixtures("probe_view")
async def test_duplicate_column_names_are_a_correctable_error_not_silent_data_loss(executor):
    query = ValidatedQuery(
        sql="SELECT a.kwh, b.kwh FROM gold.sem_executor_probe a JOIN gold.sem_executor_probe b "
        "ON a.cod_uc = b.cod_uc",
        views=frozenset({"sem_executor_probe"}),
        applied_limit=200,
        limit_imposed=False,
    )

    with pytest.raises(QueryExecutionError, match="mesmo nome"):
        await executor.execute(query)


@pytest.mark.usefixtures("probe_view")
async def test_data_error_message_keeps_the_kind_but_drops_the_database_value(executor):
    with pytest.raises(QueryExecutionError) as raised:
        await executor.execute(
            query("SELECT CAST(cod_uc || 'X' AS integer) AS n FROM gold.sem_executor_probe")
        )

    assert raised.value.kind is ErrorKind.TYPE_MISMATCH
    assert "0001X" not in raised.value.message
    assert "integer" in raised.value.message


@pytest.mark.usefixtures("probe_view")
async def test_unknown_column_message_keeps_the_name_the_model_wrote(executor):
    with pytest.raises(QueryExecutionError) as raised:
        await executor.execute(query("SELECT receita_inventada FROM gold.sem_executor_probe"))

    assert "receita_inventada" in raised.value.message


@pytest.mark.usefixtures("probe_view")
async def test_a_quote_inside_the_value_does_not_leak_part_of_it(executor):
    with pytest.raises(QueryExecutionError) as raised:
        await executor.execute(
            query("SELECT CAST(cod_uc || '\"Neil' AS integer) AS n FROM gold.sem_executor_probe")
        )

    assert "Neil" not in raised.value.message
    assert raised.value.message.endswith(": <valor>")
