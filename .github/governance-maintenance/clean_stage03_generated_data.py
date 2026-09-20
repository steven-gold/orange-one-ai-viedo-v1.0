#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, subprocess
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
RUN_ROOT=ROOT/'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02'
VISUAL_ROOT=RUN_ROOT/'05_VISUAL_DESIGN'
TEST_ROOT=ROOT/'governance/test/stage03'
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
SCOPE=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
REG=ROOT/'governance/specifications/REGISTRY.yaml'
GOV='GOV-REV-20260920-STAGE03-VISUAL-MATERIALIZATION-PROMOTION-CLOSURE'
WU='WU-STAGE03-CORE01-VISUAL-DESIGN-001'
PRODUCER='governance/ci/run_current_stage3_visual_design.py'
PLANNED_OWNER='00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_DESIGN_SPEC_PACKAGE.yaml'
EXPECTED_VISUAL={
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CHANGE_IMPACT_MAP.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CLASSIFICATION_RULESET.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_CHANGESET.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_DESIGN_SPEC_PACKAGE.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_GEOMETRY_CONTRACT.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_INTERACTION_TOPOLOGY_BINDING.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_PREVIEW.svg',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_PREVIEW_EVIDENCE.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_REVIEW_EVIDENCE.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CURRENT_PROBLEM_REGISTER.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/DENOMINATOR_SNAPSHOT.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/DEPENDENCY_TOPOLOGY.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/EFFECTIVE_CONTRACT_OVERLAY.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/FUNCTIONAL_CHAIN_MANIFEST.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/REQUIRED_FIELD_MANIFEST.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/RESOLUTION_LEDGER.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml'}
EXPECTED_TEST={
'governance/test/stage03/STAGE03_CURRENT_FINDINGS.yaml',
'governance/test/stage03/STAGE03_LATEST_TEST_EVIDENCE.json'}
PROTECTED=[
RUN_ROOT/'00_SOURCE_INTAKE',RUN_ROOT/'01_CLASSIFIED',RUN_ROOT/'02_BASE_BLUEPRINT',
RUN_ROOT/'03_BLUEPRINT_BINDING',RUN_ROOT/'04_PAGE_FUNCTIONAL_CONTRACT',
RUN_ROOT/'CURRENT_RUN_MANIFEST.yaml',RUN_ROOT/'EXECUTION_STATE.yaml',RUN_ROOT/'RUN_CONTEXT.yaml']

def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def dump(p,o): Path(p).write_text(yaml.safe_dump(o,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def run(*args,check=True):
    cp=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    if check and cp.returncode:
        print(cp.stdout); print(cp.stderr); raise SystemExit(cp.returncode)
    return cp
def tracked(prefix):
    cp=run('git','ls-files','--',str(prefix.relative_to(ROOT)))
    return {x for x in cp.stdout.splitlines() if x}
def digest_path(p):
    h=hashlib.sha256()
    if p.is_file():
        h.update(p.relative_to(ROOT).as_posix().encode()+b'\0'+p.read_bytes())
    elif p.is_dir():
        for f in sorted(x for x in p.rglob('*') if x.is_file()):
            h.update(f.relative_to(ROOT).as_posix().encode()+b'\0'+f.read_bytes())
    else: raise SystemExit(f'BLOCK: protected path missing {p.relative_to(ROOT)}')
    return h.hexdigest()
def hobj(d):
    x=dict(d); x.pop('content_hash',None)
    return hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True,width=180).encode()).hexdigest()

reg=load(REG); state=load(STATE); scope=load(SCOPE)
already_clean = (not VISUAL_ROOT.exists()) and (not TEST_ROOT.exists())
if already_clean:
    receipt=state.get('stage03_clean_baseline_receipt') or {}
    if receipt.get('result')!='PASS_CLEAN_BASELINE' or receipt.get('deleted_file_count')!=20:
        raise SystemExit('BLOCK: generated roots absent without valid clean-baseline receipt')
    if (reg.get('active_specification') or {}).get('governance_uid')!=GOV or state.get('specification_uid')!=GOV or scope.get('governance_uid')!=GOV:
        raise SystemExit('BLOCK: clean-baseline repair governance drift')
    work=state.get('active_work_unit') or {}
    if work.get('work_unit_uid')!=WU or state.get('current_primary_task_layer')!='PRODUCT_STAGE_EXECUTION':
        raise SystemExit('BLOCK: clean-baseline repair product WU drift')
    protected_before={str(p.relative_to(ROOT)):digest_path(p) for p in PROTECTED}
    ps=state.setdefault('selected_execution_profile_state',{})
    ps.pop('active_attempt_state_key',None)
    trans=state.setdefault('governance_revision_transition',{})
    trans['fresh_revalidation_required']=False
    ex=state.setdefault('execution',{})
    s3=ex.setdefault('stage3',{})
    s3['result']='NOT_EXECUTED'
    s3['execution_started']=False
    s3['artifact_root_present']=False
    s3['output_owner_materialized']=False
    s3['prior_results_authoritative_for_current_governance']=False
    s3['revalidation_required_under_current_governance']=False
    ex['stage3']=s3
    ex['website_construction_allowed']=False
    ex['deployment_allowed']=False
    state['execution']=ex
    receipt['state_projection_finalized']=True
    receipt['state_projection_repair_source_head_sha']=run('git','rev-parse','HEAD').stdout.strip()
    receipt['result']='PASS_CLEAN_BASELINE_CURRENT_STATE_FINALIZED'
    state['stage03_clean_baseline_receipt']=receipt
    state['status']='ACTIVE_CORE01_STAGE03_CLEAN_BASELINE_READY'
    state['next_action']='PATCH_STAGE03_PRODUCER_FOR_V2215_AND_RUN_FRESH_STAGE03'
    state['resume_control']={
      'current_resume_point':'STAGE03_CORE01_CLEAN_BASELINE_READY',
      'current_work_unit_uid':WU,
      'current_owner':PRODUCER,
      'historical_stage2_results_are_current_state':False,
      'stage2_execution_requires_fresh_entry_resolution':False,
      'exact_next_action':'PATCH_STAGE03_PRODUCER_FOR_V2215_AND_RUN_FRESH_STAGE03',
      'governance_uid':GOV
    }
    dump(STATE,state)
    scope['closure_status']='STAGE03_CLEAN_BASELINE_READY'
    scope['next_action']='PATCH_STAGE03_PRODUCER_FOR_V2215_AND_RUN_FRESH_STAGE03'
    scope['fresh_revalidation_required']=False
    scope['stage_exit_credit_allowed']=False
    scope['content_hash']=hobj(scope)
    dump(SCOPE,scope)
    protected_after={str(p.relative_to(ROOT)):digest_path(p) for p in PROTECTED}
    if protected_before!=protected_after:
        raise SystemExit('BLOCK: protected Stage-01/02 drift during clean-state finalization')
    print(json.dumps({'result':'PASS_CLEAN_BASELINE_CURRENT_STATE_FINALIZED','deleted_file_count':20,'next_action':state['next_action']},indent=2))
    raise SystemExit(0)
if (reg.get('active_specification') or {}).get('governance_uid')!=GOV: raise SystemExit('BLOCK: governance drift')
if state.get('specification_uid')!=GOV or scope.get('governance_uid')!=GOV: raise SystemExit('BLOCK: projector governance drift')
work=state.get('active_work_unit') or {}
if state.get('current_primary_task_layer')!='PRODUCT_STAGE_EXECUTION' or work.get('work_unit_uid')!=WU or work.get('stage_uid')!='STAGE-03': raise SystemExit('BLOCK: Stage-03 product WU not active')
if ((state.get('execution') or {}).get('stage3') or {}).get('result')!='NOT_EXECUTED': raise SystemExit('BLOCK: Stage-03 must be NOT_EXECUTED before clean reset')
if state.get('stage03_active_attempt'): raise SystemExit('BLOCK: current Stage-03 active attempt must be absent before cleanup')
if (state.get('resume_control') or {}).get('current_resume_point')!='STAGE03_CORE01_CLEAN_REEXECUTION_REQUIRED': raise SystemExit('BLOCK: cleanup resume boundary drift')

visual=tracked(VISUAL_ROOT); tests=tracked(TEST_ROOT)
if visual!=EXPECTED_VISUAL: raise SystemExit('BLOCK: visual cleanup cohort drift:'+json.dumps(sorted(visual^EXPECTED_VISUAL)))
if tests!=EXPECTED_TEST: raise SystemExit('BLOCK: test cleanup cohort drift:'+json.dumps(sorted(tests^EXPECTED_TEST)))
protected_before={str(p.relative_to(ROOT)):digest_path(p) for p in PROTECTED}

run('git','rm','-r','--',str(VISUAL_ROOT.relative_to(ROOT)),str(TEST_ROOT.relative_to(ROOT)))

old_ev=state.pop('stage03_result_evidence',None)
if old_ev:
    old_ev=dict(old_ev)
    old_ev['current_role']='HISTORICAL_PREDECESSOR_EVIDENCE_POINTER_ONLY'
    old_ev['tracked_current_evidence_deleted_by_clean_reset']=True
    state['previous_stage03_result_evidence']=old_ev
pres=state.get('preserved_stage03_product_work_unit')
if isinstance(pres,dict):
    pres['current_role']='HISTORICAL_PREDECESSOR_WORK_UNIT_SNAPSHOT_ONLY'
    pres['current_closure_credit']=False
    state['preserved_stage03_product_work_unit']=pres

work['current_status']='CLEAN_BASELINE_READY_FOR_FRESH_EXECUTION'
work['canonical_owner']=PRODUCER
work['planned_output_owner']=PLANNED_OWNER
work['generated_output_root_present']=False
work['fresh_execution_evidence_ref']=None
work['product_blocker_credit']=0
state['active_work_unit']=work
state['status']='ACTIVE_CORE01_STAGE03_CLEAN_BASELINE_READY'
state['next_action']='PATCH_STAGE03_PRODUCER_FOR_V2215_AND_RUN_FRESH_STAGE03'
state['resume_control']={
 'current_resume_point':'STAGE03_CORE01_CLEAN_BASELINE_READY',
 'current_work_unit_uid':WU,
 'current_owner':PRODUCER,
 'historical_stage2_results_are_current_state':False,
 'stage2_execution_requires_fresh_entry_resolution':False,
 'exact_next_action':'PATCH_STAGE03_PRODUCER_FOR_V2215_AND_RUN_FRESH_STAGE03',
 'governance_uid':GOV
}
ex=state.setdefault('execution',{})
s3=ex.setdefault('stage3',{})
s3['result']='NOT_EXECUTED'
s3['execution_started']=False
s3['pre_execution_gate']='GOVERNANCE_LOAD_RECEIPT_REQUIRED'
s3['pre_execution_gate_status']='NOT_EXECUTED'
s3['stage_exit_allowed']=False
s3['artifact_root_present']=False
s3['output_owner_materialized']=False
s3['prior_results_authoritative_for_current_governance']=False
s3['revalidation_required_under_current_governance']=True
ex['stage3']=s3
ex['current_stage']='STAGE-03-CLEAN-BASELINE-READY'
ex['website_construction_allowed']=False; ex['deployment_allowed']=False
state['execution']=ex
state['stage03_clean_baseline_receipt']={
 'artifact_type':'STAGE03_CLEAN_BASELINE_RECEIPT',
 'normative_authority':False,
 'governance_uid':GOV,
 'work_unit_uid':WU,
 'cleanup_source_head_sha':run('git','rev-parse','HEAD').stdout.strip(),
 'cleanup_workflow_run_id':os.environ.get('GITHUB_RUN_ID','LOCAL'),
 'deleted_roots':[str(VISUAL_ROOT.relative_to(ROOT)),str(TEST_ROOT.relative_to(ROOT))],
 'deleted_file_count':len(visual)+len(tests),
 'deleted_visual_file_count':len(visual),
 'deleted_current_test_evidence_file_count':len(tests),
 'historical_action_artifact_preserved':True,
 'stage01_stage02_inputs_deleted':False,
 'protected_subtree_sha256_before':protected_before,
 'result':'CLEAN_BASELINE_MATERIALIZED_PENDING_PERSIST'
}
dump(STATE,state)

scope['closure_status']='STAGE03_CLEAN_BASELINE_READY'
scope['next_action']='PATCH_STAGE03_PRODUCER_FOR_V2215_AND_RUN_FRESH_STAGE03'
scope['fresh_revalidation_required']=True
scope['stage_exit_credit_allowed']=False
scope['content_hash']=hobj(scope)
dump(SCOPE,scope)

protected_after={str(p.relative_to(ROOT)):digest_path(p) for p in PROTECTED}
if protected_before!=protected_after: raise SystemExit('BLOCK: Stage-01/02 protected input drift during cleanup')
if VISUAL_ROOT.exists() or TEST_ROOT.exists(): raise SystemExit('BLOCK: Stage-03 generated roots still exist after cleanup')
state=load(STATE)
state['stage03_clean_baseline_receipt']['protected_subtree_sha256_after']=protected_after
state['stage03_clean_baseline_receipt']['result']='PASS_CLEAN_BASELINE'
dump(STATE,state)
print(json.dumps({'result':'PASS_CLEAN_BASELINE','deleted_file_count':20,'protected_paths':protected_after,'next_action':state['next_action']},indent=2))
