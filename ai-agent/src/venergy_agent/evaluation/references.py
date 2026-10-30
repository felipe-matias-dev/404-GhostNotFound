from collections.abc import Mapping, Sequence
from typing import Any

from venergy_agent.application.ports import QueryExecutor, SqlValidator
from venergy_agent.domain.errors import QueryExecutionError, SqlRejected
from venergy_agent.evaluation.metrics import no_data


async def check_references(
    items: Sequence[Mapping[str, Any]],
    dataset: str,
    validator: SqlValidator,
    executor: QueryExecutor,
    allowed_views: frozenset[str],
) -> tuple[int, list[str]]:
    checked = 0
    problems = []
    for item in items:
        sql = item.get("reference_sql")
        if item["expected_status"] != "answered" or not sql or dataset not in item["datasets"]:
            continue
        checked += 1
        try:
            result = await executor.execute(validator.validate(sql, allowed_views))
        except (SqlRejected, QueryExecutionError) as error:
            problems.append(f"{item['id']}: não executa ({type(error).__name__})")
            continue
        if no_data(result.rows) and not item.get("allow_empty_reference", False):
            problems.append(f"{item['id']}: volta sem dados")
    return checked, problems
