#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
CONTRACT_ROOT = RUN / '04_PAGE_FUNCTIONAL_CONTRACT'
EVIDENCE = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
PROBLEM_REGISTER = CONTRACT_ROOT / 'CURRENT_PROBLEM_REGISTER.yaml'
DENOMINATOR = CONTRACT_ROOT / 'DENOMINATOR_SNAPSHOT.yaml'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
REGISTRY = ROOT / 'governance/specifications/REGISTRY.yaml'
OUT = ROOT / 'governance/test/stage02/STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION_R2.yaml'
MATERIAL_VALIDATOR = ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py'

PAGES = {
    'CORE-01': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
    'ASSET-01': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
}
EXTERNAL_CATEGORIES = {'SHARED_OWNER_AUTHORITY_UNRESOLVED'}
TRIGGER_FIELDS = ('trigger_event_uid', 'trigger_uid', 'invocation', 'system_trigger', 'trigger_kind')
EXPLICIT_EVENT_FIELDS = ('audit_event_uid', 'event_uid')


def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path):
    if not path.is_file():
        die(f'MISSING_INPUT:{path.relative_to(ROOT)}')
    try:
        obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception as exc:
        die(f'YAML_PARSE:{path.relative_to(ROOT)}:{exc!r}')
    if not isinstance(obj, dict):
        die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj


def nonempty(value) -> bool:
    return value not in (None, '', [], {})


def index_by(items, key):
    out = {}
    for item in items or []:
        if isinstance(item, dict) and nonempty(item.get(key)):
            if item[key] in out:
                die(f'DUPLICATE_UID:{key}:{item[key]}')
            out[item[key]] = item
    return out


def page_indexes(raw: dict):
    regs = raw.get('registries') or {}
    return {
        'actions': index_by(regs.get('actions'), 'action_uid'),
        'controls': index_by(regs.get('controls'), 'control_uid'),
        'ports': index_by(regs.get('integration_ports'), 'port_uid'),
        'transitions': index_by(regs.get('stage_transitions'), 'transition_uid'),
        'events': index_by(regs.get('events'), 'event_uid'),
    }


def action_for(idx, uid):
    return idx['actions'].get(uid)


def exact_port_join(idx, action_uid):
    action = action_for(idx, action_uid)
    if not action:
        return None
    runtime_binding = action.get('runtime_binding') or {}
    port_uid = runtime_binding.get('port_uid') or runtime_binding.get('persist_via_port_uid')
    if not nonempty(port_uid):
        return None
    port = idx['ports'].get(port_uid)
    if not port:
        return None
    return action, runtime_binding, port_uid, port


def explicit_event_proof(idx, action_uid):
    action = action_for(idx, action_uid)
    if not action:
        return None
    for field in EXPLICIT_EVENT_FIELDS:
        value = action.get(field)
        if nonempty(value):
            return {
                'proof_kind': 'ACTION_EXPLICIT_AUDIT_EVENT',
                'source_node': 'action',
                'field': field,
                'value': value,
            }
    joined = exact_port_join(idx, action_uid)
    if joined:
        _, _, port_uid, port = joined
        for field in EXPLICIT_EVENT_FIELDS:
            value = port.get(field)
            if nonempty(value):
                return {
                    'proof_kind': 'EXACT_ACTION_PORT_AUDIT_EVENT_JOIN',
                    'source_node': 'integration_port',
                    'port_uid': port_uid,
                    'field': field,
                    'value': value,
                }
    return None


def trigger_proof(idx, action_uid):
    action = action_for(idx, action_uid)
    if not action:
        return None
    for field in TRIGGER_FIELDS:
        value = action.get(field)
        if nonempty(value):
            return {
                'proof_kind': 'ACTION_EXPLICIT_TRIGGER',
                'field': field,
                'value': value,
            }
    controls = []
    for control in idx['controls'].values():
        if control.get('action_uid') == action_uid:
            controls.append(control.get('control_uid'))
    if controls:
        return {
            'proof_kind': 'REGISTERED_CONTROL_ACTION_BINDING',
            'control_uids': sorted(controls),
        }
    transitions = []
    for transition in idx['transitions'].values():
        if transition.get('trigger') == action_uid or transition.get('action_uid') == action_uid:
            transitions.append(transition.get('transition_uid'))
    if transitions:
        return {
            'proof_kind': 'REGISTERED_TRANSITION_ACTION_TRIGGER',
            'transition_uids': sorted(transitions),
        }
    return None


def success_next_state_proof(idx, action_uid):
    action = action_for(idx, action_uid)
    if not action:
        return None
    if nonempty(action.get('state_effect')):
        return {
            'proof_kind': 'ACTION_EXPLICIT_STATE_EFFECT',
            'state_effect': action.get('state_effect'),
            'bounded_output': 'COPY_EXACT_STATE_EFFECT_ONLY',
        }
    transitions = []
    for transition in idx['transitions'].values():
        if transition.get('trigger') == action_uid or transition.get('action_uid') == action_uid:
            if nonempty(transition.get('from_stage')) and nonempty(transition.get('to_stage')):
                transitions.append({
                    'transition_uid': transition.get('transition_uid'),
                    'from_stage': transition.get('from_stage'),
                    'to_stage': transition.get('to_stage'),
                    'trigger': transition.get('trigger') or transition.get('action_uid'),
                    'gate': transition.get('gate_uid') or transition.get('gate'),
                })
    if len(transitions) == 1:
        return {
            'proof_kind': 'EXACT_TRANSITION_TRIGGERED_BY_ACTION',
            'transition': transitions[0],
            'bounded_output': 'COPY_EXACT_TRANSITION_EFFECT_ONLY',
        }
    joined = exact_port_join(idx, action_uid)
    if joined:
        _, _, port_uid, port = joined
        state_event = port.get('state_event')
        if nonempty(state_event):
            return {
                'proof_kind': 'DETERMINISTIC_ACTION_PORT_STATE_EFFECT_PROJECTION',
                'port_uid': port_uid,
                'state_event': state_event,
                'bounded_output': 'COPY_EXACT_PORT_STATE_EVENT_AS_SUCCESS_STATE_EFFECT_ONLY',
            }
    return None


def negative_transition_test_proof(idx, transition_uid):
    transition = idx['transitions'].get(transition_uid)
    if not transition:
        return None
    trigger = transition.get('trigger') or transition.get('action_uid') or transition.get('trigger_event_uid')
    if not (
        nonempty(transition.get('from_stage'))
        and nonempty(transition.get('to_stage'))
        and nonempty(trigger)
    ):
        return None
    return {
        'proof_kind': 'DETERMINISTIC_REQUIRED_DEPENDENCY',
        'transition_uid': transition_uid,
        'from_stage': transition.get('from_stage'),
        'to_stage': transition.get('to_stage'),
        'trigger': trigger,
        'gate': transition.get('gate_uid') or transition.get('gate'),
        'bounded_output': 'GENERATE_NEGATIVE_TESTS_ONLY_NO_STATE_OR_AUTHORITY_VALUE_INVENTION',
    }


def classify_gap(gap: dict, idx):
    category = gap.get('category')
    uid = str(gap.get('uid'))
    detail = str(gap.get('detail') or '')

    if category in EXTERNAL_CATEGORIES or gap.get('gap_owner') == 'EXTERNAL_AUTHORITY':
        return {
            'disposition': 'EXACT_EXTERNAL_AUTHORITY_REQUIRED',
            'completion_basis': 'EXTERNAL_OR_SHARED_AUTHORITY',
            'candidate_evidence': [],
            'authorized_for_auto_completion': False,
            'proof': None,
        }

    proof = None
    basis = None
    if category == 'STATE_TRANSITION_LEDGER_FIELD_MISSING' and detail == 'illegal_transition_tests':
        proof = negative_transition_test_proof(idx, uid)
        basis = 'DETERMINISTIC_REQUIRED_DEPENDENCY'
    elif category == 'AUDIT_EVENT_NODE_MISSING':
        proof = explicit_event_proof(idx, uid)
        basis = 'EXACT_MISSING_FIELD_AUTHORITY'
    elif category == 'ACTION_WITHOUT_CONTROL_OR_TRIGGER':
        proof = trigger_proof(idx, uid)
        basis = 'EXACT_REGISTERED_TRIGGER_RELATION'
    elif category == 'SUCCESS_NEXT_STATE_BINDING_MISSING':
        proof = success_next_state_proof(idx, uid)
        basis = proof.get('proof_kind') if proof else None
    else:
        # Never admit a category merely because another field on a node carries the
        # same UID. Unknown categories remain blocked until a missing-field-specific
        # proof is implemented and validated.
        proof = None

    if proof:
        return {
            'disposition': 'BOUNDED_COMPLETION_ADMISSIBLE',
            'completion_basis': basis,
            'candidate_evidence': [proof],
            'authorized_for_auto_completion': True,
            'proof': proof,
        }
    return {
        'disposition': 'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS',
        'completion_basis': 'NO_EXACT_MISSING_FIELD_OR_UNIQUE_DETERMINISTIC_DEPENDENCY',
        'candidate_evidence': [],
        'authorized_for_auto_completion': False,
        'proof': None,
    }


def evidence_gap_rows(evidence: dict):
    rows = []
    for page_uid in sorted(PAGES):
        scan = (((evidence.get('pages') or {}).get(page_uid) or {}).get('functional_chain_fresh_scan') or {})
        gaps = scan.get('gaps') or []
        if int(scan.get('gap_count') or 0) != len(gaps):
            die(f'PAGE_GAP_COUNT_DRIFT:{page_uid}')
        for gap in gaps:
            rows.append((
                page_uid,
                gap.get('uid'),
                gap.get('category'),
                gap.get('class'),
                gap.get('detail'),
                gap.get('gap_owner'),
            ))
    return rows


def problem_rows(problem: dict):
    rows = []
    for item in problem.get('problems') or []:
        rows.append((
            item.get('page_uid'),
            item.get('target_uid'),
            item.get('category'),
            item.get('gap_class'),
            item.get('detail'),
            item.get('gap_owner'),
        ))
    return rows


if subprocess.run([sys.executable, str(MATERIAL_VALIDATOR)], cwd=str(ROOT), text=True).returncode != 0:
    die('MATERIALIZED_STAGE02_STRUCTURAL_ROOT_INVALID')
if not EVIDENCE.is_file():
    die('CURRENT_STAGE02_EVIDENCE_MISSING')
evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
state = load_yaml(STATE)
registry = load_yaml(REGISTRY)
problem = load_yaml(PROBLEM_REGISTER)
denominator = load_yaml(DENOMINATOR)
active = state.get('stage02_active_attempt') or {}
current_governance_uid = (registry.get('active_specification') or {}).get('governance_uid')
attempt_uid = active.get('attempt_uid')

if evidence.get('result') != 'BLOCKED':
    die(f'CURRENT_STAGE02_RESULT_NOT_BLOCKED:{evidence.get("result")!r}')
if evidence.get('closure_blocker_total') != 0:
    die(f'CLASSIFIER_REQUIRES_STRUCTURAL_BLOCKERS_ZERO:{evidence.get("closure_blocker_total")!r}')
if evidence.get('prior_stage2_results_used') is not False or evidence.get('prior_stage2_counts_used_as_scan_input') is not False:
    die('CURRENT_EVIDENCE_NOT_FRESH')
if not current_governance_uid or state.get('specification_uid') != current_governance_uid:
    die('CURRENT_GOVERNANCE_UID_DRIFT')
if active.get('frozen_governance_uid') != current_governance_uid or evidence.get('frozen_governance_uid') != current_governance_uid:
    die('CURRENT_EVIDENCE_GOVERNANCE_UID_DRIFT')
if not attempt_uid or evidence.get('attempt_uid') != attempt_uid:
    die('CURRENT_ATTEMPT_UID_DRIFT')

current_denominator = int(evidence.get('fresh_functional_gap_total') or 0)
if current_denominator <= 0:
    die(f'CURRENT_FRESH_FUNCTIONAL_DENOMINATOR_INVALID:{current_denominator}')
if problem.get('current_governance_uid') != current_governance_uid or problem.get('attempt_uid') != attempt_uid:
    die('CURRENT_PROBLEM_REGISTER_IDENTITY_DRIFT')
if denominator.get('current_governance_uid') != current_governance_uid or denominator.get('attempt_uid') != attempt_uid:
    die('CURRENT_DENOMINATOR_SNAPSHOT_IDENTITY_DRIFT')
if int(problem.get('fresh_physical_problem_count') or 0) != current_denominator:
    die('CURRENT_PROBLEM_REGISTER_DENOMINATOR_DRIFT')
if int(problem.get('open_problem_count') or 0) != current_denominator or int(problem.get('resolved_problem_count') or 0) != 0:
    die('CURRENT_PROBLEM_REGISTER_OPEN_RESOLVED_DRIFT')
if len(problem.get('problems') or []) != current_denominator:
    die('CURRENT_PROBLEM_REGISTER_ROW_COUNT_DRIFT')
if int(denominator.get('fresh_functional_gap_total') or 0) != current_denominator:
    die('CURRENT_DENOMINATOR_SNAPSHOT_COUNT_DRIFT')
if denominator.get('hardcoded_or_historical_denominator_used') is not False:
    die('CURRENT_DENOMINATOR_SNAPSHOT_MUST_BE_PHYSICAL')

evidence_rows = evidence_gap_rows(evidence)
if len(evidence_rows) != current_denominator:
    die(f'CURRENT_EVIDENCE_ROW_COUNT_DRIFT:{len(evidence_rows)}:{current_denominator}')
if sorted(evidence_rows, key=lambda x: tuple(str(v) for v in x)) != sorted(problem_rows(problem), key=lambda x: tuple(str(v) for v in x)):
    die('CURRENT_PROBLEM_REGISTER_NOT_EXACT_EVIDENCE_PROJECTION')

records = []
for page_uid, raw_path in PAGES.items():
    raw = load_yaml(raw_path)
    idx = page_indexes(raw)
    page_gaps = (((evidence.get('pages') or {}).get(page_uid) or {}).get('functional_chain_fresh_scan') or {}).get('gaps') or []
    for gap in page_gaps:
        rec = {
            'page_uid': page_uid,
            'class': gap.get('class'),
            'category': gap.get('category'),
            'uid': gap.get('uid'),
            'detail': gap.get('detail'),
            'gap_owner': gap.get('gap_owner'),
        }
        rec.update(classify_gap(gap, idx))
        records.append(rec)

if len(records) != current_denominator:
    die(f'CLASSIFIED_GAP_DENOMINATOR_DRIFT:{len(records)}:{current_denominator}')
summary = Counter(record['disposition'] for record in records)
basis = Counter(record['completion_basis'] for record in records)
by_category = {}
for category in sorted({record['category'] for record in records}):
    subset = [record for record in records if record['category'] == category]
    by_category[category] = {
        'total': len(subset),
        'BOUNDED_COMPLETION_ADMISSIBLE': sum(record['disposition'] == 'BOUNDED_COMPLETION_ADMISSIBLE' for record in subset),
        'EXACT_EXTERNAL_AUTHORITY_REQUIRED': sum(record['disposition'] == 'EXACT_EXTERNAL_AUTHORITY_REQUIRED' for record in subset),
        'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS': sum(record['disposition'] == 'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS' for record in subset),
    }

head = subprocess.run(
    ['git', 'rev-parse', 'HEAD'],
    cwd=str(ROOT),
    text=True,
    capture_output=True,
    check=True,
).stdout.strip()
out = {
    'schema_version': 3,
    'artifact_type': 'STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'cycle': 'R2_CLASSIFICATION',
    'source_head_sha': head,
    'current_governance_uid': current_governance_uid,
    'attempt_uid': attempt_uid,
    'current_fresh_evidence_ref': 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json',
    'current_problem_register_ref': '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/CURRENT_PROBLEM_REGISTER.yaml',
    'denominator_snapshot_ref': '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/DENOMINATOR_SNAPSHOT.yaml',
    'fresh_functional_gap_denominator': current_denominator,
    'closure_blocker_denominator': 0,
    'denominator_source': 'CURRENT_PHYSICAL_EVIDENCE_PROBLEM_REGISTER_AND_DENOMINATOR_SNAPSHOT_EXACT_AGREEMENT',
    'hardcoded_historical_denominator_used': False,
    'authority_corpus_policy': {
        'official_stage2_inputs_only': True,
        'immutable_stage1_raw_is_authorization_baseline': True,
        'stage2_current_product_output_may_self_authorize_completion': False,
        'same_uid_neighboring_field_is_proof': False,
        'missing_field_specific_proof_required': True,
        'semantic_similarity_used': False,
        'sibling_symmetry_used': False,
        'generic_crud_expansion_used': False,
        'external_authority_auto_resolution_used': False,
    },
    'classification_summary': dict(summary),
    'completion_basis_summary': dict(basis),
    'by_category': by_category,
    'records': records,
    'next_action': 'MATERIALIZE_ONLY_BOUNDED_COMPLETION_ADMISSIBLE_RECORDS_THEN_DUAL_LAYER_REEXECUTION',
    'stage03_allowed': False,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(
    yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=180),
    encoding='utf-8',
)
print(f'STAGE02_REMEDIABILITY_TOTAL={current_denominator}')
for key in (
    'BOUNDED_COMPLETION_ADMISSIBLE',
    'EXACT_EXTERNAL_AUTHORITY_REQUIRED',
    'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS',
):
    print(f'{key}={summary.get(key, 0)}')
for category, counts in by_category.items():
    print(f'CATEGORY::{category}::{counts}')
print('PASS: every current fresh Stage-02 functional gap classified against the Current physical denominator')
print('PASS: denominator is derived from exact agreement of fresh evidence, Current Problem Register, and Denominator Snapshot')
print('PASS: classifier requires missing-field-specific or exact deterministic UID-join proof')
print('PASS: no same-UID neighboring-field admission remains')
print('PASS: Stage-02 product output was not used to self-authorize completion')
