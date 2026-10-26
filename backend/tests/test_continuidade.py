from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from venergy_api.database import Base
from venergy_api.models import ContinuidadeAlimentadorMensal

SERIES = [
    ("AL-B", "2025-02", 2.0, 1.0, 100, 100, 200.0),
    ("AL-A", "2025-01", 1.0, 0.5, 100, 50, 100.0),
    ("AL-A", "2025-02", 3.0, 1.5, 100, 150, 300.0),
    ("AL-A", "2025-03", 9.0, 9.0, 100, 900, 900.0),
]


def store_series(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all(
            ContinuidadeAlimentadorMensal(
                cod_alimentador=alimentador,
                competencia=competencia,
                dec=dec,
                fec=fec,
                n_uc=n_uc,
                n_interrupcoes=n_interrupcoes,
                horas_interrompidas=horas,
            )
            for alimentador, competencia, dec, fec, n_uc, n_interrupcoes, horas in SERIES
        )


def test_returns_the_gold_values_ordered_by_feeder_and_month(
    engine: Engine, client: TestClient
) -> None:
    store_series(engine)

    response = client.get("/continuidade/alimentadores/mensal", params={"fim": "2025-02"})

    assert response.status_code == 200
    assert [(r["cod_alimentador"], r["competencia"], r["dec"]) for r in response.json()] == [
        ("AL-A", "2025-01", 1.0),
        ("AL-A", "2025-02", 3.0),
        ("AL-B", "2025-02", 2.0),
    ]


def test_filters_the_requested_feeders(engine: Engine, client: TestClient) -> None:
    store_series(engine)

    response = client.get("/continuidade/alimentadores/mensal", params={"cod_alimentador": "AL-B"})

    assert [r["cod_alimentador"] for r in response.json()] == ["AL-B"]


def test_rejects_a_start_after_the_end(engine: Engine, client: TestClient) -> None:
    store_series(engine)

    response = client.get(
        "/continuidade/alimentadores/mensal", params={"inicio": "2025-03", "fim": "2025-01"}
    )

    assert response.status_code == 422
