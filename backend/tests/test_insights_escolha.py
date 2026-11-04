import re

from venergy_api.insights import com_candidatas, leitura_escolhida, motivo_da_recusa, texto_aceito

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


def test_two_readings_repeating_a_number_can_be_merged_by_the_ai() -> None:
    metricas = com_candidatas(
        [
            ("conta", "A conta subiu R$ 7,26, e o consumo do mês cresceu 11,7%."),
            ("tendencia", "O consumo cresceu 11,7% no mês e cresceu 9,6% nos 12 meses."),
        ],
        {},
    )

    assert texto_aceito(
        "A conta subiu R$ 7,26 e o consumo do mês cresceu 11,7%. "
        "Nos 12 meses, o consumo também cresceu 9,6%.",
        metricas,
        ("conta", "tendencia"),
        NADA,
    )


def test_a_variation_with_its_direction_flipped_is_refused_in_any_order() -> None:
    metricas = com_candidatas([("receita", "A receita cresceu 8,0% e a energia recuou 4,0%.")], {})

    assert not texto_aceito(
        "A energia cresceu 4,0%, e a receita recuou 8,0%.", metricas, ("receita",), NADA
    )
    assert texto_aceito(
        "A energia recuou 4,0%, e a receita cresceu 8,0%.", metricas, ("receita",), NADA
    )


def test_a_gain_counts_as_a_rise() -> None:
    metricas = com_candidatas([("classe", "Na classe A4, a receita cresceu 14,3%.")], {})

    assert texto_aceito("O ganho de receita da classe A4 foi de 14,3%.", metricas, (), NADA)


def test_the_reason_tells_the_ai_which_numbers_to_use() -> None:
    motivo = motivo_da_recusa("A receita cresceu 8,5%.", METRICAS, ("receita",), NADA)

    assert motivo == "Use estes números, escritos exatamente assim, e nenhum outro: 8,0."


def test_the_reason_names_the_forbidden_term_and_the_size_limit() -> None:
    proibidos = re.compile(r"\bvolume\b")

    assert motivo_da_recusa("O volume cresceu 8,0%.", METRICAS, (), proibidos) == (
        'Não use "volume".'
    )
    assert "no máximo 63 caracteres" in motivo_da_recusa(
        "A receita cresceu 8,0%" + ", e isso diz muito sobre o ano." * 3, METRICAS, (), NADA
    )


def test_the_reason_points_a_flipped_direction() -> None:
    assert motivo_da_recusa("A receita caiu 8,0%.", METRICAS, ("receita",), NADA) == (
        "Mantenha o sentido de cada número: o que sobe nas leituras sobe no texto."
    )
