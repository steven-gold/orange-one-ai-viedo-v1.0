#!/usr/bin/env python3
from pathlib import Path
import subprocess
import yaml

root = Path('.')
run = root / '00_SOURCE_INTAKE/fresh_run_003'
ledger_path = run / '04_PAGE_FUNCTIONAL_CONTRACT/BLOCKER_LEDGER.yaml'
gap_path = run / '04_PAGE_FUNCTIONAL_CONTRACT/FUNCTIONAL_CHAIN_GAP_LEDGER.yaml'
review_path = run / '00_SOURCE_INTAKE/evidence/PAGE_FUNCTIONAL_REVIEW_EVIDENCE.yaml'
shared_path = run / '04_PAGE_FUNCTIONAL_CONTRACT/SHARED_OWNER_PORT_MAP.yaml'

EXPECTED_RECEIPT = {
    'provider': 'GITHUB_ACTIONS',
    'repository_or_project': 'steven-gold/orange-one-ai-viedo-v1.0',
    'head_sha': '546e3826934eefc33aa1e11ba018a9aeb706f57f',
    'run_id': 34766220936,
    'job_denominator': '19/19',
    'conclusion': 'SUCCESS',
}
EXPECTED_BLOCKERS = {
    'STAGE2-BLK-INPUT-CONTRACT-001': ('INPUT_SOURCE_GAP', 34),
    'STAGE2-BLK-ARCH-CONTRACT-001': ('ARCHITECTURE_GAP', 133),
    'STAGE2-BLK-GAP006-SHARED-AUTHORITY-001': ('AUTHORITY_GAP', 4),
}
SHARED_CONSUMERS = [
    'ASSET-01-ACT-CORRECTION-GENERATE',
    'ASSET-01-ACT-CORRECTION-APPROVE',
    'ASSET-01-ACT-RESTORE-AS-NEW',
    'ASSET-01-ACT-VERSION-LOCK',
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
}
for path, blob in locked.items():
    if gitobj(path) != blob:
        die('immutable predecessor drift:' + str(path))

B = load(ledger_path)
G = load(gap_path)
R = load(review_path)
SH = load(shared_path)

if B.get('artifact_type') != 'BLOCKER_LEDGER' or B.get('governance_overlay') != 'v2.1.12' or B.get('stage_uid') != 'STAGE-02':
    die('blocker ledger identity/governance drift')
if B.get('status') != 'OPEN_BLOCKERS':
    die('blocker ledger must remain OPEN_BLOCKERS while 171 gaps remain')
if B.get('completed_gate_receipt') != EXPECTED_RECEIPT:
    die('blocker ledger completed-gate receipt drift')
source = B.get('source_gap_ledger') or {}
if source.get('git_blob') != '093c72a8e3227c1228180a29586980ab5e8f85cd' or source.get('gap_total') != 171:
    die('blocker ledger source gap identity/count drift')
if source.get('classes') != {'ARCHITECTURE_GAP': 133, 'INPUT_SOURCE_GAP': 34, 'AUTHORITY_GAP': 4}:
    die('blocker ledger source class drift')
review_ref = B.get('functional_review_evidence') or {}
if review_ref.get('git_blob') != '7f7c821c9f037d29ac576bd1f944a881329666ef' or review_ref.get('reviewed_gap_total') != 171 or review_ref.get('safely_auto_remediable_total') != 0:
    die('blocker ledger functional review reference drift')

blocks = B.get('blockers') or []
if len(blocks) != 3 or len({r.get('blocker_uid') for r in blocks}) != 3:
    die('blocker ledger exact blocker cardinality drift')
by_uid = {r.get('blocker_uid'): r for r in blocks}
if set(by_uid) != set(EXPECTED_BLOCKERS):
    die('blocker ledger UID set drift')
for uid, (klass, count) in EXPECTED_BLOCKERS.items():
    row = by_uid[uid]
    for field in ('target_uid','scope','severity','opened_at','reason','impact','unlock_condition','current_status','completed_gates','missing_gates','exact_resume_point'):
        if row.get(field) in (None, '', []):
            die(f'{uid} required blocker field missing:{field}')
    if row.get('gap_class') != klass or row.get('gap_count') != count:
        die(uid + ' gap class/count drift')
    if row.get('target_uid') != 'ALL_REQUIRED_PAGES_STAGE2_CLOSED' or row.get('severity') != 'BLOCKING' or row.get('current_status') != 'OPEN_BLOCKING':
        die(uid + ' target/severity/status drift')
    if row.get('resolved_evidence') is not None:
        die(uid + ' falsely resolved')
    if row.get('missing_gates') != ['ALL_REQUIRED_PAGES_STAGE2_CLOSED']:
        die(uid + ' missing gate drift')

inp = by_uid['STAGE2-BLK-INPUT-CONTRACT-001']
if inp.get('owner') is not None or inp.get('owner_status') != 'UNRESOLVED_FORMAL_CONTRACT_OWNER' or inp.get('source_gap_category') != 'PAYLOAD_INPUT_CONTRACT_MISSING':
    die('input contract blocker owner/category drift')
arch = by_uid['STAGE2-BLK-ARCH-CONTRACT-001']
if arch.get('owner') is not None or arch.get('owner_status') != 'UNRESOLVED_FORMAL_CONTRACT_OWNER':
    die('architecture blocker owner must remain unresolved')
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
if ext.get('owner') != 'ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or ext.get('authority_ref') != 'ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or ext.get('gap_uid') != 'GAP-006':
    die('external authority blocker identity drift')
if ext.get('owner_status') != 'EXTERNAL_AUTHORITY_REFERENCE_UNRESOLVED' or ext.get('consumers') != SHARED_CONSUMERS:
    die('external authority blocker consumer/status drift')

# Cross-check source ledgers remain exactly open and no blocker double-count is hidden.
gs = G.get('summary') or {}
if gs.get('total') != 171 or gs.get('classes') != {'ARCHITECTURE_GAP': 133, 'INPUT_SOURCE_GAP': 34, 'AUTHORITY_GAP': 4}:
    die('source functional gap ledger drift')
rr = R.get('resolution_summary') or {}
if rr.get('reviewed_gap_total') != 171 or rr.get('safely_auto_remediable_total') != 0 or rr.get('remains_blocking_total') != 171:
    die('functional review resolution summary drift')
if (R.get('stage2_exit_gate') or {}).get('result') != 'BLOCKED':
    die('functional review exit gate false closure')
if (SH.get('authority_gap') or {}).get('consumer_count') != 4:
    die('shared owner source consumer count drift')
for row in SH.get('consumers') or []:
    if any(row.get(k) is not None for k in ('resolved_owner_uid','resolved_operation_uid','resolved_port_uid')):
        die('shared owner source contains inferred resolution')

summary = B.get('summary') or {}
if summary != {
    'blocker_count': 3,
    'open_blocker_count': 3,
    'resolved_blocker_count': 0,
    'blocked_gap_total': 171,
    'input_contract_gap_count': 34,
    'architecture_contract_gap_count': 133,
    'external_authority_gap_count': 4,
    'functional_completion': False,
    'stage2_exit_gate': 'BLOCKED',
    'website_construction_allowed': False,
    'deployment_allowed': False,
}:
    die('blocker ledger summary drift')
policy = B.get('policy') or {}
if policy.get('ai_guess_or_default_substitution') != 'FORBIDDEN' or policy.get('raw_source_mutation_allowed') is not False or policy.get('local_duplicate_shared_owner_definition') != 'FORBIDDEN':
    die('blocker ledger fail-closed policy drift')

print('PASS: Stage-02 Blocker Ledger formalizes exactly 3 legal blockers covering 171/171 open gaps')
print('PASS: 34 Input Contract + 133 Architecture Contract + 4 GAP-006 Authority gaps remain explicitly blocking with exact resume points')
print('PASS: no blocker is falsely resolved; shared-owner bindings remain null; Stage-02 exit/website/deployment remain blocked')
