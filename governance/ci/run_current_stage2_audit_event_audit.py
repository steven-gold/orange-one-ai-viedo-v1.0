#!/usr/bin/env python3
from __future__ import annotations
from collections import Counter, defaultdict
import json
import re
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
EVIDENCE = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
OUT = ROOT / '.github/stage02-audit-event/AUDIT_EVENT_CURRENT_AUTHORITY_AUDIT.json'
PAGES = {
    'CORE-01': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
    'ASSET-01': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
}
EXPECTED_COUNTS = {'CORE-01': 4, 'ASSET-01': 9}
PORT_FIELDS = ('port_uid', 'persist_via_port_uid', 'execute_port_uid', 'decision_port_uid')


def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path):
    try:
        obj = yaml.safe_load(path.read_text(encoding='utf-8'))
    except Exception as exc:
        die(f'PARSE_ERROR:{path.relative_to(ROOT)}:{exc!r}')
    if not isinstance(obj, dict):
        die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj


def load_json(path: Path):
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        die(f'JSON_PARSE_ERROR:{path.relative_to(ROOT)}:{exc!r}')
    if not isinstance(obj, dict):
        die(f'JSON_MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj


def idx(items, key):
    return {x.get(key): x for x in (items or []) if isinstance(x, dict) and x.get(key)}


def first_port(rb, ports):
    for field in PORT_FIELDS:
        uid = rb.get(field)
        if uid:
            return field, uid, ports.get(uid)
    return None, None, None


def event_token(text: str):
    text = str(text or '')
    if '|' in text:
        tail = text.split('|', 1)[1].strip()
        if tail and tail.lower() not in {'event none', 'none'}:
            return tail
    m = re.search(r'\b[a-z][a-z0-9_]*\.[a-z0-9_.]+\b', text)
    return m.group(0) if m else None


def explicit_event_candidates(action, rb, port, transitions):
    candidates = []
    for owner, obj in [('action', action), ('runtime_binding', rb), ('port', port or {})]:
        if not isinstance(obj, dict):
            continue
        for key in ('audit_event_uid', 'event_uid', 'success_event_uid'):
            value = obj.get(key)
            if value not in (None, '', [], {}):
                candidates.append({'source': owner, 'field': key, 'event_uid': str(value)})
    for tid, transition in transitions:
        for key in ('audit_event_uid', 'event_uid', 'success_event_uid'):
            value = transition.get(key)
            if value not in (None, '', [], {}):
                candidates.append({'source': f'transition:{tid}', 'field': key, 'event_uid': str(value)})
    token = event_token((port or {}).get('state_event'))
    if token:
        candidates.append({'source': 'port', 'field': 'state_event', 'event_uid': token})
    dedup = []
    seen = set()
    for c in candidates:
        key = (c['source'], c['field'], c['event_uid'])
        if key not in seen:
            seen.add(key)
            dedup.append(c)
    return dedup


state = load_yaml(STATE)
execution = state.get('execution') or {}
if execution.get('current_stage') != 'STAGE-02-TESTED-BLOCKED':
    die('CURRENT_STAGE_NOT_STAGE02_TESTED_BLOCKED')
if (execution.get('stage2') or {}).get('result') != 'TEST_EXECUTED_BLOCKED':
    die('STAGE02_RESULT_NOT_TEST_EXECUTED_BLOCKED')

evidence = load_json(EVIDENCE)
if evidence.get('test_mode') != 'FRESH_FROM_STAGE1_IMMUTABLE_INPUTS_NO_PRIOR_STAGE2_RESULT_REUSE':
    die('LATEST_STAGE02_EVIDENCE_NOT_FRESH')
if evidence.get('prior_stage2_results_used') is not False:
    die('PRIOR_STAGE2_RESULT_REUSE_FORBIDDEN')
if evidence.get('current_specification_mutated') is not False or evidence.get('ai_autofill_used') is not False or evidence.get('inference_used') is not False:
    die('LATEST_STAGE02_EVIDENCE_SAFETY_DRIFT')

rows = []
page_counts = Counter()
classification_counts = Counter()
for page, path in PAGES.items():
    raw = load_yaml(path)
    authority = raw.get('authority') or {}
    if authority.get('page_uid') != page or authority.get('status') != 'FINAL_LOCKED':
        die(f'{page}:PAGE_AUTHORITY_IDENTITY_OR_STATUS_DRIFT')
    reg = raw.get('registries') or {}
    actions = idx(reg.get('actions'), 'action_uid')
    ports = idx(reg.get('integration_ports'), 'port_uid')
    events = idx(reg.get('events'), 'event_uid')
    transitions = idx(reg.get('stage_transitions'), 'transition_uid')
    transitions_by_action = defaultdict(list)
    for tid, t in transitions.items():
        trigger = t.get('action_uid') or t.get('trigger')
        if trigger in actions:
            transitions_by_action[trigger].append((tid, t))

    page_rows = []
    for action_uid, action in actions.items():
        effect = action.get('effect_type')
        is_effectful = effect not in {'READ_ONLY', 'UI_ONLY', 'CONTEXT_STATE'}
        if not is_effectful:
            continue
        rb = action.get('runtime_binding') or {}
        if rb.get('binding_kind') == 'SHARED_OPERATION_REFERENCE':
            continue
        port_field, port_uid, port = first_port(rb, ports)
        if event_token((port or {}).get('state_event')):
            continue
        candidates = explicit_event_candidates(action, rb, port, transitions_by_action.get(action_uid, []))
        registered = []
        unregistered = []
        for c in candidates:
            uid = c['event_uid']
            if uid in events:
                registered.append(c)
            else:
                unregistered.append(c)
        if registered:
            classification = 'EXACT_REGISTERED_EVENT_BINDING_PRESENT_OUTSIDE_PORT_STATE_EVENT'
            may_materialize = True
        elif candidates:
            classification = 'EXPLICIT_EVENT_UID_PRESENT_BUT_UNREGISTERED'
            may_materialize = False
        else:
            classification = 'CURRENT_AUDIT_EVENT_AUTHORITY_MISSING'
            may_materialize = False
        row = {
            'page_uid': page,
            'action_uid': action_uid,
            'effect_type': effect,
            'port_binding_field': port_field,
            'port_uid': port_uid,
            'port_state_event': (port or {}).get('state_event'),
            'event_registry_denominator': len(events),
            'explicit_event_candidates': candidates,
            'registered_event_candidates': registered,
            'unregistered_event_candidates': unregistered,
            'classification': classification,
            'may_materialize_exact_stage2_event_binding': may_materialize,
        }
        rows.append(row)
        page_rows.append(row)
        page_counts[page] += 1
        classification_counts[classification] += 1
    if len(page_rows) != EXPECTED_COUNTS[page]:
        die(f'{page}:FRESH_AUDIT_EVENT_GAP_COUNT:{len(page_rows)} expected {EXPECTED_COUNTS[page]}')

if len(rows) != 13:
    die(f'AUDIT_EVENT_GAP_DENOMINATOR:{len(rows)} expected 13')
ev_pages = evidence.get('pages') or {}
for page, expected in EXPECTED_COUNTS.items():
    fresh = ((ev_pages.get(page) or {}).get('functional_chain_fresh_scan') or {})
    if (fresh.get('gap_categories') or {}).get('AUDIT_EVENT_NODE_MISSING') != expected:
        die(f'{page}:LATEST_EVIDENCE_AUDIT_EVENT_COUNT_DRIFT')

OUT.parent.mkdir(parents=True, exist_ok=True)
materializable = [r for r in rows if r['may_materialize_exact_stage2_event_binding']]
blocked = [r for r in rows if not r['may_materialize_exact_stage2_event_binding']]
out = {
    'schema_version': 1,
    'artifact_type': 'NON_NORMATIVE_STAGE02_AUDIT_EVENT_CURRENT_AUTHORITY_AUDIT',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'source_mode': 'CURRENT_FRESH_STAGE1_IMMUTABLE_INPUTS_ONLY',
    'prior_stage2_results_used': False,
    'current_specification_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'fresh_audit_event_gap_total': 13,
    'page_counts': dict(page_counts),
    'classification_counts': dict(classification_counts),
    'exact_stage2_event_bindings_materializable_count': len(materializable),
    'still_blocked_count': len(blocked),
    'rows': sorted(rows, key=lambda x: (x['page_uid'], x['action_uid'])),
    'rule': 'Never invent an event UID. A Stage-02 event binding is materializable only from an exact event UID already present in Current Page Authority and registered in that page event registry.',
    'website_construction_allowed': False,
    'deployment_allowed': False,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('PASS: fresh audit-event denominator=13 (CORE-01=4, ASSET-01=9)')
print('PASS: classification counts=' + json.dumps(dict(classification_counts), sort_keys=True))
print(f'PASS: exact registered event bindings materializable={len(materializable)}/13')
print(f'PASS: audit-event gaps still blocked={len(blocked)}/13')
print('PASS: no event UID invention, prior Stage-02 reuse, AI inference/autofill, or Current Specification mutation')
