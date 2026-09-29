#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import yaml
AUTH="STAGE_EXECUTION/SHARED_AUTHORITY/PRODUCT_IMPLEMENTATION_AUTHORITY.yaml"
SECTIONS={"STAGE-09":"production_target_authority","STAGE-10":"production_acceptance_target_authority","STAGE-11":"operations_target_authority"}
REQ={
"STAGE-09":["PRODUCTION_DEPLOYMENT_RECORD.yaml","CURRENT_RELEASE_IDENTITY.yaml","PRODUCTION_SMOKE_EVIDENCE.yaml"],
"STAGE-10":["PRODUCTION_ACCEPTANCE_RESULT.yaml","PRODUCTION_ACCEPTANCE_EVIDENCE_SET.yaml"],
"STAGE-11":["FINAL_PRODUCTION_ACCEPTANCE_RESULT.yaml","GOVERNED_UNIT_CLOSED.yaml","NEXT_GOVERNED_UNIT_ELIGIBILITY.yaml","FINAL_AUDIT_EVIDENCE.yaml","OPERATIONS_EVIDENCE.yaml"]}
def load(p):
 p=Path(p)
 if not p.is_file() or p.stat().st_size<=0: raise RuntimeError("MISSING_OR_EMPTY:"+str(p))
 d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
 if not isinstance(d,dict): raise RuntimeError("MAPPING_REQUIRED:"+str(p))
 return d
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--stage",required=True); ap.add_argument("--scanner-dimension",required=True); ap.add_argument("--work-unit",required=True); ap.add_argument("--product-root",required=True)
 a=ap.parse_args(); root=Path(a.product_root).resolve(); wd=(root/Path(a.work_unit)).parent; gaps=[]
 try:
  if a.stage not in SECTIONS: gaps.append("STAGE_IDENTITY_DRIFT")
  auth=load(root/AUTH); sec=auth.get(SECTIONS.get(a.stage,"")) or {}
  unresolved=[k for k,v in sec.items() if isinstance(v,dict) and v.get("status")=="UNRESOLVED_EXTERNAL_CURRENT_TARGET"]
  if unresolved: gaps.extend("EXTERNAL_TARGET_UNRESOLVED:"+x for x in unresolved)
  for rel in REQ.get(a.stage,[]):
   if not (wd/rel).is_file(): gaps.append("MISSING:"+rel)
  if not gaps:
   for rel in REQ[a.stage]:
    d=load(wd/rel)
    if d.get("status")!="PASS": gaps.append("NOT_PASS:"+rel)
    if int(d.get("historical_completion_credit") or 0)!=0: gaps.append("HISTORICAL_COMPLETION_CREDIT_FORBIDDEN:"+rel)
 except Exception as e: gaps.append("SCANNER_EXCEPTION:"+str(e))
 out={"stage_uid":a.stage,"scanner_dimension":a.scanner_dimension,"status":"PASS" if not gaps else "FAIL","gaps":gaps,"hidden_defect_total":len(gaps)}
 print(json.dumps(out,ensure_ascii=False)); raise SystemExit(0 if not gaps else 1)
if __name__=="__main__": main()
