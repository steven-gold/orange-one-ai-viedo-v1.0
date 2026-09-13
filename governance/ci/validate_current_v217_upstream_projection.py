#!/usr/bin/env python3
from pathlib import Path
import shutil,subprocess,sys,tempfile,yaml
root=Path('.')
def die(msg): raise SystemExit(msg)
with tempfile.TemporaryDirectory() as td:
    t=Path(td)
    for fn in ('GOVERNANCE_CURRENT.yaml','REBUILD_BRANCH_BASELINE.yaml'):
        shutil.copy2(root/fn,t/fn)
    for rel in ('11_EVIDENCE','governance/test-runtime/v2.1.6','00_SOURCE_INTAKE/fresh_run_003'):
        src=root/rel; dst=t/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copytree(src,dst)
    run=t/'00_SOURCE_INTAKE/fresh_run_003'
    for rel in ('01_CLASSIFIED','02_BASE_BLUEPRINT','03_BLUEPRINT_BINDING'):
        if (run/rel).exists(): shutil.rmtree(run/rel)
    for evname in ('RESPONSIBILITY_CLASSIFICATION_EVIDENCE.yaml','PAGE_BASE_BLUEPRINT_EVIDENCE.yaml'):
        ev=run/'00_SOURCE_INTAKE/evidence'/evname
        if ev.exists(): ev.unlink()
    sp=run/'EXECUTION_STATE.yaml'; state=yaml.safe_load(sp.read_text(encoding='utf-8')) or {}
    state['state']='SOURCE_FACT_MATERIALIZATION_COMPLETED'
    state['responsibility_classification_started']=False; state['responsibility_classification_completed']=False
    state['domain_decomposition_started']=False; state['blueprint_materialization_started']=False
    state['page_base_blueprint_started']=False; state['page_base_blueprint_completed']=False
    state['visual_base_blueprint_started']=False; state['visual_base_blueprint_completed']=False
    state['blueprint_binding_started']=False; state['blueprint_binding_completed']=False
    state['website_construction_started']=False; state['deployment_started']=False
    for k in ('classification_artifact_count','classification_page_artifact_count','classification_visual_artifact_count','page_base_blueprint_count','governance_candidate_overlay'): state.pop(k,None)
    sp.write_text(yaml.safe_dump(state,allow_unicode=True,sort_keys=False),encoding='utf-8')
    for script in (root/'governance/ci/validate_current_v216_workspace.py',root/'governance/ci/validate_current_v216_source_facts.py'):
        r=subprocess.run([sys.executable,str(script.resolve())],cwd=t,text=True,capture_output=True)
        if r.returncode!=0:
            print(r.stdout); print(r.stderr,file=sys.stderr); die('upstream projection validator failed: '+script.name)
        print(r.stdout.strip())
print('PASS: sealed v2.1.6 Segment Mapping + Source Facts validators replay at their valid boundary while current workspace legally advances through Classification and Page Base Blueprint')
