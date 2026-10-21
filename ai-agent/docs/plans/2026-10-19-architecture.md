# Agent Architecture (Structure and Contracts) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status (2026-10-20): executed in PR #5** (`feat/ai-agent-esqueleto`, Lucas). Kept as the record of that work; do not re-run it.
> Deviations from this plan, accepted in the spec:
> - The PR also adds `infrastructure/sql_validator.py` (`sqlglot`), which this plan left out.
> - `sql_dialect` defaults to `postgres` (DEC-002).
> - It went through a feature branch and PR instead of a single commit on `main`, following the team rule in `CLAUDE.md`.
>
> Follow-up work changes contracts this plan created and gets its own plans: `AgentAnswer` gains `refused_reason`, `model` and `latency_ms` (spec §4), while the validator hardening (spec §6) is done in `fix/ai-agent-review-pr5`. Order in spec §11.

**Goal:** Create the `venergy_agent` package skeleton with domain models, ports and settings, covered by invariant tests.

**Architecture:** Hexagonal, 3 layers. `domain` (frozen pydantic models, no I/O) ← `application` (async `Protocol` ports) ← `infrastructure` (empty for now). No adapters in this plan.

**Tech Stack:** Python ≥3.12, uv, pydantic 2, pydantic-settings 2, pytest, ruff.

**Spec:** `ai-agent/docs/specs/2026-10-19-architecture-design.md`

## Global Constraints

- All work inside `ai-agent/`. Only root change allowed: the `.gitignore` lines already staged (`/meus-docs`, `.claude/`).
- Code in English, no comments, no docstrings.
- Every domain model uses `model_config = ConfigDict(frozen=True)`.
- `domain` imports nothing from the project; `application` imports only `domain`.
- No `pydantic-ai`, `sqlglot` or DB drivers yet; they arrive with their features.
- One single commit at the end (Task 7), after code review, **without** any `Co-Authored-By` trailer, on `main`.
- Tests only for project rules; no tests for enums, Protocols or library behavior.

## Review Focus

1. `SqlDraft(status=ok, sql="   ")`: a blank SQL must count as missing → rejected (Task 2).
2. `SqlDraft(status=clarify, clarification_question="")`: a blank question counts as missing → rejected (Task 2).
3. `SemanticLayer` with two views of the same name makes the allowlist ambiguous → rejected (Task 3).
4. A developer's local `.env` leaking into settings tests → tests build `AgentSettings(_env_file=None)` (Task 6).
5. `repr(settings)` must never expose the OpenRouter key → asserted (Task 6).

---

### Task 1: Project scaffold and `Question`

**Files:**
- Create: `ai-agent/pyproject.toml`
- Create: `ai-agent/src/venergy_agent/__init__.py`, `domain/__init__.py`, `application/__init__.py`, `infrastructure/__init__.py` (all empty)
- Create: `ai-agent/src/venergy_agent/domain/question.py`
- Test: `ai-agent/tests/unit/domain/test_question.py`

**Interfaces:**
- Produces: `Question(text: str, session_id: str, request_id: str = <uuid4 hex>)`

- [ ] **Step 1: Write `pyproject.toml`**: project `venergy-agent`, `requires-python = ">=3.12"`, deps `pydantic>=2.11`, `pydantic-settings>=2.10`. Dependency group `dev`: `pytest>=8`, `ruff>=0.13`. Build backend `hatchling` with `packages = ["src/venergy_agent"]`. `[tool.pytest.ini_options] testpaths = ["tests"]`. `[tool.ruff] line-length = 100`, `lint.select = ["E","F","I","UP","B","SIM"]`. Run `uv sync` and expect success.

- [ ] **Step 2: Write the failing tests**

```python
@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_blank_text_is_rejected(text):
    with pytest.raises(ValidationError):
        Question(text=text, session_id="s1")

def test_text_is_stripped_and_request_id_generated():
    question = Question(text="  receita de 03/2025?  ", session_id="s1")
    assert question.text == "receita de 03/2025?"
    assert question.request_id
```

- [ ] **Step 3: Run** `uv run pytest tests/unit/domain/test_question.py -v` → FAIL (import error).

- [ ] **Step 4: Implement `Question`** in `domain/question.py`: `text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]`, `request_id: str = Field(default_factory=lambda: uuid4().hex)`.

- [ ] **Step 5: Run** the same command → PASS.

### Task 2: SQL contracts and errors

**Files:**
- Create: `ai-agent/src/venergy_agent/domain/sql.py`, `ai-agent/src/venergy_agent/domain/errors.py`
- Test: `ai-agent/tests/unit/domain/test_sql.py`

**Interfaces:**
- Produces:
  - `DraftStatus(StrEnum)`: `OK="ok"`, `UNKNOWN="unknown"`, `CLARIFY="clarify"`, `REFUSE="refuse"`.
  - `SqlDraft(status: DraftStatus, sql: str | None = None, views_used: tuple[str, ...] = (), assumptions: tuple[str, ...] = (), clarification_question: str | None = None)`.
  - `ErrorKind(StrEnum)`: `SYNTAX`, `UNKNOWN_OBJECT`, `TYPE_MISMATCH`, `TIMEOUT`.
  - `AttemptFeedback(previous_sql: str, error_kind: ErrorKind, message: str)`.
  - `ValidatedQuery(sql: str, views: frozenset[str], applied_limit: int)`.
  - `QueryResult(columns: tuple[str, ...], rows: tuple[dict[str, object], ...], row_count: int, truncated: bool)`.
  - `SqlRejected(Exception)` with attribute `reason: str`; `QueryExecutionError(Exception)` with attributes `kind: ErrorKind` and `message: str`. Both live in `errors.py`, and `ErrorKind` lives in `errors.py` too (`sql.py` imports it).

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize(
    "fields",
    [
        {"status": "ok"},
        {"status": "ok", "sql": "   "},
        {"status": "clarify"},
        {"status": "clarify", "clarification_question": " "},
        {"status": "unknown", "sql": "SELECT 1"},
        {"status": "refuse", "sql": "DROP TABLE x"},
    ],
)
def test_inconsistent_draft_is_rejected(fields):
    with pytest.raises(ValidationError):
        SqlDraft(**fields)

def test_ok_draft_is_accepted():
    draft = SqlDraft(status="ok", sql="SELECT 1", views_used=("sem_faturamento_mensal",))
    assert draft.status is DraftStatus.OK
```

- [ ] **Step 2: Run** `uv run pytest tests/unit/domain/test_sql.py -v` → FAIL.

- [ ] **Step 3: Implement** the models and errors listed above. Use a `model_validator(mode="after")` on `SqlDraft`; a blank string (after `strip`) counts as missing.

- [ ] **Step 4: Run** → PASS.

### Task 3: Semantic layer

**Files:**
- Create: `ai-agent/src/venergy_agent/domain/semantic.py`
- Test: `ai-agent/tests/unit/domain/test_semantic.py`

**Interfaces:**
- Consumes: `DraftStatus` (Task 2).
- Produces:
  - `ColumnSpec(name: str, type: str, description: str, unit: str | None = None, allowed_values: tuple[str, ...] = ())`.
  - `ViewSpec(name: str, description: str, grain: str, columns: tuple[ColumnSpec, ...], sample_rows: tuple[dict[str, object], ...] = ())`.
  - `Relation(left_view, left_column, right_view, right_column: str)`.
  - `GlossaryTerm(term: str, synonyms: tuple[str, ...], maps_to: str)`, `BusinessRule(text: str)`, `FewShotExample(question: str, sql: str | None, expected_status: DraftStatus)`.
  - `SemanticLayer(version: str, views: tuple[ViewSpec, ...], relations: tuple[Relation, ...] = (), glossary: tuple[GlossaryTerm, ...] = (), rules: tuple[BusinessRule, ...] = (), examples: tuple[FewShotExample, ...] = ())` with the property `allowed_views -> frozenset[str]`.

- [ ] **Step 1: Write the failing tests.** Fixture: views `sem_uc(cod_uc)` and `sem_faturamento_mensal(cod_uc, competencia)`.

```python
def test_allowed_views_lists_view_names(layer):
    assert layer.allowed_views == frozenset({"sem_uc", "sem_faturamento_mensal"})

@pytest.mark.parametrize(
    "relation",
    [
        Relation(left_view="sem_x", left_column="cod_uc", right_view="sem_uc", right_column="cod_uc"),
        Relation(left_view="sem_faturamento_mensal", left_column="nope", right_view="sem_uc", right_column="cod_uc"),
    ],
)
def test_relation_to_unknown_view_or_column_is_rejected(views, relation):
    with pytest.raises(ValidationError):
        SemanticLayer(version="v0", views=views, relations=(relation,))

def test_duplicate_view_names_are_rejected(views):
    with pytest.raises(ValidationError):
        SemanticLayer(version="v0", views=views + views[:1])
```

- [ ] **Step 2: Run** `uv run pytest tests/unit/domain/test_semantic.py -v` → FAIL.

- [ ] **Step 3: Implement** in `semantic.py`, using one `model_validator(mode="after")` for both the uniqueness check and the relation check.

- [ ] **Step 4: Run** → PASS.

### Task 4: Answer contracts

**Files:**
- Create: `ai-agent/src/venergy_agent/domain/answer.py`
- Test: `ai-agent/tests/unit/domain/test_answer.py`

**Interfaces:**
- Produces:
  - `Confidence(StrEnum)`: `HIGH`, `MEDIUM`, `LOW`, `UNKNOWN`.
  - `AgentAnswer(answer: str, sql: str | None, rows: tuple[dict[str, object], ...], row_count: int, confidence: Confidence, sources: tuple[str, ...], assumptions: tuple[str, ...], clarification: str | None, request_id: str, prompt_version: str)`.
  - `Insight(text: str, metrics_used: tuple[str, ...])`.

- [ ] **Step 1: Write the failing test**

```python
def test_row_count_below_sample_size_is_rejected():
    with pytest.raises(ValidationError):
        AgentAnswer(answer="x", sql="SELECT 1", rows=({"a": 1}, {"a": 2}), row_count=1,
                    confidence="high", sources=(), assumptions=(), clarification=None,
                    request_id="r1", prompt_version="v1")
```

- [ ] **Step 2: Run** `uv run pytest tests/unit/domain/test_answer.py -v` → FAIL.
- [ ] **Step 3: Implement** in `answer.py`.
- [ ] **Step 4: Run** → PASS.

### Task 5: Ports

**Files:**
- Create: `ai-agent/src/venergy_agent/application/ports.py`

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces (all `typing.Protocol`, all methods `async` except `SqlValidator.validate`):
  - `TextToSqlAgent.ask(question: str, session_id: str) -> AgentAnswer`
  - `SemanticLayerSource.load() -> SemanticLayer`
  - `SqlGenerator.generate(question: Question, layer: SemanticLayer, feedback: AttemptFeedback | None) -> SqlDraft`
  - `SqlValidator.validate(sql: str, allowed_views: frozenset[str]) -> ValidatedQuery`
  - `QueryExecutor.execute(query: ValidatedQuery) -> QueryResult`
  - `AnswerWriter.write(question: Question, draft: SqlDraft, result: QueryResult) -> str`
  - `InsightWriter.narrate(screen: str, metrics: Mapping[str, object]) -> Insight`

- [ ] **Step 1: Write** `ports.py`. No tests (Protocols carry no behavior).
- [ ] **Step 2: Run** `uv run ruff check . && uv run python -c "import venergy_agent.application.ports"` → no errors.

### Task 6: Settings

**Files:**
- Create: `ai-agent/src/venergy_agent/config.py`, `ai-agent/.env.example`
- Test: `ai-agent/tests/unit/test_config.py`

**Interfaces:**
- Produces: `AgentSettings(BaseSettings)` with `env_prefix="VENERGY_AGENT_"`, `env_file=".env"`, fields and bounds exactly as in spec §7 (`openrouter_api_key: SecretStr`, `sql_dialect: Literal["sqlite", "postgres"]`, `temperature: float = Field(0.0, ge=0, le=0.2)`, `max_correction_attempts: int = Field(3, ge=1, le=3)`, positive ints via `gt=0`).

- [ ] **Step 1: Write the failing tests.** Fixture `required_env(monkeypatch)` sets `VENERGY_AGENT_OPENROUTER_API_KEY=sk-test-123` and `VENERGY_AGENT_DATABASE_URL=sqlite:///gold.db`. Every construction passes `_env_file=None`.

```python
def test_prefixed_env_overrides_default(required_env, monkeypatch):
    monkeypatch.setenv("VENERGY_AGENT_MAX_ROWS", "50")
    assert AgentSettings(_env_file=None).max_rows == 50

def test_missing_api_key_fails(monkeypatch):
    monkeypatch.setenv("VENERGY_AGENT_DATABASE_URL", "sqlite:///gold.db")
    monkeypatch.delenv("VENERGY_AGENT_OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        AgentSettings(_env_file=None)

@pytest.mark.parametrize(("name", "value"), [("TEMPERATURE", "0.5"), ("MAX_CORRECTION_ATTEMPTS", "0"), ("MAX_CORRECTION_ATTEMPTS", "4")])
def test_out_of_range_values_are_rejected(required_env, monkeypatch, name, value):
    monkeypatch.setenv(f"VENERGY_AGENT_{name}", value)
    with pytest.raises(ValidationError):
        AgentSettings(_env_file=None)

def test_api_key_is_not_exposed(required_env):
    assert "sk-test-123" not in repr(AgentSettings(_env_file=None))
```

- [ ] **Step 2: Run** `uv run pytest tests/unit/test_config.py -v` → FAIL.
- [ ] **Step 3: Implement** `config.py`. Write `.env.example` listing every `VENERGY_AGENT_*` variable, with placeholder values for the two required ones.
- [ ] **Step 4: Run** → PASS.

### Task 7: README, verification, review and commit

**Files:**
- Modify: `ai-agent/README.md` (keep the existing paragraph; add "Arquitetura" with the layer rule, a link to the spec, and "Como rodar" with `uv sync`, `cp .env.example .env`, `uv run pytest`)

- [ ] **Step 1: Update** `README.md`.
- [ ] **Step 2: Run** `cd ai-agent && uv run ruff check . && uv run ruff format --check . && uv run pytest -q` → all green, 0 failures.
- [ ] **Step 3: Run** `grep -rn "#" ai-agent/src` → no comments in source.
- [ ] **Step 4: Run** the `code-review` skill on the working tree diff and address the confirmed findings.
- [ ] **Step 5: Commit** on `main`, with no Co-Authored-By trailer:

```bash
git add .gitignore ai-agent
git commit -m "feat(ai-agent): estrutura hexagonal e contratos do agente text-to-sql"
```
