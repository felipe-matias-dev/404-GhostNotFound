# SQL Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status (2026-10-22): executed in PRs #13 and #14** (merged). Kept as the record of that work; do not re-run it.
> #14 replaced the tag escaping with a random label per generator instance (`<dados-{nonce}>`, spec §5.2), moved the previous SQL and the error message into data blocks, and changed `prompts/v1` before it reached `main` (DEC-016). Next change to the prompt goes to `prompts/v2`.

**Goal:** Implement the `SqlGenerator` port with PydanticAI. The prompt is versioned and built from the `SemanticLayer`, and the structured output is validated as `SqlDraft`.

**Architecture:** There are two units.
- **Renderer:** a pure prompt renderer that turns a template plus a `SemanticLayer` into the system prompt, and a question plus optional `AttemptFeedback` into the user prompt.
- **Adapter:** a thin PydanticAI adapter that runs an `Agent(output_type=SqlDraft)` on that prompt.

The model is built from `AgentSettings` by a small factory.

**Tech Stack:** pydantic-ai-slim[openrouter]. Tests use `FunctionModel`, so there are no API calls.

> **Update (2026-10-21):** after this plan was written, Gemini direct (`google-gla:`) became the default provider and OpenRouter the alternative (spec §2). `build_model` builds by prefix, and `AgentSettings` requires only the key of the chosen providers. A real smoke test hit a Gemini 503 (high demand), so the Gemini client now retries 429/503 with exponential backoff (`llm_retry_attempts`, `llm_retry_initial_delay_seconds`); OpenRouter keeps its SDK's native retries.

**Spec:** `ai-agent/docs/specs/2026-10-19-architecture-design.md` (§5 port and "dados não são instruções", §11 item 4). Design approved in chat on 2026-10-21.

## Global Constraints

- Branch `feat/ai-agent-gerador`. No commit without explicit request.
- Code in English, no comments. Prompt text in Portuguese, the language of the questions and the domain.
- Prompts live in `ai-agent/prompts/v1/`, never as strings in code. The version comes from `AgentSettings.prompt_version`.
- The system prompt must not depend on the question, so it can be cached. Order: role and restrictions → business rules and glossary → views → few-shot examples (guide §3.1).
- `sample_rows` and `allowed_values` are rendered inside `<dados>` … `</dados>`. The question is rendered inside `<pergunta>` … `</pergunta>`.
- `output_retries=2`: an invalid `SqlDraft` is sent back to the model, never raised on the first try.

## Review Focus

1. A question containing "ignore as instruções" must end up only inside `<pergunta>`, never in the system prompt (Task 2).
2. A sample value containing `</dados>` must not close the data block early (Task 2: escape it).
3. A layer with no glossary, rules or examples must render without empty headings (Task 2).
4. A missing prompt version must fail when the generator is created, not on the first question (Task 3).

---

### Task 1: Dependency and API probe
- [ ] Run `uv add 'pydantic-ai-slim[openrouter]'`.
- [ ] Probe the installed `FunctionModel`, the output tool name in `AgentInfo`, `OpenRouterModel`, `OpenRouterProvider` and `FallbackModel`, and write the tests against what exists.

### Task 2: Prompt renderer
**Files:** create `infrastructure/prompt_renderer.py`, `prompts/v1/system.md`, `prompts/v1/correction.md`. Test: `tests/unit/infrastructure/test_prompt_renderer.py`.

**Interfaces:**
- `render_system_prompt(template: str, layer: SemanticLayer) -> str`
- `render_user_prompt(question: Question, feedback: AttemptFeedback | None, correction_template: str, layer: SemanticLayer) -> str`

**Tests:**
- every view name, column description, unit, allowed value, relation, glossary synonym, rule and example appears in the system prompt;
- sample rows appear inside `<dados>`;
- the system prompt is identical for two different questions;
- the question appears only inside `<pergunta>`;
- `</dados>` inside a sample value is escaped;
- an empty layer has no "Glossário" heading;
- with feedback, the user prompt carries the previous SQL, the error kind, the message and the columns of the views that appear in the previous SQL.

### Task 3: Generator adapter
**Files:** create `infrastructure/sql_generator.py`. Test: `tests/unit/infrastructure/test_sql_generator.py`.

**Interfaces:**
- `PydanticAiSqlGenerator(model: Model, prompts_dir: Path, prompt_version: str, temperature: float)`, which implements `SqlGenerator`.

**Tests**, with a `FunctionModel` that captures the messages:
- returns the `SqlDraft` the model produced;
- an invalid output followed by a valid one returns the valid one, and the model was called twice;
- the request carries the rendered system prompt and the user prompt;
- an unknown `prompt_version` raises at construction.

### Task 4: Model factory
**Files:** create `infrastructure/llm.py`. Test: `tests/unit/infrastructure/test_llm.py`.

**Interfaces:**
- `build_model(settings: AgentSettings) -> Model`: an `OpenRouterModel` built from `llm_model` (the `openrouter:` prefix is stripped) and the API key. When `fallback_model` is set, it returns a `FallbackModel` of both.

**Tests:**
- the model name comes from the settings;
- a `FallbackModel` is returned when a fallback is set.

### Task 5: Docs and verification
- [ ] Spec §11 item 4: mark it done in this branch.
- [ ] README: where the prompts live.
- [ ] Run `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`. Expected: all green.
- [ ] Run `code-review` on the diff and fix the confirmed findings.
