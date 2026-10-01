# User Instruction Memory

This file records user instructions and project knowledge for future work in this repository.

## Entries

[User Instruction Summary]
- Date: 2026-10-01
- Context: User observed a paused turn during governed stage execution and required the failure to be diagnosed before continuing.
- Instructions:
  - When a model call fails or the execution appears stuck, STOP advancing the task and first diagnose the failure cause and the resolution, instead of silently continuing.
  - Always report the concrete diagnosis (what is actually running, what state the pipeline is in, why it paused) before resuming any long-running step.

[Project Knowledge Summary]
- Date: 2026-10-01
- Context: Discovered by Agent while executing the governed stage lifecycle (STAGE-05 IMPLEMENTATION of GLOBAL-HOME-SHELL-NAVIGATION).
- Category: Workflow & Collaboration
- Instructions:
  - The authoritative governance engine lives outside this repo at `/tmp/opencode/rebuild-v2.1.1/governance/ci/`.
  - Run a stage: `python3 stage_lifecycle_orchestrator.py --run-stage --stage STAGE-05 --work-unit STAGE_EXECUTION/STAGE-05/<WU>/WORK_UNIT.yaml --product-root /workspace`.
  - Engine admission check: `python3 stage_execution_engine.py --admission-check --stage <STAGE>` with env `STAGE_EXECUTION_ROOT=/workspace`, `STAGE_ACTIVE_WORK_UNIT=<wu rel path>`, `STAGE_CURRENT_SCOPE=<scope rel path>`.
  - A stage can only reach `CLOSED_PASS` if the successor stage's Work Unit already exists: the predecessor's `_materialize_cross_stage_handoff` reads the successor's `input_bindings` (or an existing `CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml`) to bind the successor's declared inputs. Materialize the next stage WU scaffold before closing the current stage.
  - Successor WU directory must contain exactly one `WORK_UNIT.yaml` with matching `stage_uid` + `governed_unit_uid`; the orchestrator adopts it and returns successor status `READY`.
  - Stage scaffolds are generated deterministically (see `/tmp/opencode/build_stage05_scaffold.py`, `/tmp/opencode/build_stage06_scaffold.py`) and are non-authoritative until the stage runs.
  - The normative `input_origins` mapping per stage is defined in `.github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml`; successor input bindings must match these origins exactly.

[Project Knowledge Summary]
- Date: 2026-10-01
- Context: Discovered by Agent while verifying the materialized GLOBAL-HOME-SHELL-NAVIGATION homepage.
- Category: Operations & Deployment
- Instructions:
  - The governed unit program is an npm workspace at the product root: `apps/web` (React + TypeScript + Vite) and `apps/api` (Node.js + Express).
  - Web dev server runs on port 5173 and proxies `/api` to the API at `http://localhost:3001`; expose port 5173 for preview.
  - Both services must run together for the shell to resolve navigation (frontend calls `/api/navigation`).

[Project Knowledge Summary]
- Date: 2026-10-01
- Context: Discovered by Agent while completing STAGE-11 after a mid-operation engine failure.
- Category: Troubleshooting & Debugging
- Instructions:
  - Operation receipts are write-once: `stage_execution_engine.execute_active` fails with `ACTIVE_STAGE_OPERATION_RECEIPT_ALREADY_EXISTS` if a receipt exists while `EXECUTION_STATE.completed_operations` does not yet list that operation (e.g. a prior step-validation failure left an orphan receipt). Do not delete the receipt; reconcile `EXECUTION_STATE.yaml` by moving that operation into `completed_operations`, advancing `current_operation` to the next master-plan operation, and updating `last_operation_uid` / `last_operation_receipt_ref`.
  - The engine validates every existing NEM artifact's required `field_path` after each operation, so an operation must write its output artifact with ALL of that artifact's NEM-required fields in one shot; a partially-populated artifact blocks the step.
  - Each stage executor only needs to write operation outputs + receipts; preflight, scanners, validators, required-evidence assembly, cross-stage handoff and closure are done by the orchestrator.
