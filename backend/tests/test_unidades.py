import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete
from sqlalchemy.orm import Session

from venergy_api.database import Base
from venergy_api.models import DimUc

STORED_UC = {
    "cod_uc": "0001",
    "municipio": "Recife",
    "bairro": "Boa Viagem",
    "classe": "B1",
    "classe_cadastro": "Residencial",
    "cod_alimentador": "AL-01",
    "possui_gd": True,
    "consumo_medio_kwh_12m": 152.4,
    "titular_mascarado": "M. S.",
    "documento_mascarado": "***.***.**1-23",
    "potencia_kwp": 3.3,
    "data_ligacao": "2018-06-01",
    "data_conexao_gd": "2022-03-15",
    "modalidade_gd": "geracao_propria_uc",
    "energia_injetada_kwh_mes": 396.0,
}

UC_WITHOUT_READING = {
    **STORED_UC,
    "cod_uc": "0002",
    "possui_gd": False,
    "consumo_medio_kwh_12m": None,
    "titular_mascarado": None,
    "documento_mascarado": None,
    "potencia_kwp": None,
    "data_conexao_gd": None,
    "modalidade_gd": None,
    "energia_injetada_kwh_mes": None,
}


@pytest.fixture(autouse=True)
def stored_uc(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all([DimUc(**STORED_UC), DimUc(**UC_WITHOUT_READING)])


def test_localidades_are_distinct_ordered_and_only_expose_location(
    client: TestClient, engine: Engine
) -> None:
    with Session(engine) as session, session.begin():
        session.add_all(
            [
                DimUc(
                    **{**STORED_UC, "cod_uc": "0003", "municipio": "Paulista", "bairro": "Centro"}
                ),
                DimUc(**{**STORED_UC, "cod_uc": "0004", "municipio": "Recife", "bairro": "Centro"}),
                DimUc(
                    **{**STORED_UC, "cod_uc": "0005", "municipio": "Paulista", "bairro": "Janga"}
                ),
            ]
        )

    response = client.get("/unidades-consumidoras/localidades")

    assert response.status_code == 200
    assert response.json() == [
        {"municipio": "Paulista", "bairro": "Centro"},
        {"municipio": "Paulista", "bairro": "Janga"},
        {"municipio": "Recife", "bairro": "Boa Viagem"},
        {"municipio": "Recife", "bairro": "Centro"},
    ]


def test_localidades_are_empty_without_units(client: TestClient, engine: Engine) -> None:
    with Session(engine) as session, session.begin():
        session.execute(delete(DimUc))

    response = client.get("/unidades-consumidoras/localidades")

    assert response.status_code == 200
    assert response.json() == []


def test_returns_the_consumer_unit_when_it_exists(client: TestClient) -> None:
    response = client.get("/unidades-consumidoras/0001")

    assert response.status_code == 200
    assert response.json() == STORED_UC


def test_unit_without_reading_has_no_average_consumption(client: TestClient) -> None:
    # Vazio, e não zero: zero diria que a UC não consumiu, quando na verdade não há leitura.
    response = client.get("/unidades-consumidoras/0002")

    assert response.status_code == 200
    assert response.json() == UC_WITHOUT_READING


def test_returns_404_when_the_consumer_unit_does_not_exist(client: TestClient) -> None:
    response = client.get("/unidades-consumidoras/9999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Unidade consumidora 9999 não encontrada"}


def _add_ucs(engine: Engine, *codigos: str) -> None:
    with Session(engine) as session, session.begin():
        session.add_all([DimUc(**{**STORED_UC, "cod_uc": codigo}) for codigo in codigos])


@pytest.mark.parametrize("digitado", ["144997", "uc 144997", "UC-144997", "uc144997"])
def test_resolves_the_code_as_the_attendant_types_it(
    client: TestClient, engine: Engine, digitado: str
) -> None:
    _add_ucs(engine, "UC144997", "UC1449970")

    response = client.get(f"/unidades-consumidoras/{digitado}")

    assert response.status_code == 200
    assert response.json()["cod_uc"] == "UC144997"


def test_number_shared_by_two_units_is_not_resolved(client: TestClient, engine: Engine) -> None:
    _add_ucs(engine, "UC1024", "TESTE1024")

    response = client.get("/unidades-consumidoras/1024")

    assert response.status_code == 404


def test_search_ranks_exact_then_prefix_then_contained(client: TestClient, engine: Engine) -> None:
    _add_ucs(engine, "UC101024", "UC1024", "UC102400", "UC144997")

    response = client.get("/unidades-consumidoras/busca", params={"q": " 1024 "})

    assert response.status_code == 200
    assert [uc["cod_uc"] for uc in response.json()] == ["UC1024", "UC102400", "UC101024"]
    assert response.json()[0] == {
        "cod_uc": "UC1024",
        "municipio": "Recife",
        "bairro": "Boa Viagem",
        "classe_cadastro": "Residencial",
    }


def test_search_without_letters_or_digits_returns_nothing(client: TestClient) -> None:
    response = client.get("/unidades-consumidoras/busca", params={"q": "%_ -"})

    assert response.status_code == 200
    assert response.json() == []
