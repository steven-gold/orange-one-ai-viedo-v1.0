#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from copy import deepcopy
import hashlib, json, os, re, subprocess, sys, urllib.request
import yaml

ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
SCOPE=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
FINDINGS=ROOT/'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
LATEST=ROOT/'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
REVIEW=ROOT/'governance/test/stage02/PAGE_FUNCTIONAL_REVIEW_EVIDENCE.yaml'
CHANGE=ROOT/'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
PROBLEMS=ROOT/'00_SOURCE_INTAKE/fresh_run_005/04_PAGE_FUNCTIONAL_CONTRACT/CURRENT_PROBLEM_REGISTER.yaml'
RAW=ROOT/'00_SOURCE_INTAKE/fresh_run_005/00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml'
AUTH=ROOT/'governance/test/spec_change_authorizations/USR-DIRECTIVE-20260919-COMPLETE-CORE01-STAGE02-R3.yaml'
CURRENT_UID='GOV-REV-20260919-PROFILE-TOKEN-DECONTAMINATION-HARDENING'
RUN_UID='FRESH-RUN-005'
ATTEMPT_UID='STAGE02-FRESH-20260919-CORE01-002'
WORK_UID='WU-STAGE02-CORE01-FRESH-FUNCTIONAL-REMEDIATION-002'
RAW_BLOB='9490f3bcc28c5511bc04d6c3ce53c026e3c4667f'
PRODUCT_COMMIT='cb764da2ce787280ae4e5ef70b2383adbbc9b871'
VALIDATION_HEAD='e48ac1bce7e7798c107694087f0056b8a434bf08'
RUNS={
 'full_line':35401771995,
 'selected_profile':35401771918,
 'stage02_boundary':35401771883,
 'branch_guard':35401772007,
}
NEXT='WORK_UNIT_RESOLUTION_GATE_REQUIRED_FOR_STAGE03'

def die(msg):
    print('BLOCK:',msg,file=sys.stderr); raise SystemExit(1)
def git(*args):
    cp=subprocess.run(['git',*args],cwd=ROOT,text=True,capture_output=True)
    if cp.returncode: die('GIT:'+cp.stderr.strip())
    return cp.stdout.strip()
def y(p):
    if not p.is_file(): die('MISSING:'+str(p.relative_to(ROOT)))
    x=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(x,dict): die('MAPPING_REQUIRED:'+str(p.relative_to(ROOT)))
    return x
def j(p):
    if not p.is_file(): die('MISSING:'+str(p.relative_to(ROOT)))
    x=json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(x,dict): die('JSON_MAPPING_REQUIRED:'+str(p.relative_to(ROOT)))
    return x
def dy(p,x):
    p.write_text(yaml.safe_dump(x,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def dj(p,x):
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def content_hash(x):
    d=deepcopy(x); d.pop('content_hash',None)
    return hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def get_run(run_id):
    token=os.environ.get('GITHUB_TOKEN','').strip(); repo=os.environ.get('GITHUB_REPOSITORY','').strip()
    if not token or not repo: die('GITHUB_OBSERVATION_CONTEXT_MISSING')
    req=urllib.request.Request(
      f'https://api.github.com/repos/{repo}/actions/runs/{run_id}',
      headers={'Authorization':f'Bearer {token}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    )
    try:
        with urllib.request.urlopen(req,timeout=30) as resp: x=json.loads(resp.read().decode())
    except Exception as exc: die('GITHUB_RUN_FETCH:'+repr(exc))
    return x
def main():
    if y(AUTH).get('status')!='APPROVED_FOR_EXACT_SCOPE': die('AUTHORIZATION_INVALID')
    if git('rev-parse','HEAD:'+str(RAW.relative_to(ROOT)))!=RAW_BLOB: die('STAGE1_RAW_BLOB_DRIFT')
    git('merge-base','--is-ancestor',PRODUCT_COMMIT,'HEAD')
    git('merge-base','--is-ancestor',VALIDATION_HEAD,'HEAD')

    observed={}
    for label,rid in RUNS.items():
        x=get_run(rid)
        observed[label]={'run_id':rid,'status':x.get('status'),'conclusion':x.get('conclusion'),'head_sha':x.get('head_sha')}
        if x.get('status')!='completed' or x.get('conclusion')!='success' or x.get('head_sha')!=VALIDATION_HEAD:
            die(f'TERMINAL_RUN_INVALID:{label}:{observed[label]}')

    state=y(STATE); problems=y(PROBLEMS); latest=j(LATEST); findings=y(FINDINGS); review=y(REVIEW); change=y(CHANGE); scope=y(SCOPE)
    if state.get('specification_uid')!=CURRENT_UID: die('CURRENT_GOVERNANCE_DRIFT')
    work=state.get('active_work_unit') or {}
    if work.get('work_unit_uid')!=WORK_UID or work.get('current_status')!='PENDING_PERSISTED_HEAD_TERMINAL_VALIDATION': die('WORK_UNIT_NOT_TERMINAL_READY')
    if int(work.get('product_blocker_credit') or 0)!=45: die('WORK_UNIT_CREDIT_NOT_45')
    if problems.get('open_problem_count')!=0 or problems.get('resolved_problem_count')!=45 or problems.get('effective_open_problem_count')!=0: die('PROBLEM_REGISTER_NOT_CLOSED')
    if latest.get('result')!='PASS' or latest.get('effective_functional_gap_total')!=0 or latest.get('closure_blocker_total')!=0 or latest.get('stage_exit_allowed') is not True: die('LATEST_EVIDENCE_NOT_STAGE2_PASS')
    if latest.get('remaining_pages')!=[] or latest.get('stage_scope_complete') is not True: die('LATEST_SCOPE_NOT_COMPLETE')
    if review.get('stage_exit_allowed') is not True or review.get('effective_functional_gap_total')!=0 or review.get('remaining_required_stage2_units')!=0: die('FUNCTIONAL_REVIEW_NOT_CLOSED')
    if scope.get('included_units')!=['CORE-01'] or scope.get('excluded_units')!=['ASSET-01'] or scope.get('remaining_units')!=[]: die('SCOPE_DRIFT')
    if scope.get('stage_exit_credit_allowed') is not True or scope.get('fresh_revalidation_required') is not False: die('SCOPE_NOT_TERMINAL_READY')
    active=state.get('stage02_active_attempt') or {}
    if active.get('attempt_uid')!=ATTEMPT_UID or active.get('effective_functional_gap_total')!=0 or active.get('fresh_closure_blocker_total')!=0: die('ACTIVE_ATTEMPT_NOT_ZERO')
    if active.get('closure_credit_under_current_governance') is not True or active.get('fresh_revalidation_required') is not False: die('ACTIVE_ATTEMPT_NOT_CURRENT_REVALIDATED')

    closed=deepcopy(work)
    closed.update({
      'current_status':'CLOSED_VERIFIED_STAGE02_EFFECTIVE_GAPS_ZERO',
      'terminal_disposition':'CLOSED_VERIFIED_PRODUCT_CONTRACT_MATERIALIZATION_FRESH_REEXECUTION_AND_PERSISTED_HEAD_GATES',
      'resume_after_closure':NEXT,
      'product_blocker_credit':45,
      'closure_evidence':{
        'current_governance_uid':CURRENT_UID,'branch':'rebuild-v2.1.1','run_uid':RUN_UID,'attempt_uid':ATTEMPT_UID,
        'source_problem_denominator':45,'validated_product_successor_signature_count':45,'effective_open_problem_count':0,
        'closure_blocker_total':0,'remaining_required_stage2_units':0,'product_blocker_reduction_credit':45,
        'external_authority_resolution_credit':0,'stage1_raw_blob_sha':RAW_BLOB,
        'product_materialization_commit':PRODUCT_COMMIT,'preclosure_validation_head':VALIDATION_HEAD,
        'product_source_workflow_run_id':active.get('source_workflow_run_id'),'product_source_artifact_id':active.get('source_artifact_id'),
        'product_source_artifact_sha256':active.get('source_artifact_sha256'),
        'terminal_runs':observed,
        'candidate_ref':findings.get('candidate_ref'),'approval_evidence_ref':findings.get('approval_evidence_ref'),
        'canonical_product_contract_owner_ref':findings.get('canonical_product_contract_owner_ref'),
      }
    })
    if state.get('last_closed_product_work_unit'):
        state['previous_closed_product_work_unit']=state.get('last_closed_product_work_unit')
    state['last_closed_product_work_unit']=closed
    state.pop('active_work_unit',None)
    if state.get('work_unit_resolution_gate'):
        state['last_work_unit_resolution_gate']=state.get('work_unit_resolution_gate')
        state.pop('work_unit_resolution_gate',None)

    ex=state.setdefault('execution',{})
    ex['current_stage']='STAGE-02-CLOSED'
    s2=ex.setdefault('stage2',{})
    s2.update({'result':'TEST_EXECUTED_PASS','stage_entry_gate':'PASS','stage_exit_allowed':True,
      'prior_results_used_in_current_run':False,'prior_results_authoritative_for_current_governance':False,
      'revalidation_required_under_current_governance':False,'artifact_root_present':True,
      'tested_page_uids':['CORE-01'],'remaining_page_uids':[],'stage_scope_complete':True,
      'current_scope_manifest_ref':'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'})
    ex['website_construction_allowed']=False; ex['deployment_allowed']=False
    state['status']='STAGE02_CLOSED_VERIFIED_CORE01'
    state['next_action']=NEXT
    state['current_primary_task_product_stage_credit']=45
    resume=state.setdefault('resume_control',{})
    resume.update({'current_resume_point':'STAGE2_CORE01_CLOSED_STAGE3_WUR_REQUIRED','current_work_unit_uid':None,'current_owner':None,
      'historical_stage2_results_are_current_state':False,'stage2_execution_requires_fresh_entry_resolution':False,
      'last_closed_product_work_unit_uid':WORK_UID,'last_closed_product_validation_head':VALIDATION_HEAD,
      'last_closed_product_outer_run_id':RUNS['full_line'],'last_closed_product_outer_result':'success','exact_next_action':NEXT})
    active['next_action']=NEXT
    state['stage02_active_attempt']=active
    trans=state.setdefault('governance_revision_transition',{}); trans['fresh_revalidation_required']=False
    fl=state.setdefault('full_lifecycle_governance_system_test',{})
    fl.update({'full_line_github_result':'success','persisted_head_revalidation_required':False,'terminal_run_conclusion':'success',
      'terminal_result_credit_allowed':True,'full_line_verification_run_id':RUNS['full_line'],'full_line_verification_head_sha':VALIDATION_HEAD})
    state['stage02_terminal_closure']={
      'status':'CLOSED_VERIFIED','work_unit_uid':WORK_UID,'stage_uid':'STAGE-02','page_scope':['CORE-01'],
      'stage_exit_credit':True,'effective_functional_gap_total':0,'closure_blocker_total':0,'remaining_required_units':0,
      'validation_head':VALIDATION_HEAD,'terminal_runs':observed,'next_action':NEXT,
    }
    dy(STATE,state)

    findings.update({'status':'STAGE02_CLOSED_VERIFIED','result':'PASS','next_action':NEXT,'stage_exit_allowed':True,
      'effective_functional_gap_total':0,'closure_blocker_total':0,'product_blocker_credit':45,
      'terminal_validation_head':VALIDATION_HEAD,'terminal_validation_runs':observed})
    dy(FINDINGS,findings)

    cur=change.setdefault('current_stage2_execution',{})
    cur.update({'state':'TEST_EXECUTED_PASS','current_functional_gap_count':0,'current_closure_blocker_count':0,
      'stage_exit_allowed':True,'stage_scope_complete':True,'remaining_pages':[],'next_action':NEXT,
      'core01_work_unit_status':'CLOSED_VERIFIED_STAGE02_EFFECTIVE_GAPS_ZERO','terminal_validation_head':VALIDATION_HEAD,
      'terminal_validation_runs':observed,'closure_credit_under_current_governance':True,'fresh_revalidation_required_under_current_governance':False})
    dy(CHANGE,change)

    review.update({'status':'PASS_STAGE02_CLOSED_PERSISTED_HEAD_VERIFIED','terminal_validation_head':VALIDATION_HEAD,
      'terminal_validation_runs':observed,'stage_exit_allowed':True,'remaining_required_stage2_units':0,'next_action':NEXT})
    dy(REVIEW,review)

    latest['terminal_validation_head']=VALIDATION_HEAD
    latest['terminal_validation_runs']=observed
    latest['stage2_terminal_closure']='PASS'
    latest['next_action']=NEXT
    dj(LATEST,latest)

    scope['stage_exit_credit_allowed']=True
    scope['fresh_revalidation_required']=False
    scope['closure_status']='STAGE02_CLOSED_VERIFIED'
    scope['next_action']=NEXT
    scope['content_hash']=content_hash(scope)
    dy(SCOPE,scope)

    print(json.dumps({
      'stage2':'CLOSED_VERIFIED','work_unit_uid':WORK_UID,'effective_functional_gap_total':0,
      'closure_blocker_total':0,'remaining_required_units':0,'stage_exit_credit':True,
      'validation_head':VALIDATION_HEAD,'terminal_runs':observed,'next_action':NEXT
    },ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
