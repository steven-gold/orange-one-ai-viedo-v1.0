#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, yaml
root=Path('.')
base=root/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
gap=base/'FUNCTIONAL_CHAIN_GAP_LEDGER_R4.yaml'
pages={
 'CORE-01':base/'EXTERNAL_AUTHORITY/ASYNC_REMAINING/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
 'ASSET-01':base/'EXTERNAL_AUTHORITY/ASYNC_REMAINING/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
}
LOCKED={
 gap:'29855a6aa9940b6ea64ca75d355c60acda3d2b94',
 pages['CORE-01']:'9490f3bcc28c5511bc04d6c3ce53c026e3c4667f',
 pages['ASSET-01']:'9668e2307c722ea4cf64f93f07c92da1b3abcc28',
}
SCHEMA_KEYS={'request_schema','request_schema_id','payload_schema','input_schema','required_body','body_schema','request_fields','payload_fields','input_contract','payload_contract','form_schema'}

def die(m): raise SystemExit(m)
def load(p):
 d=yaml.safe_load(p.read_text(encoding='utf-8'))
 if not isinstance(d,dict): die('mapping required:'+str(p))
 return d
def gitobj(p):
 r=subprocess.run(['git','rev-parse','HEAD:'+str(p)],text=True,capture_output=True)
 if r.returncode: die('git object missing:'+str(p))
 return r.stdout.strip()
def walk(obj):
 if isinstance(obj,dict):
  yield obj
  for v in obj.values(): yield from walk(v)
 elif isinstance(obj,list):
  for v in obj: yield from walk(v)
def pick(d,*keys):
 for k in keys:
  v=d.get(k)
  if v not in (None,'',[]): return v
 return None
def schema_signals(d):
 return sorted(k for k in d if k in SCHEMA_KEYS)
for p,b in LOCKED.items():
 if gitobj(p)!=b: die('locked source drift:'+str(p))
G=load(gap)
cg=(G.get('category_groups') or {}).get('PAYLOAD_INPUT_CONTRACT_MISSING') or {}
if cg.get('class')!='INPUT_SOURCE_GAP': die('payload gap class drift')
expected={}
for page in ('CORE-01','ASSET-01'):
 row=cg.get(page) or {}
 acts=row.get('action_uids') or []
 expected[page]=acts
 if len(acts)!=(16 if page=='CORE-01' else 18): die(page+' payload action count drift')
if sum(map(len,expected.values()))!=34: die('payload action universe must remain 34')
rows=[]
for page,p in pages.items():
 D=load(p); all_dicts=list(walk(D))
 action_index={}
 port_index={}
 for d in all_dicts:
  au=d.get('action_uid')
  if au: action_index.setdefault(au,[]).append(d)
  pu=d.get('port_uid')
  # controls may repeat action_uid but ports should be unique; index every port-shaped dict.
  if pu: port_index.setdefault(pu,[]).append(d)
 for au in expected[page]:
  candidates=[d for d in action_index.get(au,[]) if isinstance(d.get('runtime_binding'),dict)]
  if len(candidates)!=1: die(f'{au}: expected exactly one action definition with runtime_binding, got {len(candidates)}')
  a=candidates[0]; rb=a['runtime_binding']; kind=rb.get('binding_kind')
  port_uid=pick(rb,'port_uid','source_port_uid')
  shared_operation=pick(rb,'shared_operation_id','operation_id','registered_operation','operation')
  port=None
  if port_uid:
   ports=[d for d in port_index.get(port_uid,[]) if any(k in d for k in ('operation','registered_operation','method_path','method_effective_path','boundary'))]
   # Deduplicate identical object identities serialized through repeated refs is not expected.
   if len(ports)!=1: die(f'{au}: expected one operational port {port_uid}, got {len(ports)}')
   port=ports[0]
  operation=shared_operation or (pick(port or {},'operation','registered_operation','operation_id'))
  method_path=pick(port or {},'method_path','method_effective_path')
  method=pick(port or {},'method')
  path=pick(port or {},'path')
  if method_path and (not method or not path):
   parts=str(method_path).split(' ',1)
   if len(parts)==2:
    method=method or parts[0]; path=path or parts[1]
  signals=sorted(set(schema_signals(a)+schema_signals(rb)+schema_signals(port or {})))
  if operation and port_uid: status='EXACT_PORT_OPERATION_MAPPING'
  elif operation: status='EXACT_OPERATION_WITHOUT_PORT'
  else: status='BINDING_INCOMPLETE'
  rows.append({
   'page_uid':page,'action_uid':au,'binding_kind':kind,'port_uid':port_uid,'operation_id':operation,
   'method':method,'path':path,'mapping_status':status,'inline_schema_signal_keys':signals,
   'inline_schema_candidate_present':bool(signals)
  })
# Exact row universe and deterministic ordering from gap ledger.
if len(rows)!=34 or len({r['action_uid'] for r in rows})!=34: die('inventory row uniqueness/count drift')
summary={
 'total_actions':34,
 'page_counts':{'CORE-01':16,'ASSET-01':18},
 'mapping_status_counts':{},
 'inline_schema_candidate_count':sum(1 for r in rows if r['inline_schema_candidate_present']),
 'inventory_changes_current_gap_count':False,
 'current_payload_gap_count':34,
}
for r in rows: summary['mapping_status_counts'][r['mapping_status']]=summary['mapping_status_counts'].get(r['mapping_status'],0)+1
out={
 'schema_version':1,
 'artifact_type':'PAYLOAD_ACTION_OPERATION_INVENTORY_RESULT',
 'governance_overlay':'v2.1.12','run_uid':'FRESH-RUN-003','stage_uid':'STAGE-02',
 'source_gap_ledger_git_blob':LOCKED[gap],
 'source_page_authority_blobs':{'CORE-01':LOCKED[pages['CORE-01']],'ASSET-01':LOCKED[pages['ASSET-01']]},
 'classification_rule':'Operation/route/port presence is inventory evidence only and never equals a payload/request schema.',
 'rows':rows,'summary':summary,
 'functional_completion_claim':False,'website_construction_allowed':False,'deployment_allowed':False
}
Path('stage2_payload_action_operation_inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS: exact 34-action PAYLOAD_INPUT_CONTRACT_MISSING universe inventoried from R4 gap ledger')
print('PASS: each action is resolved only through its Current Page Authority runtime_binding; missing mappings are never guessed')
print('PASS: operation/route/port inventory does not mutate the Current 34 payload gaps')
print(json.dumps(summary,ensure_ascii=False,sort_keys=True))
