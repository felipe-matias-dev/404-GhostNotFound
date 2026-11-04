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

    assert motivo == (
        "Use só estes números, escritos exatamente assim, sem deixar nenhum de fora: 8,0."
    )


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


def test_energy_to_recover_is_not_a_drop() -> None:
    metricas = com_candidatas(
        [("concentracao", "Os 3 lugares com mais energia a recuperar concentram 73,0% do kWh.")],
        {},
    )

    assert texto_aceito(
        "Três lugares concentram 73,0% do kWh a recuperar: 3 deles.", metricas, (), NADA
    )


def test_a_text_without_the_names_of_the_chosen_reading_is_refused() -> None:
    metricas = com_candidatas(
        [("concentracao", "Os 2 municípios com mais energia concentram 70,0%: Olinda e Recife.")],
        {},
        {"concentracao": ["Olinda", "Recife"]},
    )

    assert (
        motivo_da_recusa(
            "Os 2 municípios com mais energia concentram 70,0%.", metricas, ("concentracao",), NADA
        )
        == "Cite estes nomes como estão: Olinda, Recife."
    )
    assert texto_aceito(
        "Olinda e Recife, 2 municípios, concentram 70,0% da energia.",
        metricas,
        ("concentracao",),
        NADA,
    )


def test_every_reason_goes_back_at_once() -> None:
    metricas = com_candidatas(
        [("concentracao", "Os 2 municípios concentram 70,0%: Olinda e Recife.")],
        {},
        {"concentracao": ["Olinda", "Recife"]},
    )

    assert motivo_da_recusa(
        "Os municípios concentram 71,0%.", metricas, ("concentracao",), NADA
    ) == (
        "Use só estes números, escritos exatamente assim, sem deixar nenhum de fora: 2, 70,0. "
        "Cite estes nomes como estão: Olinda, Recife."
    )


def test_a_reading_without_numbers_asks_for_none() -> None:
    metricas = com_candidatas([("fator", "O que mais pesou foi o preço.")], {})

    assert motivo_da_recusa("O preço pesou 5,0%.", metricas, ("fator",), NADA) == (
        "Não use números: as leituras escolhidas não têm nenhum."
    )


def test_counts_may_be_left_out_when_the_text_names_the_places() -> None:
    metricas = com_candidatas(
        [("concentracao", "Os 3 municípios, de 13, concentram 73,0%: Olinda, Recife e Paulista.")],
        {},
        {"concentracao": ["Olinda", "Recife", "Paulista"]},
    )

    assert texto_aceito(
        "Olinda, Recife e Paulista concentram 73,0% da energia.", metricas, ("concentracao",), NADA
    )


def test_a_percentage_cannot_be_left_out_even_when_names_are_cited() -> None:
    metricas = com_candidatas(
        [("concentracao", "Os 2 municípios concentram 73,0%: Olinda e Recife.")],
        {},
        {"concentracao": ["Olinda", "Recife"]},
    )

    assert not texto_aceito(
        "Olinda e Recife concentram a maior parte.", metricas, ("concentracao",), NADA
    )


def test_counts_of_a_reading_without_names_cannot_be_left_out() -> None:
    metricas = com_candidatas([("preco", "Em 73 dos 86 bairros, a receita subiu 5,0%.")], {})

    assert not texto_aceito("Em 73 bairros, a receita subiu 5,0%.", metricas, ("preco",), NADA)


def test_a_number_outside_the_readings_is_never_accepted() -> None:
    metricas = com_candidatas([("concentracao", "Os 3 municípios concentram 73,0%.")], {})

    assert not texto_aceito("Os 4 municípios concentram 73,0%.", metricas, ("concentracao",), NADA)
