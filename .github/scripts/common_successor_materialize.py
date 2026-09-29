#!/usr/bin/env python3
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
import yaml

LIFE=Path(".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml")

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0:
        raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict):
        raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
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
    lifecycle=load(gov/LIFE)
    stages={str(x.get("stage_uid")):x for x in lifecycle.get("stages") or [] if isinstance(x,dict)}
    if a.from_stage not in stages:
        raise SystemExit("BLOCK:UNREGISTERED_PREDECESSOR_STAGE")
    successor=str(stages[a.from_stage].get("next_stage_uid") or "")
    wp=(root/Path(a.predecessor_work_unit)).resolve()
    try:
        wp.relative_to(root)
    except ValueError:
        raise SystemExit("BLOCK:PREDECESSOR_WORK_UNIT_ESCAPES_PRODUCT_ROOT")
    work=load(wp)
    if str(work.get("stage_uid") or "")!=a.from_stage:
        raise SystemExit("BLOCK:PREDECESSOR_WORK_UNIT_STAGE_DRIFT")

    if successor=="NEXT_GOVERNED_UNIT_STAGE05_OR_SCOPE_COMPLETE":
        resolution=load(wp.parent/"EVIDENCE/SUCCESSOR_EXECUTION_BINDING_RESOLUTION.yaml")
        if resolution.get("status")!="PASS" or str(resolution.get("successor_stage_uid") or "")!=successor:
            raise SystemExit("BLOCK:TERMINAL_SCOPE_TRANSITION_RESOLUTION_NOT_PASS")
        print("PASS: Stage11 terminal transition resolved; no synthetic Stage successor")
        return

    receipt=wp.parent/"WORK_UNIT_TERMINAL_RECEIPT.yaml"
    if not receipt.is_file():
        raise SystemExit("BLOCK:PREDECESSOR_TERMINAL_RECEIPT_MISSING")
    terminal=load(receipt)
    if terminal.get("status")!="CLOSED_PASS" or terminal.get("conclusion")!="success":
        raise SystemExit("BLOCK:PREDECESSOR_TERMINAL_RECEIPT_NOT_PASS")

    subprocess.check_call([
        sys.executable,".github/scripts/stage_lifecycle_gate.py",
        "--mode","assert-transition",
        "--from-stage",a.from_stage,
        "--to-stage",successor,
        "--product-root",str(root),
        "--governance-root",str(gov)
    ],cwd=root)

    handoff=load(wp.parent/"EVIDENCE/CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml")
    if handoff.get("status")!="PASS" or str(handoff.get("successor_stage_uid") or "")!=successor:
        raise SystemExit("BLOCK:PREDECESSOR_HANDOFF_NOT_PASS")
    print("PASS: successor transition plan validated",a.from_stage,"->",successor)

    if a.mode=="materialize":
        if not a.operation_binding_manifest:
            raise SystemExit("BLOCK:SUCCESSOR_OPERATION_BINDING_MANIFEST_REQUIRED")
        builder=root/".github/scripts/common_successor_work_unit_builder.py"
        if not builder.is_file():
            raise SystemExit("BLOCK:COMMON_SUCCESSOR_WORK_UNIT_BUILDER_MISSING")
        subprocess.check_call([
            sys.executable,str(builder),
            "--mode","materialize",
            "--successor-stage",successor,
            "--predecessor-work-unit",a.predecessor_work_unit,
            "--operation-binding-manifest",a.operation_binding_manifest,
            "--product-root",str(root),
            "--governance-root",str(gov)
        ],cwd=root)

if __name__=="__main__":
    main()
