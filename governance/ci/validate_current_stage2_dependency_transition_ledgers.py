#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import subprocess
import yaml

root = Path('.')
run = root / '00_SOURCE_INTAKE/fresh_run_003'
gap_path = run / '04_PAGE_FUNCTIONAL_CONTRACT/FUNCTIONAL_CHAIN_GAP_LEDGER.yaml'
dep_path = run / '04_PAGE_FUNCTIONAL_CONTRACT/STAGE2_DEPENDENCY_MAP.yaml'
state_path = run / '04_PAGE_FUNCTIONAL_CONTRACT/STATE_TRANSITION_LEDGER.yaml'

REQUIRED_FIELDS = [
    'mutation_owner',
    'failure_state',
    'recovery',
    'audit_event_uid',
    'illegal_transition_tests',
]

EXPECTED_SUMMARY = {
    'total': 171,
    'pages': {'CORE-01': 45, 'ASSET-01': 126},
    'classes': {'ARCHITECTURE_GAP': 133, 'INPUT_SOURCE_GAP': 34, 'AUTHORITY_GAP': 4},
    'categories': {
        'STATE_TRANSITION_LEDGER_FIELD_MISSING': 50,
        'FAILURE_STATE_ERROR_BINDING_MISSING': 44,
        'PAYLOAD_INPUT_CONTRACT_MISSING': 34,
        'POST_ACTION_VALIDATION_NODE_MISSING': 18,
        'AUDIT_EVENT_NODE_MISSING': 13,
        'SUCCESS_NEXT_STATE_BINDING_MISSING': 7,
        'SHARED_OWNER_AUTHORITY_UNRESOLVED': 4,
        'ACTION_WITHOUT_CONTROL_OR_TRIGGER': 1,
    },
}

EXPECTED_TRANSITIONS = {
    'CORE-01-STTR-01': ('CORE-01', 'CORE-01-STAGE-01-CONTEXT', 'CORE-01-STAGE-02-CONVERSE', 'trigger_event_uid', 'CORE-01-EVT-CONTEXT-RESOLVED', 'gate_uid', 'CORE-01-GATE-WORK-ITEM'),
    'CORE-01-STTR-02': ('CORE-01', 'CORE-01-STAGE-02-CONVERSE', 'CORE-01-STAGE-03-SUMMARY-EVAL', 'trigger_event_uid', 'CORE-01-EVT-AI-RESPONSES-READY', 'gate_uid', 'CORE-01-GATE-SUMMARY'),
    'CORE-01-STTR-03': ('CORE-01', 'CORE-01-STAGE-03-SUMMARY-EVAL', 'CORE-01-STAGE-04-HUMAN-DECIDE', 'trigger_event_uid', 'CORE-01-EVT-EVALUATION-READY', 'gate_uid', 'CORE-01-GATE-EVALUATION'),
    'CORE-01-STTR-04': ('CORE-01', 'CORE-01-STAGE-04-HUMAN-DECIDE', 'CORE-01-STAGE-02-CONVERSE', 'trigger_event_uid', 'CORE-01-EVT-HUMAN-DECISION-CONFIRMED', 'gate_uid', 'CORE-01-GATE-HUMAN-DECISION'),
    'CORE-01-STTR-05': ('CORE-01', 'CORE-01-STAGE-04-HUMAN-DECIDE', 'CORE-01-STAGE-05-CANDIDATE', 'trigger_event_uid', 'CORE-01-EVT-HUMAN-DECISION-CONFIRMED', 'gate_uid', 'CORE-01-GATE-CANDIDATE-CREATE'),
    'ASSET-01-STTR-01': ('ASSET-01', 'ASSET-01-STAGE-01-RESOLVE', 'ASSET-01-STAGE-02-REUSE-GENERATE', 'trigger', 'ASSET-01-ACT-FLOW-START', 'gate', 'ASSET-01-GATE-EXECUTE'),
    'ASSET-01-STTR-02': ('ASSET-01', 'ASSET-01-STAGE-02-REUSE-GENERATE', 'ASSET-01-STAGE-03-LAYER-COMPOSITE', 'trigger', 'Verified Candidate/Reuse Resolution', 'gate', 'all required items resolved or valid candidate produced'),
    'ASSET-01-STTR-03': ('ASSET-01', 'ASSET-01-STAGE-03-LAYER-COMPOSITE', 'ASSET-01-STAGE-04-EVALUATE-DECIDE', 'trigger', 'ASSET-01-ACT-EVALUATE', 'gate', 'candidate/layer/composite provenance PASS'),
    'ASSET-01-STTR-04': ('ASSET-01', 'ASSET-01-STAGE-04-EVALUATE-DECIDE', 'ASSET-01-STAGE-02-REUSE-GENERATE', 'trigger', 'ASSET-01-ACT-CORRECTION-EXECUTE', 'gate', 'Modify path; approved correction only'),
    'ASSET-01-STTR-05': ('ASSET-01', 'ASSET-01-STAGE-04-EVALUATE-DECIDE', 'ASSET-01-STAGE-05-FINALIZE', 'trigger', 'ASSET-01-ACT-CANDIDATE-CONFIRM', 'gate', 'ASSET-01-GATE-CONFIRM'),
}

LOCKED = {
    run / '00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml': '9490f3bcc28c5511bc04d6c3ce53c026e3c4667f',
    run / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml': '9668e2307c722ea4cf64f93f07c92da1b3abcc28',
    run / '02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml': '0c067fb8be186a899b42115a82d71312b4014502',
    run / '02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml': '52bb27bf7eb423ddb13bcac5bd34edbcb369de3a',
    run / '02_BASE_BLUEPRINT/CORE-01/VISUAL_BASE_BLUEPRINT.yaml': '8edd134ea4610ab3cb192bca7b3a34ec24ae6368',
    run / '02_BASE_BLUEPRINT/ASSET-01/VISUAL_BASE_BLUEPRINT.yaml': 'f09ec9e4ccbedd1487c91592cb1df83ba5e62464',
    run / '03_BLUEPRINT_BINDING/CORE-01/BLUEPRINT_BINDING_MANIFEST.yaml': '8180bda073fcd26e82372e6ae15b256026a5544e',
    run / '03_BLUEPRINT_BINDING/ASSET-01/BLUEPRINT_BINDING_MANIFEST.yaml': '1879d88110a430fa261660ec5052e9468a6adcdd',
}


def die(msg):
    raise SystemExit(msg)


def load(path):
    try:
        data = yaml.safe_load(path.read_text(encoding='utf-8'))
    except Exception as exc:
        die(f'parse failure {path}: {exc}')
    if not isinstance(data, dict):
        die(f'mapping required: {path}')
    return data


def gitobj(path):
    result = subprocess.run(['git', 'rev-parse', 'HEAD:' + str(path)], text=True, capture_output=True)
    if result.returncode:
        die('git object missing:' + str(path))
    return result.stdout.strip()


for path, blob in LOCKED.items():
    if gitobj(path) != blob:
        die('predecessor artifact drift:' + str(path))

L = load(gap_path)
D = load(dep_path)
S = load(state_path)

if L.get('artifact_type') != 'FUNCTIONAL_CHAIN_GAP_LEDGER' or L.get('status') != 'OPEN_BLOCKING_GAPS':
    die('source gap ledger identity/status drift')
if (L.get('summary') or {}) != EXPECTED_SUMMARY:
    die('source gap ledger summary drift')

if D.get('artifact_type') != 'STAGE2_DEPENDENCY_MAP' or D.get('stage_uid') != 'STAGE-02' or D.get('governance_overlay') != 'v2.1.12':
    die('dependency map identity drift')
if D.get('status') != 'OPEN_BLOCKING_GAPS':
    die('dependency map must remain open while source gaps exist')
if D.get('source_gap_ledger_ref') != '04_PAGE_FUNCTIONAL_CONTRACT/FUNCTIONAL_CHAIN_GAP_LEDGER.yaml':
    die('dependency map source ledger ref drift')
summary = D.get('summary') or {}
for key in ('total', 'pages', 'classes', 'categories'):
    if summary.get(key) != EXPECTED_SUMMARY[key]:
        die(f'dependency map {key} drift')
if summary.get('unresolved_external_authority_consumers') != 4:
    die('dependency map authority consumer count drift')
source_result = D.get('source_machine_result') or {}
if source_result.get('run_id') != 34763159402 or source_result.get('head_sha') != 'cbef81ec6da7f51b3379fd3e52283eda8a2dee33':
    die('dependency map machine source receipt drift')
if source_result.get('artifact_id') != 10318958789 or source_result.get('gap_total') != 171 or source_result.get('functional_completion') is not False:
    die('dependency map machine result receipt drift')

groups = D.get('dependency_groups') or {}
if set(groups) != set(EXPECTED_SUMMARY['categories']):
    die('dependency group category set drift')
for category, expected_count in EXPECTED_SUMMARY['categories'].items():
    group = groups[category]
    if group.get('expanded_gap_count') != expected_count:
        die(f'{category} expanded gap count drift')
    subtotal = 0
    for page in ('CORE-01', 'ASSET-01'):
        page_group = group.get(page)
        if not isinstance(page_group, dict):
            continue
        n = page_group.get('expanded_gap_count')
        subjects = page_group.get('subject_uids') or []
        if not isinstance(n, int) or n < 0 or len(set(subjects)) != len(subjects):
            die(f'{category}/{page} dependency mapping invalid')
        if category == 'STATE_TRANSITION_LEDGER_FIELD_MISSING':
            missing = page_group.get('missing_fields_by_subject') or {}
            if set(missing) != set(subjects):
                die(f'{category}/{page} transition subject set drift')
            if any(fields != REQUIRED_FIELDS for fields in missing.values()):
                die(f'{category}/{page} transition missing fields drift')
            if n != len(subjects) * len(REQUIRED_FIELDS):
                die(f'{category}/{page} transition expanded cardinality drift')
        else:
            if n != len(subjects):
                die(f'{category}/{page} subject cardinality drift')
        subtotal += n
    if subtotal != expected_count:
        die(f'{category} page subtotal drift')

auth = D.get('authority_preservation') or {}
if auth.get('shared_owner_authority_ref') != 'ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or auth.get('consumer_count') != 4:
    die('shared owner authority preservation drift')
if auth.get('status') != 'EXPLICITLY_UNRESOLVED_PRESERVED' or auth.get('ai_guess') != 'FORBIDDEN':
    die('shared owner authority incorrectly resolved')
boundary = D.get('resolution_boundary') or {}
if boundary.get('raw_source_mutation_allowed') is not False or boundary.get('predecessor_artifact_mutation_allowed') is not False:
    die('dependency map mutation boundary drift')
if boundary.get('website_construction_allowed') is not False or boundary.get('deployment_allowed') is not False:
    die('Stage-02 website/deployment block drift')

if S.get('artifact_type') != 'STATE_TRANSITION_LEDGER' or S.get('stage_uid') != 'STAGE-02' or S.get('governance_overlay') != 'v2.1.12':
    die('state transition ledger identity drift')
if S.get('status') != 'OPEN_BLOCKING_GAPS':
    die('state transition ledger must remain open while required fields are unresolved')
field_policy = S.get('required_architecture_field_policy') or {}
if field_policy.get('fields') != REQUIRED_FIELDS:
    die('state transition required field order/set drift')
if field_policy.get('unresolved_value') is not None:
    die('state transition unresolved value must remain null')
if field_policy.get('unresolved_status') != 'UNRESOLVED_ARCHITECTURE_GAP':
    die('state transition unresolved field status drift')
if field_policy.get('resolution_rule') != 'EXACT_EXISTING_AUTHORITY_REQUIRED_NO_INFERENCE':
    die('state transition field resolution rule drift')
raw_blobs = S.get('source_raw_blobs') or {}
if raw_blobs != {
    'CORE-01': '9490f3bcc28c5511bc04d6c3ce53c026e3c4667f',
    'ASSET-01': '9668e2307c722ea4cf64f93f07c92da1b3abcc28',
}:
    die('state transition raw blob refs drift')
transitions = S.get('transitions') or []
if len(transitions) != 10:
    die('state transition count drift')
seen = set()
unresolved = 0
page_counts = Counter()
for row in transitions:
    uid = row.get('transition_uid')
    if uid in seen or uid not in EXPECTED_TRANSITIONS:
        die('state transition uid duplicate/unknown:' + str(uid))
    seen.add(uid)
    expected = EXPECTED_TRANSITIONS[uid]
    actual = (
        row.get('page_uid'), row.get('from_stage'), row.get('to_stage'),
        row.get('trigger_field'), row.get('trigger_value'), row.get('gate_field'), row.get('gate_value')
    )
    if actual != expected:
        die('state transition source identity drift:' + uid)
    source = row.get('source_binding') or {}
    if source.get('mode') != 'EXACT_RAW_SOURCE_REFERENCE' or source.get('payload_mutation_allowed') is not False:
        die('state transition source binding drift:' + uid)
    if row.get('unresolved_required_fields') != REQUIRED_FIELDS:
        die('state transition unresolved field set/order drift:' + uid)
    unresolved += len(row.get('unresolved_required_fields') or [])
    if row.get('unresolved_field_count') != 5 or row.get('status') != 'OPEN':
        die('state transition row closure drift:' + uid)
    page_counts[row.get('page_uid')] += 1
if seen != set(EXPECTED_TRANSITIONS):
    die('state transition exact set incomplete')
ss = S.get('summary') or {}
if ss.get('transition_count') != 10 or ss.get('CORE-01') != 5 or ss.get('ASSET-01') != 5:
    die('state transition summary page count drift')
if ss.get('unresolved_required_field_total') != 50 or ss.get('resolved_required_field_total') != 0 or unresolved != 50:
    die('state transition unresolved/resolved field count drift')
policy = S.get('policy') or {}
if policy.get('raw_source_mutation_allowed') is not False or policy.get('ai_guess_or_default_substitution') != 'FORBIDDEN':
    die('state transition no-inference policy drift')
if policy.get('website_construction_allowed') is not False or policy.get('deployment_allowed') is not False:
    die('state transition website/deployment block drift')

print('PASS: Stage-02 dependency map materializes exact 171 open gaps and preserves 4 shared-owner authority consumers unresolved')
print('PASS: State transition ledger binds exact 10 Raw Source transitions and explicitly preserves 50 missing architecture fields as null')
print('PASS: predecessor Raw/Page/Visual/Binding bytes remain exact; AI guessing, website construction, and deployment remain blocked')
