#!/usr/bin/env python3
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
PRODUCT_ROOT = RUN / '04_PAGE_FUNCTIONAL_CONTRACT'
SCANNER_SOURCE = ROOT / 'governance/ci/run_current_stage2_actual_test.py'
MATERIAL_VALIDATOR = ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
FREEZE = ROOT / 'governance/test/stage02/STAGE02_STAGE_FROZEN_GOVERNANCE_RECEIPT.yaml'
CLEAN = ROOT / 'governance/test/stage02/STAGE02_REEXECUTION_CLEAN_BASELINE_RECEIPT_R1.yaml'
MATERIAL_RECEIPT = ROOT / 'governance/test/stage02/STAGE02_MATERIAL_REMEDIATION_RECEIPT_R1.yaml'
LATEST = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
FINDINGS = ROOT / 'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
REGRESSION = ROOT / 'governance/test/stage02/STAGE02_DEFECT_SIGNATURE_REGRESSION_R1.yaml'
LEDGER = ROOT / 'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
RESULT = ROOT / '.github/stage02-test/STAGE02_REEXECUTION_RESULT.json'
PAGES = {
    'CORE-01': {
        'raw': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
        'blueprint': RUN / '02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml',
        'ai_profile': True,
    },
    'ASSET-01': {
        'raw': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
        'blueprint': RUN / '02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml',
        'ai_profile': False,
    },
}
EXPECTED_GAPS = {f'GAP-{i:03}' for i in range(1, 9)}


def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    try:
        obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception as exc:
        die(f'YAML_PARSE:{path.relative_to(ROOT)}:{exc!r}')
    if not isinstance(obj, dict):
        die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj


def dump_yaml(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=140), encoding='utf-8')


def git_head() -> str:
    return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()


def exact_external_refs(blueprint: dict):
    refs = []
    for ref in blueprint.get('unresolved_external_authority_refs') or []:
        if not isinstance(ref, dict):
            continue
        refs.append({
            'gap_uid': ref.get('gap_uid'),
            'authority_ref': ref.get('authority_ref'),
            'resolved': False,
            'satisfied': False,
            'auto_filled': False,
            'inferred': False,
        })
    return refs


def load_exact_fresh_scan_implementation():
    source = SCANNER_SOURCE.read_text(encoding='utf-8')
    tree = ast.parse(source, filename=str(SCANNER_SOURCE))
    keep_functions = {'idx', 'present', 'event_token', 'has_transition', 'add', 'fresh_scan'}
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if 'KNOWN_AUTHORITIES' in names:
                selected.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in keep_functions:
            selected.append(node)
    found = {node.name for node in selected if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if found != keep_functions:
        die(f'FRESH_SCAN_IMPLEMENTATION_EXTRACTION_DRIFT:expected={sorted(keep_functions)} actual={sorted(found)}')
    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)
    ns = {'Counter': Counter, 'defaultdict': defaultdict, 're': re}
    exec(compile(module, str(SCANNER_SOURCE), 'exec'), ns, ns)
    if not callable(ns.get('fresh_scan')):
        die('FRESH_SCAN_IMPLEMENTATION_NOT_CALLABLE')
    return ns['fresh_scan']


if os.environ.get('STAGE02_FULL_LINE_CONFIRMED') != '1':
    die('REEXECUTION_REQUIRES_SAME_WORKFLOW_FULL_LINE_CONFIRMATION')
state = load_yaml(STATE)
active_work = state.get('active_work_unit') or {}
resume = state.get('resume_control') or {}
if active_work:
    if resume.get('current_work_unit_uid') != active_work.get('work_unit_uid'):
        die('REEXECUTION_ACTIVE_WORK_UNIT_RESUME_DRIFT')
    if resume.get('current_owner') != active_work.get('canonical_owner'):
        die('REEXECUTION_ACTIVE_WORK_UNIT_OWNER_DRIFT')
    if active_work.get('current_status') == 'IN_PROGRESS_COMMON_ENGINE_INTERRUPT':
        die('REEXECUTION_FORBIDDEN_DURING_COMMON_ENGINE_INTERRUPT')
freeze = load_yaml(FREEZE)
clean = load_yaml(CLEAN)
material_receipt = load_yaml(MATERIAL_RECEIPT)
execution = state.get('execution') or {}
if execution.get('current_stage') != 'STAGE-02-TESTED-BLOCKED':
    die('REEXECUTION_REQUIRES_STAGE02_TESTED_BLOCKED')
if (execution.get('stage2') or {}).get('result') != 'TEST_EXECUTED_BLOCKED':
    die('REEXECUTION_REQUIRES_TEST_EXECUTED_BLOCKED')
if clean.get('status') != 'CLEAN_REEXECUTION_BASELINE_READY':
    die('REEXECUTION_CLEAN_BASELINE_RECEIPT_INVALID')
if clean.get('frozen_governance_uid') != freeze.get('frozen_governance_uid'):
    die('REEXECUTION_FROZEN_GOVERNANCE_UID_DRIFT')
if not PRODUCT_ROOT.is_dir():
    die('MATERIALIZED_STAGE02_PRODUCT_ROOT_MISSING')
cp = subprocess.run([sys.executable, str(MATERIAL_VALIDATOR)], cwd=str(ROOT), text=True)
if cp.returncode != 0:
    die('MATERIALIZED_STAGE02_PRODUCT_ROOT_INVALID')

fresh_scan = load_exact_fresh_scan_implementation()
head = git_head()
pages = {}
external = {}
union_gap_uids = set()
for page_uid, cfg in PAGES.items():
    raw = load_yaml(cfg['raw'])
    blueprint = load_yaml(cfg['blueprint'])
    refs = exact_external_refs(blueprint)
    for ref in refs:
        gid = ref.get('gap_uid')
        union_gap_uids.add(gid)
        external.setdefault(gid, {'authority_ref': ref.get('authority_ref'), 'consumers': []})['consumers'].append(page_uid)
    scan = fresh_scan(page_uid, raw)
    pages[page_uid] = {
        'blueprint_uid': blueprint.get('blueprint_uid'),
        'ai_interaction_profile_active': cfg['ai_profile'],
        'unresolved_external_authority_ref_count': len(refs),
        'functional_chain_fresh_scan': scan,
        'closure_blockers': [],
        'closure_blocker_count': 0,
        'materialized_structural_contract_validation': 'PASS',
        'function_admission_scorecard': 'NOT_APPLICABLE_NO_AUTO_OR_AI_PROPOSED_FUNCTION_CREATED_BY_THIS_REEXECUTION',
        'automatic_completion_scope': 'NOT_APPLICABLE_NO_AUTOMATIC_COMPLETION_ATTEMPT',
    }

if union_gap_uids != EXPECTED_GAPS:
    die(f'EXTERNAL_AUTHORITY_UNION_DRIFT:expected={sorted(EXPECTED_GAPS)} actual={sorted(union_gap_uids)}')
functional_total = sum(x['functional_chain_fresh_scan']['gap_count'] for x in pages.values())
closure_total = 0
result_status = 'BLOCKED' if functional_total else 'PASS'
stage_exit = result_status == 'PASS'
result = {
    'schema_version': 2,
    'artifact_type': 'NON_NORMATIVE_STAGE02_ACTUAL_TEST_EVIDENCE',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'stage_name': 'PAGE_FUNCTIONAL_CONTRACT',
    'reexecution_cycle': 'R1',
    'source_head_sha': head,
    'frozen_governance_uid': freeze.get('frozen_governance_uid'),
    'test_mode': 'FRESH_REEXECUTION_FROM_IMMUTABLE_STAGE1_INPUTS_WITH_VALIDATED_STAGE2_OWNING_LAYER_REMEDIATION',
    'fresh_scan_implementation': 'EXACT_AST_EXTRACT_OF_run_current_stage2_actual_test.py::fresh_scan',
    'actual_product_stage_test_started': True,
    'actual_product_stage_test_completed': True,
    'stage_entry_gate': 'PASS',
    'stage_exit_allowed': stage_exit,
    'result': result_status,
    'physical_stage2_product_artifact_root_present': True,
    'materialized_structural_contract_validation': 'PASS',
    'materialized_missing_artifact_blocker_count': material_receipt.get('materialized_missing_artifact_blocker_count'),
    'pages': pages,
    'fresh_functional_gap_total': functional_total,
    'closure_blocker_total': closure_total,
    'preserved_external_authorities': dict(sorted(external.items())),
    'preserved_external_authority_union_count': len(union_gap_uids),
    'preserved_external_authority_union_gap_uids': sorted(union_gap_uids),
    'current_specification_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'prior_stage2_results_used': False,
    'prior_stage2_counts_used_as_scan_input': False,
    'website_construction_allowed': stage_exit,
    'deployment_allowed': False,
    'notes': [
        'Fresh functional scan is executed again from immutable Stage-01 raw authority using the exact scanner implementation extracted from the first-run harness.',
        'The prior 171/13 result is not used as scan input; it is regression context only.',
        'The 13 missing structural artifact blockers are counted as eliminated only because the current Stage-02 product root passed its source-bounded validator before this reexecution.',
        'GAP-001..GAP-008 remain unresolved; no external authority was inferred or auto-filled.',
    ],
}
RESULT.parent.mkdir(parents=True, exist_ok=True)
RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
LATEST.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

page_findings = {}
for page_uid, rec in pages.items():
    scan = rec['functional_chain_fresh_scan']
    page_findings[page_uid] = {
        'fresh_functional_gap_total': scan['gap_count'],
        'categories': scan['gap_categories'],
        'closure_blocker_count': 0,
        'closure_blockers': [],
    }
findings = {
    'schema_version': 2,
    'artifact_uid': 'STAGE02-FRESH-REEXECUTION-FINDINGS-20260915-R1',
    'artifact_type': 'NON_NORMATIVE_STAGE_TEST_FINDING_LEDGER',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'stage_name': 'PAGE_FUNCTIONAL_CONTRACT',
    'source_execution_sha': head,
    'reexecution_cycle': 'R1',
    'prior_stage2_results_used': False,
    'current_specification_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'result': result_status,
    'stage_entry_gate': 'PASS',
    'stage_exit_allowed': stage_exit,
    'fresh_functional_gap_total': functional_total,
    'closure_blocker_total': closure_total,
    'pages': page_findings,
    'preserved_external_authority': {
        'exact_union_count': len(union_gap_uids),
        'gap_uids': sorted(union_gap_uids),
        'rule': 'PRESERVE_UNRESOLVED_NO_INFERENCE_NO_AUTOFILL',
    },
    'material_remediation': {
        'receipt_ref': 'governance/test/stage02/STAGE02_MATERIAL_REMEDIATION_RECEIPT_R1.yaml',
        'missing_structural_artifact_blockers_before': 13,
        'missing_structural_artifact_blockers_after_fresh_reexecution': 0,
        'material_elimination_count': 13,
        'functional_gap_elimination_count': 0,
    },
    'specification_change_required': False,
    'formal_specification_may_be_modified_from_this_finding': False,
    'status': 'OPEN_STAGE02_FUNCTIONAL_GAP_REMEDIATION' if result_status == 'BLOCKED' else 'STAGE02_REEXECUTION_PASS_PENDING_HIDDEN_SWEEP',
}
dump_yaml(FINDINGS, findings)

dump_yaml(REGRESSION, {
    'schema_version': 1,
    'artifact_type': 'DEFECT_SIGNATURE_REGRESSION_RECEIPT',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'reexecution_cycle': 'R1',
    'frozen_governance_uid': freeze.get('frozen_governance_uid'),
    'fresh_reexecution_sha': head,
    'missing_structural_artifact_signature': {
        'previous_reproduction_count': 13,
        'fresh_reproduction_count': 0,
        'material_elimination_count': 13,
        'status': 'ZERO_REPRODUCTION_PASS',
    },
    'functional_gap_signature': {
        'fresh_reproduction_count': functional_total,
        'elimination_claimed': 0,
        'status': 'REMAINS_BLOCKING' if functional_total else 'ZERO_REPRODUCTION_PASS',
    },
    'external_authority_union_count': len(union_gap_uids),
    'external_authority_resolution_claimed': False,
    'stage_closure_claimed': False,
})

# Record the discovered non-normative ledger staleness before synchronizing its Current projection.
ledger = load_yaml(LEDGER)
ledger_findings = ledger.setdefault('findings', [])
finding_uid = 'FIND-20260915-014'
if not any(isinstance(x, dict) and x.get('finding_uid') == finding_uid for x in ledger_findings):
    ledger_findings.append({
        'finding_uid': finding_uid,
        'class': 'EVIDENCE_OR_STATE_BUG',
        'title': 'Specification candidate ledger Current Stage-02 projection remained NOT_EXECUTED after fresh Stage-02 execution',
        'evidence': 'STAGE02_LATEST_TEST_EVIDENCE and ACTIVE_STATE had already established TEST_EXECUTED_BLOCKED while SPECIFICATION_CHANGE_CANDIDATES.current_stage2_execution still said NOT_EXECUTED.',
        'disposition': 'RESOLVED_NON_NORMATIVE_STATE_SYNC_DURING_R1_REEXECUTION',
        'specification_change_required': False,
        'formal_specification_mutated_for_fix': False,
        'current_specification_may_be_modified_from_this_finding_alone': False,
        'resolution': 'Record the evidence/state bug, then synchronize only the non-normative Current Stage-02 projection to the fresh reexecution result.',
    })
ledger['current_stage2_execution'] = {
    'state': 'REEXECUTED_BLOCKED' if result_status == 'BLOCKED' else 'REEXECUTED_PASS',
    'current_functional_gap_count': functional_total,
    'current_closure_blocker_count': closure_total,
    'active_evidence_present': True,
    'active_findings_present': True,
    'stage_exit_allowed': stage_exit,
    'website_construction_allowed': stage_exit,
    'deployment_allowed': False,
    'historical_counts_may_be_treated_as_current': False,
    'source_execution_sha': head,
    'reexecution_cycle': 'R1',
    'next_action': 'MATERIAL_REMEDIATION_OF_REMAINING_FRESH_FUNCTIONAL_GAPS' if result_status == 'BLOCKED' else 'KNOWN_SIGNATURE_ZERO_CHECK_AND_HIDDEN_DEFECT_SWEEP',
}
dump_yaml(LEDGER, ledger)

state = load_yaml(STATE)
execution = state.setdefault('execution', {})
stage2 = execution.setdefault('stage2', {})
execution['current_stage'] = 'STAGE-02-TESTED-BLOCKED' if result_status == 'BLOCKED' else 'STAGE-02-REEXECUTED-PASS-PENDING-CLOSURE'
stage2['result'] = 'TEST_EXECUTED_BLOCKED' if result_status == 'BLOCKED' else 'TEST_EXECUTED_PASS'
stage2['stage_entry_gate'] = 'PASS'
stage2['stage_exit_allowed'] = stage_exit
stage2['prior_results_authoritative_for_next_run'] = False
stage2['prior_results_used_in_current_run'] = False
stage2['artifact_root_present'] = True
execution['website_construction_allowed'] = stage_exit
execution['deployment_allowed'] = False
attempt = state.setdefault('stage02_active_attempt', {})
attempt['source_execution_sha'] = head
attempt['active_evidence_present'] = True
attempt['active_findings_present'] = True
attempt['fresh_functional_gap_total'] = functional_total
attempt['fresh_closure_blocker_total'] = closure_total
attempt['preserved_external_authority_union_count'] = len(union_gap_uids)
attempt['material_remediation_started'] = True
attempt['material_remediation_receipt_ref'] = 'governance/test/stage02/STAGE02_MATERIAL_REMEDIATION_RECEIPT_R1.yaml'
attempt['reexecution_clean_baseline_receipt_ref'] = 'governance/test/stage02/STAGE02_REEXECUTION_CLEAN_BASELINE_RECEIPT_R1.yaml'
attempt['defect_signature_regression_receipt_ref'] = 'governance/test/stage02/STAGE02_DEFECT_SIGNATURE_REGRESSION_R1.yaml'
attempt['reexecution_cycle'] = 'R1'
state['stage02_material_remediation'] = {
    'cycle': 'R1',
    'owning_layer': 'CURRENT_STAGE_PRODUCT_OR_CONTRACT_OUTPUT',
    'materialized_missing_artifact_blockers': 13,
    'fresh_reexecution_missing_artifact_blocker_count': 0,
    'material_elimination_count': 13,
    'remaining_fresh_functional_gap_count': functional_total,
    'external_authority_union_count': len(union_gap_uids),
    'external_authority_resolution_claimed': False,
    'current_specification_mutated': False,
}
state['status'] = 'ACTIVE_STAGE2_REEXECUTED_BLOCKED' if result_status == 'BLOCKED' else 'ACTIVE_STAGE2_REEXECUTED_PASS_PENDING_CLOSURE'
state['next_action'] = 'MATERIAL_REMEDIATION_AT_OWNING_LAYER_FOR_REMAINING_FRESH_FUNCTIONAL_GAPS' if result_status == 'BLOCKED' else 'KNOWN_DEFECT_ZERO_AND_HIDDEN_DEFECT_SWEEP'
dump_yaml(STATE, state)

print('STAGE02_REEXECUTION_SOURCE_HEAD=' + head)
for page_uid, rec in pages.items():
    scan = rec['functional_chain_fresh_scan']
    print(f'STAGE02_REEXECUTION_PAGE|{page_uid}|functional_gaps={scan["gap_count"]}|closure_blockers=0')
    print('STAGE02_REEXECUTION_GAP_CATEGORIES|' + page_uid + '|' + json.dumps(scan['gap_categories'], ensure_ascii=False, sort_keys=True))
print('STAGE02_REEXECUTION_EXTERNAL_AUTHORITY_UNION=' + ','.join(sorted(union_gap_uids)))
print('STAGE02_REEXECUTION_RESULT=' + result_status)
print('STAGE02_REEXECUTION_FUNCTIONAL_GAPS=' + str(functional_total))
print('STAGE02_REEXECUTION_CLOSURE_BLOCKERS=0')
print('PASS: fresh reexecution used exact first-run fresh_scan implementation and did not reuse prior Stage-02 counts as scan input')
