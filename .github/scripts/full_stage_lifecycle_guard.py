#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import yaml

EXPECTED=[f"STAGE-{i:02d}" for i in range(1,12)]
FLOW=Path("STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW")
LIFECYCLE=Path(".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml")
SELECTION=Path("STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_GOVERNANCE_SELECTION.yaml")
AUTH=FLOW/"FULL_STAGE_LIFECYCLE_AUTHORIZATION_CONTRACT.yaml"

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0:
        raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict):
        raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d

def fail(msg):
    raise SystemExit("BLOCK:"+msg)

def local_file(root,value,label):
    value=str(value or "").strip()
    if not value:
        fail(label+"_MISSING")
    p=(root/Path(value)).resolve()
    try:
        p.relative_to(root)
    except ValueError:
        fail(label+"_ESCAPES_PRODUCT_ROOT:"+value)
    if not p.is_file():
        fail(label+"_NOT_FOUND:"+value)
    return p

def stage_map(gov):
    life=load(gov/LIFECYCLE)
    rows=[x for x in life.get("stages") or [] if isinstance(x,dict)]
    order=[str(x.get("stage_uid") or "") for x in rows]
    if order!=EXPECTED:
        fail("LIFECYCLE_REGISTRY_ORDER_DRIFT")
    return life,{str(x["stage_uid"]):x for x in rows}

def validate_contract(product,gov):
    selection=load(product/SELECTION)
    auth=load(product/AUTH)
    life,stages=stage_map(gov)

    if selection.get("status")!="SELECTED_EXACT_CURRENT_SNAPSHOT":
        fail("CURRENT_GOVERNANCE_SELECTION_NOT_EXACT")
    gov_uid=str(selection.get("governance_uid") or "")
    gov_head=str(selection.get("governance_commit_sha") or "")
    current=auth.get("current_governance") or {}
    if str(current.get("governance_uid") or "")!=gov_uid:
        fail("AUTHORIZATION_GOVERNANCE_UID_DRIFT")
    if str(current.get("governance_head") or "")!=gov_head:
        fail("AUTHORIZATION_GOVERNANCE_HEAD_DRIFT")

    if list(map(str,auth.get("lifecycle_stage_uids") or []))!=EXPECTED:
        fail("AUTHORIZATION_LIFECYCLE_RANGE_DRIFT")
    execution=auth.get("execution_authorization") or {}
    planning=list(map(str,execution.get("planning_range") or []))
    allowed=list(map(str,execution.get("authorized_effectful_range") or []))
    if planning!=EXPECTED:
        fail("PLANNING_RANGE_NOT_STAGE01_TO_STAGE11")
    if not allowed:
        fail("AUTHORIZED_EFFECTFUL_RANGE_EMPTY")
    try:
        idx=[EXPECTED.index(x) for x in allowed]
    except ValueError:
        fail("AUTHORIZED_RANGE_CONTAINS_UNREGISTERED_STAGE")
    if idx!=list(range(min(idx),max(idx)+1)):
        fail("AUTHORIZED_RANGE_NOT_CONTIGUOUS")
    if execution.get("system_may_skip_stage_inside_authorized_range") is not False:
        fail("STAGE_SKIP_POLICY_NOT_FAIL_CLOSED")
    if execution.get("normal_pass_auto_continue_within_authorized_range") is not True:
        fail("NORMAL_PASS_AUTO_CONTINUE_NOT_ENABLED")

    contracts=auth.get("stage_contracts") or []
    if [str(x.get("stage_uid") or "") for x in contracts]!=EXPECTED:
        fail("STAGE_CONTRACT_COVERAGE_DRIFT")
    for row in contracts:
        uid=str(row["stage_uid"])
        reg=stages[uid]
        for key in ("name","entry_gate","exit_gate","next_stage_uid"):
            if str(row.get(key) or "")!=str(reg.get(key) or ""):
                fail("STAGE_CONTRACT_"+key.upper()+"_DRIFT:"+uid)

    for owner in [
        ".github/scripts/current_stage_execute.py",
        ".github/scripts/common_stage_preterminal.py",
        ".github/scripts/common_stage_closure.py",
        ".github/scripts/common_stage_closure_adapter.py",
        ".github/scripts/common_stage_terminalizer.py",
        ".github/scripts/common_successor_binding_resolver.py",
        ".github/scripts/common_successor_materialize.py",
        ".github/scripts/common_successor_work_unit_builder.py",
        ".github/scripts/common_stage_human_gate.py",
        ".github/scripts/stage_lifecycle_gate.py",
        ".github/workflows/product-stage-lifecycle-driver.yml",
    ]:
        local_file(product,owner,"COMMON_LIFECYCLE_OWNER")

    return auth,life,stages,allowed

def validate_stage_runtime(product,gov,stage,stages,allowed):
    if stage not in EXPECTED:
        fail("UNREGISTERED_STAGE:"+stage)
    if stage not in allowed:
        fail("STAGE_OUTSIDE_AUTHORIZED_EFFECTFUL_RANGE:"+stage)
    if stage=="STAGE-01":
        local_file(product,".github/scripts/stage01_current_materialize.py","STAGE01_MATERIALIZER")
        return

    src=product/FLOW/"EXACT_OPERATION_BINDING_SOURCES"/(stage+".yaml")
    data=load(src)
    if data.get("artifact_type")!="EXACT_OPERATION_BINDING_SOURCE" or data.get("status")!="CURRENT_EXACT_BINDINGS":
        fail("EXACT_BINDING_SOURCE_INVALID:"+stage)
    if str(data.get("stage_uid") or "")!=stage:
        fail("EXACT_BINDING_STAGE_DRIFT:"+stage)

    expected=list(map(str,stages[stage].get("operations") or []))
    bindings=data.get("operation_bindings") or {}
    if list(map(str,bindings.keys()))!=expected:
        fail("EXACT_OPERATION_BINDING_COVERAGE_DRIFT:"+stage)
    for op in expected:
        row=bindings.get(op) or {}
        if row.get("applicability") not in {"REQUIRED","AUTHORIZED_NOT_APPLICABLE"}:
            fail("OPERATION_APPLICABILITY_INVALID:"+stage+":"+op)
        if row.get("applicability")=="REQUIRED":
            for key in ("executor_owner","executor_protocol","result_owner"):
                if not str(row.get(key) or ""):
                    fail("OPERATION_BINDING_FIELD_MISSING:"+stage+":"+op+":"+key)
            local_file(product,row.get("executor_owner"),"OPERATION_EXECUTOR_"+stage+"_"+op)
    scanner=str(data.get("scanner_owner") or "")
    protocol=str(data.get("scanner_protocol") or "")
    if not scanner or not protocol:
        fail("SCANNER_BINDING_MISSING:"+stage)
    local_file(product,scanner,"SCANNER_OWNER_"+stage)
    validators=set(map(str,(data.get("validator_bindings") or {}).keys()))
    expected_validators=set(map(str,stages[stage].get("validators") or []))
    if validators!=expected_validators:
        fail("VALIDATOR_BINDING_COVERAGE_DRIFT:"+stage)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--product-root",required=True)
    ap.add_argument("--governance-root",required=True)
    ap.add_argument("--mode",choices=["plan","execution-ready"],default="plan")
    ap.add_argument("--stage")
    a=ap.parse_args()
    product=Path(a.product_root).resolve()
    gov=Path(a.governance_root).resolve()
    auth,life,stages,allowed=validate_contract(product,gov)
    if a.mode=="execution-ready":
        if not a.stage:
            fail("STAGE_REQUIRED_FOR_EXECUTION_READY")
        validate_stage_runtime(product,gov,a.stage,stages,allowed)
    print("PASS: Mother lifecycle is the single Stage-01..11 specification source")
    print("PASS: product execution uses one Current governance selection and one stage-range authorization contract")
    print("PASS: duplicate transition/permission/runtime projection ledgers are not execution authorities")
    if a.mode=="execution-ready":
        print("PASS: current stage exact runtime bindings are ready",a.stage)

if __name__=="__main__":
    main()
