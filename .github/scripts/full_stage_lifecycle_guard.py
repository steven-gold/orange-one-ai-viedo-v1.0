#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import yaml

EXPECTED=[f"STAGE-{i:02d}" for i in range(1,12)]
FLOW=Path("STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW")
LIFECYCLE=Path(".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml")

def load(p):
    if not p.is_file() or p.stat().st_size<=0:
        raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict):
        raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d

def fail(x):
    raise SystemExit("BLOCK:"+x)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--product-root",required=True)
    ap.add_argument("--governance-root",required=True)
    ap.add_argument("--mode",choices=["plan","execution-ready"],default="plan")
    a=ap.parse_args()
    product=Path(a.product_root).resolve()
    gov=Path(a.governance_root).resolve()
    c=load(product/FLOW/"FULL_STAGE_LIFECYCLE_AUTHORIZATION_CONTRACT.yaml")
    r=load(product/FLOW/"CURRENT_EXECUTION_RESOLUTION.yaml")
    m=load(product/FLOW/"CURRENT_REMEDIATION_STATE.yaml")
    d=load(product/FLOW/"FULL_STAGE_DEFECT_LEDGER.yaml")
    lr=load(gov/LIFECYCLE)
    stages=lr.get("stages") or []
    order=[str(x.get("stage_uid") or "") for x in stages if isinstance(x,dict)]
    if order!=EXPECTED: fail("LIFECYCLE_REGISTRY_ORDER_DRIFT")
    if list(map(str,c.get("lifecycle_stage_uids") or []))!=EXPECTED: fail("CONTRACT_RANGE_NOT_01_11")
    rows=c.get("stage_contracts") or []
    if [str(x.get("stage_uid") or "") for x in rows]!=EXPECTED: fail("STAGE_ROWS_DRIFT")
    rm={str(x["stage_uid"]):x for x in stages}
    for x in rows:
        uid=str(x["stage_uid"])
        for k in ("name","entry_gate","exit_gate","next_stage_uid"):
            if str(x.get(k) or "")!=str(rm[uid].get(k) or ""): fail("STAGE_"+k.upper()+"_DRIFT:"+uid)
    auth=c.get("execution_authorization") or {}
    planning=list(map(str,auth.get("planning_range") or []))
    allowed=list(map(str,auth.get("authorized_effectful_range") or []))
    if planning!=EXPECTED: fail("PLANNING_RANGE_NOT_FULL")
    if not allowed: fail("AUTHORIZED_RANGE_EMPTY")
    pos=[EXPECTED.index(x) for x in allowed]
    if pos!=list(range(min(pos),max(pos)+1)): fail("AUTHORIZED_RANGE_NOT_CONTIGUOUS")
    if auth.get("system_may_expand_range") is not False or auth.get("system_may_shrink_range") is not False: fail("RANGE_AUTHORITY_NOT_FAIL_CLOSED")
    topo=c.get("lifecycle_topology") or {}
    if topo.get("true_governed_unit_closure_stage")!="STAGE-11": fail("TRUE_CLOSURE_STAGE_DRIFT")
    if topo.get("stage04_is_full_lifecycle_closure") is not False: fail("STAGE04_FALSE_CLOSURE")
    if topo.get("stage_local_authorization_logic")!="FORBIDDEN" or topo.get("stage_local_permission_model")!="FORBIDDEN": fail("STAGE_LOCAL_AUTHORITY_NOT_FORBIDDEN")
    pc=c.get("permission_continuity_contract") or {}
    expected={"semantic_owner_stage":"STAGE-02","visual_projection_stage":"STAGE-03","immutable_freeze_stage":"STAGE-04","implementation_stage":"STAGE-05","verification_stage":"STAGE-06","production_acceptance_stage":"STAGE-10","final_reconciliation_stage":"STAGE-11"}
    for k,v in expected.items():
        if pc.get(k)!=v: fail("PERMISSION_CONTINUITY_"+k.upper()+"_DRIFT")
    if pc.get("downstream_may_redefine_permission_semantics") is not False: fail("DOWNSTREAM_PERMISSION_REDEFINITION_NOT_FORBIDDEN")
    if list(map(str,r.get("planned_lifecycle_range") or []))!=EXPECTED: fail("RESOLUTION_TRUNCATES_LIFECYCLE")
    if list(map(str,r.get("authorized_effectful_range") or []))!=allowed: fail("RESOLUTION_AUTHORIZED_RANGE_DRIFT")
    for unit in r.get("stage_sequence") or []:
        sr=unit.get("stages") or []
        if [str(x.get("stage_uid") or "") for x in sr]!=EXPECTED: fail("UNIT_STAGE_SEQUENCE_NOT_01_11:"+str(unit.get("governed_unit_uid")))
        for row in sr:
            if str(row.get("stage_uid")) not in allowed and row.get("effectful_execution_admitted") is not False: fail("FUTURE_STAGE_PREAUTHORIZED:"+str(row.get("stage_uid")))
    if list(map(str,m.get("planned_lifecycle_range") or []))!=EXPECTED: fail("REMEDIATION_TRUNCATES_LIFECYCLE")
    if list(map(str,m.get("authorized_effectful_stage_range") or []))!=allowed: fail("REMEDIATION_AUTH_RANGE_DRIFT")
    cb={str(x.get("uid") or "") for x in c.get("known_runtime_blockers") or [] if isinstance(x,dict) and x.get("status")=="OPEN"}
    db={str(x.get("uid") or "") for x in d.get("defects") or [] if isinstance(x,dict) and x.get("state") in {"OPEN","REVERIFY_REQUIRED"}}
    if cb!=db: fail("BLOCKER_LEDGER_DRIFT")
    if a.mode=="execution-ready" and cb: fail("FULL_STAGE_RUNTIME_NOT_READY:"+",".join(sorted(cb)))
    print("PASS: full lifecycle 01-11 uses one authorization contract")
    print("PASS: one permission continuity chain spans Stage-02 through Stage-11")
    print("PASS: future stages are planned but cannot be pre-executed outside the authorized range")
    print("INFO: runtime blockers="+str(len(cb))+"; planning validation grants zero Stage completion credit")

if __name__=="__main__":
    main()
