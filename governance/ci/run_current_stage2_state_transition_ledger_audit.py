#!/usr/bin/env python3
from __future__ import annotations
from collections import Counter
import json
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
EVIDENCE = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
OUT = ROOT / '.github/stage02-state-transition/STATE_TRANSITION_LEDGER_CURRENT_AUTHORITY_AUDIT.json'
PAGES = {
    'CORE-01': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
    'ASSET-01': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
}
EXPECTED_TRANSITIONS = {'CORE-01': 5, 'ASSET-01': 5}
EXPECTED_MISSING = {'CORE-01': 25, 'ASSET-01': 25}
REQUIRED_FIELDS = ['mutation_owner', 'failure_state', 'recovery', 'audit_event_uid', 'illegal_transition_tests']


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


def nonempty(value):
    return value not in (None, '', [], {})


def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)


def exact_bindings_for_transition(raw: dict, transition_uid: str, field: str):
    hits = []
    for node in walk(raw):
        if node.get('transition_uid') != transition_uid:
            continue
        if field in node and nonempty(node.get(field)):
            hits.append(node.get(field))
    return hits


state = load_yaml(STATE)
execution = state.get('execution') or {}
if execution.get('current_stage') != 'STAGE-02-TESTED-BLOCKED':
    die(f'CURRENT_STAGE_NOT_STAGE02_TESTED_BLOCKED:{execution.get("current_stage")!r}')
stage2_state = execution.get('stage2') or {}
if stage2_state.get('result') != 'TEST_EXECUTED_BLOCKED':
    die('STAGE02_RESULT_NOT_TEST_EXECUTED_BLOCKED')
if execution.get('website_construction_allowed') is not False or execution.get('deployment_allowed') is not False:
    die('FAIL_CLOSED_STATE_DRIFT')

evidence = load_json(EVIDENCE)
if evidence.get('test_mode') != 'FRESH_FROM_STAGE1_IMMUTABLE_INPUTS_NO_PRIOR_STAGE2_RESULT_REUSE':
    die('LATEST_STAGE02_EVIDENCE_NOT_FRESH')
if evidence.get('prior_stage2_results_used') is not False:
    die('PRIOR_STAGE2_RESULT_REUSE_FORBIDDEN')
if evidence.get('current_specification_mutated') is not False or evidence.get('ai_autofill_used') is not False or evidence.get('inference_used') is not False:
    die('LATEST_STAGE02_EVIDENCE_SAFETY_DRIFT')

rows = []
page_transition_counts = Counter()
page_missing_counts = Counter()
field_missing_counts = Counter()
exact_binding_count = 0
for page, path in PAGES.items():
    raw = load_yaml(path)
    authority = raw.get('authority') or {}
    if authority.get('page_uid') != page or authority.get('status') != 'FINAL_LOCKED':
        die(f'{page}:PAGE_AUTHORITY_IDENTITY_OR_STATUS_DRIFT')
    reg = raw.get('registries') or {}
    transitions = reg.get('stage_transitions') or []
    if not isinstance(transitions, list):
        die(f'{page}:STAGE_TRANSITIONS_LIST_REQUIRED')
    if len(transitions) != EXPECTED_TRANSITIONS[page]:
        die(f'{page}:TRANSITION_DENOMINATOR:{len(transitions)} expected {EXPECTED_TRANSITIONS[page]}')
    uids = [t.get('transition_uid') for t in transitions if isinstance(t, dict)]
    if len(uids) != len(transitions) or None in uids or len(set(uids)) != len(uids):
        die(f'{page}:TRANSITION_UID_UNIQUENESS_OR_IDENTITY')

    for transition in transitions:
        uid = transition['transition_uid']
        page_transition_counts[page] += 1
        missing = []
        resolved = []
        exact_bindings = {}
        for field in REQUIRED_FIELDS:
            hits = exact_bindings_for_transition(raw, uid, field)
            if hits:
                resolved.append(field)
                exact_bindings[field] = hits
                exact_binding_count += 1
            else:
                missing.append(field)
                page_missing_counts[page] += 1
                field_missing_counts[field] += 1
        known_trigger = transition.get('trigger_event_uid') if page == 'CORE-01' else transition.get('trigger')
        known_gate = transition.get('gate_uid') if page == 'CORE-01' else transition.get('gate')
        rows.append({
            'page_uid': page,
            'transition_uid': uid,
            'from_stage': transition.get('from_stage'),
            'to_stage': transition.get('to_stage'),
            'known_trigger_or_action': known_trigger,
            'known_gate_or_precondition': known_gate,
            'required_fields': REQUIRED_FIELDS,
            'exact_required_field_bindings': exact_bindings,
            'resolved_fields': resolved,
            'unresolved_fields': missing,
            'unresolved_field_count': len(missing),
            'semantic_substitution_forbidden': {
                'trigger_event_uid_as_audit_event_uid': True,
                'runtime_or_action_owner_as_mutation_owner': True,
                'error_registry_entry_as_failure_state_or_recovery': True,
                'generated_negative_test_as_existing_authority': True,
                'gate_or_action_semantic_similarity': True,
            },
            'status': 'OPEN' if missing else 'EXACT_CURRENT_AUTHORITY_COMPLETE',
        })

for page, expected in EXPECTED_MISSING.items():
    if page_missing_counts[page] != expected:
        die(f'{page}:FRESH_STATE_TRANSITION_MISSING_COUNT:{page_missing_counts[page]} expected {expected}')
    fresh = (((evidence.get('pages') or {}).get(page) or {}).get('functional_chain_fresh_scan') or {})
    cats = fresh.get('gap_categories') or {}
    if cats.get('STATE_TRANSITION_LEDGER_FIELD_MISSING') != expected:
        die(f'{page}:LATEST_EVIDENCE_TRANSITION_COUNT_DRIFT')

if len(rows) != 10:
    die(f'TRANSITION_UNIVERSE:{len(rows)} expected 10')
if sum(page_missing_counts.values()) != 50:
    die(f'STATE_TRANSITION_MISSING_DENOMINATOR:{sum(page_missing_counts.values())} expected 50')
if any(field_missing_counts[field] != 10 for field in REQUIRED_FIELDS):
    die('REQUIRED_FIELD_MISSING_DISTRIBUTION_DRIFT:' + json.dumps(dict(field_missing_counts), sort_keys=True))

OUT.parent.mkdir(parents=True, exist_ok=True)
out = {
    'schema_version': 1,
    'artifact_type': 'NON_NORMATIVE_STAGE02_STATE_TRANSITION_LEDGER_CURRENT_AUTHORITY_AUDIT',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'source_mode': 'CURRENT_FRESH_STAGE1_FINAL_LOCKED_PAGE_AUTHORITY_ONLY',
    'prior_stage2_results_used': False,
    'current_specification_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'result': 'AUDIT_PASS_PRODUCT_GAPS_REMAIN_BLOCKED' if sum(page_missing_counts.values()) else 'AUDIT_PASS_EXACT_BINDINGS_AVAILABLE',
    'transition_total': len(rows),
    'required_fields_per_transition': REQUIRED_FIELDS,
    'required_field_denominator': 50,
    'page_transition_counts': dict(page_transition_counts),
    'page_missing_counts': dict(page_missing_counts),
    'field_missing_counts': dict(field_missing_counts),
    'exact_current_authority_required_field_binding_count': exact_binding_count,
    'authorized_gap_removals': exact_binding_count,
    'still_blocked_count': sum(page_missing_counts.values()),
    'rows': sorted(rows, key=lambda x: (x['page_uid'], x['transition_uid'])),
    'admissibility_rule': 'Only an exact non-empty required field bound to the same transition_uid in the FINAL_LOCKED Current Page Authority may resolve a transition-ledger field. Semantic joins, defaults, generated tests, and neighboring action/event/error/owner data are not authority.',
    'stage2_exit_allowed': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('PASS: fresh state-transition universe=10 transitions (CORE-01=5, ASSET-01=5)')
print('PASS: required transition-ledger denominator=50 (5 fields x 10 transitions)')
print('PASS: exact Current transition_uid+required-field bindings=' + str(exact_binding_count) + '/50')
print('PASS: unresolved state-transition ledger fields=' + str(sum(page_missing_counts.values())) + '/50')
print('PASS: missing distribution=' + json.dumps(dict(field_missing_counts), sort_keys=True))
print('PASS: no semantic substitution, generated authority, prior Stage-02 reuse, AI inference/autofill, or Current Specification mutation')
if sum(page_missing_counts.values()):
    print('BLOCKED PRODUCT GAP: EXACT_TRANSITION_ARCHITECTURE_BINDING_MISSING')
