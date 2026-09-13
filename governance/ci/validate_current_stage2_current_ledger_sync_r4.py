#!/usr/bin/env python3
from pathlib import Path
import subprocess,sys,yaml
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'; base=run/'04_PAGE_FUNCTIONAL_CONTRACT'
transaction=base/'CURRENT_LEDGER_SYNCHRONIZATION_R4.yaml'
async_current=base/'ASYNC_PROVIDER_CONTRACT_R3_CURRENT.yaml'
blocker=base/'BLOCKER_LEDGER_R4.yaml'
ledger_pairs={
 'RUN_MANIFEST':(run/'RUN_MANIFEST_R3.yaml','551cad269471151eb9260a047396bf5ce320289f',run/'RUN_MANIFEST_R4.yaml','ecf3fc187f2795edd579de8fdcaeb9d0bdf8aa7a'),
 'ARTIFACT_PLAN':(run/'ARTIFACT_PLAN_R3.yaml','bc6bfae82336975fbd9ab2360ba57dceca7e1077',run/'ARTIFACT_PLAN_R4.yaml','224420fdb7a205fd6013712f5794cbc11bfaaaa3'),
 'EXECUTION_STATE':(run/'EXECUTION_STATE_R3.yaml','f5dac4809e97e03e68e0fddbefdf662ce5c3ea3c',run/'EXECUTION_STATE_R4.yaml','5c4efdd92e34aed3f0953d8fb2d331a44d1b0e8a'),
 'GOVERNANCE_CURRENT':(root/'GOVERNANCE_CURRENT_R3.yaml','42936900f9ca254f8eb56c2a5544961ae730938d',root/'GOVERNANCE_CURRENT_R4.yaml','901a4c997cea41b6a15de2b1378916ebad611d0b'),
 'REBUILD_BRANCH_BASELINE':(root/'REBUILD_BRANCH_BASELINE_R3.yaml','77d73f517ff41948e02ee847caf75ee0c6e1b365',root/'REBUILD_BRANCH_BASELINE_R4.yaml','4c05b5438cb4f2f52ee1274c766dcba8253ebbbd'),
 'GOVERNANCE_STAGE_LOCK':(root/'11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK_R3.yaml','d6e7c1427732a69e49336b7d4df9ae3f14752e5c',root/'11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK_R4.yaml','d57c815a8ff587245b0da757650d2b82789605b7'),
 'SEALED_GOVERNANCE_TEST_BASELINE':(root/'11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE_R3.yaml','b76262859b5b8d8e2b1d54c90953b0f62e8872ab',root/'11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE_R4.yaml','5e7b600b5567c491219400dfc12fd1f5bd66d594'),
}
EXPECTED_RECEIPT={'provider':'GITHUB_ACTIONS','repository_or_project':'steven-gold/orange-one-ai-viedo-v1.0','head_sha':'abd19d51bf3dc968ccdc8a63f9ed5a918c172a14','run_id':34775172873,'run_number':175,'job_name':'current-stage2-async-provider-contract-r2-gate','job_id':103771865678,'job_denominator':'27/27','conclusion':'SUCCESS'}
EXPECTED_CURRENT={'state':'STAGE2_FUNCTIONAL_REVIEW_COMPLETE_BLOCKED_BY_FORMAL_CONTRACT_AND_AUTHORITY','operation':'BLOCKER_RESOLUTION_WAIT','open_functional_gap_total':167,'architecture_gap_total':133,'input_source_gap_total':34,'functional_authority_gap_total':0,'blocker_count':3,'functional_gap_blocker_count':2,'required_output_blocker_count':1,'async_provider_unresolved_lifecycle_binding_count':14,'stage2_external_authority_gap_uids_affecting_open_blockers':['GAP-005','GAP-008'],'gap006_status':'RESOLVED_BY_EXACT_CURRENT_AUTHORITY_SUCCESSOR','async_provider_status':'PARTIAL_EXACT_RESOLUTION_14_REMAIN','exit_gate':'ALL_REQUIRED_PAGES_STAGE2_CLOSED','exit_gate_result':'BLOCKED','functional_completion':False,'website_construction_allowed':False,'deployment_allowed':False}
RES=['input_fingerprint','idempotency','succeeded','failed','retry_eligibility']
UNRES=['request_identity','queued','running','cancel','callback_result_provenance','output_persistence','audit_correlation']

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
  print(r.stdout);print(r.stderr,file=sys.stderr);die('required predecessor validator failed:'+p)

# Prove all predecessor governance remains valid before accepting the R4 Current projection.
for v in ('governance/ci/validate_current_stage2_current_ledger_sync.py','governance/ci/validate_current_stage2_async_provider_contract_r2.py'):
 runv(v)
locked={
 base/'CURRENT_LEDGER_SYNCHRONIZATION_R3.yaml':'9a6f11d383a625e3fe87a1b654644206480b321c',
 base/'BLOCKER_LEDGER_R3.yaml':'0df6d972d35dda8778b95c8a663d70177f3379f1',
 base/'ASYNC_PROVIDER_CONTRACT_R2.yaml':'89f35cf340ba87053e51d001a5e96d17f3692db5',
 async_current:'b66515c094dd12d6832e4300817591fbe41b739f',
 blocker:'e675cc68b0eb6bfd7c484e860eef3b5ebc146890',
 transaction:'7f4780fb1d9eb8264490b68a4dd09627490e3c66',
}
for p,b in locked.items():
 if gitobj(p)!=b:die('R4/R3 locked artifact drift:'+str(p))
for role,(pp,pblob,sp,sblob) in ledger_pairs.items():
 if gitobj(pp)!=pblob:die(role+' R3 predecessor drift')
 if gitobj(sp)!=sblob:die(role+' R4 successor drift')
# Validate promoted async Current artifact: exact 10 resolved, 14 remain, still blocked.
A=load(async_current)
if A.get('artifact_type')!='ASYNC_PROVIDER_CONTRACT' or A.get('revision')!='R3_CURRENT_AFTER_R2_GATE' or A.get('status')!='CURRENT_BLOCKED_PARTIAL_LIFECYCLE_RESOLUTION':die('async Current identity/status drift')
so=A.get('successor_of') or {}
if so.get('git_blob')!='89f35cf340ba87053e51d001a5e96d17f3692db5':die('async Current R2 predecessor drift')
if A.get('promotion_receipt')!=EXPECTED_RECEIPT:die('async Current Gate27 receipt drift')
if A.get('resolved_lifecycle_fields')!=RES or A.get('unresolved_lifecycle_fields')!=UNRES:die('async Current exact field partition drift')
for page in ('CORE-01','ASSET-01'):
 p=(A.get('pages') or {}).get(page) or {}
 if p.get('resolved_lifecycle_fields')!=RES or p.get('unresolved_lifecycle_fields')!=UNRES or p.get('resolved_count')!=5 or p.get('unresolved_count')!=7:die(page+' async Current 5/7 projection drift')
cs=A.get('current_state') or {}
if cs.get('predecessor_unresolved_lifecycle_binding_count')!=24 or cs.get('exact_resolved_binding_count')!=10 or cs.get('unresolved_lifecycle_binding_count')!=14 or cs.get('is_current') is not True or cs.get('stage2_exit_gate_result')!='BLOCKED' or cs.get('functional_completion') is not False or cs.get('website_construction_allowed') is not False or cs.get('deployment_allowed') is not False:die('async Current 24->14/blocking state drift')
# Validate R4 blocker: functional truth unchanged, async blocker partially shrunk but remains open.
B=load(blocker)
if B.get('artifact_type')!='BLOCKER_LEDGER' or B.get('coverage_revision')!='R4_ASYNC_PROVIDER_R2_PROMOTED_CURRENT_14_REMAIN' or B.get('status')!='OPEN_BLOCKERS':die('R4 blocker identity/status drift')
pred=B.get('predecessor_blocker_ledger') or {}
if pred.get('git_blob')!='0df6d972d35dda8778b95c8a663d70177f3379f1' or pred.get('blocker_count')!=3:die('R4 blocker predecessor drift')
if (B.get('source_gap_ledger') or {}).get('gap_total')!=167 or (B.get('source_gap_ledger') or {}).get('git_blob')!='29855a6aa9940b6ea64ca75d355c60acda3d2b94':die('R4 blocker functional gap basis drift')
ac=B.get('async_provider_current_contract') or {}
if ac.get('git_blob')!='b66515c094dd12d6832e4300817591fbe41b739f' or ac.get('predecessor_unresolved_lifecycle_binding_total')!=24 or ac.get('exact_resolved_lifecycle_binding_total')!=10 or ac.get('unresolved_lifecycle_binding_total')!=14:die('R4 blocker async basis drift')
blocks=B.get('blockers') or []
if len(blocks)!=3:die('R4 blocker count drift')
by={x.get('blocker_uid'):x for x in blocks}
if (by.get('STAGE2-BLK-INPUT-CONTRACT-001') or {}).get('gap_count')!=34:die('input blocker drift')
if (by.get('STAGE2-BLK-ARCH-CONTRACT-001') or {}).get('gap_count')!=133:die('architecture blocker drift')
ab=by.get('STAGE2-BLK-ASYNC-PROVIDER-LIFECYCLE-001') or {}
if ab.get('current_status')!='OPEN_BLOCKING_PARTIAL_EXACT_RESOLUTION' or ab.get('unresolved_lifecycle_binding_count')!=14 or ab.get('page_unresolved_lifecycle_binding_count')!={'CORE-01':7,'ASSET-01':7} or ab.get('unresolved_lifecycle_fields_per_page')!=UNRES:die('async open blocker 14/7+7 drift')
s=B.get('summary') or {}
for k,v in {'blocker_count':3,'open_blocker_count':3,'blocked_functional_gap_total':167,'functional_gap_blocker_count':2,'required_output_blocker_count':1,'input_contract_gap_count':34,'architecture_contract_gap_count':133,'functional_authority_gap_count':0,'async_provider_unresolved_lifecycle_binding_count':14,'functional_completion':False,'stage2_exit_gate':'BLOCKED','website_construction_allowed':False,'deployment_allowed':False}.items():
 if s.get(k)!=v:die('R4 blocker summary drift:'+k)
# Validate one atomic seven-ledger R4 synchronization transaction.
T=load(transaction)
if T.get('artifact_type')!='CURRENT_LEDGER_SYNCHRONIZATION_TRANSACTION' or T.get('revision')!='R4_ASYNC_PROVIDER_PARTIAL_RESOLUTION_14_REMAIN' or T.get('status')!='CURRENT_BLOCKED' or T.get('mutation_semantics')!='MERGE_APPEND_OR_EXPLICIT_SUPERSEDE' or T.get('superseded_scope')!='STAGE2_CURRENT_PROJECTION_ONLY':die('R4 transaction identity/semantics drift')
mb=T.get('materialization_basis') or {}
if mb.get('async_provider_r2_gate_receipt')!=EXPECTED_RECEIPT:die('R4 transaction Gate27 receipt drift')
if (mb.get('functional_gap_ledger_git_blob'),mb.get('functional_review_git_blob'),mb.get('async_provider_contract_git_blob'),mb.get('blocker_ledger_git_blob'))!=('29855a6aa9940b6ea64ca75d355c60acda3d2b94','7ce3c91a73f26eb4e9ee0e5a2487e969e38054a4','b66515c094dd12d6832e4300817591fbe41b739f','e675cc68b0eb6bfd7c484e860eef3b5ebc146890'):die('R4 transaction materialization source drift')
rows=T.get('ledger_successors') or []
if len(rows)!=7 or [x.get('role') for x in rows]!=list(ledger_pairs):die('R4 seven-ledger role universe drift')
for row in rows:
 role=row['role']; pp,pblob,sp,sblob=ledger_pairs[role]
 if row.get('predecessor_path')!=str(pp) or row.get('predecessor_git_blob')!=pblob or row.get('successor_path')!=str(sp) or row.get('successor_git_blob')!=sblob:die(role+' R4 transaction mapping drift')
tc=T.get('current_stage2') or {}
for k,v in EXPECTED_CURRENT.items():
 if tc.get(k)!=v:die('R4 transaction Current drift:'+k)
if tc.get('source_capture_unresolved_authority_gap_universe')!=8:die('R4 transaction source-capture 8-ref universe drift')
guards=T.get('continuity_guards') or {}
if guards.get('r3_predecessor_bytes_must_remain_exact') is not True or guards.get('predecessor_receipts_must_remain_resolvable') is not True or guards.get('destructive_rewrite_forbidden') is not True or guards.get('same_commit_terminal_receipt_self_write')!='FORBIDDEN' or guards.get('async_partial_resolution_may_not_be_claimed_as_full_resolution') is not True:die('R4 transaction continuity guards drift')
# Every R4 role projects the same Current truth and exact R3 predecessor.
canonical=None
for role,(pp,pblob,sp,_) in ledger_pairs.items():
 d=load(sp)
 if d.get('artifact_type')!='CURRENT_LEDGER_SUCCESSOR' or d.get('ledger_role')!=role or d.get('successor_revision')!='R4_ASYNC_PROVIDER_PARTIAL_RESOLUTION_14_REMAIN':die(role+' R4 successor identity drift')
 pred=d.get('successor_of') or {}
 if pred.get('path')!=str(pp) or pred.get('git_blob')!=pblob or pred.get('superseded_scope')!='STAGE2_CURRENT_PROJECTION_ONLY':die(role+' R3 predecessor binding drift')
 cont=d.get('predecessor_continuity') or {}
 if cont.get('predecessor_bytes_immutable') is not True or cont.get('predecessor_receipts_remain_resolvable') is not True or cont.get('source_capture_unresolved_authority_gap_universe')!=8:die(role+' continuity drift')
 cur=d.get('current_stage2') or {}
 if cur.get('functional_gap_ledger_git_blob')!='29855a6aa9940b6ea64ca75d355c60acda3d2b94' or cur.get('functional_review_git_blob')!='7ce3c91a73f26eb4e9ee0e5a2487e969e38054a4' or cur.get('blocker_ledger_git_blob')!='e675cc68b0eb6bfd7c484e860eef3b5ebc146890' or cur.get('async_provider_contract_git_blob')!='b66515c094dd12d6832e4300817591fbe41b739f':die(role+' R4 artifact pointer drift')
 for k,v in EXPECTED_CURRENT.items():
  if cur.get(k)!=v:die(role+' R4 Current drift:'+k)
 if d.get('supersession_receipt')!=EXPECTED_RECEIPT:die(role+' R4 receipt drift')
 projection={k:cur.get(k) for k in EXPECTED_CURRENT}
 if canonical is None:canonical=projection
 elif projection!=canonical:die('R4 cross-ledger Current projection drift')
head=subprocess.run(['git','rev-parse','HEAD'],text=True,capture_output=True,check=True).stdout.strip()
if EXPECTED_RECEIPT['head_sha']==head:die('same-commit terminal receipt self-reference')
print('PASS: Gate27-proven Async Provider R2 is explicitly promoted to Current through an append-only R4 synchronization transaction')
print('PASS: Current functional gaps remain 167 and blockers remain 3; Async lifecycle blocker is partially reduced 24 -> 14, not closed')
print('PASS: seven R3 Current predecessors remain byte-exact and seven R4 role successors project one Current truth')
print('PASS: Stage-02 exit, website construction, and deployment remain BLOCKED')
