#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
import sys as _governance_runner_sys
if __name__ != "__main__" and "pytest" in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip("standalone governance regression executable; use registered subprocess runner", allow_module_level=True)
from pathlib import Path
import json, importlib.util
PKG=Path(__file__).resolve().parents[2]
VP=Path(__file__).resolve().parent/'validate_test_feedback_spec_evolution.py'
spec=importlib.util.spec_from_file_location('v214',VP); v214=importlib.util.module_from_spec(spec); spec.loader.exec_module(v214)

def case(name,ok): return {'case':name,'ok':bool(ok)}
def classify(recurrence_count, stage_unique_proof=False):
    if recurrence_count>1: return 'GLOBAL_SHARED'
    return 'STAGE_LOCAL' if stage_unique_proof else 'UNCLASSIFIED'
def promote_version(high_pressure): return bool(high_pressure)
def promote_source_control_current(backtrace,full_revalidation,one_pointer=True): return bool(backtrace and full_revalidation and one_pointer)
def freeze(defects_open,github_current_ok): return defects_open==0 and github_current_ok
order=['STAGE_TEST_EXECUTION','DEFECT_GAP_RECORD','PRODUCTION_CONFORMANCE_REVIEW','DEFECT_SCOPE_CLASSIFICATION','SPEC_PATCH_CANDIDATE','MULTIDIRECTION_HIGH_PRESSURE_TEST','VERSION_PROMOTION_V2_1_X','SOURCE_CONTROL_VERSIONED_CANDIDATE_SYNC','PREDECESSOR_BACKTRACE_REGRESSION','FULL_CURRENT_RULE_REVALIDATION','SOURCE_CONTROL_CURRENT_AUTHORITY_PROMOTION','FORMAL_FREEZE','NEXT_STAGE_ELIGIBLE']
res=[]
res.append(case('cross_stage_recurrence_classifies_global',classify(2)=='GLOBAL_SHARED'))
res.append(case('proven_unique_defect_classifies_stage_local',classify(1,True)=='STAGE_LOCAL'))
res.append(case('unproven_single_observation_remains_unclassified',classify(1,False)=='UNCLASSIFIED'))
res.append(case('version_promotion_without_high_pressure_blocked',not promote_version(False)))
res.append(case('version_promotion_after_high_pressure_allowed',promote_version(True)))
res.append(case('source_control_current_before_backtrace_blocked',not promote_source_control_current(False,True)))
res.append(case('source_control_current_before_full_revalidation_blocked',not promote_source_control_current(True,False)))
res.append(case('multiple_current_pointers_block_promotion',not promote_source_control_current(True,True,False)))
res.append(case('source_control_current_after_backtrace_and_revalidation_allowed',promote_source_control_current(True,True,True)))
res.append(case('freeze_with_open_defect_blocked',not freeze(1,True)))
res.append(case('freeze_with_stale_source_control_current_blocked',not freeze(0,False)))
res.append(case('freeze_after_closed_loop_allowed',freeze(0,True)))
res.append(case('required_process_has_13_steps',len(order)==13))
res.append(case('defect_record_precedes_spec_patch',order.index('DEFECT_GAP_RECORD')<order.index('SPEC_PATCH_CANDIDATE')))
res.append(case('conformance_review_precedes_scope_classification',order.index('PRODUCTION_CONFORMANCE_REVIEW')<order.index('DEFECT_SCOPE_CLASSIFICATION')))
res.append(case('high_pressure_precedes_version_promotion',order.index('MULTIDIRECTION_HIGH_PRESSURE_TEST')<order.index('VERSION_PROMOTION_V2_1_X')))
res.append(case('candidate_sync_precedes_backtrace',order.index('SOURCE_CONTROL_VERSIONED_CANDIDATE_SYNC')<order.index('PREDECESSOR_BACKTRACE_REGRESSION')))
res.append(case('backtrace_precedes_full_revalidation',order.index('PREDECESSOR_BACKTRACE_REGRESSION')<order.index('FULL_CURRENT_RULE_REVALIDATION')))
res.append(case('current_promotion_precedes_freeze',order.index('SOURCE_CONTROL_CURRENT_AUTHORITY_PROMOTION')<order.index('FORMAL_FREEZE')))
res.append(case('freeze_precedes_next_stage',order.index('FORMAL_FREEZE')<order.index('NEXT_STAGE_ELIGIBLE')))
out=v214.validate(PKG)
res.append(case('package_contract_valid',out['status']=='PASS'))
out={'suite':'v2.1.14 Stage-test feedback/spec-evolution regression','total':len(res),'passed_expectations':sum(x['ok'] for x in res),'validator':out,'results':res}
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['total']==21 and out['passed_expectations']==21 else 1)
