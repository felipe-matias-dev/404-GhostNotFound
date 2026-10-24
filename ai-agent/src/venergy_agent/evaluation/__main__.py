import argparse
import asyncio
import logging
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from venergy_agent.bootstrap import build_agent
from venergy_agent.config import AGENT_ROOT, AgentSettings
from venergy_agent.evaluation.report import EvaluationReport
from venergy_agent.evaluation.runner import EvaluationRunner
from venergy_agent.infrastructure.postgres_executor import PostgresQueryExecutor
from venergy_agent.infrastructure.semantic_source import (
    SemanticLayerError,
    YamlSemanticLayerSource,
)
from venergy_agent.infrastructure.sql_validator import SqlglotValidator

EVAL_DIR = AGENT_ROOT / "eval"
RUNS_DIR = EVAL_DIR / "runs"
DEFAULT_PAUSE_SECONDS = 4.0


def format_metrics(metrics: Mapping[str, float | int | None]) -> list[str]:
    width = max((len(name) for name in metrics), default=0)
    return [f"{name:<{width}}  {_format_value(value)}" for name, value in metrics.items()]


def _format_value(value: float | int | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value * 100:.1f}%"
    return str(value)


def report_path(root: Path, started_at: datetime) -> Path:
    return root / f"{started_at.astimezone(UTC):%Y-%m-%dT%H%M%SZ}.json"


def write_report(path: Path, report: EvaluationReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m venergy_agent.evaluation",
        description="Executa o golden set e o red team e grava o relatório em eval/runs/.",
    )
    parser.add_argument("--only", choices=("golden", "red_team"), default=None)
    parser.add_argument("--pause", type=float, default=DEFAULT_PAUSE_SECONDS, metavar="SECONDS")
    return parser.parse_args(argv)


def _load_items(name: str) -> list[dict[str, Any]]:
    document = yaml.safe_load((EVAL_DIR / name).read_text(encoding="utf-8"))
    return list(document["itens"])


async def _evaluate(only: str | None, pause_seconds: float) -> tuple[Path, list[str]]:
    settings = AgentSettings()
    layer = await YamlSemanticLayerSource(
        settings.semantic_layer_path, settings.gold_contract_path
    ).load()
    agent = await build_agent(settings)
    runner = EvaluationRunner(
        agent=agent,
        validator=SqlglotValidator(
            dialect=settings.sql_dialect,
            max_rows=settings.max_rows,
            allowed_schema=settings.allowed_schema,
        ),
        executor=PostgresQueryExecutor(settings.database_url, settings.query_timeout_seconds),
        allowed_views=layer.allowed_views,
        pause_seconds=pause_seconds,
    )
    report = await runner.run(
        _load_items("golden_set.yaml") if only != "red_team" else [],
        _load_items("red_team.yaml") if only != "golden" else [],
        model=settings.llm_model,
        prompt_version=settings.prompt_version,
        semantic_layer_version=layer.version,
    )
    path = report_path(RUNS_DIR, report.started_at)
    write_report(path, report)
    return path, format_metrics(report.metrics)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    try:
        path, lines = asyncio.run(_evaluate(args.only, args.pause))
    except ValidationError as error:
        print(f"configuração inválida (ai-agent/.env):\n{error}", file=sys.stderr)
        return 1
    except SemanticLayerError as error:
        print(f"camada semântica inválida:\n{error}", file=sys.stderr)
        return 1
    print("\n".join(lines))
    print(f"relatório: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
