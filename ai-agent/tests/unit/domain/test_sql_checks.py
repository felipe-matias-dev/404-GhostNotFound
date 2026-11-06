import pytest

from venergy_agent.domain.sql_checks import calculation_problem


@pytest.mark.parametrize(
    ("sql", "hint"),
    [
        (
            "SELECT AVG(satisfacao_media) AS s FROM semantic.sem_kpis_mensais "
            "WHERE competencia BETWEEN '2025-01' AND '2025-12'",
            "soma_notas",
        ),
        (
            "SELECT AVG(f.tarifa_media) AS t FROM semantic.sem_faturamento_mensal AS f",
            "receita_energia",
        ),
        (
            "SELECT SUM(c.dec) AS d FROM semantic.sem_continuidade_alimentador_mensal AS c "
            "JOIN g ON c.cod_alimentador = g.cod_alimentador",
            "horas_interrompidas",
        ),
        (
            "SELECT SUM(fec) FROM semantic.sem_continuidade_alimentador_mensal "
            "WHERE cod_alimentador IN (SELECT cod_alimentador FROM semantic.sem_uc)",
            "n_interrupcoes",
        ),
    ],
)
def test_a_calculation_the_layer_forbids_is_reported_with_the_right_formula(sql, hint):
    problem = calculation_problem(sql)

    assert problem is not None and hint in problem


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT SUM(dec) FROM semantic.sem_kpis_mensais WHERE competencia LIKE '2025-%'",
        "SELECT SUM(dec) FROM semantic.sem_continuidade_alimentador_mensal "
        "WHERE cod_alimentador = 'ALM-REC-024'",
        "SELECT satisfacao_media FROM semantic.sem_kpis_mensais WHERE competencia = '2025-03'",
        "SELECT canal, AVG(nota_satisfacao) FROM semantic.sem_atendimentos_uc GROUP BY canal",
    ],
)
def test_allowed_calculations_pass(sql):
    assert calculation_problem(sql) is None
