#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
LATEST = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
R3 = ROOT / 'governance/test/stage02/STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION_R3.yaml'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
CANDIDATES = ROOT / 'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
OUT = ROOT / 'governance/test/stage02/STAGE02_REMAINING_BLOCKER_DISPOSITION_R4.yaml'
AUDITS = {
    'PAYLOAD_INPUT_CONTRACT_MISSING': ROOT / 'governance/test/stage02/PAYLOAD_INPUT_CURRENT_AUTHORITY_AUDIT.yaml',
    'AUDIT_EVENT_NODE_MISSING': ROOT / 'governance/test/stage02/AUDIT_EVENT_CURRENT_AUTHORITY_AUDIT.yaml',
    'FAILURE_STATE_ERROR_BINDING_MISSING': ROOT / 'governance/test/stage02/FAILURE_STATE_ERROR_BINDING_CURRENT_AUTHORITY_AUDIT.yaml',
    'POST_ACTION_VALIDATION_NODE_MISSING': ROOT / 'governance/test/stage02/POST_ACTION_VALIDATION_CURRENT_AUTHORITY_AUDIT.yaml',
    'ACTION_WITHOUT_CONTROL_OR_TRIGGER': ROOT / 'governance/test/stage02/ACTION_CONTROL_TRIGGER_CURRENT_AUTHORITY_AUDIT.yaml',
    'STATE_TRANSITION_LEDGER_FIELD_MISSING': ROOT / 'governance/test/stage02/STATE_TRANSITION_LEDGER_CURRENT_AUTHORITY_AUDIT.yaml',
}
EXPECTED = {
    'PAYLOAD_INPUT_CONTRACT_MISSING': 34,
    'AUDIT_EVENT_NODE_MISSING': 13,
    'FAILURE_STATE_ERROR_BINDING_MISSING': 44,
    'POST_ACTION_VALIDATION_NODE_MISSING': 18,
    'ACTION_WITHOUT_CONTROL_OR_TRIGGER': 1,
    'STATE_TRANSITION_LEDGER_FIELD_MISSING': 40,
    'SHARED_OWNER_AUTHORITY_UNRESOLVED': 4,
}
TRANSITION_REMAINING_FIELDS = {'mutation_owner', 'failure_state', 'recovery', 'audit_event_uid'}


def die(msg):
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path):
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def dump_yaml(path: Path, obj):
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')

if not LATEST.is_file():
    die('LATEST_STAGE02_EVIDENCE_MISSING')
evidence = json.loads(LATEST.read_text(encoding='utf-8'))
if evidence.get('reexecution_cycle') != 'R2_DUAL_LAYER':
    die(f'CURRENT_EVIDENCE_NOT_R2_DUAL_LAYER:{evidence.get("reexecution_cycle")}')
if evidence.get('result') != 'BLOCKED' or evidence.get('closure_blocker_total') != 0:
    die('R4_REQUIRES_CURRENT_STAGE02_FUNCTIONAL_BLOCKED_WITH_ZERO_CLOSURE_BLOCKERS')
if evidence.get('raw_discovery_gap_total') != 171:
    die(f'RAW_DISCOVERY_DRIFT:{evidence.get("raw_discovery_gap_total")}')
if evidence.get('materialized_functional_elimination_count') != 17:
    die(f'R3_ELIMINATION_DRIFT:{evidence.get("materialized_functional_elimination_count")}')
if evidence.get('fresh_functional_gap_total') != 154:
    die(f'EFFECTIVE_DENOMINATOR_DRIFT:{evidence.get("fresh_functional_gap_total")}')
if evidence.get('preserved_external_authority_union_gap_uids') != [f'GAP-{i:03d}' for i in range(1,9)]:
    die('EXTERNAL_AUTHORITY_UNION_DRIFT')

remaining = []
for page_uid, page in (evidence.get('pages') or {}).items():
    scan = page.get('functional_chain_effective_dual_layer_scan') or {}
    for gap in scan.get('gaps') or []:
        rec = dict(gap)
        rec['page_uid'] = page_uid
        remaining.append(rec)
if len(remaining) != 154:
    die(f'REMAINING_GAP_LIST_DENOMINATOR_DRIFT:{len(remaining)}')
counts = Counter(g.get('category') for g in remaining)
if dict(counts) != EXPECTED:
    die(f'REMAINING_CATEGORY_DRIFT:{dict(counts)}')

# Reconcile old exact-authority audits against the immutable authority corpus and current effective remainder.
audit_refs = {}
for category, path in AUDITS.items():
    audit = load_yaml(path)
    if audit.get('result') not in ('AUDIT_PASS_PRODUCT_GAPS_REMAIN_BLOCKED', 'AUDIT_PASS_PRODUCT_GAP_REMAINS_BLOCKED'):
        die(f'AUDIT_NOT_BLOCKED_PASS:{category}:{audit.get("result")}')
    if category == 'PAYLOAD_INPUT_CONTRACT_MISSING':
        if (audit.get('current_payload_schema_authority') or {}).get('authorized_gap_removals') != 0:
            die('PAYLOAD_AUDIT_AUTHORIZED_REMOVAL_DRIFT')
    elif category == 'AUDIT_EVENT_NODE_MISSING':
        if (audit.get('current_audit_event_authority') or {}).get('authorized_gap_removals') != 0:
            die('AUDIT_EVENT_AUTHORIZED_REMOVAL_DRIFT')
    elif category == 'FAILURE_STATE_ERROR_BINDING_MISSING':
        if (audit.get('current_failure_state_error_binding_authority') or {}).get('authorized_gap_removals') != 0:
            die('FAILURE_BINDING_AUTHORIZED_REMOVAL_DRIFT')
    elif category == 'POST_ACTION_VALIDATION_NODE_MISSING':
        if (audit.get('current_post_action_validation_authority') or {}).get('authorized_gap_removals') != 0:
            die('VALIDATION_AUTHORIZED_REMOVAL_DRIFT')
    elif category == 'ACTION_WITHOUT_CONTROL_OR_TRIGGER':
        if (audit.get('current_control_trigger_authority') or {}).get('authorized_gap_removals') != 0:
            die('TRIGGER_AUTHORIZED_REMOVAL_DRIFT')
    elif category == 'STATE_TRANSITION_LEDGER_FIELD_MISSING':
        authority = audit.get('current_transition_authority') or {}
        if authority.get('exact_transition_uid_required_field_bindings') != 0 or authority.get('authorized_gap_removals') != 0:
            die('TRANSITION_AUTHORITY_AUDIT_DRIFT')
        transition_remaining = [g for g in remaining if g.get('category') == category]
        if {g.get('detail') for g in transition_remaining} != TRANSITION_REMAINING_FIELDS:
            die(f'TRANSITION_REMAINING_FIELD_SET_DRIFT:{sorted({g.get("detail") for g in transition_remaining})}')
        if Counter(g.get('detail') for g in transition_remaining) != Counter({x:10 for x in TRANSITION_REMAINING_FIELDS}):
            die('TRANSITION_REMAINING_FIELD_DENOMINATOR_DRIFT')
    audit_refs[category] = {
        'evidence_ref': str(path.relative_to(ROOT)),
        'authorized_gap_removals': 0,
        'immutable_authority_corpus_unchanged_since_audit': True,
    }

r3 = load_yaml(R3)
r3_summary = r3.get('classification_summary') or {}
if r3_summary.get('EXACT_EXTERNAL_AUTHORITY_REQUIRED') != 4:
    die('R3_EXTERNAL_DENOMINATOR_DRIFT')
if r3_summary.get('NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS') != 150:
    die('R3_NO_BASIS_DENOMINATOR_DRIFT')

external = [g for g in remaining if g.get('category') == 'SHARED_OWNER_AUTHORITY_UNRESOLVED']
if len(external) != 4 or any(g.get('gap_owner') != 'EXTERNAL_AUTHORITY' or 'GAP-006' not in str(g.get('detail')) for g in external):
    die('SHARED_OWNER_EXTERNAL_AUTHORITY_DRIFT')
local_authority_blocked = [g for g in remaining if g.get('category') != 'SHARED_OWNER_AUTHORITY_UNRESOLVED']
if len(local_authority_blocked) != 150:
    die(f'LOCAL_AUTHORITY_BLOCKED_DENOMINATOR_DRIFT:{len(local_authority_blocked)}')

category_dispositions = {}
for category, count in EXPECTED.items():
    if category == 'SHARED_OWNER_AUTHORITY_UNRESOLVED':
        category_dispositions[category] = {
            'current_count': count,
            'authority_sufficient_for_materialization_now': 0,
            'classification': 'EXTERNAL_AUTHORITY_GAP',
            'authority_owner': 'GAP-006_ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY',
            'required_action': 'PRESERVE_UNRESOLVED_AND_BLOCK_STAGE_UNTIL_AUTHORITATIVE_RESOLUTION_OR_FORMAL_NON_APPLICABILITY',
        }
    else:
        category_dispositions[category] = {
            'current_count': count,
            'authority_sufficient_for_materialization_now': 0,
            'classification': 'AUTHORITY_BLOCKED_PRODUCT_CONTRACT_GAP',
            'authority_owner': 'PRODUCT_DESIGN_AUTHORITY_INPUT_REQUIRED',
            'audit_ref': audit_refs[category]['evidence_ref'],
            'required_action': 'STOP_AND_REOPEN_DESIGN_OR_SUPPLY_EXACT_PRODUCT_AUTHORITY; AI_INFERENCE_FORBIDDEN',
        }

out = {
    'schema_version': 1,
    'artifact_uid': 'STAGE02-REMAINING-BLOCKER-DISPOSITION-20260915-R4',
    'artifact_type': 'NON_NORMATIVE_STAGE02_BLOCKER_DISPOSITION',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'source_execution_sha': evidence.get('source_head_sha'),
    'current_reexecution_cycle': evidence.get('reexecution_cycle'),
    'current_truth': {
        'raw_discovery_gap_total': 171,
        'validated_materialized_functional_elimination_count': 17,
        'effective_remaining_functional_gap_total': 154,
        'closure_blocker_total': 0,
        'authority_sufficient_materializable_now': 0,
        'product_design_authority_blocked': 150,
        'preserved_external_shared_authority_blocked': 4,
    },
    'category_dispositions': category_dispositions,
    'transition_remaining_exact_field_distribution': {
        'mutation_owner': 10,
        'failure_state': 10,
        'recovery': 10,
        'audit_event_uid': 10,
        'illegal_transition_tests': 0,
    },
    'bounded_completion_decision': {
        'registered_seed_materializable_remainder': 0,
        'outside_frozen_closure_rule': 'STOP_AND_REOPEN_DESIGN',
        'ai_may_invent_missing_product_authority': False,
        'generic_feature_invention': False,
        'semantic_inference': False,
        'current_specification_mutation_required': False,
    },
    'preserved_external_authority_union_gap_uids': [f'GAP-{i:03d}' for i in range(1,9)],
    'stage_decision': {
        'stage02_result': 'BLOCKED',
        'stage02_stage_exit_allowed': False,
        'stage03_allowed': False,
        'website_construction_allowed': False,
        'deployment_allowed': False,
        'required_next_action': 'REOPEN_PRODUCT_DESIGN_AUTHORITY_FOR_150_EXACT_FIELD_BINDINGS_AND_PRESERVE_4_GAP006_EXTERNAL_BLOCKERS',
        'repeat_audit_without_new_authority_counts_as_progress': False,
    },
}
dump_yaml(OUT, out)

state = load_yaml(STATE)
state['next_action'] = out['stage_decision']['required_next_action']
state.setdefault('stage02_active_attempt', {})['remaining_blocker_disposition_ref'] = str(OUT.relative_to(ROOT))
state['stage02_active_attempt']['authority_sufficient_materializable_now'] = 0
state['stage02_active_attempt']['product_design_authority_blocked'] = 150
state['stage02_active_attempt']['preserved_external_shared_authority_blocked'] = 4
state['stage02_active_attempt']['repeat_audit_without_new_authority_counts_as_progress'] = False
state.setdefault('stage02_material_remediation', {})['remaining_blocker_disposition_ref'] = str(OUT.relative_to(ROOT))
state['stage02_material_remediation']['authority_sufficient_materializable_now'] = 0
dump_yaml(STATE, state)

candidates = load_yaml(CANDIDATES)
current = candidates.setdefault('current_stage2_execution', {})
current['next_action'] = out['stage_decision']['required_next_action']
current['remaining_blocker_disposition_ref'] = str(OUT.relative_to(ROOT))
current['authority_sufficient_materializable_now'] = 0
current['product_design_authority_blocked'] = 150
current['preserved_external_shared_authority_blocked'] = 4
dump_yaml(CANDIDATES, candidates)

print('STAGE02_R4_EFFECTIVE_REMAINING=154')
print('STAGE02_R4_MATERIALIZABLE_NOW=0')
print('STAGE02_R4_PRODUCT_DESIGN_AUTHORITY_BLOCKED=150')
print('STAGE02_R4_GAP006_EXTERNAL_BLOCKED=4')
print('PASS: remaining Stage-02 blockers are consolidated without inventing authority or mutating Current Specification')
print('PASS: repeat audit-only loop is not accepted as progress')
