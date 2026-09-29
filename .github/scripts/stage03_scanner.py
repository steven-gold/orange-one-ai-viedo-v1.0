#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import yaml
REQ=["VISUAL_DESIGN_SPEC_PACKAGE.yaml","VISUAL_GEOMETRY_CONTRACT.yaml","VISUAL_PREVIEW_EVIDENCE.yaml","VISUAL_CHANGESET.yaml","VISUAL_INTERACTION_TOPOLOGY_BINDING.yaml","FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT.yaml","VISUAL_REFERENCE_ANNOTATION.yaml","VISUAL_INHERITANCE_MATRIX.yaml","VISUAL_SCENARIO_EVIDENCE_SET.yaml","EVIDENCE/VISUAL_REVIEW_EVIDENCE.yaml"]
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
        if a.stage!="STAGE-03": gaps.append("STAGE_IDENTITY_DRIFT")
        for r in REQ:
            if not (wd/r).is_file(): gaps.append("MISSING:"+r)
        if not gaps:
            g=load(wd/"VISUAL_GEOMETRY_CONTRACT.yaml")
            if not g.get("visual_anchors") or int(g.get("visual_anchor_count") or 0)!=len(g.get("visual_anchors") or []): gaps.append("VISUAL_ANCHOR_DENOMINATOR_INVALID")
            s=load(wd/"VISUAL_SCENARIO_EVIDENCE_SET.yaml"); sc=s.get("scenarios") or []
            if int(s.get("required_scenario_count") or -1)!=len(sc) or int(s.get("materialized_scenario_count") or -1)!=len(sc): gaps.append("SCENARIO_DENOMINATOR_DRIFT")
            for x in sc:
                if not (wd/str(x.get("evidence_ref") or "")).is_file(): gaps.append("SCENARIO_EVIDENCE_MISSING:"+str(x.get("scenario_uid")))
            if load(wd/"VISUAL_INTERACTION_TOPOLOGY_BINDING.yaml").get("functional_topology_redefined") is not False: gaps.append("FUNCTIONAL_TOPOLOGY_REDEFINED")
            if load(wd/"VISUAL_PREVIEW_EVIDENCE.yaml").get("structural_only") is not False: gaps.append("STRUCTURAL_ONLY_PREVIEW")
            vim=load(wd/"VISUAL_INHERITANCE_MATRIX.yaml")
            if int(vim.get("duplicate_visual_owner_count") or 0)!=0 or int(vim.get("unresolved_visual_authority_count") or 0)!=0: gaps.append("VISUAL_AUTHORITY_UNRESOLVED")
            rev=load(wd/"EVIDENCE/VISUAL_REVIEW_EVIDENCE.yaml")
            if rev.get("decision")!="VISUAL_APPROVED" or rev.get("visual_approved") is not True or not rev.get("reviewer") or not rev.get("reviewed_at"): gaps.append("FORMAL_HUMAN_APPROVAL_REQUIRED")
    except Exception as e: gaps.append("SCANNER_EXCEPTION:"+str(e))
    out={"stage_uid":"STAGE-03","scanner_dimension":a.scanner_dimension,"status":"PASS" if not gaps else "FAIL","gaps":gaps,"hidden_defect_total":len(gaps)}
    print(json.dumps(out,ensure_ascii=False)); raise SystemExit(0 if not gaps else 1)
if __name__=="__main__": main()
