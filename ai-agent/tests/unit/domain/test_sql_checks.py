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


def test_decomposition_effects_without_a_sum_go_back_with_the_rule():
    sql = (
        "SELECT efeito_preco, efeito_volume FROM sem_receita_decomposicao "
        "WHERE periodo_base = '2025-02/2025-02' AND periodo_atual = '2026-02/2026-02'"
    )

    assert "some" in calculation_problem(sql)


def test_summed_decomposition_effects_pass():
    sql = (
        "SELECT sum(d.efeito_preco) AS efeito_preco, sum(d.efeito_volume) AS efeito_volume "
        "FROM sem_receita_decomposicao d WHERE d.periodo_base = '2025-02/2025-02'"
    )

    assert calculation_problem(sql) is None


def test_the_accumulated_index_of_each_feeder_is_not_a_sum_across_feeders():
    sql = (
        "SELECT cod_alimentador, sum(dec) AS dec FROM sem_continuidade_alimentador_mensal "
        "WHERE competencia BETWEEN '2025-01' AND '2025-12' GROUP BY cod_alimentador "
        "ORDER BY sum(dec) DESC LIMIT 1"
    )

    assert calculation_problem(sql) is None


def test_segment_components_read_without_a_sum_go_back_with_the_rule():
    sql = (
        "SELECT n_faturas_pagas_com_atraso FROM sem_kpis_segmento_mensal "
        "WHERE competencia = '2025-03'"
    )

    assert "some" in calculation_problem(sql)


def test_segment_components_summed_or_grouped_pass():
    summed = (
        "SELECT sum(n_faturas) AS faturas FROM sem_kpis_segmento_mensal "
        "WHERE competencia = '2025-03'"
    )
    grouped = (
        "SELECT municipio, sum(receita_faturada) AS receita FROM sem_kpis_segmento_mensal "
        "GROUP BY municipio"
    )

    assert calculation_problem(summed) is None
    assert calculation_problem(grouped) is None
