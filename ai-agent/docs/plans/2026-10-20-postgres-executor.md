# Postgres Query Executor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the `QueryExecutor` port as a read-only Postgres adapter with timeout, truncation flag and SQLSTATE error classification.

**Architecture:** One adapter in `infrastructure/`. It uses async psycopg 3 directly, with no SQLAlchemy and one connection per query. Every query runs inside `BEGIN READ ONLY` with `SET LOCAL statement_timeout` and always ends in `ROLLBACK`. Integration tests run against `venergy_test` from the root `docker compose`, mirroring `backend/tests/test_agent_role.py`.

**Tech Stack:** psycopg[binary] 3, pytest-asyncio.

**Spec:** `ai-agent/docs/specs/2026-10-19-architecture-design.md` (§5 port, §8 tests, §11 item 3). Design approved in chat on 2026-10-20.

## Global Constraints

- Branch `feat/ai-agent-executor`, stacked on `fix/ai-agent-review-pr5`. No commit without explicit request.
- Code in English, no comments. Only files under `ai-agent/` change.
- `database_url` uses the plain libpq form `postgresql://user:pass@host:port/db`.
- Tests connect as `venergy_agent`. Test data is created by the owner role `venergy` in `gold` and dropped afterwards.
- Defaults match the root `.env.example`:
  - `VENERGY_AGENT_TEST_DATABASE_URL=postgresql://venergy_agent:troque-esta-senha-do-agente@127.0.0.1:5433/venergy_test`
  - `VENERGY_AGENT_TEST_OWNER_DATABASE_URL=postgresql://venergy:troque-esta-senha@127.0.0.1:5433/venergy_test`
- If the DB is unreachable, the tests fail with the message `Banco de testes indisponível. Suba com: docker compose up -d --wait db`.

## Review Focus

1. A forged `ValidatedQuery` containing `INSERT` must be refused by the database (SQLSTATE `25006`) and propagate unchanged (Task 3).
2. A permission error (`42501`) must propagate unchanged, never become a correctable `ErrorKind` (Task 4).
3. Result values (`Decimal`, `date`) are returned as-is; serialization belongs to the backend (Task 2).
4. A timeout must not leave the connection open (Task 3: `async with` closes it).

---

### Task 1: Dependencies and fixtures

**Files:**
- Modify: `ai-agent/pyproject.toml` (add `psycopg[binary]`; dev `pytest-asyncio`; `[tool.pytest.ini_options] asyncio_mode = "auto"`)
- Create: `ai-agent/tests/integration/conftest.py`

**Interfaces:**
- Produces fixtures:
  - `agent_database_url() -> str`;
  - `probe_view() -> str`, which creates `gold.sem_executor_probe(cod_uc text, kwh numeric)` with 3 rows as the owner, yields the name `sem_executor_probe` and drops it afterwards.

- [ ] Run `uv add 'psycopg[binary]'` and `uv add --dev pytest-asyncio`, then `uv run pytest -q`. Expected: the 75 existing tests pass.

### Task 2: Rows, columns and truncation

**Files:**
- Create: `ai-agent/src/venergy_agent/infrastructure/postgres_executor.py`
- Test: `ai-agent/tests/integration/test_postgres_executor.py`

**Interfaces:**
- Produces: `PostgresQueryExecutor(database_url: str, timeout_seconds: float)` with `async execute(query: ValidatedQuery) -> QueryResult`.

- [ ] **Failing tests:**
  - `test_returns_columns_and_rows`: `SELECT cod_uc, kwh FROM gold.sem_executor_probe ORDER BY cod_uc` with `applied_limit=200` → `columns == ("cod_uc", "kwh")`, `row_count == 3`, `rows[0]["cod_uc"] == "0001"`, `truncated is False`.
  - `test_marks_truncated_when_rows_reach_the_limit`: same SQL with `LIMIT 2` and `applied_limit=2` → `row_count == 2` and `truncated is True`.
- [ ] Run `uv run pytest tests/integration -q`. Expected: FAIL (import error).
- [ ] Implement it with `psycopg.AsyncConnection.connect` and the `dict_row` factory. `truncated = len(rows) >= query.applied_limit`.
- [ ] Run again. Expected: PASS.

### Task 3: Read-only guard and timeout

- [ ] **Failing tests:**
  - `test_database_refuses_writes_even_without_the_validator`: `ValidatedQuery(sql="INSERT INTO gold.sem_executor_probe VALUES ('9', 1)", ...)` raises `psycopg.errors.ReadOnlySqlTransaction`.
  - `test_slow_query_times_out`: executor with `timeout_seconds=0.2`, `SELECT pg_sleep(2)` → `QueryExecutionError` with `kind is ErrorKind.TIMEOUT`.
- [ ] Run. Expected: the timeout test FAILS. The write test may already pass because the role is read-only by default; keep it, since it is the guide's checklist item.
- [ ] Implement it: `BEGIN READ ONLY`, then `SET LOCAL statement_timeout = <ms>`, run the query, `ROLLBACK`. Map SQLSTATE `57014` to `TIMEOUT`.
- [ ] Run. Expected: PASS.

### Task 4: SQLSTATE classification

- [ ] **Failing test**, `test_classifies_errors_for_the_correction_loop`, parametrized:
  - `SELECT nope FROM gold.sem_executor_probe` → `UNKNOWN_OBJECT`;
  - `SELECT 1 FROM gold.sem_executor_probe WHERE cod_uc = 1` → `TYPE_MISMATCH`;
  - `SELECT FROM WHERE` → `SYNTAX`.
- [ ] **Failing test:** `test_permission_errors_are_not_classified` reads `app.ordem_teste`, created by the owner in the test, and expects `psycopg.errors.InsufficientPrivilege`.
- [ ] Implement a module constant `SQLSTATE_KINDS: dict[str, ErrorKind]`:
  - `42601` → `SYNTAX`;
  - `42P01`, `42703` → `UNKNOWN_OBJECT`;
  - `42804`, `42883`, `22P02` → `TYPE_MISMATCH`;
  - `57014` → `TIMEOUT`.

  Any other SQLSTATE re-raises the original error.
- [ ] Run. Expected: PASS.

### Task 5: Docs and verification

- [ ] `ai-agent/.env.example`: switch the URL to `postgresql://`.
- [ ] `README.md`: integration tests need `docker compose up -d --wait db` at the repo root.
- [ ] Spec §11 item 3: mark it done in this branch. Spec §10: add D6, the init script without the exec bit.
- [ ] Run `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`. Expected: all green.
- [ ] Run the `code-review` skill on the diff and fix the confirmed findings.
