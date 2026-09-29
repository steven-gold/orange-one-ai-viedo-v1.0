#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, re
from pathlib import Path
import yaml

LIFECYCLE=".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml"
INVARIANTS=".github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml"
SOURCE_ROOT="STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/EXACT_OPERATION_BINDING_SOURCES"

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d
def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(o,sort_keys=False,allow_unicode=True),encoding="utf-8")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def successor_uid(predecessor_uid, successor_stage):
    m=re.fullmatch(r"WU-STAGE\\d{2}-(.+)",str(predecessor_uid or ""))
    if not m: raise SystemExit("BLOCK:PREDECESSOR_WORK_UNIT_UID_PATTERN_INVALID")
    return "WU-"+successor_stage.replace("-","")+"-"+m.group(1)

def render(obj, mapping):
    if isinstance(obj,str):
        for k,v in mapping.items(): obj=obj.replace("{{"+k+"}}",str(v))
        return obj
    if isinstance(obj,list): return [render(x,mapping) for x in obj]
    if isinstance(obj,dict): return {str(k):render(v,mapping) for k,v in obj.items()}
    return obj

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=["validate-contract","resolve"],default="validate-contract")
    ap.add_argument("--from-stage"); ap.add_argument("--predecessor-work-unit")
    ap.add_argument("--product-root",required=True); ap.add_argument("--governance-root",required=True)
    a=ap.parse_args(); root=Path(a.product_root).resolve(); gov=Path(a.governance_root).resolve()
    life=load(gov/LIFECYCLE); stages={str(x.get("stage_uid")):x for x in life.get("stages") or []}
    inv=load(gov/INVARIANTS); policy=((inv.get("invariants") or {}).get("CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS") or {})
    if list(stages)!=[f"STAGE-{i:02d}" for i in range(1,12)]: raise SystemExit("BLOCK:BINDING_RESOLVER_LIFECYCLE_ORDER_DRIFT")
    if a.mode=="validate-contract":
        reqs=policy.get("successor_execution_binding_requirements") or {}
        if set(map(str,reqs))!=set([f"STAGE-{i:02d}" for i in range(2,12)]): raise SystemExit("BLOCK:SUCCESSOR_EXECUTION_BINDING_REQUIREMENT_COVERAGE_DRIFT")
        if not policy.get("next_governed_unit_successor_binding_requirements"): raise SystemExit("BLOCK:NEXT_GOVERNED_UNIT_BINDING_REQUIREMENTS_EMPTY")
        print("PASS: successor binding resolver uses exact governance binding-class denominators"); return
    if not a.from_stage or not a.predecessor_work_unit: raise SystemExit("BLOCK:BINDING_RESOLVER_REQUIRED_ARGUMENT_MISSING")
    if a.from_stage not in stages: raise SystemExit("BLOCK:BINDING_RESOLVER_STAGE_UNREGISTERED")
    wp=root/Path(a.predecessor_work_unit); work=load(wp); wd=wp.parent
    if str(work.get("stage_uid"))!=a.from_stage: raise SystemExit("BLOCK:BINDING_RESOLVER_PREDECESSOR_STAGE_DRIFT")
    nxt=str(stages[a.from_stage].get("next_stage_uid") or "")
    out=wd/"EVIDENCE/SUCCESSOR_EXECUTION_BINDING_RESOLUTION.yaml"
    reqs=policy.get("successor_execution_binding_requirements") or {}
    expected_classes=list(map(str,reqs.get(nxt) or [])) if nxt in stages else list(map(str,policy.get("next_governed_unit_successor_binding_requirements") or []))
    if nxt in stages:
        src=root/SOURCE_ROOT/f"{nxt}.yaml"
    else:
        src=root/SOURCE_ROOT/"NEXT_GOVERNED_UNIT_STAGE05_OR_SCOPE_COMPLETE.yaml"
    if not src.is_file():
        write(out,{"artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION","predecessor_stage_uid":a.from_stage,"successor_stage_uid":nxt,"successor_execution_bindings":[],"ready_total":0,"unresolved_total":len(expected_classes),"status":"BLOCKED_EXACT_BINDING_SOURCE_MISSING","required_binding_source_ref":str(src.relative_to(root))})
        raise SystemExit("BLOCK:SUCCESSOR_EXACT_BINDING_SOURCE_MISSING:"+nxt)
    source=load(src)
    if str(source.get("stage_uid") or source.get("transition_uid") or "")!=nxt or source.get("status")!="CURRENT_EXACT_BINDINGS":
        raise SystemExit("BLOCK:SUCCESSOR_BINDING_SOURCE_NOT_CURRENT:"+nxt)
    exec_rows=source.get("successor_execution_bindings") or {}
    if set(map(str,exec_rows))!=set(expected_classes): raise SystemExit("BLOCK:SUCCESSOR_EXECUTION_BINDING_SOURCE_DENOMINATOR_DRIFT:"+nxt)
    resolved=[]
    for cls in expected_classes:
        row=exec_rows.get(cls) or {}; app=str(row.get("applicability") or ""); rs=str(row.get("resolution_status") or "")
        if app=="REQUIRED" and rs!="BOUND": raise SystemExit("BLOCK:SUCCESSOR_REQUIRED_BINDING_UNRESOLVED:"+nxt+":"+cls)
        if app=="AUTHORIZED_NOT_APPLICABLE" and (rs!="AUTHORIZED_NOT_APPLICABLE" or not row.get("authority_evidence_ref")): raise SystemExit("BLOCK:SUCCESSOR_NA_BINDING_EVIDENCE_INVALID:"+nxt+":"+cls)
        if app not in {"REQUIRED","AUTHORIZED_NOT_APPLICABLE"}: raise SystemExit("BLOCK:SUCCESSOR_BINDING_APPLICABILITY_INVALID:"+nxt+":"+cls)
        resolved.append(dict(row,binding_class=cls))
    if nxt not in stages:
        write(out,{"artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION","predecessor_stage_uid":a.from_stage,"successor_stage_uid":nxt,"successor_execution_bindings":resolved,"ready_total":len(resolved),"unresolved_total":0,"status":"PASS"})
        print("PASS: exact next-governed-unit/scope transition bindings resolved"); return
    governed=str(work.get("governed_unit_uid") or "")
    suid=successor_uid(work.get("work_unit_uid"),nxt)
    mapping={"WORK_UNIT_UID":suid,"GOVERNED_UNIT_UID":governed,"STAGE_UID":nxt}
    ops=list(map(str,stages[nxt].get("operations") or [])); rows=source.get("operation_bindings") or {}
    if set(map(str,rows))!=set(ops): raise SystemExit("BLOCK:SUCCESSOR_OPERATION_BINDING_SOURCE_COVERAGE_DRIFT:"+nxt)
    manifest_ops={}
    for op in ops:
        b=render(rows.get(op) or {},mapping); owner=str(b.get("executor_owner") or "")
        if not owner or not (root/owner).is_file(): raise SystemExit("BLOCK:SUCCESSOR_EXECUTOR_OWNER_NOT_PHYSICAL:"+nxt+":"+op+":"+owner)
        result_owner=str(b.get("result_owner") or "")
        if not result_owner: raise SystemExit("BLOCK:SUCCESSOR_RESULT_OWNER_MISSING:"+nxt+":"+op)
        manifest_ops[op]={"applicability":str(b.get("applicability") or "REQUIRED"),"executor_owner":owner,"executor_protocol":str(b.get("executor_protocol") or "PYTHON_STAGE_OPERATION_V1"),"result_owner":result_owner,"operation_receipt_ref":f"STAGE_EXECUTION/{nxt}/{suid}/EVIDENCE/OPERATION_RECEIPTS/{op}.yaml"}
    scanner_owner=str(source.get("scanner_owner") or "")
    if not scanner_owner or not (root/scanner_owner).is_file(): raise SystemExit("BLOCK:SUCCESSOR_SCANNER_OWNER_UNRESOLVED:"+nxt)
    vals=list(map(str,stages[nxt].get("validators") or [])); vb=render(source.get("validator_bindings") or {},mapping)
    if set(map(str,vb))!=set(vals): raise SystemExit("BLOCK:SUCCESSOR_VALIDATOR_BINDING_COVERAGE_DRIFT:"+nxt)
    matrix=render(source.get("normative_execution_matrix_template") or {},mapping)
    if not isinstance(matrix,dict) or matrix.get("artifact_type")!="NORMATIVE_EXECUTION_MATRIX" or matrix.get("status")!="PASS":
        raise SystemExit("BLOCK:SUCCESSOR_NORMATIVE_EXECUTION_MATRIX_TEMPLATE_INVALID:"+nxt)
    for key,val in (("stage_uid",nxt),("work_unit_uid",suid),("governed_unit_uid",governed)):
        if str(matrix.get(key) or "")!=str(val): raise SystemExit("BLOCK:SUCCESSOR_RENDERED_MATRIX_IDENTITY_DRIFT:"+key)
    auth_ref="STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/FULL_STAGE_LIFECYCLE_AUTHORIZATION_CONTRACT.yaml"
    if not (root/auth_ref).is_file(): raise SystemExit("BLOCK:SUCCESSOR_REENTRY_AUTHORITY_REF_MISSING")
    manifest={"artifact_type":"SUCCESSOR_EXACT_OPERATION_BINDING_MANIFEST","status":"PASS","stage_uid":nxt,"work_unit_uid":suid,"governed_unit_uid":governed,"reentry_authority_ref":auth_ref,"operation_bindings":manifest_ops,"scanner_owner":scanner_owner,"scanner_protocol":str(source.get("scanner_protocol") or ""),"validator_bindings":vb,"normative_execution_matrix":matrix}
    if not manifest["scanner_protocol"]: raise SystemExit("BLOCK:SUCCESSOR_SCANNER_PROTOCOL_MISSING:"+nxt)
    mrel=f"STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/GENERATED_BINDINGS/{nxt}/{str(work.get('governed_unit_uid') or 'UNKNOWN').replace(':','_')}.yaml"
    write(root/mrel,manifest)
    write(out,{"artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION","predecessor_stage_uid":a.from_stage,"successor_stage_uid":nxt,"successor_execution_bindings":resolved,"ready_total":len(resolved),"unresolved_total":0,"status":"PASS","operation_binding_manifest_ref":mrel})
    print("PASS: exact successor operation and target bindings resolved",a.from_stage,"->",nxt)
if __name__=="__main__": main()
