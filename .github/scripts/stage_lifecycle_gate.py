#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import yaml

FLOW=Path("STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW")
AUTH=FLOW/"FULL_STAGE_LIFECYCLE_AUTHORIZATION_CONTRACT.yaml"
LIFE=Path(".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml")
EXPECTED=[f"STAGE-{i:02d}" for i in range(1,12)]

def load(p):
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
    auth=load(product/AUTH)
    life=load(gov/LIFE)
    rows=[x for x in life.get("stages") or [] if isinstance(x,dict)]
    order=[str(x.get("stage_uid") or "") for x in rows]
    if order!=EXPECTED:
        block("LIFECYCLE_ORDER_DRIFT")
    stages={str(x["stage_uid"]):x for x in rows}
    allowed=list(map(str,(auth.get("execution_authorization") or {}).get("authorized_effectful_range") or []))
    if not allowed:
        block("AUTHORIZED_RANGE_EMPTY")
    return auth,order,stages,allowed

def validate_all(product,gov):
    auth,order,stages,allowed=context(product,gov)
    try:
        idx=[order.index(x) for x in allowed]
    except ValueError:
        block("AUTHORIZED_RANGE_CONTAINS_UNREGISTERED_STAGE")
    if idx!=list(range(min(idx),max(idx)+1)):
        block("AUTHORIZED_RANGE_NOT_CONTIGUOUS")
    execution=auth.get("execution_authorization") or {}
    if execution.get("system_may_skip_stage_inside_authorized_range") is not False:
        block("STAGE_SKIP_POLICY_NOT_FAIL_CLOSED")
    if execution.get("normal_pass_auto_continue_within_authorized_range") is not True:
        block("NORMAL_PASS_AUTO_CONTINUE_NOT_ENABLED")
    print("PASS: lifecycle gates derive from Mother registry; product contract only supplies requested range")
    return auth,order,stages,allowed

def assert_authorized(product,gov,stage):
    auth,order,stages,allowed=validate_all(product,gov)
    if stage not in order:
        block("UNREGISTERED_STAGE:"+stage)
    if stage not in allowed:
        block("STAGE_OUTSIDE_AUTHORIZED_EFFECTFUL_RANGE:"+stage)
    print("PASS: stage is inside exact requested range",stage)

def assert_work_unit(product,gov,stage,work_unit):
    assert_authorized(product,gov,stage)
    wp=(product/Path(work_unit)).resolve()
    try:
        wp.relative_to(product)
    except ValueError:
        block("WORK_UNIT_PATH_ESCAPES_PRODUCT_ROOT")
    d=load(wp)
    state=load(wp.parent/"EXECUTION_STATE.yaml")
    if str(d.get("stage_uid") or "")!=stage or str(state.get("stage_uid") or "")!=stage:
        block("WORK_UNIT_STAGE_DRIFT")
    if str(d.get("work_unit_uid") or "")!=wp.parent.name or str(state.get("work_unit_uid") or "")!=wp.parent.name:
        block("WORK_UNIT_UID_DRIFT")
    status=str(state.get("status") or "")
    projected=str(d.get("current_status") or "")
    if projected and projected!=status:
        block("WORK_UNIT_STATE_PROJECTION_DRIFT:"+projected+":"+status)
    if status.startswith("CLOSED"):
        block("CLOSED_WORK_UNIT_REENTRY_FORBIDDEN")
    if status not in {"READY_FOR_EXECUTION","IN_PROGRESS","EXECUTION_COMPLETE_CLOSURE_PENDING"}:
        block("WORK_UNIT_STATUS_INVALID:"+status)
    kind=str(d.get("work_unit_activation_kind") or "")
    reentry=("predecessor_work_unit_uid","predecessor_work_unit_ref","predecessor_terminal_receipt_ref","reentry_authority_ref")
    if kind=="INITIAL_STAGE_WORK_UNIT":
        present=[k for k in reentry if str(d.get(k) or "").strip()]
        if present:
            block("INITIAL_WORK_UNIT_REENTRY_FIELDS_FORBIDDEN:"+",".join(present))
    elif kind=="SUCCESSOR_REENTRY_WORK_UNIT":
        missing=[k for k in reentry if not str(d.get(k) or "").strip()]
        if missing:
            block("SUCCESSOR_WORK_UNIT_PREDECESSOR_BINDING_MISSING:"+",".join(missing))
        for key in ("predecessor_work_unit_ref","predecessor_terminal_receipt_ref","reentry_authority_ref"):
            p=(product/Path(str(d[key]))).resolve()
            try:
                p.relative_to(product)
            except ValueError:
                block("SUCCESSOR_REFERENCE_ESCAPES_PRODUCT_ROOT:"+key)
            if not p.is_file():
                block("SUCCESSOR_REFERENCE_MISSING:"+key)
    else:
        block("WORK_UNIT_ACTIVATION_KIND_INVALID:"+kind)
    print("PASS: Work Unit entry is valid",wp.parent.name)

def assert_transition(product,gov,from_stage,to_stage):
    auth,order,stages,allowed=validate_all(product,gov)
    if from_stage not in order:
        block("UNREGISTERED_FROM_STAGE:"+from_stage)
    expected=str(stages[from_stage].get("next_stage_uid") or "")
    if expected!=to_stage:
        block("ILLEGAL_STAGE_TRANSITION:"+from_stage+"->"+to_stage+":expected="+expected)
    if to_stage.startswith("STAGE-") and to_stage not in allowed:
        block("SUCCESSOR_OUTSIDE_AUTHORIZED_EFFECTFUL_RANGE:"+to_stage)
    print("PASS: legal successor transition",from_stage,"->",to_stage)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--product-root",required=True)
    ap.add_argument("--governance-root",required=True)
    ap.add_argument("--mode",required=True,choices=["validate-all","assert-stage-authorized","assert-work-unit-entry","assert-transition"])
    ap.add_argument("--stage")
    ap.add_argument("--work-unit")
    ap.add_argument("--from-stage")
    ap.add_argument("--to-stage")
    a=ap.parse_args()
    product=Path(a.product_root).resolve(); gov=Path(a.governance_root).resolve()
    if a.mode=="validate-all":
        validate_all(product,gov)
    elif a.mode=="assert-stage-authorized":
        if not a.stage: block("STAGE_REQUIRED")
        assert_authorized(product,gov,a.stage)
    elif a.mode=="assert-work-unit-entry":
        if not a.stage or not a.work_unit: block("STAGE_AND_WORK_UNIT_REQUIRED")
        assert_work_unit(product,gov,a.stage,a.work_unit)
    else:
        if not a.from_stage or not a.to_stage: block("FROM_AND_TO_STAGE_REQUIRED")
        assert_transition(product,gov,a.from_stage,a.to_stage)

if __name__=="__main__":
    main()
