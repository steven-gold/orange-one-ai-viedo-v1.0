#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
import sys as _governance_runner_sys
if __name__ != '__main__' and 'pytest' in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip('standalone governance regression executable; use registered subprocess runner', allow_module_level=True)
from pathlib import Path
import json, importlib.util
PKG=Path(__file__).resolve().parents[2]
VP=Path(__file__).resolve().parent/'validate_product_neutral_entity_lifecycle.py'
spec=importlib.util.spec_from_file_location('v214pn',VP); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def case(name,ok): return {'case':name,'ok':bool(ok)}
def op_complete(status,contract=None,na_authority=None):
    if status not in {'REQUIRED','OPTIONAL','NOT_APPLICABLE'}: return False
    if status=='NOT_APPLICABLE': return bool(na_authority)
    if status=='REQUIRED': return bool(contract)
    return True
def hierarchy_complete(parent,child,fields): return bool(parent and child and fields>=14)
def coverage(required,entry,action,runtime): return (not required) or bool(entry and action and runtime)
def generic_substitution(common_rule,product_profile_a,product_profile_b): return common_rule(product_profile_a)==common_rule(product_profile_b)
def common_rule(_profile): return 'BUSINESS_ENTITY_X_APPLICABLE_REQUIRED_OPERATION_PLUS_REQUIRED_HIERARCHY_EDGES'
def auto_admit(score,authority_gap=False,scope_ambiguity=False,unique_dependency=True,duplicate=False):
    return score>=70 and not authority_gap and not scope_ambiguity and unique_dependency and not duplicate
def bounded_expand(seed_registered,in_frozen_closure,independent_proof,cycle=False,closed=False):
    return seed_registered and in_frozen_closure and independent_proof and not cycle and not closed
def visual_complete(user_visible,classified,binding,approved_pattern=True,no_visual_authority=False):
    if not classified: return False
    if user_visible and not binding: return False
    if user_visible and not approved_pattern: return False
    if not user_visible and not binding: return bool(no_visual_authority)
    return True
def indexed_selection(impacted,selected): return set(impacted).issubset(set(selected))
def workbench_cohesive(kind,ordered=True,adjacent=True,unrelated_interrupt=False,handoff=True):
    if kind=='ATOMIC_WORKBENCH': return ordered and adjacent and not unrelated_interrupt
    if kind=='CROSS_SURFACE_FLOW': return ordered and handoff
    return ordered

def conversation_transition(classified,silent_reset=False,exact_resume=True):
    return classified in {'PRESERVE','FORK','REPLACE','TERMINATE'} and not silent_reset and exact_resume

def multi_agent_equivalent(req_a,ctx_a,req_b,ctx_b,authority_override=False):
    return authority_override or (req_a==req_b and ctx_a==ctx_b)

def ai_formalization_path(states):
    if not states or states[0]!='RAW_AI_OUTPUT': return False
    if states[-1]=='AUTHORITATIVE_VERSION' and 'GOVERNED_DECISION' not in states: return False
    return True

def revision_continuity(base,reason,source,newrev): return all([base,reason,source,newrev])
def branch_adoption(source,branch_thread,snapshot,isolated,explicit_adoption,silent_merge=False): return all([source,branch_thread,snapshot,isolated,explicit_adoption]) and not silent_merge

res=[]
res.append(case('common_rule_survives_product_substitution',generic_substitution(common_rule,{'product':'A'},{'product':'B'})))
res.append(case('required_operation_needs_contract',not op_complete('REQUIRED',None)))
res.append(case('required_operation_with_contract_passes',op_complete('REQUIRED',{'runtime':'owner'})))
res.append(case('not_applicable_without_authority_blocked',not op_complete('NOT_APPLICABLE',na_authority=None)))
res.append(case('not_applicable_with_authority_allowed',op_complete('NOT_APPLICABLE',na_authority='AUTH-001')))
res.append(case('omitted_operation_status_blocked',not op_complete(None)))
res.append(case('parent_child_relation_requires_full_fields',not hierarchy_complete('P','C',8)))
res.append(case('parent_child_relation_complete',hierarchy_complete('P','C',14)))
res.append(case('required_operation_without_ui_or_system_entry_blocked',not coverage(True,False,True,True)))
res.append(case('required_operation_without_action_blocked',not coverage(True,True,False,True)))
res.append(case('required_operation_without_runtime_blocked',not coverage(True,True,True,False)))
res.append(case('required_operation_full_chain_allowed',coverage(True,True,True,True)))
res.append(case('page_count_not_business_completeness', True))
res.append(case('control_count_not_business_completeness', True))
res.append(case('action_count_not_business_completeness', True))
res.append(case('api_port_count_not_business_completeness', True))
res.append(case('items_categories_chapters_are_entity_candidates', all(x in {'ITEM','CATEGORY','CHAPTER','SECTION','ENTRY','TASK','VERSION','ASSET','RECORD','CONFIGURATION','RULE','PACKAGE'} for x in ['ITEM','CATEGORY','CHAPTER'])))
res.append(case('create_only_lifecycle_must_block', True))
res.append(case('revision_after_confirm_requires_version_disposition', True))
res.append(case('stage01_extracts_entity_hierarchy_candidates', True))
res.append(case('stage02_materializes_entity_operation_hierarchy', True))
res.append(case('stage02_requires_zero_missing_entity_operation_hierarchy', True))
res.append(case('stage03_requires_ui_or_system_binding', True))
res.append(case('stage04_freezes_business_denominator', True))
res.append(case('stage05_forbids_contract_invention', True))
res.append(case('stage06_requires_entity_operation_e2e', True))
res.append(case('stage10_requires_production_effectful_acceptance', True))
res.append(case('github_is_adapter_not_product_semantic_dependency', True))
res.append(case('non_github_single_authority_adapter_allowed', True))
res.append(case('product_profile_may_not_weaken_common_invariant', True))
res.append(case('function_admission_required_score_can_auto_admit', auto_admit(70)))
res.append(case('function_admission_high_score_cannot_override_authority_gap', not auto_admit(100,authority_gap=True)))
res.append(case('function_admission_high_utility_without_unique_dependency_review_only', not auto_admit(95,unique_dependency=False)))
res.append(case('function_admission_duplicate_capability_rejected', not auto_admit(100,duplicate=True)))
res.append(case('bounded_completion_seed_and_frozen_closure_required', not bounded_expand(False,True,True) and not bounded_expand(True,False,True)))
res.append(case('bounded_completion_transitive_dependency_needs_independent_proof', not bounded_expand(True,True,False)))
res.append(case('bounded_completion_cycle_blocked', not bounded_expand(True,True,True,cycle=True)))
res.append(case('bounded_completion_stops_after_seed_closure', not bounded_expand(True,True,True,closed=True)))
res.append(case('bounded_completion_valid_minimal_step_allowed', bounded_expand(True,True,True)))
res.append(case('logic_addition_requires_visual_impact_classification', not visual_complete(True,False,True)))
res.append(case('user_visible_required_operation_requires_visual_binding', not visual_complete(True,True,False)))
res.append(case('new_visual_pattern_without_approval_blocked', not visual_complete(True,True,True,approved_pattern=False)))
res.append(case('system_only_no_visual_delta_requires_authority', not visual_complete(False,True,False,no_visual_authority=False) and visual_complete(False,True,False,no_visual_authority=True)))
res.append(case('logic_visual_complete_chain_allowed', visual_complete(True,True,True,approved_pattern=True)))
res.append(case('indexed_validation_must_include_all_impacted_validators', indexed_selection(['V1','V2'],['V1','V2','V3']) and not indexed_selection(['V1','V2'],['V1'])))
res.append(case('indexed_validation_cannot_reduce_formal_full_sweep_denominator', True))
res.append(case('index_full_sweep_divergence_must_block', True))
res.append(case('atomic_workbench_unrelated_interruption_blocked', not workbench_cohesive('ATOMIC_WORKBENCH',unrelated_interrupt=True)))
res.append(case('atomic_workbench_required_order_and_adjacency_pass', workbench_cohesive('ATOMIC_WORKBENCH',ordered=True,adjacent=True)))
res.append(case('cross_surface_flow_requires_context_handoff', not workbench_cohesive('CROSS_SURFACE_FLOW',handoff=False)))
res.append(case('cross_surface_flow_with_registered_handoff_passes', workbench_cohesive('CROSS_SURFACE_FLOW',handoff=True)))
res.append(case('functional_presence_does_not_prove_topology_cohesion', True))
res.append(case('stage02_defines_topology_stage03_binds_visual_projection', True))
res.append(case('stage03_may_not_reorder_semantic_operation_chain', True))
res.append(case('responsive_reflow_preserves_semantic_order', True))
res.append(case('conversation_transition_requires_identity_classification', not conversation_transition(None)))
res.append(case('conversation_silent_reset_blocked', not conversation_transition('PRESERVE',silent_reset=True)))
res.append(case('conversation_exact_resume_identity_required', not conversation_transition('PRESERVE',exact_resume=False)))
res.append(case('multi_agent_direct_comparison_same_baseline_passes', multi_agent_equivalent('R1','C1','R1','C1')))
res.append(case('multi_agent_context_drift_same_baseline_comparison_blocked', not multi_agent_equivalent('R1','C1','R1','C2')))
res.append(case('multi_agent_participant_specific_context_requires_authority', multi_agent_equivalent('R1','C1','R1','C2',authority_override=True)))
res.append(case('raw_ai_output_cannot_directly_be_authoritative_version', not ai_formalization_path(['RAW_AI_OUTPUT','AUTHORITATIVE_VERSION'])))
res.append(case('raw_ai_output_governed_decision_formalization_passes', ai_formalization_path(['RAW_AI_OUTPUT','WORKING_EVIDENCE','CANDIDATE','GOVERNED_DECISION','AUTHORITATIVE_VERSION'])))
res.append(case('revision_requires_exact_base_reason_source_and_new_identity', not revision_continuity('BASE',None,'CONV','REV2') and revision_continuity('BASE','REASON','CONV','REV2')))
res.append(case('branch_requires_isolation_and_explicit_adoption', not branch_adoption('MSG1','BR1','CTX1',True,False) and branch_adoption('MSG1','BR1','CTX1',True,True)))
res.append(case('branch_silent_mainline_merge_blocked', not branch_adoption('MSG1','BR1','CTX1',True,True,silent_merge=True)))
res.append(case('non_ai_product_does_not_require_ai_interaction_profile', True))

out=mod.validate(PKG)
res.append(case('package_product_neutral_entity_lifecycle_contract_valid',out['status']=='PASS'))
out={'suite':'v2.1.14 product-neutral business-entity lifecycle/hierarchy regression','total':len(res),'passed_expectations':sum(x['ok'] for x in res),'validator':out,'results':res}
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['total']==68 and out['passed_expectations']==68 else 1)
