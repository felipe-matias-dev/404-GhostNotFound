# AgentAnswer Contract Implementation Plan

> **Status (2026-10-22): implemented on branch `feat/ai-agent-contrato-answer`, not merged.** Decision record: DEC-020 (proposed). Merge waits for V1 agreement (spec §4).

**Goal:** give the backend a status-aware answer contract: `status`, `truncated`, `refused_reason`, `model` and `latency_ms`, with the invariants of spec §4.

**Architecture:** only `domain/answer.py` changes. `AnswerStatus` is a new enum. `AgentAnswer` gets one invariant check per status, in a single validator. No port or adapter changes in this branch.

**Spec:** `ai-agent/docs/specs/2026-10-19-architecture-design.md` §4 (domain), §11 (item 2).

## Global Constraints

- Branch `feat/ai-agent-contrato-answer`, based on `feat/ai-agent-camada-semantica` (item 5). Retarget to `main` after PR #20 merges.
- No commit without an explicit request.
- Code and tests in English, no comments.
- Models stay frozen; no field is removed.

## Review Focus

1. Each status has its own invariants, and a test rejects each violation (Task 1).
2. `answered` never carries `refused_reason` or `clarification` (Task 1).
3. `truncated` is only valid for `answered` (Task 1).

---

### Task 1: Status and invariants

**Files:** `src/venergy_agent/domain/answer.py`, `tests/unit/domain/test_answer.py`.

- [x] `AnswerStatus` with five values.
- [x] `truncated`, `refused_reason`, `model`, `latency_ms >= 0`.
- [x] One test per invariant from spec §4.
- [ ] **Pending:** V1 agreement on the contract (DEC-020).
