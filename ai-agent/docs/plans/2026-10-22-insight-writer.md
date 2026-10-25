# InsightWriter Implementation Plan

> **Status (2026-10-23): rebuilt as branch `feat/ai-agent-insight-v2`, on top of PR #36 (item 8).** It uses the DEC-019 verification from #36: the text is read in pt-BR only, and the values of the metrics JSON are the number source (nested values included, keys excluded: a number that only appears in a key such as `receita_2024` does not validate the text, per Lucas in commit 4f88343). Merged into `main` through the narration branch, because PR #37 was merged into its base after PR #36 had already gone to `main`. The prompt now asks for the Brazilian number format. The composition-root wiring is not included: the backend (D9) decides how and when screens request insights.

**Goal:** narrate the metrics of a screen in two to four sentences, and return `None` whenever the text contains a number that is not in the metrics JSON (spec §11, item 9; ADR-04).

**Architecture:** `infrastructure/insight_writer.py` is a PydanticAI adapter of the `InsightWriter` port. It reuses the numeric verification from `domain/numbers.py`, so the same rule applies to the answer and to the insight. The port now returns `Insight | None`.

**Spec:** `ai-agent/docs/specs/2026-10-19-architecture-design.md` §5 (port), §9 (insight rules), §10 (D9), §11 (item 9).

## Global Constraints

- Branch `feat/ai-agent-insight`, based on `feat/ai-agent-narracao`.
- No commit without an explicit request.
- Code and tests in English, no comments. Prompt text in Portuguese.
- The insight never states a cause unless the metrics state it.

## Review Focus

1. A number outside the metrics JSON returns `None` (Task 1).
2. A provider error returns `None` instead of raising (Task 1).
3. The metrics reach the model as delimited data, with a redacted label (Task 1).

---

### Task 1: Writer, prompt and port

**Files:** `src/venergy_agent/infrastructure/insight_writer.py`, `src/venergy_agent/infrastructure/prompt_renderer.py`, `src/venergy_agent/application/ports.py`, `prompts/insight/v1/insight.md`, `tests/unit/infrastructure/test_insight_writer.py`.

- [x] Insight text is verified against the metrics JSON; metrics used are the JSON keys.
- [x] Provider errors and unverified numbers return `None`.
- [x] Prompt versioned under `prompts/insight/v1/`.
- [ ] **Pending:** wiring into the backend (spec §10, D9) and the cache by filter combination.
