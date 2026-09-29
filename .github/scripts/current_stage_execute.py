#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, sys
from pathlib import Path
import yaml

def load(path):
    obj=yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(obj,dict):
        raise SystemExit(f"BLOCK:MAPPING_REQUIRED:{path}")
    return obj

def run(cmd,cwd,env=None):
    cp=subprocess.run(cmd,cwd=cwd,env=env,text=True)
    if cp.returncode!=0:
        raise SystemExit(cp.returncode)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage",required=True)
    ap.add_argument("--work-units",required=True)
    ap.add_argument("--product-root",required=True)
    ap.add_argument("--governance-root",required=True)
    args=ap.parse_args()
    root=Path(args.product_root).resolve()
    govroot=Path(args.governance_root).resolve()
    reg=load(root/"governance/specifications/REGISTRY.yaml")
    gov_uid=str((reg.get("governance_identity") or {}).get("governance_uid") or "")
    if not gov_uid:
        raise SystemExit("BLOCK:CURRENT_GOVERNANCE_UID_MISSING")
    plan=json.loads(subprocess.check_output(
        [sys.executable,"governance/ci/stage_execution_engine.py","--plan","--stage",args.stage],
        cwd=root,text=True
    ))
    op_total=len(plan.get("operations") or [])
    if op_total<=0:
        raise SystemExit("BLOCK:EMPTY_OPERATION_UNIVERSE")
    wus=[x.strip() for x in args.work_units.split(",") if x.strip()]
    if not wus:
        raise SystemExit("BLOCK:CURRENT_WORK_UNIT_SET_EMPTY")
    for wu in wus:
        wudir=root/"STAGE_EXECUTION"/args.stage/wu
        work_path=wudir/"WORK_UNIT.yaml"
        scope_path=wudir/"CURRENT_EXECUTION_SCOPE_MANIFEST.yaml"
        state_path=wudir/"EXECUTION_STATE.yaml"
        for p,label in ((work_path,"WORK_UNIT"),(scope_path,"CURRENT_SCOPE"),(state_path,"EXECUTION_STATE")):
            if not p.is_file() or p.stat().st_size<=0:
                raise SystemExit(f"BLOCK:CURRENT_{label}_MISSING:{wu}")
        run([
            sys.executable,".github/scripts/product_current_governance_load.py",
            "--product-root",str(root),"--governance-root",str(govroot),
            "--stage",args.stage,"--work-unit",str(work_path.relative_to(root))
        ],root)
        env=dict(os.environ)
        env.update({
            "STAGE_EXECUTION_ROOT":str(root),
            "STAGE_ACTIVE_WORK_UNIT":str(work_path.relative_to(root)),
            "STAGE_CURRENT_SCOPE":str(scope_path.relative_to(root)),
            "ACPOS_PRODUCT_ROOT":str(root),
            "ACPOS_ACTIVE_WORK_UNIT":str(work_path.relative_to(root)),
            "ACPOS_CURRENT_SCOPE":str(scope_path.relative_to(root)),
            "GOVERNANCE_SOURCE_ROOT":str(govroot),
        })
        code=(
            "from pathlib import Path; import os,yaml;"
            "from governance.ci.external_execution_admission import validate_external_stage_admission;"
            "root=Path(os.environ['STAGE_EXECUTION_ROOT']).resolve();"
            "wp=root/Path(os.environ['STAGE_ACTIVE_WORK_UNIT']);"
            "sp=root/Path(os.environ['STAGE_CURRENT_SCOPE']);"
            "work=yaml.safe_load(wp.read_text(encoding='utf-8')) or {};"
            "scope=yaml.safe_load(sp.read_text(encoding='utf-8')) or {};"
            f"validate_external_stage_admission(root,wp.parent,work,{args.stage!r},{gov_uid!r},scope);"
            "print('PASS: external admission',work.get('work_unit_uid'))"
        )
        run([sys.executable,"-c",code],root,env)
        run([sys.executable,"governance/ci/stage_execution_engine.py","--admission-check","--stage",args.stage],root,env)
        state=load(state_path)
        current=str(state.get("current_operation") or "")
        if current=="COMPLETE":
            print(f"PASS: {args.stage} already operation-complete for {wu}; no effectful invocation")
            continue
        run([sys.executable,"governance/ci/stage_execution_engine.py","--execute","--stage",args.stage],root,env)
        state=load(state_path)
        completed=list(map(str,state.get("completed_operations") or []))
        expected=list(map(str,plan.get("operations") or []))
        if completed!=expected[:len(completed)]:
            raise SystemExit(f"BLOCK:COMPLETED_OPERATION_PREFIX_DRIFT:{wu}")
        print(f"PASS: {args.stage} persisted one operation checkpoint for {wu}; next={state.get('current_operation')}")
    if args.stage=="STAGE-01":
        states=[load(root/"STAGE_EXECUTION"/args.stage/wu/"EXECUTION_STATE.yaml") for wu in wus]
        if all(str(s.get("current_operation") or "")=="COMPLETE" for s in states):
            run([sys.executable,".github/scripts/stage01_successor_materialize.py","--mode","refresh-manifest","--product-root",str(root)],root)
            print("PASS: Stage01 operation universe complete for all successor work units; run manifest refreshed")
if __name__=="__main__":
    main()
