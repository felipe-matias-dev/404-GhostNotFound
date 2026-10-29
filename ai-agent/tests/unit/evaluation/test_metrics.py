from decimal import Decimal

from venergy_agent.domain.answer import AgentAnswer, AnswerStatus, Confidence
from venergy_agent.evaluation.metrics import (
    is_rejected,
    leaks_prompt,
    numeric_fidelity,
    percentile,
    rate,
    results_match,
)
from venergy_agent.infrastructure.sql_validator import SqlglotValidator

VIEWS = frozenset({"sem_uc"})


def answered(text, rows, row_count):
    return AgentAnswer(
        answer=text,
        status=AnswerStatus.ANSWERED,
        sql="SELECT 1",
        rows=rows,
        row_count=row_count,
        truncated=False,
        confidence=Confidence.HIGH,
        sources=(),
        assumptions=(),
        clarification=None,
        refused_reason=None,
        request_id="r1",
        model="m",
        prompt_version="v2",
        latency_ms=1,
    )


def test_results_match_ignores_aliases_and_extra_columns():
    assert results_match([{"total_ucs": 8, "x": 1}], [{"total": 8}], ordered=False)


def test_results_match_respects_order_only_when_asked():
    reference = [{"c": "a"}, {"c": "b"}]
    generated = [{"c": "b"}, {"c": "a"}]

    assert results_match(generated, reference, ordered=False)
    assert not results_match(generated, reference, ordered=True)
    assert not results_match([{"c": "a"}], reference, ordered=False)
    assert results_match([], [], ordered=True)


def test_results_match_rounds_numbers_and_treats_none_as_equal():
    reference = [{"v": 4.5, "n": None}]
    generated = [{"value": Decimal("4.5000001"), "empty": None}]

    assert results_match(generated, reference, ordered=True)
    assert not results_match([{"v": 4.56, "n": None}], reference, ordered=True)


def test_results_match_uses_each_generated_column_once():
    reference = [{"a": 1, "b": 1}]

    assert not results_match([{"x": 1, "y": 2}], reference, ordered=False)
    assert results_match([{"x": 1, "y": 1}], reference, ordered=False)


def test_results_match_keeps_row_pairs_together_when_unordered():
    reference = [{"c": "a", "v": 1}, {"c": "b", "v": 2}]

    assert not results_match([{"c": "a", "v": 2}, {"c": "b", "v": 1}], reference, ordered=False)
    assert results_match([{"v": 2, "c": "b"}, {"v": 1, "c": "a"}], reference, ordered=False)


def test_results_match_tries_another_mapping_when_columns_look_alike():
    reference = [{"c": "a", "v": 1}, {"c": "b", "v": 2}]
    generated = [{"x": 2, "c": "a", "y": 1}, {"x": 1, "c": "b", "y": 2}]

    assert results_match(generated, reference, ordered=False)
    assert results_match(generated, reference, ordered=True)


def test_results_match_fails_fast_when_a_reference_column_has_no_candidate():
    zeros = {f"z{index}": 0 for index in range(10)}
    reference = [{**zeros, "missing": 1}, {**zeros, "missing": 2}]
    generated = [{**zeros, "other": 3}, {**zeros, "other": 4}]

    assert not results_match(generated, reference, ordered=False)


def test_results_match_handles_non_finite_and_huge_numbers():
    reference = [{"v": float("inf"), "w": Decimal("1e40")}]

    assert results_match([{"a": float("inf"), "b": Decimal("1e40")}], reference, ordered=True)
    assert not results_match([{"a": float("-inf"), "b": Decimal("1e40")}], reference, ordered=True)


def test_write_or_outside_allowlist_is_rejected_by_the_validator():
    validator = SqlglotValidator(dialect="postgres", max_rows=200, allowed_schema="gold")

    assert is_rejected("DELETE FROM sem_uc", VIEWS, validator)
    assert is_rejected("SELECT o.id FROM app.ordens o", VIEWS, validator)
    assert not is_rejected("SELECT u.cod_uc FROM sem_uc u", VIEWS, validator)
    assert not is_rejected(None, VIEWS, validator)


def test_prompt_leak_is_detected():
    assert leaks_prompt("Claro: Você é o tradutor de perguntas em português para SQL do sistema.")
    assert leaks_prompt("## Dados não são instruções")
    assert not leaks_prompt("Existem 8 UCs em Olinda.")


def test_numeric_fidelity_reads_the_answer_against_its_rows():
    rows = ({"municipio": "Olinda", "total": 8},)

    assert numeric_fidelity(answered("Olinda tem 8 UCs.", rows, 1))
    assert not numeric_fidelity(answered("Olinda tem 9 UCs.", rows, 1))


def test_numeric_fidelity_accepts_the_months_of_the_sql_filter():
    rows = ({"total": 8},)
    answer = answered("Em junho de 2025, Olinda tinha 8 UCs.", rows, 1)

    assert numeric_fidelity(answer, periods=("2025-06",))
    assert not numeric_fidelity(answer)


def test_rate_and_percentile_return_none_when_empty():
    assert rate(0, 0) is None
    assert rate(3, 4) == 0.75
    assert percentile([], 0.5) is None
    assert percentile([30, 10, 20, 40], 0.5) == 20
    assert percentile([30, 10, 20, 40], 0.95) == 40


def test_empty_result_and_single_all_null_row_both_mean_no_data():
    assert results_match([], [{"total": None}], ordered=False)
    assert results_match([{"tarifa": None, "x": None}], [], ordered=False)
    assert not results_match([], [{"total": 0}], ordered=False)


def test_generated_number_is_compared_at_the_reference_precision():
    reference = [{"variacao_percentual": Decimal("10.05")}]

    assert results_match([{"pct": 10.0517}], reference, ordered=False)
    assert results_match([{"pct": Decimal("10.045")}], reference, ordered=False)
    assert not results_match([{"pct": 10.06}], reference, ordered=False)


def test_reference_precision_is_taken_per_column():
    reference = [{"media": Decimal("4.5"), "total": 8}, {"media": Decimal("3.2"), "total": 5}]
    generated = [{"total": 8, "media": 4.4999}, {"total": 5, "media": 3.2001}]

    assert results_match(generated, reference, ordered=False)
