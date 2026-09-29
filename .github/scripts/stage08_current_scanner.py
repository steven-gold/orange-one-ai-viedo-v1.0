#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import yaml

STAGE="STAGE-08"
AUTH="STAGE_EXECUTION/SHARED_AUTHORITY/PRODUCT_IMPLEMENTATION_AUTHORITY.yaml"

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise RuntimeError("MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise RuntimeError("MAPPING_REQUIRED:"+str(p))
    return d

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage",required=True); ap.add_argument("--scanner-dimension",required=True); ap.add_argument("--work-unit",required=True); ap.add_argument("--product-root",required=True)
    a=ap.parse_args(); root=Path(a.product_root).resolve(); wd=(root/Path(a.work_unit)).parent; gaps=[]
    try:
        if a.stage!=STAGE: gaps.append("STAGE_IDENTITY_DRIFT")
        auth=load(root/AUTH); ts=auth.get("staging_target_authority") or {}
        unresolved=[k for k,v in ts.items() if isinstance(v,dict) and v.get("status")=="UNRESOLVED_EXTERNAL_CURRENT_TARGET"]
        if unresolved: gaps.extend("EXTERNAL_TARGET_UNRESOLVED:"+x for x in unresolved)
        for rel in ["STAGING_ACCEPTANCE_OR_NA_EVIDENCE.yaml","STAGING_CLOSURE_RECORD.yaml"]:
            if not (wd/rel).is_file(): gaps.append("MISSING:"+rel)
        if not gaps:
            ev=load(wd/"STAGING_ACCEPTANCE_OR_NA_EVIDENCE.yaml"); close=load(wd/"STAGING_CLOSURE_RECORD.yaml")
            if ev.get("status")!="PASS" or ev.get("mode") not in {"STAGING_ACCEPTANCE","AUTHORITY_PROVEN_NOT_APPLICABLE"}: gaps.append("STAGING_EVIDENCE_INVALID")
            if close.get("status")!="PASS" or close.get("closure_mode")!=ev.get("mode"): gaps.append("STAGING_CLOSURE_INVALID")
            if int(ev.get("historical_completion_credit") or 0)!=0 or int(close.get("historical_completion_credit") or 0)!=0: gaps.append("HISTORICAL_COMPLETION_CREDIT_FORBIDDEN")
    except Exception as e: gaps.append("SCANNER_EXCEPTION:"+str(e))
    out={"stage_uid":STAGE,"scanner_dimension":a.scanner_dimension,"status":"PASS" if not gaps else "FAIL","gaps":gaps,"hidden_defect_total":len(gaps)}
    print(json.dumps(out,ensure_ascii=False)); raise SystemExit(0 if not gaps else 1)

if __name__=="__main__": main()
