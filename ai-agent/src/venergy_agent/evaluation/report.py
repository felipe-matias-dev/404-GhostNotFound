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
    reference_error: bool = False
    reference_empty: bool = False
    blocked: bool = False
    prompt_leak: bool
    numeric_fidelity: bool | None
    latency_ms: int | None
    judge_score: int | None = None
    judge_passed: bool | None = None
    judge_rationale: str | None = None
    judge_error: bool = False


class EvaluationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    started_at: datetime
    model: str
    prompt_version: str
    semantic_layer_version: str
    golden_version: str = "desconhecida"
    red_team_version: str = "desconhecida"
    dataset: str = "amostra"
    narrated: bool = True
    judge_model: str | None = None
    judge_prompt_version: str | None = None
    items: tuple[ItemResult, ...]
    metrics: dict[str, float | int | None]
