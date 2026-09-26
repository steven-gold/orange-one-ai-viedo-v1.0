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
    required = ['RELATION_SEMANTIC_SEPARATION', 'GAP_REMEDIATION_ADMISSIBILITY', 'CURRENT_AUTHORITY_ADMISSIBILITY', 'REQUIRED_EVIDENCE_MATERIALIZATION', 'VALIDATOR_SCHEMA_SEMANTICS', 'UNRESOLVED_PRESERVATION', 'SUCCESSOR_CURRENT_ATOMIC_PROJECTION', 'BLOCKER_DENOMINATOR_AND_RECEIPT', 'AUTHORITY_EVIDENCE_CONSUMPTION', 'FUNCTIONAL_CONTRACT_COMPLETENESS', 'STAGE_ENTRY_PRECHECK', 'IMPLEMENTATION_DEVIATION_FEEDBACK', 'REVIEW_VS_CLOSURE_SEPARATION', 'CANONICAL_STAGE_EXECUTION_PREFLIGHT', 'EFFECTIVE_CONTRACT_OVERLAY', 'ROLE_SAFE_FUNCTIONAL_CLOSURE', 'DEPENDENCY_ORDERED_INCREMENTAL_RECONCILIATION', 'COMMON_ENGINE_DEFECT_INTERRUPT', 'GENERATED_OUTPUT_PERSISTENCE', 'CONTROL_VS_SYSTEM_TRIGGER_RESOLUTION', 'PRODUCER_CONSUMER_SCHEMA_IDENTITY', 'NO_HISTORY_PRODUCT_VALUE_FALLBACK', 'TASK_LAYER_EFFECTFUL_TRANSITION_ORDER', 'VISUAL_DESIGN_PROFILE_MATERIALIZATION_COMPLETENESS', 'NORMATIVE_EXECUTION_MATRIX', 'CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS', 'DETERMINISTIC_STAGE_AUDIT']
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
    matrix = inv.get('NORMATIVE_EXECUTION_MATRIX') or {}
    matrix_chain={'NORMATIVE_SECTION','REQUIRED_ARTIFACT','REQUIRED_ROW','REQUIRED_FIELD','VALIDATOR','CLOSURE_GATE'}
    matrix_fields={'matrix_row_uid','normative_section_uid','requirement_uid','required_artifact_type','artifact_ref','artifact_owner','row_denominator_source','row_identity','field_path','applicability','validator_uid','validator_check_id','evidence_ref','closure_gate','failure_disposition','reentry_owner'}
    if matrix.get('invariant_uid')!='GOV-INV-NORMATIVE-EXECUTION-MATRIX-001' or matrix.get('required_before_first_effectful_operation') is not True or matrix.get('required_for_stage_or_capability_closure') is not True:
        failures.append('normative_execution_matrix_core_contract_missing')
    if set(matrix.get('chain') or [])!=matrix_chain or set(matrix.get('matrix_row_required_fields') or [])!=matrix_fields:
        failures.append('normative_execution_matrix_schema_incomplete')
    for key in ('every_required_normative_section_must_be_represented','every_required_artifact_must_be_represented','every_required_evidence_type_must_be_represented','every_applicable_governed_row_must_be_represented','every_required_field_requires_validator_binding','every_validator_check_requires_closure_gate_binding','validators_scanners_classifiers_materializers_and_closure_consumers_share_matrix_truth','destructive_missing_field_regression_required'):
        if matrix.get(key) is not True:
            failures.append('normative_execution_matrix_flag_missing:'+key)
    if matrix.get('validator_local_required_field_subset')!='BLOCK' or matrix.get('downstream_discovered_matrix_undercoverage_disposition')!='STOP_REENTER_EARLIEST_OWNER_MARK_DESCENDANTS_REVERIFY_REQUIRED':
        failures.append('normative_execution_matrix_fail_closed_disposition_missing')
    rng = inv.get('EXPLICIT_STAGE_RANGE_EXECUTION') or {}
    if rng.get('invariant_uid') != 'GOV-INV-EXPLICIT-STAGE-RANGE-EXECUTION-001' or rng.get('requested_range_is_execution_authority') is not True or rng.get('range_is_inclusive') is not True:
        failures.append('explicit_stage_range_execution_core_contract_missing')
    for key in ('single_stage_request_executes_only_that_stage','multi_stage_request_executes_every_registered_stage_in_range','normal_pass_auto_continues_within_requested_range','checkpoint_does_not_require_new_user_instruction','page_lifecycle_execution_mode_preserves_one_governed_unit_identity_across_requested_range'):
        if rng.get(key) is not True:
            failures.append('explicit_stage_range_execution_flag_missing:' + key)
    if rng.get('system_selected_batch_size') != 'FORBIDDEN' or rng.get('system_expand_range') != 'BLOCK' or rng.get('system_shrink_range') != 'BLOCK' or rng.get('system_skip_in_range_stage') != 'BLOCK' or rng.get('system_split_range_and_reprompt_between_normal_stages') != 'BLOCK':
        failures.append('explicit_stage_range_execution_scope_control_incomplete')
    if rng.get('unregistered_range_endpoint_may_be_silently_clamped') is not False or rng.get('stage_boundary_manual_continue_prompt') != 'FORBIDDEN':
        failures.append('explicit_stage_range_execution_silent_clamp_or_reprompt_not_blocked')
    hix = inv.get('DETERMINISTIC_HUMAN_INTERACTION_BOUNDARY') or {}
    if hix.get('invariant_uid') != 'GOV-INV-DETERMINISTIC-HUMAN-INTERACTION-001' or hix.get('same_current_state_same_user_facing_action_set') is not True:
        failures.append('deterministic_human_interaction_core_contract_missing')
    if hix.get('formal_approval_is_user_decision_required') is not False or hix.get('deterministic_successor_may_be_presented_as_user_choice') is not False or hix.get('deterministic_reentry_may_be_presented_as_user_choice') is not False:
        failures.append('approval_decision_reentry_separation_incomplete')
    if hix.get('user_choice_allowed_only_when_materially_distinct_legal_alternative_count_gte') != 2 or hix.get('ai_may_offer_gate_bypass') is not False or hix.get('ai_may_offer_future_stage_preproduction') is not False:
        failures.append('deterministic_user_choice_guard_incomplete')
    interactions = hix.get('stage_interaction_contracts') or {}
    if set(interactions) != set(expected):
        failures.append('stage_interaction_contract_set_not_all_11')
    else:
        s4 = interactions.get('STAGE-04') or {}
        if s4.get('default_mode') != 'FORMAL_APPROVAL' or s4.get('evidence_type') != 'DESIGN_APPROVAL_EVIDENCE' or s4.get('approval_consumption_operation') != 'DESIGN_FREEZE_VALIDATE' or s4.get('next_stage_after_closure') != 'STAGE-05' or s4.get('alternative_execution_path_allowed') is not False:
            failures.append('stage04_formal_approval_boundary_incomplete')
        if set(s4.get('formal_review_actions') or []) != {'APPROVE','REJECT','REQUEST_CHANGES'}:
            failures.append('stage04_formal_approval_action_set_drift')
    det = inv.get('DETERMINISTIC_STAGE_AUDIT') or {}
    expected_statuses = {'NOT_STARTED','READY_FOR_EXECUTION','IN_PROGRESS','BLOCKED','REVERIFY_REQUIRED','CURRENT_STATE_CONFLICT','EXECUTION_COMPLETE_CLOSURE_PENDING','CLOSED_PASS','CLOSED_FAIL','SNAPSHOT_INVALIDATED'}
    snapshot_required = {'repository','branch','exact_head_sha','tree_sha','governance_branch','governance_head_sha','governance_uid','governance_revision','registry_revision','lifecycle_registry_revision','stage_uid','work_unit_uid','governed_unit_uid','source_authority_uid','audit_scope','audit_started_at','denominator_hash','authority_set_hash','evidence_set_hash','validator_set_hash','audit_engine_version','audit_contract_version'}
    if det.get('invariant_uid') != 'GOV-INV-DETERMINISTIC-STAGE-AUDIT-001' or det.get('applies_to_all_registered_stages') is not True or det.get('same_complete_input_same_complete_result') is not True:
        failures.append('deterministic_stage_audit_core_contract_missing')
    if set((det.get('audit_snapshot_contract') or {}).get('required_fields') or []) != snapshot_required:
        failures.append('deterministic_stage_audit_snapshot_schema_incomplete')
    if set(det.get('canonical_stage_statuses') or []) != expected_statuses:
        failures.append('deterministic_stage_status_vocabulary_drift')
    conflict = det.get('current_state_conflict_contract') or {}
    matrix_det = det.get('normative_execution_matrix_contract') or {}
    if conflict.get('stage_pass_allowed') is not False or (det.get('historical_evidence_contract') or {}).get('historical_pass_is_current_pass') is not False:
        failures.append('deterministic_conflict_or_history_rule_incomplete')
    for key in ('pass_requires_completed_operation_set_exact_registered_stage_operations','pass_requires_current_execution_state_closed','normalized_evidence_operation_set_must_equal_current_execution_state_completed_operation_set'):
        if conflict.get(key) is not True:
            failures.append('deterministic_current_state_consistency_flag_missing:' + key)
    if conflict.get('pass_with_pending_or_pre_execution_current_operation') != 'BLOCK' or conflict.get('terminal_receipt_or_outer_run_success_may_override_conflict') is not False:
        failures.append('deterministic_current_state_conflict_override_guard_missing')
    for key in ('current_matrix_required_before_first_effectful_operation','current_matrix_required_before_stage_closure','matrix_file_must_be_nonempty_parseable_mapping','matrix_rows_must_be_nonempty','matrix_identity_must_match_current_governance_stage_work_unit','matrix_validation_must_run_again_at_terminal_closure'):
        if matrix_det.get(key) is not True:
            failures.append('deterministic_matrix_terminal_guard_missing:' + key)
    if matrix_det.get('terminal_receipt_or_outer_run_success_may_override_invalid_matrix') is not False:
        failures.append('deterministic_matrix_override_guard_missing')
    if (det.get('lifecycle_resolution_contract') or {}).get('stage_denominator_source') != 'CURRENT_LIFECYCLE_REGISTRY' or (det.get('lifecycle_resolution_contract') or {}).get('hardcoded_operation_count_as_reusable_policy') != 'BLOCK':
        failures.append('deterministic_dynamic_lifecycle_resolution_missing')
    stage_contracts = det.get('stage_contracts') or {}
    if set(stage_contracts) != set(expected):
        failures.append('deterministic_stage_contract_set_not_all_11')
    else:
        for sid in expected:
            if (stage_contracts.get(sid) or {}).get('lifecycle_registry_is_denominator_source') is not True:
                failures.append('deterministic_stage_denominator_binding_missing:' + sid)
    term = det.get('canonical_terminology_contract') or {}
    if term.get('stage_capability_must_equal_lifecycle_registry_name') is not True or term.get('authorized_not_applicable_token') != 'AUTHORIZED_NOT_APPLICABLE' or term.get('noncanonical_stage_status_or_capability_name') != 'BLOCK':
        failures.append('deterministic_canonical_terminology_contract_incomplete')
    forbidden_aliases = set(term.get('forbidden_aliases') or [])
    if forbidden_aliases != {'STAGE_NOT_PASS','AUTHORIZED_NA','VERIFICATION','BUILD_RELEASE'}:
        failures.append('deterministic_forbidden_alias_registry_drift')
    if (det.get('deterministic_decision_table') or {}).get('source_document_pass_does_not_imply_stage_pass') is not True:
        failures.append('source_document_stage_pass_separation_missing')
    if set((stage_contracts.get('STAGE-06') or {}).get('allowed_test_results') or []) != {'PASS','FAIL','BLOCKED','AUTHORIZED_NOT_APPLICABLE'}:
        failures.append('stage06_authorized_not_applicable_token_drift')
    indep = det.get('auditor_independence_acceptance') or {}
    if indep.get('independent_evaluator_count') != 3 or indep.get('identical_finding_set_percent') != 100 or indep.get('identical_stage_status_percent') != 100 or indep.get('different_result_disposition') != 'AUDIT_DETERMINISM_CONTRACT_FAILURE':
        failures.append('auditor_independence_acceptance_incomplete')
    repeat = det.get('repeatability_acceptance') or {}
    if repeat.get('same_evaluator_repeat_count') != 3 or repeat.get('identical_result_required') is not True:
        failures.append('audit_repeatability_contract_incomplete')
    if len(det.get('required_negative_test_classes') or []) < 12:
        failures.append('deterministic_negative_test_denominator_incomplete')
    audit_steps_path = root.parents[3] / 'governance/execution-domains/AUDIT/STEPS.yaml'
    audit_steps_doc = yaml.safe_load(audit_steps_path.read_text(encoding='utf-8')) or {}
    dac = audit_steps_doc.get('deterministic_audit_contract') or {}
    if dac.get('invariant_ref') != 'GOV-INV-DETERMINISTIC-STAGE-AUDIT-001' or dac.get('same_complete_input_same_complete_result') is not True or dac.get('canonical_owner_required_for_every_non_pass') is not True or dac.get('earliest_legal_reentry_required_for_every_non_pass') is not True:
        failures.append('audit_steps_deterministic_contract_missing')
    audit_profile_path = root.parents[3] / 'governance/execution-domains/AUDIT_PROFILE.yaml'
    audit_profile = yaml.safe_load(audit_profile_path.read_text(encoding='utf-8')) or {}
    if audit_profile.get('stage_deterministic_audit_invariant_ref') != 'GOV-INV-DETERMINISTIC-STAGE-AUDIT-001' or set(audit_profile.get('stage_canonical_statuses') or []) != expected_statuses:
        failures.append('audit_profile_deterministic_contract_missing')
    steps_path = root.parents[3] / 'governance/execution-domains/STAGE/STEPS.yaml'
    steps = yaml.safe_load(steps_path.read_text(encoding='utf-8')) or {}
    mc = steps.get('normative_execution_matrix_contract') or {}
    if mc.get('outputs')!=['NORMATIVE_EXECUTION_MATRIX'] or mc.get('denominator')!='COMPLETE_APPLICABLE_NORMATIVE_ARTIFACT_ROW_FIELD_UNIVERSE':
        failures.append('stage_steps_normative_execution_matrix_contract_missing')
    rc = steps.get('stage_range_execution_contract') or {}
    if rc.get('invariant_ref') != 'GOV-INV-EXPLICIT-STAGE-RANGE-EXECUTION-001' or rc.get('interaction_invariant_ref') != 'GOV-INV-DETERMINISTIC-HUMAN-INTERACTION-001' or rc.get('range_is_inclusive') is not True:
        failures.append('stage_steps_range_execution_contract_missing')
    if rc.get('execution_scope_may_be_system_selected') is not False or rc.get('normal_stage_boundary_user_prompt') != 'FORBIDDEN' or rc.get('normal_stage_pass_behavior') != 'AUTO_CONTINUE_TO_NEXT_STAGE_WITHIN_REQUESTED_RANGE':
        failures.append('stage_steps_range_execution_behavior_drift')
    er = steps.get('execution_rules') or {}
    for key in ('normative_execution_matrix_required_before_first_effectful_operation','normative_execution_matrix_required_before_stage_closure','validators_must_consume_current_matrix_truth'):
        if er.get(key) is not True:
            failures.append('stage_steps_matrix_rule_missing:'+key)
    if er.get('validator_local_required_field_subset')!='FORBIDDEN':
        failures.append('stage_steps_local_subset_not_forbidden')
    vm = inv.get('VISUAL_DESIGN_PROFILE_MATERIALIZATION_COMPLETENESS') or {}
    vm_req = {'VISUAL_DESIGN_SPEC_PACKAGE', 'VISUAL_GEOMETRY_CONTRACT', 'VISUAL_PREVIEW_EVIDENCE', 'VISUAL_CHANGESET', 'VISUAL_INTERACTION_TOPOLOGY_BINDING', 'FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT', 'VISUAL_REFERENCE_ANNOTATION', 'VISUAL_INHERITANCE_MATRIX', 'VISUAL_SCENARIO_EVIDENCE_SET'}
    if set(vm.get('required_stage03_outputs') or []) != vm_req or vm.get('every_required_output_has_explicit_producer') is not True or vm.get('mother_required_output_may_be_omitted_by_profile') is not False or (vm.get('structural_only_preview_may_satisfy_human_visual_review') is not False) or (vm.get('atomic_workbench_visual_binding_required') is not True) or (vm.get('unresolved_authority_is_authority_absent') is not False) or (vm.get('unresolved_applicable_visual_authority_in_denominator_required') is not True) or (vm.get('profile_materialization_undercoverage') != 'BLOCK'):
        failures.append('visual_design_profile_materialization_incomplete')
    rv = inv.get('REVIEW_VS_CLOSURE_SEPARATION') or {}
    if rv.get('review_completion_is_evidence_of_review_only') is not True or rv.get('review_completion_may_override_open_blockers') is not False:
        failures.append('review_closure_separation_incomplete')
    if rv.get('stage_exit_owner_granularity') != 'PAGE_OR_SYSTEM_LOGIC_UNIT' or rv.get('same_stage_uid_does_not_create_cross_unit_exit_barrier') is not True or rv.get('unrelated_page_or_system_unit_may_block_stage_exit') is not False or rv.get('cross_unit_blocking_requires_explicit_required_dependency_edge') is not True:
        failures.append('independent_governed_unit_stage_exit_invariant_incomplete')
    handoff = inv.get('CROSS_STAGE_MATERIALIZED_HANDOFF') or {}
    if handoff:
        if handoff.get('successor_input_universe_scope') != 'CURRENT_GOVERNED_UNIT' or handoff.get('cross_unit_successor_input_requires_explicit_required_dependency_edge') is not True:
            failures.append('cross_stage_handoff_scope_not_current_governed_unit')
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
    lifecycle_canonical_names = {s.get('stage_uid'): s.get('name') for s in life.get('stages') or []}
    for sid in expected:
        contract_name = (stage_contracts.get(sid) or {}).get('capability')
        if contract_name != lifecycle_canonical_names.get(sid):
            failures.append('deterministic_stage_capability_name_drift:' + sid)
    if set(stage_map) != expected_stage_ids:
        failures.append('stage_execution_optimization_stage_set_drift')
    else:
        expected_admission={'PREDECESSOR_STAGE_TERMINAL_PASS','PREDECESSOR_CURRENT_NORMATIVE_EXECUTION_MATRIX_PASS','PREDECESSOR_CURRENT_STATE_EVIDENCE_CONSISTENCY_PASS','CROSS_STAGE_HANDOFF_READINESS_PASS','SUCCESSOR_INPUT_MATERIALIZATION_PASS','SUCCESSOR_EFFECTFUL_OPERATION_BINDING_READINESS_PASS','SUCCESSOR_ENTRY_GATE_PASS'}
        if set((life.get('universal_stage_stepwise_execution_contract') or {}).get('stage_successor_admission_requires') or []) != expected_admission:
            failures.append('universal_stage_successor_admission_contract_incomplete')
        for successor_sid, classes in binding_requirements.items():
            if successor_sid not in stage_map:
                failures.append('cross_stage_binding_requirement_unknown_successor:' + successor_sid)
                continue
            opmap=binding_maps.get(successor_sid) or {}
            if successor_sid!='STAGE-02' and successor_sid not in binding_maps:
                failures.append('cross_stage_binding_operation_map_missing:' + successor_sid)
            if successor_sid in binding_maps and set(opmap) != set(classes):
                failures.append('cross_stage_binding_operation_map_class_drift:' + successor_sid)
            successor_ops=set(stage_map[successor_sid].get('operations') or [])
            for cls,op in opmap.items():
                if op not in successor_ops:
                    failures.append('cross_stage_binding_operation_not_registered:' + successor_sid + ':' + cls + ':' + str(op))
        for sid in sorted(expected_stage_ids):
            sg = stage_map[sid].get('canonical_execution_optimization_gate') or {}
            if sg.get('required') is not True or sg.get('invariant_uid') != 'GOV-INV-CANONICAL-STAGE-EXECUTION-OPTIMIZATION-001' or sg.get('explicit_stage_binding_required') is not True or (sg.get('raw_plus_legal_successor_overlay_is_effective_truth') is not True) or (sg.get('authority_gap_minimum_distinct_behaviors') != 2):
                failures.append('stage_execution_optimization_explicit_binding_missing:' + sid)
    opt = st2.get('canonical_execution_optimization_gate') or {}
    if opt.get('required') is not True or opt.get('raw_plus_legal_successor_overlay_is_effective_truth') is not True or opt.get('authority_gap_minimum_distinct_behaviors') != 2:
        failures.append('stage02_execution_optimization_gate_missing')
    idxinv = inv.get('INDEXED_INCREMENTAL_VALIDATION') or {}
    if idxinv.get('impact_and_reverse_dependency_index_loading_required') is not True:
        failures.append('indexed_validation_loading_contract_missing')
    if idxinv.get('validation_impact_index_required') is not True or idxinv.get('reverse_dependency_index_required') is not True:
        failures.append('indexed_validation_dependency_contract_missing')
    if idxinv.get('index_may_skip_required_impacted_validator') is not False or idxinv.get('index_drift_full_sweep_required_before_freeze') is not True:
        failures.append('indexed_validation_fail_closed_contract_missing')
    crossmat = inv.get('CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS') or {}
    if crossmat.get('invariant_uid') != 'GOV-INV-CROSS-STAGE-MATERIALIZATION-CONSUMER-READINESS-001':
        failures.append('cross_stage_materialization_invariant_uid_missing')
    if crossmat.get('required_artifact') != 'CROSS_STAGE_HANDOFF_READINESS_LEDGER' or crossmat.get('applies_to_all_registered_stages') is not True:
        failures.append('cross_stage_materialization_contract_missing')
    if crossmat.get('reference_presence_is_materialization') is not False or crossmat.get('physical_materialization_required') is not True:
        failures.append('reference_vs_materialization_separation_missing')
    for key in ('parse_required','schema_version_identity_required','required_field_completeness_required','denominator_inclusion_required','successor_consumer_readiness_required','successor_required_input_universe_reconciliation_before_stage_exit','successor_effectful_operation_binding_universe_reconciliation_required','authorized_not_applicable_requires_authority_evidence','current_normative_execution_matrix_nonempty_and_valid_before_exit','current_state_evidence_terminal_consistency_required_before_exit'):
        if crossmat.get(key) is not True:
            failures.append('cross_stage_readiness_flag_missing:' + key)
    if crossmat.get('single_canonical_handoff_artifact_only') is not True or crossmat.get('parallel_readiness_ledger_or_stage_local_substitute') != 'BLOCK':
        failures.append('cross_stage_single_canonical_handoff_contract_missing')
    if crossmat.get('successor_execution_binding_universe_source') != 'CURRENT_SUCCESSOR_LIFECYCLE_OPERATIONS_PLUS_CURRENT_AUTHORITY_AND_APPLICABILITY' or crossmat.get('successor_execution_binding_may_be_invented_by_consumer') is not False or crossmat.get('successor_execution_binding_may_be_inferred_from_product_need_alone') is not False or crossmat.get('stub_placeholder_or_recommended_target_may_receive_readiness_credit') is not False:
        failures.append('cross_stage_execution_binding_authority_contract_incomplete')
    if crossmat.get('technology_stack_recommendation_may_create_execution_authority') is not False or crossmat.get('implementation_language_framework_or_package_manager_may_be_ai_selected_when_unbound') is not False or crossmat.get('successor_effectful_operation_prerequisite_binding_must_be_derived_from_current_authority') is not True or crossmat.get('enumerated_binding_classes_are_minimum_not_exhaustive_when_registered_operation_has_additional_authorized_prerequisites') is not True:
        failures.append('cross_stage_dynamic_prerequisite_authority_contract_incomplete')
    if crossmat.get('authorized_not_applicable_token') != 'AUTHORIZED_NOT_APPLICABLE' or crossmat.get('terminal_receipt_or_outer_run_success_may_override_matrix_or_state_conflict') is not False:
        failures.append('cross_stage_na_or_override_contract_incomplete')
    if set(crossmat.get('required_row_fields') or []) != set(HANDOFF_REQUIRED_FIELDS_FOR_VALIDATOR):
        failures.append('cross_stage_handoff_row_schema_drift')
    binding_fields={'binding_uid','consuming_operation_uid','binding_class','applicability','canonical_owner_or_authority_ref','authority_evidence_ref','target_identity','resolution_status','denominator_inclusion_status','consumer_readiness_status'}
    if set(crossmat.get('successor_execution_binding_required_row_fields') or []) != binding_fields:
        failures.append('cross_stage_execution_binding_row_schema_drift')
    binding_requirements=crossmat.get('successor_execution_binding_requirements') or {}
    binding_maps=crossmat.get('successor_execution_binding_operation_map') or {}
    if set(binding_requirements) != {f'STAGE-{i:02d}' for i in range(2,12)}:
        failures.append('cross_stage_execution_binding_stage_requirement_set_drift')
    if set(binding_maps) != {f'STAGE-{i:02d}' for i in range(3,12)}:
        failures.append('cross_stage_execution_binding_operation_map_stage_set_drift')
    stage05_stack_required={'IMPLEMENTATION_LANGUAGE_AUTHORITY','FRONTEND_FRAMEWORK_AUTHORITY','BACKEND_FRAMEWORK_AUTHORITY','PACKAGE_MANAGER_AUTHORITY'}
    if not stage05_stack_required.issubset(set(binding_requirements.get('STAGE-05') or [])):
        failures.append('stage05_implementation_stack_authority_denominator_incomplete')
    if not stage05_stack_required.issubset(set((binding_maps.get('STAGE-05') or {}).keys())):
        failures.append('stage05_implementation_stack_operation_binding_map_incomplete')
    if crossmat.get('historical_or_reference_only_completion_credit') != 0:
        failures.append('reference_only_completion_credit_leak')
    if crossmat.get('downstream_discovered_upstream_gap') != 'STOP_REENTER_EARLIEST_OWNER_MARK_DESCENDANTS_REVERIFY_REQUIRED':
        failures.append('upstream_reentry_disposition_missing')

    bcross = bp.get('cross_stage_materialization_consumer_readiness_contract') or {}
    if bcross.get('required') is not True or bcross.get('audit_item_uid') != 'AUD-GOV-014' or bcross.get('validator_uid') != 'VAL-GOV-035':
        failures.append('acceptance_cross_stage_readiness_binding_missing')
    if bcross.get('successor_effectful_operation_binding_denominator_required') is not True or bcross.get('artifact_input_presence_alone_may_grant_consumer_readiness') is not False or bcross.get('implementation_stack_authority_required_when_materially_constraining_program_artifacts') is not True or bcross.get('ai_recommended_framework_or_toolchain_may_receive_readiness_credit') is not False:
        failures.append('acceptance_cross_stage_effectful_binding_authority_incomplete')
    catalog = load(root, '10_REGISTRY/AUDIT_CATALOG.yaml')
    aud14 = next((x for x in catalog.get('items') or [] if x.get('audit_item_uid') == 'AUD-GOV-014'), None)
    if not isinstance(aud14, dict) or aud14.get('audit_type') != 'CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS' or aud14.get('validator_uid') != 'VAL-GOV-035':
        failures.append('audit_catalog_cross_stage_item_missing')

    for sid, stage in stage_map.items():
        gate = stage.get('cross_stage_materialization_gate') or {}
        if gate.get('required') is not True or gate.get('invariant_uid') != 'GOV-INV-CROSS-STAGE-MATERIALIZATION-CONSUMER-READINESS-001':
            failures.append('cross_stage_gate_missing:' + str(sid))
        for key in ('reference_resolution_required','physical_materialization_required','parse_schema_required_field_completeness_required','denominator_inclusion_required','successor_consumer_readiness_required','successor_required_input_reconciliation_before_exit','successor_effectful_operation_binding_reconciliation_required','successor_target_authority_required_before_successor_effectful_execution','authorized_not_applicable_requires_authority_evidence','current_normative_execution_matrix_nonempty_and_valid_before_exit','current_state_evidence_terminal_consistency_required_before_exit'):
            if gate.get(key) is not True:
                failures.append('cross_stage_gate_flag_missing:' + str(sid) + ':' + key)
        if gate.get('successor_execution_binding_universe_source') != 'CURRENT_SUCCESSOR_LIFECYCLE_OPERATIONS_PLUS_CURRENT_AUTHORITY_AND_APPLICABILITY':
            failures.append('cross_stage_gate_binding_universe_source_drift:' + str(sid))
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

    return {'status': 'PASS' if not failures else 'FAIL', 'invariant_count': len(inv), 'stage_count': len(scope.get('applies_to_stages') or []), 'failures': failures}
if __name__ == '__main__':
    out = validate()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if out['status'] == 'PASS' else 1)
