import pytest

from venergy_agent.domain.followup import (
    answers_a_clarification,
    complete_question,
    needs_a_calendar_period,
)
from venergy_agent.domain.vocabulary import known_words

KNOWN = known_words(["receita faturada", "consumo", "percentual de tributos", "UCs"])


@pytest.mark.parametrize(
    "reply",
    ["entre 2024 e 2025", "percentual", "em junho de 2025", "2025", "últimos 12 meses"],
)
def test_short_replies_and_periods_answer_a_clarification(reply):
    assert answers_a_clarification(reply, KNOWN)


@pytest.mark.parametrize(
    "reply",
    [
        "Quantas UCs existem na base?",
        "qual é o percentual?",
        "Como foi a receita?",
        "por que caiu?",
    ],
)
def test_a_question_does_not_answer_a_clarification(reply):
    assert not answers_a_clarification(reply, KNOWN)


@pytest.mark.parametrize(
    "reply",
    [
        "Mostre a receita de junho de 2026",
        "Liste as UCs de Olinda com a classe",
        "Compare 2024 com 2025",
        "Receita faturada de junho de 2026",
        "Me diga o consumo de março",
    ],
)
def test_a_new_request_with_its_own_metric_is_not_a_clarification_reply(reply):
    assert not answers_a_clarification(reply, KNOWN)


def test_blank_reply_does_not_answer_a_clarification():
    assert not answers_a_clarification("   ", KNOWN)


def test_the_original_question_is_completed_with_the_reply():
    assert complete_question("queda acima de 30%?", "entre 2024 e 2025") == (
        "queda acima de 30% Esclarecimento: entre 2024 e 2025"
    )


@pytest.mark.parametrize(
    "text",
    [
        "Qual bairro mais perdeu volume residencial no último ano?",
        "Qual foi a receita do ano passado?",
        "quanto faturamos nos últimos 3 meses?",
        "Qual o DEC do último trimestre?",
        "E no mês passado?",
    ],
)
def test_a_calendar_period_without_a_year_needs_the_period(text):
    assert needs_a_calendar_period(text)


@pytest.mark.parametrize(
    "text",
    [
        "Qual foi a receita nos últimos 12 meses?",
        "Qual foi a receita no último ano da base?",
        "Qual foi a receita no último ano? Esclarecimento: em 2025",
        "Qual foi a receita no último ano? Esclarecimento: nos últimos 12 meses",
        "Qual foi a receita em 2025?",
        "Quantas UCs existem?",
    ],
)
def test_a_period_the_question_already_gives_does_not_need_it(text):
    assert not needs_a_calendar_period(text)
