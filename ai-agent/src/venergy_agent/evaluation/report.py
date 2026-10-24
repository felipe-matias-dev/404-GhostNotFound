from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from venergy_agent.domain.answer import AnswerStatus


class ItemResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    kind: Literal["golden", "red_team"]
    category: str
    expected_status: AnswerStatus
    status: AnswerStatus
    sql: str | None
    matched: bool | None
    violation: bool
    prompt_leak: bool
    numeric_fidelity: bool | None
    latency_ms: int | None


class EvaluationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    started_at: datetime
    model: str
    prompt_version: str
    semantic_layer_version: str
    items: tuple[ItemResult, ...]
    metrics: dict[str, float | int | None]
