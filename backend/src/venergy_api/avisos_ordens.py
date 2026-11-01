"""Aviso de que ordens de inspeção mudaram, entregue às telas abertas pelo próprio Postgres."""

import asyncio
import json
import sys
from collections.abc import AsyncIterator, Sequence

import psycopg
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from venergy_api.sse import PING, evento_sse

CANAL = "ordens_inspecao"
EVENTO = "ordens"
INTERVALO_PING_SEGUNDOS = 15
APLICACAO = "venergy-ordens-sse"

# O payload de um NOTIFY tem no máximo 8000 bytes. 500 ids ficam bem abaixo disso; passando
# disso o aviso vai sem a lista, porque a tela só precisa saber que algo mudou e refaz o GET.
MAX_IDS_NO_AVISO = 500


def avisar_mudanca_de_ordem(session: Session, ordem_ids: Sequence[int]) -> None:
    """Enfileira o aviso na transação aberta: o Postgres entrega no commit e descarta no rollback.

    Um aviso por transação, e não um por ordem: um lote de 30 ordens faria cada tela refazer a
    consulta 30 vezes.
    """
    ids = list(ordem_ids) if len(ordem_ids) <= MAX_IDS_NO_AVISO else None
    session.execute(
        text("SELECT pg_notify(:canal, :payload)"),
        {"canal": CANAL, "payload": json.dumps({"ordem_ids": ids})},
    )


def loop_suporta_listen() -> bool:
    """O psycopg assíncrono não roda no ProactorEventLoop, o padrão do Python no Windows.

    O uvicorn usa o SelectorEventLoop no Linux (Docker, CI) e no Windows com --reload.
    """
    ruim = sys.platform == "win32" and isinstance(
        asyncio.get_running_loop(), asyncio.ProactorEventLoop
    )
    return not ruim


async def fluxo_de_avisos(database_url: str, intervalo_ping: float) -> AsyncIterator[str]:
    """Os avisos de ordens como eventos SSE, de uma conexão LISTEN própria por tela aberta.

    O primeiro item sai depois do LISTEN: quando o navegador considera a conexão aberta, nenhum
    aviso se perde entre o abrir e o ouvir. Um aviso não é durável, então o que acontecer com a
    tela desconectada se perde, e a tela invalida os dados ao reconectar.
    """
    url = make_url(database_url).set(drivername="postgresql").render_as_string(hide_password=False)
    async with await psycopg.AsyncConnection.connect(
        url, autocommit=True, application_name=APLICACAO
    ) as conexao:
        await conexao.execute(f"LISTEN {CANAL}")
        yield PING
        while True:
            async for aviso in conexao.notifies(timeout=intervalo_ping):
                yield evento_sse(EVENTO, aviso.payload)
            yield PING
