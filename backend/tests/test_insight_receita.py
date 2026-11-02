from decimal import Decimal

from venergy_agent.domain.numbers import unsupported_numbers

from venergy_api.insight_receita import filtro_acima, metricas_da_receita, texto_aceito
from venergy_api.schemas import DecomposicaoFiltroSchema, DecomposicaoLinhaSchema

BASE = "2024-01/2024-12"
ATUAL = "2025-01/2025-12"


def filtro(**changes: str) -> DecomposicaoFiltroSchema:
    return DecomposicaoFiltroSchema(periodo_base=BASE, periodo_atual=ATUAL, **changes)


def linha(
    segmento: str,
    base: str,
    atual: str,
    tarifa: str = "0",
    bandeira: str = "0",
    volume: str = "0",
    mix: str = "0",
    nivel: str = "municipio",
) -> DecomposicaoLinhaSchema:
    return DecomposicaoLinhaSchema(
        nivel=nivel,
        segmento=segmento,
        periodo_base=BASE,
        periodo_atual=ATUAL,
        receita_base=Decimal(base),
        receita_atual=Decimal(atual),
        variacao_receita=Decimal(atual) - Decimal(base),
        efeito_preco=Decimal(tarifa) + Decimal(bandeira),
        efeito_tarifa=Decimal(tarifa),
        efeito_bandeira=Decimal(bandeira),
        efeito_volume=Decimal(volume),
        efeito_mix=Decimal(mix),
    )


def test_returns_nothing_when_the_cut_has_no_rows() -> None:
    assert metricas_da_receita(filtro(), []) is None


def test_totals_and_effects_are_the_sums_of_the_rows() -> None:
    linhas = [
        linha("Recife", "1000.00", "960.00", tarifa="30", bandeira="20", volume="-80", mix="-10"),
        linha("Olinda", "500.00", "540.00", tarifa="15", bandeira="5", volume="22.5", mix="-2.5"),
    ]

    metricas = metricas_da_receita(filtro(), linhas)

    assert metricas is not None
    assert metricas["receita_base"] == 1500.0
    assert metricas["efeito_tarifa"] == 45.0
    assert metricas["efeito_bandeira"] == 25.0
    assert metricas["efeito_preco"] == 70.0
    assert metricas["efeito_volume"] == -57.5
    assert metricas["efeito_mix"] == -12.5


def test_current_revenue_is_the_base_plus_the_effects_like_the_screen_does() -> None:
    # Cada linha fecha só dentro da tolerância do contrato (DEC-035): a soma de receita_atual
    # pode sobrar centavos, e a tela mostra base + efeitos. O insight diz o mesmo que a tela.
    linhas = [
        linha("Recife", "100.00", "101.01", tarifa="1", volume="0"),
        linha("Olinda", "100.00", "99.00", tarifa="0", volume="-1"),
    ]

    metricas = metricas_da_receita(filtro(), linhas)

    assert metricas is not None
    assert metricas["receita_atual"] == 200.0
    assert metricas["variacao_receita"] == 0.0


def test_variation_percentage_has_one_decimal_place() -> None:
    linhas = [linha("Recife", "300.00", "288.00", volume="-12")]

    metricas = metricas_da_receita(filtro(), linhas)

    assert metricas is not None
    assert metricas["variacao_receita"] == -12.0
    assert metricas["variacao_receita_pct"] == -4.0


def test_percentage_is_left_out_when_there_is_no_base_revenue() -> None:
    metricas = metricas_da_receita(filtro(), [linha("Recife", "0", "0")])

    assert metricas is not None
    assert "variacao_receita_pct" not in metricas


def test_biggest_drops_list_only_negative_segments_worst_first_and_at_most_three() -> None:
    linhas = [
        linha("A", "100", "60"),
        linha("B", "100", "90"),
        linha("C", "100", "80"),
        linha("D", "100", "95"),
        linha("E", "100", "130"),
    ]

    metricas = metricas_da_receita(filtro(), linhas)

    assert metricas is not None
    assert [queda["segmento"] for queda in metricas["maiores_quedas"]] == ["A", "C", "B"]
    assert metricas["maiores_quedas"][0] == {
        "segmento": "A",
        "variacao_receita": -40.0,
        "variacao_pct": -40.0,
    }


def test_drop_of_a_segment_without_base_revenue_has_no_percentage() -> None:
    linhas = [linha("Novo", "0", "-5"), linha("Velho", "100", "50")]

    metricas = metricas_da_receita(filtro(), linhas)

    assert metricas is not None
    novo = next(queda for queda in metricas["maiores_quedas"] if queda["segmento"] == "Novo")
    assert novo == {"segmento": "Novo", "variacao_receita": -5.0}


def test_no_drops_means_an_empty_list() -> None:
    metricas = metricas_da_receita(filtro(), [linha("A", "100", "120", volume="20")])

    assert metricas is not None
    assert metricas["maiores_quedas"] == []


def test_periods_and_level_are_values_so_the_text_can_cite_them() -> None:
    metricas = metricas_da_receita(filtro(), [linha("Recife", "100", "90", nivel="bairro")])

    assert metricas is not None
    assert metricas["periodo_base"] == BASE
    assert metricas["periodo_atual"] == ATUAL
    assert metricas["nivel_das_linhas"] == "bairro"
    assert metricas["n_segmentos"] == 1


def test_cut_is_described_in_words() -> None:
    uma_linha = [linha("Recife", "100", "90")]

    assert metricas_da_receita(filtro(), uma_linha)["recorte"] == "todos os municípios"
    assert metricas_da_receita(filtro(municipio="Recife"), uma_linha)["recorte"] == "Recife"
    assert (
        metricas_da_receita(
            filtro(municipio="Recife", bairro="Boa Viagem", classe="B1"), uma_linha
        )["recorte"]
        == "Recife · Boa Viagem · classe B1"
    )
    assert metricas_da_receita(filtro(classe="A4"), uma_linha)["recorte"] == (
        "todos os municípios · classe A4"
    )


def test_a_text_written_in_brazilian_format_passes_the_agents_number_check() -> None:
    # O contrato com o agente: todo número do texto precisa ser exatamente um valor do JSON.
    # Por isso o JSON já traz os valores arredondados do jeito que a tela mostra.
    linhas = [linha("Recife", "1234567.894", "1200000.005", tarifa="1.234", volume="-35000")]
    metricas = metricas_da_receita(filtro(), linhas)
    assert metricas is not None
    valores = list(_valores(metricas))

    texto = (
        f"A receita de {metricas['periodo_atual']} ficou em R$ {_brl(metricas['receita_atual'])}, "
        f"{_brl(abs(metricas['variacao_receita_pct']), 1)}% abaixo de {metricas['periodo_base']}."
    )

    assert unsupported_numbers(texto, valores) == ()


def test_money_has_at_most_two_decimals_and_percentages_one() -> None:
    linhas = [linha("Recife", "1234567.894", "1200000.005", tarifa="1.234", volume="-35000.333")]
    metricas = metricas_da_receita(filtro(), linhas)
    assert metricas is not None

    for chave in ("receita_base", "receita_atual", "variacao_receita", "efeito_volume"):
        assert -Decimal(str(metricas[chave])).as_tuple().exponent <= 2
    assert -Decimal(str(metricas["variacao_receita_pct"])).as_tuple().exponent <= 1


def _valores(valor: object):
    if isinstance(valor, dict):
        for item in valor.values():
            yield from _valores(item)
    elif isinstance(valor, list):
        for item in valor:
            yield from _valores(item)
    else:
        yield valor


def _brl(numero: float, casas: int = 2) -> str:
    texto = f"{numero:,.{casas}f}"
    return texto.replace(",", "#").replace(".", ",").replace("#", ".")


def test_factors_keep_each_effect_in_its_own_direction() -> None:
    linhas = [linha("Recife", "1000", "1080", tarifa="100", bandeira="20", volume="-50", mix="10")]

    metricas = metricas_da_receita(filtro(), linhas)

    assert metricas is not None
    assert metricas["fatores_a_favor"] == ["preço", "perfil de consumo"]
    assert metricas["fatores_contra"] == ["quantidade vendida"]
    assert metricas["maior_fator"] == "preço"


def test_an_effect_of_zero_is_on_neither_side() -> None:
    metricas = metricas_da_receita(filtro(), [linha("A", "100", "95", volume="-5")])

    assert metricas is not None
    assert metricas["fatores_a_favor"] == []
    assert metricas["fatores_contra"] == ["quantidade vendida"]


def test_drops_are_counted_and_the_worst_share_is_over_all_drops() -> None:
    linhas = [
        linha("A", "100", "25"),
        linha("B", "100", "90"),
        linha("C", "100", "90"),
        linha("D", "100", "95"),
        linha("E", "100", "130"),
    ]

    metricas = metricas_da_receita(filtro(), linhas)

    assert metricas is not None
    assert metricas["n_segmentos_em_queda"] == 4
    assert metricas["maior_queda_participacao_pct"] == 75.0


def test_without_drops_there_is_no_share() -> None:
    metricas = metricas_da_receita(filtro(), [linha("A", "100", "120", volume="20")])

    assert metricas is not None
    assert metricas["n_segmentos_em_queda"] == 0
    assert "maior_queda_participacao_pct" not in metricas


def test_counts_where_quantity_fell_and_where_only_price_held_the_rise() -> None:
    linhas = [
        linha("A", "100", "110", tarifa="20", volume="-10"),
        linha("B", "100", "95", tarifa="5", volume="-10"),
        linha("C", "100", "110", tarifa="5", volume="5"),
    ]

    metricas = metricas_da_receita(filtro(), linhas)

    assert metricas is not None
    assert metricas["n_segmentos_quantidade_em_queda"] == 2
    assert metricas["n_segmentos_alta_so_por_preco"] == 1


def test_flag_share_of_the_price_effect() -> None:
    metricas = metricas_da_receita(filtro(), [linha("A", "100", "120", tarifa="5", bandeira="15")])

    assert metricas is not None
    assert metricas["bandeira_no_preco_pct"] == 75.0


def test_flag_share_is_left_out_when_the_parts_do_not_add_up_as_a_share() -> None:
    contra = metricas_da_receita(filtro(), [linha("A", "100", "110", tarifa="15", bandeira="-5")])
    queda = metricas_da_receita(filtro(), [linha("A", "100", "95", tarifa="-2", bandeira="-3")])

    assert contra is not None and "bandeira_no_preco_pct" not in contra
    assert queda is not None and "bandeira_no_preco_pct" not in queda


def _preco_sustenta(segmento: str) -> DecomposicaoLinhaSchema:
    return linha(segmento, "100", "110", tarifa="20", volume="-10")


def test_reading_alta_depende_do_preco() -> None:
    linhas = [_preco_sustenta(nome) for nome in "ABC"] + [
        linha("D", "100", "110", tarifa="5", volume="5")
    ]

    metricas = metricas_da_receita(filtro(), linhas)

    assert metricas["leitura_principal"] == "alta_depende_do_preco"
    assert metricas["leitura_texto"].startswith("Em 3 dos 4 municípios, a receita só subiu")


def test_reading_says_all_when_every_segment_depends_on_price() -> None:
    metricas = metricas_da_receita(filtro(), [_preco_sustenta(nome) for nome in "ABC"])

    assert metricas["leitura_texto"].startswith("Em todos os 3 municípios,")


def test_reading_bandeira_pesa() -> None:
    linhas = [linha("A", "100", "120", tarifa="5", bandeira="15")]

    metricas = metricas_da_receita(filtro(), linhas)

    assert metricas["leitura_principal"] == "bandeira_pesa"
    assert metricas["leitura_texto"].startswith("75,0% do ganho de preço")


def test_reading_quantidade_geral_when_revenue_fell() -> None:
    linhas = [linha(nome, "100", "95", volume="-5") for nome in "ABC"]

    metricas = metricas_da_receita(filtro(), linhas)

    assert metricas["leitura_principal"] == "quantidade_geral"


def test_reading_quedas_concentradas() -> None:
    linhas = [
        linha("A", "100", "20", tarifa="-80"),
        linha("B", "100", "90", tarifa="-10"),
        linha("C", "100", "110", volume="10"),
    ]

    metricas = metricas_da_receita(filtro(), linhas)

    assert metricas["leitura_principal"] == "quedas_concentradas"
    assert metricas["leitura_texto"].startswith("A responde por 88,9% da soma das quedas")


def test_reading_unico_em_queda_compares_with_the_city() -> None:
    corte = filtro(municipio="Abreu e Lima", bairro="Planalto")
    linhas = [linha("B3", "100", "98", volume="-2", nivel="classe")]
    acima = [
        linha("Planalto", "100", "98", volume="-2", nivel="bairro"),
        linha("Centro", "100", "120", volume="20", nivel="bairro"),
        linha("Timbó", "100", "120", volume="20", nivel="bairro"),
    ]

    metricas = metricas_da_receita(corte, linhas, acima)

    assert metricas["leitura_principal"] == "unico_em_queda"
    assert metricas["leitura_texto"] == (
        "Planalto foi o único bairro a perder receita em Abreu e Lima: recuou 2,0%, "
        "enquanto Abreu e Lima cresceu 12,7%."
    )


def test_reading_comparison_is_what_a_small_cut_gets() -> None:
    corte = filtro(municipio="Abreu e Lima", bairro="Caetés")
    linhas = [linha("B1", "100", "120", volume="20", nivel="classe")]
    acima = [
        linha("Caetés", "100", "120", volume="20", nivel="bairro"),
        linha("Centro", "100", "100", nivel="bairro"),
    ]

    metricas = metricas_da_receita(corte, linhas, acima)

    assert metricas["leitura_principal"] == "comparacao_acima"
    assert metricas["leitura_texto"] == (
        "Em Caetés, a receita cresceu 20,0%, enquanto Abreu e Lima cresceu 10,0%."
    )


def test_reading_without_base_revenue_names_the_factor() -> None:
    metricas = metricas_da_receita(filtro(), [linha("Novo", "0", "10", mix="10")])

    assert metricas["leitura_principal"] == "maior_fator"
    assert metricas["leitura_texto"] == "O que mais pesou foi o perfil de consumo."


def test_reading_when_nothing_changed() -> None:
    metricas = metricas_da_receita(filtro(), [linha("A", "100", "100")])

    assert metricas["leitura_principal"] == "sem_variacao"


def test_the_cut_above_drops_the_most_specific_filter() -> None:
    assert filtro_acima(filtro()) is None
    assert filtro_acima(filtro(classe="B1")).classe is None
    assert filtro_acima(filtro(municipio="Recife", classe="B1")).municipio is None
    acima = filtro_acima(filtro(municipio="Recife", bairro="Pina"))
    assert (acima.municipio, acima.bairro) == ("Recife", None)


def test_model_text_needs_the_same_numbers_as_the_reading() -> None:
    metricas = {"leitura_texto": "Em 73 dos 86 bairros, a receita só subiu por causa do preço."}

    assert texto_aceito("A receita só subiu pelo preço em 73 dos 86 bairros.", metricas)
    assert not texto_aceito("A receita só subiu pelo preço em 73 bairros.", metricas)
    assert not texto_aceito("Em 73 dos 86 bairros, e 12,3% a mais.", metricas)


def test_model_text_cannot_use_jargon() -> None:
    metricas = {"leitura_texto": "A receita só subiu por causa do preço."}

    assert not texto_aceito("O efeito preço segurou a receita.", metricas)
    assert not texto_aceito("O faturamento subiu.", metricas)


def test_reading_agrees_with_classes_in_the_feminine() -> None:
    corte = filtro(municipio="Recife", bairro="Pina")
    linhas = [_preco_sustenta(nome) for nome in ("B1", "B2", "B3")]
    linhas = [item.model_copy(update={"nivel": "classe"}) for item in linhas]

    metricas = metricas_da_receita(corte, linhas)

    assert metricas["leitura_texto"].startswith("Em todas as 3 classes,")


def test_reading_compares_a_class_with_the_company() -> None:
    linhas = [linha("Recife", "100", "120", volume="20")]
    acima = [linha("Recife", "200", "220", volume="20")]

    metricas = metricas_da_receita(filtro(classe="A4"), linhas, acima)

    assert metricas["leitura_texto"] == (
        "Na classe A4, a receita cresceu 20,0%, enquanto a empresa cresceu 10,0%."
    )


def test_model_text_cannot_add_another_conclusion() -> None:
    metricas = {"leitura_texto": "74,0% do ganho de preço veio da bandeira, não da tarifa."}
    extra = " O resultado foi impulsionado pelo preço e pelo perfil de consumo, apesar da queda."

    assert not texto_aceito(metricas["leitura_texto"] + extra, metricas)


def test_reading_comparison_says_stable_when_the_percentage_is_zero() -> None:
    corte = filtro(municipio="Recife", bairro="Pina")
    linhas = [linha("B1", "100", "100", nivel="classe")]
    acima = [
        linha("Pina", "100", "100", nivel="bairro"),
        linha("Boa Vista", "100", "120", volume="20", nivel="bairro"),
    ]

    metricas = metricas_da_receita(corte, linhas, acima)

    assert (
        metricas["leitura_texto"]
        == "Em Pina, a receita ficou estável, enquanto Recife cresceu 10,0%."
    )


def test_model_text_cannot_swap_a_rise_with_a_drop() -> None:
    metricas = {"leitura_texto": "Em Pina, a receita cresceu 5,0%, enquanto Recife recuou 2,0%."}

    assert texto_aceito("Em Pina, a receita subiu 5,0%, enquanto Recife caiu 2,0%.", metricas)
    assert not texto_aceito("Em Pina, a receita caiu 5,0%, enquanto Recife subiu 2,0%.", metricas)
    assert not texto_aceito("Em Pina, a receita caiu 5,0%, enquanto Recife recuou 2,0%.", metricas)
