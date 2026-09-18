#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import copy, hashlib, json, os, re
import yaml

ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
SCOPE=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
EVIDENCE=ROOT/'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
CURRENT_UID='GOV-REV-20260919-PROFILE-TOKEN-DECONTAMINATION-HARDENING'
RUN_UID='FRESH-RUN-005'
PAGE='CORE-01'
ATTEMPT_UID='STAGE02-FRESH-20260919-CORE01-002'

def load_yaml(p:Path):
    obj=yaml.safe_load(p.read_text(encoding='utf-8'))
    if not isinstance(obj,dict):
        raise RuntimeError(f'MAPPING_REQUIRED:{p}')
    return obj

def dump_yaml(p:Path,obj:dict):
    p.write_text(yaml.safe_dump(obj,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')

def sha_obj(obj:dict)->str:
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def need_env(name:str)->str:
    v=os.environ.get(name,'').strip()
    if not v:
        raise RuntimeError(f'MISSING_ENV:{name}')
    return v

def main():
    run_id=need_env('FRESH_REPLAY_RUN_ID')
    source_sha=need_env('FRESH_REPLAY_SOURCE_SHA')
    artifact_id=need_env('FRESH_EVIDENCE_ARTIFACT_ID')
    digest=need_env('FRESH_EVIDENCE_ARTIFACT_DIGEST')
    digest=digest.split(':',1)[1] if digest.startswith('sha256:') else digest
    if not re.fullmatch(r'[0-9a-fA-F]{64}',digest):
        raise RuntimeError('ARTIFACT_DIGEST_NOT_SHA256')
    if not re.fullmatch(r'[0-9a-f]{40}',source_sha):
        raise RuntimeError('SOURCE_SHA_INVALID')

    state=load_yaml(STATE)
    if state.get('specification_uid')!=CURRENT_UID:
        raise RuntimeError('CURRENT_GOVERNANCE_UID_DRIFT')
    ex=state.get('execution') or {}
    if ex.get('run_uid')!=RUN_UID or ex.get('target_pages')!=[PAGE]:
        raise RuntimeError('FRESH_RUN_IDENTITY_DRIFT')
    s2=ex.get('stage2') or {}
    if s2.get('result') not in {'TEST_EXECUTED_BLOCKED','TEST_EXECUTED_PASS'}:
        raise RuntimeError('STAGE02_RESULT_NOT_EXECUTED')
    if s2.get('prior_results_used_in_current_run') is not False:
        raise RuntimeError('PRIOR_STAGE02_REUSE_DETECTED')

    attempt=state.get('stage02_active_attempt') or {}
    if attempt.get('attempt_uid')!=ATTEMPT_UID or attempt.get('run_uid')!=RUN_UID:
        raise RuntimeError('ACTIVE_ATTEMPT_IDENTITY_DRIFT')
    if attempt.get('frozen_governance_uid')!=CURRENT_UID:
        raise RuntimeError('ACTIVE_ATTEMPT_GOVERNANCE_DRIFT')

    ev=json.loads(EVIDENCE.read_text(encoding='utf-8'))
    if ev.get('target_pages')!=[PAGE] or ev.get('prior_stage2_results_used') is not False:
        raise RuntimeError('EVIDENCE_SCOPE_OR_REUSE_DRIFT')

    attempt['source_execution_sha']=source_sha
    attempt['source_workflow_run_id']=int(run_id) if run_id.isdigit() else run_id
    attempt['source_artifact_id']=int(artifact_id) if artifact_id.isdigit() else artifact_id
    attempt['source_artifact_sha256']=digest.lower()
    attempt['active_evidence_present']=True
    attempt['active_findings_present']=True
    attempt['fresh_revalidation_required']=False
    attempt['closure_credit_under_current_governance']=True
    state['stage02_active_attempt']=attempt

    profile=state.setdefault('selected_execution_profile_state',{})
    profile['active_attempt_state_key']='stage02_active_attempt'

    trans=state.setdefault('governance_revision_transition',{})
    trans['current_governance_uid']=CURRENT_UID
    trans['predecessor_attempt_preserved_as_historical_evidence']=True
    trans['predecessor_attempt_may_close_under_current_governance']=False
    trans['fresh_revalidation_required']=False
    trans['current_product_attempt_uid']=ATTEMPT_UID
    trans['current_product_attempt_run_uid']=RUN_UID
    trans['current_product_attempt_workflow_run_id']=attempt['source_workflow_run_id']
    trans['current_product_attempt_artifact_id']=attempt['source_artifact_id']
    trans['current_product_attempt_artifact_sha256']=attempt['source_artifact_sha256']

    s2['prior_results_authoritative_for_current_governance']=False
    s2['revalidation_required_under_current_governance']=False
    ex['stage2']=s2
    state['execution']=ex

    state['fresh_replay_provenance']={
      'run_uid':RUN_UID,
      'page_scope':[PAGE],
      'workflow_run_id':attempt['source_workflow_run_id'],
      'source_execution_sha':source_sha,
      'evidence_artifact_id':attempt['source_artifact_id'],
      'evidence_artifact_sha256':attempt['source_artifact_sha256'],
      'prior_stage01_stage02_product_outputs_reused':False,
      'asset01_generated_data_present':False,
      'product_blocker_credit':0,
      'status':'CURRENT_FRESH_STAGE01_STAGE02_EXECUTION_EVIDENCE_BOUND',
    }
    dump_yaml(STATE,state)

    scope=load_yaml(SCOPE)
    if scope.get('included_units')!=[PAGE] or scope.get('excluded_units')!=['ASSET-01']:
        raise RuntimeError('EXECUTION_SCOPE_DRIFT')
    scope['fresh_revalidation_required']=False
    scope['stage_exit_credit_allowed']=bool(s2.get('stage_exit_allowed'))
    tmp=copy.deepcopy(scope)
    tmp.pop('content_hash',None)
    scope['content_hash']=sha_obj(tmp)
    dump_yaml(SCOPE,scope)

    print(json.dumps({
      'run_uid':RUN_UID,
      'attempt_uid':ATTEMPT_UID,
      'workflow_run_id':attempt['source_workflow_run_id'],
      'artifact_id':attempt['source_artifact_id'],
      'artifact_sha256':attempt['source_artifact_sha256'],
      'stage2_result':s2.get('result'),
      'fresh_revalidation_required':False,
      'closure_credit_under_current_governance':True,
      'product_blocker_credit':0,
    },ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
