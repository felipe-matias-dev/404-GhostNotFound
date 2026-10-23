import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from venergy_api.database import Base
from venergy_api.models import KpisMensais

KPIS_BY_MONTH = {
    "2025-02": {
        "competencia": "2025-02",
        "kwh_faturado": 1180.5,
        "receita_faturada": 980.25,
        "receita_energia": 784.2,
        "dec": 1.2,
        "fec": 0.8,
        "n_chamados": 14,
        "satisfacao_media": 4.1,
    },
    "2025-01": {
        "competencia": "2025-01",
        "kwh_faturado": 1250.0,
        "receita_faturada": 1010.4,
        "receita_energia": 808.32,
        "dec": None,
        "fec": None,
        "n_chamados": None,
        "satisfacao_media": None,
    },
    "2024-12": {
        "competencia": "2024-12",
        "kwh_faturado": 1302.125,
        "receita_faturada": 1050.0,
        "receita_energia": 840.0,
        "dec": 2.5,
        "fec": 1.1,
        "n_chamados": 20,
        "satisfacao_media": 3.9,
    },
}


@pytest.fixture(autouse=True)
def tables(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def store_kpis(engine: Engine) -> None:
    with Session(engine) as session, session.begin():
        session.add_all(KpisMensais(**row) for row in KPIS_BY_MONTH.values())


def test_returns_the_monthly_kpis_from_oldest_to_newest(engine: Engine, client: TestClient) -> None:
    store_kpis(engine)

    response = client.get("/receita/mensal")

    assert response.status_code == 200
    assert response.json() == [KPIS_BY_MONTH[mes] for mes in ("2024-12", "2025-01", "2025-02")]


def test_returns_an_empty_list_before_the_gold_is_loaded(client: TestClient) -> None:
    response = client.get("/receita/mensal")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    ("query", "expected_months"),
    [
        ({"inicio": "2024-12", "fim": "2025-01"}, ["2024-12", "2025-01"]),
        ({"inicio": "2025-01"}, ["2025-01", "2025-02"]),
        ({"fim": "2024-12"}, ["2024-12"]),
        ({"inicio": "2025-02", "fim": "2025-02"}, ["2025-02"]),
    ],
)
def test_filters_the_period_including_both_ends(
    engine: Engine, client: TestClient, query: dict[str, str], expected_months: list[str]
) -> None:
    store_kpis(engine)

    response = client.get("/receita/mensal", params=query)

    assert response.status_code == 200
    assert [row["competencia"] for row in response.json()] == expected_months


@pytest.mark.parametrize("month", ["2025-13", "2025-1", "jan/2025"])
def test_rejects_a_month_outside_the_yyyy_mm_format(client: TestClient, month: str) -> None:
    response = client.get("/receita/mensal", params={"inicio": month})

    assert response.status_code == 422


def test_rejects_a_period_that_starts_after_it_ends(client: TestClient) -> None:
    response = client.get("/receita/mensal", params={"inicio": "2025-02", "fim": "2024-12"})

    assert response.status_code == 422
    assert "O início do período (2025-02) é depois do fim (2024-12)" in response.text
