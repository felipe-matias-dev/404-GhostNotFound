# Answer Writer and Numeric Verification Implementation Plan

> **Status (2026-10-23): rebuilt on `main` as branch `feat/ai-agent-narracao-v2`, after PR #30.** The writer is injected by `build_agent`; bootstrap and the terminal command already came with item 6. DEC-019 accepted: the narrative is read in pt-BR only, row values by their own type, and the prompt no longer allows numbers that are only in the question. The narration prompt is a new version, `prompts/answer/v1`, and is not yet measured against the golden set (spec §9.5): that measurement is item 7, which is out of this sequence.

**Goal:** narrate the query result in Portuguese, using only the returned rows, and fall back to the deterministic text whenever the narration contains a number that is not in the rows (spec §5.2 and §11, item 8).

**Architecture:**
- `domain/numbers.py` is a pure function: it extracts numbers from text and reports the ones no source contains. It is shared with item 9.
- `infrastructure/answer_writer.py` is a PydanticAI adapter. The rows travel inside a delimited data block, with a random label per instance.
- `ask()` calls the writer and checks the numbers. Any failure keeps the deterministic text.
- `bootstrap.py` injects the writer into the use case (bootstrap itself came with item 6).

**Spec:** `ai-agent/docs/specs/2026-10-19-architecture-design.md` §5.1 (step 7), §5.2 (data is not instructions), §8 (tests), §11 (item 8).

## Global Constraints

- Branch `feat/ai-agent-narracao`, based on `feat/ai-agent-ask`.
- No commit without an explicit request.
- Code and tests in English, no comments. Prompt text in Portuguese.
- Every number in the narrative must exist in the returned rows or in the row count (DEC-019).

## Review Focus

1. A number that is not in the rows rejects the narrative (Task 1).
2. A narrative that cites a number from the question or from the assumptions is rejected (Task 1).
3. The rows reach the model inside the delimited data block, with a redacted label (Task 2).

---

### Task 1: Numeric verification

**Files:** `src/venergy_agent/domain/numbers.py`, `tests/unit/domain/test_numbers.py`, `src/venergy_agent/application/ask.py`, `tests/unit/application/test_ask.py`.

- [x] Pure function `unsupported_numbers(text, sources)`, reading both pt-BR and en numbers.
- [x] Sources are only the row values and the row count (DEC-019).
- [x] A failed verification or a writer error keeps the deterministic text.

### Task 2: Narration adapter and prompt

**Files:** `src/venergy_agent/infrastructure/answer_writer.py`, `src/venergy_agent/infrastructure/prompt_renderer.py`, `prompts/answer/v1/answer.md`, `tests/unit/infrastructure/test_answer_writer.py`, `tests/unit/infrastructure/test_prompt_renderer.py`.

- [x] The rows are delimited as data, with a random label per instance and redaction of the label.
- [x] Prompt versioned under `prompts/answer/v1/`, separate from the SQL prompt.

### Task 3: Composition root and terminal command

**Files:** `src/venergy_agent/bootstrap.py`, `src/venergy_agent/__main__.py`, `src/venergy_agent/config.py`, `tests/unit/test_bootstrap.py`, `tests/unit/test_config.py`.

- [x] `build_agent` fails at startup if the semantic layer is invalid.
- [x] `python -m venergy_agent "question"` prints the answer as JSON on stdout and the step logs on stderr.
