#!/usr/bin/env python3
from pathlib import Path
import subprocess
import yaml

root = Path('.')
run = root / '00_SOURCE_INTAKE/fresh_run_003'
evidence_path = run / '00_SOURCE_INTAKE/evidence/PAGE_FUNCTIONAL_REVIEW_EVIDENCE.yaml'
gap_path = run / '04_PAGE_FUNCTIONAL_CONTRACT/FUNCTIONAL_CHAIN_GAP_LEDGER.yaml'
state_path = run / '04_PAGE_FUNCTIONAL_CONTRACT/STATE_TRANSITION_LEDGER.yaml'
shared_path = run / '04_PAGE_FUNCTIONAL_CONTRACT/SHARED_OWNER_PORT_MAP.yaml'
async_path = run / '04_PAGE_FUNCTIONAL_CONTRACT/ASYNC_PROVIDER_CONTRACT.yaml'
core_spec_path = run / '04_PAGE_FUNCTIONAL_CONTRACT/CORE-01/PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml'
asset_spec_path = run / '04_PAGE_FUNCTIONAL_CONTRACT/ASSET-01/PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml'
plan_path = run / 'ARTIFACT_PLAN.yaml'

LOCKED = {
    run / '00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml': '9490f3bcc28c5511bc04d6c3ce53c026e3c4667f',
    run / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml': '9668e2307c722ea4cf64f93f07c92da1b3abcc28',
    gap_path: '093c72a8e3227c1228180a29586980ab5e8f85cd',
}

EXPECTED_CATEGORIES = {
    'PAYLOAD_INPUT_CONTRACT_MISSING': (34, 'INPUT_SOURCE_GAP', 'BLOCKED_NO_FORMAL_INPUT_CONTRACT'),
    'AUDIT_EVENT_NODE_MISSING': (13, 'ARCHITECTURE_GAP', 'BLOCKED_NO_CANONICAL_AUDIT_EVENT_UID'),
    'SUCCESS_NEXT_STATE_BINDING_MISSING': (7, 'ARCHITECTURE_GAP', 'BLOCKED_NO_CANONICAL_NEXT_STATE_UID'),
    'FAILURE_STATE_ERROR_BINDING_MISSING': (44, 'ARCHITECTURE_GAP', 'BLOCKED_NO_EXACT_ACTION_ERROR_BINDING'),
    'POST_ACTION_VALIDATION_NODE_MISSING': (18, 'ARCHITECTURE_GAP', 'BLOCKED_NO_EXACT_POST_ACTION_VALIDATION_NODE'),
    'STATE_TRANSITION_LEDGER_FIELD_MISSING': (50, 'ARCHITECTURE_GAP', 'BLOCKED_REQUIRED_FIELDS_ABSENT'),
    'SHARED_OWNER_AUTHORITY_UNRESOLVED': (4, 'AUTHORITY_GAP', 'BLOCKED_EXTERNAL_SHARED_OWNER_AUTHORITY_UNRESOLVED'),
    'ACTION_WITHOUT_CONTROL_OR_TRIGGER': (1, 'ARCHITECTURE_GAP', 'BLOCKED_NO_EXACT_TRIGGER_AUTHORITY'),
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
    p = str(path)
    result = subprocess.run(['git', 'rev-parse', 'HEAD:' + p], text=True, capture_output=True)
    if result.returncode:
        die('git object missing:' + p)
    return result.stdout.strip()


for path, expected_blob in LOCKED.items():
    if gitobj(path) != expected_blob:
        die('immutable source drift:' + str(path))

E = load(evidence_path)
G = load(gap_path)
S = load(state_path)
SH = load(shared_path)
A = load(async_path)
C = load(core_spec_path)
AS = load(asset_spec_path)
P = load(plan_path)

if E.get('artifact_type') != 'PAGE_FUNCTIONAL_REVIEW_EVIDENCE':
    die('review evidence artifact type drift')
if E.get('governance_overlay') != 'v2.1.12' or E.get('stage_uid') != 'STAGE-02':
    die('review evidence governance/stage drift')
if E.get('status') != 'REVIEW_COMPLETE_STAGE2_NOT_CLOSED':
    die('review evidence must not claim Stage-02 closure')

baseline = E.get('baseline') or {}
if baseline.get('gap_total') != 171:
    die('review baseline total drift')
if baseline.get('pages') != {'CORE-01': 45, 'ASSET-01': 126}:
    die('review baseline page counts drift')
if baseline.get('classes') != {'ARCHITECTURE_GAP': 133, 'INPUT_SOURCE_GAP': 34, 'AUTHORITY_GAP': 4}:
    die('review baseline classes drift')
if baseline.get('auto_remediable_count') != 0 or baseline.get('implementation_gap_count') != 0:
    die('review evidence invented auto-remediable/implementation gaps')

summary = G.get('summary') or {}
if summary.get('total') != 171 or summary.get('pages') != {'CORE-01': 45, 'ASSET-01': 126}:
    die('functional gap ledger total/page drift')
if summary.get('classes') != {'ARCHITECTURE_GAP': 133, 'INPUT_SOURCE_GAP': 34, 'AUTHORITY_GAP': 4}:
    die('functional gap ledger class drift')

reviews = E.get('category_reviews') or {}
if set(reviews) != set(EXPECTED_CATEGORIES):
    die('review category set drift')
for key, (count, klass, result) in EXPECTED_CATEGORIES.items():
    row = reviews.get(key) or {}
    if row.get('gap_count') != count or row.get('class') != klass or row.get('review_result') != result:
        die('review category identity/count/result drift:' + key)
    if row.get('auto_remediable_count') != 0:
        die('review category must remain non-auto-remediable:' + key)

shared = reviews['SHARED_OWNER_AUTHORITY_UNRESOLVED']
if shared.get('authority_ref') != 'ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY':
    die('shared owner authority ref drift')
if shared.get('consumers') != [
    'ASSET-01-ACT-CORRECTION-GENERATE',
    'ASSET-01-ACT-CORRECTION-APPROVE',
    'ASSET-01-ACT-RESTORE-AS-NEW',
    'ASSET-01-ACT-VERSION-LOCK',
]:
    die('shared owner consumer set/order drift')
if reviews['ACTION_WITHOUT_CONTROL_OR_TRIGGER'].get('subject_uid') != 'ASSET-01-ACT-FINDING-CREATE':
    die('finding-create trigger gap identity drift')

resolution = E.get('resolution_summary') or {}
expected_resolution = {
    'reviewed_gap_total': 171,
    'safely_auto_remediable_total': 0,
    'authority_unique_implementation_gap_total': 0,
    'remains_blocking_total': 171,
    'reclassified_to_complete_total': 0,
    'source_mutations': 0,
    'inferred_bindings': 0,
    'synthetic_contracts': 0,
}
for key, value in expected_resolution.items():
    if resolution.get(key) != value:
        die('resolution summary drift:' + key)

exit_gate = E.get('stage2_exit_gate') or {}
if exit_gate.get('gate_uid') != 'ALL_REQUIRED_PAGES_STAGE2_CLOSED' or exit_gate.get('result') != 'BLOCKED':
    die('Stage-02 exit gate false closure')
if exit_gate.get('functional_completion') is not False:
    die('functional completion must remain false')
if exit_gate.get('website_construction_allowed') is not False or exit_gate.get('deployment_allowed') is not False:
    die('website/deployment must remain blocked')

ss = S.get('summary') or {}
if ss.get('unresolved_required_field_total') != 50 or ss.get('resolved_required_field_total') != 0:
    die('transition required field resolution drift')
if (SH.get('summary') or {}).get('unresolved_consumer_count') != 4:
    die('shared owner unresolved consumer count drift')
if SH.get('status') != 'OPEN_BLOCKING_AUTHORITY_GAP':
    die('shared owner map false resolution')
if A.get('status') != 'OPEN_BLOCKING_GAPS':
    die('async provider contract false closure')
for page_spec in (C, AS):
    if page_spec.get('status') != 'OPEN_BLOCKING_GAPS':
        die('page construction spec false closure')
    gate = page_spec.get('construction_gate') or {}
    if gate.get('ready_for_implementation') is not False:
        die('page construction incorrectly marked implementation-ready')
    if gate.get('website_construction_allowed') is not False or gate.get('deployment_allowed') is not False:
        die('page construction spec website/deployment false enablement')

if 'PAGE_FUNCTIONAL_REVIEW_EVIDENCE' not in (P.get('current_artifacts') or []):
    die('artifact plan missing required PAGE_FUNCTIONAL_REVIEW_EVIDENCE registration')

print('PASS: PAGE_FUNCTIONAL_REVIEW_EVIDENCE physically exists and reviews all 171 Stage-02 gaps')
print('PASS: 0/171 gaps are falsely reclassified as auto-remediable; 171 remain blocking under v2.1.12 authority rules')
print('PASS: 4 shared-owner consumers and 50 transition architecture fields remain unresolved; no source mutation/inferred contract')
print('PASS: ALL_REQUIRED_PAGES_STAGE2_CLOSED remains BLOCKED; website construction and deployment remain forbidden')
