#!/usr/bin/env python3
from pathlib import Path
import json,yaml,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]

def load(root,rel):
    p=root/rel
    return yaml.safe_load(p.read_text(encoding='utf-8')) or {}

def validate(root=ROOT):
    failures=[]
    rel='10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'
    p=root/rel
    if not p.exists(): return {'status':'FAIL','failures':['stage_execution_invariant_registry_missing']}
    d=load(root,rel); inv=d.get('invariants') or {}
    if d.get('artifact_uid')!='REG-STAGE-EXECUTION-INVARIANT-001': failures.append('registry_uid_invalid')
    rev=str(d.get('governance_revision') or '')
    root_rev=str(load(root,'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml').get('governance_revision') or '')
    if not rev or rev != root_rev: failures.append('revision_invalid')
    scope=d.get('scope') or {}; expected=[f'STAGE-{i:02d}' for i in range(1,12)]
    if scope.get('applies_to_stages')!=expected: failures.append('stage_scope_not_all_11')
    if scope.get('stage_specific_exception_without_registered_authority')!='BLOCK': failures.append('unregistered_stage_exception_not_blocked')
    required=['RELATION_SEMANTIC_SEPARATION','GAP_REMEDIATION_ADMISSIBILITY','CURRENT_AUTHORITY_ADMISSIBILITY','REQUIRED_EVIDENCE_MATERIALIZATION','VALIDATOR_SCHEMA_SEMANTICS','UNRESOLVED_PRESERVATION','SUCCESSOR_CURRENT_ATOMIC_PROJECTION','BLOCKER_DENOMINATOR_AND_RECEIPT','AUTHORITY_EVIDENCE_CONSUMPTION','FUNCTIONAL_CONTRACT_COMPLETENESS','STAGE_ENTRY_PRECHECK','IMPLEMENTATION_DEVIATION_FEEDBACK','REVIEW_VS_CLOSURE_SEPARATION','CANONICAL_STAGE_EXECUTION_PREFLIGHT','EFFECTIVE_CONTRACT_OVERLAY','ROLE_SAFE_FUNCTIONAL_CLOSURE','DEPENDENCY_ORDERED_INCREMENTAL_RECONCILIATION','COMMON_ENGINE_DEFECT_INTERRUPT','GENERATED_OUTPUT_PERSISTENCE']
    for k in required:
        if k not in inv: failures.append('missing_invariant:'+k)
    r=inv.get('RELATION_SEMANTIC_SEPARATION') or {}
    if any(r.get(k) is not False for k in ['port_exposure_is_trigger','state_event_is_trigger_without_explicit_binding','registry_membership_is_action_binding','semantic_similarity_may_create_binding']): failures.append('relation_inference_not_forbidden')
    if r.get('explicit_binding_or_unique_current_authority_required') is not True: failures.append('explicit_binding_rule_missing')
    g=inv.get('GAP_REMEDIATION_ADMISSIBILITY') or {}; gc=g.get('gap_classes') or {}
    for k in ['INPUT_SOURCE_GAP','AUTHORITY_GAP','ARCHITECTURE_GAP']:
        if gc.get(k)!='AI_AUTO_FILL_BLOCK': failures.append('gap_autofill_not_blocked:'+k)
    a=inv.get('CURRENT_AUTHORITY_ADMISSIBILITY') or {}
    if a.get('current_authority_set_membership_required') is not True or a.get('final_or_locked_status_alone_confers_current_authority') is not False or a.get('non_current_final_locked_source_use')!='BLOCK': failures.append('current_authority_admissibility_incomplete')
    e=inv.get('REQUIRED_EVIDENCE_MATERIALIZATION') or {}
    if e.get('ledger_or_plan_claim_proves_physical_artifact') is not False or e.get('canonical_physical_artifact_required') is not True or e.get('parse_required') is not True or e.get('schema_or_required_field_validation_required') is not True or e.get('review_complete_implies_stage_closed') is not False: failures.append('required_evidence_materialization_incomplete')
    v=inv.get('VALIDATOR_SCHEMA_SEMANTICS') or {}
    if v.get('authoritative_schema_path_required') is not True or v.get('authoritative_enum_or_status_constant_required') is not True or v.get('stale_path_or_constant_is_validator_defect_not_data_defect') is not True or v.get('optional_sparse_zero_missing_key_equals_zero') is not True or v.get('mandatory_missing_field_equals_zero') is not False: failures.append('validator_schema_semantics_incomplete')
    u=inv.get('UNRESOLVED_PRESERVATION') or {}
    if u.get('unresolved_owner_operation_port_must_remain_null') is not True or u.get('unresolved_lifecycle_fields_must_remain_unresolved') is not True or u.get('derived_default_or_similarity_binding')!='BLOCK': failures.append('unresolved_preservation_incomplete')
    s=inv.get('SUCCESSOR_CURRENT_ATOMIC_PROJECTION') or {}
    if s.get('verified_successor_must_project_to_current_atomically') is not True or s.get('stale_current_snapshot_disposition')!='REMOVE_FROM_CURRENT_PROJECTION_AND_MARK_SUPERSEDED' or s.get('predecessor_evidence_disposition')!='RETAIN_IMMUTABLE_HISTORY_ONLY' or s.get('physical_delete_predecessor_evidence_to_fix_current_state')!='BLOCK': failures.append('successor_current_projection_incomplete')
    b=inv.get('BLOCKER_DENOMINATOR_AND_RECEIPT') or {}
    if b.get('denominator_change_invalidates_old_receipt_for_successor') is not True or b.get('successor_state_before_new_external_receipt')!='PENDING_EXTERNAL_CI' or b.get('successor_state_after_valid_external_receipt')!='SUCCESS_EXTERNAL_RECEIPT' or b.get('prior_pass_may_be_reused_as_successor_verification') is not False: failures.append('receipt_denominator_incomplete')
    c=inv.get('AUTHORITY_EVIDENCE_CONSUMPTION') or {}
    if c.get('enumerate_current_admissible_evidence_before_gap_disposition') is not True or c.get('track_evidence_consumption_per_gap') is not True or c.get('uniquely_relevant_current_evidence_skipped')!='GOVERNANCE_DEFECT' or c.get('unconsumed_evidence_may_be_silently_ignored') is not False: failures.append('authority_consumption_incomplete')
    f=inv.get('FUNCTIONAL_CONTRACT_COMPLETENESS') or {}
    needed={'business_intent_or_user_journey','explicit_trigger_or_control_binding','input_source','payload_schema','validation','permission_or_gate','authority_ref','prerequisite_state','resulting_state_or_state_transition','runtime_owner','next_action_or_terminal_disposition','audit_event','error_or_failure_binding','retry_recovery_or_rollback_disposition'}
    if set(f.get('effectful_action_required_fields') or [])!=needed: failures.append('functional_contract_fields_incomplete')
    if set(f.get('create_additional_required_fields') or [])!={'creation_mode','created_entity_or_output_identity'}: failures.append('create_contract_fields_incomplete')
    async_needed={'queue_or_trigger_contract','provider_or_worker_owner','idempotency','retry_policy','timeout_or_expiry','failure_or_dlq','recovery_or_compensation','completion_or_response_binding'}
    if set(f.get('async_additional_required_fields') or [])!=async_needed: failures.append('async_contract_fields_incomplete')
    pre=inv.get('CANONICAL_STAGE_EXECUTION_PREFLIGHT') or {}
    pre_req={'REQUIRED_FIELD_MANIFEST','FUNCTIONAL_CHAIN_MANIFEST','EFFECTIVE_CONTRACT_OVERLAY','DEPENDENCY_TOPOLOGY','DENOMINATOR_SNAPSHOT','CLASSIFICATION_RULESET','CHANGE_IMPACT_MAP','STAGE_EXECUTION_PREFLIGHT_RECEIPT'}
    if set(pre.get('required_artifacts') or [])!=pre_req or pre.get('all_scanners_validators_classifiers_share_same_manifest_set') is not True or pre.get('applicability_before_blocker_count') is not True: failures.append('canonical_preflight_incomplete')
    if pre.get('explicit_stage_registry_binding_required') is not True or set(pre.get('required_stage_uid_set') or [])!={f'STAGE-{i:02d}' for i in range(1,12)} or pre.get('all_stage_entries_must_reference_invariant_uid')!='GOV-INV-CANONICAL-STAGE-EXECUTION-OPTIMIZATION-001': failures.append('canonical_preflight_explicit_stage_binding_incomplete')
    eff=inv.get('EFFECTIVE_CONTRACT_OVERLAY') or {}
    if eff.get('raw_absence_alone_is_effective_gap') is not False or eff.get('exact_role_correct_successor_may_close_matching_signature') is not True or eff.get('physical_rescan_and_signature_reconciliation_required') is not True: failures.append('effective_overlay_incomplete')
    role=inv.get('ROLE_SAFE_FUNCTIONAL_CLOSURE') or {}
    if role.get('pre_materialized_exact_value_absence_alone_is_authority_gap') is not False or role.get('unique_functional_closure_derivation_required_before_auto_remediable') is not True or role.get('authority_gap_minimum_materially_distinct_viable_behaviors')!=2: failures.append('role_safe_closure_incomplete')
    dep=inv.get('DEPENDENCY_ORDERED_INCREMENTAL_RECONCILIATION') or {}
    if dep.get('local_reverse_dependency_validation_after_each_batch') is not True or dep.get('checkpoint_full_sweep_required_after') is None or dep.get('one_current_problem_register') is not True or dep.get('append_only_resolution_ledger') is not True: failures.append('dependency_incremental_reconciliation_incomplete')
    eng=inv.get('COMMON_ENGINE_DEFECT_INTERRUPT') or {}
    if eng.get('harness_or_parser_or_classifier_defect_is_product_blocker') is not False or eng.get('common_engine_fix_required_before_affected_remediation_continues') is not True or eng.get('replay_required_before_product_progress_credit') is not True: failures.append('common_engine_defect_interrupt_incomplete')
    per=inv.get('GENERATED_OUTPUT_PERSISTENCE') or {}
    if per.get('tracked_and_untracked_output_detection_required') is not True or per.get('git_diff_quiet_alone_sufficient') is not False or per.get('exact_output_path_persistence_proof_required') is not True: failures.append('generated_output_persistence_incomplete')
    rv=inv.get('REVIEW_VS_CLOSURE_SEPARATION') or {}
    if rv.get('review_completion_is_evidence_of_review_only') is not True or rv.get('review_completion_may_override_open_blockers') is not False: failures.append('review_closure_separation_incomplete')
    # Cross-artifact bindings
    bp=load(root,'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'); bc=bp.get('stage_execution_invariant_contract') or {}
    if bc.get('registry_uid')!='REG-STAGE-EXECUTION-INVARIANT-001' or bc.get('validator_uid')!='VAL-GOV-035' or bc.get('observed_stage_does_not_limit_scope') is not True: failures.append('acceptance_blueprint_binding_missing')
    life=load(root,'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml')
    if life.get('stage_execution_invariant_ref')!='REG-STAGE-EXECUTION-INVARIANT-001': failures.append('lifecycle_common_binding_missing')
    cs=(life.get('cross_stage_invariants') or {}).get('stage_execution_invariant_hardening') or {}
    if cs.get('applies_to_all_stages') is not True: failures.append('lifecycle_cross_stage_scope_missing')
    st2=next((x for x in life.get('stages') or [] if x.get('stage_uid')=='STAGE-02'),{})
    if (st2.get('stage_execution_invariant_gate') or {}).get('required') is not True: failures.append('stage02_empirical_gate_binding_missing')
    expected_stage_ids={f'STAGE-{i:02d}' for i in range(1,12)}
    stage_map={s.get('stage_uid'):s for s in (life.get('stages') or [])}
    if set(stage_map)!=expected_stage_ids: failures.append('stage_execution_optimization_stage_set_drift')
    else:
        for sid in sorted(expected_stage_ids):
            sg=stage_map[sid].get('canonical_execution_optimization_gate') or {}
            if sg.get('required') is not True or sg.get('invariant_uid')!='GOV-INV-CANONICAL-STAGE-EXECUTION-OPTIMIZATION-001' or sg.get('explicit_stage_binding_required') is not True or sg.get('raw_plus_legal_successor_overlay_is_effective_truth') is not True or sg.get('authority_gap_minimum_distinct_behaviors')!=2:
                failures.append('stage_execution_optimization_explicit_binding_missing:'+sid)
    opt=st2.get('canonical_execution_optimization_gate') or {}
    if opt.get('required') is not True or opt.get('raw_plus_legal_successor_overlay_is_effective_truth') is not True or opt.get('authority_gap_minimum_distinct_behaviors')!=2: failures.append('stage02_execution_optimization_gate_missing')
    idx=load(root,'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml')
    if idx.get('stage_execution_invariant_registry_ref')!='REG-STAGE-EXECUTION-INVARIANT-001': failures.append('construction_index_binding_missing')
    ur=idx.get('universal_rules') or {}
    for k in ['port_exposure_as_trigger','state_event_as_trigger_without_explicit_binding','semantic_similarity_binding_creation','non_current_final_locked_authority_use','input_authority_architecture_gap_ai_autofill','required_evidence_ledger_claim_without_physical_artifact','validator_stale_schema_path_or_enum','stale_current_snapshot_after_successor_acceptance','receipt_reuse_after_denominator_change','unique_current_authority_evidence_skip','review_completion_as_stage_closure']:
        if ur.get(k)!='BLOCK': failures.append('construction_universal_rule_not_block:'+k)
    return {'status':'PASS' if not failures else 'FAIL','invariant_count':len(inv),'stage_count':len(scope.get('applies_to_stages') or []),'failures':failures}

if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
