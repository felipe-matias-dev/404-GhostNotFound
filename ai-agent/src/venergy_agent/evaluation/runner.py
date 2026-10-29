import asyncio
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from venergy_agent.application.ports import AnswerJudge, QueryExecutor, SqlValidator, TextToSqlAgent
from venergy_agent.domain.answer import AgentAnswer, AnswerStatus
from venergy_agent.domain.judge import JudgeVerdict
from venergy_agent.evaluation.metrics import (
    is_rejected,
    leaks_prompt,
    no_data,
    numeric_fidelity,
    percentile,
    rate,
    results_match,
)
from venergy_agent.evaluation.report import EvaluationReport, ItemResult

RATIONALE_MAX_CHARS = 300

Kind = Literal["golden", "red_team"]


class DatabaseGuard(Protocol):
    async def snapshot(self) -> Mapping[str, str]: ...

    async def accepted_writes(self) -> int: ...


class TurnRecorder(Protocol):
    async def record(self, session_id: str, question: str, answer: AgentAnswer) -> None: ...


class EvaluationRunner:
    def __init__(
        self,
        agent: TextToSqlAgent,
        validator: SqlValidator,
        executor: QueryExecutor,
        allowed_views: frozenset[str],
        guard: DatabaseGuard,
        pause_seconds: float = 0.0,
        recorder: TurnRecorder | None = None,
        judge: AnswerJudge | None = None,
    ) -> None:
        self._agent = agent
        self._validator = validator
        self._executor = executor
        self._allowed_views = allowed_views
        self._guard = guard
        self._pause_seconds = pause_seconds
        self._recorder = recorder
        self._judge = judge
        self._narrated = True

    async def run(
        self,
        golden: Sequence[Mapping[str, Any]],
        red_team: Sequence[Mapping[str, Any]],
        *,
        model: str,
        prompt_version: str,
        semantic_layer_version: str,
        golden_version: str,
        red_team_version: str,
        dataset: str,
        narrated: bool,
        judge_model: str | None = None,
        judge_prompt_version: str | None = None,
    ) -> EvaluationReport:
        started_at = datetime.now(UTC)
        self._narrated = narrated
        run_id = uuid.uuid4().hex[:8]
        in_dataset = [item for item in golden if dataset in item["datasets"]]
        chains = _chains(in_dataset)
        scheduled = sum(len(chain) for chain in chains)
        plan: list[tuple[Kind, Mapping[str, Any], str]] = [
            *(
                ("golden", item, f"eval-{run_id}-{chain[0]['id']}")
                for chain in chains
                for item in chain
            ),
            *(("red_team", item, f"eval-{run_id}-{item['id']}") for item in red_team),
        ]
        before = await self._guard.snapshot()
        items: list[ItemResult] = []
        for index, (kind, item, session_id) in enumerate(plan):
            if index and self._pause_seconds:
                await asyncio.sleep(self._pause_seconds)
            items.append(await self._evaluate(kind, item, session_id))
        writes_accepted = await self._guard.accepted_writes()
        after = await self._guard.snapshot()
        views_changed = sum(after.get(view) != fingerprint for view, fingerprint in before.items())
        return EvaluationReport(
            started_at=started_at,
            model=model,
            prompt_version=prompt_version,
            semantic_layer_version=semantic_layer_version,
            golden_version=golden_version,
            red_team_version=red_team_version,
            dataset=dataset,
            narrated=narrated,
            judge_model=judge_model,
            judge_prompt_version=judge_prompt_version,
            items=tuple(items),
            metrics={
                **compute_metrics(items),
                "writes_accepted": writes_accepted,
                "views_changed": views_changed,
                "red_team_violations": writes_accepted + views_changed,
                "follow_up_skipped": len(in_dataset) - scheduled,
                "other_dataset_skipped": len(golden) - len(in_dataset),
            },
        )

    async def _evaluate(self, kind: Kind, item: Mapping[str, Any], session_id: str) -> ItemResult:
        golden = kind == "golden"
        question = item["question"] if golden else item["attack"]
        expected = AnswerStatus(item["expected_status"])
        scored = golden and expected is AnswerStatus.ANSWERED
        reference_sql = item.get("reference_sql") if scored else None
        reference = await self._reference(item) if scored else None
        reference_empty = (
            reference is not None
            and no_data(reference)
            and not item.get("allow_empty_reference", False)
        )
        if reference_empty:
            reference = None
        judged = reference is not None
        reference_error = scored and not judged
        common = {
            "id": item["id"],
            "kind": kind,
            "category": item["category"] if golden else item["kind"],
            "expected_status": expected,
            "reference_error": reference_error,
            "reference_empty": reference_empty,
        }
        try:
            answer = await self._agent.ask(question, session_id=session_id)
        except Exception:
            return ItemResult(
                **common,
                status=AnswerStatus.FAILED,
                sql=None,
                matched=False if judged else None,
                prompt_leak=False,
                numeric_fidelity=None,
                latency_ms=None,
            )
        if self._recorder is not None:
            await self._recorder.record(session_id, question, answer)
        answered = answer.status is AnswerStatus.ANSWERED
        matched = None
        if reference is not None:
            matched = await self._matched(answer, reference, reference_sql or "")
        verdict, judge_error = await self._verdict(question, answer)
        return ItemResult(
            **common,
            status=answer.status,
            sql=answer.sql,
            matched=matched,
            blocked=is_rejected(answer.sql, self._allowed_views, self._validator),
            prompt_leak=leaks_prompt(answer.answer),
            numeric_fidelity=numeric_fidelity(answer) if answered and self._narrated else None,
            latency_ms=answer.latency_ms,
            judge_score=verdict.score if verdict else None,
            judge_passed=verdict.passed if verdict else None,
            judge_rationale=verdict.rationale[:RATIONALE_MAX_CHARS] if verdict else None,
            judge_error=judge_error,
        )

    async def _verdict(
        self, question: str, answer: AgentAnswer
    ) -> tuple[JudgeVerdict | None, bool]:
        if self._judge is None or not self._narrated or answer.status is not AnswerStatus.ANSWERED:
            return None, False
        try:
            return await self._judge.judge(question, answer), False
        except Exception:
            return None, True
        finally:
            if self._pause_seconds:
                await asyncio.sleep(self._pause_seconds)

    async def _reference(self, item: Mapping[str, Any]) -> tuple[dict[str, object], ...] | None:
        if item.get("expected_values"):
            return (dict(item["expected_values"]),)
        sql = item.get("reference_sql")
        if not sql:
            return None
        try:
            return await self._rows(sql)
        except Exception:
            return None

    async def _matched(
        self,
        answer: AgentAnswer,
        reference: Sequence[Mapping[str, object]],
        reference_sql: str,
    ) -> bool:
        if answer.status is not AnswerStatus.ANSWERED or answer.sql is None:
            return False
        try:
            generated = await self._rows(answer.sql)
        except Exception:
            return False
        return results_match(generated, reference, ordered="ORDER BY" in reference_sql.upper())

    async def _rows(self, sql: str) -> tuple[dict[str, object], ...]:
        query = self._validator.validate(sql, self._allowed_views)
        return (await self._executor.execute(query)).rows


def _chains(items: Sequence[Mapping[str, Any]]) -> list[list[Mapping[str, Any]]]:
    children: dict[str, list[Mapping[str, Any]]] = {}
    for item in items:
        if item.get("follow_up_of"):
            children.setdefault(item["follow_up_of"], []).append(item)

    def descendants(item: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        ordered: list[Mapping[str, Any]] = []
        for child in children.get(item["id"], []):
            ordered += [child, *descendants(child)]
        return ordered

    return [[item, *descendants(item)] for item in items if not item.get("follow_up_of")]


def compute_metrics(items: Sequence[ItemResult]) -> dict[str, float | int | None]:
    golden = [item for item in items if item.kind == "golden"]
    red_team = [item for item in items if item.kind == "red_team"]
    scored = [
        item
        for item in golden
        if item.expected_status is AnswerStatus.ANSWERED and not item.reference_error
    ]
    unknown = [item for item in golden if item.expected_status is AnswerStatus.UNKNOWN]
    manipulation = red_team + [
        item for item in golden if item.expected_status is AnswerStatus.REFUSED
    ]
    fidelity = [item.numeric_fidelity for item in items if item.numeric_fidelity is not None]
    refusals = [item for item in items if item.expected_status is AnswerStatus.REFUSED]
    judged = [item for item in items if item.judge_score is not None]
    latencies = [item.latency_ms for item in items if item.latency_ms is not None]
    return {
        "execution_accuracy": rate(sum(item.matched is True for item in scored), len(scored)),
        "status_accuracy": rate(_status_hits(golden), len(golden)),
        "status_accuracy_unknown": rate(_status_hits(unknown), len(unknown)),
        "failed_rate": rate(sum(item.status is AnswerStatus.FAILED for item in items), len(items)),
        "manipulation_block_rate": rate(
            sum(not item.prompt_leak for item in manipulation), len(manipulation)
        ),
        "refusal_accuracy": rate(
            sum(item.status is AnswerStatus.REFUSED for item in refusals), len(refusals)
        ),
        "prompt_leaks": sum(item.prompt_leak for item in items),
        "blocked_attempts": sum(item.blocked for item in items),
        "numeric_fidelity": rate(sum(fidelity), len(fidelity)),
        "latency_p50_ms": percentile(latencies, 0.5),
        "latency_p95_ms": percentile(latencies, 0.95),
        "judge_pass_rate": rate(sum(item.judge_passed is True for item in judged), len(judged)),
        "judge_mean_score": sum(item.judge_score for item in judged) / len(judged)
        if judged
        else None,
        "judge_items": len(judged),
        "judge_errors": sum(item.judge_error for item in items),
        "reference_errors": sum(item.reference_error for item in items),
        "reference_empty": sum(item.reference_empty for item in items),
        "golden_items": len(golden),
        "red_team_items": len(red_team),
    }


def _status_hits(items: Sequence[ItemResult]) -> int:
    return sum(item.status is item.expected_status for item in items)
