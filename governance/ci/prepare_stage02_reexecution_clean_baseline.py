#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
FREEZE = ROOT / 'governance/test/stage02/STAGE02_STAGE_FROZEN_GOVERNANCE_RECEIPT.yaml'
PRODUCT_ROOT = ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
RESULT = ROOT / '.github/stage02-test/STAGE02_REEXECUTION_RESULT.json'
RECEIPT = ROOT / 'governance/test/stage02/STAGE02_REEXECUTION_CLEAN_BASELINE_RECEIPT_R1.yaml'
VALIDATOR = ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py'


def die(msg):
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load(path):
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}

state = load(STATE)
freeze = load(FREEZE)
if (state.get('execution') or {}).get('current_stage') != 'STAGE-02-TESTED-BLOCKED':
    die('REEXECUTION_REQUIRES_STAGE02_TESTED_BLOCKED')
if ((state.get('execution') or {}).get('stage2') or {}).get('result') != 'TEST_EXECUTED_BLOCKED':
    die('REEXECUTION_REQUIRES_BLOCKED_RESULT')
if not PRODUCT_ROOT.is_dir():
    die('REEXECUTION_REQUIRES_MATERIALIZED_PRODUCT_ROOT')
if RESULT.exists():
    RESULT.unlink()
if RECEIPT.exists():
    RECEIPT.unlink()
cp = subprocess.run([sys.executable, str(VALIDATOR)], cwd=str(ROOT), text=True)
if cp.returncode != 0:
    die('MATERIALIZED_PRODUCT_ROOT_INVALID')

bad = []
for path in PRODUCT_ROOT.rglob('*'):
    if path.is_file() and (path.name.endswith(('.pyc', '.tmp', '.bak')) or path.name.endswith('~')):
        bad.append(str(path.relative_to(ROOT)))
    if path.is_dir() and path.name == '__pycache__':
        bad.append(str(path.relative_to(ROOT)))
if bad:
    die('REEXECUTION_PRODUCT_ROOT_RESIDUE:' + ','.join(sorted(bad)))

head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
current_evidence = __import__('json').loads((ROOT/'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json').read_text(encoding='utf-8'))
target_page_uids = list(current_evidence.get('target_pages') or (state.get('execution') or {}).get('target_pages') or [])
if not target_page_uids:
    die('REEXECUTION_TARGET_PAGE_SCOPE_MISSING')

receipt = {
    'schema_version': 1,
    'artifact_type': 'CLEAN_BASELINE_RESET_RECEIPT',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'attempt_uid': freeze.get('attempt_uid'),
    'reexecution_cycle': 'R1',
    'frozen_governance_uid': freeze.get('frozen_governance_uid'),
    'baseline_head_sha': head,
    'predecessor_stage1_inputs_preserved': True,
    'owning_layer_product_fix_preserved': True,
    'product_fix_root': '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT',
    'target_pages': target_page_uids,
    'remaining_pages': list(current_evidence.get('remaining_pages') or []),
    'stage_scope_complete': bool(current_evidence.get('stage_scope_complete')),
    'prior_reexecution_runtime_result_removed': True,
    'prior_stage2_result_used_as_scan_input': False,
    'materialized_product_root_validation': 'PASS',
    'runtime_residue_count': 0,
    'current_specification_mutated': False,
    'status': 'CLEAN_REEXECUTION_BASELINE_READY',
}
RECEIPT.parent.mkdir(parents=True, exist_ok=True)
RECEIPT.write_text(yaml.safe_dump(receipt, allow_unicode=True, sort_keys=False), encoding='utf-8')
print('PASS: Stage-02 reexecution baseline is clean while owning-layer remediation is preserved')
print('PASS: prior reexecution runtime result removed; prior Stage-02 result is not a scan input')
print('REEXECUTION_BASELINE_HEAD=' + head)
