from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from venergy_api.amostra import write_sample
from venergy_api.carga import load_gold
from venergy_api.database import Base
from venergy_api.models import KpisSegmentoMensal

URL = "/continuidade/recortes"
PERIOD = {"inicio": "2025-01", "fim": "2025-02"}

# (competencia, municipio, bairro, classe, cod_alimentador, tipo_medidor, n_uc, n_interrupcoes,
# horas). O AL-01 atende os dois bairros do Recife. Em janeiro a Boa Viagem está dividida em
# dois tipos de medidor, e as duas linhas somam como uma só.
ROWS = [
    ("2025-01", "Recife", "Boa Viagem", "B1", "AL-01", "eletronico", 60, 6, 12.0),
    ("2025-01", "Recife", "Boa Viagem", "B1", "AL-01", "smart", 40, 4, 8.0),
    ("2025-02", "Recife", "Boa Viagem", "B1", "AL-01", "eletronico", 100, 20, 40.0),
    ("2025-01", "Recife", "Casa Forte", "B3", "AL-01", "eletronico", 50, 5, 10.0),
    ("2025-02", "Recife", "Casa Forte", "B3", "AL-01", "eletronico", 50, 5, 40.0),
    ("2025-01", "Olinda", "Carmo", "B1", "AL-02", "eletronico", 50, 0, 0.0),
    ("2025-02", "Olinda", "Carmo", "B1", "AL-02", "eletronico", 50, 10, 30.0),
]


def store_segments(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all(
            KpisSegmentoMensal(
                competencia=competencia,
                municipio=municipio,
                bairro=bairro,
                classe_cadastro="Residencial" if classe == "B1" else "Comercial",
                possui_gd=False,
                cod_alimentador=alimentador,
                tipo_medidor=medidor,
                classe=classe,
                n_uc=n_uc,
                kwh_faturado=Decimal(0),
                receita_faturada=Decimal(0),
                receita_energia=Decimal(0),
                tributos=Decimal(0),
                receita_arrecadada=None,
                horas_interrompidas=horas,
                n_interrupcoes=n_interrupcoes,
                n_chamados=0,
                soma_notas=None,
                n_notas=0,
                receita_bandeira=Decimal(0),
                n_faturas=0,
                n_faturas_nao_pagas=0,
                valor_nao_pago=Decimal(0),
                n_faturas_pagas_com_atraso=0,
                soma_dias_em_atraso=0,
                n_leituras=0,
                n_leituras_estimadas=0,
            )
            for (
                competencia,
                municipio,
                bairro,
                classe,
                alimentador,
                medidor,
                n_uc,
                n_interrupcoes,
                horas,
            ) in ROWS
        )


def recortes(client: TestClient, **params: str) -> dict:
    response = client.get(URL, params={**PERIOD, **params})
    assert response.status_code == 200
    return response.json()


def summary(result: dict) -> list[tuple[str, float, float]]:
    return [(r["segmento"], r["dec"], r["fec"]) for r in result["recortes"]]


def test_without_filter_groups_by_municipality(engine: Engine, client: TestClient) -> None:
    store_segments(engine)

    result = recortes(client)

    # Recife: 110 h ÷ (300 UC ÷ 2 meses) = 0,7333 e 40 interrupções ÷ 150 = 0,2667.
    # Olinda: 30 h ÷ (100 ÷ 2) = 0,6 e 10 ÷ 50 = 0,2.
    assert result["nivel"] == "municipio"
    assert result["n_meses"] == 2
    assert summary(result) == [
        ("Recife", pytest.approx(110 / 150), pytest.approx(40 / 150)),
        ("Olinda", 0.6, 0.2),
    ]


def test_with_a_municipality_groups_by_neighborhood_worst_first(
    engine: Engine, client: TestClient
) -> None:
    store_segments(engine)

    result = recortes(client, municipio="Recife")

    # Casa Forte: 50 h ÷ (100 ÷ 2) = 1,0. Boa Viagem: 60 h ÷ (200 ÷ 2) = 0,6, com as duas
    # linhas de medidor de janeiro somadas.
    assert result["nivel"] == "bairro"
    assert summary(result) == [("Casa Forte", 1.0, 0.2), ("Boa Viagem", 0.6, 0.3)]


def test_with_a_neighborhood_groups_by_feeder(engine: Engine, client: TestClient) -> None:
    store_segments(engine)

    result = recortes(client, municipio="Recife", bairro="Boa Viagem")

    assert result["nivel"] == "alimentador"
    assert summary(result) == [("AL-01", 0.6, 0.3)]


def test_class_filter_restricts_the_sums(engine: Engine, client: TestClient) -> None:
    store_segments(engine)

    result = recortes(client, classe="B1")

    # Só o B1: Recife fica com a Boa Viagem (0,6 e 0,3) e empata o DEC com Olinda (0,6 e 0,2);
    # o FEC desempata.
    assert summary(result) == [("Recife", 0.6, 0.3), ("Olinda", 0.6, 0.2)]


def test_ranks_by_fec_when_asked(engine: Engine, client: TestClient) -> None:
    store_segments(engine)

    result = recortes(client, municipio="Recife", criterio="fec")

    assert [r["segmento"] for r in result["recortes"]] == ["Boa Viagem", "Casa Forte"]


def test_requires_a_period_and_a_municipality_with_the_neighborhood(
    engine: Engine, client: TestClient
) -> None:
    store_segments(engine)

    assert client.get(URL).status_code == 422
    assert client.get(URL, params={**PERIOD, "bairro": "Carmo"}).status_code == 422
    assert client.get(URL, params={"inicio": "2025-03", "fim": "2025-01"}).status_code == 422


def test_period_without_data_is_empty(engine: Engine, client: TestClient) -> None:
    store_segments(engine)

    result = recortes(client, inicio="2030-01", fim="2030-02")

    assert (result["n_meses"], result["recortes"]) == (0, [])


def test_municipalities_add_up_to_the_feeders_and_the_company_total(
    tmp_path: Path, engine: Engine, client: TestClient
) -> None:
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)
    month = {"inicio": "2025-06", "fim": "2025-06"}

    municipios = client.get(URL, params=month).json()["recortes"]
    alimentadores = client.get("/continuidade/alimentadores/mensal", params=month).json()
    kpis = client.get("/receita/mensal", params=month).json()[0]

    assert sum(m["horas_interrompidas"] for m in municipios) == pytest.approx(
        sum(a["horas_interrompidas"] for a in alimentadores)
    )
    horas = sum(m["horas_interrompidas"] for m in municipios)
    unidades = sum(m["n_uc_medio"] for m in municipios)
    assert horas / unidades == pytest.approx(kpis["dec"])
