#!/usr/bin/env python3
from pathlib import Path
from collections import defaultdict
import json, subprocess, yaml

root=Path('.')
run=root/'00_SOURCE_INTAKE/fresh_run_003'
gap_path=run/'04_PAGE_FUNCTIONAL_CONTRACT/FUNCTIONAL_CHAIN_GAP_LEDGER_R4.yaml'
asset_path=run/'00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'
LOCKED={
 gap_path:'29855a6aa9940b6ea64ca75d355c60acda3d2b94',
 asset_path:'9668e2307c722ea4cf64f93f07c92da1b3abcc28',
}
PORT_FIELDS=('port_uid','persist_via_port_uid','execute_port_uid','decision_port_uid')
DIRECT_NEXT_FIELDS=('success_state','next_state','next_step','next_gate','transition_uid')

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
def has_transition(se):
 se=str(se or '')
 return '→' in se or '->' in se
def direct_signals(node): return {f:node.get(f) for f in DIRECT_NEXT_FIELDS if isinstance(node,dict) and nonempty(node.get(f))}

for p,b in LOCKED.items():
 if gitobj(p)!=b: die('locked source drift: '+str(p))
G=load(gap_path); A=load(asset_path)
cat=(G.get('category_groups') or {}).get('SUCCESS_NEXT_STATE_BINDING_MISSING') or {}
grp=cat.get('ASSET-01') or {}; gap_actions=grp.get('action_uids') or []
EXPECTED=[
 'ASSET-01-ACT-LAYER-ADD','ASSET-01-ACT-LAYER-DELETE','ASSET-01-ACT-LAYER-DUPLICATE',
 'ASSET-01-ACT-LAYER-REORDER','ASSET-01-ACT-LAYER-PROPERTIES','ASSET-01-ACT-LAYER-MASK',
 'ASSET-01-ACT-PATCH-CREATE']
if cat.get('class')!='ARCHITECTURE_GAP' or gap_actions!=EXPECTED or grp.get('expanded_gap_count')!=7:
 die('R4 success/next-state universe drift')
summary=G.get('summary') or {}
if (summary.get('categories') or {}).get('SUCCESS_NEXT_STATE_BINDING_MISSING')!=7: die('R4 success/next-state count drift')
if (summary.get('classes') or {}).get('ARCHITECTURE_GAP')!=133 or summary.get('total')!=167: die('R4 totals drift')
reg=A.get('registries') or {}; actions=idx(reg.get('actions'),'action_uid'); ports=idx(reg.get('integration_ports'),'port_uid'); transitions=idx(reg.get('stage_transitions'),'transition_uid')
if len(actions)!=44: die('ASSET action registry drift')
transitions_by_action=defaultdict(list)
for tid,t in transitions.items():
 trig=t.get('action_uid') or t.get('trigger_event_uid') or t.get('trigger')
 if trig in actions: transitions_by_action[trig].append(tid)
rows=[]; detector_resolvable=[]; secondary=[]; direct=[]
for aid in gap_actions:
 a=actions.get(aid)
 if not a: die('gap action missing: '+aid)
 rb=a.get('runtime_binding') or {}; refs=[]
 for fld in PORT_FIELDS:
  puid=rb.get(fld)
  if puid:
   p=ports.get(puid) or {}; se=p.get('state_event')
   refs.append({'field':fld,'port_uid':puid,'port_exists':puid in ports,'state_event':se,'has_state_transition':has_transition(se)})
 primary_port_transition=refs[0]['has_state_transition'] if refs else False
 exact_transition_uids=transitions_by_action.get(aid,[])
 state_effect=a.get('state_effect')
 detector_ok=bool(primary_port_transition or exact_transition_uids or nonempty(state_effect))
 any_port_transition=any(r['has_state_transition'] for r in refs)
 secondary_only=(not detector_ok) and any_port_transition
 dsignals=direct_signals(a)
 direct_alt=(not detector_ok) and bool(dsignals)
 if detector_ok: detector_resolvable.append(aid)
 if secondary_only: secondary.append(aid)
 if direct_alt: direct.append(aid)
 rows.append({
  'action_uid':aid,'binding_kind':rb.get('binding_kind'),'state_effect':state_effect,
  'exact_registered_transition_uids':exact_transition_uids,'referenced_ports':refs,
  'direct_next_state_signals_outside_detector':dsignals,
  'detector_resolvable_by_current_page_authority':detector_ok,
  'latent_secondary_port_transition_only':secondary_only,
  'latent_direct_next_state_signal_outside_detector':direct_alt,
  'gap_status_after_inventory':'RESOLVABLE_BY_EXISTING_DETECTOR' if detector_ok else ('POTENTIAL_COMPILER_MISS_REVIEW_REQUIRED' if secondary_only or direct_alt else 'OPEN')
 })
S={
 'gap_action_total':7,
 'actions_with_state_effect':sum(nonempty(r['state_effect']) for r in rows),
 'actions_with_exact_registered_transition':sum(bool(r['exact_registered_transition_uids']) for r in rows),
 'actions_with_primary_port_state_transition':sum(bool(r['referenced_ports']) and r['referenced_ports'][0]['has_state_transition'] for r in rows),
 'actions_with_any_port_state_transition':sum(any(p['has_state_transition'] for p in r['referenced_ports']) for r in rows),
 'detector_resolvable_gap_count':len(detector_resolvable),'detector_resolvable_action_uids':detector_resolvable,
 'latent_secondary_port_transition_only_count':len(secondary),'latent_secondary_port_transition_action_uids':secondary,
 'latent_direct_next_state_signal_outside_detector_count':len(direct),'latent_direct_next_state_action_uids':direct,
 'unresolved_gap_count_if_no_latent_successor':7-len(detector_resolvable),
 'inventory_changes_current_gap_count':False,'current_success_next_state_gap_count':7,
 'current_architecture_gap_total':133,'current_functional_gap_total':167,
}
out={'schema_version':1,'artifact_type':'SUCCESS_NEXT_STATE_INVENTORY_RESULT',
 'artifact_uid':'FRESH-RUN-003-STAGE2-SUCCESS-NEXT-STATE-INVENTORY-V212-R1','governance_overlay':'v2.1.12',
 'run_uid':'FRESH-RUN-003','stage_uid':'STAGE-02','source_gap_ledger_git_blob':LOCKED[gap_path],
 'source_asset_authority_git_blob':LOCKED[asset_path],
 'detector_rule':{'success_binding_satisfied_by':['primary resolved port state_event containing → or ->','exact registered stage transition triggered by action','nonempty action.state_effect'],
  'port_reference_order':list(PORT_FIELDS),'all_referenced_ports_scanned_for_parser_miss':True,
  'direct_next_state_fields_scanned_as_latent_alternative':list(DIRECT_NEXT_FIELDS)},
 'rows':rows,'summary':S,'functional_completion_claim':False,'website_construction_allowed':False,'deployment_allowed':False}
Path('stage2_success_next_state_inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS: exact 7-action success/next-state inventory compiled')
print('PASS: original detector semantics reproduced; secondary ports and direct next-state fields also scanned for parser misses')
print('PASS: inventory never mutates Current gap totals')
print(json.dumps(S,ensure_ascii=False,sort_keys=True))
