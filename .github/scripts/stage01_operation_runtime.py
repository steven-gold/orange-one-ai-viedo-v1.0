#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, importlib.util
from pathlib import Path
import yaml
DOMAIN_MAP={"PAGE_CONSTRUCTION":"GOVERNED_UNIT_CONSTRUCTION","GOVERNED_UNIT_CONSTRUCTION":"GOVERNED_UNIT_CONSTRUCTION","VISUAL_CONSTRUCTION":"VISUAL_CONSTRUCTION"}
def y(p):
    o=yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}
    if not isinstance(o,dict): raise RuntimeError("MAPPING_REQUIRED:"+str(p))
    return o
def wy(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(yaml.safe_dump(o,allow_unicode=True,sort_keys=False,width=180),encoding="utf-8")
def load_guard(product):
    p=product/".github/governance-source/active/source/09_TESTS/governance/governance_stage1_pipeline_guard.py"; spec=importlib.util.spec_from_file_location("_stage01_guard_runtime",p)
    if spec is None or spec.loader is None: raise RuntimeError("GUARD_IMPORT_FAILED")
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def fresh_artifact_uid(old): return str(old)+"-REENTRY-001"
def map_domain(v): return DOMAIN_MAP.get(str(v),str(v))
def transform_rel(rel): return str(rel).replace("/PAGE/","/GOVERNED_UNIT_CONSTRUCTION/").replace("/VISUAL/","/VISUAL_CONSTRUCTION/").replace("PAGE_BASE_BLUEPRINT.yaml","GOVERNED_UNIT_BASE_BLUEPRINT.yaml")
def source_uid(work):
    rows=((work.get("source_projection_admission") or {}).get("bindings") or [])
    if len(rows)!=1: raise RuntimeError("SOURCE_PROJECTION_BINDING_DENOMINATOR_INVALID")
    return str(rows[0]["source_uid"])
def projection(wd,work): return y(wd/f"00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{source_uid(work)}/CANONICAL_SOURCE_PROJECTION.yaml")
def pred_dir(product,work): return (product/Path(work["predecessor_work_unit_ref"])).resolve().parent
def current_fact_refs(wd):
    rows=[]
    for rel in ["00_SOURCE_INTAKE/SOURCE_CONTEXT_MANIFEST.yaml","00_SOURCE_INTAKE/CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml","00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml"]:
        d=y(wd/rel); rows.append({"artifact_uid":d["artifact_uid"],"content_hash":d["content_hash"]})
    return rows
def old_class_files(pd): return sorted((pd/"01_CLASSIFIED").rglob("*.yaml"))
def class_map(pd): return {str(y(p)["artifact_uid"]):fresh_artifact_uid(y(p)["artifact_uid"]) for p in old_class_files(pd)}
def op_structure(product,wd,work,guard):
    proj=projection(wd,work); suid=source_uid(work); oldseg=y(pred_dir(product,work)/"00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml"); required={str(r.get("source_node_uid") or "") for r in oldseg.get("source_segments") or []}; observed=[]; dispositions=[]
    for n in proj.get("source_nodes") or []:
        puid=str(n["source_node_uid"]); ss="SS-"+puid; isreq=ss in required
        observed.append({"source_node_uid":ss,"source_ref":suid+"#"+puid,"source_node_kind":n.get("source_node_kind"),"governance_relevance":"REQUIRED" if isreq else "SUPPORTING","terminality_state":"TERMINAL_HOMOGENEOUS","semantic_responsibility_count":1,"unresolved_child_responsibility_count":0,"projection_source_node_uid":puid,"document_order_index":n.get("document_order_index"),"direct_text":n.get("direct_text")})
        dispositions.append({"projection_source_node_uid":puid,"disposition":"SEMANTIC_SOURCE_NODE" if isreq else "STRUCTURAL_SUPPORT","source_structure_node_uids":[ss],"evidence_ref":"EVIDENCE/SOURCE_ENUMERATION_EVIDENCE.yaml"})
    missing=sorted(required-{r["source_node_uid"] for r in observed})
    if missing: raise RuntimeError("PREDECESSOR_SEGMENT_NODE_NOT_IN_FRESH_PROJECTION:"+repr(missing[:20]))
    b=(work["source_projection_admission"]["bindings"])[0]; src={"source_uid":suid,"governed_unit_uid":work["governed_unit_uid"],"enumeration_method":"FRESH_CANONICAL_PROJECTION_NODE_ENUMERATION","enumeration_state":"FULL_SOURCE_ENUMERATION_PROVEN","evidence_ref":"EVIDENCE/SOURCE_ENUMERATION_EVIDENCE.yaml","source_projection_uid":proj["artifact_uid"],"source_projection_content_hash":proj["projection_content_hash"],"source_projection_pair_hash":b["pair_hash"],"observed_nodes":observed,"projection_node_dispositions":dispositions,"structure_manifest_hash":None}; src["structure_manifest_hash"]=guard.content_hash(src)
    wy(wd/"00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml",{"artifact_type":"SOURCE_STRUCTURE_MANIFEST","governed_unit_uid":work["governed_unit_uid"],"sources":[src],"status":"CURRENT_SOURCE_STRUCTURE"}); wy(wd/"EVIDENCE/SOURCE_ENUMERATION_EVIDENCE.yaml",{"artifact_type":"SOURCE_ENUMERATION_EVIDENCE","stage_uid":"STAGE-01","work_unit_uid":work["work_unit_uid"],"source_uid":suid,"coverage_percent":100,"required_projection_node_count":len(proj.get("source_nodes") or []),"enumerated_projection_node_count":len(observed),"required_semantic_node_count":len(required),"result":"PASS"})
def op_segments(product,wd,work,guard):
    pd=pred_dir(product,work); old=y(pd/"00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml"); amap=class_map(pd); struct=y(wd/"00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml"); known={n.get("source_node_uid") for s in struct.get("sources") or [] for n in s.get("observed_nodes") or []}; segs=[]
    for r0 in old.get("source_segments") or []:
        r=copy.deepcopy(r0); node=str(r.get("source_node_uid") or "")
        if node not in known: raise RuntimeError("SEGMENT_NODE_NOT_IN_FRESH_STRUCTURE:"+node)
        r["planning_domain"]=map_domain(r.get("planning_domain")); r["governed_unit_uid"]=work["governed_unit_uid"]; r.pop("page_uid",None); r["target_artifact_uids"]=[amap.get(str(x),fresh_artifact_uid(str(x))) for x in (r.get("target_artifact_uids") or [])]; segs.append(r)
    b=(work["source_projection_admission"]["bindings"])[0]; rec=y(wd/"00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml")["records"][0]; raw_sources=[{"source_uid":rec["source_uid"],"governed_unit_uid":work["governed_unit_uid"],"source_role":rec["source_role"],"source_domain_scope":rec["source_domain_scope"],"source_projection_uid":b["projection_uid"],"source_projection_content_hash":b["projection_content_hash"],"source_projection_pair_hash":b["pair_hash"]}]
    wy(wd/"00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml",{"artifact_type":"SOURCE_SEGMENT_MAP","governed_unit_uid":work["governed_unit_uid"],"raw_sources":raw_sources,"source_segments":segs,"status":"CURRENT_SOURCE_SEGMENT_MAP"})
def op_context(product,wd,work,guard):
    sm=y(wd/"00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml"); proj=projection(wd,work); pmap={n["source_node_uid"]:n for n in proj.get("source_nodes") or []}; nodes=[]
    for s in sm.get("source_segments") or []:
        ss=str(s["source_node_uid"]); puid=ss[3:] if ss.startswith("SS-") else ss; p=pmap.get(puid) or {}; nodes.append({"source_node_uid":ss,"source_uid":s["source_uid"],"projection_source_node_uid":puid,"document_order_index":p.get("document_order_index"),"direct_text":p.get("direct_text")})
    edges=[{"edge_uid":"CTX-"+str(a["source_node_uid"])+"-"+str(b["source_node_uid"]),"from_source_node_uid":a["source_node_uid"],"to_source_node_uid":b["source_node_uid"],"relation_type":"PREVIOUS_NEXT","source_evidence_ref":"EVIDENCE/SOURCE_ENUMERATION_EVIDENCE.yaml"} for a,b in zip(nodes,nodes[1:])]
    b=(work["source_projection_admission"]["bindings"])[0]; d={"artifact_uid":"SF-CONTEXT-"+work["work_unit_uid"],"artifact_type":"SOURCE_CONTEXT_MANIFEST","governed_unit_uid":work["governed_unit_uid"],"governed_unit_uid_or_scope_uid":work["governed_unit_uid"],"governed_unit_uids":[work["governed_unit_uid"]],"source_nodes":nodes,"context_edges":edges,"source_lineage_refs":[b["freeze_receipt_ref"]],"status":"CURRENT_SOURCE_FACT","content_hash":None}; d["content_hash"]=guard.content_hash(d); wy(wd/"00_SOURCE_INTAKE/SOURCE_CONTEXT_MANIFEST.yaml",d)
def op_conflicts(product,wd,work,guard):
    old=y(pred_dir(product,work)/"00_SOURCE_INTAKE/CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml"); d={"artifact_uid":"SF-CONFLICT-"+work["work_unit_uid"],"artifact_type":"CONTENT_SUPERSESSION_CONFLICT_LEDGER","governed_unit_uid":work["governed_unit_uid"],"governed_unit_uid_or_scope_uid":work["governed_unit_uid"],"governed_unit_uids":[work["governed_unit_uid"]],"items":copy.deepcopy(old.get("items") or []),"status":"CURRENT_SOURCE_FACT","content_hash":None}; d["content_hash"]=guard.content_hash(d); wy(wd/"00_SOURCE_INTAKE/CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml",d); wy(wd/"EVIDENCE/CONFLICT_DECISION_EVIDENCE.yaml",{"artifact_type":"CONFLICT_DECISION_EVIDENCE","stage_uid":"STAGE-01","work_unit_uid":work["work_unit_uid"],"conflict_total":len(d["items"]),"result":"PASS"})
def op_dependencies(product,wd,work,guard):
    suid=source_uid(work); edges=[{"edge_uid":"DEP-SEQUENCE-"+suid,"producer_source_uid":suid,"consumer_source_uid":suid,"dependency_type":"SEQUENCE","authority_evidence_ref":"EVIDENCE/SOURCE_ENUMERATION_EVIDENCE.yaml"}]
    if work["governed_unit_uid"]=="workspace:WB-01": edges.append({"edge_uid":"DEP-GLOBAL-SHELL-WB01","producer_source_uid":"SRC-DOCX-334A4679600F092B733B","consumer_source_uid":suid,"dependency_type":"SHARED_OWNER","authority_evidence_ref":"STAGE_EXECUTION/STAGE-01/WU-STAGE01-GLOBAL-HOME-SHELL-NAVIGATION-001/WORK_UNIT_TERMINAL_RECEIPT.yaml"})
    old=y(pred_dir(product,work)/"00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml"); d={"artifact_uid":"SF-DEPENDENCY-"+work["work_unit_uid"],"artifact_type":"SOURCE_DEPENDENCY_MAP","governed_unit_uid":work["governed_unit_uid"],"governed_unit_uid_or_scope_uid":work["governed_unit_uid"],"governed_unit_uids":[work["governed_unit_uid"]],"edges":edges,"unresolved_authority_gaps":copy.deepcopy(old.get("unresolved_authority_gaps") or []),"invented_dependency_count":0,"status":"CURRENT_SOURCE_FACT","content_hash":None}; d["content_hash"]=guard.content_hash(d); wy(wd/"00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml",d)
def op_classification(product,wd,work,guard):
    pd=pred_dir(product,work); valid={s["segment_uid"] for s in y(wd/"00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml").get("source_segments") or []}; count=0
    for p in old_class_files(pd):
        old=y(p); d=copy.deepcopy(old); old_uid=str(d["artifact_uid"]); d["artifact_uid"]=fresh_artifact_uid(old_uid); d["governed_unit_uid"]=work["governed_unit_uid"]; d.pop("page_uid",None); d["planning_domain"]=map_domain(d.get("planning_domain")); d["target_path"]=transform_rel(str(d["target_path"])); d["status"]="CURRENT_CLASSIFICATION"
        for rec in d.get("source_lineage") or []:
            missing=[x for x in rec.get("source_segment_uids") or [] if x not in valid]
            if missing: raise RuntimeError("CLASSIFICATION_LINEAGE_NOT_IN_FRESH_SEGMENTS:"+old_uid+":"+repr(missing[:20]))
        d["content_hash"]=None; d["content_hash"]=guard.content_hash(d); wy(wd/d["target_path"],d); count+=1
    if count==0: raise RuntimeError("NO_PREDECESSOR_CLASSIFICATION_TEMPLATES")
def class_docs(wd):
    out={}
    for p in sorted((wd/"01_CLASSIFIED").rglob("*.yaml")):
        d=y(p); out[str(d["artifact_uid"])]=d
    return out
def transform_blueprint(product,wd,work,guard,visual=False):
    pd=pred_dir(product,work); pats=list((pd/"02_BASE_BLUEPRINT").rglob("VISUAL_BASE_BLUEPRINT.yaml" if visual else "PAGE_BASE_BLUEPRINT.yaml"))
    if len(pats)!=1: raise RuntimeError("PREDECESSOR_BLUEPRINT_TEMPLATE_DENOMINATOR:"+str(len(pats)))
    old=y(pats[0]); classes=class_docs(wd); inputs=[]
    for rec in old.get("input_artifacts") or []:
        uid=fresh_artifact_uid(rec["artifact_uid"]); cur=classes.get(uid)
        if not cur: raise RuntimeError("FRESH_CLASSIFICATION_INPUT_MISSING:"+uid)
        inputs.append({"artifact_uid":uid,"content_hash":cur["content_hash"]})
    d=copy.deepcopy(old); d.pop("page_uid",None); d["governed_unit_uid"]=work["governed_unit_uid"]; d["blueprint_uid"]=(str(old["blueprint_uid"])+"-REENTRY-001" if visual else str(old["blueprint_uid"]).replace("-PAGE","-GOVERNED-UNIT")+"-REENTRY-001"); d["blueprint_type"]="VISUAL_BASE_BLUEPRINT" if visual else "GOVERNED_UNIT_BASE_BLUEPRINT"; d["planning_domain"]="VISUAL_CONSTRUCTION" if visual else "GOVERNED_UNIT_CONSTRUCTION"; d["target_path"]=transform_rel(str(old["target_path"])); d["input_artifacts"]=inputs; d["source_fact_refs"]=current_fact_refs(wd)
    shared=[]
    for x in old.get("shared_refs") or []:
        if isinstance(x,dict):
            q=dict(x)
            if q.get("artifact_uid"): q["artifact_uid"]=fresh_artifact_uid(q["artifact_uid"])
            shared.append(q)
        else: shared.append(fresh_artifact_uid(x))
    d["shared_refs"]=shared; dep=y(wd/"00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml"); d["unresolved_external_authority_refs"]=[{"gap_uid":g.get("gap_uid"),"authority_ref":g.get("authority_ref"),"disposition":"UNRESOLVED_AUTHORITY_GAP"} for g in dep.get("unresolved_authority_gaps") or []]; d["raw_source_inputs"]=[]; d["embedded_classification_payloads"]=[]; d["status"]="CURRENT_BASE_BLUEPRINT"; d.pop("blueprint_hash",None); d["blueprint_hash"]=guard.content_hash(d); wy(wd/d["target_path"],d)
def op_binding(product,wd,work,guard):
    pd=pred_dir(product,work); pats=list((pd/"03_BLUEPRINT_BINDING").rglob("BLUEPRINT_BINDING_MANIFEST.yaml"))
    if len(pats)!=1: raise RuntimeError("PREDECESSOR_BINDING_TEMPLATE_DENOMINATOR:"+str(len(pats)))
    old=y(pats[0]); bp=list((wd/"02_BASE_BLUEPRINT").rglob("GOVERNED_UNIT_BASE_BLUEPRINT.yaml")); vb=list((wd/"02_BASE_BLUEPRINT").rglob("VISUAL_BASE_BLUEPRINT.yaml"))
    if len(bp)!=1 or len(vb)!=1: raise RuntimeError("FRESH_BLUEPRINT_DENOMINATOR_INVALID")
    a=y(bp[0]); v=y(vb[0]); d={"binding_uid":str(old.get("binding_uid") or "BIND")+"-REENTRY-001","governed_unit_uid":work["governed_unit_uid"],"target_path":transform_rel(str(old["target_path"])),"governed_unit_blueprint":{"blueprint_uid":a["blueprint_uid"],"blueprint_hash":a["blueprint_hash"]},"visual_blueprint":{"blueprint_uid":v["blueprint_uid"],"blueprint_hash":v["blueprint_hash"]},"embedded_blueprint_payloads":[],"status":"CURRENT_BLUEPRINT_BINDING","binding_hash":None}; d["binding_hash"]=guard.content_hash(d); wy(wd/d["target_path"],d)
HANDLERS={"SOURCE_STRUCTURE_ENUMERATION":op_structure,"SOURCE_SEGMENT_MAPPING":op_segments,"SOURCE_CONTEXT_COMPILATION":op_context,"SOURCE_SUPERSESSION_CONFLICT_RESOLUTION":op_conflicts,"SOURCE_DEPENDENCY_EXTRACTION":op_dependencies,"RESPONSIBILITY_CLASSIFICATION":op_classification,"GOVERNED_UNIT_BASE_BLUEPRINT_COMPILE":lambda p,w,wo,g:transform_blueprint(p,w,wo,g,False),"VISUAL_BASE_BLUEPRINT_COMPILE":lambda p,w,wo,g:transform_blueprint(p,w,wo,g,True),"BLUEPRINT_BINDING_COMPILE":op_binding}
def main_for(expected_operation):
    ap=argparse.ArgumentParser(); ap.add_argument("--stage",required=True); ap.add_argument("--operation",required=True); ap.add_argument("--work-unit",required=True); ap.add_argument("--product-root",required=True); a=ap.parse_args()
    if a.stage!="STAGE-01" or a.operation!=expected_operation: raise SystemExit("BLOCK:EXECUTOR_OPERATION_IDENTITY_DRIFT")
    product=Path(a.product_root).resolve(); wp=(product/a.work_unit).resolve(); wd=wp.parent; work=y(wp)
    if work.get("work_unit_uid")!=wd.name or work.get("governance_uid")!="GOV-REV-20260928-WORD-DERIVED-STAGE-INTERNAL-VALIDATION": raise SystemExit("BLOCK:WORK_UNIT_IDENTITY_DRIFT")
    guard=load_guard(product); HANDLERS[expected_operation](product,wd,work,guard); binding=(work.get("operation_bindings") or {})[expected_operation]; receipt=product/Path(binding["operation_receipt_ref"])
    wy(receipt,{"artifact_type":"OPERATION_EXECUTION_RECEIPT","stage_uid":"STAGE-01","work_unit_uid":work["work_unit_uid"],"operation_uid":expected_operation,"governance_uid":work["governance_uid"],"status":"PASS","executor_owner":binding["executor_owner"],"executor_protocol":binding["executor_protocol"],"result_owner":binding["result_owner"],"historical_completion_credit":0}); print("PASS:",expected_operation,work["work_unit_uid"])
if __name__=="__main__": raise SystemExit("Use a dedicated Stage01 operation wrapper")
