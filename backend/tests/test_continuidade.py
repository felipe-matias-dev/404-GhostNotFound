from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from venergy_api.amostra import write_sample
from venergy_api.carga import load_gold
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


def store_rows(engine: Engine, rows: list[tuple[str, str, int, int, float]]) -> None:
    """Linhas (alimentador, competência, n_uc, n_interrupcoes, horas) de teste."""
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all(
            ContinuidadeAlimentadorMensal(
                cod_alimentador=alimentador,
                competencia=competencia,
                dec=0.0,
                fec=0.0,
                n_uc=n_uc,
                n_interrupcoes=n_interrupcoes,
                horas_interrompidas=horas,
            )
            for alimentador, competencia, n_uc, n_interrupcoes, horas in rows
        )


def ranking(client: TestClient, **params: str) -> dict:
    response = client.get("/continuidade/alimentadores/ranking", params=params)
    assert response.status_code == 200
    return response.json()


TWO_FEEDERS = [
    ("AL-A", "2025-01", 100, 20, 50.0),
    ("AL-A", "2025-02", 100, 10, 30.0),
    ("AL-A", "2025-03", 100, 10, 20.0),
    ("AL-B", "2025-01", 100, 0, 0.0),
    ("AL-B", "2025-02", 300, 120, 300.0),
    ("AL-B", "2025-03", 0, 0, 0.0),
]


def test_ranking_divides_by_the_monthly_average_of_units_not_by_the_average_of_indexes(
    engine: Engine, client: TestClient
) -> None:
    store_rows(engine, TWO_FEEDERS)

    result = ranking(client, inicio="2025-01", fim="2025-02")

    # AL-A: 80 h ÷ (200 UC ÷ 2 meses) = 0,8 e 30 interrupções ÷ 100 = 0,3.
    # AL-B: 300 h ÷ (400 UC ÷ 2 meses) = 1,5 e 120 ÷ 200 = 0,6. A média dos DEC mensais do
    # AL-B daria (0 + 1) ÷ 2 = 0,5, e ele ficaria atrás do AL-A.
    assert result["n_meses"] == 2
    assert [
        (a["cod_alimentador"], a["dec"], a["fec"], a["n_uc_medio"], a["horas_interrompidas"])
        for a in result["alimentadores"]
    ] == [("AL-B", 1.5, 0.6, 200.0, 300.0), ("AL-A", 0.8, 0.3, 100.0, 80.0)]


def test_ranking_by_fec_reorders_when_the_indexes_disagree(
    engine: Engine, client: TestClient
) -> None:
    store_rows(
        engine,
        [
            ("AL-LONGO", "2025-01", 100, 10, 90.0),
            ("AL-FREQUENTE", "2025-01", 100, 50, 20.0),
        ],
    )

    by_dec = ranking(client, inicio="2025-01", fim="2025-01")
    by_fec = ranking(client, inicio="2025-01", fim="2025-01", criterio="fec")

    assert [a["cod_alimentador"] for a in by_dec["alimentadores"]] == ["AL-LONGO", "AL-FREQUENTE"]
    assert [a["cod_alimentador"] for a in by_fec["alimentadores"]] == ["AL-FREQUENTE", "AL-LONGO"]
    assert by_fec["criterio"] == "fec"


def test_ranking_counts_only_months_that_exist_in_the_data(
    engine: Engine, client: TestClient
) -> None:
    store_rows(engine, TWO_FEEDERS)

    within = ranking(client, inicio="2025-01", fim="2025-03")
    beyond = ranking(client, inicio="2025-01", fim="2025-12")

    assert beyond["n_meses"] == 3
    assert beyond["alimentadores"] == within["alimentadores"]


def test_ranking_counts_a_feeder_missing_in_a_month_as_zero_units(
    engine: Engine, client: TestClient
) -> None:
    store_rows(engine, [("AL-A", "2025-01", 100, 0, 0.0), ("AL-B", "2025-02", 100, 0, 50.0)])

    result = ranking(client, inicio="2025-01", fim="2025-02")

    # AL-B só tem o segundo mês: 50 h ÷ (100 UC ÷ 2 meses) = 1,0.
    assert result["alimentadores"][0]["cod_alimentador"] == "AL-B"
    assert result["alimentadores"][0]["dec"] == 1.0


def test_ranking_leaves_the_index_empty_when_no_unit_is_served(
    engine: Engine, client: TestClient
) -> None:
    store_rows(engine, TWO_FEEDERS)

    result = ranking(client, inicio="2025-03", fim="2025-03")

    assert result["alimentadores"][-1]["cod_alimentador"] == "AL-B"
    assert result["alimentadores"][-1]["dec"] is None


def test_ranking_without_data_in_the_period_is_empty(engine: Engine, client: TestClient) -> None:
    store_rows(engine, TWO_FEEDERS)

    assert ranking(client, inicio="2030-01", fim="2030-02") == {
        "inicio": "2030-01",
        "fim": "2030-02",
        "criterio": "dec",
        "n_meses": 0,
        "alimentadores": [],
    }


def test_ranking_requires_a_valid_period(engine: Engine, client: TestClient) -> None:
    store_rows(engine, TWO_FEEDERS)
    url = "/continuidade/alimentadores/ranking"

    assert client.get(url).status_code == 422
    assert client.get(url, params={"inicio": "2025-01"}).status_code == 422
    assert client.get(url, params={"inicio": "2025-03", "fim": "2025-01"}).status_code == 422


def test_ranking_of_one_month_matches_the_gold_and_puts_the_worst_feeder_first(
    tmp_path: Path, engine: Engine, client: TestClient
) -> None:
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)

    result = ranking(client, inicio="2025-06", fim="2025-06")
    gold = client.get(
        "/continuidade/alimentadores/mensal", params={"inicio": "2025-06", "fim": "2025-06"}
    ).json()

    assert result["alimentadores"][0]["cod_alimentador"] == "AL-06"
    for alimentador in result["alimentadores"]:
        linha = next(g for g in gold if g["cod_alimentador"] == alimentador["cod_alimentador"])
        assert alimentador["dec"] == pytest.approx(linha["dec"])
        assert alimentador["fec"] == pytest.approx(linha["fec"])
