import pytest
import yaml

from venergy_agent.infrastructure.sql_validator import SqlglotValidator
from venergy_agent.infrastructure.views_sql import LAYER_PATH

LAYER = yaml.safe_load(LAYER_PATH.read_text(encoding="utf-8"))
VIEWS = frozenset(view["name"] for view in LAYER["views"])


@pytest.mark.parametrize(
    "example",
    [example for example in LAYER["examples"] if example["sql"]],
    ids=lambda example: example["question"],
)
def test_every_example_sql_passes_the_validator(example):
    validator = SqlglotValidator(dialect="postgres", max_rows=200, allowed_schema="gold")

    validator.validate(example["sql"], VIEWS)
