#!/usr/bin/env python3
from pathlib import Path
import sys, yaml
from governance_resolver import resolve
ROOT=Path(__file__).resolve().parents[2]
protocol_p=ROOT/'governance/specifications/current/VALIDATION_REMEDIATION_CLOSURE_PROTOCOL.yaml'
mutation_p=ROOT/'governance/specifications/current/SPECIFICATION_MUTATION_CONTROL.yaml'
layers_p=ROOT/'governance/specifications/current/GOVERNANCE_LAYER_SEPARATION_AND_PORTABILITY.yaml'
manifest_p=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'
registry_p=ROOT/'governance/specifications/REGISTRY.yaml'
state_p=ROOT/'governance/test/ACTIVE_STATE.yaml'
errors=[]
for p in (protocol_p,mutation_p,layers_p,manifest_p,registry_p,state_p):
    if not p.is_file(): errors.append('MISSING_REQUIRED_FILE:'+str(p.relative_to(ROOT)))
if errors:
    [print('BLOCK:',e,file=sys.stderr) for e in errors]; raise SystemExit(1)
protocol=yaml.safe_load(protocol_p.read_text()) or {}; mutation=yaml.safe_load(mutation_p.read_text()) or {}; layers=yaml.safe_load(layers_p.read_text()) or {}; manifest=yaml.safe_load(manifest_p.read_text()) or {}; registry=yaml.safe_load(registry_p.read_text()) or {}; state=yaml.safe_load(state_p.read_text()) or {}
uid=resolve()['governance_uid']
if protocol.get('artifact_uid')!='GOV-COMP-VALIDATION-REMEDIATION-CLOSURE-PROTOCOL': errors.append('PROTOCOL_UID_INVALID')
if protocol.get('formal_current_authority') is not True or protocol.get('layer_classification')!='POLICY': errors.append('PROTOCOL_NOT_FORMAL_POLICY')
principles=protocol.get('principles') or {}; remediation=protocol.get('material_remediation') or {}; retest=protocol.get('retest_and_regression') or {}; closure=protocol.get('closure_gate') or {}; cycle=protocol.get('canonical_cycle') or []
required_principles={'audit_pass_with_reproducible_product_gap_is_closure':False,'repeated_audit_blocked_loop_counts_as_progress':False,'hidden_defect_search_after_known_fix':True,'fresh_verification_from_clean_registered_baseline':True,'prior_result_reuse_as_current':False,'ai_may_invent_missing_product_authority':False,'external_authority_auto_resolution':False,'mixed_governance_uid_evidence_for_one_closure':False}
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
purpose=mutation.get('purpose') or {}; auth=mutation.get('explicit_change_authorization') or {}; freeze=mutation.get('execution_cycle_freeze_control') or {}; promo=mutation.get('consolidated_promotion_control') or {}; fatal=mutation.get('fatal_specification_contradiction_exception') or {}
if purpose.get('default_decision')!='DENY_MUTATION' or purpose.get('fail_closed') is not True: errors.append('MUTATION_DEFAULT_DENY_MISSING')
if auth.get('required') is not True or auth.get('authorization_receipt_must_preexist_spec_mutation_commit') is not True or auth.get('same_commit_authorization_fabrication')!='BLOCK': errors.append('PREEXISTING_AUTHORIZATION_INVARIANT_MISSING')
if freeze.get('freeze_required_before_validation_or_governed_execution') is not True or freeze.get('ordinary_cycle_mutation') is not False or freeze.get('results_may_mix_multiple_governance_uids') is not False: errors.append('CYCLE_FREEZE_INVARIANT_MISSING')
for k in ('registry_manifest_atomic_update_required','active_consumer_inventory_required','stale_predecessor_pin_scan_required','projection_atomicity_required','portability_validation_required','policy_layer_contamination_scan_required','fresh_reverification_required'):
    if promo.get(k) is not True: errors.append('PROMOTION_INVARIANT_MISSING:'+k)
if fatal.get('default')!='DENY' or fatal.get('requires_proven_current_policy_self_contradiction') is not True or fatal.get('new_explicit_authorization_required') is not True or fatal.get('ai_may_self_authorize') is not False: errors.append('FATAL_CONTRADICTION_EXCEPTION_INVALID')
lm=layers.get('layer_model') or {}; pol=lm.get('POLICY') or {}; prof=lm.get('EXECUTION_PROFILE') or {}
if 'PROJECT_FIXED_STEP_IDENTITY' not in (pol.get('may_not_define') or []) or 'PROJECT_FIXED_STEP_COUNT' not in (pol.get('may_not_define') or []): errors.append('POLICY_PROFILE_SEPARATION_MISSING')
if prof.get('global_normative_authority') is not False or prof.get('may_weaken_policy') is not False: errors.append('EXECUTION_PROFILE_AUTHORITY_BOUNDARY_INVALID')
comps=manifest.get('components') or []
if sum(1 for x in comps if x.get('file')=='VALIDATION_REMEDIATION_CLOSURE_PROTOCOL.yaml')!=1: errors.append('MANIFEST_PROTOCOL_BINDING_INVALID')
if (registry.get('active_specification') or {}).get('governance_uid')!=uid: errors.append('REGISTRY_UID_RESOLUTION_DRIFT')
if state.get('specification_uid')!=uid: errors.append('ACTIVE_STATE_CURRENT_UID_STALE')
trans=state.get('governance_revision_transition') or {}; attempt=state.get('stage02_active_attempt') or {}; ex=state.get('execution') or {}; s2=ex.get('stage2') or {}
if trans.get('current_governance_uid')!=uid or trans.get('fresh_revalidation_required') is not True: errors.append('AUTHORITY_TRANSITION_REVALIDATION_MISSING')
if trans.get('predecessor_attempt_may_close_under_current_governance') is not False: errors.append('PREDECESSOR_ATTEMPT_CLOSURE_CREDIT_NOT_BLOCKED')
if attempt.get('closure_credit_under_current_governance') is not False or attempt.get('fresh_revalidation_required') is not True: errors.append('PREDECESSOR_ATTEMPT_NOT_HISTORICAL')
if s2.get('prior_results_authoritative_for_current_governance') is not False or s2.get('revalidation_required_under_current_governance') is not True: errors.append('RUN_STATE_REVALIDATION_PROJECTION_INVALID')
if ex.get('website_construction_allowed') is not False or ex.get('deployment_allowed') is not False: errors.append('PRODUCT_GATE_WRONGLY_OPENED')
if errors:
    [print('BLOCK:',e,file=sys.stderr) for e in errors]; raise SystemExit(1)
print('PASS: reusable validation/remediation/closure policy is profile-neutral and fail-closed')
print('PASS: mutation control preserves freeze, explicit authorization, atomic projection, portability, and fresh revalidation')
print('PASS: predecessor Stage/Run evidence remains historical RUN_STATE and cannot become current closure credit')
print('PASS: website construction and deployment remain blocked')
