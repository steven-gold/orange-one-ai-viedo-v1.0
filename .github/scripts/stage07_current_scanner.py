#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import yaml

STAGE="STAGE-07"
AUTH="STAGE_EXECUTION/SHARED_AUTHORITY/PRODUCT_IMPLEMENTATION_AUTHORITY.yaml"

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
        if a.stage!=STAGE: gaps.append("STAGE_IDENTITY_DRIFT")
        auth=load(root/AUTH); ready=auth.get("stage07_readiness") or {}
        if auth.get("status")!="CURRENT_PRODUCT_EXECUTION_AUTHORITY" or int(ready.get("unresolved_binding_class_total") or -1)!=0: gaps.append("STAGE07_BUILD_AUTHORITY_NOT_READY")
        for rel in ["BUILD_IDENTITY_MANIFEST.yaml","RELEASE_CANDIDATE.yaml","STAGING_APPLICABILITY_DECISION.yaml","BUILD_TEST_EVIDENCE.yaml"]:
            if not (wd/rel).is_file(): gaps.append("MISSING:"+rel)
        if not gaps:
            build=load(wd/"BUILD_IDENTITY_MANIFEST.yaml"); rc=load(wd/"RELEASE_CANDIDATE.yaml"); stg=load(wd/"STAGING_APPLICABILITY_DECISION.yaml"); ev=load(wd/"BUILD_TEST_EVIDENCE.yaml")
            if build.get("status")!="PASS" or not build.get("build_digest_sha256") or build.get("build_command")!="npm run build": gaps.append("BUILD_IDENTITY_INVALID")
            if rc.get("status")!="PASS" or rc.get("build_digest_sha256")!=build.get("build_digest_sha256"): gaps.append("RELEASE_CANDIDATE_INVALID")
            if ev.get("status")!="PASS" or ev.get("build_result")!="PASS" or ev.get("migration_compatibility_result")!="PASS" or ev.get("security_freshness_result")!="PASS": gaps.append("BUILD_TEST_EVIDENCE_NOT_PASS")
            if int(ev.get("historical_completion_credit") or 0)!=0: gaps.append("HISTORICAL_BUILD_CREDIT_FORBIDDEN")
            if stg.get("status")!="PASS" or stg.get("applicability")!="REQUIRED_FOR_REGISTERED_STAGE08": gaps.append("STAGING_APPLICABILITY_DECISION_INVALID")
            if stg.get("external_staging_target_authority_status")!="UNRESOLVED_CURRENT_EXTERNAL_PROJECT_IDENTITY": gaps.append("STAGING_EXTERNAL_AUTHORITY_STATUS_DRIFT")
            if stg.get("ai_selected_external_project") is not False: gaps.append("AI_SELECTED_EXTERNAL_PROJECT_FORBIDDEN")
    except Exception as e: gaps.append("SCANNER_EXCEPTION:"+str(e))
    out={"stage_uid":STAGE,"scanner_dimension":a.scanner_dimension,"status":"PASS" if not gaps else "FAIL","gaps":gaps,"hidden_defect_total":len(gaps)}
    print(json.dumps(out,ensure_ascii=False)); raise SystemExit(0 if not gaps else 1)

if __name__=="__main__": main()
