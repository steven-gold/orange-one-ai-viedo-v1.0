#!/usr/bin/env python3
from pathlib import Path
import json,re,subprocess,yaml

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
DIRECT_FIELDS=('audit_event_uid','event_uid','audit_event','event_ref')

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
def event_token(se):
 se=str(se or '')
 if '|' in se:
  tail=se.split('|',1)[1].strip()
  if tail and tail.lower() not in {'event none','none'}: return tail
 m=re.search(r'\b[a-z][a-z0-9_]*\.[a-z0-9_.]+\b',se)
 return m.group(0) if m else None

def explicit_signals(node):
 out={f:node.get(f) for f in DIRECT_FIELDS if isinstance(node,dict) and nonempty(node.get(f))}
 tok=event_token(node.get('state_event')) if isinstance(node,dict) else None
 if tok: out['state_event_token']=tok
 return out

for p,b in LOCKED.items():
 if gitobj(p)!=b: die('locked bounded Authority/source drift: '+str(p))
G=load(gap_path); M=load(manifest_path)
if ((M.get('load_policy') or {}).get('only_listed_files_are_current_authority') is not True or
    (M.get('load_policy') or {}).get('unlisted_authority_or_spec_file')!='DO_NOT_LOAD_FOR_CURRENT_CONSTRUCTION'):
 die('Current Authority manifest load policy drift')
cat=(G.get('category_groups') or {}).get('AUDIT_EVENT_NODE_MISSING') or {}
if cat.get('class')!='ARCHITECTURE_GAP': die('audit-event category class drift')
universe=[]
for page,count in [('CORE-01',4),('ASSET-01',9)]:
 grp=cat.get(page) or {}; uids=grp.get('action_uids') or []
 if len(uids)!=count or grp.get('expanded_gap_count')!=count: die(page+' audit-event universe drift')
 universe.extend((page,uid) for uid in uids)
summary=G.get('summary') or {}
if (summary.get('categories') or {}).get('AUDIT_EVENT_NODE_MISSING')!=13: die('R4 audit-event count drift')
if (summary.get('classes') or {}).get('ARCHITECTURE_GAP')!=133 or summary.get('total')!=167: die('R4 totals drift')

docs={role:load(path) for role,path in sources.items()}
rows=[]; authorized=[]
for page,aid in universe:
 candidates=[]; accepted=[]
 for role,doc in docs.items():
  for pth,node in walk(doc):
   if node.get('action_uid')!=aid: continue
   sig=explicit_signals(node)
   ok=bool(sig)
   rec={'source_role':role,'node_path':'/'.join(pth),'explicit_event_signals':sig,'exact_binding_authorized':ok}
   candidates.append(rec)
   if ok: accepted.append(rec)
 if accepted: authorized.append({'page':page,'action_uid':aid})
 rows.append({'page':page,'action_uid':aid,'exact_action_nodes_found':len(candidates),'candidate_nodes':candidates,
              'authorized_exact_audit_event_bindings':accepted,'authorized_for_gap_removal':bool(accepted),
              'gap_status_after_audit':'RESOLVABLE_BY_EXACT_CURRENT_AUTHORITY' if accepted else 'OPEN'})
S={'gap_action_total':13,'page_counts':{'CORE-01':4,'ASSET-01':9},'bounded_authority_source_count':len(sources),
   'actions_with_any_exact_action_node':sum(r['exact_action_nodes_found']>0 for r in rows),
   'exact_action_node_total':sum(r['exact_action_nodes_found'] for r in rows),
   'actions_with_exact_audit_event_binding_authorized_for_removal':len(authorized),
   'authorized_rows':authorized,'unresolved_gap_count_after_audit':13-len(authorized),
   'audit_changes_current_gap_count':False,'current_audit_event_gap_count':13,
   'current_architecture_gap_total':133,'current_functional_gap_total':167}
out={'schema_version':1,'artifact_type':'AUDIT_EVENT_AUTHORITY_AUDIT_RESULT',
 'artifact_uid':'FRESH-RUN-003-STAGE2-AUDIT-EVENT-AUTHORITY-AUDIT-V212-R1','governance_overlay':'v2.1.12',
 'run_uid':'FRESH-RUN-003','stage_uid':'STAGE-02','source_gap_ledger_git_blob':LOCKED[gap_path],
 'bounded_authority_sources':[{'role':r,'ref':str(p.relative_to(root)),'git_blob':LOCKED[p]} for r,p in sources.items()],
 'acceptance_rule':{'exact_action_uid_required':True,'accepted_direct_fields':list(DIRECT_FIELDS),
  'exact_action_node_state_event_token_allowed':True,
  'generic_logging_audit_policy':'FORBIDDEN','trace_or_correlation_id_as_audit_event':'FORBIDDEN',
  'route_operation_owner_or_unrelated_event_registry_as_binding':'FORBIDDEN','cross_source_semantic_join':'FORBIDDEN',
  'ai_guess_or_default_substitution':'FORBIDDEN'},
 'rows':rows,'summary':S,'functional_completion_claim':False,'website_construction_allowed':False,'deployment_allowed':False}
Path('stage2_audit_event_authority_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS: bounded Current Authority audit-event audit scanned exact 13-action universe')
print('PASS: exact action_uid plus explicit event/audit binding required; generic audit/log/trace semantics forbidden')
print('PASS: audit is classification-only and never mutates Current gap totals')
print(json.dumps(S,ensure_ascii=False,sort_keys=True))
