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
ASSET = RUN / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'
OUT = ROOT / '.github/stage02-failure-state/FAILURE_STATE_ERROR_BINDING_CURRENT_AUTHORITY_AUDIT.json'
EXPECTED_ACTIONS = 44
ERROR_REF_KEYS = ('error_uid', 'error_uids', 'error_binding_uid', 'error_binding', 'error_or_failure_binding')


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


def walk(obj, path=()):
    if isinstance(obj, dict):
        yield path, obj
        for key, value in obj.items():
            yield from walk(value, path + (str(key),))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from walk(value, path + (str(index),))


def flatten_error_refs(node: dict):
    refs = []
    for key in ERROR_REF_KEYS:
        value = node.get(key)
        if not nonempty(value):
            continue
        values = value if isinstance(value, list) else [value]
        for item in values:
            if isinstance(item, str):
                refs.append({'field': key, 'error_uid': item})
            elif isinstance(item, dict):
                uid = item.get('error_uid') or item.get('uid')
                if uid:
                    refs.append({'field': key, 'error_uid': str(uid)})
    dedup = []
    seen = set()
    for ref in refs:
        key = (ref['field'], ref['error_uid'])
        if key not in seen:
            seen.add(key)
            dedup.append(ref)
    return dedup


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
if (fresh.get('gap_categories') or {}).get('FAILURE_STATE_ERROR_BINDING_MISSING') != 44:
    die('LATEST_EVIDENCE_FAILURE_STATE_COUNT_DRIFT')

raw = load_yaml(ASSET)
authority = raw.get('authority') or {}
if authority.get('page_uid') != 'ASSET-01' or authority.get('status') != 'FINAL_LOCKED':
    die('ASSET_PAGE_AUTHORITY_IDENTITY_OR_STATUS_DRIFT')
reg = raw.get('registries') or {}
actions = reg.get('actions') or []
errors = reg.get('errors') or []
if not isinstance(actions, list) or len(actions) != EXPECTED_ACTIONS:
    die(f'ASSET_ACTION_DENOMINATOR:{len(actions) if isinstance(actions, list) else "NOT_LIST"} expected 44')
action_uids = [a.get('action_uid') for a in actions if isinstance(a, dict)]
if len(action_uids) != 44 or None in action_uids or len(set(action_uids)) != 44:
    die('ASSET_ACTION_UID_UNIVERSE_DRIFT')
error_registry = {}
for error in errors if isinstance(errors, list) else []:
    if not isinstance(error, dict) or not error.get('error_uid'):
        continue
    error_registry[error['error_uid']] = error

rows = []
classifications = Counter()
authorized_actions = []
for action_uid in action_uids:
    exact_nodes = []
    authorized = []
    for path, node in walk(raw):
        if node.get('action_uid') != action_uid:
            continue
        failure_state = node.get('failure_state')
        direct_recovery = node.get('recovery')
        error_refs = flatten_error_refs(node)
        registered_refs = []
        unregistered_refs = []
        for ref in error_refs:
            error_uid = ref['error_uid']
            error = error_registry.get(error_uid)
            if error:
                registered_refs.append({
                    **ref,
                    'registered_recovery': error.get('recovery'),
                    'registered_context': error.get('context'),
                })
            else:
                unregistered_refs.append(ref)
        exact_failure_recovery = nonempty(failure_state) and nonempty(direct_recovery)
        exact_error_recovery = any(nonempty(x.get('registered_recovery')) for x in registered_refs)
        admissible = exact_failure_recovery or exact_error_recovery
        record = {
            'node_path': '/'.join(path),
            'failure_state': failure_state,
            'direct_recovery': direct_recovery,
            'explicit_error_refs': error_refs,
            'registered_error_refs': registered_refs,
            'unregistered_error_refs': unregistered_refs,
            'exact_failure_binding_admissible': admissible,
        }
        exact_nodes.append(record)
        if admissible:
            authorized.append(record)
    if authorized:
        classification = 'EXACT_CURRENT_FAILURE_OR_ERROR_BINDING_PRESENT'
        authorized_actions.append(action_uid)
    else:
        classification = 'CURRENT_FAILURE_STATE_ERROR_BINDING_AUTHORITY_MISSING'
    classifications[classification] += 1
    rows.append({
        'page_uid': 'ASSET-01',
        'action_uid': action_uid,
        'exact_action_node_count': len(exact_nodes),
        'candidate_nodes': exact_nodes,
        'authorized_exact_bindings': authorized,
        'authorized_for_gap_removal': bool(authorized),
        'classification': classification,
    })

if len(rows) != 44:
    die('FAILURE_STATE_ROW_DENOMINATOR_DRIFT')
blocked = 44 - len(authorized_actions)
OUT.parent.mkdir(parents=True, exist_ok=True)
out = {
    'schema_version': 1,
    'artifact_type': 'NON_NORMATIVE_STAGE02_FAILURE_STATE_ERROR_BINDING_CURRENT_AUTHORITY_AUDIT',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'page_uid': 'ASSET-01',
    'source_mode': 'CURRENT_FRESH_STAGE1_FINAL_LOCKED_PAGE_AUTHORITY_ONLY',
    'prior_stage2_results_used': False,
    'current_specification_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'fresh_failure_state_error_binding_gap_total': 44,
    'action_denominator': 44,
    'page_error_registry_denominator': len(error_registry),
    'classification_counts': dict(classifications),
    'exact_current_failure_or_error_bindings_materializable_count': len(authorized_actions),
    'authorized_action_uids': authorized_actions,
    'authorized_gap_removals': len(authorized_actions),
    'still_blocked_count': blocked,
    'rows': sorted(rows, key=lambda x: x['action_uid']),
    'admissibility_rule': 'A gap may resolve only when the exact action_uid is bound on the same Current Authority node to failure_state+recovery or to an explicit registered error_uid whose exact same-page error entry supplies recovery. Generic error registries, route/runtime owner, labels, gates, or semantic similarity are not bindings.',
    'stage2_exit_allowed': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('PASS: fresh ASSET-01 failure/error denominator=44 actions')
print('PASS: page error registry denominator=' + str(len(error_registry)))
print('PASS: classification counts=' + json.dumps(dict(classifications), sort_keys=True))
print('PASS: exact Current failure/error bindings materializable=' + str(len(authorized_actions)) + '/44')
print('PASS: failure/error gaps still blocked=' + str(blocked) + '/44')
print('PASS: no generic error join, semantic inference, prior Stage-02 reuse, AI autofill, or Current Specification mutation')
if blocked:
    print('BLOCKED PRODUCT GAP: CURRENT_FAILURE_STATE_ERROR_BINDING_AUTHORITY_MISSING')
