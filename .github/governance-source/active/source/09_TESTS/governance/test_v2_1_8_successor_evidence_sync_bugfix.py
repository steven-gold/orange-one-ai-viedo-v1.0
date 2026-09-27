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
stage=imp('governance_stage1_pipeline_guard')
def case(name,ok,detail=None): return {'case':name,'ok':bool(ok),'detail':detail or {}}

REPO=ROOT.parents[3]
def successor_migration_contract():
    mutation=yaml.safe_load((REPO/'governance/specifications/current/SPECIFICATION_MUTATION_CONTROL.yaml').read_text(encoding='utf-8')) or {}
    cycle=yaml.safe_load((REPO/'governance/specifications/current/EXECUTION_CYCLE_CONTROL.yaml').read_text(encoding='utf-8')) or {}
    candidate=yaml.safe_load((REPO/'governance/source-successor/SOURCE_PACKAGE_CANDIDATE.yaml').read_text(encoding='utf-8')) or {}
    m=mutation.get('predecessor_evidence_consumer_migration_control') or {}
    s=cycle.get('successor_candidate_state_resolution') or {}
    return {'migration':m,'state':s,'candidate':candidate}

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
 case('successor_migration_baseline_pass',
      (lambda c:
        c['migration'].get('removed_predecessor_run_state_or_evidence_may_be_recreated_as_current') is False
        and c['migration'].get('historical_predecessor_evidence_role')=='HISTORICAL_REFERENCE_ONLY'
        and c['migration'].get('missing_retired_predecessor_evidence_disposition')=='MIGRATE_CONSUMER_NOT_RESTORE_ARTIFACT'
        and c['state'].get('current_candidate_identity_source')=='governance/specifications/REGISTRY.yaml'
        and c['candidate'].get('status')=='UNSIGNED_NOT_CURRENT'
      )(successor_migration_contract())),
]
c=successor_migration_contract()
m=c['migration']; st=c['state']; cand=c['candidate']
retired=[
 '11_EVIDENCE/audit/HIGH_PRESSURE_HARDENING_RESULT.yaml',
 '11_EVIDENCE/audit/REFERENCE_SEMANTIC_REPAIR_RESULT.yaml',
 '11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml',
 '11_EVIDENCE/audit/GITHUB_REPLAY_CLOSURE_RESULT.yaml',
 '11_EVIDENCE/audit/GOVERNANCE_DEFECT_LEDGER.yaml',
]
results += [
 case('retired_predecessor_live_evidence_absent',all(not (ROOT/x).exists() for x in retired),{'present':[x for x in retired if (ROOT/x).exists()]}),
 case('retired_predecessor_state_restore_forbidden',m.get('removed_predecessor_run_state_or_evidence_may_be_recreated_as_current') is False),
 case('historical_predecessor_current_credit_zero',m.get('historical_predecessor_pass_current_credit')==0),
 case('missing_retired_evidence_routes_to_consumer_migration',m.get('missing_retired_predecessor_evidence_disposition')=='MIGRATE_CONSUMER_NOT_RESTORE_ARTIFACT'),
 case('legacy_regression_requires_isolated_fixture',m.get('legacy_regression_must_use_isolated_historical_fixture_when_historical_semantics_remain_required') is True),
 case('legacy_fixture_not_current_authority',m.get('legacy_fixture_may_not_be_current_authority') is True),
 case('current_candidate_identity_from_registry',st.get('current_candidate_identity_source')=='governance/specifications/REGISTRY.yaml'),
 case('current_validation_truth_external_exact_head',st.get('current_validation_truth_source')=='EXACT_HEAD_REQUIRED_WORKFLOW_RECEIPTS'),
 case('retired_run_ids_not_current_evidence',st.get('retired_predecessor_run_ids_are_current_evidence') is False),
 case('source_successor_remains_unsigned_not_current',cand.get('status')=='UNSIGNED_NOT_CURRENT' and cand.get('current_authority') is False),
 case('machine_review_registry_still_present',(ROOT/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml').is_file()),
 case('acceptance_blueprint_sync_contract_still_present',bool((yaml.safe_load((ROOT/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml').read_text(encoding='utf-8')) or {}).get('current_test_evidence_sync_contract'))),
out={'suite':'v2.1.8 successor-aware phase linkage and Current Evidence synchronization regression','total':len(results),'passed_expectations':sum(x['ok'] for x in results),'results':results}
print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['passed_expectations']==out['total'] else 1)
