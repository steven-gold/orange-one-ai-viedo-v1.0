#!/usr/bin/env python3
from pathlib import Path
import subprocess, yaml

root=Path('.')
base=root/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
audit=base/'STATE_TRANSITION_AUTHORITY_AUDIT_R1.yaml'
ledger=base/'STATE_TRANSITION_LEDGER.yaml'
gap=base/'FUNCTIONAL_CHAIN_GAP_LEDGER_R4.yaml'
sources={
 'CURRENT_AUTHORITY_MANIFEST': base/'EXTERNAL_AUTHORITY/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml',
 'CORE_PAGE_AUTHORITY': base/'EXTERNAL_AUTHORITY/ASYNC_REMAINING/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
 'ASSET_PAGE_AUTHORITY': base/'EXTERNAL_AUTHORITY/ASYNC_REMAINING/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
 'SYSTEM_AUTHORITY': base/'EXTERNAL_AUTHORITY/GAP-008/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml',
 'AIAPI_AUTHORITY': base/'EXTERNAL_AUTHORITY/GAP-008/ACPOS_AIAPI-01_FINAL_LOCKED_ENCODING.yaml',
 'OPERATION_REGISTRY': base/'EXTERNAL_AUTHORITY/GAP-008/operation_registry.yaml',
 'SHARED_RUNTIME_OPERATION_AUTHORITY': base/'EXTERNAL_AUTHORITY/GAP-006/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml',
 'ASYNC_QUEUE_RUNTIME_AUTHORITY': base/'EXTERNAL_AUTHORITY/ASYNC/ACPOS_PRODUCTION_ASYNC_QUEUE_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml',
 'PROVIDER_ADAPTER_AUTHORITY': base/'EXTERNAL_AUTHORITY/GAP-005/ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT_FINAL_LOCKED_V1.3.yaml',
}
LOCKED={
 audit:'3fcf16f5e2137292da8e8e9d4af631602cae1565',
 ledger:'f08d7c637a51e29dab01dc8378555d6bc4c9e635',
 gap:'29855a6aa9940b6ea64ca75d355c60acda3d2b94',
 sources['CURRENT_AUTHORITY_MANIFEST']:'465329b6fb19b8e44c3083a9f280015ee95cc55c',
 sources['CORE_PAGE_AUTHORITY']:'9490f3bcc28c5511bc04d6c3ce53c026e3c4667f',
 sources['ASSET_PAGE_AUTHORITY']:'9668e2307c722ea4cf64f93f07c92da1b3abcc28',
 sources['SYSTEM_AUTHORITY']:'b09b7ca50313172ea021d9da0c8d57f2942f7b19',
 sources['AIAPI_AUTHORITY']:'dd9f05e295af57cc833e90d1a12030c8198580c6',
 sources['OPERATION_REGISTRY']:'7d234cc2f2f831b82f2007403c71d4008b46a012',
 sources['SHARED_RUNTIME_OPERATION_AUTHORITY']:'12dbdf59a60df5b1cb3d3b18666209c05bb0c0a3',
 sources['ASYNC_QUEUE_RUNTIME_AUTHORITY']:'ac3619b3bc547ce06f244c239fa69d3cac78da76',
 sources['PROVIDER_ADAPTER_AUTHORITY']:'12ef6d233e09f84571dd5d694ae8e3789ae70502',
}
REQ=['mutation_owner','failure_state','recovery','audit_event_uid','illegal_transition_tests']

def die(m): raise SystemExit(m)
def load(p):
 d=yaml.safe_load(p.read_text(encoding='utf-8'))
 if not isinstance(d,dict): die('mapping required:'+str(p))
 return d
def gitobj(p):
 r=subprocess.run(['git','rev-parse','HEAD:'+str(p)],text=True,capture_output=True)
 if r.returncode: die('git object missing:'+str(p))
 return r.stdout.strip()
def walk(o):
 if isinstance(o,dict):
  yield o
  for v in o.values(): yield from walk(v)
 elif isinstance(o,list):
  for v in o: yield from walk(v)

for p,b in LOCKED.items():
 if gitobj(p)!=b: die('locked evidence/source drift:'+str(p))

L=load(ledger); G=load(gap); A=load(audit)
policy=L.get('required_architecture_field_policy') or {}
if policy.get('fields')!=REQ or policy.get('resolution_rule')!='EXACT_EXISTING_AUTHORITY_REQUIRED_NO_INFERENCE': die('transition required-field policy drift')
trans=L.get('transitions') or []
if len(trans)!=10 or len({t.get('transition_uid') for t in trans})!=10: die('transition universe drift')
if (L.get('summary') or {}).get('unresolved_required_field_total')!=50: die('predecessor transition unresolved total drift')
for t in trans:
 if t.get('unresolved_required_fields')!=REQ or t.get('unresolved_field_count')!=5 or t.get('status')!='OPEN': die('transition predecessor row drift:'+str(t.get('transition_uid')))

cg=(G.get('category_groups') or {}).get('STATE_TRANSITION_LEDGER_FIELD_MISSING') or {}
if cg.get('class')!='ARCHITECTURE_GAP' or cg.get('required_fields')!=REQ: die('R4 transition gap category drift')
if ((G.get('summary') or {}).get('categories') or {}).get('STATE_TRANSITION_LEDGER_FIELD_MISSING')!=50: die('R4 transition gap count drift')
if ((G.get('summary') or {}).get('classes') or {}).get('ARCHITECTURE_GAP')!=133 or (G.get('summary') or {}).get('total')!=167: die('R4 architecture/functional totals drift')

source_docs={role:load(p) for role,p in sources.items()}
explicit=[]
for t in trans:
 uid=t['transition_uid']
 for field in REQ:
  hits=[]
  for role,D in source_docs.items():
   for d in walk(D):
    if d.get('transition_uid')==uid and field in d and d.get(field) is not None:
     hits.append((role,d.get(field)))
  if hits: explicit.append((uid,field,hits))
if explicit:
 die('bounded Authority set now contains explicit transition-field bindings; audit successor required before any removal: '+repr(explicit))

if A.get('artifact_type')!='STATE_TRANSITION_AUTHORITY_AUDIT' or A.get('status')!='AUDITED_NO_EXACT_TRANSITION_FIELD_BINDING_FOUND': die('audit identity/status drift')
if A.get('required_fields')!=REQ: die('audit required fields drift')
bs=A.get('bounded_authority_sources') or []
if len(bs)!=9: die('bounded Authority source count drift')
expected_roles=list(sources.keys())
if [x.get('role') for x in bs]!=expected_roles: die('bounded Authority source order/roles drift')
for x in bs:
 role=x['role']
 if x.get('git_blob')!=LOCKED[sources[role]]: die('audit source blob drift:'+role)
rule=A.get('acceptance_rule') or {}
if rule.get('exact_binding_required') is not True or rule.get('semantic_join_by_gate_action_event_error_or_owner')!='FORBIDDEN' or rule.get('error_level_recovery_may_fill_transition_recovery') is not False or rule.get('generic_runtime_owner_may_fill_transition_mutation_owner') is not False or rule.get('generic_audit_or_correlation_may_fill_transition_audit_event_uid') is not False or rule.get('generated_illegal_transition_test_may_fill_authority') is not False or rule.get('cross_source_union_without_explicit_transition_binding') is not False: die('audit acceptance rule drift')
res=A.get('audit_result') or {}
if res.get('exact_transition_field_bindings_found')!=0 or res.get('exact_transition_field_bindings_authorized_for_removal')!=0 or res.get('unresolved_required_field_total_after_audit')!=50 or res.get('current_architecture_gap_total_after_audit')!=133 or res.get('current_functional_gap_total_after_audit')!=167 or res.get('source_scope_is_bounded_not_repository_exhaustive') is not True: die('audit result drift')
rows=A.get('transitions') or []
if len(rows)!=10: die('audit transition row count drift')
expected={t['transition_uid']:t['page_uid'] for t in trans}
for r in rows:
 uid=r.get('transition_uid')
 if uid not in expected or r.get('page_uid')!=expected[uid] or r.get('resolved_fields')!=[] or r.get('unresolved_fields')!=REQ: die('audit transition row drift:'+str(uid))
br=A.get('blocker_reason') or {}
if br.get('code')!='EXACT_TRANSITION_ARCHITECTURE_BINDING_MISSING' or br.get('ai_guess_or_default_substitution')!='FORBIDDEN': die('audit blocker reason drift')
eff=A.get('stage2_effect') or {}
if eff.get('functional_completion') is not False or eff.get('exit_gate_result')!='BLOCKED' or eff.get('website_construction_allowed') is not False or eff.get('deployment_allowed') is not False: die('audit falsely enables Stage2/site/deploy')

print('PASS: exact Stage-02 transition universe remains 10 transitions x 5 required fields = 50')
print('PASS: bounded materialized Authority set contains 0 exact transition_uid+required-field bindings')
print('PASS: error recovery/runtime owner/audit/action/event/gate semantics are not joined by inference')
print('PASS: State Transition architecture gaps remain 50; architecture total 133; functional total 167; site/deploy blocked')
