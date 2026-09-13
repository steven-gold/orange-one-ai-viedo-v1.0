#!/usr/bin/env python3
from pathlib import Path
import subprocess,yaml
root=Path('.')
base=root/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
audit=base/'ASYNC_PROVIDER_REMAINING_LIFECYCLE_AUTHORITY_AUDIT_R2.yaml'
current=base/'ASYNC_PROVIDER_CONTRACT_R3_CURRENT.yaml'
blocker=base/'BLOCKER_LEDGER_R4.yaml'
manifest=base/'EXTERNAL_AUTHORITY/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml'
sources={
 'SYSTEM_AUTHORITY':(base/'EXTERNAL_AUTHORITY/GAP-008/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml','b09b7ca50313172ea021d9da0c8d57f2942f7b19'),
 'PRODUCTION_SCRIPT_V1_3':(base/'EXTERNAL_AUTHORITY/GAP-005/ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT_FINAL_LOCKED_V1.3.yaml','12ef6d233e09f84571dd5d694ae8e3789ae70502'),
 'ASYNC_QUEUE_RUNTIME':(base/'EXTERNAL_AUTHORITY/ASYNC/ACPOS_PRODUCTION_ASYNC_QUEUE_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml','ac3619b3bc547ce06f244c239fa69d3cac78da76'),
 'AIAPI_PAGE':(base/'EXTERNAL_AUTHORITY/GAP-008/ACPOS_AIAPI-01_FINAL_LOCKED_ENCODING.yaml','dd9f05e295af57cc833e90d1a12030c8198580c6'),
 'CORE_PAGE':(base/'EXTERNAL_AUTHORITY/ASYNC_REMAINING/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml','9490f3bcc28c5511bc04d6c3ce53c026e3c4667f'),
 'ASSET_PAGE':(base/'EXTERNAL_AUTHORITY/ASYNC_REMAINING/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml','9668e2307c722ea4cf64f93f07c92da1b3abcc28'),
 'PAGE_INTEGRATION_MATRIX':(base/'EXTERNAL_AUTHORITY/ASYNC_REMAINING/ACPOS_PAGE_INTEGRATION_MATRIX_FINAL_LOCKED_CURRENT.yaml','0150019aaa56666b43af88948551f0c57a77762c'),
}
REMAIN=['request_identity','queued','running','cancel','callback_result_provenance','output_persistence','audit_correlation']

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
# Immutable Current baseline and enumerated Authority bytes.
locked={
 current:'b66515c094dd12d6832e4300817591fbe41b739f',
 blocker:'e675cc68b0eb6bfd7c484e860eef3b5ebc146890',
 manifest:'465329b6fb19b8e44c3083a9f280015ee95cc55c',
 audit:'4b981a2fdc0d23bde71f331b3b0fb768a36f41c0',
}
for _,(p,b) in sources.items(): locked[p]=b
for p,b in locked.items():
 if gitobj(p)!=b:die('remaining async audit locked artifact drift:'+str(p))
A=load(audit); C=load(current); B=load(blocker); M=load(manifest)
if A.get('artifact_type')!='ASYNC_REMAINING_LIFECYCLE_AUTHORITY_AUDIT' or A.get('status')!='AUDITED_NO_ADDITIONAL_EXACT_BINDINGS_CURRENT_REMAINS_14':die('audit identity/status drift')
if A.get('pinned_source_commit')!='6c8a0c3334ccd17942ba14079976fb295859a43c':die('pinned source commit drift')
if A.get('remaining_required_fields')!=REMAIN:die('remaining S061 field universe drift')
cb=A.get('current_baseline') or {}
if cb.get('async_provider_contract_git_blob')!='b66515c094dd12d6832e4300817591fbe41b739f' or cb.get('unresolved_lifecycle_binding_count')!=14 or cb.get('unresolved_per_page')!=7 or cb.get('pages')!=['CORE-01','ASSET-01']:die('audit Current baseline drift')
# Ensure every enumerated materialized Authority is exactly the declared Git blob and is part of the audit set.
rows=A.get('materialized_audit_sources') or []
byrole={r.get('authority_role'):r for r in rows}
required_roles={'CURRENT_MANIFEST','SYSTEM_AUTHORITY','PRODUCTION_SCRIPT_V1_3','ASYNC_QUEUE_RUNTIME','AIAPI_PAGE','CORE_PAGE','ASSET_PAGE','PAGE_INTEGRATION_MATRIX'}
if set(byrole)!=required_roles:die('enumerated Authority role universe drift')
if byrole['CURRENT_MANIFEST'].get('git_blob')!='465329b6fb19b8e44c3083a9f280015ee95cc55c':die('manifest source binding drift')
for role,(p,b) in sources.items():
 if byrole[role].get('git_blob')!=b:die(role+' audit source blob drift')
# Confirm these Authority sources are admissible Current members by exact source path through the Current Manifest.
cas=M.get('current_authority_set') or {}
flat=[]
for v in cas.values():
 if isinstance(v,list): flat.extend(v)
for role in ('SYSTEM_AUTHORITY','PRODUCTION_SCRIPT_V1_3','ASYNC_QUEUE_RUNTIME','AIAPI_PAGE','CORE_PAGE','ASSET_PAGE','PAGE_INTEGRATION_MATRIX'):
 source_path=byrole[role].get('source_path')
 if source_path not in flat:die(role+' is not an exact Current Manifest member')
# Conservative second-round result: no new field accepted; Current remains 14.
find=A.get('review_findings') or {}
if set(find)!=set(REMAIN):die('review finding field universe drift')
for f in REMAIN:
 row=find.get(f) or {}
 if row.get('accepted_exact_binding') is not False:die(f+' was improperly accepted as exact')
 if not isinstance(row.get('observations'),list) or not row.get('observations'):die(f+' lacks observations')
pp=A.get('per_page_result') or {}
for page in ('CORE-01','ASSET-01'):
 p=pp.get(page) or {}
 if p.get('unresolved_lifecycle_fields')!=REMAIN or p.get('unresolved_count_before')!=7 or p.get('additional_exact_resolved_fields')!=[] or p.get('unresolved_count_after_audit_only')!=7:die(page+' remaining audit projection drift')
r=A.get('result') or {}
expected={'additional_exact_resolved_field_count_per_page':0,'additional_exact_resolved_binding_count':0,'current_unresolved_binding_count_before':14,'current_unresolved_binding_count_after_audit_only':14,'audit_authorizes_current_mutation':False,'classification':'TRUE_AUTHORITY_CONTRACT_GAP_WITHIN_ENUMERATED_CURRENT_AUTHORITIES','repository_wide_absence_claim':False,'compiler_omission_claim':False}
for k,v in expected.items():
 if r.get(k)!=v:die('audit result drift:'+k)
# Guard against broad/no-evidence closure semantics.
if 'limited to the enumerated Current Authority sources' not in str(A.get('scope_statement')):die('audit scope is not explicitly bounded')
safe=A.get('safety') or {}
for k in ('semantic_similarity_as_exact_binding','cross_authority_composition_without_explicit_binding','ui_read_model_as_lifecycle_authority','runtime_implementation_as_authority_without_current_delegation','ai_inference_or_default'):
 if safe.get(k)!='FORBIDDEN':die('safety drift:'+k)
if safe.get('raw_source_mutation_allowed') is not False or safe.get('predecessor_mutation_allowed') is not False:die('mutation safety drift')
# Known textual signals remain only signals, not accepted S061 bindings.
system=sources['SYSTEM_AUTHORITY'][0].read_text(encoding='utf-8')
prod=sources['PRODUCTION_SCRIPT_V1_3'][0].read_text(encoding='utf-8')
queue=sources['ASYNC_QUEUE_RUNTIME'][0].read_text(encoding='utf-8')
aiapi=sources['AIAPI_PAGE'][0].read_text(encoding='utf-8')
core=sources['CORE_PAGE'][0].read_text(encoding='utf-8')
asset=sources['ASSET_PAGE'][0].read_text(encoding='utf-8')
matrix=sources['PAGE_INTEGRATION_MATRIX'][0].read_text(encoding='utf-8')
if 'request_identity' in system or 'audit_correlation' in system:die('System Authority now contains an exact field token; re-audit required')
if 'request_identity' in matrix:die('Integration Matrix now contains request_identity; re-audit required')
if 'callback_fields:' not in aiapi or 'frontend_job_state_write: FORBIDDEN' not in aiapi:die('AIAPI callback read-model evidence drift')
if 'correlation_id REQUIRED' not in queue:die('queue correlation evidence drift')
if 'api_request_hash -> job/result lineage' not in prod:die('Production Script lineage evidence drift')
if 'callback' in core.lower():die('CORE page now contains callback token; re-audit required')
if 'Runtime / Provider' not in asset or 'Job/Attempt/Callback/Retry/Trace' not in asset:die('ASSET read-model evidence drift')
# Current contract and blocker must remain exactly 14 and BLOCKED after audit only.
cs=C.get('current_state') or {}
if cs.get('unresolved_lifecycle_binding_count')!=14 or cs.get('is_current') is not True or cs.get('functional_completion') is not False or cs.get('stage2_exit_gate_result')!='BLOCKED' or cs.get('website_construction_allowed') is not False or cs.get('deployment_allowed') is not False:die('Current async state mutated by audit')
bs=B.get('summary') or {}
if bs.get('async_provider_unresolved_lifecycle_binding_count')!=14 or bs.get('open_blocker_count')!=3 or bs.get('blocked_functional_gap_total')!=167 or bs.get('functional_completion') is not False or bs.get('stage2_exit_gate')!='BLOCKED':die('Current blocker state drift')
p=A.get('current_state_preservation') or {}
for k,v in {'open_functional_gap_total':167,'blocker_count':3,'async_provider_unresolved_lifecycle_binding_count':14,'functional_completion':False,'stage2_exit_gate_result':'BLOCKED','website_construction_allowed':False,'deployment_allowed':False}.items():
 if p.get(k)!=v:die('audit Current preservation drift:'+k)
print('PASS: second-round Async Authority audit is bounded to exact enumerated Current Authority sources')
print('PASS: no additional exact S061 binding is accepted for the remaining seven fields per page')
print('PASS: Current Async lifecycle remains 14 unresolved; no audit-only mutation or compiler-omission claim is permitted')
print('PASS: Stage-02, website construction, and deployment remain BLOCKED')
