#!/usr/bin/env python3
from pathlib import Path
from collections import Counter,defaultdict
import json,subprocess,yaml
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'
PAGES={
 'CORE-01': run/'00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
 'ASSET-01': run/'00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'}
SPEC={p:run/f'04_PAGE_FUNCTIONAL_CONTRACT/{p}/FUNCTIONAL_CHAIN_SPEC.yaml' for p in PAGES}
RAW_BLOBS={'CORE-01':'9490f3bcc28c5511bc04d6c3ce53c026e3c4667f','ASSET-01':'9668e2307c722ea4cf64f93f07c92da1b3abcc28'}
NODE_ORDER=['BUSINESS_INTENT','PRECONDITIONS','ENTRY','OPERATOR_OR_SYSTEM_INPUT_SOURCE','CONTROL_OR_TRIGGER','GATE','PERMISSION','ACTION','VALIDATION','PAYLOAD','API_OR_ENTRY','RUNTIME_OWNER','REPOSITORY_DATA_OR_PROVIDER','AUDIT_EVENT','RESPONSE','UI_OR_CALLER_FEEDBACK','SUCCESS_STATE','NEXT_STATE','NEXT_STEP','NEXT_GATE','FAILURE_STATE','RETRY_RECOVERY_OR_ROLLBACK','TERMINAL_OUTCOME']
KNOWN_GAPS={'GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY@V1.9':'GAP-001','GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY@V1.0':'GAP-002','ACPOS_SYSTEM_AUTHORITY@V1.0':'GAP-003','ACPOS_CURRENT_NAVIGATION_PERMISSION_AUTHORITY@V1.0':'GAP-004','ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT@V1.3':'GAP-005','ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY':'GAP-006','IAM-01 / account permission runtime':'GAP-007','ACPOS shared AI Router/Capability Assignment':'GAP-008'}
def die(m): raise SystemExit(m)
def load(p):
 try: d=yaml.safe_load(p.read_text(encoding='utf-8'))
 except Exception as e: die('parse failure:'+str(p)+':'+str(e))
 if not isinstance(d,dict): die('mapping required:'+str(p))
 return d
def gitobj(path):
 r=subprocess.run(['git','rev-parse','HEAD:'+path],text=True,capture_output=True)
 if r.returncode: die('git object missing:'+path)
 return r.stdout.strip()
def idx(items,key): return {x.get(key):x for x in (items or []) if isinstance(x,dict) and x.get(key)}
def has_any(d,needles):
 txt=yaml.safe_dump(d,allow_unicode=True,sort_keys=False)
 return [v for v in needles if v in txt]
def fieldish(d,*names):
 return any(d.get(n) not in (None,'',[],{}) for n in names)
def add(gaps,page,klass,category,uid,detail): gaps.append({'page':page,'class':klass,'category':category,'uid':uid,'detail':detail})
all_summary={}; all_gaps=[]
for page,raw_path in PAGES.items():
 if gitobj(str(raw_path))!=RAW_BLOBS[page]: die(page+' Raw Source blob drift')
 d=load(raw_path); reg=d.get('registries') or {}; spec=load(SPEC[page])
 if spec.get('artifact_type')!='FUNCTIONAL_CHAIN_SPEC' or spec.get('stage_uid')!='STAGE-02' or spec.get('page_uid')!=page or spec.get('governance_overlay')!='v2.1.12': die(page+' functional spec identity drift')
 if spec.get('functional_chain_node_order')!=NODE_ORDER: die(page+' functional chain node order drift')
 rec=((spec.get('entry_gate') or {}).get('terminal_receipt') or {})
 if (rec.get('head_sha'),rec.get('run_id'),rec.get('job_denominator'),rec.get('conclusion'))!=('c6a9c2e5b38a189a6517d59345a0738618e8cd28',34755361339,'12/12','SUCCESS'): die(page+' Stage1 entry receipt drift')
 grec=spec.get('governance_predecessor_receipt') or {}
 if (grec.get('head_sha'),grec.get('run_id'),grec.get('job_denominator'),grec.get('conclusion'))!=('3247937d7b8ccd57551119b079cb33cee45e4ecc',34757919043,'13/13','SUCCESS'): die(page+' v2.1.12 governance receipt drift')
 actions=idx(reg.get('actions'),'action_uid'); controls=idx(reg.get('controls'),'control_uid'); perms=idx(reg.get('permissions'),'permission_uid'); gates=idx(reg.get('gates'),'gate_uid'); errors=idx(reg.get('errors'),'error_uid'); ports=idx(reg.get('integration_ports'),'port_uid'); states=idx(reg.get('page_states'),'state_uid'); stages=idx(reg.get('stages'),'stage_uid'); events=idx(reg.get('events'),'event_uid'); trans=idx(reg.get('stage_transitions'),'transition_uid')
 gaps=[]; controls_by_action=defaultdict(list); transitions_by_action=defaultdict(list)
 for cid,c in controls.items():
  au=c.get('action_uid')
  if au: controls_by_action[au].append(cid)
  if not au or au not in actions: add(gaps,page,'IMPLEMENTATION_GAP','CONTROL_WITHOUT_VALID_ACTION',cid,str(au))
  if c.get('gate_uid') and c.get('gate_uid') not in gates: add(gaps,page,'IMPLEMENTATION_GAP','CONTROL_GATE_REF_MISSING',cid,str(c.get('gate_uid')))
  if c.get('permission_uid') and c.get('permission_uid') not in perms: add(gaps,page,'IMPLEMENTATION_GAP','CONTROL_PERMISSION_REF_MISSING',cid,str(c.get('permission_uid')))
 for tid,t in trans.items():
  if t.get('action_uid'): transitions_by_action[t.get('action_uid')].append(tid)
 effectful=0
 for aid,a in actions.items():
  effect=a.get('effect_type'); is_effectful=effect not in {'READ_ONLY','UI_ONLY','CONTEXT_STATE'}; effectful += int(is_effectful)
  for field,registry,cat in [('permission_uid',perms,'ACTION_PERMISSION_REF_MISSING'),('gate_uid',gates,'ACTION_GATE_REF_MISSING'),('error_uid',errors,'ACTION_ERROR_REF_MISSING')]:
   ref=a.get(field)
   if not ref or ref not in registry: add(gaps,page,'IMPLEMENTATION_GAP',cat,aid,str(ref))
  if not a.get('label') or not a.get('success_contract'): add(gaps,page,'IMPLEMENTATION_GAP','BUSINESS_INTENT_OR_RESPONSE_MISSING',aid,'label/success_contract')
  explicit_trigger=fieldish(a,'trigger_event_uid','trigger_uid','invocation','system_trigger','trigger_kind') or bool(transitions_by_action.get(aid))
  if not controls_by_action.get(aid) and not explicit_trigger: add(gaps,page,'ARCHITECTURE_GAP','ACTION_WITHOUT_CONTROL_OR_TRIGGER',aid,'no registered control or explicit/system transition trigger')
  rb=a.get('runtime_binding') or {}; kind=rb.get('binding_kind')
  if not kind: add(gaps,page,'IMPLEMENTATION_GAP','RUNTIME_BINDING_MISSING',aid,'runtime_binding.binding_kind absent')
  client = kind=='CLIENT_STATE_OR_VIEW_NO_API_REQUIRED'
  port_uid=rb.get('port_uid'); port=ports.get(port_uid) if port_uid else None
  if client:
   if rb.get('api_required') is not False: add(gaps,page,'IMPLEMENTATION_GAP','CLIENT_ACTION_API_NA_CONTRACT_MISSING',aid,'api_required must be false')
  else:
   if port_uid and not port: add(gaps,page,'IMPLEMENTATION_GAP','RUNTIME_PORT_REF_MISSING',aid,str(port_uid))
   if not port_uid:
    hits=has_any(rb,KNOWN_GAPS.keys())
    if hits:
     for ref in hits: add(gaps,page,'AUTHORITY_GAP','RUNTIME_EXTERNAL_AUTHORITY_UNRESOLVED',aid,KNOWN_GAPS[ref]+': '+ref)
    elif kind and ('SHARED' in kind or 'REFERENCE' in kind): add(gaps,page,'SHARED_OWNER_REFERENCE','RUNTIME_SHARED_OWNER_REFERENCE',aid,kind)
    else: add(gaps,page,'IMPLEMENTATION_GAP','RUNTIME_ENTRY_OR_PORT_MISSING',aid,str(kind))
  combined={'action':a,'runtime_binding':rb,'port':port or {}}
  if is_effectful:
   if not has_any(combined,['validation','validate','validator']): add(gaps,page,'IMPLEMENTATION_GAP','POST_ACTION_VALIDATION_NODE_MISSING',aid,'no explicit validation contract in action/runtime/port')
   if not (fieldish(rb,'payload_rule','payload','input_contract','request_contract') or fieldish(port or {},'payload_rule','payload','input_contract','request_contract','request_schema')): add(gaps,page,'INPUT_SOURCE_GAP','PAYLOAD_CONTRACT_MISSING',aid,'no explicit payload/input contract')
   if not (fieldish(rb,'runtime_owner','owner','service_owner') or fieldish(port or {},'runtime_owner','owner','service_owner')): add(gaps,page,'IMPLEMENTATION_GAP','RUNTIME_OWNER_MISSING',aid,'page action owner is not sufficient runtime-owner contract')
   if not (fieldish(rb,'provider','repository','data_owner','service','adapter','endpoint','operation','api_entry') or fieldish(port or {},'provider','repository','data_owner','service','adapter','endpoint','operation','api_entry')): add(gaps,page,'IMPLEMENTATION_GAP','REPOSITORY_DATA_PROVIDER_NODE_MISSING',aid,'no explicit repository/data/provider/API target')
   if not (fieldish(a,'audit_event_uid','audit_item_uid','audit_event') or fieldish(rb,'audit_event_uid','audit_item_uid','audit_event') or fieldish(port or {},'audit_event_uid','audit_item_uid','audit_event')): add(gaps,page,'IMPLEMENTATION_GAP','AUDIT_EVENT_NODE_MISSING',aid,'no explicit audit event/item UID')
  if not a.get('state_effect'): add(gaps,page,'IMPLEMENTATION_GAP','SUCCESS_STATE_FEEDBACK_MISSING',aid,'state_effect absent')
  if a.get('error_uid') in errors and not errors[a.get('error_uid')].get('recovery'): add(gaps,page,'IMPLEMENTATION_GAP','RECOVERY_CONTRACT_MISSING',aid,str(a.get('error_uid')))
  if not (fieldish(a,'next_state_uid','success_event_uid','next_step_uid','next_gate_uid') or fieldish(rb,'next_state_uid','success_event_uid','next_step_uid','next_gate_uid') or bool(transitions_by_action.get(aid))): add(gaps,page,'ARCHITECTURE_GAP','NEXT_STATE_STEP_GATE_BINDING_MISSING',aid,'no explicit action-to-next-state/event/step/gate/transition binding')
  hits=has_any({'a':a,'gate':gates.get(a.get('gate_uid')) or {},'port':port or {}},KNOWN_GAPS.keys())
  for ref in hits: add(gaps,page,'AUTHORITY_GAP','KNOWN_EXTERNAL_AUTHORITY_DEPENDENCY',aid,KNOWN_GAPS[ref]+': '+ref)
 for tid,t in trans.items():
  if t.get('from_stage') not in stages or t.get('to_stage') not in stages: add(gaps,page,'IMPLEMENTATION_GAP','TRANSITION_STAGE_REF_MISSING',tid,str((t.get('from_stage'),t.get('to_stage'))))
  if events and t.get('trigger_event_uid') not in events: add(gaps,page,'IMPLEMENTATION_GAP','TRANSITION_EVENT_REF_MISSING',tid,str(t.get('trigger_event_uid')))
  if t.get('gate_uid') not in gates: add(gaps,page,'IMPLEMENTATION_GAP','TRANSITION_GATE_REF_MISSING',tid,str(t.get('gate_uid')))
  for req in ('mutation_owner','failure_state','recovery','audit_event_uid','illegal_transition_tests'):
   if t.get(req) in (None,'',[],{}): add(gaps,page,'IMPLEMENTATION_GAP','STATE_TRANSITION_LEDGER_FIELD_MISSING',tid,req)
 counts=Counter(x['class'] for x in gaps); cats=Counter(x['category'] for x in gaps)
 summary={'actions':len(actions),'controls':len(controls),'permissions':len(perms),'gates':len(gates),'errors':len(errors),'integration_ports':len(ports),'page_states':len(states),'stages':len(stages),'events':len(events),'stage_transitions':len(trans),'effectful_actions':effectful,'actions_with_controls':sum(1 for a in actions if controls_by_action.get(a)),'gap_count':len(gaps),'gap_classes':dict(sorted(counts.items())),'gap_categories':dict(sorted(cats.items())),'functional_completion':len(gaps)==0}
 all_summary[page]=summary; all_gaps.extend(gaps)
result={'schema_version':1,'run_uid':'FRESH-RUN-003','stage_uid':'STAGE-02','operation_uid':'FUNCTIONAL_CHAIN_COMPILE','governance_overlay':'v2.1.12','summary':all_summary,'gap_total':len(all_gaps),'gaps':all_gaps,'functional_completion':len(all_gaps)==0}
Path('stage2_functional_preflight_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
print('STAGE2_FUNCTIONAL_CHAIN_PREFLIGHT_SUMMARY='+json.dumps(all_summary,ensure_ascii=False,sort_keys=True))
print('STAGE2_FUNCTIONAL_CHAIN_GAP_TOTAL='+str(len(all_gaps)))
for g in all_gaps: print('GAP|{page}|{class}|{category}|{uid}|{detail}'.format(**g))
print('PASS: Stage-02 functional-chain preflight exhaustively scanned all source-registered actions/controls and classified every detected missing chain node/reference')
print('PASS does NOT mean functional completion when gap_count > 0; machine-readable result written to stage2_functional_preflight_result.json')
