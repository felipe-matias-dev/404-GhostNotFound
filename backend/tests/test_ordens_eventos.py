import asyncio
import time
from collections.abc import AsyncIterator, Callable, Coroutine
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import psycopg
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from venergy_api.auth import Perfil, UsuarioLogado, criar_token
from venergy_api.avisos_ordens import (
    APLICACAO,
    VagasDeAvisos,
    avisar_mudanca_de_ordem,
    fluxo_de_avisos,
)
from venergy_api.routers import ordens as rota_ordens
from venergy_api.sessao import COOKIE_SESSAO, conferidor_da_sessao
from venergy_api.sse import PING, evento_sse

URL = "/ordens-inspecao/eventos"
LIMITE_DO_TESTE = 5


def rodar[T](corrotina: Coroutine[Any, Any, T]) -> T:
    # O psycopg assíncrono não roda no ProactorEventLoop, o padrão do Python no Windows.
    return asyncio.run(corrotina, loop_factory=asyncio.SelectorEventLoop)


def nada() -> None:
    pass


def sempre() -> bool:
    return True


def vagas(client: TestClient) -> VagasDeAvisos:
    return client.app.state.vagas_avisos_ordens


def database_url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def ouvintes_abertos(engine: Engine) -> int:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT count(*) FROM pg_stat_activity WHERE application_name = :nome"),
            {"nome": APLICACAO},
        ).scalar_one()


def esperar_ouvintes(engine: Engine, esperado: int) -> int:
    # O Postgres solta a conexão fechada um instante depois do cliente.
    for _ in range(20):
        abertos = ouvintes_abertos(engine)
        if abertos == esperado:
            break
        time.sleep(0.1)
    return abertos


def test_route_streams_the_events_and_is_not_read_as_an_order_id(
    engine: Engine, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fluxo_finito(
        database_url: str,
        intervalo_ping: float,
        ao_fechar: Callable[[], None],
        sessao_valida: Callable[[], bool],
    ) -> AsyncIterator[str]:
        try:
            yield PING
            yield evento_sse("ordens", '{"ordem_ids": [7]}')
        finally:
            ao_fechar()

    monkeypatch.setattr(rota_ordens, "fluxo_de_avisos", fluxo_finito)
    monkeypatch.setattr(rota_ordens, "loop_suporta_listen", lambda: True)

    response = client.get(URL)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.text == f'{PING}event: ordens\ndata: {{"ordem_ids": [7]}}\n\n'


def test_route_answers_503_instead_of_opening_a_stream_that_would_abort(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rota_ordens, "loop_suporta_listen", lambda: False)

    response = client.get(URL)

    assert response.status_code == 503
    assert "--reload" in response.json()["detail"]


def test_route_hands_the_stream_a_checker_of_the_request_token(
    client: TestClient, jwt_secret: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    conferencias: list[bool] = []

    async def fluxo_que_confere(
        database_url: str,
        intervalo_ping: float,
        ao_fechar: Callable[[], None],
        sessao_valida: Callable[[], bool],
    ) -> AsyncIterator[str]:
        try:
            conferencias.append(sessao_valida())
            yield PING
        finally:
            ao_fechar()

    monkeypatch.setattr(rota_ordens, "fluxo_de_avisos", fluxo_que_confere)
    monkeypatch.setattr(rota_ordens, "loop_suporta_listen", lambda: True)
    rafael = UsuarioLogado(login="rafael", nome="Rafael", perfil=Perfil.PERDAS)
    vencido = criar_token(rafael, jwt_secret, agora=datetime.now(UTC) - timedelta(hours=9))
    client.cookies.set(COOKIE_SESSAO, vencido)

    assert client.get(URL).status_code == 200
    assert conferencias == [False]


@pytest.mark.parametrize("ocupante", ["teste", "outro"])
def test_route_answers_429_before_opening_a_stream_without_a_free_slot(
    engine: Engine,
    client_for: Callable[..., TestClient],
    monkeypatch: pytest.MonkeyPatch,
    ocupante: str,
) -> None:
    monkeypatch.setattr(rota_ordens, "loop_suporta_listen", lambda: True)
    client = client_for(engine, ordens_avisos_por_usuario=1, ordens_avisos_total=1)
    vagas(client).reservar(ocupante)

    response = client.get(URL)

    assert response.status_code == 429
    assert vagas(client).abertos() == 1


def test_route_answers_503_and_frees_the_slot_when_the_database_refuses(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def banco_lotado(
        database_url: str,
        intervalo_ping: float,
        ao_fechar: Callable[[], None],
        sessao_valida: Callable[[], bool],
    ) -> AsyncIterator[str]:
        try:
            raise psycopg.OperationalError("too many clients already")
            yield PING
        finally:
            ao_fechar()

    monkeypatch.setattr(rota_ordens, "fluxo_de_avisos", banco_lotado)
    monkeypatch.setattr(rota_ordens, "loop_suporta_listen", lambda: True)

    response = client.get(URL)

    assert response.status_code == 503
    assert vagas(client).abertos() == 0


def test_slots_are_limited_per_login_and_in_total() -> None:
    limite = VagasDeAvisos(por_usuario=2, total=3)

    assert [limite.reservar("rafael") for _ in range(3)] == [True, True, False]
    assert limite.reservar("camila") is True
    assert limite.reservar("henrique") is False

    limite.liberar("rafael")

    assert limite.reservar("henrique") is True
    assert limite.abertos() == 3


def test_route_requires_login(engine: Engine, client_for: Callable[..., TestClient]) -> None:
    assert client_for(engine, sem_login=True).get(URL).status_code == 401


def test_stream_opens_with_a_ping_only_after_it_is_listening(engine: Engine) -> None:
    async def abrir() -> str:
        fluxo = fluxo_de_avisos(database_url(engine), 5, nada, sempre)
        try:
            async with asyncio.timeout(LIMITE_DO_TESTE):
                primeiro = await anext(fluxo)
                avisar_em_outra_conexao()
                return primeiro + await anext(fluxo)
        finally:
            await fluxo.aclose()

    def avisar_em_outra_conexao() -> None:
        with Session(engine) as session:
            avisar_mudanca_de_ordem(session, [7])
            session.commit()

    assert rodar(abrir()) == f'{PING}event: ordens\ndata: {{"ordem_ids": [7]}}\n\n'


def test_stream_pings_while_nothing_happens(engine: Engine) -> None:
    async def colher() -> list[str]:
        fluxo = fluxo_de_avisos(database_url(engine), 0.05, nada, sempre)
        try:
            async with asyncio.timeout(LIMITE_DO_TESTE):
                return [await anext(fluxo) for _ in range(3)]
        finally:
            await fluxo.aclose()

    assert rodar(colher()) == [PING, PING, PING]


def test_closing_the_stream_releases_its_database_connection(engine: Engine) -> None:
    async def abrir_e_fechar() -> int:
        fluxo = fluxo_de_avisos(database_url(engine), 5, nada, sempre)
        await anext(fluxo)
        abertos = ouvintes_abertos(engine)
        await fluxo.aclose()
        return abertos

    assert rodar(abrir_e_fechar()) == 1
    assert esperar_ouvintes(engine, 0) == 0


def test_closing_the_stream_calls_ao_fechar_once(engine: Engine) -> None:
    fechamentos: list[None] = []

    async def abrir_e_fechar() -> None:
        fluxo = fluxo_de_avisos(database_url(engine), 5, lambda: fechamentos.append(None), sempre)
        await anext(fluxo)
        await fluxo.aclose()

    rodar(abrir_e_fechar())

    assert len(fechamentos) == 1


def test_a_refused_connection_still_calls_ao_fechar(engine: Engine) -> None:
    fechamentos: list[None] = []
    sem_banco = engine.url.set(database="banco_que_nao_existe")

    async def abrir() -> None:
        fluxo = fluxo_de_avisos(
            sem_banco.render_as_string(hide_password=False),
            5,
            lambda: fechamentos.append(None),
            sempre,
        )
        await anext(fluxo)

    with pytest.raises(psycopg.OperationalError):
        rodar(abrir())
    assert len(fechamentos) == 1


def test_stream_ends_at_the_ping_after_the_session_stops_being_valid(engine: Engine) -> None:
    fechamentos: list[None] = []
    conferencias = iter([True, False])

    async def colher() -> list[str]:
        fluxo = fluxo_de_avisos(
            database_url(engine),
            0.05,
            lambda: fechamentos.append(None),
            lambda: next(conferencias),
        )
        async with asyncio.timeout(LIMITE_DO_TESTE):
            return [item async for item in fluxo]

    assert rodar(colher()) == [PING, PING]
    assert len(fechamentos) == 1


SEGREDO = "segredo-de-teste-com-tamanho-suficiente-para-hs256"


def requisicao_com_cookie(cookie: str | None) -> Request:
    headers = [(b"cookie", f"{COOKIE_SESSAO}={cookie}".encode())] if cookie else []
    app = SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(jwt_secret=SEGREDO)))
    return Request({"type": "http", "headers": headers, "app": app})


@pytest.mark.parametrize(
    ("horas_desde_o_login", "esperado"), [(0, True), (7.9, True), (8.1, False), (None, False)]
)
def test_session_checker_follows_the_token_the_request_arrived_with(
    horas_desde_o_login: float | None, esperado: bool
) -> None:
    rafael = UsuarioLogado(login="rafael", nome="Rafael", perfil=Perfil.PERDAS)
    token = (
        None
        if horas_desde_o_login is None
        else criar_token(
            rafael, SEGREDO, agora=datetime.now(UTC) - timedelta(hours=horas_desde_o_login)
        )
    )

    assert conferidor_da_sessao(requisicao_com_cookie(token))() is esperado
