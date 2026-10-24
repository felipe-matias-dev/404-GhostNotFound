from datetime import date
from decimal import Decimal

import pytest

from venergy_agent.domain.numbers import unsupported_numbers


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
