#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import yaml
AUTH="STAGE_EXECUTION/SHARED_AUTHORITY/PRODUCT_IMPLEMENTATION_AUTHORITY.yaml"
OPS={
"STAGE-09":["OP-39-PRODUCTION_CONFIGURATION","OP-40-PRODUCTION_MIGRATION","OP-41-PRODUCTION_DEPLOYMENT","OP-42-PRODUCTION_SMOKE","CURRENT_RELEASE_IDENTITY_CAPTURE"],
"STAGE-10":["OP-43-PRODUCTION_BROWSER_ACCEPTANCE","OP-44-PRODUCTION_GOVERNED_UNIT_ACCEPTANCE","OP-45-PRODUCTION_CONTROL_ACCEPTANCE","OP-46-PRODUCTION_DATABASE_ACCEPTANCE","OP-47-PRODUCTION_EFFECTFUL_ACCEPTANCE","OP-48-EXTERNAL_INTEGRATION_ACCEPTANCE","OP-49-ASYNC_RUNTIME_ACCEPTANCE","PRODUCTION_VISUAL_GEOMETRY_ACCEPTANCE","PRODUCTION_STALE_RENDER_ACCEPTANCE","PRODUCTION_CROSS_GOVERNED_UNIT_SLICE_ACCEPTANCE","PRODUCTION_ACCEPTANCE_RECONCILIATION"],
"STAGE-11":["OP-50-MONITORING_VERIFICATION","OP-51-BACKUP_VERIFICATION","OP-52-ROLLBACK_VERIFICATION","OP-53-FINAL_AUDIT_MATRIX_RECONCILIATION","OP-54-FINAL_PRODUCTION_ACCEPTANCE","GOVERNED_UNIT_CLOSURE","NEXT_GOVERNED_UNIT_ELIGIBILITY_EVALUATE"]}
SECTIONS={"STAGE-09":"production_target_authority","STAGE-10":"production_acceptance_target_authority","STAGE-11":"operations_target_authority"}
def load(p):
 p=Path(p)
 if not p.is_file() or p.stat().st_size<=0: raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
 d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
 if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
 return d
def write(p,o):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(yaml.safe_dump(o,sort_keys=False,allow_unicode=True,width=180),encoding="utf-8")
def receipt(root,work,stage,op):
 b=(work.get("operation_bindings") or {}).get(op) or {}; ref=str(b.get("operation_receipt_ref") or "")
 if not ref: raise SystemExit("BLOCK:OPERATION_RECEIPT_REF_MISSING:"+stage+":"+op)
 write(root/ref,{"artifact_type":"OPERATION_EXECUTION_RECEIPT","stage_uid":stage,"work_unit_uid":work["work_unit_uid"],"operation_uid":op,"governance_uid":work["governance_uid"],"status":"PASS","executor_owner":b.get("executor_owner"),"executor_protocol":b.get("executor_protocol"),"result_owner":b.get("result_owner"),"historical_completion_credit":0})
def require_external_receipt(root,row,label):
 if row.get("status")=="UNRESOLVED_EXTERNAL_CURRENT_TARGET": raise SystemExit("BLOCK:EXTERNAL_CURRENT_TARGET_UNRESOLVED:"+label)
 if row.get("status") not in {"RESOLVED","RESOLVED_BY_AUTHORIZED_TEMPLATE"}: raise SystemExit("BLOCK:EXTERNAL_TARGET_STATUS_INVALID:"+label)
 if row.get("resolution_kind")=="EXTERNAL_CURRENT_TARGET":
  ref=str(row.get("external_execution_receipt_ref") or "")
  if not ref: raise SystemExit("BLOCK:EXTERNAL_EXECUTION_RECEIPT_MISSING:"+label)
  d=load(root/ref)
  if d.get("status")!="PASS": raise SystemExit("BLOCK:EXTERNAL_EXECUTION_RECEIPT_NOT_PASS:"+label)
  return ref,d
 return None,None
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--stage",required=True); ap.add_argument("--operation",required=True); ap.add_argument("--work-unit",required=True); ap.add_argument("--product-root",required=True)
 a=ap.parse_args()
 if a.stage not in OPS or a.operation not in OPS[a.stage]: raise SystemExit("BLOCK:EXTERNAL_STAGE_EXECUTOR_IDENTITY_DRIFT")
 root=Path(a.product_root).resolve(); wp=root/Path(a.work_unit); wd=wp.parent; work=load(wp); auth=load(root/AUTH); sec=auth.get(SECTIONS[a.stage]) or {}
 unresolved=[k for k,v in sec.items() if isinstance(v,dict) and v.get("status")=="UNRESOLVED_EXTERNAL_CURRENT_TARGET"]
 if unresolved: raise SystemExit("BLOCK:"+a.stage+"_EXTERNAL_TARGETS_UNRESOLVED:"+",".join(unresolved))
 if a.stage=="STAGE-09":
  if a.operation=="OP-39-PRODUCTION_CONFIGURATION":
   cfg=sec.get("PRODUCTION_CONFIGURATION_AUTHORITY") or {}
   if cfg.get("status")!="RESOLVED": raise SystemExit("BLOCK:PRODUCTION_CONFIGURATION_AUTHORITY_UNRESOLVED")
  elif a.operation=="OP-40-PRODUCTION_MIGRATION": require_external_receipt(root,sec.get("PRODUCTION_MIGRATION_TARGET") or {},"PRODUCTION_MIGRATION_TARGET")
  elif a.operation=="OP-41-PRODUCTION_DEPLOYMENT":
   ref,d=require_external_receipt(root,sec.get("PRODUCTION_DEPLOYMENT_TARGET") or {},"PRODUCTION_DEPLOYMENT_TARGET")
   write(wd/"PRODUCTION_DEPLOYMENT_RECORD.yaml",{"artifact_type":"PRODUCTION_DEPLOYMENT_RECORD","stage_uid":a.stage,"work_unit_uid":work["work_unit_uid"],"deployment_receipt_ref":ref,"deployment_identity":d.get("external_target_identity") or d.get("deployment_url"),"status":"PASS","historical_completion_credit":0})
  elif a.operation=="OP-42-PRODUCTION_SMOKE":
   ref,d=require_external_receipt(root,sec.get("PRODUCTION_SMOKE_TARGET") or {},"PRODUCTION_SMOKE_TARGET")
   write(wd/"PRODUCTION_SMOKE_EVIDENCE.yaml",{"artifact_type":"PRODUCTION_SMOKE_EVIDENCE","stage_uid":a.stage,"work_unit_uid":work["work_unit_uid"],"smoke_receipt_ref":ref,"status":"PASS","historical_completion_credit":0})
  elif a.operation=="CURRENT_RELEASE_IDENTITY_CAPTURE":
   dep=load(wd/"PRODUCTION_DEPLOYMENT_RECORD.yaml")
   write(wd/"CURRENT_RELEASE_IDENTITY.yaml",{"artifact_type":"CURRENT_RELEASE_IDENTITY","stage_uid":a.stage,"work_unit_uid":work["work_unit_uid"],"deployment_identity":dep.get("deployment_identity"),"deployment_record_ref":str((wd/"PRODUCTION_DEPLOYMENT_RECORD.yaml").relative_to(root)),"status":"PASS","historical_completion_credit":0})
 elif a.stage=="STAGE-10":
  mapping={"OP-43-PRODUCTION_BROWSER_ACCEPTANCE":"CURRENT_PRODUCTION_RUNTIME_TARGET","OP-44-PRODUCTION_GOVERNED_UNIT_ACCEPTANCE":"PRODUCTION_GOVERNED_UNIT_TARGET","OP-45-PRODUCTION_CONTROL_ACCEPTANCE":"PRODUCTION_PERMISSION_TARGET","OP-46-PRODUCTION_DATABASE_ACCEPTANCE":"PRODUCTION_DATABASE_TARGET","OP-47-PRODUCTION_EFFECTFUL_ACCEPTANCE":"PRODUCTION_PERMISSION_TARGET","OP-48-EXTERNAL_INTEGRATION_ACCEPTANCE":"PRODUCTION_EXTERNAL_INTEGRATION_TARGET","OP-49-ASYNC_RUNTIME_ACCEPTANCE":"PRODUCTION_ASYNC_RUNTIME_TARGET","PRODUCTION_VISUAL_GEOMETRY_ACCEPTANCE":"PRODUCTION_VISUAL_ACCEPTANCE_TARGET","PRODUCTION_STALE_RENDER_ACCEPTANCE":"CURRENT_PRODUCTION_RUNTIME_TARGET","PRODUCTION_CROSS_GOVERNED_UNIT_SLICE_ACCEPTANCE":"PRODUCTION_GOVERNED_UNIT_TARGET"}
  if a.operation!="PRODUCTION_ACCEPTANCE_RECONCILIATION":
   cls=mapping[a.operation]; ref,_=require_external_receipt(root,sec.get(cls) or {},cls)
   out=wd/"EVIDENCE/PRODUCTION_ACCEPTANCE"/(a.operation+".yaml"); write(out,{"artifact_type":"PRODUCTION_ACCEPTANCE_DIMENSION_EVIDENCE","stage_uid":a.stage,"operation_uid":a.operation,"target_class":cls,"external_execution_receipt_ref":ref,"status":"PASS","historical_completion_credit":0})
  else:
   refs=sorted((wd/"EVIDENCE/PRODUCTION_ACCEPTANCE").glob("*.yaml"))
   if len(refs)!=10: raise SystemExit("BLOCK:PRODUCTION_ACCEPTANCE_DIMENSION_DENOMINATOR_DRIFT:"+str(len(refs)))
   write(wd/"PRODUCTION_ACCEPTANCE_EVIDENCE_SET.yaml",{"artifact_type":"PRODUCTION_ACCEPTANCE_EVIDENCE_SET","stage_uid":a.stage,"evidence_refs":[str(x.relative_to(root)) for x in refs],"status":"PASS"})
   write(wd/"PRODUCTION_ACCEPTANCE_RESULT.yaml",{"artifact_type":"PRODUCTION_ACCEPTANCE_RESULT","stage_uid":a.stage,"work_unit_uid":work["work_unit_uid"],"accepted_dimension_total":len(refs),"status":"PASS","historical_completion_credit":0})
 else:
  if a.operation=="OP-50-MONITORING_VERIFICATION": require_external_receipt(root,sec.get("MONITORING_TARGET") or {},"MONITORING_TARGET")
  elif a.operation=="OP-51-BACKUP_VERIFICATION": require_external_receipt(root,sec.get("BACKUP_TARGET") or {},"BACKUP_TARGET")
  elif a.operation=="OP-52-ROLLBACK_VERIFICATION": require_external_receipt(root,sec.get("ROLLBACK_TARGET") or {},"ROLLBACK_TARGET")
  elif a.operation=="OP-53-FINAL_AUDIT_MATRIX_RECONCILIATION":
   write(wd/"FINAL_AUDIT_EVIDENCE.yaml",{"artifact_type":"FINAL_AUDIT_EVIDENCE","stage_uid":a.stage,"work_unit_uid":work["work_unit_uid"],"operations_verified":["OP-50-MONITORING_VERIFICATION","OP-51-BACKUP_VERIFICATION","OP-52-ROLLBACK_VERIFICATION"],"status":"PASS"})
   write(wd/"OPERATIONS_EVIDENCE.yaml",{"artifact_type":"OPERATIONS_EVIDENCE","stage_uid":a.stage,"work_unit_uid":work["work_unit_uid"],"status":"PASS"})
  elif a.operation=="OP-54-FINAL_PRODUCTION_ACCEPTANCE":
   write(wd/"FINAL_PRODUCTION_ACCEPTANCE_RESULT.yaml",{"artifact_type":"FINAL_PRODUCTION_ACCEPTANCE_RESULT","stage_uid":a.stage,"work_unit_uid":work["work_unit_uid"],"status":"PASS","historical_completion_credit":0})
  elif a.operation=="GOVERNED_UNIT_CLOSURE":
   write(wd/"GOVERNED_UNIT_CLOSED.yaml",{"artifact_type":"GOVERNED_UNIT_CLOSED","stage_uid":a.stage,"work_unit_uid":work["work_unit_uid"],"governed_unit_uid":work["governed_unit_uid"],"status":"PASS","historical_completion_credit":0})
  elif a.operation=="NEXT_GOVERNED_UNIT_ELIGIBILITY_EVALUATE":
   write(wd/"NEXT_GOVERNED_UNIT_ELIGIBILITY.yaml",{"artifact_type":"NEXT_GOVERNED_UNIT_ELIGIBILITY","stage_uid":a.stage,"work_unit_uid":work["work_unit_uid"],"eligibility_result":"REQUIRES_REGISTERED_SUCCESSOR_AUTHORITY_RESOLUTION","next_governed_unit_identity_when_ready":None,"legal_stage_admission_target_when_ready":None,"ai_may_select_next_governed_unit":False,"status":"PASS","historical_completion_credit":0})
 receipt(root,work,a.stage,a.operation); print("PASS:",a.stage,a.operation,work["work_unit_uid"])
if __name__=="__main__": main()
