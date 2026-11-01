from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.orm import Session

from venergy_api.database import Base
from venergy_api.estrutura_app import garantir_estrutura_do_app
from venergy_api.models import TentativaLogin
from venergy_api.usuarios import criar_usuarios_demo

SENHA = "senha-de-demonstracao"
ERRADA = "senha-errada"
LIMITE = 3
JANELA = 900
ENDERECO_DO_TESTE = "testclient"


@pytest.fixture
def usuarios(engine: Engine) -> None:
    criar_usuarios_demo(engine, SENHA)


@pytest.fixture
def api(engine: Engine, client_for: Callable[..., TestClient], usuarios: None) -> TestClient:
    return client_for(engine, sem_login=True, login_max_falhas=LIMITE, login_janela_segundos=JANELA)


def entrar(client: TestClient, login: str = "camila", senha: str = ERRADA) -> Response:
    return client.post("/auth/login", json={"login": login, "senha": senha})


def errar(client: TestClient, vezes: int, login: str = "camila") -> None:
    for _ in range(vezes):
        assert entrar(client, login).status_code == 401


def gravar_falhas(engine: Engine, *idades_em_segundos: int, login: str = "camila") -> None:
    """Põe falhas antigas direto no banco, sem esperar o tempo passar."""
    with Session(engine) as session, session.begin():
        for idade in idades_em_segundos:
            session.execute(
                text(
                    "INSERT INTO app.tentativa_login (login, ip, sucesso, ocorrida_em) "
                    "VALUES (:login, :ip, false, now() - make_interval(secs => :idade))"
                ),
                {"login": login, "ip": ENDERECO_DO_TESTE, "idade": idade},
            )


def tentativas(engine: Engine) -> list[tuple[str, str, bool]]:
    with Session(engine) as session:
        linhas = session.scalars(select(TentativaLogin).order_by(TentativaLogin.id))
        return [(t.login, t.ip, t.sucesso) for t in linhas]


def test_old_database_gets_the_login_attempts_table(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE app.tentativa_login"))
        garantir_estrutura_do_app(connection)

    assert inspect(engine).has_table("tentativa_login", schema="app")


def test_blocks_after_the_limit_even_with_the_right_password(api: TestClient) -> None:
    errar(api, LIMITE)

    response = entrar(api, senha=SENHA)

    assert response.status_code == 429
    assert "Muitas tentativas" in response.json()["detail"]
    assert 0 < int(response.headers["retry-after"]) <= JANELA


def test_wrong_password_below_the_limit_is_still_a_plain_401(api: TestClient) -> None:
    errar(api, LIMITE)

    outro = entrar(api, "patricia", SENHA)

    assert outro.status_code == 200


def test_a_successful_login_clears_the_count(api: TestClient) -> None:
    errar(api, LIMITE - 1)
    assert entrar(api, senha=SENHA).status_code == 200

    errar(api, LIMITE - 1)

    assert entrar(api, senha=SENHA).status_code == 200


def test_another_address_is_not_blocked(api: TestClient) -> None:
    errar(api, LIMITE)
    de_outro_endereco = TestClient(api.app, client=("203.0.113.9", 50000))

    assert entrar(de_outro_endereco, senha=SENHA).status_code == 200


def test_unknown_login_is_blocked_the_same_way_as_a_real_one(api: TestClient) -> None:
    errar(api, LIMITE, login="camila")
    errar(api, LIMITE, login="ninguem")

    real = entrar(api, "camila", SENHA)
    inexistente = entrar(api, "ninguem", SENHA)

    assert real.status_code == inexistente.status_code == 429
    assert real.json() == inexistente.json()


def test_failures_outside_the_window_do_not_count(api: TestClient, engine: Engine) -> None:
    gravar_falhas(engine, *[JANELA + 60] * LIMITE)

    assert entrar(api).status_code == 401


@pytest.mark.parametrize(
    ("idades", "espera"),
    [
        ((600, 500, 400), 300),
        ((800, 500, 400, 10), 400),
    ],
)
def test_retry_after_is_when_the_block_lifts(
    api: TestClient, engine: Engine, idades: tuple[int, ...], espera: int
) -> None:
    gravar_falhas(engine, *idades)

    response = entrar(api, senha=SENHA)

    assert response.status_code == 429
    # Com 4 falhas e limite 3, saem duas até liberar: a de 800 s (em 100 s) e a de 500 s (em
    # 400 s). A espera é a da última delas. A folga cobre o tempo do próprio teste.
    assert int(response.headers["retry-after"]) in (espera, espera - 1)


def test_attempts_blocked_are_not_recorded(api: TestClient, engine: Engine) -> None:
    errar(api, LIMITE)
    for _ in range(3):
        assert entrar(api).status_code == 429

    assert len(tentativas(engine)) == LIMITE


def test_each_attempt_is_recorded_with_its_outcome_and_the_connection_address(
    api: TestClient, engine: Engine
) -> None:
    entrar(api)
    entrar(api, senha=SENHA)

    assert tentativas(engine) == [
        ("camila", ENDERECO_DO_TESTE, False),
        ("camila", ENDERECO_DO_TESTE, True),
    ]


def test_forwarded_header_does_not_change_the_address_that_counts(
    api: TestClient, engine: Engine
) -> None:
    for numero in range(LIMITE):
        api.post(
            "/auth/login",
            json={"login": "camila", "senha": ERRADA},
            headers={"X-Forwarded-For": f"198.51.100.{numero}"},
        )

    response = api.post(
        "/auth/login",
        json={"login": "camila", "senha": SENHA},
        headers={"X-Forwarded-For": "198.51.100.200"},
    )

    assert response.status_code == 429
    assert {ip for _, ip, _ in tentativas(engine)} == {ENDERECO_DO_TESTE}


def test_simultaneous_wrong_attempts_respect_the_limit(api: TestClient) -> None:
    with ThreadPoolExecutor(max_workers=12) as pool:
        codigos = Counter(r.status_code for r in pool.map(lambda _: entrar(api), range(12)))

    assert codigos == {401: LIMITE, 429: 12 - LIMITE}


def test_zero_turns_the_limit_off_and_records_nothing(
    engine: Engine, client_for: Callable[..., TestClient], usuarios: None
) -> None:
    sem_limite = client_for(engine, sem_login=True, login_max_falhas=0)

    errar(sem_limite, LIMITE * 4)

    assert entrar(sem_limite, senha=SENHA).status_code == 200
    assert tentativas(engine) == []
