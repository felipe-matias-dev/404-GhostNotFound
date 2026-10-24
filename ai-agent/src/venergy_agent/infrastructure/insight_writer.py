import secrets
from collections.abc import Iterator, Mapping
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models import Model

from venergy_agent.domain.answer import Insight
from venergy_agent.domain.numbers import unsupported_numbers
from venergy_agent.infrastructure.prompt_renderer import render_insight_system, render_insight_user


class PydanticAiInsightWriter:
    def __init__(
        self,
        model: Model,
        prompts_dir: Path,
        prompt_version: str,
        temperature: float,
        nonce: str | None = None,
    ) -> None:
        template = (prompts_dir / prompt_version / "insight.md").read_text(encoding="utf-8")
        self._model = model
        self._nonce = nonce or secrets.token_hex(8)
        self._system = render_insight_system(template, self._nonce)
        self._temperature = temperature

    async def narrate(self, screen: str, metrics: Mapping[str, object]) -> Insight | None:
        try:
            agent = Agent(self._model, output_type=str, system_prompt=self._system)
            run = await agent.run(
                render_insight_user(screen, metrics, self._nonce),
                model_settings={"temperature": self._temperature},
            )
        except Exception:
            return None
        text = run.output.strip()
        if not text or unsupported_numbers(text, list(_metric_values(metrics))):
            return None
        return Insight(text=text, metrics_used=tuple(metrics.keys()))


def _metric_values(value: object) -> Iterator[object]:
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _metric_values(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _metric_values(item)
    else:
        yield value
