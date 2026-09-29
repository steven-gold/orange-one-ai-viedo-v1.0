#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import yaml
def load(p):
    p=Path(p)
    if not p.is_file(): raise RuntimeError("MISSING:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise RuntimeError("MAPPING_REQUIRED:"+str(p))
    return d
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--stage",required=True); ap.add_argument("--scanner-dimension",required=True); ap.add_argument("--work-unit",required=True); ap.add_argument("--product-root",required=True)
    a=ap.parse_args(); root=Path(a.product_root).resolve(); wd=(root/Path(a.work_unit)).parent; gaps=[]
    try:
        if a.stage!="STAGE-04": gaps.append("STAGE_IDENTITY_DRIFT")
        for rel in ["BASIC_DESIGN_PACKAGE.yaml","ACCEPTANCE_AUDIT_BLUEPRINT.yaml","DESIGN_FREEZE_PACKAGE.yaml","FOUNDATION_BARRIER_RECORD.yaml","EVIDENCE/DESIGN_APPROVAL_EVIDENCE.yaml"]:
            if not (wd/rel).is_file(): gaps.append("MISSING:"+rel)
        if not gaps:
            pkg=load(wd/"BASIC_DESIGN_PACKAGE.yaml"); ds=pkg.get("design_domains") or []; refs=pkg.get("basic_design_domain_checkpoint_refs") or []
            if not ds or len(refs)!=len(ds) or int(pkg.get("basic_design_required_domain_total") or -1)!=len(ds) or int(pkg.get("basic_design_missing_domain_total") or -1)!=0: gaps.append("BASIC_DESIGN_DOMAIN_DENOMINATOR_DRIFT")
            for d,ref in zip(ds,refs):
                cp=load(root/ref)
                if cp.get("domain_uid")!=d.get("domain_uid") or cp.get("checkpoint_state")!="PASS" or cp.get("completeness_validation_result")!="PASS" or cp.get("conflict_validation_result")!="PASS": gaps.append("DOMAIN_CHECKPOINT_NOT_PASS:"+str(d.get("domain_uid")))
            ae=load(wd/"EVIDENCE/DESIGN_APPROVAL_EVIDENCE.yaml")
            if ae.get("approved_by_human") is not True or not ae.get("reviewer") or not ae.get("reviewed_at"): gaps.append("DESIGN_APPROVAL_EVIDENCE_INVALID")
            if load(wd/"FOUNDATION_BARRIER_RECORD.yaml").get("foundation_frozen") is not True: gaps.append("FOUNDATION_NOT_FROZEN")
            if load(wd/"DESIGN_FREEZE_PACKAGE.yaml").get("immutable") is not True: gaps.append("FREEZE_PACKAGE_NOT_IMMUTABLE")
    except Exception as e: gaps.append("SCANNER_EXCEPTION:"+str(e))
    out={"stage_uid":"STAGE-04","scanner_dimension":a.scanner_dimension,"status":"PASS" if not gaps else "FAIL","gaps":gaps,"hidden_defect_total":len(gaps)}
    print(json.dumps(out,ensure_ascii=False)); raise SystemExit(0 if not gaps else 1)
if __name__=="__main__": main()
