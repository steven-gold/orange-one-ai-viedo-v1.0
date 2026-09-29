#!/usr/bin/env python3
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from pathlib import Path
import yaml
def load(p):
    d=yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d
def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(yaml.safe_dump(o,sort_keys=False,allow_unicode=True),encoding="utf-8")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--work-unit",required=True); ap.add_argument("--action",choices=["APPROVE","REJECT","REQUEST_CHANGES"],required=True); ap.add_argument("--reviewer",required=True); ap.add_argument("--product-root",required=True)
    a=ap.parse_args(); root=Path(a.product_root).resolve(); wd=root/"STAGE_EXECUTION/STAGE-03"/a.work_unit
    state=load(wd/"EXECUTION_STATE.yaml")
    if state.get("current_operation")!="COMPLETE": raise SystemExit("BLOCK:VISUAL_REVIEW_BEFORE_OPERATION_COMPLETE")
    p=wd/"EVIDENCE/VISUAL_REVIEW_EVIDENCE.yaml"; d=load(p); now=datetime.now(timezone.utc).isoformat()
    if a.action=="APPROVE":
        d.update({"decision":"VISUAL_APPROVED","visual_approved":True,"reviewer":a.reviewer,"reviewed_at":now,"stage_exit_credit":0,"status":"REVIEW_COMPLETE_PENDING_STAGE03_CLOSURE"})
        write(wd/"EVIDENCE/FORMAL_HUMAN_APPROVAL_DISPOSITION.yaml",{"artifact_type":"FORMAL_HUMAN_APPROVAL_DISPOSITION","stage_uid":"STAGE-03","work_unit_uid":a.work_unit,"human_action_required":False,"human_action_selected":"APPROVE","reviewer":a.reviewer,"reviewed_at":now,"source_decision":"VISUAL_APPROVED","status":"CURRENT_APPROVED_HUMAN_DISPOSITION"})
        pr=load(wd/"CURRENT_PROBLEM_REGISTER.yaml")
        for g in pr.get("non_problem_closure_gates") or []:
            if g.get("gate_uid")=="HUMAN_VISUAL_REVIEW": g["status"]="VISUAL_APPROVED"; g["stage_exit_credit"]=0
        pr["closure_blocker_total"]=int(pr.get("open_problem_total") or 0); write(wd/"CURRENT_PROBLEM_REGISTER.yaml",pr)
    else:
        d.update({"decision":"VISUAL_REJECTED" if a.action=="REJECT" else "REQUEST_CHANGES","visual_approved":False,"reviewer":a.reviewer,"reviewed_at":now,"stage_exit_credit":0,"status":"REVERIFY_REQUIRED"})
    write(p,d); print("PASS: governed Stage03 human review recorded",a.work_unit,a.action)
if __name__=="__main__": main()
