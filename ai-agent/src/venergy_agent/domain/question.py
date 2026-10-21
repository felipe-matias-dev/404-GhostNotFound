from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Question(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: Text
    session_id: str
    request_id: str = Field(default_factory=lambda: uuid4().hex)
