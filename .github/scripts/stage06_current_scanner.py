#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path
import yaml

STAGE="STAGE-06"
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
        work=load(wd/"WORK_UNIT.yaml"); auth=load(root/AUTH)
        if auth.get("status")!="CURRENT_PRODUCT_EXECUTION_AUTHORITY": gaps.append("PRODUCT_EXECUTION_AUTHORITY_NOT_CURRENT")
        ready=auth.get("stage06_readiness") or {}
        if int(ready.get("required_binding_class_total") or 0)!=9 or int(ready.get("unresolved_binding_class_total") or -1)!=0:
            gaps.append("STAGE06_AUTHORITY_NOT_READY")
        required=["TEST_ADMISSION_MANIFEST.yaml","AUDIT_MATRIX.yaml","TEST_EVIDENCE_SET.yaml","VERIFICATION_RESULT.yaml","WORK_UNIT_CLOSURE_RECORD.yaml","VERIFIED_SOURCE_REVISION.yaml"]
        for rel in required:
            if not (wd/rel).is_file(): gaps.append("MISSING:"+rel)
        if not gaps:
            adm=load(wd/"TEST_ADMISSION_MANIFEST.yaml")
            rows=adm.get("tests") or []
            admitted=[x for x in rows if isinstance(x,dict) and x.get("status")=="ADMITTED"]
            excluded=[x for x in rows if isinstance(x,dict) and x.get("status")=="EXCLUDED_LEGACY_REFERENCE"]
            if int(adm.get("test_corpus_total") or 0)!=len(rows): gaps.append("TEST_CORPUS_DENOMINATOR_DRIFT")
            if int(adm.get("admitted_total") or 0)!=len(admitted): gaps.append("TEST_ADMITTED_DENOMINATOR_DRIFT")
            if int(adm.get("excluded_legacy_reference_total") or 0)!=len(excluded): gaps.append("TEST_EXCLUDED_DENOMINATOR_DRIFT")
            for row in admitted:
                ref=str(row.get("test_ref") or ""); p=root/ref
                if not p.is_file() or not git(root,"ls-files","--",ref).strip(): gaps.append("ADMITTED_TEST_NOT_CURRENT:"+ref)
            for row in excluded:
                if not row.get("unresolved_excluded_source_refs"): gaps.append("EXCLUDED_TEST_WITHOUT_REASON:"+str(row.get("test_ref") or ""))
            audit=load(wd/"AUDIT_MATRIX.yaml"); evidence=load(wd/"TEST_EVIDENCE_SET.yaml")
            verify=load(wd/"VERIFICATION_RESULT.yaml"); close=load(wd/"WORK_UNIT_CLOSURE_RECORD.yaml"); rev=load(wd/"VERIFIED_SOURCE_REVISION.yaml")
            if audit.get("status")!="PASS" or int(audit.get("fail_total") or 0)!=0: gaps.append("AUDIT_MATRIX_NOT_PASS")
            evrefs=evidence.get("evidence_refs") or []
            if evidence.get("status")!="PASS" or not isinstance(evrefs,list) or len(evrefs)<11: gaps.append("TEST_EVIDENCE_SET_INCOMPLETE")
            if int(evidence.get("legacy_reference_completion_credit") or -1)!=0: gaps.append("LEGACY_TEST_COMPLETION_CREDIT_FORBIDDEN")
            for ref in evrefs:
                d=load(root/str(ref))
                if d.get("result")!="PASS" or int(d.get("historical_completion_credit") or 0)!=0: gaps.append("TEST_RESULT_NOT_CURRENT_PASS:"+str(ref))
            if verify.get("status")!="PASS" or int(verify.get("profile_failure_total") or -1)!=0: gaps.append("VERIFICATION_RESULT_NOT_PASS")
            if close.get("status")!="PASS" or close.get("closure_state")!="PRE_RELEASE_VERIFIED": gaps.append("WORK_UNIT_CLOSURE_NOT_PASS")
            if rev.get("status")!="PASS" or not rev.get("head_sha") or not rev.get("tree_sha"): gaps.append("VERIFIED_SOURCE_REVISION_INVALID")
            aset=load(root/str((work.get("input_bindings") or {}).get("PROGRAM_ARTIFACT_SET",{}).get("artifact_ref") or ""))
            for row in aset.get("program_artifacts") or []:
                rel=str((row or {}).get("canonical_path") or ""); p=root/rel
                if not p.is_file(): gaps.append("VERIFIED_PROGRAM_ARTIFACT_MISSING:"+rel)
                elif str((row or {}).get("current_hash") or "")!=sha(p): gaps.append("VERIFIED_PROGRAM_ARTIFACT_HASH_DRIFT:"+rel)
    except Exception as e:
        gaps.append("SCANNER_EXCEPTION:"+str(e))
    out={"stage_uid":STAGE,"scanner_dimension":a.scanner_dimension,"status":"PASS" if not gaps else "FAIL","gaps":gaps,"hidden_defect_total":len(gaps)}
    print(json.dumps(out,ensure_ascii=False))
    raise SystemExit(0 if not gaps else 1)

if __name__=="__main__": main()
