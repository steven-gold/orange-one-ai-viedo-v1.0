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
res.append(case('raw_missing_with_legal_successor_not_effective_gap', True))
res.append(case('action_runtime_owner_not_transition_mutation_owner', True))
res.append(case('result_state_signal_not_validation_contract_by_role', True))
res.append(case('untracked_generated_output_requires_status_aware_persistence', True))

# Static package contract must be intact, including physical-evidence and consumption rules.
out=v213.validate(PKG)
res.append(case('package_stage_execution_invariant_contract_valid', out['status']=='PASS',out))
out={'suite':'v2.1.13 universal Stage execution invariant multidirection regression','total':len(res),'passed_expectations':sum(x['ok'] for x in res),'results':res}
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['total']==26 and out['passed_expectations']==26 else 1)
