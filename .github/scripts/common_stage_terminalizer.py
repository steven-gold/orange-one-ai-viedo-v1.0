#!/usr/bin/env python3
from __future__ import annotations
import argparse, subprocess, sys
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

def repo_identity(root):
    raw=git(root,"config","--get","remote.origin.url").strip()
    if raw.endswith(".git"): raw=raw[:-4]
    if raw.startswith("git@github.com:"): raw=raw.split(":",1)[1]
    elif "github.com/" in raw: raw=raw.split("github.com/",1)[1]
    return raw or "UNKNOWN_REPOSITORY"

def validate_contract(gov):
    reg=load(gov/LIFECYCLE)
    order=[str(x.get("stage_uid") or "") for x in reg.get("stages") or [] if isinstance(x,dict)]
    expected=[f"STAGE-{i:02d}" for i in range(1,12)]
    if order!=expected: raise SystemExit("BLOCK:TERMINALIZER_LIFECYCLE_ORDER_DRIFT")
    print("PASS: common terminalizer contract covers Stage-01..11")

def run(cmd,cwd,env=None):
    cp=subprocess.run(cmd,cwd=cwd,env=env,text=True)
    if cp.returncode!=0: raise SystemExit(cp.returncode)

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
    stage=stages[a.stage]; next_stage=str(stage.get("next_stage_uid") or "")
    gate_rel=f"STAGE_EXECUTION/{a.stage}/{wd.name}/EVIDENCE/EXACT_HEAD_GATE_RECEIPTS.yaml"
    write(root/gate_rel,{"artifact_type":"EXACT_HEAD_GATE_RECEIPTS","stage_uid":a.stage,"work_unit_uid":work.get("work_unit_uid"),"receipts":[{"gate_uid":"PRETERMINAL_EXACT_HEAD_VALIDATION","head_sha":a.validated_head,"run_id":str(a.validation_run_id),"conclusion":"success"}],"status":"PASS"})
    run([sys.executable,".github/scripts/common_stage_closure.py","--mode","close","--stage",a.stage,"--work-unit",a.work_unit,"--product-root",str(root),"--governance-root",str(gov)],root)
    ev_rel=f"STAGE_EXECUTION/{a.stage}/{wd.name}/EVIDENCE/NORMALIZED_STAGE_EVIDENCE.json"
    ev_path=root/ev_rel
    if not ev_path.is_file(): raise SystemExit("BLOCK:TERMINALIZER_NORMALIZED_EVIDENCE_MISSING")
    handoff_path=wd/"EVIDENCE/CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml"
    handoff=load(handoff_path)
    if str(handoff.get("successor_stage_uid") or "")!=next_stage or handoff.get("status")!="PASS":
        raise SystemExit("BLOCK:TERMINALIZER_HANDOFF_NOT_PASS")

    receipt_rel=f"STAGE_EXECUTION/{a.stage}/{wd.name}/WORK_UNIT_TERMINAL_RECEIPT.yaml"
    receipt={
      "artifact_type":"WORK_UNIT_TERMINAL_RECEIPT",
      "provider":"github-actions",
      "repository_or_project":repo_identity(root),
      "head_sha":a.validated_head,
      "run_id":str(a.validation_run_id),
      "job_denominator":["normalized-evidence-validation","terminal-closure-validation"],
      "conclusion":"success",
      "governance_uid":work.get("governance_uid"),
      "stage_uid":a.stage,
      "evidence_ref":ev_rel,
      "work_unit_uid":work.get("work_unit_uid"),
      "governed_unit_uid":work.get("governed_unit_uid"),
      "exit_gate":stage.get("exit_gate"),
      "next_stage_uid":next_stage,
      "status":"CLOSED_PASS",
      "completion_credit":1,
    }
    write(root/receipt_rel,receipt)

    env=dict(**__import__("os").environ)
    env["STAGE_EXECUTION_ROOT"]=str(root)
    engine=root/"governance/ci/stage_execution_engine.py"
    if not engine.is_file():
        raise SystemExit("BLOCK:TERMINALIZER_CURRENT_GOVERNANCE_RUNTIME_NOT_LOADED")
    run([sys.executable,str(engine),"--validate-terminal-receipt","--stage",a.stage,"--evidence",ev_rel,"--receipt",receipt_rel],root,env)

    state=load(wd/"EXECUTION_STATE.yaml")
    state["status"]="CLOSED_PASS"; state["current_operation"]="COMPLETE"; state["stage_exit_authorized"]=True
    state["next_stage_uid"]=next_stage; state["terminal_receipt_ref"]=receipt_rel
    write(wd/"EXECUTION_STATE.yaml",state)
    work["current_status"]="CLOSED_PASS"; work["terminal_receipt_ref"]=receipt_rel
    write(wp,work)

    auth=load(root/"STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/FULL_STAGE_LIFECYCLE_AUTHORIZATION_CONTRACT.yaml")
    allowed=list(map(str,(auth.get("execution_authorization") or {}).get("authorized_effectful_range") or []))
    resume={
      "artifact_type":"CURRENT_STAGE_RESUME",
      "stage_uid":a.stage,
      "work_unit_uid":work.get("work_unit_uid"),
      "governed_unit_uid":work.get("governed_unit_uid"),
      "terminal_status":"CLOSED_PASS",
      "next_stage_uid":next_stage,
      "next_action":"MATERIALIZE_REGISTERED_SUCCESSOR_IF_EXACT_BINDINGS_READY" if next_stage in allowed else "PERSIST_ELIGIBILITY_AND_STOP_AT_AUTHORIZED_RANGE_BOUNDARY",
      "source_validated_head_sha":a.validated_head,
      "validation_run_id":str(a.validation_run_id),
      "status":"CURRENT",
    }
    write(wd/"CURRENT_STAGE_RESUME.yaml",resume)
    print("PASS: Mother-engine terminal receipt validated and closure projection materialized",a.stage,work.get("work_unit_uid"))

if __name__=="__main__":
    main()
