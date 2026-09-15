#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import re, subprocess, sys, yaml

ROOT=Path(__file__).resolve().parents[2]
R34=ROOT/'governance/test/stage02/STAGE02_TRANSITION_LEDGER_REQUIRED_APPLICABILITY_R34.yaml'
RAW={
 'ASSET-01':ROOT/'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
 'CORE-01':ROOT/'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
}
OUT=ROOT/'governance/test/stage02/STAGE02_TRANSITION_ROLE_SAFE_CANDIDATE_AUTHORING_R36.yaml'
FIELDS=('mutation_owner','failure_state','recovery','audit_event_uid')
NON_EFFECTFUL={'READ_ONLY','UI_ONLY','CONTEXT_STATE'}

def die(m): print(f'BLOCK: {m}',file=sys.stderr); raise SystemExit(1)
def load(p):
 o=yaml.safe_load(p.read_text(encoding='utf-8')) if p.is_file() else None
 if not isinstance(o,dict): die(f'MAPPING_REQUIRED:{p.relative_to(ROOT)}')
 return o
def idx(items,key):
 out={}
 for x in items or []:
  if isinstance(x,dict) and x.get(key):
   if x[key] in out: die(f'DUPLICATE_{key}:{x[key]}')
   out[x[key]]=x
 return out
def event_token(text):
 text=str(text or '')
 if '|' in text:
  tail=text.split('|',1)[1].strip()
  if tail and tail.lower() not in {'event none','none'}: return tail
 m=re.search(r'\b[a-z][a-z0-9_]*\.[a-z0-9_.]+\b',text)
 return m.group(0) if m else None
def resolved_ports(action,ports):
 rb=action.get('runtime_binding') or {}; out=[]
 for f in ('port_uid','persist_via_port_uid','execute_port_uid','decision_port_uid'):
  p=rb.get(f)
  if p and p in ports: out.append((f,p,ports[p]))
 return out
def exact_event_matches(token,events):
 if not token: return []
 exact_fields=('event_uid','event_name','canonical_name','name','event','audit_event_uid','state_event')
 out=[]
 for uid,e in events.items():
  for f in exact_fields:
   if str(e.get(f) or '')==token:
    out.append({'event_uid':uid,'matched_field':f,'matched_value':token})
    break
 return out

r34=load(R34)
if (r34.get('denominators') or {}).get('current_transition_ledger_field_problems')!=40: die('R36_R34_DENOMINATOR_DRIFT')
rows=r34.get('records') or []
if len(rows)!=40: die('R36_R34_RECORD_DRIFT')
rawdata={}
for page,path in RAW.items():
 raw=load(path); reg=raw.get('registries') or {}
 rawdata[page]={
  'raw':raw,'actions':idx(reg.get('actions'),'action_uid'),'errors':idx(reg.get('errors'),'error_uid'),
  'ports':idx(reg.get('integration_ports'),'port_uid'),'events':idx(reg.get('events'),'event_uid'),
  'transitions':idx(reg.get('stage_transitions'),'transition_uid'),'page_states':idx(reg.get('page_states'),'state_uid'),
 }

records=[]; class_counts=Counter(); candidate_fields=Counter(); page_counts=Counter(); transition_summary=defaultdict(dict)
for source in rows:
 page=source['scope']; tid=source['transition_uid']; field=source['missing_field']; data=rawdata[page]
 t=data['transitions'].get(tid)
 if not t: die(f'R36_TRANSITION_MISSING:{page}:{tid}')
 trigger=t.get('action_uid') or t.get('trigger_event_uid') or t.get('trigger')
 action=data['actions'].get(trigger)
 gate=t.get('gate_uid') or t.get('gate')
 action_gate=(action or {}).get('gate_uid')
 gate_exact_match=bool(action and gate and action_gate==gate)
 ports=resolved_ports(action or {},data['ports']) if action else []
 port_events=[]
 for _,puid,p in ports:
  token=event_token(p.get('state_event'))
  port_events.append({'port_uid':puid,'state_event':p.get('state_event'),'event_token':token,'exact_registered_event_matches':exact_event_matches(token,data['events'])})
 error_uid=(action or {}).get('error_uid')
 error=data['errors'].get(error_uid) if error_uid else None
 page_error_states=[uid for uid,s in data['page_states'].items() if str(s.get('display') or '').upper() in {'ERROR','FAILED','FAILURE','BLOCKED'} or 'ERROR' in uid.upper() or 'FAIL' in uid.upper()]
 candidate=None; cls='NO_ROLE_SAFE_CANDIDATE'; reason='NO_EXACT_ROLE_EQUIVALENCE_IN_CURRENT_CHAIN'
 evidence={
  'trigger':trigger,'trigger_kind':'ACTION' if action else ('REGISTERED_EVENT' if trigger in data['events'] else 'SYSTEM_OR_FREE_TEXT'),
  'gate':gate,'direct_trigger_action_uid':trigger if action else None,'action_gate_uid':action_gate,'action_gate_matches_transition_gate':gate_exact_match,
  'action_effect_type':(action or {}).get('effect_type'),'action_owner_evidence_only':(action or {}).get('owner'),
  'action_error_uid':error_uid,'action_error_recovery':(error or {}).get('recovery') if error else None,
  'resolved_runtime_ports':port_events,'page_failure_state_candidates_evidence_only':page_error_states,
 }
 if field=='mutation_owner':
  if (action or {}).get('owner'):
   cls='ROLE_ADJACENT_EVIDENCE_ONLY'
   reason='ACTION_OWNER_IS_NOT_TRANSITION_MUTATION_OWNER_WITHOUT_EXPLICIT_ROLE_EQUIVALENCE'
 elif field=='failure_state':
  if page_error_states:
   cls='ROLE_ADJACENT_EVIDENCE_ONLY'
   reason='PAGE_ERROR_STATE_EXISTS_BUT_NO_EXACT_TRANSITION_FAILURE_STATE_BINDING'
 elif field=='recovery':
  if action and gate_exact_match and action.get('effect_type') not in NON_EFFECTFUL and error_uid and error and error.get('recovery'):
   candidate={'value':error.get('recovery'),'source_error_uid':error_uid,'derivation':'EXACT_DIRECT_TRIGGER_ACTION_ERROR_RECOVERY_WITH_MATCHING_TRANSITION_GATE'}
   cls='UNIQUE_ROLE_SAFE_CANDIDATE'
   reason='DIRECT_TRIGGER_ACTION_AND_TRANSITION_SHARE_EXACT_GATE_AND_ACTION_HAS_ONE_EXACT_ERROR_RECOVERY'
  elif error and error.get('recovery'):
   cls='ROLE_ADJACENT_EVIDENCE_ONLY'
   reason='ACTION_ERROR_RECOVERY_EXISTS_BUT_TRIGGER_OR_GATE_ROLE_EQUIVALENCE_NOT_PROVEN'
 elif field=='audit_event_uid':
  matches=[]
  for pe in port_events: matches.extend(pe['exact_registered_event_matches'])
  uniq={m['event_uid']:m for m in matches}
  if len(uniq)==1:
   m=next(iter(uniq.values()))
   candidate={'value':m['event_uid'],'source_event_match':m,'derivation':'EXACT_DIRECT_RUNTIME_PORT_EVENT_TOKEN_TO_REGISTERED_EVENT_IDENTITY'}
   cls='UNIQUE_ROLE_SAFE_CANDIDATE'
   reason='ONE_EXACT_REGISTERED_EVENT_IDENTITY_MATCHES_DIRECT_RUNTIME_PORT_STATE_EVENT_TOKEN'
  elif len(uniq)>1:
   cls='MULTIPLE_REASONABLE_CANDIDATES'
   reason='MULTIPLE_EXACT_REGISTERED_EVENT_IDENTITIES_MATCH_DIRECT_RUNTIME_PORT_EVENT_TOKEN'
  elif any(pe.get('event_token') for pe in port_events):
   cls='ROLE_ADJACENT_EVIDENCE_ONLY'
   reason='DOTTED_RUNTIME_EVENT_TOKEN_EXISTS_BUT_NO_EXACT_REGISTERED_EVENT_UID_MATCH'
 if candidate: candidate_fields[field]+=1
 class_counts[cls]+=1; page_counts[page]+=1
 rec={
  'blocker_uid':source['blocker_uid'],'problem_uid':source.get('problem_uid'),'scope':page,'transition_uid':tid,'missing_field':field,
  'classification':cls,'classification_reason':reason,'candidate':candidate,'chain_evidence':evidence,
  'cross_role_substitution_used':False,'semantic_similarity_used':False,'invented_uid_used':False,'blocker_reduction_credit':0,
  'materialization_allowed_next_cycle':cls=='UNIQUE_ROLE_SAFE_CANDIDATE',
 }
 records.append(rec)
 transition_summary[(page,tid)][field]={'classification':cls,'candidate_value':candidate.get('value') if candidate else None}

head=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
out={
 'schema_version':1,'artifact_uid':'STAGE02-TRANSITION-ROLE-SAFE-CANDIDATE-AUTHORING-R36','artifact_type':'NON_NORMATIVE_STAGE02_TRANSITION_ROLE_SAFE_CANDIDATE_AUTHORING','normative_authority':False,
 'stage_uid':'STAGE-02','source_head_sha':head,'source_r34':str(R34.relative_to(ROOT)),
 'authoring_contract':{
  'candidate_requires_unique_exact_role_safe_chain':True,'action_owner_directly_promoted_to_mutation_owner':False,'page_error_state_directly_promoted_to_failure_state':False,
  'dotted_event_token_directly_promoted_to_audit_event_uid':False,'recovery_candidate_requires_direct_trigger_action_exact_gate_match_exact_error_recovery':True,
  'audit_candidate_requires_exact_registered_event_identity_match':True,'candidate_is_authoring_output_not_materialized_contract':True,
 },
 'denominators':{
  'input_required_fields':40,'transition_count':10,'classification_counts':dict(sorted(class_counts.items())),'candidate_count':sum(candidate_fields.values()),
  'candidate_field_counts':dict(sorted(candidate_fields.items())),'scope_counts':dict(sorted(page_counts.items())),'blocker_reduction_claimed':0,
 },
 'records':records,
 'transition_summary':[{'scope':p,'transition_uid':t,'fields':v} for (p,t),v in sorted(transition_summary.items())],
 'current_specification_mutated':False,'immutable_stage1_source_mutated':False,'product_contract_materialized_this_cycle':False,
 'stage02_status':'BLOCKED','stage03_allowed':False,'website_construction_allowed':False,'deployment_allowed':False,
 'next_execution_gate':'MATERIALIZE_ONLY_UNIQUE_ROLE_SAFE_R36_CANDIDATES_THEN_FRESH_REEXECUTE; KEEP_ALL_OTHER_FIELDS_PENDING_AND_CONTINUE_OTHER_FUNCTIONAL_CATEGORIES',
}
OUT.write_text(yaml.safe_dump(out,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
print(f"PASS: R36 authored {out['denominators']['candidate_count']} unique role-safe candidates from 40 required transition fields")
print(f"CLASSIFICATIONS: {dict(sorted(class_counts.items()))}")
print('PASS: no candidate materialized and blocker reduction remains zero in R36')
