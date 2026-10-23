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

ANSWERED = {
    "sql": "SELECT 1",
    "rows": ({"total": 1},),
    "row_count": 1,
    "confidence": Confidence.HIGH,
    "clarification": None,
    "refused_reason": None,
}

CLARIFY = {
    "sql": None,
    "rows": (),
    "row_count": 0,
    "confidence": Confidence.UNKNOWN,
    "clarification": "qual mês?",
    "refused_reason": None,
}

NO_RESULT = {
    "sql": None,
    "rows": (),
    "row_count": 0,
    "confidence": Confidence.UNKNOWN,
    "clarification": None,
    "refused_reason": "motivo",
}

BY_STATUS = {
    AnswerStatus.ANSWERED: ANSWERED,
    AnswerStatus.CLARIFY: CLARIFY,
    AnswerStatus.UNKNOWN: NO_RESULT,
    AnswerStatus.REFUSED: NO_RESULT,
    AnswerStatus.FAILED: NO_RESULT,
}

NON_ANSWERED = (AnswerStatus.UNKNOWN, AnswerStatus.REFUSED, AnswerStatus.FAILED)


def answer(status, **overrides):
    return AgentAnswer(**{**COMMON, **BY_STATUS[status], "status": status, **overrides})


@pytest.mark.parametrize("status", list(AnswerStatus))
def test_a_valid_result_is_accepted_for_every_status(status):
    assert answer(status).status is status


def test_failed_may_keep_the_last_sql_for_audit():
    assert answer(AnswerStatus.FAILED, sql="SELECT 1").sql == "SELECT 1"


def test_answered_truncated_with_rows_is_accepted():
    assert answer(AnswerStatus.ANSWERED, truncated=True, row_count=200).truncated


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
        pytest.param(
            AnswerStatus.ANSWERED,
            {"truncated": True, "row_count": 0, "rows": ()},
            id="truncated-without-rows",
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
    ]
    + [
        pytest.param(status, {"refused_reason": None}, id=f"{status.value}-without-reason")
        for status in NON_ANSWERED
    ]
    + [
        pytest.param(status, {"clarification": "x"}, id=f"{status.value}-with-clarification")
        for status in NON_ANSWERED
    ]
    + [
        pytest.param(status, {"rows": ({"a": 1},), "row_count": 1}, id=f"{status.value}-with-rows")
        for status in NON_ANSWERED
    ]
    + [
        pytest.param(status, {"confidence": Confidence.HIGH}, id=f"{status.value}-known-confidence")
        for status in NON_ANSWERED
    ]
    + [
        pytest.param(status, {"truncated": True}, id=f"{status.value}-truncated")
        for status in NON_ANSWERED
    ],
)
def test_status_invariants_reject_each_violation(status, overrides):
    with pytest.raises(ValidationError):
        answer(status, **overrides)


@pytest.mark.parametrize(
    "field",
    ["answer", "sql", "clarification", "refused_reason", "model", "request_id", "prompt_version"],
)
@pytest.mark.parametrize("blank", ["", "   "], ids=["empty", "spaces"])
def test_blank_text_is_rejected_in_every_text_field(field, blank):
    status = AnswerStatus.ANSWERED
    overrides = {field: blank}
    if field == "clarification":
        status = AnswerStatus.CLARIFY
        overrides = {
            "clarification": blank,
            "sql": None,
            "rows": (),
            "row_count": 0,
            "confidence": Confidence.UNKNOWN,
            "refused_reason": None,
        }
    if field == "refused_reason":
        status = AnswerStatus.UNKNOWN
    with pytest.raises(ValidationError):
        answer(status, **overrides)


def test_latency_cannot_be_negative():
    with pytest.raises(ValidationError):
        answer(AnswerStatus.ANSWERED, latency_ms=-1)


def test_row_count_cannot_be_negative():
    with pytest.raises(ValidationError):
        answer(AnswerStatus.ANSWERED, row_count=-3)


def test_row_count_below_sample_size_is_rejected():
    with pytest.raises(ValidationError, match="row_count"):
        answer(AnswerStatus.ANSWERED, rows=({"a": 1}, {"a": 2}), row_count=1)
