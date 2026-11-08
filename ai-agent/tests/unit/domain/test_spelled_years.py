import pytest

from venergy_agent.domain.text import with_spelled_years_as_digits


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("em dois mil e dezenove", "em 2019"),
        ("de dois mil e vinte e quatro pra dois mil e vinte e cinco", "de 2024 pra 2025"),
        ("Dois mil e vinte", "2020"),
        ("no ano dois mil", "no ano 2000"),
        ("dois mil e três reais", "2003 reais"),
    ],
)
def test_spelled_years_become_digits(text, expected):
    assert with_spelled_years_as_digits(text) == expected


def test_text_without_a_spelled_year_is_unchanged():
    assert with_spelled_years_as_digits("vinte e cinco UCs em 2024") == "vinte e cinco UCs em 2024"
