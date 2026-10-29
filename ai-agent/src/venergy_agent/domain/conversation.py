from pydantic import BaseModel, ConfigDict

from venergy_agent.domain.answer import AnswerStatus
from venergy_agent.domain.text import NonBlankText


class ConversationTurn(BaseModel):
    model_config = ConfigDict(frozen=True)

    question: NonBlankText
    sql: NonBlankText | None
    status: AnswerStatus
