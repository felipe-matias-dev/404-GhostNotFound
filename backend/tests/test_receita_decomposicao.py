from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from venergy_api.amostra import SAMPLE_DECOMPOSICAO, write_sample
from venergy_api.carga import load_gold
from venergy_api.database import Base
from venergy_api.models import ReceitaDecomposicao

CURRENT = ("2024-01/2024-12", "2025-01/2025-12")
PREVIOUS = ("2023-01/2023-12", "2024-01/2024-12")

# (períodos, município, bairro, classe, GD, receita_base, receita_atual, tarifa, bandeira,
# volume, mix). Em cada linha, preço = tarifa + bandeira e preço + volume + mix =
# receita_atual - receita_base, como no contrato.
BRIDGE = [
    (CURRENT, "Recife", "Boa Viagem", "B1", False, "100", "90", "3", "2", "-12", "-3"),
    (CURRENT, "Recife", "Boa Viagem", "B3", False, "200", "230", "15", "5", "8", "2"),
    (CURRENT, "Recife", "Casa Forte", "B1", False, "50", "45", "-2", "1", "-4", "0"),
    (CURRENT, "Olinda", "Carmo", "B1", True, "80", "60", "-6", "1", "-14", "-1"),
    (PREVIOUS, "Olinda", "Carmo", "B1", True, "70", "80", "6", "0", "4", "0"),
]


def bridge_line(
    periods: tuple[str, str],
    municipio: str,
    bairro: str,
    classe: str,
    possui_gd: bool,
    *values: str,
) -> ReceitaDecomposicao:
    base, atual, tarifa, bandeira, volume, mix = (Decimal(value) for value in values)
    return ReceitaDecomposicao(
        periodo_base=periods[0],
        periodo_atual=periods[1],
        municipio=municipio,
        bairro=bairro,
        classe=classe,
        possui_gd=possui_gd,
        receita_base=base,
        receita_atual=atual,
        efeito_preco=tarifa + bandeira,
        efeito_tarifa=tarifa,
        efeito_bandeira=bandeira,
        efeito_volume=volume,
        efeito_mix=mix,
    )


@pytest.fixture
def bridge(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all(bridge_line(*line) for line in BRIDGE)


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
            "efeito_tarifa": -6.0,
            "efeito_bandeira": 1.0,
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
            "efeito_tarifa": 16.0,
            "efeito_bandeira": 8.0,
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


def test_lines_with_and_without_solar_add_up_in_the_same_segment(
    bridge: None, engine: Engine, client: TestClient
) -> None:
    with Session(engine) as session, session.begin():
        session.add(
            bridge_line(CURRENT, "Olinda", "Carmo", "B1", False, "20", "25", "2", "1", "2", "0")
        )

    olinda = next(row for row in decompose(client) if row["segmento"] == "Olinda")

    assert (olinda["receita_base"], olinda["receita_atual"]) == (100.0, 85.0)
    assert olinda["efeito_bandeira"] == 2.0


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
    # Os checks do contrato continuam valendo depois de a API somar os segmentos, senão a
    # ponte da tela não fecha. A tolerância é a do contrato por linha (R$ 0,01 em preço =
    # tarifa + bandeira, R$ 0,02 em preço + volume + mix = variação), vezes as linhas somadas.
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)
    lines = len(SAMPLE_DECOMPOSICAO)

    rows = client.get("/receita/decomposicao").json()
    for municipio in {row["segmento"] for row in rows}:
        rows += client.get("/receita/decomposicao", params={"municipio": municipio}).json()

    assert rows
    for row in rows:
        effect = {
            key: Decimal(str(value)) for key, value in row.items() if key.startswith("efeito")
        }
        price = effect["efeito_tarifa"] + effect["efeito_bandeira"]
        assert abs(effect["efeito_preco"] - price) <= Decimal("0.01") * lines
        effects = effect["efeito_preco"] + effect["efeito_volume"] + effect["efeito_mix"]
        assert abs(effects - Decimal(str(row["variacao_receita"]))) <= Decimal("0.02") * lines


def test_rejects_a_neighborhood_without_its_city(engine: Engine, client: TestClient) -> None:
    response = client.get("/receita/decomposicao", params={"bairro": "Carmo"})

    assert response.status_code == 422
    assert "Informe o município junto com o bairro" in response.text


def test_returns_an_empty_list_before_the_gold_is_loaded(
    engine: Engine, client: TestClient
) -> None:
    Base.metadata.create_all(engine)

    assert decompose(client) == []
