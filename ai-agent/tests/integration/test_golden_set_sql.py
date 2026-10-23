import asyncio
from pathlib import Path

import pytest
import yaml

from venergy_agent.config import AGENT_ROOT
from venergy_agent.infrastructure.postgres_executor import PostgresQueryExecutor
from venergy_agent.infrastructure.sql_validator import SqlglotValidator

GOLDEN = AGENT_ROOT / "eval" / "golden_set.yaml"
ALLOWED = frozenset({"sem_uc", "sem_faturamento_mensal", "sem_continuidade_alimentador_mensal"})


def answered_items():
    items = yaml.safe_load(Path(GOLDEN).read_text(encoding="utf-8"))["itens"]
    return [item for item in items if item["expected_status"] == "answered"]


@pytest.mark.parametrize("item", answered_items(), ids=lambda item: item["id"])
def test_reference_sql_runs_on_the_database_through_the_agent_path(
    item, agent_database_url, gold_views
):
    validator = SqlglotValidator(dialect="postgres", max_rows=200, allowed_schema="gold")
    executor = PostgresQueryExecutor(agent_database_url, timeout_seconds=10)

    query = validator.validate(item["reference_sql"], ALLOWED)
    result = asyncio.run(executor.execute(query))

    assert result.columns, item["id"]
