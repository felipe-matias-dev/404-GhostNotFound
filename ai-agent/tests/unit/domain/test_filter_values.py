from venergy_agent.domain.filter_values import filter_value_problem

KNOWN = {
    "municipio": ("Olinda", "Recife", "Jaboatão dos Guararapes"),
    "bairro": ("Boa Viagem", "Iputinga", "Casa Caiada"),
    "classe": ("A4", "B1", "B2", "B3"),
}


def test_known_values_pass_whatever_the_case_or_accents():
    sql = (
        "SELECT 1 FROM sem_uc u WHERE u.municipio ILIKE 'recife' AND bairro = 'Boa Viagem' "
        "AND classe IN ('B1', 'B3') AND municipio ILIKE 'Jaboatao%'"
    )

    assert filter_value_problem(sql, KNOWN) is None


def test_a_value_of_another_column_says_where_it_is():
    sql = "SELECT 1 FROM sem_uc WHERE municipio = 'Boa Viagem' AND bairro = 'Boa Viagem'"

    problem = filter_value_problem(sql, KNOWN)

    assert problem is not None
    assert "'Boa Viagem'" in problem
    assert "municipio" in problem
    assert "bairro" in problem


def test_a_value_that_exists_nowhere_lists_the_column_values_and_the_whole_area_option():
    sql = "SELECT 1 FROM sem_kpis_segmento_mensal WHERE municipio = 'Região Metropolitana'"

    problem = filter_value_problem(sql, KNOWN)

    assert problem is not None
    assert "Olinda" in problem
    assert "não filtre" in problem


def test_a_value_inside_an_in_list_is_checked():
    sql = "SELECT 1 FROM sem_uc WHERE classe IN ('B1', 'Comercial')"

    problem = filter_value_problem(sql, KNOWN)

    assert problem is not None
    assert "'Comercial'" in problem


def test_columns_without_known_values_are_not_checked():
    sql = "SELECT 1 FROM sem_uc WHERE cod_uc = '0001' AND competencia = '2025-01'"

    assert filter_value_problem(sql, KNOWN) is None
