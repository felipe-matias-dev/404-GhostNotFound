import re

from venergy_api.insights import com_candidatas, leitura_escolhida, texto_aceito

NADA = re.compile(r"(?!)")
METRICAS = com_candidatas(
    [
        ("receita", "A receita cresceu 8,0%."),
        ("energia", "A energia faturada recuou 4,0%."),
        ("chamados", "Os chamados cresceram 12,3%."),
    ],
    {"variacao_receita_pct": 8.0},
)


def test_the_first_candidate_is_the_rule_fallback() -> None:
    assert METRICAS["leitura_principal"] == "receita"
    assert METRICAS["leitura_texto"] == "A receita cresceu 8,0%."


def test_the_chosen_readings_are_read_in_the_order_the_ai_wrote_them() -> None:
    assert leitura_escolhida(METRICAS, ("energia", "receita")) == (
        "A energia faturada recuou 4,0%. A receita cresceu 8,0%."
    )


def test_without_a_choice_the_text_is_compared_with_the_fallback() -> None:
    assert leitura_escolhida(METRICAS, ()) == "A receita cresceu 8,0%."


def test_an_unknown_repeated_or_too_long_choice_is_refused() -> None:
    assert leitura_escolhida(METRICAS, ("inventada",)) is None
    assert leitura_escolhida(METRICAS, ("receita", "receita")) is None
    assert leitura_escolhida(METRICAS, ("receita", "energia", "chamados")) is None


def test_the_ai_may_pick_a_reading_other_than_the_rule_one_in_its_own_words() -> None:
    assert texto_aceito("Os chamados subiram 12,3% no período.", METRICAS, ("chamados",), NADA)


def test_a_text_with_numbers_of_a_reading_it_did_not_choose_is_refused() -> None:
    assert not texto_aceito(
        "Os chamados subiram 12,3%, e a receita cresceu 8,0%.", METRICAS, ("chamados",), NADA
    )
