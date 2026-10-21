from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from venergy_agent.domain.errors import ErrorKind


class DraftStatus(StrEnum):
    OK = "ok"
    UNKNOWN = "unknown"
    CLARIFY = "clarify"
    REFUSE = "refuse"


def _has_text(value: str | None) -> bool:
    return value is not None and value.strip() != ""


class SqlDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: DraftStatus
    sql: str | None = None
    views_used: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    clarification_question: str | None = None

    @model_validator(mode="after")
    def check_consistency(self) -> Self:
        if self.status is DraftStatus.OK and not _has_text(self.sql):
            raise ValueError("status ok requires sql")
        if self.status is DraftStatus.CLARIFY and not _has_text(self.clarification_question):
            raise ValueError("status clarify requires clarification_question")
        if self.status is not DraftStatus.OK and self.sql is not None:
            raise ValueError("sql is only allowed with status ok")
        return self


class AttemptFeedback(BaseModel):
    model_config = ConfigDict(frozen=True)

    previous_sql: str
    error_kind: ErrorKind
    message: str


class ValidatedQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    sql: str
    views: frozenset[str]
    applied_limit: int
    limit_imposed: bool


class QueryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    columns: tuple[str, ...]
    rows: tuple[dict[str, object], ...]
    row_count: int
    truncated: bool
