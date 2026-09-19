#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import copy, hashlib, importlib.util, json, os, re, sys
import yaml

ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
SCOPE=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
HISTORY=ROOT/'governance/test/SELECTED_PROFILE_HISTORY_BINDING.yaml'
CANDIDATES=ROOT/'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
FINDINGS=ROOT/'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
EVIDENCE=ROOT/'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
RUNNER=ROOT/'.github/governance-maintenance/run_fresh_stage_replay.py'

def load_runner():
    spec=importlib.util.spec_from_file_location('acpos_dynamic_fresh_replay_runner',RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError('DYNAMIC_REPLAY_RUNNER_IMPORT_FAILED')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

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
    runner=load_runner()
    if '--identity-self-test' in sys.argv:
        runner.identity_self_test()
        print(json.dumps({'result':'PASS','finalizer_dynamic_context_import':True},indent=2))
        return
    ctx=runner.resolve_execution_context()
    CURRENT_UID=ctx['governance_uid']
    DISPLAY_VERSION=ctx['display_version']
    RUN_UID=ctx['run_uid']
    PAGE=ctx['page_scope'][0]
    ATTEMPT_UID=ctx['attempt_uid']
    RUN_ROOT=ctx['run_root']
    EXCLUDED_UNITS=list(ctx['excluded_page_scope'])
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
    attempt['fresh_functional_gap_total']=int(ev.get('fresh_functional_gap_total') or 0)
    attempt['fresh_closure_blocker_total']=int(ev.get('closure_blocker_total') or 0)
    attempt['preserved_external_authority_union_count']=int(ev.get('preserved_external_authority_union_count') or 0)
    attempt['official_stage_output_denominator_count']=len(ev.get('official_stage_output_denominator') or [])
    attempt['current_manifest_mandatory_stage_output_subset_count']=len(ev.get('execution_profile_mandatory_output_subset') or [])
    attempt['next_action']=state.get('next_action')
    state['stage02_active_attempt']=attempt
    state['stage2_result_evidence']={
      'mode':'RUNTIME_GENERATED_GITHUB_ACTION_ARTIFACT',
      'static_result_pointer_required':False,
      'static_run_id_copy_forbidden':True,
      'static_head_sha_copy_forbidden':True,
      'static_specification_digest_copy_forbidden':True,
      'tracked_current_evidence_ref':'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json',
      'artifact_provenance_recorded_in_active_attempt':True,
    }
    state['stage02_material_remediation']={
      'material_remediation_started':bool(s2.get('artifact_root_present')),
      'run_uid':RUN_UID,'attempt_uid':ATTEMPT_UID,
      'source_problem_denominator':attempt['fresh_functional_gap_total'],
      'source_closure_blocker_denominator':attempt['fresh_closure_blocker_total'],
      'product_blocker_credit':0,
      'status':'CURRENT_FRESH_PRODUCT_ROOT_PROVENANCE_BOUND',
    }

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
      'excluded_unit_generated_data_present':{uid:False for uid in EXCLUDED_UNITS},
      'product_blocker_credit':0,
      'status':'CURRENT_FRESH_STAGE01_STAGE02_EXECUTION_EVIDENCE_BOUND',
    }
    replay_ctx=state.get('fresh_replay_execution_context') or {}
    if replay_ctx.get('run_uid')!=RUN_UID or replay_ctx.get('status')!='READY_FOR_REPLAY':
        raise RuntimeError('FRESH_REPLAY_CONTEXT_CONSUMPTION_DRIFT')
    replay_ctx['status']='CONSUMED'
    replay_ctx['consumed_by_workflow_run_id']=attempt['source_workflow_run_id']
    replay_ctx['consumed_source_sha']=source_sha
    replay_ctx['evidence_artifact_id']=attempt['source_artifact_id']
    replay_ctx['evidence_artifact_sha256']=attempt['source_artifact_sha256']
    state['fresh_replay_execution_context']=replay_ctx
    dump_yaml(STATE,state)

    scope=load_yaml(SCOPE)
    if scope.get('included_units')!=[PAGE] or scope.get('excluded_units')!=EXCLUDED_UNITS:
        raise RuntimeError('EXECUTION_SCOPE_DRIFT')
    scope['fresh_revalidation_required']=False
    scope['stage_exit_credit_allowed']=bool(s2.get('stage_exit_allowed'))
    tmp=copy.deepcopy(scope)
    tmp.pop('content_hash',None)
    scope['content_hash']=sha_obj(tmp)
    dump_yaml(SCOPE,scope)

    history=load_yaml(HISTORY)
    history['status']='ACTIVE_PROFILE_HISTORY_EVIDENCE_BINDING'
    history['scope']={
      PAGE:{
        'expected_result':'PASS',
        'artifacts':[
          {'artifact_ref':f'{RUN_ROOT}/02_BASE_BLUEPRINT/{PAGE}/PAGE_BASE_BLUEPRINT.yaml','creation_governance_overlay':DISPLAY_VERSION},
          {'artifact_ref':f'{RUN_ROOT}/02_BASE_BLUEPRINT/{PAGE}/VISUAL_BASE_BLUEPRINT.yaml','creation_governance_overlay':DISPLAY_VERSION},
          {'artifact_ref':f'{RUN_ROOT}/03_BLUEPRINT_BINDING/{PAGE}/BLUEPRINT_BINDING_MANIFEST.yaml','creation_governance_overlay':DISPLAY_VERSION},
        ],
        'profile_step_uid':'STAGE-01',
      }
    }
    history['current_scope_binding']={
      'run_uid':RUN_UID,
      'page_scope':[PAGE],
      'excluded_page_scope':EXCLUDED_UNITS,
      'prior_product_artifact_reuse':False,
      'binding_reason':'FRESH_STAGE01_REPLAY_CURRENT_SCOPE',
    }
    dump_yaml(HISTORY,history)

    candidates=load_yaml(CANDIDATES)
    candidates['current_stage2_execution']={
      'state':s2.get('result'),
      'current_functional_gap_count':attempt.get('fresh_functional_gap_total'),
      'current_closure_blocker_count':attempt.get('fresh_closure_blocker_total'),
      'active_evidence_present':True,
      'active_findings_present':True,
      'stage_exit_allowed':bool(s2.get('stage_exit_allowed')),
      'website_construction_allowed':False,
      'deployment_allowed':False,
      'historical_counts_may_be_treated_as_current':False,
      'source_execution_sha':source_sha,
      'reexecution_cycle':RUN_UID,
      'target_pages':[PAGE],
      'remaining_pages':[],
      'stage_scope_complete':True,
      'next_action':state.get('next_action'),
      'attempt_uid':ATTEMPT_UID,
      'frozen_governance_uid':CURRENT_UID,
      'raw_discovery_gap_count':attempt.get('fresh_functional_gap_total'),
      'product_materialization_elimination_count':0,
      'external_authority_elimination_count':0,
      'total_fresh_elimination_count':0,
      'preserved_external_authority_union_count':ev.get('preserved_external_authority_union_count'),
      'official_stage_output_denominator_count':len(ev.get('official_stage_output_denominator') or []),
      'current_manifest_mandatory_stage_output_subset_count':len(ev.get('execution_profile_mandatory_output_subset') or []),
      'prior_stage2_results_used':False,
      'source_workflow_run_id':attempt['source_workflow_run_id'],
      'source_artifact_id':attempt['source_artifact_id'],
      'source_artifact_sha256':attempt['source_artifact_sha256'],
      'product_blocker_reduction_credit':0,
      'validated_product_successor_signature_count':0,
      'effective_functional_gap_count':attempt.get('fresh_functional_gap_total'),
      'planning_baseline_completeness':ev.get('planning_baseline_completeness'),
      'current_work_unit_status':'DESIGN_CONTRACT_REMEDIATION_REQUIRED' if attempt.get('fresh_functional_gap_total') else 'READY_FOR_TERMINAL_CLOSURE',
      'fresh_revalidation_required_under_current_governance':False,
      'current_governance_uid':CURRENT_UID,
      'closure_credit_under_current_governance':True,
      'execution_scope_manifest_ref':'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml',
      'canonical_product_contract_owner_ref':f'{RUN_ROOT}/04_PAGE_FUNCTIONAL_CONTRACT/{PAGE}/FUNCTIONAL_CHAIN_SPEC.yaml',
    }
    dump_yaml(CANDIDATES,candidates)

    findings=load_yaml(FINDINGS)
    findings['attempt_uid']=ATTEMPT_UID
    findings['run_uid']=RUN_UID
    findings['governance_uid']=CURRENT_UID
    findings['frozen_governance_uid']=CURRENT_UID
    findings['source_execution_sha']=source_sha
    findings['source_head_sha']=source_sha
    findings['source_workflow_run_id']=attempt['source_workflow_run_id']
    findings['source_artifact_id']=attempt['source_artifact_id']
    findings['source_artifact_sha256']=attempt['source_artifact_sha256']
    findings['fresh_functional_gap_total']=attempt.get('fresh_functional_gap_total')
    findings['closure_blocker_total']=attempt.get('fresh_closure_blocker_total')
    findings['fresh_closure_blocker_total']=attempt.get('fresh_closure_blocker_total')
    findings['preserved_external_authority_union_count']=attempt.get('preserved_external_authority_union_count')
    findings['official_stage_output_denominator_count']=attempt.get('official_stage_output_denominator_count')
    findings['current_manifest_mandatory_stage_output_subset_count']=attempt.get('current_manifest_mandatory_stage_output_subset_count')
    findings['next_action']=state.get('next_action')
    findings['prior_stage2_results_used']=False
    findings['product_blocker_credit']=0
    dump_yaml(FINDINGS,findings)

    print(json.dumps({
      'run_uid':RUN_UID,
      'attempt_uid':ATTEMPT_UID,
      'workflow_run_id':attempt['source_workflow_run_id'],
      'artifact_id':attempt['source_artifact_id'],
      'artifact_sha256':attempt['source_artifact_sha256'],
      'stage2_result':s2.get('result'),
      'planning_baseline_completeness':ev.get('planning_baseline_completeness'),
      'fresh_revalidation_required':False,
      'closure_credit_under_current_governance':True,
      'product_blocker_credit':0,
    },ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
