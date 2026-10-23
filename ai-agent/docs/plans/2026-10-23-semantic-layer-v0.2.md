# Semantic Layer v0.2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the semantic layer with the Gold contract v0.2.0 (PR #23). Enforce the DEC-022 access rule in code, drop the date range copied from the synthetic sample, and add the KPI and revenue decomposition views.

**Architecture:** No new module. `semantic_source.py` gains two checks. `semantic_layer.yaml` gains three views. `views.sql` is regenerated.

> **Status (2026-10-23): executed on the branch.** The branch also merges PRs #29 and #31, so their conflicts in `decisoes.md`, the spec and `CLAUDE.md` are already resolved. Merge order: #29 → #31 → this branch → #30 → #32.

**Spec:** `ai-agent/docs/specs/2026-10-19-architecture-design.md` (§5 item 5, §10 D7, §11). Requested in chat on 2026-10-23.

## Global Constraints

- Branch `feat/ai-agent-camada-semantica-v0.2`. No commit without explicit request.
- Code in English, no comments. Docs and prompt text in Portuguese.
- Sample rows stay synthetic and hand-written.
- Only GenAI files change (`ai-agent/` and the GenAI decisions in `docs/decisoes.md`).

## Review Focus

1. A table without `agente` in `consumers` must be rejected, even if the YAML lists it (Task 1).
2. A column with `sensitive: true` must be rejected (Task 1).
3. `sem_receita_decomposicao` must not get a relation to any other view (DEC-018: composite join still open) (Task 2).
4. Index metrics in `sem_kpis_segmento_mensal` (DEC, FEC, satisfaction) are computed from summed components, never averaged across rows (Task 3).

---

### Task 1: DEC-022 access rule in code
**Files:** modify `infrastructure/semantic_source.py`. Test: `tests/unit/infrastructure/test_semantic_source.py`.

**Tests:**
- a view over a table whose `consumers` does not include `agente` is rejected;
- a column with `sensitive: true` is rejected.

### Task 2: New views
**Files:** `semantic/semantic_layer.yaml`, `semantic/views.sql` (regenerated). Test: the real-files test lists the six views; the decomposition view has no relation.

- `sem_kpis_mensais` ← `gold_kpis_mensais`.
- `sem_kpis_segmento_mensal` ← `gold_kpis_segmento_mensal`.
- `sem_receita_decomposicao` ← `gold_receita_decomposicao`.

### Task 3: Rules, glossary and examples
- Remove the fixed 2024-01 to 2025-12 rule.
- Replace "satisfação não está nas views" with rules for chamados and satisfação.
- Rules for segment indices (sum components, then divide) and for decomposition periods (`AAAA-MM/AAAA-MM`; ask for clarification when the pair is not given).
- The chamados example becomes answerable; add one decomposition example.

### Task 4: Docs and verification
- [ ] Spec §1, §11 (items 2 and 5 done), §10 D4; DEC-018 and DEC-020 accepted; `README.md`; `docs/architecture.md`.
- [ ] Run `uv run pytest -q && uv run ruff check . && uv run ruff format --check .` and `views_sql --check`.
- [ ] Run `code-review` on the diff and fix the confirmed findings.
