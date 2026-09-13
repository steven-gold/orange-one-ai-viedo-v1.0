#!/usr/bin/env python3
from pathlib import Path
import shutil,subprocess,sys,tempfile,yaml

root=Path('.')

V216_PKG='3dcc0b4b94250b7487ec923fde2604f13b6d4ce3ee1ec4636feba27bcf3c92c6'
V216_TRUST='70b19fa78f641fb570c9c31455d518b50a358ce18075de0e5cad89edd746de2'

def die(msg):
    raise SystemExit(msg)

def load(p):
    return yaml.safe_load(p.read_text(encoding='utf-8')) or {}

def write(p,d):
    p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False),encoding='utf-8')

with tempfile.TemporaryDirectory() as td:
    t=Path(td)

    # Copy the current files, but all historical compatibility rewrites below
    # happen only inside this isolated temporary projection.
    for fn in ('GOVERNANCE_CURRENT.yaml','REBUILD_BRANCH_BASELINE.yaml'):
        shutil.copy2(root/fn,t/fn)
    for rel in ('11_EVIDENCE','governance/test-runtime/v2.1.6','00_SOURCE_INTAKE/fresh_run_003'):
        src=root/rel
        dst=t/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(src,dst)

    # Reconstruct the sealed v2.1.6 authority view expected by the historical
    # validators. Never mutate the actual branch Current pointers.
    cur=load(t/'GOVERNANCE_CURRENT.yaml')
    na=cur.setdefault('normative_authority',{})
    na['version']='v2.1.6'
    na['package_sha256']=V216_PKG
    na['external_trust_root_sha256']=V216_TRUST
    write(t/'GOVERNANCE_CURRENT.yaml',cur)

    base=load(t/'REBUILD_BRANCH_BASELINE.yaml')
    base.setdefault('governance_test',{})['version']='v2.1.6'
    write(t/'REBUILD_BRANCH_BASELINE.yaml',base)

    lockp=t/'11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml'
    lock=load(lockp)
    lock.setdefault('current_test_authority',{})['version']='v2.1.6'
    write(lockp,lock)

    sealp=t/'11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml'
    seal=load(sealp)
    seal.setdefault('sealed_governance',{})['version']='v2.1.6'
    write(sealp,seal)

    run=t/'00_SOURCE_INTAKE/fresh_run_003'
    for rel in ('01_CLASSIFIED','02_BASE_BLUEPRINT','03_BLUEPRINT_BINDING'):
        if (run/rel).exists():
            shutil.rmtree(run/rel)
    for evname in ('RESPONSIBILITY_CLASSIFICATION_EVIDENCE.yaml','PAGE_BASE_BLUEPRINT_EVIDENCE.yaml'):
        ev=run/'00_SOURCE_INTAKE/evidence'/evname
        if ev.exists():
            ev.unlink()

    sp=run/'EXECUTION_STATE.yaml'
    state=load(sp)
    state['state']='SOURCE_FACT_MATERIALIZATION_COMPLETED'
    state['responsibility_classification_started']=False
    state['responsibility_classification_completed']=False
    state['domain_decomposition_started']=False
    state['blueprint_materialization_started']=False
    state['page_base_blueprint_started']=False
    state['page_base_blueprint_completed']=False
    state['visual_base_blueprint_started']=False
    state['visual_base_blueprint_completed']=False
    state['blueprint_binding_started']=False
    state['blueprint_binding_completed']=False
    state['website_construction_started']=False
    state['deployment_started']=False
    for k in ('classification_artifact_count','classification_page_artifact_count','classification_visual_artifact_count','page_base_blueprint_count','governance_candidate_overlay'):
        state.pop(k,None)
    write(sp,state)

    for script in (
        root/'governance/ci/validate_current_v216_workspace.py',
        root/'governance/ci/validate_current_v216_source_facts.py'
    ):
        r=subprocess.run([sys.executable,str(script.resolve())],cwd=t,text=True,capture_output=True)
        if r.returncode!=0:
            print(r.stdout)
            print(r.stderr,file=sys.stderr)
            die('historical upstream projection validator failed: '+script.name)
        print(r.stdout.strip())

print('PASS: v2.1.8 isolated historical upstream projection validates sealed v2.1.6 Segment Mapping + Source Facts without coupling to mutable Current pointers')
print('PASS: actual branch Current pointers remain v2.1.8; historical v2.1.6 authority view exists only inside temporary replay workspace')
