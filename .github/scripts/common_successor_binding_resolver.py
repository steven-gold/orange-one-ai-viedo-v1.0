#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib
from pathlib import Path
import yaml
LIFECYCLE=".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml"
SOURCE_ROOT="STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/EXACT_OPERATION_BINDING_SOURCES"
def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d
def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(yaml.safe_dump(o,sort_keys=False,allow_unicode=True),encoding="utf-8")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["validate-contract","resolve"],default="validate-contract"); ap.add_argument("--from-stage"); ap.add_argument("--predecessor-work-unit"); ap.add_argument("--product-root",required=True); ap.add_argument("--governance-root",required=True)
    a=ap.parse_args(); root=Path(a.product_root).resolve(); gov=Path(a.governance_root).resolve(); life=load(gov/LIFECYCLE); stages={str(x.get("stage_uid")):x for x in life.get("stages") or []}
    if list(stages)!=[f"STAGE-{i:02d}" for i in range(1,12)]: raise SystemExit("BLOCK:BINDING_RESOLVER_LIFECYCLE_ORDER_DRIFT")
    if a.mode=="validate-contract": print("PASS: successor binding resolver covers Stage-01..11 and terminal sentinel"); return
    if not a.from_stage or not a.predecessor_work_unit: raise SystemExit("BLOCK:BINDING_RESOLVER_REQUIRED_ARGUMENT_MISSING")
    wp=root/Path(a.predecessor_work_unit); work=load(wp); wd=wp.parent
    if str(work.get("stage_uid"))!=a.from_stage: raise SystemExit("BLOCK:BINDING_RESOLVER_PREDECESSOR_STAGE_DRIFT")
    nxt=str(stages[a.from_stage].get("next_stage_uid") or ""); out=wd/"EVIDENCE/SUCCESSOR_EXECUTION_BINDING_RESOLUTION.yaml"
    if nxt=="NEXT_GOVERNED_UNIT_STAGE05_OR_SCOPE_COMPLETE":
        write(out,{"artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION","predecessor_stage_uid":a.from_stage,"successor_stage_uid":nxt,"transition_kind":"NEXT_GOVERNED_UNIT_OR_SCOPE_COMPLETE","successor_execution_bindings":[],"ready_total":0,"unresolved_total":0,"status":"PASS"}); print("PASS: Stage11 terminal transition requires no registered successor executor"); return
    if nxt not in stages: raise SystemExit("BLOCK:SUCCESSOR_STAGE_NOT_REGISTERED:"+nxt)
    src=root/SOURCE_ROOT/f"{nxt}.yaml"; ops=list(map(str,stages[nxt].get("operations") or []))
    if not src.is_file():
        write(out,{"artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION","predecessor_stage_uid":a.from_stage,"successor_stage_uid":nxt,"successor_execution_bindings":[],"ready_total":0,"unresolved_total":len(ops),"status":"BLOCKED_EXACT_BINDING_SOURCE_MISSING","required_binding_source_ref":str(src.relative_to(root))}); raise SystemExit("BLOCK:SUCCESSOR_EXACT_OPERATION_BINDING_SOURCE_MISSING:"+nxt)
    source=load(src)
    if str(source.get("stage_uid") or "")!=nxt or source.get("status")!="CURRENT_EXACT_BINDINGS": raise SystemExit("BLOCK:SUCCESSOR_BINDING_SOURCE_NOT_CURRENT:"+nxt)
    rows=source.get("operation_bindings") or {}
    if set(map(str,rows))!=set(ops): raise SystemExit("BLOCK:SUCCESSOR_BINDING_SOURCE_OPERATION_COVERAGE_DRIFT:"+nxt)
    resolved=[]; manifest_ops={}
    for op in ops:
        b=rows.get(op) or {}; owner=str(b.get("executor_owner") or "")
        if not owner or not (root/owner).is_file(): raise SystemExit("BLOCK:SUCCESSOR_EXECUTOR_OWNER_NOT_PHYSICAL:"+nxt+":"+op+":"+owner)
        result_owner=str(b.get("result_owner") or "")
        if not result_owner: raise SystemExit("BLOCK:SUCCESSOR_RESULT_OWNER_MISSING:"+nxt+":"+op)
        resolved.append({"binding_class":"OPERATION:"+op,"status":"READY","target_ref":owner,"content_sha256":sha(root/owner)})
        manifest_ops[op]={"applicability":str(b.get("applicability") or "REQUIRED"),"executor_owner":owner,"executor_protocol":str(b.get("executor_protocol") or "PYTHON_STAGE_OPERATION_V1"),"result_owner":result_owner,"operation_receipt_ref":f"STAGE_EXECUTION/{nxt}/"+str(source.get("work_unit_uid"))+f"/EVIDENCE/OPERATION_RECEIPTS/{op}.yaml"}
    scanner_owner=str(source.get("scanner_owner") or "")
    if not scanner_owner or not (root/scanner_owner).is_file(): raise SystemExit("BLOCK:SUCCESSOR_SCANNER_OWNER_UNRESOLVED:"+nxt)
    vals=list(map(str,stages[nxt].get("validators") or [])); vb=source.get("validator_bindings") or {}
    if set(map(str,vb))!=set(vals): raise SystemExit("BLOCK:SUCCESSOR_VALIDATOR_BINDING_COVERAGE_DRIFT:"+nxt)
    manifest={"artifact_type":"SUCCESSOR_EXACT_OPERATION_BINDING_MANIFEST","status":"PASS","stage_uid":nxt,"work_unit_uid":source.get("work_unit_uid"),"governed_unit_uid":work.get("governed_unit_uid"),"operation_bindings":manifest_ops,"scanner_owner":scanner_owner,"scanner_protocol":source.get("scanner_protocol"),"validator_bindings":vb,"normative_execution_matrix":source.get("normative_execution_matrix")}
    if not manifest["work_unit_uid"] or not isinstance(manifest["normative_execution_matrix"],dict): raise SystemExit("BLOCK:SUCCESSOR_BINDING_SOURCE_MATRIX_OR_WU_MISSING:"+nxt)
    mrel=f"STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/GENERATED_BINDINGS/{nxt}/{str(work.get('governed_unit_uid') or 'UNKNOWN').replace(':','_')}.yaml"; write(root/mrel,manifest)
    write(out,{"artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION","predecessor_stage_uid":a.from_stage,"successor_stage_uid":nxt,"successor_execution_bindings":resolved,"ready_total":len(resolved),"unresolved_total":0,"status":"PASS","operation_binding_manifest_ref":mrel}); print("PASS: exact successor binding manifest resolved",a.from_stage,"->",nxt,mrel)
if __name__=="__main__": main()
