from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from venergy_api.amostra import write_sample
from venergy_api.carga import load_gold
from venergy_api.database import Base
from venergy_api.models import ReceitaDecomposicao

CURRENT = ("2024-01/2024-12", "2025-01/2025-12")
PREVIOUS = ("2023-01/2023-12", "2024-01/2024-12")

# (períodos, município, bairro, classe, receita_base, receita_atual, preço, volume, mix).
# Em cada linha, preço + volume + mix = receita_atual - receita_base, como no contrato.
BRIDGE = [
    (CURRENT, "Recife", "Boa Viagem", "B1", "100.00", "90.00", "5.00", "-12.00", "-3.00"),
    (CURRENT, "Recife", "Boa Viagem", "B3", "200.00", "230.00", "20.00", "8.00", "2.00"),
    (CURRENT, "Recife", "Casa Forte", "B1", "50.00", "45.00", "-1.00", "-4.00", "0.00"),
    (CURRENT, "Olinda", "Carmo", "B1", "80.00", "60.00", "-5.00", "-14.00", "-1.00"),
    (PREVIOUS, "Olinda", "Carmo", "B1", "70.00", "80.00", "6.00", "4.00", "0.00"),
]


@pytest.fixture
def bridge(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all(
            ReceitaDecomposicao(
                periodo_base=periodo_base,
                periodo_atual=periodo_atual,
                municipio=municipio,
                bairro=bairro,
                classe=classe,
                receita_base=Decimal(base),
                receita_atual=Decimal(atual),
                efeito_preco=Decimal(preco),
                efeito_volume=Decimal(volume),
                efeito_mix=Decimal(mix),
            )
            for (
                (periodo_base, periodo_atual),
                municipio,
                bairro,
                classe,
                base,
                atual,
                preco,
                volume,
                mix,
            ) in BRIDGE
        )


def decompose(client: TestClient, **query: str) -> list[dict]:
    params = {"periodo_base": CURRENT[0], "periodo_atual": CURRENT[1], **query}
    response = client.get("/receita/decomposicao", params=params)
    assert response.status_code == 200
    return response.json()


@pytest.mark.usefixtures("bridge")
def test_top_level_is_one_row_per_city_with_the_biggest_drop_first(client: TestClient) -> None:
    assert decompose(client) == [
        {
            "nivel": "municipio",
            "segmento": "Olinda",
            "periodo_base": CURRENT[0],
            "periodo_atual": CURRENT[1],
            "receita_base": 80.0,
            "receita_atual": 60.0,
            "variacao_receita": -20.0,
            "efeito_preco": -5.0,
            "efeito_volume": -14.0,
            "efeito_mix": -1.0,
        },
        {
            "nivel": "municipio",
            "segmento": "Recife",
            "periodo_base": CURRENT[0],
            "periodo_atual": CURRENT[1],
            "receita_base": 350.0,
            "receita_atual": 365.0,
            "variacao_receita": 15.0,
            "efeito_preco": 24.0,
            "efeito_volume": -8.0,
            "efeito_mix": -1.0,
        },
    ]


@pytest.mark.usefixtures("bridge")
@pytest.mark.parametrize(
    ("query", "level", "segments"),
    [
        ({"municipio": "Recife"}, "bairro", ["Casa Forte", "Boa Viagem"]),
        ({"municipio": "Recife", "bairro": "Boa Viagem"}, "classe", ["B1", "B3"]),
        ({"classe": "B1"}, "municipio", ["Olinda", "Recife"]),
        ({"municipio": "Recife", "classe": "B3"}, "bairro", ["Boa Viagem"]),
    ],
)
def test_each_filter_goes_one_level_down(
    client: TestClient, query: dict[str, str], level: str, segments: list[str]
) -> None:
    rows = decompose(client, **query)

    assert [row["nivel"] for row in rows] == [level] * len(segments)
    assert [row["segmento"] for row in rows] == segments


@pytest.mark.usefixtures("bridge")
def test_keeps_each_pair_of_periods_apart(client: TestClient) -> None:
    response = client.get("/receita/decomposicao", params={"municipio": "Olinda"})

    rows = response.json()
    assert [(row["periodo_base"], row["variacao_receita"]) for row in rows] == [
        (PREVIOUS[0], 10.0),
        (CURRENT[0], -20.0),
    ]


def test_effects_add_up_to_the_revenue_change_at_every_level(
    tmp_path: Path, engine: Engine, client: TestClient
) -> None:
    # O check do contrato (preço + volume + mix = variação) tem que continuar valendo depois
    # de a API somar os segmentos: senão a ponte da tela não fecha.
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)

    rows = client.get("/receita/decomposicao").json()
    for municipio in {row["segmento"] for row in rows}:
        rows += client.get("/receita/decomposicao", params={"municipio": municipio}).json()

    assert rows
    for row in rows:
        effects = Decimal(str(row["efeito_preco"])) + Decimal(str(row["efeito_volume"]))
        effects += Decimal(str(row["efeito_mix"]))
        assert effects == Decimal(str(row["variacao_receita"]))


def test_rejects_a_neighborhood_without_its_city(engine: Engine, client: TestClient) -> None:
    response = client.get("/receita/decomposicao", params={"bairro": "Carmo"})

    assert response.status_code == 422
    assert "Informe o município junto com o bairro" in response.text


def test_returns_an_empty_list_before_the_gold_is_loaded(
    engine: Engine, client: TestClient
) -> None:
    Base.metadata.create_all(engine)

    assert decompose(client) == []
