from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from venergy_api.amostra import write_sample
from venergy_api.carga import load_gold
from venergy_api.database import Base
from venergy_api.models import DimUc, FatoFaturamentoMensal, KpisMensais

YEARS = {
    "base_inicio": "2024-01",
    "base_fim": "2024-12",
    "atual_inicio": "2025-01",
    "atual_fim": "2025-12",
}

UCS = [
    ("0001", "Recife", "Boa Viagem", "B1"),
    ("0002", "Recife", "Casa Forte", "B3"),
    ("0003", "Olinda", "Carmo", "B1"),
]
REGISTRY_CLASS = {"B1": "Residencial", "B3": "Comercial"}

# (cod_uc, competencia, kwh_faturado, receita_faturada). A UC 0003 foi ligada em 2025.
BILLING = [
    ("0001", "2024-01", "100.000", "80.00"),
    ("0001", "2025-01", "90.000", "81.00"),
    ("0002", "2024-01", "200.000", "150.00"),
    ("0002", "2025-01", "210.000", "168.00"),
    ("0003", "2025-01", "50.000", "40.00"),
    ("0001", "2023-12", "999.000", "999.00"),
]


def store_billing(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all(
            DimUc(
                cod_uc=cod_uc,
                municipio=municipio,
                bairro=bairro,
                classe=classe,
                classe_cadastro=REGISTRY_CLASS[classe],
                cod_alimentador="AL-01",
                possui_gd=False,
                consumo_medio_kwh_12m=Decimal("100"),
            )
            for cod_uc, municipio, bairro, classe in UCS
        )
        session.add_all(
            FatoFaturamentoMensal(
                cod_uc=cod_uc,
                competencia=competencia,
                kwh_faturado=Decimal(kwh),
                receita_faturada=Decimal(receita),
            )
            for cod_uc, competencia, kwh, receita in BILLING
        )


def compare(client: TestClient, **segment: str) -> dict:
    response = client.get("/receita/comparacao", params={**YEARS, **segment})
    assert response.status_code == 200
    return response.json()


def test_compares_one_segment_between_the_two_periods(engine: Engine, client: TestClient) -> None:
    store_billing(engine)

    assert compare(client, municipio="Recife", bairro="Casa Forte") == {
        "base": {
            "inicio": "2024-01",
            "fim": "2024-12",
            "kwh_faturado": 200.0,
            "receita_faturada": 150.0,
        },
        "atual": {
            "inicio": "2025-01",
            "fim": "2025-12",
            "kwh_faturado": 210.0,
            "receita_faturada": 168.0,
        },
        "variacao_kwh": 10.0,
        "variacao_receita": 18.0,
        "variacao_kwh_pct": 5.0,
        "variacao_receita_pct": 12.0,
    }


@pytest.mark.parametrize(
    ("segment", "base", "atual"),
    [
        ({}, (300.0, 230.0), (350.0, 289.0)),
        ({"municipio": "Recife"}, (300.0, 230.0), (300.0, 249.0)),
        ({"classe": "B1"}, (100.0, 80.0), (140.0, 121.0)),
        ({"municipio": "Recife", "classe": "B1"}, (100.0, 80.0), (90.0, 81.0)),
    ],
)
def test_sums_only_the_months_and_units_of_the_segment(
    engine: Engine,
    client: TestClient,
    segment: dict[str, str],
    base: tuple[float, float],
    atual: tuple[float, float],
) -> None:
    store_billing(engine)

    result = compare(client, **segment)

    assert (result["base"]["kwh_faturado"], result["base"]["receita_faturada"]) == base
    assert (result["atual"]["kwh_faturado"], result["atual"]["receita_faturada"]) == atual


def test_percent_change_is_empty_when_the_base_is_zero(engine: Engine, client: TestClient) -> None:
    store_billing(engine)

    result = compare(client, municipio="Olinda")

    assert result["variacao_receita"] == 40.0
    assert result["variacao_kwh_pct"] is None
    assert result["variacao_receita_pct"] is None


def test_returns_zero_totals_for_a_segment_without_billing(
    engine: Engine, client: TestClient
) -> None:
    store_billing(engine)

    result = compare(client, municipio="Paulista")

    assert result["base"]["receita_faturada"] == 0.0
    assert result["atual"]["receita_faturada"] == 0.0


@pytest.mark.parametrize(
    ("query", "message"),
    [
        ({**YEARS, "bairro": "Casa Forte"}, "Informe o município junto com o bairro"),
        (
            {**YEARS, "base_inicio": "2025-01"},
            "O início do período (2025-01) é depois do fim (2024-12)",
        ),
        ({**YEARS, "classe": "X9"}, "B1"),
    ],
)
def test_rejects_an_invalid_filter(
    engine: Engine, client: TestClient, query: dict[str, str], message: str
) -> None:
    response = client.get("/receita/comparacao", params=query)

    assert response.status_code == 422
    assert message in response.text


def test_requires_both_periods(engine: Engine, client: TestClient) -> None:
    response = client.get("/receita/comparacao", params={"base_inicio": "2024-01"})

    assert response.status_code == 422


def test_total_without_filter_matches_the_monthly_kpis(
    tmp_path: Path, engine: Engine, client: TestClient
) -> None:
    # A conferência que vale para a Gold real: a comparação da tela de Receita, somada da
    # fato pela API, tem que bater centavo por centavo com o painel da diretoria.
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)

    result = compare(client)

    with Session(engine) as session:
        for period in ("base", "atual"):
            no_periodo = KpisMensais.competencia.between(
                YEARS[f"{period}_inicio"], YEARS[f"{period}_fim"]
            )
            kwh, receita = session.execute(
                select(
                    func.sum(KpisMensais.kwh_faturado), func.sum(KpisMensais.receita_faturada)
                ).where(no_periodo)
            ).one()
            assert result[period]["kwh_faturado"] == float(kwh)
            assert result[period]["receita_faturada"] == float(receita)
