#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, yaml

root=Path('.')
base=root/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
gap_path=base/'FUNCTIONAL_CHAIN_GAP_LEDGER_R4.yaml'
manifest_path=base/'EXTERNAL_AUTHORITY/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml'
sources={
 'CURRENT_AUTHORITY_MANIFEST':manifest_path,
 'CORE_PAGE_AUTHORITY':base/'EXTERNAL_AUTHORITY/ASYNC_REMAINING/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
 'ASSET_PAGE_AUTHORITY':base/'EXTERNAL_AUTHORITY/ASYNC_REMAINING/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
 'SYSTEM_AUTHORITY':base/'EXTERNAL_AUTHORITY/GAP-008/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml',
 'AIAPI_AUTHORITY':base/'EXTERNAL_AUTHORITY/GAP-008/ACPOS_AIAPI-01_FINAL_LOCKED_ENCODING.yaml',
 'OPERATION_REGISTRY':base/'EXTERNAL_AUTHORITY/GAP-008/operation_registry.yaml',
 'SHARED_RUNTIME_OPERATION_AUTHORITY':base/'EXTERNAL_AUTHORITY/GAP-006/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml',
 'ASYNC_QUEUE_RUNTIME_AUTHORITY':base/'EXTERNAL_AUTHORITY/ASYNC/ACPOS_PRODUCTION_ASYNC_QUEUE_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml',
 'PROVIDER_ADAPTER_AUTHORITY':base/'EXTERNAL_AUTHORITY/GAP-005/ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT_FINAL_LOCKED_V1.3.yaml',
}
LOCKED={
 gap_path:'29855a6aa9940b6ea64ca75d355c60acda3d2b94',
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
AID='ASSET-01-ACT-FINDING-CREATE'
DIRECT_CONTROL_FIELDS=('control_uid','source_control_uid','control_uids')
DIRECT_TRIGGER_FIELDS=('trigger_event_uid','trigger_uid','trigger_uids','invocation','system_trigger','trigger_kind')
NESTED_HOLDERS=('control','trigger','invocation_binding','trigger_binding','control_binding')
NESTED_FIELDS=('control_uid','source_control_uid','control_uids','trigger_event_uid','trigger_uid','trigger_uids','trigger_kind')


def die(m): raise SystemExit(m)
def load(p):
 d=yaml.safe_load(p.read_text(encoding='utf-8'))
 if not isinstance(d,dict): die('mapping required: '+str(p))
 return d
def gitobj(p):
 r=subprocess.run(['git','rev-parse','HEAD:'+str(p)],text=True,capture_output=True)
 if r.returncode: die('git object missing: '+str(p))
 return r.stdout.strip()
def walk(obj,path=()):
 if isinstance(obj,dict):
  yield path,obj
  for k,v in obj.items(): yield from walk(v,path+(str(k),))
 elif isinstance(obj,list):
  for i,v in enumerate(obj): yield from walk(v,path+(str(i),))
def nonempty(v): return v not in (None,'',[],{})
def explicit_control_trigger_signals(node):
 out={}
 if not isinstance(node,dict): return out
 for f in DIRECT_CONTROL_FIELDS+DIRECT_TRIGGER_FIELDS:
  if nonempty(node.get(f)): out[f]=node.get(f)
 for holder in NESTED_HOLDERS:
  sub=node.get(holder)
  if isinstance(sub,dict):
   vals={f:sub.get(f) for f in NESTED_FIELDS if nonempty(sub.get(f))}
   if vals: out[holder]=vals
 return out

for p,b in LOCKED.items():
 if gitobj(p)!=b: die('locked bounded Authority/source drift: '+str(p))
G=load(gap_path); M=load(manifest_path)
if ((M.get('load_policy') or {}).get('only_listed_files_are_current_authority') is not True or
    (M.get('load_policy') or {}).get('unlisted_authority_or_spec_file')!='DO_NOT_LOAD_FOR_CURRENT_CONSTRUCTION'):
 die('Current Authority manifest load policy drift')
cat=(G.get('category_groups') or {}).get('ACTION_WITHOUT_CONTROL_OR_TRIGGER') or {}
grp=cat.get('ASSET-01') or {}
if cat.get('class')!='ARCHITECTURE_GAP' or grp.get('action_uids')!=[AID] or grp.get('expanded_gap_count')!=1:
 die('R4 action control/trigger universe drift')
summary=G.get('summary') or {}
if (summary.get('categories') or {}).get('ACTION_WITHOUT_CONTROL_OR_TRIGGER')!=1: die('R4 category count drift')
if (summary.get('classes') or {}).get('ARCHITECTURE_GAP')!=133 or summary.get('total')!=167: die('R4 totals drift')

docs={role:load(path) for role,path in sources.items()}
candidates=[]; accepted=[]
for role,doc in docs.items():
 for pth,node in walk(doc):
  if node.get('action_uid')!=AID: continue
  sig=explicit_control_trigger_signals(node)
  rec={
   'source_role':role,
   'node_path':'/'.join(pth),
   'explicit_control_trigger_signals':sig,
   'exposure':node.get('exposure'),
   'state_event':node.get('state_event'),
   'registered_operation':node.get('registered_operation') or node.get('operation'),
   'route_or_endpoint':node.get('route') or node.get('path') or node.get('endpoint'),
   'permission_uid':node.get('permission_uid'),
   'gate_uid':node.get('gate_uid'),
   'forbidden_generic_fields_present':any(nonempty(node.get(f)) for f in ('exposure','state_event','registered_operation','operation','route','path','endpoint','permission_uid','gate_uid')),
   'exact_binding_authorized':bool(sig),
  }
  candidates.append(rec)
  if sig: accepted.append(rec)
authorized=bool(accepted)
S={
 'gap_action_total':1,
 'bounded_authority_source_count':len(sources),
 'actions_with_any_exact_action_node':1 if candidates else 0,
 'exact_action_node_total':len(candidates),
 'actions_with_exact_control_or_trigger_binding_authorized_for_removal':1 if authorized else 0,
 'authorized_action_uids':[AID] if authorized else [],
 'unresolved_gap_count_after_audit':0 if authorized else 1,
 'audit_changes_current_gap_count':False,
 'current_action_without_control_or_trigger_gap_count':1,
 'current_architecture_gap_total':133,
 'current_functional_gap_total':167,
}
out={
 'schema_version':1,
 'artifact_type':'ACTION_CONTROL_TRIGGER_AUTHORITY_AUDIT_RESULT',
 'artifact_uid':'FRESH-RUN-003-STAGE2-ACTION-CONTROL-TRIGGER-AUTHORITY-AUDIT-V212-R1',
 'governance_overlay':'v2.1.12','run_uid':'FRESH-RUN-003','stage_uid':'STAGE-02',
 'source_gap_ledger_git_blob':LOCKED[gap_path],
 'bounded_authority_sources':[{'role':r,'ref':str(p.relative_to(root)),'git_blob':LOCKED[p]} for r,p in sources.items()],
 'acceptance_rule':{
  'exact_action_uid_required':True,
  'accepted_direct_control_fields':list(DIRECT_CONTROL_FIELDS),
  'accepted_direct_trigger_fields':list(DIRECT_TRIGGER_FIELDS),
  'accepted_nested_holders':list(NESTED_HOLDERS),
  'accepted_nested_fields':list(NESTED_FIELDS),
  'exposure_as_control_or_trigger':'FORBIDDEN',
  'state_event_as_control_or_trigger':'FORBIDDEN',
  'route_operation_permission_gate_as_control_or_trigger':'FORBIDDEN',
  'semantic_label_or_related_action_as_control_or_trigger':'FORBIDDEN',
  'cross_source_semantic_join':'FORBIDDEN',
  'ai_guess_or_default_substitution':'FORBIDDEN'
 },
 'rows':[{
  'page':'ASSET-01','action_uid':AID,
  'exact_action_nodes_found':len(candidates),
  'candidate_nodes':candidates,
  'authorized_exact_control_or_trigger_bindings':accepted,
  'authorized_for_gap_removal':authorized,
  'gap_status_after_audit':'RESOLVABLE_BY_EXACT_CURRENT_AUTHORITY' if authorized else 'OPEN'
 }],
 'summary':S,
 'functional_completion_claim':False,'website_construction_allowed':False,'deployment_allowed':False
}
Path('stage2_action_control_trigger_authority_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS: bounded Current Authority control/trigger audit scanned exact 1-action universe')
print('PASS: exact action_uid plus explicit control/trigger binding required; exposure/state_event/route/operation/permission/gate forbidden')
print('PASS: audit is classification-only and never mutates Current gap totals')
print(json.dumps(S,ensure_ascii=False,sort_keys=True))
