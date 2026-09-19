#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
SCOPE = ROOT / 'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
EVIDENCE = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
ZERO = ROOT / 'governance/ci/validate_stage02_zero_residual.py'


def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception as exc:
        die(f'YAML_PARSE:{path.relative_to(ROOT)}:{exc!r}')


def resolve_current_stage2_product_root(state: dict) -> tuple[Path, Path, Path, dict]:
    work = state.get('active_work_unit') or {}
    if work.get('stage_uid') != 'STAGE-02' or work.get('semantic_capability') != 'PAGE_FUNCTIONAL_CONTRACT':
        die(f'CURRENT_STAGE2_PRODUCT_WORK_UNIT_UNRESOLVED:{work.get("work_unit_uid")!r}')
    owner = str(work.get('canonical_owner') or '')
    marker = '/04_PAGE_FUNCTIONAL_CONTRACT/'
    run_root = owner.split(marker, 1)[0] if marker in owner else ''
    if not run_root:
        scope = load_yaml(SCOPE)
        refs = [str(x) for x in (scope.get('dependency_closure_refs') or [])]
        roots = sorted({x.split(marker, 1)[0] for x in refs if marker in x})
        if len(roots) != 1:
            die(f'CURRENT_STAGE2_RUN_ROOT_AMBIGUOUS:{roots!r}')
        run_root = roots[0]
    product_root = ROOT / run_root / '04_PAGE_FUNCTIONAL_CONTRACT'
    material = work.get('exact_closure_materialization') or {}
    successor_ref = str(material.get('canonical_successor_ref') or '')
    receipt_ref = str(material.get('receipt_ref') or '')
    if not successor_ref or not receipt_ref:
        die('CURRENT_STAGE2_EXACT_CLOSURE_OWNER_OR_RECEIPT_MISSING')
    successor = ROOT / successor_ref
    receipt = ROOT / receipt_ref
    for label, path in (('CANONICAL_SUCCESSOR', successor), ('EXACT_CLOSURE_RECEIPT', receipt)):
        try:
            path.relative_to(ROOT)
        except ValueError:
            die(f'CURRENT_STAGE2_{label}_OUTSIDE_REPOSITORY')
    return product_root, successor, receipt, work

if not STATE.is_file():
    die('ACTIVE_STATE_MISSING')
state = load_yaml(STATE)
PRODUCT_ROOT, CANONICAL_SUCCESSOR, REMEDIATION_RECEIPT, ACTIVE_WORK = resolve_current_stage2_product_root(state)
execution = state.get('execution') or {}
stage1 = execution.get('stage1') or {}
stage2 = execution.get('stage2') or {}
result = stage2.get('result')

if not isinstance(stage1, dict) or not stage1 or any(v != 'PASS' for v in stage1.values()):
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
    raw_functional_total = int(evidence.get('fresh_functional_gap_total') or 0)
    effective = evidence.get('effective_functional_gap_total')
    functional_total = int(effective if effective is not None else raw_functional_total)
    closure_total = int(evidence.get('closure_blocker_total') or 0)
    scope_incomplete = evidence.get('stage_scope_complete') is False and bool(evidence.get('remaining_pages'))
    if functional_total + closure_total <= 0 and not scope_incomplete:
        die('BLOCKED_STATE_WITHOUT_EFFECTIVE_FUNCTIONAL_OR_CLOSURE_GAP_OR_REMAINING_SCOPE')
    if functional_total + closure_total <= 0 and scope_incomplete:
        if any(int((rec or {}).get('effective_functional_gap_count') or 0) for rec in (pages or {}).values()):
            die('PARTIAL_SCOPE_EFFECTIVE_ZERO_DECLARATION_DRIFT')

    if declared_root is True:
        if not physical_exists:
            die('DECLARED_STAGE2_PRODUCT_ROOT_MISSING')
        if not CANONICAL_SUCCESSOR.is_file():
            die('DECLARED_STAGE2_CANONICAL_SUCCESSOR_MISSING')
        if not REMEDIATION_RECEIPT.is_file():
            die('MATERIAL_REMEDIATION_RECEIPT_MISSING')
        receipt = load_yaml(REMEDIATION_RECEIPT)
        materialized = int(receipt.get('materialized_closure_count') or 0)
        expected_materialized = int((ACTIVE_WORK.get('exact_closure_materialization') or {}).get('materialized_closure_count') or 0)
        if materialized <= 0 or materialized != expected_materialized:
            die(f'MATERIAL_REMEDIATION_RECEIPT_DENOMINATOR_DRIFT:{materialized}:{expected_materialized}')
        status = receipt.get('status')
        revalidation_mode = os.environ.get('STAGE02_REVALIDATION_MODE', '').strip() == '1'
        if status == 'MATERIALIZED_PENDING_FRESH_REVALIDATION':
            if not revalidation_mode:
                die('PENDING_MATERIALIZED_ROOT_REQUIRES_REVALIDATION_MODE')
            if int(receipt.get('product_blocker_credit_before_fresh_revalidation') or 0) != 0:
                die('PENDING_MATERIALIZED_ROOT_PREMATURE_PRODUCT_CREDIT')
            print('PASS: Current product root and exact-closure receipt are materialized pending fresh revalidation')
        elif status == 'MATERIALIZED_FRESH_REVALIDATED':
            credit = int(receipt.get('product_blocker_credit_after_fresh_revalidation') or 0)
            if credit != materialized or int(ACTIVE_WORK.get('product_blocker_credit') or 0) != credit:
                die(f'FRESH_REVALIDATED_PRODUCT_CREDIT_DRIFT:{credit}:{ACTIVE_WORK.get("product_blocker_credit")!r}:{materialized}')
            print('PASS: Current product root and exact-closure receipt are fresh-revalidated')
        else:
            die(f'MATERIAL_REMEDIATION_RECEIPT_STATUS_INVALID:{status!r}')
    elif declared_root is False:
        if physical_exists:
            if not CANONICAL_SUCCESSOR.is_file() or not REMEDIATION_RECEIPT.is_file():
                die('UNDECLARED_PRODUCT_ROOT_WITHOUT_CURRENT_SUCCESSOR_AND_RECEIPT')
            receipt = load_yaml(REMEDIATION_RECEIPT)
            if receipt.get('status') != 'MATERIALIZED_PENDING_FRESH_REVALIDATION':
                die('UNDECLARED_PRODUCT_ROOT_NOT_IN_LEGAL_PENDING_REVALIDATION_STATE')
            print('PASS: Stage-02 product root is materially present but remains pending fresh revalidation acceptance')
    else:
        die(f'STAGE2_ARTIFACT_ROOT_DECLARATION_INVALID:{declared_root!r}')
else:
    if evidence.get('result') != 'PASS' or evidence.get('stage_exit_allowed') is not True:
        die('PASS_STATE_EVIDENCE_MISMATCH')
    if execution.get('current_stage') != 'STAGE-02-CLOSED':
        die('PASS_STATE_CURRENT_STAGE_MISMATCH')
    if declared_root is not True or not physical_exists:
        die('PASS_STATE_REQUIRES_VALID_STAGE2_PRODUCT_ARTIFACT_ROOT')
    if not CANONICAL_SUCCESSOR.is_file() or not REMEDIATION_RECEIPT.is_file():
        die('PASS_STATE_CURRENT_PRODUCT_OWNER_OR_RECEIPT_MISSING')
    receipt = load_yaml(REMEDIATION_RECEIPT)
    if receipt.get('status') != 'MATERIALIZED_FRESH_REVALIDATED':
        die(f'PASS_STATE_REQUIRES_FRESH_REVALIDATED_RECEIPT:{receipt.get("status")!r}')

print(f'PASS: Stage-02 successor integrity result={result} product_root_present={physical_exists} declared={declared_root}')
print('PASS: Stage-01 closure continuity retained')
print('PASS: Current Specification mutation/autofill/inference all false')
print('PASS: blocked state may be driven by functional gaps even after missing structural artifacts are materially created')
print('PASS: website construction and deployment remain fail-closed unless Stage-02 is formally closed')
