#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
import yaml

root = Path('.')
run = root / '00_SOURCE_INTAKE/fresh_run_003'

LEDGERS = {
    'RUN_MANIFEST': run / 'RUN_MANIFEST.yaml',
    'ARTIFACT_PLAN': run / 'ARTIFACT_PLAN.yaml',
    'EXECUTION_STATE': run / 'EXECUTION_STATE.yaml',
    'GOVERNANCE_CURRENT': root / 'GOVERNANCE_CURRENT.yaml',
    'REBUILD_BRANCH_BASELINE': root / 'REBUILD_BRANCH_BASELINE.yaml',
    'GOVERNANCE_STAGE_LOCK': root / '11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml',
    'SEALED_GOVERNANCE_TEST_BASELINE': root / '11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml',
}

EXPECTED_STATE = 'STAGE2_FUNCTIONAL_REVIEW_COMPLETE_BLOCKED_BY_FORMAL_CONTRACT_AND_AUTHORITY'
EXPECTED_REVIEW = {
    'provider': 'GITHUB_ACTIONS',
    'repository_or_project': 'steven-gold/orange-one-ai-viedo-v1.0',
    'head_sha': '546e3826934eefc33aa1e11ba018a9aeb706f57f',
    'run_id': 34766220936,
    'job_denominator': '19/19',
    'conclusion': 'SUCCESS',
}
EXPECTED_BLOCKER = {
    'provider': 'GITHUB_ACTIONS',
    'repository_or_project': 'steven-gold/orange-one-ai-viedo-v1.0',
    'head_sha': '42736f94524f7e46d280271b1d15dd1221a9af8d',
    'run_id': 34766464982,
    'job_denominator': '20/20',
    'conclusion': 'SUCCESS',
}
EXPECTED_IDENTITY = (
    '2d6602b20983a9764c2f1496f36ab20a2f0ebcd73826492c27ba67159f5ef3df',
    '4c013cfc1a91142a8b4ce44830ef467c5c960f56b136a75ff670729a523f71e3',
    '512eb9178054d26fce807ae8b7617f06818788e23260b9f104bbb588bd5d0ee9',
)


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


def run_validator(path):
    result = subprocess.run([sys.executable, path], text=True, capture_output=True)
    if result.returncode:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        die('predecessor Stage-02 validator failed: ' + path)


# The synchronization gate is additive: existing review/blocker validation must still pass.
for validator in (
    'governance/ci/validate_current_stage2_functional_review_evidence.py',
    'governance/ci/validate_current_stage2_blocker_ledger.py',
):
    run_validator(validator)

D = {name: load(path) for name, path in LEDGERS.items()}
R = D['RUN_MANIFEST']
P = D['ARTIFACT_PLAN']
E = D['EXECUTION_STATE']
G = D['GOVERNANCE_CURRENT']
B = D['REBUILD_BRANCH_BASELINE']
L = D['GOVERNANCE_STAGE_LOCK']
S = D['SEALED_GOVERNANCE_TEST_BASELINE']

# All Current ledgers must carry the same immutable 19/19 review and 20/20 blocker receipts.
head = subprocess.run(['git', 'rev-parse', 'HEAD'], text=True, capture_output=True, check=True).stdout.strip()
for name, doc in D.items():
    receipts = doc.get('terminal_receipts') or {}
    if receipts.get('stage2_functional_review') != EXPECTED_REVIEW:
        die(f'{name} Stage-02 functional review receipt drift')
    if receipts.get('stage2_blocker_ledger') != EXPECTED_BLOCKER:
        die(f'{name} Stage-02 blocker receipt drift')
    for receipt_name, receipt in receipts.items():
        if isinstance(receipt, dict) and receipt.get('head_sha') == head:
            die(f'{name} illegal same-commit self receipt: {receipt_name}')
    pointer = doc.get('current_stage2_blocker_receipt')
    if pointer is not None:
        if pointer.get('mode') != 'EXTERNAL_IMMUTABLE_RECEIPT' or pointer.get('required') is not True:
            die(f'{name} Stage-02 blocker receipt mode drift')
        if pointer.get('embedded_run_id') != 34766464982 or pointer.get('same_commit_self_write') != 'FORBIDDEN':
            die(f'{name} Stage-02 blocker receipt pointer drift')

# Governance authority identity must stay exact while Current execution advances.
ri = R.get('governance') or {}
if (ri.get('current_package_sha256'), ri.get('current_external_trust_root_sha256'), ri.get('current_semantic_authority_content_hash')) != EXPECTED_IDENTITY:
    die('RUN_MANIFEST v2.1.12 identity drift')
pi = P.get('governance_v212') or {}
if (pi.get('package_sha256'), pi.get('external_trust_root_sha256'), pi.get('semantic_authority_content_hash')) != EXPECTED_IDENTITY:
    die('ARTIFACT_PLAN v2.1.12 identity drift')
gi = G.get('normative_authority') or {}
if gi.get('version') != 'v2.1.12' or (gi.get('package_sha256'), gi.get('external_trust_root_sha256'), gi.get('semantic_authority_content_hash')) != EXPECTED_IDENTITY:
    die('GOVERNANCE_CURRENT authority identity drift')
bi = B.get('governance_test') or {}
if bi.get('version') != 'v2.1.12' or (bi.get('package_sha256'), bi.get('external_trust_root_sha256'), bi.get('semantic_authority_content_hash')) != EXPECTED_IDENTITY:
    die('REBUILD_BRANCH_BASELINE authority identity drift')
li = L.get('current_test_authority') or {}
if li.get('version') != 'v2.1.12' or (li.get('package_sha256'), li.get('external_trust_root_sha256'), li.get('semantic_authority_content_hash')) != EXPECTED_IDENTITY:
    die('GOVERNANCE_STAGE_LOCK authority identity drift')
si = S.get('sealed_governance') or {}
if si.get('version') != 'v2.1.12' or (si.get('package_sha256'), si.get('external_trust_root_sha256'), si.get('semantic_authority_content_hash')) != EXPECTED_IDENTITY:
    die('SEALED baseline authority identity drift')
if E.get('governance_candidate_overlay') != 'v2.1.12':
    die('EXECUTION_STATE governance overlay drift')

# Current state/status labels are successor-monotonic and must describe blocking, never closure.
if R.get('status') != EXPECTED_STATE:
    die('RUN_MANIFEST current status drift')
if P.get('current_step') != EXPECTED_STATE or P.get('status') != EXPECTED_STATE:
    die('ARTIFACT_PLAN current status drift')
if E.get('state') != EXPECTED_STATE or E.get('last_result') != EXPECTED_STATE:
    die('EXECUTION_STATE current status drift')
if G.get('status') != EXPECTED_STATE or (G.get('current_execution') or {}).get('state') != EXPECTED_STATE:
    die('GOVERNANCE_CURRENT current status drift')
if B.get('status') != EXPECTED_STATE:
    die('REBUILD_BRANCH_BASELINE current status drift')
if L.get('status') != EXPECTED_STATE:
    die('GOVERNANCE_STAGE_LOCK current status drift')
if S.get('status') != 'SEALED_V2_1_12_STAGE2_FUNCTIONAL_REVIEW_COMPLETE_BLOCKED' or (S.get('execution_checkpoint') or {}).get('state') != EXPECTED_STATE:
    die('SEALED baseline current status drift')

# Cross-ledger Stage-02 counts and blocked exit gate must be identical.
r = R.get('stage2_contract') or {}
if (r.get('functional_gap_total'), r.get('architecture_gap_total'), r.get('input_source_gap_total'), r.get('authority_gap_total'), r.get('blocker_count')) != (171, 133, 34, 4, 3):
    die('RUN_MANIFEST Stage-02 counts drift')
if r.get('exit_gate') != 'ALL_REQUIRED_PAGES_STAGE2_CLOSED' or r.get('exit_gate_result') != 'BLOCKED' or r.get('completion_claim') is not False:
    die('RUN_MANIFEST false Stage-02 closure')

p = P.get('stage2_functional_chain_materialization') or {}
if (p.get('functional_gap_total'), p.get('architecture_gap_total'), p.get('input_source_gap_total'), p.get('authority_gap_total')) != (171, 133, 34, 4):
    die('ARTIFACT_PLAN Stage-02 gap counts drift')
pb = p.get('blocker_ledger') or {}
if pb.get('blocker_count') != 3 or pb.get('blocked_gap_total') != 171 or pb.get('status') != 'OPEN_BLOCKERS':
    die('ARTIFACT_PLAN blocker projection drift')
if p.get('exit_gate_result') != 'BLOCKED' or p.get('functional_completion_claim') is not False or p.get('website_construction_allowed') is not False or p.get('deployment_allowed') is not False:
    die('ARTIFACT_PLAN false Stage-02 enablement')
if 'BLOCKER_LEDGER' not in (P.get('current_artifacts') or []):
    die('ARTIFACT_PLAN missing BLOCKER_LEDGER registration')

if (E.get('stage2_gap_total'), E.get('stage2_architecture_gap_total'), E.get('stage2_input_source_gap_total'), E.get('stage2_authority_gap_total'), E.get('stage2_blocker_count')) != (171, 133, 34, 4, 3):
    die('EXECUTION_STATE Stage-02 counts drift')
if E.get('stage2_reviewed_gap_total') != 171 or E.get('stage2_safely_auto_remediable_total') != 0:
    die('EXECUTION_STATE review result drift')
if E.get('stage2_exit_gate') != 'BLOCKED' or E.get('stage2_functional_completion') is not False or E.get('website_construction_started') is not False or E.get('deployment_started') is not False:
    die('EXECUTION_STATE false Stage-02 enablement')
ci = E.get('github_ci') or {}
if ci.get('stage2_blocker_ledger_run_id') != 34766464982 or ci.get('stage2_blocker_ledger_result') != 'SUCCESS_20_OF_20' or ci.get('current_stage2_blocker_ledger_gate') != 'SUCCESS_EXTERNAL_RECEIPT':
    die('EXECUTION_STATE 20/20 CI projection drift')

gc = G.get('current_execution') or {}
if (gc.get('stage2_gap_total'), gc.get('stage2_blocker_count'), gc.get('stage2_exit_gate')) != (171, 3, 'BLOCKED'):
    die('GOVERNANCE_CURRENT Stage-02 projection drift')
if gc.get('stage2_functional_completion') is not False or gc.get('website_construction_started') is not False or gc.get('deployment_started') is not False:
    die('GOVERNANCE_CURRENT false Stage-02 enablement')
gf = G.get('stage2_functional_contract') or {}
if gf.get('open_gap_total') != 171 or gf.get('blocker_count') != 3 or gf.get('exit_gate_result') != 'BLOCKED' or gf.get('functional_completion_claim') is not False or gf.get('website_construction_allowed') is not False or gf.get('deployment_allowed') is not False:
    die('GOVERNANCE_CURRENT functional contract drift')

bw = B.get('workspace_progress') or {}
if (bw.get('stage2_open_gap_total'), bw.get('stage2_blocker_count'), bw.get('stage2_exit_gate')) != (171, 3, 'BLOCKED'):
    die('REBUILD_BRANCH_BASELINE Stage-02 projection drift')
if bw.get('stage2_functional_completion') is not False or bw.get('website_construction_started') is not False or bw.get('deployment_started') is not False:
    die('REBUILD_BRANCH_BASELINE false Stage-02 enablement')
bc = B.get('stage2_current') or {}
if bc.get('open_gap_total') != 171 or bc.get('blocker_count') != 3 or bc.get('exit_gate_result') != 'BLOCKED' or bc.get('completion_claim') is not False or bc.get('website_construction_allowed') is not False or bc.get('deployment_allowed') is not False:
    die('REBUILD_BRANCH_BASELINE Stage-02 current drift')

lc = L.get('current_execution') or {}
if (lc.get('stage2_gap_total'), lc.get('stage2_blocker_count'), lc.get('stage2_exit_gate')) != (171, 3, 'BLOCKED'):
    die('GOVERNANCE_STAGE_LOCK Stage-02 projection drift')
if lc.get('stage2_functional_completion') is not False or lc.get('website_construction_started') is not False or lc.get('deployment_started') is not False:
    die('GOVERNANCE_STAGE_LOCK false Stage-02 enablement')
ll = L.get('stage2_contract_lock') or {}
if ll.get('open_gap_total') != 171 or ll.get('blocker_count') != 3 or ll.get('exit_gate_result') != 'BLOCKED' or ll.get('functional_completion_claim') is not False or ll.get('website_construction') != 'FORBIDDEN' or ll.get('deployment') != 'FORBIDDEN':
    die('GOVERNANCE_STAGE_LOCK Stage-02 contract lock drift')

sc = S.get('execution_checkpoint') or {}
if (sc.get('stage2_open_gap_total'), sc.get('stage2_blocker_count'), sc.get('stage2_exit_gate')) != (171, 3, 'BLOCKED') or sc.get('stage2_functional_completion') is not False:
    die('SEALED baseline Stage-02 checkpoint drift')
ss = S.get('stage2_current') or {}
if ss.get('open_gap_total') != 171 or ss.get('blocker_count') != 3 or ss.get('exit_gate_result') != 'BLOCKED' or ss.get('functional_completion_claim') is not False or ss.get('website_construction_allowed') is not False or ss.get('deployment_allowed') is not False:
    die('SEALED baseline Stage-02 current drift')

# The original 8 unresolved external Authority references remain preserved; this stage did not resolve them synthetically.
if (R.get('blueprint_binding_contract') or {}).get('unresolved_authority_gap_universe') != 8 or (R.get('blueprint_binding_contract') or {}).get('authority_resolution_performed') is not False:
    die('RUN_MANIFEST external Authority preservation drift')
if (P.get('classification_materialization') or {}).get('unresolved_authority_gaps_preserved') != 8:
    die('ARTIFACT_PLAN external Authority universe drift')
if E.get('unresolved_authority_gap_count') != 8 or gc.get('unresolved_authority_gap_count') != 8 or lc.get('unresolved_authority_gap_count') != 8:
    die('Current ledger external Authority universe drift')

print('PASS: seven Current ledgers carry identical immutable Stage-02 review 19/19 and blocker 20/20 receipts')
print('PASS: v2.1.12 authority identity and the 8 unresolved external Authority references remain preserved')
print('PASS: 171 gaps = 133 architecture + 34 input-source + 4 authority; exactly 3 formal blockers remain open')
print('PASS: ALL_REQUIRED_PAGES_STAGE2_CLOSED remains BLOCKED; functional completion, website construction and deployment remain false/forbidden')
