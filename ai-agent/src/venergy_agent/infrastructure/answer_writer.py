import secrets
from collections.abc import Mapping
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models import Model

from venergy_agent.domain.narration import Narration
from venergy_agent.domain.question import Question
from venergy_agent.domain.sql import QueryResult, SqlDraft
from venergy_agent.infrastructure.prompt_renderer import render_answer_system, render_answer_user


class PydanticAiAnswerWriter:
    def __init__(
        self,
        model: Model,
        prompts_dir: Path,
        prompt_version: str,
        temperature: float,
        nonce: str | None = None,
        units: Mapping[str, str] | None = None,
    ) -> None:
        template = (prompts_dir / prompt_version / "answer.md").read_text(encoding="utf-8")
        self._model = model
        self._nonce = nonce or secrets.token_hex(8)
        self._system = render_answer_system(template, self._nonce)
        self._temperature = temperature
        self._units = dict(units or {})

    async def write(self, question: Question, draft: SqlDraft, result: QueryResult) -> Narration:
        agent = Agent(self._model, output_type=str, system_prompt=self._system)
        run = await agent.run(
            render_answer_user(question, draft, result, self._nonce, self._units),
            model_settings={"temperature": self._temperature},
        )
        usage = run.usage
        return Narration(
            text=run.output.strip(),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )
