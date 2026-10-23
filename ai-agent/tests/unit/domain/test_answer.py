import pytest
from pydantic import ValidationError

from venergy_agent.domain.answer import AgentAnswer, AnswerStatus, Confidence

COMMON = {
    "answer": "texto",
    "truncated": False,
    "sources": ("sem_uc",),
    "assumptions": (),
    "request_id": "r1",
    "model": "google-gla:gemini-3.1-flash-lite",
    "prompt_version": "v1",
    "latency_ms": 12,
}

BY_STATUS = {
    AnswerStatus.ANSWERED: {
        "sql": "SELECT 1",
        "rows": ({"total": 1},),
        "row_count": 1,
        "confidence": Confidence.HIGH,
        "clarification": None,
        "refused_reason": None,
    },
    AnswerStatus.CLARIFY: {
        "sql": None,
        "rows": (),
        "row_count": 0,
        "confidence": Confidence.UNKNOWN,
        "clarification": "qual mês?",
        "refused_reason": None,
    },
    AnswerStatus.UNKNOWN: {
        "sql": None,
        "rows": (),
        "row_count": 0,
        "confidence": Confidence.UNKNOWN,
        "clarification": None,
        "refused_reason": "motivo",
    },
    AnswerStatus.REFUSED: {
        "sql": None,
        "rows": (),
        "row_count": 0,
        "confidence": Confidence.UNKNOWN,
        "clarification": None,
        "refused_reason": "motivo",
    },
    AnswerStatus.FAILED: {
        "sql": None,
        "rows": (),
        "row_count": 0,
        "confidence": Confidence.UNKNOWN,
        "clarification": None,
        "refused_reason": "motivo",
    },
}


def answer(status, **overrides):
    return AgentAnswer(**{**COMMON, **BY_STATUS[status], "status": status, **overrides})


@pytest.mark.parametrize("status", list(AnswerStatus))
def test_a_valid_result_is_accepted_for_every_status(status):
    assert answer(status).status is status


def test_failed_may_keep_the_last_sql_for_audit():
    assert answer(AnswerStatus.FAILED, sql="SELECT 1").sql == "SELECT 1"


@pytest.mark.parametrize(
    ("status", "overrides"),
    [
        pytest.param(AnswerStatus.ANSWERED, {"sql": None}, id="answered-without-sql"),
        pytest.param(
            AnswerStatus.ANSWERED,
            {"confidence": Confidence.UNKNOWN},
            id="answered-unknown-confidence",
        ),
        pytest.param(
            AnswerStatus.ANSWERED, {"refused_reason": "x"}, id="answered-with-refused-reason"
        ),
        pytest.param(
            AnswerStatus.ANSWERED, {"clarification": "x"}, id="answered-with-clarification"
        ),
        pytest.param(AnswerStatus.CLARIFY, {"clarification": None}, id="clarify-without-question"),
        pytest.param(AnswerStatus.CLARIFY, {"sql": "SELECT 1"}, id="clarify-with-sql"),
        pytest.param(
            AnswerStatus.CLARIFY, {"rows": ({"a": 1},), "row_count": 1}, id="clarify-with-rows"
        ),
        pytest.param(AnswerStatus.CLARIFY, {"row_count": 3}, id="clarify-with-row-count"),
        pytest.param(
            AnswerStatus.CLARIFY, {"confidence": Confidence.HIGH}, id="clarify-known-confidence"
        ),
        pytest.param(
            AnswerStatus.CLARIFY, {"refused_reason": "x"}, id="clarify-with-refused-reason"
        ),
        pytest.param(AnswerStatus.UNKNOWN, {"refused_reason": None}, id="unknown-without-reason"),
        pytest.param(AnswerStatus.UNKNOWN, {"clarification": "x"}, id="unknown-with-clarification"),
        pytest.param(
            AnswerStatus.UNKNOWN, {"rows": ({"a": 1},), "row_count": 1}, id="unknown-with-rows"
        ),
        pytest.param(
            AnswerStatus.UNKNOWN, {"confidence": Confidence.HIGH}, id="unknown-known-confidence"
        ),
        pytest.param(AnswerStatus.REFUSED, {"refused_reason": None}, id="refused-without-reason"),
        pytest.param(AnswerStatus.REFUSED, {"clarification": "x"}, id="refused-with-clarification"),
        pytest.param(AnswerStatus.FAILED, {"refused_reason": None}, id="failed-without-reason"),
        pytest.param(
            AnswerStatus.FAILED, {"confidence": Confidence.LOW}, id="failed-known-confidence"
        ),
    ],
)
def test_status_invariants_reject_each_violation(status, overrides):
    with pytest.raises(ValidationError):
        answer(status, **overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"refused_reason": ""}, id="blank-refused-reason"),
        pytest.param({"refused_reason": "   "}, id="spaces-refused-reason"),
        pytest.param({"clarification": ""}, id="blank-clarification"),
        pytest.param({"sql": ""}, id="blank-sql"),
    ],
)
def test_blank_text_is_rejected_instead_of_passing_as_filled(overrides):
    status = AnswerStatus.ANSWERED if "sql" in overrides else AnswerStatus.UNKNOWN
    with pytest.raises(ValidationError):
        answer(status, **overrides)


def test_only_answered_results_can_be_truncated():
    with pytest.raises(ValidationError, match="truncated"):
        answer(AnswerStatus.UNKNOWN, truncated=True)


def test_latency_cannot_be_negative():
    with pytest.raises(ValidationError):
        answer(AnswerStatus.ANSWERED, latency_ms=-1)


def test_row_count_cannot_be_negative():
    with pytest.raises(ValidationError):
        answer(AnswerStatus.ANSWERED, row_count=-3)


def test_row_count_below_sample_size_is_rejected():
    with pytest.raises(ValidationError, match="row_count"):
        answer(AnswerStatus.ANSWERED, rows=({"a": 1}, {"a": 2}), row_count=1)
