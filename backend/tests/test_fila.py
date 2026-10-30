from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, update

from venergy_api.amostra import SAMPLE_FILA, write_sample
from venergy_api.carga import load_gold
from venergy_api.models import FilaSuspeita

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


@pytest.mark.parametrize(
    ("direction", "expected"),
    [("asc", ["0005", "0004", "0007"]), ("desc", ["0007", "0004", "0005"])],
)
def test_energy_sort_applies_before_pagination(
    client: TestClient, direction: str, expected: list[str]
) -> None:
    result = [
        codes(queue(client, ordenar_por="energia", direcao=direction, pagina=page, tamanho=1))[0]
        for page in range(1, 4)
    ]
    assert result == expected


@pytest.mark.parametrize(
    ("direction", "expected"),
    [("asc", ["0005", "0004", "0007"]), ("desc", ["0007", "0005", "0004"])],
)
def test_active_order_sort_is_global_and_stable(
    client: TestClient, direction: str, expected: list[str]
) -> None:
    client.post("/ordens-inspecao", json={"cod_ucs": ["0007"]})
    assert [
        codes(queue(client, ordenar_por="ordem_ativa", direcao=direction, pagina=page, tamanho=1))[
            0
        ]
        for page in range(1, 4)
    ] == expected


@pytest.mark.parametrize("direction", ["asc", "desc"])
def test_missing_energy_is_last(client: TestClient, engine: Engine, direction: str) -> None:
    with engine.begin() as connection:
        connection.execute(
            update(FilaSuspeita)
            .where(FilaSuspeita.cod_uc == "0005")
            .values(kwh_recuperavel_est=None)
        )
    assert codes(queue(client, ordenar_por="energia", direcao=direction))[-1] == "0005"


def test_rejects_unknown_sort(client: TestClient) -> None:
    assert client.get(URL, params={"ordenar_por": "invalido"}).status_code == 422
    assert client.get(URL, params={"direcao": "invalida"}).status_code == 422


def test_drop_distribution_filter_and_sort(client: TestClient) -> None:
    response = client.get(f"{URL}/distribuicao-queda")
    assert response.status_code == 200
    assert {item["queda"]: item["total"] for item in response.json()["itens"]} == {20: 1, 33: 2}
    assert response.json()["sem_queda_identificada"] == 0
    page = queue(client, queda_min=33, queda_max=33, tamanho=1, pagina=2)
    assert (codes(page), page["total"]) == (["0007"], 2)
    assert codes(queue(client, ordenar_por="queda", direcao="asc")) == ["0004", "0005", "0007"]
    assert client.get(URL, params={"queda_min": 34, "queda_max": 20}).status_code == 422


def test_unrecognized_drop_is_not_confused_with_other_percentages(
    client: TestClient, engine: Engine
) -> None:
    with engine.begin() as connection:
        connection.execute(
            update(FilaSuspeita)
            .where(FilaSuspeita.cod_uc == "0005")
            .values(motivos=["25% das leituras foram estimadas"])
        )
    assert client.get(f"{URL}/distribuicao-queda").json()["sem_queda_identificada"] == 1
    assert "0005" not in codes(queue(client, queda_min=0, queda_max=100))
    assert "0005" in codes(queue(client))


def test_electromechanical_filter_matches_the_exact_reason(
    client: TestClient, engine: Engine
) -> None:
    with engine.begin() as connection:
        connection.execute(
            update(FilaSuspeita)
            .where(FilaSuspeita.cod_uc == "0004")
            .values(motivos=["Não é Medidor eletromecânico"])
        )
    page = queue(client, medidor_eletromecanico=True)
    assert (codes(page), page["total"]) == (["0005"], 1)
    assert queue(client, medidor_eletromecanico=False)["total"] == 3


def test_estimated_readings_bounds_are_inclusive_and_missing_is_not_zero(
    client: TestClient, engine: Engine
) -> None:
    with engine.begin() as connection:
        for code, percentage in [("0005", 25), ("0007", 100)]:
            connection.execute(
                update(FilaSuspeita)
                .where(FilaSuspeita.cod_uc == code)
                .values(
                    motivos=[
                        f"{percentage}% das leituras das 12 últimas competências foram estimadas"
                    ]
                )
            )
    assert codes(queue(client, leituras_estimadas_max=25)) == ["0005"]
    assert codes(queue(client, leituras_estimadas_min=100)) == ["0007"]
    page = queue(client, leituras_estimadas_min=25, leituras_estimadas_max=100)
    assert (codes(page), page["total"]) == (["0005", "0007"], 2)
    assert "0004" in codes(queue(client))
    assert client.get(URL, params={"leituras_estimadas_max": 20}).status_code == 422


@pytest.mark.parametrize(
    "reason",
    [
        "Queda de 25% no consumo médio das 12 últimas competências contra as 12 anteriores",
        "25% das leituras foram estimadas",
        "101% das leituras das 12 últimas competências foram estimadas",
        "1000% das leituras das 12 últimas competências foram estimadas",
        "-1% das leituras das 12 últimas competências foram estimadas",
        "2.5% das leituras das 12 últimas competências foram estimadas",
        "25% das leituras das 12 últimas competências foram estimadas aproximadamente",
    ],
)
def test_estimated_readings_filter_excludes_unrecognized_reasons(
    client: TestClient, engine: Engine, reason: str
) -> None:
    with engine.begin() as connection:
        connection.execute(
            update(FilaSuspeita).where(FilaSuspeita.cod_uc == "0005").values(motivos=[reason])
        )
    page = queue(client, leituras_estimadas_min=25, leituras_estimadas_max=100)
    assert (codes(page), page["total"]) == ([], 0)
    assert "0005" in codes(queue(client))


def test_all_suspicion_filters_combine_before_pagination(
    client: TestClient, engine: Engine
) -> None:
    with engine.begin() as connection:
        for code, drop, estimated in [("0005", 33, 25), ("0007", 33, 75), ("0004", 20, 50)]:
            connection.execute(
                update(FilaSuspeita)
                .where(FilaSuspeita.cod_uc == code)
                .values(
                    motivos=[
                        f"Queda de {drop}% no consumo médio das 12 últimas competências"
                        " contra as 12 anteriores",
                        "Medidor eletromecânico",
                        f"{estimated}% das leituras das 12 últimas competências foram estimadas",
                    ]
                )
            )
    filters = {
        "queda_min": 30,
        "medidor_eletromecanico": True,
        "leituras_estimadas_min": 25,
        "leituras_estimadas_max": 75,
        "tamanho": 1,
    }
    first = queue(client, **filters)
    second = queue(client, pagina=2, **filters)
    assert (codes(first), codes(second), first["total"], second["total"]) == (
        ["0005"],
        ["0007"],
        2,
        2,
    )
    narrower = queue(client, **{**filters, "leituras_estimadas_min": 50})
    assert (codes(narrower), narrower["total"]) == (["0007"], 1)


@pytest.mark.parametrize(
    "params",
    [
        {"leituras_estimadas_min": -1},
        {"leituras_estimadas_min": 101},
        {"leituras_estimadas_max": -1},
        {"leituras_estimadas_max": 101},
        {"leituras_estimadas_min": 50, "leituras_estimadas_max": 25},
        {"medidor_eletromecanico": "invalido"},
    ],
)
def test_rejects_invalid_suspicion_filters(client: TestClient, params: dict) -> None:
    assert client.get(URL, params=params).status_code == 422
