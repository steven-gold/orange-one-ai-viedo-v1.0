# Stage Execution Fixed Pattern

This directory holds the deterministic tooling that every governed-unit page run
uses. It turns the cross-stage handoff fix into a fixed, repeatable pattern so no
page or stage is ever run ad-hoc.

## Why this exists

The lifecycle orchestrator can only close a stage when the **successor stage Work
Unit already exists**. During closure it runs `_materialize_cross_stage_handoff`,
which reads the successor's `input_bindings` to bind the successor's declared
inputs. If the successor Work Unit is absent, closure fails with:

```
CROSS_STAGE_HANDOFF_INPUT_BINDING_UNRESOLVED:<stage>:<INPUT>
```

Materializing the successor scaffold by hand, per stage, was the source of drift.
The tools below make it automatic and deterministic.

## The fixed pattern

For each governed unit (page) and each stage:

1. `materialize_stage_work_unit.py` builds the stage Work Unit contract surface
   from authoritative sources only.
2. `run_stage.py` guarantees the successor Work Unit exists, then invokes the
   orchestrator `--run-stage`.
3. The orchestrator executes the stage, materializes the cross-stage handoff
   against the successor, closes the stage (`CLOSED_PASS`), and resolves the
   successor to `READY`.

Nothing here grants completion credit and nothing invents authority.

## Commands

Materialize one stage Work Unit:

```bash
python3 STAGE_EXECUTION/_tools/materialize_stage_work_unit.py \
  --stage STAGE-06 \
  --governed-unit GLOBAL-HOME-SHELL-NAVIGATION \
  --work-unit-uid WU-STAGE06-GLOBAL-HOME-SHELL-NAVIGATION-001
```

Run a stage with the successor guarantee:

```bash
python3 STAGE_EXECUTION/_tools/run_stage.py \
  --stage STAGE-05 \
  --governed-unit GLOBAL-HOME-SHELL-NAVIGATION
```

## Contract sources

| Contract element | Source |
| --- | --- |
| operations, outputs, output producers, validators, required evidence, exit gate, next stage, required normative sections, scanners | `.github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml` (`stages[]`) |
| successor input artifact refs + hashes | resolved from `inputs` + `input_origins` to the owning predecessor Work Unit on disk |
| Normative Execution Matrix section -> artifact -> required field mapping | `stage_specs/<STAGE>.yaml` (the only stage-local declaration) |

## Adding a stage spec

Copy an existing `stage_specs/STAGE-0X.yaml` and update the `nem` list so every
`required_normative_section_uids` entry from the master plan has exactly one row.
The generator fails loudly if the section universe and the spec rows diverge.

## Safety

- `materialize_stage_work_unit.py` refuses to overwrite an existing Work Unit
  unless `--force` is given, because overwriting resets the authoritative
  `EXECUTION_STATE` of a running or closed stage.
- After regenerating a successor Work Unit that a predecessor already adopted,
  re-run the predecessor stage so successor adoption is refreshed.
