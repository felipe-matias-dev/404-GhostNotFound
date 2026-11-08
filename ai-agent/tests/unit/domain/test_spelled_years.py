import pytest

from venergy_agent.domain.text import with_spelled_years_as_digits


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("em dois mil e dezenove", "em 2019"),
        ("de dois mil e vinte e quatro pra dois mil e vinte e cinco", "de 2024 pra 2025"),
        ("Dois mil e vinte", "2020"),
    ],
)
def test_spelled_years_become_digits(text, expected):
    assert with_spelled_years_as_digits(text) == expected


def test_text_without_a_spelled_year_is_unchanged():
    assert with_spelled_years_as_digits("vinte e cinco UCs em 2024") == "vinte e cinco UCs em 2024"


def test_a_quantity_of_two_thousand_is_not_a_year():
    assert with_spelled_years_as_digits("mais de dois mil kWh") == "mais de dois mil kWh"
