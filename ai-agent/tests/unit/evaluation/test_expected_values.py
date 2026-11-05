from decimal import Decimal

from venergy_agent.evaluation.expected_values import build_entry, format_pt_br


def test_numbers_are_written_in_brazilian_format_with_the_unit_rule():
    assert format_pt_br(Decimal("1234.5"), "R$") == "1.234,50"
    assert format_pt_br(Decimal("1234.56"), "kWh") == "1.235"
    assert format_pt_br(Decimal("0.0256"), "h") == "0,03"
    assert format_pt_br(Decimal("3"), None) == "3"


def test_entry_keeps_the_question_status_and_each_column_with_its_unit():
    item = {
        "id": "G106",
        "question": "Qual foi a receita de junho de 2026?",
        "expected_status": "answered",
    }
    rows = [{"receita_faturada": Decimal("45712401.17"), "n_uc": 3}]
    units = {"receita_faturada": "R$"}

    entry = build_entry(item, ("receita_faturada", "n_uc"), rows, units)

    assert entry == {
        "id": "G106",
        "pergunta": "Qual foi a receita de junho de 2026?",
        "status_esperado": "answered",
        "colunas": ["receita_faturada", "n_uc"],
        "unidades": {"receita_faturada": "R$"},
        "linhas": [{"receita_faturada": "45.712.401,17", "n_uc": "3"}],
    }


def test_entry_for_a_large_result_stops_at_the_limit_and_says_so():
    rows = [{"n": index} for index in range(300)]

    entry = build_entry(
        {"id": "G119", "question": "liste", "expected_status": "answered"}, ("n",), rows, {}
    )

    assert len(entry["linhas"]) == 200
    assert entry["linhas_totais"] == 300


def test_text_columns_are_kept_as_they_are_and_missing_values_stay_empty():
    rows = [{"municipio": "Olinda", "classe": None}]

    entry = build_entry(
        {"id": "G115", "question": "q", "expected_status": "answered"},
        ("municipio", "classe"),
        rows,
        {},
    )

    assert entry["linhas"] == [{"municipio": "Olinda", "classe": None}]
