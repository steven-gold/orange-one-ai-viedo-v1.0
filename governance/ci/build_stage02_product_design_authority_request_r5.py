#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
LATEST = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
R4 = ROOT / 'governance/test/stage02/STAGE02_REMAINING_BLOCKER_DISPOSITION_R4.yaml'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
CANDIDATES = ROOT / 'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
OUT = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_REQUEST_R5.yaml'
ASSET_RAW = ROOT / '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'

EXPECTED = {
    'PAYLOAD_INPUT_CONTRACT_MISSING': 34,
    'AUDIT_EVENT_NODE_MISSING': 13,
    'FAILURE_STATE_ERROR_BINDING_MISSING': 44,
    'POST_ACTION_VALIDATION_NODE_MISSING': 18,
    'ACTION_WITHOUT_CONTROL_OR_TRIGGER': 1,
    'STATE_TRANSITION_LEDGER_FIELD_MISSING': 40,
    'SHARED_OWNER_AUTHORITY_UNRESOLVED': 4,
}
LOCAL_CATEGORIES = set(EXPECTED) - {'SHARED_OWNER_AUTHORITY_UNRESOLVED'}


def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path):
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def dump_yaml(path: Path, obj) -> None:
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')


def nonempty(v) -> bool:
    return v not in (None, '', [], {})


def action_index(raw: dict) -> dict:
    actions = ((raw.get('registries') or {}).get('actions') or [])
    out = {}
    for a in actions:
        if isinstance(a, dict) and nonempty(a.get('action_uid')):
            out[a['action_uid']] = a
    return out


def local_authority_requirement(category: str, detail: str | None) -> dict:
    if category == 'PAYLOAD_INPUT_CONTRACT_MISSING':
        return {
            'required_authority_kind': 'EXACT_PAYLOAD_OR_INPUT_SCHEMA_BINDING',
            'required_exact_fields_or_relation': [
                'explicit action payload/input/request schema OR exact runtime/port payload/input/request schema bound to the same action_uid',
            ],
            'not_acceptable_as_authority': ['operation name', 'route identity', 'port identity alone', 'semantic similarity', 'AI-inferred request fields'],
        }
    if category == 'AUDIT_EVENT_NODE_MISSING':
        return {
            'required_authority_kind': 'EXACT_REGISTERED_AUDIT_EVENT_BINDING',
            'required_exact_fields_or_relation': [
                'exact event_uid/audit_event_uid bound to the same action or exact resolved port and present in the same-page event registry',
            ],
            'not_acceptable_as_authority': ['state text', 'trigger text', 'semantic event guess', 'invented event UID'],
        }
    if category == 'FAILURE_STATE_ERROR_BINDING_MISSING':
        return {
            'required_authority_kind': 'EXACT_FAILURE_ERROR_RECOVERY_BINDING',
            'required_exact_fields_or_relation': [
                'same action_uid explicitly binds failure_state + recovery',
                'OR same action_uid explicitly binds a registered error_uid whose same-page error entry supplies recovery',
            ],
            'not_acceptable_as_authority': ['generic page error registry', 'nearest error by meaning', 'AI-selected recovery'],
        }
    if category == 'POST_ACTION_VALIDATION_NODE_MISSING':
        return {
            'required_authority_kind': 'EXACT_POST_ACTION_VALIDATION_BINDING',
            'required_exact_fields_or_relation': [
                'same action_uid has success_contract/validation_contract/validator_uid',
                'OR exact runtime binding has validation/validation_rule/evaluation_rule',
                'OR exact resolved port has validation/validation_rule/validator_uid',
            ],
            'not_acceptable_as_authority': ['operation response label', 'route response wording', 'gate similarity', 'AI-generated validator'],
        }
    if category == 'ACTION_WITHOUT_CONTROL_OR_TRIGGER':
        return {
            'required_authority_kind': 'EXACT_ACTION_ADMISSION_TRIGGER_RELATION',
            'required_exact_fields_or_relation': [
                'registered control.action_uid equals this action_uid',
                'OR exact stage transition trigger/action_uid equals this action_uid',
                'OR action has explicit trigger_event_uid/trigger_uid/invocation/system_trigger/trigger_kind',
            ],
            'not_acceptable_as_authority': ['neighboring control', 'label similarity', 'route identity', 'inferred system trigger'],
        }
    if category == 'STATE_TRANSITION_LEDGER_FIELD_MISSING':
        if detail not in {'mutation_owner', 'failure_state', 'recovery', 'audit_event_uid'}:
            die(f'UNEXPECTED_REMAINING_TRANSITION_FIELD:{detail}')
        return {
            'required_authority_kind': 'EXACT_TRANSITION_FIELD_BINDING',
            'required_exact_fields_or_relation': [f'exact non-empty {detail} value bound to the same transition_uid'],
            'not_acceptable_as_authority': ['trigger/gate/action/error/owner similarity', 'value copied from sibling transition', 'AI-inferred value'],
        }
    die(f'UNSUPPORTED_LOCAL_CATEGORY:{category}')


evidence = json.loads(LATEST.read_text(encoding='utf-8')) if LATEST.is_file() else die('LATEST_MISSING')
r4 = load_yaml(R4)
if evidence.get('result') != 'BLOCKED' or evidence.get('fresh_functional_gap_total') != 154:
    die('R5_REQUIRES_CURRENT_FRESH_BLOCKED_154')
if evidence.get('closure_blocker_total') != 0:
    die('R5_REQUIRES_ZERO_CLOSURE_BLOCKERS')
truth = r4.get('current_truth') or {}
if truth.get('effective_remaining_functional_gap_total') != 154 or truth.get('authority_sufficient_materializable_now') != 0:
    die('R4_CURRENT_TRUTH_DRIFT')
if truth.get('product_design_authority_blocked') != 150 or truth.get('preserved_external_shared_authority_blocked') != 4:
    die('R4_BLOCKER_DENOMINATOR_DRIFT')

remaining = []
for page_uid, page in (evidence.get('pages') or {}).items():
    scan = page.get('functional_chain_effective_dual_layer_scan') or {}
    for gap in scan.get('gaps') or []:
        rec = dict(gap)
        rec['page_uid'] = page_uid
        remaining.append(rec)
if len(remaining) != 154:
    die(f'REMAINING_LIST_NOT_154:{len(remaining)}')
counts = Counter(g.get('category') for g in remaining)
if dict(counts) != EXPECTED:
    die(f'CATEGORY_DRIFT:{dict(counts)}')

asset_actions = action_index(load_yaml(ASSET_RAW))
completed_gates = [
    'EXACT_75_FILE_GOVERNANCE_SOURCE_IDENTITY_PASS',
    'CURRENT_SPECIFICATION_FREEZE_PASS',
    'STAGE01_CLOSURE_CONTINUITY_PASS',
    'STAGE02_STRUCTURAL_CLOSURE_BLOCKERS_13_TO_0_FRESH_PROVEN',
    'R3_BOUNDED_FUNCTIONAL_MATERIALIZATION_17_OF_17_VALIDATED',
    'FULL_LINE_MULTIDIRECTIONAL_HIGH_PRESSURE_SYSTEM_GATE_PASS_BEFORE_R2_REEXECUTION',
    'R2_DUAL_LAYER_FRESH_REEXECUTION_RAW_171_EFFECTIVE_154_PASS',
    'R4_REMAINING_BLOCKER_DISPOSITION_PASS',
]
resume_point = 'AFTER_APPROVED_AUTHORITY_INGESTION_RESET_EXECUTION_OUTPUTS_TO_SAME_STAGE01_BASELINE_THEN_FULL_LINE_SYSTEM_GATE_THEN_FRESH_STAGE02_REEXECUTION'

local_requests = []
external_requests = []
seq_local = 0
seq_external = 0
for gap in remaining:
    category = gap.get('category')
    page_uid = gap.get('page_uid')
    target_uid = str(gap.get('uid'))
    detail = gap.get('detail')
    if category in LOCAL_CATEGORIES:
        seq_local += 1
        req = local_authority_requirement(category, detail)
        local_requests.append({
            'blocker_uid': f'STAGE02-R5-PRODUCT-AUTH-{seq_local:03d}',
            'scope': page_uid,
            'severity': 'STAGE_EXIT_BLOCKING',
            'category': category,
            'target_uid': target_uid,
            'missing_field_or_relation': detail,
            'reason': 'CURRENT_FROZEN_PRODUCT_AUTHORITY_HAS_NO_EXACT_ADMISSIBLE_BINDING_FOR_THIS_REQUIRED_STAGE02_CONTRACT_ELEMENT',
            'impact': 'STAGE02_CANNOT_CLOSE_AND_STAGE03_CONSTRUCTION_AND_DEPLOYMENT_REMAIN_FAIL_CLOSED',
            'authority_request': req,
            'unlock_condition': 'APPROVED_PRODUCT_DESIGN_AUTHORITY_PROVIDES_THE_REQUIRED_EXACT_BINDING_AND_CATEGORY_SPECIFIC_VALIDATOR_ACCEPTS_IT_WITHOUT_INFERENCE',
            'completed_gates': completed_gates,
            'missing_gates': [
                'APPROVED_EXACT_PRODUCT_DESIGN_AUTHORITY_BINDING',
                'CATEGORY_SPECIFIC_EXACT_AUTHORITY_VALIDATION_PASS',
                'CLEAN_STAGE02_REEXECUTION_KNOWN_SIGNATURE_ZERO_FOR_THIS_BLOCKER',
            ],
            'exact_resume_point': resume_point,
            'authority_value_supplied_by_ai': False,
            'request_is_authority': False,
        })
    elif category == 'SHARED_OWNER_AUTHORITY_UNRESOLVED':
        seq_external += 1
        action = asset_actions.get(target_uid) or {}
        rb = action.get('runtime_binding') or {}
        shared_authority_id = rb.get('shared_authority_id')
        shared_operation_id = rb.get('shared_operation_id')
        if shared_authority_id != 'ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or not nonempty(shared_operation_id):
            die(f'GAP006_SHARED_REFERENCE_INCOMPLETE:{target_uid}:{shared_authority_id}:{shared_operation_id}')
        external_requests.append({
            'blocker_uid': f'STAGE02-R5-EXTERNAL-AUTH-{seq_external:03d}',
            'scope': page_uid,
            'severity': 'STAGE_EXIT_BLOCKING',
            'category': category,
            'target_uid': target_uid,
            'gap_uid': 'GAP-006',
            'shared_authority_id': shared_authority_id,
            'shared_operation_id': shared_operation_id,
            'reason': 'EXACT_SHARED_OWNER_AUTHORITY_IS_REFERENCED_BUT_NOT_CAPTURED_IN_CURRENT_AUTHORITY_SET',
            'impact': 'SHARED_OPERATION_OWNER_CANNOT_BE_RESOLVED_AND_STAGE02_REMAINS_BLOCKED',
            'unlock_condition': 'AUTHORITATIVE_GAP006_SOURCE_IS_PROVIDED_AND_EXACTLY_RESOLVES_THIS_SHARED_OPERATION_OR_FORMAL_NON_APPLICABILITY_IS_AUTHORIZED',
            'completed_gates': completed_gates,
            'missing_gates': [
                'GAP006_AUTHORITATIVE_SOURCE_RESOLUTION_OR_FORMAL_NON_APPLICABILITY',
                'SHARED_OWNER_EXACT_RESOLUTION_VALIDATION_PASS',
                'CLEAN_STAGE02_REEXECUTION_KNOWN_SIGNATURE_ZERO_FOR_THIS_BLOCKER',
            ],
            'exact_resume_point': resume_point,
            'authority_value_supplied_by_ai': False,
            'request_is_authority': False,
        })
    else:
        die(f'UNEXPECTED_CATEGORY:{category}')

if len(local_requests) != 150 or len(external_requests) != 4:
    die(f'REQUEST_DENOMINATOR_DRIFT:local={len(local_requests)} external={len(external_requests)}')
if len({r['blocker_uid'] for r in local_requests + external_requests}) != 154:
    die('DUPLICATE_BLOCKER_UID')
if len({(r['scope'], r['category'], r['target_uid'], r.get('missing_field_or_relation')) for r in local_requests}) != 150:
    die('DUPLICATE_LOCAL_REQUEST_SIGNATURE')

out = {
    'schema_version': 1,
    'artifact_uid': 'STAGE02-PRODUCT-DESIGN-AUTHORITY-REQUEST-20260915-R5',
    'artifact_type': 'NON_NORMATIVE_AUTHORITY_REQUEST_AND_BLOCKER_PACKAGE',
    'normative_authority': False,
    'request_is_product_authority': False,
    'stage_uid': 'STAGE-02',
    'current_frozen_governance_uid': evidence.get('frozen_governance_uid'),
    'source_execution_sha': evidence.get('source_head_sha'),
    'source_evidence_ref': 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json',
    'source_disposition_ref': 'governance/test/stage02/STAGE02_REMAINING_BLOCKER_DISPOSITION_R4.yaml',
    'purpose': 'REQUEST_ONLY_THE_EXACT_MISSING_PRODUCT_OR_EXTERNAL_AUTHORITY_NEEDED_TO_RESUME_STAGE02_WITHOUT_AI_INVENTION',
    'safety': {
        'contains_product_authority_values': False,
        'may_be_used_as_authority_input': False,
        'may_auto_resolve_any_blocker': False,
        'current_specification_mutated': False,
        'stage1_immutable_source_mutated': False,
        'stage2_stage_exit_claimed': False,
        'stage3_allowed': False,
        'website_construction_allowed': False,
        'deployment_allowed': False,
    },
    'denominators': {
        'current_effective_blockers': 154,
        'product_design_authority_requests': 150,
        'gap006_external_authority_requests': 4,
        'materializable_from_current_authority_now': 0,
    },
    'category_counts': dict(counts),
    'product_design_authority_requests': local_requests,
    'gap006_external_authority_requests': external_requests,
    'intake_rule': {
        'approved_authority_must_be_new_explicit_input': True,
        'request_package_itself_is_not_authority': True,
        'do_not_rewrite_historical_stage1_authority': True,
        'do_not_mutate_current_governance_specification_for_product_values': True,
        'after_authority_arrival': [
            'VALIDATE_EXACT_UID_FIELD_RELATIONS',
            'BIND_APPROVED_AUTHORITY_AS_AUTHORIZED_STAGE02_REOPEN_INPUT_WITH_PROVENANCE',
            'RESET_STAGE02_EXECUTION_OUTPUT_AND_RUNTIME_EVIDENCE_TO_SAME_STAGE01_BASELINE_WHILE_PRESERVING_AUTHORIZED_FIXES',
            'RUN_FULL_LINE_MULTIDIRECTIONAL_HIGH_PRESSURE_SYSTEM_GATE',
            'RUN_FRESH_STAGE02_REEXECUTION',
            'REQUIRE_KNOWN_DEFECT_ZERO_REPRODUCTION_BEFORE_HIDDEN_SWEEP',
        ],
    },
    'exact_resume_point': resume_point,
    'status': 'OPEN_AWAITING_150_PRODUCT_DESIGN_AUTHORITY_BINDINGS_AND_4_GAP006_EXTERNAL_AUTHORITY_RESOLUTIONS',
}
dump_yaml(OUT, out)

state = load_yaml(STATE)
state['next_action'] = 'AWAIT_OR_INGEST_APPROVED_STAGE02_PRODUCT_DESIGN_AUTHORITY_REQUEST_R5_INPUTS; DO_NOT_REPEAT_AUDIT_WITHOUT_NEW_AUTHORITY'
attempt = state.setdefault('stage02_active_attempt', {})
attempt['authority_request_package_ref'] = str(OUT.relative_to(ROOT))
attempt['authority_request_product_count'] = 150
attempt['authority_request_gap006_external_count'] = 4
attempt['authority_request_is_authority'] = False
attempt['exact_resume_point'] = resume_point
attempt['new_authority_required_before_more_material_remediation'] = True
dump_yaml(STATE, state)

candidates = load_yaml(CANDIDATES)
current = candidates.setdefault('current_stage2_execution', {})
current['next_action'] = state['next_action']
current['authority_request_package_ref'] = str(OUT.relative_to(ROOT))
current['authority_request_product_count'] = 150
current['authority_request_gap006_external_count'] = 4
current['authority_request_is_authority'] = False
dump_yaml(CANDIDATES, candidates)

print('STAGE02_R5_PRODUCT_AUTHORITY_REQUESTS=150')
print('STAGE02_R5_GAP006_EXTERNAL_REQUESTS=4')
print('STAGE02_R5_MATERIALIZABLE_NOW=0')
print('PASS: authority request package contains no invented product authority values')
print('PASS: every blocker has reason, impact, unlock condition, completed gates, missing gates, and exact resume point')
print('PASS: historical Stage-01 and Current Specification remain immutable')
