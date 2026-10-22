# Semantic Layer Implementation Plan

> **Status (2026-10-22): implemented on branch `feat/ai-agent-camada-semantica`.** Recorded work, do not re-run. Spec §11, item 5.

**Goal:** validate a semantic layer written by the GenAI against the Gold contract, and generate the `views.sql` that the backend applies in the database.

**Architecture:** a YAML file chooses the views, columns and examples. An adapter validates each view against `contracts/gold_schema.yaml` and builds the relations. A generator writes `semantic/views.sql` from the same validated layer.

**Spec:** `ai-agent/docs/specs/2026-10-19-architecture-design.md` §4, §5 (`SemanticLayerSource`), §10 (D7), §11 (item 5).

## Global Constraints

- Branch `feat/ai-agent-camada-semantica`, from `main`. One PR, reviewed by GenAI (Perylo) before merge.
- No commit without an explicit request.
- Code and tests in English, no comments. Descriptions in the YAML in Portuguese.
- Only `gold_dim_uc`, `gold_fato_faturamento_mensal` and `gold_continuidade_alimentador_mensal` in the first version.

## Review Focus

1. A column marked `a_confirmar` never reaches a view (Task 1).
2. A view whose primary key is not confirmed or proposed is rejected at load time (Task 1).
3. `views.sql` matches what the generator produces from the YAML (Task 1).

---

### Task 1: Validated layer and generated views

**Files:** `semantic/semantic_layer.yaml`, `semantic/views.sql` (generated), `src/venergy_agent/infrastructure/semantic_source.py`, `src/venergy_agent/infrastructure/views_sql.py`, `tests/unit/infrastructure/test_semantic_source.py`, `tests/unit/infrastructure/test_views_sql.py`, `tests/integration/test_semantic_views.py`, `tests/integration/conftest.py`.

- [x] Three views, validated against the contract, all errors reported together.
- [x] Relations from foreign keys and entity keys (DEC-018, proposed).
- [x] `views.sql` generated, with a drift test (`--check`).
- [x] Integration test: Gold tables with contract types, views applied as the owner, queried by the agent role through the validator and the executor.
- [ ] **Pending before production:** the backend applies `views.sql` and drops the views before reloading the Gold (spec §10, D7).
