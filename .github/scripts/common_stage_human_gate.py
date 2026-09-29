#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import yaml

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage",required=True); ap.add_argument("--work-units",required=True); ap.add_argument("--product-root",required=True)
    a=ap.parse_args()
    if a.stage!="STAGE-03":
        print("PASS: no governed human stop at this stage"); return
    root=Path(a.product_root).resolve()
    pending=[]; rejected=[]
    for wu in [x.strip() for x in a.work_units.split(",") if x.strip()]:
        wd=root/"STAGE_EXECUTION"/a.stage/wu
        state=load(wd/"EXECUTION_STATE.yaml")
        if str(state.get("current_operation") or "")!="COMPLETE":
            raise SystemExit("BLOCK:HUMAN_GATE_BEFORE_OPERATION_COMPLETE:"+wu)
        p=wd/"EVIDENCE/VISUAL_REVIEW_EVIDENCE.yaml"
        if not p.is_file():
            pending.append(wu); continue
        d=load(p); decision=str(d.get("decision") or "")
        if decision=="VISUAL_APPROVED":
            continue
        if decision=="PENDING_HUMAN_REVIEW":
            pending.append(wu)
        elif decision in {"VISUAL_REJECTED","REQUEST_CHANGES"}:
            rejected.append(wu)
        else:
            raise SystemExit("BLOCK:HUMAN_REVIEW_DECISION_INVALID:"+wu+":"+decision)
    if rejected:
        raise SystemExit("BLOCK:HUMAN_REVIEW_REMEDIATION_REQUIRED:"+",".join(rejected))
    if pending:
        print("PAUSE:FORMAL_HUMAN_APPROVAL_REQUIRED:"+",".join(pending))
        raise SystemExit(75)
    print("PASS: all Stage03 governed human visual approvals are present")

if __name__=="__main__": main()
