import pytest
from pydantic import ValidationError

from venergy_agent.domain.answer import AgentAnswer, AnswerStatus, Confidence


def answer(**overrides):
    values = {
        "answer": "texto",
        "status": AnswerStatus.ANSWERED,
        "sql": "SELECT 1",
        "rows": ({"total": 1},),
        "row_count": 1,
        "truncated": False,
        "confidence": Confidence.HIGH,
        "sources": ("sem_uc",),
        "assumptions": (),
        "clarification": None,
        "refused_reason": None,
        "request_id": "r1",
        "model": "google-gla:gemini-3.1-flash-lite",
        "prompt_version": "v1",
        "latency_ms": 12,
    }
    values.update(overrides)
    return AgentAnswer(**values)


def test_valid_answered_result_is_accepted():
    assert answer().status is AnswerStatus.ANSWERED


@pytest.mark.parametrize(
    "status",
    [AnswerStatus.UNKNOWN, AnswerStatus.REFUSED, AnswerStatus.FAILED],
)
def test_terminal_statuses_carry_a_reason_and_no_rows(status):
    result = answer(
        status=status,
        sql=None,
        rows=(),
        row_count=0,
        confidence=Confidence.UNKNOWN,
        refused_reason="motivo",
    )

    assert result.refused_reason == "motivo"


def test_clarify_carries_the_question_and_no_sql():
    result = answer(
        status=AnswerStatus.CLARIFY,
        sql=None,
        rows=(),
        row_count=0,
        confidence=Confidence.UNKNOWN,
        clarification="qual mês?",
    )

    assert result.clarification == "qual mês?"


@pytest.mark.parametrize(
    "overrides",
    [
        {"row_count": 0},
        {"sql": None},
        {"confidence": Confidence.UNKNOWN},
        {"refused_reason": "não deveria existir"},
        {"clarification": "não deveria existir"},
    ],
    ids=[
        "row_count_below_sample",
        "answered_without_executed_sql",
        "answered_with_unknown_confidence",
        "answered_with_refused_reason",
        "answered_with_clarification",
    ],
)
def test_answered_invariants(overrides):
    with pytest.raises(ValidationError):
        answer(**overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "status": AnswerStatus.CLARIFY,
            "sql": None,
            "rows": (),
            "row_count": 0,
            "confidence": Confidence.UNKNOWN,
            "clarification": None,
        },
        {
            "status": AnswerStatus.CLARIFY,
            "sql": "SELECT 1",
            "rows": (),
            "row_count": 0,
            "confidence": Confidence.UNKNOWN,
            "clarification": "qual mês?",
        },
        {
            "status": AnswerStatus.CLARIFY,
            "sql": None,
            "rows": (),
            "row_count": 0,
            "confidence": Confidence.UNKNOWN,
            "clarification": "qual mês?",
            "refused_reason": "não deveria existir",
        },
        {
            "status": AnswerStatus.UNKNOWN,
            "sql": None,
            "rows": (),
            "row_count": 0,
            "confidence": Confidence.UNKNOWN,
            "refused_reason": None,
        },
        {
            "status": AnswerStatus.UNKNOWN,
            "sql": None,
            "rows": (),
            "row_count": 0,
            "confidence": Confidence.UNKNOWN,
            "refused_reason": "x",
            "clarification": "qual?",
        },
        {
            "status": AnswerStatus.REFUSED,
            "sql": None,
            "rows": ({"a": 1},),
            "row_count": 1,
            "confidence": Confidence.UNKNOWN,
            "refused_reason": "x",
        },
        {
            "status": AnswerStatus.FAILED,
            "sql": None,
            "rows": (),
            "row_count": 0,
            "confidence": Confidence.HIGH,
            "refused_reason": "x",
        },
    ],
)
def test_non_answered_statuses_invariants(overrides):
    with pytest.raises(ValidationError):
        answer(**overrides)


def test_only_answered_results_can_be_truncated():
    with pytest.raises(ValidationError):
        answer(
            status=AnswerStatus.UNKNOWN,
            sql=None,
            rows=(),
            row_count=0,
            truncated=True,
            confidence=Confidence.UNKNOWN,
            refused_reason="x",
        )


def test_latency_cannot_be_negative():
    with pytest.raises(ValidationError):
        answer(latency_ms=-1)


def test_row_count_below_sample_size_is_rejected():
    with pytest.raises(ValidationError, match="row_count"):
        answer(rows=({"a": 1}, {"a": 2}), row_count=1)
