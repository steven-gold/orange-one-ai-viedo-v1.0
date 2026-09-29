#!/usr/bin/env python3
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
import yaml

LIFECYCLE=Path(".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml")
ADAPTERS=Path("governance/ci/stage_execution_semantic_adapters.yaml")

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d

def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(o,sort_keys=False,allow_unicode=True),encoding="utf-8")

def safe(root,rel,label):
    rp=Path(str(rel or ""))
    if not str(rp) or rp.is_absolute() or ".." in rp.parts: raise SystemExit("BLOCK:"+label+"_REF_INVALID")
    p=(root/rp).resolve()
    try:p.relative_to(root)
    except ValueError: raise SystemExit("BLOCK:"+label+"_REF_ESCAPES_ROOT")
    return p

def maps(gov):
    life=load(gov/LIFECYCLE); sem=load(gov/ADAPTERS)
    stages={str(x.get("stage_uid")):x for x in life.get("stages") or [] if isinstance(x,dict)}
    return stages,sem

def validate_contract(gov):
    stages,sem=maps(gov)
    expected=[f"STAGE-{i:02d}" for i in range(1,12)]
    if list(stages)!=expected: raise SystemExit("BLOCK:SUCCESSOR_BUILDER_LIFECYCLE_ORDER_DRIFT")
    for uid in expected:
        sad=((sem.get("stages") or {}).get(uid) or {})
        if sad.get("effectful_executor_owner_resolution")!="CURRENT_WORK_UNIT_OPERATION_BINDING_ONLY":
            raise SystemExit("BLOCK:SUCCESSOR_BUILDER_EXECUTOR_RESOLUTION_DRIFT:"+uid)
        if not sad.get("scanner_dimensions"): raise SystemExit("BLOCK:SUCCESSOR_BUILDER_SCANNER_DENOMINATOR_EMPTY:"+uid)
    print("PASS: common successor builder contract covers Stage-01..11")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=["validate-contract","materialize"],default="validate-contract")
    ap.add_argument("--successor-stage")
    ap.add_argument("--predecessor-work-unit")
    ap.add_argument("--operation-binding-manifest")
    ap.add_argument("--product-root",required=True)
    ap.add_argument("--governance-root",required=True)
    a=ap.parse_args()
    root=Path(a.product_root).resolve(); gov=Path(a.governance_root).resolve()
    validate_contract(gov)
    if a.mode=="validate-contract": return
    if not a.successor_stage or not a.predecessor_work_unit or not a.operation_binding_manifest:
        raise SystemExit("BLOCK:SUCCESSOR_BUILDER_REQUIRED_ARGUMENT_MISSING")
    stages,sem=maps(gov)
    if a.successor_stage not in stages or a.successor_stage=="STAGE-01":
        raise SystemExit("BLOCK:SUCCESSOR_BUILDER_INVALID_SUCCESSOR_STAGE")
    pred_wp=safe(root,a.predecessor_work_unit,"PREDECESSOR_WORK_UNIT"); pred=load(pred_wp)
    predecessor_stage=str(pred.get("stage_uid") or "")
    if predecessor_stage not in stages:
        raise SystemExit("BLOCK:SUCCESSOR_BUILDER_PREDECESSOR_STAGE_UNREGISTERED")
    expected_successor=str(stages[predecessor_stage].get("next_stage_uid") or "")
    if expected_successor!=a.successor_stage:
        raise SystemExit("BLOCK:SUCCESSOR_BUILDER_TRANSITION_DRIFT:"+predecessor_stage+"->"+str(a.successor_stage))
    subprocess.check_call([
        sys.executable,".github/scripts/stage_lifecycle_gate.py",
        "--mode","assert-transition",
        "--from-stage",predecessor_stage,
        "--to-stage",a.successor_stage,
        "--product-root",str(root),
        "--governance-root",str(gov)
    ],cwd=root)
    receipt=pred_wp.parent/"WORK_UNIT_TERMINAL_RECEIPT.yaml"
    if not receipt.is_file(): raise SystemExit("BLOCK:SUCCESSOR_BUILDER_PREDECESSOR_TERMINAL_RECEIPT_MISSING")
    terminal=load(receipt)
    if terminal.get("status")!="CLOSED_PASS" or terminal.get("conclusion")!="success":
        raise SystemExit("BLOCK:SUCCESSOR_BUILDER_PREDECESSOR_TERMINAL_RECEIPT_NOT_PASS")
    handoff=load(pred_wp.parent/"EVIDENCE/CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml")
    if str(handoff.get("successor_stage_uid") or "")!=a.successor_stage or str(handoff.get("status") or "")!="PASS":
        raise SystemExit("BLOCK:SUCCESSOR_BUILDER_HANDOFF_NOT_PASS")

    bindings=load(safe(root,a.operation_binding_manifest,"SUCCESSOR_OPERATION_BINDING_MANIFEST"))
    stage=stages[a.successor_stage]
    expected=list(map(str,stage.get("operations") or []))
    ops=bindings.get("operation_bindings") or {}
    if list(map(str,ops))!=expected: raise SystemExit("BLOCK:SUCCESSOR_OPERATION_BINDING_COVERAGE_DRIFT")
    for uid,b in ops.items():
        if not isinstance(b,dict) or not b.get("result_owner") or not b.get("operation_receipt_ref"):
            raise SystemExit("BLOCK:SUCCESSOR_OPERATION_BINDING_INCOMPLETE:"+str(uid))
        app=str(b.get("applicability") or "")
        if app=="AUTHORIZED_NOT_APPLICABLE":
            if not b.get("authority_evidence_ref"):
                raise SystemExit("BLOCK:SUCCESSOR_OPERATION_NA_AUTHORITY_MISSING:"+str(uid))
            if b.get("executor_owner") or b.get("executor_protocol"):
                raise SystemExit("BLOCK:SUCCESSOR_OPERATION_NA_EXECUTOR_FORBIDDEN:"+str(uid))
            continue
        if app!="REQUIRED" or not b.get("executor_owner") or not b.get("executor_protocol"):
            raise SystemExit("BLOCK:SUCCESSOR_OPERATION_REQUIRED_EXECUTOR_MISSING:"+str(uid))
        ep=safe(root,b.get("executor_owner"),"SUCCESSOR_EXECUTOR_OWNER")
        if not ep.is_file(): raise SystemExit("BLOCK:SUCCESSOR_EXECUTOR_OWNER_MISSING:"+str(uid))

    successor_uid=str(bindings.get("work_unit_uid") or "")
    governed=str(pred.get("governed_unit_uid") or "")
    reentry_authority_ref=str(bindings.get("reentry_authority_ref") or "")
    if not reentry_authority_ref: raise SystemExit("BLOCK:SUCCESSOR_REENTRY_AUTHORITY_REF_MISSING")
    rap=safe(root,reentry_authority_ref,"SUCCESSOR_REENTRY_AUTHORITY")
    if not rap.is_file(): raise SystemExit("BLOCK:SUCCESSOR_REENTRY_AUTHORITY_NOT_FOUND")
    if not successor_uid or str(bindings.get("stage_uid") or "")!=a.successor_stage:
        raise SystemExit("BLOCK:SUCCESSOR_BINDING_MANIFEST_IDENTITY_DRIFT")
    if str(bindings.get("governed_unit_uid") or "")!=governed:
        raise SystemExit("BLOCK:SUCCESSOR_BINDING_MANIFEST_GOVERNED_UNIT_DRIFT")
    wd=root/"STAGE_EXECUTION"/a.successor_stage/successor_uid
    if wd.exists(): raise SystemExit("BLOCK:SUCCESSOR_WORK_UNIT_PREEXISTS")

    inputs={}
    for row in handoff.get("successor_required_inputs") or []:
        if isinstance(row,dict) and row.get("input_uid"): inputs[str(row["input_uid"])]=row
    if set(inputs)!=set(map(str,stage.get("inputs") or [])):
        raise SystemExit("BLOCK:SUCCESSOR_INPUT_BINDING_COVERAGE_DRIFT")

    scanner_dims=list(map(str,((sem.get("stages") or {}).get(a.successor_stage) or {}).get("scanner_dimensions") or []))
    scanner_owner=str(bindings.get("scanner_owner") or "")
    scanner_protocol=str(bindings.get("scanner_protocol") or "")
    if not scanner_owner: raise SystemExit("BLOCK:SUCCESSOR_SCANNER_OWNER_MISSING")
    if not scanner_protocol: raise SystemExit("BLOCK:SUCCESSOR_SCANNER_PROTOCOL_MISSING")
    sp=safe(root,scanner_owner,"SUCCESSOR_SCANNER_OWNER")
    if not sp.is_file(): raise SystemExit("BLOCK:SUCCESSOR_SCANNER_OWNER_NOT_FOUND")

    matrix=bindings.get("normative_execution_matrix")
    if not isinstance(matrix,dict): raise SystemExit("BLOCK:SUCCESSOR_NORMATIVE_EXECUTION_MATRIX_PAYLOAD_MISSING")
    if matrix.get("artifact_type")!="NORMATIVE_EXECUTION_MATRIX" or matrix.get("status")!="PASS":
        raise SystemExit("BLOCK:SUCCESSOR_NORMATIVE_EXECUTION_MATRIX_INVALID")
    for key,val in (("stage_uid",a.successor_stage),("work_unit_uid",successor_uid),("governed_unit_uid",governed)):
        if str(matrix.get(key) or "")!=str(val): raise SystemExit("BLOCK:SUCCESSOR_NORMATIVE_EXECUTION_MATRIX_IDENTITY_DRIFT:"+key)
    rows=matrix.get("rows") or []
    if not isinstance(rows,list) or not rows: raise SystemExit("BLOCK:SUCCESSOR_NORMATIVE_EXECUTION_MATRIX_ROWS_EMPTY")

    validators=list(map(str,stage.get("validators") or []))
    validator_bindings=bindings.get("validator_bindings") or {}
    if set(map(str,validator_bindings))!=set(validators):
        raise SystemExit("BLOCK:SUCCESSOR_VALIDATOR_BINDING_COVERAGE_DRIFT")

    gov_uid=str(pred.get("governance_uid") or "")
    scope_uid=str(pred.get("scope_uid") or governed)
    matrix_rel=f"STAGE_EXECUTION/{a.successor_stage}/{successor_uid}/NORMATIVE_EXECUTION_MATRIX.yaml"
    work={
      "artifact_type":"WORK_UNIT","work_unit_uid":successor_uid,"stage_uid":a.successor_stage,
      "governed_unit_uid":governed,"scope_uid":scope_uid,"primary_task_layer":"PRODUCT_STAGE_EXECUTION",
      "governance_uid":gov_uid,"governance_execution_mode":"CURRENT_VALIDATED_GOVERNANCE",
      "work_unit_activation_kind":"SUCCESSOR_REENTRY_WORK_UNIT",
      "predecessor_work_unit_uid":pred.get("work_unit_uid"),
      "predecessor_work_unit_ref":str(pred_wp.relative_to(root)),
      "predecessor_terminal_receipt_ref":str(receipt.relative_to(root)),
      "reentry_authority_ref":reentry_authority_ref,
      "predecessor_artifact_index_ref":str(handoff.get("lifecycle_artifact_index_ref") or ""),
      "pre_execution_gate_status":"PENDING_RUNTIME_INLINE_VALIDATION","current_status":"READY_FOR_EXECUTION",
      "required_outputs":stage.get("outputs") or [],"input_bindings":inputs,"operation_bindings":ops,
      "scanner_bindings":{s:{"scanner_owner":scanner_owner,"scanner_protocol":scanner_protocol,"result_owner":"OWNER-"+a.successor_stage+"-SCANNER-"+s,"result_ref":f"STAGE_EXECUTION/{a.successor_stage}/{successor_uid}/EVIDENCE/SCANNER_RESULTS/{s}.yaml"} for s in scanner_dims},
      "validator_bindings":validator_bindings,
      "normative_execution_matrix_ref":matrix_rel,"completion_credit":0,
    }
    wd.mkdir(parents=True)
    write(wd/"NORMATIVE_EXECUTION_MATRIX.yaml",matrix)
    write(wd/"WORK_UNIT.yaml",work)
    write(wd/"CURRENT_EXECUTION_SCOPE_MANIFEST.yaml",{
      "artifact_type":"EXECUTION_SCOPE_MANIFEST","scope_uid":scope_uid,"scope_kind":"CURRENT_GOVERNED_UNIT_SUCCESSOR",
      "stage_uid":a.successor_stage,"work_unit_uid":successor_uid,"governed_unit_uid":governed,"governance_uid":gov_uid,
      "included_governed_units":[governed],"excluded_governed_units":[],"remaining_governed_units":[governed],
      "partial_scope":False,"product_stage_execution_allowed":True,"stage_exit_credit_allowed":False,"status":"READY_FOR_EXECUTION"})
    write(wd/"EXECUTION_STATE.yaml",{
      "artifact_type":"WORK_UNIT_EXECUTION_STATE","stage_uid":a.successor_stage,"work_unit_uid":successor_uid,
      "governed_unit_uid":governed,"governance_uid":gov_uid,"status":"READY_FOR_EXECUTION",
      "current_operation":expected[0],"completed_operations":[],"resume_control":{"product_execution_allowed":True},
      "predecessor_work_unit_uid":pred.get("work_unit_uid"),
      "next_action":"RUN_CURRENT_GOVERNANCE_LOAD_AND_STAGE_ADMISSION","resume_status":"CURRENT","completion_credit":0})
    write(wd/"SUCCESSOR_WORK_UNIT_MATERIALIZATION_RECEIPT.yaml",{
      "artifact_type":"SUCCESSOR_WORK_UNIT_MATERIALIZATION_RECEIPT","stage_uid":a.successor_stage,
      "work_unit_uid":successor_uid,"governed_unit_uid":governed,
      "predecessor_terminal_receipt_ref":str(receipt.relative_to(root)),
      "operation_binding_manifest_ref":a.operation_binding_manifest,
      "normative_execution_matrix_ref":matrix_rel,"status":"MATERIALIZED_PENDING_ADMISSION","completion_credit":0})
    print("PASS: successor Work Unit matrix/scope/state/bindings materialized; EXECUTION_STATE is resume truth",successor_uid)

if __name__=="__main__":
    main()
