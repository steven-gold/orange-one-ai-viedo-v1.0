#!/usr/bin/env python3
from pathlib import Path
from collections import defaultdict
import json, subprocess, yaml

root=Path('.')
run=root/'00_SOURCE_INTAKE/fresh_run_003'
raw=run/'00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'
gap=run/'04_PAGE_FUNCTIONAL_CONTRACT/FUNCTIONAL_CHAIN_GAP_LEDGER_R4.yaml'
RAW_BLOB='9668e2307c722ea4cf64f93f07c92da1b3abcc28'
GAP_BLOB='29855a6aa9940b6ea64ca75d355c60acda3d2b94'
AID='ASSET-01-ACT-FINDING-CREATE'
TRIGGER_FIELDS=('trigger_event_uid','trigger_uid','invocation','system_trigger','trigger_kind')

def die(m): raise SystemExit(m)
def load(p):
 d=yaml.safe_load(p.read_text(encoding='utf-8'))
 if not isinstance(d,dict): die('mapping required: '+str(p))
 return d
def gitobj(p):
 r=subprocess.run(['git','rev-parse','HEAD:'+str(p)],text=True,capture_output=True)
 if r.returncode: die('git object missing: '+str(p))
 return r.stdout.strip()
def idx(items,key): return {x.get(key):x for x in (items or []) if isinstance(x,dict) and x.get(key)}
def nonempty(v): return v not in (None,'',[],{})
def walk(obj,path=()):
 if isinstance(obj,dict):
  yield path,obj
  for k,v in obj.items(): yield from walk(v,path+(str(k),))
 elif isinstance(obj,list):
  for i,v in enumerate(obj): yield from walk(v,path+(str(i),))
def contains_aid(v):
 if isinstance(v,str): return AID in v
 if isinstance(v,list): return any(contains_aid(x) for x in v)
 if isinstance(v,dict): return any(contains_aid(x) for x in v.values())
 return False

if gitobj(raw)!=RAW_BLOB: die('ASSET Raw Source blob drift')
if gitobj(gap)!=GAP_BLOB: die('R4 gap ledger blob drift')
D=load(raw); G=load(gap); reg=D.get('registries') or {}
actions=idx(reg.get('actions'),'action_uid')
controls=idx(reg.get('controls'),'control_uid')
transitions=idx(reg.get('stage_transitions'),'transition_uid')
if AID not in actions: die('target action missing')
cat=(G.get('category_groups') or {}).get('ACTION_WITHOUT_CONTROL_OR_TRIGGER') or {}
agrp=cat.get('ASSET-01') or {}
if cat.get('class')!='ARCHITECTURE_GAP' or agrp.get('action_uids')!=[AID] or agrp.get('expanded_gap_count')!=1:
 die('R4 action-without-control-or-trigger universe drift')
summary=G.get('summary') or {}
if (summary.get('categories') or {}).get('ACTION_WITHOUT_CONTROL_OR_TRIGGER')!=1: die('R4 category count drift')
if (summary.get('classes') or {}).get('ARCHITECTURE_GAP')!=133 or summary.get('total')!=167: die('R4 totals drift')

registered_controls=[]
for cid,c in controls.items():
 if c.get('action_uid')==AID: registered_controls.append(cid)
registered_transitions=[]
for tid,t in transitions.items():
 trig=t.get('action_uid') or t.get('trigger_event_uid') or t.get('trigger')
 if trig==AID: registered_transitions.append(tid)
a=actions[AID]
explicit_trigger_fields={f:a.get(f) for f in TRIGGER_FIELDS if nonempty(a.get(f))}

latent_refs=[]
for pth,node in walk(D):
 if not contains_aid(node): continue
 p='/'.join(pth)
 # Exclude the canonical action row itself; exact registered control/transition are already counted above.
 if p.startswith('registries/actions/') and node.get('action_uid')==AID: continue
 if p.startswith('registries/controls/') and node.get('action_uid')==AID: continue
 if p.startswith('registries/stage_transitions/'):
  trig=node.get('action_uid') or node.get('trigger_event_uid') or node.get('trigger')
  if trig==AID: continue
 matches={k:v for k,v in node.items() if contains_aid(v)}
 if matches:
  latent_refs.append({'node_path':p,'matching_fields':matches})

resolver=bool(registered_controls or registered_transitions or explicit_trigger_fields)
out={
 'schema_version':1,
 'artifact_type':'ACTION_WITHOUT_CONTROL_OR_TRIGGER_INVENTORY_RESULT',
 'artifact_uid':'FRESH-RUN-003-STAGE2-ACTION-WITHOUT-CONTROL-OR-TRIGGER-INVENTORY-V212-R1',
 'governance_overlay':'v2.1.12','run_uid':'FRESH-RUN-003','stage_uid':'STAGE-02',
 'source_raw_git_blob':RAW_BLOB,'source_gap_ledger_git_blob':GAP_BLOB,
 'detector_rule':{
  'registered_control':'registries.controls[*].action_uid == action_uid',
  'explicit_action_trigger_fields':list(TRIGGER_FIELDS),
  'registered_stage_transition':'transition action_uid/trigger_event_uid/trigger resolves exactly to action_uid',
  'integration_port_exposure_or_state_event_is_control_or_trigger':False,
  'semantic_label_operation_or_route_match_is_control_or_trigger':False,
  'ai_inference_or_default_substitution':'FORBIDDEN'
 },
 'rows':[{
  'page':'ASSET-01','action_uid':AID,
  'registered_control_uids':registered_controls,
  'registered_control_count':len(registered_controls),
  'registered_transition_uids':registered_transitions,
  'registered_transition_trigger_count':len(registered_transitions),
  'explicit_action_trigger_fields':explicit_trigger_fields,
  'explicit_action_trigger_field_count':len(explicit_trigger_fields),
  'latent_exact_action_references_outside_detector':latent_refs,
  'latent_reference_count':len(latent_refs),
  'detector_resolvable':resolver,
  'gap_status_after_inventory':'RESOLVABLE_BY_PAGE_AUTHORITY' if resolver else 'OPEN'
 }],
 'summary':{
  'gap_action_total':1,
  'registered_control_count':len(registered_controls),
  'registered_transition_trigger_count':len(registered_transitions),
  'explicit_action_trigger_field_count':len(explicit_trigger_fields),
  'latent_reference_count':len(latent_refs),
  'detector_resolvable_action_count':1 if resolver else 0,
  'unresolved_gap_count_after_inventory':0 if resolver else 1,
  'inventory_changes_current_gap_count':False,
  'current_action_without_control_or_trigger_gap_count':1,
  'current_architecture_gap_total':133,
  'current_functional_gap_total':167
 },
 'functional_completion_claim':False,'website_construction_allowed':False,'deployment_allowed':False
}
Path('stage2_action_without_control_or_trigger_inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS: exact 1-action control/trigger inventory compiled')
print('PASS: registered control, explicit action trigger, and exact stage-transition trigger are the only detector resolvers')
print('PASS: port exposure/state_event and semantic matches remain latent evidence only, never trigger authority')
print(json.dumps(out['summary'],ensure_ascii=False,sort_keys=True))
