from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, update
from sqlalchemy.orm import Session

from venergy_api.amostra import SAMPLE_FILA, write_sample
from venergy_api.carga import load_gold
from venergy_api.models import FilaSuspeita, InspecaoUc

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


@pytest.mark.parametrize(
    "params",
    [
        {"queda_min": 50, "queda_max": 25},
        {"leituras_estimadas_min": 50, "leituras_estimadas_max": 25},
    ],
)
def test_inverted_ranges_return_validation_errors(client: TestClient, params: dict) -> None:
    response = client.get(URL, params=params)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "value_error"


@pytest.mark.parametrize(
    ("recorte", "expected"),
    [
        ({"municipio": "Paulista", "bairro": "Janga", "classe": "B1"}, ["0005"]),
        (
            {"municipio": "Jaboatão dos Guararapes", "bairro": "Piedade", "classe": "B3"},
            ["0004"],
        ),
        ({"municipio": "Inexistente"}, []),
    ],
)
def test_queue_filters_segment_before_pagination(
    client: TestClient, recorte: dict[str, str], expected: list[str]
) -> None:
    first = queue(client, **recorte, tamanho=1)
    second = queue(client, **recorte, tamanho=1, pagina=2)
    assert (codes(first), first["total"], codes(second), second["total"]) == (
        expected,
        len(expected),
        [],
        len(expected),
    )


def test_segment_combines_with_drop_and_active_order(client: TestClient) -> None:
    recorte = {"municipio": "Paulista", "bairro": "Janga", "classe": "B1"}
    client.post("/ordens-inspecao", json={"cod_ucs": ["0005"]})
    assert codes(queue(client, **recorte, queda_min=33, queda_max=33)) == ["0005"]
    assert queue(client, **recorte, sem_ordem_ativa=True)["total"] == 0


def test_distribution_uses_segment_and_includes_unidentified_drop(
    client: TestClient, engine: Engine
) -> None:
    with engine.begin() as connection:
        connection.execute(
            update(FilaSuspeita).where(FilaSuspeita.cod_uc == "0005").values(motivos=["Outro"])
        )
    recorte = {"municipio": "Paulista", "bairro": "Janga", "classe": "B1"}
    response = client.get(f"{URL}/distribuicao-queda", params=recorte)
    assert response.status_code == 200
    distribution = response.json()
    assert distribution == {"itens": [], "sem_queda_identificada": 1}
    assert (
        sum(item["total"] for item in distribution["itens"])
        + distribution["sem_queda_identificada"]
        == queue(client, **recorte)["total"]
    )
    assert queue(client, **recorte, queda_min=20)["total"] == 0


@pytest.mark.parametrize("url", [URL, f"{URL}/distribuicao-queda"])
def test_segment_requires_municipality_for_neighborhood(client: TestClient, url: str) -> None:
    assert client.get(url, params={"bairro": "Janga"}).status_code == 422


def inspect_uc(engine: Engine, cod_uc: str, day: date, result: str, kwh: str = "0") -> None:
    with Session(engine) as session, session.begin():
        session.add(
            InspecaoUc(
                cod_inspecao=f"T-{cod_uc}-{day}",
                cod_uc=cod_uc,
                data_inspecao=day,
                competencia=day.strftime("%Y-%m"),
                resultado=result,
                tipo_irregularidade="DESVIO" if kwh != "0" else None,
                kwh_recuperado=Decimal(kwh),
            )
        )


def conclude(client: TestClient, cod_uc: str, **result: object) -> int:
    order_id = client.post("/ordens-inspecao", json={"cod_ucs": [cod_uc]}).json()[0]["id"]
    client.patch(f"/ordens-inspecao/{order_id}", json={"status": "EM_CAMPO"})
    response = client.patch(f"/ordens-inspecao/{order_id}", json={"status": "CONCLUIDA", **result})
    assert response.status_code == 200, response.text
    return order_id


def last_inspection(client: TestClient, cod_uc: str) -> dict | None:
    item = next(i for i in queue(client)["itens"] if i["cod_uc"] == cod_uc)
    return item["ultima_inspecao"]


def today_in_recife() -> date:
    return datetime.now(ZoneInfo("America/Recife")).date()


def test_last_inspection_is_the_most_recent_of_gold_and_portal(
    client: TestClient, engine: Engine
) -> None:
    inspect_uc(engine, "0007", date(2020, 1, 10), "sem_irregularidade")
    inspect_uc(engine, "0007", date(2021, 3, 5), "irregularidade_confirmada", "100")
    assert last_inspection(client, "0007") == {
        "data": "2021-03-05",
        "resultado": "irregularidade_confirmada",
        "origem": "gold",
    }
    assert last_inspection(client, "0005") is None

    conclude(client, "0007", resultado="REGULAR")

    assert last_inspection(client, "0007") == {
        "data": today_in_recife().isoformat(),
        "resultado": "sem_irregularidade",
        "origem": "portal",
    }


def test_a_tie_between_sources_goes_to_the_portal(client: TestClient, engine: Engine) -> None:
    inspect_uc(engine, "0007", today_in_recife(), "irregularidade_confirmada", "100")

    conclude(client, "0007", resultado="REGULAR")

    assert last_inspection(client, "0007")["origem"] == "portal"


def test_an_unperformed_order_is_not_an_inspection(client: TestClient, engine: Engine) -> None:
    inspect_uc(engine, "0007", date(2021, 3, 5), "sem_irregularidade")

    conclude(client, "0007", resultado="NAO_REALIZADA")

    assert last_inspection(client, "0007")["origem"] == "gold"


def test_recently_inspected_units_leave_the_items_and_the_total(
    client: TestClient, engine: Engine
) -> None:
    inspect_uc(engine, "0007", today_in_recife() - timedelta(days=30), "sem_irregularidade")
    inspect_uc(engine, "0004", date(2020, 1, 1), "sem_irregularidade")

    page = queue(client, sem_inspecao_meses=12)

    assert (codes(page), page["total"]) == (["0005", "0004"], 2)
    assert queue(client)["total"] == 3
    assert codes(queue(client, sem_inspecao_meses=12, tamanho=1, pagina=2)) == ["0004"]
    assert client.get(URL, params={"sem_inspecao_meses": 0}).status_code == 422


def test_indicators_count_suspects_orders_and_inspection_results(client: TestClient) -> None:
    client.post("/ordens-inspecao", json={"cod_ucs": ["0007"]})
    conclude(
        client,
        "0005",
        resultado="IRREGULAR_CONFIRMADA",
        tipo_irregularidade="DESVIO",
        kwh_recuperado=300,
    )
    conclude(client, "0004", resultado="REGULAR")
    conclude(client, "0001", resultado="NAO_REALIZADA")

    body = client.get(f"{URL}/indicadores").json()

    assert body["suspeitas"] == 3
    assert body["suspeitas_sem_ordem_ativa"] == 2
    assert body["kwh_recuperavel_est_sem_ordem"] == 105.35 + 310
    assert (body["ordens_geradas"], body["ordens_em_campo"]) == (1, 0)
    assert body["portal"] == {
        "inspecoes": 3,
        "irregulares": 1,
        "regulares": 1,
        "nao_realizadas": 1,
        "taxa_irregularidade": 0.5,
        "kwh_recuperado": 300.0,
    }
    assert body["gold"]["nao_realizadas"] == 0
    assert (body["gold"]["inspecoes"], body["gold"]["irregulares"]) == (2, 1)
    assert body["gold"]["taxa_irregularidade"] == 0.5
    assert body["gold"]["kwh_recuperado"] == 1200.0


def test_indicators_rate_is_empty_without_decided_inspections(
    client: TestClient, engine: Engine
) -> None:
    conclude(client, "0005", resultado="NAO_REALIZADA")

    portal = client.get(f"{URL}/indicadores", params={"municipio": "Paulista"}).json()["portal"]

    assert (portal["inspecoes"], portal["taxa_irregularidade"]) == (1, None)
    other = client.get(f"{URL}/indicadores", params={"municipio": "Recife"}).json()
    assert (other["suspeitas"], other["portal"]["inspecoes"]) == (1, 0)


def test_indicators_have_no_recoverable_energy_when_none_is_known(
    client: TestClient, engine: Engine
) -> None:
    with engine.begin() as connection:
        connection.execute(update(FilaSuspeita).values(kwh_recuperavel_est=None))

    assert client.get(f"{URL}/indicadores").json()["kwh_recuperavel_est_sem_ordem"] is None


def test_recortes_group_by_municipality_by_default_and_by_neighborhood_inside_one(
    client: TestClient, engine: Engine
) -> None:
    with engine.begin() as connection:
        connection.execute(
            update(FilaSuspeita)
            .where(FilaSuspeita.cod_uc == "0005")
            .values(kwh_recuperavel_est=None)
        )
    client.post("/ordens-inspecao", json={"cod_ucs": ["0007"]})

    body = client.get(f"{URL}/recortes").json()

    assert body["nivel"] == "municipio"
    assert body["recortes"] == [
        {
            "segmento": "Recife",
            "municipio": None,
            "suspeitas": 1,
            "suspeitas_sem_ordem_ativa": 0,
            "kwh_recuperavel_est": 1425.0,
        },
        {
            "segmento": "Jaboatão dos Guararapes",
            "municipio": None,
            "suspeitas": 1,
            "suspeitas_sem_ordem_ativa": 1,
            "kwh_recuperavel_est": 310.0,
        },
        {
            "segmento": "Paulista",
            "municipio": None,
            "suspeitas": 1,
            "suspeitas_sem_ordem_ativa": 1,
            "kwh_recuperavel_est": None,
        },
    ]
    inside = client.get(f"{URL}/recortes", params={"municipio": "Recife"}).json()
    assert inside["nivel"] == "bairro"
    assert [(r["segmento"], r["municipio"]) for r in inside["recortes"]] == [
        ("Santo Amaro", "Recife")
    ]


def test_recortes_reject_a_level_above_the_filter(client: TestClient) -> None:
    response = client.get(f"{URL}/recortes", params={"municipio": "Recife", "nivel": "municipio"})

    assert response.status_code == 422


def test_insight_narrates_only_totals_of_the_queue(client_with_writer) -> None:
    client, redator = client_with_writer()

    corpo = client.get(f"{URL}/insight").json()

    assert corpo["origem"] == "ia"
    ((tela, metricas),) = redator.chamadas
    assert tela == "perdas"
    codigos = codes(queue(client))
    assert not any(codigo in str(metricas) for codigo in codigos)


def test_insight_of_a_cut_without_suspicions_is_empty(client: TestClient) -> None:
    corpo = client.get(f"{URL}/insight", params={"municipio": "Município Inexistente"}).json()

    assert corpo == {"texto": None, "origem": None, "metricas": None}
