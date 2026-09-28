# Blocker B - Evidence cycle specification

Entry point for the schema and generator specification that close the product-cycle evidence
blocker. Values are real product-execution data and are supplied by the `0921acpos` product line.

- `evidence_schema.yaml` - machine-readable schema for the five evidence files and their coupled
  registry updates, with every constraint traced to `file:line`.
- `GENERATOR_SPEC.md` - generator design: inputs, algorithm, validation loop, CLI contract,
  fail-closed rules.

## Regression-suite to blocker mapping

| Suite | Missing blocker | Note |
|-------|-----------------|------|
| `test_high_pressure_hardening.py` | B | `HIGH_PRESSURE_HARDENING_RESULT.yaml` not in root manifest |
| `test_v2_1_8_*` | B | missing `GOVERNANCE_CANDIDATE_STATE`/`HIGH_PRESSURE`/`REFERENCE_SEMANTIC` |
| `test_v2_1_9_*` | B | missing `GOVERNANCE_DEFECT_LEDGER`/`GITHUB_REPLAY_CLOSURE_RESULT` |
| `test_v2_1_12_*` | B | same as 8/9 |
| `test_execution_load_guard.py` | C | mother-spec anchors pending authoritative version |
| `test_bugfix_regressions.py` | A + C | external trust root + section registry anchor |

B closes the B rows only; A and C remain external.
