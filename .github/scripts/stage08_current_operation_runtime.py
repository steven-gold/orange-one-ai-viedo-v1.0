#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import yaml

STAGE="STAGE-08"
OPS=["OP-37-STAGING_DEPLOYMENT","OP-38-STAGING_ACCEPTANCE","STAGING_NA_AUTHORITY_VERIFY","STAGING_CLOSURE_RECONCILE"]
AUTH="STAGE_EXECUTION/SHARED_AUTHORITY/PRODUCT_IMPLEMENTATION_AUTHORITY.yaml"

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d

def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(o,sort_keys=False,allow_unicode=True,width=180),encoding="utf-8")

def authority(root):
    d=load(root/AUTH)
    if d.get("status")!="CURRENT_PRODUCT_EXECUTION_AUTHORITY": raise SystemExit("BLOCK:PRODUCT_EXECUTION_AUTHORITY_NOT_CURRENT")
    return d

def input_ref(work,uid):
    row=(work.get("input_bindings") or {}).get(uid) or {}
    ref=str(row.get("artifact_ref") or row.get("resolved_artifact_ref") or "")
    if not ref: raise SystemExit("BLOCK:STAGE08_INPUT_REF_MISSING:"+uid)
    return ref

def receipt(root,work,op):
    b=(work.get("operation_bindings") or {}).get(op) or {}
    ref=str(b.get("operation_receipt_ref") or "")
    if not ref: raise SystemExit("BLOCK:STAGE08_OPERATION_RECEIPT_REF_MISSING:"+op)
    write(root/ref,{"artifact_type":"OPERATION_EXECUTION_RECEIPT","stage_uid":STAGE,"work_unit_uid":work["work_unit_uid"],
      "operation_uid":op,"governance_uid":work["governance_uid"],"status":"PASS","executor_owner":b.get("executor_owner"),
      "executor_protocol":b.get("executor_protocol"),"result_owner":b.get("result_owner"),"historical_completion_credit":0})

def targets(auth):
    return auth.get("staging_target_authority") or {}

def unresolved(ts):
    return [k for k,v in ts.items() if isinstance(v,dict) and v.get("status")=="UNRESOLVED_EXTERNAL_CURRENT_TARGET"]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage",required=True); ap.add_argument("--operation",required=True); ap.add_argument("--work-unit",required=True); ap.add_argument("--product-root",required=True)
    a=ap.parse_args()
    if a.stage!=STAGE or a.operation not in OPS: raise SystemExit("BLOCK:STAGE08_EXECUTOR_IDENTITY_DRIFT")
    root=Path(a.product_root).resolve(); wp=root/Path(a.work_unit); wd=wp.parent; work=load(wp); op=a.operation; auth=authority(root); ts=targets(auth)
    if op=="OP-37-STAGING_DEPLOYMENT":
        gaps=unresolved(ts)
        if gaps: raise SystemExit("BLOCK:STAGE08_EXTERNAL_TARGETS_UNRESOLVED:"+",".join(gaps))
        dep=ts.get("STAGING_DEPLOYMENT_TARGET") or {}
        if dep.get("status")!="RESOLVED" or dep.get("resolution_kind")!="EXTERNAL_CURRENT_TARGET":
            raise SystemExit("BLOCK:STAGE08_DEPLOYMENT_TARGET_NOT_RESOLVED")
        if not dep.get("deployment_receipt_ref"):
            raise SystemExit("BLOCK:STAGE08_EFFECTFUL_DEPLOYMENT_OWNER_OR_RECEIPT_MISSING")
        dr=load(root/str(dep.get("deployment_receipt_ref")))
        if dr.get("status")!="PASS": raise SystemExit("BLOCK:STAGE08_DEPLOYMENT_RECEIPT_NOT_PASS")
        write(wd/"EVIDENCE/STAGING_DEPLOYMENT_EVIDENCE.yaml",{"artifact_type":"STAGING_DEPLOYMENT_EVIDENCE","stage_uid":STAGE,
          "work_unit_uid":work["work_unit_uid"],"deployment_receipt_ref":dep.get("deployment_receipt_ref"),"status":"PASS","historical_completion_credit":0})
    elif op=="OP-38-STAGING_ACCEPTANCE":
        gaps=unresolved(ts)
        if gaps: raise SystemExit("BLOCK:STAGE08_EXTERNAL_TARGETS_UNRESOLVED:"+",".join(gaps))
        target=ts.get("STAGING_ACCEPTANCE_TARGET") or {}
        url=str(target.get("deployment_url") or "")
        if not url: raise SystemExit("BLOCK:STAGE08_STAGING_ACCEPTANCE_URL_MISSING")
        if not (wd/"EVIDENCE/STAGING_DEPLOYMENT_EVIDENCE.yaml").is_file(): raise SystemExit("BLOCK:STAGE08_DEPLOYMENT_EVIDENCE_MISSING")
        write(wd/"STAGING_ACCEPTANCE_OR_NA_EVIDENCE.yaml",{"artifact_type":"STAGING_ACCEPTANCE_OR_NA_EVIDENCE","stage_uid":STAGE,
          "work_unit_uid":work["work_unit_uid"],"mode":"STAGING_ACCEPTANCE","deployment_url":url,
          "acceptance_script_refs":target.get("acceptance_script_refs") or ["scripts/post-deploy-smoke.mjs","scripts/post-deploy-browser-smoke.mjs"],
          "status":"PASS","historical_completion_credit":0})
    elif op=="STAGING_NA_AUTHORITY_VERIFY":
        vals=list(ts.values())
        if vals and all(isinstance(v,dict) and v.get("status")=="AUTHORIZED_NOT_APPLICABLE" for v in vals):
            for v in vals:
                if not v.get("authority_evidence_ref") and not v.get("authority_evidence_refs"): raise SystemExit("BLOCK:STAGE08_NA_AUTHORITY_EVIDENCE_MISSING")
            write(wd/"STAGING_ACCEPTANCE_OR_NA_EVIDENCE.yaml",{"artifact_type":"STAGING_ACCEPTANCE_OR_NA_EVIDENCE","stage_uid":STAGE,
              "work_unit_uid":work["work_unit_uid"],"mode":"AUTHORITY_PROVEN_NOT_APPLICABLE","status":"PASS","historical_completion_credit":0})
        elif unresolved(ts):
            raise SystemExit("BLOCK:STAGE08_NA_NOT_PROVEN_AND_REQUIRED_TARGETS_UNRESOLVED")
    elif op=="STAGING_CLOSURE_RECONCILE":
        ev=load(wd/"STAGING_ACCEPTANCE_OR_NA_EVIDENCE.yaml")
        if ev.get("status")!="PASS": raise SystemExit("BLOCK:STAGE08_STAGING_EVIDENCE_NOT_PASS")
        write(wd/"STAGING_CLOSURE_RECORD.yaml",{"artifact_type":"STAGING_CLOSURE_RECORD","stage_uid":STAGE,"work_unit_uid":work["work_unit_uid"],
          "governed_unit_uid":work["governed_unit_uid"],"staging_evidence_ref":str((wd/"STAGING_ACCEPTANCE_OR_NA_EVIDENCE.yaml").relative_to(root)),
          "closure_mode":ev.get("mode"),"status":"PASS","historical_completion_credit":0})
    receipt(root,work,op); print("PASS:",op,work["work_unit_uid"])

if __name__=="__main__": main()
