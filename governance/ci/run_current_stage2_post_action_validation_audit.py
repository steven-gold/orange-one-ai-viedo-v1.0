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
OUT = ROOT / '.github/stage02-post-action-validation/POST_ACTION_VALIDATION_CURRENT_AUTHORITY_AUDIT.json'
EXPECTED_GAPS = 18
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


def present(obj, *names):
    return any(isinstance(obj, dict) and obj.get(name) not in (None, '', [], {}) for name in names)


def first_resolved_port(rb, ports):
    for field in PORT_FIELDS:
        uid = rb.get(field)
        if uid and uid in ports:
            return field, uid, ports[uid]
    return None, None, {}


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
if (fresh.get('gap_categories') or {}).get('POST_ACTION_VALIDATION_NODE_MISSING') != EXPECTED_GAPS:
    die('LATEST_EVIDENCE_POST_ACTION_VALIDATION_COUNT_DRIFT')

raw = load_yaml(ASSET)
authority = raw.get('authority') or {}
if authority.get('page_uid') != 'ASSET-01' or authority.get('status') != 'FINAL_LOCKED':
    die('ASSET_PAGE_AUTHORITY_IDENTITY_OR_STATUS_DRIFT')
reg = raw.get('registries') or {}
actions = idx(reg.get('actions'), 'action_uid')
ports = idx(reg.get('integration_ports'), 'port_uid')

rows = []
classifications = Counter()
for action_uid, action in actions.items():
    effect = action.get('effect_type')
    is_effectful = effect not in {'READ_ONLY', 'UI_ONLY', 'CONTEXT_STATE'}
    if not is_effectful:
        continue
    rb = action.get('runtime_binding') or {}
    if rb.get('binding_kind') == 'SHARED_OPERATION_REFERENCE':
        continue
    port_field, port_uid, port = first_resolved_port(rb, ports)
    action_signals = [k for k in ('success_contract', 'validation_contract', 'validator_uid') if present(action, k)]
    runtime_signals = [k for k in ('validation', 'validation_rule', 'evaluation_rule') if present(rb, k)]
    port_signals = [k for k in ('validation', 'validation_rule', 'validator_uid') if present(port, k)]
    exact_present = bool(action_signals or runtime_signals or port_signals)
    if exact_present:
        continue
    operation = port.get('operation') or port.get('registered_operation') if isinstance(port, dict) else None
    method_path = port.get('method_path') or port.get('method_effective_path') if isinstance(port, dict) else None
    row = {
        'page_uid': 'ASSET-01',
        'action_uid': action_uid,
        'effect_type': effect,
        'binding_kind': rb.get('binding_kind'),
        'port_binding_field': port_field,
        'port_uid': port_uid,
        'operation_id': operation,
        'method_path': method_path,
        'action_validation_signal_keys': action_signals,
        'runtime_validation_signal_keys': runtime_signals,
        'port_validation_signal_keys': port_signals,
        'current_post_action_validation_authority_present': False,
        'authority_disposition': 'BLOCKED_CURRENT_STAGE1_POST_ACTION_VALIDATION_AUTHORITY_ABSENT',
        'may_materialize_post_action_validation_contract': False,
        'gap_category': 'POST_ACTION_VALIDATION_NODE_MISSING',
    }
    rows.append(row)
    classifications['CURRENT_POST_ACTION_VALIDATION_AUTHORITY_MISSING'] += 1

if len(rows) != EXPECTED_GAPS:
    die(f'POST_ACTION_VALIDATION_GAP_DENOMINATOR:{len(rows)} expected {EXPECTED_GAPS}')
if len({r['action_uid'] for r in rows}) != EXPECTED_GAPS:
    die('POST_ACTION_VALIDATION_ACTION_UID_UNIQUENESS')
if any(r['action_validation_signal_keys'] or r['runtime_validation_signal_keys'] or r['port_validation_signal_keys'] for r in rows):
    die('POST_ACTION_VALIDATION_SIGNAL_CLASSIFICATION_DRIFT')

OUT.parent.mkdir(parents=True, exist_ok=True)
out = {
    'schema_version': 1,
    'artifact_type': 'NON_NORMATIVE_STAGE02_POST_ACTION_VALIDATION_CURRENT_AUTHORITY_AUDIT',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'page_uid': 'ASSET-01',
    'source_mode': 'CURRENT_FRESH_STAGE1_FINAL_LOCKED_PAGE_AUTHORITY_ONLY',
    'prior_stage2_results_used': False,
    'current_specification_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'fresh_post_action_validation_gap_total': EXPECTED_GAPS,
    'classification_counts': dict(classifications),
    'exact_current_post_action_validation_bindings_materializable_count': 0,
    'authorized_gap_removals': 0,
    'still_blocked_count': EXPECTED_GAPS,
    'rows': sorted(rows, key=lambda x: x['action_uid']),
    'admissibility_rule': 'Use exactly the Stage-02 fresh scanner predicate: success_contract/validation_contract/validator_uid on the action, validation/validation_rule/evaluation_rule on runtime_binding, or validation/validation_rule/validator_uid on the exact resolved port. Operation, route, response labels, gates, or semantic similarity are not validation authority.',
    'stage2_exit_allowed': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('PASS: fresh ASSET-01 post-action validation gap denominator=18')
print('PASS: exact Current post-action validation bindings materializable=0/18')
print('PASS: post-action validation gaps still blocked=18/18')
print('PASS: reused exact Stage-02 fresh scanner validation predicate; no semantic inference/autofill/spec mutation')
print('BLOCKED PRODUCT GAP: CURRENT_POST_ACTION_VALIDATION_AUTHORITY_MISSING')
