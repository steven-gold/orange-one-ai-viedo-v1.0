#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import yaml

FLOW=Path("STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW")
LIFE=Path(".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml")

def y(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0:
        raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict):
        raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d

def block(x):
    raise SystemExit("BLOCK:"+x)

def context(product,gov):
    c=y(product/FLOW/"FULL_STAGE_LIFECYCLE_AUTHORIZATION_CONTRACT.yaml")
    t=y(product/FLOW/"FULL_STAGE_TRANSITION_MATRIX.yaml")
    p=y(product/FLOW/"FULL_STAGE_PERMISSION_CONTINUITY_MATRIX.yaml")
    a=y(product/FLOW/"FULL_STAGE_RUNTIME_ADAPTER_REGISTRY.yaml")
    l=y(gov/LIFE)
    stages=l.get("stages") or []
    order=[str(x.get("stage_uid") or "") for x in stages if isinstance(x,dict)]
    reg={str(x.get("stage_uid")):x for x in stages if isinstance(x,dict)}
    return c,t,p,a,order,reg

def validate_all(product,gov):
    c,t,p,a,order,reg=context(product,gov)
    expected=[f"STAGE-{i:02d}" for i in range(1,12)]
    if order!=expected: block("LIFECYCLE_ORDER_DRIFT")
    allowed=list(map(str,(c.get("execution_authorization") or {}).get("authorized_effectful_range") or []))
    rows=t.get("transitions") or []
    adapters=a.get("adapters") or []
    checks=p.get("stage_checkpoints") or []
    if [str(x.get("stage_uid")) for x in rows]!=expected: block("TRANSITION_MATRIX_STAGE_COVERAGE_DRIFT")
    if [str(x.get("stage_uid")) for x in adapters]!=expected: block("ADAPTER_REGISTRY_STAGE_COVERAGE_DRIFT")
    if [str(x.get("stage_uid")) for x in checks]!=expected: block("PERMISSION_MATRIX_STAGE_COVERAGE_DRIFT")
    for i,row in enumerate(rows):
        uid=expected[i]; r=reg[uid]
        if str(row.get("entry_gate") or "")!=str(r.get("entry_gate") or ""): block("ENTRY_GATE_DRIFT:"+uid)
        if str(row.get("exit_gate") or "")!=str(r.get("exit_gate") or ""): block("EXIT_GATE_DRIFT:"+uid)
        if str(row.get("next_stage_uid") or "")!=str(r.get("next_stage_uid") or ""): block("NEXT_STAGE_DRIFT:"+uid)
        pred=None if i==0 else expected[i-1]
        if row.get("predecessor_stage_uid")!=pred: block("PREDECESSOR_DRIFT:"+uid)
        if bool(row.get("current_effectful_authorized"))!=(uid in allowed): block("EFFECTFUL_AUTHORIZATION_PROJECTION_DRIFT:"+uid)
    if p.get("semantic_owner_stage")!="STAGE-02": block("PERMISSION_SEMANTIC_OWNER_DRIFT")
    if (p.get("rules") or {}).get("downstream_semantic_redefinition")!="FORBIDDEN": block("DOWNSTREAM_PERMISSION_REDEFINITION_NOT_FORBIDDEN")
    rules=a.get("rules") or {}
    if rules.get("operation_universe_source")!="CURRENT_LIFECYCLE_REGISTRY": block("ADAPTER_OPERATION_UNIVERSE_NOT_REGISTRY_DRIVEN")
    if rules.get("operation_executor_source")!="CURRENT_WORK_UNIT_OPERATION_BINDINGS": block("ADAPTER_EXECUTOR_SOURCE_DRIFT")
    if rules.get("stage_specific_adapter_may_define_authorization") is not False: block("STAGE_LOCAL_AUTHORIZATION_NOT_FORBIDDEN")
    if rules.get("stage_specific_adapter_may_define_permission_semantics") is not False: block("STAGE_LOCAL_PERMISSION_NOT_FORBIDDEN")
    print("PASS: Stage-01..11 transition, permission and runtime-adapter skeletons are registry-aligned")
    return c,t,p,a,order,reg

def assert_authorized(product,gov,stage):
    c,t,p,a,order,reg=validate_all(product,gov)
    if stage not in order: block("UNREGISTERED_STAGE:"+stage)
    allowed=list(map(str,(c.get("execution_authorization") or {}).get("authorized_effectful_range") or []))
    if stage not in allowed: block("STAGE_OUTSIDE_AUTHORIZED_EFFECTFUL_RANGE:"+stage)
    print("PASS: stage inside exact authorized effectful range",stage)

def assert_work_unit(product,gov,stage,work_unit):
    assert_authorized(product,gov,stage)
    wp=(product/Path(work_unit)).resolve()
    try: wp.relative_to(product)
    except ValueError: block("WORK_UNIT_PATH_ESCAPES_PRODUCT_ROOT")
    d=y(wp)
    if str(d.get("stage_uid") or "")!=stage: block("WORK_UNIT_STAGE_DRIFT")
    if str(d.get("work_unit_uid") or "")!=wp.parent.name: block("WORK_UNIT_UID_DRIFT")
    if stage!="STAGE-01":
        required=("predecessor_work_unit_uid","predecessor_work_unit_ref","predecessor_terminal_receipt_ref")
        missing=[k for k in required if not str(d.get(k) or "").strip()]
        if missing: block("SUCCESSOR_WORK_UNIT_PREDECESSOR_BINDING_MISSING:"+",".join(missing))
        pr=(product/Path(str(d["predecessor_terminal_receipt_ref"]))).resolve()
        try: pr.relative_to(product)
        except ValueError: block("PREDECESSOR_RECEIPT_PATH_ESCAPES_PRODUCT_ROOT")
        if not pr.is_file(): block("PREDECESSOR_TERMINAL_RECEIPT_MISSING")
    print("PASS: Work Unit entry bound to common lifecycle authorization",wp.parent.name)

def assert_transition(product,gov,from_stage,to_stage):
    c,t,p,a,order,reg=validate_all(product,gov)
    if from_stage not in order: block("UNREGISTERED_FROM_STAGE")
    expected=str(reg[from_stage].get("next_stage_uid") or "")
    if expected!=to_stage: block("ILLEGAL_STAGE_TRANSITION:"+from_stage+"->"+to_stage+":expected="+expected)
    allowed=list(map(str,(c.get("execution_authorization") or {}).get("authorized_effectful_range") or []))
    if to_stage.startswith("STAGE-") and to_stage not in allowed:
        block("SUCCESSOR_OUTSIDE_AUTHORIZED_EFFECTFUL_RANGE:"+to_stage)
    print("PASS: legal authorized successor transition",from_stage,"->",to_stage)

def self_test(product,gov):
    validate_all(product,gov)
    assert_authorized(product,gov,"STAGE-01")
    try:
        assert_authorized(product,gov,"STAGE-05")
    except SystemExit as e:
        if "STAGE_OUTSIDE_AUTHORIZED_EFFECTFUL_RANGE:STAGE-05" not in str(e): raise
    else:
        block("SELF_TEST_STAGE05_UNAUTHORIZED_NOT_BLOCKED")
    try:
        assert_transition(product,gov,"STAGE-02","STAGE-04")
    except SystemExit as e:
        if "ILLEGAL_STAGE_TRANSITION" not in str(e): raise
    else:
        block("SELF_TEST_STAGE_SKIP_NOT_BLOCKED")
    print("PASS: lifecycle negative self-tests")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--product-root",required=True)
    ap.add_argument("--governance-root",required=True)
    ap.add_argument("--mode",required=True,choices=["validate-all","assert-stage-authorized","assert-work-unit-entry","assert-transition","self-test"])
    ap.add_argument("--stage")
    ap.add_argument("--work-unit")
    ap.add_argument("--from-stage")
    ap.add_argument("--to-stage")
    a=ap.parse_args()
    product=Path(a.product_root).resolve(); gov=Path(a.governance_root).resolve()
    if a.mode=="validate-all": validate_all(product,gov)
    elif a.mode=="assert-stage-authorized":
        if not a.stage: block("STAGE_REQUIRED")
        assert_authorized(product,gov,a.stage)
    elif a.mode=="assert-work-unit-entry":
        if not a.stage or not a.work_unit: block("STAGE_AND_WORK_UNIT_REQUIRED")
        assert_work_unit(product,gov,a.stage,a.work_unit)
    elif a.mode=="assert-transition":
        if not a.from_stage or not a.to_stage: block("FROM_AND_TO_STAGE_REQUIRED")
        assert_transition(product,gov,a.from_stage,a.to_stage)
    else: self_test(product,gov)

if __name__=="__main__":
    main()
