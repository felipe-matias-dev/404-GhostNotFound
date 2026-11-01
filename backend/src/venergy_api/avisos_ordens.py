"""Aviso de que ordens de inspeção mudaram, entregue às telas abertas pelo próprio Postgres."""

import json
from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

CANAL = "ordens_inspecao"

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
