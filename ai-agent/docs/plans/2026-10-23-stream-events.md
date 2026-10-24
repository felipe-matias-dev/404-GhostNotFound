# Progress Events (SSE) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** let the backend stream the agent's progress to the portal over Server-Sent Events. The agent emits one event per stage, then the final `AgentAnswer`. No partial text is shown before the numeric check (DEC-019).

**Architecture:** a new `stream(question, session_id)` on the use case returns an async iterator of `AgentEvent`. The current `ask()` body moves into `_run`, which reports stages through a callback into an `asyncio.Queue`. `stream()` runs `_run` as a task and yields from the queue until the `AnswerEvent`. `ask()` consumes `stream()` and returns the last answer, so both always agree. The SSE route and the portal belong to Dev (issue, spec §10 D10).

**Tech Stack:** asyncio, pydantic. No new dependency.

**Spec:** `ai-agent/docs/specs/2026-10-19-architecture-design.md` §4 (events), §5 (port), §5.1 (stages), §10 (D10), §11 (item 10, a differential). Design approved in chat on 2026-10-23.

## Global Constraints

- Branch `feat/ai-agent-stream`, stacked on `feat/ai-agent-narracao-v2` (PR #36), because the `writing` stage only exists with the narration.
- The port changes (spec §4): the PR merges only after V1 accepts the issue.
- Stage codes and Portuguese labels, exactly:
  - `understanding`: "Entendendo a pergunta"
  - `querying`: "Consultando os dados"
  - `correcting`: "Ajustando a consulta"
  - `writing`: "Escrevendo a resposta"
- A stage event carries only `type`, `stage`, `label` and `attempt`: no SQL, no rows, no error text.
- Code in English, no comments.

## Review Focus

1. The client disconnects after the first event: the running task is cancelled, and the executor is never called (Task 2).
2. An unexpected error inside a step still ends the stream with a `failed` answer, never with an exception (Task 2).
3. A refused question (empty or too long) yields only the answer event, with no stage (Task 2).
4. Exactly one `AnswerEvent`, always the last one (Task 2).
5. `ask()` returns the same answer the stream ends with (Task 2).

---

### Task 1: Event models
**Files:** create `domain/events.py`. Test: `tests/unit/domain/test_events.py`.

**Interfaces:**
- Produces:
  - `Stage(StrEnum)`: `UNDERSTANDING`, `QUERYING`, `CORRECTING`, `WRITING`.
  - `StageEvent(type: Literal["stage"], stage: Stage, attempt: int >= 1)`, frozen, with a computed `label: str` from the table above.
  - `AnswerEvent(type: Literal["answer"], answer: AgentAnswer)`, frozen.
  - `AgentEvent = Annotated[StageEvent | AnswerEvent, Field(discriminator="type")]`.

- [ ] Test `test_each_stage_has_its_portuguese_label`, parametrized over the four pairs above, checking `StageEvent(stage=..., attempt=1).label`.
- [ ] Test `test_stage_event_serializes_without_technical_fields`: `model_dump()` keys == `{"type", "stage", "label", "attempt"}`.
- [ ] Implement, then run `uv run pytest tests/unit/domain/test_events.py -q`. Expected: PASS.

### Task 2: `stream()` and `ask()` on top of it
**Files:** modify `application/ask.py` and `application/ports.py` (`TextToSqlAgent.stream(question: str, session_id: str) -> AsyncIterator[AgentEvent]`). Test: `tests/unit/application/test_stream.py`, reusing the fakes of `test_ask.py`.

**Emission points:**
- `UNDERSTANDING` before the generation on attempt 1, and `CORRECTING` before the generation on later attempts;
- `QUERYING` before validation, only for an `ok` draft;
- `WRITING` before the narration.

**Tests:**
- `test_answered_flow_emits_stages_then_the_answer`: stages `[understanding, querying, writing]`, then one `AnswerEvent` with status `answered`.
- `test_correction_emits_correcting_before_the_new_attempt`: a rejected SQL, then a valid one, gives `[understanding, querying, correcting, querying, writing]`.
- `test_unknown_draft_emits_only_understanding`.
- `test_refused_question_emits_only_the_answer`: a question over `max_question_chars`.
- `test_unexpected_error_still_ends_with_a_failed_answer`: `BrokenValidator`.
- `test_client_disconnect_cancels_the_run`: the generator blocks on an `asyncio.Event`; the consumer takes the first event and calls `aclose()`; the executor was never called.
- `test_ask_returns_the_answer_the_stream_ends_with`.

- [ ] Write the tests and run them. Expected: FAIL (`stream` missing).
- [ ] Move the body of `ask()` into `_run(question, session_id, emit: Callable[[StageEvent], None]) -> AgentAnswer`, with the internal-error guard.
- [ ] Implement `stream()`. It creates `asyncio.Queue`, runs `_run` in `asyncio.create_task`, and puts the `AnswerEvent` when the task returns. It yields until the `AnswerEvent`, and cancels the task in `finally` if it is still running.
- [ ] Rewrite `ask()` to consume `stream()`.
- [ ] Run `uv run pytest -q`. Expected: all green, including the existing `test_ask.py`.

### Task 3: Docs, issue and verification
- [ ] Spec: §4 events, §5 port table, §5.1 stages, §10 D10 (Dev: SSE route and portal), §11 item 10 (differential). Update `ai-agent/CLAUDE.md` (Para Dev) and `docs/architecture.md`.
- [ ] Open the issue for Dev with the SSE contract (route, event format, audit, disconnect, `fetch` on the portal).
- [ ] Run `uv run pytest -q && uv run ruff check . && uv run ruff format --check .` and the hooks.
- [ ] Run `code-review` on the diff and fix the confirmed findings.
