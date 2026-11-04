from decimal import Decimal

from venergy_agent.domain.numbers import unsupported_numbers

from venergy_api.insight_uc import metricas_da_uc, texto_aceito
from venergy_api.schemas import ConsumoUcSchema, VariacaoContaSchema


def consumo(mes: float | None, ano: float | None) -> ConsumoUcSchema:
    return ConsumoUcSchema(
        referencia="2025-12",
        meses=[],
        kwh_12m=Decimal(0),
        kwh_12m_ano_anterior=Decimal(0),
        variacao_12m_pct=ano,
        meses_comparados=12 if ano is not None else 0,
        variacao_ultimo_mes_pct=mes,
        tendencia="sem_comparacao",
    )


def conta(diferenca: str, leitura_estimada: bool = False) -> VariacaoContaSchema:
    return VariacaoContaSchema(
        competencia="2025-12",
        competencia_comparada="2024-12",
        conta=Decimal("100") + Decimal(diferenca),
        conta_comparada=Decimal("100"),
        diferenca=Decimal(diferenca),
        dias_faturados=30,
        dias_faturados_comparada=30,
        consumo=Decimal(0),
        tarifa=Decimal(diferenca),
        bandeira=Decimal(0),
        tributos=Decimal(0),
        leitura_estimada=leitura_estimada,
    )


def ids(metricas: dict) -> list[str]:
    return [candidata["id"] for candidata in metricas["candidatas"]]


def test_nothing_to_narrate_without_any_comparison() -> None:
    assert metricas_da_uc(consumo(None, None), None) is None


def test_bill_up_without_more_energy_is_the_first_reading() -> None:
    metricas = metricas_da_uc(consumo(-2.04, -1.0), conta("35.5"))

    assert metricas["leitura_principal"] == "conta_sem_consumo"
    assert metricas["leitura_texto"] == (
        "A conta subiu R$ 35,50, mas o consumo do mês recuou 2,0% contra o mesmo mês do ano "
        "anterior: o cliente não gastou mais energia."
    )


def test_a_rise_only_in_the_last_month_is_an_exception() -> None:
    metricas = metricas_da_uc(consumo(25.0, -3.0), None)

    assert ids(metricas) == ["mes_fora_do_padrao"]


def test_a_rise_in_the_month_and_in_the_year_is_a_trend() -> None:
    metricas = metricas_da_uc(consumo(10.0, 6.0), conta("12"))

    assert ids(metricas) == ["conta_com_consumo", "tendencia"]


def test_a_bill_that_went_down_has_no_bill_reading() -> None:
    metricas = metricas_da_uc(consumo(-5.0, -4.0), conta("-8"))

    assert ids(metricas) == ["tendencia"]


def test_an_estimated_reading_is_a_candidate() -> None:
    metricas = metricas_da_uc(consumo(3.0, 1.0), conta("5", leitura_estimada=True))

    assert ids(metricas)[-1] == "leitura_estimada"


def test_every_candidate_passes_the_agents_number_check() -> None:
    metricas = metricas_da_uc(consumo(-2.04, 7.77), conta("1234.5"))

    for candidata in metricas["candidatas"]:
        assert unsupported_numbers(candidata["texto"], list(metricas.values())) == ()


def test_model_text_cannot_flip_the_month_into_a_rise() -> None:
    metricas = metricas_da_uc(consumo(-2.0, -1.0), conta("35.5"))

    assert texto_aceito(
        "A conta subiu R$ 35,50, mas o consumo do mês recuou 2,0% contra o mesmo mês do ano "
        "anterior: o cliente não gastou mais energia.",
        metricas,
        ("conta_sem_consumo",),
    )
    assert not texto_aceito(
        "A conta subiu R$ 35,50 porque o consumo do mês subiu 2,0%.",
        metricas,
        ("conta_sem_consumo",),
    )
