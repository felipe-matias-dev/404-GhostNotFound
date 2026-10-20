import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import Engine, update
from sqlalchemy.orm import Session

from venergy_api.database import Base
from venergy_api.models import DimUc, OrdemInspecao
from venergy_api.ordens import StatusOrdem
from venergy_api.schemas import MAX_ORDENS_POR_PEDIDO

UC_BASE = {
    "municipio": "Recife",
    "bairro": "Boa Viagem",
    "classe": "B1",
    "cod_alimentador": "AL-01",
    "possui_gd": False,
    "consumo_medio_kwh_12m": 150.0,
}


@pytest.fixture(autouse=True)
def stored_ucs(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all([DimUc(cod_uc=cod, **UC_BASE) for cod in ("0001", "0002", "0003")])


def create_orders(client: TestClient, *cod_ucs: str) -> list[dict]:
    response = client.post("/ordens-inspecao", json={"cod_ucs": list(cod_ucs)})
    assert response.status_code == 201, response.text
    return response.json()


def set_status(engine: Engine, ordem_id: int, novo: StatusOrdem) -> None:
    with Session(engine) as session, session.begin():
        session.execute(
            update(OrdemInspecao).where(OrdemInspecao.id == ordem_id).values(status=novo)
        )


def test_creates_one_generated_order_per_uc(client: TestClient) -> None:
    ordens = create_orders(client, "0001", "0002")

    assert [(o["cod_uc"], o["status"], o["resultado"]) for o in ordens] == [
        ("0001", "GERADA", None),
        ("0002", "GERADA", None),
    ]


def test_new_order_starts_its_history_with_a_generated_event(client: TestClient) -> None:
    [ordem] = create_orders(client, "0001")

    detalhe = client.get(f"/ordens-inspecao/{ordem['id']}").json()

    assert [(e["status_anterior"], e["status_novo"]) for e in detalhe["eventos"]] == [
        (None, "GERADA")
    ]


def test_unknown_uc_returns_404_and_creates_no_order(client: TestClient) -> None:
    response = client.post("/ordens-inspecao", json={"cod_ucs": ["0001", "9999"]})

    assert response.status_code == 404
    assert response.json() == {"detail": "Unidades consumidoras não encontradas: 9999"}
    assert client.get("/ordens-inspecao").json() == []


def test_uc_with_an_active_order_returns_409_and_creates_nothing(client: TestClient) -> None:
    create_orders(client, "0001")

    response = client.post("/ordens-inspecao", json={"cod_ucs": ["0002", "0001"]})

    assert response.status_code == 409
    assert response.json() == {"detail": "Já existe ordem ativa para as UCs: 0001"}
    assert [o["cod_uc"] for o in client.get("/ordens-inspecao").json()] == ["0001"]


def test_uc_whose_order_was_cancelled_can_get_a_new_one(client: TestClient, engine: Engine) -> None:
    [ordem] = create_orders(client, "0001")
    set_status(engine, ordem["id"], StatusOrdem.CANCELADA)

    create_orders(client, "0001")


@pytest.mark.parametrize(
    "cod_ucs",
    [
        pytest.param([], id="lista vazia"),
        pytest.param(["0001", "0001"], id="UC repetida"),
        pytest.param(["  "], id="código em branco"),
        pytest.param(["0001"] * (MAX_ORDENS_POR_PEDIDO + 1), id="acima do teto"),
    ],
)
def test_rejects_invalid_requests_with_422(client: TestClient, cod_ucs: list[str]) -> None:
    response = client.post("/ordens-inspecao", json={"cod_ucs": cod_ucs})

    assert response.status_code == 422


def test_lists_most_recent_orders_first(client: TestClient) -> None:
    create_orders(client, "0001")
    create_orders(client, "0002")

    ordens = client.get("/ordens-inspecao").json()

    assert [o["cod_uc"] for o in ordens] == ["0002", "0001"]


def test_filters_orders_by_status(client: TestClient, engine: Engine) -> None:
    primeira, _ = create_orders(client, "0001", "0002")
    set_status(engine, primeira["id"], StatusOrdem.EM_CAMPO)

    em_campo = client.get("/ordens-inspecao", params={"status": "EM_CAMPO"}).json()

    assert [o["cod_uc"] for o in em_campo] == ["0001"]


def test_unknown_status_filter_returns_422(client: TestClient) -> None:
    response = client.get("/ordens-inspecao", params={"status": "PERDIDA"})

    assert response.status_code == 422


def test_unknown_order_returns_404(client: TestClient) -> None:
    response = client.get("/ordens-inspecao/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Ordem de inspeção 999 não encontrada"}


def change(client: TestClient, ordem_id: int, **mudanca: str) -> Response:
    return client.patch(f"/ordens-inspecao/{ordem_id}", json=mudanca)


def test_full_flow_records_the_result_and_every_step_in_the_history(
    client: TestClient,
) -> None:
    [ordem] = create_orders(client, "0001")

    assert change(client, ordem["id"], status="EM_CAMPO").status_code == 200
    response = change(
        client,
        ordem["id"],
        status="CONCLUIDA",
        resultado="IRREGULAR_CONFIRMADA",
        observacao="Desvio antes do medidor",
    )

    assert response.status_code == 200
    concluida = response.json()
    assert concluida["status"] == "CONCLUIDA"
    assert concluida["resultado"] == "IRREGULAR_CONFIRMADA"
    assert concluida["observacao"] == "Desvio antes do medidor"
    assert [(e["status_anterior"], e["status_novo"]) for e in concluida["eventos"]] == [
        (None, "GERADA"),
        ("GERADA", "EM_CAMPO"),
        ("EM_CAMPO", "CONCLUIDA"),
    ]


def test_concluding_without_a_result_returns_422_and_keeps_the_order(
    client: TestClient,
) -> None:
    [ordem] = create_orders(client, "0001")
    change(client, ordem["id"], status="EM_CAMPO")

    response = change(client, ordem["id"], status="CONCLUIDA")

    assert response.status_code == 422
    assert client.get(f"/ordens-inspecao/{ordem['id']}").json()["status"] == "EM_CAMPO"


def test_result_outside_conclusion_returns_422(client: TestClient) -> None:
    [ordem] = create_orders(client, "0001")

    response = change(client, ordem["id"], status="EM_CAMPO", resultado="REGULAR")

    assert response.status_code == 422


def test_skipping_the_field_step_returns_409(client: TestClient) -> None:
    [ordem] = create_orders(client, "0001")

    response = change(client, ordem["id"], status="CONCLUIDA", resultado="REGULAR")

    assert response.status_code == 409
    assert response.json() == {"detail": "Não é possível mudar uma ordem de GERADA para CONCLUIDA"}


def test_cancelled_order_cannot_be_reopened(client: TestClient) -> None:
    [ordem] = create_orders(client, "0001")
    change(client, ordem["id"], status="CANCELADA")

    response = change(client, ordem["id"], status="EM_CAMPO")

    assert response.status_code == 409
    assert client.get(f"/ordens-inspecao/{ordem['id']}").json()["status"] == "CANCELADA"


def test_cancelling_keeps_the_reason_and_frees_the_uc_for_a_new_order(
    client: TestClient,
) -> None:
    [ordem] = create_orders(client, "0001")

    response = change(client, ordem["id"], status="CANCELADA", observacao="Gerada por engano")

    assert response.status_code == 200
    assert response.json()["eventos"][-1]["observacao"] == "Gerada por engano"
    create_orders(client, "0001")


def test_changing_an_unknown_order_returns_404(client: TestClient) -> None:
    response = change(client, 999, status="EM_CAMPO")

    assert response.status_code == 404
