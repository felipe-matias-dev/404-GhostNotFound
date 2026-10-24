import pytest
import yaml

from venergy_agent.config import AGENT_ROOT, REPO_ROOT
from venergy_agent.domain.answer import AnswerStatus
from venergy_agent.infrastructure.semantic_source import read_documents, view_definitions
from venergy_agent.infrastructure.sql_validator import SqlglotValidator

GOLDEN = AGENT_ROOT / "eval" / "golden_set.yaml"
GUIDE_CATEGORIES = {
    "simples",
    "juncao",
    "temporal",
    "sinonimo",
    "sem_resposta",
    "ambigua",
    "manipulacao",
}


@pytest.fixture(scope="module")
def items():
    return yaml.safe_load(GOLDEN.read_text(encoding="utf-8"))["itens"]


@pytest.fixture(scope="module")
def allowed_views():
    layer, contract = read_documents(
        AGENT_ROOT / "semantic" / "semantic_layer.yaml",
        REPO_ROOT / "contracts" / "gold_schema.yaml",
    )
    return frozenset(view.name for view in view_definitions(layer, contract))


def test_has_at_least_40_questions(items):
    assert len(items) >= 40


def test_ids_and_questions_are_unique(items):
    assert len({item["id"] for item in items}) == len(items)
    assert len({item["question"] for item in items}) == len(items)


def test_expected_status_is_a_real_answer_status_and_never_failed(items):
    valid = {status.value for status in AnswerStatus} - {"failed"}

    assert {item["expected_status"] for item in items} <= valid


def test_reference_sql_exists_exactly_when_the_answer_is_answered(items):
    for item in items:
        if item["expected_status"] == "answered":
            assert item["reference_sql"], item["id"]
        else:
            assert item["reference_sql"] is None, item["id"]


def test_every_reference_sql_passes_the_agent_validator(items, allowed_views):
    validator = SqlglotValidator(dialect="postgres", max_rows=200, allowed_schema="gold")

    for item in items:
        if item["reference_sql"]:
            validator.validate(item["reference_sql"], allowed_views)


def test_at_least_8_questions_have_no_answer_in_the_data(items):
    unknown = [item for item in items if item["expected_status"] == "unknown"]

    assert len(unknown) >= 8


def test_at_least_5_injection_attempts(items):
    injections = [item for item in items if item["category"] == "injecao"]

    assert len(injections) >= 5


def test_every_guide_category_is_covered(items):
    assert {item["category"] for item in items} >= GUIDE_CATEGORIES


def test_follow_up_points_to_an_existing_item(items):
    ids = {item["id"] for item in items}

    for item in items:
        if item["follow_up_of"] is not None:
            assert item["follow_up_of"] in ids, item["id"]


def test_review_field_is_null_or_the_name_of_who_reviewed_the_item(items):
    for item in items:
        assert "revisado_por" in item, item["id"]
        reviewer = item["revisado_por"]
        assert reviewer is None or (isinstance(reviewer, str) and reviewer.strip()), item["id"]
