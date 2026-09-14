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
EVIDENCE = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
OUT = ROOT / 'governance/test/stage02/STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION_R3.yaml'
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
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def nonempty(v) -> bool:
    return v not in (None, '', [], {})


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
    rb = action.get('runtime_binding') or {}
    port_uid = rb.get('port_uid') or rb.get('persist_via_port_uid')
    if not nonempty(port_uid):
        return None
    port = idx['ports'].get(port_uid)
    if not port:
        return None
    return action, rb, port_uid, port


def explicit_event_proof(idx, action_uid):
    action = action_for(idx, action_uid)
    if not action:
        return None
    for field in EXPLICIT_EVENT_FIELDS:
        value = action.get(field)
        if nonempty(value):
            return {'source_node': 'action', 'field': field, 'value': value}
    joined = exact_port_join(idx, action_uid)
    if joined:
        _, _, port_uid, port = joined
        for field in EXPLICIT_EVENT_FIELDS:
            value = port.get(field)
            if nonempty(value):
                return {'source_node': 'integration_port', 'port_uid': port_uid, 'field': field, 'value': value}
    return None


def trigger_proof(idx, action_uid):
    action = action_for(idx, action_uid)
    if not action:
        return None
    for field in TRIGGER_FIELDS:
        value = action.get(field)
        if nonempty(value):
            return {'proof_kind': 'ACTION_EXPLICIT_TRIGGER', 'field': field, 'value': value}
    controls = []
    for ctl in idx['controls'].values():
        if ctl.get('action_uid') == action_uid:
            controls.append(ctl.get('control_uid'))
    if controls:
        return {'proof_kind': 'REGISTERED_CONTROL_ACTION_BINDING', 'control_uids': sorted(controls)}
    transitions = []
    for tr in idx['transitions'].values():
        if tr.get('trigger') == action_uid or tr.get('action_uid') == action_uid:
            transitions.append(tr.get('transition_uid'))
    if transitions:
        return {'proof_kind': 'REGISTERED_TRANSITION_ACTION_TRIGGER', 'transition_uids': sorted(transitions)}
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
    for tr in idx['transitions'].values():
        if tr.get('trigger') == action_uid or tr.get('action_uid') == action_uid:
            if nonempty(tr.get('from_stage')) and nonempty(tr.get('to_stage')):
                transitions.append({
                    'transition_uid': tr.get('transition_uid'),
                    'from_stage': tr.get('from_stage'),
                    'to_stage': tr.get('to_stage'),
                    'trigger': tr.get('trigger') or tr.get('action_uid'),
                    'gate': tr.get('gate_uid') or tr.get('gate'),
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
    tr = idx['transitions'].get(transition_uid)
    if not tr:
        return None
    trigger = tr.get('trigger') or tr.get('action_uid') or tr.get('trigger_event_uid')
    if not (nonempty(tr.get('from_stage')) and nonempty(tr.get('to_stage')) and nonempty(trigger)):
        return None
    return {
        'proof_kind': 'DETERMINISTIC_REQUIRED_DEPENDENCY',
        'transition_uid': transition_uid,
        'from_stage': tr.get('from_stage'),
        'to_stage': tr.get('to_stage'),
        'trigger': trigger,
        'gate': tr.get('gate_uid') or tr.get('gate'),
        'bounded_output': 'GENERATE_NEGATIVE_TESTS_ONLY_NO_STATE_OR_AUTHORITY_VALUE_INVENTION',
    }


def classify(gap, idx):
    category = gap.get('category')
    uid = str(gap.get('uid'))
    detail = str(gap.get('detail') or '')

    if category in EXTERNAL_CATEGORIES or gap.get('gap_owner') == 'EXTERNAL_AUTHORITY':
        return {
            'disposition': 'EXACT_EXTERNAL_AUTHORITY_REQUIRED',
            'completion_basis': 'EXTERNAL_OR_SHARED_AUTHORITY',
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
        # R3 intentionally does not broaden any other category. A value for the exact
        # missing field must be established by a future category-specific proof, not
        # by same-UID proximity or semantic similarity.
        proof = None

    if proof:
        return {
            'disposition': 'BOUNDED_COMPLETION_ADMISSIBLE',
            'completion_basis': basis,
            'authorized_for_auto_completion': True,
            'proof': proof,
        }
    return {
        'disposition': 'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS',
        'completion_basis': 'NO_EXACT_MISSING_FIELD_OR_UNIQUE_DETERMINISTIC_DEPENDENCY',
        'authorized_for_auto_completion': False,
        'proof': None,
    }


if subprocess.run([sys.executable, str(MATERIAL_VALIDATOR)], cwd=str(ROOT), text=True).returncode != 0:
    die('MATERIALIZED_STAGE02_STRUCTURAL_ROOT_INVALID')
if not EVIDENCE.is_file():
    die('CURRENT_STAGE02_EVIDENCE_MISSING')
evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
if evidence.get('result') != 'BLOCKED':
    die(f'CURRENT_STAGE02_RESULT_NOT_BLOCKED:{evidence.get("result")!r}')
if evidence.get('closure_blocker_total') != 0:
    die(f'CLASSIFIER_REQUIRES_STRUCTURAL_BLOCKERS_ZERO:{evidence.get("closure_blocker_total")!r}')
if evidence.get('fresh_functional_gap_total') != 171:
    die(f'CURRENT_FRESH_FUNCTIONAL_DENOMINATOR_DRIFT:{evidence.get("fresh_functional_gap_total")!r}')
if evidence.get('prior_stage2_results_used') is not False or evidence.get('prior_stage2_counts_used_as_scan_input') is not False:
    die('CURRENT_EVIDENCE_NOT_FRESH')

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
        rec.update(classify(gap, idx))
        records.append(rec)

if len(records) != 171:
    die(f'CLASSIFIED_GAP_DENOMINATOR_DRIFT:{len(records)}')
summary = Counter(r['disposition'] for r in records)
basis = Counter(r['completion_basis'] for r in records)
by_category = {}
for category in sorted({r['category'] for r in records}):
    subset = [r for r in records if r['category'] == category]
    by_category[category] = {
        'total': len(subset),
        'BOUNDED_COMPLETION_ADMISSIBLE': sum(r['disposition'] == 'BOUNDED_COMPLETION_ADMISSIBLE' for r in subset),
        'EXACT_EXTERNAL_AUTHORITY_REQUIRED': sum(r['disposition'] == 'EXACT_EXTERNAL_AUTHORITY_REQUIRED' for r in subset),
        'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS': sum(r['disposition'] == 'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS' for r in subset),
    }

head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
out = {
    'schema_version': 1,
    'artifact_type': 'STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'cycle': 'R3_STRICT_CLASSIFICATION',
    'supersedes_for_remediation_decision': 'governance/test/stage02/STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION_R2.yaml',
    'source_head_sha': head,
    'current_fresh_evidence_ref': 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json',
    'fresh_functional_gap_denominator': 171,
    'closure_blocker_denominator': 0,
    'authority_corpus_policy': {
        'immutable_stage1_raw_is_authorization_baseline': True,
        'same_uid_neighboring_field_is_proof': False,
        'semantic_similarity_used': False,
        'sibling_symmetry_used': False,
        'generic_crud_expansion_used': False,
        'external_authority_auto_resolution_used': False,
        'missing_field_specific_proof_required': True,
    },
    'classification_summary': dict(summary),
    'completion_basis_summary': dict(basis),
    'by_category': by_category,
    'records': records,
    'next_action': 'MATERIALIZE_ONLY_R3_BOUNDED_COMPLETION_ADMISSIBLE_RECORDS_WITH_EXACT_PROVENANCE_THEN_DUAL_LAYER_REEXECUTION',
    'stage03_allowed': False,
}
OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')
print('STAGE02_R3_REMEDIABILITY_TOTAL=171')
for key in ('BOUNDED_COMPLETION_ADMISSIBLE', 'EXACT_EXTERNAL_AUTHORITY_REQUIRED', 'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS'):
    print(f'{key}={summary.get(key, 0)}')
for category, counts in by_category.items():
    print(f'CATEGORY::{category}::{counts}')
print('PASS: R3 requires missing-field-specific or exact deterministic UID-join proof')
print('PASS: no same-UID neighboring-field admission remains')
