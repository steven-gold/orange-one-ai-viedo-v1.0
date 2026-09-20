from pathlib import Path
import json, yaml, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]

def load(root, rel):
    p = root / rel
    return yaml.safe_load(p.read_text(encoding='utf-8')) or {}

HANDOFF_REQUIRED_FIELDS_FOR_VALIDATOR=['producer_stage_or_capability', 'producer_output_uid_or_type', 'producer_owner', 'producer_physical_ref_or_external_evidence', 'producer_hash_or_version_or_schema', 'consumer_stage_or_capability', 'consumer_input_uid_or_type', 'consumer_owner_or_schema', 'applicability', 'reference_resolution_status', 'physical_materialization_status', 'parse_schema_status', 'required_field_completeness', 'denominator_inclusion_status', 'consumer_readiness_status', 'unresolved_required_dependency_total', 'blocking_owner_or_reentry_target', 'current_evidence_ref']

def validate(root=ROOT):
    failures = []
    rel = '10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'
    p = root / rel
    if not p.exists():
        return {'status': 'FAIL', 'failures': ['stage_execution_invariant_registry_missing']}
    d = load(root, rel)
    inv = d.get('invariants') or {}
    if d.get('artifact_uid') != 'REG-STAGE-EXECUTION-INVARIANT-001':
        failures.append('registry_uid_invalid')
    rev = str(d.get('governance_revision') or '')
    root_rev = str(load(root, '10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml').get('governance_revision') or '')
    if not rev or rev != root_rev:
        failures.append('revision_invalid')
    scope = d.get('scope') or {}
    expected = [f'STAGE-{i:02d}' for i in range(1, 12)]
    if scope.get('applies_to_stages') != expected:
        failures.append('stage_scope_not_all_11')
    if scope.get('stage_specific_exception_without_registered_authority') != 'BLOCK':
        failures.append('unregistered_stage_exception_not_blocked')
    required = ['RELATION_SEMANTIC_SEPARATION', 'GAP_REMEDIATION_ADMISSIBILITY', 'CURRENT_AUTHORITY_ADMISSIBILITY', 'REQUIRED_EVIDENCE_MATERIALIZATION', 'VALIDATOR_SCHEMA_SEMANTICS', 'UNRESOLVED_PRESERVATION', 'SUCCESSOR_CURRENT_ATOMIC_PROJECTION', 'BLOCKER_DENOMINATOR_AND_RECEIPT', 'AUTHORITY_EVIDENCE_CONSUMPTION', 'FUNCTIONAL_CONTRACT_COMPLETENESS', 'STAGE_ENTRY_PRECHECK', 'IMPLEMENTATION_DEVIATION_FEEDBACK', 'REVIEW_VS_CLOSURE_SEPARATION', 'CANONICAL_STAGE_EXECUTION_PREFLIGHT', 'EFFECTIVE_CONTRACT_OVERLAY', 'ROLE_SAFE_FUNCTIONAL_CLOSURE', 'DEPENDENCY_ORDERED_INCREMENTAL_RECONCILIATION', 'COMMON_ENGINE_DEFECT_INTERRUPT', 'GENERATED_OUTPUT_PERSISTENCE', 'CONTROL_VS_SYSTEM_TRIGGER_RESOLUTION', 'PRODUCER_CONSUMER_SCHEMA_IDENTITY', 'NO_HISTORY_PRODUCT_VALUE_FALLBACK', 'TASK_LAYER_EFFECTFUL_TRANSITION_ORDER', 'VISUAL_DESIGN_PROFILE_MATERIALIZATION_COMPLETENESS']
    for k in required:
        if k not in inv:
            failures.append('missing_invariant:' + k)
    r = inv.get('RELATION_SEMANTIC_SEPARATION') or {}
    if any((r.get(k) is not False for k in ['port_exposure_is_trigger', 'state_event_is_trigger_without_explicit_binding', 'registry_membership_is_action_binding', 'semantic_similarity_may_create_binding'])):
        failures.append('relation_inference_not_forbidden')
    if r.get('explicit_binding_or_unique_current_authority_required') is not True:
        failures.append('explicit_binding_rule_missing')
    g = inv.get('GAP_REMEDIATION_ADMISSIBILITY') or {}
    gc = g.get('gap_classes') or {}
    for k in ['INPUT_SOURCE_GAP', 'AUTHORITY_GAP', 'ARCHITECTURE_GAP']:
        if gc.get(k) != 'AI_AUTO_FILL_BLOCK':
            failures.append('gap_autofill_not_blocked:' + k)
    a = inv.get('CURRENT_AUTHORITY_ADMISSIBILITY') or {}
    if a.get('current_authority_set_membership_required') is not True or a.get('final_or_locked_status_alone_confers_current_authority') is not False or a.get('non_current_final_locked_source_use') != 'BLOCK':
        failures.append('current_authority_admissibility_incomplete')
    e = inv.get('REQUIRED_EVIDENCE_MATERIALIZATION') or {}
    if e.get('ledger_or_plan_claim_proves_physical_artifact') is not False or e.get('canonical_physical_artifact_required') is not True or e.get('parse_required') is not True or (e.get('schema_or_required_field_validation_required') is not True) or (e.get('review_complete_implies_stage_closed') is not False):
        failures.append('required_evidence_materialization_incomplete')
    v = inv.get('VALIDATOR_SCHEMA_SEMANTICS') or {}
    if v.get('authoritative_schema_path_required') is not True or v.get('authoritative_enum_or_status_constant_required') is not True or v.get('stale_path_or_constant_is_validator_defect_not_data_defect') is not True or (v.get('optional_sparse_zero_missing_key_equals_zero') is not True) or (v.get('mandatory_missing_field_equals_zero') is not False):
        failures.append('validator_schema_semantics_incomplete')
    u = inv.get('UNRESOLVED_PRESERVATION') or {}
    if u.get('unresolved_owner_operation_port_must_remain_null') is not True or u.get('unresolved_lifecycle_fields_must_remain_unresolved') is not True or u.get('derived_default_or_similarity_binding') != 'BLOCK':
        failures.append('unresolved_preservation_incomplete')
    s = inv.get('SUCCESSOR_CURRENT_ATOMIC_PROJECTION') or {}
    if s.get('verified_successor_must_project_to_current_atomically') is not True or s.get('stale_current_snapshot_disposition') != 'REMOVE_FROM_CURRENT_PROJECTION_AND_MARK_SUPERSEDED' or s.get('predecessor_evidence_disposition') != 'RETAIN_IMMUTABLE_HISTORY_ONLY' or (s.get('physical_delete_predecessor_evidence_to_fix_current_state') != 'BLOCK'):
        failures.append('successor_current_projection_incomplete')
    b = inv.get('BLOCKER_DENOMINATOR_AND_RECEIPT') or {}
    if b.get('denominator_change_invalidates_old_receipt_for_successor') is not True or b.get('successor_state_before_new_external_receipt') != 'PENDING_EXTERNAL_CI' or b.get('successor_state_after_valid_external_receipt') != 'SUCCESS_EXTERNAL_RECEIPT' or (b.get('prior_pass_may_be_reused_as_successor_verification') is not False):
        failures.append('receipt_denominator_incomplete')
    c = inv.get('AUTHORITY_EVIDENCE_CONSUMPTION') or {}
    if c.get('enumerate_current_admissible_evidence_before_gap_disposition') is not True or c.get('track_evidence_consumption_per_gap') is not True or c.get('uniquely_relevant_current_evidence_skipped') != 'GOVERNANCE_DEFECT' or (c.get('unconsumed_evidence_may_be_silently_ignored') is not False):
        failures.append('authority_consumption_incomplete')
    f = inv.get('FUNCTIONAL_CONTRACT_COMPLETENESS') or {}
    needed = {'business_intent_or_user_journey', 'explicit_trigger_or_control_binding', 'input_source', 'payload_schema', 'validation', 'permission_or_gate', 'authority_ref', 'prerequisite_state', 'resulting_state_or_state_transition', 'runtime_owner', 'next_action_or_terminal_disposition', 'audit_event', 'error_or_failure_binding', 'retry_recovery_or_rollback_disposition'}
    if set(f.get('effectful_action_required_fields') or []) != needed:
        failures.append('functional_contract_fields_incomplete')
    if set(f.get('create_additional_required_fields') or []) != {'creation_mode', 'created_entity_or_output_identity'}:
        failures.append('create_contract_fields_incomplete')
    async_needed = {'queue_or_trigger_contract', 'provider_or_worker_owner', 'idempotency', 'retry_policy', 'timeout_or_expiry', 'failure_or_dlq', 'recovery_or_compensation', 'completion_or_response_binding'}
    if set(f.get('async_additional_required_fields') or []) != async_needed:
        failures.append('async_contract_fields_incomplete')
    pre = inv.get('CANONICAL_STAGE_EXECUTION_PREFLIGHT') or {}
    pre_req = {'REQUIRED_FIELD_MANIFEST', 'FUNCTIONAL_CHAIN_MANIFEST', 'EFFECTIVE_CONTRACT_OVERLAY', 'DEPENDENCY_TOPOLOGY', 'DENOMINATOR_SNAPSHOT', 'CLASSIFICATION_RULESET', 'CHANGE_IMPACT_MAP', 'STAGE_EXECUTION_PREFLIGHT_RECEIPT'}
    if set(pre.get('required_artifacts') or []) != pre_req or pre.get('all_scanners_validators_classifiers_share_same_manifest_set') is not True or pre.get('applicability_before_blocker_count') is not True:
        failures.append('canonical_preflight_incomplete')
    if pre.get('explicit_stage_registry_binding_required') is not True or set(pre.get('required_stage_uid_set') or []) != {f'STAGE-{i:02d}' for i in range(1, 12)} or pre.get('all_stage_entries_must_reference_invariant_uid') != 'GOV-INV-CANONICAL-STAGE-EXECUTION-OPTIMIZATION-001':
        failures.append('canonical_preflight_explicit_stage_binding_incomplete')
    eff = inv.get('EFFECTIVE_CONTRACT_OVERLAY') or {}
    if eff.get('raw_absence_alone_is_effective_gap') is not False or eff.get('exact_role_correct_successor_may_close_matching_signature') is not True or eff.get('physical_rescan_and_signature_reconciliation_required') is not True:
        failures.append('effective_overlay_incomplete')
    role = inv.get('ROLE_SAFE_FUNCTIONAL_CLOSURE') or {}
    if role.get('pre_materialized_exact_value_absence_alone_is_authority_gap') is not False or role.get('unique_functional_closure_derivation_required_before_auto_remediable') is not True or role.get('authority_gap_minimum_materially_distinct_viable_behaviors') != 2:
        failures.append('role_safe_closure_incomplete')
    dep = inv.get('DEPENDENCY_ORDERED_INCREMENTAL_RECONCILIATION') or {}
    if dep.get('local_reverse_dependency_validation_after_each_batch') is not True or dep.get('checkpoint_full_sweep_required_after') is None or dep.get('one_current_problem_register') is not True or (dep.get('append_only_resolution_ledger') is not True):
        failures.append('dependency_incremental_reconciliation_incomplete')
    eng = inv.get('COMMON_ENGINE_DEFECT_INTERRUPT') or {}
    if eng.get('harness_or_parser_or_classifier_defect_is_product_blocker') is not False or eng.get('common_engine_fix_required_before_affected_remediation_continues') is not True or eng.get('replay_required_before_product_progress_credit') is not True:
        failures.append('common_engine_defect_interrupt_incomplete')
    per = inv.get('GENERATED_OUTPUT_PERSISTENCE') or {}
    if per.get('tracked_and_untracked_output_detection_required') is not True or per.get('git_diff_quiet_alone_sufficient') is not False or per.get('exact_output_path_persistence_proof_required') is not True:
        failures.append('generated_output_persistence_incomplete')
    trig = inv.get('CONTROL_VS_SYSTEM_TRIGGER_RESOLUTION') or {}
    if trig.get('required_before_no_control_action_gap_escalation') is not True or trig.get('port_exposure_or_state_event_alone_is_trigger') is not False or trig.get('deterministic_system_owned_outcome') != 'SYSTEM_TRIGGER_BINDING_MISSING_AUTO_REMEDIABLE' or (trig.get('explicit_system_trigger_materialization_required') is not True) or (trig.get('new_visual_control_for_system_only_operation') is not False) or (trig.get('authority_gap_minimum_materially_distinct_viable_behaviors') != 2) or (trig.get('missing_trigger_syntax_alone_is_authority_gap') is not False):
        failures.append('control_vs_system_trigger_resolution_incomplete')
    pcs = inv.get('PRODUCER_CONSUMER_SCHEMA_IDENTITY') or {}
    if pcs.get('canonical_field_name_exact') is not True or pcs.get('field_type_exact') is not True or pcs.get('alias_or_legacy_field_fallback') is not False or (pcs.get('mismatch') != 'PRODUCER_CONSUMER_SCHEMA_MISMATCH') or (pcs.get('stage02_audit_event_canonical_field') != 'audit_event_uid') or (pcs.get('stage02_audit_event_legacy_alias_forbidden') != 'event_uid'):
        failures.append('producer_consumer_schema_identity_incomplete')
    hist = inv.get('NO_HISTORY_PRODUCT_VALUE_FALLBACK') or {}
    if hist.get('historical_commit_or_generated_output_may_fill_current_product_value') is not False or hist.get('historical_stage_result_may_receive_current_completion_credit') is not False or hist.get('fresh_replay_source') != 'REGISTERED_IMMUTABLE_INPUTS_PLUS_CURRENT_AUTHORITY':
        failures.append('no_history_product_value_fallback_incomplete')
    order = inv.get('TASK_LAYER_EFFECTFUL_TRANSITION_ORDER') or {}
    if order.get('materializer_or_environment_may_force_primary_task_layer') is not False or order.get('nearby_stage_or_retry_may_skip_resolution') is not False or len(order.get('required_order') or []) != 6:
        failures.append('task_layer_effectful_transition_order_incomplete')
    vm = inv.get('VISUAL_DESIGN_PROFILE_MATERIALIZATION_COMPLETENESS') or {}
    vm_req = {'VISUAL_DESIGN_SPEC_PACKAGE', 'VISUAL_GEOMETRY_CONTRACT', 'VISUAL_PREVIEW_EVIDENCE', 'VISUAL_CHANGESET', 'VISUAL_INTERACTION_TOPOLOGY_BINDING', 'FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT', 'VISUAL_REFERENCE_ANNOTATION', 'VISUAL_INHERITANCE_MATRIX', 'VISUAL_SCENARIO_EVIDENCE_SET'}
    if set(vm.get('required_stage03_outputs') or []) != vm_req or vm.get('every_required_output_has_explicit_producer') is not True or vm.get('mother_required_output_may_be_omitted_by_profile') is not False or (vm.get('structural_only_preview_may_satisfy_human_visual_review') is not False) or (vm.get('atomic_workbench_visual_binding_required') is not True) or (vm.get('unresolved_authority_is_authority_absent') is not False) or (vm.get('unresolved_applicable_visual_authority_in_denominator_required') is not True) or (vm.get('profile_materialization_undercoverage') != 'BLOCK'):
        failures.append('visual_design_profile_materialization_incomplete')
    rv = inv.get('REVIEW_VS_CLOSURE_SEPARATION') or {}
    if rv.get('review_completion_is_evidence_of_review_only') is not True or rv.get('review_completion_may_override_open_blockers') is not False:
        failures.append('review_closure_separation_incomplete')
    bp = load(root, '10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml')
    bc = bp.get('stage_execution_invariant_contract') or {}
    if bc.get('registry_uid') != 'REG-STAGE-EXECUTION-INVARIANT-001' or bc.get('validator_uid') != 'VAL-GOV-035' or bc.get('observed_stage_does_not_limit_scope') is not True:
        failures.append('acceptance_blueprint_binding_missing')
    life = load(root, '10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml')
    if life.get('stage_execution_invariant_ref') != 'REG-STAGE-EXECUTION-INVARIANT-001':
        failures.append('lifecycle_common_binding_missing')
    cs = (life.get('cross_stage_invariants') or {}).get('stage_execution_invariant_hardening') or {}
    if cs.get('applies_to_all_stages') is not True:
        failures.append('lifecycle_cross_stage_scope_missing')
    st3 = next((x for x in life.get('stages') or [] if x.get('stage_uid') == 'STAGE-03'), {})
    stage3_required = {'VISUAL_DESIGN_SPEC_PACKAGE', 'VISUAL_GEOMETRY_CONTRACT', 'VISUAL_PREVIEW_EVIDENCE', 'VISUAL_CHANGESET', 'VISUAL_INTERACTION_TOPOLOGY_BINDING', 'FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT', 'VISUAL_REFERENCE_ANNOTATION', 'VISUAL_INHERITANCE_MATRIX', 'VISUAL_SCENARIO_EVIDENCE_SET'}
    if not stage3_required.issubset(set(st3.get('outputs') or [])):
        failures.append('stage03_mother_required_visual_outputs_missing')
    st3prod = st3.get('output_producers') or {}
    if any((not st3prod.get(x) for x in stage3_required)):
        failures.append('stage03_required_output_producer_missing')
    if not {'WEB-GOV-01-S080', 'WEB-GOV-01-S087'}.issubset(set(st3.get('required_normative_section_uids') or [])):
        failures.append('stage03_visual_materialization_normative_binding_missing')
    va = st3.get('visual_materialization_gate') or {}
    if va.get('required') is not True or va.get('structural_only_preview_may_reach_visual_review') is not False or va.get('explicit_atomic_workbench_visual_binding_required') is not True or (va.get('unresolved_visual_authority_is_authority_absent') is not False) or (va.get('unresolved_visual_authority_must_enter_current_problem_denominator') is not True):
        failures.append('stage03_visual_materialization_gate_incomplete')
    st2 = next((x for x in life.get('stages') or [] if x.get('stage_uid') == 'STAGE-02'), {})
    if (st2.get('stage_execution_invariant_gate') or {}).get('required') is not True:
        failures.append('stage02_empirical_gate_binding_missing')
    expected_stage_ids = {f'STAGE-{i:02d}' for i in range(1, 12)}
    stage_map = {s.get('stage_uid'): s for s in life.get('stages') or []}
    if set(stage_map) != expected_stage_ids:
        failures.append('stage_execution_optimization_stage_set_drift')
    else:
        for sid in sorted(expected_stage_ids):
            sg = stage_map[sid].get('canonical_execution_optimization_gate') or {}
            if sg.get('required') is not True or sg.get('invariant_uid') != 'GOV-INV-CANONICAL-STAGE-EXECUTION-OPTIMIZATION-001' or sg.get('explicit_stage_binding_required') is not True or (sg.get('raw_plus_legal_successor_overlay_is_effective_truth') is not True) or (sg.get('authority_gap_minimum_distinct_behaviors') != 2):
                failures.append('stage_execution_optimization_explicit_binding_missing:' + sid)
    opt = st2.get('canonical_execution_optimization_gate') or {}
    if opt.get('required') is not True or opt.get('raw_plus_legal_successor_overlay_is_effective_truth') is not True or opt.get('authority_gap_minimum_distinct_behaviors') != 2:
        failures.append('stage02_execution_optimization_gate_missing')
    idx = load(root, '10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml')
    if idx.get('stage_execution_invariant_registry_ref') != 'REG-STAGE-EXECUTION-INVARIANT-001':
        failures.append('construction_index_binding_missing')
    ur = idx.get('universal_rules') or {}
    for k in ['port_exposure_as_trigger', 'state_event_as_trigger_without_explicit_binding', 'semantic_similarity_binding_creation', 'non_current_final_locked_authority_use', 'input_authority_architecture_gap_ai_autofill', 'required_evidence_ledger_claim_without_physical_artifact', 'validator_stale_schema_path_or_enum', 'stale_current_snapshot_after_successor_acceptance', 'receipt_reuse_after_denominator_change', 'unique_current_authority_evidence_skip', 'review_completion_as_stage_closure']:
        if ur.get(k) != 'BLOCK':
            failures.append('construction_universal_rule_not_block:' + k)
    crossmat = inv.get('CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS') or {}
    if crossmat.get('invariant_uid') != 'GOV-INV-CROSS-STAGE-MATERIALIZATION-CONSUMER-READINESS-001':
        failures.append('cross_stage_materialization_invariant_uid_missing')
    if crossmat.get('required_artifact') != 'CROSS_STAGE_HANDOFF_READINESS_LEDGER' or crossmat.get('applies_to_all_registered_stages') is not True:
        failures.append('cross_stage_materialization_contract_missing')
    if crossmat.get('reference_presence_is_materialization') is not False or crossmat.get('physical_materialization_required') is not True:
        failures.append('reference_vs_materialization_separation_missing')
    for key in ('parse_required','schema_version_identity_required','required_field_completeness_required','denominator_inclusion_required','successor_consumer_readiness_required','successor_required_input_universe_reconciliation_before_stage_exit'):
        if crossmat.get(key) is not True:
            failures.append('cross_stage_readiness_flag_missing:' + key)
    if set(crossmat.get('required_row_fields') or []) != set(HANDOFF_REQUIRED_FIELDS_FOR_VALIDATOR):
        failures.append('cross_stage_handoff_row_schema_drift')
    if crossmat.get('historical_or_reference_only_completion_credit') != 0:
        failures.append('reference_only_completion_credit_leak')
    if crossmat.get('downstream_discovered_upstream_gap') != 'STOP_REENTER_EARLIEST_OWNER_MARK_DESCENDANTS_REVERIFY_REQUIRED':
        failures.append('upstream_reentry_disposition_missing')

    bcross = bp.get('cross_stage_materialization_consumer_readiness_contract') or {}
    if bcross.get('required') is not True or bcross.get('audit_item_uid') != 'AUD-GOV-014' or bcross.get('validator_uid') != 'VAL-GOV-035':
        failures.append('acceptance_cross_stage_readiness_binding_missing')
    catalog = load(root, '10_REGISTRY/AUDIT_CATALOG.yaml')
    aud14 = next((x for x in catalog.get('items') or [] if x.get('audit_item_uid') == 'AUD-GOV-014'), None)
    if not isinstance(aud14, dict) or aud14.get('audit_type') != 'CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS' or aud14.get('validator_uid') != 'VAL-GOV-035':
        failures.append('audit_catalog_cross_stage_item_missing')

    for sid, stage in stage_map.items():
        gate = stage.get('cross_stage_materialization_gate') or {}
        if gate.get('required') is not True or gate.get('invariant_uid') != 'GOV-INV-CROSS-STAGE-MATERIALIZATION-CONSUMER-READINESS-001':
            failures.append('cross_stage_gate_missing:' + str(sid))
        for key in ('reference_resolution_required','physical_materialization_required','parse_schema_required_field_completeness_required','denominator_inclusion_required','successor_consumer_readiness_required','successor_required_input_reconciliation_before_exit'):
            if gate.get(key) is not True:
                failures.append('cross_stage_gate_flag_missing:' + str(sid) + ':' + key)
        if gate.get('reference_only_completion_credit') != 0:
            failures.append('cross_stage_reference_only_credit_leak:' + str(sid))

    st1 = stage_map.get('STAGE-01') or {}
    s1g = st1.get('source_capture_materialization_gate') or {}
    if s1g.get('required') is not True or s1g.get('source_declared_registry_manifest_candidate_anchor_dependency_must_be_physical_or_gap') is not True or s1g.get('reference_only_source_dependency_may_receive_stage1_completion_credit') is not False or s1g.get('missing_required_physical_owner_disposition') != 'SOURCE_CAPTURE_GAP':
        failures.append('stage01_source_capture_materialization_gate_incomplete')
    st2x = stage_map.get('STAGE-02') or {}
    s2g = st2x.get('successor_readiness_gate') or {}
    if s2g.get('required') is not True or s2g.get('functional_gap_zero_substitutes_stage03_visual_dependency_readiness') is not False or s2g.get('stage03_required_visual_dependency_reconciliation_required') is not True:
        failures.append('stage02_successor_readiness_gate_incomplete')
    st3x = stage_map.get('STAGE-03') or {}
    s3g = st3x.get('visual_materialization_gate') or {}
    if s3g.get('applicable_visual_anchor_registry_must_be_nonempty') is not True or s3g.get('declared_visual_candidate_requires_physical_evidence') is not True or s3g.get('single_overview_may_substitute_required_scenarios') is not False or s3g.get('missing_required_anchor_or_candidate_blocks_human_visual_review') is not True:
        failures.append('stage03_anchor_candidate_scenario_readiness_gate_incomplete')

    for key in ('reference_only_required_dependency_completion','physical_required_input_missing','required_input_schema_or_version_mismatch','required_input_required_field_incomplete','successor_required_edge_denominator_omission','successor_consumer_readiness_unproven','applicable_visual_anchor_registry_empty','declared_visual_candidate_without_physical_evidence','multi_state_visual_single_overview_without_explicit_simultaneous_state_proof'):
        if ur.get(key) != 'BLOCK':
            failures.append('construction_universal_cross_stage_rule_not_block:' + key)
    return {'status': 'PASS' if not failures else 'FAIL', 'invariant_count': len(inv), 'stage_count': len(scope.get('applies_to_stages') or []), 'failures': failures}
if __name__ == '__main__':
    out = validate()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if out['status'] == 'PASS' else 1)
