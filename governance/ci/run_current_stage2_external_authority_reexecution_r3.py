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
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
FREEZE = ROOT / 'governance/test/stage02/STAGE02_STAGE_FROZEN_GOVERNANCE_RECEIPT.yaml'
CLEAN = ROOT / 'governance/test/stage02/STAGE02_EXTERNAL_AUTHORITY_REEXECUTION_CLEAN_BASELINE_RECEIPT_R3.yaml'
FUNCTIONAL_RECEIPT = ROOT / 'governance/test/stage02/STAGE02_FUNCTIONAL_MATERIAL_REMEDIATION_R3_RECEIPT.yaml'
LATEST = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
FINDINGS = ROOT / 'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
REGRESSION = ROOT / 'governance/test/stage02/STAGE02_DEFECT_SIGNATURE_REGRESSION_R3.yaml'
LEDGER = ROOT / 'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
RESULT = ROOT / '.github/stage02-test/STAGE02_EXTERNAL_AUTHORITY_REEXECUTION_RESULT_R3.json'
GAP006_MAP = PRODUCT_ROOT / 'SHARED_OWNER_PORT_MAP_R3.yaml'
VALIDATORS = [
    ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py',
    ROOT / 'governance/ci/validate_current_stage2_functional_remediation_r3.py',
    ROOT / 'governance/ci/validate_current_stage2_external_authority_resolution_r3.py',
    ROOT / 'governance/ci/validate_stage02_remediation_reset_continuity_r3.py',
]
PAGES = {
    'CORE-01': {
        'raw': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
        'blueprint': RUN / '02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml',
        'ledger': PRODUCT_ROOT / 'CORE-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml',
        'ai_profile': True,
    },
    'ASSET-01': {
        'raw': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
        'blueprint': RUN / '02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml',
        'ledger': PRODUCT_ROOT / 'ASSET-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml',
        'ai_profile': False,
    },
}
EXPECTED_GAPS = {f'GAP-{i:03}' for i in range(1, 9)}
GAP006_DETAIL = 'GAP-006: ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY'
EXPECTED_EFFECTIVE_CATEGORIES = {
    'ACTION_WITHOUT_CONTROL_OR_TRIGGER': 1,
    'AUDIT_EVENT_NODE_MISSING': 13,
    'FAILURE_STATE_ERROR_BINDING_MISSING': 44,
    'PAYLOAD_INPUT_CONTRACT_MISSING': 34,
    'POST_ACTION_VALIDATION_NODE_MISSING': 18,
    'STATE_TRANSITION_LEDGER_FIELD_MISSING': 40,
}


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
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')


def git_head() -> str:
    return subprocess.run(['git','rev-parse','HEAD'], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()


def exact_external_refs(blueprint: dict):
    refs = []
    for ref in blueprint.get('unresolved_external_authority_refs') or []:
        if isinstance(ref, dict):
            refs.append({'gap_uid': ref.get('gap_uid'), 'authority_ref': ref.get('authority_ref')})
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


def signature(page_uid: str, gap: dict):
    return (page_uid, gap.get('category'), str(gap.get('uid')), gap.get('detail'))


def load_product_signatures():
    materialized = {}
    by_page = Counter()
    for page_uid, cfg in PAGES.items():
        ledger = load_yaml(cfg['ledger'])
        if ledger.get('artifact_type') != 'AUTO_COMPLETION_SCOPE_LEDGER':
            die(f'WRONG_AUTO_COMPLETION_LEDGER:{page_uid}')
        for rem in ledger.get('remediations') or []:
            ds = rem.get('defect_signature') or {}
            key = (page_uid, ds.get('category'), str(ds.get('uid')), ds.get('detail'))
            if key in materialized:
                die(f'DUPLICATE_PRODUCT_SIGNATURE:{key}')
            materialized[key] = rem
            by_page[page_uid] += 1
    if len(materialized) != 17 or by_page != Counter({'ASSET-01': 12, 'CORE-01': 5}):
        die(f'PRODUCT_SIGNATURE_DENOMINATOR_DRIFT:total={len(materialized)} pages={dict(by_page)}')
    return materialized


def load_gap006_signatures():
    doc = load_yaml(GAP006_MAP)
    if doc.get('artifact_uid') != 'FRESH-RUN-003-STAGE2-SHARED-OWNER-PORT-MAP-R3' or doc.get('status') != 'RESOLVED_AUTHORITY_GAP_CURRENT_SUCCESSOR':
        die('GAP006_R3_MAP_IDENTITY_DRIFT')
    consumers = doc.get('consumers') or []
    if len(consumers) != 4:
        die(f'GAP006_CONSUMER_DENOMINATOR_DRIFT:{len(consumers)}')
    materialized = {}
    for row in consumers:
        if row.get('page_uid') != 'ASSET-01' or row.get('status') != 'RESOLVED_EXACT_AUTHORITY' or row.get('binding_kind') != 'SHARED_OPERATION_REFERENCE' or row.get('resolved_port_uid') is not None or row.get('port_uid_status') != 'NOT_APPLICABLE_BY_BINDING_KIND':
            die(f'GAP006_CONSUMER_NOT_EXACT:{row.get("action_uid")}')
        key = ('ASSET-01', 'SHARED_OWNER_AUTHORITY_UNRESOLVED', str(row.get('action_uid')), GAP006_DETAIL)
        if key in materialized:
            die(f'DUPLICATE_GAP006_SIGNATURE:{key}')
        materialized[key] = row
    if len(materialized) != 4:
        die('GAP006_SIGNATURE_DENOMINATOR_DRIFT')
    return materialized


def effective_scan(page_uid: str, raw_scan: dict, product: dict, gap006: dict):
    raw_gaps = raw_scan.get('gaps') or []
    raw_keys = [signature(page_uid, g) for g in raw_gaps]
    if len(raw_keys) != len(set(raw_keys)):
        die(f'RAW_GAP_SIGNATURE_DUPLICATE:{page_uid}')
    remaining = []
    product_eliminated = []
    authority_eliminated = []
    for gap in raw_gaps:
        key = signature(page_uid, gap)
        if key in product and key in gap006:
            die(f'OVERLAPPING_REMEDIATION_SIGNATURE:{key}')
        if key in product:
            product_eliminated.append({'raw_gap': gap, 'remediation_uid': product[key].get('remediation_uid'), 'owning_layer': product[key].get('owning_layer'), 'effective_reproduction': False})
        elif key in gap006:
            authority_eliminated.append({'raw_gap': gap, 'authority_gap_uid': 'GAP-006', 'resolution': 'RESOLVED_EXACT_AUTHORITY', 'binding_kind': 'SHARED_OPERATION_REFERENCE', 'effective_reproduction': False})
        else:
            remaining.append(gap)
    return {
        'gap_count': len(remaining),
        'gap_categories': dict(sorted(Counter(g.get('category') for g in remaining).items())),
        'gap_classes': dict(sorted(Counter(g.get('class') for g in remaining).items())),
        'gaps': remaining,
        'product_materialization_elimination_count': len(product_eliminated),
        'product_materialization_eliminations': product_eliminated,
        'gap006_authority_elimination_count': len(authority_eliminated),
        'gap006_authority_eliminations': authority_eliminated,
        'total_elimination_count': len(product_eliminated) + len(authority_eliminated),
    }


if os.environ.get('STAGE02_FULL_LINE_CONFIRMED') != '1':
    die('R3_REEXECUTION_REQUIRES_SAME_WORKFLOW_FULL_LINE_CONFIRMATION')
state = load_yaml(STATE)
freeze = load_yaml(FREEZE)
clean = load_yaml(CLEAN)
functional_receipt = load_yaml(FUNCTIONAL_RECEIPT)
execution = state.get('execution') or {}
if execution.get('current_stage') != 'STAGE-02-TESTED-BLOCKED' or (execution.get('stage2') or {}).get('result') != 'TEST_EXECUTED_BLOCKED':
    die('R3_REEXECUTION_REQUIRES_CURRENT_STAGE02_BLOCKED_STATE')
if clean.get('status') != 'CLEAN_EXTERNAL_AUTHORITY_AWARE_REEXECUTION_BASELINE_READY' or clean.get('gap006_exact_authority_fix_validated') is not True:
    die('R3_CLEAN_BASELINE_RECEIPT_INVALID')
if clean.get('frozen_governance_uid') != freeze.get('frozen_governance_uid'):
    die('R3_FROZEN_GOVERNANCE_UID_DRIFT')
if (functional_receipt.get('materialized_now') or {}).get('total') != 17:
    die('R3_PRODUCT_FUNCTIONAL_MATERIAL_RECEIPT_NOT_17')
for validator in VALIDATORS:
    cp = subprocess.run([sys.executable, str(validator)], cwd=str(ROOT), text=True)
    if cp.returncode != 0:
        die(f'R3_PRE_EXECUTION_VALIDATOR_FAILED:{validator.name}')

fresh_scan = load_exact_fresh_scan_implementation()
product = load_product_signatures()
gap006 = load_gap006_signatures()
if set(product) & set(gap006):
    die('PRODUCT_AND_GAP006_SIGNATURE_SETS_OVERLAP')

head = git_head()
pages = {}
source_external = {}
union_gap_uids = set()
raw_total = 0
product_eliminated_total = 0
gap006_eliminated_total = 0
effective_total = 0
matched_product = set()
matched_gap006 = set()

for page_uid, cfg in PAGES.items():
    raw = load_yaml(cfg['raw'])
    blueprint = load_yaml(cfg['blueprint'])
    refs = exact_external_refs(blueprint)
    for ref in refs:
        gid = ref.get('gap_uid')
        union_gap_uids.add(gid)
        rec = source_external.setdefault(gid, {'authority_ref': ref.get('authority_ref'), 'consumers': [], 'source_reference_preserved': True})
        rec['consumers'].append(page_uid)
    raw_scan = fresh_scan(page_uid, raw)
    eff = effective_scan(page_uid, raw_scan, product, gap006)
    raw_total += int(raw_scan.get('gap_count') or 0)
    product_eliminated_total += eff['product_materialization_elimination_count']
    gap006_eliminated_total += eff['gap006_authority_elimination_count']
    effective_total += eff['gap_count']
    for item in eff['product_materialization_eliminations']:
        matched_product.add(signature(page_uid, item['raw_gap']))
    for item in eff['gap006_authority_eliminations']:
        matched_gap006.add(signature(page_uid, item['raw_gap']))
    pages[page_uid] = {
        'blueprint_uid': blueprint.get('blueprint_uid'),
        'ai_interaction_profile_active': cfg['ai_profile'],
        'source_external_authority_ref_count': len(refs),
        'functional_chain_raw_fresh_scan': raw_scan,
        'functional_chain_effective_r3_scan': eff,
        'closure_blockers': [],
        'closure_blocker_count': 0,
        'materialized_structural_contract_validation': 'PASS',
        'materialized_product_functional_contract_validation': 'PASS',
        'gap006_external_authority_validation': 'PASS',
    }

if raw_total != 171:
    die(f'RAW_DISCOVERY_DENOMINATOR_DRIFT:{raw_total}')
if matched_product != set(product):
    die(f'PRODUCT_SIGNATURE_RAW_MATCH_DRIFT:missing={sorted(set(product)-matched_product)} extra={sorted(matched_product-set(product))}')
if matched_gap006 != set(gap006):
    die(f'GAP006_SIGNATURE_RAW_MATCH_DRIFT:missing={sorted(set(gap006)-matched_gap006)} extra={sorted(matched_gap006-set(gap006))}')
if product_eliminated_total != 17 or gap006_eliminated_total != 4:
    die(f'R3_ELIMINATION_DENOMINATOR_DRIFT:product={product_eliminated_total}:gap006={gap006_eliminated_total}')
if effective_total != 150 or effective_total != raw_total - product_eliminated_total - gap006_eliminated_total:
    die(f'R3_EFFECTIVE_ARITHMETIC_DRIFT:raw={raw_total}:product={product_eliminated_total}:gap006={gap006_eliminated_total}:effective={effective_total}')
if union_gap_uids != EXPECTED_GAPS:
    die(f'SOURCE_EXTERNAL_AUTHORITY_UNION_DRIFT:expected={sorted(EXPECTED_GAPS)} actual={sorted(union_gap_uids)}')
if pages['CORE-01']['functional_chain_effective_r3_scan']['gap_count'] != 40 or pages['ASSET-01']['functional_chain_effective_r3_scan']['gap_count'] != 110:
    die('R3_PAGE_EFFECTIVE_DENOMINATOR_DRIFT')
all_effective_categories = Counter()
effective_gap006 = []
for page_uid, rec in pages.items():
    eff = rec['functional_chain_effective_r3_scan']
    all_effective_categories.update(eff['gap_categories'])
    for gap in eff['gaps']:
        if gap.get('category') == 'SHARED_OWNER_AUTHORITY_UNRESOLVED':
            effective_gap006.append((page_uid, gap.get('uid'), gap.get('detail')))
if dict(sorted(all_effective_categories.items())) != EXPECTED_EFFECTIVE_CATEGORIES:
    die(f'R3_EFFECTIVE_CATEGORY_DRIFT:{dict(sorted(all_effective_categories.items()))}')
if effective_gap006:
    die(f'GAP006_EFFECTIVE_REPRODUCTION_NOT_ZERO:{effective_gap006}')

for gid, rec in source_external.items():
    rec['stage2_successor_status'] = 'RESOLVED_EXACT_AUTHORITY' if gid == 'GAP-006' else 'PRESERVED_SOURCE_REFERENCE_NO_BULK_CLOSURE'

result_status = 'BLOCKED'
stage_exit = False
result = {
    'schema_version': 4,
    'artifact_type': 'NON_NORMATIVE_STAGE02_ACTUAL_TEST_EVIDENCE',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'stage_name': 'PAGE_FUNCTIONAL_CONTRACT',
    'reexecution_cycle': 'R3_EXTERNAL_AUTHORITY_AWARE',
    'source_head_sha': head,
    'frozen_governance_uid': freeze.get('frozen_governance_uid'),
    'test_mode': 'FRESH_RAW_DISCOVERY_PLUS_VALIDATED_PRODUCT_AND_EXACT_GAP006_SUCCESSOR_ACCEPTANCE',
    'fresh_scan_implementation': 'EXACT_AST_EXTRACT_OF_run_current_stage2_actual_test.py::fresh_scan',
    'actual_product_stage_test_started': True,
    'actual_product_stage_test_completed': True,
    'stage_entry_gate': 'PASS',
    'stage_exit_allowed': False,
    'result': result_status,
    'physical_stage2_product_artifact_root_present': True,
    'pages': pages,
    'raw_discovery_gap_total': raw_total,
    'materialized_product_functional_elimination_count': product_eliminated_total,
    'materialized_external_authority_elimination_count': gap006_eliminated_total,
    'materialized_functional_elimination_count': product_eliminated_total + gap006_eliminated_total,
    'fresh_total_elimination_count': product_eliminated_total + gap006_eliminated_total,
    'fresh_functional_gap_total': effective_total,
    'closure_blocker_total': 0,
    'preserved_source_external_authorities': dict(sorted(source_external.items())),
    'preserved_external_authority_union_count': len(union_gap_uids),
    'preserved_external_authority_union_gap_uids': sorted(union_gap_uids),
    'gap006_stage2_successor_status': 'RESOLVED_EXACT_AUTHORITY',
    'effective_shared_owner_external_gap_count': 0,
    'current_specification_mutated': False,
    'stage1_raw_source_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'prior_stage2_results_used': False,
    'prior_stage2_counts_used_as_scan_input': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
    'notes': [
        'Raw discovery is freshly executed from immutable Stage-01 authority with the exact first-run scanner.',
        'Seventeen product signatures are eliminated only by exact matches to validated current AUTO_COMPLETION_SCOPE_LEDGER entries.',
        'Four GAP-006 signatures are eliminated only by exact action/detail matches to the validated R3 shared-operation successor; no port_uid is invented.',
        'The eight Stage-01 external Authority references remain preserved as source history; GAP-006 is separately marked resolved in the Stage-02 successor and is not an effective blocker.',
        'One hundred fifty product-design/contract gaps remain blocking, therefore Stage-02 does not close.',
    ],
}
RESULT.parent.mkdir(parents=True, exist_ok=True)
RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
LATEST.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

page_findings = {}
for page_uid, rec in pages.items():
    raw_scan = rec['functional_chain_raw_fresh_scan']
    eff = rec['functional_chain_effective_r3_scan']
    page_findings[page_uid] = {
        'raw_discovery_gap_total': raw_scan['gap_count'],
        'raw_categories': raw_scan['gap_categories'],
        'product_materialization_elimination_count': eff['product_materialization_elimination_count'],
        'gap006_authority_elimination_count': eff['gap006_authority_elimination_count'],
        'fresh_functional_gap_total': eff['gap_count'],
        'effective_categories': eff['gap_categories'],
        'closure_blocker_count': 0,
        'closure_blockers': [],
    }
findings = {
    'schema_version': 4,
    'artifact_uid': 'STAGE02-FRESH-EXTERNAL-AUTHORITY-AWARE-FINDINGS-20260915-R3',
    'artifact_type': 'NON_NORMATIVE_STAGE_TEST_FINDING_LEDGER',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'stage_name': 'PAGE_FUNCTIONAL_CONTRACT',
    'source_execution_sha': head,
    'reexecution_cycle': 'R3_EXTERNAL_AUTHORITY_AWARE',
    'prior_stage2_results_used': False,
    'current_specification_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'result': result_status,
    'stage_entry_gate': 'PASS',
    'stage_exit_allowed': False,
    'raw_discovery_gap_total': raw_total,
    'product_materialization_elimination_count': product_eliminated_total,
    'gap006_authority_elimination_count': gap006_eliminated_total,
    'fresh_total_elimination_count': product_eliminated_total + gap006_eliminated_total,
    'fresh_functional_gap_total': effective_total,
    'closure_blocker_total': 0,
    'pages': page_findings,
    'preserved_external_authority': {
        'source_union_count': len(union_gap_uids),
        'source_gap_uids': sorted(union_gap_uids),
        'gap006_stage2_successor_status': 'RESOLVED_EXACT_AUTHORITY',
        'effective_shared_owner_gap_count': 0,
        'all_other_source_references_bulk_closed': False,
    },
    'remaining_product_design_authority_request_count': 150,
    'specification_change_required': False,
    'formal_specification_may_be_modified_from_this_finding': False,
    'status': 'OPEN_STAGE02_PRODUCT_DESIGN_AUTHORITY_REMEDIATION',
}
dump_yaml(FINDINGS, findings)

dump_yaml(REGRESSION, {
    'schema_version': 1,
    'artifact_type': 'DEFECT_SIGNATURE_REGRESSION_RECEIPT',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'reexecution_cycle': 'R3_EXTERNAL_AUTHORITY_AWARE',
    'frozen_governance_uid': freeze.get('frozen_governance_uid'),
    'fresh_reexecution_sha': head,
    'structural_missing_artifact_signature': {'original_reproduction_count': 13, 'effective_fresh_reproduction_count': 0, 'status': 'ZERO_REPRODUCTION_PASS'},
    'bounded_product_functional_signature': {'validated_materialized_signature_count': 17, 'effective_fresh_reproduction_count': 0, 'status': 'ZERO_EFFECTIVE_REPRODUCTION_PASS'},
    'gap006_shared_owner_authority_signature': {'validated_exact_authority_signature_count': 4, 'effective_fresh_reproduction_count': 0, 'status': 'ZERO_EFFECTIVE_REPRODUCTION_PASS'},
    'remaining_product_contract_signature': {'effective_fresh_reproduction_count': effective_total, 'status': 'REMAINS_BLOCKING'},
    'source_external_authority_union_count': len(union_gap_uids),
    'gap006_stage2_successor_resolution_claimed': True,
    'all_external_authorities_resolved_claimed': False,
    'stage_closure_claimed': False,
})

ledger = load_yaml(LEDGER)
ledger['current_stage2_execution'] = {
    'state': 'REEXECUTED_BLOCKED',
    'raw_discovery_gap_count': raw_total,
    'product_materialization_elimination_count': product_eliminated_total,
    'gap006_exact_authority_elimination_count': gap006_eliminated_total,
    'total_fresh_elimination_count': product_eliminated_total + gap006_eliminated_total,
    'current_functional_gap_count': effective_total,
    'current_closure_blocker_count': 0,
    'active_evidence_present': True,
    'active_findings_present': True,
    'stage_exit_allowed': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
    'historical_counts_may_be_treated_as_current': False,
    'source_execution_sha': head,
    'reexecution_cycle': 'R3_EXTERNAL_AUTHORITY_AWARE',
    'next_action': 'MATERIAL_REMEDIATION_OF_REMAINING_150_PRODUCT_DESIGN_AUTHORITY_GAPS',
}
dump_yaml(LEDGER, ledger)

state = load_yaml(STATE)
execution = state.setdefault('execution', {})
stage2 = execution.setdefault('stage2', {})
execution['current_stage'] = 'STAGE-02-TESTED-BLOCKED'
stage2['result'] = 'TEST_EXECUTED_BLOCKED'
stage2['stage_entry_gate'] = 'PASS'
stage2['stage_exit_allowed'] = False
stage2['prior_results_authoritative_for_next_run'] = False
stage2['prior_results_used_in_current_run'] = False
stage2['artifact_root_present'] = True
execution['website_construction_allowed'] = False
execution['deployment_allowed'] = False
attempt = state.setdefault('stage02_active_attempt', {})
attempt['source_execution_sha'] = head
attempt['active_evidence_present'] = True
attempt['active_findings_present'] = True
attempt['raw_discovery_gap_total'] = raw_total
attempt['materialized_product_functional_elimination_count'] = product_eliminated_total
attempt['materialized_external_authority_elimination_count'] = gap006_eliminated_total
attempt['materialized_functional_elimination_count'] = product_eliminated_total + gap006_eliminated_total
attempt['fresh_functional_gap_total'] = effective_total
attempt['fresh_closure_blocker_total'] = 0
attempt['preserved_external_authority_union_count'] = len(union_gap_uids)
attempt['effective_shared_owner_external_gap_count'] = 0
attempt['gap006_stage2_successor_status'] = 'RESOLVED_EXACT_AUTHORITY'
attempt['external_authority_reexecution_clean_baseline_receipt_ref'] = 'governance/test/stage02/STAGE02_EXTERNAL_AUTHORITY_REEXECUTION_CLEAN_BASELINE_RECEIPT_R3.yaml'
attempt['defect_signature_regression_receipt_ref'] = 'governance/test/stage02/STAGE02_DEFECT_SIGNATURE_REGRESSION_R3.yaml'
attempt['reexecution_cycle'] = 'R3_EXTERNAL_AUTHORITY_AWARE'
attempt['product_design_authority_blocked'] = 150
attempt['preserved_external_shared_authority_blocked'] = 0
attempt['new_authority_required_before_more_material_remediation'] = True
attempt['exact_resume_point'] = 'INGEST_OR_RESOLVE_REMAINING_150_PRODUCT_DESIGN_AUTHORITY_GAPS_THEN_FULL_LINE_SYSTEM_GATE_THEN_FRESH_STAGE02_REEXECUTION'
state['stage02_material_remediation'] = {
    'cycle': 'R3_EXTERNAL_AUTHORITY_AWARE',
    'owning_layer': 'CURRENT_STAGE_PRODUCT_OR_CONTRACT_OUTPUT',
    'materialized_structural_blockers': 13,
    'fresh_structural_blocker_count': 0,
    'raw_discovery_functional_gap_count': raw_total,
    'validated_product_materialization_count': 17,
    'validated_gap006_external_authority_resolution_count': 4,
    'fresh_total_elimination_count': product_eliminated_total + gap006_eliminated_total,
    'remaining_fresh_functional_gap_count': effective_total,
    'source_external_authority_union_count': len(union_gap_uids),
    'gap006_stage2_successor_resolved': True,
    'all_external_authority_resolved': False,
    'current_specification_mutated': False,
}
state['status'] = 'ACTIVE_STAGE2_REEXECUTED_BLOCKED'
state['next_action'] = 'MATERIAL_REMEDIATION_AT_OWNING_LAYER_FOR_REMAINING_150_PRODUCT_DESIGN_AUTHORITY_GAPS'
dump_yaml(STATE, state)

print('STAGE02_R3_SOURCE_HEAD=' + head)
for page_uid, rec in pages.items():
    raw_scan = rec['functional_chain_raw_fresh_scan']
    eff = rec['functional_chain_effective_r3_scan']
    print(f'STAGE02_R3_PAGE|{page_uid}|raw={raw_scan["gap_count"]}|product_eliminated={eff["product_materialization_elimination_count"]}|gap006_eliminated={eff["gap006_authority_elimination_count"]}|effective={eff["gap_count"]}')
print('STAGE02_R3_RAW_DISCOVERY_GAPS=' + str(raw_total))
print('STAGE02_R3_PRODUCT_ELIMINATED=' + str(product_eliminated_total))
print('STAGE02_R3_GAP006_ELIMINATED=' + str(gap006_eliminated_total))
print('STAGE02_R3_TOTAL_ELIMINATED=' + str(product_eliminated_total + gap006_eliminated_total))
print('STAGE02_R3_EFFECTIVE_GAPS=' + str(effective_total))
print('STAGE02_R3_EFFECTIVE_GAP006=0')
print('STAGE02_R3_RESULT=BLOCKED')
print('PASS: 171 fresh raw signatures -> 17 exact product eliminations + 4 exact GAP-006 Authority eliminations -> 150 effective blockers')
