import pytest

from venergy_agent.domain.vocabulary import close_terms, unmapped_report, value_hints

VOCABULARY = ["percentual de tributos", "tributos", "inadimplência", "receita faturada", "consumo"]


def test_a_misspelled_term_gets_the_close_word_from_the_vocabulary():
    assert close_terms("Qual o percentil de tributos?", VOCABULARY) == {"percentil": ["percentual"]}


def test_a_missing_letter_still_matches_the_vocabulary_word():
    assert close_terms("inadiplencia no bairro", VOCABULARY) == {"inadiplencia": ["inadimplência"]}


def test_known_words_and_short_words_are_never_suggested():
    assert close_terms("para o consumo mês", VOCABULARY) == {}


def test_accents_do_not_count_as_a_difference():
    assert close_terms("inadimplencia", VOCABULARY) == {}


def test_a_question_without_close_words_has_no_suggestions():
    assert close_terms("Quantas UCs existem na base?", VOCABULARY) == {}


def test_unmapped_report_lists_only_clarify_and_unknown_turns_with_their_suggestions():
    rows = [
        {"pergunta": "percentil de tributos", "status": "clarify", "assumptions": []},
        {"pergunta": "quantas UCs?", "status": "answered", "assumptions": []},
        {
            "pergunta": "inadiplencia em Olinda",
            "status": "unknown",
            "assumptions": ["entendi 'inadiplencia' como inadimplência"],
        },
    ]

    report = unmapped_report(rows, VOCABULARY)

    assert [item["pergunta"] for item in report] == [
        "percentil de tributos",
        "inadiplencia em Olinda",
    ]
    assert report[0]["sugestoes"] == {"percentil": ["percentual"]}
    assert report[1]["suposicoes"] == ["entendi 'inadiplencia' como inadimplência"]


def test_markdown_report_says_when_there_is_nothing_to_review():
    from venergy_agent.evaluation.unmapped_terms import format_markdown

    assert format_markdown([]).startswith("Nenhum turno")


def test_markdown_report_lists_the_suggestion_for_a_person_to_decide():
    from venergy_agent.evaluation.unmapped_terms import format_markdown

    text = format_markdown(
        [
            {
                "pergunta": "percentil de tributos",
                "status": "clarify",
                "sugestoes": {"percentil": ["percentual"]},
                "suposicoes": [],
            }
        ]
    )

    assert "`percentil` lembra: percentual" in text


VALUES = {
    "municipio": ("Recife", "Jaboatão dos Guararapes", "Olinda"),
    "bairro": ("Casa Caiada", "Boa Viagem", "Iputinga"),
    "classe_cadastro": ("Residencial", "Poder Público"),
}


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Quantas UCs em jaboatao?", [("jaboatao", "Jaboatão dos Guararapes", "municipio")]),
        (
            "Quantas UCs em Jaboatao dos Guararapez?",
            [("Jaboatao dos Guararapez", "Jaboatão dos Guararapes", "municipio")],
        ),
        ("UCs solares em casa caiada", [("casa caiada", "Casa Caiada", "bairro")]),
        ("receita do poder publico", [("poder publico", "Poder Público", "classe_cadastro")]),
    ],
)
def test_a_value_written_another_way_points_to_the_value_in_the_base(question, expected):
    assert value_hints(question, VALUES) == expected


@pytest.mark.parametrize(
    "question",
    ["Quantas UCs em Olinda?", "Quantas UCs existem na base?", "receita de Boa Viagem"],
)
def test_a_value_written_as_in_the_base_or_no_value_gives_no_hint(question):
    assert value_hints(question, VALUES) == []
