from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AnswerStatus(StrEnum):
    ANSWERED = "answered"
    UNKNOWN = "unknown"
    CLARIFY = "clarify"
    REFUSED = "refused"
    FAILED = "failed"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class AgentAnswer(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str
    status: AnswerStatus
    sql: str | None
    rows: tuple[dict[str, object], ...]
    row_count: int = Field(ge=0)
    truncated: bool
    confidence: Confidence
    sources: tuple[str, ...]
    assumptions: tuple[str, ...]
    clarification: str | None
    refused_reason: str | None
    request_id: str
    model: str
    prompt_version: str
    latency_ms: int = Field(ge=0)

    @field_validator("sql", "clarification", "refused_reason")
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("text must not be blank; use null instead")
        return value

    @model_validator(mode="after")
    def check_status_invariants(self) -> Self:
        if self.row_count < len(self.rows):
            raise ValueError("row_count cannot be smaller than the rows sample")
        if self.truncated and self.status is not AnswerStatus.ANSWERED:
            raise ValueError("only an answered result can be truncated")

        if self.status is AnswerStatus.ANSWERED:
            if self.sql is None:
                raise ValueError("answered requires the executed sql")
            if self.confidence is Confidence.UNKNOWN:
                raise ValueError("answered requires a known confidence")
            if self.refused_reason is not None or self.clarification is not None:
                raise ValueError("answered carries neither refused_reason nor clarification")
            return self

        if self.confidence is not Confidence.UNKNOWN:
            raise ValueError(f"{self.status} requires unknown confidence")
        if self.rows or self.row_count != 0:
            raise ValueError(f"{self.status} cannot carry result rows")

        if self.status is AnswerStatus.CLARIFY:
            if self.clarification is None or self.sql is not None:
                raise ValueError("clarify requires a clarification and no sql")
            if self.refused_reason is not None:
                raise ValueError("clarify carries no refused_reason")
            return self

        if self.refused_reason is None or self.clarification is not None:
            raise ValueError(f"{self.status} requires refused_reason and no clarification")
        return self


class Insight(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    metrics_used: tuple[str, ...]
