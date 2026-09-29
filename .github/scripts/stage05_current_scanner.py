#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, subprocess
from pathlib import Path
import yaml

STAGE="STAGE-05"
AUTH="STAGE_EXECUTION/SHARED_AUTHORITY/PRODUCT_IMPLEMENTATION_AUTHORITY.yaml"

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise RuntimeError("MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise RuntimeError("MAPPING_REQUIRED:"+str(p))
    return d

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def git(root,*args):
    cp=subprocess.run(["git","-C",str(root),*args],text=True,capture_output=True)
    if cp.returncode!=0: raise RuntimeError("GIT:"+cp.stderr.strip())
    return cp.stdout.strip()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage",required=True); ap.add_argument("--scanner-dimension",required=True); ap.add_argument("--work-unit",required=True); ap.add_argument("--product-root",required=True)
    a=ap.parse_args(); root=Path(a.product_root).resolve(); wd=(root/Path(a.work_unit)).parent; gaps=[]
    try:
        if a.stage!=STAGE: gaps.append("STAGE_IDENTITY_DRIFT")
        work=load(wd/"WORK_UNIT.yaml")
        auth=load(root/AUTH)
        if auth.get("status")!="CURRENT_STAGE05_AUTHORITY": gaps.append("IMPLEMENTATION_AUTHORITY_NOT_CURRENT")
        ready=auth.get("stage05_readiness") or {}
        if int(ready.get("unresolved_binding_class_total") or -1)!=0: gaps.append("IMPLEMENTATION_AUTHORITY_UNRESOLVED")
        storage=(auth.get("execution_target_authority") or {}).get("STORAGE_RUNTIME_TARGET") or {}
        if storage.get("status")!="AUTHORIZED_NOT_APPLICABLE" or not storage.get("authority_evidence_refs"):
            gaps.append("STORAGE_NA_AUTHORITY_INVALID")
        for rel in ["PROGRAM_ARTIFACT_SET.yaml","IMPLEMENTATION_MANIFEST.yaml","IMPLEMENTATION_EVIDENCE.yaml","IMPLEMENTATION_DIFF_EVIDENCE.yaml"]:
            if not (wd/rel).is_file(): gaps.append("MISSING:"+rel)
        if not gaps:
            aset=load(wd/"PROGRAM_ARTIFACT_SET.yaml")
            manifest=load(wd/"IMPLEMENTATION_MANIFEST.yaml")
            evidence=load(wd/"IMPLEMENTATION_EVIDENCE.yaml")
            diff=load(wd/"IMPLEMENTATION_DIFF_EVIDENCE.yaml")
            arts=aset.get("program_artifacts") or []
            if not isinstance(arts,list) or not arts or int(aset.get("program_artifact_total") or 0)!=len(arts): gaps.append("PROGRAM_ARTIFACT_DENOMINATOR_DRIFT")
            seen=set()
            for row in arts:
                rel=str((row or {}).get("canonical_path") or "")
                if not rel or rel in seen: gaps.append("PROGRAM_ARTIFACT_PATH_INVALID:"+rel); continue
                seen.add(rel); p=root/rel
                if not p.is_file(): gaps.append("PROGRAM_ARTIFACT_MISSING:"+rel); continue
                if str((row or {}).get("current_hash") or "")!=sha(p): gaps.append("PROGRAM_ARTIFACT_HASH_DRIFT:"+rel)
                if not str((row or {}).get("construction_profile") or ""): gaps.append("PROGRAM_ARTIFACT_PROFILE_MISSING:"+rel)
                if not str((row or {}).get("owner_uid") or ""): gaps.append("PROGRAM_ARTIFACT_OWNER_MISSING:"+rel)
                if not git(root,"ls-files","--",rel).strip(): gaps.append("PROGRAM_ARTIFACT_NOT_TRACKED:"+rel)
            if manifest.get("status")!="PASS" or manifest.get("program_artifact_total")!=len(arts): gaps.append("IMPLEMENTATION_MANIFEST_INVALID")
            if manifest.get("storage_runtime_applicability")!="AUTHORIZED_NOT_APPLICABLE": gaps.append("IMPLEMENTATION_STORAGE_APPLICABILITY_DRIFT")
            if evidence.get("status")!="PASS" or int(evidence.get("verified_program_artifact_total") or 0)!=len(arts): gaps.append("IMPLEMENTATION_EVIDENCE_INVALID")
            if diff.get("status")!="PASS" or len(diff.get("program_artifact_hashes") or [])!=len(arts): gaps.append("IMPLEMENTATION_DIFF_EVIDENCE_INVALID")
            if evidence.get("current_head_sha")!=git(root,"rev-parse","HEAD"): gaps.append("IMPLEMENTATION_EVIDENCE_HEAD_DRIFT")
            if int(manifest.get("historical_completion_credit") or 0)!=0 or int(evidence.get("historical_completion_credit") or 0)!=0 or int(diff.get("historical_completion_credit") or 0)!=0:
                gaps.append("HISTORICAL_COMPLETION_CREDIT_FORBIDDEN")
            if str(work.get("governed_unit_uid") or "")!=str(manifest.get("governed_unit_uid") or ""): gaps.append("GOVERNED_UNIT_DRIFT")
    except Exception as e:
        gaps.append("SCANNER_EXCEPTION:"+str(e))
    out={"stage_uid":STAGE,"scanner_dimension":a.scanner_dimension,"status":"PASS" if not gaps else "FAIL","gaps":gaps,"hidden_defect_total":len(gaps)}
    print(json.dumps(out,ensure_ascii=False))
    raise SystemExit(0 if not gaps else 1)

if __name__=="__main__": main()
