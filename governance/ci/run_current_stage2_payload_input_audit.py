#!/usr/bin/env python3
from __future__ import annotations
from collections import Counter, defaultdict
import json
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
EVIDENCE = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
OUT = ROOT / '.github/stage02-payload-audit/PAYLOAD_INPUT_CURRENT_AUTHORITY_AUDIT.json'
PAGES = {
    'CORE-01': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
    'ASSET-01': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
}
SCHEMA_KEYS = {
    'payload','payload_rule','payload_mode','payload_schema','payload_schema_id','payload_fields','payload_contract',
    'input_contract','input_schema','input_fields','request_contract','request_schema','request_schema_id','request_fields',
    'required_body','body_schema','form_schema',
}
PORT_FIELDS = ('port_uid', 'persist_via_port_uid', 'execute_port_uid', 'decision_port_uid')
EXPECTED_COUNTS = {'CORE-01': 16, 'ASSET-01': 18}


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


def signal_keys(*objects):
    found = set()
    for obj in objects:
        if isinstance(obj, dict):
            for key in SCHEMA_KEYS:
                if obj.get(key) not in (None, '', [], {}):
                    found.add(key)
    return sorted(found)


def first_port(rb, ports):
    for field in PORT_FIELDS:
        uid = rb.get(field)
        if uid:
            return field, uid, ports.get(uid)
    return None, None, None


state = load_yaml(STATE)
execution = state.get('execution') or {}
if execution.get('current_stage') != 'STAGE-02-TESTED-BLOCKED':
    die(f'CURRENT_STAGE_NOT_STAGE02_TESTED_BLOCKED:{execution.get("current_stage")!r}')
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
if evidence.get('fresh_functional_gap_total') != 171:
    die('LATEST_STAGE02_GAP_TOTAL_DRIFT')

rows = []
page_counts = Counter()
for page, path in PAGES.items():
    raw = load_yaml(path)
    if ((raw.get('authority') or {}).get('page_uid')) != page:
        die(f'{page}:PAGE_AUTHORITY_IDENTITY_DRIFT')
    if ((raw.get('authority') or {}).get('status')) != 'FINAL_LOCKED':
        die(f'{page}:PAGE_AUTHORITY_NOT_FINAL_LOCKED')
    reg = raw.get('registries') or {}
    actions = idx(reg.get('actions'), 'action_uid')
    ports = idx(reg.get('integration_ports'), 'port_uid')
    current_rows = []
    for action_uid, action in actions.items():
        effect = action.get('effect_type')
        is_effectful = effect not in {'READ_ONLY', 'UI_ONLY', 'CONTEXT_STATE'}
        if not is_effectful:
            continue
        rb = action.get('runtime_binding') or {}
        if rb.get('binding_kind') == 'SHARED_OPERATION_REFERENCE':
            continue
        port_field, port_uid, port = first_port(rb, ports)
        signals = signal_keys(action, rb, port or {})
        if signals:
            continue
        operation = None
        method_path = None
        if isinstance(port, dict):
            operation = port.get('operation') or port.get('registered_operation')
            method_path = port.get('method_path') or port.get('method_effective_path')
        row = {
            'page_uid': page,
            'action_uid': action_uid,
            'effect_type': effect,
            'binding_kind': rb.get('binding_kind'),
            'port_binding_field': port_field,
            'port_uid': port_uid,
            'operation_id': operation,
            'method_path': method_path,
            'current_payload_schema_signal_keys': signals,
            'exact_runtime_mapping_present': bool(port_uid and port and operation and method_path),
            'current_payload_schema_authority_present': False,
            'authority_disposition': 'BLOCKED_CURRENT_STAGE1_INPUT_SOURCE_ABSENT',
            'may_materialize_payload_contract': False,
            'gap_category': 'PAYLOAD_INPUT_CONTRACT_MISSING',
        }
        current_rows.append(row)
        rows.append(row)
        page_counts[page] += 1
    if len(current_rows) != EXPECTED_COUNTS[page]:
        die(f'{page}:FRESH_PAYLOAD_GAP_COUNT:{len(current_rows)} expected {EXPECTED_COUNTS[page]}')

if len(rows) != 34:
    die(f'PAYLOAD_GAP_DENOMINATOR:{len(rows)} expected 34')
if len({r['action_uid'] for r in rows}) != 34:
    die('PAYLOAD_ACTION_UID_UNIQUENESS')
if not all(r['exact_runtime_mapping_present'] for r in rows):
    bad = [r['action_uid'] for r in rows if not r['exact_runtime_mapping_present']]
    die('RUNTIME_MAPPING_INCOMPLETE:' + ','.join(bad))
if any(r['current_payload_schema_signal_keys'] for r in rows):
    die('SCHEMA_SIGNAL_CLASSIFICATION_DRIFT')

ev_pages = evidence.get('pages') or {}
for page, expected in EXPECTED_COUNTS.items():
    fresh = ((ev_pages.get(page) or {}).get('functional_chain_fresh_scan') or {})
    cats = fresh.get('gap_categories') or {}
    if cats.get('PAYLOAD_INPUT_CONTRACT_MISSING') != expected:
        die(f'{page}:LATEST_EVIDENCE_PAYLOAD_COUNT_DRIFT')

OUT.parent.mkdir(parents=True, exist_ok=True)
out = {
    'schema_version': 1,
    'artifact_type': 'NON_NORMATIVE_STAGE02_PAYLOAD_INPUT_CURRENT_AUTHORITY_AUDIT',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'source_mode': 'CURRENT_FRESH_STAGE1_IMMUTABLE_INPUTS_ONLY',
    'prior_stage2_results_used': False,
    'current_specification_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'result': 'AUDIT_PASS_PRODUCT_GAPS_REMAIN_BLOCKED',
    'payload_gap_total': 34,
    'page_counts': dict(page_counts),
    'exact_action_port_operation_route_mapping_count': 34,
    'admissible_current_payload_schema_binding_count': 0,
    'payload_gap_removal_authorized': 0,
    'rows': sorted(rows, key=lambda x: (x['page_uid'], x['action_uid'])),
    'remediation_rule': 'Operation/route/port identity is not a payload schema. Do not infer request fields. Materialize a payload contract only from exact Current product authority or an explicitly authorized product contract source.',
    'stage2_exit_allowed': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('PASS: fresh payload/input audit denominator=34 (CORE-01=16, ASSET-01=18)')
print('PASS: exact action->port->operation/route mapping=34/34')
print('PASS: admissible Current payload schema binding=0/34; gap removals authorized=0')
print('PASS: no prior Stage-02 result reuse, no AI inference/autofill, no Current Specification mutation')
print('BLOCKED PRODUCT GAP: CURRENT_PAYLOAD_SCHEMA_AUTHORITY_MISSING for 34 actions')
