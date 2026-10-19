from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from venergy_api.database import create_db_engine


def test_health_returns_ok_when_database_is_reachable(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_unreachable(
    client_for: Callable[[Engine], TestClient],
) -> None:
    # Ninguém escuta na porta 1: a conexão é recusada na hora, como um banco fora do ar.
    broken_engine = create_db_engine("postgresql+psycopg://venergy:x@127.0.0.1:1/venergy")

    response = client_for(broken_engine).get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unreachable"}
