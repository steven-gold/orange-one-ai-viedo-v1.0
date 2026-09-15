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
val=imp('validate_closure_evidence_continuity')
def case(name,ok,detail=None): return {'case':name,'ok':bool(ok),'detail':detail or {}}
def mutate_yaml(name,rel,mut):
 with tempfile.TemporaryDirectory() as td:
  r=Path(td)/'pkg'; shutil.copytree(ROOT,r); p=r/rel; d=yaml.safe_load(p.read_text(encoding='utf-8')) or {}; mut(d); p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8'); out=val.validate(r); return case(name,out['status']=='FAIL',{'failures':out.get('failures',[])[:8]})
def mutate_text(name,rel,mut):
 with tempfile.TemporaryDirectory() as td:
  r=Path(td)/'pkg'; shutil.copytree(ROOT,r); p=r/rel; p.write_text(mut(p.read_text(encoding='utf-8')),encoding='utf-8'); out=val.validate(r); return case(name,out['status']=='FAIL',{'failures':out.get('failures',[])[:8]})
base=val.validate(ROOT); life=yaml.safe_load((ROOT/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml').read_text()) or {}; inv=life['cross_stage_invariants']['closure_evidence_continuity']; ua=inv['unresolved_authority_identity']; tr=inv['terminal_ci_receipt']
AUTH=['gap_uid','authority_ref','disposition','authority_evidence_ref']; RECEIPT=['provider','repository_or_project','head_sha','run_id','job_denominator','conclusion']
results=[
 case('baseline_validator_pass',base['status']=='PASS',base),
 case('authority_tuple_exact_fields',ua.get('canonical_tuple_fields')==AUTH),
 case('authority_exact_carry_required',ua.get('carry_forward_exact_tuple_required') is True),
 case('authority_count_uid_only_blocked',ua.get('count_only_or_uid_only_validation')=='BLOCK'),
 case('authority_evidence_ref_required',ua.get('authority_evidence_ref_required') is True),
 case('authority_tuple_change_requires_supersession',ua.get('explicit_supersession_required_for_tuple_change') is True),
 case('terminal_canonical_projection_required',tr.get('canonical_projection_required') is True),
 case('terminal_projection_fields_exact',tr.get('ledger_projection_required_fields')==RECEIPT),
 case('terminal_alias_substitution_blocked',tr.get('alias_field_substitution')=='BLOCK'),
 case('jobs_result_not_canonical',tr.get('abbreviated_jobs_or_result_is_not_canonical_receipt') is True),
]
for sid in [f'STAGE-{i:02d}' for i in range(1,12)]:
 st=next(x for x in life['stages'] if x['stage_uid']==sid); results.append(case('common_gate_'+sid.lower(),(st.get('closure_evidence_continuity_gate') or {}).get('mode')=='REQUIRED'))
results += [
 mutate_yaml('authority_tuple_field_drop_blocked','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['unresolved_authority_identity']['canonical_tuple_fields'].remove('authority_evidence_ref')),
 mutate_yaml('authority_count_only_allow_blocked','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['unresolved_authority_identity'].__setitem__('count_only_or_uid_only_validation','ALLOW')),
 mutate_yaml('authority_exact_carry_disable_blocked','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['unresolved_authority_identity'].__setitem__('carry_forward_exact_tuple_required',False)),
 mutate_yaml('receipt_projection_field_drop_blocked','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['terminal_ci_receipt']['ledger_projection_required_fields'].remove('repository_or_project')),
 mutate_yaml('receipt_alias_allow_blocked','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['terminal_ci_receipt'].__setitem__('alias_field_substitution','ALLOW')),
 mutate_yaml('acceptance_authority_contract_drop_blocked','10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml',lambda d:d['closure_evidence_continuity_contract'].pop('unresolved_authority_canonical_identity_fields')),
 mutate_yaml('acceptance_receipt_projection_drop_blocked','10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml',lambda d:d['closure_evidence_continuity_contract'].pop('ledger_terminal_receipt_required_fields')),
 mutate_yaml('stage1_authority_tuple_weaken_blocked','10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml',lambda d:d['unresolved_external_authority_preservation_contract'].__setitem__('blueprint_carry_must_preserve_exact_identity_fields',['gap_uid'])),
 mutate_yaml('stage1_receipt_alias_allow_blocked','10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml',lambda d:d['closure_evidence_continuity_contract'].__setitem__('terminal_receipt_alias_substitution','ALLOW')),
 mutate_text('normative_authority_tuple_text_removal_blocked','12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',lambda t:t.replace('Unresolved Authority continuity is exact, not count-only.','Unresolved Authority continuity may be count-only.')),
 mutate_text('normative_receipt_schema_text_removal_blocked','12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',lambda t:t.replace('provider, repository/project, head SHA, evidence-cycle identity, job denominator, and conclusion','provider and conclusion')),
 mutate_text('version_rule_count_only_rule_removal_blocked','VERSIONING_RULE.md',lambda t:t.replace('Count-only, GAP-UID-only','Loose identity')),
]
prev_auth=[{'gap_uid':'GAP-001','authority_ref':'A@1','disposition':'UNRESOLVED_AUTHORITY_GAP','authority_evidence_ref':'e#1'},{'gap_uid':'GAP-002','authority_ref':'B@1','disposition':'UNRESOLVED_AUTHORITY_GAP','authority_evidence_ref':'e#2'}]
prev={'predecessor_facts':{'x_started':True,'x_completed':True,'proof':'p'},'unresolved_authority_records':prev_auth}
base_ledgers={k:{'current_phase':'BINDING','artifact_count':2,'authority_identity':'2_GAPS','gate_status':'SUCCESS','next_transition':'STAGE1_VALIDATION','predecessor_proof':'p'} for k in ['EXECUTION_STATE','RUN_MANIFEST','ARTIFACT_PLAN']}
receipt={'provider':'GITHUB_ACTIONS','repository_or_project':'owner/repo','head_sha':'abc','run_id':10,'job_denominator':'10/10','conclusion':'SUCCESS'}
def trans(name,mod,expect_fail=True):
 cur={'predecessor_facts':dict(prev['predecessor_facts']),'unresolved_authority_records':[dict(x) for x in prev_auth],'ledgers':base_ledgers,'terminal_receipt':dict(receipt),'terminal_receipt_projections':{'EXECUTION_STATE':dict(receipt),'RUN_MANIFEST':dict(receipt),'GOVERNANCE_CURRENT':dict(receipt)},'receipt_reference_commit_sha':'zzz'}; mod(cur); out=val.validate_transition(prev,cur); return case(name,(out['status']=='FAIL')==expect_fail,out)
results += [
 trans('dynamic_authority_valid_exact_tuple_pass',lambda c:None,False),
 trans('dynamic_authority_ref_drift_blocked',lambda c:c['unresolved_authority_records'][0].__setitem__('authority_ref','WRONG')),
 trans('dynamic_authority_evidence_ref_drift_blocked',lambda c:c['unresolved_authority_records'][0].__setitem__('authority_evidence_ref','wrong#1')),
 trans('dynamic_authority_disposition_drift_blocked',lambda c:c['unresolved_authority_records'][0].__setitem__('disposition','SATISFIED')),
 trans('dynamic_authority_gap_uid_drift_blocked',lambda c:c['unresolved_authority_records'][0].__setitem__('gap_uid','GAP-099')),
 trans('dynamic_authority_record_drop_blocked',lambda c:c['unresolved_authority_records'].pop()),
 trans('dynamic_authority_count_same_identity_changed_blocked',lambda c:(c['unresolved_authority_records'][0].__setitem__('authority_ref','C@1'),c['unresolved_authority_records'][1].__setitem__('authority_ref','D@1'))),
 trans('dynamic_authority_missing_evidence_ref_blocked',lambda c:c['unresolved_authority_records'][0].pop('authority_evidence_ref')),
 trans('dynamic_receipt_projection_valid_pass',lambda c:None,False),
 trans('dynamic_receipt_provider_missing_blocked',lambda c:c['terminal_receipt_projections']['EXECUTION_STATE'].pop('provider')),
 trans('dynamic_receipt_repo_missing_blocked',lambda c:c['terminal_receipt_projections']['RUN_MANIFEST'].pop('repository_or_project')),
 trans('dynamic_receipt_head_missing_blocked',lambda c:c['terminal_receipt_projections']['GOVERNANCE_CURRENT'].pop('head_sha')),
 trans('dynamic_receipt_run_missing_blocked',lambda c:c['terminal_receipt_projections']['EXECUTION_STATE'].pop('run_id')),
 trans('dynamic_receipt_denominator_missing_blocked',lambda c:c['terminal_receipt_projections']['RUN_MANIFEST'].pop('job_denominator')),
 trans('dynamic_receipt_conclusion_missing_blocked',lambda c:c['terminal_receipt_projections']['GOVERNANCE_CURRENT'].pop('conclusion')),
 trans('dynamic_receipt_cross_ledger_run_drift_blocked',lambda c:c['terminal_receipt_projections']['RUN_MANIFEST'].__setitem__('run_id',11)),
 trans('dynamic_receipt_cross_ledger_head_drift_blocked',lambda c:c['terminal_receipt_projections']['RUN_MANIFEST'].__setitem__('head_sha','def')),
 trans('dynamic_receipt_jobs_alias_only_blocked',lambda c:(c['terminal_receipt_projections'].__setitem__('EXECUTION_STATE',{'head_sha':'abc','run_id':10,'jobs':'10/10','result':'SUCCESS'}))),
 trans('dynamic_receipt_result_alias_only_blocked',lambda c:(c['terminal_receipt_projections'].__setitem__('RUN_MANIFEST',{'provider':'GITHUB_ACTIONS','repository_or_project':'owner/repo','head_sha':'abc','run_id':10,'job_denominator':'10/10','result':'SUCCESS'}))),
]
# two final combined attack cases to reach 52
results += [
 trans('combined_same_count_authority_and_receipt_alias_attack_blocked',lambda c:(c['unresolved_authority_records'][0].__setitem__('authority_evidence_ref','evil'),c['terminal_receipt_projections'].__setitem__('EXECUTION_STATE',{'head_sha':'abc','run_id':10,'jobs':'10/10','result':'SUCCESS'}))),
 trans('combined_cross_stage_identity_receipt_drift_blocked',lambda c:(c['unresolved_authority_records'][1].__setitem__('authority_ref','OTHER'),c['terminal_receipt_projections']['GOVERNANCE_CURRENT'].__setitem__('conclusion','FAIL'))),
]
assert len(results)==54,len(results)
out={'suite':'v2.1.11 binding authority identity / canonical terminal receipt schema multidirection regression','total':len(results),'passed_expectations':sum(x['ok'] for x in results),'results':results}
print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['passed_expectations']==out['total'] else 1)
