import pytest
from fastapi.testclient import TestClient


def test_allows_the_configured_frontend_origin(client: TestClient, frontend_origin: str) -> None:
    response = client.get("/health", headers={"Origin": frontend_origin})

    assert response.headers["access-control-allow-origin"] == frontend_origin


def test_does_not_allow_an_unknown_origin(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://site-desconhecido.example"})

    assert "access-control-allow-origin" not in response.headers


def preflight(client: TestClient, origin: str, method: str) -> int:
    # O navegador pergunta antes de um POST/PATCH vindo de outra origem (preflight).
    response = client.options(
        "/ordens-inspecao/1",
        headers={"Origin": origin, "Access-Control-Request-Method": method},
    )
    return response.status_code


@pytest.mark.parametrize("method", ["POST", "PATCH"])
def test_allows_the_write_methods_used_by_inspection_orders(
    client: TestClient, frontend_origin: str, method: str
) -> None:
    assert preflight(client, frontend_origin, method) == 200


def test_does_not_allow_methods_the_api_does_not_use(
    client: TestClient, frontend_origin: str
) -> None:
    # Ordem de inspeção não se apaga, se cancela: DELETE não tem motivo para ser liberado.
    assert preflight(client, frontend_origin, "DELETE") == 400
