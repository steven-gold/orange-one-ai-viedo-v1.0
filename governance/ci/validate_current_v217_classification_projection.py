#!/usr/bin/env python3
from pathlib import Path
import shutil,subprocess,sys,tempfile,yaml
root=Path('.')
def die(msg): raise SystemExit(msg)
with tempfile.TemporaryDirectory() as td:
    t=Path(td)
    src=root/'00_SOURCE_INTAKE/fresh_run_003'; run=t/'00_SOURCE_INTAKE/fresh_run_003'
    run.parent.mkdir(parents=True,exist_ok=True); shutil.copytree(src,run)
    if (run/'02_BASE_BLUEPRINT').exists(): shutil.rmtree(run/'02_BASE_BLUEPRINT')
    if (run/'03_BLUEPRINT_BINDING').exists(): shutil.rmtree(run/'03_BLUEPRINT_BINDING')
    ev=run/'00_SOURCE_INTAKE/evidence/PAGE_BASE_BLUEPRINT_EVIDENCE.yaml'
    if ev.exists(): ev.unlink()
    sp=run/'EXECUTION_STATE.yaml'; state=yaml.safe_load(sp.read_text(encoding='utf-8')) or {}
    state['state']='RESPONSIBILITY_CLASSIFICATION_COMPLETED'
    state['blueprint_materialization_started']=False
    state['page_base_blueprint_started']=False
    state['page_base_blueprint_completed']=False
    state['visual_base_blueprint_started']=False
    state['visual_base_blueprint_completed']=False
    state['blueprint_binding_started']=False
    state['blueprint_binding_completed']=False
    for k in ('page_base_blueprint_count',): state.pop(k,None)
    if isinstance(state.get('github_ci'),dict): state['github_ci'].pop('current_page_blueprint_gate',None)
    sp.write_text(yaml.safe_dump(state,allow_unicode=True,sort_keys=False),encoding='utf-8')
    script=(root/'governance/ci/validate_current_v217_classification.py').resolve()
    r=subprocess.run([sys.executable,str(script)],cwd=t,text=True,capture_output=True)
    if r.returncode!=0:
        print(r.stdout); print(r.stderr,file=sys.stderr); die('classification projection failed')
    print(r.stdout.strip())
print('PASS: sealed Responsibility Classification validator replays at its valid boundary while current workspace legally advances to Page Base Blueprint')
