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
val=imp('validate_evidence_state_closure')
def case(name,ok,detail=None): return {'case':name,'ok':bool(ok),'detail':detail or {}}
def mutate_yaml(name,rel,mut):
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)/'pkg'; shutil.copytree(ROOT,r)
        p=r/rel; d=yaml.safe_load(p.read_text(encoding='utf-8')) or {}; mut(d)
        p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=160),encoding='utf-8')
        out=val.validate(r); return case(name,out['status']=='FAIL',{'failures':out.get('failures',[])[:6]})
def mutate_text(name,rel,mut):
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)/'pkg'; shutil.copytree(ROOT,r)
        p=r/rel; p.write_text(mut(p.read_text(encoding='utf-8')),encoding='utf-8')
        out=val.validate(r); return case(name,out['status']=='FAIL',{'failures':out.get('failures',[])[:6]})
base=val.validate(ROOT)
stage=yaml.safe_load((ROOT/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml').read_text()) or {}
s2={x.get('stage_uid'):x for x in stage.get('stages') or []}.get('STAGE-02') or {}
closure=yaml.safe_load((ROOT/'11_EVIDENCE/audit/GITHUB_REPLAY_CLOSURE_RESULT.yaml').read_text()) or {}
results=[
 case('baseline_closure_validator_pass',base['status']=='PASS',base),
 case('stage02_page_functional_contract_registered',s2.get('name')=='PAGE_FUNCTIONAL_CONTRACT'),
 case('stage02_functional_chain_compile_registered','FUNCTIONAL_CHAIN_COMPILE' in (s2.get('operations') or [])),
 case('stage02_dependency_map_compile_registered','DEPENDENCY_MAP_COMPILE' in (s2.get('operations') or [])),
 case('stage02_async_provider_contract_registered','ASYNC_PROVIDER_CONTRACT_COMPILE' in (s2.get('operations') or [])),
 case('stage02_shared_owner_port_resolve_registered','SHARED_OWNER_PORT_RESOLVE' in (s2.get('operations') or [])),
 case('stage02_functional_guard_registered','FUNCTIONAL_CONTRACT_GUARD' in (s2.get('validator_names') or [])),
 case('stage02_dependency_guard_registered','DEPENDENCY_CONTINUITY_GUARD' in (s2.get('validator_names') or [])),
 case('closure_run_34733833659_bound',(closure.get('evidence') or {}).get('v218_successor_linkage_final',{}).get('run_id')==34733833659),
 case('closure_run_34734265713_bound',(closure.get('evidence') or {}).get('pre_page_replay',{}).get('run_id')==34734265713),
 case('closure_run_34734528373_bound',(closure.get('evidence') or {}).get('page_blueprint_replay_after_hash_correction',{}).get('run_id')==34734528373),
 case('closure_run_34734730080_bound',(closure.get('evidence') or {}).get('page_replay_content_audit_closure',{}).get('run_id')==34734730080),
 mutate_text('readme_superseded_pending_blocked','README.md',lambda t:t+'\\nStatus: GITHUB PRIOR-PHASE REPLAY PENDING\\n'),
 mutate_yaml('candidate_prior_replay_pending_blocked','11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml',lambda d:d['preformal_execution'].__setitem__('github_prior_phase_replay','PENDING')),
 mutate_yaml('candidate_successor_run_id_drift_blocked','11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml',lambda d:d['preformal_execution'].__setitem__('github_successor_replay_run_id',1)),
 mutate_yaml('defect_replay_pending_blocked','11_EVIDENCE/audit/GOVERNANCE_DEFECT_LEDGER.yaml',lambda d:next(x for x in d['defects'] if x.get('defect_uid')=='DEF-V218-PREDECESSOR-VALIDATOR-SUCCESSOR-REJECTION-001').__setitem__('status','FIXED_PREFORMAL_VERIFIED_GITHUB_REPLAY_PENDING')),
 mutate_yaml('defect_reverify_pending_blocked','11_EVIDENCE/audit/GOVERNANCE_DEFECT_LEDGER.yaml',lambda d:next(x for x in d['defects'] if x.get('defect_uid')=='DEF-V219-IMMUTABLE-PACKAGE-EVIDENCE-STATE-DRIFT-001').__setitem__('status','FIXED_PREFORMAL_REVERIFY_PENDING')),
 mutate_yaml('closure_evidence_run_drift_blocked','11_EVIDENCE/audit/GITHUB_REPLAY_CLOSURE_RESULT.yaml',lambda d:d['evidence']['page_replay_content_audit_closure'].__setitem__('run_id',0)),
 mutate_yaml('human_review_auto_pass_blocked','10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml',lambda d:d['required_review_plan'][0].__setitem__('status','APPROVED')),
 mutate_yaml('sync_contract_disabled_blocked','10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml',lambda d:d['current_test_evidence_sync_contract'].__setitem__('github_replay_closure_evidence_required',False)),
 mutate_yaml('stage02_functional_compile_missing_blocked','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:[s['operations'].remove('FUNCTIONAL_CHAIN_COMPILE') for s in d['stages'] if s.get('stage_uid')=='STAGE-02']),
 mutate_text('functional_chain_runtime_owner_missing_blocked','12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md',lambda t:t.replace(' -> Runtime Owner -> ',' -> ')),
 mutate_text('cross_page_system_slice_missing_blocked','12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md',lambda t:t.replace('Cross-page / System Logic Slice Test','Cross-page Slice')),
 mutate_text('second_system_guard_missing_blocked','12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',lambda t:t.replace('SECOND_SYSTEM_GUARD','SECOND_SYSTEM_DISABLED')),
]
out={'suite':'v2.1.9 evidence-state closure and Stage-02 system-logic detector regression','total':len(results),'passed_expectations':sum(x['ok'] for x in results),'results':results}
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['passed_expectations']==out['total'] else 1)
