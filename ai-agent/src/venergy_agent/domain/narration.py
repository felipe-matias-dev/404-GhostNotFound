from pydantic import BaseModel, ConfigDict


class Narration(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    input_tokens: int = 0
    output_tokens: int = 0
