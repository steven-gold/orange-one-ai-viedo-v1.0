#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
import sys as _governance_runner_sys
if __name__ != "__main__" and "pytest" in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip("standalone governance regression executable; use registered subprocess runner", allow_module_level=True)
from pathlib import Path
import importlib.util,json,shutil,tempfile,yaml,sys
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
def imp(name):
    spec=importlib.util.spec_from_file_location(name,HERE/f'{name}.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
stage=imp('governance_stage1_pipeline_guard'); ev=imp('validate_current_test_evidence')
def case(name,ok,detail=None): return {'case':name,'ok':bool(ok),'detail':detail or {}}
def phase(name,state,expect_pass):
    f=stage.validate_stage1_phase_boundary_state(state); return case(name,(not f)==expect_pass,{'failures':f})
def mutate_case(name,rel,mut,expected='FAIL'):
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)/'pkg'; shutil.copytree(ROOT,r)
        p=r/rel; d=yaml.safe_load(p.read_text(encoding='utf-8')) or {}; mut(d); p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False),encoding='utf-8')
        out=ev.validate(r); return case(name,out['status']==expected,{'failures':out.get('failures',[])[:5]})
results=[]
base={'source_segment_mapping_completed':True,'source_fact_materialization_started':True,'source_fact_materialization_completed':True,'responsibility_classification_started':True,'responsibility_classification_completed':True,'github_ci':{'current_classification_gate':'SUCCESS'}}
results += [
 phase('classification_closed_page_start_allowed',{**base,'page_base_blueprint_started':True},True),
 phase('page_start_without_classification_gate_blocked',{**base,'github_ci':{},'page_base_blueprint_started':True},False),
 phase('classification_successor_does_not_retroactively_fail',{**base,'page_base_blueprint_started':True,'page_base_blueprint_completed':True,'github_ci':{'current_classification_gate':'SUCCESS','current_page_blueprint_gate':'SUCCESS'}},True),
 phase('visual_after_page_gate_allowed',{**base,'page_base_blueprint_started':True,'page_base_blueprint_completed':True,'visual_base_blueprint_started':True,'github_ci':{'current_classification_gate':'SUCCESS','current_page_blueprint_gate':'SUCCESS'}},True),
 phase('visual_before_page_gate_blocked',{**base,'page_base_blueprint_started':True,'page_base_blueprint_completed':True,'visual_base_blueprint_started':True,'github_ci':{'current_classification_gate':'SUCCESS'}},False),
 phase('visual_before_page_complete_blocked',{**base,'page_base_blueprint_started':True,'visual_base_blueprint_started':True,'github_ci':{'current_classification_gate':'SUCCESS','current_page_blueprint_gate':'SUCCESS'}},False),
 phase('binding_after_page_visual_gates_allowed',{**base,'page_base_blueprint_started':True,'page_base_blueprint_completed':True,'visual_base_blueprint_started':True,'visual_base_blueprint_completed':True,'blueprint_binding_started':True,'github_ci':{'current_classification_gate':'SUCCESS','current_page_blueprint_gate':'SUCCESS','current_visual_blueprint_gate':'SUCCESS'}},True),
 phase('binding_without_visual_gate_blocked',{**base,'page_base_blueprint_started':True,'page_base_blueprint_completed':True,'visual_base_blueprint_started':True,'visual_base_blueprint_completed':True,'blueprint_binding_started':True,'github_ci':{'current_classification_gate':'SUCCESS','current_page_blueprint_gate':'SUCCESS'}},False),
 phase('binding_without_visual_complete_blocked',{**base,'page_base_blueprint_started':True,'page_base_blueprint_completed':True,'visual_base_blueprint_started':True,'blueprint_binding_started':True,'github_ci':{'current_classification_gate':'SUCCESS','current_page_blueprint_gate':'SUCCESS','current_visual_blueprint_gate':'SUCCESS'}},False),
 phase('website_still_blocked_in_stage1',{**base,'website_construction_started':True},False),
 phase('deployment_still_blocked_in_stage1',{**base,'deployment_started':True},False),
 case('current_evidence_baseline_pass',ev.validate(ROOT)['status']=='PASS',ev.validate(ROOT)),
]
results += [
 mutate_case('high_pressure_old_revision_blocked','11_EVIDENCE/audit/HIGH_PRESSURE_HARDENING_RESULT.yaml',lambda d:d.__setitem__('governance_revision','v2.1.4-old')),
 mutate_case('reference_old_revision_blocked','11_EVIDENCE/audit/REFERENCE_SEMANTIC_REPAIR_RESULT.yaml',lambda d:d.__setitem__('governance_revision','v2.1.4-old')),
 mutate_case('high_pressure_stage1_27_blocked','11_EVIDENCE/audit/HIGH_PRESSURE_HARDENING_RESULT.yaml',lambda d:d['results'].__setitem__('stage1_minimal_control','27/27 PASS')),
 mutate_case('high_pressure_matrix_9_blocked','11_EVIDENCE/audit/HIGH_PRESSURE_HARDENING_RESULT.yaml',lambda d:d['results'].__setitem__('mandatory_regression_matrix','9/9 SUITES PASS')),
 mutate_case('reference_preformal_14_blocked','11_EVIDENCE/audit/REFERENCE_SEMANTIC_REPAIR_RESULT.yaml',lambda d:d['results'].__setitem__('preformal_global','14/14 PASS; 0 BLOCKING FAILURES')),
 mutate_case('candidate_preformal_14_blocked','11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml',lambda d:d['preformal_execution'].__setitem__('preformal_definition_audit','14/14 CHECKS PASS')),
 mutate_case('candidate_matrix_9_blocked','11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml',lambda d:d['preformal_execution'].__setitem__('mandatory_regression_matrix','9/9 SUITES PASS')),
 mutate_case('candidate_v218_result_missing_blocked','11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml',lambda d:d['preformal_execution'].pop('v2_1_8_successor_evidence_sync_regression')),
 mutate_case('machine_review_pending_blocked','10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml',lambda d:d['machine_review_plan'][0].__setitem__('status','PENDING')),
 mutate_case('machine_review_wrong_revision_blocked','10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml',lambda d:d['machine_review_plan'][0].__setitem__('target_revision','v2.1.7')),
 mutate_case('evidence_sync_contract_disabled_blocked','10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml',lambda d:d['current_test_evidence_sync_contract'].__setitem__('required',False)),
 mutate_case('human_self_approval_without_evidence_blocked','10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml',lambda d:d['progress'].__setitem__('approved',1)),
]
out={'suite':'v2.1.8 successor-aware phase linkage and Current Evidence synchronization regression','total':len(results),'passed_expectations':sum(x['ok'] for x in results),'results':results}
print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['passed_expectations']==out['total'] else 1)
