# HOME + WB01 Clean Bootstrap Current Execution

Current product branch: `0921acpos`

Current Governance:
- UID: `GOV-REV-20260928-WORD-DERIVED-STAGE-INTERNAL-VALIDATION`
- exact head: `c353d7bdb5dc7edb43c6c7453517d1df75d54ce8`

Current authorization:
- Issue #61
- clean-bootstrap authorization comment id: `5877510981`

## Current rule

HOME and WB01 Stage-01..04 generated execution data has been intentionally purged by explicit user authorization.

A fresh execution MUST begin from:
1. canonical root Word source;
2. exact selected Current Governance;
3. Current Authority;
4. a newly materialized `INITIAL_STAGE_WORK_UNIT`.

A fresh run MUST NOT require or restore:
- predecessor Work Unit;
- predecessor Segment Map;
- predecessor Normative Execution Matrix;
- predecessor classification artifacts;
- predecessor blueprints;
- predecessor terminal receipt;
- historical PASS or historical completion credit.

Historical Git data MAY be inspected for defect analysis only. It MUST NOT become a runtime input or Current completion evidence.

## Current Stage-01 Work Unit identities

- `WU-STAGE01-GLOBAL-HOME-SHELL-NAVIGATION-CLEAN-001`
- `WU-STAGE01-WB01-DASHBOARD-CLEAN-001`

Execution selection is explicit. HOME and WB01 are independent selectable governed units. Selecting one MUST NOT implicitly execute the other.

## Current source flow

`root Word -> fresh source review -> fresh canonical projection -> fresh Current matrix -> INITIAL_STAGE_WORK_UNIT -> Stage-01 operations`

Stage-02/03/04 MUST NOT be preproduced. Each next Stage is materialized only after the same governed unit's immediately preceding Current Stage has terminal PASS.

## Historical V232 files

Other legacy files remaining under this directory are historical planning/reference artifacts from pre-clean-reset work. They are non-current, receive zero Product completion credit, and MUST NOT be consumed by runtime or current-stage admission.

Current runtime truth is limited to:
- `CURRENT_REMEDIATION_STATE.yaml`
- `successor_reentry_resolution.yaml` (retained filename for compatibility; content now describes Current clean execution)
- `STAGE01_04_DEFECT_LEDGER.yaml`
- `STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_GOVERNANCE_SELECTION.yaml`
