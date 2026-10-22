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
        "dec": 1.2,
        "fec": 0.8,
        "n_chamados": 14,
        "satisfacao_media": 4.1,
    },
    "2025-01": {
        "competencia": "2025-01",
        "kwh_faturado": 1250.0,
        "receita_faturada": 1010.4,
        "dec": None,
        "fec": None,
        "n_chamados": None,
        "satisfacao_media": None,
    },
    "2024-12": {
        "competencia": "2024-12",
        "kwh_faturado": 1302.125,
        "receita_faturada": 1050.0,
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
