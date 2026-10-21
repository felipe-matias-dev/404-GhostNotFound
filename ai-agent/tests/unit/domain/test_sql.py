import pytest
from pydantic import ValidationError

from venergy_agent.domain.sql import DraftStatus, SqlDraft


@pytest.mark.parametrize(
    "fields",
    [
        {"status": "ok"},
        {"status": "ok", "sql": "   "},
        {"status": "clarify"},
        {"status": "clarify", "clarification_question": " "},
        {"status": "unknown", "sql": "SELECT 1"},
        {"status": "refuse", "sql": "DROP TABLE x"},
    ],
)
def test_inconsistent_draft_is_rejected(fields):
    with pytest.raises(ValidationError):
        SqlDraft(**fields)


def test_ok_draft_is_accepted():
    draft = SqlDraft(status="ok", sql="SELECT 1", views_used=("sem_faturamento_mensal",))

    assert draft.status is DraftStatus.OK
