import asyncio
import time
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from venergy_api.avisos_ordens import (
    APLICACAO,
    VagasDeAvisos,
    avisar_mudanca_de_ordem,
    fluxo_de_avisos,
)
from venergy_api.routers import ordens as rota_ordens
from venergy_api.sse import PING, evento_sse

URL = "/ordens-inspecao/eventos"
LIMITE_DO_TESTE = 5


def rodar[T](corrotina: Coroutine[Any, Any, T]) -> T:
    # O psycopg assíncrono não roda no ProactorEventLoop, o padrão do Python no Windows.
    return asyncio.run(corrotina, loop_factory=asyncio.SelectorEventLoop)


def nada() -> None:
    pass


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
        database_url: str, intervalo_ping: float, ao_fechar: Callable[[], None]
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
        database_url: str, intervalo_ping: float, ao_fechar: Callable[[], None]
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
        fluxo = fluxo_de_avisos(database_url(engine), 5, nada)
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
        fluxo = fluxo_de_avisos(database_url(engine), 0.05, nada)
        try:
            async with asyncio.timeout(LIMITE_DO_TESTE):
                return [await anext(fluxo) for _ in range(3)]
        finally:
            await fluxo.aclose()

    assert rodar(colher()) == [PING, PING, PING]


def test_closing_the_stream_releases_its_database_connection(engine: Engine) -> None:
    async def abrir_e_fechar() -> int:
        fluxo = fluxo_de_avisos(database_url(engine), 5, nada)
        await anext(fluxo)
        abertos = ouvintes_abertos(engine)
        await fluxo.aclose()
        return abertos

    assert rodar(abrir_e_fechar()) == 1
    assert esperar_ouvintes(engine, 0) == 0


def test_closing_the_stream_calls_ao_fechar_once(engine: Engine) -> None:
    fechamentos: list[None] = []

    async def abrir_e_fechar() -> None:
        fluxo = fluxo_de_avisos(database_url(engine), 5, lambda: fechamentos.append(None))
        await anext(fluxo)
        await fluxo.aclose()

    rodar(abrir_e_fechar())

    assert len(fechamentos) == 1


def test_a_refused_connection_still_calls_ao_fechar(engine: Engine) -> None:
    fechamentos: list[None] = []
    sem_banco = engine.url.set(database="banco_que_nao_existe")

    async def abrir() -> None:
        fluxo = fluxo_de_avisos(
            sem_banco.render_as_string(hide_password=False), 5, lambda: fechamentos.append(None)
        )
        await anext(fluxo)

    with pytest.raises(psycopg.OperationalError):
        rodar(abrir())
    assert len(fechamentos) == 1
