#!/usr/bin/env python3
from pathlib import Path
import copy, subprocess, yaml, json
ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
AUTH=ROOT/'governance/test/spec_change_authorizations/USR-DIRECTIVE-20260920-CROSS-STAGE-MATERIALIZATION-CONTINUITY-HARDENING-R1.yaml'
PRODUCT_WU='WU-STAGE03-CORE01-VISUAL-DESIGN-001'
GOV_WU='WU-GOV-CROSS-STAGE-MATERIALIZATION-CONTINUITY-HARDENING-001'
OLD_GOV='GOV-REV-20260920-STAGE03-VISUAL-MATERIALIZATION-PROMOTION-CLOSURE'
AUTH_UID='USR-DIRECTIVE-20260920-CROSS-STAGE-MATERIALIZATION-CONTINUITY-HARDENING-R1'
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def dump(p,o): p.write_text(yaml.safe_dump(o,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
s=load(STATE); a=load(AUTH)
if a.get('artifact_uid')!=AUTH_UID or a.get('status')!='AUTHORIZED_EXACT_SCOPE':
    raise SystemExit('BLOCK: authorization receipt missing or invalid')
if s.get('specification_uid')!=OLD_GOV:
    raise SystemExit('BLOCK: current governance drift')
aw=s.get('active_work_unit') or {}
if s.get('current_primary_task_layer')!='PRODUCT_STAGE_EXECUTION' or aw.get('work_unit_uid')!=PRODUCT_WU:
    raise SystemExit('BLOCK: expected Stage-03 product WU not active')
if aw.get('current_status')!='PENDING_HUMAN_VISUAL_REVIEW':
    raise SystemExit('BLOCK: expected review-pending product boundary')
s['suspended_product_work_unit_for_cross_stage_governance_hardening']=copy.deepcopy(aw)
s['suspended_product_resume_for_cross_stage_governance_hardening']=copy.deepcopy(s.get('resume_control') or {})
s['suspended_product_state_for_cross_stage_governance_hardening']={
  'status':s.get('status'),'next_action':s.get('next_action'),
  'current_primary_task_authorization_uid':s.get('current_primary_task_authorization_uid'),
  'current_primary_task_product_stage_credit':s.get('current_primary_task_product_stage_credit',0)
}
wur={
 'resolution_uid':'WUR-GOV-CROSS-STAGE-MATERIALIZATION-CONTINUITY-HARDENING-001',
 'normative_authority':False,'result':'PASS_SINGLE_LEGAL_SUCCESSOR',
 'requested_primary_task_layer':'GOVERNANCE_MAINTENANCE',
 'resolved_work_unit_uid':GOV_WU,'authorization_uid':AUTH_UID,
 'source_product_work_unit_uid':PRODUCT_WU,
 'basis':['EXPLICIT_USER_DIRECTIVE','CURRENT_STAGE03_FALSE_REVIEW_READINESS_EVIDENCE','STAGE01_REFERENCE_ONLY_ANCHOR_CANDIDATE_CAPTURE','STAGE02_SUCCESSOR_READINESS_DENOMINATOR_OMISSION','ELEVEN_STAGE_COMMON_HANDOFF_RULE_ABSENCE'],
 'product_stage_credit':0
}
s['last_work_unit_resolution_gate']=wur
s['work_unit_resolution_gate_cross_stage_materialization_hardening']=wur
s['active_work_unit']={
 'work_unit_uid':GOV_WU,
 'canonical_name':'CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS_HARDENING',
 'primary_task_layer':'GOVERNANCE_MAINTENANCE',
 'canonical_owner':'governance/specifications/current/SPECIFICATION_MUTATION_CONTROL.yaml',
 'authorization_uid':AUTH_UID,
 'current_status':'ACTIVE_AUTHORIZED_SUCCESSOR_PREPARATION',
 'scope':a.get('authorized_scope') or [],
 'out_of_scope':a.get('forbidden_scope') or [],
 'definition_of_done':[
  'MOTHER_01_02_03_04_HARDENED',
  'ALL_11_STAGE_LIFECYCLE_ENTRIES_BIND_CROSS_STAGE_HANDOFF_INVARIANT',
  'STAGE_EXECUTION_INVARIANT_REGISTRY_HARDENED',
  'ACCEPTANCE_AUDIT_BLUEPRINT_AND_AUDIT_CATALOG_HARDENED',
  'REUSABLE_VALIDATOR_AND_STAGE_ENGINE_ENFORCE_REFERENCE_MATERIALIZATION_COMPLETENESS_READINESS',
  'NEGATIVE_REGRESSION_REFERENCE_ONLY_FALSE_PASS_BLOCKED',
  'PERSISTED_SUCCESSOR_GOVERNANCE_UID_AND_REGISTRY_MANIFEST_UPDATED_ATOMICALLY',
  'FULL_LINE_AND_SELECTED_PROFILE_EXACT_HEAD_PASS',
  'AFFECTED_PRODUCT_STAGE03_MARKED_REVERIFY_REQUIRED'
 ],
 'product_stage_credit':0
}
s['current_primary_task_layer']='GOVERNANCE_MAINTENANCE'
s['current_primary_task_authorization_uid']=AUTH_UID
s['current_primary_task_product_stage_credit']=0
s['status']='ACTIVE_GOVERNANCE_CROSS_STAGE_MATERIALIZATION_CONTINUITY_HARDENING'
s['next_action']='PROMOTE_V2_2_16_CROSS_STAGE_MATERIALIZATION_CONSUMER_READINESS_HARDENING'
s['resume_control']={
 'current_resume_point':'GOV_CROSS_STAGE_MATERIALIZATION_HARDENING_AUTHORIZED',
 'current_work_unit_uid':GOV_WU,
 'current_owner':'governance/specifications/current/SPECIFICATION_MUTATION_CONTROL.yaml',
 'exact_next_action':'PROMOTE_V2_2_16_CROSS_STAGE_MATERIALIZATION_CONSUMER_READINESS_HARDENING',
 'suspended_product_work_unit_uid':PRODUCT_WU,
 'suspended_product_resume_point':'STAGE3_CORE01_VISUAL_REVIEW_PENDING'
}
dump(STATE,s)
print(json.dumps({'result':'PASS','active_work_unit':GOV_WU,'product_stage_credit':0},indent=2))
