from datetime import date
from decimal import Decimal

import pytest

from venergy_api.conta_uc import montar_variacao_conta
from venergy_api.models import FatoFaturamentoMensal

REFERENCIA = "2025-12"
MESMO_MES_DO_ANO_ANTERIOR = "2024-12"
CENTAVO = Decimal("0.01")


def fatura(competencia: str, **changes: object) -> FatoFaturamentoMensal:
    values: dict[str, object] = {
        "cod_uc": "0001",
        "competencia": competencia,
        "kwh_faturado": Decimal("100"),
        "kwh_leitura": Decimal("100"),
        "origem_kwh": "leitura",
        "receita_faturada": Decimal("90.00"),
        "receita_energia": Decimal("70.00"),
        "tributos": Decimal("20.00"),
        "receita_arrecadada": Decimal("90.00"),
        "tarifa_media": 0.7,
        "bandeira": "verde",
        "data_vencimento": date(2026, 1, 10),
        "data_pagamento": date(2026, 1, 8),
        "status_pagamento": "paga",
        "dias_em_atraso": None,
        "receita_bandeira": Decimal("0.00"),
        "tipo_leitura": "real",
        "tipo_medidor": "smart",
        "dias_faturados": 30,
    }
    return FatoFaturamentoMensal(**{**values, **changes})


def partes(variacao) -> list[Decimal]:
    return [
        variacao.consumo,
        variacao.tarifa,
        variacao.bandeira,
        variacao.tributos,
    ]


def test_parts_always_add_up_to_the_difference_of_the_bills() -> None:
    # Números que não dividem em centavos exatos: o arredondamento não pode quebrar a soma.
    anterior = fatura(
        MESMO_MES_DO_ANO_ANTERIOR,
        kwh_faturado=Decimal("97"),
        receita_energia=Decimal("68.37"),
        receita_bandeira=Decimal("1.84"),
        tributos=Decimal("17.09"),
        receita_faturada=Decimal("85.46"),
        dias_faturados=29,
    )
    atual = fatura(
        REFERENCIA,
        kwh_faturado=Decimal("103"),
        receita_energia=Decimal("76.52"),
        receita_bandeira=Decimal("4.64"),
        tributos=Decimal("19.13"),
        receita_faturada=Decimal("95.65"),
        dias_faturados=31,
    )

    variacao = montar_variacao_conta(REFERENCIA, [anterior, atual])

    assert variacao is not None
    assert variacao.diferenca == Decimal("10.19")
    assert sum(partes(variacao)) == variacao.diferenca
    assert all(parte == parte.quantize(CENTAVO) for parte in partes(variacao))


def test_reports_both_bills_and_the_month_they_are_compared_with() -> None:
    variacao = montar_variacao_conta(
        REFERENCIA, [fatura(MESMO_MES_DO_ANO_ANTERIOR), fatura(REFERENCIA)]
    )

    assert variacao is not None
    assert (variacao.competencia, variacao.competencia_comparada) == (REFERENCIA, "2024-12")
    assert (variacao.conta, variacao.conta_comparada) == (Decimal("90.00"), Decimal("90.00"))


def test_compares_only_with_the_same_month_of_the_previous_year() -> None:
    ruido = fatura("2025-11", receita_faturada=Decimal("999.00"), receita_energia=Decimal("900.00"))

    variacao = montar_variacao_conta(
        REFERENCIA, [ruido, fatura(MESMO_MES_DO_ANO_ANTERIOR), fatura(REFERENCIA)]
    )

    assert variacao is not None
    assert variacao.diferenca == Decimal("0.00")


def test_a_bandeira_increase_goes_entirely_to_the_bandeira() -> None:
    anterior = fatura(MESMO_MES_DO_ANO_ANTERIOR)
    atual = fatura(
        REFERENCIA,
        receita_bandeira=Decimal("1.90"),
        receita_energia=Decimal("71.90"),
        receita_faturada=Decimal("91.90"),
    )

    variacao = montar_variacao_conta(REFERENCIA, [anterior, atual])

    assert variacao is not None
    assert variacao.bandeira == Decimal("1.90")
    assert [variacao.consumo, variacao.tarifa, variacao.tributos] == [0, 0, 0]


def test_a_tariff_increase_goes_to_the_tariff_and_the_taxes_to_the_taxes() -> None:
    anterior = fatura(MESMO_MES_DO_ANO_ANTERIOR)
    atual = fatura(
        REFERENCIA,
        receita_energia=Decimal("75.60"),
        tributos=Decimal("21.00"),
        receita_faturada=Decimal("96.60"),
    )

    variacao = montar_variacao_conta(REFERENCIA, [anterior, atual])

    assert variacao is not None
    assert (variacao.tarifa, variacao.tributos) == (Decimal("5.60"), Decimal("1.00"))
    assert [variacao.consumo, variacao.bandeira] == [0, 0]


def test_a_different_number_of_days_does_not_split_the_volume() -> None:
    # Na Gold real o kWh não acompanha os dias faturados: 10 dias a mais com 3 kWh a mais.
    # Todo o volume é consumo, a R$ 0,70 por kWh do ano anterior.
    anterior = fatura(
        MESMO_MES_DO_ANO_ANTERIOR,
        kwh_faturado=Decimal("90"),
        receita_energia=Decimal("63.00"),
        receita_faturada=Decimal("83.00"),
        dias_faturados=30,
    )
    atual = fatura(
        REFERENCIA,
        kwh_faturado=Decimal("93"),
        receita_energia=Decimal("65.10"),
        receita_faturada=Decimal("85.10"),
        dias_faturados=40,
    )

    variacao = montar_variacao_conta(REFERENCIA, [anterior, atual])

    assert variacao is not None
    assert variacao.consumo == Decimal("2.10")
    assert [variacao.tarifa, variacao.bandeira, variacao.tributos] == [0, 0, 0]


def test_more_energy_in_the_same_days_goes_to_the_consumption() -> None:
    anterior = fatura(MESMO_MES_DO_ANO_ANTERIOR)
    atual = fatura(
        REFERENCIA,
        kwh_faturado=Decimal("120"),
        receita_energia=Decimal("84.00"),
        receita_faturada=Decimal("104.00"),
    )

    variacao = montar_variacao_conta(REFERENCIA, [anterior, atual])

    assert variacao is not None
    assert variacao.consumo == Decimal("14.00")
    assert [variacao.tarifa, variacao.bandeira, variacao.tributos] == [0, 0, 0]


def test_reports_the_days_each_bill_covered() -> None:
    anterior = fatura(MESMO_MES_DO_ANO_ANTERIOR, dias_faturados=29)
    atual = fatura(REFERENCIA, dias_faturados=33)

    variacao = montar_variacao_conta(REFERENCIA, [anterior, atual])

    assert variacao is not None
    assert (variacao.dias_faturados, variacao.dias_faturados_comparada) == (33, 29)


def test_a_bill_without_the_days_reports_them_empty_and_still_adds_up() -> None:
    anterior = fatura(MESMO_MES_DO_ANO_ANTERIOR, dias_faturados=None)
    atual = fatura(
        REFERENCIA,
        kwh_faturado=Decimal("110"),
        receita_energia=Decimal("77.00"),
        receita_faturada=Decimal("97.00"),
        dias_faturados=31,
    )

    variacao = montar_variacao_conta(REFERENCIA, [anterior, atual])

    assert variacao is not None
    assert (variacao.dias_faturados, variacao.dias_faturados_comparada) == (31, None)
    assert variacao.consumo == Decimal("7.00")
    assert sum(partes(variacao)) == variacao.diferenca


@pytest.mark.parametrize(
    "faturas",
    [
        pytest.param([fatura(MESMO_MES_DO_ANO_ANTERIOR)], id="no bill in the reference month"),
        pytest.param([fatura(REFERENCIA)], id="no bill in the same month of the previous year"),
        pytest.param(
            [
                fatura(MESMO_MES_DO_ANO_ANTERIOR, kwh_faturado=Decimal("0")),
                fatura(REFERENCIA),
            ],
            id="no energy in the bill it is compared with",
        ),
        pytest.param([], id="no bills at all"),
    ],
)
def test_there_is_no_breakdown_when_the_bills_cannot_be_compared(faturas) -> None:
    assert montar_variacao_conta(REFERENCIA, faturas) is None


def test_there_is_no_breakdown_before_the_gold_has_invoices() -> None:
    assert montar_variacao_conta(None, []) is None


@pytest.mark.parametrize(
    ("estimada_antes", "estimada_agora", "esperado"),
    [(False, False, False), (True, False, True), (False, True, True)],
)
def test_flags_when_either_reading_was_estimated(
    estimada_antes: bool, estimada_agora: bool, esperado: bool
) -> None:
    anterior = fatura(
        MESMO_MES_DO_ANO_ANTERIOR, tipo_leitura="estimada" if estimada_antes else "real"
    )
    atual = fatura(REFERENCIA, tipo_leitura="estimada" if estimada_agora else "real")

    variacao = montar_variacao_conta(REFERENCIA, [anterior, atual])

    assert variacao is not None
    assert variacao.leitura_estimada is esperado
