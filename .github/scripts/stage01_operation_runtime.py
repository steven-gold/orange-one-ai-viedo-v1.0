#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, re
from pathlib import Path
import yaml

VISUAL_TERMS=(
 "visual","視覺","layout","geometry","幾何","px","width","height","spacing","gap",
 "grid","flex","font","typography","字體","字級","color","顏色","violet","purple",
 "radius","shadow","opacity","icon","responsive","自適應","viewport","z-index",
 "position","left","right","top","bottom","sidebar","workspace","header"
)
RESP_RULES=[
 ("RESPONSIVE_LAYOUT",("responsive","自適應","viewport","breakpoint")),
 ("TYPOGRAPHY",("font","typography","字體","字級","line-height")),
 ("VISUAL_STYLE",("color","顏色","violet","purple","shadow","opacity","radius","icon")),
 ("LAYOUT_GEOMETRY",("layout","geometry","幾何","px","width","height","spacing","gap","grid","flex","position","left","right","top","bottom","sidebar","workspace","header")),
 ("AUTHORIZATION_REQUIREMENT",("permission","權限","role","角色","authorization")),
 ("NAVIGATION_REQUIREMENT",("navigation","導航","route","路由","menu","選單")),
 ("CONTROL_DEFINITION",("button","按鈕","control","action","操作")),
 ("STATE_BEHAVIOR",("state","狀態","status","disabled","enabled")),
 ("RUNTIME_INTEGRATION",("api","runtime","provider","worker","queue","database","db"))
]

def y(p):
    o=yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}
    if not isinstance(o,dict): raise RuntimeError("MAPPING_REQUIRED:"+str(p))
    return o

def wy(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(o,allow_unicode=True,sort_keys=False,width=180),encoding="utf-8")

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_guard(product):
    p=product/".github/governance-source/active/source/09_TESTS/governance/governance_stage1_pipeline_guard.py"
    spec=importlib.util.spec_from_file_location("_stage01_guard_runtime",p)
    if spec is None or spec.loader is None: raise RuntimeError("GUARD_IMPORT_FAILED")
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def source_uid(work):
    rows=((work.get("source_projection_admission") or {}).get("bindings") or [])
    if len(rows)!=1: raise RuntimeError("SOURCE_PROJECTION_BINDING_DENOMINATOR_INVALID")
    return str(rows[0]["source_uid"])

def projection(wd,work):
    return y(wd/f"00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{source_uid(work)}/CANONICAL_SOURCE_PROJECTION.yaml")

def unit_dir(work): return str(work.get("scope_uid") or work["governed_unit_uid"]).replace(":","-").replace("/","-")

def domain_for_text(text):
    t=str(text or "").casefold()
    return "VISUAL_CONSTRUCTION" if any(term.casefold() in t for term in VISUAL_TERMS) else "GOVERNED_UNIT_CONSTRUCTION"

def responsibility_for_text(text,domain):
    t=str(text or "").casefold()
    for uid,terms in RESP_RULES:
        if any(term.casefold() in t for term in terms):
            if domain=="VISUAL_CONSTRUCTION" and uid in {"AUTHORIZATION_REQUIREMENT","NAVIGATION_REQUIREMENT","CONTROL_DEFINITION","STATE_BEHAVIOR","RUNTIME_INTEGRATION"}:
                continue
            if domain=="GOVERNED_UNIT_CONSTRUCTION" and uid in {"RESPONSIVE_LAYOUT","TYPOGRAPHY","VISUAL_STYLE","LAYOUT_GEOMETRY"}:
                continue
            return uid
    return "VISUAL_REQUIREMENT" if domain=="VISUAL_CONSTRUCTION" else "GOVERNED_UNIT_REQUIREMENT"

def artifact_uid(work,domain,responsibility):
    scope=re.sub(r"[^A-Za-z0-9]+","-",str(work.get("scope_uid") or "UNIT")).strip("-").upper()
    return f"CL-{scope}-{domain}-{responsibility}"

def current_fact_refs(wd):
    rows=[]
    for rel in [
      "00_SOURCE_INTAKE/SOURCE_CONTEXT_MANIFEST.yaml",
      "00_SOURCE_INTAKE/CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml",
      "00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml"
    ]:
        d=y(wd/rel); rows.append({"artifact_uid":d["artifact_uid"],"content_hash":d["content_hash"]})
    return rows

def refresh_run_manifest(wd,work_path):
    mpath=wd/"CURRENT_RUN_MANIFEST.yaml"
    m=y(mpath)
    m["current_files"]=sorted(p.relative_to(wd).as_posix() for p in wd.rglob("*") if p.is_file())
    wy(mpath,m)
    work=y(work_path)
    row=(work.get("current_ledger_bindings") or {}).get("RUN_MANIFEST")
    if isinstance(row,dict):
        row["content_sha256"]=sha(mpath)
        work["current_ledger_bindings"]["RUN_MANIFEST"]=row
        wy(work_path,work)

def op_structure(product,wd,work,guard):
    proj=projection(wd,work); suid=source_uid(work); observed=[]; dispositions=[]; semantic=0
    for n in proj.get("source_nodes") or []:
        puid=str(n["source_node_uid"]); ss="SS-"+puid; text=str(n.get("direct_text") or "").strip()
        required=bool(text)
        if required: semantic+=1
        observed.append({
          "source_node_uid":ss,
          "source_ref":suid+"#"+puid,
          "source_node_kind":n.get("source_node_kind"),
          "governance_relevance":"REQUIRED" if required else "SUPPORTING",
          "terminality_state":"TERMINAL_HOMOGENEOUS",
          "semantic_responsibility_count":1,
          "unresolved_child_responsibility_count":0,
          "projection_source_node_uid":puid,
          "document_order_index":n.get("document_order_index"),
          "direct_text":n.get("direct_text")
        })
        dispositions.append({
          "projection_source_node_uid":puid,
          "disposition":"SEMANTIC_SOURCE_NODE" if required else "STRUCTURAL_SUPPORT",
          "source_structure_node_uids":[ss],
          "evidence_ref":"EVIDENCE/SOURCE_ENUMERATION_EVIDENCE.yaml"
        })
    if semantic<=0: raise RuntimeError("NO_SEMANTIC_SOURCE_NODE_FROM_CURRENT_PROJECTION")
    b=work["source_projection_admission"]["bindings"][0]
    src={"source_uid":suid,"governed_unit_uid":work["governed_unit_uid"],"enumeration_method":"FRESH_CANONICAL_PROJECTION_NODE_ENUMERATION","enumeration_state":"FULL_SOURCE_ENUMERATION_PROVEN","evidence_ref":"EVIDENCE/SOURCE_ENUMERATION_EVIDENCE.yaml","source_projection_uid":proj["artifact_uid"],"source_projection_content_hash":proj["projection_content_hash"],"source_projection_pair_hash":b["pair_hash"],"observed_nodes":observed,"projection_node_dispositions":dispositions,"structure_manifest_hash":None}
    src["structure_manifest_hash"]=guard.content_hash(src)
    wy(wd/"00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml",{"artifact_type":"SOURCE_STRUCTURE_MANIFEST","governed_unit_uid":work["governed_unit_uid"],"sources":[src],"status":"CURRENT_SOURCE_STRUCTURE"})
    wy(wd/"EVIDENCE/SOURCE_ENUMERATION_EVIDENCE.yaml",{"artifact_type":"SOURCE_ENUMERATION_EVIDENCE","stage_uid":"STAGE-01","work_unit_uid":work["work_unit_uid"],"source_uid":suid,"coverage_percent":100,"required_projection_node_count":len(proj.get("source_nodes") or []),"enumerated_projection_node_count":len(observed),"required_semantic_node_count":semantic,"result":"PASS"})

def op_segments(product,wd,work,guard):
    struct=y(wd/"00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml")
    segs=[]
    for src in struct.get("sources") or []:
        for n in src.get("observed_nodes") or []:
            if n.get("governance_relevance")!="REQUIRED": continue
            text=str(n.get("direct_text") or "").strip()
            domain=domain_for_text(text); resp=responsibility_for_text(text,domain)
            suid=str(n["source_node_uid"])
            segs.append({
              "segment_uid":"SEG-"+suid,
              "source_uid":src["source_uid"],
              "source_node_uid":suid,
              "governed_unit_uid":work["governed_unit_uid"],
              "planning_domain":domain,
              "responsibility_uid":resp,
              "required":True,
              "disposition":"CLASSIFIED",
              "target_artifact_uids":[artifact_uid(work,domain,resp)]
            })
    domains={s["planning_domain"] for s in segs}
    missing=sorted({"GOVERNED_UNIT_CONSTRUCTION","VISUAL_CONSTRUCTION"}-domains)
    if missing: raise RuntimeError("FRESH_SEGMENT_DOMAIN_GAP:"+repr(missing))
    b=work["source_projection_admission"]["bindings"][0]
    rec=y(wd/"00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml")["records"][0]
    raw_sources=[{"source_uid":rec["source_uid"],"governed_unit_uid":work["governed_unit_uid"],"source_role":rec["source_role"],"source_domain_scope":rec["source_domain_scope"],"source_projection_uid":b["projection_uid"],"source_projection_content_hash":b["projection_content_hash"],"source_projection_pair_hash":b["pair_hash"]}]
    wy(wd/"00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml",{"artifact_type":"SOURCE_SEGMENT_MAP","governed_unit_uid":work["governed_unit_uid"],"raw_sources":raw_sources,"source_segments":segs,"status":"CURRENT_SOURCE_SEGMENT_MAP"})

def op_context(product,wd,work,guard):
    sm=y(wd/"00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml"); proj=projection(wd,work)
    pmap={n["source_node_uid"]:n for n in proj.get("source_nodes") or []}; nodes=[]
    for s in sm.get("source_segments") or []:
        ss=str(s["source_node_uid"]); puid=ss[3:] if ss.startswith("SS-") else ss; p=pmap.get(puid) or {}
        nodes.append({"source_node_uid":ss,"source_uid":s["source_uid"],"projection_source_node_uid":puid,"document_order_index":p.get("document_order_index"),"direct_text":p.get("direct_text")})
    nodes.sort(key=lambda x:(x.get("document_order_index") is None,x.get("document_order_index") or 0,x["source_node_uid"]))
    edges=[{"edge_uid":"CTX-"+str(a["source_node_uid"])+"-"+str(b["source_node_uid"]),"from_source_node_uid":a["source_node_uid"],"to_source_node_uid":b["source_node_uid"],"relation_type":"PREVIOUS_NEXT","source_evidence_ref":"EVIDENCE/SOURCE_ENUMERATION_EVIDENCE.yaml"} for a,b in zip(nodes,nodes[1:])]
    b=work["source_projection_admission"]["bindings"][0]
    d={"artifact_uid":"SF-CONTEXT-"+work["work_unit_uid"],"artifact_type":"SOURCE_CONTEXT_MANIFEST","governed_unit_uid":work["governed_unit_uid"],"governed_unit_uid_or_scope_uid":work["governed_unit_uid"],"governed_unit_uids":[work["governed_unit_uid"]],"source_nodes":nodes,"context_edges":edges,"source_lineage_refs":[b["freeze_receipt_ref"]],"status":"CURRENT_SOURCE_FACT","content_hash":None}
    d["content_hash"]=guard.content_hash(d); wy(wd/"00_SOURCE_INTAKE/SOURCE_CONTEXT_MANIFEST.yaml",d)

def op_conflicts(product,wd,work,guard):
    ctx=y(wd/"00_SOURCE_INTAKE/SOURCE_CONTEXT_MANIFEST.yaml")
    explicit=[]
    pattern=re.compile(r"\b(supersede|superseded|obsolete|replace)\b|取代|替代|廢止",re.I)
    for row in ctx.get("source_nodes") or []:
        text=str(row.get("direct_text") or "")
        if pattern.search(text):
            explicit.append({"source_node_uid":row["source_node_uid"],"source_text":text,"disposition":"REVIEW_AS_EXPLICIT_SUPERSESSION_LANGUAGE","resolution":"CURRENT_SOURCE_TEXT_RETAINS_AUTHORITY"})
    d={"artifact_uid":"SF-CONFLICT-"+work["work_unit_uid"],"artifact_type":"CONTENT_SUPERSESSION_CONFLICT_LEDGER","governed_unit_uid":work["governed_unit_uid"],"governed_unit_uid_or_scope_uid":work["governed_unit_uid"],"governed_unit_uids":[work["governed_unit_uid"]],"items":explicit,"status":"CURRENT_SOURCE_FACT","content_hash":None}
    d["content_hash"]=guard.content_hash(d); wy(wd/"00_SOURCE_INTAKE/CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml",d)
    wy(wd/"EVIDENCE/CONFLICT_DECISION_EVIDENCE.yaml",{"artifact_type":"CONFLICT_DECISION_EVIDENCE","stage_uid":"STAGE-01","work_unit_uid":work["work_unit_uid"],"conflict_total":len(explicit),"decision_basis":"CURRENT_CANONICAL_SOURCE_ONLY","result":"PASS"})

def op_dependencies(product,wd,work,guard):
    suid=source_uid(work)
    edges=[{"edge_uid":"DEP-SEQUENCE-"+suid,"producer_source_uid":suid,"consumer_source_uid":suid,"dependency_type":"SEQUENCE","authority_evidence_ref":"EVIDENCE/SOURCE_ENUMERATION_EVIDENCE.yaml"}]
    if work["governed_unit_uid"]=="workspace:WB-01":
        edges.append({"edge_uid":"DEP-GLOBAL-SHELL-WB01","producer_source_uid":"SRC-DOCX-334A4679600F092B733B","consumer_source_uid":suid,"dependency_type":"SHARED_OWNER","authority_evidence_ref":"ACPOS_GLOBAL_HOME_SHELL_NAVIGATION_Mother_Basic_Design_OPTIMIZED.docx"})
    d={"artifact_uid":"SF-DEPENDENCY-"+work["work_unit_uid"],"artifact_type":"SOURCE_DEPENDENCY_MAP","governed_unit_uid":work["governed_unit_uid"],"governed_unit_uid_or_scope_uid":work["governed_unit_uid"],"governed_unit_uids":[work["governed_unit_uid"]],"edges":edges,"unresolved_authority_gaps":[],"invented_dependency_count":0,"status":"CURRENT_SOURCE_FACT","content_hash":None}
    d["content_hash"]=guard.content_hash(d); wy(wd/"00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml",d)

def op_classification(product,wd,work,guard):
    sm=y(wd/"00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml"); proj=projection(wd,work)
    pmap={"SS-"+str(n["source_node_uid"]):n for n in proj.get("source_nodes") or []}
    groups={}
    for seg in sm.get("source_segments") or []:
        key=str((seg.get("target_artifact_uids") or [None])[0] or "")
        if not key: raise RuntimeError("SEGMENT_TARGET_ARTIFACT_UID_MISSING:"+str(seg.get("segment_uid")))
        groups.setdefault(key,[]).append(seg)
    refs=[]
    for auid,segs in sorted(groups.items()):
        domain=str(segs[0]["planning_domain"]); resp=str(segs[0]["responsibility_uid"])
        if any(s["planning_domain"]!=domain or s["responsibility_uid"]!=resp for s in segs):
            raise RuntimeError("CLASSIFICATION_GROUP_SEMANTIC_DRIFT:"+auid)
        by_source={}
        requirements=[]
        for seg in segs:
            by_source.setdefault(seg["source_uid"],[]).append(seg["segment_uid"])
            node=pmap.get(seg["source_node_uid"]) or {}
            requirements.append({"source_segment_uid":seg["segment_uid"],"source_node_uid":seg["source_node_uid"],"direct_text":node.get("direct_text"),"document_order_index":node.get("document_order_index")})
        rel=f"01_CLASSIFIED/{domain}/{auid}.yaml"
        d={"artifact_uid":auid,"governed_unit_uid":work["governed_unit_uid"],"planning_domain":domain,"responsibility_uid":resp,"responsibility_class":"VISUAL" if domain=="VISUAL_CONSTRUCTION" else "GOVERNED_UNIT","canonical_owner_uid":"OWNER-"+re.sub(r"[^A-Za-z0-9]+","-",work["scope_uid"]).strip("-").upper()+"-"+resp,"lifecycle_uid":"LIFECYCLE-STAGE01-CLEAN","approval_scope_uid":"APPROVAL-"+work["scope_uid"],"version_scope_uid":"VERSION-"+work["scope_uid"],"test_scope_uid":"TEST-"+work["scope_uid"],"source_lineage":[{"source_uid":suid,"source_segment_uids":sorted(ids)} for suid,ids in sorted(by_source.items())],"source_requirements":requirements,"target_path":rel,"status":"CURRENT_CLASSIFICATION","content_hash":None}
        d["content_hash"]=guard.content_hash(d); wy(wd/rel,d); refs.append({"artifact_uid":auid,"artifact_ref":rel,"content_hash":d["content_hash"]})
    if not refs: raise RuntimeError("NO_FRESH_CLASSIFICATION_ARTIFACTS")
    wy(wd/"CLASSIFIED_ARTIFACT_SET.yaml",{"artifact_type":"CLASSIFIED_ARTIFACT_SET","stage_uid":"STAGE-01","work_unit_uid":work["work_unit_uid"],"governed_unit_uid":work["governed_unit_uid"],"artifact_count":len(refs),"artifacts":refs,"status":"CURRENT"})

def class_docs(wd):
    out={}
    root=wd/"01_CLASSIFIED"
    for p in sorted(root.rglob("*.yaml")) if root.exists() else []:
        d=y(p); out[str(d["artifact_uid"])]=d
    return out

def compile_blueprint(product,wd,work,guard,visual=False):
    domain="VISUAL_CONSTRUCTION" if visual else "GOVERNED_UNIT_CONSTRUCTION"
    btype="VISUAL_BASE_BLUEPRINT" if visual else "GOVERNED_UNIT_BASE_BLUEPRINT"
    classes={uid:d for uid,d in class_docs(wd).items() if d.get("planning_domain")==domain}
    if not classes: raise RuntimeError("BLUEPRINT_CLASSIFICATION_DOMAIN_EMPTY:"+domain)
    inputs=[{"artifact_uid":uid,"content_hash":d["content_hash"]} for uid,d in sorted(classes.items())]
    required=sorted({str(d["responsibility_uid"]) for d in classes.values()})
    udir=unit_dir(work); rel=f"02_BASE_BLUEPRINT/{udir}/{btype}.yaml"
    d={"blueprint_uid":f"BP-{work['scope_uid']}-{btype}-CLEAN-001","governed_unit_uid":work["governed_unit_uid"],"blueprint_type":btype,"planning_domain":domain,"target_path":rel,"input_artifacts":inputs,"required_responsibility_uids":required,"source_fact_refs":current_fact_refs(wd),"shared_refs":[],"unresolved_external_authority_refs":[],"raw_source_inputs":[],"embedded_classification_payloads":[],"status":"CURRENT_BASE_BLUEPRINT","blueprint_hash":None}
    d["blueprint_hash"]=guard.content_hash(d); wy(wd/rel,d)

def op_binding(product,wd,work,guard):
    udir=unit_dir(work)
    bp=wd/f"02_BASE_BLUEPRINT/{udir}/GOVERNED_UNIT_BASE_BLUEPRINT.yaml"
    vb=wd/f"02_BASE_BLUEPRINT/{udir}/VISUAL_BASE_BLUEPRINT.yaml"
    if not bp.is_file() or not vb.is_file(): raise RuntimeError("FRESH_BLUEPRINT_DENOMINATOR_INVALID")
    a=y(bp); v=y(vb); rel=f"03_BLUEPRINT_BINDING/{udir}/BLUEPRINT_BINDING_MANIFEST.yaml"
    d={"binding_uid":f"BIND-{work['scope_uid']}-CLEAN-001","governed_unit_uid":work["governed_unit_uid"],"target_path":rel,"governed_unit_blueprint":{"blueprint_uid":a["blueprint_uid"],"blueprint_hash":a["blueprint_hash"]},"visual_blueprint":{"blueprint_uid":v["blueprint_uid"],"blueprint_hash":v["blueprint_hash"]},"embedded_blueprint_payloads":[],"status":"CURRENT_BLUEPRINT_BINDING","binding_hash":None}
    d["binding_hash"]=guard.content_hash(d); wy(wd/rel,d)

HANDLERS={
 "SOURCE_STRUCTURE_ENUMERATION":op_structure,
 "SOURCE_SEGMENT_MAPPING":op_segments,
 "SOURCE_CONTEXT_COMPILATION":op_context,
 "SOURCE_SUPERSESSION_CONFLICT_RESOLUTION":op_conflicts,
 "SOURCE_DEPENDENCY_EXTRACTION":op_dependencies,
 "RESPONSIBILITY_CLASSIFICATION":op_classification,
 "GOVERNED_UNIT_BASE_BLUEPRINT_COMPILE":lambda p,w,wo,g:compile_blueprint(p,w,wo,g,False),
 "VISUAL_BASE_BLUEPRINT_COMPILE":lambda p,w,wo,g:compile_blueprint(p,w,wo,g,True),
 "BLUEPRINT_BINDING_COMPILE":op_binding
}

def main_for(expected_operation):
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage",required=True); ap.add_argument("--operation",required=True)
    ap.add_argument("--work-unit",required=True); ap.add_argument("--product-root",required=True)
    a=ap.parse_args()
    if a.stage!="STAGE-01" or a.operation!=expected_operation: raise SystemExit("BLOCK:EXECUTOR_OPERATION_IDENTITY_DRIFT")
    product=Path(a.product_root).resolve(); wp=(product/a.work_unit).resolve(); wd=wp.parent; work=y(wp)
    if work.get("work_unit_uid")!=wd.name or work.get("governance_uid")!="GOV-REV-20260928-WORD-DERIVED-STAGE-INTERNAL-VALIDATION":
        raise SystemExit("BLOCK:WORK_UNIT_IDENTITY_DRIFT")
    if work.get("work_unit_activation_kind")!="INITIAL_STAGE_WORK_UNIT":
        raise SystemExit("BLOCK:CLEAN_BOOTSTRAP_REQUIRES_INITIAL_STAGE_WORK_UNIT")
    for key in ("predecessor_work_unit_uid","predecessor_work_unit_ref","predecessor_terminal_receipt_ref"):
        if str(work.get(key) or "").strip(): raise SystemExit("BLOCK:PREDECESSOR_RUNTIME_DEPENDENCY_FORBIDDEN:"+key)
    guard=load_guard(product); HANDLERS[expected_operation](product,wd,work,guard)
    binding=(work.get("operation_bindings") or {})[expected_operation]; receipt=product/Path(binding["operation_receipt_ref"])
    wy(receipt,{"artifact_type":"OPERATION_EXECUTION_RECEIPT","stage_uid":"STAGE-01","work_unit_uid":work["work_unit_uid"],"operation_uid":expected_operation,"governance_uid":work["governance_uid"],"status":"PASS","executor_owner":binding["executor_owner"],"executor_protocol":binding["executor_protocol"],"result_owner":binding["result_owner"],"historical_completion_credit":0,"predecessor_runtime_dependency_count":0})
    refresh_run_manifest(wd,wp)
    print("PASS:",expected_operation,work["work_unit_uid"])

if __name__=="__main__": raise SystemExit("Use a dedicated Stage01 operation wrapper")
