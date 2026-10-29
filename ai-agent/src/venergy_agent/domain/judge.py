from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from venergy_agent.domain.text import NonBlankText

PASS_SCORE = 4


class JudgeVerdict(BaseModel):
    model_config = ConfigDict(frozen=True)

    score: int = Field(ge=1, le=5)
    passed: bool
    rationale: NonBlankText

    @model_validator(mode="after")
    def check_passed_matches_score(self) -> Self:
        if self.passed != (self.score >= PASS_SCORE):
            raise ValueError(f"passed must be true if and only if score >= {PASS_SCORE}")
        return self
