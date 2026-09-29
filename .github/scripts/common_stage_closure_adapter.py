#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import yaml

LIFECYCLE=Path(".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml")

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0:
        raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict):
        raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d

def sha256(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def write_yaml(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(obj,sort_keys=False,allow_unicode=True),encoding="utf-8")

def safe(root,rel,label):
    rp=Path(str(rel or ""))
    if not str(rp) or rp.is_absolute() or ".." in rp.parts:
        raise SystemExit("BLOCK:"+label+"_REF_INVALID:"+str(rel))
    p=(root/rp).resolve()
    try: p.relative_to(root)
    except ValueError: raise SystemExit("BLOCK:"+label+"_REF_ESCAPES_ROOT:"+str(rel))
    return p

def stage_map(gov):
    reg=load(gov/LIFECYCLE)
    rows=reg.get("stages") or []
    return {str(x.get("stage_uid")):x for x in rows if isinstance(x,dict)}

def validate_contract(gov):
    stages=stage_map(gov)
    expected=[f"STAGE-{i:02d}" for i in range(1,12)]
    if list(stages)!=expected:
        raise SystemExit("BLOCK:CLOSURE_ADAPTER_LIFECYCLE_ORDER_DRIFT")
    for uid,row in stages.items():
        if not row.get("operations") or not row.get("outputs") or not row.get("required_evidence"):
            raise SystemExit("BLOCK:CLOSURE_ADAPTER_STAGE_DENOMINATOR_EMPTY:"+uid)
        if not row.get("exit_gate") or not row.get("next_stage_uid"):
            raise SystemExit("BLOCK:CLOSURE_ADAPTER_STAGE_TRANSITION_MISSING:"+uid)
    print("PASS: common closure adapter contract covers Stage-01..11")

def matrix_artifacts(root,wd,matrix,required):
    rows=matrix.get("rows") or []
    out={}
    for art in required:
        refs=[]
        for row in rows:
            if isinstance(row,dict) and str(row.get("required_artifact_type") or "")==art and str(row.get("applicability") or "REQUIRED")=="REQUIRED":
                ref=str(row.get("artifact_ref") or "")
                if ref and ref not in refs: refs.append(ref)
        if not refs:
            raise SystemExit("BLOCK:CLOSURE_REQUIRED_ARTIFACT_MATRIX_REF_MISSING:"+art)
        phys=[]
        for ref in refs:
            p=safe(root,ref,"CLOSURE_ARTIFACT")
            if not p.is_file() or p.stat().st_size<=0:
                raise SystemExit("BLOCK:CLOSURE_REQUIRED_ARTIFACT_NOT_MATERIALIZED:"+art+":"+ref)
            phys.append({"artifact_ref":ref,"sha256":sha256(p)})
        out[art]=phys
    return out

def predecessor_index(root,work):
    ref=str(work.get("predecessor_artifact_index_ref") or "")
    if not ref:
        return {}
    p=safe(root,ref,"PREDECESSOR_ARTIFACT_INDEX")
    idx=load(p)
    result={}
    for row in idx.get("artifacts") or []:
        if not isinstance(row,dict): continue
        uid=str(row.get("artifact_uid") or "")
        if uid: result.setdefault(uid,[]).append(row)
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=["validate-contract","candidate"],default="validate-contract")
    ap.add_argument("--stage")
    ap.add_argument("--work-unit")
    ap.add_argument("--product-root",required=True)
    ap.add_argument("--governance-root",required=True)
    a=ap.parse_args()
    root=Path(a.product_root).resolve(); gov=Path(a.governance_root).resolve()
    validate_contract(gov)
    if a.mode=="validate-contract": return
    if not a.stage or not a.work_unit:
        raise SystemExit("BLOCK:CLOSURE_ADAPTER_STAGE_AND_WORK_UNIT_REQUIRED")
    stages=stage_map(gov)
    if a.stage not in stages: raise SystemExit("BLOCK:CLOSURE_ADAPTER_STAGE_UNREGISTERED")
    wp=safe(root,a.work_unit,"WORK_UNIT"); wd=wp.parent
    work=load(wp)
    if str(work.get("stage_uid") or "")!=a.stage:
        raise SystemExit("BLOCK:CLOSURE_ADAPTER_WORK_UNIT_STAGE_DRIFT")
    matrix_ref=str(work.get("normative_execution_matrix_ref") or "")
    matrix=load(safe(root,matrix_ref,"NORMATIVE_MATRIX"))
    stage=stages[a.stage]
    required=list(map(str,stage.get("outputs") or []))+list(map(str,stage.get("required_evidence") or []))
    current=matrix_artifacts(root,wd,matrix,required)
    merged=predecessor_index(root,work)
    for uid,refs in current.items():
        merged[uid]=[dict(x,source_stage_uid=a.stage) for x in refs]
    artifacts=[]
    for uid,refs in merged.items():
        for item in refs:
            artifacts.append({"artifact_uid":uid,**item})
    index_rel=f"STAGE_EXECUTION/{a.stage}/{wd.name}/EVIDENCE/LIFECYCLE_ARTIFACT_INDEX.yaml"
    index={
      "artifact_type":"LIFECYCLE_ARTIFACT_INDEX",
      "stage_uid":a.stage,
      "work_unit_uid":work.get("work_unit_uid"),
      "governed_unit_uid":work.get("governed_unit_uid"),
      "artifacts":artifacts,
      "status":"CURRENT_CLOSURE_CANDIDATE",
      "completion_credit":0,
    }
    write_yaml(root/index_rel,index)
    next_stage=str(stage.get("next_stage_uid") or "")
    handoff_rel=f"STAGE_EXECUTION/{a.stage}/{wd.name}/EVIDENCE/CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml"
    handoff={
      "artifact_type":"CROSS_STAGE_HANDOFF_READINESS_LEDGER",
      "predecessor_stage_uid":a.stage,
      "predecessor_work_unit_uid":work.get("work_unit_uid"),
      "successor_stage_uid":next_stage,
      "lifecycle_artifact_index_ref":index_rel,
      "status":"CANDIDATE_REQUIRES_COMMON_TERMINALIZATION",
      "completion_credit":0,
    }
    if next_stage.startswith("STAGE-") and next_stage in stages:
        successor=stages[next_stage]
        inputs=[]
        for uid in map(str,successor.get("inputs") or []):
            candidates=merged.get(uid) or []
            if len(candidates)!=1:
                raise SystemExit("BLOCK:SUCCESSOR_INPUT_ARTIFACT_RESOLUTION_NOT_EXACT:"+next_stage+":"+uid+":"+str(len(candidates)))
            item=candidates[0]
            inputs.append({"input_uid":uid,"artifact_ref":item["artifact_ref"],"sha256":item["sha256"],"status":"MATERIALIZED"})
        handoff["successor_input_bindings"]=inputs
        handoff["successor_operation_binding_policy"]="CURRENT_WORK_UNIT_OPERATION_BINDING_ONLY"
        handoff["successor_scanner_binding_policy"]="CURRENT_STAGE_SEMANTIC_ADAPTER_SCANNER_DIMENSIONS"
    write_yaml(root/handoff_rel,handoff)
    normalized={
      "artifact_type":"COMMON_NORMALIZED_STAGE_EVIDENCE_CANDIDATE",
      "stage_uid":a.stage,
      "work_unit_uid":work.get("work_unit_uid"),
      "governed_unit_uid":work.get("governed_unit_uid"),
      "exit_gate":stage.get("exit_gate"),
      "next_stage_uid":next_stage,
      "lifecycle_artifact_index_ref":index_rel,
      "cross_stage_handoff_ref":handoff_rel,
      "required_artifact_types":required,
      "status":"CANDIDATE_NOT_TERMINAL",
      "completion_credit":0,
    }
    (wd/"EVIDENCE").mkdir(parents=True,exist_ok=True)
    (wd/"EVIDENCE/COMMON_NORMALIZED_STAGE_EVIDENCE_CANDIDATE.json").write_text(json.dumps(normalized,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("PASS: common closure candidate materialized without terminal completion credit",a.stage,wd.name)

if __name__=="__main__":
    main()
