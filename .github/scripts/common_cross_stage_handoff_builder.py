#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib
from pathlib import Path
import yaml

LIFECYCLE=Path(".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml")
INVARIANTS=Path(".github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml")

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0:
        raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict):
        raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d

def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(o,sort_keys=False,allow_unicode=True),encoding="utf-8")

def sha256(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def safe(root,rel,label):
    rp=Path(str(rel or ""))
    if not str(rp) or rp.is_absolute() or ".." in rp.parts:
        raise SystemExit("BLOCK:"+label+"_REF_INVALID:"+str(rel))
    p=(root/rp).resolve()
    try: p.relative_to(root)
    except ValueError: raise SystemExit("BLOCK:"+label+"_REF_ESCAPES_ROOT:"+str(rel))
    return p

def merge_artifacts(root,work_dir,matrix,work):
    merged={}
    pref=str(work.get("predecessor_artifact_index_ref") or "")
    if pref:
        idx=load(safe(root,pref,"PREDECESSOR_ARTIFACT_INDEX"))
        for row in idx.get("artifacts") or []:
            if isinstance(row,dict) and row.get("artifact_uid"):
                merged.setdefault(str(row["artifact_uid"]),[]).append(dict(row))
    for row in matrix.get("rows") or []:
        if not isinstance(row,dict) or str(row.get("applicability") or "REQUIRED")!="REQUIRED":
            continue
        uid=str(row.get("required_artifact_type") or "")
        ref=str(row.get("artifact_ref") or "")
        if not uid or not ref: continue
        p=safe(root,ref,"CURRENT_ARTIFACT")
        if not p.is_file() or p.stat().st_size<=0:
            raise SystemExit("BLOCK:CURRENT_ARTIFACT_NOT_MATERIALIZED:"+uid+":"+ref)
        item={"artifact_ref":ref,"sha256":sha256(p),"source_stage_uid":str(work.get("stage_uid") or "")}
        bucket=merged.setdefault(uid,[])
        if not any(str(x.get("artifact_ref") or "")==ref for x in bucket):
            bucket.append(item)
    return merged

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage",required=True)
    ap.add_argument("--work-unit",required=True)
    ap.add_argument("--product-root",required=True)
    ap.add_argument("--governance-root",required=True)
    a=ap.parse_args()
    root=Path(a.product_root).resolve(); gov=Path(a.governance_root).resolve()
    life=load(gov/LIFECYCLE); inv=load(gov/INVARIANTS)
    stages={str(x.get("stage_uid")):x for x in life.get("stages") or [] if isinstance(x,dict)}
    if a.stage not in stages: raise SystemExit("BLOCK:HANDOFF_STAGE_UNREGISTERED")
    wp=safe(root,a.work_unit,"WORK_UNIT"); wd=wp.parent; work=load(wp)
    if str(work.get("stage_uid") or "")!=a.stage: raise SystemExit("BLOCK:HANDOFF_WORK_UNIT_STAGE_DRIFT")
    state=load(wd/"EXECUTION_STATE.yaml")
    if str(state.get("current_operation") or "")!="COMPLETE":
        raise SystemExit("BLOCK:HANDOFF_OPERATIONS_NOT_COMPLETE")
    mref=str(work.get("normative_execution_matrix_ref") or "")
    matrix=load(safe(root,mref,"NORMATIVE_EXECUTION_MATRIX"))
    if matrix.get("status")!="PASS": raise SystemExit("BLOCK:HANDOFF_MATRIX_NOT_PASS")
    merged=merge_artifacts(root,wd,matrix,work)
    stage=stages[a.stage]; successor_uid=str(stage.get("next_stage_uid") or "")
    index_rel=f"STAGE_EXECUTION/{a.stage}/{wd.name}/EVIDENCE/LIFECYCLE_ARTIFACT_INDEX.yaml"
    artifacts=[]
    for uid,rows in merged.items():
        for row in rows: artifacts.append({"artifact_uid":uid,**row})
    write(root/index_rel,{"artifact_type":"LIFECYCLE_ARTIFACT_INDEX","stage_uid":a.stage,"work_unit_uid":work.get("work_unit_uid"),"governed_unit_uid":work.get("governed_unit_uid"),"artifacts":artifacts,"status":"CURRENT_CLOSURE_CANDIDATE","completion_credit":0})

    inputs=[]
    if successor_uid in stages:
        for uid in map(str,stages[successor_uid].get("inputs") or []):
            candidates=merged.get(uid) or []
            if len(candidates)!=1:
                raise SystemExit("BLOCK:SUCCESSOR_INPUT_ARTIFACT_RESOLUTION_NOT_EXACT:"+successor_uid+":"+uid+":"+str(len(candidates)))
            item=candidates[0]
            aref=str(item["artifact_ref"]); ap=safe(root,aref,"SUCCESSOR_INPUT")
            readiness_rel=f"STAGE_EXECUTION/{a.stage}/{wd.name}/EVIDENCE/SUCCESSOR_INPUT_READINESS/{uid}.yaml"
            write(root/readiness_rel,{"artifact_type":"SUCCESSOR_INPUT_READINESS_EVIDENCE","stage_uid":a.stage,"successor_stage_uid":successor_uid,"input_uid":uid,"artifact_ref":aref,"content_sha256":sha256(ap),"result":"PASS"})
            inputs.append({"input_uid":uid,"status":"MATERIALIZED","artifact_ref":aref,"content_sha256":sha256(ap),"external_evidence_ref":None,"authority_evidence_ref":None,"consumer_readiness_evidence_ref":readiness_rel})

    policy=((inv.get("invariants") or {}).get("CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS") or {})
    reqs=(policy.get("successor_execution_binding_requirements") or {})
    expected_classes=list(map(str,reqs.get(successor_uid) or [])) if successor_uid in stages else list(map(str,policy.get("next_governed_unit_successor_binding_requirements") or []))
    resolution_path=wd/"EVIDENCE/SUCCESSOR_EXECUTION_BINDING_RESOLUTION.yaml"
    if not resolution_path.is_file():
        raise SystemExit("BLOCK:SUCCESSOR_EXECUTION_BINDING_RESOLUTION_MISSING:"+successor_uid)
    resolution=load(resolution_path)
    rows=resolution.get("successor_execution_bindings") or []
    seen={str(x.get("binding_class") or ""):x for x in rows if isinstance(x,dict)}
    if set(seen)!=set(expected_classes):
        raise SystemExit("BLOCK:SUCCESSOR_EXECUTION_BINDING_DENOMINATOR_DRIFT:"+successor_uid)
    ready=0
    unresolved=0
    for cls in expected_classes:
        row=seen[cls]
        app=str(row.get("applicability") or "")
        rs=str(row.get("resolution_status") or "")
        if app=="REQUIRED" and rs=="BOUND": ready+=1
        elif app=="AUTHORIZED_NOT_APPLICABLE" and rs=="AUTHORIZED_NOT_APPLICABLE": ready+=1
        else: unresolved+=1
    if unresolved:
        raise SystemExit("BLOCK:SUCCESSOR_EXECUTION_BINDING_UNRESOLVED:"+successor_uid+":"+str(unresolved))

    ledger_rel=f"STAGE_EXECUTION/{a.stage}/{wd.name}/EVIDENCE/CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml"
    ledger={
      "artifact_type":"CROSS_STAGE_HANDOFF_READINESS_LEDGER",
      "stage_uid":a.stage,
      "predecessor_work_unit_uid":work.get("work_unit_uid"),
      "successor_stage_uid":successor_uid,
      "lifecycle_artifact_index_ref":index_rel,
      "current_matrix_valid":True,
      "current_state_consistent":True,
      "denominator_reconciled":True,
      "reference_resolution_complete":True,
      "physical_materialization_complete":True,
      "required_field_completeness_complete":True,
      "consumer_readiness_complete":True,
      "successor_required_inputs":inputs,
      "successor_execution_bindings":[seen[x] for x in expected_classes],
      "successor_execution_binding_total":len(expected_classes),
      "successor_execution_binding_ready_total":ready,
      "successor_execution_binding_unresolved_total":0,
      "unresolved_required_dependency_total":0,
      "status":"PASS",
      "completion_credit":0,
    }
    for k,v in resolution.items():
        if k.endswith("_resolution_receipts") or k in {"target_resolution_receipts","current_execution_context"}:
            ledger[k]=v
    write(root/ledger_rel,ledger)
    print("PASS: exact cross-stage handoff ledger materialized",a.stage,"->",successor_uid)

if __name__=="__main__":
    main()
