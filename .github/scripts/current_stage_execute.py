#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path
import yaml

def load(path):
    obj=yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(obj,dict):
        raise SystemExit(f"BLOCK:MAPPING_REQUIRED:{path}")
    return obj

def run(cmd,cwd,env=None):
    timeout=int(os.environ.get("ACPOS_OPERATION_SUBPROCESS_TIMEOUT_SECONDS","900"))
    print("RUN:", " ".join(map(str,cmd)), flush=True)
    try:
        cp=subprocess.run(cmd,cwd=cwd,env=env,text=True,timeout=timeout)
    except subprocess.TimeoutExpired:
        raise SystemExit("BLOCK:SUBPROCESS_TIMEOUT:"+str(timeout)+":"+str(cmd[0]))
    if cp.returncode!=0:
        raise SystemExit(cp.returncode)

def reconcile_work_status_from_state(root, work_path, state_path):
    work=load(work_path)
    state=load(state_path)
    state_status=str(state.get("status") or "")
    if state_status not in {"READY_FOR_EXECUTION","IN_PROGRESS","EXECUTION_COMPLETE_CLOSURE_PENDING","CLOSED_PASS"}:
        raise SystemExit("BLOCK:UNSUPPORTED_EXECUTION_STATE_STATUS:"+state_status)
    work_status=str(work.get("current_status") or "")
    if work_status.startswith("CLOSED") and state_status!="CLOSED_PASS":
        raise SystemExit("BLOCK:CLOSED_WORK_UNIT_STATUS_REENTRY_CONFLICT:"+work_status+":"+state_status)
    if work_status!=state_status:
        work["current_status"]=state_status
        Path(work_path).write_text(yaml.safe_dump(work,allow_unicode=True,sort_keys=False,width=180),encoding="utf-8")
        print("PASS: reconciled Work Unit status from execution state",work.get("work_unit_uid"),work_status,"->",state_status,flush=True)

def rebind_run_manifest_hash(root, work_path):
    work=load(work_path)
    row=(work.get("current_ledger_bindings") or {}).get("RUN_MANIFEST")
    if not isinstance(row,dict):
        return
    ref=str(row.get("artifact_ref") or "")
    if not ref:
        raise SystemExit("BLOCK:RUN_MANIFEST_LEDGER_REF_MISSING:"+str(work.get("work_unit_uid") or ""))
    p=(root/Path(ref)).resolve()
    try:
        p.relative_to(root)
    except ValueError:
        raise SystemExit("BLOCK:RUN_MANIFEST_LEDGER_REF_ESCAPES_ROOT:"+ref)
    if not p.is_file() or p.stat().st_size<=0:
        raise SystemExit("BLOCK:RUN_MANIFEST_LEDGER_TARGET_MISSING:"+ref)
    row["content_sha256"]=hashlib.sha256(p.read_bytes()).hexdigest()
    work["current_ledger_bindings"]["RUN_MANIFEST"]=row
    Path(work_path).write_text(yaml.safe_dump(work,allow_unicode=True,sort_keys=False,width=180),encoding="utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage",required=True)
    ap.add_argument("--work-units",required=True)
    ap.add_argument("--product-root",required=True)
    ap.add_argument("--governance-root",required=True)
    ap.add_argument("--reconcile-only",action="store_true")
    args=ap.parse_args()
    root=Path(args.product_root).resolve()
    govroot=Path(args.governance_root).resolve()

    # Full lifecycle hard gate: no Stage, including STAGE-01, may execute while
    # the common 01-11 lifecycle skeleton still has unresolved execution-ready blockers.
    run([
        sys.executable,".github/scripts/full_stage_lifecycle_guard.py",
        "--mode","execution-ready",
        "--stage",args.stage,
        "--product-root",str(root),
        "--governance-root",str(govroot),
    ],root)
    run([
        sys.executable,".github/scripts/stage_lifecycle_gate.py",
        "--mode","assert-stage-authorized",
        "--stage",args.stage,
        "--product-root",str(root),
        "--governance-root",str(govroot),
    ],root)

    reg=load(root/"governance/specifications/REGISTRY.yaml")
    gov_uid=str((reg.get("governance_identity") or {}).get("governance_uid") or "")
    if not gov_uid:
        raise SystemExit("BLOCK:CURRENT_GOVERNANCE_UID_MISSING")

    plan=json.loads(subprocess.check_output(
        [sys.executable,"governance/ci/stage_execution_engine.py","--plan","--stage",args.stage],
        cwd=root,text=True,timeout=int(os.environ.get("ACPOS_OPERATION_SUBPROCESS_TIMEOUT_SECONDS","900"))
    ))
    op_total=len(plan.get("operations") or [])
    if op_total<=0:
        raise SystemExit("BLOCK:EMPTY_OPERATION_UNIVERSE")

    wus=[x.strip() for x in args.work_units.split(",") if x.strip()]
    if not wus:
        raise SystemExit("BLOCK:CURRENT_WORK_UNIT_SET_EMPTY")

    if args.reconcile_only:
        for wu in wus:
            wudir=root/"STAGE_EXECUTION"/args.stage/wu
            work_path=wudir/"WORK_UNIT.yaml"
            state_path=wudir/"EXECUTION_STATE.yaml"
            if not work_path.is_file() or not state_path.is_file():
                raise SystemExit("BLOCK:RECONCILE_TARGET_MISSING:"+wu)
            reconcile_work_status_from_state(root,work_path,state_path)
        return

    for wu in wus:
        wudir=root/"STAGE_EXECUTION"/args.stage/wu
        work_path=wudir/"WORK_UNIT.yaml"
        scope_path=wudir/"CURRENT_EXECUTION_SCOPE_MANIFEST.yaml"
        state_path=wudir/"EXECUTION_STATE.yaml"
        for p,label in ((work_path,"WORK_UNIT"),(scope_path,"CURRENT_SCOPE"),(state_path,"EXECUTION_STATE")):
            if not p.is_file() or p.stat().st_size<=0:
                raise SystemExit(f"BLOCK:CURRENT_{label}_MISSING:{wu}")

        run([
            sys.executable,".github/scripts/stage_lifecycle_gate.py",
            "--mode","assert-work-unit-entry",
            "--stage",args.stage,
            "--work-unit",str(work_path.relative_to(root)),
            "--product-root",str(root),
            "--governance-root",str(govroot),
        ],root)

        # Recovery reconcile for a previously persisted operation checkpoint. The
        # Mother engine owns state mutation and can rewrite WORK_UNIT from the
        # pre-executor snapshot; RUN_MANIFEST itself remains executor-owned, so
        # rebind its exact persisted SHA before Current admission.
        rebind_run_manifest_hash(root,work_path)

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
            "from pathlib import Path; import os,yaml,sys;"
            "sys.path.insert(0,'governance/ci');"
            "from external_execution_admission import validate_external_stage_admission;"
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
            reconcile_work_status_from_state(root,work_path,state_path)
            print(f"PASS: {args.stage} already operation-complete for {wu}; no effectful invocation")
            continue

        run([sys.executable,"governance/ci/stage_execution_engine.py","--execute","--stage",args.stage],root,env)
        # Reconcile after Mother engine state persistence so its stale in-memory
        # WORK_UNIT snapshot cannot erase the executor-refreshed RUN_MANIFEST hash.
        rebind_run_manifest_hash(root,work_path)
        reconcile_work_status_from_state(root,work_path,state_path)
        state=load(state_path)
        completed=list(map(str,state.get("completed_operations") or []))
        expected=list(map(str,plan.get("operations") or []))
        if completed!=expected[:len(completed)]:
            raise SystemExit(f"BLOCK:COMPLETED_OPERATION_PREFIX_DRIFT:{wu}")
        print(f"PASS: {args.stage} persisted one operation checkpoint for {wu}; next={state.get('current_operation')}")

    if args.stage=="STAGE-01":
        states=[load(root/"STAGE_EXECUTION"/args.stage/wu/"EXECUTION_STATE.yaml") for wu in wus]
        if all(str(s.get("current_operation") or "")=="COMPLETE" for s in states):
            run([
                sys.executable,".github/scripts/stage01_current_materialize.py",
                "--mode","refresh-manifest",
                "--product-root",str(root),
            ],root)
            print("PASS: Stage01 operation universe complete for all Current clean Work Units; run manifest refreshed")

if __name__=="__main__":
    main()
