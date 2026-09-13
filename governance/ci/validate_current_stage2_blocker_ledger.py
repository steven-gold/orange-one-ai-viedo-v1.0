#!/usr/bin/env python3
from pathlib import Path
import subprocess
import yaml

root = Path('.')
run = root / '00_SOURCE_INTAKE/fresh_run_003'
base = run / '04_PAGE_FUNCTIONAL_CONTRACT'
ledger_path = base / 'BLOCKER_LEDGER.yaml'
gap_path = base / 'FUNCTIONAL_CHAIN_GAP_LEDGER.yaml'
review_path = run / '00_SOURCE_INTAKE/evidence/PAGE_FUNCTIONAL_REVIEW_EVIDENCE.yaml'
shared_path = base / 'SHARED_OWNER_PORT_MAP.yaml'
async_path = base / 'ASYNC_PROVIDER_CONTRACT.yaml'
source_dep_path = run / '00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml'

EXPECTED_REVIEW_RECEIPT = {
    'provider': 'GITHUB_ACTIONS',
    'repository_or_project': 'steven-gold/orange-one-ai-viedo-v1.0',
    'head_sha': '546e3826934eefc33aa1e11ba018a9aeb706f57f',
    'run_id': 34766220936,
    'job_denominator': '19/19',
    'conclusion': 'SUCCESS',
}
EXPECTED_R1_RECEIPT = {
    'revision': 'R1_FUNCTIONAL_GAP_ONLY',
    'disposition': 'SUPERSEDED_BY_R2_COVERAGE_CORRECTION',
    'provider': 'GITHUB_ACTIONS',
    'repository_or_project': 'steven-gold/orange-one-ai-viedo-v1.0',
    'head_sha': '42736f94524f7e46d280271b1d15dd1221a9af8d',
    'run_id': 34766464982,
    'job_denominator': '20/20',
    'conclusion': 'SUCCESS',
}
SHARED_CONSUMERS = [
    'ASSET-01-ACT-CORRECTION-GENERATE',
    'ASSET-01-ACT-CORRECTION-APPROVE',
    'ASSET-01-ACT-RESTORE-AS-NEW',
    'ASSET-01-ACT-VERSION-LOCK',
]
ASYNC_FIELDS = [
    'request_identity','input_fingerprint','idempotency','queued','running','succeeded','failed','cancel',
    'retry_eligibility','callback_result_provenance','output_persistence','audit_correlation',
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


locked = {
    run / '00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml': '9490f3bcc28c5511bc04d6c3ce53c026e3c4667f',
    run / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml': '9668e2307c722ea4cf64f93f07c92da1b3abcc28',
    gap_path: '093c72a8e3227c1228180a29586980ab5e8f85cd',
    review_path: '7f7c821c9f037d29ac576bd1f944a881329666ef',
    async_path: '2aa1db9a2ec013dc2820b83a010464fe40facb0f',
    source_dep_path: '14d99735dcb0f9647c7906592233ef1bee0fe425',
}
for path, blob in locked.items():
    if gitobj(path) != blob:
        die('immutable predecessor drift:' + str(path))

B = load(ledger_path)
G = load(gap_path)
R = load(review_path)
SH = load(shared_path)
A = load(async_path)
SD = load(source_dep_path)

if B.get('artifact_type') != 'BLOCKER_LEDGER' or B.get('artifact_uid') != 'FRESH-RUN-003-STAGE2-BLOCKER-LEDGER-V212-R2':
    die('blocker ledger R2 identity drift')
if B.get('coverage_revision') != 'R2_ASYNC_PROVIDER_REQUIRED_OUTPUT_INCLUDED' or B.get('status') != 'OPEN_BLOCKERS':
    die('blocker ledger R2 coverage/status drift')
if B.get('completed_gate_receipt') != EXPECTED_REVIEW_RECEIPT:
    die('blocker ledger review receipt drift')
if B.get('predecessor_blocker_ledger_receipt') != EXPECTED_R1_RECEIPT:
    die('R1 blocker receipt lineage drift')

source = B.get('source_gap_ledger') or {}
if source.get('git_blob') != '093c72a8e3227c1228180a29586980ab5e8f85cd' or source.get('gap_total') != 171:
    die('functional gap baseline drift')
if source.get('classes') != {'ARCHITECTURE_GAP': 133, 'INPUT_SOURCE_GAP': 34, 'AUTHORITY_GAP': 4}:
    die('functional gap class drift')
review_ref = B.get('functional_review_evidence') or {}
if review_ref.get('git_blob') != '7f7c821c9f037d29ac576bd1f944a881329666ef' or review_ref.get('reviewed_gap_total') != 171 or review_ref.get('safely_auto_remediable_total') != 0:
    die('functional review reference drift')

ro = (B.get('required_output_blocker_sources') or {}).get('async_provider_contract') or {}
if ro.get('ref') != '04_PAGE_FUNCTIONAL_CONTRACT/ASYNC_PROVIDER_CONTRACT.yaml' or ro.get('git_blob') != '2aa1db9a2ec013dc2820b83a010464fe40facb0f':
    die('async required-output source identity drift')
if ro.get('status') != 'OPEN_BLOCKING_AUTHORITY_AND_LIFECYCLE_GAPS' or ro.get('unresolved_lifecycle_binding_total') != 24:
    die('async required-output blocker state drift')
if ro.get('unique_external_authority_gap_uids') != ['GAP-005','GAP-008'] or ro.get('coverage_in_171_functional_gap_ledger') is not False:
    die('async required-output coverage classification drift')

blocks = B.get('blockers') or []
if len(blocks) != 4 or len({r.get('blocker_uid') for r in blocks}) != 4:
    die('blocker ledger exact cardinality must be 4')
by_uid = {r.get('blocker_uid'): r for r in blocks}
expected_uids = {
    'STAGE2-BLK-INPUT-CONTRACT-001',
    'STAGE2-BLK-ARCH-CONTRACT-001',
    'STAGE2-BLK-GAP006-SHARED-AUTHORITY-001',
    'STAGE2-BLK-ASYNC-PROVIDER-LIFECYCLE-001',
}
if set(by_uid) != expected_uids:
    die('blocker UID universe drift')
for uid, row in by_uid.items():
    for field in ('target_uid','scope','severity','opened_at','reason','impact','unlock_condition','current_status','completed_gates','missing_gates','exact_resume_point'):
        if row.get(field) in (None, '', []):
            die(f'{uid} required blocker field missing:{field}')
    if row.get('target_uid') != 'ALL_REQUIRED_PAGES_STAGE2_CLOSED' or row.get('severity') != 'BLOCKING' or row.get('current_status') != 'OPEN_BLOCKING':
        die(uid + ' target/severity/status drift')
    if row.get('resolved_evidence') is not None or row.get('missing_gates') != ['ALL_REQUIRED_PAGES_STAGE2_CLOSED']:
        die(uid + ' false resolution/missing-gate drift')

inp = by_uid['STAGE2-BLK-INPUT-CONTRACT-001']
if (inp.get('gap_class'), inp.get('gap_count'), inp.get('source_gap_category')) != ('INPUT_SOURCE_GAP',34,'PAYLOAD_INPUT_CONTRACT_MISSING'):
    die('input blocker drift')
arch = by_uid['STAGE2-BLK-ARCH-CONTRACT-001']
if (arch.get('gap_class'), arch.get('gap_count')) != ('ARCHITECTURE_GAP',133):
    die('architecture blocker drift')
if arch.get('source_gap_categories') != {
    'STATE_TRANSITION_LEDGER_FIELD_MISSING': 50,
    'FAILURE_STATE_ERROR_BINDING_MISSING': 44,
    'POST_ACTION_VALIDATION_NODE_MISSING': 18,
    'AUDIT_EVENT_NODE_MISSING': 13,
    'SUCCESS_NEXT_STATE_BINDING_MISSING': 7,
    'ACTION_WITHOUT_CONTROL_OR_TRIGGER': 1,
}:
    die('architecture blocker category decomposition drift')
ext = by_uid['STAGE2-BLK-GAP006-SHARED-AUTHORITY-001']
if (ext.get('gap_class'), ext.get('gap_uid'), ext.get('gap_count'), ext.get('authority_ref')) != ('AUTHORITY_GAP','GAP-006',4,'ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY'):
    die('GAP-006 blocker drift')
if ext.get('consumers') != SHARED_CONSUMERS:
    die('GAP-006 consumer drift')

ap = by_uid['STAGE2-BLK-ASYNC-PROVIDER-LIFECYCLE-001']
if ap.get('source_required_output') != 'ASYNC_PROVIDER_CONTRACT' or ap.get('source_required_output_git_blob') != '2aa1db9a2ec013dc2820b83a010464fe40facb0f':
    die('async blocker source output drift')
if ap.get('covered_by_171_functional_gap_ledger') is not False or ap.get('unresolved_lifecycle_binding_count') != 24:
    die('async blocker denominator drift')
if ap.get('page_unresolved_lifecycle_binding_count') != {'CORE-01':12,'ASSET-01':12}:
    die('async blocker per-page denominator drift')
if ap.get('authority_gaps') != [
    {'gap_uid':'GAP-005','authority_ref':'ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT@V1.3','consumers':['CORE-01','ASSET-01']},
    {'gap_uid':'GAP-008','authority_ref':'ACPOS shared AI Router/Capability Assignment','consumers':['CORE-01']},
]:
    die('async blocker external Authority refs drift')

# Prove the fourth blocker is physically required by the canonical ASYNC_PROVIDER_CONTRACT and is not already in the 171 ledger.
if A.get('status') != 'OPEN_BLOCKING_AUTHORITY_AND_LIFECYCLE_GAPS' or A.get('required_lifecycle_fields') != ASYNC_FIELDS:
    die('async provider contract status/lifecycle schema drift')
pages = A.get('pages') or {}
if set(pages) != {'CORE-01','ASSET-01'}:
    die('async provider page universe drift')
for page in ('CORE-01','ASSET-01'):
    if pages[page].get('resolved_lifecycle_fields') != {} or pages[page].get('unresolved_lifecycle_fields') != ASYNC_FIELDS:
        die(page + ' async lifecycle is not exactly 12/12 unresolved')
core_refs = pages['CORE-01'].get('provider_authority_refs') or []
asset_refs = pages['ASSET-01'].get('provider_authority_refs') or []
if core_refs != [
    {'gap_uid':'GAP-005','authority_ref':'ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT@V1.3'},
    {'gap_uid':'GAP-008','authority_ref':'ACPOS shared AI Router/Capability Assignment'},
]:
    die('CORE async authority refs drift')
if asset_refs != [{'gap_uid':'GAP-005','authority_ref':'ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT@V1.3'}]:
    die('ASSET async authority refs drift')

cats = (G.get('summary') or {}).get('categories') or {}
if any(k in cats for k in ('ASYNC_PROVIDER_LIFECYCLE_MISSING','PROVIDER_AUTHORITY_UNRESOLVED','GAP-005','GAP-008')):
    die('async blocker was unexpectedly folded into 171 functional-gap denominator')
if (G.get('summary') or {}).get('total') != 171:
    die('171 functional-gap baseline changed')

source_gaps = {g.get('gap_uid'): g for g in SD.get('unresolved_authority_gaps') or []}
for uid, ref in {
    'GAP-005':'ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT@V1.3',
    'GAP-006':'ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY',
    'GAP-008':'ACPOS shared AI Router/Capability Assignment',
}.items():
    row = source_gaps.get(uid) or {}
    if row.get('authority_ref') != ref or row.get('disposition') != 'UNRESOLVED_AUTHORITY_GAP':
        die(uid + ' source Authority preservation drift')

if (SH.get('authority_gap') or {}).get('consumer_count') != 4:
    die('shared owner source consumer count drift')
for row in SH.get('consumers') or []:
    if any(row.get(k) is not None for k in ('resolved_owner_uid','resolved_operation_uid','resolved_port_uid')):
        die('shared owner source contains inferred resolution')
rr = R.get('resolution_summary') or {}
if rr.get('reviewed_gap_total') != 171 or rr.get('safely_auto_remediable_total') != 0 or rr.get('remains_blocking_total') != 171:
    die('functional review resolution summary drift')

summary = B.get('summary') or {}
expected_summary = {
    'blocker_count': 4,
    'open_blocker_count': 4,
    'resolved_blocker_count': 0,
    'blocked_gap_total': 171,
    'functional_gap_blocker_count': 3,
    'required_output_blocker_count': 1,
    'input_contract_gap_count': 34,
    'architecture_contract_gap_count': 133,
    'functional_authority_gap_count': 4,
    'async_provider_unresolved_lifecycle_binding_count': 24,
    'async_provider_external_authority_gap_uid_count': 2,
    'stage2_external_authority_gap_uids_affecting_blockers': ['GAP-005','GAP-006','GAP-008'],
    'functional_completion': False,
    'stage2_exit_gate': 'BLOCKED',
    'website_construction_allowed': False,
    'deployment_allowed': False,
}
if summary != expected_summary:
    die('blocker ledger R2 summary drift')
policy = B.get('policy') or {}
if policy.get('ai_guess_or_default_substitution') != 'FORBIDDEN' or policy.get('raw_source_mutation_allowed') is not False or policy.get('local_duplicate_shared_owner_definition') != 'FORBIDDEN':
    die('blocker ledger fail-closed policy drift')

print('PASS: Stage-02 Blocker Ledger R2 formalizes 4 blockers without changing the immutable 171 functional-gap denominator')
print('PASS: new blocker covers canonical ASYNC_PROVIDER_CONTRACT: GAP-005/GAP-008 plus 24 unresolved lifecycle bindings (12 per page)')
print('PASS: 171 functional gaps remain 133 architecture + 34 input + 4 GAP-006 action gaps; no double-count or inferred resolution')
print('PASS: all four blockers remain open; Stage-02 exit, website construction and deployment remain blocked')
