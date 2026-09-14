#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
FREEZE = ROOT / 'governance/test/stage02/STAGE02_STAGE_FROZEN_GOVERNANCE_RECEIPT.yaml'
PRODUCT_ROOT = ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
RESULT = ROOT / '.github/stage02-test/STAGE02_EXTERNAL_AUTHORITY_REEXECUTION_RESULT_R3.json'
RECEIPT = ROOT / 'governance/test/stage02/STAGE02_EXTERNAL_AUTHORITY_REEXECUTION_CLEAN_BASELINE_RECEIPT_R3.yaml'
REGRESSION = ROOT / 'governance/test/stage02/STAGE02_DEFECT_SIGNATURE_REGRESSION_R3.yaml'
VALIDATORS = [
    ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py',
    ROOT / 'governance/ci/validate_current_stage2_functional_remediation_r3.py',
    ROOT / 'governance/ci/validate_current_stage2_external_authority_resolution_r3.py',
    ROOT / 'governance/ci/validate_stage02_remediation_reset_continuity_r3.py',
]


def die(msg):
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load(path):
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(obj, dict):
        die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj

state = load(STATE)
freeze = load(FREEZE)
execution = state.get('execution') or {}
if execution.get('current_stage') != 'STAGE-02-TESTED-BLOCKED':
    die(f'R3_REEXECUTION_REQUIRES_STAGE02_TESTED_BLOCKED:{execution.get("current_stage")}')
if (execution.get('stage2') or {}).get('result') != 'TEST_EXECUTED_BLOCKED':
    die('R3_REEXECUTION_REQUIRES_TEST_EXECUTED_BLOCKED')
if not PRODUCT_ROOT.is_dir():
    die('R3_REEXECUTION_REQUIRES_STAGE2_PRODUCT_ROOT')
for validator in VALIDATORS:
    cp = subprocess.run([sys.executable, str(validator)], cwd=str(ROOT), text=True)
    if cp.returncode != 0:
        die(f'R3_PRE_RESET_VALIDATOR_FAILED:{validator.name}')

# Clean only R3 execution output/receipt. Never delete owning-layer remediation.
for path in (RESULT, RECEIPT, REGRESSION):
    if path.exists():
        path.unlink()

bad = []
for path in PRODUCT_ROOT.rglob('*'):
    if path.is_file() and (path.name.endswith(('.pyc','.tmp','.bak')) or path.name.endswith('~')):
        bad.append(str(path.relative_to(ROOT)))
    if path.is_dir() and path.name == '__pycache__':
        bad.append(str(path.relative_to(ROOT)))
if bad:
    die('R3_PRODUCT_ROOT_RESIDUE:' + ','.join(sorted(bad)))

# Re-prove remediation survived the reset operation itself.
cp = subprocess.run([sys.executable, str(ROOT / 'governance/ci/validate_stage02_remediation_reset_continuity_r3.py')], cwd=str(ROOT), text=True)
if cp.returncode != 0:
    die('R3_POST_RESET_REMEDIATION_CONTINUITY_FAILED')

head = subprocess.run(['git','rev-parse','HEAD'], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
receipt = {
    'schema_version': 1,
    'artifact_type': 'CLEAN_BASELINE_RESET_RECEIPT',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'attempt_uid': freeze.get('attempt_uid'),
    'reexecution_cycle': 'R3_EXTERNAL_AUTHORITY_AWARE',
    'frozen_governance_uid': freeze.get('frozen_governance_uid'),
    'baseline_head_sha': head,
    'predecessor_stage1_inputs_preserved': True,
    'structural_stage2_fix_preserved': True,
    'bounded_functional_stage2_fix_preserved': True,
    'gap006_exact_authority_fix_preserved': True,
    'gap006_exact_authority_fix_validated': True,
    'finding_017_reset_continuity_regression_enforced': True,
    'product_fix_root': '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT',
    'prior_r3_runtime_result_removed': True,
    'prior_stage2_result_used_as_scan_input': False,
    'runtime_residue_count': 0,
    'current_specification_mutated': False,
    'status': 'CLEAN_EXTERNAL_AUTHORITY_AWARE_REEXECUTION_BASELINE_READY',
}
RECEIPT.parent.mkdir(parents=True, exist_ok=True)
RECEIPT.write_text(yaml.safe_dump(receipt, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')
print('PASS: R3 clean baseline removed execution-only R3 residue and preserved all verified owning-layer remediation')
print('PASS: no prior Stage-02 count is used as scan input')
print('R3_EXTERNAL_AUTHORITY_BASELINE_HEAD=' + head)
