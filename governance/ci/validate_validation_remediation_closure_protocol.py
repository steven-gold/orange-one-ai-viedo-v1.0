#!/usr/bin/env python3
from pathlib import Path
import sys, yaml
from governance_resolver import resolve

ROOT=Path(__file__).resolve().parents[2]
protocol_p=ROOT/'governance/specifications/current/VALIDATION_REMEDIATION_CLOSURE_PROTOCOL.yaml'
mutation_p=ROOT/'governance/specifications/current/SPECIFICATION_MUTATION_CONTROL.yaml'
execution_p=ROOT/'governance/specifications/current/EXECUTION_CYCLE_CONTROL.yaml'
evidence_p=ROOT/'governance/specifications/current/EVIDENCE_FEEDBACK_ARTIFACT_LIFECYCLE.yaml'
layers_p=ROOT/'governance/specifications/current/GOVERNANCE_LAYER_SEPARATION_AND_PORTABILITY.yaml'
manifest_p=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'
registry_p=ROOT/'governance/specifications/REGISTRY.yaml'
state_p=ROOT/'governance/test/ACTIVE_STATE.yaml'
targeted_workflow_p=ROOT/'.github/workflows/governance-selected-profile-integrity.yml'
full_line_workflow_p=ROOT/'.github/workflows/governance-full-line-system-gate.yml'
errors=[]
for p in (protocol_p,mutation_p,execution_p,evidence_p,layers_p,manifest_p,registry_p,state_p,targeted_workflow_p,full_line_workflow_p):
    if not p.is_file(): errors.append('MISSING_REQUIRED_FILE:'+str(p.relative_to(ROOT)))
if errors:
    [print('BLOCK:',e,file=sys.stderr) for e in errors]; raise SystemExit(1)

protocol=yaml.safe_load(protocol_p.read_text()) or {}
mutation=yaml.safe_load(mutation_p.read_text()) or {}
execution=yaml.safe_load(execution_p.read_text()) or {}
evidence=yaml.safe_load(evidence_p.read_text()) or {}
layers=yaml.safe_load(layers_p.read_text()) or {}
manifest=yaml.safe_load(manifest_p.read_text()) or {}
registry=yaml.safe_load(registry_p.read_text()) or {}
state=yaml.safe_load(state_p.read_text()) or {}
uid=resolve()['governance_uid']

if protocol.get('artifact_uid')!='GOV-COMP-VALIDATION-REMEDIATION-CLOSURE-PROTOCOL': errors.append('PROTOCOL_UID_INVALID')
if protocol.get('formal_current_authority') is not True or protocol.get('layer_classification')!='POLICY': errors.append('PROTOCOL_NOT_FORMAL_POLICY')
principles=protocol.get('principles') or {}
remediation=protocol.get('material_remediation') or {}
retest=protocol.get('retest_and_regression') or {}
closure=protocol.get('closure_gate') or {}
cycle=protocol.get('canonical_cycle') or []
required_principles={
    'audit_pass_with_reproducible_product_gap_is_closure':False,
    'repeated_audit_blocked_loop_counts_as_progress':False,
    'hidden_defect_search_after_known_fix':True,
    'fresh_verification_from_clean_registered_baseline':True,
    'prior_result_reuse_as_current':False,
    'ai_may_invent_missing_product_authority':False,
    'external_authority_auto_resolution':False,
    'mixed_governance_uid_evidence_for_one_closure':False,
}
for k,v in required_principles.items():
    if principles.get(k)!=v: errors.append('PRINCIPLE_DRIFT:'+k)
if remediation.get('required_for_every_remediable_defect') is not True: errors.append('MATERIAL_REMEDIATION_NOT_REQUIRED')
if remediation.get('audit_or_diagnosis_only')!='NOT_REMEDIATION': errors.append('AUDIT_WRONGLY_COUNTS_AS_REMEDIATION')
if remediation.get('evidence_only_without_owning_layer_change')!='NOT_REMEDIATION': errors.append('EVIDENCE_ONLY_WRONGLY_COUNTS_AS_REMEDIATION')
if retest.get('clean_registered_baseline_required') is not True or retest.get('fresh_reexecution_required') is not True: errors.append('FRESH_RETEST_INVARIANT_MISSING')
if retest.get('known_remediable_signature_reproduction_count')!=0: errors.append('KNOWN_SIGNATURE_ZERO_INVARIANT_MISSING')
if retest.get('same_signature_after_claimed_fix')!='REMEDIATION_FAILURE': errors.append('REMEDIATION_FAILURE_CLASSIFICATION_MISSING')
must_steps=['FREEZE_CURRENT_POLICY_AND_INPUT_BASELINE','MATERIALLY_REMEDIATE_AT_OWNER','FRESHLY_REEXECUTE','VERIFY_KNOWN_SIGNATURE_ZERO','RUN_HIDDEN_DEFECT_SWEEP','PROMOTE_ONLY_IF_EXPLICITLY_AUTHORIZED','MAKE_CLOSURE_DECISION']
if any(x not in cycle for x in must_steps): errors.append('CANONICAL_CYCLE_SEMANTIC_STEP_MISSING')
if closure.get('all_discovered_remediable_defects_materially_eliminated')!='REQUIRED' or closure.get('hidden_defect_sweep')!='PASS_REQUIRED' or closure.get('otherwise')!='BLOCK_ADVANCE': errors.append('CLOSURE_FAIL_CLOSED_INVARIANT_MISSING')

purpose=mutation.get('purpose') or {}
auth=mutation.get('explicit_change_authorization') or {}
freeze=mutation.get('execution_cycle_freeze_control') or {}
promo=mutation.get('consolidated_promotion_control') or {}
refmig=mutation.get('reference_migration_atomicity_control') or {}
fatal=mutation.get('fatal_specification_contradiction_exception') or {}
if purpose.get('default_decision')!='DENY_MUTATION' or purpose.get('fail_closed') is not True: errors.append('MUTATION_DEFAULT_DENY_MISSING')
if auth.get('required') is not True or auth.get('authorization_receipt_must_preexist_spec_mutation_commit') is not True or auth.get('same_commit_authorization_fabrication')!='BLOCK': errors.append('PREEXISTING_AUTHORIZATION_INVARIANT_MISSING')
if freeze.get('freeze_required_before_validation_or_governed_execution') is not True or freeze.get('ordinary_cycle_mutation') is not False or freeze.get('results_may_mix_multiple_governance_uids') is not False: errors.append('CYCLE_FREEZE_INVARIANT_MISSING')
for k in ('registry_manifest_atomic_update_required','active_consumer_inventory_required','stale_predecessor_pin_scan_required','projection_atomicity_required','portability_validation_required','policy_layer_contamination_scan_required','fresh_reverification_required'):
    if promo.get(k) is not True: errors.append('PROMOTION_INVARIANT_MISSING:'+k)

for k in (
    'complete_active_reverse_consumer_set_required',
    'reverse_consumer_set_must_be_frozen_against_prewrite_commit_and_tree',
    'all_affected_active_references_must_migrate_in_same_atomic_commit',
    'persisted_head_reference_integrity_gate_required',
    'full_line_regression_required_after_reference_migration',
    'zero_stale_or_broken_current_reference_required',
    'zero_unjustified_residual_required',
):
    if refmig.get(k) is not True: errors.append('REFERENCE_MIGRATION_INVARIANT_MISSING:'+k)
if refmig.get('partial_consumer_migration')!='BLOCK': errors.append('REFERENCE_PARTIAL_MIGRATION_NOT_BLOCKED')
if refmig.get('old_target_retirement_before_complete_migration')!='BLOCK': errors.append('REFERENCE_EARLY_RETIREMENT_NOT_BLOCKED')
if refmig.get('commit_message_or_declared_migration_count_is_closure_evidence') is not False: errors.append('REFERENCE_CLAIM_WRONGLY_COUNTS_AS_EVIDENCE')
if refmig.get('required_machine_gate')!='governance/ci/validate_active_consumer_reference_integrity.py': errors.append('REFERENCE_MACHINE_GATE_OWNER_INVALID')
inventory=set(refmig.get('required_inventory_classes') or [])
required_inventory={
    'ACTIVE_WORKFLOW_REFERENCES',
    'WORKFLOW_INVOKED_GOVERNANCE_PYTHON_CONSUMERS',
    'DERIVED_TRUST_IDENTITY_CONSUMERS',
    'AUTHORITATIVE_DENOMINATOR_CONSUMERS',
    'LIFECYCLE_OUTPUT_EXPECTATION_CONSUMERS',
    'ACTIVE_PROJECTORS',
}
if not required_inventory.issubset(inventory): errors.append('REFERENCE_REVERSE_CONSUMER_INVENTORY_INCOMPLETE')

refexec=execution.get('reference_change_execution_control') or {}
for k in (
    'applies_when_reference_target_or_governance_identity_changes',
    'discover_complete_active_reverse_consumer_set_before_write',
    'freeze_reverse_consumer_set_to_same_commit_and_tree_as_context_lock',
    'derived_trust_identity_impact_map_required',
    'authoritative_denominator_impact_map_required',
    'lifecycle_output_expectation_impact_map_required',
    'active_projector_impact_map_required',
):
    if refexec.get(k) is not True: errors.append('REFERENCE_EXECUTION_CONTROL_MISSING:'+k)
if refexec.get('partial_reference_rewrite')!='BLOCK': errors.append('REFERENCE_PARTIAL_REWRITE_NOT_BLOCKED')
if refexec.get('broad_search_replace_without_role_classification')!='BLOCK': errors.append('REFERENCE_BROAD_REWRITE_NOT_BLOCKED')
if refexec.get('historical_evidence_may_be_rewritten_as_active_pointer') is not False: errors.append('HISTORY_ACTIVE_POINTER_ROLE_DRIFT')
if refexec.get('active_pointer_may_remain_on_superseded_owner') is not False: errors.append('STALE_ACTIVE_POINTER_ALLOWED')
if refexec.get('stale_reference_or_unjustified_residual')!='BLOCK_CLOSURE': errors.append('REFERENCE_RESIDUAL_CLOSURE_NOT_BLOCKED')

terminal=(evidence.get('finding_terminalization') or {})
fresh=(terminal.get('fresh_evidence_integrity') or {})
for k in (
    'persisted_current_head_validation_required',
    'validation_governance_uid_must_equal_current_registry_uid',
    'exact_finding_signature_to_remediation_relation_required',
    'exact_remediation_target_evidence_required',
    'only_directly_related_reproduced_finding_may_terminalize',
    'historical_origin_and_prior_evidence_must_remain_traceable',
):
    if fresh.get(k) is not True: errors.append('FINDING_TERMINAL_EVIDENCE_INVARIANT_MISSING:'+k)
if fresh.get('disappearance_from_current_view_is_terminalization_evidence') is not False: errors.append('FINDING_DISAPPEARANCE_WRONGLY_COUNTS_AS_TERMINALIZATION')
if fresh.get('commit_message_or_declared_fix_count_is_terminalization_evidence') is not False: errors.append('FINDING_CLAIM_WRONGLY_COUNTS_AS_TERMINALIZATION')
if fresh.get('inferred_fix_without_fresh_validation')!='BLOCK': errors.append('FINDING_INFERRED_FIX_NOT_BLOCKED')

if fatal.get('default')!='DENY' or fatal.get('requires_proven_current_policy_self_contradiction') is not True or fatal.get('new_explicit_authorization_required') is not True or fatal.get('ai_may_self_authorize') is not False: errors.append('FATAL_CONTRADICTION_EXCEPTION_INVALID')

lm=layers.get('layer_model') or {}
pol=lm.get('POLICY') or {}
prof=lm.get('EXECUTION_PROFILE') or {}
if 'PROJECT_FIXED_STEP_IDENTITY' not in (pol.get('may_not_define') or []) or 'PROJECT_FIXED_STEP_COUNT' not in (pol.get('may_not_define') or []): errors.append('POLICY_PROFILE_SEPARATION_MISSING')
if prof.get('global_normative_authority') is not False or prof.get('may_weaken_policy') is not False: errors.append('EXECUTION_PROFILE_AUTHORITY_BOUNDARY_INVALID')
comps=manifest.get('components') or []
if sum(1 for x in comps if x.get('file')=='VALIDATION_REMEDIATION_CLOSURE_PROTOCOL.yaml')!=1: errors.append('MANIFEST_PROTOCOL_BINDING_INVALID')
if (registry.get('active_specification') or {}).get('governance_uid')!=uid: errors.append('REGISTRY_UID_RESOLUTION_DRIFT')
if state.get('specification_uid')!=uid: errors.append('ACTIVE_STATE_CURRENT_UID_STALE')
trans=state.get('governance_revision_transition') or {}
profile_state=state.get('selected_execution_profile_state') or {}
execution_state_key=profile_state.get('execution_state_key')
current_step_state_key=profile_state.get('current_step_state_key')
active_attempt_state_key=profile_state.get('active_attempt_state_key')
if not execution_state_key or not current_step_state_key or not active_attempt_state_key:
    errors.append('SELECTED_PROFILE_STATE_BINDING_INCOMPLETE')
    ex={}; current_step={}; attempt={}
else:
    ex=state.get(str(execution_state_key)) or {}
    current_step=ex.get(str(current_step_state_key)) or {}
    attempt=state.get(str(active_attempt_state_key)) or {}
if profile_state.get('owner_ref')!='GOVERNANCE_CURRENT.yaml': errors.append('SELECTED_PROFILE_STATE_OWNER_INVALID')
if profile_state.get('global_normative_authority') is not False: errors.append('SELECTED_PROFILE_STATE_WRONGLY_NORMATIVE')
if profile_state.get('profile_step_identities_are_global_governance') is not False: errors.append('PROFILE_STEP_IDENTITY_WRONGLY_GLOBAL')
if trans.get('current_governance_uid')!=uid: errors.append('AUTHORITY_TRANSITION_CURRENT_UID_MISMATCH')
if trans.get('predecessor_attempt_may_close_under_current_governance') is not False: errors.append('PREDECESSOR_ATTEMPT_CLOSURE_CREDIT_NOT_BLOCKED')
if trans.get('predecessor_attempt_preserved_as_historical_evidence') is not True: errors.append('PREDECESSOR_ATTEMPT_HISTORY_PRESERVATION_MISSING')
active_current_revalidation = (
    attempt.get('frozen_governance_uid') == uid
    and current_step.get('result') in {'TEST_EXECUTED_BLOCKED','TEST_EXECUTED_PASS'}
    and attempt.get('active_evidence_present') is True
    and attempt.get('active_findings_present') is True
    and attempt.get('fresh_revalidation_required') is False
)
if active_current_revalidation:
    if trans.get('fresh_revalidation_required') is not False: errors.append('CURRENT_REVALIDATION_TRANSITION_NOT_CLOSED')
    if attempt.get('closure_credit_under_current_governance') is not True: errors.append('CURRENT_REVALIDATED_ATTEMPT_CREDIT_MISSING')
    if current_step.get('prior_results_authoritative_for_current_governance') is not False or current_step.get('revalidation_required_under_current_governance') is not False: errors.append('CURRENT_RUN_STATE_REVALIDATION_PROJECTION_INVALID')
    for k in ('source_execution_sha','source_workflow_run_id','source_artifact_id','source_artifact_sha256'):
        if attempt.get(k) in (None,''): errors.append('CURRENT_REVALIDATION_PROVENANCE_MISSING:'+k)
else:
    if trans.get('fresh_revalidation_required') is not True: errors.append('AUTHORITY_TRANSITION_REVALIDATION_MISSING')
    if attempt.get('closure_credit_under_current_governance') is not False or attempt.get('fresh_revalidation_required') is not True: errors.append('PREDECESSOR_ATTEMPT_NOT_HISTORICAL')
    if current_step.get('prior_results_authoritative_for_current_governance') is not False or current_step.get('revalidation_required_under_current_governance') is not True: errors.append('RUN_STATE_REVALIDATION_PROJECTION_INVALID')
if ex.get('website_construction_allowed') is not False or ex.get('deployment_allowed') is not False: errors.append('PRODUCT_GATE_WRONGLY_OPENED')

gate_ref='governance/ci/validate_active_consumer_reference_integrity.py'
for workflow_p in (targeted_workflow_p,full_line_workflow_p):
    if gate_ref not in workflow_p.read_text(encoding='utf-8'):
        errors.append('REFERENCE_INTEGRITY_GATE_NOT_WIRED:'+str(workflow_p.relative_to(ROOT)))

reg_ref=(registry.get('active_consumer_reference_integrity') or {})
if reg_ref.get('validator')!=gate_ref or reg_ref.get('required_in_targeted_regression') is not True or reg_ref.get('required_in_full_line_regression') is not True or reg_ref.get('persisted_head_verification_required') is not True or reg_ref.get('zero_stale_or_broken_current_reference_required') is not True:
    errors.append('REGISTRY_REFERENCE_INTEGRITY_GATE_BINDING_INVALID')

if errors:
    [print('BLOCK:',e,file=sys.stderr) for e in errors]; raise SystemExit(1)
print('PASS: reusable validation/remediation/closure policy is profile-neutral and fail-closed')
print('PASS: mutation control preserves freeze, explicit authorization, complete reverse-consumer inventory, atomic reference migration, and fresh revalidation')
print('PASS: finding terminalization requires persisted-head evidence tied to the exact finding signature and remediation target')
print('PASS: active-consumer reference-integrity gate is mandatory in targeted and Full-Line regression paths')
print('PASS: predecessor profile/run evidence remains historical RUN_STATE and cannot become current closure credit')
print('PASS: website construction and deployment remain blocked')
