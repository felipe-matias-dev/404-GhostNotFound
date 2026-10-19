import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from venergy_api.database import Base
from venergy_api.models import UcResumo

STORED_UC = {
    "uc_id": "0001",
    "municipio": "Recife",
    "bairro": "Boa Viagem",
    "classe": "B1",
    "alimentador": "AL-01",
    "possui_gd": True,
    "consumo_medio_kwh_12m": 152.4,
}


@pytest.fixture(autouse=True)
def stored_uc(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add(UcResumo(**STORED_UC))


def test_returns_the_consumer_unit_when_it_exists(client: TestClient) -> None:
    response = client.get("/unidades-consumidoras/0001")

    assert response.status_code == 200
    assert response.json() == STORED_UC


def test_returns_404_when_the_consumer_unit_does_not_exist(client: TestClient) -> None:
    response = client.get("/unidades-consumidoras/9999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Unidade consumidora 9999 não encontrada"}
