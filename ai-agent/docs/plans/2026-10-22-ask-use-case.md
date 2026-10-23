# ask() Use Case Implementation Plan

> **Status (2026-10-22): implemented on branch `feat/ai-agent-ask`, not merged.** Based on `feat/ai-agent-contrato-answer` (item 2). Bootstrap and the terminal command moved here from item 8 after the review on PR #30 (2026-10-23): `build_agent` wires the use case with the deterministic answer text, so the backend can start D3; item 8 only injects the answer writer.

**Goal:** implement `TextToSqlAgent.ask()` with the flow of spec §5.1: size limit, statuses without SQL, correction after rejection and correctable errors, unclassified errors that fail at once, exhausted attempts, provider errors, confidence, and one log line per step. The answer text is deterministic in this branch.

**Architecture:** `application/ask.py` chains the ports. The validator, executor and generator are injected. `ask()` never raises. The error types `ErrorKind.REJECTED` and `Generation` are added in `domain/`.

**Spec:** `ai-agent/docs/specs/2026-10-19-architecture-design.md` §5.1 (flow), §8 (tests), §11 (item 6).

## Global Constraints

- Branch `feat/ai-agent-ask`, based on `feat/ai-agent-contrato-answer`.
- No commit without an explicit request.
- Code and tests in English, no comments.
- Logs never carry row values.

## Review Focus

1. A validator rejection goes back to the model with its reason (Task 1).
2. An unclassified database error becomes `failed` without a retry (Task 1).
3. The log has one line per step, with latency, and no row values (Task 2).

---

### Task 1: Flow and statuses

**Files:** `src/venergy_agent/application/ask.py`, `src/venergy_agent/application/ports.py`, `src/venergy_agent/domain/errors.py`, `src/venergy_agent/domain/sql.py`, `src/venergy_agent/infrastructure/sql_generator.py`, `tests/unit/application/test_ask.py`, `tests/unit/infrastructure/test_sql_generator.py`.

- [x] Size limit and empty question refused without calling the model.
- [x] `unknown`, `refuse` and `clarify` drafts end without SQL.
- [x] Validator rejection and correctable execution errors go back to the model.
- [x] Unclassified database error becomes `failed` at once.
- [x] Exhausted attempts and provider errors become `failed`, with the last SQL kept for audit.
- [x] `SqlGenerator` returns `Generation`, with the model that answered and token counts.

### Task 2: Confidence, logs and executor

**Files:** `src/venergy_agent/infrastructure/postgres_executor.py`, `tests/integration/test_postgres_executor.py`, `tests/unit/application/test_ask.py`, `tests/unit/test_config.py`.

- [x] Confidence: `low` for empty or truncated, `medium` for assumptions or correction, `high` otherwise.
- [x] One JSON log line per step, with per-step latency and no row values.
- [x] Duplicate output column names become a correctable error, so data is not overwritten silently.
- [x] `answer_sample_rows` setting.
