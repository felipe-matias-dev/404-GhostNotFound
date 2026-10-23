import asyncio
from decimal import Decimal

from venergy_agent.domain.errors import ErrorKind, QueryExecutionError
from venergy_agent.infrastructure.postgres_executor import PostgresQueryExecutor
from venergy_agent.infrastructure.sql_validator import SqlglotValidator

ALLOWED = frozenset({"sem_uc", "sem_faturamento_mensal", "sem_continuidade_alimentador_mensal"})


def run(agent_database_url, sql):
    validator = SqlglotValidator(dialect="postgres", max_rows=200, allowed_schema="gold")
    executor = PostgresQueryExecutor(agent_database_url, timeout_seconds=10)
    query = validator.validate(sql, ALLOWED)
    return asyncio.run(executor.execute(query))


def test_agent_reads_the_views_through_the_validator_and_executor(agent_database_url, gold_views):
    result = run(agent_database_url, "SELECT count(*) AS total FROM sem_uc")

    assert result.rows == ({"total": 3},)


def test_join_between_views_returns_the_fact_rows_of_the_uc(agent_database_url, gold_views):
    result = run(
        agent_database_url,
        "SELECT u.municipio, round(sum(f.receita_faturada), 2) AS receita "
        "FROM sem_uc u JOIN sem_faturamento_mensal f ON f.cod_uc = u.cod_uc "
        "WHERE f.competencia = '2025-03' GROUP BY u.municipio ORDER BY u.municipio",
    )

    assert result.rows == (
        {"municipio": "Olinda", "receita": Decimal("190.10")},
        {"municipio": "Recife", "receita": Decimal("7100.00")},
    )


def test_column_marked_a_confirmar_is_not_visible_to_the_agent(agent_database_url, gold_views):
    try:
        run(agent_database_url, "SELECT cod_cliente FROM sem_uc")
    except QueryExecutionError as error:
        assert error.kind is ErrorKind.UNKNOWN_OBJECT
    else:
        raise AssertionError("cod_cliente não deveria estar na view do agente")


def test_views_are_created_by_the_owner_and_readable_by_the_agent(agent_database_url, gold_views):
    result = run(
        agent_database_url, "SELECT count(*) AS total FROM sem_continuidade_alimentador_mensal"
    )

    assert result.rows == ({"total": 3},)
