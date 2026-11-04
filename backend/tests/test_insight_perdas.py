from decimal import Decimal

from venergy_agent.domain.numbers import unsupported_numbers

from venergy_api.insight_perdas import metricas_de_perdas, texto_aceito
from venergy_api.schemas import (
    AcertoInspecoesSchema,
    IndicadoresPerdasSchema,
    RecorteFilaSchema,
    RecorteFiltroSchema,
    RecortesFilaSchema,
)


def acerto(irregulares: int = 0, regulares: int = 0) -> AcertoInspecoesSchema:
    decididas = irregulares + regulares
    return AcertoInspecoesSchema(
        inspecoes=decididas,
        irregulares=irregulares,
        regulares=regulares,
        nao_realizadas=0,
        taxa_irregularidade=irregulares / decididas if decididas else None,
        kwh_recuperado=Decimal(0),
    )


def indicadores(
    suspeitas: int = 100,
    sem_ordem: int = 80,
    kwh: str | None = "12345.6",
    portal: AcertoInspecoesSchema | None = None,
    gold: AcertoInspecoesSchema | None = None,
) -> IndicadoresPerdasSchema:
    return IndicadoresPerdasSchema(
        suspeitas=suspeitas,
        suspeitas_sem_ordem_ativa=sem_ordem,
        kwh_recuperavel_est_sem_ordem=Decimal(kwh) if kwh else None,
        ordens_geradas=0,
        ordens_em_campo=0,
        portal=portal or acerto(),
        gold=gold or acerto(),
    )


def recortes(*kwhs: int, nivel: str = "municipio") -> RecortesFilaSchema:
    return RecortesFilaSchema(
        nivel=nivel,
        recortes=[
            RecorteFilaSchema(
                segmento=f"Lugar {chr(65 + i)}",
                suspeitas=10,
                suspeitas_sem_ordem_ativa=10,
                kwh_recuperavel_est=Decimal(kwh),
            )
            for i, kwh in enumerate(kwhs)
        ],
    )


def textos(metricas: dict) -> dict[str, str]:
    return {candidata["id"]: candidata["texto"] for candidata in metricas["candidatas"]}


def test_an_empty_queue_has_nothing_to_narrate() -> None:
    assert metricas_de_perdas(RecorteFiltroSchema(), indicadores(suspeitas=0), recortes()) is None


def test_concentration_names_the_places_with_most_energy_to_recover() -> None:
    metricas = metricas_de_perdas(
        RecorteFiltroSchema(), indicadores(), recortes(500, 300, 100, 50, 50)
    )

    assert metricas["leitura_principal"] == "concentracao"
    assert metricas["leitura_texto"] == (
        "Os 3 municípios com mais energia a recuperar, de 5, concentram 90,0% do kWh estimado "
        "da fila: Lugar A, Lugar B e Lugar C."
    )


def test_few_places_have_no_concentration_reading() -> None:
    metricas = metricas_de_perdas(RecorteFiltroSchema(), indicadores(), recortes(500, 300))

    assert "concentracao" not in textos(metricas)


def test_portal_hit_rate_is_compared_with_the_history() -> None:
    metricas = metricas_de_perdas(
        RecorteFiltroSchema(),
        indicadores(portal=acerto(9, 11), gold=acerto(52, 48)),
        recortes(),
    )

    assert textos(metricas)["acerto_das_inspecoes"] == (
        "As vistorias do portal confirmaram irregularidade em 45,0% dos casos, "
        "abaixo dos 52,0% do histórico."
    )


def test_few_portal_inspections_give_no_hit_rate_reading() -> None:
    metricas = metricas_de_perdas(
        RecorteFiltroSchema(), indicadores(portal=acerto(2, 1), gold=acerto(5, 5)), recortes()
    )

    assert "acerto_das_inspecoes" not in textos(metricas)


def test_idle_queue_counts_suspicions_without_an_order_and_their_energy() -> None:
    metricas = metricas_de_perdas(RecorteFiltroSchema(), indicadores(), recortes())

    assert textos(metricas)["fila_parada"] == (
        "80 das 100 suspeitas ainda não têm ordem de inspeção; juntas, estimam 12.345 kWh por mês."
    )


def test_no_unit_code_reaches_the_metrics() -> None:
    metricas = metricas_de_perdas(
        RecorteFiltroSchema(municipio="Olinda"), indicadores(), recortes(5, 4, 3, 2, 1)
    )

    assert "cod_uc" not in str(metricas) and "UC" not in str(metricas)


def test_every_candidate_passes_the_agents_number_check() -> None:
    metricas = metricas_de_perdas(
        RecorteFiltroSchema(),
        indicadores(portal=acerto(9, 11), gold=acerto(52, 48)),
        recortes(500, 300, 100, 50, 50),
    )

    for candidata in metricas["candidatas"]:
        assert unsupported_numbers(candidata["texto"], list(metricas.values())) == ()


def test_model_text_cannot_turn_below_into_above() -> None:
    metricas = metricas_de_perdas(
        RecorteFiltroSchema(),
        indicadores(portal=acerto(9, 11), gold=acerto(52, 48)),
        recortes(),
    )
    escolha = ("acerto_das_inspecoes",)

    assert texto_aceito(
        "No portal, 45,0% das vistorias acharam irregularidade, abaixo dos 52,0% históricos.",
        metricas,
        escolha,
    )
    assert not texto_aceito(
        "No portal, 45,0% das vistorias acharam irregularidade, acima dos 52,0% históricos.",
        metricas,
        escolha,
    )
