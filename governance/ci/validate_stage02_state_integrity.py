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
FINDINGS = ROOT / 'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
CANDIDATES = ROOT / 'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
ZERO = ROOT / 'governance/ci/validate_stage02_zero_residual.py'


def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path, label: str) -> dict:
    if not path.is_file():
        die(f'{label}_MISSING')
    try:
        obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception as exc:
        die(f'{label}_PARSE_ERROR:{exc!r}')
    if not isinstance(obj, dict):
        die(f'{label}_MAPPING_REQUIRED')
    return obj

state = load_yaml(STATE, 'ACTIVE_STATE')
execution = state.get('execution') or {}; stage1 = execution.get('stage1') or {}; stage2 = execution.get('stage2') or {}; result = stage2.get('result')
if stage1 != {'CORE-01': 'PASS', 'ASSET-01': 'PASS'}: die(f'STAGE1_CLOSURE_CONTINUITY_MISSING:{stage1!r}')
if execution.get('website_construction_allowed') is not False: die('WEBSITE_CONSTRUCTION_MUST_REMAIN_BLOCKED')
if execution.get('deployment_allowed') is not False: die('DEPLOYMENT_MUST_REMAIN_BLOCKED')
if result == 'NOT_EXECUTED':
    cp = subprocess.run([sys.executable, str(ZERO)], cwd=str(ROOT), text=True)
    if cp.returncode != 0: die('STAGE2_PREDECESSOR_ZERO_RESIDUAL_FAILED')
    print('PASS: Stage-02 predecessor state is NOT_EXECUTED and zero-residual'); raise SystemExit(0)
if result not in {'TEST_EXECUTED_BLOCKED', 'TEST_EXECUTED_PASS'}: die(f'UNKNOWN_STAGE2_RESULT:{result!r}')
runtime = state.get('stage2_result_evidence') or {}
required_runtime = {'mode':'RUNTIME_GENERATED_GITHUB_ACTION_ARTIFACT','static_result_pointer_required':False,'static_run_id_copy_forbidden':True,'static_head_sha_copy_forbidden':True,'static_specification_digest_copy_forbidden':True}
for key, expected in required_runtime.items():
    if runtime.get(key) != expected: die(f'STAGE2_RUNTIME_EVIDENCE_CONTRACT:{key}:expected={expected!r}:actual={runtime.get(key)!r}')
if not EVIDENCE.is_file(): die('STAGE2_LATEST_TEST_EVIDENCE_MISSING')
try: evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
except Exception as exc: die(f'STAGE2_LATEST_TEST_EVIDENCE_PARSE_ERROR:{exc!r}')
required = {'stage_uid':'STAGE-02','actual_product_stage_test_started':True,'actual_product_stage_test_completed':True,'current_specification_mutated':False,'ai_autofill_used':False,'inference_used':False,'website_construction_allowed':False,'deployment_allowed':False}
for key, expected in required.items():
    if evidence.get(key) != expected: die(f'STAGE2_EVIDENCE_FIELD:{key}:expected={expected!r}:actual={evidence.get(key)!r}')

active = state.get('stage02_active_attempt') or {}
findings = load_yaml(FINDINGS, 'STAGE02_CURRENT_FINDINGS')
candidate_ledger = load_yaml(CANDIDATES, 'SPECIFICATION_CHANGE_CANDIDATES')
candidate = candidate_ledger.get('current_stage2_execution') or {}
if not active: die('EXECUTED_STAGE2_REQUIRES_ACTIVE_ATTEMPT')
if not candidate: die('EXECUTED_STAGE2_REQUIRES_CURRENT_CANDIDATE_PROJECTION')

identity_checks = {
    'attempt_uid': (active.get('attempt_uid'), findings.get('attempt_uid'), candidate.get('attempt_uid')),
    'frozen_governance_uid': (active.get('frozen_governance_uid'), findings.get('frozen_governance_uid'), candidate.get('frozen_governance_uid')),
    'source_execution_sha': (active.get('source_execution_sha'), findings.get('source_head_sha'), candidate.get('source_execution_sha')),
    'source_workflow_run_id': (active.get('source_workflow_run_id'), findings.get('source_workflow_run_id'), candidate.get('source_workflow_run_id')),
    'source_artifact_id': (active.get('source_artifact_id'), findings.get('source_artifact_id'), candidate.get('source_artifact_id')),
    'source_artifact_sha256': (active.get('source_artifact_sha256'), findings.get('source_artifact_sha256'), candidate.get('source_artifact_sha256')),
}
for key, values in identity_checks.items():
    if any(v in (None, '') for v in values) or len(set(values)) != 1:
        die(f'STAGE2_CURRENT_PROJECTOR_IDENTITY_DRIFT:{key}:{values!r}')
if active.get('frozen_governance_uid') != state.get('specification_uid'):
    die('STAGE2_ACTIVE_ATTEMPT_GOVERNANCE_UID_DRIFT')
if evidence.get('source_head_sha') != active.get('source_execution_sha'):
    die('STAGE2_EVIDENCE_SOURCE_SHA_DRIFT')

fresh_gap_total = int(evidence.get('fresh_functional_gap_total') or 0)
closure_total = int(evidence.get('closure_blocker_total') or 0)
count_checks = {
    'fresh_functional_gap_total': (int(active.get('fresh_functional_gap_total') or 0), int(findings.get('fresh_functional_gap_total') or 0), int(candidate.get('raw_discovery_gap_count') or 0), fresh_gap_total),
    'fresh_closure_blocker_total': (int(active.get('fresh_closure_blocker_total') or 0), int(findings.get('fresh_closure_blocker_total') or 0), int(candidate.get('current_closure_blocker_count') or 0), closure_total),
    'preserved_external_authority_union_count': (int(active.get('preserved_external_authority_union_count') or 0), int(findings.get('preserved_external_authority_union_count') or 0), int(candidate.get('preserved_external_authority_union_count') or 0), int(evidence.get('preserved_external_authority_union_count') or 0)),
    'official_stage_output_denominator_count': (int(active.get('official_stage_output_denominator_count') or 0), int(findings.get('official_stage_output_denominator_count') or 0), int(candidate.get('official_stage_output_denominator_count') or 0), len(evidence.get('official_stage_output_denominator') or [])),
    'current_manifest_mandatory_stage_output_subset_count': (int(active.get('current_manifest_mandatory_stage_output_subset_count') or 0), int(findings.get('current_manifest_mandatory_stage_output_subset_count') or 0), int(candidate.get('current_manifest_mandatory_stage_output_subset_count') or 0), len(evidence.get('execution_profile_mandatory_output_subset') or [])),
}
for key, values in count_checks.items():
    if len(set(values)) != 1:
        die(f'STAGE2_CURRENT_PROJECTOR_COUNT_DRIFT:{key}:{values!r}')

next_actions = (state.get('next_action'), active.get('next_action'), findings.get('next_action'), candidate.get('next_action'))
if any(v in (None, '') for v in next_actions) or len(set(next_actions)) != 1:
    die(f'STAGE2_CURRENT_PROJECTOR_NEXT_ACTION_DRIFT:{next_actions!r}')
for key in ('stage_exit_allowed', 'website_construction_allowed', 'deployment_allowed'):
    expected = False if result == 'TEST_EXECUTED_BLOCKED' else True if key == 'stage_exit_allowed' else False
    if candidate.get(key) is not expected:
        die(f'STAGE2_CANDIDATE_GATE_DRIFT:{key}:expected={expected!r}:actual={candidate.get(key)!r}')

if result == 'TEST_EXECUTED_BLOCKED':
    if candidate.get('state') != 'TEST_EXECUTED_BLOCKED': die('BLOCKED_CANDIDATE_STATE_MISMATCH')
    if findings.get('result') != 'BLOCKED': die('BLOCKED_FINDINGS_RESULT_MISMATCH')
    if evidence.get('result') != 'BLOCKED' or evidence.get('stage_exit_allowed') is not False: die('BLOCKED_STATE_EVIDENCE_MISMATCH')
    if execution.get('current_stage') != 'STAGE-02-TESTED-BLOCKED': die('BLOCKED_STATE_CURRENT_STAGE_MISMATCH')
    pages = evidence.get('pages') or {}
    if set(pages) != {'CORE-01', 'ASSET-01'}: die('STAGE2_PAGE_DENOMINATOR_MISMATCH')
    root_present = stage2.get('artifact_root_present')
    if root_present not in {True, False}: die('BLOCKED_STAGE2_ARTIFACT_ROOT_FLAG_INVALID')
    material = state.get('stage02_material_remediation') or {}
    if root_present is True:
        if material.get('material_remediation_started') is not True: die('BLOCKED_PRODUCT_ROOT_REQUIRES_MATERIAL_REMEDIATION_STATE')
        if evidence.get('physical_stage2_product_artifact_root_present') is not True: die('BLOCKED_PRODUCT_ROOT_EVIDENCE_MISMATCH')
    effective = evidence.get('effective_functional_gap_total')
    blocking_functional = int(effective if effective is not None else fresh_gap_total)
    if blocking_functional <= 0 and closure_total <= 0: die('BLOCKED_STATE_WITHOUT_EFFECTIVE_OR_STRUCTURAL_BLOCKERS')
else:
    if candidate.get('state') != 'TEST_EXECUTED_PASS': die('PASS_CANDIDATE_STATE_MISMATCH')
    if evidence.get('result') != 'PASS' or evidence.get('stage_exit_allowed') is not True: die('PASS_STATE_EVIDENCE_MISMATCH')
    if execution.get('current_stage') != 'STAGE-02-CLOSED': die('PASS_STATE_CURRENT_STAGE_MISMATCH')
    if stage2.get('artifact_root_present') is not True: die('PASS_STATE_REQUIRES_PRODUCT_ARTIFACT_ROOT')
print(f'PASS: Stage-02 successor state integrity result={result}')
print('PASS: Stage-01 closure continuity retained')
print('PASS: ACTIVE_STATE, findings, evidence, and candidate Current projectors are identity/count/action synchronized')
print('PASS: blocked remediation root is allowed only with explicit material-remediation state')
print('PASS: Current Specification mutation/autofill/inference all false')
print('PASS: website construction and deployment remain fail-closed unless Stage-02 is formally closed')
