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
        r=Path(td)/'pkg'; shutil.copytree(ROOT,r)
        p=r/rel; d=yaml.safe_load(p.read_text(encoding='utf-8')) or {}; mut(d); p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=160),encoding='utf-8')
        out=val.validate(r); return case(name,out['status']=='FAIL',{'failures':out.get('failures',[])[:8]})
def mutate_text(name,rel,mut):
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)/'pkg'; shutil.copytree(ROOT,r)
        p=r/rel; p.write_text(mut(p.read_text(encoding='utf-8')),encoding='utf-8'); out=val.validate(r)
        return case(name,out['status']=='FAIL',{'failures':out.get('failures',[])[:8]})
base=val.validate(ROOT)
life=yaml.safe_load((ROOT/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml').read_text()) or {}
inv=(life.get('cross_stage_invariants') or {}).get('closure_evidence_continuity') or {}
idx=yaml.safe_load((ROOT/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml').read_text()) or {}
results=[
 case('baseline_continuity_validator_pass',base['status']=='PASS',base),
 case('all_11_stages_covered',inv.get('applies_to_stages')==[f'STAGE-{i:02d}' for i in range(1,12)]),
 case('common_bundle_loads_s058','WEB-GOV-03-S058' in idx['mandatory_common_normative_bundles']['BUNDLE-GOV-COMMON-CORE']['section_uids']),
 case('monotonic_merge_append_semantics',inv.get('closure_mutation_semantics')=='MERGE_APPEND_OR_EXPLICIT_SUPERSEDE'),
 case('legal_successor_allowed',inv.get('legal_successor_presence')=='ALLOW'),
 case('retroactive_predecessor_invalidation_forbidden',inv.get('retroactive_predecessor_invalidation')=='FORBIDDEN'),
 case('predecessor_deletion_blocked',inv.get('established_predecessor_fact_deletion')=='BLOCK'),
 case('predecessor_reversion_blocked',inv.get('established_predecessor_fact_reversion')=='BLOCK'),
 case('current_ledger_sync_required',inv.get('current_ledger_synchronization_required') is True),
 case('terminal_receipt_external',inv.get('terminal_ci_receipt',{}).get('model')=='EXTERNAL_IMMUTABLE_RECEIPT'),
 case('terminal_self_write_forbidden',inv.get('terminal_ci_receipt',{}).get('self_write_same_commit_run_identity')=='FORBIDDEN'),
 case('materialization_terminal_distinct',inv.get('terminal_ci_receipt',{}).get('materialization_and_terminal_receipt_are_distinct') is True),
]
# Every downstream large stage must carry the common closure gate.
for sid in [f'STAGE-{i:02d}' for i in range(1,12)]:
    st=next(x for x in life['stages'] if x.get('stage_uid')==sid)
    results.append(case('continuity_gate_'+sid.lower(),(st.get('closure_evidence_continuity_gate') or {}).get('mode')=='REQUIRED'))
# Static destructive mutations.
results += [
 mutate_yaml('all_stage_coverage_shrink_blocked','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['applies_to_stages'].pop()),
 mutate_yaml('stage05_gate_deletion_blocked','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:[s.pop('closure_evidence_continuity_gate',None) for s in d['stages'] if s.get('stage_uid')=='STAGE-05']),
 mutate_yaml('destructive_rewrite_policy_blocked','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity'].__setitem__('closure_mutation_semantics','REPLACE_SUMMARY')),
 mutate_yaml('retroactive_invalidation_allow_blocked','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity'].__setitem__('retroactive_predecessor_invalidation','ALLOW')),
 mutate_yaml('ledger_set_shrink_blocked','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['current_ledgers'].remove('RUN_MANIFEST')),
 mutate_yaml('sync_dimension_loss_blocked','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['synchronization_dimensions'].remove('PREDECESSOR_PROOF')),
 mutate_yaml('terminal_receipt_internal_model_blocked','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['terminal_ci_receipt'].__setitem__('model','INTERNAL_SELF_WRITTEN')),
 mutate_yaml('terminal_required_field_loss_blocked','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['terminal_ci_receipt']['required_fields'].remove('head_sha')),
 mutate_yaml('common_bundle_s058_removal_blocked','10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['mandatory_common_normative_bundles']['BUNDLE-GOV-COMMON-CORE']['section_uids'].remove('WEB-GOV-03-S058')),
 mutate_text('normative_self_reference_rule_removal_blocked','12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',lambda t:t.replace('infinite self-reference loop','self reference')),
]
# Dynamic transition stress.
prev={'predecessor_facts':{'source_fact_started':True,'source_fact_completed':True,'replay_proof':'proof-A','checkpoint_sha':'abc','gate_status':'SUCCESS'}}
def transition(name,current,expect_fail):
    out=val.validate_transition(prev,current); return case(name,(out['status']=='FAIL')==expect_fail,out)
base_ledgers={k:{'current_phase':'VISUAL_CLOSED','artifact_count':2,'authority_identity':'8_GAPS','gate_status':'SUCCESS','next_transition':'BINDING','predecessor_proof':'proof-A'} for k in ['EXECUTION_STATE','RUN_MANIFEST','ARTIFACT_PLAN']}
current_ok={'predecessor_facts':dict(prev['predecessor_facts']),'ledgers':base_ledgers,'materialization_evidence':{'run_id':100,'head_sha':'aaa'},'terminal_receipt':{'provider':'GitHub','repository_or_project':'repo','head_sha':'bbb','run_id':101,'job_denominator':'8/8','conclusion':'SUCCESS'},'requires_distinct_terminal_receipt':True,'receipt_reference_commit_sha':'ccc'}
results += [
 transition('dynamic_valid_successor_closure_pass',current_ok,False),
 transition('dynamic_started_fact_deletion_blocked',{**current_ok,'predecessor_facts':{k:v for k,v in prev['predecessor_facts'].items() if k!='source_fact_started'}},True),
 transition('dynamic_completion_reversion_blocked',{**current_ok,'predecessor_facts':{**prev['predecessor_facts'],'source_fact_completed':False}},True),
 transition('dynamic_replay_proof_loss_blocked',{**current_ok,'predecessor_facts':{k:v for k,v in prev['predecessor_facts'].items() if k!='replay_proof'}},True),
 transition('dynamic_checkpoint_drift_blocked',{**current_ok,'predecessor_facts':{**prev['predecessor_facts'],'checkpoint_sha':'zzz'}},True),
 transition('dynamic_cross_ledger_phase_drift_blocked',{**current_ok,'ledgers':{**base_ledgers,'RUN_MANIFEST':{**base_ledgers['RUN_MANIFEST'],'current_phase':'BINDING'}}},True),
 transition('dynamic_cross_ledger_gate_drift_blocked',{**current_ok,'ledgers':{**base_ledgers,'ARTIFACT_PLAN':{**base_ledgers['ARTIFACT_PLAN'],'gate_status':'PENDING'}}},True),
 transition('dynamic_terminal_head_missing_blocked',{**current_ok,'terminal_receipt':{k:v for k,v in current_ok['terminal_receipt'].items() if k!='head_sha'}},True),
 transition('dynamic_terminal_self_reference_blocked',{**current_ok,'terminal_receipt':{**current_ok['terminal_receipt'],'head_sha':'ccc'}},True),
 transition('dynamic_materialization_terminal_same_receipt_blocked',{**current_ok,'terminal_receipt':{**current_ok['terminal_receipt'],'head_sha':'aaa','run_id':100},'receipt_reference_commit_sha':'ccc'},True),
]
assert len(results)==43, len(results)
out={'suite':'v2.1.10 closure evidence continuity / current ledger synchronization / terminal CI receipt multidirection regression','total':len(results),'passed_expectations':sum(x['ok'] for x in results),'results':results}
print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['passed_expectations']==out['total'] else 1)
