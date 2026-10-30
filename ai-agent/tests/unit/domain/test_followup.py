import pytest

from venergy_agent.domain.followup import depends_on_previous_turn


@pytest.mark.parametrize(
    "text",
    [
        "Agora faça o mesmo para Olinda.",
        "faz o mesmo em Recife",
        "Repita a mesma consulta para 2024",
        "o mesmo para a classe B3",
        "E em Olinda?",
        "e no mês anterior?",
        "E o FEC?",
        "E da B3?",
    ],
)
def test_questions_that_only_make_sense_after_another_turn(text):
    assert depends_on_previous_turn(text)


@pytest.mark.parametrize(
    "text",
    [
        "Quantas UCs existem em Olinda?",
        "E qual foi a receita faturada em março de 2025?",
        "Quais UCs tiveram o mesmo consumo em 2024 e 2025?",
        "Energia e receita?",
        "Qual a mesma?",
    ],
)
def test_questions_that_stand_on_their_own(text):
    assert not depends_on_previous_turn(text)
