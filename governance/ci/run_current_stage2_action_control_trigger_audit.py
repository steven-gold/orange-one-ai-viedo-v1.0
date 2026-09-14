#!/usr/bin/env python3
from __future__ import annotations
from collections import defaultdict
import json
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
EVIDENCE = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
ASSET = RUN / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'
OUT = ROOT / '.github/stage02-action-trigger/ACTION_CONTROL_TRIGGER_CURRENT_AUTHORITY_AUDIT.json'
EXPECTED_GAPS = 1


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


def present(obj, *names):
    return any(isinstance(obj, dict) and obj.get(name) not in (None, '', [], {}) for name in names)


state = load_yaml(STATE)
execution = state.get('execution') or {}
if execution.get('current_stage') != 'STAGE-02-TESTED-BLOCKED':
    die('CURRENT_STAGE_NOT_STAGE02_TESTED_BLOCKED')
if (execution.get('stage2') or {}).get('result') != 'TEST_EXECUTED_BLOCKED':
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
fresh = (((evidence.get('pages') or {}).get('ASSET-01') or {}).get('functional_chain_fresh_scan') or {})
if (fresh.get('gap_categories') or {}).get('ACTION_WITHOUT_CONTROL_OR_TRIGGER') != EXPECTED_GAPS:
    die('LATEST_EVIDENCE_ACTION_TRIGGER_COUNT_DRIFT')

raw = load_yaml(ASSET)
authority = raw.get('authority') or {}
if authority.get('page_uid') != 'ASSET-01' or authority.get('status') != 'FINAL_LOCKED':
    die('ASSET_PAGE_AUTHORITY_IDENTITY_OR_STATUS_DRIFT')
reg = raw.get('registries') or {}
actions = idx(reg.get('actions'), 'action_uid')
controls = idx(reg.get('controls'), 'control_uid')
transitions = idx(reg.get('stage_transitions'), 'transition_uid')
controls_by_action = defaultdict(list)
transitions_by_action = defaultdict(list)
for control_uid, control in controls.items():
    action_uid = control.get('action_uid')
    if action_uid:
        controls_by_action[action_uid].append(control_uid)
for transition_uid, transition in transitions.items():
    trigger = transition.get('action_uid') or transition.get('trigger_event_uid') or transition.get('trigger')
    if trigger in actions:
        transitions_by_action[trigger].append(transition_uid)

rows = []
for action_uid, action in actions.items():
    explicit_trigger_fields = [k for k in ('trigger_event_uid', 'trigger_uid', 'invocation', 'system_trigger', 'trigger_kind') if present(action, k)]
    exact_transition_triggers = sorted(transitions_by_action.get(action_uid, []))
    exact_controls = sorted(controls_by_action.get(action_uid, []))
    explicit_trigger = bool(explicit_trigger_fields or exact_transition_triggers)
    if exact_controls or explicit_trigger:
        continue
    rows.append({
        'page_uid': 'ASSET-01',
        'action_uid': action_uid,
        'effect_type': action.get('effect_type'),
        'label': action.get('label'),
        'registered_control_uids': exact_controls,
        'exact_transition_trigger_uids': exact_transition_triggers,
        'explicit_trigger_fields': explicit_trigger_fields,
        'current_control_or_trigger_authority_present': False,
        'authority_disposition': 'BLOCKED_CURRENT_STAGE1_CONTROL_OR_TRIGGER_AUTHORITY_ABSENT',
        'may_materialize_control_or_trigger': False,
        'gap_category': 'ACTION_WITHOUT_CONTROL_OR_TRIGGER',
    })

if len(rows) != EXPECTED_GAPS:
    die(f'ACTION_CONTROL_TRIGGER_GAP_DENOMINATOR:{len(rows)} expected {EXPECTED_GAPS}')
if not rows[0].get('action_uid'):
    die('ACTION_UID_MISSING')

OUT.parent.mkdir(parents=True, exist_ok=True)
out = {
    'schema_version': 1,
    'artifact_type': 'NON_NORMATIVE_STAGE02_ACTION_CONTROL_TRIGGER_CURRENT_AUTHORITY_AUDIT',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'page_uid': 'ASSET-01',
    'source_mode': 'CURRENT_FRESH_STAGE1_FINAL_LOCKED_PAGE_AUTHORITY_ONLY',
    'prior_stage2_results_used': False,
    'current_specification_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'fresh_action_without_control_or_trigger_gap_total': EXPECTED_GAPS,
    'exact_current_control_or_trigger_bindings_materializable_count': 0,
    'authorized_gap_removals': 0,
    'still_blocked_count': EXPECTED_GAPS,
    'rows': rows,
    'admissibility_rule': 'Use exactly the Stage-02 fresh scanner predicate: an action is admitted only by an exact registered control bound through control.action_uid, an exact stage transition whose trigger resolves to that action_uid, or an explicit non-empty action trigger_event_uid/trigger_uid/invocation/system_trigger/trigger_kind. Labels, route identity, neighboring controls, or semantic similarity are not trigger authority.',
    'stage2_exit_allowed': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('PASS: fresh ASSET-01 action-without-control-or-trigger denominator=1')
print('PASS: exact Current control/trigger bindings materializable=0/1')
print('PASS: blocked action_uid=' + rows[0]['action_uid'])
print('PASS: reused exact Stage-02 fresh scanner control/trigger predicate; no semantic inference/autofill/spec mutation')
print('BLOCKED PRODUCT GAP: CURRENT_ACTION_CONTROL_OR_TRIGGER_AUTHORITY_MISSING')
