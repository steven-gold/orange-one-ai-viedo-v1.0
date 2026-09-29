#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import yaml

ENTITY_OPS=["DISCOVER_OR_LIST","SELECT_OR_OPEN","CREATE","CREATION_MODE","PARENT_BIND","CATEGORY_OR_GROUP_BIND","DRAFT","RESUME","EDIT","SAVE","VALIDATE","CONFIRM_OR_APPROVE","VERSION","REVISE","LOCK_OR_UNLOCK","REORDER","MOVE_OR_REPARENT","ARCHIVE_OR_DELETE","RESTORE","DEPENDENCY_IMPACT","AUDIT","ERROR_RECOVERY","NEXT_STEP"]
CHAIN_FIELDS=["business_intent","preconditions","entry","input_source","trigger","gate","permission","action","validation","payload","runtime_owner","resulting_state","audit_event","feedback","failure_state","recovery","next_step","authority_refs"]
WB_FIELDS=["functional_cluster_uid","business_journey","required_operations","shared_context_identity","workbench_class","visual_container_requirement","required_order","adjacency_requirements","same_surface_requirement","allowed_separation_modes","forbidden_interruptions","cross_surface_transition_contract","context_handoff_contract","responsive_reflow_rule","authority_ref"]
TOPO_FIELDS=["functional_cluster_uid","operation_sequence","grouping","adjacency","interruption_boundary","surface_transition_boundary","shared_context_or_state_identity","continuation_or_recovery_path","responsive_reflow_contract","authority_ref"]

def load(p):
    p=Path(p)
    if not p.is_file(): raise RuntimeError("MISSING:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise RuntimeError("MAPPING_REQUIRED:"+str(p))
    return d

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--stage",required=True); ap.add_argument("--scanner-dimension",required=True); ap.add_argument("--work-unit",required=True); ap.add_argument("--product-root",required=True)
    a=ap.parse_args(); root=Path(a.product_root).resolve(); wp=root/Path(a.work_unit); wd=wp.parent; gaps=[]
    try:
        work=load(wp)
        if a.stage!="STAGE-02" or work.get("stage_uid")!="STAGE-02": gaps.append("STAGE_IDENTITY_DRIFT")
        required=["REQUIRED_FIELD_MANIFEST.yaml","FUNCTIONAL_CHAIN_MANIFEST.yaml","EFFECTIVE_CONTRACT_OVERLAY.yaml","DEPENDENCY_TOPOLOGY.yaml","CHANGE_IMPACT_MAP.yaml","FUNCTIONAL_CHAIN_SPEC.yaml","DEPENDENCY_MAP.yaml","GOVERNED_UNIT_CONSTRUCTION_SPEC_PACKAGE.yaml","ASYNC_PROVIDER_CONTRACT.yaml","SHARED_OWNER_PORT_MAP.yaml","FUNCTIONAL_WORKBENCH_CONTRACT.yaml","INTERACTION_TOPOLOGY_SPEC.yaml","FUNCTION_ADMISSION_SCORECARD.yaml","AUTO_COMPLETION_SCOPE_LEDGER.yaml","DENOMINATOR_SNAPSHOT.yaml","CLASSIFICATION_RULESET.yaml","STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml","CURRENT_PROBLEM_REGISTER.yaml","RESOLUTION_LEDGER.yaml","EVIDENCE/GOVERNED_UNIT_FUNCTIONAL_REVIEW_EVIDENCE.yaml"]
        for rel in required:
            if not (wd/rel).is_file(): gaps.append("MISSING_REQUIRED_ARTIFACT:"+rel)
        if not gaps:
            chains=load(wd/"FUNCTIONAL_CHAIN_SPEC.yaml").get("chains") or []
            if not chains: gaps.append("FUNCTIONAL_CHAIN_EMPTY")
            for c in chains:
                miss=[k for k in CHAIN_FIELDS if c.get(k) in (None,"",[])]
                if miss: gaps.append("FUNCTIONAL_CHAIN_FIELDS_MISSING:"+str(c.get("chain_uid"))+":"+",".join(miss))
            inv=load(wd/"GOVERNED_ENTITY_INVENTORY.yaml"); ents=inv.get("entities") or []
            matrix=load(wd/"GOVERNED_ENTITY_OPERATION_MATRIX.yaml"); rows=matrix.get("rows") or []
            if len(rows)!=len(ents)*len(ENTITY_OPS): gaps.append("ENTITY_OPERATION_DENOMINATOR_DRIFT")
            seen={(str(x.get("entity_uid")),str(x.get("operation_uid"))) for x in rows}
            if len(seen)!=len(rows): gaps.append("ENTITY_OPERATION_DUPLICATE")
            for row in rows:
                if row.get("applicability")=="AUTHORIZED_NOT_APPLICABLE" and not row.get("authority_evidence_ref"): gaps.append("NA_AUTHORITY_EVIDENCE_MISSING")
            h=load(wd/"ENTITY_HIERARCHY_MATRIX.yaml"); edges=h.get("edges") or []
            if len(edges)!=max(0,len(ents)-1): gaps.append("ENTITY_HIERARCHY_EDGE_DENOMINATOR_DRIFT")
            wb=load(wd/"FUNCTIONAL_WORKBENCH_CONTRACT.yaml").get("workbenches") or []
            if not wb: gaps.append("WORKBENCH_EMPTY")
            for x in wb:
                miss=[k for k in WB_FIELDS if x.get(k) in (None,"",[])]
                if miss: gaps.append("WORKBENCH_FIELDS_MISSING:"+",".join(miss))
            topo=load(wd/"INTERACTION_TOPOLOGY_SPEC.yaml").get("rows") or []
            if not topo: gaps.append("INTERACTION_TOPOLOGY_EMPTY")
            for x in topo:
                miss=[k for k in TOPO_FIELDS if x.get(k) in (None,"",[])]
                if miss: gaps.append("TOPOLOGY_FIELDS_MISSING:"+",".join(miss))
            visual=load(wd/"FUNCTION_VISUAL_IMPACT_MATRIX.yaml").get("rows") or []
            if len(visual)!=len(chains): gaps.append("FUNCTION_VISUAL_IMPACT_DENOMINATOR_DRIFT")
            pr=load(wd/"CURRENT_PROBLEM_REGISTER.yaml")
            if pr.get("items"): gaps.append("CURRENT_PROBLEM_REGISTER_NOT_ZERO")
            ev=load(wd/"EVIDENCE/GOVERNED_UNIT_FUNCTIONAL_REVIEW_EVIDENCE.yaml")
            if ev.get("result")!="PASS" or int(ev.get("historical_completion_credit") or 0)!=0: gaps.append("FUNCTIONAL_REVIEW_EVIDENCE_INVALID")
    except Exception as e:
        gaps.append("SCANNER_EXCEPTION:"+str(e))
    out={"stage_uid":"STAGE-02","scanner_dimension":a.scanner_dimension,"status":"PASS" if not gaps else "FAIL","gaps":gaps,"hidden_defect_total":len(gaps)}
    print(json.dumps(out,ensure_ascii=False))
    raise SystemExit(0 if not gaps else 1)

if __name__=="__main__": main()
