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
STRUCTURAL_VALIDATOR = ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py'
FUNCTIONAL_VALIDATOR = ROOT / 'governance/ci/validate_current_stage2_functional_remediation_r3.py'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
FREEZE = ROOT / 'governance/test/stage02/STAGE02_STAGE_FROZEN_GOVERNANCE_RECEIPT.yaml'
CLEAN = ROOT / 'governance/test/stage02/STAGE02_DUAL_LAYER_REEXECUTION_CLEAN_BASELINE_RECEIPT_R2.yaml'
FUNCTIONAL_RECEIPT = ROOT / 'governance/test/stage02/STAGE02_FUNCTIONAL_MATERIAL_REMEDIATION_R3_RECEIPT.yaml'
LATEST = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
FINDINGS = ROOT / 'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
REGRESSION = ROOT / 'governance/test/stage02/STAGE02_DEFECT_SIGNATURE_REGRESSION_R2.yaml'
LEDGER = ROOT / 'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
RESULT = ROOT / '.github/stage02-test/STAGE02_DUAL_LAYER_REEXECUTION_RESULT_R2.json'
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


def sig(page_uid: str, gap: dict):
    return (page_uid, gap.get('category'), str(gap.get('uid')), gap.get('detail'))


def load_materialized_signatures():
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
                die(f'DUPLICATE_MATERIALIZED_SIGNATURE:{key}')
            materialized[key] = rem
            by_page[page_uid] += 1
    if len(materialized) != 17 or by_page != Counter({'ASSET-01': 12, 'CORE-01': 5}):
        die(f'MATERIALIZED_SIGNATURE_DENOMINATOR_DRIFT:total={len(materialized)} pages={dict(by_page)}')
    return materialized


def effective_scan(page_uid: str, raw_scan: dict, materialized: dict):
    raw_gaps = raw_scan.get('gaps') or []
    raw_keys = [sig(page_uid, g) for g in raw_gaps]
    if len(raw_keys) != len(set(raw_keys)):
        die(f'RAW_GAP_SIGNATURE_DUPLICATE:{page_uid}')
    eliminated = []
    remaining = []
    for gap in raw_gaps:
        key = sig(page_uid, gap)
        if key in materialized:
            eliminated.append({
                'raw_gap': gap,
                'remediation_uid': materialized[key].get('remediation_uid'),
                'owning_layer': materialized[key].get('owning_layer'),
                'completion_basis': materialized[key].get('completion_basis'),
                'materialized_closure': materialized[key].get('materialized_closure'),
                'effective_reproduction': False,
            })
        else:
            remaining.append(gap)
    categories = Counter(g.get('category') for g in remaining)
    classes = Counter(g.get('class') for g in remaining)
    return {
        'gap_count': len(remaining),
        'gap_categories': dict(sorted(categories.items())),
        'gap_classes': dict(sorted(classes.items())),
        'gaps': remaining,
        'materialized_gap_elimination_count': len(eliminated),
        'materialized_gap_eliminations': eliminated,
    }


if os.environ.get('STAGE02_FULL_LINE_CONFIRMED') != '1':
    die('DUAL_LAYER_REEXECUTION_REQUIRES_SAME_WORKFLOW_FULL_LINE_CONFIRMATION')
state = load_yaml(STATE)
freeze = load_yaml(FREEZE)
clean = load_yaml(CLEAN)
functional_receipt = load_yaml(FUNCTIONAL_RECEIPT)
execution = state.get('execution') or {}
if execution.get('current_stage') != 'STAGE-02-TESTED-BLOCKED':
    die(f'DUAL_LAYER_REEXECUTION_REQUIRES_STAGE02_TESTED_BLOCKED:{execution.get("current_stage")}')
if (execution.get('stage2') or {}).get('result') != 'TEST_EXECUTED_BLOCKED':
    die('DUAL_LAYER_REEXECUTION_REQUIRES_TEST_EXECUTED_BLOCKED')
if clean.get('status') != 'CLEAN_DUAL_LAYER_REEXECUTION_BASELINE_READY':
    die('DUAL_LAYER_CLEAN_BASELINE_RECEIPT_INVALID')
if clean.get('frozen_governance_uid') != freeze.get('frozen_governance_uid'):
    die('DUAL_LAYER_FROZEN_GOVERNANCE_UID_DRIFT')
if functional_receipt.get('materialized_now', {}).get('total') != 17:
    die('FUNCTIONAL_MATERIAL_RECEIPT_NOT_17')
if not PRODUCT_ROOT.is_dir():
    die('STAGE02_PRODUCT_ROOT_MISSING')
for validator in (STRUCTURAL_VALIDATOR, FUNCTIONAL_VALIDATOR):
    cp = subprocess.run([sys.executable, str(validator)], cwd=str(ROOT), text=True)
    if cp.returncode != 0:
        die(f'DUAL_LAYER_OWNING_LAYER_VALIDATOR_FAILED:{validator.name}')

fresh_scan = load_exact_fresh_scan_implementation()
materialized = load_materialized_signatures()
head = git_head()
pages = {}
external = {}
union_gap_uids = set()
raw_total = 0
effective_total = 0
eliminated_total = 0
matched_keys = set()

for page_uid, cfg in PAGES.items():
    raw = load_yaml(cfg['raw'])
    blueprint = load_yaml(cfg['blueprint'])
    refs = exact_external_refs(blueprint)
    for ref in refs:
        gid = ref.get('gap_uid')
        union_gap_uids.add(gid)
        external.setdefault(gid, {'authority_ref': ref.get('authority_ref'), 'consumers': []})['consumers'].append(page_uid)
    raw_scan = fresh_scan(page_uid, raw)
    eff = effective_scan(page_uid, raw_scan, materialized)
    raw_total += raw_scan.get('gap_count', 0)
    effective_total += eff['gap_count']
    eliminated_total += eff['materialized_gap_elimination_count']
    for item in eff['materialized_gap_eliminations']:
        matched_keys.add(sig(page_uid, item['raw_gap']))
    pages[page_uid] = {
        'blueprint_uid': blueprint.get('blueprint_uid'),
        'ai_interaction_profile_active': cfg['ai_profile'],
        'unresolved_external_authority_ref_count': len(refs),
        'functional_chain_raw_fresh_scan': raw_scan,
        'functional_chain_effective_dual_layer_scan': eff,
        'closure_blockers': [],
        'closure_blocker_count': 0,
        'materialized_structural_contract_validation': 'PASS',
        'materialized_functional_contract_validation': 'PASS',
        'automatic_completion_scope': 'VALIDATED_R3_AUTO_COMPLETION_SCOPE_LEDGER_ONLY',
    }

if raw_total != 171:
    die(f'RAW_DISCOVERY_DENOMINATOR_DRIFT:{raw_total}')
if matched_keys != set(materialized):
    missing = sorted(set(materialized) - matched_keys)
    extra = sorted(matched_keys - set(materialized))
    die(f'MATERIALIZED_SIGNATURE_RAW_MATCH_DRIFT:missing={missing}:extra={extra}')
if eliminated_total != len(materialized) or eliminated_total != 17:
    die(f'FRESH_MATERIAL_ELIMINATION_DENOMINATOR_DRIFT:{eliminated_total}')
if effective_total != raw_total - eliminated_total:
    die(f'EFFECTIVE_ARITHMETIC_DRIFT:raw={raw_total}:eliminated={eliminated_total}:effective={effective_total}')
if union_gap_uids != EXPECTED_GAPS:
    die(f'EXTERNAL_AUTHORITY_UNION_DRIFT:expected={sorted(EXPECTED_GAPS)} actual={sorted(union_gap_uids)}')

# All 4 external shared-owner gaps must remain in the effective scan.
effective_external = []
for page_uid, rec in pages.items():
    for gap in rec['functional_chain_effective_dual_layer_scan']['gaps']:
        if gap.get('category') == 'SHARED_OWNER_AUTHORITY_UNRESOLVED':
            effective_external.append((page_uid, gap.get('uid'), gap.get('detail')))
if len(effective_external) != 4:
    die(f'EXTERNAL_SHARED_OWNER_EFFECTIVE_DENOMINATOR_DRIFT:{len(effective_external)}')

closure_total = 0
result_status = 'BLOCKED' if effective_total else 'PASS'
stage_exit = result_status == 'PASS'
result = {
    'schema_version': 3,
    'artifact_type': 'NON_NORMATIVE_STAGE02_ACTUAL_TEST_EVIDENCE',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'stage_name': 'PAGE_FUNCTIONAL_CONTRACT',
    'reexecution_cycle': 'R2_DUAL_LAYER',
    'source_head_sha': head,
    'frozen_governance_uid': freeze.get('frozen_governance_uid'),
    'test_mode': 'FRESH_RAW_DISCOVERY_PLUS_VALIDATED_STAGE2_OWNING_LAYER_DUAL_LAYER_ACCEPTANCE',
    'fresh_scan_implementation': 'EXACT_AST_EXTRACT_OF_run_current_stage2_actual_test.py::fresh_scan',
    'actual_product_stage_test_started': True,
    'actual_product_stage_test_completed': True,
    'stage_entry_gate': 'PASS',
    'stage_exit_allowed': stage_exit,
    'result': result_status,
    'physical_stage2_product_artifact_root_present': True,
    'materialized_structural_contract_validation': 'PASS',
    'materialized_functional_contract_validation': 'PASS',
    'pages': pages,
    'raw_discovery_gap_total': raw_total,
    'materialized_functional_elimination_count': eliminated_total,
    'fresh_functional_gap_total': effective_total,
    'closure_blocker_total': closure_total,
    'preserved_external_authorities': dict(sorted(external.items())),
    'preserved_external_authority_union_count': len(union_gap_uids),
    'preserved_external_authority_union_gap_uids': sorted(union_gap_uids),
    'effective_shared_owner_external_gap_count': len(effective_external),
    'current_specification_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'prior_stage2_results_used': False,
    'prior_stage2_counts_used_as_scan_input': False,
    'website_construction_allowed': stage_exit,
    'deployment_allowed': False,
    'notes': [
        'Raw discovery is freshly executed from immutable Stage-01 authority using the exact first-run scanner and remains visible as a separate baseline.',
        'Only exact raw gap signatures also present in the currently validated Stage-02 AUTO_COMPLETION_SCOPE_LEDGER are removed from the effective dual-layer acceptance set.',
        'No historical gap count is subtracted as input; elimination is derived from exact fresh raw-signature matches against validated current product artifacts.',
        'GAP-001..GAP-008 remain unresolved and the four shared-owner external-authority gaps remain in the effective blocking set.',
    ],
}
RESULT.parent.mkdir(parents=True, exist_ok=True)
RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
LATEST.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

page_findings = {}
for page_uid, rec in pages.items():
    raw_scan = rec['functional_chain_raw_fresh_scan']
    eff = rec['functional_chain_effective_dual_layer_scan']
    page_findings[page_uid] = {
        'raw_discovery_gap_total': raw_scan['gap_count'],
        'raw_categories': raw_scan['gap_categories'],
        'materialized_functional_elimination_count': eff['materialized_gap_elimination_count'],
        'fresh_functional_gap_total': eff['gap_count'],
        'effective_categories': eff['gap_categories'],
        'closure_blocker_count': 0,
        'closure_blockers': [],
    }
findings = {
    'schema_version': 3,
    'artifact_uid': 'STAGE02-FRESH-DUAL-LAYER-REEXECUTION-FINDINGS-20260915-R2',
    'artifact_type': 'NON_NORMATIVE_STAGE_TEST_FINDING_LEDGER',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'stage_name': 'PAGE_FUNCTIONAL_CONTRACT',
    'source_execution_sha': head,
    'reexecution_cycle': 'R2_DUAL_LAYER',
    'prior_stage2_results_used': False,
    'current_specification_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'result': result_status,
    'stage_entry_gate': 'PASS',
    'stage_exit_allowed': stage_exit,
    'raw_discovery_gap_total': raw_total,
    'materialized_functional_elimination_count': eliminated_total,
    'fresh_functional_gap_total': effective_total,
    'closure_blocker_total': 0,
    'pages': page_findings,
    'preserved_external_authority': {
        'exact_union_count': len(union_gap_uids),
        'gap_uids': sorted(union_gap_uids),
        'effective_shared_owner_gap_count': len(effective_external),
        'rule': 'PRESERVE_UNRESOLVED_NO_INFERENCE_NO_AUTOFILL',
    },
    'material_remediation': {
        'structural_missing_artifact_blockers_before': 13,
        'structural_missing_artifact_blockers_after': 0,
        'functional_raw_discovery_before_overlay': raw_total,
        'functional_r3_materialized_and_fresh_matched': eliminated_total,
        'functional_effective_remaining': effective_total,
        'receipt_ref': 'governance/test/stage02/STAGE02_FUNCTIONAL_MATERIAL_REMEDIATION_R3_RECEIPT.yaml',
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
    'reexecution_cycle': 'R2_DUAL_LAYER',
    'frozen_governance_uid': freeze.get('frozen_governance_uid'),
    'fresh_reexecution_sha': head,
    'structural_missing_artifact_signature': {
        'original_reproduction_count': 13,
        'effective_fresh_reproduction_count': 0,
        'status': 'ZERO_REPRODUCTION_PASS',
    },
    'r3_bounded_functional_signature': {
        'raw_discovery_reproduction_count': eliminated_total,
        'validated_materialized_signature_count': len(materialized),
        'effective_fresh_reproduction_count': 0,
        'status': 'ZERO_EFFECTIVE_REPRODUCTION_PASS',
    },
    'remaining_functional_signature': {
        'effective_fresh_reproduction_count': effective_total,
        'status': 'REMAINS_BLOCKING' if effective_total else 'ZERO_REPRODUCTION_PASS',
    },
    'external_authority_union_count': len(union_gap_uids),
    'external_authority_resolution_claimed': False,
    'stage_closure_claimed': False,
})

ledger = load_yaml(LEDGER)
ledger['current_stage2_execution'] = {
    'state': 'REEXECUTED_BLOCKED' if result_status == 'BLOCKED' else 'REEXECUTED_PASS',
    'raw_discovery_gap_count': raw_total,
    'materialized_functional_elimination_count': eliminated_total,
    'current_functional_gap_count': effective_total,
    'current_closure_blocker_count': 0,
    'active_evidence_present': True,
    'active_findings_present': True,
    'stage_exit_allowed': stage_exit,
    'website_construction_allowed': stage_exit,
    'deployment_allowed': False,
    'historical_counts_may_be_treated_as_current': False,
    'source_execution_sha': head,
    'reexecution_cycle': 'R2_DUAL_LAYER',
    'next_action': 'MATERIAL_REMEDIATION_OF_REMAINING_EFFECTIVE_FUNCTIONAL_GAPS' if result_status == 'BLOCKED' else 'KNOWN_SIGNATURE_ZERO_CHECK_AND_HIDDEN_DEFECT_SWEEP',
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
attempt['raw_discovery_gap_total'] = raw_total
attempt['materialized_functional_elimination_count'] = eliminated_total
attempt['fresh_functional_gap_total'] = effective_total
attempt['fresh_closure_blocker_total'] = 0
attempt['preserved_external_authority_union_count'] = len(union_gap_uids)
attempt['functional_material_remediation_receipt_ref'] = 'governance/test/stage02/STAGE02_FUNCTIONAL_MATERIAL_REMEDIATION_R3_RECEIPT.yaml'
attempt['dual_layer_clean_baseline_receipt_ref'] = 'governance/test/stage02/STAGE02_DUAL_LAYER_REEXECUTION_CLEAN_BASELINE_RECEIPT_R2.yaml'
attempt['defect_signature_regression_receipt_ref'] = 'governance/test/stage02/STAGE02_DEFECT_SIGNATURE_REGRESSION_R2.yaml'
attempt['reexecution_cycle'] = 'R2_DUAL_LAYER'
state['stage02_material_remediation'] = {
    'cycle': 'R3_MATERIALIZED_R2_DUAL_LAYER_ACCEPTANCE',
    'owning_layer': 'CURRENT_STAGE_PRODUCT_OR_CONTRACT_OUTPUT',
    'materialized_structural_blockers': 13,
    'fresh_structural_blocker_count': 0,
    'raw_discovery_functional_gap_count': raw_total,
    'validated_functional_materialization_count': len(materialized),
    'fresh_functional_elimination_count': eliminated_total,
    'remaining_fresh_functional_gap_count': effective_total,
    'external_authority_union_count': len(union_gap_uids),
    'external_authority_resolution_claimed': False,
    'current_specification_mutated': False,
}
state['status'] = 'ACTIVE_STAGE2_REEXECUTED_BLOCKED' if result_status == 'BLOCKED' else 'ACTIVE_STAGE2_REEXECUTED_PASS_PENDING_CLOSURE'
state['next_action'] = 'MATERIAL_REMEDIATION_AT_OWNING_LAYER_FOR_REMAINING_EFFECTIVE_FUNCTIONAL_GAPS' if result_status == 'BLOCKED' else 'KNOWN_DEFECT_ZERO_AND_HIDDEN_DEFECT_SWEEP'
dump_yaml(STATE, state)

print('STAGE02_DUAL_LAYER_REEXECUTION_SOURCE_HEAD=' + head)
for page_uid, rec in pages.items():
    raw_scan = rec['functional_chain_raw_fresh_scan']
    eff = rec['functional_chain_effective_dual_layer_scan']
    print(f'STAGE02_DUAL_LAYER_PAGE|{page_uid}|raw={raw_scan["gap_count"]}|eliminated={eff["materialized_gap_elimination_count"]}|effective={eff["gap_count"]}|closure=0')
    print('STAGE02_DUAL_LAYER_EFFECTIVE_CATEGORIES|' + page_uid + '|' + json.dumps(eff['gap_categories'], ensure_ascii=False, sort_keys=True))
print('STAGE02_DUAL_LAYER_RAW_DISCOVERY_GAPS=' + str(raw_total))
print('STAGE02_DUAL_LAYER_FRESH_ELIMINATED=' + str(eliminated_total))
print('STAGE02_DUAL_LAYER_EFFECTIVE_GAPS=' + str(effective_total))
print('STAGE02_DUAL_LAYER_CLOSURE_BLOCKERS=0')
print('STAGE02_DUAL_LAYER_EXTERNAL_AUTHORITY_UNION=' + ','.join(sorted(union_gap_uids)))
print('STAGE02_DUAL_LAYER_RESULT=' + result_status)
print('PASS: no historical count was used as scan input; effective result is exact fresh raw signature matching against validated Stage-02 remediation')
