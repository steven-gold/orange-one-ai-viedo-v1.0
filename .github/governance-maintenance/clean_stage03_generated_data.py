#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json, os, subprocess
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
NEXT_ATTEMPT='STAGE03-CORE01-V2215-20260920-002'
NEXT_RUN='VISUAL-CORE01-V2215-STAGE03-R2'

EXPECTED_VISUAL={
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CHANGE_IMPACT_MAP.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CLASSIFICATION_RULESET.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CURRENT_PROBLEM_REGISTER.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/DENOMINATOR_SNAPSHOT.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/DEPENDENCY_TOPOLOGY.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/EFFECTIVE_CONTRACT_OVERLAY.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/FUNCTIONAL_CHAIN_MANIFEST.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/REQUIRED_FIELD_MANIFEST.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/RESOLUTION_LEDGER.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_CHANGESET.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_DESIGN_SPEC_PACKAGE.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_GEOMETRY_CONTRACT.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_INHERITANCE_MATRIX.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_INTERACTION_TOPOLOGY_BINDING.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_PREVIEW.svg',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_PREVIEW_EVIDENCE.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_REFERENCE_ANNOTATION.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_REVIEW_EVIDENCE.yaml',
'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01/VISUAL_SCENARIO_EVIDENCE_SET.yaml',
}
EXPECTED_TEST={
'governance/test/stage03/STAGE03_CURRENT_FINDINGS.yaml',
'governance/test/stage03/STAGE03_LATEST_TEST_EVIDENCE.json',
}
PROTECTED=[
RUN_ROOT/'00_SOURCE_INTAKE',
RUN_ROOT/'01_CLASSIFIED',
RUN_ROOT/'02_BASE_BLUEPRINT',
RUN_ROOT/'03_BLUEPRINT_BINDING',
RUN_ROOT/'04_PAGE_FUNCTIONAL_CONTRACT',
RUN_ROOT/'CURRENT_RUN_MANIFEST.yaml',
RUN_ROOT/'EXECUTION_STATE.yaml',
RUN_ROOT/'RUN_CONTEXT.yaml',
]

def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def dump(p,o): Path(p).write_text(yaml.safe_dump(o,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def run(*args,check=True):
    cp=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    if check and cp.returncode:
        print(cp.stdout)
        print(cp.stderr)
        raise SystemExit(cp.returncode)
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
    else:
        raise SystemExit(f'BLOCK: protected path missing {p.relative_to(ROOT)}')
    return h.hexdigest()
def hobj(d):
    x=copy.deepcopy(d); x.pop('content_hash',None)
    return hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True,width=180).encode()).hexdigest()

reg=load(REG); state=load(STATE); scope=load(SCOPE)
if (reg.get('active_specification') or {}).get('governance_uid')!=GOV:
    raise SystemExit('BLOCK: governance drift')
if state.get('specification_uid')!=GOV or scope.get('governance_uid')!=GOV:
    raise SystemExit('BLOCK: projector governance drift')
work=state.get('active_work_unit') or {}
if state.get('current_primary_task_layer')!='PRODUCT_STAGE_EXECUTION' or work.get('work_unit_uid')!=WU or work.get('stage_uid')!='STAGE-03':
    raise SystemExit('BLOCK: Stage-03 product WU not active')

stage3=((state.get('execution') or {}).get('stage3') or {})
attempt=state.get('stage03_active_attempt') or {}
resume=(state.get('resume_control') or {}).get('current_resume_point')

# Second clean replay is authorized only from the persisted first fresh attempt.
if stage3.get('result')!='TEST_EXECUTED_BLOCKED' or work.get('current_status')!='BLOCKED_UNRESOLVED_VISUAL_AUTHORITY':
    raise SystemExit('BLOCK: rerun cleanup requires persisted blocked Stage-03 product attempt')
if resume!='STAGE3_CORE01_VISUAL_AUTHORITY_BLOCKED':
    raise SystemExit('BLOCK: rerun cleanup resume boundary drift')
if attempt.get('attempt_uid')!='STAGE03-CORE01-V2215-20260920-001':
    raise SystemExit('BLOCK: unexpected predecessor Stage-03 attempt')
if attempt.get('source_workflow_run_id')!=35484945017 or attempt.get('source_artifact_id')!=10597038682:
    raise SystemExit('BLOCK: predecessor Stage-03 provenance drift')
if attempt.get('open_gap_total')!=2 or attempt.get('closure_blocker_total')!=2:
    raise SystemExit('BLOCK: predecessor blocker denominator drift')

visual=tracked(VISUAL_ROOT); tests=tracked(TEST_ROOT)
if visual!=EXPECTED_VISUAL:
    raise SystemExit('BLOCK: visual cleanup cohort drift:'+json.dumps(sorted(visual^EXPECTED_VISUAL)))
if tests!=EXPECTED_TEST:
    raise SystemExit('BLOCK: test cleanup cohort drift:'+json.dumps(sorted(tests^EXPECTED_TEST)))

protected_before={str(p.relative_to(ROOT)):digest_path(p) for p in PROTECTED}
source_head=run('git','rev-parse','HEAD').stdout.strip()

# Persist the exact first fresh attempt as historical provenance before deleting Current materializations.
history=state.setdefault('stage03_attempt_history',[])
snapshot=copy.deepcopy(attempt)
snapshot['historical_role']='SUPERSEDED_BY_EXPLICIT_FRESH_RERUN_REQUEST'
snapshot['current_closure_credit']=False
snapshot['tracked_current_files_deleted_for_rerun']=True
snapshot['preserved_execution_commit']='47bd0e2b7206feeba8063894e7aefdadd5d4b7d7'
snapshot['preserved_high_pressure_review_head']='122d9cfc49c49d7120e0c01ab82252f1634e486e'
snapshot['preserved_high_pressure_run_id']=35485261155
snapshot['preserved_high_pressure_artifact_id']=10596879379
snapshot['preserved_high_pressure_result']='75/75_PASS'
if not any(isinstance(x,dict) and x.get('attempt_uid')==snapshot.get('attempt_uid') for x in history):
    history.append(snapshot)
state['stage03_attempt_history']=history

old_result=state.pop('stage03_result_evidence',None)
if old_result:
    evidence_history=state.setdefault('stage03_result_evidence_history',[])
    evidence_history.append({
      **copy.deepcopy(old_result),
      'attempt_uid':attempt.get('attempt_uid'),
      'source_workflow_run_id':attempt.get('source_workflow_run_id'),
      'source_artifact_id':attempt.get('source_artifact_id'),
      'source_artifact_sha256':attempt.get('source_artifact_sha256'),
      'current_role':'HISTORICAL_PREDECESSOR_EVIDENCE_POINTER_ONLY',
      'tracked_current_evidence_deleted_by_clean_reset':True,
    })
    state['stage03_result_evidence_history']=evidence_history

prior_receipt=state.get('stage03_clean_baseline_receipt')
if isinstance(prior_receipt,dict):
    receipt_history=state.setdefault('stage03_clean_baseline_receipt_history',[])
    if not any(isinstance(x,dict) and x.get('cleanup_workflow_run_id')==prior_receipt.get('cleanup_workflow_run_id') for x in receipt_history):
        receipt_history.append(copy.deepcopy(prior_receipt))
    state['stage03_clean_baseline_receipt_history']=receipt_history

run('git','rm','-r','--',str(VISUAL_ROOT.relative_to(ROOT)),str(TEST_ROOT.relative_to(ROOT))

state.pop('stage03_active_attempt',None)
ps=state.setdefault('selected_execution_profile_state',{})
ps.pop('active_attempt_state_key',None)

work['current_status']='CLEAN_BASELINE_READY_FOR_FRESH_EXECUTION_R2'
work['attempt_uid']=NEXT_ATTEMPT
work['run_uid']=NEXT_RUN
work['canonical_owner']=PRODUCER
work['planned_output_owner']=PLANNED_OWNER
work['generated_output_root_present']=False
work['fresh_execution_evidence_ref']=None
work['product_blocker_credit']=0
hb=work.setdefault('human_review_boundary',{})
hb['visual_review']='NOT_REACHED_R2_NOT_EXECUTED'
hb['visual_approval']=False
hb['authority_update']=False
hb['design_freeze']=False
state['active_work_unit']=work

ex=state.setdefault('execution',{})
ex['run_uid']=NEXT_RUN
ex['current_stage']='STAGE-03-CLEAN-BASELINE-READY-R2'
s3=ex.setdefault('stage3',{})
s3['result']='NOT_EXECUTED'
s3['execution_started']=False
s3['pre_execution_gate']='GOVERNANCE_LOAD_RECEIPT_REQUIRED'
s3['pre_execution_gate_status']='NOT_EXECUTED'
s3['stage_exit_allowed']=False
s3['artifact_root_present']=False
s3['output_owner_materialized']=False
s3['prior_results_authoritative_for_current_governance']=False
s3['revalidation_required_under_current_governance']=False
s3['target_page_uids']=['CORE-01']
s3['remaining_page_uids']=['CORE-01']
s3['human_visual_review_reached']=False
ex['stage3']=s3
ex['website_construction_allowed']=False
ex['deployment_allowed']=False
state['execution']=ex

trans=state.setdefault('governance_revision_transition',{})
trans['fresh_revalidation_required']=False
trans['current_product_attempt_uid']=NEXT_ATTEMPT
trans['current_product_attempt_run_uid']=NEXT_RUN
trans.pop('current_product_attempt_workflow_run_id',None)
trans.pop('current_product_attempt_artifact_id',None)
trans.pop('current_product_attempt_artifact_sha256',None)

state['status']='ACTIVE_CORE01_STAGE03_CLEAN_BASELINE_READY_R2'
state['next_action']='RUN_FRESH_STAGE03_R2'
state['resume_control']={
  'current_resume_point':'STAGE03_CORE01_CLEAN_BASELINE_READY_R2',
  'current_work_unit_uid':WU,
  'current_owner':PRODUCER,
  'historical_stage2_results_are_current_state':False,
  'stage2_execution_requires_fresh_entry_resolution':False,
  'exact_next_action':'RUN_FRESH_STAGE03_R2',
  'governance_uid':GOV,
}
state['stage03_clean_baseline_receipt']={
  'artifact_type':'STAGE03_CLEAN_BASELINE_RECEIPT',
  'normative_authority':False,
  'governance_uid':GOV,
  'work_unit_uid':WU,
  'cleanup_generation':'R2',
  'cleanup_source_head_sha':source_head,
  'cleanup_workflow_run_id':os.environ.get('GITHUB_RUN_ID','LOCAL'),
  'predecessor_attempt_uid':'STAGE03-CORE01-V2215-20260920-001',
  'predecessor_workflow_run_id':35484945017,
  'predecessor_artifact_id':10597038682,
  'predecessor_high_pressure_run_id':35485261155,
  'predecessor_high_pressure_artifact_id':10596879379,
  'next_attempt_uid':NEXT_ATTEMPT,
  'next_run_uid':NEXT_RUN,
  'deleted_roots':[str(VISUAL_ROOT.relative_to(ROOT)),str(TEST_ROOT.relative_to(ROOT))],
  'deleted_file_count':len(visual)+len(tests),
  'deleted_visual_file_count':len(visual),
  'deleted_current_test_evidence_file_count':len(tests),
  'historical_action_artifacts_preserved':True,
  'stage01_stage02_inputs_deleted':False,
  'protected_subtree_sha256_before':protected_before,
  'result':'CLEANING',
}
dump(STATE,state)

scope['remaining_units']=['CORE-01']
scope['closure_status']='STAGE03_CLEAN_BASELINE_READY_R2'
scope['next_action']='RUN_FRESH_STAGE03_R2'
scope['fresh_revalidation_required']=False
scope['stage_exit_credit_allowed']=False
scope['content_hash']=hobj(scope)
dump(SCOPE,scope)

protected_after={str(p.relative_to(ROOT)):digest_path(p) for p in PROTECTED}
if protected_before!=protected_after:
    raise SystemExit('BLOCK: Stage-01/02 protected input drift during R2 cleanup')
if VISUAL_ROOT.exists() or TEST_ROOT.exists():
    raise SystemExit('BLOCK: Stage-03 generated roots still exist after R2 cleanup')

state=load(STATE)
state['stage03_clean_baseline_receipt']['protected_subtree_sha256_after']=protected_after
state['stage03_clean_baseline_receipt']['result']='PASS_CLEAN_BASELINE_R2'
dump(STATE,state)

print(json.dumps({
  'result':'PASS_CLEAN_BASELINE_R2',
  'deleted_file_count':len(visual)+len(tests),
  'deleted_visual_file_count':len(visual),
  'deleted_test_file_count':len(tests),
  'next_attempt_uid':NEXT_ATTEMPT,
  'next_run_uid':NEXT_RUN,
  'stage01_stage02_hashes_preserved':protected_before==protected_after,
  'next_action':'RUN_FRESH_STAGE03_R2'
},indent=2))
