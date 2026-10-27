from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from venergy_api.amostra import SAMPLE_FILA, write_sample
from venergy_api.carga import load_gold

URL = "/fila-suspeitas"


@pytest.fixture(autouse=True)
def loaded_sample(tmp_path: Path, engine: Engine) -> None:
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)


def queue(client: TestClient, **params: object) -> dict:
    response = client.get(URL, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def codes(page: dict) -> list[str]:
    return [item["cod_uc"] for item in page["itens"]]


def test_lists_the_queue_by_ranking_position(client: TestClient) -> None:
    page = queue(client)

    assert page["total"] == len(SAMPLE_FILA)
    assert [(i["cod_uc"], i["score_suspeita"], i["motivos"]) for i in page["itens"]] == [
        (s.cod_uc, s.score_suspeita, s.motivos)
        for s in sorted(SAMPLE_FILA, key=lambda s: s.score_suspeita)
    ]


def test_reports_the_recoverable_energy(client: TestClient) -> None:
    energy = {i["cod_uc"]: i["kwh_recuperavel_est"] for i in queue(client)["itens"]}

    assert energy["0007"] == 1425.0
    assert energy["0004"] == 310.0


def test_pages_follow_the_ranking(client: TestClient) -> None:
    second = queue(client, pagina=2, tamanho=1)

    assert (codes(second), second["total"], second["pagina"], second["tamanho"]) == (
        ["0007"],
        3,
        2,
        1,
    )


def test_page_past_the_end_is_empty_with_the_right_total(client: TestClient) -> None:
    page = queue(client, pagina=9, tamanho=50)

    assert (page["itens"], page["total"]) == ([], 3)


@pytest.mark.parametrize("params", [{"pagina": 0}, {"tamanho": 0}, {"tamanho": 201}])
def test_rejects_an_invalid_page(client: TestClient, params: dict[str, int]) -> None:
    assert client.get(URL, params=params).status_code == 422


def test_shows_the_active_order_until_it_is_cancelled(client: TestClient) -> None:
    order = client.post("/ordens-inspecao", json={"cod_ucs": ["0007"]}).json()[0]

    item = next(i for i in queue(client)["itens"] if i["cod_uc"] == "0007")
    assert item["ordem_ativa"] == {"id": order["id"], "status": "GERADA"}

    client.patch(f"/ordens-inspecao/{order['id']}", json={"status": "CANCELADA"})
    item = next(i for i in queue(client)["itens"] if i["cod_uc"] == "0007")
    assert item["ordem_ativa"] is None


def test_hides_units_with_an_active_order_and_adjusts_the_total(client: TestClient) -> None:
    client.post("/ordens-inspecao", json={"cod_ucs": ["0007"]})

    page = queue(client, sem_ordem_ativa=True)

    assert (codes(page), page["total"]) == (["0005", "0004"], 2)
