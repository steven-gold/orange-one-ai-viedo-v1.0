#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
import sys as _governance_runner_sys
if __name__ != "__main__" and "pytest" in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip("standalone governance regression executable; use registered subprocess runner", allow_module_level=True)
from pathlib import Path
import json, yaml, tempfile, shutil, importlib.util
PKG=Path(__file__).resolve().parents[2]
VP=Path(__file__).resolve().parent/'validate_closure_evidence_continuity.py'
spec=importlib.util.spec_from_file_location('cont',VP); cont=importlib.util.module_from_spec(spec); spec.loader.exec_module(cont)
VP219=Path(__file__).resolve().parent/'validate_evidence_state_closure.py'
spec219=importlib.util.spec_from_file_location('ev219',VP219); ev219=importlib.util.module_from_spec(spec219); spec219.loader.exec_module(ev219)

def case(name,ok,detail=None): return {'case':name,'ok':bool(ok),'detail':detail or {}}
def previous(stage):
    return {'stage_uid':stage,'terminal_state':stage+'_CLOSED','completed':True,'proof_identity':'proof-'+stage,'authority_identity':'AUTH-8-GAPS','terminal_receipt':{'provider':'GITHUB_ACTIONS','repository_or_project':'repo','head_sha':'abc','run_id':123,'job_denominator':'12/12','conclusion':'SUCCESS'}}
def current(prev,cstage,**kw):
    d={'current_stage_uid':cstage,'current_state':cstage+'_ACTIVE','successor_started':cstage!=prev['stage_uid'],'predecessor_completed':True,'proof_identity':prev['proof_identity'],'authority_identity':prev['authority_identity'],'terminal_receipt':dict(prev['terminal_receipt'])}
    d.update(kw); return d
legal=[(f'STAGE-{i:02d}',f'STAGE-{i+1:02d}') for i in range(1,11)]
res=[]
# 10 legal successor cases: global current state changes, predecessor remains valid.
for pstage,cstage in legal:
    p=previous(pstage); out=cont.validate_predecessor_successor_state(p,current(p,cstage),legal)
    res.append(case('legal_successor_'+pstage+'_to_'+cstage,out['status']=='PASS',out))
# 9 illegal skip cases must remain blocked.
for i in range(1,10):
    pstage=f'STAGE-{i:02d}'; cstage=f'STAGE-{i+2:02d}'; p=previous(pstage); out=cont.validate_predecessor_successor_state(p,current(p,cstage),legal)
    res.append(case('illegal_skip_'+pstage+'_to_'+cstage,out['status']=='FAIL' and 'illegal_successor_or_stage_skip' in out['failures'],out))
# 10 completion reversions on legal successor edges.
for pstage,cstage in legal:
    p=previous(pstage); out=cont.validate_predecessor_successor_state(p,current(p,cstage,predecessor_completed=False),legal)
    res.append(case('completion_reversion_'+pstage,out['status']=='FAIL' and 'predecessor_completion_reverted' in out['failures'],out))
# 5 proof identity drifts.
for pstage,cstage in legal[:5]:
    p=previous(pstage); out=cont.validate_predecessor_successor_state(p,current(p,cstage,proof_identity='drift'),legal)
    res.append(case('proof_drift_'+pstage,out['status']=='FAIL' and 'predecessor_proof_identity_drift' in out['failures'],out))
# 5 authority identity drifts.
for pstage,cstage in legal[5:]:
    p=previous(pstage); out=cont.validate_predecessor_successor_state(p,current(p,cstage,authority_identity='DRIFT'),legal)
    res.append(case('authority_drift_'+pstage,out['status']=='FAIL' and 'predecessor_authority_identity_drift' in out['failures'],out))
# 5 terminal receipt drifts.
for pstage,cstage in legal[:5]:
    p=previous(pstage); bad=dict(p['terminal_receipt']); bad['run_id']=999
    out=cont.validate_predecessor_successor_state(p,current(p,cstage,terminal_receipt=bad),legal)
    res.append(case('receipt_drift_'+pstage,out['status']=='FAIL' and 'predecessor_terminal_receipt_drift' in out['failures'],out))
# 4 static contract mutation attacks.
def mutate_case(name,mutator,expected_fragment):
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)/'pkg'; shutil.copytree(PKG,r)
        p=r/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'; d=yaml.safe_load(p.read_text())
        mutator(d); p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=180))
        out=cont.validate(r); ok=out['status']=='FAIL' and any(expected_fragment in x for x in out['failures'])
        res.append(case(name,ok,{'failures':out['failures'][:8]}))
mutate_case('static_exact_state_lock_allow_blocked',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['predecessor_validator_successor_state_contract'].__setitem__('current_state_exact_predecessor_terminal_equality_as_pass_condition','ALLOW'),'predecessor_successor_state_contract_drift')
mutate_case('static_successor_started_false_required_blocked',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['predecessor_validator_successor_state_contract'].__setitem__('successor_started_false_as_permanent_pass_condition','REQUIRED'),'predecessor_successor_state_contract_drift')
mutate_case('static_phase_order_owner_drift_blocked',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['predecessor_validator_successor_state_contract'].__setitem__('phase_order_owner','PREDECESSOR_VALIDATOR'),'predecessor_successor_state_contract_drift')
mutate_case('static_presence_only_evidence_allow_blocked',lambda d:d['cross_stage_invariants']['required_evidence_integrity'].__setitem__('presence_only_acceptance','ALLOW'),'required_evidence_integrity_contract_incomplete')
# 8 evidence parse/schema cases.
ev=[
 ('evidence_valid_yaml', 'uid: E1\nstatus: PASS\n', 'yaml',['uid','status'],'PASS'),
 ('evidence_valid_json', '{"uid":"E1","status":"PASS"}', 'json',['uid','status'],'PASS'),
 ('evidence_malformed_yaml_blocked', 'uid: E1\nfact: value: invalid\n', 'yaml',['uid'],'FAIL'),
 ('evidence_malformed_json_blocked', '{"uid":"E1",', 'json',['uid'],'FAIL'),
 ('evidence_missing_required_field_blocked', 'uid: E1\n', 'yaml',['uid','status'],'FAIL'),
 ('evidence_scalar_root_blocked', '- a\n- b\n', 'yaml',[],'FAIL'),
 ('evidence_empty_yaml_blocked', '', 'yaml',[],'FAIL'),
 ('evidence_unsupported_parser_blocked', 'uid=E1', 'toml',['uid'],'FAIL'),
]
for name,text,fmt,fields,expected in ev:
    out=cont.validate_required_evidence_bytes(text,fmt,fields); res.append(case(name,out['status']==expected,out))


# 4 historical predecessor-validator successor-awareness cases.
out219=ev219.validate(PKG)
res.append(case('historical_v219_validator_accepts_v212_successor',out219['status']=='PASS',out219))
with tempfile.TemporaryDirectory() as td:
    r=Path(td)/'pkg'; shutil.copytree(PKG,r)
    p=r/'11_EVIDENCE/audit/GOVERNANCE_DEFECT_LEDGER.yaml'; d=yaml.safe_load(p.read_text())
    next(x for x in d['defects'] if x.get('defect_uid')=='DEF-V212-PREDECESSOR-CURRENT-STATE-LOCK-001')['status']='FIXED_PREFORMAL_CONSTITUENT_VERIFIED_GITHUB_REPLAY_PENDING'
    p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=180))
    o=ev219.validate(r); res.append(case('historical_v219_allows_future_successor_pending_defect',o['status']=='PASS',o))
with tempfile.TemporaryDirectory() as td:
    r=Path(td)/'pkg'; shutil.copytree(PKG,r)
    p=r/'11_EVIDENCE/audit/GOVERNANCE_DEFECT_LEDGER.yaml'; d=yaml.safe_load(p.read_text())
    next(x for x in d['defects'] if x.get('defect_uid')=='DEF-V218-PREDECESSOR-VALIDATOR-SUCCESSOR-REJECTION-001')['status']='FIXED_PREFORMAL_VERIFIED_GITHUB_REPLAY_PENDING'
    p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=180))
    o=ev219.validate(r); res.append(case('historical_v219_blocks_owned_v218_pending_regression',o['status']=='FAIL' and any('superseded_defect_pending_states' in x for x in o['failures']),o))
with tempfile.TemporaryDirectory() as td:
    r=Path(td)/'pkg'; shutil.copytree(PKG,r)
    p=r/'11_EVIDENCE/audit/GOVERNANCE_DEFECT_LEDGER.yaml'; d=yaml.safe_load(p.read_text())
    next(x for x in d['defects'] if x.get('defect_uid')=='DEF-V219-IMMUTABLE-PACKAGE-EVIDENCE-STATE-DRIFT-001')['status']='FIXED_PREFORMAL_REVERIFY_PENDING'
    p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=180))
    o=ev219.validate(r); res.append(case('historical_v219_blocks_owned_v219_pending_regression',o['status']=='FAIL' and any('superseded_defect_pending_states' in x for x in o['failures']),o))

out={'suite':'v2.1.12 successor-state monotonic predecessor validation / Required Evidence parse-integrity multidirection high-pressure regression','total':len(res),'passed_expectations':sum(x['ok'] for x in res),'results':res}
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['total']==60 and out['passed_expectations']==60 else 1)
