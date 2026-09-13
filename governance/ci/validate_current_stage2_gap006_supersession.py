#!/usr/bin/env python3
from pathlib import Path
import subprocess,yaml
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'; base=run/'04_PAGE_FUNCTIONAL_CONTRACT'
review=run/'00_SOURCE_INTAKE/evidence/PAGE_FUNCTIONAL_REVIEW_EVIDENCE_R2.yaml'
blocker=base/'BLOCKER_LEDGER_R3.yaml'; r4=base/'FUNCTIONAL_CHAIN_GAP_LEDGER_R4.yaml'

def die(m): raise SystemExit(m)
def load(p):
 d=yaml.safe_load(p.read_text(encoding='utf-8'))
 if not isinstance(d,dict): die('mapping required:'+str(p))
 return d
def gitobj(p):
 r=subprocess.run(['git','rev-parse','HEAD:'+str(p)],text=True,capture_output=True)
 if r.returncode: die('git object missing:'+str(p))
 return r.stdout.strip()
locked={
 base/'FUNCTIONAL_CHAIN_GAP_LEDGER.yaml':'093c72a8e3227c1228180a29586980ab5e8f85cd',
 run/'00_SOURCE_INTAKE/evidence/PAGE_FUNCTIONAL_REVIEW_EVIDENCE.yaml':'7f7c821c9f037d29ac576bd1f944a881329666ef',
 base/'BLOCKER_LEDGER.yaml':'82e327222a9ea3e988ce9b317913987be6195a31',
 r4:'29855a6aa9940b6ea64ca75d355c60acda3d2b94',
 base/'SHARED_OWNER_PORT_MAP_R2.yaml':'65f821ad766994716f4336e961b1b160b5aac457',
 base/'EXTERNAL_AUTHORITY/STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE.yaml':'ff99fd8c48f4593c5ef5cdeab1d49c5caa027cfd',
 base/'ASYNC_PROVIDER_CONTRACT.yaml':'2aa1db9a2ec013dc2820b83a010464fe40facb0f'}
for p,b in locked.items():
 if gitobj(p)!=b: die('predecessor/successor evidence drift:'+str(p))
if gitobj(review)!='7ce3c91a73f26eb4e9ee0e5a2487e969e38054a4': die('R2 review blob drift')
if gitobj(blocker)!='0df6d972d35dda8778b95c8a663d70177f3379f1': die('R3 blocker blob drift')
R=load(review); B=load(blocker); G=load(r4)
receipt={'provider':'GITHUB_ACTIONS','repository_or_project':'steven-gold/orange-one-ai-viedo-v1.0','head_sha':'0b1bd29533dab4887ae5c077a57257388efe6a27','run_id':34771926824,'job_denominator':'23/23','conclusion':'SUCCESS'}
if R.get('artifact_type')!='PAGE_FUNCTIONAL_REVIEW_EVIDENCE' or R.get('artifact_uid')!='FRESH-RUN-003-PAGE-FUNCTIONAL-REVIEW-EVIDENCE-V212-R2': die('R2 review identity drift')
if (R.get('predecessor_review') or {}).get('git_blob')!='7f7c821c9f037d29ac576bd1f944a881329666ef': die('review predecessor drift')
sg=R.get('successor_gap_ledger') or {}
if sg.get('git_blob')!='29855a6aa9940b6ea64ca75d355c60acda3d2b94' or sg.get('gap_total')!=167 or sg.get('pages')!={'CORE-01':45,'ASSET-01':122} or sg.get('classes')!={'ARCHITECTURE_GAP':133,'INPUT_SOURCE_GAP':34,'AUTHORITY_GAP':0}: die('review successor gap summary drift')
res=R.get('resolution_evidence') or {}
cons=['ASSET-01-ACT-CORRECTION-GENERATE','ASSET-01-ACT-CORRECTION-APPROVE','ASSET-01-ACT-RESTORE-AS-NEW','ASSET-01-ACT-VERSION-LOCK']
if res.get('gap_uid')!='GAP-006' or res.get('authority_ref')!='ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or res.get('resolved_consumer_count')!=4 or res.get('consumers')!=cons or res.get('disposition')!='SUPERSEDED_BY_EXACT_EXTERNAL_AUTHORITY' or res.get('ai_inference_used') is not False or res.get('raw_source_mutated') is not False: die('GAP-006 review resolution drift')
if R.get('successor_ci_receipt')!=receipt: die('R2 review CI receipt drift')
ma=R.get('machine_result_artifact') or {}
if ma.get('artifact_id')!=10321674696 or ma.get('digest')!='sha256:00967fc9ad5943cb4cad211f7cca97b0052ffec45fca72851d6483b485484ee2': die('R2 review machine artifact drift')
rs=R.get('resolution_summary') or {}
if rs!={'predecessor_reviewed_gap_total':171,'authority_resolved_gap_total':4,'reviewed_gap_total':167,'safely_auto_remediable_total':0,'remains_blocking_total':167,'architecture_gap_total':133,'input_source_gap_total':34,'authority_gap_total':0,'source_mutations':0,'inferred_bindings':0,'synthetic_contracts':0}: die('R2 review resolution summary drift')
ind=R.get('independent_required_output_blocker') or {}
if ind.get('unresolved_lifecycle_binding_count')!=24 or ind.get('covered_by_167_functional_gap_ledger') is not False or ind.get('authority_gap_uids')!=['GAP-005','GAP-008']: die('R2 review async blocker drift')
if (R.get('stage2_exit_gate') or {}).get('result')!='BLOCKED' or (R.get('stage2_exit_gate') or {}).get('functional_completion') is not False or (R.get('stage2_exit_gate') or {}).get('website_construction_allowed') is not False or (R.get('stage2_exit_gate') or {}).get('deployment_allowed') is not False: die('R2 review false enablement')
if B.get('artifact_type')!='BLOCKER_LEDGER' or B.get('artifact_uid')!='FRESH-RUN-003-STAGE2-BLOCKER-LEDGER-V212-R3' or B.get('coverage_revision')!='R3_GAP006_AUTHORITY_RESOLVED': die('R3 blocker identity drift')
if (B.get('predecessor_blocker_ledger') or {}).get('git_blob')!='82e327222a9ea3e988ce9b317913987be6195a31': die('R3 blocker predecessor drift')
source=B.get('source_gap_ledger') or {}
if source.get('git_blob')!='29855a6aa9940b6ea64ca75d355c60acda3d2b94' or source.get('gap_total')!=167 or source.get('classes')!={'ARCHITECTURE_GAP':133,'INPUT_SOURCE_GAP':34,'AUTHORITY_GAP':0}: die('R3 blocker source gap drift')
fr=B.get('functional_review_evidence') or {}
if fr.get('git_blob')!='7ce3c91a73f26eb4e9ee0e5a2487e969e38054a4' or fr.get('reviewed_gap_total')!=167: die('R3 blocker review ref drift')
resolved=B.get('resolved_predecessor_blockers') or []
if len(resolved)!=1 or resolved[0].get('blocker_uid')!='STAGE2-BLK-GAP006-SHARED-AUTHORITY-001' or resolved[0].get('successor_status')!='SUPERSEDED_BY_AUTHORITY' or resolved[0].get('resolved_gap_count')!=4 or ((resolved[0].get('resolved_evidence') or {}).get('ci_receipt'))!=receipt: die('R3 GAP-006 resolved blocker lineage drift')
blocks=B.get('blockers') or []
if [x.get('blocker_uid') for x in blocks]!=['STAGE2-BLK-INPUT-CONTRACT-001','STAGE2-BLK-ARCH-CONTRACT-001','STAGE2-BLK-ASYNC-PROVIDER-LIFECYCLE-001']: die('R3 open blocker universe drift')
if any(x.get('current_status')!='OPEN_BLOCKING' or x.get('resolved_evidence') is not None for x in blocks): die('R3 false blocker resolution')
s=B.get('summary') or {}
expected={'blocker_count':3,'open_blocker_count':3,'resolved_predecessor_blocker_count':1,'blocked_functional_gap_total':167,'functional_gap_blocker_count':2,'required_output_blocker_count':1,'input_contract_gap_count':34,'architecture_contract_gap_count':133,'functional_authority_gap_count':0,'async_provider_unresolved_lifecycle_binding_count':24,'stage2_external_authority_gap_uids_affecting_open_blockers':['GAP-005','GAP-008'],'functional_completion':False,'stage2_exit_gate':'BLOCKED','website_construction_allowed':False,'deployment_allowed':False}
if s!=expected: die('R3 blocker summary drift')
gs=G.get('summary') or {}
if gs.get('total')!=167 or gs.get('classes')!={'ARCHITECTURE_GAP':133,'INPUT_SOURCE_GAP':34,'AUTHORITY_GAP':0}: die('R4 ledger current candidate summary drift')
print('PASS: GAP-006 exact Authority resolution is preserved as explicit successor evidence; predecessor 171/R1/R2 artifacts remain immutable')
print('PASS: reviewed functional-gap universe is 167 = 133 architecture + 34 input + 0 functional Authority gaps')
print('PASS: R3 Blocker Ledger has exactly 3 open blockers; GAP-006 predecessor blocker is explicitly superseded by Authority evidence')
print('PASS: independent ASYNC_PROVIDER blocker remains 24 lifecycle bindings with GAP-005/GAP-008; Stage-02 exit/website/deployment remain blocked')
