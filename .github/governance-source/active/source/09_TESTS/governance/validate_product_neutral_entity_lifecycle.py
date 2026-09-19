#!/usr/bin/env python3
from pathlib import Path
import json, yaml, sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]

def load(root,rel):
    p=root/rel
    return yaml.safe_load(p.read_text(encoding='utf-8')) or {}

def recursive_strings(obj,path=()):
    if isinstance(obj,dict):
        for k,v in obj.items():
            yield from recursive_strings(v,path+(str(k),))
    elif isinstance(obj,list):
        for i,v in enumerate(obj):
            yield from recursive_strings(v,path+(str(i),))
    elif isinstance(obj,str):
        yield path,obj

def validate(root=ROOT):
    failures=[]
    reg=load(root,'10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml')
    inv=reg.get('invariants') or {}
    app=reg.get('applicability') or {}
    if app.get('common_spec_is_product_neutral') is not True: failures.append('common_spec_not_declared_product_neutral')
    if app.get('specific_product_identity_required_to_interpret_common_rules') is not False: failures.append('specific_product_identity_still_required')
    if app.get('product_profile_may_weaken_common_invariants') is not False: failures.append('product_profile_can_weaken_common_invariants')
    if app.get('product_specific_binding_in_common_normative_rule')!='BLOCK': failures.append('common_product_binding_not_blocked')
    if app.get('binding_substitution_audit_required_before_freeze') is not True: failures.append('binding_substitution_audit_not_required')
    pna=inv.get('PRODUCT_NEUTRAL_APPLICABILITY') or {}
    for k in ['common_rule_may_require_product_name','common_rule_may_require_product_page_uid_or_route','common_rule_may_require_product_repository','common_rule_may_require_product_provider_or_database_schema','product_profile_can_weaken_common_rule','product_profile_can_replace_common_invariant']:
        if pna.get(k) is not False: failures.append('product_neutral_rule_not_false:'+k)
    if pna.get('binding_substitution_test_required') is not True or pna.get('binding_substitution_failure')!='GOVERNANCE_DEFECT': failures.append('binding_substitution_contract_invalid')
    if set(pna.get('product_specific_material_allowed_contexts') or [])!={'EMPIRICAL_PROVENANCE','SYNTHETIC_TEST_FIXTURE','COMPATIBILITY_ALIAS','PRODUCT_PROFILE_EXTENSION'}: failures.append('product_specific_allowed_contexts_invalid')

    ei=inv.get('BUSINESS_ENTITY_INVENTORY_COMPLETENESS') or {}
    if ei.get('required_for_every_governed_interaction_scope') is not True or ei.get('required_artifact')!='BUSINESS_ENTITY_INVENTORY': failures.append('entity_inventory_contract_missing')
    if ei.get('list_or_selector_presence_proves_entity_completeness') is not False or ei.get('missing_required_entity')!='BLOCK': failures.append('entity_inventory_fail_closed_missing')
    required_examples={'ITEM','CATEGORY','CHAPTER','SECTION','ENTRY','TASK','VERSION','ASSET','RECORD','CONFIGURATION','RULE','PACKAGE'}
    if not required_examples.issubset(set(ei.get('entity_kinds_examples_are_non_exhaustive') or [])): failures.append('entity_child_examples_incomplete')

    lc=inv.get('BUSINESS_ENTITY_LIFECYCLE_COMPLETENESS') or {}
    expected_ops={'DISCOVER_OR_LIST','SELECT_OR_OPEN','CREATE','CREATION_MODE','PARENT_BIND','CATEGORY_OR_GROUP_BIND','DRAFT','RESUME','EDIT','SAVE','VALIDATE','CONFIRM_OR_APPROVE','VERSION','REVISE','LOCK_OR_UNLOCK','REORDER','MOVE_OR_REPARENT','ARCHIVE_OR_DELETE','RESTORE','DEPENDENCY_IMPACT','AUDIT','ERROR_RECOVERY','NEXT_STEP'}
    if set(lc.get('operation_universe') or [])!=expected_ops: failures.append('entity_operation_universe_incomplete')
    if set(lc.get('allowed_applicability_status') or [])!={'REQUIRED','OPTIONAL','NOT_APPLICABLE'}: failures.append('entity_operation_status_universe_invalid')
    if lc.get('blank_or_omitted_operation_status')!='BLOCK' or lc.get('not_applicable_requires_authority_evidence') is not True or lc.get('required_operation_without_complete_contract')!='BLOCK': failures.append('entity_operation_fail_closed_missing')
    req_fields={'business_intent_or_user_journey','entry_trigger_or_control','input_source','payload_schema','validation','permission_or_gate','authority_ref','prerequisite_state','resulting_state_or_transition','runtime_owner','persistence_or_state_owner_when_applicable','audit_event','error_or_failure_binding','recovery_or_rollback','user_or_system_feedback','next_action_or_terminal_disposition'}
    if set(lc.get('required_operation_contract_fields') or [])!=req_fields: failures.append('entity_required_operation_contract_fields_incomplete')
    if lc.get('create_only_without_governed_post_create_lifecycle')!='BLOCK' or lc.get('confirmed_or_locked_entity_revision_without_version_disposition')!='BLOCK': failures.append('entity_lifecycle_truncation_not_blocked')

    hi=inv.get('ENTITY_HIERARCHY_COMPLETENESS') or {}
    hfields={'parent_entity_identity','child_entity_identity','cardinality','creation_entry','payload_or_reference_binding','ordering_semantics_when_applicable','permission_or_gate','state_dependency','version_dependency','move_or_reparent_rule','archive_or_delete_propagation','upstream_change_impact','downstream_revalidation','authority_ref'}
    if hi.get('required_artifact')!='ENTITY_HIERARCHY_MATRIX' or set(hi.get('required_relation_fields') or [])!=hfields: failures.append('entity_hierarchy_contract_incomplete')
    for k in ['unresolved_required_parent_child_relation','list_only_child_without_governed_lifecycle','category_or_group_relation_without_management_contract']:
        if hi.get(k)!='BLOCK': failures.append('entity_hierarchy_fail_closed_missing:'+k)

    bi=inv.get('OPERATION_TO_UI_RUNTIME_BIDIRECTIONAL_COVERAGE') or {}
    expected_chain=['BUSINESS_ENTITY_OPERATION','UI_CONTROL_OR_SYSTEM_TRIGGER','ACTION','INPUT_OR_PAYLOAD','API_OR_COMMAND','RUNTIME_OWNER','PERSISTENCE_OR_STATE_TRANSITION','FEEDBACK_OR_AUDIT']
    if bi.get('required_operation_forward_chain')!=expected_chain: failures.append('operation_forward_chain_invalid')
    for k in ['required_operation_without_entry','visible_control_without_allowed_operation','action_without_operation','runtime_endpoint_without_operation']:
        if bi.get(k)!='BLOCK': failures.append('bidirectional_fail_closed_missing:'+k)
    if bi.get('implementation_may_invent_missing_upstream_contract') is not False: failures.append('implementation_invention_not_forbidden')

    fa=inv.get('FUNCTION_ADMISSION_NECESSITY_AND_UTILITY') or {}
    if fa.get('required_artifact')!='FUNCTION_ADMISSION_SCORECARD' or fa.get('required_for_every_auto_or_ai_proposed_functional_addition') is not True: failures.append('function_admission_scorecard_contract_missing')
    if fa.get('score_scale')!='0_TO_100_DIAGNOSTIC_NOT_AUTHORITY' or fa.get('score_may_override_authority_gap') is not False or fa.get('score_may_create_new_product_scope') is not False: failures.append('function_admission_score_authority_guard_invalid')
    dims=fa.get('score_dimensions') or {}
    if sum(int((v or {}).get('max',0)) for v in dims.values())!=100: failures.append('function_admission_score_not_100')
    for k in ['AUTHORITY_NECESSITY','TASK_COMPLETION_CRITICALITY','DEPENDENCY_BLOCKING_IMPACT','ERROR_RISK_REDUCTION','USER_REACH_OR_FREQUENCY','REUSE_ACROSS_REQUIRED_FLOWS','ACCESSIBILITY_OR_RECOVERY_IMPACT']:
        if k not in dims or not (dims.get(k) or {}).get('evidence'): failures.append('function_admission_dimension_missing:'+k)
    dc=fa.get('decision_classes') or {}; auto=dc.get('REQUIRED_AUTO_COMPLETION_ELIGIBLE') or {}; opt=dc.get('REVIEW_ONLY_OPTIONAL') or {}
    if int(auto.get('minimum_necessity_score',-1))!=70 or auto.get('requires_unique_minimal_dependency') is not True or auto.get('requires_zero_authority_gap') is not True or auto.get('requires_zero_scope_ambiguity') is not True: failures.append('function_auto_admission_gate_invalid')
    if opt.get('auto_add') is not False or fa.get('high_utility_without_required_authority_is_auto_add') is not False: failures.append('optional_utility_can_auto_expand')

    bfc=inv.get('BOUNDED_FUNCTIONAL_COMPLETION') or {}
    if bfc.get('required_artifact')!='AUTO_COMPLETION_SCOPE_LEDGER' or bfc.get('auto_completion_requires_seed_gap_uid_or_required_operation_uid') is not True: failures.append('bounded_completion_seed_contract_missing')
    if bfc.get('minimal_closure_set_required') is not True or bfc.get('auto_completion_graph_source')!='FROZEN_REGISTERED_DEPENDENCY_CLOSURE_ONLY': failures.append('bounded_completion_minimal_closure_invalid')
    if bfc.get('transitive_dependency_requires_independent_admission_proof') is not True or bfc.get('new_dependency_outside_frozen_closure')!='STOP_AND_REOPEN_DESIGN' or bfc.get('new_entity_outside_authority_inventory')!='STOP_AND_REOPEN_DESIGN': failures.append('bounded_completion_transitive_scope_guard_invalid')
    for k in ['generic_crud_symmetry_expansion','sibling_feature_symmetry_expansion','nice_to_have_or_best_practice_only_expansion']:
        if bfc.get(k)!='BLOCK': failures.append('bounded_completion_expansion_not_blocked:'+k)
    if bfc.get('recursive_cycle_detection_required') is not True or bfc.get('dependency_cycle')!='BLOCK_AND_ESCALATE' or bfc.get('continue_after_stop_condition')!='BLOCK': failures.append('bounded_completion_cycle_or_stop_guard_invalid')
    if bfc.get('denominator_growth_without_authority_trace')!='UNAUTHORIZED_SCOPE_EXPANSION' or bfc.get('completion_may_expand_product_scope') is not False: failures.append('bounded_completion_denominator_scope_guard_invalid')

    vis=inv.get('FUNCTION_VISUAL_SYNCHRONIZED_COMPLETION') or {}
    visual_fields={'business_entity_or_scope','operation_uid','visual_section_or_surface','component_or_control_identity','interaction_entry','state_binding','loading_or_pending_state','permission_or_disabled_state','success_feedback','error_feedback','recovery_feedback','version_or_revision_visibility_when_applicable','responsive_or_overflow_behavior','i18n_label_ref_when_applicable','accessibility_semantics','visual_authority_ref'}
    if vis.get('required_artifact')!='FUNCTION_VISUAL_IMPACT_MATRIX' or set(vis.get('required_visual_binding_fields') or [])!=visual_fields: failures.append('function_visual_impact_contract_incomplete')
    for k in ['logic_addition_without_visual_impact_classification','user_visible_operation_without_visual_binding','visual_control_without_allowed_operation','new_visual_pattern_without_stage03_design_authority']:
        if vis.get(k)!='BLOCK': failures.append('function_visual_fail_closed_missing:'+k)
    if vis.get('no_visual_delta_allowed_only_with_authority_evidence') is not True or vis.get('visual_delta_requires_approved_design_before_stage05') is not True or vis.get('visual_and_logic_state_feedback_must_remain_synchronized') is not True: failures.append('function_visual_sync_rule_missing')

    wc=inv.get('FUNCTIONAL_WORKBENCH_COHESION') or {}
    if wc.get('required_artifact')!='FUNCTIONAL_WORKBENCH_CONTRACT' or wc.get('applies_to_every_contiguous_user_or_system_work_unit') is not True: failures.append('functional_workbench_contract_missing')
    if set(wc.get('workbench_classes') or [])!={'ATOMIC_WORKBENCH','SAME_SURFACE_CLUSTER','CROSS_SURFACE_FLOW','INDEPENDENT_SUPPORT_PANEL'}: failures.append('functional_workbench_classification_invalid')
    wf={'functional_cluster_uid','business_journey','required_operations','shared_context_identity','workbench_class','visual_container_requirement','required_order','adjacency_requirements','same_surface_requirement','allowed_separation_modes','forbidden_interruptions','cross_surface_transition_contract','context_handoff_contract','responsive_reflow_rule','authority_ref'}
    if set(wc.get('required_fields') or [])!=wf: failures.append('functional_workbench_fields_incomplete')
    if wc.get('atomic_workbench_core_chain_may_be_split_by_unrelated_surface') is not False or wc.get('functional_unit_present_but_fragmented_across_unapproved_surfaces')!='BLOCK' or wc.get('same_workbench_required_component_missing')!='BLOCK': failures.append('functional_workbench_fragmentation_not_blocked')
    if wc.get('separation_requires_authority_and_context_handoff') is not True or wc.get('responsive_reflow_may_change_semantic_order_without_contract') is not False or wc.get('component_presence_alone_proves_workbench_cohesion') is not False: failures.append('functional_workbench_continuity_guard_invalid')

    topo=inv.get('INTERACTION_TOPOLOGY_BINDING') or {}
    if topo.get('required_artifact')!='INTERACTION_TOPOLOGY_MATRIX' or topo.get('stage02_defines_functional_topology') is not True or topo.get('stage03_binds_visual_topology') is not True: failures.append('interaction_topology_contract_missing')
    tf={'functional_cluster_uid','operation_sequence','grouping','adjacency','interruption_boundary','surface_transition_boundary','shared_context_or_state_identity','continuation_or_recovery_path','responsive_reflow_contract','authority_ref'}
    if set(topo.get('required_fields') or [])!=tf or topo.get('functional_topology_to_visual_topology_equivalence_required') is not True: failures.append('interaction_topology_fields_or_equivalence_invalid')
    for k in ['unapproved_visual_reordering_of_required_operation_chain','unapproved_surface_insert_inside_atomic_workbench','cross_surface_without_context_handoff','visual_presence_without_topology_conformance']:
        if topo.get(k)!='BLOCK': failures.append('interaction_topology_fail_closed_missing:'+k)
    if topo.get('stage03_may_redefine_stage02_functional_topology') is not False: failures.append('stage03_can_redefine_functional_topology')

    ai=inv.get('AI_INTERACTION_CONTINUITY_AND_DECISION_BOUNDARY') or {}
    if ai.get('conditional_profile_only') is not True or ai.get('non_ai_scope_requires_this_profile') is not False or ai.get('required_artifact')!='AI_INTERACTION_CONTINUITY_MATRIX': failures.append('ai_interaction_profile_not_conditional')
    if set(ai.get('activation_scope_kinds') or [])!={'AI_CONVERSATION','AI_ASSISTED_WORKSPACE','MULTI_AGENT_INTERACTION'}: failures.append('ai_interaction_activation_scope_invalid')
    expected_sub={'CONVERSATION_IDENTITY_CONTINUITY','MULTI_AGENT_CONTEXT_EQUIVALENCE','AI_OUTPUT_FORMALIZATION_BOUNDARY','REVISION_CONTEXT_CONTINUITY','BRANCH_CONTEXT_ISOLATION_AND_ADOPTION'}
    if set(ai.get('required_subcontracts') or [])!=expected_sub or ai.get('missing_required_subcontract_when_profile_active')!='BLOCK': failures.append('ai_interaction_subcontracts_incomplete')

    ci=inv.get('CONVERSATION_IDENTITY_CONTINUITY') or {}
    if set(ci.get('required_identity_fields') or [])!={'conversation_id','thread_id','context_ref_or_hash','work_scope_ref','base_version_ref_when_applicable'}: failures.append('conversation_identity_fields_incomplete')
    if set(ci.get('transition_classes') or [])!={'PRESERVE','FORK','REPLACE','TERMINATE'} or ci.get('mode_or_work_item_transition_must_classify_each_identity') is not True: failures.append('conversation_transition_contract_invalid')
    for k in ['silent_context_or_thread_reset','unregistered_second_conversation_memory_owner','resume_without_exact_continuation_identity']:
        if ci.get(k)!='BLOCK': failures.append('conversation_continuity_fail_closed_missing:'+k)

    ma=inv.get('MULTI_AGENT_CONTEXT_EQUIVALENCE') or {}
    if set(ma.get('required_baseline_fields') or [])!={'original_request_hash','context_snapshot_hash','source_fact_refs','attachment_refs','work_scope_ref','participant_set','response_identity'}: failures.append('multi_agent_context_baseline_incomplete')
    if ma.get('same_round_direct_comparison_requires_same_original_request_and_context_snapshot') is not True or ma.get('participant_specific_context_requires_registered_authority') is not True or ma.get('different_baselines_presented_as_same_baseline_comparison')!='BLOCK': failures.append('multi_agent_context_equivalence_guard_invalid')

    fb=inv.get('AI_OUTPUT_FORMALIZATION_BOUNDARY') or {}
    if set(fb.get('minimum_semantic_states') or [])!={'RAW_AI_OUTPUT','WORKING_EVIDENCE','CANDIDATE','GOVERNED_DECISION','AUTHORITATIVE_VERSION'}: failures.append('ai_formalization_state_universe_incomplete')
    if fb.get('raw_ai_output_is_authoritative_truth') is not False or fb.get('raw_ai_output_direct_to_authoritative_version')!='BLOCK' or fb.get('governed_decision_or_registered_approval_boundary_required') is not True or fb.get('multi_agent_majority_may_auto_create_authoritative_truth') is not False: failures.append('ai_formalization_boundary_invalid')

    rc=inv.get('REVISION_CONTEXT_CONTINUITY') or {}
    if set(rc.get('required_fields') or [])!={'exact_base_candidate_or_version','revision_reason_or_evidence','source_conversation_or_evidence_ref','resulting_revision_identity'} or rc.get('revision_lineage_required') is not True: failures.append('revision_context_contract_incomplete')
    if rc.get('revision_into_blank_unrelated_context')!='BLOCK' or rc.get('overwrite_confirmed_or_locked_base_in_place')!='BLOCK': failures.append('revision_context_fail_closed_invalid')

    br=inv.get('BRANCH_CONTEXT_ISOLATION_AND_ADOPTION') or {}
    if set(br.get('required_fields') or [])!={'exact_source_message_or_ref','branch_thread_id','branch_context_snapshot','isolation_rule','adoption_path','authority_ref'}: failures.append('branch_context_contract_incomplete')
    if br.get('mainline_future_messages_auto_merge_into_branch') is not False or br.get('branch_output_silent_merge_into_mainline')!='BLOCK' or br.get('explicit_governed_adoption_required') is not True: failures.append('branch_isolation_or_adoption_invalid')

    iv=inv.get('INDEXED_INCREMENTAL_VALIDATION') or {}
    if iv.get('construction_index_first_loading_required') is not True or iv.get('validation_impact_index_required') is not True or iv.get('reverse_dependency_index_required') is not True: failures.append('indexed_validation_core_contract_missing')
    if iv.get('index_may_skip_required_impacted_validator') is not False or iv.get('index_drift_full_sweep_required_before_freeze') is not True or iv.get('index_and_full_sweep_result_divergence')!='BLOCK': failures.append('indexed_validation_coverage_guard_invalid')
    if iv.get('mutation_case_copy_mode')!='COPY_ON_WRITE_OR_IN_MEMORY_OVERLAY_PREFERRED': failures.append('indexed_validation_mutation_mode_missing')
    perf={'files_read','bytes_read','parse_count','cache_hits','cache_misses','full_package_copies','impacted_validators','elapsed_ms'}
    if set(iv.get('performance_receipt_fields') or [])!=perf: failures.append('indexed_validation_performance_receipt_incomplete')

    den=inv.get('BUSINESS_CAPABILITY_COMPLETENESS_DENOMINATOR') or {}
    if den.get('authoritative_denominator_formula')!='BUSINESS_ENTITY_X_APPLICABLE_REQUIRED_OPERATION_PLUS_REQUIRED_HIERARCHY_EDGES': failures.append('business_denominator_formula_invalid')
    for k in ['page_count_is_completeness_denominator','control_count_is_completeness_denominator','action_count_is_completeness_denominator','api_or_port_count_is_completeness_denominator']:
        if den.get(k) is not False: failures.append('count_surrogate_not_forbidden:'+k)
    for k in ['missing_entity_count_must_equal_zero_for_stage02_close','missing_required_operation_count_must_equal_zero_for_stage02_close','unresolved_hierarchy_edge_count_must_equal_zero_for_stage02_close','orphan_control_action_runtime_count_must_equal_zero_for_relevant_stage_close']:
        if den.get(k) is not True: failures.append('denominator_zero_gate_missing:'+k)

    scm=inv.get('SINGLE_SPEC_AUTHORITY_ABSTRACTION') or {}
    if scm.get('source_control_provider_is_adapter_not_common_semantic_dependency') is not True or scm.get('non_github_equivalent_adapter_allowed') is not True: failures.append('source_control_abstraction_missing')
    sc=inv.get('SOURCE_CONTROL_SINGLE_SPEC_AUTHORITY') or {}
    if sc.get('required') is not True or sc.get('canonical_entry_path_is_adapter_defined') is not True or sc.get('source_control_provider_is_common_semantic_dependency') is not False: failures.append('source_control_common_contract_not_neutral')
    gh=inv.get('GITHUB_SINGLE_SPEC_AUTHORITY') or {}
    if gh.get('adapter_role')!='GITHUB_SOURCE_CONTROL_PROFILE' or gh.get('common_semantic_dependency') is not False or gh.get('non_github_equivalent_single_authority_adapter_allowed') is not True or gh.get('inherits_common_invariant')!='SOURCE_CONTROL_SINGLE_SPEC_AUTHORITY': failures.append('github_not_scoped_as_adapter')

    # Cross-artifact binding
    bp=load(root,'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'); c=bp.get('product_neutral_entity_lifecycle_contract') or {}
    if c.get('required') is not True or c.get('validator_uid')!='VAL-GOV-037' or c.get('validator_path')!='09_TESTS/governance/validate_product_neutral_entity_lifecycle.py': failures.append('acceptance_product_neutral_contract_missing')
    if c.get('completeness_denominator')!='BUSINESS_ENTITY_X_APPLICABLE_REQUIRED_OPERATION_PLUS_REQUIRED_HIERARCHY_EDGES': failures.append('acceptance_business_denominator_invalid')
    for k in ['function_admission_scorecard_required','score_cannot_override_authority_gap','bounded_functional_completion_required','minimal_closure_set_required','out_of_frozen_closure_discovery_reopens_design','auto_completion_scope_ledger_required','function_visual_impact_matrix_required','logic_visual_synchronized_completion_required','indexed_incremental_validation_required','index_drift_full_sweep_required_before_freeze','functional_workbench_contract_required','interaction_topology_matrix_required','functional_to_visual_topology_equivalence_required','responsive_reflow_semantic_order_preservation_required','ai_interaction_continuity_matrix_required_when_profile_active','conversation_identity_continuity_required_when_applicable','multi_agent_context_equivalence_required_when_applicable','revision_context_continuity_required_when_applicable','branch_context_isolation_and_explicit_adoption_required_when_applicable']:
        if c.get(k) is not True: failures.append('acceptance_bounded_visual_index_rule_missing:'+k)
    if c.get('user_visible_required_operation_without_visual_binding')!='BLOCK' or c.get('new_visual_pattern_without_design_authority')!='BLOCK' or c.get('index_may_skip_impacted_validator') is not False or c.get('atomic_workbench_fragmentation')!='BLOCK' or c.get('cross_surface_without_context_handoff')!='BLOCK' or c.get('raw_ai_output_direct_authoritative_promotion')!='BLOCK': failures.append('acceptance_bounded_visual_index_topology_fail_closed_invalid')
    life=load(root,'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml')
    cs=(life.get('cross_stage_invariants') or {}).get('stage_execution_invariant_hardening') or {}
    for k in ['product_neutral_common_governance_required','business_entity_inventory_required_for_governed_interaction_scopes','business_entity_operation_matrix_required','entity_hierarchy_matrix_required','entity_operation_completeness_denominator_required','operation_to_ui_runtime_bidirectional_coverage_required','function_admission_scorecard_required','bounded_functional_completion_required','function_visual_impact_matrix_required','logic_visual_synchronized_completion_required','indexed_incremental_validation_required','functional_workbench_cohesion_required','interaction_topology_binding_required','functional_to_visual_topology_equivalence_required','ai_interaction_continuity_profile_required_when_declared','conversation_identity_continuity_required_when_applicable','multi_agent_context_equivalence_required_when_applicable','revision_context_continuity_required_when_applicable','branch_context_isolation_and_explicit_adoption_required_when_applicable']:
        if cs.get(k) is not True: failures.append('lifecycle_cross_stage_rule_missing:'+k)
    if cs.get('product_specific_common_rule_binding')!='BLOCK' or cs.get('count_surrogate_for_functional_completeness')!='BLOCK': failures.append('lifecycle_product_or_count_binding_not_blocked')
    if cs.get('auto_completion_outside_frozen_dependency_closure')!='BLOCK_AND_REOPEN_DESIGN' or cs.get('index_may_skip_impacted_validator') is not False or cs.get('atomic_workbench_fragmentation')!='BLOCK' or cs.get('cross_surface_without_context_handoff')!='BLOCK' or cs.get('raw_ai_output_direct_authoritative_promotion')!='BLOCK': failures.append('lifecycle_bounded_index_topology_guard_invalid')
    stage_map={s.get('stage_uid'):s for s in life.get('stages') or []}
    for uid in ['STAGE-01','STAGE-02','STAGE-03','STAGE-04','STAGE-05','STAGE-06','STAGE-10']:
        g=(stage_map.get(uid) or {}).get('business_entity_completeness_gate') or {}
        if g.get('required') is not True or g.get('validator_uid')!='VAL-GOV-037': failures.append('stage_business_entity_gate_missing:'+uid)
    if not ((stage_map.get('STAGE-02') or {}).get('business_entity_completeness_gate') or {}).get('zero_missing_required_entity_operation_hierarchy_before_exit') is True: failures.append('stage02_zero_missing_business_gate_missing')
    s2stage=(stage_map.get('STAGE-02') or {})
    s2=s2stage.get('business_entity_completeness_gate') or {}
    for k in ['function_admission_scorecard_required','bounded_minimal_closure_plan_required','frozen_dependency_closure_required_before_exit','function_visual_impact_classification_required','functional_workbench_contract_required','interaction_topology_matrix_required','workbench_classification_required','ai_interaction_continuity_contract_required_when_profile_active']:
        if s2.get(k) is not True: failures.append('stage02_bounded_completion_gate_missing:'+k)
    aiop=(s2stage.get('conditional_operations') or {}).get('AI_INTERACTION_CONTINUITY_COMPILE') or {}
    aiout=(s2stage.get('conditional_outputs') or {}).get('AI_INTERACTION_CONTINUITY_CONTRACT') or {}
    expected_ai_scopes={'AI_CONVERSATION','AI_ASSISTED_WORKSPACE','MULTI_AGENT_INTERACTION'}
    if set(aiop.get('when_scope_kind_in') or [])!=expected_ai_scopes or aiop.get('required') is not True: failures.append('stage02_ai_continuity_operation_not_conditional')
    if set(aiout.get('when_scope_kind_in') or [])!=expected_ai_scopes or aiout.get('required') is not True or aiout.get('producer')!='AI_INTERACTION_CONTINUITY_COMPILE': failures.append('stage02_ai_continuity_output_not_conditional')
    s3stage=(stage_map.get('STAGE-03') or {})
    s3=s3stage.get('business_entity_completeness_gate') or {}
    if s3.get('required_function_visual_binding_required') is not True or s3.get('new_visual_pattern_requires_design_authority') is not True or s3.get('functional_workbench_visual_cohesion_required') is not True or s3.get('functional_to_visual_topology_equivalence_required') is not True or s3.get('atomic_workbench_fragmentation')!='BLOCK': failures.append('stage03_visual_topology_completion_gate_missing')
    aiin=(s3stage.get('conditional_inputs') or {}).get('AI_INTERACTION_CONTINUITY_CONTRACT') or {}
    if set(aiin.get('when_scope_kind_in') or [])!=expected_ai_scopes or aiin.get('required') is not True or aiin.get('origin')!='STAGE-02_IMMUTABLE_REFERENCE_ONLY': failures.append('stage03_ai_continuity_input_not_conditional')
    s5=(stage_map.get('STAGE-05') or {}).get('business_entity_completeness_gate') or {}
    if s5.get('auto_completion_within_frozen_dependency_closure_only') is not True or s5.get('out_of_closure_discovery_reopens_design') is not True or s5.get('logic_visual_sync_required') is not True or s5.get('implement_frozen_interaction_topology_without_fragmentation') is not True or s5.get('preserve_context_handoff_and_identity_continuity') is not True: failures.append('stage05_bounded_visual_topology_gate_missing')

    idx=load(root,'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'); ur=idx.get('universal_rules') or {}
    for k in ['product_specific_binding_in_common_normative_rule','product_profile_weakening_common_invariant','business_entity_inventory_missing','business_entity_operation_matrix_missing','entity_hierarchy_matrix_missing','business_entity_required_operation_unclassified','business_entity_not_applicable_without_authority','business_entity_required_operation_contract_missing','entity_list_without_create_modify_finalization_lifecycle','unresolved_parent_child_category_chapter_item_relation','required_operation_without_ui_or_system_entry','visible_control_without_business_or_utility_operation','action_or_runtime_without_business_operation','functional_completeness_by_control_action_api_port_count']:
        if ur.get(k)!='BLOCK': failures.append('construction_product_entity_rule_not_block:'+k)
    for k in ['auto_completion_without_function_admission_scorecard','function_score_override_authority_gap','auto_completion_without_seed_gap_or_required_operation','auto_completion_outside_frozen_dependency_closure','generic_crud_or_sibling_symmetry_scope_expansion','transitive_auto_completion_without_independent_admission_proof','auto_completion_dependency_cycle','continue_auto_completion_after_minimal_closure','denominator_growth_without_authority_trace','logic_addition_without_visual_impact_classification','user_visible_required_operation_without_visual_binding','new_visual_pattern_without_stage03_authority','logic_visual_state_feedback_drift','validation_index_may_skip_impacted_validator','index_drift_before_freeze','functional_workbench_contract_missing','interaction_topology_matrix_missing','atomic_workbench_fragmented_by_unrelated_surface','visual_topology_drift_from_functional_topology','cross_surface_without_context_handoff','responsive_reflow_semantic_order_drift','ai_profile_missing_interaction_continuity_matrix','silent_conversation_or_thread_reset','multi_agent_same_baseline_context_drift','raw_ai_output_direct_authoritative_promotion','revision_without_exact_base_context','branch_silent_mainline_merge']:
        if ur.get(k)!='BLOCK': failures.append('construction_bounded_visual_index_rule_not_block:'+k)
    if ur.get('indexed_incremental_validation_required') is not True: failures.append('construction_indexed_incremental_validation_not_required')

    # Product-binding static audit: common mother specs must be free of empirical product-only markers.
    common_docs=[
      '12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md','12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md','12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md','12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md'
    ]
    prov=reg.get('provenance') or {}
    forbidden_markers=list(prov.get('empirical_product_markers') or [])
    common_provider_markers=['GitHub','Vercel','GitLab','Bitbucket']
    legacy_env_prefixes=list(prov.get('legacy_product_env_prefixes') or [])
    for rel in common_docs:
        text=(root/rel).read_text(encoding='utf-8')
        for marker in forbidden_markers:
            if marker in text: failures.append('product_binding_in_common_mother_spec:'+rel+':'+marker)
        for marker in common_provider_markers:
            if marker in text: failures.append('provider_binding_in_common_mother_spec:'+rel+':'+marker)
    # Common program identity registry must use neutral example identities.
    pr=load(root,'10_REGISTRY/PROGRAM_IDENTITY_AUTHORITY_REGISTRY.yaml'); pt=(root/'10_REGISTRY/PROGRAM_IDENTITY_AUTHORITY_REGISTRY.yaml').read_text(encoding='utf-8')
    if (pr.get('policy') or {}).get('product_neutral_reference_identity_required') is not True or (pr.get('policy') or {}).get('product_specific_identity_in_common_registry')!='BLOCK': failures.append('program_identity_product_neutral_policy_missing')
    for marker in forbidden_markers:
        if marker in pt: failures.append('product_binding_in_program_identity_registry:'+marker)
    # Product-specific material is legal only in explicit provenance or an explicitly
    # non-global execution-profile projection. It remains forbidden in reusable invariants.
    profile_identity_allowed=(reg.get('layer_classification')=='EXECUTION_PROFILE' and reg.get('global_normative_authority') is False)
    for path,val in recursive_strings(reg):
        has_marker=any(marker and marker in val for marker in forbidden_markers)
        allowed=(bool(path) and path[0]=='provenance') or (profile_identity_allowed and path==('profile_uid',))
        if has_marker and not allowed:
            failures.append('product_marker_outside_allowed_profile_or_provenance:'+('.'.join(path)))
    if prov.get('empirical_source_role')!='DEFECT_DISCOVERY_INPUT_NOT_CURRENT_CONSTRUCTION_AUTHORITY': failures.append('empirical_product_provenance_role_invalid')
    # Generic governance runtime must not require legacy product-named environment variables.
    runtime_text=(root/'09_TESTS/governance/validate_governance.py').read_text(encoding='utf-8')
    hp_text=(root/'09_TESTS/governance/test_high_pressure_hardening.py').read_text(encoding='utf-8')
    if any(prefix and prefix in runtime_text+hp_text for prefix in legacy_env_prefixes): failures.append('governance_runtime_still_requires_product_named_env')
    if 'WEB_GOVERNANCE_TRUST_ROOT' not in runtime_text or 'WEB_GOVERNANCE_PREFORMAL_SUITE_CHILD' not in runtime_text: failures.append('generic_governance_env_contract_missing')

    for uid in ['WEB-GOV-01-S071','WEB-GOV-02-S071','WEB-GOV-03-S060','WEB-GOV-04-S076','WEB-GOV-01-S072','WEB-GOV-02-S072','WEB-GOV-03-S061','WEB-GOV-04-S077']:
        if not any(uid in (root/rel).read_text(encoding='utf-8') for rel in common_docs): failures.append('mother_spec_entity_product_neutral_section_missing:'+uid)


    bd=inv.get('BASIC_DESIGN_PACKAGE_COMPLETENESS') or {}
    if bd.get('required_artifact')!='BASIC_DESIGN_PACKAGE' or bd.get('design_domain_only') is not True or bd.get('independent_of_implementation_runtime_deployment') is not True: failures.append('basic_design_package_contract_missing')
    if bd.get('missing_applicable_package_item')!='BASIC_DESIGN_PACKAGE_INCOMPLETE' or bd.get('basic_design_freeze_before_complete_package')!='BLOCK': failures.append('basic_design_package_fail_closed_invalid')
    fv=inv.get('FUNCTION_VISUAL_BIDIRECTIONAL_TRACEABILITY') or {}
    if fv.get('reverse_trace_required_for_visible_interactive_or_state_bearing_elements') is not True or fv.get('orphan_visual_element')!='BLOCK' or fv.get('required_user_observable_function_without_visual_binding')!='BLOCK' or fv.get('arbitrary_visual_topology_change')!='BLOCK': failures.append('function_visual_bidirectional_traceability_invalid')
    mv=inv.get('MANDATORY_MULTI_STATE_VISUAL_EVIDENCE') or {}
    required_scenarios={'VISUAL_ARCHITECTURE_OVERVIEW','CANONICAL_WORKSPACE_OVERVIEW','VISUAL_STYLE_BOARD','INTERACTION_TOPOLOGY_DIAGRAM','INITIAL_OR_EMPTY_STATE','ACTIVE_WORKING_STATE','COMPLEX_OR_CONDITIONAL_STATE','FINALIZATION_OR_CONFIRMATION_STATE','ERROR_BLOCKED_RECOVERY_STATE','CROSS_PAGE_RELATION_DIAGRAM','RESPONSIVE_VARIANT'}
    if mv.get('required_artifact')!='VISUAL_SCENARIO_EVIDENCE_SET' or set(mv.get('scenario_universe') or [])!=required_scenarios or mv.get('actual_visual_design_required') is not True or mv.get('wireframe_only_is_complete_visual_design') is not False or mv.get('style_application_required') is not True or mv.get('missing_required_scenario')!='BLOCK': failures.append('complete_visual_design_evidence_contract_invalid')
    va=inv.get('VISUAL_REFERENCE_ANNOTATION') or {}
    if va.get('required_artifact')!='VISUAL_REFERENCE_ANNOTATION' or va.get('unannotated_visual_may_pass_visual_review') is not False or 'verification_purpose' not in (va.get('required_fields') or []) or 'inherited_visual_authority_refs' not in (va.get('required_fields') or []): failures.append('visual_reference_annotation_contract_invalid')
    vi=inv.get('VISUAL_INHERITANCE_AND_STYLE_DEFINITION') or {}
    required_style={'DESIGN_INTENT','COLOR_ROLE_TOKEN_MODEL','TYPOGRAPHY','SPACING_DENSITY_GRID','GEOMETRY_RADIUS_BORDER_ELEVATION','ICONOGRAPHY','CONTROL_AND_COMPONENT_VARIANTS','STATE_SEMANTICS','MEDIA_ASSET_TREATMENT','MOTION','RESPONSIVE','ACCESSIBILITY','LOCALIZATION','THEME_BRAND_CONSTRAINTS'}
    if set(vi.get('required_artifacts') or [])!={'VISUAL_INHERITANCE_MATRIX','VISUAL_STYLE_DEFINITION'} or vi.get('read_current_visual_authorities_before_design') is not True or vi.get('inherit_existing_current_visual_authority_when_present') is not True or vi.get('silent_global_style_redefinition')!='BLOCK' or set(vi.get('style_category_universe') or [])!=required_style: failures.append('visual_inheritance_or_style_definition_invalid')
    sv=inv.get('SCENARIO_TO_FUNCTION_VISUAL_COVERAGE') or {}
    if sv.get('denominator')!='APPROVED_REQUIRED_JOURNEY_STATE_BRANCH_SET' or int(sv.get('required_coverage_percent',0))!=100 or sv.get('visual_scenario_drift')!='BLOCK': failures.append('scenario_visual_coverage_contract_invalid')
    df=inv.get('BASIC_DESIGN_FREEZE_QUANTITATIVE_COMPLETENESS') or {}
    if any(int(v)!=100 for v in (df.get('required_percent_fields') or {}).values()) or len(df.get('required_zero_fields') or [])<9 or df.get('authority_gap_may_be_hidden_by_percentage') is not False or df.get('single_overview_or_wireframe_may_substitute_denominator') is not False: failures.append('quantitative_basic_design_freeze_contract_invalid')
    de=inv.get('DESIGN_DOCUMENT_VISUAL_EMBEDDING') or {}
    if de.get('external_image_only_delivery')!='BLOCK' or de.get('required_figures_embedded_adjacent_to_relevant_section') is not True or de.get('self_contained_human_review_required') is not True or de.get('implementation_artifacts_required') is not False: failures.append('design_document_visual_embedding_contract_invalid')
    for k in ['basic_design_package_required','basic_design_independent_of_implementation_runtime_deployment','function_visual_bidirectional_traceability_required','mandatory_complete_visual_design_required','visual_reference_annotation_required','visual_inheritance_matrix_required','visual_style_definition_required','scenario_to_function_visual_coverage_required','quantitative_basic_design_freeze_completeness_required','human_readable_design_document_embedded_visuals_required','visual_style_category_coverage_required','orphan_visual_element_zero_required','unbound_control_zero_required','unbound_field_zero_required','undefined_next_step_zero_required','missing_recovery_path_zero_required','required_visual_candidate_missing_zero_required','missing_visual_style_category_zero_required','missing_required_figure_annotation_zero_required','unresolved_visual_authority_conflict_zero_required']:
        if c.get(k) is not True: failures.append('acceptance_basic_design_rule_missing:'+k)
    if c.get('arbitrary_visual_layout_without_topology_binding')!='BLOCK' or c.get('silent_global_style_redefinition')!='BLOCK' or c.get('external_image_only_basic_design_delivery')!='BLOCK': failures.append('acceptance_basic_design_fail_closed_invalid')
    am=inv.get('ATOMIC_BASIC_DESIGN_MATERIALIZATION') or {}
    if am.get('complete_applicable_denominator_must_be_individually_materialized') is not True or am.get('representative_sample_may_satisfy_denominator') is not False or am.get('group_or_capability_summary_may_replace_rows') is not False or am.get('status_label_only_may_receive_coverage_credit') is not False or am.get('missing_applicable_row')!='BLOCK' or am.get('summary_only_substitution')!='BLOCK' or len(am.get('required_row_fields') or [])<20: failures.append('atomic_basic_design_materialization_invalid')
    dr=inv.get('BASIC_DESIGN_DENOMINATOR_RECONCILIATION') or {}
    if set(dr.get('required_artifacts') or [])!={'BASIC_DESIGN_DENOMINATOR_SNAPSHOT','BASIC_DESIGN_DELIVERABLE_RECONCILIATION'} or dr.get('machine_and_human_denominator_identity_required') is not True or dr.get('uid_level_reconciliation_required') is not True or any(int(dr.get(k,-1))!=0 for k in ['missing_required_uid_count','duplicate_credit_count','summary_only_credit_count','representative_sample_credit_count','human_machine_denominator_mismatch_count','unclassified_applicability_count']) or dr.get('mismatch')!='BLOCK': failures.append('basic_design_denominator_reconciliation_invalid')
    ed=inv.get('BASIC_DESIGN_EXECUTION_DETAIL_COMPLETENESS') or {}
    if len(ed.get('required_chain') or [])<20 or ed.get('undefined_required_detail_is_design_gap') is not True or ed.get('ai_may_invent_missing_product_decision') is not False or ed.get('downstream_evidence_may_retroactively_close_incomplete_basic_design') is not False: failures.append('basic_design_execution_detail_completeness_invalid')
    for k in ['atomic_basic_design_materialization_required','complete_denominator_enumeration_required','row_level_design_binding_required','basic_design_denominator_snapshot_required','human_machine_design_deliverable_reconciliation_required','no_summary_substitution_required','no_representative_sample_credit_required','execution_detail_chain_complete_required','zero_silent_omission_required','zero_summary_only_credit_required','zero_representative_sample_credit_required','zero_human_machine_denominator_mismatch_required','zero_unclassified_applicability_required']:
        if c.get(k) is not True: failures.append('acceptance_atomic_design_rule_missing:'+k)
    if c.get('missing_atomic_design_row')!='BLOCK' or c.get('missing_required_design_binding')!='BLOCK' or c.get('summary_only_design_completion_claim')!='BLOCK': failures.append('acceptance_atomic_design_fail_closed_invalid')
    for uid in ['WEB-GOV-01-S076','WEB-GOV-01-S077','WEB-GOV-01-S078','WEB-GOV-01-S079','WEB-GOV-01-S080','WEB-GOV-01-S081','WEB-GOV-01-S082','WEB-GOV-01-S083','WEB-GOV-01-S084','WEB-GOV-01-S085','WEB-GOV-01-S086']:
        if uid not in (root/'12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md').read_text(encoding='utf-8'): failures.append('mother_basic_design_section_missing:'+uid)

    return {'status':'PASS' if not failures else 'FAIL','operation_count':len(lc.get('operation_universe') or []),'function_admission_score_max':sum(int((v or {}).get('max',0)) for v in (fa.get('score_dimensions') or {}).values()),'product_binding_failures':len([x for x in failures if 'product_binding' in x or 'product_named' in x]),'failures':failures}

if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
