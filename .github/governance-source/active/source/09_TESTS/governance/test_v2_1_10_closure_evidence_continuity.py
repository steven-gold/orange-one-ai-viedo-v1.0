#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
import sys as _s
if __name__ != "__main__" and "pytest" in _s.modules:
    import pytest as _p; _p.skip("standalone governance regression executable",allow_module_level=True)
from pathlib import Path
import importlib.util,json,shutil,tempfile,yaml
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('v',HERE/'validate_closure_evidence_continuity.py'); v=importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
def case(name,ok,detail=None): return {'case':name,'ok':bool(ok),'detail':detail or {}}
def mutate(name,rel,fn):
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)/'pkg'; shutil.copytree(ROOT,r); p=r/rel; d=yaml.safe_load(p.read_text(encoding='utf-8')) or {}; fn(d); p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False),encoding='utf-8'); o=v.validate(r); return case(name,o['status']=='FAIL',o)
base=v.validate(ROOT); life=yaml.safe_load((ROOT/'10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml').read_text()) or {}; inv=(life.get('cross_stage_invariants') or {}).get('closure_evidence_continuity') or {}
res=[case('baseline',base['status']=='PASS',base),case('single_state',inv.get('current_state_authority')=='EXECUTION_STATE'),case('no_parallel_state',inv.get('parallel_mutable_current_state_authority')=='FORBIDDEN'),case('no_cross_ledger_state_sync',inv.get('cross_ledger_state_synchronization_required') is False),case('ci_not_closure',inv.get('terminal_ci_receipt_required_for_stage_closure') is False)]
res += [
 mutate('single_state_mutation_blocked','10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity'].__setitem__('current_state_authority','WORK_UNIT')),
 mutate('parallel_state_mutation_blocked','10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity'].__setitem__('parallel_mutable_current_state_authority','ALLOW')),
 mutate('cross_ledger_reintroduction_blocked','10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity'].__setitem__('cross_ledger_state_synchronization_required',True)),
 mutate('terminal_ci_reintroduction_blocked','10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity'].__setitem__('terminal_ci_receipt_required_for_stage_closure',True)),
 mutate('content_denominator_shrink_blocked','10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml',lambda d:d['cross_stage_invariants']['closure_evidence_continuity']['content_closure_required_facts'].pop()),
]
prev={'predecessor_facts':{'completed':True,'proof':'A','authority':'AUTH-A'}}
res.append(case('transition_keeps_content_proof',v.validate_transition(prev,{'predecessor_facts':dict(prev['predecessor_facts'])})['status']=='PASS'))
res.append(case('transition_fact_loss_blocked',v.validate_transition(prev,{'predecessor_facts':{'completed':True,'authority':'AUTH-A'}})['status']=='FAIL'))
res.append(case('parallel_state_dynamic_blocked',v.validate_transition(prev,{'predecessor_facts':dict(prev['predecessor_facts']),'parallel_state_authority':True})['status']=='FAIL'))
res.append(case('terminal_ci_dynamic_reintroduction_blocked',v.validate_transition(prev,{'predecessor_facts':dict(prev['predecessor_facts']),'terminal_ci_required_for_closure':True})['status']=='FAIL'))
out={'suite':'v2.1.10 simplified content closure / single execution state regression','total':len(res),'passed_expectations':sum(x['ok'] for x in res),'results':res}
print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['passed_expectations']==out['total'] else 1)
