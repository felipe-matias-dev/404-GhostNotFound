import secrets
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models import Model

from venergy_agent.domain.conversation import ConversationTurn
from venergy_agent.domain.question import Question
from venergy_agent.domain.semantic import SemanticLayer
from venergy_agent.domain.sql import AttemptFeedback, Generation, SqlDraft
from venergy_agent.infrastructure.history_renderer import render_history
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
        history_file = version_dir / "history.md"
        self._history_template = (
            history_file.read_text(encoding="utf-8") if history_file.exists() else None
        )
        self._temperature = temperature
        self._nonce = nonce or secrets.token_hex(8)

    async def generate(
        self,
        question: Question,
        layer: SemanticLayer,
        feedback: AttemptFeedback | None,
        history: tuple[ConversationTurn, ...] = (),
    ) -> Generation:
        agent = Agent(
            self._model,
            output_type=SqlDraft,
            system_prompt=render_system_prompt(self._system_template, layer, self._nonce),
            retries=OUTPUT_RETRIES,
        )
        prompt = render_user_prompt(
            question, feedback, self._correction_template, layer, self._nonce
        )
        if history and self._history_template is not None:
            prompt = f"{render_history(self._history_template, history, self._nonce)}\n\n{prompt}"
        result = await agent.run(
            prompt,
            model_settings={"temperature": self._temperature},
        )
        usage = result.usage
        return Generation(
            draft=result.output,
            model=result.response.model_name or "desconhecido",
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )
