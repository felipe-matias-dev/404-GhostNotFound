from datetime import UTC, datetime
from pathlib import Path

import pytest

from venergy_agent.domain.answer import AnswerStatus
from venergy_agent.evaluation.compare import compare, load_report, main
from venergy_agent.evaluation.report import EvaluationReport, ItemResult

RUNS = Path(__file__).parents[3] / "eval" / "runs"


def item(item_id, **overrides):
    fields = {
        "id": item_id,
        "kind": "golden",
        "category": "simples",
        "expected_status": AnswerStatus.ANSWERED,
        "status": AnswerStatus.ANSWERED,
        "sql": "SELECT 1",
        "matched": True,
        "prompt_leak": False,
        "numeric_fidelity": True,
        "latency_ms": 100,
        **overrides,
    }
    return ItemResult(**fields)


def report(items, metrics=None, **overrides):
    fields = {
        "started_at": datetime(2026, 10, 28, tzinfo=UTC),
        "model": "google-gla:gemini-3.1-flash-lite",
        "prompt_version": "v2",
        "semantic_layer_version": "0.4.0",
        "golden_version": "0.9.0",
        "red_team_version": "0.1.0",
        "items": tuple(items),
        "metrics": metrics or {},
        **overrides,
    }
    return EvaluationReport(**fields)


def failing(index, failed):
    return item(f"G{index}", status=AnswerStatus.FAILED if failed else AnswerStatus.ANSWERED)


def many(count, **overrides):
    return [item(f"G{index:03d}", **overrides) for index in range(count)]


def test_metrics_sit_side_by_side_with_the_difference_in_points_and_units():
    a = report([item(f"G{i}", matched=i < 7, latency_ms=100) for i in range(10)])
    b = report([item(f"G{i}", matched=i < 9, latency_ms=220) for i in range(10)])

    text = compare(a, b)

    assert "| execution_accuracy | 70.0% | 90.0% | +20.0 pp |" in text
    assert "| latency_p50_ms | 100 | 220 | +120 |" in text
    assert "| golden_items | 10 | 10 | +0 |" in text


def test_a_missing_side_shows_a_dash_instead_of_a_difference():
    a = report([item("G1")])
    b = report([item("G1")])

    text = compare(a, b)

    assert "| judge_pass_rate | — | — | — |" in text
    assert "| refusal_accuracy | — | — | — |" in text


def test_judge_mean_score_is_a_plain_number():
    a = report([item("G1", judge_score=3, judge_passed=False)])
    b = report([item("G1", judge_score=5, judge_passed=True)])

    assert "| judge_mean_score | 3.00 | 5.00 | +2.00 |" in compare(a, b)


def test_different_golden_versions_compare_only_the_common_items():
    a = report([item("G1"), item("G2", matched=False), item("G3")], golden_version="0.9.0")
    b = report([item("G1"), item("G2", matched=True), item("G4")], golden_version="0.10.0")

    text = compare(a, b)

    assert "| golden_items | 2 | 2 | +0 |" in text
    assert "| execution_accuracy | 50.0% | 100.0% | +50.0 pp |" in text
    assert "Itens só em A: 1" in text
    assert "Itens só em B: 1" in text


def test_header_carries_the_configuration_of_both_runs():
    a = report([item("G1")], golden_version="0.9.0")
    b = report(
        [item("G1")],
        golden_version="0.10.0",
        prompt_version="v3",
        narrated=False,
        judge_model="google-gla:gemini-3.1-flash",
        judge_prompt_version="v1",
    )

    text = compare(a, b)

    assert "| prompt_version | v2 | v3 |" in text
    assert "| golden_version | 0.9.0 | 0.10.0 |" in text
    assert "| narrada | sim | não |" in text
    assert "| juiz | — | google-gla:gemini-3.1-flash (v1) |" in text
    assert "| base | amostra | amostra |" in text


def test_common_items_that_changed_are_listed_and_equal_ones_are_not():
    a = report(
        [
            item("G1"),
            item("G2", matched=True, numeric_fidelity=True),
            item("G3", status=AnswerStatus.ANSWERED, judge_passed=True, judge_score=5),
        ]
    )
    b = report(
        [
            item("G1"),
            item("G2", matched=False, numeric_fidelity=False),
            item("G3", status=AnswerStatus.FAILED, judge_passed=None),
        ]
    )

    text = compare(a, b)

    assert "| G2 | matched | True → False |" in text
    assert "| G2 | numeric_fidelity | True → False |" in text
    assert "| G3 | status | answered → failed |" in text
    assert "| G3 | judge_passed | True → — |" in text
    assert "| G1 |" not in text


def test_a_run_with_many_failed_items_gets_a_provider_warning():
    healthy = report(many(20))
    broken = report([*many(18), *many(2, status=AnswerStatus.FAILED)][:20])
    broken = report(
        [
            item(f"G{i}", status=AnswerStatus.FAILED if i < 2 else AnswerStatus.ANSWERED)
            for i in range(20)
        ]
    )

    warned = compare(healthy, broken)

    assert "a rodada B tem 10.0% de itens `failed`" in warned
    assert "a rodada A" not in warned
    assert "Aviso" not in compare(healthy, report(many(20)))


def test_failed_at_the_limit_does_not_warn():
    at_limit = report(
        [
            item(f"G{i}", status=AnswerStatus.FAILED if i == 0 else AnswerStatus.ANSWERED)
            for i in range(20)
        ]
    )

    assert "Aviso" not in compare(at_limit, at_limit)


def test_run_metrics_are_shown_as_recorded_and_missing_keys_become_a_dash():
    a = report([item("G1")], metrics={"red_team_violations": 0, "follow_up_skipped": 1})
    b = report(
        [item("G1")],
        metrics={"red_team_violations": 2, "follow_up_skipped": 0, "writes_accepted": 2},
    )

    text = compare(a, b)

    assert "| red_team_violations | 0 | 2 |" in text
    assert "| writes_accepted | — | 2 |" in text
    assert "| other_dataset_skipped | — | — |" in text


@pytest.mark.parametrize("path", sorted(RUNS.glob("*.json")), ids=lambda p: p.name)
def test_every_versioned_report_still_loads(path):
    assert load_report(path).items


def test_main_prints_the_comparison_of_two_files(tmp_path, capsys):
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    first.write_text(report([item("G1")]).model_dump_json(), encoding="utf-8")
    second.write_text(report([item("G1")]).model_dump_json(), encoding="utf-8")

    assert main([str(first), str(second)]) == 0
    assert "execution_accuracy" in capsys.readouterr().out


def test_main_reports_a_missing_file_with_a_short_message(tmp_path, capsys):
    assert main([str(tmp_path / "nope.json"), str(tmp_path / "nope.json")]) == 1
    assert "nope.json" in capsys.readouterr().err


def test_main_reports_invalid_json_with_a_short_message(tmp_path, capsys):
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")

    assert main([str(broken), str(broken)]) == 1
    assert "broken.json" in capsys.readouterr().err
