#!/usr/bin/env python3
from pathlib import Path
from collections import Counter,defaultdict
import json,subprocess,yaml,re
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'
PAGES={'CORE-01':run/'00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml','ASSET-01':run/'00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'}
SPEC={p:run/f'04_PAGE_FUNCTIONAL_CONTRACT/{p}/FUNCTIONAL_CHAIN_SPEC.yaml' for p in PAGES}
RAW_BLOBS={'CORE-01':'9490f3bcc28c5511bc04d6c3ce53c026e3c4667f','ASSET-01':'9668e2307c722ea4cf64f93f07c92da1b3abcc28'}
NODE_ORDER=['BUSINESS_INTENT','PRECONDITIONS','ENTRY','OPERATOR_OR_SYSTEM_INPUT_SOURCE','CONTROL_OR_TRIGGER','GATE','PERMISSION','ACTION','VALIDATION','PAYLOAD','API_OR_ENTRY','RUNTIME_OWNER','REPOSITORY_DATA_OR_PROVIDER','AUDIT_EVENT','RESPONSE','UI_OR_CALLER_FEEDBACK','SUCCESS_STATE','NEXT_STATE','NEXT_STEP','NEXT_GATE','FAILURE_STATE','RETRY_RECOVERY_OR_ROLLBACK','TERMINAL_OUTCOME']
KNOWN_GAPS={'GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY@V1.9':'GAP-001','GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY@V1.0':'GAP-002','ACPOS_SYSTEM_AUTHORITY@V1.0':'GAP-003','ACPOS_CURRENT_NAVIGATION_PERMISSION_AUTHORITY@V1.0':'GAP-004','ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT@V1.3':'GAP-005','ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY':'GAP-006','IAM-01 / account permission runtime':'GAP-007','ACPOS shared AI Router/Capability Assignment':'GAP-008'}
def die(m): raise SystemExit(m)
def load(p):
 try:d=yaml.safe_load(p.read_text(encoding='utf-8'))
 except Exception as e:die('parse failure:'+str(p)+':'+str(e))
 if not isinstance(d,dict):die('mapping required:'+str(p))
 return d
def gitobj(path):
 r=subprocess.run(['git','rev-parse','HEAD:'+path],text=True,capture_output=True)
 if r.returncode:die('git object missing:'+path)
 return r.stdout.strip()
def idx(items,key):return{x.get(key):x for x in(items or[]) if isinstance(x,dict) and x.get(key)}
def fieldish(d,*names):return any(isinstance(d,dict) and d.get(n) not in(None,'',[],{}) for n in names)
def add(g,p,c,cat,u,detail,owner='PAGE_FUNCTIONAL_CONTRACT'):g.append({'page':p,'class':c,'category':cat,'uid':u,'detail':detail,'gap_owner':owner})
def port_refs(rb):return[(k,rb[k]) for k in('port_uid','persist_via_port_uid','execute_port_uid','decision_port_uid') if rb.get(k)]
def poper(p):return(p or{}).get('operation')or(p or{}).get('registered_operation')
def pmethod(p):return(p or{}).get('method_path')or(p or{}).get('method_effective_path')
def pperm(p):return(p or{}).get('permission')or(p or{}).get('registered_permission')
def sevent(p):return str((p or{}).get('state_event')or'')
def audit_event(se):
 if '|' in se:
  t=se.split('|',1)[1].strip()
  if t and t.lower()not in{'event none','none'}:return t
 m=re.search(r'\b[a-z][a-z0-9_]*\.[a-z0-9_.]+\b',se);return m.group(0)if m else None
def state_change(se):return'→'in se or'->'in se
def validation(a,rb,p):return fieldish(a,'success_contract','validation_contract','validator_uid')or fieldish(rb,'validation','validation_rule','evaluation_rule','decision','result')or fieldish(p,'validation','validation_rule','validator_uid')
def payload(a,rb,p):return fieldish(a,'payload','payload_rule','input_contract','request_contract')or fieldish(rb,'payload','payload_rule','payload_mode','input_contract','request_contract')or fieldish(p,'payload','payload_rule','input_contract','request_contract','request_schema')
all_summary={};all_gaps=[];all_refs=[]
for page,raw_path in PAGES.items():
 if gitobj(str(raw_path))!=RAW_BLOBS[page]:die(page+' Raw Source blob drift')
 d=load(raw_path);reg=d.get('registries')or{};spec=load(SPEC[page])
 if spec.get('artifact_type')!='FUNCTIONAL_CHAIN_SPEC'or spec.get('stage_uid')!='STAGE-02'or spec.get('page_uid')!=page or spec.get('governance_overlay')!='v2.1.12':die(page+' functional spec identity drift')
 if spec.get('functional_chain_node_order')!=NODE_ORDER:die(page+' functional chain node order drift')
 rec=(spec.get('entry_gate')or{}).get('terminal_receipt')or{};grec=spec.get('governance_predecessor_receipt')or{}
 if(rec.get('head_sha'),rec.get('run_id'),rec.get('job_denominator'),rec.get('conclusion'))!=('c6a9c2e5b38a189a6517d59345a0738618e8cd28',34755361339,'12/12','SUCCESS'):die(page+' Stage1 entry receipt drift')
 if(grec.get('head_sha'),grec.get('run_id'),grec.get('job_denominator'),grec.get('conclusion'))!=('3247937d7b8ccd57551119b079cb33cee45e4ecc',34757919043,'13/13','SUCCESS'):die(page+' v2.1.12 governance receipt drift')
 actions=idx(reg.get('actions'),'action_uid');controls=idx(reg.get('controls'),'control_uid');perms=idx(reg.get('permissions'),'permission_uid');gates=idx(reg.get('gates'),'gate_uid');errors=idx(reg.get('errors'),'error_uid');ports=idx(reg.get('integration_ports'),'port_uid');stages=idx(reg.get('stages'),'stage_uid');events=idx(reg.get('events'),'event_uid');trans=idx(reg.get('stage_transitions'),'transition_uid')
 gaps=[];refs=[];controls_by_action=defaultdict(list);trans_by_action=defaultdict(list)
 for cid,c in controls.items():
  au=c.get('action_uid');
  if au:controls_by_action[au].append(cid)
  if not au or au not in actions:add(gaps,page,'IMPLEMENTATION_GAP','CONTROL_WITHOUT_VALID_ACTION',cid,str(au))
  if c.get('gate_uid')and c.get('gate_uid')not in gates:add(gaps,page,'IMPLEMENTATION_GAP','CONTROL_GATE_REF_MISSING',cid,str(c.get('gate_uid')))
  if c.get('permission_uid')and c.get('permission_uid')not in perms:add(gaps,page,'IMPLEMENTATION_GAP','CONTROL_PERMISSION_REF_MISSING',cid,str(c.get('permission_uid')))
 for tid,t in trans.items():
  trig=t.get('action_uid')or t.get('trigger_event_uid')or t.get('trigger')
  if trig in actions:trans_by_action[trig].append(tid)
 effectful=0
 for aid,a in actions.items():
  effect=a.get('effect_type');is_eff=effect not in{'READ_ONLY','UI_ONLY','CONTEXT_STATE'};effectful+=int(is_eff)
  if not a.get('label'):add(gaps,page,'IMPLEMENTATION_GAP','BUSINESS_INTENT_MISSING',aid,'action label/intent absent')
  for field,registry,cat in [('permission_uid',perms,'ACTION_PERMISSION_REF_MISSING'),('gate_uid',gates,'ACTION_GATE_REF_MISSING')]:
   r=a.get(field)
   if not r or r not in registry:add(gaps,page,'IMPLEMENTATION_GAP',cat,aid,str(r))
  err=a.get('error_uid')
  if err:
   if err not in errors:add(gaps,page,'IMPLEMENTATION_GAP','ACTION_ERROR_REF_MISSING',aid,str(err))
   elif not errors[err].get('recovery'):add(gaps,page,'IMPLEMENTATION_GAP','RECOVERY_CONTRACT_MISSING',aid,str(err))
  elif not any((trans.get(t)or{}).get('recovery')for t in trans_by_action.get(aid,[])):add(gaps,page,'ARCHITECTURE_GAP','FAILURE_STATE_ERROR_BINDING_MISSING',aid,'no exact action->error/recovery or transition recovery binding')
  explicit=fieldish(a,'trigger_event_uid','trigger_uid','invocation','system_trigger','trigger_kind')or bool(trans_by_action.get(aid))
  if not controls_by_action.get(aid)and not explicit:add(gaps,page,'ARCHITECTURE_GAP','ACTION_WITHOUT_CONTROL_OR_TRIGGER',aid,'no registered control or exact transition/system trigger')
  rb=a.get('runtime_binding')or{};kind=rb.get('binding_kind')
  if not kind:add(gaps,page,'IMPLEMENTATION_GAP','RUNTIME_BINDING_MISSING',aid,'runtime_binding.binding_kind absent');continue
  client=kind=='CLIENT_STATE_OR_VIEW_NO_API_REQUIRED';resolved=[]
  for fld,puid in port_refs(rb):
   p=ports.get(puid)
   if not p:add(gaps,page,'IMPLEMENTATION_GAP','RUNTIME_PORT_REF_MISSING',aid,fld+'='+str(puid))
   else:resolved.append((puid,p))
  if client:
   if rb.get('api_required')is not False:add(gaps,page,'IMPLEMENTATION_GAP','CLIENT_ACTION_API_NA_CONTRACT_MISSING',aid,'api_required must be false')
   refs.append({'page':page,'action_uid':aid,'classification':'NOT_APPLICABLE','binding_kind':kind,'evidence':'api_required=false; local client state/view owns API/Runtime/Persistence N/A'})
  elif kind=='SHARED_OPERATION_REFERENCE':
   auth=rb.get('shared_authority_id');op=rb.get('shared_operation_id')
   if not auth or not op:add(gaps,page,'IMPLEMENTATION_GAP','SHARED_OWNER_REFERENCE_INCOMPLETE',aid,str((auth,op)))
   else:
    refs.append({'page':page,'action_uid':aid,'classification':'SHARED_OWNER_REFERENCE','binding_kind':kind,'authority_ref':auth,'operation_ref':op})
    if auth in KNOWN_GAPS:add(gaps,page,'AUTHORITY_GAP','SHARED_OWNER_AUTHORITY_UNRESOLVED',aid,KNOWN_GAPS[auth]+': '+auth,'EXTERNAL_AUTHORITY')
  else:
   if not resolved:add(gaps,page,'IMPLEMENTATION_GAP','RUNTIME_ENTRY_OR_PORT_MISSING',aid,str(kind))
   for puid,p in resolved:
    if not poper(p):add(gaps,page,'IMPLEMENTATION_GAP','PORT_OPERATION_MISSING',aid,puid)
    if not pmethod(p):add(gaps,page,'IMPLEMENTATION_GAP','API_ENTRY_MISSING',aid,puid)
    if not pperm(p):add(gaps,page,'IMPLEMENTATION_GAP','PORT_PERMISSION_MISSING',aid,puid)
    refs.append({'page':page,'action_uid':aid,'classification':'REGISTERED_PORT_REFERENCE','binding_kind':kind,'port_uid':puid,'operation':poper(p),'api_entry':pmethod(p)})
  if is_eff and kind!='SHARED_OPERATION_REFERENCE':
   p=resolved[0][1]if resolved else{}
   if not validation(a,rb,p):add(gaps,page,'IMPLEMENTATION_GAP','POST_ACTION_VALIDATION_NODE_MISSING',aid,'no explicit success/validation/result/evaluation contract')
   if not payload(a,rb,p):add(gaps,page,'INPUT_SOURCE_GAP','PAYLOAD_INPUT_CONTRACT_MISSING',aid,'registered operation exists but no explicit payload/input contract or schema')
   se=sevent(p)
   if not audit_event(se):add(gaps,page,'IMPLEMENTATION_GAP','AUDIT_EVENT_NODE_MISSING',aid,'registered port has no explicit audit/event UID in state_event')
   if not(state_change(se)or bool(trans_by_action.get(aid))or a.get('state_effect')):add(gaps,page,'ARCHITECTURE_GAP','SUCCESS_NEXT_STATE_BINDING_MISSING',aid,'no state_effect, state transition, or port state_event transition')
  if kind!='SHARED_OPERATION_REFERENCE':
   body=yaml.safe_dump({'action':a,'runtime':rb},allow_unicode=True,sort_keys=False)
   for ref,gid in KNOWN_GAPS.items():
    if ref in body:add(gaps,page,'AUTHORITY_GAP','KNOWN_EXTERNAL_AUTHORITY_DEPENDENCY',aid,gid+': '+ref,'EXTERNAL_AUTHORITY')
 for tid,t in trans.items():
  if t.get('from_stage')not in stages or t.get('to_stage')not in stages:add(gaps,page,'IMPLEMENTATION_GAP','TRANSITION_STAGE_REF_MISSING',tid,str((t.get('from_stage'),t.get('to_stage'))))
  trig=t.get('action_uid')or t.get('trigger_event_uid')or t.get('trigger')
  if not trig:add(gaps,page,'ARCHITECTURE_GAP','TRANSITION_TRIGGER_MISSING',tid,'trigger/action absent')
  elif t.get('trigger_event_uid')and events and t.get('trigger_event_uid')not in events:add(gaps,page,'IMPLEMENTATION_GAP','TRANSITION_EVENT_REF_MISSING',tid,str(t.get('trigger_event_uid')))
  gate=t.get('gate_uid')or t.get('gate')
  if not gate:add(gaps,page,'ARCHITECTURE_GAP','TRANSITION_GATE_PRECONDITION_MISSING',tid,'gate/preconditions absent')
  elif t.get('gate_uid')and t.get('gate_uid')not in gates:add(gaps,page,'IMPLEMENTATION_GAP','TRANSITION_GATE_REF_MISSING',tid,str(t.get('gate_uid')))
  for req in('mutation_owner','failure_state','recovery','audit_event_uid','illegal_transition_tests'):
   if t.get(req)in(None,'',[],{}):add(gaps,page,'IMPLEMENTATION_GAP','STATE_TRANSITION_LEDGER_FIELD_MISSING',tid,req)
 uniq=[];seen=set()
 for g in gaps:
  k=(g['page'],g['class'],g['category'],g['uid'],g['detail'])
  if k not in seen:seen.add(k);uniq.append(g)
 gaps=uniq;counts=Counter(x['class']for x in gaps);cats=Counter(x['category']for x in gaps)
 all_summary[page]={'actions':len(actions),'controls':len(controls),'permissions':len(perms),'gates':len(gates),'errors':len(errors),'integration_ports':len(ports),'stages':len(stages),'events':len(events),'stage_transitions':len(trans),'effectful_actions':effectful,'actions_with_controls':sum(1 for a in actions if controls_by_action.get(a)),'registered_runtime_references':len(refs),'gap_count':len(gaps),'gap_classes':dict(sorted(counts.items())),'gap_categories':dict(sorted(cats.items())),'functional_completion':len(gaps)==0};all_gaps.extend(gaps);all_refs.extend(refs)
auth=defaultdict(list)
for g in all_gaps:
 if g['class']=='AUTHORITY_GAP':
  m=re.search(r'(GAP-\d{3})',g['detail']);auth[m.group(1)if m else g['detail']].append({'page':g['page'],'uid':g['uid'],'category':g['category']})
result={'schema_version':2,'detector_revision':'v2-authority-native-alias-calibrated','run_uid':'FRESH-RUN-003','stage_uid':'STAGE-02','operation_uid':'FUNCTIONAL_CHAIN_COMPILE','governance_overlay':'v2.1.12','summary':all_summary,'gap_total':len(all_gaps),'gaps':all_gaps,'registered_runtime_references':all_refs,'unique_external_authority_gaps':dict(sorted(auth.items())),'functional_completion':len(all_gaps)==0,'semantics':'PASS means exhaustive scan/classification only; gap_total>0 blocks functional completion'}
Path('stage2_functional_preflight_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
print('STAGE2_FUNCTIONAL_CHAIN_PREFLIGHT_SUMMARY='+json.dumps(all_summary,ensure_ascii=False,sort_keys=True));print('STAGE2_FUNCTIONAL_CHAIN_GAP_TOTAL='+str(len(all_gaps)));print('STAGE2_UNIQUE_EXTERNAL_AUTHORITY_GAPS='+json.dumps(dict(sorted(auth.items())),ensure_ascii=False,sort_keys=True))
for g in all_gaps:print('GAP|{page}|{class}|{category}|{uid}|{detail}'.format(**g))
print('PASS: authority-native aliases resolved before gap classification; registered source/composite/shared owner bindings are not duplicated as page-local runtime gaps')
print('PASS: Stage-02 functional-chain preflight exhaustively scanned all source-registered actions/controls/transitions and classified remaining unresolved chain nodes')
print('PASS does NOT mean functional completion when gap_count > 0; machine-readable result written to stage2_functional_preflight_result.json')
