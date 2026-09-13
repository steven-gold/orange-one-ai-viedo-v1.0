#!/usr/bin/env python3
from pathlib import Path
import subprocess,yaml
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'; base=run/'04_PAGE_FUNCTIONAL_CONTRACT'; ext=base/'EXTERNAL_AUTHORITY'
audit=base/'ASYNC_PROVIDER_LIFECYCLE_AUTHORITY_AUDIT.yaml'; r1=base/'ASYNC_PROVIDER_CONTRACT.yaml'; tx=base/'CURRENT_LEDGER_SYNCHRONIZATION_R3.yaml'
manifest=ext/'ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml'; queue=ext/'ASYNC/ACPOS_PRODUCTION_ASYNC_QUEUE_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml'; provider=ext/'GAP-005/ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT_FINAL_LOCKED_V1.3.yaml'; aiapi=ext/'GAP-008/ACPOS_AIAPI-01_FINAL_LOCKED_ENCODING.yaml'; system=ext/'GAP-008/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml'
REQ=['request_identity','input_fingerprint','idempotency','queued','running','succeeded','failed','cancel','retry_eligibility','callback_result_provenance','output_persistence','audit_correlation']
EXACT=['input_fingerprint','idempotency','succeeded','failed','retry_eligibility']; UNRES=[x for x in REQ if x not in EXACT]

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
def flatten(x):
 out=[]
 if isinstance(x,str):out.append(x)
 elif isinstance(x,list):
  for v in x:out.extend(flatten(v))
 elif isinstance(x,dict):
  for v in x.values():out.extend(flatten(v))
 return out
locked={audit:'bc988b364ffc6a3e61267e152a47fb7528b6d1b3',r1:'2aa1db9a2ec013dc2820b83a010464fe40facb0f',tx:'9a6f11d383a625e3fe87a1b654644206480b321c',manifest:'465329b6fb19b8e44c3083a9f280015ee95cc55c',queue:'ac3619b3bc547ce06f244c239fa69d3cac78da76',provider:'12ef6d233e09f84571dd5d694ae8e3789ae70502',aiapi:'dd9f05e295af57cc833e90d1a12030c8198580c6',system:'b09b7ca50313172ea021d9da0c8d57f2942f7b19'}
for p,b in locked.items():
 if gitobj(p)!=b:die('async audit evidence/predecessor drift:'+str(p))
A=load(audit); R=load(r1); T=load(tx); M=load(manifest); Q=load(queue); P=load(provider); AI=load(aiapi); S=load(system)
if A.get('artifact_type')!='ASYNC_LIFECYCLE_AUTHORITY_COVERAGE_AUDIT' or A.get('artifact_uid')!='FRESH-RUN-003-STAGE2-ASYNC-LIFECYCLE-AUTHORITY-COVERAGE-AUDIT-V212-R1' or A.get('status')!='AUDITED_SUCCESSOR_CANDIDATE_NOT_CURRENT' or A.get('normative_gate_ref')!='WEB-GOV-01-S061':die('audit identity/status drift')
if A.get('required_lifecycle_fields')!=REQ:die('audit required lifecycle field order/universe drift')
# Current Authority admissibility is mandatory for every audited source.
current_paths=set(flatten(M.get('current_authority_set') or {}))
required_paths={'authority/runtime/ACPOS_PRODUCTION_ASYNC_QUEUE_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml','authority/global/ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT_FINAL_LOCKED_V1.3.yaml','authority/pages/admin/AIAPI-01/ACPOS_AIAPI-01_FINAL_LOCKED_ENCODING.yaml','authority/global/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml'}
if not required_paths.issubset(current_paths):die('audited async authority missing from Current Authority Manifest')
if ((M.get('load_policy') or {}).get('only_listed_files_are_current_authority')) is not True:die('manifest current-only load policy drift')
# R1 must remain the exact 24-unresolved predecessor; audit itself may not mutate it.
if R.get('artifact_type')!='ASYNC_PROVIDER_CONTRACT' or R.get('status')!='OPEN_BLOCKING_AUTHORITY_AND_LIFECYCLE_GAPS' or R.get('required_lifecycle_fields')!=REQ:die('async R1 identity/status/required fields drift')
for page in ('CORE-01','ASSET-01'):
 p=(R.get('pages') or {}).get(page) or {}
 if p.get('resolved_lifecycle_fields')!={} or p.get('unresolved_lifecycle_fields')!=REQ:die(page+' async R1 no longer exact 12-unresolved predecessor')
cur=T.get('current_stage2') or {}
if cur.get('async_provider_unresolved_lifecycle_binding_count')!=24 or cur.get('exit_gate_result')!='BLOCKED' or cur.get('functional_completion') is not False:die('R3 Current async predecessor state drift')
# Exact Current Authority facts supporting ONLY the five resolution candidates.
qa=Q.get('authority') or {}
if qa.get('id')!='ACPOS_PRODUCTION_ASYNC_QUEUE_RUNTIME_CONTRACT' or qa.get('status')!='FINAL_LOCKED' or qa.get('current_only') is not True:die('queue Current Authority identity drift')
queues=((Q.get('topology') or {}).get('queues') or [])
q=[x for x in queues if isinstance(x,dict) and x.get('queue_key')=='acpos.provider.execution.v1']
if len(q)!=1 or ((q[0].get('policy') or {}).get('idempotency_scope'))!='QUEUE_ID_PLUS_IDEMPOTENCY_KEY':die('queue idempotency exact evidence drift')
out=Q.get('outbox_delivery_extension') or {}
if out.get('terminal_success')!='published_at IS NOT NULL' or out.get('terminal_failure')!='dead_lettered_at IS NOT NULL':die('queue terminal success/failure exact evidence drift')
if 'attempt_count < max_attempts' not in (out.get('claimable_predicate') or []):die('retry eligibility claimable predicate missing')
failure=(Q.get('worker_contract') or {}).get('failure') or []
if not any('attempt_count < max_attempts' in str(x) for x in failure) or not any('attempt_count >= max_attempts' in str(x) for x in failure):die('retry/DLQ cutoff exact evidence drift')
if 'correlation_id REQUIRED' not in ((Q.get('provider_execution_contract') or {}).get('payload_rules') or []):die('queue partial correlation evidence drift')
pa=P.get('authority') or {}
if pa.get('id')!='ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT' or pa.get('version')!='V1.3' or pa.get('status')!='FINAL_LOCKED' or pa.get('current_only') is not True:die('provider V1.3 Current Authority identity drift')
if 'input_fingerprint' not in ((P.get('shared_rules') or {}).get('trace_required') or []):die('provider input_fingerprint exact evidence missing')
pipe=P.get('conversion_pipeline') or []
if not any('job/result lineage' in str(x) for x in pipe):die('provider partial result-lineage evidence drift')
auth=AI.get('authority') or {}
if auth.get('page_uid')!='admin:AIAPI-01' or auth.get('status')!='FINAL_LOCKED' or auth.get('current_only') is not True:die('AIAPI Current Authority identity drift')
j=AI.get('job_attempt_contract') or {}
if 'job_id' not in (j.get('job_fields') or []):die('AIAPI partial request identity evidence missing')
if not {'callback_status','verification','received_at'}.issubset(set(j.get('callback_fields') or [])):die('AIAPI callback partial evidence drift')
if not {'artifact_ref','version','provider_output_ref'}.issubset(set(j.get('artifact_fields') or [])):die('AIAPI artifact partial evidence drift')
if j.get('retry_preserves_independent_attempt') is not True or j.get('artifact_silent_overwrite')!='FORBIDDEN' or j.get('unverified_callback_success')!='FORBIDDEN':die('AIAPI attempt/artifact guard drift')
# Coverage classification is deterministic and conservative.
fc=A.get('field_coverage') or {}
if set(fc)!=set(REQ):die('audit coverage field universe drift')
for f in EXACT:
 row=fc.get(f) or {}
 if row.get('classification')!='EXACT_RESOLUTION_CANDIDATE' or row.get('successor_compile_eligible') is not True:die(f+' must be exact candidate')
for f in UNRES:
 row=fc.get(f) or {}
 if row.get('successor_compile_eligible') is not False or row.get('classification') not in {'PARTIAL_NOT_EXACT','UNRESOLVED_NO_EXACT_BINDING_IDENTIFIED'}:die(f+' must remain unresolved/partial')
if (fc.get('cancel') or {}).get('classification')!='UNRESOLVED_NO_EXACT_BINDING_IDENTIFIED':die('cancel must remain no-exact-binding identified')
for page in ('CORE-01','ASSET-01'):
 p=(A.get('page_projection') or {}).get(page) or {}
 if p.get('exact_resolution_candidate_fields')!=EXACT or p.get('exact_resolution_candidate_count')!=5 or p.get('unresolved_fields')!=UNRES or p.get('unresolved_count_if_successor_compiled')!=7:die(page+' audit projection drift')
math=A.get('candidate_successor_math') or {}
if math!={'predecessor_unresolved_binding_count':24,'exact_resolution_candidate_binding_count':10,'candidate_unresolved_binding_count_after_successor_compile':14,'current_unresolved_binding_count_after_audit_only':24,'audit_authorizes_current_mutation':False}:die('candidate successor math drift')
pol=A.get('policy') or {}
if pol.get('semantic_similarity_as_exact_binding')!='FORBIDDEN' or pol.get('cross_authority_field_union_without_explicit_binding')!='FORBIDDEN' or pol.get('ai_default_lifecycle_values')!='FORBIDDEN' or pol.get('raw_source_mutation_allowed') is not False or pol.get('current_authority_mutation_allowed') is not False:die('audit safety policy drift')
eff=A.get('stage2_effect') or {}
if eff.get('async_provider_contract_current_revision')!='R1' or eff.get('async_provider_unresolved_lifecycle_binding_count')!=24 or eff.get('functional_completion') is not False or eff.get('exit_gate_result')!='BLOCKED' or eff.get('website_construction_allowed') is not False or eff.get('deployment_allowed') is not False:die('audit falsely mutates Current/Stage2/site/deploy')
print('PASS: Async lifecycle Authority audit preserves R1 Current at 24 unresolved bindings and performs no Current mutation')
print('PASS: exact successor candidates are only input_fingerprint, idempotency, succeeded, failed, retry_eligibility = 5/page')
print('PASS: request_identity, queued, running, cancel, callback/result provenance, output persistence, audit correlation remain 7/page unresolved/partial')
print('PASS: all audited sources are exact Current Authority Manifest members; semantic similarity/cross-source inference remains forbidden')
