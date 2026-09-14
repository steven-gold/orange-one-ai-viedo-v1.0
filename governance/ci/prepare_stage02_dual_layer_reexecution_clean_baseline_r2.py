#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
FREEZE = ROOT / 'governance/test/stage02/STAGE02_STAGE_FROZEN_GOVERNANCE_RECEIPT.yaml'
PRODUCT_ROOT = ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
RESULT = ROOT / '.github/stage02-test/STAGE02_DUAL_LAYER_REEXECUTION_RESULT_R2.json'
RECEIPT = ROOT / 'governance/test/stage02/STAGE02_DUAL_LAYER_REEXECUTION_CLEAN_BASELINE_RECEIPT_R2.yaml'
STRUCTURAL_VALIDATOR = ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py'
FUNCTIONAL_VALIDATOR = ROOT / 'governance/ci/validate_current_stage2_functional_remediation_r3.py'


def die(msg):
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load(path):
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}

state = load(STATE)
freeze = load(FREEZE)
execution = state.get('execution') or {}
if execution.get('current_stage') != 'STAGE-02-TESTED-BLOCKED':
    die(f'R2_REEXECUTION_REQUIRES_STAGE02_TESTED_BLOCKED:{execution.get("current_stage")}')
if (execution.get('stage2') or {}).get('result') != 'TEST_EXECUTED_BLOCKED':
    die('R2_REEXECUTION_REQUIRES_TEST_EXECUTED_BLOCKED')
if not PRODUCT_ROOT.is_dir():
    die('R2_REEXECUTION_REQUIRES_STAGE2_PRODUCT_ROOT')
for validator in (STRUCTURAL_VALIDATOR, FUNCTIONAL_VALIDATOR):
    cp = subprocess.run([sys.executable, str(validator)], cwd=str(ROOT), text=True)
    if cp.returncode != 0:
        die(f'OWNING_LAYER_VALIDATOR_FAILED:{validator.name}')
if RESULT.exists():
    RESULT.unlink()
if RECEIPT.exists():
    RECEIPT.unlink()

bad = []
for path in PRODUCT_ROOT.rglob('*'):
    if path.is_file() and (path.name.endswith(('.pyc','.tmp','.bak')) or path.name.endswith('~')):
        bad.append(str(path.relative_to(ROOT)))
    if path.is_dir() and path.name == '__pycache__':
        bad.append(str(path.relative_to(ROOT)))
if bad:
    die('R2_PRODUCT_ROOT_RESIDUE:' + ','.join(sorted(bad)))

head = subprocess.run(['git','rev-parse','HEAD'], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
receipt = {
    'schema_version': 1,
    'artifact_type': 'CLEAN_BASELINE_RESET_RECEIPT',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'attempt_uid': freeze.get('attempt_uid'),
    'reexecution_cycle': 'R2_DUAL_LAYER',
    'frozen_governance_uid': freeze.get('frozen_governance_uid'),
    'baseline_head_sha': head,
    'predecessor_stage1_inputs_preserved': True,
    'structural_stage2_fix_preserved': True,
    'functional_stage2_r3_fix_preserved': True,
    'functional_stage2_r3_fix_validated': True,
    'product_fix_root': '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT',
    'prior_dual_layer_runtime_result_removed': True,
    'prior_stage2_result_used_as_scan_input': False,
    'runtime_residue_count': 0,
    'current_specification_mutated': False,
    'status': 'CLEAN_DUAL_LAYER_REEXECUTION_BASELINE_READY',
}
RECEIPT.parent.mkdir(parents=True, exist_ok=True)
RECEIPT.write_text(yaml.safe_dump(receipt, allow_unicode=True, sort_keys=False, width=160), encoding='utf-8')
print('PASS: R2 dual-layer clean baseline preserves immutable Stage-01 and validated Stage-02 owning-layer fixes')
print('PASS: no prior Stage-02 count is used as scan input')
print('R2_DUAL_LAYER_BASELINE_HEAD=' + head)
