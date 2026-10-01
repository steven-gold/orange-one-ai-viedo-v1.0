#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
import sys as _s
if __name__ != "__main__" and "pytest" in _s.modules:
    import pytest as _p; _p.skip("standalone governance regression executable",allow_module_level=True)
from pathlib import Path
import importlib.util,json,shutil,tempfile,yaml
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('v',HERE/'validate_closure_evidence_continuity.py')
v=importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
def case(name,ok,detail=None): return {'case':name,'ok':bool(ok),'detail':detail or {}}
def mutate(name,mut):
    with tempfile.TemporaryDirectory() as td:
        rr=Path(td)/'pkg'; shutil.copytree(ROOT,rr)
        p=rr/'10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml'
        d=yaml.safe_load(p.read_text(encoding='utf-8')) or {}; mut(d)
        p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
        out=v.validate(rr); return case(name,out['status']=='FAIL',out)
life=yaml.safe_load((ROOT/'10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml').read_text(encoding='utf-8')) or {}
inv=((life.get('cross_stage_invariants') or {}).get('closure_evidence_continuity') or {})
ua=inv.get('unresolved_authority_identity') or {}
facts=set(inv.get('content_closure_required_facts') or [])
AUTH=['gap_uid','authority_ref','disposition','authority_evidence_ref']
expected_facts={'REQUIRED_OPERATION_RESULTS','REQUIRED_OUTPUTS_AND_FIELDS','REQUIRED_SCANNER_RESULTS','REQUIRED_VALIDATOR_RESULTS','REQUIRED_EVIDENCE','ZERO_REQUIRED_GAPS_AND_BLOCKERS','REGISTERED_HUMAN_GATE_IF_APPLICABLE'}
base=v.validate(ROOT)
res=[
 case('baseline_validator_pass',base['status']=='PASS',base),
 case('authority_tuple_exact_fields',ua.get('canonical_tuple_fields')==AUTH),
 case('authority_exact_carry_required',ua.get('carry_forward_exact_tuple_required') is True),
 case('authority_count_uid_only_blocked',ua.get('count_only_or_uid_only_validation')=='BLOCK'),
 case('authority_evidence_ref_required',ua.get('authority_evidence_ref_required') is True),
 case('authority_tuple_change_requires_supersession',ua.get('explicit_supersession_required_for_tuple_change') is True),
 case('single_current_state_authority',inv.get('current_state_authority')=='EXECUTION_STATE'),
 case('parallel_mutable_state_forbidden',inv.get('parallel_mutable_current_state_authority')=='FORBIDDEN'),
 case('cross_ledger_state_sync_removed',inv.get('cross_ledger_state_synchronization_required') is False),
 case('terminal_ci_not_product_closure_gate',inv.get('terminal_ci_receipt_required_for_stage_closure') is False),
 case('terminal_ci_role_optional_transport',inv.get('terminal_ci_receipt_role')=='OPTIONAL_TRANSPORT_ATTESTATION'),
 case('content_closure_denominator_exact',facts==expected_facts),
]
for sid in [f'STAGE-{i:02d}' for i in range(1,12)]:
    st=next(x for x in life['stages'] if x['stage_uid']==sid)
    res.append(case('common_gate_'+sid.lower(),(st.get('closure_evidence_continuity_gate') or {}).get('mode')=='REQUIRED'))
res += [
 mutate('authority_tuple_field_drop_blocked',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['unresolved_authority_identity']['canonical_tuple_fields'].remove('authority_evidence_ref')),
 mutate('authority_count_only_allow_blocked',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['unresolved_authority_identity'].__setitem__('count_only_or_uid_only_validation','ALLOW')),
 mutate('authority_exact_carry_disable_blocked',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['unresolved_authority_identity'].__setitem__('carry_forward_exact_tuple_required',False)),
 mutate('parallel_state_allow_blocked',lambda d:d['cross_stage_invariants']['closure_evidence_continuity'].__setitem__('parallel_mutable_current_state_authority','ALLOW')),
 mutate('terminal_ci_reintroduced_blocked',lambda d:d['cross_stage_invariants']['closure_evidence_continuity'].__setitem__('terminal_ci_receipt_required_for_stage_closure',True)),
]
prev_auth=[{'gap_uid':'GAP-001','authority_ref':'A@1','disposition':'UNRESOLVED_AUTHORITY_GAP','authority_evidence_ref':'e#1'},{'gap_uid':'GAP-002','authority_ref':'B@1','disposition':'UNRESOLVED_AUTHORITY_GAP','authority_evidence_ref':'e#2'}]
prev={'predecessor_facts':{'completed':True,'proof':'p'},'unresolved_authority_records':prev_auth}
def authority_transition(name,mut,expect_fail=True):
    cur={'predecessor_facts':dict(prev['predecessor_facts']),'unresolved_authority_records':[dict(x) for x in prev_auth]}
    mut(cur)
    failures=[]
    current=cur['unresolved_authority_records']
    if len(current)!=len(prev_auth): failures.append('authority_record_count_drift')
    else:
        for a,b in zip(prev_auth,current):
            if any(a.get(k)!=b.get(k) for k in AUTH): failures.append('authority_tuple_drift')
    ok=(bool(failures)==expect_fail)
    return case(name,ok,{'failures':failures})
res += [
 authority_transition('dynamic_authority_valid_exact_tuple_pass',lambda c:None,False),
 authority_transition('dynamic_authority_ref_drift_blocked',lambda c:c['unresolved_authority_records'][0].__setitem__('authority_ref','WRONG')),
 authority_transition('dynamic_authority_evidence_ref_drift_blocked',lambda c:c['unresolved_authority_records'][0].__setitem__('authority_evidence_ref','wrong')),
 authority_transition('dynamic_authority_disposition_drift_blocked',lambda c:c['unresolved_authority_records'][0].__setitem__('disposition','SATISFIED')),
 authority_transition('dynamic_authority_gap_uid_drift_blocked',lambda c:c['unresolved_authority_records'][0].__setitem__('gap_uid','GAP-X')),
 authority_transition('dynamic_authority_record_drop_blocked',lambda c:c['unresolved_authority_records'].pop()),
 authority_transition('dynamic_authority_same_count_identity_change_blocked',lambda c:c['unresolved_authority_records'][1].__setitem__('authority_ref','OTHER')),
 authority_transition('dynamic_authority_missing_evidence_ref_blocked',lambda c:c['unresolved_authority_records'][0].pop('authority_evidence_ref')),
]
res += [
 case('dynamic_single_state_transition_pass',v.validate_transition({'predecessor_facts':{'completed':True}},{'predecessor_facts':{'completed':True}})['status']=='PASS'),
 case('dynamic_parallel_state_blocked',v.validate_transition({'predecessor_facts':{'completed':True}},{'predecessor_facts':{'completed':True},'parallel_state_authority':True})['status']=='FAIL'),
 case('dynamic_terminal_ci_reintroduced_blocked',v.validate_transition({'predecessor_facts':{'completed':True}},{'predecessor_facts':{'completed':True},'terminal_ci_required_for_closure':True})['status']=='FAIL'),
 case('optional_receipt_metadata_drift_does_not_block_content',v.validate_transition({'predecessor_facts':{'completed':True}},{'predecessor_facts':{'completed':True},'terminal_receipt':{'head_sha':'different'}})['status']=='PASS'),
 case('optional_receipt_omission_does_not_block_content',v.validate_transition({'predecessor_facts':{'completed':True}},{'predecessor_facts':{'completed':True}})['status']=='PASS'),
]
for fact in sorted(expected_facts):
    res.append(case('content_fact_registered_'+fact.lower(),fact in facts))
bp=yaml.safe_load((ROOT/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml').read_text(encoding='utf-8')) or {}
ab=bp.get('closure_evidence_continuity_contract') or {}
res += [
 case('acceptance_single_state',ab.get('current_state_authority')=='EXECUTION_STATE'),
 case('acceptance_parallel_state_forbidden',ab.get('parallel_mutable_current_state_authority')=='FORBIDDEN'),
 case('acceptance_terminal_ci_optional',ab.get('terminal_ci_receipt_required_for_product_stage_closure') is False),
]
s1=yaml.safe_load((ROOT/'10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml').read_text(encoding='utf-8')) or {}
sc=s1.get('closure_evidence_continuity_contract') or {}
res += [
 case('stage1_single_state',sc.get('current_state_authority')=='EXECUTION_STATE'),
 case('stage1_no_cross_ledger_state_sync',sc.get('cross_ledger_state_synchronization_required') is False),
 case('stage1_terminal_ci_optional',sc.get('terminal_ci_receipt_required_for_stage_closure') is False),
]
out={'suite':'v2.1.11 single-state authority continuity / optional transport receipt regression','total':len(res),'passed_expectations':sum(x['ok'] for x in res),'results':res}
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['total']==54 and out['passed_expectations']==54 else 1)
