from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from venergy_api.database import Base
from venergy_api.models import FatoFaturamentoMensal, KpisMensais, KpisSegmentoMensal

COMPARE = "/indicadores/comparacao"
WINDOWS = "/indicadores/janelas"
NO_BASE = ("2000-01", "2000-01")
MONTHLY = "/indicadores/mensal"


def month(index: int) -> str:
    """Competência `index` meses depois de 2024-01."""
    year, number = divmod(index, 12)
    return f"{2024 + year}-{number + 1:02d}"


def segment(competencia: str, **values: object) -> KpisSegmentoMensal:
    fields: dict[str, object] = {
        "competencia": competencia,
        "municipio": "Recife",
        "bairro": "Boa Viagem",
        "classe_cadastro": "Residencial",
        "possui_gd": False,
        "cod_alimentador": "AL-01",
        "tipo_medidor": "eletronico",
        "classe": "B1",
        "n_uc": 100,
        "kwh_faturado": Decimal("1000.000"),
        "receita_faturada": Decimal("1200.00"),
        "receita_energia": Decimal("1000.00"),
        "tributos": Decimal("200.00"),
        "receita_arrecadada": None,
        "horas_interrompidas": 0.0,
        "n_interrupcoes": 0,
        "n_chamados": 0,
        "soma_notas": None,
        "n_notas": 0,
        "receita_bandeira": Decimal("0.00"),
        "n_faturas": 0,
        "n_faturas_nao_pagas": 0,
        "valor_nao_pago": Decimal("0.00"),
        "n_faturas_pagas_com_atraso": 0,
        "soma_dias_em_atraso": 0,
        "n_leituras": 0,
        "n_leituras_estimadas": 0,
    }
    return KpisSegmentoMensal(**{**fields, **values})


def store(engine: Engine, *objects: object) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all(objects)


def compare(client: TestClient, base: tuple[str, str], atual: tuple[str, str], **extra: str):
    params = {
        "base_inicio": base[0],
        "base_fim": base[1],
        "atual_inicio": atual[0],
        "atual_fim": atual[1],
        **extra,
    }
    response = client.get(COMPARE, params=params)
    assert response.status_code == 200
    return response.json()


def test_single_month_matches_gold_kpis(engine: Engine, client: TestClient) -> None:
    store(
        engine,
        segment(
            "2025-01",
            municipio="Recife",
            n_uc=60,
            kwh_faturado=Decimal("600.000"),
            receita_faturada=Decimal("720.00"),
            receita_energia=Decimal("600.00"),
            horas_interrompidas=12.0,
            n_interrupcoes=6,
            n_chamados=4,
            soma_notas=Decimal(10),
            n_notas=3,
        ),
        segment(
            "2025-01",
            municipio="Olinda",
            bairro="Carmo",
            n_uc=40,
            kwh_faturado=Decimal("400.000"),
            receita_faturada=Decimal("480.00"),
            receita_energia=Decimal("400.00"),
            horas_interrompidas=8.0,
            n_interrupcoes=4,
            n_chamados=2,
            soma_notas=Decimal(5),
            n_notas=1,
        ),
        KpisMensais(
            competencia="2025-01",
            kwh_faturado=Decimal("1000.000"),
            receita_faturada=Decimal("1200.00"),
            receita_energia=Decimal("1000.00"),
            dec=0.2,
            fec=0.1,
            n_chamados=6,
            satisfacao_media=15 / 4,
        ),
    )

    atual = compare(client, NO_BASE, ("2025-01", "2025-01"))["atual"]

    assert atual["n_meses"] == 1
    assert atual["receita_faturada"] == 1200.0
    assert atual["receita_energia"] == 1000.0
    assert atual["kwh_faturado"] == 1000.0
    assert atual["dec"] == pytest.approx(0.2)
    assert atual["fec"] == pytest.approx(0.1)
    assert atual["n_chamados"] == 6
    assert atual["n_notas"] == 4
    assert atual["satisfacao_media"] == pytest.approx(3.75)


def test_variation_is_percent_and_null_without_base(engine: Engine, client: TestClient) -> None:
    store(
        engine,
        segment("2025-01", receita_faturada=Decimal("1000.00")),
        segment("2025-02", receita_faturada=Decimal("1080.00")),
    )

    result = compare(client, ("2025-01", "2025-01"), ("2025-02", "2025-02"))
    assert result["variacao_pct"]["receita_faturada"] == pytest.approx(8.0)
    assert result["variacao_pct"]["kwh_faturado"] == pytest.approx(0.0)
    # Sem nota nenhuma nos dois meses, a satisfação não existe e a variação também não.
    assert result["variacao_pct"]["satisfacao_media"] is None

    no_base = compare(client, ("2023-01", "2023-01"), ("2025-02", "2025-02"))
    assert no_base["base"]["receita_faturada"] == 0.0
    assert no_base["base"]["n_meses"] == 0
    assert no_base["variacao_pct"]["receita_faturada"] is None
    assert no_base["variacao_pct"]["dec"] is None


def test_multi_month_dec_fec_match_recortes_and_are_not_a_mean_of_months(
    engine: Engine, client: TestClient
) -> None:
    rows = [
        ("2025-01", "Recife", "Boa Viagem", 60, 6, 12.0),
        ("2025-01", "Olinda", "Carmo", 50, 0, 0.0),
        ("2025-02", "Recife", "Boa Viagem", 100, 20, 40.0),
        ("2025-02", "Olinda", "Carmo", 50, 10, 30.0),
    ]
    store(
        engine,
        *(
            segment(
                competencia,
                municipio=municipio,
                bairro=bairro,
                n_uc=n_uc,
                n_interrupcoes=interrupcoes,
                horas_interrompidas=horas,
            )
            for competencia, municipio, bairro, n_uc, interrupcoes, horas in rows
        ),
    )

    atual = compare(client, NO_BASE, ("2025-01", "2025-02"))["atual"]
    recortes = client.get(
        "/continuidade/recortes", params={"inicio": "2025-01", "fim": "2025-02"}
    ).json()["recortes"]
    horas = sum(r["horas_interrompidas"] for r in recortes)
    interrupcoes = sum(r["n_interrupcoes"] for r in recortes)
    n_uc_medio = sum(r["n_uc_medio"] for r in recortes)

    assert atual["dec"] == pytest.approx(horas / n_uc_medio)
    assert atual["fec"] == pytest.approx(interrupcoes / n_uc_medio)
    # Janeiro: 12 h ÷ 110 UC; fevereiro: 70 h ÷ 150 UC. A média dos dois não é o índice.
    mean_of_months = (12 / 110 + 70 / 150) / 2
    assert atual["dec"] != pytest.approx(mean_of_months)


def test_n_uc_is_stock_not_flow(engine: Engine, client: TestClient) -> None:
    store(
        engine,
        *(segment(month(i), n_uc=100) for i in range(3)),
        segment("2024-03", n_uc=100, municipio="Olinda", bairro="Carmo"),
    )

    atual = compare(client, NO_BASE, ("2024-01", "2024-03"))["atual"]
    assert atual["n_uc_medio"] == pytest.approx(400 / 3)
    assert atual["n_uc_fim"] == 200

    only_recife = compare(client, NO_BASE, ("2024-01", "2024-03"), municipio="Recife")["atual"]
    assert only_recife["n_uc_medio"] == pytest.approx(100.0)
    assert only_recife["n_uc_fim"] == 100


def test_n_uc_fim_is_the_last_month_with_data(engine: Engine, client: TestClient) -> None:
    store(
        engine,
        segment("2024-01", n_uc=90),
        segment("2024-02", n_uc=100),
        segment("2024-03", n_uc=110),
    )

    atual = compare(client, NO_BASE, ("2024-01", "2024-02"))["atual"]
    assert atual["n_uc_fim"] == 100
    assert atual["n_uc_medio"] == pytest.approx(95.0)


def test_satisfaction_is_sum_of_grades_over_grades_given(
    engine: Engine, client: TestClient
) -> None:
    store(
        engine,
        segment("2025-01", n_chamados=1, soma_notas=Decimal(5), n_notas=1),
        segment("2025-02", n_chamados=3, soma_notas=Decimal(9), n_notas=3),
    )

    atual = compare(client, NO_BASE, ("2025-01", "2025-02"))["atual"]
    assert atual["satisfacao_media"] == pytest.approx(3.5)
    assert atual["satisfacao_media"] != pytest.approx(4.0)


def test_tariffs(engine: Engine, client: TestClient) -> None:
    store(
        engine,
        segment(
            "2025-01",
            kwh_faturado=Decimal("1000.000"),
            receita_energia=Decimal("800.00"),
            receita_bandeira=Decimal("50.00"),
        ),
        segment("2025-02", kwh_faturado=Decimal("0.000"), receita_energia=Decimal("0.00")),
    )

    with_flag = compare(client, NO_BASE, ("2025-01", "2025-01"))["atual"]
    assert with_flag["tarifa_media"] == pytest.approx(0.8)
    assert with_flag["tarifa_base_media"] == pytest.approx(0.75)
    assert with_flag["tarifa_base_media"] < with_flag["tarifa_media"]

    no_kwh = compare(client, NO_BASE, ("2025-02", "2025-02"))["atual"]
    assert no_kwh["tarifa_media"] is None
    assert no_kwh["tarifa_base_media"] is None


def test_filters_by_class_and_municipality(engine: Engine, client: TestClient) -> None:
    store(
        engine,
        segment("2025-01", receita_faturada=Decimal("100.00")),
        segment("2025-01", classe="B3", bairro="Casa Forte", receita_faturada=Decimal("200.00")),
        segment(
            "2025-01",
            municipio="Olinda",
            bairro="Carmo",
            receita_faturada=Decimal("400.00"),
        ),
    )
    period = ("2025-01", "2025-01")

    assert compare(client, NO_BASE, period)["atual"]["receita_faturada"] == 700.0
    assert compare(client, NO_BASE, period, classe="B3")["atual"]["receita_faturada"] == 200.0
    assert (
        compare(client, NO_BASE, period, municipio="Olinda")["atual"]["receita_faturada"] == 400.0
    )
    assert (
        compare(client, NO_BASE, period, municipio="Recife", classe="B1")["atual"][
            "receita_faturada"
        ]
        == 100.0
    )


def test_invalid_filters_are_rejected(client: TestClient) -> None:
    valid = {
        "base_inicio": "2024-01",
        "base_fim": "2024-12",
        "atual_inicio": "2025-01",
        "atual_fim": "2025-12",
    }
    assert client.get(COMPARE, params={**valid, "bairro": "Carmo"}).status_code == 422
    assert client.get(COMPARE, params={**valid, "atual_inicio": "2026-01"}).status_code == 422
    assert client.get(COMPARE, params={**valid, "base_inicio": "2025-01"}).status_code == 422
    assert client.get(WINDOWS, params={"bairro": "Carmo"}).status_code == 422


def test_windows_over_24_months_give_13_points(engine: Engine, client: TestClient) -> None:
    store(
        engine,
        *(segment(month(i), receita_faturada=Decimal(100 + i), n_uc=100 + i) for i in range(24)),
    )

    windows = client.get(WINDOWS, params={"meses": 12}).json()

    assert len(windows) == 13
    assert [(w["inicio"], w["fim"]) for w in windows] == [
        (month(i), month(i + 11)) for i in range(13)
    ]
    first = windows[0]
    assert first["receita_faturada"] == sum(100 + i for i in range(12))
    assert first["kwh_faturado"] == 12000.0
    assert first["n_uc_medio"] == pytest.approx(sum(100 + i for i in range(12)) / 12)
    assert first["tarifa_media"] == pytest.approx(1.0)
    assert first["tarifa_base_media"] == pytest.approx(1.0)


def test_default_window_is_12_months(engine: Engine, client: TestClient) -> None:
    store(engine, *(segment(month(i)) for i in range(12)))

    assert len(client.get(WINDOWS).json()) == 1


def test_gap_removes_windows_that_cross_it(engine: Engine, client: TestClient) -> None:
    store(engine, *(segment(month(i)) for i in range(24) if i != 12))

    windows = client.get(WINDOWS, params={"meses": 6}).json()

    # Faltando o mês 12, só cabem janelas inteiras antes (fins 5..11) ou depois (fins 18..23).
    assert [w["fim"] for w in windows] == [month(i) for i in [*range(5, 12), *range(18, 24)]]


def test_windows_keep_months_missing_only_in_the_segment(
    engine: Engine, client: TestClient
) -> None:
    store(
        engine,
        *(segment(month(i)) for i in range(12) if i != 5),
        segment(month(5), municipio="Olinda", bairro="Carmo"),
    )
    recorte = {"municipio": "Recife", "bairro": "Boa Viagem"}

    response = client.get(WINDOWS, params={"meses": 12, **recorte})
    assert response.status_code == 200
    assert [(w["inicio"], w["fim"]) for w in response.json()] == [("2024-01", "2024-12")]
    window = response.json()[0]
    assert window["receita_faturada"] == 13200.0
    assert window["kwh_faturado"] == 11000.0
    assert window["n_uc_medio"] == pytest.approx(1100 / 12)
    comparison = compare(client, NO_BASE, ("2024-01", "2024-12"), **recorte)["atual"]
    for field in (
        "receita_faturada",
        "receita_energia",
        "kwh_faturado",
        "n_uc_medio",
        "tarifa_media",
        "tarifa_base_media",
    ):
        assert window[field] == pytest.approx(comparison[field])


def test_windows_respect_the_segment(engine: Engine, client: TestClient) -> None:
    store(
        engine,
        *(segment(month(i)) for i in range(3)),
        *(segment(month(i), classe="B3", bairro="Casa Forte") for i in range(2)),
    )

    all_classes = client.get(WINDOWS, params={"meses": 3}).json()
    only_b3 = client.get(WINDOWS, params={"meses": 3, "classe": "B3"}).json()

    assert len(all_classes) == 1
    assert [(w["inicio"], w["fim"]) for w in only_b3] == [("2024-01", "2024-03")]
    assert only_b3[0]["receita_faturada"] == 2400.0
    assert only_b3[0]["n_uc_medio"] == pytest.approx(200 / 3)


def test_windows_months_out_of_range_is_422(client: TestClient) -> None:
    assert client.get(WINDOWS, params={"meses": 25}).status_code == 422
    assert client.get(WINDOWS, params={"meses": 0}).status_code == 422


def test_matches_receita_comparacao_for_the_same_pair(engine: Engine, client: TestClient) -> None:
    pairs = [("2024-01", "1000.000", "1200.00"), ("2025-01", "1100.000", "1296.00")]
    store(
        engine,
        *(
            segment(c, kwh_faturado=Decimal(kwh), receita_faturada=Decimal(r))
            for c, kwh, r in pairs
        ),
        *(
            FatoFaturamentoMensal(
                cod_uc="0001",
                competencia=c,
                kwh_faturado=Decimal(kwh),
                kwh_leitura=Decimal(kwh),
                origem_kwh="leitura",
                receita_faturada=Decimal(r),
                receita_energia=Decimal("1000.00"),
                tributos=Decimal("200.00"),
                data_vencimento=date(2026, 1, 10),
                status_pagamento="paga",
                receita_bandeira=Decimal("0.00"),
                tipo_leitura="real",
                tipo_medidor="eletronico",
            )
            for c, kwh, r in pairs
        ),
    )
    period = {
        "base_inicio": "2024-01",
        "base_fim": "2024-01",
        "atual_inicio": "2025-01",
        "atual_fim": "2025-01",
    }

    receita = client.get("/receita/comparacao", params=period).json()
    indicadores = client.get(COMPARE, params=period).json()

    for side in ("base", "atual"):
        assert indicadores[side]["receita_faturada"] == receita[side]["receita_faturada"]
        assert indicadores[side]["kwh_faturado"] == receita[side]["kwh_faturado"]


def test_variation_is_null_without_the_current_period(engine: Engine, client: TestClient) -> None:
    store(engine, segment("2025-01"))

    result = compare(client, ("2025-01", "2025-01"), ("2026-01", "2026-01"))

    assert result["atual"]["n_meses"] == 0
    assert result["variacao_pct"]["receita_faturada"] is None


def test_variation_is_null_when_a_period_has_missing_months(
    engine: Engine, client: TestClient
) -> None:
    store(engine, segment("2024-01"), segment("2024-02"), segment("2025-01"))

    result = compare(client, ("2024-01", "2024-02"), ("2025-01", "2025-02"))

    assert result["atual"]["n_meses"] == 1
    assert result["atual"]["receita_faturada"] == 1200.0
    assert result["variacao_pct"]["receita_faturada"] is None


def test_twelve_months_against_twelve_months(engine: Engine, client: TestClient) -> None:
    store(
        engine,
        *(segment(month(i), receita_faturada=Decimal("100.00")) for i in range(12)),
        *(segment(month(i), receita_faturada=Decimal("110.00")) for i in range(12, 24)),
    )

    result = compare(client, (month(0), month(11)), (month(12), month(23)))

    assert result["base"]["receita_faturada"] == 1200.0
    assert result["atual"]["receita_faturada"] == 1320.0
    assert result["variacao_pct"]["receita_faturada"] == pytest.approx(10.0)


@pytest.mark.parametrize(
    ("base", "atual"),
    [
        (("2025-01", "2025-06"), ("2024-01", "2024-06")),
        (("2024-01", "2024-12"), ("2024-12", "2025-11")),
    ],
)
def test_base_must_end_before_the_current_period_starts(
    client: TestClient, base: tuple[str, str], atual: tuple[str, str]
) -> None:
    response = client.get(
        COMPARE,
        params={
            "base_inicio": base[0],
            "base_fim": base[1],
            "atual_inicio": atual[0],
            "atual_fim": atual[1],
        },
    )

    assert response.status_code == 422


def test_monthly_uses_weighted_components_and_global_calendar(
    engine: Engine, client: TestClient
) -> None:
    store(
        engine,
        KpisMensais(
            competencia="2024-01",
            kwh_faturado=0,
            receita_faturada=0,
            receita_energia=0,
            n_chamados=8,
        ),
        segment(
            "2024-01",
            n_uc=100,
            n_faturas=2,
            horas_interrompidas=200,
            n_interrupcoes=300,
            soma_notas=8,
            n_notas=2,
            n_chamados=3,
        ),
        segment(
            "2024-01",
            bairro="Carmo",
            n_uc=300,
            n_faturas=1,
            horas_interrompidas=300,
            n_interrupcoes=100,
            soma_notas=3,
            n_notas=1,
            n_chamados=5,
        ),
        segment("2024-02", municipio="Paulista", bairro="Janga"),
        segment("2024-03", municipio="Paulista", bairro="Janga"),
    )
    response = client.get(
        MONTHLY,
        params={"municipio": "Recife", "classe": "B1", "inicio": "2024-01", "fim": "2024-02"},
    )
    assert response.status_code == 200
    first, empty = response.json()
    assert first["competencia"] == "2024-01"
    assert first["dec"] == pytest.approx(1.25)
    assert first["fec"] == pytest.approx(1.0)
    assert first["satisfacao_media"] == pytest.approx(11 / 3)
    assert first["n_chamados"] == 8
    comparison = compare(
        client,
        NO_BASE,
        ("2024-01", "2024-01"),
        municipio="Recife",
        classe="B1",
    )["atual"]
    for field in (
        "dec",
        "fec",
        "satisfacao_media",
        "n_chamados",
        "kwh_faturado",
        "receita_faturada",
        "receita_energia",
    ):
        assert float(first[field]) == pytest.approx(float(comparison[field]))
    assert empty["competencia"] == "2024-02"
    # Mês sem linha no recorte: nulo, nunca zero (DEC-030).
    for field in ("kwh_faturado", "receita_faturada", "receita_energia", "n_chamados"):
        assert empty[field] is None
    assert empty["dec"] is None
    assert empty["fec"] is None
    assert empty["satisfacao_media"] is None


def test_monthly_keeps_real_zeros_and_nulls_months_without_invoice(
    engine: Engine, client: TestClient
) -> None:
    store(
        engine,
        KpisMensais(
            competencia="2024-01",
            kwh_faturado=0,
            receita_faturada=0,
            receita_energia=0,
            n_chamados=None,
        ),
        KpisMensais(
            competencia="2024-02",
            kwh_faturado=0,
            receita_faturada=0,
            receita_energia=0,
            n_chamados=2,
        ),
        # Fatura emitida com energia e receita zeradas: zero é um fato do recorte.
        segment(
            "2024-01",
            n_uc=1,
            n_faturas=1,
            kwh_faturado=Decimal("0.000"),
            receita_faturada=Decimal("0.00"),
            receita_energia=Decimal("0.00"),
        ),
        # Só chamado no mês, sem fatura: as somas de faturamento são nulas (DEC-030),
        # e o chamado continua contado.
        segment(
            "2024-02",
            n_uc=0,
            n_faturas=0,
            n_chamados=2,
            kwh_faturado=Decimal("0.000"),
            receita_faturada=Decimal("0.00"),
            receita_energia=Decimal("0.00"),
        ),
    )

    com_fatura, sem_fatura = client.get(MONTHLY).json()

    assert com_fatura["competencia"] == "2024-01"
    for field in ("kwh_faturado", "receita_faturada", "receita_energia"):
        assert com_fatura[field] == 0
    assert com_fatura["n_chamados"] is None
    assert sem_fatura["competencia"] == "2024-02"
    for field in ("kwh_faturado", "receita_faturada", "receita_energia"):
        assert sem_fatura[field] is None
    assert sem_fatura["n_chamados"] == 2


def test_monthly_validates_filters_and_handles_empty_calendar(
    engine: Engine, client: TestClient
) -> None:
    store(engine)
    assert client.get(MONTHLY).json() == []
    for params in (
        {"bairro": "Janga"},
        {"inicio": "2024-13"},
        {"inicio": "2024-02", "fim": "2024-01"},
        {"classe": "invalida"},
    ):
        assert client.get(MONTHLY, params=params).status_code == 422
