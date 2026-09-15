#!/usr/bin/env python3
from pathlib import Path
import sys
import yaml

ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'governance/test/stage02/STAGE02_FINDING_CREATE_CONTROL_TRIGGER_CANDIDATE_REVIEW_R32.yaml'

def die(m): print(f'BLOCK: {m}',file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die('R32_MAPPING_REQUIRED')
    return o

d=load(DOC)
if d.get('artifact_type')!='NON_NORMATIVE_STAGE02_FUNCTIONAL_CHAIN_PRODUCT_BEHAVIOR_CANDIDATE_REVIEW_R32' or d.get('stage_uid')!='STAGE-02' or d.get('normative_authority') is not False: die('R32_IDENTITY_DRIFT')
p=d.get('problem_identity') or {}
expected={'problem_uid':'STAGE02-FUNCTIONAL-REMEDIATION-032','blocker_uid':'STAGE02-R5-PRODUCT-AUTH-032','remediation_input_uid':'STAGE02-R27-INPUT-032','scope':'ASSET-01','category':'ACTION_WITHOUT_CONTROL_OR_TRIGGER','target_uid':'ASSET-01-ACT-FINDING-CREATE','owning_contract':'PAGE_CONTROL_OR_REGISTERED_TRIGGER_BINDING'}
for k,v in expected.items():
    if p.get(k)!=v: die(f'R32_PROBLEM_IDENTITY_DRIFT:{k}:{p.get(k)}')
c=d.get('candidate_review_contract') or {}
for k in ('candidate_is_not_authority','candidate_may_not_reduce_blocker','candidate_may_not_create_canonical_uid','candidate_may_not_create_trigger_condition','two_or_more_reasonable_behaviors_without_unique_authority_proves_product_authority_decision_required','port_exposure_may_not_be_promoted_to_trigger','current_specification_mutation_forbidden','stage1_raw_mutation_forbidden'):
    if c.get(k) is not True: die(f'R32_REVIEW_CONTRACT_DRIFT:{k}')
f=d.get('functional_chain_evidence') or {}
if f.get('existing_exact_control_binding_count')!=0 or f.get('existing_exact_registered_trigger_count')!=0 or f.get('existing_nonqualifying_port_exposure_count')!=2: die('R32_EXISTING_BINDING_DENOMINATOR_DRIFT')
if f.get('finding_action_uid')!='ASSET-01-ACT-FINDING-CREATE' or f.get('finding_gate_uid')!='ASSET-01-GATE-EVALUATION' or f.get('finding_action_permission_uid')!='ASSET_CORRECT': die('R32_ACTION_CHAIN_DRIFT')
if f.get('finding_port_uid')!='ASSET-01-PORT-FINDING' or f.get('finding_operation')!='createFinding' or f.get('finding_method_path')!='POST /v1/findings' or f.get('finding_state_event')!='IN_REVIEW→FINDING_OPEN | finding.created': die('R32_PORT_CHAIN_DRIFT')
if f.get('finding_object_owner')!='ASSET/EVALUATION' or f.get('scorecard_contains_issues') is not True or f.get('evaluation_contains_evidence') is not True: die('R32_EVALUATION_CONTEXT_DRIFT')
rows=d.get('candidates') or []
if len(rows)!=2 or {x.get('behavior_kind') for x in rows}!={'MANUAL_UI_CONTROL_BINDING','AUTOMATIC_EVALUATION_SYSTEM_TRIGGER'}: die('R32_CANDIDATE_SET_DRIFT')
for row in rows:
    review=row.get('review') or {}
    if review.get('role_correct') is not True or review.get('upstream_context_available') is not True or review.get('gate_permission_alignment') is not True or review.get('runtime_port_continuity') is not True: die(f'R32_CANDIDATE_CHAIN_REVIEW_DRIFT:{row.get("candidate_uid")}')
    if review.get('uniquely_mandated_by_current_authority') is not False or review.get('candidate_status')!='REASONABLE_PRODUCT_BEHAVIOR_REQUIRES_AUTHORITY_SELECTION': die(f'R32_CANDIDATE_UNIQUENESS_DRIFT:{row.get("candidate_uid")}')
    invented=row.get('authority_values_not_invented') or {}
    if any(v is not None for v in invented.values()): die(f'R32_CANDIDATE_INVENTED_AUTHORITY_VALUE:{row.get("candidate_uid")}')
manual=next(x for x in rows if x.get('behavior_kind')=='MANUAL_UI_CONTROL_BINDING')
auto=next(x for x in rows if x.get('behavior_kind')=='AUTOMATIC_EVALUATION_SYSTEM_TRIGGER')
if (manual.get('review') or {}).get('requires_new_ui_design_authority') is not True: die('R32_MANUAL_DESIGN_AUTHORITY_BOUNDARY_DRIFT')
if (auto.get('review') or {}).get('requires_trigger_policy_authority') is not True: die('R32_AUTO_TRIGGER_POLICY_BOUNDARY_DRIFT')
r=d.get('review_result') or {}
if r.get('reasonable_candidate_count')!=2 or r.get('unique_minimal_behavior_proven') is not False: die('R32_REASONABLE_CANDIDATE_DENOMINATOR_DRIFT')
if r.get('exact_current_authority_selecting_manual') is not False or r.get('exact_current_authority_selecting_automatic') is not False: die('R32_PREMATURE_AUTHORITY_SELECTION')
if r.get('product_authority_decision_required') is not True or r.get('classification')!='AUTHORITY_GAP_MULTIPLE_REASONABLE_PRODUCT_BEHAVIORS': die('R32_AUTHORITY_GAP_CLASSIFICATION_DRIFT')
if r.get('owning_layer_contract_value_materialized') is not False or r.get('blocker_reduction_credit')!=0: die('R32_PREMATURE_MATERIALIZATION_DRIFT')
if d.get('product_behavior_selected_by_ai') is not False or d.get('current_specification_mutated') is not False or d.get('immutable_stage1_source_mutated') is not False: die('R32_SAFETY_FLAG_DRIFT')
if d.get('stage02_status')!='BLOCKED' or d.get('stage03_allowed') is not False or d.get('website_construction_allowed') is not False or d.get('deployment_allowed') is not False: die('R32_FAIL_CLOSED_DRIFT')
print('PASS: R32 two grounded product-behavior candidates validated; no AI selection or materialization')
print('BLOCKED: Finding Create control/trigger requires Product Authority decision')
