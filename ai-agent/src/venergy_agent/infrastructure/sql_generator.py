import secrets
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models import Model

from venergy_agent.domain.question import Question
from venergy_agent.domain.semantic import SemanticLayer
from venergy_agent.domain.sql import AttemptFeedback, SqlDraft
from venergy_agent.infrastructure.prompt_renderer import render_system_prompt, render_user_prompt

OUTPUT_RETRIES = 2


class PydanticAiSqlGenerator:
    def __init__(
        self,
        model: Model,
        prompts_dir: Path,
        prompt_version: str,
        temperature: float,
        nonce: str | None = None,
    ) -> None:
        version_dir = prompts_dir / prompt_version
        self._model = model
        self._system_template = (version_dir / "system.md").read_text(encoding="utf-8")
        self._correction_template = (version_dir / "correction.md").read_text(encoding="utf-8")
        self._temperature = temperature
        self._nonce = nonce or secrets.token_hex(8)

    async def generate(
        self, question: Question, layer: SemanticLayer, feedback: AttemptFeedback | None
    ) -> SqlDraft:
        agent = Agent(
            self._model,
            output_type=SqlDraft,
            system_prompt=render_system_prompt(self._system_template, layer, self._nonce),
            retries=OUTPUT_RETRIES,
        )
        result = await agent.run(
            render_user_prompt(question, feedback, self._correction_template, layer, self._nonce),
            model_settings={"temperature": self._temperature},
        )
        return result.output
