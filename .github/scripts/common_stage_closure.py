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
    ap.add_argument("--validated-head")
    ap.add_argument("--validation-run-id")
    a=ap.parse_args()
    root=Path(a.product_root).resolve(); gov=Path(a.governance_root).resolve()
    run([sys.executable,".github/scripts/full_stage_lifecycle_guard.py","--mode","execution-ready","--stage",a.stage,"--product-root",str(root),"--governance-root",str(gov)],root)
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
        if rec.get("status") not in {"PASS","NOT_APPLICABLE_WITH_PROOF"} or str(rec.get("operation_uid") or "")!=op:
            raise SystemExit("BLOCK:COMMON_CLOSURE_OPERATION_RECEIPT_INVALID:"+op)
    print("PASS: common closure preflight operation receipt chain complete",a.stage,work.get("work_unit_uid"))
    if a.mode=="close":
        if not a.validated_head or not a.validation_run_id:
            raise SystemExit("BLOCK:CLOSURE_VALIDATION_ID_REQUIRED")
        run([sys.executable,".github/scripts/common_cross_stage_handoff_builder.py","--stage",a.stage,"--work-unit",a.work_unit,"--product-root",str(root),"--governance-root",str(gov)],root)
        run([sys.executable,".github/scripts/common_stage_closure_adapter.py","--mode","candidate","--stage",a.stage,"--work-unit",a.work_unit,"--validated-head",a.validated_head,"--validation-run-id",a.validation_run_id,"--product-root",str(root),"--governance-root",str(gov)],root)
        ev=f"STAGE_EXECUTION/{a.stage}/{wd.name}/EVIDENCE/NORMALIZED_STAGE_EVIDENCE.json"
        run([sys.executable,"governance/ci/stage_execution_engine.py","--validate-evidence","--stage",a.stage,"--evidence",ev],root)
        print("PASS: normalized content evidence validated")

if __name__=="__main__":
    main()
