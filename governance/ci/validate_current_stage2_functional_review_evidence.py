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
SHARED_CONSUMERS = [
    'ASSET-01-ACT-CORRECTION-GENERATE',
    'ASSET-01-ACT-CORRECTION-APPROVE',
    'ASSET-01-ACT-RESTORE-AS-NEW',
    'ASSET-01-ACT-VERSION-LOCK',
]
ASYNC_FIELDS = [
    'request_identity', 'input_fingerprint', 'idempotency', 'queued', 'running',
    'succeeded', 'failed', 'cancel', 'retry_eligibility', 'callback_result_provenance',
    'output_persistence', 'audit_correlation',
]


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

if E.get('artifact_type') != 'PAGE_FUNCTIONAL_REVIEW_EVIDENCE' or E.get('governance_overlay') != 'v2.1.12' or E.get('stage_uid') != 'STAGE-02':
    die('review evidence identity/governance drift')
if E.get('status') != 'REVIEW_COMPLETE_STAGE2_NOT_CLOSED':
    die('review evidence must not claim Stage-02 closure')

baseline = E.get('baseline') or {}
if baseline != {
    'gap_total': 171,
    'pages': {'CORE-01': 45, 'ASSET-01': 126},
    'classes': {'ARCHITECTURE_GAP': 133, 'INPUT_SOURCE_GAP': 34, 'AUTHORITY_GAP': 4},
    'auto_remediable_count': 0,
    'implementation_gap_count': 0,
}:
    die('review baseline drift')

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
        die('review category falsely auto-remediable:' + key)

shared_review = reviews['SHARED_OWNER_AUTHORITY_UNRESOLVED']
if shared_review.get('authority_ref') != 'ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or shared_review.get('consumers') != SHARED_CONSUMERS:
    die('functional review shared-owner identity/consumer drift')
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
if exit_gate.get('gate_uid') != 'ALL_REQUIRED_PAGES_STAGE2_CLOSED' or exit_gate.get('result') != 'BLOCKED' or exit_gate.get('functional_completion') is not False:
    die('Stage-02 exit gate false closure')
if exit_gate.get('website_construction_allowed') is not False or exit_gate.get('deployment_allowed') is not False:
    die('website/deployment must remain blocked')

ss = S.get('summary') or {}
if ss.get('transition_count') != 10 or ss.get('unresolved_required_field_total') != 50 or ss.get('resolved_required_field_total') != 0:
    die('transition ledger resolution drift')

if SH.get('artifact_type') != 'SHARED_OWNER_PORT_MAP' or SH.get('status') != 'OPEN_BLOCKING_AUTHORITY_GAP':
    die('shared owner map identity/status drift')
auth_gap = SH.get('authority_gap') or {}
if auth_gap.get('gap_uid') != 'GAP-006' or auth_gap.get('authority_ref') != 'ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or auth_gap.get('consumer_count') != 4:
    die('shared owner authority gap identity/count drift')
consumers = SH.get('consumers') or []
if [r.get('action_uid') for r in consumers] != SHARED_CONSUMERS:
    die('shared owner map consumer set/order drift')
for row in consumers:
    if row.get('status') != 'UNRESOLVED_AUTHORITY_GAP':
        die('shared owner consumer falsely resolved:' + str(row.get('action_uid')))
    if any(row.get(k) is not None for k in ('resolved_owner_uid', 'resolved_operation_uid', 'resolved_port_uid')):
        die('shared owner consumer contains inferred resolution:' + str(row.get('action_uid')))

if A.get('artifact_type') != 'ASYNC_PROVIDER_CONTRACT' or A.get('status') != 'OPEN_BLOCKING_AUTHORITY_AND_LIFECYCLE_GAPS':
    die('async provider contract identity/status drift')
if A.get('required_lifecycle_fields') != ASYNC_FIELDS:
    die('async provider required lifecycle field drift')
for page in ('CORE-01', 'ASSET-01'):
    row = (A.get('pages') or {}).get(page) or {}
    if row.get('resolved_lifecycle_fields') != {} or row.get('unresolved_lifecycle_fields') != ASYNC_FIELDS:
        die('async provider lifecycle falsely resolved:' + page)
if A.get('functional_completion_claim') is not False or A.get('website_construction_allowed') is not False or A.get('deployment_allowed') is not False:
    die('async provider false completion/enablement')

for page_spec, page_uid, gap_total in ((C, 'CORE-01', 45), (AS, 'ASSET-01', 126)):
    if page_spec.get('artifact_type') != 'PAGE_CONSTRUCTION_SPEC_PACKAGE' or page_spec.get('page_uid') != page_uid or page_spec.get('status') != 'OPEN_BLOCKING_GAPS':
        die('page construction spec identity/status drift:' + page_uid)
    if (page_spec.get('gap_materialization') or {}).get('page_gap_total') != gap_total:
        die('page construction spec gap total drift:' + page_uid)
    gate = page_spec.get('construction_gate') or {}
    if gate.get('ready_for_implementation') is not False or gate.get('website_construction_allowed') is not False or gate.get('deployment_allowed') is not False:
        die('page construction incorrectly enabled:' + page_uid)
    if page_spec.get('ai_autofill_used') is not False or page_spec.get('inference_used') is not False or page_spec.get('functional_completion_claim') is not False:
        die('page construction spec false inference/completion:' + page_uid)

if 'PAGE_FUNCTIONAL_REVIEW_EVIDENCE' not in (P.get('current_artifacts') or []):
    die('artifact plan missing required PAGE_FUNCTIONAL_REVIEW_EVIDENCE registration')

print('PASS: PAGE_FUNCTIONAL_REVIEW_EVIDENCE physically exists and reviews all 171 Stage-02 gaps')
print('PASS: 0/171 gaps are falsely reclassified as auto-remediable; all 171 remain blocking under v2.1.12 authority rules')
print('PASS: 4 shared-owner consumers retain null owner/operation/port and 50 transition architecture fields remain unresolved')
print('PASS: both async-provider lifecycle contracts retain all 12 fields unresolved; no inferred lifecycle defaults')
print('PASS: ALL_REQUIRED_PAGES_STAGE2_CLOSED remains BLOCKED; website construction and deployment remain forbidden')
