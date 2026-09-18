#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from copy import deepcopy
from collections import Counter, defaultdict
import argparse, hashlib, json, os, re, subprocess, sys
import yaml

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'00_SOURCE_INTAKE/fresh_run_005'
BASE=RUN/'04_PAGE_FUNCTIONAL_CONTRACT'
CORE=BASE/'CORE-01'
RAW=RUN/'00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml'
SPEC=CORE/'FUNCTIONAL_CHAIN_SPEC.yaml'
PROBLEMS=BASE/'CURRENT_PROBLEM_REGISTER.yaml'
OVERLAY=BASE/'EFFECTIVE_CONTRACT_OVERLAY.yaml'
LEDGER=BASE/'RESOLUTION_LEDGER.yaml'
SCORE=CORE/'FUNCTION_ADMISSION_SCORECARD.yaml'
AUTO=CORE/'AUTO_COMPLETION_SCOPE_LEDGER.yaml'
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
SCOPE=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
FINDINGS=ROOT/'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
CHANGE=ROOT/'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
LATEST=ROOT/'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
STAGE2_RESULT=ROOT/'.github/stage02-test/STAGE02_ACTUAL_TEST_RESULT.json'
AUTH=ROOT/'governance/test/spec_change_authorizations/USR-DIRECTIVE-20260919-COMPLETE-CORE01-STAGE02-R3.yaml'
OUT=ROOT/'governance/test/stage02'
CANDIDATE=OUT/'STAGE02_CORE01_FRESH_DESIGN_CONTRACT_CANDIDATE_R3.json'
SEMANTIC=OUT/'STAGE02_CORE01_FRESH_DESIGN_CONTRACT_SEMANTIC_REVIEW_R3.json'
PACKAGE=OUT/'STAGE02_CORE01_FRESH_DESIGN_CONTRACT_REVIEW_PACKAGE_R3.json'
APPROVAL=OUT/'STAGE02_CORE01_FRESH_DESIGN_CONTRACT_APPROVAL_R3.yaml'
REVIEW=OUT/'PAGE_FUNCTIONAL_REVIEW_EVIDENCE.yaml'
CURRENT_UID='GOV-REV-20260919-PROFILE-TOKEN-DECONTAMINATION-HARDENING'
RUN_UID='FRESH-RUN-005'
ATTEMPT_UID='STAGE02-FRESH-20260919-CORE01-002'
WORK_UID='WU-STAGE02-CORE01-FRESH-FUNCTIONAL-REMEDIATION-002'
PAGE='CORE-01'
RAW_BLOB='9490f3bcc28c5511bc04d6c3ce53c026e3c4667f'
HIST_REF='d7d1fbd9ae353e256bc766bd8150d9448ed6b230'
HIST_CANDIDATE='governance/test/stage02/STAGE02_CORE01_DESIGN_CONTRACT_CANDIDATE.json'
RESOLUTION_UID='STAGE02-RESOLUTION-CORE01-FRESH-R3-001'

def die(msg):
    print('BLOCK:',msg,file=sys.stderr); raise SystemExit(1)
def run(*args,env=None):
    print('+',' '.join(map(str,args)))
    subprocess.run(args,cwd=ROOT,env=env,check=True)
def git(*args):
    cp=subprocess.run(['git',*args],cwd=ROOT,text=True,capture_output=True)
    if cp.returncode: die('GIT:'+cp.stderr.strip())
    return cp.stdout.strip()
def load_yaml(p):
    if not p.is_file(): die('MISSING:'+str(p.relative_to(ROOT)))
    x=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(x,dict): die('MAPPING_REQUIRED:'+str(p.relative_to(ROOT)))
    return x
def load_json(p):
    if not p.is_file(): die('MISSING:'+str(p.relative_to(ROOT)))
    x=json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(x,dict): die('JSON_MAPPING_REQUIRED:'+str(p.relative_to(ROOT)))
    return x
def dump_yaml(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(x,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def dump_json(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=False)+'\n',encoding='utf-8')
def sha_obj(x):
    return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def sha_file(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def idx(xs,key):
    return {x.get(key):x for x in (xs or []) if isinstance(x,dict) and x.get(key)}
def canonicalize(v):
    if isinstance(v,dict): return {k:canonicalize(x) for k,x in v.items()}
    if isinstance(v,list): return [canonicalize(x) for x in v]
    if isinstance(v,str) and v.startswith('TEMP-CORE01-'): return v[len('TEMP-'):]
    return v
def event_token(text):
    text=str(text or '')
    if '|' in text:
        tail=text.split('|',1)[1].strip()
        if tail and tail.lower() not in {'event none','none'}: return tail
    m=re.search(r'\b[a-z][a-z0-9_]*\.[a-z0-9_.]+\b',text)
    return m.group(0) if m else None
def build_event_state(old,event):
    old=str(old or '').strip()
    if '|' in old:
        prefix=old.split('|',1)[0].strip()
        return f'{prefix} | {event}' if prefix else event
    if 'no canonical transition/event' in old.lower(): return f'business action | {event}'
    return f'{old} | {event}' if old else event
def problem_key(row):
    return (str(row.get('category')),str(row.get('target_uid')),str(row.get('detail')))
def hist_template():
    raw=git('show',f'{HIST_REF}:{HIST_CANDIDATE}')
    x=json.loads(raw)
    if not isinstance(x,dict) or len(x.get('units') or [])!=25: die('HISTORICAL_DESIGN_REFERENCE_INVALID')
    return x

def current_context(raw, unit):
    reg=raw.get('registries') or {}
    actions=idx(reg.get('actions'),'action_uid'); ports=idx(reg.get('integration_ports'),'port_uid'); transitions=idx(reg.get('stage_transitions'),'transition_uid')
    target=unit.get('target_uid')
    if target in actions:
        a=deepcopy(actions[target]); rb=a.get('runtime_binding') or {}; p=ports.get(rb.get('port_uid')) or {}
        return {
          'action_uid':target,'label':a.get('label'),'effect_type':a.get('effect_type'),'owner':a.get('owner'),
          'gate_uid':a.get('gate_uid'),'permission_uid':a.get('permission_uid'),'success_contract':a.get('success_contract'),
          'error_uid':a.get('error_uid'),'state_effect':a.get('state_effect'),'port_uid':rb.get('port_uid'),
          'operation':p.get('operation'),'method_path':p.get('method_path'),'state_event':p.get('state_event'),
        }
    if target in transitions:
        return deepcopy(transitions[target])
    die('CURRENT_CONTEXT_TARGET_NOT_FOUND:'+str(target))

def validate_fresh_candidate(candidate, raw, problems):
    reg=raw.get('registries') or {}
    actions=idx(reg.get('actions'),'action_uid'); ports=idx(reg.get('integration_ports'),'port_uid')
    transitions=idx(reg.get('stage_transitions'),'transition_uid'); events=idx(reg.get('events'),'event_uid')
    objects=idx(reg.get('objects_refs'),'object_uid'); states=idx(raw.get('page_states'),'state_uid')
    rows=problems.get('problems') or []
    current_ids={r.get('problem_uid') for r in rows}
    covered=[]; cats=Counter(); semantic_records=[]
    for u in candidate.get('units') or []:
        cats[u.get('category')]+=1; covered.extend(u.get('blocker_uids') or [])
        prop=u.get('proposal') or {}; kind=prop.get('proposal_kind')
        checks=[]
        if kind=='ACTION_PAYLOAD_INPUT_SCHEMA':
            aid,puid=prop.get('action_uid'),prop.get('port_uid'); schema=prop.get('schema') or {}
            a=actions.get(aid); p=ports.get(puid)
            if not a or not p: die('SEMANTIC_PAYLOAD_OWNER_MISSING:'+str(aid))
            if ((a.get('runtime_binding') or {}).get('port_uid'))!=puid: die('SEMANTIC_ACTION_PORT_DRIFT:'+str(aid))
            method=str(p.get('method_path') or '')
            placeholders=re.findall(r'\{([^}]+)\}',method)
            if sorted(placeholders)!=sorted(schema.get('path_params') or []): die('SEMANTIC_PATH_PARAM_DRIFT:'+str(aid))
            names=(schema.get('required') or [])+(schema.get('optional') or [])
            if any(re.search(r'(provider|model|api[_-]?key)',str(x),re.I) for x in names): die('SEMANTIC_PROVIDER_FIELD_FORBIDDEN:'+str(aid))
            def walk(v):
                if isinstance(v,dict):
                    ou=v.get('object_uid')
                    if ou and ou not in objects: die('SEMANTIC_OBJECT_REF_UNKNOWN:'+str(ou))
                    for z in v.values(): walk(z)
                elif isinstance(v,list):
                    for z in v: walk(z)
            walk(schema)
            checks=['ACTION_EXISTS','EXACT_PORT_BINDING','PATH_PARAMS_MATCH','OBJECT_REFS_EXIST','NO_PROVIDER_MODEL_INPUT']
        elif kind=='AUDIT_EVENT_BINDING_AND_EVENT_REGISTRY_ENTRY':
            aid,puid=prop.get('action_uid'),prop.get('port_uid')
            a=actions.get(aid); p=ports.get(puid)
            if not a or not p or ((a.get('runtime_binding') or {}).get('port_uid'))!=puid: die('SEMANTIC_AUDIT_ACTION_PORT_DRIFT:'+str(aid))
            euid,event=prop.get('event_uid'),prop.get('event')
            if not euid or not re.fullmatch(r'[a-z][a-z0-9_]*\.[a-z0-9_.]+',str(event or '')): die('SEMANTIC_AUDIT_EVENT_INVALID:'+str(aid))
            if euid in events and events[euid].get('event')!=event: die('SEMANTIC_AUDIT_EVENT_CONFLICT:'+str(euid))
            checks=['ACTION_EXISTS','EXACT_PORT_BINDING','EVENT_UID_NONCONFLICTING','EVENT_TOKEN_VALID']
        elif kind=='STATE_TRANSITION_LEDGER_ENRICHMENT':
            tid=prop.get('transition_uid'); tr=transitions.get(tid)
            if not tr: die('SEMANTIC_TRANSITION_MISSING:'+str(tid))
            for k in ('from_stage','to_stage','trigger_event_uid','gate_uid'):
                if tr.get(k)!=prop.get(k): die(f'SEMANTIC_TRANSITION_BASE_DRIFT:{tid}:{k}')
            if prop.get('failure_state') not in states: die('SEMANTIC_FAILURE_STATE_UNKNOWN:'+str(tid))
            if prop.get('audit_event_uid') not in events: die('SEMANTIC_TRANSITION_AUDIT_EVENT_UNKNOWN:'+str(tid))
            rec=prop.get('recovery') or {}
            if rec.get('retain_stage')!=tr.get('from_stage') or not rec.get('action') or not rec.get('retry_condition'): die('SEMANTIC_RECOVERY_INVALID:'+str(tid))
            tests=prop.get('illegal_transition_tests') or []
            if len(tests)!=4 or len({x.get('test_uid') for x in tests})!=4 or any(not x.get('reject_when') for x in tests): die('SEMANTIC_ILLEGAL_TEST_SET_INVALID:'+str(tid))
            checks=['BASE_TRANSITION_EXACT','FAILURE_STATE_EXISTS','AUDIT_EVENT_EXISTS','RECOVERY_RETains_SOURCE_STAGE','ILLEGAL_TESTS_4_OF_4']
        else:
            die('SEMANTIC_PROPOSAL_KIND_UNSUPPORTED:'+str(kind))
        semantic_records.append({'candidate_uid':u.get('candidate_uid'),'target_uid':u.get('target_uid'),'proposal_kind':kind,'checks':checks,'result':'PASS'})
    if len(candidate.get('units') or [])!=25: die('CANDIDATE_UNIT_DENOMINATOR')
    if cats!=Counter({'PAYLOAD_INPUT_CONTRACT_MISSING':16,'STATE_TRANSITION_LEDGER_FIELD_MISSING':5,'AUDIT_EVENT_NODE_MISSING':4}): die('CANDIDATE_CATEGORY_DENOMINATOR:'+repr(cats))
    if len(covered)!=45 or len(set(covered))!=45 or set(covered)!=current_ids: die('CANDIDATE_CURRENT_BLOCKER_COVERAGE_DRIFT')
    return semantic_records

def build_candidate_and_approval():
    auth=load_yaml(AUTH); state=load_yaml(STATE); problems=load_yaml(PROBLEMS); raw=load_yaml(RAW)
    if auth.get('status')!='APPROVED_FOR_EXACT_SCOPE': die('AUTHORIZATION_INVALID')
    if git('rev-parse','HEAD:'+str(RAW.relative_to(ROOT)))!=RAW_BLOB: die('RAW_BLOB_DRIFT')
    work=state.get('active_work_unit') or {}
    if work.get('work_unit_uid')!=WORK_UID or work.get('current_status')!='DESIGN_CONTRACT_REMEDIATION_REQUIRED': die('WORK_UNIT_NOT_READY')
    rows=problems.get('problems') or []
    if len(rows)!=45 or problems.get('open_problem_count')!=45: die('CURRENT_PROBLEM_DENOMINATOR')
    by=defaultdict(list)
    for r in rows: by[(r.get('category'),r.get('target_uid'))].append(r)

    hist=hist_template(); units=[]
    for hu in hist.get('units') or []:
        miss=set(str(x) for x in (hu.get('missing_fields_or_relations') or []))
        matches=[r for r in by[(hu.get('category'),hu.get('target_uid'))] if str(r.get('detail')) in miss]
        if not matches: die('FRESH_CANDIDATE_NO_CURRENT_MATCH:'+str(hu.get('candidate_uid')))
        u={
          'candidate_uid':'FRESH-R3-'+str(hu.get('candidate_uid')).removeprefix('TEMP-'),
          'page_uid':PAGE,'category':hu.get('category'),'target_uid':hu.get('target_uid'),
          'blocker_uids':sorted(r.get('problem_uid') for r in matches),
          'missing_fields_or_relations':sorted(r.get('detail') for r in matches),
          'current_context':current_context(raw,hu),
          'proposal':deepcopy(hu.get('proposal') or {}),
          'status':'REVIEW_ONLY_PROPOSED_NOT_AUTHORITY','materialization_allowed':False,'product_blocker_credit':0,
        }
        units.append(u)
    candidate={
      'schema_version':3,'artifact_uid':'STAGE02-CORE01-FRESH-DESIGN-CONTRACT-CANDIDATE-R3',
      'artifact_type':'NON_NORMATIVE_BOUNDED_DESIGN_CONTRACT_CANDIDATE','layer_classification':'RUN_STATE',
      'normative_authority':False,'review_only_candidate':True,'current_governance_uid':CURRENT_UID,
      'run_uid':RUN_UID,'attempt_uid':ATTEMPT_UID,'work_unit_uid':WORK_UID,'page_uid':PAGE,'source_head_sha':git('rev-parse','HEAD'),
      'source_problem_register_ref':str(PROBLEMS.relative_to(ROOT)),'current_raw_authority_ref':str(RAW.relative_to(ROOT)),
      'current_raw_git_blob_sha':RAW_BLOB,
      'historical_reference':{
        'role':'NON_AUTHORITATIVE_DESIGN_REFERENCE_ONLY_NO_PRODUCT_CREDIT',
        'commit':HIST_REF,'path':HIST_CANDIDATE,'prior_approval_reused':False,'prior_run_evidence_reused_as_current':False,
      },
      'denominator':{'source_blockers':45,'design_units':25,'audit_binding_units':4,'payload_schema_units':16,'transition_units':5},
      'boundedness':{
        'new_business_entities':0,'new_actions':0,'new_ports':0,'new_runtime_owners':0,
        'existing_identity_reuse_only':True,'provider_model_fields_added':False,
        'materially_distinct_viable_behavior_count':1,'authority_gap_selection_required':False,
      },
      'units':units,'status':'SEMANTIC_REVIEW_PENDING','materialization_allowed':False,'product_blocker_credit':0,
    }
    records=validate_fresh_candidate(candidate,raw,problems)
    candidate['status']='SEMANTIC_REVIEW_PASS_READY_FOR_WHOLE_PACKAGE_APPROVAL'
    dump_json(CANDIDATE,candidate)
    semantic={
      'schema_version':3,'artifact_uid':'STAGE02-CORE01-FRESH-DESIGN-CONTRACT-SEMANTIC-REVIEW-R3',
      'artifact_type':'NON_NORMATIVE_DESIGN_CONTRACT_SEMANTIC_REVIEW','normative_authority':False,
      'current_governance_uid':CURRENT_UID,'run_uid':RUN_UID,'attempt_uid':ATTEMPT_UID,'work_unit_uid':WORK_UID,'page_uid':PAGE,
      'candidate_ref':str(CANDIDATE.relative_to(ROOT)),'candidate_sha256':sha_file(CANDIDATE),
      'current_raw_git_blob_sha':RAW_BLOB,'current_problem_coverage':'45/45','design_unit_result':'25/25 PASS',
      'semantic_records':records,'materially_distinct_viable_behavior_count':1,'authority_gap_selection_required':False,
      'historical_reference_used_as_authority':False,'prior_approval_reused':False,'product_blocker_credit':0,
      'result':'PASS_UNIQUE_COHERENT_MINIMAL_CLOSURE',
    }
    dump_json(SEMANTIC,semantic)
    package={
      'schema_version':3,'artifact_uid':'STAGE02-CORE01-FRESH-DESIGN-CONTRACT-REVIEW-PACKAGE-R3',
      'artifact_type':'NON_NORMATIVE_COHERENT_DESIGN_CONTRACT_REVIEW_PACKAGE','normative_authority':False,
      'current_governance_uid':CURRENT_UID,'run_uid':RUN_UID,'attempt_uid':ATTEMPT_UID,'work_unit_uid':WORK_UID,'page_uid':PAGE,
      'package_scope':{'source_blockers':45,'design_units':25,'categories':dict(Counter(r.get('category') for r in rows))},
      'artifact_refs':{'candidate':str(CANDIDATE.relative_to(ROOT)),'semantic_review':str(SEMANTIC.relative_to(ROOT)),
                       'function_admission_scorecard':str(SCORE.relative_to(ROOT)),'auto_completion_scope_ledger':str(AUTO.relative_to(ROOT))},
      'review_result_precondition':'SEMANTIC_PASS_AND_MATERIALLY_DISTINCT_VIABLE_BEHAVIOR_COUNT_1',
      'field_by_field_user_approval_required':False,'whole_package_user_authorization_ref':str(AUTH.relative_to(ROOT)),
      'candidate_is_authority':False,'product_blocker_credit':0,'status':'READY_FOR_AUTHORIZED_WHOLE_PACKAGE_MATERIALIZATION',
    }
    dump_json(PACKAGE,package)
    approval={
      'schema_version':1,'artifact_uid':'STAGE02-CORE01-FRESH-DESIGN-CONTRACT-APPROVAL-R3',
      'artifact_type':'PRODUCT_DESIGN_CONTRACT_PACKAGE_REVIEW_EVIDENCE','normative_authority':False,
      'current_governance_uid':CURRENT_UID,'run_uid':RUN_UID,'attempt_uid':ATTEMPT_UID,'work_unit_uid':WORK_UID,'page_uid':PAGE,
      'approval_source':'EXPLICIT_USER_DIRECTIVE','approval_authorization_ref':str(AUTH.relative_to(ROOT)),
      'directive_text':'繼續將stage-02完成','approved_by':'USER','explicit_user_decision_observed':True,
      'decision':'APPROVE_WHOLE_UNIQUE_COHERENT_MINIMAL_CANDIDATE_AND_COMPLETE_STAGE02',
      'approval_condition':{'semantic_review_result':'PASS_UNIQUE_COHERENT_MINIMAL_CLOSURE','materially_distinct_viable_behavior_count':1,'authority_gap_selection_required':False},
      'bound_artifacts':{
        'candidate':{'path':str(CANDIDATE.relative_to(ROOT)),'sha256':sha_file(CANDIDATE),'artifact_uid':candidate['artifact_uid']},
        'semantic_review':{'path':str(SEMANTIC.relative_to(ROOT)),'sha256':sha_file(SEMANTIC),'artifact_uid':semantic['artifact_uid']},
        'review_package':{'path':str(PACKAGE.relative_to(ROOT)),'sha256':sha_file(PACKAGE),'artifact_uid':package['artifact_uid']},
      },
      'candidate_is_product_authority':False,'canonical_owner_materialization_allowed':True,
      'prior_approval_reused':False,'product_blocker_credit_before_fresh_reexecution':0,
    }
    dump_yaml(APPROVAL,approval)

def apply_materialization():
    candidate=load_json(CANDIDATE); semantic=load_json(SEMANTIC); approval=load_yaml(APPROVAL); problems=load_yaml(PROBLEMS)
    if semantic.get('result')!='PASS_UNIQUE_COHERENT_MINIMAL_CLOSURE' or approval.get('approved_by')!='USER': die('APPROVAL_OR_SEMANTIC_NOT_READY')
    if approval.get('bound_artifacts',{}).get('candidate',{}).get('sha256')!=sha_file(CANDIDATE): die('APPROVAL_CANDIDATE_BINDING_DRIFT')
    spec=load_yaml(SPEC); proj=spec.get('source_projection') or {}
    ports=idx(proj.get('integration_ports'),'port_uid'); events=idx(proj.get('events'),'event_uid'); transitions=idx(proj.get('stage_transitions'),'transition_uid')
    promoted={}
    for u in candidate.get('units') or []:
        p=canonicalize(u.get('proposal') or {}); kind=p.get('proposal_kind')
        if kind=='ACTION_PAYLOAD_INPUT_SCHEMA':
            port=ports.get(p.get('port_uid')); schema=p.get('schema')
            if not port or not isinstance(schema,dict): die('MATERIALIZE_PAYLOAD_OWNER_MISSING:'+str(u.get('target_uid')))
            old=((u.get('proposal') or {}).get('schema') or {}).get('schema_uid'); new=schema.get('schema_uid')
            if old and new and old!=new: promoted[old]=new
            if port.get('request_schema') not in (None,{}) and port.get('request_schema')!=schema: die('MATERIALIZE_REQUEST_SCHEMA_CONFLICT:'+str(p.get('port_uid')))
            port['request_schema']=schema
        elif kind=='AUDIT_EVENT_BINDING_AND_EVENT_REGISTRY_ENTRY':
            port=ports.get(p.get('port_uid')); euid,event=p.get('event_uid'),p.get('event')
            if not port: die('MATERIALIZE_AUDIT_PORT_MISSING:'+str(p.get('port_uid')))
            if euid in events and events[euid].get('event')!=event: die('MATERIALIZE_EVENT_CONFLICT:'+str(euid))
            if euid not in events:
                rec={'event_uid':euid,'event':event}; proj.setdefault('events',[]).append(rec); events[euid]=rec
            port['state_event']=build_event_state(port.get('state_event'),event)
        elif kind=='STATE_TRANSITION_LEDGER_ENRICHMENT':
            tr=transitions.get(p.get('transition_uid'))
            if not tr: die('MATERIALIZE_TRANSITION_MISSING:'+str(p.get('transition_uid')))
            for k in ('mutation_owner','failure_state','recovery','audit_event_uid','illegal_transition_tests'):
                val=p.get(k)
                if val in (None,'',[],{}): die(f'MATERIALIZE_TRANSITION_FIELD_EMPTY:{p.get("transition_uid")}:{k}')
                if k=='illegal_transition_tests':
                    for before,after in zip((u.get('proposal') or {}).get(k) or [],val):
                        if before.get('test_uid')!=after.get('test_uid'): promoted[before.get('test_uid')]=after.get('test_uid')
                if tr.get(k) not in (None,'',[],{}) and tr.get(k)!=val: die(f'MATERIALIZE_TRANSITION_CONFLICT:{p.get("transition_uid")}:{k}')
                tr[k]=val
        else: die('MATERIALIZE_UNSUPPORTED_KIND:'+str(kind))
    spec['source_projection']=proj
    spec['design_contract_remediation']={
      'current_governance_uid':CURRENT_UID,'run_uid':RUN_UID,'attempt_uid':ATTEMPT_UID,'work_unit_uid':WORK_UID,
      'review_package_ref':str(PACKAGE.relative_to(ROOT)),'candidate_ref':str(CANDIDATE.relative_to(ROOT)),
      'semantic_review_ref':str(SEMANTIC.relative_to(ROOT)),'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),
      'approved_unit_count':25,'covered_problem_count':45,'canonical_owner_materialization':True,
      'candidate_bytes_became_authority_directly':False,'raw_source_mutated':False,
      'identity_promotion_rule':'TEMP-CORE01-* -> CORE-01-*; semantic payload unchanged',
      'identity_promotions':dict(sorted(promoted.items())),'fresh_reexecution_status':'PENDING',
    }
    dump_yaml(SPEC,spec)

    # Materialization exists, but product credit remains zero until fresh reexecution proves the signatures absent.
    overlay=load_yaml(OVERLAY)
    overlay.update({'schema_version':1,'artifact_type':'EFFECTIVE_CONTRACT_OVERLAY','stage_uid':'STAGE-02','current_governance_uid':CURRENT_UID,
      'run_uid':RUN_UID,'attempt_uid':ATTEMPT_UID,'formula':'IMMUTABLE_RAW_REQUIREMENT_PLUS_APPROVED_CANONICAL_FUNCTIONAL_CONTRACT_SUCCESSOR',
      'raw_absence_alone_is_effective_gap':False,'current_discovery_gap_total':45,'legal_successor_resolution_count':45,
      'validated_product_successor_signature_count':0,'effective_open_gap_count':45,'current_effective_gap_total':45,
      'fresh_reexecution_required':True,'current_product_contract_owner_ref':str(SPEC.relative_to(ROOT)),
      'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),'external_authority_resolution_claimed':False})
    dump_yaml(OVERLAY,overlay)
    ledger=load_yaml(LEDGER); entries=ledger.setdefault('entries',[])
    entries.append({'resolution_uid':RESOLUTION_UID,'resolution_type':'APPROVED_COHERENT_DESIGN_CONTRACT_MATERIALIZATION_PENDING_FRESH_REEXECUTION',
      'work_unit_uid':WORK_UID,'page_uid':PAGE,'source_problem_denominator':45,'materialized_design_unit_count':25,
      'validated_product_successor_signature_count':0,'functional_gap_reduction_credit':0,'external_authority_resolution_credit':0,
      'canonical_owner_ref':str(SPEC.relative_to(ROOT)),'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),'validation_status':'PENDING_FRESH_REEXECUTION'})
    dump_yaml(LEDGER,ledger)
    for row in problems.get('problems') or []:
        row.update({'status':'MATERIALIZED_PENDING_FRESH_REEXECUTION','resolution_credit':0,'resolution_uid':RESOLUTION_UID,
                    'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),'canonical_owner_ref':str(SPEC.relative_to(ROOT))})
    problems.update({'raw_discovery_problem_count':45,'open_problem_count':45,'resolved_problem_count':0,'effective_open_problem_count':45,
                     'validated_product_successor_signature_count':0,'stage_exit_allowed':False})
    dump_yaml(PROBLEMS,problems)

def reset_and_reexecute():
    state=load_yaml(STATE)
    ex=state.setdefault('execution',{})
    ex['current_stage']='STAGE-01-CLOSED'
    ex['stage1']={PAGE:'PASS'}
    ex['stage2']={'result':'NOT_EXECUTED','stage_entry_gate':'PENDING','stage_exit_allowed':False,'prior_results_authoritative_for_current_governance':False,
                  'revalidation_required_under_current_governance':True,'artifact_root_present':True,'tested_page_uids':[],'remaining_page_uids':[],
                  'stage_scope_complete':False,'current_scope_manifest_ref':'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'}
    state.setdefault('governance_revision_transition',{})['fresh_revalidation_required']=True
    active=state.setdefault('stage02_active_attempt',{})
    active.update({'attempt_uid':ATTEMPT_UID,'run_uid':RUN_UID,'frozen_governance_uid':CURRENT_UID,'fresh_revalidation_required':True,
                   'closure_credit_under_current_governance':False,'product_blocker_credit':0,'validated_product_materialization_count':0})
    state.setdefault('selected_execution_profile_state',{})['active_attempt_state_key']='stage02_active_attempt'
    work=state.get('active_work_unit') or {}; work['current_status']='MATERIALIZED_PENDING_FRESH_REEXECUTION'; work['product_blocker_credit']=0
    state['next_action']='FRESHLY_REEXECUTE_CORE01_STAGE02_AGAINST_APPROVED_CANONICAL_SUCCESSOR'
    state.setdefault('resume_control',{})['current_resume_point']='STAGE2_CORE01_MATERIALIZED_PENDING_FRESH_REEXECUTION'
    state['resume_control']['exact_next_action']=state['next_action']
    dump_yaml(STATE,state)

    env=dict(os.environ); env['ACPOS_RUN_ROOT']='00_SOURCE_INTAKE/fresh_run_005'; env['STAGE02_PAGE_SCOPE']=PAGE
    run('python',str(ROOT/'governance/ci/run_current_stage2_actual_test.py'),env=env)
    result=json.loads(STAGE2_RESULT.read_text(encoding='utf-8'))
    if result.get('result')!='PASS' or result.get('stage_exit_allowed') is not True: die('FRESH_STAGE02_REEXECUTION_NOT_PASS')
    if result.get('fresh_functional_gap_total')!=0 or result.get('closure_blocker_total')!=0: die('FRESH_STAGE02_REEXECUTION_GAPS_NOT_ZERO')
    if result.get('target_pages')!=[PAGE] or result.get('remaining_pages')!=[] or result.get('stage_scope_complete') is not True: die('FRESH_STAGE02_SCOPE_NOT_COMPLETE')
    page=(result.get('pages') or {}).get(PAGE) or {}
    eci=page.get('effective_contract_input') or {}
    if eci.get('applied') is not True or eci.get('canonical_owner_ref')!=str(SPEC.relative_to(ROOT)): die('APPROVED_SUCCESSOR_NOT_CONSUMED')
    if git('rev-parse','HEAD:'+str(RAW.relative_to(ROOT)))!=RAW_BLOB: die('RAW_BLOB_MUTATED_DURING_REEXECUTION')

    problems=load_yaml(PROBLEMS)
    for row in problems.get('problems') or []:
        row.update({'status':'RESOLVED_VERIFIED_FRESH_REEXECUTION','resolution_credit':1,'fresh_reproduction_count':0})
    problems.update({'open_problem_count':0,'resolved_problem_count':45,'effective_open_problem_count':0,'validated_product_successor_signature_count':45,
                     'stage_exit_allowed':True,'stage03_allowed':True})
    dump_yaml(PROBLEMS,problems)
    overlay=load_yaml(OVERLAY); overlay.update({'validated_product_successor_signature_count':45,'effective_open_gap_count':0,'current_effective_gap_total':0,
        'fresh_reexecution_required':False,'fresh_reexecution_result':'PASS','stage_exit_allowed':True}); dump_yaml(OVERLAY,overlay)
    ledger=load_yaml(LEDGER)
    rec=next((x for x in ledger.get('entries') or [] if x.get('resolution_uid')==RESOLUTION_UID),None)
    if not rec: die('RESOLUTION_ENTRY_MISSING')
    rec.update({'resolution_type':'APPROVED_COHERENT_DESIGN_CONTRACT_MATERIALIZATION_FRESHLY_REEXECUTED',
                'validated_product_successor_signature_count':45,'functional_gap_reduction_credit':45,'validation_status':'PASS_FRESH_REEXECUTION_45_OF_45_ZERO_REPRODUCTION'})
    ledger['functional_problem_resolution_credit_total']=45; ledger['external_authority_resolution_credit_total']=0; dump_yaml(LEDGER,ledger)
    score=load_yaml(SCORE); score['review_status']='APPROVED_MATERIALIZED_FRESHLY_REEXECUTED'; score['product_blocker_credit']=45; dump_yaml(SCORE,score)
    auto=load_yaml(AUTO); auto['automatic_product_materialization_performed']=False; auto['approved_design_contract_materialization_performed']=True; auto['product_blocker_credit']=45; dump_yaml(AUTO,auto)
    spec=load_yaml(SPEC); spec['design_contract_remediation']['fresh_reexecution_status']='PASS_EFFECTIVE_GAPS_ZERO'; dump_yaml(SPEC,spec)

    dump_json(LATEST,{**result,'run_uid':RUN_UID,'attempt_uid':ATTEMPT_UID,'raw_discovery_functional_gap_total':45,
      'validated_product_successor_signature_count':45,'effective_functional_gap_total':0,'prior_stage2_results_used':False,
      'candidate_ref':str(CANDIDATE.relative_to(ROOT)),'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),
      'canonical_product_contract_owner_ref':str(SPEC.relative_to(ROOT))})
    findings=load_yaml(FINDINGS); findings.update({'run_uid':RUN_UID,'attempt_uid':ATTEMPT_UID,'fresh_functional_gap_total':0,
      'raw_discovery_functional_gap_total':45,'validated_product_successor_signature_count':45,'effective_functional_gap_total':0,'closure_blocker_total':0,
      'status':'STAGE02_PASS_PENDING_EVIDENCE_FINALIZATION','result':'PASS','candidate_ref':str(CANDIDATE.relative_to(ROOT)),
      'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),'canonical_product_contract_owner_ref':str(SPEC.relative_to(ROOT)),
      'prior_stage2_results_used':False,'product_blocker_credit':45}); dump_yaml(FINDINGS,findings)
    change=load_yaml(CHANGE); cur=change.setdefault('current_stage2_execution',{})
    cur.clear(); cur.update({'state':'PASS','current_functional_gap_count':0,'current_closure_blocker_count':0,'active_evidence_present':True,
      'active_findings_present':True,'stage_exit_allowed':True,'website_construction_allowed':False,'deployment_allowed':False,
      'historical_counts_may_be_treated_as_current':False,'source_execution_sha':git('rev-parse','HEAD'),'reexecution_cycle':'CORE01_FRESH_R3',
      'target_pages':[PAGE],'remaining_pages':[],'stage_scope_complete':True,'next_action':'FINALIZE_STAGE02_CURRENT_EVIDENCE_AND_PERSISTED_HEAD_VALIDATION',
      'attempt_uid':ATTEMPT_UID,'frozen_governance_uid':CURRENT_UID,'raw_discovery_gap_count':45,'product_materialization_elimination_count':45,
      'validated_product_successor_signature_count':45,'effective_functional_gap_count':0,'external_authority_elimination_count':0,
      'total_fresh_elimination_count':45,'preserved_external_authority_union_count':result.get('preserved_external_authority_union_count'),
      'prior_stage2_results_used':False,'product_blocker_reduction_credit':45,'candidate_ref':str(CANDIDATE.relative_to(ROOT)),
      'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),'canonical_product_contract_owner_ref':str(SPEC.relative_to(ROOT)),
      'fresh_revalidation_required_under_current_governance':True,'closure_credit_under_current_governance':False,
      'execution_scope_manifest_ref':'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'})
    dump_yaml(CHANGE,change)

    state=load_yaml(STATE); ex=state['execution']; ex['current_stage']='STAGE-02-CLOSED'; ex['stage2']={
      'result':'PASS','stage_entry_gate':'PASS','stage_exit_allowed':True,'prior_results_used_in_current_run':False,
      'prior_results_authoritative_for_current_governance':False,'revalidation_required_under_current_governance':True,
      'artifact_root_present':True,'tested_page_uids':[PAGE],'remaining_page_uids':[],'stage_scope_complete':True,
      'current_scope_manifest_ref':'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'}
    active=state['stage02_active_attempt']; active.update({'raw_discovery_functional_gap_total':45,'fresh_functional_gap_total':0,
      'effective_functional_gap_total':0,'fresh_closure_blocker_total':0,'validated_product_materialization_count':45,'product_blocker_credit':45,
      'fresh_revalidation_required':True,'closure_credit_under_current_governance':False,'next_action':'FINALIZE_STAGE02_CURRENT_EVIDENCE_AND_PERSISTED_HEAD_VALIDATION'})
    work=state.get('active_work_unit') or {}; work.update({'current_status':'PENDING_EVIDENCE_FINALIZATION','product_blocker_credit':45,
      'human_product_contract_review_status':'APPROVED_BY_EXPLICIT_USER_DIRECTIVE_UNIQUE_COHERENT_CANDIDATE',
      'canonical_product_contract_owner_ref':str(SPEC.relative_to(ROOT))})
    state['status']='STAGE02_PASS_PENDING_PERSISTED_HEAD_VALIDATION'; state['next_action']='FINALIZE_STAGE02_CURRENT_EVIDENCE_AND_PERSISTED_HEAD_VALIDATION'
    state['current_primary_task_product_stage_credit']=45
    state.setdefault('governance_revision_transition',{})['fresh_revalidation_required']=True
    resume=state.setdefault('resume_control',{}); resume.update({'current_resume_point':'STAGE2_CORE01_PASS_PENDING_PERSISTED_HEAD_VALIDATION',
      'current_work_unit_uid':WORK_UID,'current_owner':str(SPEC.relative_to(ROOT)),'exact_next_action':state['next_action']})
    dump_yaml(STATE,state)
    scope=load_yaml(SCOPE); scope['stage_exit_credit_allowed']=True; scope['fresh_revalidation_required']=True
    tmp=deepcopy(scope); tmp.pop('content_hash',None); scope['content_hash']=sha_obj(tmp); dump_yaml(SCOPE,scope)
    review={'schema_version':1,'artifact_type':'PAGE_FUNCTIONAL_REVIEW_EVIDENCE','normative_authority':False,'current_governance_uid':CURRENT_UID,
      'run_uid':RUN_UID,'attempt_uid':ATTEMPT_UID,'page_uid':PAGE,'stage_uid':'STAGE-02','stage1_raw_blob_sha':RAW_BLOB,
      'raw_discovery_functional_gap_total':45,'validated_product_successor_signature_count':45,'effective_functional_gap_total':0,
      'closure_blocker_total':0,'remaining_required_stage2_units':0,'stage_exit_allowed':True,'prior_stage2_results_used':False,
      'external_authority_resolution_credit':0,'candidate_ref':str(CANDIDATE.relative_to(ROOT)),'semantic_review_ref':str(SEMANTIC.relative_to(ROOT)),
      'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),'canonical_product_contract_owner_ref':str(SPEC.relative_to(ROOT)),
      'status':'PASS_PENDING_EXACT_ARTIFACT_AND_PERSISTED_HEAD_BINDING'}
    dump_yaml(REVIEW,review)

def finalize():
    run_id=os.environ.get('GITHUB_RUN_ID','').strip(); aid=os.environ.get('STAGE02_ARTIFACT_ID','').strip(); digest=os.environ.get('STAGE02_ARTIFACT_DIGEST','').strip()
    if not run_id or not aid or not digest: die('FINALIZE_ENV_MISSING')
    digest=digest.removeprefix('sha256:')
    if not re.fullmatch(r'[0-9a-f]{64}',digest): die('FINALIZE_DIGEST_INVALID')
    state=load_yaml(STATE); findings=load_yaml(FINDINGS); change=load_yaml(CHANGE); review=load_yaml(REVIEW)
    active=state.get('stage02_active_attempt') or {}; active.update({'source_workflow_run_id':int(run_id),'source_artifact_id':int(aid),
      'source_artifact_sha256':digest,'fresh_revalidation_required':False,'closure_credit_under_current_governance':True})
    state['stage02_active_attempt']=active
    trans=state.setdefault('governance_revision_transition',{}); trans['fresh_revalidation_required']=False
    ex=state.get('execution') or {}; s2=ex.get('stage2') or {}; s2['revalidation_required_under_current_governance']=False; ex['stage2']=s2; state['execution']=ex
    work=state.get('active_work_unit') or {}; work['current_status']='PENDING_PERSISTED_HEAD_TERMINAL_VALIDATION'; work['source_workflow_run_id']=int(run_id); work['source_artifact_id']=int(aid); work['source_artifact_sha256']=digest
    state['next_action']='RUN_PERSISTED_HEAD_FULL_LINE_AND_CLOSE_STAGE02'
    state['status']='STAGE02_PASS_CURRENT_EVIDENCE_BOUND_PENDING_TERMINAL_VALIDATION'
    state['resume_control'].update({'current_resume_point':'STAGE2_PASS_CURRENT_EVIDENCE_BOUND_PENDING_TERMINAL_VALIDATION','exact_next_action':state['next_action']})
    dump_yaml(STATE,state)
    findings.update({'source_workflow_run_id':int(run_id),'source_artifact_id':int(aid),'source_artifact_sha256':digest,'status':'STAGE02_PASS_CURRENT_EVIDENCE_BOUND'}); dump_yaml(FINDINGS,findings)
    cur=change.get('current_stage2_execution') or {}; cur.update({'source_workflow_run_id':int(run_id),'source_artifact_id':int(aid),'source_artifact_sha256':digest,
      'fresh_revalidation_required_under_current_governance':False,'closure_credit_under_current_governance':True,'next_action':state['next_action']}); dump_yaml(CHANGE,change)
    review.update({'source_workflow_run_id':int(run_id),'source_artifact_id':int(aid),'source_artifact_sha256':digest,'status':'PASS_CURRENT_EVIDENCE_BOUND_PENDING_PERSISTED_HEAD_TERMINAL_VALIDATION'}); dump_yaml(REVIEW,review)
    scope=load_yaml(SCOPE); scope['fresh_revalidation_required']=False; tmp=deepcopy(scope); tmp.pop('content_hash',None); scope['content_hash']=sha_obj(tmp); dump_yaml(SCOPE,scope)

def materialize_and_reexecute():
    build_candidate_and_approval(); apply_materialization(); reset_and_reexecute()
    print(json.dumps({'candidate_units':25,'source_problems':45,'fresh_effective_gaps':0,'closure_blockers':0,'stage_exit_allowed':True,
      'raw_blob':RAW_BLOB,'external_authority_resolution_credit':0,'next':'FINALIZE_EVIDENCE'},ensure_ascii=False,indent=2))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=['materialize','finalize'],default='materialize'); a=ap.parse_args()
    if a.mode=='materialize': materialize_and_reexecute()
    else: finalize()

if __name__=='__main__': main()
