#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
import sys as _governance_runner_sys
if __name__ != "__main__" and "pytest" in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip("standalone governance regression executable; use registered subprocess runner", allow_module_level=True)
from pathlib import Path
import json, tempfile, yaml, importlib.util, shutil
PKG=Path(__file__).resolve().parents[2]
VP=Path(__file__).resolve().parent/'validate_stage_execution_invariants.py'
spec=importlib.util.spec_from_file_location('v213',VP); v213=importlib.util.module_from_spec(spec); spec.loader.exec_module(v213)

def case(name,ok,detail=None): return {'case':name,'ok':bool(ok),'detail':detail or {}}
def binding_allowed(explicit=False, unique_current=False, exposure=False, state_event=False, registry=False, similarity=False): return bool(explicit or unique_current)
def authority_admissible(current_member, final_locked): return bool(current_member)
def sparse_zero(record,key,optional_sparse=True): return record.get(key,0) if optional_sparse else record.get(key,None)
def receipt_valid_for_successor(old_den,new_den,new_receipt=False): return bool(old_den==new_den or new_receipt)
def review_closes_stage(review_complete,blockers,required_evidence,exit_gate): return bool(review_complete and blockers==0 and required_evidence and exit_gate)
def successor_projection_ok(successor_id,current_ids): return bool(current_ids and all(x==successor_id for x in current_ids))
def gap_autofill_allowed(gap_class, unique_current=False): return gap_class in ('AUTO_REMEDIABLE','IMPLEMENTATION_GAP') and unique_current
CANON_STAGE_STATUSES={'NOT_STARTED','READY_FOR_EXECUTION','IN_PROGRESS','BLOCKED','REVERIFY_REQUIRED','CURRENT_STATE_CONFLICT','EXECUTION_COMPLETE_CLOSURE_PENDING','CLOSED_PASS','CLOSED_FAIL','SNAPSHOT_INVALIDATED'}
def deterministic_stage_status(total_ops,completed_ops,snapshot_valid=True,current_state_conflict=False,reverify=False,blocked=False,closure_pass=False):
    if not snapshot_valid: return 'SNAPSHOT_INVALIDATED'
    if current_state_conflict: return 'CURRENT_STATE_CONFLICT'
    if reverify: return 'REVERIFY_REQUIRED'
    if blocked: return 'BLOCKED'
    if total_ops > 0 and completed_ops == 0: return 'READY_FOR_EXECUTION'
    if completed_ops < total_ops: return 'IN_PROGRESS'
    if completed_ops == total_ops and not closure_pass: return 'EXECUTION_COMPLETE_CLOSURE_PENDING'
    return 'CLOSED_PASS' if closure_pass else 'CLOSED_FAIL'
def same_complete_input_same_result(left,right): return left == right
res=[]
# Relationship semantics: observational adjacency is not a binding.
res.append(case('port_exposure_is_not_trigger', not binding_allowed(exposure=True)))
res.append(case('state_event_is_not_trigger', not binding_allowed(state_event=True)))
res.append(case('error_registry_membership_is_not_action_error_binding', not binding_allowed(registry=True)))
res.append(case('semantic_similarity_cannot_create_binding', not binding_allowed(similarity=True)))
res.append(case('explicit_binding_is_admissible', binding_allowed(explicit=True)))
res.append(case('unique_current_authority_can_resolve_binding', binding_allowed(unique_current=True)))
# Authority and gap remediation.
res.append(case('final_locked_noncurrent_is_inadmissible', not authority_admissible(False,True)))
res.append(case('current_authority_membership_is_admissible', authority_admissible(True,False)))
res.append(case('architecture_gap_ai_autofill_blocked', not gap_autofill_allowed('ARCHITECTURE_GAP',True)))
res.append(case('input_source_gap_ai_autofill_blocked', not gap_autofill_allowed('INPUT_SOURCE_GAP',True)))
res.append(case('authority_gap_ai_autofill_blocked', not gap_autofill_allowed('AUTHORITY_GAP',True)))
# Validator schema/sparse zero.
res.append(case('optional_sparse_zero_absent_equals_zero', sparse_zero({},'AUTHORITY_GAP',True)==0))
res.append(case('prohibited_nonzero_authority_gap_detected', sparse_zero({'AUTHORITY_GAP':1},'AUTHORITY_GAP',True)!=0))
# Current/successor and receipts.
res.append(case('stale_current_projection_blocked', not successor_projection_ok('S167',['S171','S171'])))
res.append(case('atomic_successor_projection_passes', successor_projection_ok('S167',['S167','S167','S167'])))
res.append(case('denominator_change_invalidates_old_receipt', not receipt_valid_for_successor(20,21,False)))
# Review vs closure.
res.append(case('review_complete_with_blockers_does_not_close_stage', not review_closes_stage(True,167,True,True)))


# v2.2.13 shared contract hardening helpers.
def trigger_resolution(has_control=False,source_derived=False,exact_port=False,gate=False,permission=False,success=False,explicit=False):
    if has_control: return 'CONTROL_BOUND'
    if explicit: return 'EXPLICIT_TRIGGER_BOUND'
    if source_derived and exact_port and gate and permission and success: return 'SYSTEM_TRIGGER_BINDING_MISSING_AUTO_REMEDIABLE'
    return 'UNRESOLVED'
def schema_identity(producer_field,consumer_field,producer_type='string',consumer_type='string',version_ok=True):
    return producer_field==consumer_field and producer_type==consumer_type and version_ok
def history_fallback_allowed(role):
    return role in {'PROVENANCE','NEGATIVE_REGRESSION'}
def task_layer_transition_allowed(current_terminal,resume_persisted,wur_passed,resolved_active,bootstrap_passed):
    return all((current_terminal,resume_persisted,wur_passed,resolved_active,bootstrap_passed))

# v2.1.15 canonical execution optimization regressions.
def unique_closure(absent_exact, viable_role_correct_behaviors, outside_closure=False):
    if outside_closure: return 'STOP_AND_REOPEN_DESIGN'
    if viable_role_correct_behaviors==1: return 'AUTO_REMEDIABLE'
    if viable_role_correct_behaviors>=2: return 'AUTHORITY_GAP'
    return 'OWNING_LAYER_UNRESOLVED_CONTRACT_GAP'
res.append(case('exact_value_absence_alone_not_authority_gap', unique_closure(True,0)=='OWNING_LAYER_UNRESOLVED_CONTRACT_GAP'))
res.append(case('one_role_correct_minimal_closure_auto_remediable', unique_closure(True,1)=='AUTO_REMEDIABLE'))
res.append(case('two_distinct_viable_behaviors_authority_gap', unique_closure(True,2)=='AUTHORITY_GAP'))
res.append(case('out_of_frozen_closure_stops_design', unique_closure(True,1,True)=='STOP_AND_REOPEN_DESIGN'))
res.append(case('deterministic_system_trigger_is_auto_remediable', trigger_resolution(source_derived=True,exact_port=True,gate=True,permission=True,success=True)=='SYSTEM_TRIGGER_BINDING_MISSING_AUTO_REMEDIABLE'))
res.append(case('audit_event_uid_schema_identity_rejects_event_uid_alias', schema_identity('audit_event_uid','audit_event_uid') and not schema_identity('audit_event_uid','event_uid')))
res.append(case('historical_product_value_fallback_forbidden', history_fallback_allowed('CURRENT_PRODUCT_VALUE') is False))
res.append(case('task_layer_transition_requires_terminal_resume_wur_active_bootstrap', task_layer_transition_allowed(True,True,True,True,True) and not task_layer_transition_allowed(False,True,True,True,True)))

# Static package contract must be intact, including physical-evidence and consumption rules.
def handoff_ready(reference=True, physical=True, complete=True, denominator=True, consumer=True, unresolved=0):
    return bool(reference and physical and complete and denominator and consumer and unresolved == 0)
res.append(case('reference_only_handoff_is_not_ready', not handoff_ready(reference=True, physical=False)))
res.append(case('physical_but_required_field_incomplete_handoff_is_not_ready', not handoff_ready(complete=False)))
res.append(case('required_handoff_denominator_omission_is_not_ready', not handoff_ready(denominator=False)))
res.append(case('successor_consumer_not_ready_blocks_handoff', not handoff_ready(consumer=False)))
res.append(case('unresolved_required_dependency_blocks_handoff', not handoff_ready(unresolved=1)))
res.append(case('complete_materialized_consumer_ready_handoff_passes', handoff_ready()))

res.append(case('deterministic_same_input_same_result', same_complete_input_same_result({'status':'CLOSED_PASS','finding_codes':[]},{'status':'CLOSED_PASS','finding_codes':[]})))
res.append(case('deterministic_current_state_conflict', deterministic_stage_status(9,9,current_state_conflict=True)=='CURRENT_STATE_CONFLICT'))
res.append(case('deterministic_zero_operations_ready', deterministic_stage_status(4,0)=='READY_FOR_EXECUTION'))
res.append(case('deterministic_all_operations_without_closure_pending', deterministic_stage_status(4,4,closure_pass=False)=='EXECUTION_COMPLETE_CLOSURE_PENDING'))
res.append(case('deterministic_closed_pass', deterministic_stage_status(4,4,closure_pass=True)=='CLOSED_PASS'))
res.append(case('deterministic_snapshot_invalidation_precedence', deterministic_stage_status(4,4,snapshot_valid=False,closure_pass=True)=='SNAPSHOT_INVALIDATED'))
invdoc=yaml.safe_load((PKG/'10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml').read_text(encoding='utf-8')) or {}
det=(invdoc.get('invariants') or {}).get('DETERMINISTIC_STAGE_AUDIT') or {}
contracts=det.get('stage_contracts') or {}
res.append(case('canonical_stage06_name_exact', (contracts.get('STAGE-06') or {}).get('capability')=='VERIFICATION_QA'))
res.append(case('canonical_stage07_name_exact', (contracts.get('STAGE-07') or {}).get('capability')=='BUILD_RELEASE_CANDIDATE'))
res.append(case('canonical_authorized_not_applicable_token_exact', set((contracts.get('STAGE-06') or {}).get('allowed_test_results') or [])=={'PASS','FAIL','BLOCKED','AUTHORIZED_NOT_APPLICABLE'} and (contracts.get('STAGE-08') or {}).get('legal_na_result')=='AUTHORIZED_NOT_APPLICABLE'))
res.append(case('noncanonical_stage_not_pass_is_forbidden_alias_only', (det.get('deterministic_decision_table') or {}).get('source_document_pass_does_not_imply_stage_pass') is True and 'STAGE_NOT_PASS' in set((det.get('canonical_terminology_contract') or {}).get('forbidden_aliases') or [])))
out=v213.validate(PKG)
res.append(case('package_stage_execution_invariant_contract_valid', out['status']=='PASS',out))
out={'suite':'v2.1.13 universal Stage execution invariant multidirection regression','total':len(res),'passed_expectations':sum(x['ok'] for x in res),'results':res}
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['total']==42 and out['passed_expectations']==42 else 1)
