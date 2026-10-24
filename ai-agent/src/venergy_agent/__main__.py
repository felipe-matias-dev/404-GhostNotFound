import asyncio
import logging
import sys

from pydantic import ValidationError

from venergy_agent.bootstrap import build_agent
from venergy_agent.config import AgentSettings
from venergy_agent.infrastructure.semantic_source import SemanticLayerError

USAGE = 'uso: uv run python -m venergy_agent "sua pergunta em português"'


async def _ask(question: str) -> str:
    agent = await build_agent(AgentSettings())
    answer = await agent.ask(question, session_id="cli")
    return answer.model_dump_json(indent=2)


def main(argv: list[str]) -> int:
    if not argv:
        print(USAGE, file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    try:
        print(asyncio.run(_ask(" ".join(argv))))
    except ValidationError as error:
        print(f"configuração inválida (ai-agent/.env):\n{error}", file=sys.stderr)
        return 1
    except SemanticLayerError as error:
        print(f"camada semântica inválida:\n{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
