#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
import sys as _governance_runner_sys
if __name__ != "__main__" and "pytest" in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip("standalone governance regression executable; use registered subprocess runner", allow_module_level=True)
from pathlib import Path
import importlib.util,json,shutil,tempfile,yaml
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
def imp(name):
    spec=importlib.util.spec_from_file_location(name,HERE/f'{name}.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def case(name,ok,detail=None): return {'case':name,'ok':bool(ok),'detail':detail or {}}

REPO=ROOT.parents[3]
def successor_migration_contract():
    mutation=yaml.safe_load((REPO/'governance/specifications/current/SPECIFICATION_MUTATION_CONTROL.yaml').read_text(encoding='utf-8')) or {}
    cycle=yaml.safe_load((REPO/'governance/specifications/current/EXECUTION_CYCLE_CONTROL.yaml').read_text(encoding='utf-8')) or {}
    candidate=yaml.safe_load((REPO/'governance/source-successor/SOURCE_PACKAGE_CANDIDATE.yaml').read_text(encoding='utf-8')) or {}
    m=mutation.get('retired_evidence_consumer_migration_control') or {}
    s=cycle.get('successor_candidate_state_resolution') or {}
    return {'migration':m,'state':s,'candidate':candidate}

def validate_successor_static(root):
    root=Path(root); failures=[]
    readme=(root/'README.md').read_text(encoding='utf-8')
    review=yaml.safe_load((root/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml').read_text(encoding='utf-8')) or {}
    bp=yaml.safe_load((root/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml').read_text(encoding='utf-8')) or {}
    stage=yaml.safe_load((root/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml').read_text(encoding='utf-8')) or {}
    bdoc=(root/'12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md').read_text(encoding='utf-8')
    idoc=(root/'12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md').read_text(encoding='utf-8')
    edoc=(root/'12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md').read_text(encoding='utf-8')
    if 'GITHUB PRIOR-PHASE REPLAY PENDING' in readme.upper(): failures.append('readme_superseded_github_replay_pending')
    human=review.get('required_review_plan') or []
    if len(human)!=1 or human[0].get('status')!='PENDING': failures.append('human_formal_review_not_pending')
    sync=bp.get('current_test_evidence_sync_contract') or {}
    if sync.get('exact_head_required_workflow_receipts_required') is not True or sync.get('current_validation_truth_source')!='EXACT_HEAD_REQUIRED_WORKFLOW_RECEIPTS': failures.append('evidence_state_closure_contract_missing')
    stages={x.get('stage_uid'):x for x in stage.get('stages') or []}
    s2=stages.get('STAGE-02') or {}
    if 'FUNCTIONAL_CHAIN_COMPILE' not in (s2.get('operations') or []): failures.append('stage02_logic_operations_incomplete')
    chain='Business Intent -> Preconditions -> Entry -> Operator/System Input Source -> Control/Trigger -> Gate -> Permission -> Action -> Validation -> Payload -> API/Entry -> Runtime Owner -> Repository/Data/Provider -> Audit Event -> Response -> UI/Caller Feedback -> Success State -> Next State -> Next Step -> Next Gate -> Failure State -> Retry/Recovery/Rollback -> Terminal Outcome'
    if chain not in bdoc: failures.append('functional_chain_full_logic_contract_missing')
    if 'Cross-page / System Logic Slice Test' not in idoc: failures.append('cross_page_system_logic_slice_missing')
    if 'SECOND_SYSTEM_GUARD' not in edoc: failures.append('second_system_guard_missing')
    return {'status':'PASS' if not failures else 'FAIL','failures':failures}
def mutate_yaml(name,rel,mut):
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)/'pkg'; shutil.copytree(ROOT,r)
        p=r/rel; d=yaml.safe_load(p.read_text(encoding='utf-8')) or {}; mut(d)
        p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=160),encoding='utf-8')
        out=validate_successor_static(r); return case(name,out['status']=='FAIL',{'failures':out.get('failures',[])[:6]})
def mutate_text(name,rel,mut):
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)/'pkg'; shutil.copytree(ROOT,r)
        p=r/rel; p.write_text(mut(p.read_text(encoding='utf-8')),encoding='utf-8')
        out=validate_successor_static(r); return case(name,out['status']=='FAIL',{'failures':out.get('failures',[])[:6]})
stage=yaml.safe_load((ROOT/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml').read_text()) or {}
s2={x.get('stage_uid'):x for x in stage.get('stages') or []}.get('STAGE-02') or {}
c=successor_migration_contract(); m=c['migration']; st=c['state']; cand=c['candidate']
retired=[
 '11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml',
 '11_EVIDENCE/audit/GOVERNANCE_DEFECT_LEDGER.yaml',
 '11_EVIDENCE/audit/GITHUB_REPLAY_CLOSURE_RESULT.yaml',
]
results=[
 case('successor_migration_contract_pass',
      m.get('missing_retired_predecessor_evidence_disposition')=='MIGRATE_CONSUMER_NOT_RESTORE_ARTIFACT'
      and st.get('current_candidate_identity_source')=='governance/specifications/REGISTRY.yaml'),
 case('stage02_governed_unit_functional_contract_registered',s2.get('name')=='GOVERNED_UNIT_FUNCTIONAL_CONTRACT'),
 case('stage02_functional_chain_compile_registered','FUNCTIONAL_CHAIN_COMPILE' in (s2.get('operations') or [])),
 case('stage02_dependency_map_compile_registered','DEPENDENCY_MAP_COMPILE' in (s2.get('operations') or [])),
 case('stage02_async_provider_contract_registered','ASYNC_PROVIDER_CONTRACT_COMPILE' in (s2.get('operations') or [])),
 case('stage02_shared_owner_port_resolve_registered','SHARED_OWNER_PORT_RESOLVE' in (s2.get('operations') or [])),
 case('stage02_functional_guard_registered','FUNCTIONAL_CONTRACT_GUARD' in (s2.get('validator_names') or [])),
 case('stage02_dependency_guard_registered','DEPENDENCY_CONTINUITY_GUARD' in (s2.get('validator_names') or [])),
 case('retired_live_candidate_state_absent',not (ROOT/retired[0]).exists()),
 case('retired_live_defect_ledger_absent',not (ROOT/retired[1]).exists()),
 case('retired_live_replay_closure_absent',not (ROOT/retired[2]).exists()),
 case('historical_predecessor_evidence_is_reference_only',m.get('historical_predecessor_evidence_role')=='HISTORICAL_REFERENCE_ONLY'),
 mutate_text('readme_superseded_pending_blocked','README.md',lambda t:t+'\\nStatus: GITHUB PRIOR-PHASE REPLAY PENDING\\n'),
 case('removed_predecessor_state_must_not_be_restored',m.get('removed_predecessor_run_state_or_evidence_may_be_recreated_as_current') is False),
 case('retired_run_ids_have_no_current_credit',st.get('retired_predecessor_run_ids_are_current_evidence') is False),
 case('deleted_history_not_required_for_current_validation',st.get('deleted_historical_evidence_must_be_restored_for_current_validation') is False),
 case('historical_fixture_required_for_legacy_semantics',m.get('legacy_regression_must_use_isolated_historical_fixture_when_historical_semantics_remain_required') is True),
 case('source_package_single_branch_current_authority',cand.get('status')=='INTEGRATED_CURRENT_WORKLINE' and cand.get('current_authority') is True and (cand.get('integration') or {}).get('mode')=='SINGLE_BRANCH_INTEGRATED'),
 mutate_yaml('human_review_auto_pass_blocked','10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml',lambda d:d['required_review_plan'][0].__setitem__('status','APPROVED')),
 mutate_yaml('sync_contract_disabled_blocked','10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml',lambda d:d['current_test_evidence_sync_contract'].__setitem__('exact_head_required_workflow_receipts_required',False)),
 mutate_yaml('stage02_functional_compile_missing_blocked','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:[s['operations'].remove('FUNCTIONAL_CHAIN_COMPILE') for s in d['stages'] if s.get('stage_uid')=='STAGE-02']),
 mutate_text('functional_chain_runtime_owner_missing_blocked','12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md',lambda t:t.replace(' -> Runtime Owner -> ',' -> ')),
 mutate_text('cross_page_system_slice_missing_blocked','12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md',lambda t:t.replace('Cross-page / System Logic Slice Test','Cross-page Slice')),
 mutate_text('second_system_guard_missing_blocked','12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',lambda t:t.replace('SECOND_SYSTEM_GUARD','SECOND_SYSTEM_DISABLED')),
]
out={'suite':'v2.1.9 evidence-state closure and Stage-02 system-logic detector regression','total':len(results),'passed_expectations':sum(x['ok'] for x in results),'results':results}
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['passed_expectations']==out['total'] else 1)
