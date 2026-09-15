#!/usr/bin/env python3
from pathlib import Path
import json,yaml,sys,re
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]

def load(root,rel):
    p=root/rel
    return yaml.safe_load(p.read_text(encoding='utf-8')) or {}

def validate(root=ROOT):
    failures=[]
    invreg=load(root,'10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml')
    inv=invreg.get('invariants') or {}
    rev=str(invreg.get('governance_revision') or '')
    if not (rev.startswith('v2.1.14-') or rev.startswith('v2.1.15-')): failures.append('revision_not_v214_or_v215')
    t=inv.get('TEST_DEFECT_FEEDBACK_AND_SPEC_EVOLUTION') or {}
    sc=inv.get('SOURCE_CONTROL_SINGLE_SPEC_AUTHORITY') or {}
    gh=inv.get('GITHUB_SINGLE_SPEC_AUTHORITY') or {}
    required_true=['required_for_every_stage_test','defect_and_gap_record_required_during_execution','evidence_required_for_each_record','production_or_construction_conformance_review_after_test','defect_scope_classification_required','version_promotion_requires_high_pressure_pass','predecessor_backtrace_required_after_version_promotion','full_revalidation_required_after_predecessor_backtrace']
    for k in required_true:
        if t.get(k) is not True: failures.append('test_feedback_rule_missing:'+k)
    scopes=t.get('scope_classes') or {}
    gs=scopes.get('GLOBAL_SHARED') or {}; sl=scopes.get('STAGE_LOCAL') or {}
    if gs.get('rule')!='REPAIR_AT_COMMON_INVARIANT_LAYER_AND_ALL_AFFECTED_LAYERS': failures.append('global_shared_scope_rule_invalid')
    need_layers={'NORMATIVE_MOTHER_SPEC','COMMON_INVARIANT_REGISTRY','LIFECYCLE_STAGE_REGISTRY','ACCEPTANCE_AUDIT_BLUEPRINT','VALIDATOR','REGRESSION','VERSIONING','SOURCE_CONTROL_CURRENT_SPEC_AUTHORITY'}
    if set(gs.get('required_layers') or [])!=need_layers: failures.append('global_shared_layers_incomplete')
    if sl.get('rule')!='REPAIR_ONLY_STAGE_SCOPED_CONTRACT_AND_AFFECTED_VALIDATORS' or sl.get('expansion_without_cross_stage_recurrence_evidence')!='BLOCK': failures.append('stage_local_scope_rule_invalid')
    expected_order=['STAGE_TEST_EXECUTION','DEFECT_GAP_RECORD','PRODUCTION_CONFORMANCE_REVIEW','DEFECT_SCOPE_CLASSIFICATION','SPEC_PATCH_CANDIDATE','MULTIDIRECTION_HIGH_PRESSURE_TEST','VERSION_PROMOTION_V2_1_X','SOURCE_CONTROL_VERSIONED_CANDIDATE_SYNC','PREDECESSOR_BACKTRACE_REGRESSION','FULL_CURRENT_RULE_REVALIDATION','SOURCE_CONTROL_CURRENT_AUTHORITY_PROMOTION','FORMAL_FREEZE','NEXT_STAGE_ELIGIBLE']
    if t.get('required_process_order')!=expected_order: failures.append('required_process_order_invalid')
    if t.get('order_skip')!='BLOCK' or t.get('freeze_with_open_governance_bug_or_gap')!='BLOCK' or t.get('next_stage_before_freeze')!='BLOCK': failures.append('process_fail_closed_rules_missing')
    if sc.get('required') is not True or sc.get('exactly_one_current_governance_entry_required') is not True or sc.get('canonical_entry_path_is_adapter_defined') is not True: failures.append('source_control_single_authority_contract_invalid')
    if sc.get('all_governance_consumers_must_start_from_adapter_current_entry') is not True or sc.get('historical_evidence_or_stage_correction_package_may_be_loaded_as_current_spec') is not False: failures.append('source_control_consumer_authority_rule_invalid')
    if sc.get('multiple_current_version_pointers')!='BLOCK' or sc.get('promote_current_before_predecessor_backtrace_and_full_revalidation')!='BLOCK' or sc.get('current_promotion_requires_full_revalidation_pass') is not True: failures.append('source_control_promotion_guard_missing')
    if sc.get('source_control_provider_is_common_semantic_dependency') is not False: failures.append('source_control_provider_still_common_dependency')
    if gh.get('required_for_github_adapter_profile') is not True or gh.get('canonical_entry_path')!='docs/governance/CURRENT_GOVERNANCE_SPEC.yaml' or gh.get('inherits_common_invariant')!='SOURCE_CONTROL_SINGLE_SPEC_AUTHORITY': failures.append('github_adapter_profile_invalid')
    bp=load(root,'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'); c=bp.get('test_feedback_spec_evolution_contract') or {}
    if c.get('required') is not True or c.get('applies_to_all_stages') is not True or c.get('source_control_single_spec_authority_required') is not True or c.get('source_control_current_entry_path_is_adapter_defined') is not True: failures.append('acceptance_contract_binding_missing')
    if c.get('source_control_current_promotion_before_backtrace_and_full_revalidation')!='BLOCK' or c.get('source_control_provider_is_common_semantic_dependency') is not False: failures.append('acceptance_source_control_promotion_guard_missing')
    ghp=((c.get('source_control_adapter_profiles') or {}).get('GITHUB') or {})
    if ghp.get('canonical_current_entry_path')!='docs/governance/CURRENT_GOVERNANCE_SPEC.yaml': failures.append('acceptance_github_adapter_profile_invalid')
    life=load(root,'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml')
    cs=(life.get('cross_stage_invariants') or {}).get('stage_execution_invariant_hardening') or {}
    for k in ['stage_test_defect_gap_record_required','production_conformance_review_required','defect_scope_classification_required','global_shared_defect_common_layer_propagation_required','multidirection_high_pressure_before_version_promotion_required','predecessor_backtrace_after_version_promotion_required','full_current_rule_revalidation_before_freeze_required','source_control_single_current_spec_authority_required']:
        if cs.get(k) is not True: failures.append('lifecycle_rule_missing:'+k)
    if cs.get('stage_local_defect_cross_stage_expansion_without_evidence')!='BLOCK' or cs.get('source_control_current_promotion_before_backtrace_and_revalidation')!='BLOCK' or cs.get('next_stage_before_governance_freeze')!='BLOCK': failures.append('lifecycle_fail_closed_rule_missing')
    idx=load(root,'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'); ur=idx.get('universal_rules') or {}
    for k in ['stage_test_without_defect_gap_record','test_without_production_conformance_review','unclassified_defect_scope_before_governance_patch','global_shared_defect_patched_only_at_observed_stage','stage_local_defect_generalized_without_recurrence_evidence','governance_version_promotion_without_multidirection_high_pressure_pass','predecessor_backtrace_omitted_after_governance_version_promotion','freeze_without_full_current_rule_revalidation','source_control_multiple_current_governance_versions','source_control_current_promotion_before_backtrace_and_full_revalidation','next_stage_before_governance_freeze']:
        if ur.get(k)!='BLOCK': failures.append('construction_rule_not_block:'+k)
    if ur.get('source_control_current_entry_must_be_adapter_declared') is not True: failures.append('construction_source_control_entry_invalid')
    if ur.get('github_adapter_current_spec_path')!='docs/governance/CURRENT_GOVERNANCE_SPEC.yaml': failures.append('construction_github_adapter_profile_invalid')
    d3=(root/'12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md').read_text(encoding='utf-8')
    d4=(root/'12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md').read_text(encoding='utf-8')
    if 'SECTION_UID: WEB-GOV-03-S059' not in d3 or 'SOURCE_CONTROL_CURRENT_AUTHORITY_PROMOTION' not in d3: failures.append('mother_spec_03_closed_loop_missing')
    if 'SECTION_UID: WEB-GOV-04-S075' not in d4 or 'Source-Control Single-Authority Audit' not in d4: failures.append('mother_spec_04_audit_missing')
    vr=(root/'VERSIONING_RULE.md').read_text(encoding='utf-8')
    if 'v2.1.14 test-feedback / specification-evolution rule' not in vr: failures.append('versioning_v214_rule_missing')
    return {'status':'PASS' if not failures else 'FAIL','failures':failures,'process_steps':len(t.get('required_process_order') or []),'scope_classes':sorted(scopes.keys())}

if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
