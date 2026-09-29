#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
import yaml

def y(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d

def run(cmd,cwd):
    cp=subprocess.run(cmd,cwd=cwd,text=True)
    if cp.returncode!=0: raise SystemExit(cp.returncode)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage",required=True)
    ap.add_argument("--work-unit",required=True)
    ap.add_argument("--product-root",required=True)
    ap.add_argument("--governance-root",required=True)
    ap.add_argument("--mode",choices=["preflight","close"],default="preflight")
    a=ap.parse_args()
    root=Path(a.product_root).resolve(); gov=Path(a.governance_root).resolve()
    run([sys.executable,".github/scripts/full_stage_lifecycle_guard.py","--mode","execution-ready","--product-root",str(root),"--governance-root",str(gov)],root)
    run([sys.executable,".github/scripts/stage_lifecycle_gate.py","--mode","assert-work-unit-entry","--stage",a.stage,"--work-unit",a.work_unit,"--product-root",str(root),"--governance-root",str(gov)],root)
    wp=(root/Path(a.work_unit)).resolve(); wd=wp.parent
    work=y(wp); state=y(wd/"EXECUTION_STATE.yaml")
    plan=json.loads(subprocess.check_output([sys.executable,"governance/ci/stage_execution_engine.py","--plan","--stage",a.stage],cwd=root,text=True))
    expected=list(map(str,plan.get("operations") or []))
    completed=list(map(str,state.get("completed_operations") or []))
    if completed!=expected or str(state.get("current_operation") or "")!="COMPLETE":
        raise SystemExit("BLOCK:COMMON_CLOSURE_OPERATIONS_NOT_COMPLETE:"+a.stage)
    bindings=work.get("operation_bindings") or {}
    for op in expected:
        b=bindings.get(op) or {}
        ref=str(b.get("operation_receipt_ref") or "")
        if not ref: raise SystemExit("BLOCK:COMMON_CLOSURE_OPERATION_RECEIPT_REF_MISSING:"+op)
        rp=(root/Path(ref)).resolve()
        try: rp.relative_to(root)
        except ValueError: raise SystemExit("BLOCK:COMMON_CLOSURE_OPERATION_RECEIPT_REF_ESCAPES_ROOT:"+op)
        rec=y(rp)
        if rec.get("status")!="PASS" or str(rec.get("operation_uid") or "")!=op:
            raise SystemExit("BLOCK:COMMON_CLOSURE_OPERATION_RECEIPT_INVALID:"+op)
    print("PASS: common closure preflight operation receipt chain complete",a.stage,work.get("work_unit_uid"))
    if a.mode=="close":
        registry=y(root/"STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/FULL_STAGE_RUNTIME_ADAPTER_REGISTRY.yaml")
        row=next((x for x in registry.get("adapters") or [] if x.get("stage_uid")==a.stage),None)
        adapter=str((row or {}).get("closure_adapter_owner") or "")
        if not adapter:
            raise SystemExit("BLOCK:COMMON_CLOSURE_ADAPTER_UNRESOLVED:"+a.stage)
        apath=(root/Path(adapter)).resolve()
        try: apath.relative_to(root)
        except ValueError: raise SystemExit("BLOCK:COMMON_CLOSURE_ADAPTER_ESCAPES_ROOT")
        if not apath.is_file(): raise SystemExit("BLOCK:COMMON_CLOSURE_ADAPTER_MISSING:"+adapter)
        if apath.name=="common_stage_closure.py": raise SystemExit("BLOCK:COMMON_CLOSURE_RECURSIVE_ADAPTER")
        run([sys.executable,str(apath),"--mode","candidate","--stage",a.stage,"--work-unit",a.work_unit,"--product-root",str(root),"--governance-root",str(gov)],root)
        print("PASS: common closure candidate prepared; terminal receipt requires prior terminal-success validation run")

if __name__=="__main__":
    main()
