from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from venergy_api.database import create_db_engine


def test_health_returns_ok_when_database_is_reachable(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_unreachable(
    tmp_path: Path, client_for: Callable[[Engine], TestClient]
) -> None:
    # O SQLite cria o arquivo, mas não a pasta: um diretório inexistente simula banco fora do ar.
    missing_path = tmp_path / "missing-dir" / "venergy.db"
    broken_engine = create_db_engine(f"sqlite:///{missing_path.as_posix()}")

    response = client_for(broken_engine).get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unreachable"}
