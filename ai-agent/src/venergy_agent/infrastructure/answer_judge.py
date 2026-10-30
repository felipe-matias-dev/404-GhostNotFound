import secrets
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models import Model

from venergy_agent.domain.answer import AgentAnswer
from venergy_agent.domain.judge import JudgeVerdict
from venergy_agent.infrastructure.prompt_renderer import render_judge_system, render_judge_user

OUTPUT_RETRIES = 2
TEMPERATURE = 0.0


class PydanticAiAnswerJudge:
    def __init__(
        self,
        model: Model,
        prompts_dir: Path,
        prompt_version: str,
        nonce: str | None = None,
    ) -> None:
        template = (prompts_dir / prompt_version / "judge.md").read_text(encoding="utf-8")
        self._model = model
        self._nonce = nonce or secrets.token_hex(8)
        self._system = render_judge_system(template, self._nonce)

    async def judge(self, question: str, answer: AgentAnswer) -> JudgeVerdict:
        agent = Agent(
            self._model,
            output_type=JudgeVerdict,
            system_prompt=self._system,
            retries=OUTPUT_RETRIES,
        )
        run = await agent.run(
            render_judge_user(question, answer, self._nonce),
            model_settings={"temperature": TEMPERATURE},
        )
        return run.output
