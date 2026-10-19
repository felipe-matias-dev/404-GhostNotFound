from fastapi.testclient import TestClient


def test_allows_the_configured_frontend_origin(client: TestClient, frontend_origin: str) -> None:
    response = client.get("/health", headers={"Origin": frontend_origin})

    assert response.headers["access-control-allow-origin"] == frontend_origin


def test_does_not_allow_an_unknown_origin(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://site-desconhecido.example"})

    assert "access-control-allow-origin" not in response.headers
