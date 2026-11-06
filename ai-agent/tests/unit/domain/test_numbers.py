from datetime import date
from decimal import Decimal

import pytest

from venergy_agent.domain.numbers import (
    display_for_unit,
    durations,
    rounded_for_display,
    unsupported_numbers,
)


@pytest.mark.parametrize(
    ("text", "values"),
    [
        ("A receita foi de 152,4 mil", [Decimal("152.4")]),
        ("A receita foi de R$ 1.234,56", [Decimal("1234.56")]),
        ("Foram 1.234 UCs", [1234]),
        ("Foram 1.234.567 kWh", [Decimal("1234567.000")]),
        ("A queda foi de 10,5%", [10.5]),
        ("Em março de 2025 houve 3 interrupções", ["2025-03", 3]),
        ("Vencida em 10/04/2025", [date(2025, 4, 10)]),
        ("Foram 7 linhas", [7]),
        ("Valor de 0,50", [Decimal("0.50")]),
        ("A tarifa foi de 0,7", [0.70]),
    ],
)
def test_numbers_written_in_pt_br_and_present_in_the_values_are_supported(text, values):
    assert unsupported_numbers(text, values) == ()


def test_a_number_that_no_value_contains_is_reported():
    assert unsupported_numbers("A receita foi de 999", [Decimal("152.4"), 7]) == ("999",)


def test_only_the_invented_number_is_reported():
    assert unsupported_numbers("Foram 7 UCs e a receita foi de 999.", [7, 150]) == ("999",)


def test_dot_is_a_thousands_separator_not_a_decimal_point():
    assert unsupported_numbers("valor 1.234", [Decimal("1.234")]) == ("1.234",)


def test_number_written_in_english_format_is_not_accepted():
    assert unsupported_numbers("valor 1,234.56", [Decimal("1234.56")]) == ("1,234.56",)


def test_booleans_are_not_numbers():
    assert unsupported_numbers("Foram 1 UC", [True]) == ("1",)


def test_text_without_numbers_is_always_supported():
    assert unsupported_numbers("Nenhum registro atende à consulta.", []) == ()


def test_negative_value_is_supported_when_the_text_cites_its_magnitude():
    assert unsupported_numbers("O efeito mix foi uma queda de 10,5 mil", [Decimal("-10.5")]) == ()


@pytest.mark.parametrize("text", ["As classes 1,2,3", "Meses 01,02,03"])
def test_token_that_is_not_a_pt_br_number_is_reported_instead_of_raising(text):
    assert unsupported_numbers(text, [1, 2, 3]) == (text.split()[-1],)


def test_numbers_inside_a_code_are_not_a_source():
    assert unsupported_numbers("Há 7 alimentadores", ["AL-07"]) == ("7",)


@pytest.mark.parametrize(
    "text", ["A classe B1 tem 3 UCs", "O alimentador AL-07 teve 3 interrupções"]
)
def test_digits_inside_a_code_in_the_text_are_not_numbers(text):
    assert unsupported_numbers(text, [3]) == ()


def test_a_negative_number_in_the_text_is_still_checked():
    assert unsupported_numbers("O efeito mix foi de -999", [Decimal("-10.5")]) == ("999",)


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("nota 3,89", Decimal("3.89368")),
        ("nota 3,90", 3.895467),
        ("R$ 98,56", Decimal("98.562205")),
        ("DEC de 2,42", 2.4199999570846558),
        ("1,9 hora", Decimal("1.9135965")),
    ],
)
def test_a_value_rounded_to_the_decimals_written_is_supported(text, value):
    assert unsupported_numbers(text, [value]) == ()


def test_a_value_rounded_the_wrong_way_is_reported():
    assert unsupported_numbers("nota 3,88", [Decimal("3.89368")]) == ("3,88",)


def test_an_integer_must_match_a_value_exactly():
    assert unsupported_numbers("3 canais", [2.6]) == ("3",)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("nos últimos 12 meses", {Decimal(12)}),
        ("as 12 primeiras competências e os primeiros 2 anos", {Decimal(12), Decimal(2)}),
        ("medidores com mais de 10 anos", set()),
        ("atraso de 30 dias", set()),
        ("acima de 300 kWh em 2025", set()),
    ],
)
def test_durations_are_the_first_or_last_months_or_years_of_a_period(text, expected):
    assert durations(text) == expected


def test_a_duration_given_elsewhere_is_supported_when_written_as_a_duration():
    assert unsupported_numbers("Nos últimos 12 meses, 3 UCs", [3], {Decimal(12)}) == ()


def test_a_duration_given_elsewhere_is_not_a_source_for_a_count():
    assert unsupported_numbers("Foram 12 UCs", [3], {Decimal(12)}) == ("12",)


def test_a_duration_given_elsewhere_does_not_support_another_number_of_years():
    assert unsupported_numbers("A idade média é de 10 anos", [3], {Decimal(12)}) == ("10",)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("1.9135965"), Decimal("1.91")),
        (Decimal("2.4200001"), Decimal("2.42")),
        (Decimal("4.5000000"), Decimal("4.5")),
        (Decimal("35482.70"), Decimal("35482.70")),
        (Decimal("0.05612345"), Decimal("0.0561")),
        (Decimal("1200"), Decimal("1200")),
        (Decimal("-4656505.19"), Decimal("-4656505.19")),
        (Decimal("100.0000001"), Decimal("100")),
    ],
)
def test_long_decimals_are_rounded_for_display(value, expected):
    assert rounded_for_display(value) == expected
    assert str(rounded_for_display(value)) == str(expected)


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("O percentual foi de 25%", Decimal("24.99999999")),
        ("Foram 100 kWh", Decimal("100.0000001")),
    ],
)
def test_an_integer_is_supported_when_it_is_the_value_rounded_for_display(text, value):
    assert unsupported_numbers(text, [value]) == ()


def test_an_integer_is_still_not_a_rounded_short_decimal():
    assert unsupported_numbers("Foram 3 UCs", [Decimal("2.6")]) == ("3",)


@pytest.mark.parametrize(
    "text",
    [
        "Comparando períodos de 12 meses, há 3 UCs.",
        "Nos 12 meses mais recentes, há 3 UCs.",
        "Nas 12 competências da base, há 3 UCs.",
        "Entre as 12 primeiras e as 12 últimas competências, há 3 UCs.",
    ],
)
def test_a_duration_from_the_question_is_supported_with_its_period_unit(text):
    assert unsupported_numbers(text, [3], {Decimal(12)}) == ()


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        (Decimal("0.0256"), "h", Decimal("0.03")),
        (Decimal("0.024"), "h", Decimal("0.02")),
        (Decimal("0.5"), "R$/kWh", Decimal("0.5")),
        (Decimal("3.456"), "%", Decimal("3.46")),
        (Decimal("0.50"), "%", Decimal("0.5")),
    ],
)
def test_hours_money_and_percent_have_at_most_two_decimals(value, unit, expected):
    assert display_for_unit(value, unit) == expected


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        (Decimal("1234.56"), "kWh", Decimal("1235")),
        (Decimal("12.4"), "contagem", Decimal("12")),
    ],
)
def test_energy_and_counts_are_whole_numbers(value, unit, expected):
    assert display_for_unit(value, unit) == expected


def test_without_a_unit_the_display_rule_is_the_old_one():
    assert display_for_unit(Decimal("0.024567"), None) == rounded_for_display(Decimal("0.024567"))


def test_money_keeps_two_decimals_so_it_matches_the_table_currency_format():
    assert str(display_for_unit(Decimal("1234.5"), "R$")) == "1234.50"
    assert str(display_for_unit(Decimal("1234.567"), "R$")) == "1234.57"


def test_consumption_per_month_is_a_whole_number_like_kwh():
    assert display_for_unit(Decimal("433.6"), "kWh/mês") == Decimal("434")


@pytest.mark.parametrize(
    ("text", "sql_numbers", "expected"),
    [
        ("queda acima de 30%", {Decimal("0.7")}, {Decimal(30)}),
        ("queda acima de 30%", {Decimal("0.3")}, {Decimal(30)}),
        ("alta de 30%", {Decimal("1.3")}, {Decimal(30)}),
        ("acima de 12,5%", {Decimal("0.875")}, {Decimal("12.5")}),
        ("acima de 30%", {Decimal("0.5")}, set()),
        ("300 kWh", {Decimal("0.7")}, set()),
    ],
)
def test_a_percentage_in_the_question_is_supported_by_its_transformed_literal(
    text, sql_numbers, expected
):
    from venergy_agent.domain.numbers import threshold_percents

    assert threshold_percents(text, sql_numbers) == expected
