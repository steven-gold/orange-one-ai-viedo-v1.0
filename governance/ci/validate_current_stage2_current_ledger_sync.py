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
PENDING_STATE = 'STAGE2_BLOCKER_COVERAGE_R2_MATERIALIZED_PENDING_EXTERNAL_CI'
CLOSED_BLOCKED_STATE = 'STAGE2_FUNCTIONAL_REVIEW_COMPLETE_BLOCKED_BY_FORMAL_CONTRACT_AND_AUTHORITY'
SEALED_PENDING = 'SEALED_V2_1_12_STAGE2_BLOCKER_COVERAGE_R2_PENDING_CI'
SEALED_BLOCKED = 'SEALED_V2_1_12_STAGE2_FUNCTIONAL_REVIEW_COMPLETE_BLOCKED'
EXPECTED_REVIEW = {
    'provider':'GITHUB_ACTIONS','repository_or_project':'steven-gold/orange-one-ai-viedo-v1.0',
    'head_sha':'546e3826934eefc33aa1e11ba018a9aeb706f57f','run_id':34766220936,'job_denominator':'19/19','conclusion':'SUCCESS',
}
EXPECTED_R1_BLOCKER = {
    'provider':'GITHUB_ACTIONS','repository_or_project':'steven-gold/orange-one-ai-viedo-v1.0',
    'head_sha':'42736f94524f7e46d280271b1d15dd1221a9af8d','run_id':34766464982,'job_denominator':'20/20','conclusion':'SUCCESS',
}
EXPECTED_R1_SYNC = {
    'provider':'GITHUB_ACTIONS','repository_or_project':'steven-gold/orange-one-ai-viedo-v1.0',
    'head_sha':'92b4c2f148fbd5690eea03a0f554ba25ff1cffea','run_id':34768036053,'job_denominator':'21/21','conclusion':'SUCCESS',
}
EXPECTED_IDENTITY = (
    '2d6602b20983a9764c2f1496f36ab20a2f0ebcd73826492c27ba67159f5ef3df',
    '4c013cfc1a91142a8b4ce44830ef467c5c960f56b136a75ff670729a523f71e3',
    '512eb9178054d26fce807ae8b7617f06818788e23260b9f104bbb588bd5d0ee9',
)


def die(msg): raise SystemExit(msg)
def load(path):
    try: data=yaml.safe_load(path.read_text(encoding='utf-8'))
    except Exception as exc: die(f'parse failure {path}: {exc}')
    if not isinstance(data,dict): die(f'mapping required: {path}')
    return data

def run_validator(path):
    r=subprocess.run([sys.executable,path],text=True,capture_output=True)
    if r.returncode:
        print(r.stdout); print(r.stderr,file=sys.stderr); die('predecessor Stage-02 validator failed: '+path)

for validator in (
    'governance/ci/validate_current_stage2_functional_review_evidence.py',
    'governance/ci/validate_current_stage2_blocker_ledger.py',
): run_validator(validator)

D={name:load(path) for name,path in LEDGERS.items()}
R=D['RUN_MANIFEST']; P=D['ARTIFACT_PLAN']; E=D['EXECUTION_STATE']; G=D['GOVERNANCE_CURRENT']; B=D['REBUILD_BRANCH_BASELINE']; L=D['GOVERNANCE_STAGE_LOCK']; S=D['SEALED_GOVERNANCE_TEST_BASELINE']
head=subprocess.run(['git','rev-parse','HEAD'],text=True,capture_output=True,check=True).stdout.strip()

# All seven ledgers must preserve immutable R1 receipts after explicit R2 coverage correction.
for name,doc in D.items():
    receipts=doc.get('terminal_receipts') or {}
    if receipts.get('stage2_functional_review')!=EXPECTED_REVIEW: die(f'{name} review receipt drift')
    if receipts.get('stage2_blocker_ledger_r1')!=EXPECTED_R1_BLOCKER: die(f'{name} R1 blocker receipt drift')
    if receipts.get('stage2_current_ledger_sync_r1')!=EXPECTED_R1_SYNC: die(f'{name} R1 sync receipt drift')
    if 'stage2_blocker_ledger' in receipts: die(f'{name} ambiguous unsuffixed blocker receipt forbidden after R2')

# Candidate may be pending external CI or a later successor may project the prior R2 external receipt.
pointers=[]
for name,doc in D.items():
    ptr=doc.get('current_stage2_blocker_receipt') or {}
    if ptr.get('mode')!='EXTERNAL_IMMUTABLE_RECEIPT' or ptr.get('required') is not True or ptr.get('current_revision')!='R2_ASYNC_PROVIDER_REQUIRED_OUTPUT_INCLUDED' or ptr.get('same_commit_self_write')!='FORBIDDEN':
        die(f'{name} current R2 receipt pointer drift')
    pointers.append((name,ptr))
statuses={ptr.get('validation_status') for _,ptr in pointers}
if len(statuses)!=1: die('R2 receipt validation status cross-ledger drift')
receipt_status=statuses.pop()
if receipt_status not in {'PENDING_EXTERNAL_CI','SUCCESS_EXTERNAL_RECEIPT'}: die('illegal R2 receipt validation status')

if receipt_status=='PENDING_EXTERNAL_CI':
    for name,doc in D.items():
        ptr=doc.get('current_stage2_blocker_receipt') or {}; receipts=doc.get('terminal_receipts') or {}
        if ptr.get('embedded_run_id') is not None or ptr.get('predecessor_receipt_key')!='stage2_blocker_ledger_r1': die(f'{name} pending R2 pointer drift')
        if 'stage2_blocker_ledger_r2' in receipts: die(f'{name} pending R2 cannot carry terminal receipt')
else:
    canonical=None
    for name,doc in D.items():
        ptr=doc.get('current_stage2_blocker_receipt') or {}; receipts=doc.get('terminal_receipts') or {}; rr=receipts.get('stage2_blocker_ledger_r2')
        if not isinstance(rr,dict): die(f'{name} missing R2 terminal receipt')
        if set(('provider','repository_or_project','head_sha','run_id','job_denominator','conclusion'))-set(rr): die(f'{name} R2 terminal receipt fields missing')
        if rr.get('provider')!='GITHUB_ACTIONS' or rr.get('repository_or_project')!='steven-gold/orange-one-ai-viedo-v1.0' or rr.get('job_denominator')!='21/21' or rr.get('conclusion')!='SUCCESS': die(f'{name} R2 terminal receipt value drift')
        if not isinstance(rr.get('run_id'),int) or rr.get('head_sha')==head: die(f'{name} R2 receipt self-reference/identity invalid')
        if ptr.get('embedded_run_id')!=rr.get('run_id') or ptr.get('receipt_key')!='stage2_blocker_ledger_r2': die(f'{name} R2 receipt pointer mismatch')
        if canonical is None: canonical=rr
        elif rr!=canonical: die('R2 terminal receipt cross-ledger drift')

# v2.1.12 identity is unchanged.
ri=R.get('governance') or {}; pi=P.get('governance_v212') or {}; gi=G.get('normative_authority') or {}; bi=B.get('governance_test') or {}; li=L.get('current_test_authority') or {}; si=S.get('sealed_governance') or {}
if (ri.get('current_package_sha256'),ri.get('current_external_trust_root_sha256'),ri.get('current_semantic_authority_content_hash'))!=EXPECTED_IDENTITY: die('RUN_MANIFEST authority identity drift')
for label,d in [('ARTIFACT_PLAN',pi),('GOVERNANCE_CURRENT',gi),('REBUILD_BRANCH_BASELINE',bi),('GOVERNANCE_STAGE_LOCK',li),('SEALED_BASELINE',si)]:
    if (d.get('package_sha256'),d.get('external_trust_root_sha256'),d.get('semantic_authority_content_hash'))!=EXPECTED_IDENTITY: die(label+' authority identity drift')
if E.get('governance_candidate_overlay')!='v2.1.12': die('EXECUTION_STATE overlay drift')

# Cross-ledger blocker universe: 171 immutable functional gaps + one independent async required-output blocker = 4 blockers.
def assert_common_counts(label, gap, blockers, async_bindings):
    if (gap,blockers,async_bindings)!=(171,4,24): die(label+' Stage-02 blocker universe drift')

rc=R.get('stage2_contract') or {}; assert_common_counts('RUN_MANIFEST',rc.get('functional_gap_total'),rc.get('blocker_count'),rc.get('async_provider_unresolved_lifecycle_binding_count'))
pc=P.get('stage2_functional_chain_materialization') or {}; pb=pc.get('blocker_ledger') or {}; assert_common_counts('ARTIFACT_PLAN',pc.get('functional_gap_total'),pb.get('blocker_count'),pb.get('async_provider_unresolved_lifecycle_binding_count'))
assert_common_counts('EXECUTION_STATE',E.get('stage2_gap_total'),E.get('stage2_blocker_count'),E.get('stage2_async_provider_unresolved_lifecycle_binding_count'))
gc=G.get('current_execution') or {}; assert_common_counts('GOVERNANCE_CURRENT',gc.get('stage2_gap_total'),gc.get('stage2_blocker_count'),gc.get('stage2_async_provider_unresolved_lifecycle_binding_count'))
bw=B.get('workspace_progress') or {}; assert_common_counts('REBUILD_BRANCH_BASELINE',bw.get('stage2_open_gap_total'),bw.get('stage2_blocker_count'),bw.get('stage2_async_provider_unresolved_lifecycle_binding_count'))
lc=L.get('current_execution') or {}; assert_common_counts('GOVERNANCE_STAGE_LOCK',lc.get('stage2_gap_total'),lc.get('stage2_blocker_count'),lc.get('stage2_async_provider_unresolved_lifecycle_binding_count'))
sc=S.get('execution_checkpoint') or {}; assert_common_counts('SEALED_BASELINE',sc.get('stage2_open_gap_total'),sc.get('stage2_blocker_count'),sc.get('stage2_async_provider_unresolved_lifecycle_binding_count'))

for label,obj in [('RUN_MANIFEST',rc),('ARTIFACT_PLAN',pc),('GOVERNANCE_CURRENT',G.get('stage2_functional_contract') or {}),('REBUILD_BRANCH_BASELINE',B.get('stage2_current') or {}),('GOVERNANCE_STAGE_LOCK',L.get('stage2_contract_lock') or {}),('SEALED_BASELINE',S.get('stage2_current') or {})]:
    if obj.get('exit_gate_result')!='BLOCKED' or obj.get('website_construction_allowed',False) is not False and label not in {'GOVERNANCE_STAGE_LOCK'} or obj.get('deployment_allowed',False) is not False and label not in {'GOVERNANCE_STAGE_LOCK'}:
        die(label+' false Stage-02 enablement')
if E.get('stage2_exit_gate')!='BLOCKED' or E.get('stage2_functional_completion') is not False or E.get('website_construction_started') is not False or E.get('deployment_started') is not False: die('EXECUTION_STATE false Stage-02 enablement')
if (L.get('stage2_contract_lock') or {}).get('website_construction')!='FORBIDDEN' or (L.get('stage2_contract_lock') or {}).get('deployment')!='FORBIDDEN': die('stage lock false enablement')

# Pending vs externally-receipted state labels must be synchronized.
if receipt_status=='PENDING_EXTERNAL_CI':
    if R.get('status')!=PENDING_STATE or P.get('current_step')!=PENDING_STATE or P.get('status')!=PENDING_STATE or E.get('state')!=PENDING_STATE or E.get('last_result')!=PENDING_STATE or G.get('status')!=PENDING_STATE or (G.get('current_execution') or {}).get('state')!=PENDING_STATE or B.get('status')!=PENDING_STATE or L.get('status')!=PENDING_STATE or S.get('status')!=SEALED_PENDING or (S.get('execution_checkpoint') or {}).get('state')!=PENDING_STATE:
        die('R2 pending state label synchronization drift')
else:
    if R.get('status')!=CLOSED_BLOCKED_STATE or P.get('current_step')!=CLOSED_BLOCKED_STATE or P.get('status')!=CLOSED_BLOCKED_STATE or E.get('state')!=CLOSED_BLOCKED_STATE or E.get('last_result')!=CLOSED_BLOCKED_STATE or G.get('status')!=CLOSED_BLOCKED_STATE or (G.get('current_execution') or {}).get('state')!=CLOSED_BLOCKED_STATE or B.get('status')!=CLOSED_BLOCKED_STATE or L.get('status')!=CLOSED_BLOCKED_STATE or S.get('status')!=SEALED_BLOCKED or (S.get('execution_checkpoint') or {}).get('state')!=CLOSED_BLOCKED_STATE:
        die('R2 receipted state label synchronization drift')

# Eight original unresolved Authority refs remain; currently blocking Stage-02 external refs are GAP-005/006/008.
if (R.get('blueprint_binding_contract') or {}).get('unresolved_authority_gap_universe')!=8 or (R.get('blueprint_binding_contract') or {}).get('authority_resolution_performed') is not False: die('RUN_MANIFEST 8-ref preservation drift')
if (P.get('classification_materialization') or {}).get('unresolved_authority_gaps_preserved')!=8: die('ARTIFACT_PLAN 8-ref preservation drift')
if E.get('unresolved_authority_gap_count')!=8 or gc.get('unresolved_authority_gap_count')!=8 or lc.get('unresolved_authority_gap_count')!=8: die('Current ledger 8-ref preservation drift')
for label,obj in [('RUN_MANIFEST',rc),('ARTIFACT_PLAN',pb),('EXECUTION_STATE',E),('GOVERNANCE_CURRENT',gc),('REBUILD_BRANCH_BASELINE',bw),('GOVERNANCE_STAGE_LOCK',lc),('SEALED_BASELINE',sc)]:
    uids=obj.get('stage2_external_authority_gap_uids_affecting_blockers')
    if uids!=['GAP-005','GAP-006','GAP-008']: die(label+' Stage-02 external Authority blocker UID drift')

print('PASS: seven Current ledgers agree on R2 blocker universe: 171 functional gaps + 1 async required-output blocker = 4 blockers')
print('PASS: ASYNC_PROVIDER_CONTRACT contributes 24 unresolved lifecycle bindings and GAP-005/GAP-008 without altering the 171 denominator')
print('PASS: R1 20/20 blocker receipt and R1 21/21 ledger-sync receipt remain immutable predecessor evidence')
print('PASS: R2 receipt mode is successor-safe ('+receipt_status+'); Stage-02 exit, website construction and deployment remain blocked')
