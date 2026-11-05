import pytest

from venergy_agent.domain.followup import answers_a_clarification, complete_question


@pytest.mark.parametrize("answer", ["entre 2024 e 2025", "percentual", "em junho de 2025", "2025"])
def test_short_replies_answer_a_clarification(answer):
    assert answers_a_clarification(answer)


@pytest.mark.parametrize(
    "answer",
    [
        "Quantas UCs existem na base?",
        "qual é o percentual?",
        "Como foi a receita?",
        "por que caiu?",
    ],
)
def test_a_new_question_does_not_answer_a_clarification(answer):
    assert not answers_a_clarification(answer)


def test_blank_reply_does_not_answer_a_clarification():
    assert not answers_a_clarification("   ")


def test_the_original_question_is_completed_with_the_reply():
    assert complete_question("queda acima de 30%?", "entre 2024 e 2025") == (
        "queda acima de 30% Esclarecimento: entre 2024 e 2025"
    )
