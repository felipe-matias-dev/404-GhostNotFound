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
from venergy_agent.evaluation.database_guard import PostgresDatabaseGuard
from venergy_agent.evaluation.report import EvaluationReport
from venergy_agent.evaluation.runner import EvaluationRunner
from venergy_agent.infrastructure.answer_judge import PydanticAiAnswerJudge
from venergy_agent.infrastructure.llm import build_judge_model
from venergy_agent.infrastructure.postgres_executor import PostgresQueryExecutor
from venergy_agent.infrastructure.semantic_source import (
    SemanticLayerError,
    YamlSemanticLayerSource,
)
from venergy_agent.infrastructure.sql_validator import SqlglotValidator

EVAL_DIR = AGENT_ROOT / "eval"
RUNS_DIR = EVAL_DIR / "runs"
RUNS_GOLD_DIR = EVAL_DIR / "runs_gold"
DEFAULT_PAUSE_SECONDS = 4.0
SAMPLE_MAX_UCS = 1000
UC_COUNT_SQL = "SELECT count(*) AS total FROM sem_uc"


class DatasetMismatch(Exception):
    pass


class JudgeNotAllowed(Exception):
    pass


def runs_dir(dataset: str) -> Path:
    return RUNS_GOLD_DIR if dataset == "gold_real" else RUNS_DIR


def narrates(sql_only: bool) -> bool:
    return not sql_only


def judges(dataset: str, judge: bool, sql_only: bool) -> bool:
    if not judge:
        return False
    if sql_only:
        raise JudgeNotAllowed("--judge precisa da narrativa: não use junto com --sql-only")
    return True


def check_dataset(dataset: str, uc_count: int) -> None:
    looks_like_sample = uc_count <= SAMPLE_MAX_UCS
    if looks_like_sample != (dataset == "amostra"):
        loaded = "a amostra" if looks_like_sample else "a Gold real"
        raise DatasetMismatch(
            f"--dataset {dataset}, mas o banco tem {uc_count} UCs em sem_uc, o que indica {loaded}"
        )


def format_metrics(metrics: Mapping[str, float | int | None]) -> list[str]:
    width = max((len(name) for name in metrics), default=0)
    return [f"{name:<{width}}  {_format_value(name, value)}" for name, value in metrics.items()]


def _format_value(name: str, value: float | int | None) -> str:
    if value is None:
        return "—"
    if name == "judge_mean_score":
        return f"{value:.2f}"
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
    parser.add_argument("--dataset", choices=("amostra", "gold_real"), default="amostra")
    parser.add_argument("--sql-only", action="store_true")
    parser.add_argument("--judge", action="store_true")
    return parser.parse_args(argv)


def load_set(path: Path) -> tuple[str, list[dict[str, Any]]]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return str(document["versao"]), list(document["itens"])


def _build_judge(settings: AgentSettings) -> PydanticAiAnswerJudge:
    try:
        model = build_judge_model(settings)
    except ValueError as error:
        raise JudgeNotAllowed(str(error)) from error
    return PydanticAiAnswerJudge(
        model, settings.prompts_dir / "judge", settings.judge_prompt_version
    )


async def _evaluate(
    only: str | None, pause_seconds: float, dataset: str, sql_only: bool, judge: bool
) -> tuple[Path, list[str]]:
    with_judge = judges(dataset, judge, sql_only)
    settings = AgentSettings()
    layer = await YamlSemanticLayerSource(
        settings.semantic_layer_path, settings.gold_contract_path
    ).load()
    validator = SqlglotValidator(
        dialect=settings.sql_dialect,
        max_rows=settings.max_rows,
        allowed_schema=settings.allowed_schema,
    )
    executor = PostgresQueryExecutor(settings.database_url, settings.query_timeout_seconds)
    counted = await executor.execute(validator.validate(UC_COUNT_SQL, layer.allowed_views))
    check_dataset(dataset, int(counted.rows[0]["total"]))
    narrate = narrates(sql_only)
    agent = await build_agent(settings, narrate=narrate)
    answer_judge = _build_judge(settings) if with_judge else None
    runner = EvaluationRunner(
        agent=agent,
        validator=validator,
        executor=executor,
        allowed_views=layer.allowed_views,
        guard=PostgresDatabaseGuard(
            settings.database_url, settings.allowed_schema, layer.allowed_views
        ),
        pause_seconds=pause_seconds,
        judge=answer_judge,
    )
    golden_version, golden = load_set(EVAL_DIR / "golden_set.yaml")
    red_team_version, red_team = load_set(EVAL_DIR / "red_team.yaml")
    report = await runner.run(
        golden if only != "red_team" else [],
        red_team if only != "golden" else [],
        model=settings.llm_model,
        prompt_version=settings.prompt_version,
        semantic_layer_version=layer.version,
        golden_version=golden_version,
        red_team_version=red_team_version,
        dataset=dataset,
        narrated=narrate,
        judge_model=settings.judge_model if with_judge else None,
        judge_prompt_version=settings.judge_prompt_version if with_judge else None,
    )
    path = report_path(runs_dir(dataset), report.started_at)
    write_report(path, report)
    return path, format_metrics(report.metrics)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    try:
        path, lines = asyncio.run(
            _evaluate(args.only, args.pause, args.dataset, args.sql_only, args.judge)
        )
    except ValidationError as error:
        print(f"configuração inválida (ai-agent/.env):\n{error}", file=sys.stderr)
        return 1
    except SemanticLayerError as error:
        print(f"camada semântica inválida:\n{error}", file=sys.stderr)
        return 1
    except JudgeNotAllowed as error:
        print(f"juiz não permitido: {error}", file=sys.stderr)
        return 1
    except DatasetMismatch as error:
        print(f"base errada: {error}", file=sys.stderr)
        return 1
    print("\n".join(lines))
    print(f"relatório: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
