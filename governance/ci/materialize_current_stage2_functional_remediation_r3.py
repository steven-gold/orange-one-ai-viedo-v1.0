#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
STAGE2 = RUN / '04_PAGE_FUNCTIONAL_CONTRACT'
R3 = ROOT / 'governance/test/stage02/STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION_R3.yaml'
RECEIPT = ROOT / 'governance/test/stage02/STAGE02_FUNCTIONAL_MATERIAL_REMEDIATION_R3_RECEIPT.yaml'
RAW = {
    'CORE-01': '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
    'ASSET-01': '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
}


def die(msg):
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load(path):
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def negative_tests(page_uid, proof):
    transition_uid = proof['transition_uid']
    frm = proof['from_stage']
    trigger = proof['trigger']
    gate = proof.get('gate')
    tests = [
        {
            'test_uid': f'{transition_uid}-NEG-WRONG-FROM-STAGE',
            'condition': f'current_stage != {frm}',
            'expected': 'BLOCK_TRANSITION',
            'invented_business_value': False,
        },
        {
            'test_uid': f'{transition_uid}-NEG-WRONG-TRIGGER',
            'condition': f'observed_trigger != {trigger}',
            'expected': 'BLOCK_TRANSITION',
            'invented_business_value': False,
        },
    ]
    if gate not in (None, '', [], {}):
        tests.append({
            'test_uid': f'{transition_uid}-NEG-GATE-NOT-SATISFIED',
            'condition': f'gate_not_satisfied: {gate}',
            'expected': 'BLOCK_TRANSITION',
            'invented_business_value': False,
        })
    return tests


r3 = load(R3)
summary = r3.get('classification_summary') or {}
if r3.get('fresh_functional_gap_denominator') != 171:
    die('R3_DENOMINATOR_NOT_171')
if summary.get('BOUNDED_COMPLETION_ADMISSIBLE') != 17:
    die(f'R3_ADMISSIBLE_NOT_17:{summary.get("BOUNDED_COMPLETION_ADMISSIBLE")}')
if summary.get('EXACT_EXTERNAL_AUTHORITY_REQUIRED') != 4:
    die('R3_EXTERNAL_NOT_4')
if summary.get('NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS') != 150:
    die('R3_BLOCKED_NOT_150')

admissible = [r for r in r3.get('records', []) if r.get('disposition') == 'BOUNDED_COMPLETION_ADMISSIBLE']
if len(admissible) != 17:
    die(f'R3_RECORD_ADMISSIBLE_COUNT:{len(admissible)}')
by_page = defaultdict(list)
for rec in admissible:
    page = rec.get('page_uid')
    if page not in RAW:
        die(f'UNEXPECTED_PAGE:{page}')
    proof = rec.get('proof') or {}
    category = rec.get('category')
    if category == 'STATE_TRANSITION_LEDGER_FIELD_MISSING':
        if rec.get('detail') != 'illegal_transition_tests':
            die(f'ILLEGAL_TRANSITION_REMEDIATION_SCOPE:{rec.get("uid")}')
        if proof.get('proof_kind') != 'DETERMINISTIC_REQUIRED_DEPENDENCY':
            die(f'INVALID_TRANSITION_PROOF:{rec.get("uid")}')
        closure = {
            'closure_type': 'ILLEGAL_TRANSITION_NEGATIVE_TESTS',
            'transition_uid': rec['uid'],
            'illegal_transition_tests': negative_tests(page, proof),
        }
    elif category == 'SUCCESS_NEXT_STATE_BINDING_MISSING':
        if proof.get('proof_kind') != 'DETERMINISTIC_ACTION_PORT_STATE_EFFECT_PROJECTION':
            die(f'INVALID_SUCCESS_PROOF:{rec.get("uid")}')
        if not proof.get('port_uid') or proof.get('state_event') in (None, ''):
            die(f'INCOMPLETE_ACTION_PORT_PROOF:{rec.get("uid")}')
        closure = {
            'closure_type': 'SUCCESS_NEXT_STATE_BINDING',
            'action_uid': rec['uid'],
            'source_port_uid': proof['port_uid'],
            'success_state_effect': proof['state_event'],
            'projection_rule': 'EXACT_COPY_FROM_REGISTERED_ACTION_PORT_STATE_EVENT',
        }
    else:
        die(f'R3_ADMITTED_UNSUPPORTED_CATEGORY:{category}:{rec.get("uid")}')
    by_page[page].append({
        'remediation_uid': f'R3::{page}::{category}::{rec.get("uid")}::{rec.get("detail")}',
        'defect_signature': {
            'category': category,
            'uid': rec.get('uid'),
            'detail': rec.get('detail'),
        },
        'owning_layer': 'STAGE-02_PAGE_FUNCTIONAL_CONTRACT',
        'registered_seed_authority': RAW[page],
        'completion_basis': rec.get('completion_basis'),
        'exact_proof': proof,
        'materialized_closure': closure,
        'semantic_inference_used': False,
        'ai_invented_business_value': False,
        'external_authority_resolution_performed': False,
    })

if {p: len(v) for p, v in by_page.items()} != {'CORE-01': 5, 'ASSET-01': 12}:
    die(f'PAGE_ADMISSIBLE_DENOMINATOR_DRIFT:{ {p: len(v) for p, v in by_page.items()} }')

for page_uid in ('CORE-01', 'ASSET-01'):
    package_path = STAGE2 / page_uid / 'PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml'
    package = load(package_path)
    frozen_uid = package.get('frozen_governance_uid')
    if not frozen_uid:
        die(f'MISSING_FROZEN_UID:{page_uid}')
    ledger = {
        'schema_version': 1,
        'artifact_type': 'AUTO_COMPLETION_SCOPE_LEDGER',
        'normative_authority': False,
        'stage_uid': 'STAGE-02',
        'page_uid': page_uid,
        'frozen_governance_uid': frozen_uid,
        'source_classification_ref': 'governance/test/stage02/STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION_R3.yaml',
        'activation_reason': 'REQUIRED_GAP_CLOSURE_FROM_REGISTERED_SEED',
        'bounded_completion': {
            'seed_gap_or_required_operation_required': True,
            'minimal_closure_set': True,
            'generic_crud_symmetry_expansion_used': False,
            'sibling_feature_symmetry_expansion_used': False,
            'semantic_similarity_used': False,
            'external_authority_auto_resolution_used': False,
        },
        'materialized_remediation_count': len(by_page[page_uid]),
        'remediations': by_page[page_uid],
        'unresolved_external_authority_refs_preserved': ['GAP-001','GAP-002','GAP-003','GAP-004','GAP-005','GAP-006','GAP-007','GAP-008'],
        'stage_exit_claimed': False,
    }
    ledger_path = STAGE2 / page_uid / 'AUTO_COMPLETION_SCOPE_LEDGER.yaml'
    ledger_path.write_text(yaml.safe_dump(ledger, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')
    included = package.setdefault('included_artifacts', [])
    if 'AUTO_COMPLETION_SCOPE_LEDGER.yaml' not in included:
        included.append('AUTO_COMPLETION_SCOPE_LEDGER.yaml')
    package['stage_exit_claimed'] = False
    package_path.write_text(yaml.safe_dump(package, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')

head = subprocess.run(['git','rev-parse','HEAD'], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
receipt = {
    'schema_version': 1,
    'artifact_type': 'MATERIAL_REMEDIATION_RECEIPT',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'cycle': 'FUNCTIONAL_REMEDIATION_R3',
    'source_head_sha': head,
    'defect_signature': 'R3_BOUNDED_FUNCTIONAL_COMPLETION_SET',
    'owning_layer': 'CURRENT_STAGE_PRODUCT_OR_CONTRACT_OUTPUT',
    'changed_artifacts': [
        '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/CORE-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml',
        '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/ASSET-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml',
        '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/CORE-01/PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml',
        '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/ASSET-01/PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml',
    ],
    'before_state': {'fresh_functional_gaps': 171, 'closure_blockers': 0},
    'materialized_now': {'total': 17, 'CORE-01': 5, 'ASSET-01': 12},
    'not_materialized': {'exact_external_authority_required': 4, 'no_authorized_bounded_completion_basis': 150},
    'after_state_claim_before_fresh_reexecution': 'NOT_CLAIMED',
    'expected_remaining_if_dual_layer_reexecution_accepts_all_17': 154,
    'regression_target': 'R3_ADMISSIBLE_DEFECT_SIGNATURES_REPRODUCE_ZERO_WITH_DUAL_LAYER_VALIDATOR',
    'current_specification_mutated': False,
    'immutable_stage1_source_mutated': False,
    'external_authority_resolved': False,
    'stage03_allowed': False,
}
RECEIPT.write_text(yaml.safe_dump(receipt, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')
print('PASS: materialized 17 R3-bounded Stage-02 functional closures at owning product/contract layer')
print('PASS: CORE-01=5 ASSET-01=12')
print('PASS: 150 no-basis gaps and 4 external-authority gaps were not materialized')
print('PASS: no fresh gap reduction is claimed before reexecution')
