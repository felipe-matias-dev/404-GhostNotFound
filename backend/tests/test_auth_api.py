"""Login, sessão e logout pela API, com os usuários de demonstração no banco."""

import base64
import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from venergy_api.auth import Perfil, UsuarioLogado, criar_token
from venergy_api.usuarios import criar_usuarios_demo

SENHA = "senha-de-demonstracao"
COOKIE = "venergy_sessao"


@pytest.fixture
def usuarios(engine: Engine) -> None:
    criar_usuarios_demo(engine, SENHA)


def _entrar(client: TestClient, login: str = "camila", senha: str = SENHA):
    return client.post("/auth/login", json={"login": login, "senha": senha})


def test_login_certo_devolve_o_usuario_e_grava_o_cookie_de_sessao(
    client: TestClient, usuarios: None
):
    response = _entrar(client)

    assert response.status_code == 200
    assert response.json() == {"login": "camila", "nome": "Camila", "perfil": "atendimento"}
    cookie = response.headers["set-cookie"].lower()
    assert cookie.startswith(f"{COOKIE}=")
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "max-age=28800" in cookie
    assert "path=/" in cookie


def test_o_corpo_do_login_nao_traz_token_nem_hash(client: TestClient, usuarios: None):
    corpo = _entrar(client).text

    assert "senha_hash" not in corpo
    assert "argon2" not in corpo
    assert client.cookies[COOKIE] not in corpo


def test_me_devolve_quem_entrou(client: TestClient, usuarios: None):
    _entrar(client, "patricia")

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json() == {"login": "patricia", "nome": "Patrícia", "perfil": "ti"}


def test_me_sem_login_responde_401(client: TestClient, usuarios: None):
    response = client.get("/auth/me")

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("login", "senha"),
    [("camila", "senha-errada"), ("ninguem", SENHA)],
    ids=["senha errada", "login inexistente"],
)
def test_falha_no_login_responde_igual_e_nao_grava_cookie(
    client: TestClient, usuarios: None, login: str, senha: str
):
    response = _entrar(client, login, senha)

    # A mesma resposta nos dois casos: quem erra não descobre quais logins existem.
    assert response.status_code == 401
    assert response.json() == {"detail": "Login ou senha inválidos"}
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("corpo", [{}, {"login": "camila"}, {"login": "", "senha": ""}])
def test_login_com_corpo_invalido_responde_422(client: TestClient, usuarios: None, corpo: dict):
    assert client.post("/auth/login", json=corpo).status_code == 422


def test_cookie_com_o_perfil_trocado_e_a_assinatura_antiga_responde_401(
    client: TestClient, usuarios: None
):
    _entrar(client)
    cabecalho, carga, assinatura = client.cookies[COOKIE].split(".")
    promovida = json.loads(base64.urlsafe_b64decode(carga + "=" * (-len(carga) % 4)))
    promovida["perfil"] = "ti"
    carga_nova = base64.urlsafe_b64encode(json.dumps(promovida).encode()).rstrip(b"=").decode()
    client.cookies.clear()
    client.cookies.set(COOKIE, f"{cabecalho}.{carga_nova}.{assinatura}")

    assert client.get("/auth/me").status_code == 401


def test_cookie_de_sessao_vencida_responde_401(client: TestClient, usuarios: None, jwt_secret: str):
    camila = UsuarioLogado(login="camila", nome="Camila", perfil=Perfil.ATENDIMENTO)
    ontem = datetime.now(UTC) - timedelta(days=1)
    client.cookies.set(COOKIE, criar_token(camila, jwt_secret, agora=ontem))

    assert client.get("/auth/me").status_code == 401


def test_logout_encerra_a_sessao(client: TestClient, usuarios: None):
    _entrar(client)

    response = client.post("/auth/logout")

    assert response.status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_logout_sem_sessao_tambem_responde_204(client: TestClient, usuarios: None):
    assert client.post("/auth/logout").status_code == 204


def test_login_ignora_maiusculas_e_espacos_nas_pontas(client: TestClient, usuarios: None):
    response = _entrar(client, "  CAMILA ")

    assert response.status_code == 200
    assert response.json()["login"] == "camila"
