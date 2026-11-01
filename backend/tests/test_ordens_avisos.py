import json
from collections import Counter
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from venergy_api.avisos_ordens import CANAL, MAX_IDS_NO_AVISO, avisar_mudanca_de_ordem
from venergy_api.database import Base
from venergy_api.models import DimUc

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

ESPERA_SEM_AVISO = 0.3


class Ouvinte:
    """Conexão própria em LISTEN: vê só o que o Postgres entrega, ou seja, o que foi commitado."""

    def __init__(self, conexao: psycopg.Connection) -> None:
        self._conexao = conexao

    def avisos(self) -> list[dict]:
        return [json.loads(n.payload) for n in self._conexao.notifies(timeout=ESPERA_SEM_AVISO)]


@pytest.fixture(autouse=True)
def stored_ucs(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all([DimUc(cod_uc=cod, **UC_BASE) for cod in ("0001", "0002", "0003")])


@pytest.fixture
def ouvinte(engine: Engine, stored_ucs: None) -> Iterator[Ouvinte]:
    url = engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    with psycopg.connect(url, autocommit=True) as conexao:
        conexao.execute(f"LISTEN {CANAL}")
        yield Ouvinte(conexao)


def create_orders(client: TestClient, *cod_ucs: str) -> list[dict]:
    response = client.post("/ordens-inspecao", json={"cod_ucs": list(cod_ucs)})
    assert response.status_code == 201, response.text
    return response.json()


def test_valid_change_sends_one_notice_with_the_order_id(
    client: TestClient, ouvinte: Ouvinte
) -> None:
    [ordem] = create_orders(client, "0001")
    ouvinte.avisos()

    response = client.patch(f"/ordens-inspecao/{ordem['id']}", json={"status": "EM_CAMPO"})

    assert response.status_code == 200
    assert ouvinte.avisos() == [{"ordem_ids": [ordem["id"]]}]


def test_rejected_change_sends_no_notice(client: TestClient, ouvinte: Ouvinte) -> None:
    [ordem] = create_orders(client, "0001")
    ouvinte.avisos()

    response = client.patch(
        f"/ordens-inspecao/{ordem['id']}", json={"status": "CONCLUIDA", "resultado": "REGULAR"}
    )

    assert response.status_code == 409
    assert ouvinte.avisos() == []


def test_batch_creation_sends_a_single_notice_with_every_id(
    client: TestClient, ouvinte: Ouvinte
) -> None:
    ordens = create_orders(client, "0001", "0002", "0003")

    assert ouvinte.avisos() == [{"ordem_ids": [o["id"] for o in ordens]}]


def test_creation_refused_for_an_active_order_sends_no_notice(
    client: TestClient, ouvinte: Ouvinte
) -> None:
    create_orders(client, "0001")
    ouvinte.avisos()

    response = client.post("/ordens-inspecao", json={"cod_ucs": ["0001", "0002"]})

    assert response.status_code == 409
    assert ouvinte.avisos() == []


def test_creation_refused_for_an_unknown_uc_sends_no_notice(
    client: TestClient, ouvinte: Ouvinte
) -> None:
    response = client.post("/ordens-inspecao", json={"cod_ucs": ["9999"]})

    assert response.status_code == 404
    assert ouvinte.avisos() == []


def test_notice_is_only_delivered_when_the_transaction_commits(
    engine: Engine, ouvinte: Ouvinte
) -> None:
    with Session(engine) as session:
        avisar_mudanca_de_ordem(session, [7])
        session.rollback()

    assert ouvinte.avisos() == []


def test_batch_too_large_for_the_notice_goes_without_the_ids(
    engine: Engine, ouvinte: Ouvinte
) -> None:
    with Session(engine) as session:
        avisar_mudanca_de_ordem(session, list(range(MAX_IDS_NO_AVISO + 1)))
        session.commit()

    assert ouvinte.avisos() == [{"ordem_ids": None}]


def test_simultaneous_changes_to_the_same_order_let_one_through_and_notify_once(
    client: TestClient, ouvinte: Ouvinte
) -> None:
    [ordem] = create_orders(client, "0001")
    ouvinte.avisos()

    def enviar_para_o_campo(_: int) -> int:
        return client.patch(
            f"/ordens-inspecao/{ordem['id']}", json={"status": "EM_CAMPO"}
        ).status_code

    with ThreadPoolExecutor(max_workers=20) as pool:
        resultados = Counter(pool.map(enviar_para_o_campo, range(20)))

    assert resultados == {200: 1, 409: 19}
    assert ouvinte.avisos() == [{"ordem_ids": [ordem["id"]]}]
