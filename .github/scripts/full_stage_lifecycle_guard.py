#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import yaml

EXPECTED=[f"STAGE-{i:02d}" for i in range(1,12)]
FLOW=Path("STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW")
LIFECYCLE=Path(".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml")

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0:
        raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict):
        raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d

def fail(x):
    raise SystemExit("BLOCK:"+x)

def local_owner(product,value,label):
    value=str(value or "").strip()
    if not value or value=="UNRESOLVED":
        return None
    p=(product/Path(value)).resolve()
    try:
        p.relative_to(product)
    except ValueError:
        fail(label+"_OWNER_ESCAPES_PRODUCT_ROOT:"+value)
    if not p.is_file():
        fail(label+"_OWNER_MISSING:"+value)
    return p

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
    t=load(product/FLOW/"FULL_STAGE_TRANSITION_MATRIX.yaml")
    pmat=load(product/FLOW/"FULL_STAGE_PERMISSION_CONTINUITY_MATRIX.yaml")
    adapters=load(product/FLOW/"FULL_STAGE_RUNTIME_ADAPTER_REGISTRY.yaml")
    closure=load(product/FLOW/"COMMON_STAGE_CLOSURE_PROTOCOL.yaml")
    successor=load(product/FLOW/"COMMON_SUCCESSOR_MATERIALIZATION_PROTOCOL.yaml")
    handoff=load(product/FLOW/"FULL_STAGE_HANDOFF_INPUT_ORIGIN_MATRIX.yaml")
    op_profiles=load(product/FLOW/"FULL_STAGE_OPERATION_BINDING_PROFILE_REGISTRY.yaml")
    preentry=load(product/FLOW/"FULL_STAGE_PREENTRY_CONVERGENCE_MATRIX.yaml")
    target=load(product/"STAGE_EXECUTION/SHARED_AUTHORITY/IMPLEMENTATION_EXECUTION_TARGET_AUTHORITY.yaml")
    lr=load(gov/LIFECYCLE)

    stages=lr.get("stages") or []
    order=[str(x.get("stage_uid") or "") for x in stages if isinstance(x,dict)]
    if order!=EXPECTED: fail("LIFECYCLE_REGISTRY_ORDER_DRIFT")
    rm={str(x["stage_uid"]):x for x in stages}

    if list(map(str,c.get("lifecycle_stage_uids") or []))!=EXPECTED:
        fail("CONTRACT_RANGE_NOT_01_11")
    rows=c.get("stage_contracts") or []
    if [str(x.get("stage_uid") or "") for x in rows]!=EXPECTED:
        fail("STAGE_ROWS_DRIFT")
    for x in rows:
        uid=str(x["stage_uid"])
        for k in ("name","entry_gate","exit_gate","next_stage_uid"):
            if str(x.get(k) or "")!=str(rm[uid].get(k) or ""):
                fail("STAGE_"+k.upper()+"_DRIFT:"+uid)

    auth=c.get("execution_authorization") or {}
    planning=list(map(str,auth.get("planning_range") or []))
    allowed=list(map(str,auth.get("authorized_effectful_range") or []))
    if planning!=EXPECTED: fail("PLANNING_RANGE_NOT_FULL")
    if not allowed: fail("AUTHORIZED_RANGE_EMPTY")
    pos=[EXPECTED.index(x) for x in allowed]
    if pos!=list(range(min(pos),max(pos)+1)): fail("AUTHORIZED_RANGE_NOT_CONTIGUOUS")
    if auth.get("system_may_expand_range") is not False or auth.get("system_may_shrink_range") is not False:
        fail("RANGE_AUTHORITY_NOT_FAIL_CLOSED")

    topo=c.get("lifecycle_topology") or {}
    if topo.get("true_governed_unit_closure_stage")!="STAGE-11":
        fail("TRUE_CLOSURE_STAGE_DRIFT")
    if topo.get("stage04_is_full_lifecycle_closure") is not False:
        fail("STAGE04_FALSE_CLOSURE")
    if topo.get("stage_local_authorization_logic")!="FORBIDDEN" or topo.get("stage_local_permission_model")!="FORBIDDEN":
        fail("STAGE_LOCAL_AUTHORITY_NOT_FORBIDDEN")

    pc=c.get("permission_continuity_contract") or {}
    expected_pc={
        "semantic_owner_stage":"STAGE-02",
        "visual_projection_stage":"STAGE-03",
        "immutable_freeze_stage":"STAGE-04",
        "implementation_stage":"STAGE-05",
        "verification_stage":"STAGE-06",
        "production_acceptance_stage":"STAGE-10",
        "final_reconciliation_stage":"STAGE-11",
    }
    for k,v in expected_pc.items():
        if pc.get(k)!=v:
            fail("PERMISSION_CONTINUITY_"+k.upper()+"_DRIFT")
    if pc.get("downstream_may_redefine_permission_semantics") is not False:
        fail("DOWNSTREAM_PERMISSION_REDEFINITION_NOT_FORBIDDEN")

    transition_rows=t.get("transitions") or []
    if [str(x.get("stage_uid") or "") for x in transition_rows]!=EXPECTED:
        fail("TRANSITION_MATRIX_STAGE_COVERAGE_DRIFT")
    for i,row in enumerate(transition_rows):
        uid=EXPECTED[i]
        reg=rm[uid]
        pred=None if i==0 else EXPECTED[i-1]
        if row.get("predecessor_stage_uid")!=pred:
            fail("TRANSITION_PREDECESSOR_DRIFT:"+uid)
        for k in ("entry_gate","exit_gate","next_stage_uid"):
            if str(row.get(k) or "")!=str(reg.get(k) or ""):
                fail("TRANSITION_"+k.upper()+"_DRIFT:"+uid)
        if bool(row.get("current_effectful_authorized"))!=(uid in allowed):
            fail("TRANSITION_AUTHORIZATION_PROJECTION_DRIFT:"+uid)

    if pmat.get("semantic_owner_stage")!="STAGE-02":
        fail("PERMISSION_MATRIX_SEMANTIC_OWNER_DRIFT")
    checkpoints=pmat.get("stage_checkpoints") or []
    if [str(x.get("stage_uid") or "") for x in checkpoints]!=EXPECTED:
        fail("PERMISSION_MATRIX_STAGE_COVERAGE_DRIFT")
    if (pmat.get("rules") or {}).get("downstream_semantic_redefinition")!="FORBIDDEN":
        fail("PERMISSION_MATRIX_DOWNSTREAM_REDEFINITION_NOT_FORBIDDEN")

    arules=adapters.get("rules") or {}
    if arules.get("operation_universe_source")!="CURRENT_LIFECYCLE_REGISTRY":
        fail("ADAPTER_OPERATION_UNIVERSE_NOT_REGISTRY_DRIVEN")
    if arules.get("operation_executor_source")!="CURRENT_WORK_UNIT_OPERATION_BINDINGS":
        fail("ADAPTER_OPERATION_EXECUTOR_SOURCE_DRIFT")
    if arules.get("stage_specific_adapter_may_define_authorization") is not False:
        fail("ADAPTER_STAGE_LOCAL_AUTHORIZATION_NOT_FORBIDDEN")
    if arules.get("stage_specific_adapter_may_define_permission_semantics") is not False:
        fail("ADAPTER_STAGE_LOCAL_PERMISSION_NOT_FORBIDDEN")
    local_owner(product,arules.get("common_closure_orchestrator"),"COMMON_CLOSURE")
    local_owner(product,arules.get("common_successor_orchestrator"),"COMMON_SUCCESSOR")

    adapter_rows=adapters.get("adapters") or []
    if [str(x.get("stage_uid") or "") for x in adapter_rows]!=EXPECTED:
        fail("RUNTIME_ADAPTER_STAGE_COVERAGE_DRIFT")
    unresolved=[]
    for row in adapter_rows:
        uid=str(row.get("stage_uid") or "")
        for field in ("materializer_owner","operation_executor_owner","closure_adapter_owner"):
            value=str(row.get(field) or "").strip()
            if not value or value=="UNRESOLVED":
                unresolved.append(uid+":"+field)
            else:
                local_owner(product,value,"RUNTIME_ADAPTER_"+uid+"_"+field.upper())
        state=str(row.get("state") or "")
        if not state:
            fail("RUNTIME_ADAPTER_STATE_MISSING:"+uid)
        if state not in {"READY","READY_STRUCTURAL"}:
            unresolved.append(uid+":state="+state)

    if closure.get("owner")!="COMMON_STAGE_CLOSURE_PROTOCOL":
        fail("COMMON_CLOSURE_OWNER_DRIFT")
    if list(map(str,closure.get("applies_to") or []))!=EXPECTED:
        fail("COMMON_CLOSURE_STAGE_COVERAGE_DRIFT")
    if (closure.get("rules") or {}).get("stage_specific_closure_semantics")!="FORBIDDEN":
        fail("COMMON_CLOSURE_STAGE_LOCAL_SEMANTICS_NOT_FORBIDDEN")

    if successor.get("owner")!="COMMON_SUCCESSOR_WORK_UNIT_MATERIALIZER":
        fail("COMMON_SUCCESSOR_OWNER_DRIFT")
    if list(map(str,successor.get("applies_to_predecessors") or []))!=EXPECTED:
        fail("COMMON_SUCCESSOR_STAGE_COVERAGE_DRIFT")
    if (successor.get("rules") or {}).get("stage_local_successor_logic")!="FORBIDDEN":
        fail("COMMON_SUCCESSOR_STAGE_LOCAL_LOGIC_NOT_FORBIDDEN")

    handoff_rows=handoff.get("stages") or []
    if [str(x.get("stage_uid") or "") for x in handoff_rows]!=EXPECTED:
        fail("HANDOFF_INPUT_ORIGIN_STAGE_COVERAGE_DRIFT")
    for row in handoff_rows:
        uid=str(row.get("stage_uid") or "")
        registered=rm[uid]
        expected_inputs=list(map(str,registered.get("inputs") or []))
        matrix_inputs=[str(x.get("input_uid") or "") for x in row.get("inputs") or [] if isinstance(x,dict)]
        if matrix_inputs!=expected_inputs:
            fail("HANDOFF_INPUT_DENOMINATOR_DRIFT:"+uid)
        origins={str(x.get("input_uid") or ""):str(x.get("origin") or "") for x in row.get("inputs") or [] if isinstance(x,dict)}
        registered_origins={str(k):str(v) for k,v in (registered.get("input_origins") or {}).items()}
        if origins!=registered_origins:
            fail("HANDOFF_INPUT_ORIGIN_DRIFT:"+uid)

    profiles=op_profiles.get("profiles") or []
    if [str(x.get("stage_uid") or "") for x in profiles]!=EXPECTED:
        fail("OPERATION_BINDING_PROFILE_STAGE_COVERAGE_DRIFT")
    for row in profiles:
        owner=local_owner(product,row.get("binding_manifest_owner"),"OP_BINDING_PROFILE_"+str(row.get("stage_uid")))
        if owner is None:
            fail("OPERATION_BINDING_PROFILE_OWNER_UNRESOLVED:"+str(row.get("stage_uid")))
    oprules=op_profiles.get("rules") or {}
    if oprules.get("binding_manifest_required_before_successor_work_unit_materialization") is not True:
        fail("SUCCESSOR_OPERATION_BINDING_MANIFEST_NOT_REQUIRED")
    if oprules.get("unresolved_binding_disposition")!="BLOCK_AT_STAGE_BOUNDARY_BEFORE_SUCCESSOR_WORK_UNIT_CREATION":
        fail("UNRESOLVED_OPERATION_BINDING_NOT_BOUNDARY_BLOCK")

    dims=preentry.get("dimensions") or {}
    structural_required=[
      "lifecycle_registry_alignment","stage_order_and_entry_exit_gate_alignment","explicit_range_authority_model",
      "permission_continuity_model","common_closure_protocol","common_terminal_receipt_protocol",
      "common_successor_materialization_protocol","cross_stage_input_origin_matrix","full_stage_transition_matrix",
      "runtime_adapter_orchestration_model","stage04_not_full_closure_semantics","stage11_true_closure_semantics"
    ]
    for key in structural_required:
        if not str(dims.get(key) or "").startswith("PASS"):
            fail("PREENTRY_STRUCTURAL_CONVERGENCE_NOT_PASS:"+key)

    authority=target.get("authority") or {}
    if authority.get("status")!="CURRENT_DYNAMIC_RESOLUTION_CONTRACT":
        fail("STAGE05_TARGET_AUTHORITY_NOT_DYNAMIC_CURRENT_PROTOCOL")
    if authority.get("static_historical_branch_or_head_binding")!="FORBIDDEN":
        fail("STAGE05_TARGET_STATIC_HISTORY_NOT_FORBIDDEN")
    serialized=yaml.safe_dump(target,sort_keys=True)
    if "V232_STAGE04_SUCCESSOR_BINDING_CONFORMANCE" in serialized or "construction_branch: new" in serialized or "production_branch: main" in serialized:
        fail("STAGE05_TARGET_HISTORICAL_BINDING_RESIDUE")

    if list(map(str,r.get("planned_lifecycle_range") or []))!=EXPECTED:
        fail("RESOLUTION_TRUNCATES_LIFECYCLE")
    if list(map(str,r.get("authorized_effectful_range") or []))!=allowed:
        fail("RESOLUTION_AUTHORIZED_RANGE_DRIFT")
    for unit in r.get("stage_sequence") or []:
        sr=unit.get("stages") or []
        if [str(x.get("stage_uid") or "") for x in sr]!=EXPECTED:
            fail("UNIT_STAGE_SEQUENCE_NOT_01_11:"+str(unit.get("governed_unit_uid")))
        for row in sr:
            if str(row.get("stage_uid")) not in allowed and row.get("effectful_execution_admitted") is not False:
                fail("FUTURE_STAGE_PREAUTHORIZED:"+str(row.get("stage_uid")))

    if list(map(str,m.get("planned_lifecycle_range") or []))!=EXPECTED:
        fail("REMEDIATION_TRUNCATES_LIFECYCLE")
    if list(map(str,m.get("authorized_effectful_stage_range") or []))!=allowed:
        fail("REMEDIATION_AUTH_RANGE_DRIFT")

    cb={str(x.get("uid") or "") for x in c.get("known_runtime_blockers") or [] if isinstance(x,dict) and x.get("status")=="OPEN"}
    db={str(x.get("uid") or "") for x in d.get("defects") or [] if isinstance(x,dict) and x.get("state") in {"OPEN","REVERIFY_REQUIRED"}}
    if cb!=db:
        fail("BLOCKER_LEDGER_DRIFT")

    if a.mode=="execution-ready":
        if cb:
            fail("FULL_STAGE_RUNTIME_NOT_READY:"+",".join(sorted(cb)))
        if unresolved:
            fail("FULL_STAGE_RUNTIME_ADAPTERS_NOT_READY:"+",".join(sorted(set(unresolved))))
        effectful=preentry.get("effectful_preentry") or {}
        if effectful.get("stage01_may_start_now") is not True:
            fail("STAGE01_PREENTRY_HOLD:"+str(effectful.get("hold_reason") or "UNSPECIFIED"))

    print("PASS: full lifecycle 01-11 uses one authorization contract")
    print("PASS: transition, permission, closure and successor protocols cover all registered stages")
    print("PASS: future stages cannot be pre-executed outside the authorized range")
    print("INFO: declared runtime blockers="+str(len(cb)))
    print("INFO: unresolved physical runtime adapter fields="+str(len(set(unresolved))))
    print("INFO: planning validation grants zero Stage completion credit")

if __name__=="__main__":
    main()
