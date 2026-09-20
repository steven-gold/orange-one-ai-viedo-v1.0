#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
SCOPE=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
PROFILE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
REG=ROOT/'governance/specifications/REGISTRY.yaml'
GOV_UID='GOV-REV-20260920-STAGE03-VISUAL-MATERIALIZATION-PROMOTION-CLOSURE'
GOV_WU='WU-GOV-STAGE03-VISUAL-MATERIALIZATION-HARDENING-001'
PRODUCT_WU='WU-STAGE03-CORE01-VISUAL-DESIGN-001'
VALIDATED_HEAD='f7dad5ac112337251f35678a95e9d8f3d99d9d4d'
FULL_LINE_RUN=35483671654
PROFILE_RUN=35483671548
BRANCH_RUN=35483671577
PROMOTION_RUN=35483447515
PROMOTION_COMMIT='c8831d036acb26e1b518e2ca54d79c55bf1faa8a'

def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def dump(p,o): Path(p).write_text(yaml.safe_dump(o,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def hobj(d):
    x=dict(d); x.pop('content_hash',None)
    return hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True,width=180).encode()).hexdigest()

state=load(STATE); scope=load(SCOPE); profile=load(PROFILE); reg=load(REG)
if (reg.get('active_specification') or {}).get('governance_uid')!=GOV_UID: raise SystemExit('BLOCK: Current Governance UID drift')
if state.get('specification_uid')!=GOV_UID or scope.get('governance_uid')!=GOV_UID: raise SystemExit('BLOCK: Current projector Governance UID drift')
aw=state.get('active_work_unit') or {}
if aw.get('work_unit_uid')!=GOV_WU or state.get('current_primary_task_layer')!='GOVERNANCE_MAINTENANCE': raise SystemExit('BLOCK: governance WU not active')
st=next((x for x in profile.get('stages',[]) if x.get('stage_uid')=='STAGE-03'),None)
if not st: raise SystemExit('BLOCK: Stage-03 profile missing')
ops=list(map(str,st.get('operations') or [])); outputs=list(map(str,st.get('outputs') or [])); producers=st.get('output_producers') or {}
if len(ops)!=9 or len(outputs)!=9 or any(not producers.get(x) for x in outputs): raise SystemExit('BLOCK: Stage-03 9-output profile not current')
deps=list(scope.get('dependency_closure_refs') or [])
needed=['VISUAL_BASE_BLUEPRINT.yaml','PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml','FUNCTIONAL_WORKBENCH_CONTRACT.yaml','INTERACTION_TOPOLOGY_SPEC.yaml','AI_INTERACTION_CONTINUITY_CONTRACT.yaml','FUNCTION_VISUAL_IMPACT_MATRIX.yaml']
resolved=[]
for name in needed:
    rows=[x for x in deps if str(x).endswith('/'+name)]
    if len(rows)!=1: raise SystemExit(f'BLOCK: exact dependency {name} unresolved: {rows}')
    resolved.append(rows[0])

old_attempt=state.get('stage03_active_attempt') or {}
state['previous_stage03_attempt']={**old_attempt,'current_role':'HISTORICAL_PREDECESSOR_ATTEMPT_ONLY','current_closure_credit':False,'superseded_by_governance_uid':GOV_UID}
state.pop('stage03_active_attempt',None)
closed=dict(aw)
closed.update({
  'current_status':'CLOSED_VERIFIED_NO_PRODUCT_CREDIT',
  'closure_head_sha':VALIDATED_HEAD,
  'closure_evidence':{
    'current_governance_uid':GOV_UID,'branch':'rebuild-v2.1.1','validated_head_sha':VALIDATED_HEAD,
    'promotion_commit':PROMOTION_COMMIT,'promotion_run_id':PROMOTION_RUN,'promotion_result':'success',
    'full_line_run_id':FULL_LINE_RUN,'full_line_result':'success',
    'selected_profile_run_id':PROFILE_RUN,'selected_profile_result':'success',
    'branch_authority_run_id':BRANCH_RUN,'branch_authority_result':'success',
    'product_stage_credit':0
  },
  'product_stage_credit':0,
  'resume_after_closure':'STAGE03_CORE01_CLEAN_REEXECUTION_REQUIRED'
})
state['closed_governance_work_unit_stage03_visual_materialization_hardening']=closed

outroot='00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/05_VISUAL_DESIGN/CORE-01'
operation_bindings={}
for op in ops:
    out=[x for x in outputs if str(producers.get(x))==op]
    operation_bindings[op]={
      'executor_owner':'governance/ci/run_current_stage3_visual_design.py',
      'result_owner':f'{outroot}/{out[0]}.yaml' if out else f'governance/test/stage03/{op}_RESULT.yaml'
    }

product={
  'work_unit_uid':PRODUCT_WU,
  'canonical_name':'CORE01_VISUAL_DESIGN',
  'primary_task_layer':'PRODUCT_STAGE_EXECUTION',
  'stage_uid':'STAGE-03',
  'semantic_capability':'VISUAL_DESIGN',
  'scope':['CORE-01'],
  'out_of_scope':['ASSET-01','STAGE-04','WEBSITE_CONSTRUCTION','DEPLOYMENT','EXTERNAL_AUTHORITY_AUTOFILL','GLOBAL_VISUAL_AUTHORITY_INVENTION','GLOBAL_SHELL_AUTHORITY_INVENTION'],
  'canonical_policy_owner':'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',
  'state_owner':'governance/test/ACTIVE_STATE.yaml',
  'scope_manifest_ref':'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml',
  'current_status':'FRESH_REEXECUTION_REQUIRED_AFTER_GOVERNANCE_SUCCESSOR',
  'attempt_uid':'STAGE03-CORE01-V2215-20260920-001',
  'run_uid':'VISUAL-CORE01-V2215-STAGE03-R1',
  'canonical_owner':f'{outroot}/VISUAL_DESIGN_SPEC_PACKAGE.yaml',
  'output_root':outroot,
  'predecessor_stage02_work_unit_uid':'WU-STAGE02-CORE01-D81DF9AC-REPLAY',
  'start_condition':['STAGE02_CLOSED_VERIFIED','STAGE02_EFFECTIVE_FUNCTIONAL_GAPS_ZERO','STAGE02_REMAINING_REQUIRED_UNITS_ZERO','CURRENT_SCOPE_CORE01_ONLY','GOVERNANCE_V2_2_15_EXACT_HEAD_VALIDATED','WORK_UNIT_RESOLUTION_PASS_SINGLE_LEGAL_SUCCESSOR'],
  'dependencies':resolved,
  'required_operations':ops,
  'required_outputs':outputs,
  'operation_bindings':operation_bindings,
  'required_gates':['ALL_REQUIRED_PAGES_STAGE2_CLOSED','GOVERNANCE_LOAD_RECEIPT_PASS','VAL-GOV-029','VAL-GOV-030','VAL-GOV-037','CLOSURE_EVIDENCE_CONTINUITY','CANONICAL_EXECUTION_PREFLIGHT','VISUAL_DESIGN_PROFILE_MATERIALIZATION_COMPLETENESS'],
  'required_evidence':['VISUAL_REVIEW_EVIDENCE','VISUAL_REFERENCE_ANNOTATION','VISUAL_INHERITANCE_MATRIX','VISUAL_SCENARIO_EVIDENCE_SET'],
  'definition_of_done':['ALL_PROFILE_REQUIRED_STAGE03_OUTPUTS_MATERIALIZED_FOR_CORE01','VISUAL_REFERENCE_ANNOTATION_COMPLETE','VISUAL_INHERITANCE_MATRIX_MATERIALIZED_WITH_UNRESOLVED_AUTHORITIES_PRESERVED','VISUAL_SCENARIO_EVIDENCE_SET_MATERIALIZED','EXPLICIT_ATOMIC_WORKBENCH_VISUAL_BINDINGS_PRESERVED','FUNCTIONAL_TO_VISUAL_TOPOLOGY_EQUIVALENCE_PRESERVED','NO_UNAPPROVED_FUNCTIONAL_TOPOLOGY_REDEFINITION','REVIEWABLE_VISUAL_EVIDENCE_COVERS_APPLICABLE_CONTROL_FIELD_STATE_DENOMINATOR','CURRENT_PROBLEM_DENOMINATOR_RECOMPUTED_FROM_PHYSICAL_CURRENT_INPUTS','UNRESOLVED_GLOBAL_VISUAL_SHELL_AUTHORITY_NOT_AUTOFILLED','VISUAL_REVIEW_EVIDENCE_PERSISTED_WHEN_REVIEWABLE','CORE01_STAGE03_REQUIRED_SCOPE_CLOSED_WITH_FRESH_EVIDENCE','ASSET01_REMAINS_OUT_OF_SCOPE_AND_UNMATERIALIZED','NEXT_RESUME_PERSISTED_TO_STAGE04_WORK_UNIT_RESOLUTION_BOUNDARY'],
  'human_review_boundary':{'visual_review':'NOT_REACHED_AFTER_GOVERNANCE_SUCCESSOR','visual_approval':False,'authority_update':False,'design_freeze':False,'rule':'DO_NOT_REACH_HUMAN_VISUAL_REVIEW_UNTIL_CURRENT_VISUAL_AUTHORITY_AND_REVIEWABILITY_GATES_PASS'},
  'product_blocker_credit':0,
  'legal_next_transition':'STAGE03_CLOSED_TO_STAGE04_WORK_UNIT_RESOLUTION'
}
wur={'resolution_uid':'WUR-PRODUCT-STAGE03-CORE01-RESTORE-AFTER-GOV-V2215-001','normative_authority':False,'requested_primary_task_layer':'PRODUCT_STAGE_EXECUTION','predecessor_work_unit_uid':GOV_WU,'predecessor_disposition':'CLOSED_VERIFIED_NO_PRODUCT_CREDIT','candidate_successor_work_unit_uid':PRODUCT_WU,'canonical_owner':product['canonical_owner'],'dependency_legality':'PASS','reverse_dependency_legality':'PASS','applicability':'PASS','duplicate_parallel_work_unit':'NONE','result':'PASS_SINGLE_LEGAL_SUCCESSOR','exact_resume_point':'STAGE03_CORE01_CLEAN_REEXECUTION_REQUIRED','product_stage_credit':0}
state['last_work_unit_resolution_gate']=wur
state['work_unit_resolution_gate_stage03_product_restore_v2215']=wur
state['active_work_unit']=product
state['current_primary_task_layer']='PRODUCT_STAGE_EXECUTION'
state['current_primary_task_authorization_uid']='USR-DIRECTIVE-20260920-STAGE03-VISUAL-MATERIALIZATION-HARDENING-R3'
state['current_primary_task_product_stage_credit']=0
state['status']='ACTIVE_CORE01_STAGE03_CLEAN_REEXECUTION_REQUIRED'
state['next_action']='DELETE_STAGE03_GENERATED_OUTPUTS_AND_RUN_FRESH_STAGE03'
state['resume_control']={'current_resume_point':'STAGE03_CORE01_CLEAN_REEXECUTION_REQUIRED','current_work_unit_uid':PRODUCT_WU,'current_owner':product['canonical_owner'],'historical_stage2_results_are_current_state':False,'stage2_execution_requires_fresh_entry_resolution':False,'exact_next_action':'DELETE_STAGE03_GENERATED_OUTPUTS_AND_RUN_FRESH_STAGE03','governance_validation_head':VALIDATED_HEAD,'governance_full_line_run_id':FULL_LINE_RUN,'governance_selected_profile_run_id':PROFILE_RUN,'governance_branch_authority_run_id':BRANCH_RUN}
ex=state.setdefault('execution',{})
ex['run_uid']=product['run_uid']; ex['scope_mode']='EXACT_PAGE_SCOPE_ONLY'; ex['target_pages']=['CORE-01']; ex['current_stage']='STAGE-03-CLEAN-REEXECUTION-REQUIRED'
ex['stage3']={'result':'NOT_EXECUTED_AFTER_GOVERNANCE_SUCCESSOR','work_unit_uid':PRODUCT_WU,'work_unit_resolution':'PASS_SINGLE_LEGAL_SUCCESSOR','execution_started':False,'pre_execution_gate':'GOVERNANCE_LOAD_RECEIPT_REQUIRED','pre_execution_gate_status':'NOT_EXECUTED','stage_exit_allowed':False,'artifact_root_present':True,'prior_results_authoritative_for_current_governance':False,'revalidation_required_under_current_governance':True,'target_page_uids':['CORE-01'],'remaining_page_uids':['CORE-01'],'current_scope_manifest_ref':'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml','output_owner_materialized':True,'visual_review_required':True}
ex['website_construction_allowed']=False; ex['deployment_allowed']=False
state['execution']=ex
gt=state.setdefault('governance_revision_transition',{})
gt['mother_machine_revalidation_complete']=True
gt['mother_machine_revalidation_run_id']=FULL_LINE_RUN
gt['mother_machine_revalidation_head']=VALIDATED_HEAD
gt['mother_machine_revalidation_result']='success'
gt['selected_execution_profile_run_id']=PROFILE_RUN
gt['branch_guard_run_id']=BRANCH_RUN
gt['fresh_revalidation_required']=False
gt['product_fresh_replay_required_after_governance_change']=True
dump(STATE,state)

scope['fresh_revalidation_required']=True
scope['stage_exit_credit_allowed']=False
scope['closure_status']='STAGE03_CLEAN_REEXECUTION_REQUIRED'
scope['next_action']='DELETE_STAGE03_GENERATED_OUTPUTS_AND_RUN_FRESH_STAGE03'
scope['denominator_source_refs']=[
 '.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',
 '00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/04_PAGE_FUNCTIONAL_CONTRACT/CURRENT_PROBLEM_REGISTER.yaml',
 '00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/04_PAGE_FUNCTIONAL_CONTRACT/DENOMINATOR_SNAPSHOT.yaml',
 '00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/02_BASE_BLUEPRINT/CORE-01/VISUAL_BASE_BLUEPRINT.yaml',
 'governance/test/ACTIVE_STATE.yaml'
]
scope['content_hash']=hobj(scope)
dump(SCOPE,scope)
print(json.dumps({'result':'PASS','closed_governance_work_unit':GOV_WU,'restored_product_work_unit':PRODUCT_WU,'resume_point':state['resume_control']['current_resume_point'],'required_operations':len(ops),'required_outputs':len(outputs)},indent=2))
