#!/usr/bin/env python3
from pathlib import Path
import subprocess,sys,yaml
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'; base=run/'04_PAGE_FUNCTIONAL_CONTRACT'
transaction=base/'CURRENT_LEDGER_SYNCHRONIZATION_R3.yaml'
ledger_pairs={
 'RUN_MANIFEST':(run/'RUN_MANIFEST.yaml','b0d87e8f81c70773886028f28bcaaff3b04908f7',run/'RUN_MANIFEST_R3.yaml','551cad269471151eb9260a047396bf5ce320289f'),
 'ARTIFACT_PLAN':(run/'ARTIFACT_PLAN.yaml','7da6d0d6b4f52d65c605a068b3ee089c3cabeaf1',run/'ARTIFACT_PLAN_R3.yaml','bc6bfae82336975fbd9ab2360ba57dceca7e1077'),
 'EXECUTION_STATE':(run/'EXECUTION_STATE.yaml','d6619afcd653aaac84ee0398a8c1c628e645b704',run/'EXECUTION_STATE_R3.yaml','f5dac4809e97e03e68e0fddbefdf662ce5c3ea3c'),
 'GOVERNANCE_CURRENT':(root/'GOVERNANCE_CURRENT.yaml','852dd9515fdd9ebb66e4c27cb3df9ec1086cf4b1',root/'GOVERNANCE_CURRENT_R3.yaml','42936900f9ca254f8eb56c2a5544961ae730938d'),
 'REBUILD_BRANCH_BASELINE':(root/'REBUILD_BRANCH_BASELINE.yaml','07c79514066178f882153790b4ea84d3ef0521d0',root/'REBUILD_BRANCH_BASELINE_R3.yaml','77d73f517ff41948e02ee847caf75ee0c6e1b365'),
 'GOVERNANCE_STAGE_LOCK':(root/'11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml','3ec8b9e923c2cf06382cf51f6b4a8693230eac0c',root/'11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK_R3.yaml','d6e7c1427732a69e49336b7d4df9ae3f14752e5c'),
 'SEALED_GOVERNANCE_TEST_BASELINE':(root/'11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml','3daf04bd0ad0a96a9a07e9ce19738afdf25e256a',root/'11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE_R3.yaml','b76262859b5b8d8e2b1d54c90953b0f62e8872ab'),
}
EXPECTED_RECEIPT={'provider':'GITHUB_ACTIONS','repository_or_project':'steven-gold/orange-one-ai-viedo-v1.0','head_sha':'e0c6d3e87f763ad0d77e2743fac44760f35573ed','run_id':34773312526,'job_denominator':'24/24','conclusion':'SUCCESS'}
EXPECTED_CURRENT={'state':'STAGE2_FUNCTIONAL_REVIEW_COMPLETE_BLOCKED_BY_FORMAL_CONTRACT_AND_AUTHORITY','operation':'BLOCKER_RESOLUTION_WAIT','open_functional_gap_total':167,'architecture_gap_total':133,'input_source_gap_total':34,'functional_authority_gap_total':0,'blocker_count':3,'functional_gap_blocker_count':2,'required_output_blocker_count':1,'async_provider_unresolved_lifecycle_binding_count':24,'stage2_external_authority_gap_uids_affecting_open_blockers':['GAP-005','GAP-008'],'gap006_status':'RESOLVED_BY_EXACT_CURRENT_AUTHORITY_SUCCESSOR','exit_gate':'ALL_REQUIRED_PAGES_STAGE2_CLOSED','exit_gate_result':'BLOCKED','functional_completion':False,'website_construction_allowed':False,'deployment_allowed':False}

def die(m): raise SystemExit(m)
def load(p):
 try:d=yaml.safe_load(p.read_text(encoding='utf-8'))
 except Exception as e:die('parse failure '+str(p)+': '+str(e))
 if not isinstance(d,dict):die('mapping required:'+str(p))
 return d
def gitobj(p):
 r=subprocess.run(['git','rev-parse','HEAD:'+str(p)],text=True,capture_output=True)
 if r.returncode:die('git object missing:'+str(p))
 return r.stdout.strip()
def runv(p):
 r=subprocess.run([sys.executable,p],text=True,capture_output=True)
 if r.returncode:
  print(r.stdout);print(r.stderr,file=sys.stderr);die('predecessor/successor validator failed:'+p)

for v in ('governance/ci/validate_current_stage2_functional_review_evidence.py','governance/ci/validate_current_stage2_blocker_ledger.py','governance/ci/validate_current_stage2_gap006_supersession.py'):
 runv(v)
if gitobj(transaction)!='9a6f11d383a625e3fe87a1b654644206480b321c':die('R3 synchronization transaction blob drift')
# Explicit supersession is append-only: all seven predecessor current ledgers remain byte-exact.
for role,(pp,pblob,sp,sblob) in ledger_pairs.items():
 if gitobj(pp)!=pblob:die(role+' predecessor current ledger drift')
 if gitobj(sp)!=sblob:die(role+' successor current ledger drift')
T=load(transaction)
if T.get('artifact_type')!='CURRENT_LEDGER_SYNCHRONIZATION_TRANSACTION' or T.get('revision')!='R3_GAP006_AUTHORITY_RESOLVED' or T.get('status')!='CURRENT_BLOCKED' or T.get('mutation_semantics')!='MERGE_APPEND_OR_EXPLICIT_SUPERSEDE' or T.get('superseded_scope')!='STAGE2_CURRENT_PROJECTION_ONLY':die('R3 transaction identity/semantics drift')
mb=T.get('materialization_basis') or {}
if mb.get('gap006_supersession_receipt')!=EXPECTED_RECEIPT:die('R3 transaction terminal predecessor receipt drift')
if (mb.get('functional_gap_ledger_git_blob'),mb.get('functional_review_git_blob'),mb.get('blocker_ledger_git_blob'))!=('29855a6aa9940b6ea64ca75d355c60acda3d2b94','7ce3c91a73f26eb4e9ee0e5a2487e969e38054a4','0df6d972d35dda8778b95c8a663d70177f3379f1'):die('R3 transaction successor source drift')
rows=T.get('ledger_successors') or []
if len(rows)!=7 or [x.get('role') for x in rows]!=list(ledger_pairs):die('R3 transaction seven-ledger role universe drift')
for row in rows:
 role=row['role']; pp,pblob,sp,sblob=ledger_pairs[role]
 if row.get('predecessor_path')!=str(pp) or row.get('predecessor_git_blob')!=pblob or row.get('successor_path')!=str(sp) or row.get('successor_git_blob')!=sblob:die(role+' transaction mapping drift')
tc=T.get('current_stage2') or {}
for k,v in EXPECTED_CURRENT.items():
 if tc.get(k)!=v:die('transaction current_stage2 drift:'+k)
if tc.get('source_capture_unresolved_authority_gap_universe')!=8:die('source-capture 8 Authority refs not preserved')
guards=T.get('continuity_guards') or {}
if guards.get('predecessor_bytes_must_remain_exact') is not True or guards.get('predecessor_receipts_must_remain_resolvable') is not True or guards.get('destructive_rewrite_forbidden') is not True or guards.get('same_commit_terminal_receipt_self_write')!='FORBIDDEN':die('transaction continuity guard drift')
# Every role-specific successor must project exactly the same R3 Current truth.
canonical=None
for role,(_,_,sp,_) in ledger_pairs.items():
 d=load(sp)
 if d.get('artifact_type')!='CURRENT_LEDGER_SUCCESSOR' or d.get('ledger_role')!=role or d.get('run_uid')!='FRESH-RUN-003' or d.get('governance_overlay')!='v2.1.12' or d.get('successor_revision')!='R3_GAP006_AUTHORITY_RESOLVED':die(role+' successor identity drift')
 pred=d.get('successor_of') or {}; pp,pblob,_,_=ledger_pairs[role]
 if pred.get('path')!=str(pp) or pred.get('git_blob')!=pblob or pred.get('superseded_scope')!='STAGE2_CURRENT_PROJECTION_ONLY':die(role+' predecessor binding drift')
 cont=d.get('predecessor_continuity') or {}
 if cont.get('predecessor_bytes_immutable') is not True or cont.get('predecessor_receipts_remain_resolvable') is not True or cont.get('source_capture_unresolved_authority_gap_universe')!=8:die(role+' predecessor continuity drift')
 cur=d.get('current_stage2') or {}
 if cur.get('functional_gap_ledger_git_blob')!='29855a6aa9940b6ea64ca75d355c60acda3d2b94' or cur.get('functional_review_git_blob')!='7ce3c91a73f26eb4e9ee0e5a2487e969e38054a4' or cur.get('blocker_ledger_git_blob')!='0df6d972d35dda8778b95c8a663d70177f3379f1' or cur.get('blocker_ledger_revision')!='R3_GAP006_AUTHORITY_RESOLVED':die(role+' current artifact pointer drift')
 for k,v in EXPECTED_CURRENT.items():
  if cur.get(k)!=v:die(role+' current Stage2 drift:'+k)
 if d.get('supersession_receipt')!=EXPECTED_RECEIPT:die(role+' supersession receipt drift')
 projection={k:cur.get(k) for k in EXPECTED_CURRENT}
 if canonical is None:canonical=projection
 elif projection!=canonical:die('R3 cross-ledger current projection drift')
head=subprocess.run(['git','rev-parse','HEAD'],text=True,capture_output=True,check=True).stdout.strip()
if EXPECTED_RECEIPT['head_sha']==head:die('same-commit terminal receipt self-reference')
print('PASS: seven Stage-02 Current ledger roles are explicitly superseded as one R3 synchronization transaction; all R2 predecessor blobs remain exact')
print('PASS: Current functional gaps = 167 (133 architecture + 34 input + 0 functional Authority); GAP-006 is resolved by exact Authority evidence')
print('PASS: Current blockers = 3 (2 functional + 1 ASYNC_PROVIDER); async lifecycle bindings remain 24 with GAP-005/GAP-008')
print('PASS: source-capture 8-ref Authority universe remains preserved; Stage-02 exit, website construction, and deployment remain blocked')
