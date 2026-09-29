#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path
import yaml

LIFECYCLE=Path(".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml")

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d

def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(o,sort_keys=False,allow_unicode=True),encoding="utf-8")

def git(root,*args):
    cp=subprocess.run(["git","-C",str(root),*args],text=True,capture_output=True)
    if cp.returncode!=0: raise SystemExit("BLOCK:GIT:"+cp.stderr.strip())
    return cp.stdout.strip()

def validate_contract(gov):
    reg=load(gov/LIFECYCLE)
    stages=reg.get("stages") or []
    expected=[f"STAGE-{i:02d}" for i in range(1,12)]
    order=[str(x.get("stage_uid") or "") for x in stages if isinstance(x,dict)]
    if order!=expected: raise SystemExit("BLOCK:TERMINALIZER_LIFECYCLE_ORDER_DRIFT")
    for row in stages:
        if not row.get("exit_gate") or not row.get("next_stage_uid"):
            raise SystemExit("BLOCK:TERMINALIZER_STAGE_TRANSITION_MISSING:"+str(row.get("stage_uid")))
    print("PASS: common terminalizer contract covers Stage-01..11")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=["validate-contract","terminalize"],default="validate-contract")
    ap.add_argument("--stage")
    ap.add_argument("--work-unit")
    ap.add_argument("--validated-head")
    ap.add_argument("--validation-run-id")
    ap.add_argument("--product-root",required=True)
    ap.add_argument("--governance-root",required=True)
    a=ap.parse_args()
    root=Path(a.product_root).resolve(); gov=Path(a.governance_root).resolve()
    validate_contract(gov)
    if a.mode=="validate-contract": return
    if not all([a.stage,a.work_unit,a.validated_head,a.validation_run_id]):
        raise SystemExit("BLOCK:TERMINALIZER_REQUIRED_ARGUMENT_MISSING")
    if git(root,"rev-parse","HEAD")!=a.validated_head:
        raise SystemExit("BLOCK:TERMINALIZER_HEAD_NOT_EXACT_VALIDATED_CANDIDATE")
    reg=load(gov/LIFECYCLE)
    stages={str(x.get("stage_uid")):x for x in reg.get("stages") or [] if isinstance(x,dict)}
    if a.stage not in stages: raise SystemExit("BLOCK:TERMINALIZER_STAGE_UNREGISTERED")
    wp=(root/Path(a.work_unit)).resolve()
    try: wp.relative_to(root)
    except ValueError: raise SystemExit("BLOCK:TERMINALIZER_WORK_UNIT_ESCAPES_ROOT")
    work=load(wp); wd=wp.parent
    if str(work.get("stage_uid") or "")!=a.stage: raise SystemExit("BLOCK:TERMINALIZER_WORK_UNIT_STAGE_DRIFT")
    candidate=wd/"EVIDENCE/COMMON_NORMALIZED_STAGE_EVIDENCE_CANDIDATE.json"
    if not candidate.is_file(): raise SystemExit("BLOCK:TERMINALIZER_NORMALIZED_CANDIDATE_MISSING")
    ev=json.loads(candidate.read_text(encoding="utf-8"))
    if ev.get("status")!="CANDIDATE_NOT_TERMINAL": raise SystemExit("BLOCK:TERMINALIZER_CANDIDATE_STATUS_INVALID")
    handoff_path=wd/"EVIDENCE/CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml"
    handoff=load(handoff_path)
    stage=stages[a.stage]; next_stage=str(stage.get("next_stage_uid") or "")
    if str(handoff.get("successor_stage_uid") or "")!=next_stage: raise SystemExit("BLOCK:TERMINALIZER_SUCCESSOR_DRIFT")
    auth=load(root/"STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/FULL_STAGE_LIFECYCLE_AUTHORIZATION_CONTRACT.yaml")
    allowed=list(map(str,(auth.get("execution_authorization") or {}).get("authorized_effectful_range") or []))
    if next_stage.startswith("STAGE-") and next_stage in allowed:
        if not handoff.get("successor_input_bindings"): raise SystemExit("BLOCK:TERMINALIZER_SUCCESSOR_INPUT_BINDINGS_MISSING")
        handoff["status"]="PASS"
    elif next_stage.startswith("STAGE-"):
        handoff["status"]="ELIGIBLE_PENDING_EXPLICIT_RANGE_AUTHORIZATION"
    else:
        handoff["status"]="PASS_TERMINAL_LIFECYCLE"
    handoff["terminalized_from_validated_head"]=a.validated_head
    handoff["validation_run_id"]=str(a.validation_run_id)
    write(handoff_path,handoff)
    receipt={
      "artifact_type":"WORK_UNIT_TERMINAL_RECEIPT",
      "stage_uid":a.stage,
      "work_unit_uid":work.get("work_unit_uid"),
      "governed_unit_uid":work.get("governed_unit_uid"),
      "governance_uid":work.get("governance_uid"),
      "validated_candidate_head_sha":a.validated_head,
      "validation_run_id":str(a.validation_run_id),
      "evidence_ref":str(candidate.relative_to(root)),
      "cross_stage_handoff_ref":str(handoff_path.relative_to(root)),
      "exit_gate":stage.get("exit_gate"),
      "status":"CLOSED_PASS",
      "completion_credit":1,
    }
    write(wd/"WORK_UNIT_TERMINAL_RECEIPT.yaml",receipt)
    state=load(wd/"EXECUTION_STATE.yaml")
    state["status"]="CLOSED_PASS"; state["current_operation"]="COMPLETE"; state["stage_exit_authorized"]=True
    state["next_stage_uid"]=next_stage; state["terminal_receipt_ref"]=str((wd/"WORK_UNIT_TERMINAL_RECEIPT.yaml").relative_to(root))
    write(wd/"EXECUTION_STATE.yaml",state)
    work["current_status"]="CLOSED_PASS"; work["terminal_receipt_ref"]=state["terminal_receipt_ref"]
    write(wp,work)
    resume={
      "artifact_type":"CURRENT_STAGE_RESUME",
      "stage_uid":a.stage,
      "work_unit_uid":work.get("work_unit_uid"),
      "governed_unit_uid":work.get("governed_unit_uid"),
      "terminal_status":"CLOSED_PASS",
      "next_stage_uid":next_stage,
      "next_action":"MATERIALIZE_REGISTERED_SUCCESSOR_IF_INSIDE_AUTHORIZED_RANGE" if next_stage in allowed else "PERSIST_ELIGIBILITY_AND_STOP_AT_AUTHORIZED_RANGE_BOUNDARY",
      "source_validated_head_sha":a.validated_head,
      "validation_run_id":str(a.validation_run_id),
      "status":"CURRENT",
    }
    write(wd/"CURRENT_STAGE_RESUME.yaml",resume)
    print("PASS: terminal receipt and resume materialized from prior terminal-success validation",a.stage,work.get("work_unit_uid"))

if __name__=="__main__":
    main()
