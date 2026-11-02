from collections.abc import Callable
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from venergy_api.database import Base
from venergy_api.models import DimUc
from venergy_api.ordens import SEGUNDOS_POR_DIA

UC_BASE = {
    "municipio": "Recife",
    "bairro": "Boa Viagem",
    "classe": "B1",
    "classe_cadastro": "Residencial",
    "cod_alimentador": "AL-01",
    "possui_gd": False,
    "consumo_medio_kwh_12m": 150.0,
    "data_ligacao": date(2018, 6, 1),
}

# Folga para o tempo que o próprio teste leva entre gravar o evento e ler a ordem.
TOLERANCIA_SEGUNDOS = 30


@pytest.fixture(autouse=True)
def stored_ucs(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all([DimUc(cod_uc=cod, **UC_BASE) for cod in ("0001", "0002")])


def create_order(client: TestClient, cod_uc: str = "0001") -> dict:
    response = client.post("/ordens-inspecao", json={"cod_ucs": [cod_uc]})
    assert response.status_code == 201, response.text
    return response.json()[0]


def change(client: TestClient, ordem_id: int, **mudanca: str) -> dict:
    response = client.patch(f"/ordens-inspecao/{ordem_id}", json=mudanca)
    assert response.status_code == 200, response.text
    return response.json()


def move_last_event_back(engine: Engine, ordem_id: int, *, seconds: int) -> None:
    """Põe a entrada da OI no status atual `seconds` atrás, sem esperar o tempo passar."""
    with Session(engine) as session, session.begin():
        session.execute(
            text(
                "UPDATE app.ordem_evento SET ocorrido_em = now() - make_interval(secs => :s) "
                "WHERE id = (SELECT max(id) FROM app.ordem_evento WHERE ordem_id = :o)"
            ),
            {"s": seconds, "o": ordem_id},
        )


def test_new_order_has_just_entered_its_status(client: TestClient) -> None:
    ordem = create_order(client)

    assert 0 <= ordem["segundos_no_status"] < TOLERANCIA_SEGUNDOS
    assert ordem["no_status_desde"] is not None
    assert ordem["atrasada"] is False


def test_time_counts_from_the_last_event_and_not_from_the_creation(
    client: TestClient, engine: Engine
) -> None:
    ordem = create_order(client)
    with Session(engine) as session, session.begin():
        session.execute(text("UPDATE app.ordem_evento SET ocorrido_em = now() - interval '3 days'"))
    ordem = change(client, ordem["id"], status="EM_CAMPO")
    move_last_event_back(engine, ordem["id"], seconds=3600)

    detalhe = client.get(f"/ordens-inspecao/{ordem['id']}").json()

    assert abs(detalhe["segundos_no_status"] - 3600) < TOLERANCIA_SEGUNDOS


def test_changing_the_status_restarts_the_counter(client: TestClient, engine: Engine) -> None:
    ordem = create_order(client)
    move_last_event_back(engine, ordem["id"], seconds=2 * SEGUNDOS_POR_DIA)

    depois = change(client, ordem["id"], status="EM_CAMPO")

    assert 0 <= depois["segundos_no_status"] < TOLERANCIA_SEGUNDOS


def test_going_back_to_generated_restarts_the_counter(client: TestClient, engine: Engine) -> None:
    ordem = create_order(client)
    change(client, ordem["id"], status="EM_CAMPO")
    move_last_event_back(engine, ordem["id"], seconds=2 * SEGUNDOS_POR_DIA)

    depois = change(client, ordem["id"], status="GERADA")

    assert 0 <= depois["segundos_no_status"] < TOLERANCIA_SEGUNDOS


def test_order_without_events_counts_from_its_creation(client: TestClient, engine: Engine) -> None:
    ordem = create_order(client)
    with Session(engine) as session, session.begin():
        session.execute(text("DELETE FROM app.ordem_evento"))
        session.execute(text("UPDATE app.ordem_inspecao SET criada_em = now() - interval '1 hour'"))

    detalhe = client.get(f"/ordens-inspecao/{ordem['id']}").json()

    assert abs(detalhe["segundos_no_status"] - 3600) < TOLERANCIA_SEGUNDOS


@pytest.mark.parametrize(
    ("status_final", "dias", "atrasada"),
    [
        ("GERADA", 4, False),
        ("GERADA", 6, True),
        ("EM_CAMPO", 6, False),
        ("EM_CAMPO", 11, True),
    ],
)
def test_marks_as_late_by_the_limit_of_the_status(
    client: TestClient, engine: Engine, status_final: str, dias: int, atrasada: bool
) -> None:
    ordem = create_order(client)
    if status_final == "EM_CAMPO":
        change(client, ordem["id"], status="EM_CAMPO")
    move_last_event_back(engine, ordem["id"], seconds=dias * SEGUNDOS_POR_DIA)

    listada = next(o for o in client.get("/ordens-inspecao").json() if o["id"] == ordem["id"])
    detalhe = client.get(f"/ordens-inspecao/{ordem['id']}").json()

    assert listada["atrasada"] is atrasada
    assert detalhe["atrasada"] is atrasada


@pytest.mark.parametrize(
    ("mudanca", "resultado_esperado"),
    [
        ({"status": "CANCELADA", "observacao": "Imóvel demolido"}, None),
        ({"status": "CONCLUIDA", "resultado": "REGULAR"}, "REGULAR"),
    ],
)
def test_finished_order_is_never_late(
    client: TestClient,
    engine: Engine,
    mudanca: dict[str, str],
    resultado_esperado: str | None,
) -> None:
    ordem = create_order(client)
    change(client, ordem["id"], status="EM_CAMPO")
    finalizada = change(client, ordem["id"], **mudanca)
    move_last_event_back(engine, ordem["id"], seconds=400 * SEGUNDOS_POR_DIA)

    detalhe = client.get(f"/ordens-inspecao/{finalizada['id']}").json()

    assert detalhe["resultado"] == resultado_esperado
    assert detalhe["atrasada"] is False
    assert detalhe["segundos_no_status"] > 399 * SEGUNDOS_POR_DIA


def test_limits_come_from_the_settings(
    engine: Engine, client_for: Callable[..., TestClient]
) -> None:
    api = client_for(engine, ordem_atraso_gerada_dias=1, ordem_atraso_em_campo_dias=2)
    ordem = create_order(api)
    move_last_event_back(engine, ordem["id"], seconds=2 * SEGUNDOS_POR_DIA)

    assert api.get(f"/ordens-inspecao/{ordem['id']}").json()["atrasada"] is True


def test_patch_response_already_carries_the_new_time(client: TestClient) -> None:
    ordem = create_order(client)

    depois = change(client, ordem["id"], status="EM_CAMPO")

    assert depois["status"] == "EM_CAMPO"
    assert {"no_status_desde", "segundos_no_status", "atrasada"} <= depois.keys()
