import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import ValidationError

from venergy_agent.domain.answer import AnswerStatus
from venergy_agent.evaluation.report import EvaluationReport, ItemResult
from venergy_agent.evaluation.runner import compute_metrics

FAILED_WARNING_RATE = 0.05
RUN_METRICS = (
    "writes_accepted",
    "views_changed",
    "red_team_violations",
    "follow_up_skipped",
    "other_dataset_skipped",
)
COMPARED_FIELDS = ("matched", "status", "numeric_fidelity", "judge_passed")
DASH = "—"

Metric = float | int | None
Key = tuple[str, str]


class ReportError(Exception):
    pass


def load_report(path: Path) -> EvaluationReport:
    try:
        return EvaluationReport.model_validate_json(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ReportError(f"não foi possível ler {path}: {error.strerror}") from error
    except ValidationError as error:
        raise ReportError(f"{path} não é um relatório de avaliação válido") from error


def compare(a: EvaluationReport, b: EvaluationReport, skip: frozenset[str] = frozenset()) -> str:
    keys_a = {_key(item): item for item in a.items if item.id not in skip}
    keys_b = {_key(item): item for item in b.items if item.id not in skip}
    common = [key for key in keys_a if key in keys_b]
    metrics_a = compute_metrics([keys_a[key] for key in common])
    metrics_b = compute_metrics([keys_b[key] for key in common])
    sections = [
        "# Comparação de rodadas",
        *_warnings(a, b),
        _table("Configuração", ("", "A", "B"), _configuration(a, b)),
        _items_line(len(common), len(keys_a) - len(common), len(keys_b) - len(common)),
        _table(
            "Métricas (itens em comum)",
            ("métrica", "A", "B", "diferença"),
            [
                [name, _format(name, metrics_a[name]), _format(name, metrics_b[name])]
                + [_difference(name, metrics_a[name], metrics_b[name])]
                for name in metrics_a
            ],
        ),
        _table(
            "Da rodada (como gravado)",
            ("métrica", "A", "B"),
            [
                [name, _format(name, a.metrics.get(name)), _format(name, b.metrics.get(name))]
                for name in RUN_METRICS
            ],
        ),
        _changes(common, keys_a, keys_b),
    ]
    return "\n\n".join(section for section in sections if section) + "\n"


def _key(item: ItemResult) -> Key:
    return item.kind, item.id


def _warnings(a: EvaluationReport, b: EvaluationReport) -> list[str]:
    lines = []
    for label, report in (("A", a), ("B", b)):
        failed = compute_metrics(report.items)["failed_rate"]
        if isinstance(failed, float) and failed > FAILED_WARNING_RATE:
            lines.append(
                f"**Aviso:** a rodada {label} tem {failed * 100:.1f}% de itens `failed` "
                f"(limite {FAILED_WARNING_RATE * 100:.0f}%): provável erro do provedor "
                "(429/503), a comparação não vale."
            )
    return ["\n\n".join(lines)] if lines else []


def _configuration(a: EvaluationReport, b: EvaluationReport) -> list[list[str]]:
    fields = {
        "iniciada em": lambda r: f"{r.started_at:%Y-%m-%d %H:%M}",
        "modelo": lambda r: r.model,
        "prompt_version": lambda r: r.prompt_version,
        "camada semântica": lambda r: r.semantic_layer_version,
        "golden_version": lambda r: r.golden_version,
        "red_team_version": lambda r: r.red_team_version,
        "base": lambda r: r.dataset,
        "narrada": lambda r: "sim" if r.narrated else "não",
        "juiz": _judge_label,
    }
    return [[label, read(a), read(b)] for label, read in fields.items()]


def _judge_label(report: EvaluationReport) -> str:
    if report.judge_model is None:
        return DASH
    return f"{report.judge_model} ({report.judge_prompt_version})"


def _items_line(common: int, only_a: int, only_b: int) -> str:
    return f"Itens em comum: {common}. Itens só em A: {only_a}. Itens só em B: {only_b}."


def _changes(
    common: Sequence[Key], keys_a: Mapping[Key, ItemResult], keys_b: Mapping[Key, ItemResult]
) -> str:
    rows = []
    for key in common:
        for field in COMPARED_FIELDS:
            before, after = getattr(keys_a[key], field), getattr(keys_b[key], field)
            if before != after:
                rows.append([key[1], field, f"{_value(before)} → {_value(after)}"])
    if not rows:
        return "Nenhum item em comum mudou de resultado."
    return _table("Itens que mudaram", ("item", "campo", "A → B"), rows)


def _value(value: object) -> str:
    if value is None:
        return DASH
    if isinstance(value, AnswerStatus):
        return value.value
    return str(value)


def _format(name: str, value: Metric) -> str:
    if value is None:
        return DASH
    if name == "judge_mean_score":
        return f"{value:.2f}"
    if isinstance(value, float):
        return f"{value * 100:.1f}%"
    return str(value)


def _difference(name: str, a: Metric, b: Metric) -> str:
    if a is None or b is None:
        return DASH
    if name == "judge_mean_score":
        return f"{b - a:+.2f}"
    if isinstance(a, float) or isinstance(b, float):
        return f"{(b - a) * 100:+.1f} pp"
    return f"{b - a:+d}"


def _table(title: str, header: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    lines = [
        f"## {title}",
        "",
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---" for _ in header) + "|",
        *("| " + " | ".join(row) + " |" for row in rows),
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m venergy_agent.evaluation.compare")
    parser.add_argument("a")
    parser.add_argument("b")
    parser.add_argument("--skip", default="", metavar="G001,G002")
    args = parser.parse_args(argv)
    try:
        a, b = load_report(Path(args.a)), load_report(Path(args.b))
    except ReportError as error:
        print(error, file=sys.stderr)
        return 1
    print(compare(a, b, frozenset(filter(None, args.skip.split(",")))), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
