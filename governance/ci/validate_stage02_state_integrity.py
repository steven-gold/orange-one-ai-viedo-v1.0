#!/usr/bin/env python3
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
EVIDENCE = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
ZERO = ROOT / 'governance/ci/validate_stage02_zero_residual.py'


def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)

if not STATE.is_file():
    die('ACTIVE_STATE_MISSING')
try:
    state = yaml.safe_load(STATE.read_text(encoding='utf-8')) or {}
except Exception as exc:
    die(f'ACTIVE_STATE_PARSE_ERROR:{exc!r}')

execution = state.get('execution') or {}
stage1 = execution.get('stage1') or {}
stage2 = execution.get('stage2') or {}
result = stage2.get('result')

if stage1 != {'CORE-01': 'PASS', 'ASSET-01': 'PASS'}:
    die(f'STAGE1_CLOSURE_CONTINUITY_MISSING:{stage1!r}')
if execution.get('website_construction_allowed') is not False:
    die('WEBSITE_CONSTRUCTION_MUST_REMAIN_BLOCKED')
if execution.get('deployment_allowed') is not False:
    die('DEPLOYMENT_MUST_REMAIN_BLOCKED')

if result == 'NOT_EXECUTED':
    cp = subprocess.run([sys.executable, str(ZERO)], cwd=str(ROOT), text=True)
    if cp.returncode != 0:
        die('STAGE2_PREDECESSOR_ZERO_RESIDUAL_FAILED')
    print('PASS: Stage-02 predecessor state is NOT_EXECUTED and zero-residual')
    raise SystemExit(0)

allowed_executed = {'TEST_EXECUTED_BLOCKED', 'TEST_EXECUTED_PASS'}
if result not in allowed_executed:
    die(f'UNKNOWN_STAGE2_RESULT:{result!r}')

runtime = state.get('stage2_result_evidence') or {}
required_runtime = {
    'mode': 'RUNTIME_GENERATED_GITHUB_ACTION_ARTIFACT',
    'static_result_pointer_required': False,
    'static_run_id_copy_forbidden': True,
    'static_head_sha_copy_forbidden': True,
    'static_specification_digest_copy_forbidden': True,
}
for key, expected in required_runtime.items():
    if runtime.get(key) != expected:
        die(f'STAGE2_RUNTIME_EVIDENCE_CONTRACT:{key}:expected={expected!r}:actual={runtime.get(key)!r}')

if not EVIDENCE.is_file():
    die('STAGE2_LATEST_TEST_EVIDENCE_MISSING')
try:
    evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
except Exception as exc:
    die(f'STAGE2_LATEST_TEST_EVIDENCE_PARSE_ERROR:{exc!r}')

required = {
    'stage_uid': 'STAGE-02',
    'actual_product_stage_test_started': True,
    'actual_product_stage_test_completed': True,
    'current_specification_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
}
for key, expected in required.items():
    if evidence.get(key) != expected:
        die(f'STAGE2_EVIDENCE_FIELD:{key}:expected={expected!r}:actual={evidence.get(key)!r}')

if result == 'TEST_EXECUTED_BLOCKED':
    if evidence.get('result') != 'BLOCKED' or evidence.get('stage_exit_allowed') is not False:
        die('BLOCKED_STATE_EVIDENCE_MISMATCH')
    if execution.get('current_stage') != 'STAGE-02-TESTED-BLOCKED':
        die('BLOCKED_STATE_CURRENT_STAGE_MISMATCH')
    if stage2.get('artifact_root_present') is not False:
        die('BLOCKED_AUDIT_MUST_NOT_CLAIM_STAGE2_PRODUCT_ARTIFACT_ROOT')
    pages = evidence.get('pages') or {}
    if set(pages) != {'CORE-01', 'ASSET-01'}:
        die('STAGE2_PAGE_DENOMINATOR_MISMATCH')
    if not any((p.get('closure_blockers') or []) for p in pages.values()):
        die('BLOCKED_STATE_WITHOUT_BLOCKERS')
else:
    if evidence.get('result') != 'PASS' or evidence.get('stage_exit_allowed') is not True:
        die('PASS_STATE_EVIDENCE_MISMATCH')
    if execution.get('current_stage') != 'STAGE-02-CLOSED':
        die('PASS_STATE_CURRENT_STAGE_MISMATCH')
    if stage2.get('artifact_root_present') is not True:
        die('PASS_STATE_REQUIRES_PRODUCT_ARTIFACT_ROOT')

print(f'PASS: Stage-02 successor state integrity result={result}')
print('PASS: Stage-01 closure continuity retained')
print('PASS: Current Specification mutation/autofill/inference all false')
print('PASS: website construction and deployment remain fail-closed unless Stage-02 is formally closed')
