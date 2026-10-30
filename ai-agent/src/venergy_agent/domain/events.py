from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from venergy_agent.domain.answer import AgentAnswer


class Stage(StrEnum):
    UNDERSTANDING = "understanding"
    QUERYING = "querying"
    CORRECTING = "correcting"
    WRITING = "writing"


STAGE_LABELS: dict[Stage, str] = {
    Stage.UNDERSTANDING: "Entendendo a pergunta",
    Stage.QUERYING: "Consultando os dados",
    Stage.CORRECTING: "Ajustando a consulta",
    Stage.WRITING: "Escrevendo a resposta",
}


class StageEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["stage"] = "stage"
    stage: Stage
    attempt: int = Field(ge=1)

    @computed_field
    @property
    def label(self) -> str:
        return STAGE_LABELS[self.stage]


class AnswerEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["answer"] = "answer"
    answer: AgentAnswer


AgentEvent = Annotated[StageEvent | AnswerEvent, Field(discriminator="type")]
