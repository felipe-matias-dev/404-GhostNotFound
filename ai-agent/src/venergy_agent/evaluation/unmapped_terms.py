"""Relatório de termos fora do vocabulário, para uma pessoa decidir o que vira sinônimo.

Lê a auditoria (app.ai_auditoria) com a conexão de leitura do backend, pela variável
VENERGY_UNMAPPED_DATABASE_URL, e imprime em markdown. Não escreve em lugar nenhum: nada entra
no glossário sozinho.
"""

import asyncio
import os
import sys
from collections.abc import Mapping, Sequence
from typing import Any

import psycopg

from venergy_agent.config import AGENT_ROOT, REPO_ROOT
from venergy_agent.domain.vocabulary import unmapped_report, vocabulary_of
from venergy_agent.infrastructure.semantic_source import YamlSemanticLayerSource

URL_VARIABLE = "VENERGY_UNMAPPED_DATABASE_URL"
QUERY = (
    "SELECT pergunta, status, assumptions FROM app.ai_auditoria "
    "WHERE status IN ('clarify', 'unknown') ORDER BY criado_em DESC LIMIT 1000"
)


def format_markdown(report: Sequence[Mapping[str, Any]]) -> str:
    if not report:
        return "Nenhum turno de esclarecimento ou 'não sei' na auditoria.\n"
    lines = [f"# Termos fora do vocabulário ({len(report)} turnos)", ""]
    for item in report:
        lines.append(f"- **{item['pergunta']}** ({item['status']})")
        for word, candidates in item["sugestoes"].items():
            lines.append(f"  - `{word}` lembra: {', '.join(candidates)}")
        for assumption in item["suposicoes"]:
            lines.append(f"  - suposição: {assumption}")
    return "\n".join(lines) + "\n"


async def _vocabulary() -> list[str]:
    # Só a camada é lida aqui: não precisa de AgentSettings, que exige a URL do banco do agente.
    layer = await YamlSemanticLayerSource(
        AGENT_ROOT / "semantic" / "semantic_layer.yaml",
        REPO_ROOT / "contracts" / "gold_schema.yaml",
    ).load()
    columns = [column.name for view in layer.views for column in view.columns]
    return vocabulary_of(layer.glossary, columns)


def main() -> int:
    url = os.environ.get(URL_VARIABLE)
    if not url:
        print(f"defina {URL_VARIABLE} com a conexão de leitura do backend", file=sys.stderr)
        return 1
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(QUERY)
        rows = [
            {"pergunta": pergunta, "status": status, "assumptions": assumptions or []}
            for pergunta, status, assumptions in cursor.fetchall()
        ]
    print(format_markdown(unmapped_report(rows, asyncio.run(_vocabulary()))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
