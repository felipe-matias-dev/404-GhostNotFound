import asyncio
from decimal import Decimal

import yaml

from venergy_agent.domain.errors import ErrorKind, QueryExecutionError
from venergy_agent.infrastructure.postgres_executor import PostgresQueryExecutor
from venergy_agent.infrastructure.sql_validator import SqlglotValidator
from venergy_agent.infrastructure.views_sql import LAYER_PATH

ALLOWED = frozenset(
    view["name"] for view in yaml.safe_load(LAYER_PATH.read_text(encoding="utf-8"))["views"]
)


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


def test_sensitive_column_is_not_visible_to_the_agent(agent_database_url, gold_views):
    try:
        run(agent_database_url, "SELECT documento_mascarado FROM sem_uc")
    except QueryExecutionError as error:
        assert error.kind is ErrorKind.UNKNOWN_OBJECT
    else:
        raise AssertionError("documento_mascarado não deveria estar na view do agente")


def test_views_are_created_by_the_owner_and_readable_by_the_agent(agent_database_url, gold_views):
    result = run(
        agent_database_url, "SELECT count(*) AS total FROM sem_continuidade_alimentador_mensal"
    )

    assert result.rows == ({"total": 3},)


def test_segment_dec_divides_summed_hours_by_the_average_over_the_months_asked(
    agent_database_url, gold_views
):
    result = run(
        agent_database_url,
        "SELECT municipio, sum(horas_interrompidas) / "
        "NULLIF(sum(n_uc) / 3.0, 0) AS dec, "
        "sum(soma_notas) / NULLIF(sum(n_notas), 0) AS satisfacao "
        "FROM sem_kpis_segmento_mensal WHERE competencia BETWEEN '2025-01' AND '2025-03' "
        "GROUP BY municipio",
    )

    assert result.rows[0]["dec"] == 0.6
    assert round(result.rows[0]["satisfacao"], 4) == 3.8333


def test_integer_counts_in_a_ratio_do_not_truncate_to_zero(agent_database_url, gold_views):
    result = run(
        agent_database_url,
        "SELECT sum(n_interrupcoes) / NULLIF(sum(n_uc), 0) AS fec "
        "FROM sem_continuidade_alimentador_mensal WHERE competencia = '2025-03'",
    )

    assert result.rows[0]["fec"] > 0


def test_a_nested_division_of_counts_does_not_truncate_either(agent_database_url, gold_views):
    result = run(
        agent_database_url,
        "SELECT sum(n_interrupcoes) / sum(n_uc) / 3 AS fec "
        "FROM sem_continuidade_alimentador_mensal WHERE competencia = '2025-03'",
    )

    assert result.rows[0]["fec"] > 0


def test_decomposition_effects_add_up_to_the_revenue_change(agent_database_url, gold_views):
    result = run(
        agent_database_url,
        "SELECT sum(efeito_preco + efeito_volume + efeito_mix) AS efeitos, "
        "sum(receita_atual - receita_base) AS variacao FROM sem_receita_decomposicao "
        "WHERE periodo_base = '2024-01/2024-12' AND periodo_atual = '2025-01/2025-12'",
    )

    assert result.rows == ({"efeitos": Decimal("20.00"), "variacao": Decimal("20.00")},)


def test_interruptions_of_each_uc_reach_its_feeder_through_the_registry(
    agent_database_url, gold_views
):
    result = run(
        agent_database_url,
        "SELECT u.cod_alimentador, count(*) AS interrupcoes, sum(i.duracao_horas) AS horas "
        "FROM sem_interrupcoes_uc i JOIN sem_uc u ON u.cod_uc = i.cod_uc "
        "WHERE i.competencia BETWEEN '2025-01' AND '2025-12' "
        "GROUP BY u.cod_alimentador ORDER BY u.cod_alimentador",
    )

    assert result.rows == (
        {"cod_alimentador": "AL-03", "interrupcoes": 1, "horas": 0.5},
        {"cod_alimentador": "AL-07", "interrupcoes": 2, "horas": 3.5},
    )


def test_customer_service_and_meter_views_are_readable(agent_database_url, gold_views):
    service = run(
        agent_database_url,
        "SELECT canal, avg(nota_satisfacao) AS nota FROM sem_atendimentos_uc "
        "GROUP BY canal ORDER BY canal",
    )
    meters = run(agent_database_url, "SELECT count(*) AS total FROM sem_medidor_uc")

    assert service.rows == ({"canal": "APP", "nota": None}, {"canal": "TELEFONE", "nota": 4.0})
    assert meters.rows == ({"total": 2},)
