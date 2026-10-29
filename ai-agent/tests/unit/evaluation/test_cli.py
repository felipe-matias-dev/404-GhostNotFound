from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from venergy_agent.evaluation.__main__ import (
    RUNS_DIR,
    RUNS_GOLD_DIR,
    DatasetMismatch,
    JudgeNotAllowed,
    check_dataset,
    format_metrics,
    judges,
    load_set,
    main,
    narrates,
    report_path,
    runs_dir,
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


def test_real_gold_reports_go_to_a_folder_outside_git():
    assert runs_dir("amostra") == RUNS_DIR
    assert runs_dir("gold_real") == RUNS_GOLD_DIR
    ignored = (RUNS_GOLD_DIR.parents[2] / ".gitignore").read_text(encoding="utf-8")
    assert "ai-agent/eval/runs_gold/" in ignored


def test_real_gold_always_runs_without_the_answer_writer():
    assert narrates("amostra", sql_only=False) is True
    assert narrates("amostra", sql_only=True) is False
    assert narrates("gold_real", sql_only=False) is False


@pytest.mark.parametrize(("dataset", "uc_count"), [("amostra", 50_000), ("gold_real", 8)])
def test_loaded_database_must_be_the_declared_dataset(dataset, uc_count):
    with pytest.raises(DatasetMismatch, match=dataset):
        check_dataset(dataset, uc_count)


@pytest.mark.parametrize(("dataset", "uc_count"), [("amostra", 8), ("gold_real", 50_000)])
def test_matching_database_passes_the_check(dataset, uc_count):
    check_dataset(dataset, uc_count)


def test_judge_is_off_unless_requested():
    assert judges("amostra", judge=False, sql_only=False) is False
    assert judges("gold_real", judge=False, sql_only=False) is False


def test_judge_runs_on_the_sample_when_requested():
    assert judges("amostra", judge=True, sql_only=False) is True


def test_judge_is_refused_on_the_real_gold_and_names_the_reason():
    with pytest.raises(JudgeNotAllowed, match="#56"):
        judges("gold_real", judge=True, sql_only=False)


def test_judge_is_refused_without_the_narrative():
    with pytest.raises(JudgeNotAllowed, match="--sql-only"):
        judges("amostra", judge=True, sql_only=True)


def test_judge_mean_score_is_a_number_and_not_a_percentage():
    lines = format_metrics({"judge_mean_score": 4.2, "judge_pass_rate": 0.8})

    assert lines[0].endswith("4.20")
    assert lines[1].endswith("80.0%")


def test_judge_flag_is_refused_before_any_connection_on_the_real_gold(capsys):
    assert main(["--dataset", "gold_real", "--judge"]) == 1
    assert "juiz" in capsys.readouterr().err
