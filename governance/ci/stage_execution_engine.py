#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'governance/specifications/REGISTRY.yaml'
LIFECYCLE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
ADAPTERS=ROOT/'governance/ci/stage_execution_semantic_adapters.yaml'
INVARIANTS=ROOT/'.github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'
PRODUCT_ROOT_ENV='ACPOS_PRODUCT_ROOT'
ACTIVE_WORK_UNIT_ENV='ACPOS_ACTIVE_WORK_UNIT'
CURRENT_SCOPE_ENV='ACPOS_CURRENT_SCOPE'

EXPECTED_PHASES=[
'SESSION_BOOTSTRAP_RESUME_GATE','CURRENT_GOVERNANCE','CURRENT_SCOPE','WORK_UNIT','AUTHORITY','APPLICABILITY','DEPENDENCY',
'REQUIRED_FIELD_MANIFEST','STAGE_INPUT_CONTRACT','STAGE_OPERATIONS','OUTPUT_PRODUCER','CURRENT_PROBLEM_REGISTER',
'DENOMINATOR_SNAPSHOT','CHANGE_IMPACT','RESOLUTION_LEDGER','FRESH_EXECUTION','STAGE_SPECIFIC_SCANNER','GAP_CLASSIFICATION',
'OWNER_REMEDIATION','FRESH_REEXECUTION','HIDDEN_DEFECT_SWEEP','REQUIRED_EVIDENCE','EXACT_HEAD_GATES','TERMINAL_CLOSURE',
'PERSIST_RESUME','NEXT_STAGE']
REQUIRED_PREFLIGHT={'REQUIRED_FIELD_MANIFEST','FUNCTIONAL_CHAIN_MANIFEST','EFFECTIVE_CONTRACT_OVERLAY','DEPENDENCY_TOPOLOGY','DENOMINATOR_SNAPSHOT','CLASSIFICATION_RULESET','CHANGE_IMPACT_MAP','STAGE_EXECUTION_PREFLIGHT_RECEIPT'}
ROUTE_KEYS={'GOVERNANCE_DEFECT','AUTHORITY_GAP','PRODUCT_CONTRACT_GAP','RUNTIME_IMPLEMENTATION_GAP','EVIDENCE_STATE_GAP','EXTERNAL_AUTHORITY_GAP'}
EVIDENCE_FIELDS={'actual_stage_execution_completed','actual_stage_execution_started','artifact_type','attempt_uid','closure_blockers','cross_stage_handoff','current_specification_mutated','denominator','exact_head_gate_receipts','fresh_execution','gaps','governance_uid','hidden_defect_sweep','next_stage_transition','operation_results','output_results','phase_trace','prior_results_used','remediation','required_evidence','result','resume_persistence','scanner_results','scope_manifest_ref','source_head_sha','stage_exit_allowed','stage_uid','validator_results'}
PHASE_TERMINAL_STATUSES={'PASS','BLOCKED','NOT_APPLICABLE_WITH_PROOF','NOT_EXECUTED_AFTER_BLOCK'}
RESULT_TERMINAL_STATUSES={'PASS','BLOCKED','NOT_APPLICABLE_WITH_PROOF'}

class StageEngineError(RuntimeError): pass
def fail(msg): raise StageEngineError(msg)
def _display_path(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)
def y(path):
    if not path.is_file(): fail(f'MISSING_FILE:{_display_path(path)}')
    obj=yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(obj,dict): fail(f'MAPPING_REQUIRED:{_display_path(path)}')
    return obj
def j(path):
    if not path.is_file(): fail(f'MISSING_FILE:{_display_path(path)}')
    obj=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj,dict): fail(f'MAPPING_REQUIRED:{_display_path(path)}')
    return obj
def identity():
    reg=y(REGISTRY)
    spec_root=str(reg.get('rules_root') or '')
    if not spec_root: fail('REGISTRY_RULES_ROOT_MISSING')
    manifest_path=ROOT/spec_root/'SPECIFICATION_MANIFEST.yaml'
    manifest=y(manifest_path)
    gov=str(manifest.get('artifact_uid') or '')
    if not gov: fail('CURRENT_GOVERNANCE_UID_MISSING')
    if reg.get('lifecycle_registry')!=str(LIFECYCLE.relative_to(ROOT)): fail('SELECTED_PROFILE_REGISTRY_DRIFT')
    if (manifest.get('resolution_contract') or {}).get('canonical_root')!=spec_root: fail('CURRENT_SPECIFICATION_ROOT_DRIFT')
    return manifest,reg,gov
def data():
    entry,reg,gov=identity()
    return entry,reg,gov,y(LIFECYCLE),y(ADAPTERS)

def _external_yaml(path,label):
    if not path.is_file(): fail(label+'_MISSING:'+str(path))
    obj=yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(obj,dict): fail(label+'_MAPPING_REQUIRED')
    return obj

def _product_artifact_root():
    raw=os.environ.get(PRODUCT_ROOT_ENV,'').strip()
    root=Path(raw).resolve() if raw else ROOT
    if not root.is_dir(): fail('PRODUCT_EXECUTION_ROOT_MISSING')
    return root

def product_execution_context():
    root_raw=os.environ.get(PRODUCT_ROOT_ENV,'').strip()
    work_rel=os.environ.get(ACTIVE_WORK_UNIT_ENV,'').strip()
    scope_rel=os.environ.get(CURRENT_SCOPE_ENV,'').strip()
    if not root_raw or not work_rel or not scope_rel:
        fail('PRODUCT_EXECUTION_CONTEXT_ENV_REQUIRED')
    product_root=Path(root_raw).resolve()
    if not product_root.is_dir(): fail('PRODUCT_EXECUTION_ROOT_MISSING')
    def resolve_rel(rel,label):
        p=Path(rel)
        if p.is_absolute() or '..' in p.parts: fail(label+'_PATH_INVALID')
        return product_root/p
    work_path=resolve_rel(work_rel,'ACTIVE_WORK_UNIT')
    scope_path=resolve_rel(scope_rel,'CURRENT_SCOPE')
    return product_root,_external_yaml(work_path,'ACTIVE_WORK_UNIT'),_external_yaml(scope_path,'CURRENT_SCOPE'),work_rel,scope_rel
def stage_map(profile):
    rows=profile.get('stages') or []
    if not isinstance(rows,list) or not rows: fail('PROFILE_STAGES_EMPTY')
    out={}
    for row in rows:
        if not isinstance(row,dict) or not row.get('stage_uid'): fail('PROFILE_STAGE_RECORD_INVALID')
        uid=str(row['stage_uid'])
        if uid in out: fail(f'PROFILE_STAGE_DUPLICATE:{uid}')
        out[uid]=row
    return out

def validate_definition_data(profile,adapters):
    stages=stage_map(profile)
    if int(profile.get('profile_local_denominator') or -1)!=len(stages): fail('PROFILE_DENOMINATOR_DRIFT')
    common=adapters.get('common_execution_skeleton') or {}
    if common.get('phases')!=EXPECTED_PHASES or int(common.get('phase_count') or -1)!=len(EXPECTED_PHASES): fail('COMMON_EXECUTION_SKELETON_DRIFT')
    phase_contracts=common.get('phase_contracts') or {}
    if set(phase_contracts)!=set(EXPECTED_PHASES): fail('COMMON_PHASE_CONTRACT_DENOMINATOR_DRIFT')
    for ph in EXPECTED_PHASES:
        contract=phase_contracts.get(ph)
        if not isinstance(contract,dict) or not contract.get('required_artifact') or not contract.get('pass_condition'):
            fail(f'COMMON_PHASE_CONTRACT_INVALID:{ph}')
    req=adapters.get('common_requirements') or {}
    expected={
      'definition_audit_may_claim_product_completion':False,'governance_maintenance_product_stage_credit':0,
      'actual_product_execution_requires_active_product_work_unit':True,'fresh_execution_required':True,
      'prior_result_may_replace_fresh_execution':False,'fresh_reexecution_after_remediation_required':True,
      'hidden_defect_sweep_required':True,'required_evidence_presence_only_is_pass':False,
      'exact_head_outer_terminal_conclusion_required':True,'stage_exit_requires_zero_open_gap_zero_blocker_zero_remaining_scope':True,
      'missing_stage_specific_scanner_contract':'BLOCK','missing_semantic_adapter':'BLOCK','missing_product_evidence_in_execution_mode':'BLOCK',
      'downstream_owned_gap_requires_owner_reentry':True,'phase_trace_exact_order_required':True,
      'phase_trace_terminal_status_required':True,'operation_result_coverage_required':True,'output_result_coverage_required':True,
      'scanner_result_coverage_required':True,'validator_result_coverage_required':True,
      'remediation_reexecution_pair_required_when_gap_found':True,'zero_gap_remediation_may_be_not_applicable_with_proof':True,
      'hidden_defect_sweep_after_reexecution_required':True,'terminal_closure_requires_exact_head_gate_receipts':True,
      'persist_resume_before_next_stage_required':True,'next_stage_must_match_profile':True}
    for k,v in expected.items():
        if req.get(k)!=v: fail(f'COMMON_REQUIREMENT_DRIFT:{k}')
    if set(adapters.get('owner_remediation_routes') or {})!=ROUTE_KEYS: fail('OWNER_REMEDIATION_ROUTE_DENOMINATOR_DRIFT')
    driver=adapters.get('execution_driver_contract') or {}
    expected_driver={
      'driver_binding_source':'ACTIVE_WORK_UNIT','operation_universe_source':'SELECTED_PROFILE_STAGE_OPERATIONS',
      'output_producer_source':'SELECTED_PROFILE_STAGE_OUTPUT_PRODUCERS','semantic_adapter_source':'STAGE_EXECUTION_SEMANTIC_ADAPTER_REGISTRY',
      'scanner_universe_source':'STAGE_SEMANTIC_ADAPTER_SCANNER_DIMENSIONS','exact_operation_binding_coverage_required':True,
      'exact_scanner_binding_coverage_required':True,'executor_owner_required_per_operation':True,'result_owner_required_per_operation':True,
      'scanner_owner_required_per_dimension':True,'arbitrary_shell_command_from_adapter':'FORBIDDEN',
      'unregistered_operation_execution':'BLOCK','unregistered_scanner_execution':'BLOCK',
      'missing_operation_binding':'BLOCK','missing_scanner_binding':'BLOCK',
      'operation_executor_protocol_required':True,
      'allowed_operation_executor_protocols':['PYTHON_STAGE_OPERATION_V1'],
      'operation_receipt_ref_required_per_operation':True,
      'operation_receipt_status_required':'PASS',
      'operation_execution_unit':'ONE_OPERATION_PER_ENGINE_INVOCATION',
      'operation_checkpoint_after_pass_required':True,
      'stage_closure_may_be_auto_claimed_by_operation_executor':False}
    for k,v in expected_driver.items():
        if driver.get(k)!=v: fail(f'EXECUTION_DRIVER_CONTRACT_DRIFT:{k}')
    ads=adapters.get('stages') or {}
    if set(ads)!=set(stages): fail('SEMANTIC_ADAPTER_DENOMINATOR_DRIFT')
    if adapters.get('derived_from_profile_uid')!=profile.get('profile_uid'): fail('SEMANTIC_ADAPTER_PROFILE_UID_DRIFT')
    scalars=('stage_uid','name','scope_mode','entry_gate','exit_gate','next_stage_uid','pre_execution_gate')
    for uid,st in stages.items():
        for f in scalars:
            if not st.get(f): fail(f'STAGE_FIELD_MISSING:{uid}:{f}')
        for f in ('inputs','operations','outputs','validators','required_evidence','required_normative_section_uids'):
            vals=st.get(f)
            if not isinstance(vals,list) or not vals or len(vals)!=len(set(map(str,vals))): fail(f'STAGE_LIST_INVALID:{uid}:{f}')
        ins=list(map(str,st['inputs'])); origins=st.get('input_origins') or {}
        if not isinstance(origins,dict) or set(origins)!=set(ins): fail(f'STAGE_INPUT_ORIGIN_COVERAGE_INVALID:{uid}')
        outs=list(map(str,st['outputs'])); ops=set(map(str,st['operations'])); producers=st.get('output_producers') or {}
        if not isinstance(producers,dict) or set(producers)!=set(outs): fail(f'STAGE_OUTPUT_PRODUCER_COVERAGE_INVALID:{uid}')
        bad=sorted(set(map(str,producers.values()))-ops)
        if bad: fail(f'STAGE_OUTPUT_PRODUCER_NOT_OPERATION:{uid}:{bad}')
        if st.get('pre_execution_gate')!='GOVERNANCE_LOAD_RECEIPT_PASS': fail(f'STAGE_PREEXECUTION_GATE_DRIFT:{uid}')
        if uid=='STAGE-01':
            pg=st.get('pre_stage_source_projection_admission_gate') or {}
            if pg.get('required') is not True or pg.get('evaluation_boundary')!='BEFORE_PRODUCT_STAGE01_WORK_UNIT_ACTIVATION' or pg.get('freeze_state')!='SOURCE_PAIR_FROZEN' or pg.get('validator_uid')!='VAL-GOV-026':
                fail('PRE_STAGE_SOURCE_PROJECTION_GATE_INVALID')
        if (st.get('semantic_granularity_gate') or {}).get('mode')!='REQUIRED': fail(f'SEMANTIC_GRANULARITY_GATE_MISSING:{uid}')
        if (st.get('closure_evidence_continuity_gate') or {}).get('mode')!='REQUIRED': fail(f'CLOSURE_EVIDENCE_CONTINUITY_GATE_MISSING:{uid}')
        opt=st.get('canonical_execution_optimization_gate') or {}
        if opt.get('required') is not True or set(opt.get('preflight_manifest_set') or [])!=REQUIRED_PREFLIGHT: fail(f'CANONICAL_EXECUTION_GATE_DRIFT:{uid}')
        for k in ('one_current_problem_register_required','append_only_resolution_ledger_required','dependency_ordered_batches_required','incremental_impact_validation_required','checkpoint_full_sweep_required','engine_defect_requires_common_engine_repair_and_replay','explicit_stage_binding_required'):
            if opt.get(k) is not True: fail(f'CANONICAL_EXECUTION_FLAG_MISSING:{uid}:{k}')
        if st.get('work_unit_scope_source')!='CURRENT_EXECUTION_SCOPE_MANIFEST': fail(f'WORK_UNIT_SCOPE_SOURCE_DRIFT:{uid}')
        if st.get('stage_exit_scope_source')!='CURRENT_GOVERNED_UNIT_STAGE_REQUIRED_UNIVERSE_RECONCILIATION': fail(f'STAGE_EXIT_SCOPE_SOURCE_DRIFT:{uid}')
        if st.get('lifecycle_owner_granularity')!='PAGE_OR_SYSTEM_LOGIC_UNIT': fail(f'LIFECYCLE_OWNER_GRANULARITY_DRIFT:{uid}')
        if st.get('unrelated_same_stage_units_may_block_current_unit_exit') is not False: fail(f'UNRELATED_SAME_STAGE_UNIT_BARRIER_DRIFT:{uid}')
        if st.get('cross_unit_blocking_requires_explicit_required_dependency_edge') is not True: fail(f'CROSS_UNIT_DEPENDENCY_EDGE_RULE_DRIFT:{uid}')
        if st.get('partial_work_unit_closure_may_grant_stage_exit') is not False: fail(f'PARTIAL_STAGE_EXIT_CREDIT_NOT_BLOCKED:{uid}')
        ad=ads[uid]
        if ad.get('profile_name')!=st.get('name'): fail(f'ADAPTER_PROFILE_NAME_DRIFT:{uid}')
        if ad.get('effectful_executor_owner_resolution')!='CURRENT_WORK_UNIT_OPERATION_BINDING_ONLY':
            fail(f'ADAPTER_EFFECTFUL_EXECUTOR_OWNER_RESOLUTION_DRIFT:{uid}')
        for f in ('semantic_dimensions','scanner_dimensions'):
            vals=ad.get(f)
            if not isinstance(vals,list) or not vals or len(vals)!=len(set(map(str,vals))): fail(f'ADAPTER_DIMENSIONS_INVALID:{uid}:{f}')
        if not ad.get('denominator_kind'): fail(f'ADAPTER_DENOMINATOR_KIND_MISSING:{uid}')
        if ad.get('scanner_mode') not in {'NORMALIZED_COMMON_EVIDENCE_CONTRACT','SPECIALIZED_COMPATIBILITY_PLUS_NORMALIZED_COMMON'}: fail(f'ADAPTER_SCANNER_MODE_INVALID:{uid}')
        if ad.get('product_completion_credit_from_definition_audit')!=0: fail(f'DEFINITION_AUDIT_PRODUCT_CREDIT_LEAK:{uid}')
        if ad.get('business_entity_gate_required') is True and not isinstance(st.get('business_entity_completeness_gate'),dict): fail(f'BUSINESS_ENTITY_GATE_REQUIRED_BUT_MISSING:{uid}')
    for _sid,_stage in stages.items():
        _gate=_stage.get('cross_stage_materialization_gate') or {}
        if _gate.get('required') is not True or _gate.get('invariant_uid')!='GOV-INV-CROSS-STAGE-MATERIALIZATION-CONSUMER-READINESS-001':
            fail(f'CROSS_STAGE_GATE_INVALID:{_sid}')
        for _k in ('reference_resolution_required','physical_materialization_required','parse_schema_required_field_completeness_required','denominator_inclusion_required','successor_consumer_readiness_required','successor_required_input_reconciliation_before_exit'):
            if _gate.get(_k) is not True:
                fail(f'CROSS_STAGE_GATE_FLAG_MISSING:{_sid}:{_k}')
        if _gate.get('reference_only_completion_credit')!=0:
            fail(f'CROSS_STAGE_REFERENCE_ONLY_CREDIT_LEAK:{_sid}')
    for uid,st in stages.items():
        nxt=str(st.get('next_stage_uid') or '')
        if nxt in stages:
            predecessor_exit=str(st.get('exit_gate') or '')
            successor_entry=str(stages[nxt].get('entry_gate') or '')
            exact_or_stricter=(
                successor_entry==predecessor_exit
                or successor_entry.startswith(predecessor_exit+'_AND_')
            )
            if not exact_or_stricter:
                fail(f'SUCCESSOR_GATE_MISMATCH:{uid}->{nxt}:{predecessor_exit}:{successor_entry}')
    return stages

def validate_definition():
    entry,reg,gov,profile,adapters=data()
    stages=validate_definition_data(profile,adapters)
    validate_current_ledger_synchronization_contract()
    return entry,reg,gov,profile,adapters,stages

def resolve_stage_range(start_stage_uid,end_stage_uid):
    _,_,_,_,_,stages=validate_definition()
    order=list(stages)
    if start_stage_uid not in stages: fail('RANGE_START_NOT_REGISTERED:'+str(start_stage_uid))
    if end_stage_uid not in stages: fail('RANGE_END_NOT_REGISTERED:'+str(end_stage_uid))
    start=order.index(start_stage_uid); end=order.index(end_stage_uid)
    if start>end: fail('RANGE_ORDER_INVALID:'+str(start_stage_uid)+'>'+str(end_stage_uid))
    selected=order[start:end+1]
    if not selected: fail('RANGE_EMPTY')
    return selected

def plan_range(start_stage_uid,end_stage_uid):
    selected=resolve_stage_range(start_stage_uid,end_stage_uid)
    plans=[plan(uid) for uid in selected]
    return {
      'artifact_type':'COMMON_STAGE_RANGE_EXECUTION_PLAN',
      'normative_authority':False,
      'requested_start_stage_uid':start_stage_uid,
      'requested_end_stage_uid':end_stage_uid,
      'range_is_inclusive':True,
      'selected_stage_uids':selected,
      'selected_stage_count':len(selected),
      'system_selected_batch_size':False,
      'normal_stage_pass_behavior':'AUTO_CONTINUE_WITHIN_REQUESTED_RANGE',
      'normal_stage_boundary_user_prompt':'FORBIDDEN',
      'stop_conditions':['FORMAL_HUMAN_APPROVAL_REQUIRED','USER_DECISION_REQUIRED','BLOCKED','CURRENT_STATE_CONFLICT','REVERIFY_REQUIRED','SNAPSHOT_INVALIDATED','EXECUTION_FAILURE'],
      'plans':plans,
      'product_execution_credit':0
    }

def _deterministic_stage_audit_contract():
    inv=(y(INVARIANTS).get('invariants') or {}).get('DETERMINISTIC_STAGE_AUDIT') or {}
    if inv.get('invariant_uid')!='GOV-INV-DETERMINISTIC-STAGE-AUDIT-001':
        fail('DETERMINISTIC_STAGE_AUDIT_CONTRACT_MISSING')
    return inv

def validate_current_ledger_synchronization_contract():
    contract=_deterministic_stage_audit_contract().get('current_ledger_synchronization') or {}
    expected={
      'EXECUTION_STATE','RUN_MANIFEST','ARTIFACT_PLAN','GOVERNANCE_CURRENT','BRANCH_BASELINE',
      'GOVERNANCE_STAGE_LOCK','STAGE_EVIDENCE','DEPENDENCY_INDEX','REVERSE_DEPENDENCY_INDEX'
    }
    actual=set(map(str,contract.get('ledgers') or []))
    if actual!=expected:
        fail('CURRENT_LEDGER_SYNCHRONIZATION_LEDGER_DENOMINATOR_DRIFT:expected='+repr(sorted(expected))+':actual='+repr(sorted(actual)))
    if str(contract.get('disagreement_finding') or '')!='CURRENT_LEDGER_SYNCHRONIZATION_DRIFT':
        fail('CURRENT_LEDGER_SYNCHRONIZATION_FINDING_DRIFT')
    return True

def validate_release_identity_continuity(records):
    contract=_deterministic_stage_audit_contract().get('release_identity_continuity') or {}
    required=list(map(str,contract.get('required_chain') or []))
    finding=str(contract.get('broken_chain_finding') or 'RELEASE_IDENTITY_CONTINUITY_BROKEN')
    if not required: fail('RELEASE_IDENTITY_CONTINUITY_CONTRACT_EMPTY')
    if not isinstance(records,dict): fail(finding+':CHAIN_MAPPING_REQUIRED')
    missing=[uid for uid in required if uid not in records]
    if missing: fail(finding+':MISSING:'+','.join(missing))
    identities=[]
    for uid in required:
        rec=records.get(uid)
        if not isinstance(rec,dict): fail(finding+':RECORD_MAPPING_REQUIRED:'+uid)
        rid=str(rec.get('release_identity') or '').strip()
        if not rid: fail(finding+':RELEASE_IDENTITY_MISSING:'+uid)
        identities.append(rid)
    if len(set(identities))!=1:
        fail(finding+':IDENTITY_DRIFT')
    return identities[0]

def validate_environment_evidence(evidence,required_environment):
    contract=_deterministic_stage_audit_contract().get('environment_evidence_separation') or {}
    allowed=set(map(str,contract.get('environments') or []))
    required=str(required_environment or '').strip()
    if required not in allowed: fail('ENVIRONMENT_REQUIREMENT_INVALID:'+required)
    if not isinstance(evidence,dict): fail('ENVIRONMENT_EVIDENCE_MAPPING_REQUIRED')
    observed=str(evidence.get('environment') or '').strip()
    if observed not in allowed: fail('ENVIRONMENT_EVIDENCE_IDENTITY_INVALID:'+observed)
    if observed!=required:
        fail('CROSS_ENVIRONMENT_SUBSTITUTION_BLOCKED:'+observed+'->'+required)
    return True

def validate_production_release_acceptance(deployment_record,acceptance_record):
    validate_environment_evidence(deployment_record,'PRODUCTION')
    validate_environment_evidence(acceptance_record,'PRODUCTION')
    deployed=str(deployment_record.get('release_identity') or '').strip()
    accepted=str(acceptance_record.get('release_identity') or '').strip()
    if not deployed or not accepted or deployed!=accepted:
        fail('PRODUCTION_RELEASE_IDENTITY_MISMATCH')
    return True

def validate_reverify_propagation(stage_statuses,impacted_predecessor_uid):
    contract=_deterministic_stage_audit_contract().get('reverify_propagation_contract') or {}
    allowed=set(map(str,contract.get('allowed_descendant_dispositions') or []))
    if not allowed: fail('REVERIFY_PROPAGATION_ALLOWED_DISPOSITIONS_EMPTY')
    _,_,_,_,_,stages=validate_definition()
    order=list(stages)
    impacted=str(impacted_predecessor_uid or '')
    if impacted not in stages: fail('REVERIFY_PROPAGATION_PREDECESSOR_NOT_REGISTERED:'+impacted)
    if not isinstance(stage_statuses,dict): fail('REVERIFY_PROPAGATION_STATUS_MAPPING_REQUIRED')
    for sid in order[order.index(impacted)+1:]:
        status=str(stage_statuses.get(sid) or '').strip()
        if status not in allowed:
            fail('DOWNSTREAM_UNCONDITIONAL_CURRENT_PASS_AFTER_IMPACTED_PREDECESSOR_REVERIFY:'+sid+':'+status)
    return True

def production_redeploy_acceptance_disposition(current_deployment_record,prior_acceptance_record):
    validate_environment_evidence(current_deployment_record,'PRODUCTION')
    validate_environment_evidence(prior_acceptance_record,'PRODUCTION')
    current=str(current_deployment_record.get('release_identity') or '').strip()
    prior=str(prior_acceptance_record.get('release_identity') or '').strip()
    if not current or not prior: fail('PRODUCTION_RELEASE_IDENTITY_MISSING')
    if current!=prior:
        contract=_deterministic_stage_audit_contract().get('environment_evidence_separation') or {}
        return str(contract.get('production_redeploy_invalidates_prior_release_acceptance') or 'REVERIFY_REQUIRED')
    return 'CURRENT'

def validate_vertical_scope_identity(stage_records):
    contract=_deterministic_stage_audit_contract().get('vertical_lifecycle_contract') or {}
    fields=list(map(str,contract.get('sticky_identity_fields') or []))
    finding=str(contract.get('drift_finding') or 'VERTICAL_SCOPE_IDENTITY_DRIFT')
    start=str(contract.get('applies_from_stage') or 'STAGE-05')
    end_stage=str(contract.get('applies_through_stage') or 'STAGE-11')
    _,_,_,_,_,stages=validate_definition()
    order=list(stages)
    if start not in stages or end_stage not in stages: fail('VERTICAL_SCOPE_STAGE_RANGE_INVALID')
    selected=order[order.index(start):order.index(end_stage)+1]
    if not isinstance(stage_records,dict): fail(finding+':STAGE_RECORD_MAPPING_REQUIRED')
    for sid in selected:
        if sid not in stage_records or not isinstance(stage_records[sid],dict):
            fail(finding+':STAGE_RECORD_MISSING:'+sid)
    for field in fields:
        values=[]
        for sid in selected:
            value=str(stage_records[sid].get(field) or '').strip()
            if not value: fail(finding+':FIELD_MISSING:'+sid+':'+field)
            values.append(value)
        if len(set(values))!=1: fail(finding+':'+field)
    return True

def validate_full_lifecycle_closure(stage_statuses,impacted_reverify_count,stage11_eligibility):
    contract=_deterministic_stage_audit_contract().get('full_lifecycle_closure_contract') or {}
    _,_,_,_,_,stages=validate_definition()
    if not isinstance(stage_statuses,dict): fail('FULL_LIFECYCLE_STAGE_STATUS_MAPPING_REQUIRED')
    if contract.get('all_registered_stages_must_close_under_current_governance') is True:
        for sid in stages:
            if str(stage_statuses.get(sid) or '')!='CLOSED_PASS':
                fail('FULL_LIFECYCLE_STAGE_NOT_CLOSED_PASS:'+sid+':'+str(stage_statuses.get(sid) or ''))
    required_reverify=int(contract.get('impacted_reverify_count_required') or 0)
    if int(impacted_reverify_count)!=required_reverify:
        fail('FULL_LIFECYCLE_IMPACTED_REVERIFY_NONZERO:'+str(impacted_reverify_count))
    if contract.get('next_page_or_project_completion_requires_registered_stage11_eligibility') is True:
        if not isinstance(stage11_eligibility,dict):
            fail('FULL_LIFECYCLE_STAGE11_ELIGIBILITY_RECORD_REQUIRED')
        if str(stage11_eligibility.get('operation_uid') or '')!='NEXT_PAGE_ELIGIBILITY_EVALUATE':
            fail('FULL_LIFECYCLE_STAGE11_ELIGIBILITY_OPERATION_INVALID')
        if not str(stage11_eligibility.get('result') or '').strip():
            fail('FULL_LIFECYCLE_STAGE11_ELIGIBILITY_RESULT_MISSING')
    return True

def plan(stage_uid):
    entry,reg,gov,profile,adapters,stages=validate_definition()
    if stage_uid not in stages: fail(f'UNKNOWN_STAGE:{stage_uid}')
    st,ad=stages[stage_uid],adapters['stages'][stage_uid]
    semantic_phases={'AUTHORITY','APPLICABILITY','REQUIRED_FIELD_MANIFEST','STAGE_INPUT_CONTRACT','STAGE_OPERATIONS','OUTPUT_PRODUCER','STAGE_SPECIFIC_SCANNER','GAP_CLASSIFICATION','OWNER_REMEDIATION','REQUIRED_EVIDENCE'}
    contracts=(adapters.get('common_execution_skeleton') or {}).get('phase_contracts') or {}
    return {'artifact_type':'COMMON_STAGE_EXECUTION_PLAN','normative_authority':False,'governance_uid':gov,'selected_profile_uid':profile.get('profile_uid'),'stage_uid':stage_uid,'stage_name':st.get('name'),'scope_mode':st.get('scope_mode'),'entry_gate':st.get('entry_gate'),'exit_gate':st.get('exit_gate'),'next_stage_uid':st.get('next_stage_uid'),'semantic_dimensions':ad.get('semantic_dimensions'),'scanner_dimensions':ad.get('scanner_dimensions'),'denominator_kind':ad.get('denominator_kind'),'operations':st.get('operations'),'outputs':st.get('outputs'),'output_producers':st.get('output_producers'),'validators':st.get('validators'),'required_evidence_types':st.get('required_evidence'),'phases':[{'ordinal':i+1,'phase_uid':ph,'executor_owner':'COMMON_STAGE_EXECUTION_ENGINE','semantic_owner':'STAGE_SEMANTIC_ADAPTER' if ph in semantic_phases else 'COMMON_STAGE_EXECUTION_ENGINE','required_artifact':contracts[ph]['required_artifact'],'pass_condition':contracts[ph]['pass_condition'],'definition_status':'BOUND'} for i,ph in enumerate(EXPECTED_PHASES)],'definition_audit_product_completion_credit':0}

def validate_stage01_source_projection_admission(work,stage):
    gate=stage.get('pre_stage_source_projection_admission_gate') or {}
    adm=work.get('source_projection_admission')
    if not isinstance(adm,dict): fail('STAGE01_SOURCE_PROJECTION_ADMISSION_BINDING_MISSING')
    applicability=adm.get('applicability')
    if applicability=='NOT_APPLICABLE_WITH_AUTHORITY':
        if not adm.get('authority_evidence_ref'): fail('STAGE01_SOURCE_PROJECTION_NA_AUTHORITY_MISSING')
        return True
    if applicability!='REQUIRED': fail('STAGE01_SOURCE_PROJECTION_APPLICABILITY_UNRESOLVED')
    bindings=adm.get('bindings')
    if not isinstance(bindings,list) or not bindings: fail('STAGE01_SOURCE_PROJECTION_BINDING_SET_MISSING')
    seen=set()
    required=['source_uid','freeze_receipt_ref','pair_hash','raw_source_sha256','projection_uid','projection_content_hash']
    for b in bindings:
        if not isinstance(b,dict) or list(b.keys())!=required: fail('STAGE01_SOURCE_PROJECTION_BINDING_SCHEMA_DRIFT')
        suid=str(b.get('source_uid') or '')
        if not suid or suid in seen: fail('STAGE01_SOURCE_PROJECTION_SOURCE_UID_INVALID:'+suid)
        seen.add(suid)
        rel=str(b.get('freeze_receipt_ref') or '')
        if not rel or rel.startswith('/') or '..' in Path(rel).parts: fail('STAGE01_SOURCE_PROJECTION_RECEIPT_REF_INVALID:'+suid)
        fp=ROOT/rel
        if not fp.is_file(): fail('STAGE01_SOURCE_PROJECTION_FREEZE_RECEIPT_MISSING:'+suid)
        fr=y(fp)
        if fr.get('artifact_type')!='SOURCE_PROJECTION_FREEZE_RECEIPT' or fr.get('source_uid')!=suid or fr.get('status')!='FROZEN_FOR_STAGE01' or fr.get('lock_state')!='SOURCE_PAIR_FROZEN' or fr.get('raw_source_writable') is not False or fr.get('projection_writable') is not False:
            fail('STAGE01_SOURCE_PROJECTION_FREEZE_RECEIPT_INVALID:'+suid)
        for k in ('pair_hash','raw_source_sha256','projection_uid','projection_content_hash'):
            if fr.get(k)!=b.get(k): fail('STAGE01_SOURCE_PROJECTION_BINDING_HASH_DRIFT:'+suid+':'+k)
    return True

def validate_work_unit_bindings(stage_uid,work,stages,adapters):
    if stage_uid not in stages: fail(f'UNKNOWN_STAGE:{stage_uid}')
    if not isinstance(work,dict): fail('ACTIVE_PRODUCT_WORK_UNIT_MISSING')
    if work.get('primary_task_layer')!='PRODUCT_STAGE_EXECUTION': fail('ACTIVE_WORK_UNIT_NOT_PRODUCT_STAGE_EXECUTION')
    if work.get('stage_uid')!=stage_uid: fail('ACTIVE_WORK_UNIT_STAGE_MISMATCH')
    if stage_uid=='STAGE-01': validate_stage01_source_projection_admission(work,stages[stage_uid])
    if str(work.get('current_status') or '').startswith('CLOSED'): fail('ACTIVE_PRODUCT_WORK_UNIT_ALREADY_CLOSED')
    req=set(map(str,work.get('required_outputs') or [])); prof=set(map(str,stages[stage_uid].get('outputs') or []))
    if req and not prof.issubset(req): fail('ACTIVE_WORK_UNIT_OUTPUT_DENOMINATOR_INCOMPLETE')
    op_bindings=work.get('operation_bindings')
    expected_ops=set(map(str,stages[stage_uid].get('operations') or []))
    if not isinstance(op_bindings,dict) or set(map(str,op_bindings))!=expected_ops:
        fail(f'ACTIVE_WORK_UNIT_OPERATION_BINDING_COVERAGE_INVALID:{stage_uid}')
    driver=adapters.get('execution_driver_contract') or {}
    allowed_protocols=set(map(str,driver.get('allowed_operation_executor_protocols') or []))
    for uid,binding in op_bindings.items():
        if not isinstance(binding,dict) or not binding.get('executor_owner') or not binding.get('result_owner') or not binding.get('executor_protocol') or not binding.get('operation_receipt_ref'):
            fail(f'ACTIVE_WORK_UNIT_OPERATION_BINDING_INVALID:{uid}')
        if str(binding.get('executor_protocol')) not in allowed_protocols:
            fail(f'ACTIVE_WORK_UNIT_OPERATION_EXECUTOR_PROTOCOL_INVALID:{uid}')
        for field,label in (('executor_owner','EXECUTOR_OWNER'),('operation_receipt_ref','OPERATION_RECEIPT_REF')):
            rel=Path(str(binding.get(field) or ''))
            if rel.is_absolute() or '..' in rel.parts:
                fail(f'ACTIVE_WORK_UNIT_{label}_PATH_INVALID:{uid}')
    scan_bindings=work.get('scanner_bindings')
    expected_scans=set(map(str,(adapters['stages'][stage_uid]).get('scanner_dimensions') or []))
    if not isinstance(scan_bindings,dict) or set(map(str,scan_bindings))!=expected_scans:
        fail(f'ACTIVE_WORK_UNIT_SCANNER_BINDING_COVERAGE_INVALID:{stage_uid}')
    for uid,binding in scan_bindings.items():
        if not isinstance(binding,dict) or not binding.get('scanner_owner') or not binding.get('result_owner'):
            fail(f'ACTIVE_WORK_UNIT_SCANNER_BINDING_INVALID:{uid}')
    return True

def _matrix_get(value,path_tokens):
    cur=value
    for tok in path_tokens:
        if isinstance(cur,dict):
            if tok not in cur: fail('NORMATIVE_MATRIX_REQUIRED_FIELD_MISSING:'+str(tok))
            cur=cur[tok]
        elif isinstance(cur,list):
            if not isinstance(tok,int) or tok<0 or tok>=len(cur): fail('NORMATIVE_MATRIX_FIELD_PATH_INDEX_INVALID:'+str(tok))
            cur=cur[tok]
        else:
            fail('NORMATIVE_MATRIX_FIELD_PATH_UNRESOLVABLE:'+str(tok))
    return cur

def _matrix_nonblank(value):
    if value is None: return False
    if isinstance(value,str): return bool(value.strip())
    if isinstance(value,(list,dict)): return len(value)>0
    return True

def validate_normative_execution_matrix(stage_uid,product_root,work,stage,gov):
    inv=y(INVARIANTS)
    policy=((inv.get('invariants') or {}).get('NORMATIVE_EXECUTION_MATRIX') or {})
    if policy.get('required_before_first_effectful_operation') is not True or policy.get('required_for_stage_or_capability_closure') is not True:
        fail('NORMATIVE_EXECUTION_MATRIX_POLICY_MISSING')
    rel=str(work.get('normative_execution_matrix_ref') or '')
    if not rel: fail('NORMATIVE_EXECUTION_MATRIX_REF_MISSING')
    rp=Path(rel)
    if rp.is_absolute() or '..' in rp.parts: fail('NORMATIVE_EXECUTION_MATRIX_REF_INVALID')
    path=product_root/rp
    matrix=_external_yaml(path,'NORMATIVE_EXECUTION_MATRIX')
    if matrix.get('artifact_type')!='NORMATIVE_EXECUTION_MATRIX': fail('NORMATIVE_EXECUTION_MATRIX_TYPE_INVALID')
    if matrix.get('stage_uid')!=stage_uid or matrix.get('work_unit_uid')!=work.get('work_unit_uid') or matrix.get('governance_uid')!=gov:
        fail('NORMATIVE_EXECUTION_MATRIX_IDENTITY_DRIFT')
    if matrix.get('status')!='PASS': fail('NORMATIVE_EXECUTION_MATRIX_NOT_PASS')
    rows=matrix.get('rows')
    if not isinstance(rows,list) or not rows: fail('NORMATIVE_EXECUTION_MATRIX_ROWS_EMPTY')
    required_row_fields=set(map(str,policy.get('matrix_row_required_fields') or []))
    seen=set(); section_uids=set(); artifact_types=set(); required_count=0; validator_bound=0; closure_bound=0
    for idx,row in enumerate(rows):
        if not isinstance(row,dict): fail(f'NORMATIVE_EXECUTION_MATRIX_ROW_INVALID:{idx}')
        missing=sorted(required_row_fields-set(row))
        if missing: fail(f'NORMATIVE_EXECUTION_MATRIX_ROW_FIELDS_MISSING:{idx}:{missing}')
        uid=str(row.get('matrix_row_uid') or '')
        if not uid or uid in seen: fail('NORMATIVE_EXECUTION_MATRIX_ROW_UID_INVALID:'+uid)
        seen.add(uid)
        section_uids.add(str(row.get('normative_section_uid') or ''))
        artifact_types.add(str(row.get('required_artifact_type') or ''))
        applicability=row.get('applicability')
        if applicability=='NOT_APPLICABLE_WITH_AUTHORITY':
            if not row.get('authority_evidence_ref'): fail('NORMATIVE_EXECUTION_MATRIX_NA_AUTHORITY_MISSING:'+uid)
            continue
        if applicability!='REQUIRED': fail('NORMATIVE_EXECUTION_MATRIX_APPLICABILITY_INVALID:'+uid)
        required_count+=1
        if row.get('validator_uid') and row.get('validator_check_id'): validator_bound+=1
        if row.get('closure_gate')==stage.get('exit_gate'): closure_bound+=1
        aref=str(row.get('artifact_ref') or '')
        ap=Path(aref)
        if not aref or ap.is_absolute() or '..' in ap.parts: fail('NORMATIVE_EXECUTION_MATRIX_ARTIFACT_REF_INVALID:'+uid)
        full=product_root/ap
        if not full.is_file(): fail('NORMATIVE_EXECUTION_MATRIX_ARTIFACT_MISSING:'+uid+':'+aref)
        if full.suffix.lower()=='.json':
            obj=json.loads(full.read_text(encoding='utf-8'))
        else:
            obj=yaml.safe_load(full.read_text(encoding='utf-8'))
        if not isinstance(obj,dict): fail('NORMATIVE_EXECUTION_MATRIX_ARTIFACT_MAPPING_REQUIRED:'+uid)
        fpath=row.get('field_path')
        if not isinstance(fpath,list) or not fpath: fail('NORMATIVE_EXECUTION_MATRIX_FIELD_PATH_INVALID:'+uid)
        val=_matrix_get(obj,fpath)
        if not _matrix_nonblank(val): fail('NORMATIVE_EXECUTION_MATRIX_REQUIRED_FIELD_BLANK:'+uid)
    required_sections=set(map(str,stage.get('required_normative_section_uids') or []))
    missing_sections=sorted(required_sections-section_uids)
    if missing_sections: fail('NORMATIVE_EXECUTION_MATRIX_SECTION_COVERAGE_MISSING:'+repr(missing_sections))
    required_artifacts=set(map(str,stage.get('outputs') or []))|set(map(str,stage.get('required_evidence') or []))
    missing_artifacts=sorted(required_artifacts-artifact_types)
    if missing_artifacts: fail('NORMATIVE_EXECUTION_MATRIX_ARTIFACT_COVERAGE_MISSING:'+repr(missing_artifacts))
    cov=matrix.get('coverage')
    if not isinstance(cov,dict): fail('NORMATIVE_EXECUTION_MATRIX_COVERAGE_MISSING')
    expected={
      'required_normative_section_total':len(required_sections),
      'represented_normative_section_total':len(required_sections & section_uids),
      'required_artifact_total':len(required_artifacts),
      'represented_artifact_total':len(required_artifacts & artifact_types),
      'required_field_total':required_count,
      'validator_bound_field_total':validator_bound,
      'closure_bound_field_total':closure_bound,
      'missing_required_row_count':0,
      'missing_required_field_count':0,
      'duplicate_credit_count':0,
      'summary_only_credit_count':0,
      'unclassified_applicability_count':0,
      'validator_unbound_count':0,
      'closure_unbound_count':0,
      'stale_matrix_count':0}
    for k,v in expected.items():
        if cov.get(k)!=v: fail(f'NORMATIVE_EXECUTION_MATRIX_COVERAGE_DRIFT:{k}:expected={v}:actual={cov.get(k)}')
    if required_count!=validator_bound or required_count!=closure_bound:
        fail('NORMATIVE_EXECUTION_MATRIX_BINDING_COVERAGE_INCOMPLETE')
    return True

def active_product(stage_uid):
    entry,reg,gov,profile,adapters,stages=validate_definition()
    product_root,work,scope,work_rel,scope_rel=product_execution_context()
    validate_work_unit_bindings(stage_uid,work,stages,adapters)
    if scope.get('stage_uid')!=stage_uid or scope.get('work_unit_uid')!=work.get('work_unit_uid'):
        fail('CURRENT_SCOPE_WORK_UNIT_BINDING_DRIFT')
    if scope.get('governance_uid') not in {None,gov}: fail('CURRENT_SCOPE_GOVERNANCE_UID_DRIFT')
    deps=work.get('dependencies') or []
    if not isinstance(deps,list) or not deps: fail('ACTIVE_PRODUCT_WORK_UNIT_DEPENDENCY_CLOSURE_MISSING')
    for dep in deps:
        if isinstance(dep,str) and '/' in dep and not (product_root/dep).exists():
            fail(f'ACTIVE_PRODUCT_WORK_UNIT_DEPENDENCY_MISSING:{dep}')
        if isinstance(dep,dict):
            ref=dep.get('ref') or dep.get('path') or dep.get('source_ref')
            if isinstance(ref,str) and '/' in ref and not (product_root/ref).exists():
                fail(f'ACTIVE_PRODUCT_WORK_UNIT_DEPENDENCY_MISSING:{ref}')
    validate_normative_execution_matrix(stage_uid,product_root,work,stages[stage_uid],gov)
    return work

def admission(stage_uid):
    work=active_product(stage_uid); pl=plan(stage_uid)
    print(f"PASS: common engine admission context resolved for {stage_uid} work_unit={work.get('work_unit_uid')}")
    print(f"PASS: common execution skeleton phases={len(pl['phases'])}/{len(EXPECTED_PHASES)}")
    print('PASS: admission check performs no product execution and grants zero completion credit')

def _result_map(rows,key,label):
    if not isinstance(rows,list): fail(f'{label}_INVALID')
    out={}
    for row in rows:
        if not isinstance(row,dict) or not row.get(key): fail(f'{label}_ROW_INVALID')
        uid=str(row[key])
        if uid in out: fail(f'{label}_DUPLICATE:{uid}')
        if row.get('status') not in RESULT_TERMINAL_STATUSES: fail(f'{label}_STATUS_INVALID:{uid}')
        out[uid]=row
    return out

def _validate_current_stage_state_bundle(stage_uid,e,stage,gov):
    scope_ref=str(e.get('scope_manifest_ref') or '')
    rp=Path(scope_ref)
    if not scope_ref or rp.is_absolute() or '..' in rp.parts:
        fail('EVIDENCE_SCOPE_MANIFEST_REF_INVALID')
    product_root=_product_artifact_root()
    scope_path=product_root/rp
    scope=_external_yaml(scope_path,'CURRENT_EXECUTION_SCOPE')
    if scope.get('stage_uid')!=stage_uid:
        fail('CURRENT_SCOPE_STAGE_IDENTITY_DRIFT')
    work_dir=scope_path.parent
    work=_external_yaml(work_dir/'WORK_UNIT.yaml','CURRENT_WORK_UNIT')
    state=_external_yaml(work_dir/'EXECUTION_STATE.yaml','CURRENT_EXECUTION_STATE')
    if work.get('stage_uid')!=stage_uid or state.get('stage_uid')!=stage_uid:
        fail('CURRENT_WORK_OR_STATE_STAGE_IDENTITY_DRIFT')
    if scope.get('work_unit_uid')!=work.get('work_unit_uid') or state.get('work_unit_uid')!=work.get('work_unit_uid'):
        fail('CURRENT_SCOPE_WORK_STATE_IDENTITY_DRIFT')
    validate_normative_execution_matrix(stage_uid,product_root,work,stage,gov)
    if e.get('result')=='PASS':
        expected=list(map(str,stage.get('operations') or []))
        completed=state.get('completed_operations')
        if not isinstance(completed,list):
            fail('CURRENT_STATE_COMPLETED_OPERATIONS_INVALID')
        completed=list(map(str,completed))
        if len(completed)!=len(expected) or set(completed)!=set(expected):
            fail('CURRENT_STATE_OPERATION_SET_CONFLICT:expected='+repr(expected)+':actual='+repr(completed))
        if str(state.get('status') or '') not in {'CLOSED','EXECUTION_COMPLETE_CLOSURE_PENDING'}:
            fail('CURRENT_STATE_STATUS_CONFLICT:'+str(state.get('status')))
        current_op=str(state.get('current_operation') or '')
        if current_op in set(expected) or 'READINESS' in current_op or 'PENDING' in current_op:
            fail('CURRENT_STATE_CURRENT_OPERATION_CONFLICT:'+current_op)
        work_status=str(work.get('current_status') or work.get('status') or '')
        if work_status not in {'CLOSED','EXECUTION_COMPLETE_CLOSURE_PENDING'}:
            fail('CURRENT_WORK_UNIT_STATUS_CONFLICT:'+work_status)
    return scope,work,state,work_dir

def _validate_cross_stage_handoff_ledger(stage_uid,e,stage,stages):
    inv=y(INVARIANTS)
    product_root=_product_artifact_root()
    policy=((inv.get('invariants') or {}).get('CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS') or {})
    handoff=e.get('cross_stage_handoff') or {}
    ref=str(handoff.get('ledger_ref') or '')
    if handoff.get('external_receipt'):
        fail('CROSS_STAGE_EXTERNAL_LEDGER_CANNOT_SKIP_EXECUTION_BINDING_RECONCILIATION')
    rp=Path(ref)
    if not ref or rp.is_absolute() or '..' in rp.parts:
        fail('CROSS_STAGE_HANDOFF_LEDGER_REF_INVALID')
    ledger=_external_yaml(product_root/rp,'CROSS_STAGE_HANDOFF_READINESS_LEDGER')
    if ledger.get('artifact_type')!='CROSS_STAGE_HANDOFF_READINESS_LEDGER':
        fail('CROSS_STAGE_HANDOFF_LEDGER_TYPE_INVALID')
    if ledger.get('stage_uid')!=stage_uid or ledger.get('successor_stage_uid')!=stage.get('next_stage_uid'):
        fail('CROSS_STAGE_HANDOFF_LEDGER_IDENTITY_DRIFT')
    pass_result=e.get('result')=='PASS'
    for key in ('current_matrix_valid','current_state_consistent','denominator_reconciled'):
        if ledger.get(key) is not True:
            fail('CROSS_STAGE_HANDOFF_LEDGER_CORE_INTEGRITY_INVALID:'+key)
    if pass_result:
        for key in ('reference_resolution_complete','physical_materialization_complete','required_field_completeness_complete','consumer_readiness_complete'):
            if ledger.get(key) is not True:
                fail('CROSS_STAGE_HANDOFF_LEDGER_NOT_READY:'+key)

    successor_uid=str(stage.get('next_stage_uid') or '')
    input_rows=ledger.get('successor_required_inputs')
    if not isinstance(input_rows,list):
        fail('CROSS_STAGE_SUCCESSOR_INPUT_ROWS_INVALID')
    seen_inputs={}
    for row in input_rows:
        if not isinstance(row,dict) or not row.get('input_uid') or row.get('input_uid') in seen_inputs:
            fail('CROSS_STAGE_SUCCESSOR_INPUT_ROW_INVALID')
        seen_inputs[str(row['input_uid'])]=row
    if successor_uid in stages:
        expected_inputs=set(map(str,stages[successor_uid].get('inputs') or []))
        if set(seen_inputs)!=expected_inputs:
            fail('CROSS_STAGE_SUCCESSOR_INPUT_DENOMINATOR_DRIFT:expected='+repr(sorted(expected_inputs))+':actual='+repr(sorted(seen_inputs)))
    unresolved_input_total=0
    for uid,row in seen_inputs.items():
        status=str(row.get('status') or '')
        if status=='AUTHORIZED_NOT_APPLICABLE':
            if not row.get('authority_evidence_ref'):
                fail('CROSS_STAGE_SUCCESSOR_INPUT_NA_AUTHORITY_MISSING:'+uid)
        elif status in {'MATERIALIZED','EXTERNAL_RECEIPT'}:
            pass
        elif not pass_result and status in {'UNRESOLVED','BLOCKED','MISSING'}:
            unresolved_input_total+=1
        else:
            fail('CROSS_STAGE_SUCCESSOR_INPUT_NOT_READY:'+uid+':'+status)

    requirements=(policy.get('successor_execution_binding_requirements') or {})
    operation_map=(policy.get('successor_execution_binding_operation_map') or {})
    if successor_uid in stages:
        expected_classes=list(map(str,requirements.get(successor_uid) or []))
        expected_map=operation_map.get(successor_uid) or {}
        successor_ops=set(map(str,stages[successor_uid].get('operations') or []))
    else:
        expected_classes=list(map(str,policy.get('next_page_successor_binding_requirements') or []))
        expected_map={}
        successor_ops=set()
    rows=ledger.get('successor_execution_bindings')
    if not isinstance(rows,list):
        fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDINGS_INVALID')
    required_fields=set(map(str,policy.get('successor_execution_binding_required_row_fields') or []))
    seen={}
    ready=0
    unresolved_binding_total=0
    for row in rows:
        if not isinstance(row,dict):
            fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_ROW_INVALID')
        missing=sorted(required_fields-set(row))
        if missing:
            fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_FIELDS_MISSING:'+repr(missing))
        cls=str(row.get('binding_class') or '')
        if not cls or cls in seen:
            fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_DUPLICATE_OR_BLANK:'+cls)
        seen[cls]=row
        op=str(row.get('consuming_operation_uid') or '')
        if successor_uid in stages:
            if cls in expected_map and op!=str(expected_map[cls]):
                fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_OPERATION_DRIFT:'+cls+':'+op)
            if op not in successor_ops:
                fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_OPERATION_UNKNOWN:'+cls+':'+op)
        applicability=str(row.get('applicability') or '')
        resolution=str(row.get('resolution_status') or '')
        if applicability=='REQUIRED':
            if resolution=='BOUND':
                for key in ('canonical_owner_or_authority_ref','authority_evidence_ref','target_identity'):
                    if not str(row.get(key) or '').strip():
                        fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_REQUIRED_VALUE_MISSING:'+cls+':'+key)
                if row.get('denominator_inclusion_status')!='INCLUDED' or row.get('consumer_readiness_status')!='READY':
                    fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_NOT_READY:'+cls)
                ready+=1
            elif not pass_result and resolution in {'UNRESOLVED','BLOCKED','MISSING'}:
                if row.get('denominator_inclusion_status')!='INCLUDED' or row.get('consumer_readiness_status') not in {'BLOCKED','NOT_READY'}:
                    fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_BLOCKED_ROW_INVALID:'+cls)
                unresolved_binding_total+=1
            else:
                fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_NOT_READY:'+cls)
        elif applicability=='AUTHORIZED_NOT_APPLICABLE':
            if not str(row.get('authority_evidence_ref') or '').strip():
                fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_NA_AUTHORITY_MISSING:'+cls)
            if resolution!='AUTHORIZED_NOT_APPLICABLE' or row.get('denominator_inclusion_status')!='INCLUDED' or row.get('consumer_readiness_status')!='NOT_APPLICABLE_WITH_AUTHORITY':
                fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_NA_INVALID:'+cls)
            ready+=1
        else:
            fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_APPLICABILITY_INVALID:'+cls)
    if set(seen)!=set(expected_classes):
        fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_DENOMINATOR_DRIFT:expected='+repr(sorted(expected_classes))+':actual='+repr(sorted(seen)))
    if ledger.get('successor_execution_binding_total')!=len(expected_classes):
        fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_TOTAL_DRIFT')
    if ledger.get('successor_execution_binding_ready_total')!=ready:
        fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_READY_TOTAL_DRIFT')
    if ledger.get('successor_execution_binding_unresolved_total')!=unresolved_binding_total:
        fail('CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_UNRESOLVED_TOTAL_DRIFT')
    if ledger.get('unresolved_required_dependency_total')!=unresolved_input_total:
        fail('CROSS_STAGE_SUCCESSOR_INPUT_UNRESOLVED_TOTAL_DRIFT')
    if pass_result:
        if unresolved_binding_total!=0 or unresolved_input_total!=0 or ledger.get('status')!='PASS':
            fail('CROSS_STAGE_HANDOFF_PASS_WITH_UNRESOLVED')
    else:
        handoff_blocked=(unresolved_binding_total>0 or unresolved_input_total>0 or any(ledger.get(k) is not True for k in ('reference_resolution_complete','physical_materialization_complete','required_field_completeness_complete','consumer_readiness_complete')))
        expected_status='BLOCKED' if handoff_blocked else 'PASS'
        if ledger.get('status')!=expected_status:
            fail('CROSS_STAGE_HANDOFF_STATUS_RESULT_DRIFT:expected='+expected_status+':actual='+str(ledger.get('status')))
    return True

def validate_evidence_data(stage_uid,e):
    entry,reg,gov,profile,adapters,stages=validate_definition()
    if stage_uid not in stages: fail(f'UNKNOWN_STAGE:{stage_uid}')
    st=stages[stage_uid]; ad=adapters['stages'][stage_uid]
    missing=sorted(EVIDENCE_FIELDS-set(e))
    if missing: fail(f'NORMALIZED_EVIDENCE_FIELD_MISSING:{missing}')
    if e.get('governance_uid')!=gov or e.get('stage_uid')!=stage_uid: fail('EVIDENCE_IDENTITY_DRIFT')
    scope_ref=str(e.get('scope_manifest_ref') or '')
    if not scope_ref: fail('EVIDENCE_SCOPE_MANIFEST_REF_MISSING')
    if scope_ref.startswith('governance/test/'): fail('LEGACY_GOVERNANCE_TEST_SCOPE_REF_FORBIDDEN')
    _scope,_work,_state,_work_dir=_validate_current_stage_state_bundle(stage_uid,e,st,gov)
    if e.get('actual_stage_execution_started') is not True or e.get('actual_stage_execution_completed') is not True: fail('EVIDENCE_ACTUAL_EXECUTION_NOT_COMPLETE')
    if e.get('fresh_execution') is not True or e.get('prior_results_used') is not False: fail('EVIDENCE_FRESH_EXECUTION_PROVENANCE_INVALID')
    if e.get('current_specification_mutated') is not False: fail('EVIDENCE_CURRENT_SPECIFICATION_MUTATION_FORBIDDEN')
    head=str(e.get('source_head_sha') or '')
    if len(head)!=40 or any(ch not in '0123456789abcdef' for ch in head.lower()): fail('EVIDENCE_SOURCE_HEAD_SHA_INVALID')

    trace=e.get('phase_trace')
    if not isinstance(trace,list) or len(trace)!=len(EXPECTED_PHASES): fail('PHASE_TRACE_DENOMINATOR_DRIFT')
    seen=[]
    blocked_seen=False
    for idx,row in enumerate(trace):
        if not isinstance(row,dict) or row.get('phase_uid')!=EXPECTED_PHASES[idx]: fail(f'PHASE_TRACE_ORDER_DRIFT:{idx+1}')
        status=row.get('status')
        if status not in PHASE_TERMINAL_STATUSES: fail(f'PHASE_TRACE_STATUS_INVALID:{EXPECTED_PHASES[idx]}')
        if status=='NOT_APPLICABLE_WITH_PROOF' and not row.get('proof'): fail(f'PHASE_NA_PROOF_MISSING:{EXPECTED_PHASES[idx]}')
        if status=='BLOCKED': blocked_seen=True
        if status=='NOT_EXECUTED_AFTER_BLOCK' and not blocked_seen: fail(f'PHASE_NOT_EXECUTED_BEFORE_BLOCK:{EXPECTED_PHASES[idx]}')
        seen.append(status)

    ops=_result_map(e.get('operation_results'),'operation_uid','OPERATION_RESULTS')
    expected_ops=set(map(str,st.get('operations') or []))
    if set(ops)!=expected_ops: fail(f'OPERATION_RESULT_COVERAGE_DRIFT:expected={sorted(expected_ops)} actual={sorted(ops)}')
    outs=_result_map(e.get('output_results'),'output_uid','OUTPUT_RESULTS')
    expected_outs=set(map(str,st.get('outputs') or []))
    if set(outs)!=expected_outs: fail(f'OUTPUT_RESULT_COVERAGE_DRIFT:expected={sorted(expected_outs)} actual={sorted(outs)}')
    for uid,row in outs.items():
        if row.get('producer_operation_uid')!=str((st.get('output_producers') or {}).get(uid)): fail(f'OUTPUT_PRODUCER_RESULT_DRIFT:{uid}')
    scans=_result_map(e.get('scanner_results'),'scanner_dimension','SCANNER_RESULTS')
    expected_scans=set(map(str,ad.get('scanner_dimensions') or []))
    if set(scans)!=expected_scans: fail(f'SCANNER_RESULT_COVERAGE_DRIFT:expected={sorted(expected_scans)} actual={sorted(scans)}')
    vals=_result_map(e.get('validator_results'),'validator_uid','VALIDATOR_RESULTS')
    expected_vals=set(map(str,st.get('validators') or []))
    if set(vals)!=expected_vals: fail(f'VALIDATOR_RESULT_COVERAGE_DRIFT:expected={sorted(expected_vals)} actual={sorted(vals)}')

    d=e.get('denominator')
    if not isinstance(d,dict): fail('EVIDENCE_DENOMINATOR_INVALID')
    for k in ('required_total','open_gap_total','closure_blocker_total','remaining_scope_total'):
        if not isinstance(d.get(k),int) or d.get(k)<0: fail(f'EVIDENCE_DENOMINATOR_FIELD_INVALID:{k}')
    if not isinstance(e.get('gaps'),list) or len(e['gaps'])!=d['open_gap_total']: fail('EVIDENCE_OPEN_GAP_DENOMINATOR_DRIFT')
    if not isinstance(e.get('closure_blockers'),list) or len(e['closure_blockers'])!=d['closure_blocker_total']: fail('EVIDENCE_BLOCKER_DENOMINATOR_DRIFT')

    remediation=e.get('remediation')
    if not isinstance(remediation,dict): fail('REMEDIATION_RESULT_INVALID')
    for k in ('discovered_gap_total','remediated_gap_total','unresolved_gap_total'):
        if not isinstance(remediation.get(k),int) or remediation.get(k)<0: fail(f'REMEDIATION_FIELD_INVALID:{k}')
    if remediation['discovered_gap_total'] != remediation['remediated_gap_total'] + remediation['unresolved_gap_total']:
        fail('REMEDIATION_DENOMINATOR_DRIFT')
    if remediation['discovered_gap_total']>0:
        if remediation.get('reexecution_required') is not True or remediation.get('reexecution_performed') is not True:
            fail('REMEDIATION_FRESH_REEXECUTION_MISSING')
    else:
        if remediation.get('reexecution_required') not in {False,None}: fail('ZERO_GAP_REEXECUTION_REQUIREMENT_INVALID')
    sweep=e.get('hidden_defect_sweep')
    if not isinstance(sweep,dict) or sweep.get('performed') is not True or sweep.get('result') not in {'PASS','BLOCKED'}:
        fail('HIDDEN_DEFECT_SWEEP_INVALID')
    if not isinstance(sweep.get('discovered_defect_total'),int) or sweep['discovered_defect_total']<0: fail('HIDDEN_DEFECT_COUNT_INVALID')

    req=set(map(str,st.get('required_evidence') or [])); items=e.get('required_evidence')
    if not isinstance(items,list): fail('REQUIRED_EVIDENCE_LEDGER_INVALID')
    got={str(x.get('evidence_type')) for x in items if isinstance(x,dict)}
    if not req.issubset(got): fail(f'REQUIRED_EVIDENCE_TYPE_MISSING:{sorted(req-got)}')
    for item in items:
        if not isinstance(item,dict) or item.get('status')!='PASS' or not item.get('ref'): fail('REQUIRED_EVIDENCE_ITEM_INVALID')
        if not item.get('external_receipt') and not (_product_artifact_root()/str(item['ref'])).is_file(): fail(f'REQUIRED_EVIDENCE_PHYSICAL_REF_MISSING:{item["ref"]}')

    handoff=e.get('cross_stage_handoff')
    if not isinstance(handoff,dict):
        fail('CROSS_STAGE_HANDOFF_INVALID')
    required_handoff_fields={'ledger_ref','external_receipt','successor_stage_uid','reference_resolution_complete','physical_materialization_complete','required_field_completeness_complete','denominator_reconciled','consumer_readiness_complete','successor_execution_binding_total','successor_execution_binding_ready_total','successor_execution_binding_unresolved_total','current_matrix_valid','current_state_consistent','unresolved_required_dependency_total','status'}
    if not required_handoff_fields.issubset(handoff):
        fail('CROSS_STAGE_HANDOFF_FIELD_MISSING')
    if handoff.get('successor_stage_uid')!=st.get('next_stage_uid'):
        fail('CROSS_STAGE_HANDOFF_SUCCESSOR_DRIFT')
    if handoff.get('status') not in {'PASS','BLOCKED'}:
        fail('CROSS_STAGE_HANDOFF_STATUS_INVALID')
    if not isinstance(handoff.get('unresolved_required_dependency_total'),int) or handoff.get('unresolved_required_dependency_total')<0:
        fail('CROSS_STAGE_HANDOFF_UNRESOLVED_COUNT_INVALID')
    if not handoff.get('external_receipt'):
        ref=str(handoff.get('ledger_ref') or '')
        if not ref or not (_product_artifact_root()/ref).is_file():
            fail('CROSS_STAGE_HANDOFF_LEDGER_PHYSICAL_REF_MISSING')
    _validate_cross_stage_handoff_ledger(stage_uid,e,st,stages)
    if e.get('result')=='PASS':
        for key in ('reference_resolution_complete','physical_materialization_complete','required_field_completeness_complete','denominator_reconciled','consumer_readiness_complete','current_matrix_valid','current_state_consistent'):
            if handoff.get(key) is not True:
                fail('PASS_WITH_CROSS_STAGE_HANDOFF_NOT_READY:'+key)
        if handoff.get('unresolved_required_dependency_total')!=0 or handoff.get('successor_execution_binding_unresolved_total')!=0 or handoff.get('status')!='PASS':
            fail('PASS_WITH_UNRESOLVED_CROSS_STAGE_HANDOFF')
        if handoff.get('successor_execution_binding_total')!=handoff.get('successor_execution_binding_ready_total'):
            fail('PASS_WITH_INCOMPLETE_SUCCESSOR_EXECUTION_BINDINGS')
    gates=e.get('exact_head_gate_receipts')
    if not isinstance(gates,list) or not gates: fail('EXACT_HEAD_GATE_RECEIPTS_MISSING')
    for gate in gates:
        if not isinstance(gate,dict) or gate.get('head_sha')!=head or gate.get('conclusion')!='success' or not gate.get('run_id') or not gate.get('gate_uid'):
            fail('EXACT_HEAD_GATE_RECEIPT_INVALID')
    resume=e.get('resume_persistence')
    if not isinstance(resume,dict) or resume.get('performed') is not True or not resume.get('resume_point'):
        fail('RESUME_PERSISTENCE_INVALID')
    nxt=e.get('next_stage_transition')
    if not isinstance(nxt,dict) or nxt.get('next_stage_uid')!=st.get('next_stage_uid'):
        fail('NEXT_STAGE_TRANSITION_INVALID')
    if e.get('result') not in {'PASS','BLOCKED'}: fail('EVIDENCE_RESULT_INVALID')
    if e.get('result')=='BLOCKED':
        if nxt.get('status')!='BLOCKED': fail('BLOCKED_EVIDENCE_NEXT_STAGE_TRANSITION_NOT_BLOCKED')
    elif nxt.get('status') not in {'READY','PROJECT_COMPLETE','NEXT_PAGE_READY'}:
        fail('PASS_EVIDENCE_NEXT_STAGE_TRANSITION_INVALID')

    if e['result']=='PASS':
        if any(d[k]!=0 for k in ('open_gap_total','closure_blocker_total','remaining_scope_total')): fail('PASS_WITH_NONZERO_DENOMINATOR')
        if e.get('stage_exit_allowed') is not True: fail('PASS_WITH_STAGE_EXIT_BLOCKED')
        if any(x in {'BLOCKED','NOT_EXECUTED_AFTER_BLOCK'} for x in seen): fail('PASS_WITH_NONPASS_PHASE')
        for label,rows in [('OPERATION',ops),('OUTPUT',outs),('SCANNER',scans),('VALIDATOR',vals)]:
            bad=[uid for uid,row in rows.items() if row.get('status')!='PASS']
            if bad: fail(f'PASS_WITH_NONPASS_{label}:{bad}')
        if remediation['unresolved_gap_total']!=0: fail('PASS_WITH_UNRESOLVED_REMEDIATION')
        if sweep.get('result')!='PASS' or sweep.get('discovered_defect_total')!=0: fail('PASS_WITH_HIDDEN_DEFECT')
    else:
        if e.get('stage_exit_allowed') is not False: fail('BLOCKED_WITH_STAGE_EXIT_ALLOWED')
        if 'BLOCKED' not in seen: fail('BLOCKED_WITHOUT_BLOCKED_PHASE')
    return e

def validate_evidence(stage_uid,path):
    return validate_evidence_data(stage_uid,j(path))

def validate_terminal(stage_uid,evidence,receipt):
    e=validate_evidence(stage_uid,evidence)
    if e.get('result')!='PASS': fail('TERMINAL_CLOSURE_REQUIRES_PASS_EVIDENCE')
    r=j(receipt)
    for k in ('provider','repository_or_project','head_sha','run_id','job_denominator','conclusion','governance_uid','stage_uid','evidence_ref'):
        if r.get(k) in (None,'',[]): fail(f'TERMINAL_RECEIPT_FIELD_MISSING:{k}')
    if r.get('governance_uid')!=e.get('governance_uid') or r.get('stage_uid')!=stage_uid or r.get('conclusion')!='success': fail('TERMINAL_RECEIPT_IDENTITY_OR_RESULT_DRIFT')
    if not isinstance(r.get('job_denominator'),list) or not r['job_denominator']: fail('TERMINAL_RECEIPT_JOB_DENOMINATOR_INVALID')
    product_root=_product_artifact_root()
    evidence_ref=Path(str(r.get('evidence_ref') or ''))
    if evidence_ref.is_absolute() or '..' in evidence_ref.parts: fail('TERMINAL_RECEIPT_EVIDENCE_REF_INVALID')
    if (product_root/evidence_ref).resolve()!=Path(evidence).resolve():
        fail('TERMINAL_RECEIPT_EVIDENCE_REF_DRIFT')
    _,_,gov,_,_,stages=validate_definition()
    st=stages[stage_uid]
    scope_ref=Path(str(e.get('scope_manifest_ref') or ''))
    scope=_external_yaml(product_root/scope_ref,'CURRENT_EXECUTION_SCOPE')
    work_dir=(product_root/scope_ref).parent
    work=_external_yaml(work_dir/'WORK_UNIT.yaml','CURRENT_WORK_UNIT')
    governed_scope=str(scope.get('governed_unit_uid') or '').strip()
    governed_work=str(work.get('governed_unit_uid') or '').strip()
    if not governed_scope or not governed_work or governed_scope!=governed_work:
        fail('TERMINAL_CLOSURE_GOVERNED_UNIT_IDENTITY_DRIFT')
    denominator=e.get('denominator') or {}
    expected_ops=list(map(str,st.get('operations') or []))
    if denominator.get('required_total')!=len(expected_ops):
        fail('TERMINAL_CLOSURE_DENOMINATOR_IDENTITY_DRIFT')
    op_rows=e.get('operation_results') or []
    if [str(x.get('operation_uid') or '') for x in op_rows]!=expected_ops:
        fail('TERMINAL_CLOSURE_OPERATION_RECEIPT_CHAIN_DRIFT')
    evidence_rows=e.get('required_evidence') or []
    if not evidence_rows or any(not str(x.get('ref') or '').strip() for x in evidence_rows):
        fail('TERMINAL_CLOSURE_EVIDENCE_REFS_INCOMPLETE')
    successor=e.get('next_stage_transition')
    if not isinstance(successor,dict) or successor.get('next_stage_uid')!=st.get('next_stage_uid') or not successor.get('status'):
        fail('TERMINAL_CLOSURE_SUCCESSOR_ELIGIBILITY_INVALID')
    contract=_deterministic_stage_audit_contract().get('terminal_receipt_contract') or {}
    expected_projection={'stage_uid','governed_unit_uid','denominator_identity','operation_receipt_chain','evidence_refs','result','successor_eligibility'}
    if set(map(str,contract.get('closure_projection_must_prove') or []))!=expected_projection:
        fail('TERMINAL_CLOSURE_PROJECTION_CONTRACT_DRIFT')
    if gov!=e.get('governance_uid'):
        fail('TERMINAL_CLOSURE_CURRENT_GOVERNANCE_DRIFT')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if r.get('head_sha')!=head: fail('TERMINAL_RECEIPT_HEAD_MISMATCH')
    print(f'PASS: terminal receipt exact-head closure valid for {stage_uid} governed_unit={governed_scope} head={head}')

def _load_operation_receipt(path):
    if not path.is_file():
        fail('ACTIVE_OPERATION_RECEIPT_MISSING:'+_display_path(path))
    try:
        if path.suffix.lower()=='.json':
            obj=json.loads(path.read_text(encoding='utf-8'))
        else:
            obj=yaml.safe_load(path.read_text(encoding='utf-8'))
    except Exception as exc:
        fail('ACTIVE_OPERATION_RECEIPT_PARSE_FAILED:'+type(exc).__name__)
    if not isinstance(obj,dict):
        fail('ACTIVE_OPERATION_RECEIPT_MAPPING_REQUIRED')
    return obj

def _atomic_yaml_write(path,obj):
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(yaml.safe_dump(obj,sort_keys=False,allow_unicode=True),encoding='utf-8')
    tmp.replace(path)

def execute_active(stage_uid):
    _,_,gov,_,adapters,stages=validate_definition()
    work=active_product(stage_uid)
    product_root,work_ctx,scope,work_rel,scope_rel=product_execution_context()
    if work_ctx.get('work_unit_uid')!=work.get('work_unit_uid'):
        fail('ACTIVE_STAGE_WORK_UNIT_CONTEXT_DRIFT')
    work_path=(product_root/Path(work_rel)).resolve()
    work_dir=work_path.parent
    state_path=work_dir/'EXECUTION_STATE.yaml'
    state=_external_yaml(state_path,'CURRENT_EXECUTION_STATE')
    if (work.get('pre_execution_gate_status')!='PASS'
        or scope.get('product_stage_execution_allowed') is not True
        or (state.get('resume_control') or {}).get('product_execution_allowed') is not True):
        fail('ACTIVE_STAGE_EXECUTION_NOT_ADMITTED')
    bindings=work.get('operation_bindings') or {}
    expected_ops=list(map(str,stages[stage_uid].get('operations') or []))
    if set(map(str,bindings))!=set(expected_ops):
        fail('ACTIVE_STAGE_OPERATION_BINDING_COVERAGE_INVALID:'+stage_uid)
    completed=state.get('completed_operations')
    if not isinstance(completed,list):
        fail('ACTIVE_STAGE_COMPLETED_OPERATIONS_INVALID')
    completed=list(map(str,completed))
    if len(completed)!=len(set(completed)) or completed!=expected_ops[:len(completed)]:
        fail('ACTIVE_STAGE_COMPLETED_OPERATION_PREFIX_INVALID:'+repr(completed))
    if len(completed)>=len(expected_ops):
        if str(state.get('current_operation') or '')!='COMPLETE':
            fail('ACTIVE_STAGE_COMPLETE_STATE_OPERATION_DRIFT')
        fail('ACTIVE_STAGE_OPERATIONS_ALREADY_COMPLETE:'+stage_uid)
    operation_uid=expected_ops[len(completed)]
    if str(state.get('current_operation') or '')!=operation_uid:
        fail('ACTIVE_STAGE_CURRENT_OPERATION_DRIFT:expected='+operation_uid+':actual='+str(state.get('current_operation')))
    binding=bindings.get(operation_uid)
    if not isinstance(binding,dict):
        fail('ACTIVE_STAGE_CURRENT_OPERATION_BINDING_MISSING:'+operation_uid)
    owner=str(binding.get('executor_owner') or '')
    protocol=str(binding.get('executor_protocol') or '')
    result_owner=str(binding.get('result_owner') or '')
    receipt_ref=str(binding.get('operation_receipt_ref') or '')
    driver=adapters.get('execution_driver_contract') or {}
    if protocol not in set(map(str,driver.get('allowed_operation_executor_protocols') or [])):
        fail('ACTIVE_STAGE_EXECUTOR_PROTOCOL_FORBIDDEN:'+protocol)
    if protocol!='PYTHON_STAGE_OPERATION_V1':
        fail('ACTIVE_STAGE_EXECUTOR_PROTOCOL_UNSUPPORTED:'+protocol)
    rel=Path(owner)
    if rel.is_absolute() or '..' in rel.parts or rel.suffix.lower()!='.py':
        fail('ACTIVE_STAGE_EXECUTOR_OWNER_PATH_INVALID')
    executor=(product_root/rel).resolve()
    try:
        executor.relative_to(product_root)
    except ValueError:
        fail('ACTIVE_STAGE_EXECUTOR_OUTSIDE_PRODUCT_ROOT')
    if not executor.is_file():
        fail('ACTIVE_STAGE_EXECUTOR_OWNER_MISSING:'+owner)
    if executor.resolve()==Path(__file__).resolve():
        fail('COMMON_ENGINE_RECURSIVE_EXECUTOR_FORBIDDEN')
    receipt_rel=Path(receipt_ref)
    if receipt_rel.is_absolute() or '..' in receipt_rel.parts:
        fail('ACTIVE_STAGE_OPERATION_RECEIPT_REF_INVALID:'+operation_uid)
    receipt_path=(product_root/receipt_rel).resolve()
    try:
        receipt_path.relative_to(work_dir.resolve())
    except ValueError:
        fail('ACTIVE_STAGE_OPERATION_RECEIPT_OUTSIDE_WORK_UNIT:'+operation_uid)
    if receipt_path.exists():
        fail('ACTIVE_STAGE_OPERATION_RECEIPT_ALREADY_EXISTS:'+receipt_ref)
    adapter=(adapters.get('stages') or {}).get(stage_uid) or {}
    if adapter.get('effectful_executor_owner_resolution')!='CURRENT_WORK_UNIT_OPERATION_BINDING_ONLY':
        fail('ACTIVE_STAGE_EXECUTOR_OWNER_RESOLUTION_POLICY_INVALID:'+stage_uid)
    ref=str(adapter.get('stepwise_execution_contract_ref') or '')
    if ref!='stepwise_execution_defaults':
        fail('ACTIVE_STAGE_STEPWISE_EXECUTION_CONTRACT_REF_INVALID:'+stage_uid)
    stepwise=adapters.get('stepwise_execution_defaults')
    if not isinstance(stepwise,dict):
        fail('ACTIVE_STAGE_STEPWISE_EXECUTION_CONTRACT_MISSING:'+stage_uid)
    if stepwise.get('mode')!='OPERATION_BY_OPERATION':
        fail('ACTIVE_STAGE_STEPWISE_EXECUTION_MODE_INVALID:'+stage_uid)
    if stepwise.get('bulk_stage_materialization')!='FORBIDDEN':
        fail('ACTIVE_STAGE_BULK_MATERIALIZATION_NOT_FORBIDDEN:'+stage_uid)
    if stepwise.get('checkpoint_after_each_operation') is not True:
        fail('ACTIVE_STAGE_OPERATION_CHECKPOINT_NOT_REQUIRED:'+stage_uid)
    if stepwise.get('successor_requires_operation_pass') is not True:
        fail('ACTIVE_STAGE_SUCCESSOR_OPERATION_PASS_NOT_REQUIRED:'+stage_uid)
    cmd=[sys.executable,str(executor),'--stage',stage_uid,'--operation',operation_uid,'--work-unit',work_rel,'--product-root',str(product_root)]
    proc=subprocess.run(cmd,cwd=product_root,text=True,capture_output=True)
    if proc.returncode!=0:
        msg=(proc.stderr or proc.stdout or '').strip().replace('\n',' ')[:800]
        fail('ACTIVE_STAGE_OPERATION_EXECUTOR_FAILED:'+operation_uid+':'+str(proc.returncode)+':'+msg)
    receipt=_load_operation_receipt(receipt_path)
    expected_receipt={
      'artifact_type':'OPERATION_EXECUTION_RECEIPT',
      'stage_uid':stage_uid,
      'work_unit_uid':str(work.get('work_unit_uid') or ''),
      'operation_uid':operation_uid,
      'governance_uid':gov,
      'status':str(driver.get('operation_receipt_status_required') or 'PASS'),
      'executor_owner':owner,
      'executor_protocol':protocol,
      'result_owner':result_owner
    }
    for key,val in expected_receipt.items():
        if receipt.get(key)!=val:
            fail('ACTIVE_STAGE_OPERATION_RECEIPT_IDENTITY_DRIFT:'+operation_uid+':'+key)
    completed.append(operation_uid)
    next_op=expected_ops[len(completed)] if len(completed)<len(expected_ops) else 'COMPLETE'
    state['completed_operations']=completed
    state['current_operation']=next_op
    state['status']='IN_PROGRESS' if next_op!='COMPLETE' else 'EXECUTION_COMPLETE_CLOSURE_PENDING'
    if 'current_status' in state:
        state['current_status']=state['status']
    state['last_operation_uid']=operation_uid
    state['last_operation_receipt_ref']=receipt_ref
    _atomic_yaml_write(state_path,state)
    print(json.dumps({
      'result':'PASS',
      'stage_uid':stage_uid,
      'work_unit_uid':work.get('work_unit_uid'),
      'operation_uid':operation_uid,
      'operation_receipt_ref':receipt_ref,
      'next_operation':next_op,
      'stage_status':state['status'],
      'stage_closure_claimed':False
    },ensure_ascii=False))
    return True


def main():
    p=argparse.ArgumentParser(); g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--definition-audit-all',action='store_true'); g.add_argument('--plan',action='store_true'); g.add_argument('--plan-range',action='store_true'); g.add_argument('--admission-check',action='store_true'); g.add_argument('--validate-evidence',action='store_true'); g.add_argument('--validate-terminal-receipt',action='store_true'); g.add_argument('--execute',action='store_true')
    p.add_argument('--stage'); p.add_argument('--start-stage'); p.add_argument('--end-stage'); p.add_argument('--evidence'); p.add_argument('--receipt'); a=p.parse_args()
    try:
        if a.execute:
            if not a.stage: fail('STAGE_REQUIRED')
            execute_active(a.stage); return
        if a.plan_range:
            if not a.start_stage or not a.end_stage: fail('RANGE_ENDPOINTS_REQUIRED')
            print(json.dumps(plan_range(a.start_stage,a.end_stage),ensure_ascii=False,indent=2)); return
        if a.definition_audit_all:
            _,_,_,profile,_,stages=validate_definition()
            print(f'PASS: common Stage Execution Engine definition audit stages={len(stages)}/{profile.get("profile_local_denominator")} phases={len(EXPECTED_PHASES)}/{len(EXPECTED_PHASES)}')
            print('PASS: all profile stages have semantic adapters, scanner dimensions, denominator, operations, outputs, evidence and closure contracts')
            print('PASS: definition audit product_stage_credit=0; product PASS requires fresh evidence and exact-head terminal receipt')
            return
        if not a.stage: fail('STAGE_REQUIRED')
        if a.plan: print(json.dumps(plan(a.stage),ensure_ascii=False,indent=2)); return
        if a.admission_check: admission(a.stage); return
        if a.validate_evidence:
            if not a.evidence: fail('EVIDENCE_PATH_REQUIRED')
            validate_evidence(a.stage,ROOT/a.evidence); print(f'PASS: normalized fresh execution evidence valid for {a.stage}'); return
        if a.validate_terminal_receipt:
            if not a.evidence or not a.receipt: fail('EVIDENCE_AND_RECEIPT_REQUIRED')
            validate_terminal(a.stage,ROOT/a.evidence,ROOT/a.receipt); return
    except StageEngineError as exc:
        print(f'BLOCK: {exc}',file=sys.stderr); raise SystemExit(1)
if __name__=='__main__': main()
