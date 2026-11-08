from venergy_agent.domain.filter_values import filter_value_problem, known_values

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


def test_values_of_a_column_in_several_views_are_joined():
    known = known_values(
        [
            ("tipo_medidor", ("eletronico", "smart")),
            ("tipo_medidor", ("eletronico", "smart", "sem_medidor")),
            ("classe", ("B1",)),
        ]
    )

    assert known == {"tipo_medidor": ("eletronico", "smart", "sem_medidor"), "classe": ("B1",)}


def test_literals_inside_a_subquery_are_not_values_of_the_outer_column():
    sql = (
        "SELECT 1 FROM sem_uc WHERE classe IN "
        "(SELECT classe FROM sem_uc WHERE classe_cadastro = 'Comercial')"
    )

    assert filter_value_problem(sql, KNOWN | {"classe_cadastro": ("Comercial",)}) is None


def test_the_single_character_wildcard_of_like_matches_known_values():
    assert filter_value_problem("SELECT 1 FROM sem_uc WHERE classe LIKE 'B_'", KNOWN) is None
