#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
FINDING = ROOT / 'governance/test/stage02/FIND-20260915-017_CLEAN_RESET_REMEDIATION_CONTINUITY.yaml'
VALIDATORS = [
    ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py',
    ROOT / 'governance/ci/validate_current_stage2_functional_remediation_r3.py',
    ROOT / 'governance/ci/validate_current_stage2_external_authority_resolution_r3.py',
]
REQUIRED = [
    ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/CORE-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml',
    ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/ASSET-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml',
    ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/SHARED_OWNER_PORT_MAP_R3.yaml',
    ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/EXTERNAL_AUTHORITY/GAP-006/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml',
    ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/EXTERNAL_AUTHORITY/STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE.yaml',
]


def die(msg):
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)

for path in REQUIRED:
    if not path.is_file():
        die('VERIFIED_REMEDIATION_MISSING_AFTER_RESET:' + str(path.relative_to(ROOT)))
if not FINDING.is_file():
    die('RESET_CONTINUITY_FINDING_MISSING')
finding = yaml.safe_load(FINDING.read_text(encoding='utf-8')) or {}
if finding.get('finding_uid') != 'FIND-20260915-017' or finding.get('class') != 'TEST_HARNESS_STATE_CONTINUITY_BUG':
    die('RESET_CONTINUITY_FINDING_IDENTITY_DRIFT')
for validator in VALIDATORS:
    cp = subprocess.run([sys.executable, str(validator)], cwd=str(ROOT), text=True)
    if cp.returncode != 0:
        die('REMEDIATION_CONTINUITY_VALIDATOR_FAILED:' + validator.name)
state = yaml.safe_load(STATE.read_text(encoding='utf-8')) or {}
execution = state.get('execution') or {}
if execution.get('current_stage') != 'STAGE-02-TESTED-BLOCKED' or (execution.get('stage2') or {}).get('result') != 'TEST_EXECUTED_BLOCKED':
    die('RESET_CONTINUITY_REQUIRES_CURRENT_STAGE02_BLOCKED_STATE')
if execution.get('website_construction_allowed') is not False or execution.get('deployment_allowed') is not False:
    die('RESET_CONTINUITY_FAIL_CLOSED_STATE_DRIFT')
print('PASS: structural, 17 bounded functional, and exact GAP-006 owning-layer remediation all survive the clean-reset boundary')
print('PASS: FIND-20260915-017 is enforced as a live reset-continuity regression target')
print('PASS: Stage-02 remains blocked and website/deployment remain fail-closed before fresh R3 reexecution')
