#!/usr/bin/env python3
from __future__ import annotations

import sys

EXTERNAL_CATEGORIES = {'SHARED_OWNER_AUTHORITY_UNRESOLVED'}
TRIGGER_FIELDS = ('trigger_event_uid', 'trigger_uid', 'invocation', 'system_trigger', 'trigger_kind')
EXPLICIT_EVENT_FIELDS = ('audit_event_uid', 'event_uid')


def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


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
    controls = [ctl.get('control_uid') for ctl in idx['controls'].values() if ctl.get('action_uid') == action_uid]
    if controls:
        return {'proof_kind': 'REGISTERED_CONTROL_ACTION_BINDING', 'control_uids': sorted(controls)}
    transitions = [
        tr.get('transition_uid') for tr in idx['transitions'].values()
        if tr.get('trigger') == action_uid or tr.get('action_uid') == action_uid
    ]
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


def main() -> int:
    print('PASS: bounded functional-remediability classifier guard loaded')
    print('PASS: no product run root, product blob, workflow identity, or fixed denominator is owned by this guard')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
