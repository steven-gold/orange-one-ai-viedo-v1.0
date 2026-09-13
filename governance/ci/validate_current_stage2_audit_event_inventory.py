#!/usr/bin/env python3
from pathlib import Path
import json,re,subprocess,yaml

root=Path('.')
run=root/'00_SOURCE_INTAKE/fresh_run_003'
gap_path=run/'04_PAGE_FUNCTIONAL_CONTRACT/FUNCTIONAL_CHAIN_GAP_LEDGER_R4.yaml'
pages={
 'CORE-01':run/'00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
 'ASSET-01':run/'00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
}
LOCKED={gap_path:'29855a6aa9940b6ea64ca75d355c60acda3d2b94',pages['CORE-01']:'9490f3bcc28c5511bc04d6c3ce53c026e3c4667f',pages['ASSET-01']:'9668e2307c722ea4cf64f93f07c92da1b3abcc28'}
PORT_FIELDS=('port_uid','persist_via_port_uid','execute_port_uid','decision_port_uid')
DIRECT_EVENT_FIELDS=('audit_event_uid','event_uid','audit_event','event_ref')

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
def event_token(se):
 se=str(se or '')
 if '|' in se:
  tail=se.split('|',1)[1].strip()
  if tail and tail.lower() not in {'event none','none'}: return tail
 m=re.search(r'\b[a-z][a-z0-9_]*\.[a-z0-9_.]+\b',se)
 return m.group(0) if m else None
def direct_signals(node): return {f:node.get(f) for f in DIRECT_EVENT_FIELDS if isinstance(node,dict) and nonempty(node.get(f))}

for p,b in LOCKED.items():
 if gitobj(p)!=b: die('locked source drift: '+str(p))
G=load(gap_path); cat=(G.get('category_groups') or {}).get('AUDIT_EVENT_NODE_MISSING') or {}
if cat.get('class')!='ARCHITECTURE_GAP': die('audit-event category class drift')
universe={}
for page,count in [('CORE-01',4),('ASSET-01',9)]:
 grp=cat.get(page) or {}; uids=grp.get('action_uids') or []
 if len(uids)!=count or grp.get('expanded_gap_count')!=count: die(page+' audit-event universe drift')
 universe[page]=uids
if ((G.get('summary') or {}).get('categories') or {}).get('AUDIT_EVENT_NODE_MISSING')!=13: die('R4 audit-event count drift')
if ((G.get('summary') or {}).get('classes') or {}).get('ARCHITECTURE_GAP')!=133 or (G.get('summary') or {}).get('total')!=167: die('R4 totals drift')

rows=[]; detector_resolvable=[]; secondary=[]; direct=[]
for page,uids in universe.items():
 D=load(pages[page]); reg=D.get('registries') or {}; actions=idx(reg.get('actions'),'action_uid'); ports=idx(reg.get('integration_ports'),'port_uid')
 for aid in uids:
  a=actions.get(aid)
  if not a: die(page+' missing action '+aid)
  rb=a.get('runtime_binding') or {}; refs=[]
  for fld in PORT_FIELDS:
   puid=rb.get(fld)
   if puid:
    p=ports.get(puid) or {}; se=p.get('state_event'); tok=event_token(se)
    refs.append({'field':fld,'port_uid':puid,'port_exists':puid in ports,'state_event':se,'event_token':tok})
  primary_token=refs[0]['event_token'] if refs else None
  any_token=next((r['event_token'] for r in refs if r['event_token']),None)
  action_sig=direct_signals(a); runtime_sig=direct_signals(rb)
  detector_ok=bool(primary_token)
  secondary_only=(not detector_ok) and bool(any_token)
  direct_alt=(not detector_ok) and bool(action_sig or runtime_sig)
  if detector_ok: detector_resolvable.append({'page':page,'action_uid':aid,'event_token':primary_token})
  if secondary_only: secondary.append({'page':page,'action_uid':aid,'event_token':any_token})
  if direct_alt: direct.append({'page':page,'action_uid':aid,'action_signals':action_sig,'runtime_signals':runtime_sig})
  rows.append({'page':page,'action_uid':aid,'action_event_signals':action_sig,'runtime_event_signals':runtime_sig,'referenced_ports':refs,
               'detector_primary_event_token':primary_token,'detector_resolvable_by_current_page_authority':detector_ok,
               'latent_secondary_port_event_token_only':secondary_only,'latent_direct_event_signal_outside_detector':direct_alt,
               'gap_status_after_inventory':'RESOLVABLE_BY_EXISTING_DETECTOR' if detector_ok else ('POTENTIAL_COMPILER_MISS_REVIEW_REQUIRED' if secondary_only or direct_alt else 'OPEN')})
S={'gap_action_total':13,'page_counts':{'CORE-01':4,'ASSET-01':9},
   'detector_resolvable_gap_count':len(detector_resolvable),'detector_resolvable_rows':detector_resolvable,
   'latent_secondary_port_only_count':len(secondary),'latent_secondary_port_only_rows':secondary,
   'latent_direct_event_signal_outside_detector_count':len(direct),'latent_direct_event_signal_rows':direct,
   'unresolved_gap_count_if_no_latent_successor':13-len(detector_resolvable),
   'inventory_changes_current_gap_count':False,'current_audit_event_gap_count':13,'current_architecture_gap_total':133,'current_functional_gap_total':167}
out={'schema_version':1,'artifact_type':'AUDIT_EVENT_INVENTORY_RESULT','artifact_uid':'FRESH-RUN-003-STAGE2-AUDIT-EVENT-INVENTORY-V212-R1',
     'governance_overlay':'v2.1.12','run_uid':'FRESH-RUN-003','stage_uid':'STAGE-02','source_gap_ledger_git_blob':LOCKED[gap_path],
     'source_page_blobs':{p:LOCKED[path] for p,path in pages.items()},
     'detector_rule':{'primary_port_event_token_from_state_event':True,'port_reference_order':list(PORT_FIELDS),'event_token_semantics':'pipe-tail unless none, else dotted lowercase token regex','all_referenced_ports_scanned_for_parser_miss':True,'direct_action_runtime_event_fields_scanned_as_latent_alternative':list(DIRECT_EVENT_FIELDS)},
     'rows':rows,'summary':S,'functional_completion_claim':False,'website_construction_allowed':False,'deployment_allowed':False}
Path('stage2_audit_event_inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS: exact 13-action audit-event inventory compiled')
print('PASS: original primary-port event_token semantics reproduced; all referenced ports and direct event fields also scanned for parser misses')
print('PASS: inventory never mutates Current gap totals')
print(json.dumps(S,ensure_ascii=False,sort_keys=True))
