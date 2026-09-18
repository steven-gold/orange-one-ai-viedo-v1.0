#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
EVIDENCE = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
ZERO = ROOT / 'governance/ci/validate_stage02_zero_residual.py'
PRODUCT_ROOT = RUN / '04_PAGE_FUNCTIONAL_CONTRACT'
REMEDIATION_RECEIPT = ROOT / 'governance/test/stage02/STAGE02_MATERIAL_REMEDIATION_RECEIPT_R1.yaml'
MATERIAL_VALIDATOR = ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py'


def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception as exc:
        die(f'YAML_PARSE:{path.relative_to(ROOT)}:{exc!r}')

if not STATE.is_file():
    die('ACTIVE_STATE_MISSING')
state = load_yaml(STATE)
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
    if PRODUCT_ROOT.exists():
        die('PRE_EXECUTION_STATE_MUST_NOT_HAVE_STAGE2_PRODUCT_ROOT')
    print('PASS: Stage-02 predecessor state is NOT_EXECUTED and zero-residual')
    raise SystemExit(0)

if result not in {'TEST_EXECUTED_BLOCKED', 'TEST_EXECUTED_PASS'}:
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

physical_exists = PRODUCT_ROOT.is_dir()
declared_root = stage2.get('artifact_root_present')

if result == 'TEST_EXECUTED_BLOCKED':
    if evidence.get('result') != 'BLOCKED' or evidence.get('stage_exit_allowed') is not False:
        die('BLOCKED_STATE_EVIDENCE_MISMATCH')
    if execution.get('current_stage') != 'STAGE-02-TESTED-BLOCKED':
        die('BLOCKED_STATE_CURRENT_STAGE_MISMATCH')
    pages = evidence.get('pages') or {}
    target_pages = evidence.get('target_pages') or []
    if not isinstance(target_pages, list) or not target_pages:
        die('STAGE2_TARGET_PAGE_SCOPE_MISSING')
    if set(pages) != set(target_pages):
        die('STAGE2_PAGE_DENOMINATOR_MISMATCH')
    if not set(target_pages).issubset(set(stage1)):
        die('STAGE2_TARGET_PAGE_SCOPE_OUTSIDE_STAGE1')
    if evidence.get('stage_scope_complete') is not (set(target_pages) == set(stage1)):
        die('STAGE2_SCOPE_COMPLETENESS_DRIFT')
    functional_total = int(evidence.get('fresh_functional_gap_total') or 0)
    closure_total = int(evidence.get('closure_blocker_total') or 0)
    if functional_total + closure_total <= 0:
        die('BLOCKED_STATE_WITHOUT_CURRENT_FUNCTIONAL_OR_CLOSURE_GAP')

    if declared_root is True:
        if not physical_exists:
            die('DECLARED_STAGE2_PRODUCT_ROOT_MISSING')
        if not REMEDIATION_RECEIPT.is_file():
            die('MATERIAL_REMEDIATION_RECEIPT_MISSING')
        cp = subprocess.run([sys.executable, str(MATERIAL_VALIDATOR)], cwd=str(ROOT), text=True)
        if cp.returncode != 0:
            die('MATERIALIZED_STAGE2_PRODUCT_ROOT_VALIDATION_FAILED')
    elif declared_root is False:
        if physical_exists:
            if not REMEDIATION_RECEIPT.is_file():
                die('UNDECLARED_PRODUCT_ROOT_WITHOUT_PENDING_REMEDIATION_RECEIPT')
            receipt = load_yaml(REMEDIATION_RECEIPT)
            if receipt.get('status') != 'MATERIALIZED_PENDING_FRESH_REEXECUTION_PROOF':
                die('UNDECLARED_PRODUCT_ROOT_NOT_IN_LEGAL_PENDING_REEXECUTION_STATE')
            cp = subprocess.run([sys.executable, str(MATERIAL_VALIDATOR)], cwd=str(ROOT), text=True)
            if cp.returncode != 0:
                die('PENDING_REMEDIATION_PRODUCT_ROOT_INVALID')
            print('PASS: Stage-02 product root is materially present but remains pending fresh reexecution acceptance')
    else:
        die(f'STAGE2_ARTIFACT_ROOT_DECLARATION_INVALID:{declared_root!r}')
else:
    if evidence.get('result') != 'PASS' or evidence.get('stage_exit_allowed') is not True:
        die('PASS_STATE_EVIDENCE_MISMATCH')
    if execution.get('current_stage') != 'STAGE-02-CLOSED':
        die('PASS_STATE_CURRENT_STAGE_MISMATCH')
    if declared_root is not True or not physical_exists:
        die('PASS_STATE_REQUIRES_VALID_STAGE2_PRODUCT_ARTIFACT_ROOT')
    cp = subprocess.run([sys.executable, str(MATERIAL_VALIDATOR)], cwd=str(ROOT), text=True)
    if cp.returncode != 0:
        die('PASS_STATE_PRODUCT_ROOT_VALIDATION_FAILED')

print(f'PASS: Stage-02 successor integrity result={result} product_root_present={physical_exists} declared={declared_root}')
print('PASS: Stage-01 closure continuity retained')
print('PASS: Current Specification mutation/autofill/inference all false')
print('PASS: blocked state may be driven by functional gaps even after missing structural artifacts are materially created')
print('PASS: website construction and deployment remain fail-closed unless Stage-02 is formally closed')
