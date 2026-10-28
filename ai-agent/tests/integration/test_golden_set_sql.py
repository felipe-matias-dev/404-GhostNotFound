import asyncio
from pathlib import Path

import pytest
import yaml

from venergy_agent.config import AGENT_ROOT
from venergy_agent.infrastructure.postgres_executor import PostgresQueryExecutor
from venergy_agent.infrastructure.sql_validator import SqlglotValidator
from venergy_agent.infrastructure.views_sql import LAYER_PATH

GOLDEN = AGENT_ROOT / "eval" / "golden_set.yaml"
ALLOWED = frozenset(
    view["name"] for view in yaml.safe_load(LAYER_PATH.read_text(encoding="utf-8"))["views"]
)


def answered_items():
    items = yaml.safe_load(Path(GOLDEN).read_text(encoding="utf-8"))["itens"]
    return [
        item for item in items if item["expected_status"] == "answered" and item["reference_sql"]
    ]


@pytest.mark.parametrize("item", answered_items(), ids=lambda item: item["id"])
def test_reference_sql_runs_on_the_database_through_the_agent_path(
    item, agent_database_url, gold_views
):
    validator = SqlglotValidator(dialect="postgres", max_rows=200, allowed_schema="gold")
    executor = PostgresQueryExecutor(agent_database_url, timeout_seconds=10)

    query = validator.validate(item["reference_sql"], ALLOWED)
    result = asyncio.run(executor.execute(query))

    assert result.columns, item["id"]
