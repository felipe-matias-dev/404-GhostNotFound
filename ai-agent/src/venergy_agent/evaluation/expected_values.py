"""Grava o que cada item do golden deve mostrar na Gold real (eval/runs_gold/esperado.json).

As referências são executadas no banco carregado, sem chamar modelo. O arquivo fica fora do
Git (DEC-024): tem números da Gold real. Quem confere a tela (T3) lê esse arquivo.
"""

import asyncio
import json
import sys
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from venergy_agent.config import AgentSettings
from venergy_agent.domain.errors import QueryExecutionError, SqlRejected
from venergy_agent.domain.numbers import display_for_unit
from venergy_agent.domain.semantic import unit_of
from venergy_agent.domain.sql import QueryResult
from venergy_agent.evaluation.__main__ import (
    EVAL_DIR,
    RUNS_GOLD_DIR,
    UC_COUNT_SQL,
    check_dataset,
    load_set,
)
from venergy_agent.evaluation.metrics import no_data
from venergy_agent.infrastructure.postgres_executor import PostgresQueryExecutor
from venergy_agent.infrastructure.semantic_source import YamlSemanticLayerSource
from venergy_agent.infrastructure.sql_validator import SqlglotValidator

MAX_ROWS_PER_ITEM = 200
OUTPUT = RUNS_GOLD_DIR / "esperado.json"


def format_pt_br(value: Decimal, unit: str | None) -> str:
    number = display_for_unit(value, unit)
    grouped = format(number, ",f")
    return grouped.replace(",", "_").replace(".", ",").replace("_", ".")


def _cell(value: Any, unit: str | None) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int | float | Decimal):
        return format_pt_br(Decimal(str(value)), unit)
    return str(value)


def build_entry(
    item: Mapping[str, Any],
    columns: Sequence[str],
    rows: Sequence[Mapping[str, Any]],
    units: Mapping[str, str],
    truncated: bool = False,
) -> dict[str, Any]:
    shown = rows[:MAX_ROWS_PER_ITEM]
    cells = [
        {column: _cell(row.get(column), unit_of(column, units)) for column in columns}
        for row in shown
    ]
    entry: dict[str, Any] = {
        "id": item["id"],
        "pergunta": item["question"],
        "status_esperado": item["expected_status"],
        "colunas": list(columns),
        "unidades": {column: unit for column in columns if (unit := unit_of(column, units))},
        "linhas": cells,
        # Verdadeiro quando a execução cortou o resultado no limite. O total exato não é
        # conhecido sem uma consulta de contagem, então o arquivo só diz que há mais linhas.
        "truncado": truncated or len(rows) > MAX_ROWS_PER_ITEM,
    }
    return entry


async def collect(
    items: Sequence[Mapping[str, Any]],
    dataset: str,
    validator: SqlglotValidator,
    executor: PostgresQueryExecutor,
    layer: Any,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Executa as referências. Uma que não roda vira um problema registrado, e a exportação
    segue, como no --only references."""
    entries: list[dict[str, Any]] = []
    problems: list[str] = []
    for item in items:
        sql = item.get("reference_sql")
        if item["expected_status"] != "answered" or not sql or dataset not in item["datasets"]:
            continue
        try:
            result: QueryResult = await executor.execute(
                validator.validate(sql, layer.allowed_views)
            )
        except (SqlRejected, QueryExecutionError) as error:
            problems.append(f"{item['id']}: não executa ({type(error).__name__})")
            continue
        if no_data(result.rows) and not item.get("allow_empty_reference", False):
            problems.append(f"{item['id']}: volta sem dados")
            continue
        entries.append(
            build_entry(
                item,
                result.columns,
                result.rows,
                layer.column_units,
                truncated=result.truncated,
            )
        )
    return entries, problems


async def _run(dataset: str) -> Path:
    settings = AgentSettings()
    layer = await YamlSemanticLayerSource(
        settings.semantic_layer_path, settings.gold_contract_path
    ).load()
    validator = SqlglotValidator(
        dialect=settings.sql_dialect,
        max_rows=settings.max_rows,
        allowed_schema=settings.allowed_schema,
    )
    executor = PostgresQueryExecutor(settings.database_url, settings.query_timeout_seconds)
    counted = await executor.execute(validator.validate(UC_COUNT_SQL, layer.allowed_views))
    check_dataset(dataset, int(counted.rows[0]["total"]))
    version, items = load_set(EVAL_DIR / "golden_set.yaml")
    entries, problems = await collect(items, dataset, validator, executor, layer)
    document = {
        "golden_version": version,
        "dataset": dataset,
        "itens": entries,
        "problemas": problems,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return OUTPUT


def main(argv: list[str]) -> int:
    dataset = argv[0] if argv else "gold_real"
    path = asyncio.run(_run(dataset))
    print(f"valores esperados gravados em {path} (fora do Git)")
    document = json.loads(path.read_text(encoding="utf-8"))
    for problem in document["problemas"]:
        print(f"problema: {problem}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
