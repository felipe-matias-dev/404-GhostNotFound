# Semantic Layer v0.3 Implementation Plan

**Goal:** bring the Gold contract v0.3 (PR #43, DEC-027 to DEC-030) to the agent: the per-UC tables of the UC 360 (interruptions, customer service and meter), the new columns of the registry, the billing fact and the segment KPIs, and the glossary and rules that go with them.

**Spec:** `ai-agent/docs/specs/2026-10-19-architecture-design.md` §3 (semantic layer), §9.5 (DEC-016) and §11. Issue #56 (G062).

## Global Constraints

- Branch `feat/ai-agent-camada-v0.3`, from `main`. Code in English, no comments; docs in Portuguese.
- Every view and column passes the contract checks of `semantic_source.py` (DEC-022): table with `agente` in `consumers`, column `confirmada` or `proposta`, never `sensitive`.
- Sample rows are synthetic, written by hand.
- Golden set items (G062 to `answered`, new per-UC items) wait for #57 and #65, which also change `golden_set.yaml`. The DEC-016 run happens once, with those items, when the Gemini quota allows.

## Changes

1. **Relations rule (TDD).** A key covered by a foreign key of the contract to a view of the layer links only through that foreign key. Shared-key links (`ENTITY_KEYS`) stay only for keys without a foreign key, such as `cod_alimentador`. Without this, every view with `cod_uc` would link to every other one (billing × interruptions × customer service), and a join between two event tables multiplies sums.
2. **New views:**
   - `sem_interrupcoes_uc` (`gold_interrupcoes_uc`), without `cod_alimentador`, which comes from `sem_uc`;
   - `sem_atendimentos_uc` (`gold_atendimentos_uc`);
   - `sem_medidor_uc` (`gold_medidor_uc`).
3. **New columns:**
   - `sem_uc`: connection date, GD connection date, GD mode, injected energy and peak power;
   - `sem_faturamento_mensal`: flag revenue, due and payment dates, payment status, days late, reading type, meter type and billed days. `kwh_leitura` and `origem_kwh` stay out: they are data-quality columns, and next to `kwh_faturado` they invite the model to pick the wrong energy;
   - `sem_kpis_segmento_mensal`: flag revenue, invoice, delinquency and reading components.
4. **Glossary and rules:** occurrence, meter, delinquency and estimated reading; the rule that said the per-UC data was not in the views changes; DEC-032 is no longer a proposal.
5. **Version 0.4.0** of the layer, `views.sql` regenerated, integration fixtures with the new tables.

## Review Focus

1. No link between two event views (billing, interruptions, customer service).
2. The registry ↔ continuity link by feeder stays (UC 360 asks for the DEC of the UC's feeder).
3. No sensitive column reaches a view.
