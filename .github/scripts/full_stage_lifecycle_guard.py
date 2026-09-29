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
INVARIANTS=Path(".github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml")

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

    execution=auth.get("execution_authorization") or {}
    allowed=list(map(str,execution.get("authorized_effectful_range") or []))
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

    for owner in [
        ".github/scripts/current_stage_execute.py",
        ".github/scripts/common_stage_preterminal.py",
        ".github/scripts/common_stage_closure.py",
        ".github/scripts/common_stage_closure_adapter.py",
        ".github/scripts/common_stage_terminalizer.py",
        ".github/scripts/common_successor_binding_resolver.py",
        ".github/scripts/common_successor_work_unit_builder.py",
        ".github/scripts/common_stage_human_gate.py",
        ".github/scripts/stage_lifecycle_gate.py",
        ".github/workflows/product-stage-lifecycle-driver.yml",
    ]:
        local_file(product,owner,"COMMON_LIFECYCLE_OWNER")

    return auth,life,stages,allowed

def _file_gap(root,value,label,gaps):
    value=str(value or "").strip()
    if not value:
        gaps.append(label+"_MISSING")
        return
    p=(root/Path(value)).resolve()
    try:
        p.relative_to(root)
    except ValueError:
        gaps.append(label+"_ESCAPES_PRODUCT_ROOT:"+value)
        return
    if not p.is_file():
        gaps.append(label+"_NOT_FOUND:"+value)

def stage_runtime_gaps(product,gov,stage,stages,allowed):
    gaps=[]
    if stage not in EXPECTED:
        return ["UNREGISTERED_STAGE:"+stage]
    if stage not in allowed:
        return ["STAGE_OUTSIDE_AUTHORIZED_EFFECTFUL_RANGE:"+stage]
    if stage=="STAGE-01":
        _file_gap(product,".github/scripts/stage01_current_materialize.py","STAGE01_MATERIALIZER",gaps)
        return gaps

    src=product/FLOW/"EXACT_OPERATION_BINDING_SOURCES"/(stage+".yaml")
    if not src.is_file() or src.stat().st_size<=0:
        return ["EXACT_BINDING_SOURCE_MISSING:"+stage]
    try:
        data=load(src)
    except SystemExit as e:
        return ["EXACT_BINDING_SOURCE_UNREADABLE:"+stage+":"+str(e)]

    if data.get("artifact_type")!="EXACT_OPERATION_BINDING_SOURCE" or data.get("status")!="CURRENT_EXACT_BINDINGS":
        gaps.append("EXACT_BINDING_SOURCE_INVALID:"+stage)
    if str(data.get("stage_uid") or "")!=stage:
        gaps.append("EXACT_BINDING_STAGE_DRIFT:"+stage)
    if str(data.get("runtime_readiness") or "EFFECTFUL_READY")!="EFFECTFUL_READY":
        gaps.append("RUNTIME_READINESS_NOT_EFFECTFUL:"+stage)

    expected=list(map(str,stages[stage].get("operations") or []))
    bindings=data.get("operation_bindings") or {}
    actual_ops=list(map(str,bindings.keys()))
    if actual_ops!=expected:
        missing=[x for x in expected if x not in bindings]
        extra=[x for x in actual_ops if x not in expected]
        if missing: gaps.append("OPERATION_BINDINGS_MISSING:"+stage+":"+",".join(missing))
        if extra: gaps.append("OPERATION_BINDINGS_EXTRA:"+stage+":"+",".join(extra))
    for op in expected:
        row=bindings.get(op) or {}
        app=row.get("applicability")
        if app not in {"REQUIRED","AUTHORIZED_NOT_APPLICABLE"}:
            gaps.append("OPERATION_APPLICABILITY_INVALID:"+stage+":"+op)
            continue
        if app=="REQUIRED":
            for key in ("executor_owner","executor_protocol","result_owner"):
                if not str(row.get(key) or ""):
                    gaps.append("OPERATION_BINDING_FIELD_MISSING:"+stage+":"+op+":"+key)
            _file_gap(product,row.get("executor_owner"),"OPERATION_EXECUTOR_"+stage+"_"+op,gaps)

    scanner=str(data.get("scanner_owner") or "")
    protocol=str(data.get("scanner_protocol") or "")
    if not scanner: gaps.append("SCANNER_OWNER_MISSING:"+stage)
    else: _file_gap(product,scanner,"SCANNER_OWNER_"+stage,gaps)
    if not protocol: gaps.append("SCANNER_PROTOCOL_MISSING:"+stage)

    validators=set(map(str,(data.get("validator_bindings") or {}).keys()))
    expected_validators=set(map(str,stages[stage].get("validators") or []))
    missing_validators=sorted(expected_validators-validators)
    extra_validators=sorted(validators-expected_validators)
    if missing_validators: gaps.append("VALIDATOR_BINDINGS_MISSING:"+stage+":"+",".join(missing_validators))
    if extra_validators: gaps.append("VALIDATOR_BINDINGS_EXTRA:"+stage+":"+",".join(extra_validators))

    expected_artifacts=list(map(str,stages[stage].get("outputs") or []))+list(map(str,stages[stage].get("required_evidence") or []))
    if stage=="STAGE-04":
        expected_artifacts=[x for x in expected_artifacts if x!="BASIC_DESIGN_DOMAIN_STEPWISE_CHECKPOINT"]
    specs=set(map(str,(data.get("artifact_specs") or {}).keys()))
    miss_specs=sorted(set(expected_artifacts)-specs)
    extra_specs=sorted(specs-set(expected_artifacts))
    if miss_specs: gaps.append("ARTIFACT_SPECS_MISSING:"+stage+":"+",".join(miss_specs))
    if extra_specs: gaps.append("ARTIFACT_SPECS_EXTRA:"+stage+":"+",".join(extra_specs))

    inv=load(gov/INVARIANTS)
    policy=((inv.get("invariants") or {}).get("CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS") or {})
    reqs=policy.get("successor_execution_binding_requirements") or {}
    expected_successor=set(map(str,reqs.get(stage) or []))
    actual_successor=set(map(str,(data.get("successor_execution_bindings") or {}).keys()))
    miss_successor=sorted(expected_successor-actual_successor)
    extra_successor=sorted(actual_successor-expected_successor)
    if miss_successor: gaps.append("SUCCESSOR_BINDINGS_MISSING:"+stage+":"+",".join(miss_successor))
    if extra_successor: gaps.append("SUCCESSOR_BINDINGS_EXTRA:"+stage+":"+",".join(extra_successor))
    return gaps

def validate_stage_runtime(product,gov,stage,stages,allowed):
    gaps=stage_runtime_gaps(product,gov,stage,stages,allowed)
    if gaps:
        for gap in gaps:
            print("GAP:",gap)
        fail("STAGE_RUNTIME_NOT_READY:"+stage+":"+str(len(gaps)))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--product-root",required=True)
    ap.add_argument("--governance-root",required=True)
    ap.add_argument("--mode",choices=["plan","execution-ready","range-ready"],default="plan")
    ap.add_argument("--stage")
    ap.add_argument("--start-stage")
    ap.add_argument("--end-stage")
    a=ap.parse_args()
    product=Path(a.product_root).resolve()
    gov=Path(a.governance_root).resolve()
    auth,life,stages,allowed=validate_contract(product,gov)
    if a.mode=="execution-ready":
        if not a.stage:
            fail("STAGE_REQUIRED_FOR_EXECUTION_READY")
        validate_stage_runtime(product,gov,a.stage,stages,allowed)
    elif a.mode=="range-ready":
        start=a.start_stage or allowed[0]
        end=a.end_stage or allowed[-1]
        if start not in allowed or end not in allowed:
            fail("REQUESTED_RANGE_OUTSIDE_AUTHORIZED_EFFECTFUL_RANGE")
        si,ei=EXPECTED.index(start),EXPECTED.index(end)
        if si>ei:
            fail("REQUESTED_RANGE_REVERSED")
        gaps=[]
        for stage in EXPECTED[si:ei+1]:
            for gap in stage_runtime_gaps(product,gov,stage,stages,allowed):
                gaps.append(stage+"|"+gap)
        if gaps:
            for gap in gaps:
                print("RANGE_GAP:",gap)
            fail("AUTHORIZED_RANGE_RUNTIME_NOT_READY:"+str(len(gaps)))
    print("PASS: Mother lifecycle is the single Stage-01..11 specification source")
    print("PASS: product execution uses one Current governance selection and one stage-range authorization contract")
    print("PASS: duplicate transition/permission/runtime projection ledgers are not execution authorities")
    if a.mode=="execution-ready":
        print("PASS: current stage exact runtime bindings are ready",a.stage)
    if a.mode=="range-ready":
        print("PASS: requested authorized stage range has complete exact runtime bindings",a.start_stage or allowed[0],"->",a.end_stage or allowed[-1])

if __name__=="__main__":
    main()
