from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from venergy_agent.evaluation.__main__ import (
    format_metrics,
    load_set,
    main,
    report_path,
    write_report,
)
from venergy_agent.evaluation.report import EvaluationReport


def test_format_metrics_shows_rates_as_percentages_and_none_as_dash():
    lines = format_metrics(
        {
            "execution_accuracy": 0.8125,
            "violations": 0,
            "latency_p95_ms": 1234,
            "unknown_rate": None,
            "refusal_rate": 1.0,
        }
    )

    assert len(lines) == 5
    assert "execution_accuracy" in lines[0] and lines[0].endswith("81.2%")
    assert lines[1].endswith(" 0") and "%" not in lines[1]
    assert lines[2].endswith(" 1234")
    assert lines[3].endswith(" —")
    assert lines[4].endswith("100.0%")


def test_report_path_uses_utc_timestamp():
    local = timezone(timedelta(hours=-3))
    started_at = datetime(2026, 10, 24, 12, 30, 0, tzinfo=local)

    path = report_path(Path("/tmp/runs"), started_at)

    assert path == Path("/tmp/runs/2026-10-24T153000Z.json")
    assert started_at.astimezone(UTC).strftime("%H") == "15"


def test_only_option_rejects_unknown_set():
    with pytest.raises(SystemExit) as exit_info:
        main(["--only", "everything"])

    assert exit_info.value.code == 2


def test_written_report_ends_with_a_newline(tmp_path):
    report = EvaluationReport(
        started_at=datetime(2026, 10, 24, tzinfo=UTC),
        model="m",
        prompt_version="v2",
        semantic_layer_version="0.3.0",
        golden_version="0.3.2",
        red_team_version="0.1.0",
        items=(),
        metrics={},
    )
    path = tmp_path / "runs" / "report.json"

    write_report(path, report)

    assert path.read_text(encoding="utf-8").endswith("}\n")


def test_load_set_returns_the_version_and_the_items(tmp_path):
    path = tmp_path / "set.yaml"
    path.write_text("versao: 0.1.0\nitens:\n  - id: R001\n", encoding="utf-8")

    assert load_set(path) == ("0.1.0", [{"id": "R001"}])
