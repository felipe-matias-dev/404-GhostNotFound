import pytest

from venergy_agent.domain.numbers import unsupported_numbers


@pytest.mark.parametrize(
    ("text", "source"),
    [
        ("A receita foi de 152,4 mil", "152.4"),
        ("A receita foi de R$ 1.234,56", "1234.56"),
        ("A receita foi de R$ 1.234,56", "1.234,56"),
        ("Foram 1.234 UCs", "1234"),
        ("A queda foi de 10,5%", "10.5"),
        ("Em março de 2025 houve 3 interrupções", "2025-03"),
        ("Foram 7 linhas", "7"),
        ("Valor de 0,50", "0.50"),
    ],
)
def test_numbers_present_in_the_source_are_supported(text, source):
    assert unsupported_numbers(text, [source]) == ()


def test_a_number_that_no_source_contains_is_reported():
    assert unsupported_numbers("A receita foi de 999", ["152.4", "7"]) == ("999",)


def test_only_the_invented_number_is_reported():
    text = "Foram 7 UCs e a receita foi de 999."

    assert unsupported_numbers(text, ["7", "R$ 150"]) == ("999",)


def test_number_from_the_question_is_a_valid_source():
    question = "Quantas UCs consomem mais de 300 kWh?"
    text = "Há 12 UCs acima de 300 kWh."

    assert unsupported_numbers(text, [question, "12"]) == ()


def test_text_without_numbers_is_always_supported():
    assert unsupported_numbers("Nenhum registro atende à consulta.", []) == ()


def test_thousands_and_decimal_readings_are_both_accepted():
    # "1.234" pode ser mil duzentos e trinta e quatro ou um vírgula dois: as duas leituras valem.
    assert unsupported_numbers("valor 1.234", ["1234"]) == ()
    assert unsupported_numbers("valor 1,234", ["1.234"]) == ()
