from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class AgentAnswer(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str
    sql: str | None
    rows: tuple[dict[str, object], ...]
    row_count: int
    confidence: Confidence
    sources: tuple[str, ...]
    assumptions: tuple[str, ...]
    clarification: str | None
    request_id: str
    prompt_version: str

    @model_validator(mode="after")
    def check_row_count(self) -> Self:
        if self.row_count < len(self.rows):
            raise ValueError("row_count cannot be smaller than the rows sample")
        return self


class Insight(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    metrics_used: tuple[str, ...]
