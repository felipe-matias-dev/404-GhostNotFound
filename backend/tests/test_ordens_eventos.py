import asyncio
import time
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from venergy_api.avisos_ordens import (
    APLICACAO,
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
    async def fluxo_finito(database_url: str, intervalo_ping: float) -> AsyncIterator[str]:
        yield PING
        yield evento_sse("ordens", '{"ordem_ids": [7]}')

    monkeypatch.setattr(rota_ordens, "fluxo_de_avisos", fluxo_finito)

    response = client.get(URL)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.text == f'{PING}event: ordens\ndata: {{"ordem_ids": [7]}}\n\n'


def test_route_requires_login(engine: Engine, client_for: Callable[..., TestClient]) -> None:
    assert client_for(engine, sem_login=True).get(URL).status_code == 401


def test_stream_opens_with_a_ping_only_after_it_is_listening(engine: Engine) -> None:
    async def abrir() -> str:
        fluxo = fluxo_de_avisos(database_url(engine), 5)
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
        fluxo = fluxo_de_avisos(database_url(engine), 0.05)
        try:
            async with asyncio.timeout(LIMITE_DO_TESTE):
                return [await anext(fluxo) for _ in range(3)]
        finally:
            await fluxo.aclose()

    assert rodar(colher()) == [PING, PING, PING]


def test_closing_the_stream_releases_its_database_connection(engine: Engine) -> None:
    async def abrir_e_fechar() -> int:
        fluxo = fluxo_de_avisos(database_url(engine), 5)
        await anext(fluxo)
        abertos = ouvintes_abertos(engine)
        await fluxo.aclose()
        return abertos

    assert rodar(abrir_e_fechar()) == 1
    assert esperar_ouvintes(engine, 0) == 0
