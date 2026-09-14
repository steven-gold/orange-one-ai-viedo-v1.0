#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
import sys as _governance_runner_sys
if __name__ != "__main__" and "pytest" in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip("standalone governance regression executable; use registered subprocess runner", allow_module_level=True)
import importlib.util, tempfile, pathlib, yaml, json, sys
base=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(base))
spec=importlib.util.spec_from_file_location('vg', base/'validate_governance.py')
vg=importlib.util.module_from_spec(spec); spec.loader.exec_module(vg)

def write(root, rel, data):
    p=root/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(yaml.safe_dump(data,sort_keys=False,allow_unicode=True),encoding='utf-8')

def run(name, setup, fn, expect='FAIL'):
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td); setup(root); vg.ROOT=root; vg.RESULTS=[]; fn(); r=vg.RESULTS[-1]
        return {'case':name,'actual':r['status'],'expected':expect,'ok':r['status']==expect,'details':r.get('details')}

def ctx(root, cycle='INITIAL_RELEASE', uid='RUN-NEW'):
    write(root,'11_EVIDENCE/audit/VALIDATION_RUN_CONTEXT.yaml',{'run_uid':uid,'execution_cycle':cycle,'source_revision':'sha-new','started_at':'2026-09-12T01:00:00Z','terminal_status':'RUNNING'})

results=[]
results.append(run('post_v18_validation_run_uid_missing',lambda r: None,vg.check_validation_run_freshness))

def stale_setup(r):
    ctx(r)
    nodes={k:'ok' for k in ['business_intent','preconditions','entry','input_source','trigger','gate','permission','action','validation','response_feedback','success_state','next_state','next_step','next_gate','failure_state','recovery','terminal_outcome']}
    nodes.update({'payload':'N/A','api_entry':'N/A','runtime_owner':'N/A','data_provider':'N/A','audit_event':'local'})
    write(r,'11_EVIDENCE/audit/FUNCTIONAL_CHAIN_MATRIX.yaml',{'run_uid':'RUN-OLD','source_revision':'sha-old','chains':[{'flow_uid':'UI','effect_type':'UI_ONLY','binding_kind':'CLIENT_STATE_OR_VIEW_NO_API_REQUIRED','required':True,'classification':'COMPLETE','not_applicable_authority_evidence':'authority','nodes':nodes}]})
results.append(run('post_v18_stale_pass_replay_blocked',stale_setup,vg.check_functional_chain))

results.append(run('post_v18_execution_cycle_initial_release_closure',lambda r: ctx(r),vg.check_execution_cycle))

def repo_setup(r):
    write(r,'11_EVIDENCE/audit/REPOSITORY_BOUNDARY.yaml',{'repo_root':'repo','governed_paths':['12_DOCS','../escape'],'evidence_root':'11_EVIDENCE'})
results.append(run('post_v18_repository_boundary_escape_blocked',repo_setup,vg.check_repository_boundary))

def approval_setup(r):
    write(r,'11_EVIDENCE/audit/DESIGN_APPROVAL_LEDGER.yaml',{'visual_review_status':'PASS','design_approval_status':'PASS','freeze_status':'PASS','design_revision':'D2','approved_design_revision':'D2','visual_reviewed_at':'2026-09-12T03:00:00Z','design_approved_at':'2026-09-12T02:00:00Z','frozen_at':'2026-09-12T04:00:00Z'})
results.append(run('post_v18_approval_timing_blocked',approval_setup,vg.check_design_approval_timing))

def dep_setup(r):
    write(r,'11_EVIDENCE/audit/DEPLOYMENT_APPLICABILITY.yaml',{'deployment_applicable':True,'build_gate_consumed':True,'deployment_gate_consumed':True,'production_identity_gate_consumed':False,'production_browser_gate_consumed':True})
results.append(run('post_v18_deployment_applicability_requires_all_gates',dep_setup,vg.check_deployment_applicability))
print(json.dumps({'total':len(results),'passed_expectations':sum(x['ok'] for x in results),'results':results},ensure_ascii=False,indent=2))
if not all(x['ok'] for x in results): raise SystemExit(1)
