# Evaluation on Two Datasets (Sample and Real Gold) Implementation Plan

**Goal:** implement the GenAI part of issue #56. The golden set must be able to measure the agent on the real Gold without proving nothing on empty results, without sending Gold rows to the model and without committing reports that may carry real values.

**Architecture:** changes stay in `venergy_agent/evaluation/`, plus one optional dependency in `AskUseCase` (no answer writer means the deterministic text) and one flag in `bootstrap.build_agent`.

**Spec:** `ai-agent/docs/specs/2026-10-19-architecture-design.md` §9.1, §9.3 and §9.6 (finding 7). Issue #56. DEC-024.

## Global Constraints

- Branch `feat/ai-agent-avaliacao-duas-bases`. Code in English, no comments; docs in Portuguese.
- TDD for each rule below. Unit tests use fakes; nothing here calls the model.
- The golden set classification (`datasets`) made here is GenAI's first pass. Dados confirms it in the review of each item (issue #56).

## Rules

1. **`datasets` per golden item** (`[amostra]`, `[gold_real]` or both), required. The runner evaluates only the items of the chosen dataset and counts the others in `other_dataset_skipped`. Red team attacks don't depend on data and always run.
2. **Empty reference only with permission.** `allow_empty_reference` is false by default. A reference that returns no data on the loaded database, without permission, becomes a `reference_error` with `reference_empty = true`, and stays out of the execution accuracy. Today G019, G029 and G030 need the permission; G026 and G059 return empty on the sample by accident.
3. **`expected_values`** for items whose answer key is a published number and not a SQL (real Gold set from Dados). The reference becomes a single row with those values, compared with the same rule as a reference result.
4. **`--dataset amostra|gold_real`** in the CLI, recorded in the report. Before running, the CLI checks that the loaded database is the declared one: the sample has at most `SAMPLE_MAX_UCS` UCs in `sem_uc`, the real Gold has more.
5. **Reports of the real Gold go to `eval/runs_gold/`**, which is in `.gitignore`.
6. **SQL-only mode** (`--sql-only`): the agent is built without the answer writer, so no Gold row reaches the model; the answer is the deterministic text. The report records `narrated = false`, and numeric fidelity is `None`. `--dataset gold_real` always runs in this mode.

## Review Focus

1. A golden item outside the chosen dataset is never sent to the agent.
2. An empty reference without permission never counts as a match, even when the agent also returns nothing.
3. Running with `--dataset gold_real` against the sample database (or the opposite) stops before calling the model.
4. With `gold_real`, the answer writer is never built.
