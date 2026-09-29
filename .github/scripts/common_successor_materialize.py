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

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--from-stage",required=True)
    ap.add_argument("--predecessor-work-unit",required=True)
    ap.add_argument("--product-root",required=True)
    ap.add_argument("--governance-root",required=True)
    ap.add_argument("--mode",choices=["plan","materialize"],default="plan")
    ap.add_argument("--operation-binding-manifest")
    a=ap.parse_args()
    root=Path(a.product_root).resolve(); gov=Path(a.governance_root).resolve()
    lifecycle=y(gov/".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml")
    stages={str(x.get("stage_uid")):x for x in lifecycle.get("stages") or []}
    if a.from_stage not in stages: raise SystemExit("BLOCK:UNREGISTERED_PREDECESSOR_STAGE")
    to=str(stages[a.from_stage].get("next_stage_uid") or "")
    wp=(root/Path(a.predecessor_work_unit)).resolve(); work=y(wp)
    if str(work.get("stage_uid") or "")!=a.from_stage: raise SystemExit("BLOCK:PREDECESSOR_WORK_UNIT_STAGE_DRIFT")
    receipt=wp.parent/"WORK_UNIT_TERMINAL_RECEIPT.yaml"
    if not receipt.is_file(): raise SystemExit("BLOCK:PREDECESSOR_TERMINAL_RECEIPT_MISSING")
    evref=str(y(receipt).get("evidence_ref") or "")
    if not evref: raise SystemExit("BLOCK:PREDECESSOR_TERMINAL_EVIDENCE_REF_MISSING")
    env=dict()
    subprocess.check_call([sys.executable,".github/scripts/stage_lifecycle_gate.py","--mode","assert-transition","--from-stage",a.from_stage,"--to-stage",to,"--product-root",str(root),"--governance-root",str(gov)],cwd=root)
    handoff=wp.parent/"EVIDENCE"/"CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml"
    h=y(handoff)
    if h.get("status")!="PASS" or str(h.get("successor_stage_uid") or "")!=to:
        raise SystemExit("BLOCK:PREDECESSOR_HANDOFF_NOT_PASS")
    print("PASS: successor transition plan validated",a.from_stage,"->",to)
    if a.mode=="materialize":
        registry=y(root/"STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/FULL_STAGE_RUNTIME_ADAPTER_REGISTRY.yaml")
        row=next((x for x in registry.get("adapters") or [] if x.get("stage_uid")==to),None)
        owner=str((row or {}).get("materializer_owner") or "")
        if not owner:
            raise SystemExit("BLOCK:SUCCESSOR_STAGE_MATERIALIZER_OWNER_UNRESOLVED:"+to)
        p=(root/Path(owner)).resolve()
        if not p.is_file(): raise SystemExit("BLOCK:SUCCESSOR_STAGE_MATERIALIZER_OWNER_MISSING:"+owner)
        if p.name=="common_successor_materialize.py": raise SystemExit("BLOCK:SUCCESSOR_MATERIALIZER_RECURSIVE_OWNER")
        binding_manifest=a.operation_binding_manifest
        subprocess.check_call([
            sys.executable,str(p),"--mode","materialize",
            "--successor-stage",to,
            "--predecessor-work-unit",a.predecessor_work_unit,
            "--operation-binding-manifest",binding_manifest,
            "--product-root",str(root),
            "--governance-root",str(gov)
        ],cwd=root)

if __name__=="__main__":
    main()
