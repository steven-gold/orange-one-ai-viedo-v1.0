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
        src=root/rel; dst=t/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(src,dst)
    run=t/'00_SOURCE_INTAKE/fresh_run_003'
    if (run/'01_CLASSIFIED').exists(): shutil.rmtree(run/'01_CLASSIFIED')
    ev=run/'00_SOURCE_INTAKE/evidence/RESPONSIBILITY_CLASSIFICATION_EVIDENCE.yaml'
    if ev.exists(): ev.unlink()
    sp=run/'EXECUTION_STATE.yaml'
    state=yaml.safe_load(sp.read_text(encoding='utf-8')) or {}
    state['state']='SOURCE_FACT_MATERIALIZATION_COMPLETED'
    state['responsibility_classification_started']=False
    state['responsibility_classification_completed']=False
    state['domain_decomposition_started']=False
    state['blueprint_materialization_started']=False
    state['website_construction_started']=False
    state['deployment_started']=False
    for k in ('classification_artifact_count','classification_page_artifact_count','classification_visual_artifact_count','governance_candidate_overlay'):
        state.pop(k,None)
    sp.write_text(yaml.safe_dump(state,allow_unicode=True,sort_keys=False),encoding='utf-8')
    checks=[
      root/'governance/ci/validate_current_v216_workspace.py',
      root/'governance/ci/validate_current_v216_source_facts.py',
    ]
    for script in checks:
        r=subprocess.run([sys.executable,str(script.resolve())],cwd=t,text=True,capture_output=True)
        if r.returncode!=0:
            print(r.stdout); print(r.stderr,file=sys.stderr)
            die('upstream projection validator failed: '+script.name)
        print(r.stdout.strip())
print('PASS: v2.1.7 upstream projection replays sealed v2.1.6 Segment Mapping + Source Facts validators at their valid phase boundary while current workspace may legally advance to Responsibility Classification')
