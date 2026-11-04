from decimal import Decimal

from venergy_agent.domain.numbers import unsupported_numbers

from venergy_api.insight_indicadores import metricas_dos_indicadores, texto_aceito
from venergy_api.schemas import (
    ComparacaoIndicadoresSchema,
    IndicadoresComparacaoFiltroSchema,
    IndicadoresPeriodoSchema,
    VariacaoIndicadoresSchema,
)


def filtro(**recorte: str) -> IndicadoresComparacaoFiltroSchema:
    return IndicadoresComparacaoFiltroSchema(
        base_inicio="2024-01",
        base_fim="2024-12",
        atual_inicio="2025-01",
        atual_fim="2025-12",
        **recorte,
    )


def periodo(inicio: str, fim: str) -> IndicadoresPeriodoSchema:
    return IndicadoresPeriodoSchema(
        inicio=inicio,
        fim=fim,
        n_meses=12,
        receita_faturada=Decimal(0),
        receita_energia=Decimal(0),
        tributos=Decimal(0),
        kwh_faturado=Decimal(0),
        n_uc_medio=None,
        n_uc_fim=0,
        tarifa_media=None,
        tarifa_base_media=None,
        horas_interrompidas=0,
        n_interrupcoes=0,
        dec=None,
        fec=None,
        n_chamados=0,
        n_notas=0,
        satisfacao_media=None,
    )


def comparacao(**variacoes: float) -> ComparacaoIndicadoresSchema:
    nulas = dict.fromkeys(VariacaoIndicadoresSchema.model_fields)
    return ComparacaoIndicadoresSchema(
        base=periodo("2024-01", "2024-12"),
        atual=periodo("2025-01", "2025-12"),
        variacao_pct=VariacaoIndicadoresSchema(**{**nulas, **variacoes}),
    )


def test_nothing_to_narrate_without_any_variation() -> None:
    assert metricas_dos_indicadores(filtro(), comparacao()) is None


def test_revenue_up_with_less_energy_says_the_gain_came_from_price() -> None:
    metricas = metricas_dos_indicadores(
        filtro(), comparacao(receita_faturada=8.04, kwh_faturado=-3.96)
    )

    assert metricas["leitura_principal"] == "receita_sem_consumo"
    assert metricas["leitura_texto"] == (
        "A receita cresceu 8,0%, mas a energia faturada recuou 4,0%: "
        "o ganho veio do preço, não do consumo."
    )


def test_revenue_growing_faster_than_energy_credits_part_to_price() -> None:
    metricas = metricas_dos_indicadores(filtro(), comparacao(receita_faturada=9, kwh_faturado=2))

    assert metricas["leitura_principal"] == "preco_acima_do_consumo"


def test_both_falling_just_states_the_two_variations() -> None:
    metricas = metricas_dos_indicadores(filtro(), comparacao(receita_faturada=-2, kwh_faturado=-5))

    assert metricas["leitura_texto"] == "A receita recuou 2,0% e a energia faturada recuou 5,0%."


def test_service_reading_names_the_indicator_that_worsened_most() -> None:
    metricas = metricas_dos_indicadores(
        filtro(), comparacao(dec=4.0, fec=-10.0, n_chamados=12.3, satisfacao_media=-1.0)
    )

    assert metricas["leitura_principal"] == "maior_piora"
    assert metricas["leitura_texto"] == (
        "Na rede e no atendimento, o que mais piorou foi o número de chamados, que cresceu 12,3%."
    )


def test_satisfaction_worsens_when_it_falls() -> None:
    metricas = metricas_dos_indicadores(filtro(), comparacao(dec=1.0, satisfacao_media=-6.5))

    assert "a satisfação média, que recuou 6,5%" in metricas["leitura_texto"]


def test_service_improving_everywhere_is_said_without_numbers() -> None:
    metricas = metricas_dos_indicadores(filtro(), comparacao(dec=-3.0, satisfacao_media=2.0))

    assert metricas["leitura_texto"] == "Nenhum indicador de rede e atendimento piorou."


def test_both_readings_are_joined_in_order() -> None:
    metricas = metricas_dos_indicadores(
        filtro(municipio="Olinda"), comparacao(receita_faturada=8, kwh_faturado=-4, dec=5)
    )

    assert metricas["leitura_principal"] == "receita_sem_consumo+maior_piora"
    assert metricas["recorte"] == "Olinda"
    assert metricas["periodo_atual"] == "2025-01/2025-12"


def test_every_number_of_the_reading_passes_the_agents_number_check() -> None:
    metricas = metricas_dos_indicadores(
        filtro(), comparacao(receita_faturada=8.04, kwh_faturado=-3.96, satisfacao_media=-6.54)
    )

    assert unsupported_numbers(str(metricas["leitura_texto"]), list(metricas.values())) == ()


def test_model_text_is_refused_when_it_flips_a_direction_or_cites_a_key() -> None:
    metricas = metricas_dos_indicadores(filtro(), comparacao(receita_faturada=8, kwh_faturado=-4))

    assert texto_aceito(
        "A receita cresceu 8,0%, mas a energia faturada recuou 4,0%; o ganho veio do preço.",
        metricas,
    )
    assert not texto_aceito(
        "A receita recuou 8,0%, mas a energia faturada cresceu 4,0%: o ganho veio do preço.",
        metricas,
    )
    assert not texto_aceito("A receita_faturada cresceu 8,0% e o kwh recuou 4,0%.", metricas)


def test_a_growing_base_with_less_energy_says_each_unit_consumes_less() -> None:
    metricas = metricas_dos_indicadores(
        filtro(), comparacao(n_uc_medio=2.5, receita_faturada=8, kwh_faturado=-4, dec=3)
    )

    assert [candidata["id"] for candidata in metricas["candidatas"]] == [
        "base_cresce_consumo_cai",
        "receita_sem_consumo",
        "maior_piora",
    ]
    assert metricas["leitura_principal"] == "base_cresce_consumo_cai+maior_piora"
    assert metricas["candidatas"][0]["texto"] == (
        "O número de unidades consumidoras cresceu 2,5%, mas a energia faturada recuou 4,0%: "
        "cada unidade passou a consumir menos."
    )
