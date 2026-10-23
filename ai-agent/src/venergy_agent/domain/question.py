from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from venergy_agent.domain.text import NonBlankText


class Question(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: NonBlankText
    session_id: str
    request_id: str = Field(default_factory=lambda: uuid4().hex)
