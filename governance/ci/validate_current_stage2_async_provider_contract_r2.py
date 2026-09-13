#!/usr/bin/env python3
from pathlib import Path
import subprocess,yaml
root=Path('.')
base=root/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
r1=base/'ASYNC_PROVIDER_CONTRACT.yaml'
audit=base/'ASYNC_PROVIDER_LIFECYCLE_AUTHORITY_AUDIT.yaml'
r2=base/'ASYNC_PROVIDER_CONTRACT_R2.yaml'
tx=base/'CURRENT_LEDGER_SYNCHRONIZATION_R3.yaml'
REQ=['request_identity','input_fingerprint','idempotency','queued','running','succeeded','failed','cancel','retry_eligibility','callback_result_provenance','output_persistence','audit_correlation']
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
locked={
 r1:'2aa1db9a2ec013dc2820b83a010464fe40facb0f',
 audit:'bc988b364ffc6a3e61267e152a47fb7528b6d1b3',
 r2:'89f35cf340ba87053e51d001a5e96d17f3692db5',
 tx:'9a6f11d383a625e3fe87a1b654644206480b321c'
}
for p,b in locked.items():
 if gitobj(p)!=b:die('async successor/predecessor drift:'+str(p))
R1=load(r1); A=load(audit); R2=load(r2); T=load(tx)
if R1.get('artifact_type')!='ASYNC_PROVIDER_CONTRACT' or R1.get('status')!='OPEN_BLOCKING_AUTHORITY_AND_LIFECYCLE_GAPS':die('R1 identity/status drift')
if R1.get('required_lifecycle_fields')!=REQ:die('R1 lifecycle universe drift')
for page in ('CORE-01','ASSET-01'):
 p=(R1.get('pages') or {}).get(page) or {}
 if p.get('resolved_lifecycle_fields')!={} or p.get('unresolved_lifecycle_fields')!=REQ:die(page+' R1 must remain 12 unresolved')
if A.get('artifact_type')!='ASYNC_LIFECYCLE_AUTHORITY_COVERAGE_AUDIT' or A.get('status')!='AUDITED_SUCCESSOR_CANDIDATE_NOT_CURRENT':die('audit identity/status drift')
math=A.get('candidate_successor_math') or {}
if math.get('predecessor_unresolved_binding_count')!=24 or math.get('exact_resolution_candidate_binding_count')!=10 or math.get('candidate_unresolved_binding_count_after_successor_compile')!=14 or math.get('current_unresolved_binding_count_after_audit_only')!=24 or math.get('audit_authorizes_current_mutation') is not False:die('audit math/current-preservation drift')
if R2.get('artifact_uid')!='FRESH-RUN-003-ASYNC-PROVIDER-CONTRACT-V212-R2' or R2.get('artifact_type')!='ASYNC_PROVIDER_CONTRACT' or R2.get('status')!='CANDIDATE_AWAITING_DEDICATED_GATE' or R2.get('normative_gate_ref')!='WEB-GOV-01-S061':die('R2 identity/status drift')
pre=R2.get('predecessor') or {}
if pre.get('git_blob')!='2aa1db9a2ec013dc2820b83a010464fe40facb0f' or pre.get('unresolved_lifecycle_binding_count')!=24:die('R2 predecessor drift')
aud=R2.get('authority_coverage_audit') or {}
if aud.get('git_blob')!='bc988b364ffc6a3e61267e152a47fb7528b6d1b3':die('R2 audit binding drift')
rec=aud.get('gate26_receipt') or {}
if rec!={'exact_sha':'7cb820401f956c201f1871ced59f3468577adab8','workflow_run_id':34774969576,'workflow_run_number':173,'workflow_conclusion':'success','job_name':'current-stage2-async-lifecycle-authority-audit-gate','job_id':103771299713,'job_conclusion':'success'}:die('Gate26 receipt drift')
if R2.get('required_lifecycle_fields')!=REQ or R2.get('exact_resolved_field_order')!=RES or R2.get('remaining_unresolved_field_order')!=UNRES:die('R2 field universe/order drift')
ra=R2.get('resolved_field_authority') or {}
if set(ra)!=set(RES):die('R2 resolved authority field set drift')
if (ra.get('input_fingerprint') or {}).get('authority_blob')!='12ef6d233e09f84571dd5d694ae8e3789ae70502':die('input_fingerprint authority drift')
for f in ('idempotency','succeeded','failed','retry_eligibility'):
 if (ra.get(f) or {}).get('authority_blob')!='ac3619b3bc547ce06f244c239fa69d3cac78da76':die(f+' authority drift')
for page in ('CORE-01','ASSET-01'):
 p=(R2.get('pages') or {}).get(page) or {}
 if p.get('binding_status')!='PARTIAL_EXACT_LIFECYCLE_RESOLUTION_REMAINS_BLOCKED':die(page+' binding status drift')
 if p.get('resolved_lifecycle_fields')!=RES or p.get('unresolved_lifecycle_fields')!=UNRES or p.get('resolved_count')!=5 or p.get('unresolved_count')!=7:die(page+' exact 5/7 partition drift')
cm=R2.get('candidate_successor_math') or {}
if cm!={'predecessor_unresolved_lifecycle_binding_count':24,'exact_resolved_binding_count':10,'candidate_unresolved_lifecycle_binding_count':14,'page_count':2,'exact_resolved_per_page':5,'unresolved_per_page':7}:die('R2 successor math drift')
cp=R2.get('current_state_policy') or {}
if cp!={'candidate_is_current':False,'current_async_provider_contract_revision':'R1','current_async_provider_unresolved_lifecycle_binding_count':24,'dedicated_r2_gate_required_before_current_supersession':True}:die('R2 Current preservation policy drift')
cur=T.get('current_stage2') or {}
if cur.get('async_provider_unresolved_lifecycle_binding_count')!=24 or cur.get('exit_gate_result')!='BLOCKED' or cur.get('functional_completion') is not False:die('Current transaction mutated before dedicated R2 gate')
pol=R2.get('policy') or {}
if pol.get('semantic_similarity_as_exact_binding')!='FORBIDDEN' or pol.get('cross_authority_field_union_without_explicit_binding')!='FORBIDDEN' or pol.get('ai_default_lifecycle_values')!='FORBIDDEN' or pol.get('raw_source_mutation_allowed') is not False or pol.get('predecessor_mutation_allowed') is not False:die('R2 safety policy drift')
if R2.get('functional_completion_claim') is not False or R2.get('stage2_exit_gate_result')!='BLOCKED' or R2.get('website_construction_allowed') is not False or R2.get('deployment_allowed') is not False:die('R2 falsely closes Stage2/site/deploy')
print('PASS: Async Provider Contract R2 is an immutable candidate successor of R1 with exact 24 -> 14 delta')
print('PASS: exactly 5 lifecycle fields per page are resolved and exactly 7 per page remain unresolved')
print('PASS: Current remains R1/24 until a dedicated R2 gate and explicit Current supersession transaction')
