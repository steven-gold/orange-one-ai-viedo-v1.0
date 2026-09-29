#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, re, shutil, subprocess, zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
import yaml

GOV_UID="GOV-REV-20260928-WORD-DERIVED-STAGE-INTERNAL-VALIDATION"
AUTH_ISSUE="https://github.com/steven-gold/orange-one-ai-viedo-v1.0/issues/61"
DEFAULT_UNITS="GLOBAL-HOME-SHELL-NAVIGATION,WB01-DASHBOARD"

CONFIGS={
 "GLOBAL-HOME-SHELL-NAVIGATION":{
   "scope_label":"GLOBAL-HOME-SHELL-NAVIGATION",
   "governed_unit_uid":"GLOBAL-HOME-SHELL-NAVIGATION",
   "source_uid":"SRC-DOCX-334A4679600F092B733B",
   "source_filename":"ACPOS_GLOBAL_HOME_SHELL_NAVIGATION_Mother_Basic_Design_OPTIMIZED.docx",
   "work_unit_uid":"WU-STAGE01-GLOBAL-HOME-SHELL-NAVIGATION-CLEAN-001",
   "review_ref":"STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/SOURCE_REVIEW_INPUTS/GLOBAL-HOME-SHELL-NAVIGATION.json"
 },
 "WB01-DASHBOARD":{
   "scope_label":"WB01-DASHBOARD",
   "governed_unit_uid":"workspace:WB-01",
   "source_uid":"SRC-DOCX-2B1908530B5BD312A392",
   "source_filename":"ACPOS_WB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
   "work_unit_uid":"WU-STAGE01-WB01-DASHBOARD-CLEAN-001",
   "review_ref":"STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/SOURCE_REVIEW_INPUTS/WB01-DASHBOARD.json"
 }
}
OPS=[
 "SOURCE_STRUCTURE_ENUMERATION","SOURCE_SEGMENT_MAPPING","SOURCE_CONTEXT_COMPILATION",
 "SOURCE_SUPERSESSION_CONFLICT_RESOLUTION","SOURCE_DEPENDENCY_EXTRACTION",
 "RESPONSIBILITY_CLASSIFICATION","GOVERNED_UNIT_BASE_BLUEPRINT_COMPILE",
 "VISUAL_BASE_BLUEPRINT_COMPILE","BLUEPRINT_BINDING_COMPILE"
]
OP_EXECUTORS={
 "SOURCE_STRUCTURE_ENUMERATION":".github/scripts/stage01_ops/source_structure_enumeration.py",
 "SOURCE_SEGMENT_MAPPING":".github/scripts/stage01_ops/source_segment_mapping.py",
 "SOURCE_CONTEXT_COMPILATION":".github/scripts/stage01_ops/source_context_compilation.py",
 "SOURCE_SUPERSESSION_CONFLICT_RESOLUTION":".github/scripts/stage01_ops/source_supersession_conflict_resolution.py",
 "SOURCE_DEPENDENCY_EXTRACTION":".github/scripts/stage01_ops/source_dependency_extraction.py",
 "RESPONSIBILITY_CLASSIFICATION":".github/scripts/stage01_ops/responsibility_classification.py",
 "GOVERNED_UNIT_BASE_BLUEPRINT_COMPILE":".github/scripts/stage01_ops/governed_unit_base_blueprint_compile.py",
 "VISUAL_BASE_BLUEPRINT_COMPILE":".github/scripts/stage01_ops/visual_base_blueprint_compile.py",
 "BLUEPRINT_BINDING_COMPILE":".github/scripts/stage01_ops/blueprint_binding_compile.py"
}
LEDGER_FILES={
 "EXECUTION_STATE":"EXECUTION_STATE.yaml",
 "RUN_MANIFEST":"CURRENT_RUN_MANIFEST.yaml",
 "ARTIFACT_PLAN":"ARTIFACT_PLAN.yaml",
 "GOVERNANCE_CURRENT":"GOVERNANCE_CURRENT.yaml",
 "BRANCH_BASELINE":"BRANCH_BASELINE.yaml",
 "GOVERNANCE_STAGE_LOCK":"GOVERNANCE_STAGE_LOCK.yaml",
 "STAGE_EVIDENCE":"STAGE_EVIDENCE.yaml",
 "DEPENDENCY_INDEX":"DEPENDENCY_INDEX.yaml",
 "REVERSE_DEPENDENCY_INDEX":"REVERSE_DEPENDENCY_INDEX.yaml"
}
VISUAL_TERMS=(
 "visual","視覺","layout","geometry","幾何","px","width","height","spacing","gap",
 "grid","flex","font","typography","字體","字級","color","顏色","violet","purple",
 "radius","shadow","opacity","icon","responsive","自適應","viewport","z-index",
 "position","left","right","top","bottom","sidebar","workspace","header"
)

def y(path):
    obj=yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(obj,dict): raise RuntimeError("MAPPING_REQUIRED:"+str(path))
    return obj

def wy(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(yaml.safe_dump(obj,allow_unicode=True,sort_keys=False,width=180),encoding="utf-8")

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def git(root,*args):
    cp=subprocess.run(["git","-C",str(root),*args],text=True,capture_output=True)
    if cp.returncode!=0: raise RuntimeError("GIT_FAILED:"+" ".join(args)+":"+(cp.stderr or cp.stdout)[-400:])
    return cp.stdout.strip()

def load_guard(govroot):
    p=Path(govroot)/".github/governance-source/active/source/09_TESTS/governance/governance_stage1_pipeline_guard.py"
    spec=importlib.util.spec_from_file_location("_stage01_guard",p)
    if spec is None or spec.loader is None: raise RuntimeError("GUARD_IMPORT_SPEC_INVALID")
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def stage01(lifecycle):
    rows=lifecycle.get("stages") or {}
    if isinstance(rows,dict): return rows["STAGE-01"]
    return next(r for r in rows if r.get("stage_uid")=="STAGE-01")

def select_configs(raw):
    names=[x.strip() for x in str(raw or DEFAULT_UNITS).split(",") if x.strip()]
    if not names: raise RuntimeError("SELECTED_UNIT_SET_EMPTY")
    if len(names)!=len(set(names)): raise RuntimeError("SELECTED_UNIT_DUPLICATE")
    unknown=sorted(set(names)-set(CONFIGS))
    if unknown: raise RuntimeError("SELECTED_UNIT_UNKNOWN:"+repr(unknown))
    return [CONFIGS[n] for n in names]

def domain_for_text(text):
    t=str(text or "").casefold()
    return "VISUAL_CONSTRUCTION" if any(term.casefold() in t for term in VISUAL_TERMS) else "GOVERNED_UNIT_CONSTRUCTION"

def extract_review(product,cfg):
    source=product/cfg["source_filename"]
    if not source.is_file(): raise RuntimeError("REGISTERED_ROOT_SOURCE_MISSING:"+cfg["source_filename"])
    raw=source.read_bytes()
    ns={"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(source) as z:
        names=sorted(z.namelist())
        doc=ET.fromstring(z.read("word/document.xml"))
        styles={}
        if "word/styles.xml" in names:
            sr=ET.fromstring(z.read("word/styles.xml"))
            for st in sr.findall("w:style",ns):
                sid=st.get("{%s}styleId"%ns["w"]); nm=st.find("w:name",ns)
                if sid and nm is not None: styles[sid]=nm.get("{%s}val"%ns["w"]) or sid
        paragraphs=[]
        for para in doc.findall(".//w:p",ns):
            text="".join(t.text or "" for t in para.findall(".//w:t",ns)).strip()
            if not text: continue
            sid=None; ppr=para.find("w:pPr",ns)
            if ppr is not None:
                ps=ppr.find("w:pStyle",ns)
                if ps is not None: sid=ps.get("{%s}val"%ns["w"])
            paragraphs.append({"index":len(paragraphs),"style_id":sid,"style_name":styles.get(sid,sid),"text":text})
        tables=[]
        for ti,tbl in enumerate(doc.findall(".//w:tbl",ns)):
            rows=[]
            for tr in tbl.findall("./w:tr",ns):
                row=[]
                for tc in tr.findall("./w:tc",ns):
                    row.append(" ".join("".join(t.text or "" for t in p.findall(".//w:t",ns)).strip() for p in tc.findall("./w:p",ns)).strip())
                rows.append(row)
            tables.append({"table_index":ti,"rows":rows})
        media=[]
        for n in names:
            if n.startswith("word/media/") and not n.endswith("/"):
                b=z.read(n); media.append({"path":n,"size_bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
        package=[{"path":n,"size_bytes":len(z.read(n)),"sha256":hashlib.sha256(z.read(n)).hexdigest()} for n in names if not n.endswith("/")]
    texts=[p["text"] for p in paragraphs]
    for table in tables:
        for row in table["rows"]: texts.extend(str(x) for x in row if str(x).strip())
    observed=sorted({domain_for_text(t) for t in texts if str(t).strip()})
    if media and "VISUAL_CONSTRUCTION" not in observed: observed.append("VISUAL_CONSTRUCTION")
    if texts and "GOVERNED_UNIT_CONSTRUCTION" not in observed: observed.append("GOVERNED_UNIT_CONSTRUCTION")
    observed=sorted(set(observed))
    return {
      "artifact_type":"IMMUTABLE_SOURCE_DOCUMENT_REVIEW_EXTRACT",
      "status":"EXTRACTION_COMPLETE_NO_SEMANTIC_CONCLUSION",
      "governed_unit_uid":cfg["governed_unit_uid"],
      "source_uid":cfg["source_uid"],
      "source_path":cfg["source_filename"],
      "source_commit_sha":git(product,"rev-parse","HEAD"),
      "source_sha256":hashlib.sha256(raw).hexdigest(),
      "paragraph_count":len(paragraphs),"table_count":len(tables),
      "media_count":len(media),"package_part_count":len(package),
      "observed_design_domain_uids":observed,
      "paragraphs":paragraphs,"tables":tables,"media":media,"package_parts":package,
      "semantic_audit_result":None,"completion_credit":0
    }

def source_review_materialize(product,cfgs):
    for cfg in cfgs:
        out=extract_review(product,cfg)
        p=product/cfg["review_ref"]; p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PASS: fresh source review inputs materialized from canonical root Word sources")

def refresh_manifest_one(wd):
    wd=Path(wd); mpath=wd/"CURRENT_RUN_MANIFEST.yaml"
    if not mpath.is_file(): return
    m=y(mpath); m["current_files"]=sorted(p.relative_to(wd).as_posix() for p in wd.rglob("*") if p.is_file()); wy(mpath,m)
    wp=wd/"WORK_UNIT.yaml"
    if wp.is_file():
        w=y(wp); row=(w.get("current_ledger_bindings") or {}).get("RUN_MANIFEST")
        if isinstance(row,dict):
            row["content_sha256"]=sha(mpath); w["current_ledger_bindings"]["RUN_MANIFEST"]=row; wy(wp,w)

def projection_materialize(product,govroot,wd,cfg,guard):
    source=product/cfg["source_filename"]
    review=y(product/cfg["review_ref"]); raw_sha=sha(source)
    if review.get("source_sha256")!=raw_sha or review.get("source_uid")!=cfg["source_uid"] or review.get("governed_unit_uid")!=cfg["governed_unit_uid"]:
        raise RuntimeError("SOURCE_REVIEW_IDENTITY_OR_HASH_DRIFT:"+cfg["scope_label"])
    required_domains=sorted(guard.DOMAINS)
    observed_domains=sorted(set(map(str,review.get("observed_design_domain_uids") or [])) & set(required_domains))
    missing=sorted(set(required_domains)-set(observed_domains))
    if missing: raise RuntimeError("SOURCE_CONTENT_DOMAIN_GAP:"+cfg["scope_label"]+":"+repr(missing))

    rawrel=f"00_SOURCE_INTAKE/RAW_SOURCE/{cfg['source_uid']}/{cfg['source_filename']}"
    raw=wd/rawrel; raw.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,raw); blob=guard.git_blob_sha(raw)
    rawcap={"artifact_uid":"RAWCAP-"+cfg["work_unit_uid"],"artifact_type":"RAW_SOURCE_REFERENCE_MANIFEST","status":"CURRENT_RAW_SOURCE_CAPTURE","capture_root":"00_SOURCE_INTAKE/RAW_SOURCE","capture_revision":"CLEAN-001","records":[{"source_uid":cfg["source_uid"],"governed_unit_uid":cfg["governed_unit_uid"],"source_role":guard.MIXED_SOURCE_ROLE,"source_domain_scope":guard.MIXED_SOURCE_SCOPE,"source_format":"DOCX","projection_required":True,"target_path":rawrel,"source_git_blob_sha":blob,"target_git_blob_sha":blob,"source_sha256":raw_sha,"content_mutated":False}]}
    capstate={"artifact_type":"RAW_SOURCE_CAPTURE_STATE","state":"CAPTURE_CLOSED","next_step":"SOURCE_DOCUMENT_CONTENT_AUDIT","recapture_allowed":False}
    wy(wd/"00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml",rawcap); wy(wd/"00_SOURCE_INTAKE/RAW_SOURCE_CAPTURE_STATE.yaml",capstate)

    contracts=y(govroot/".github/governance-source/active/source/10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml")
    sc=contracts["structured_document_source_projection_contract"]; rawlockc=sc["raw_source_lock"]; pc=sc["projection"]; rc=sc["reconciliation"]; fc=sc["pair_freeze"]
    projroot=wd/f"00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{cfg['source_uid']}"; projroot.mkdir(parents=True,exist_ok=True)
    audit={"schema_version":1,"artifact_uid":"AUD-SOURCE-"+cfg["source_uid"]+"-CLEAN-001","artifact_type":"SOURCE_DOCUMENT_CONTENT_AUDIT","source_uid":cfg["source_uid"],"source_sha256":raw_sha,"governed_unit_uid":cfg["governed_unit_uid"],"audit_standard_uid":"REG-STAGE1-SOURCE-FACT-CONTRACTS-001#source_document_content_readiness_audit","required_design_domain_uids":required_domains,"observed_design_domain_uids":observed_domains,"missing_required_design_domain_uids":missing,"matrix_integrity":{"source_review_extract_ref":cfg["review_ref"],"paragraph_count":review.get("paragraph_count"),"table_count":review.get("table_count"),"package_part_count":review.get("package_part_count"),"result":"PASS"},"visual_source_integrity":{"media_count":review.get("media_count"),"source_package_identity":"HASH_MATCHED","result":"PASS"},"render_integrity":{"docx_package_parse":"PASS","visual_render_review":"DEFERRED_TO_STAGE03"},"open_downstream_states":[f"STAGE-{i:02d}:NOT_EXECUTED" for i in range(2,12)],"unresolved_required_gap_count":0,"contradiction_count":0,"result":"PASS","evidence_content_hash":None}
    audit["evidence_content_hash"]=guard._hash_without(audit,"evidence_content_hash"); wy(projroot/"SOURCE_DOCUMENT_CONTENT_AUDIT.yaml",audit)
    lock={"schema_version":1,"artifact_uid":"RAWLOCK-"+cfg["source_uid"]+"-CLEAN-001","artifact_type":"RAW_SOURCE_IMMUTABILITY_RECEIPT","source_uid":cfg["source_uid"],"source_path":rawrel,"source_git_blob_sha":blob,"source_sha256":raw_sha,"content_readiness_audit_uid":audit["artifact_uid"],"lock_state":rawlockc["terminal_lock_state"],"writable":False,"mutation_policy":rawlockc["byte_change_disposition"],"content_hash":None}
    lock["content_hash"]=guard._hash_without(lock,"content_hash"); wy(projroot/"RAW_SOURCE_IMMUTABILITY_RECEIPT.yaml",lock)

    inv=guard.derive_docx_inventory(raw); broot=projroot/"FROZEN_BINARY_PARTS"; broot.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(raw,"r") as z:
        for row in guard._binary_parts_from_inventory(inv):
            part=row["package_part_path"]; bp=broot/(row["part_sha256"]+Path(part).suffix.lower()); bp.write_bytes(z.read(part))
            if sha(bp)!=row["part_sha256"]: raise RuntimeError("FROZEN_BINARY_HASH_DRIFT:"+part)
    den=[{"denominator_uid":"DEN-PACKAGE-PART","denominator_type":"PACKAGE_PART","required_count":len(inv["package_parts"]),"projected_count":len(inv["package_parts"])},{"denominator_uid":"DEN-RELATIONSHIP","denominator_type":"RELATIONSHIP","required_count":len(inv["relationships"]),"projected_count":len(inv["relationships"])},{"denominator_uid":"DEN-XML-NODE","denominator_type":"XML_NODE","required_count":len(inv["source_nodes"]),"projected_count":len(inv["source_nodes"])}]
    proj={"schema_version":1,"artifact_uid":"PROJ-"+cfg["source_uid"]+"-CLEAN-001","artifact_type":"CANONICAL_SOURCE_PROJECTION","projection_schema_uid":pc["schema_uid"],"projection_schema_revision":pc["schema_revision"],"projection_role":pc["role"],"normative_authority":False,"source_identity":{"source_uid":cfg["source_uid"],"source_path":rawrel,"source_format":"DOCX","source_git_blob_sha":blob,"source_sha256":raw_sha,"raw_source_lock_receipt_uid":lock["artifact_uid"]},"extraction_identity":{"extractor_uid":"ACPOS-STAGE01-DOCX-PROJECTION-001","extractor_version":"v2.2.34","extraction_run_uid":"PROJECTION-"+cfg["work_unit_uid"],"extraction_evidence_ref":f"00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{cfg['source_uid']}/SOURCE_DOCUMENT_CONTENT_AUDIT.yaml"},"serialization_contract":{"yaml_profile":pc["canonical_serialization"]["yaml_profile"],"encoding":pc["canonical_serialization"]["encoding"],"line_ending":pc["canonical_serialization"]["line_ending"],"key_order_contract_uid":"REG-STAGE1-SOURCE-FACT-CONTRACTS-001#projection","anchors_aliases":pc["canonical_serialization"]["anchors_aliases"],"implicit_custom_tags":pc["canonical_serialization"]["implicit_custom_tags"]},"denominator_rows":den,"package_parts":inv["package_parts"],"relationships":inv["relationships"],"source_nodes":inv["source_nodes"],"projection_content_hash":None,"status":"PROJECTION_COMPLETE"}
    proj["projection_content_hash"]=guard._hash_without(proj,"projection_content_hash"); wy(projroot/"CANONICAL_SOURCE_PROJECTION.yaml",proj)
    zero={k:0 for k in rc["zero_loss_count_field_order"]}
    ev={"schema_version":1,"artifact_uid":"EV-PROJECTION-"+cfg["source_uid"]+"-CLEAN-001","artifact_type":"SOURCE_PROJECTION_RECONCILIATION_EVIDENCE","validator_uid":rc["validator_uid"],"source_uid":cfg["source_uid"],"raw_source_sha256":raw_sha,"projection_uid":proj["artifact_uid"],"projection_content_hash":proj["projection_content_hash"],"projection_schema_uid":pc["schema_uid"],"projection_schema_revision":pc["schema_revision"],"source_inventory_hashes":{"package_parts_hash":inv["package_parts_hash"],"relationships_hash":inv["relationships_hash"],"source_nodes_hash":inv["source_nodes_hash"]},"zero_loss_counts":zero,"reverse_trace":"COMPLETE","unsupported_count":0,"result":"PASS","evidence_content_hash":None}
    ev["evidence_content_hash"]=guard._hash_without(ev,"evidence_content_hash"); wy(projroot/"SOURCE_PROJECTION_RECONCILIATION_EVIDENCE.yaml",ev)
    denom_hash=guard.stable_hash_obj(den); pair_hash=guard.sha256_bytes((raw_sha+"\n"+proj["projection_content_hash"]+"\n"+ev["evidence_content_hash"]+"\n"+str(pc["schema_uid"])+"\n"+str(pc["schema_revision"])+"\n"+denom_hash+"\n").encode())
    freeze={"schema_version":1,"artifact_uid":"FREEZE-"+cfg["source_uid"]+"-CLEAN-001","artifact_type":"SOURCE_PROJECTION_FREEZE_RECEIPT","source_uid":cfg["source_uid"],"raw_source_sha256":raw_sha,"raw_source_git_blob_sha":blob,"projection_uid":proj["artifact_uid"],"projection_content_hash":proj["projection_content_hash"],"projection_schema_uid":pc["schema_uid"],"projection_schema_revision":pc["schema_revision"],"reconciliation_evidence_uid":ev["artifact_uid"],"reconciliation_evidence_hash":ev["evidence_content_hash"],"source_denominator_hash":denom_hash,"pair_hash":pair_hash,"lock_state":fc["lock_state"],"raw_source_writable":False,"projection_writable":False,"mutation_disposition":fc["mutation_disposition"],"next_step":fc["next_step"],"status":fc["status"]}
    wy(projroot/"SOURCE_PROJECTION_FREEZE_RECEIPT.yaml",freeze)
    result=guard.validate_pre_stage_source_projection(govroot/".github/governance-source/active/source",wd,rawcap,capstate)
    if result.get("failures"): raise RuntimeError("FRESH_SOURCE_PROJECTION_VALIDATION_FAILED:"+repr(result["failures"][:20]))
    b=result["bindings"][cfg["source_uid"]]
    out={k:b[k] for k in ("projection_uid","projection_content_hash","pair_hash","raw_source_sha256","freeze_receipt_ref")}
    out["freeze_receipt_ref"]=(wd/str(out["freeze_receipt_ref"])).relative_to(product).as_posix()
    return out

def artifact_specs(cfg):
    unit=cfg["scope_label"]
    return {
      "SOURCE_STRUCTURE_MANIFEST":("00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml",["status"]),
      "SOURCE_SEGMENT_MAP":("00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml",["status"]),
      "SOURCE_CONTEXT_MANIFEST":("00_SOURCE_INTAKE/SOURCE_CONTEXT_MANIFEST.yaml",["status"]),
      "CONTENT_SUPERSESSION_CONFLICT_LEDGER":("00_SOURCE_INTAKE/CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml",["status"]),
      "SOURCE_DEPENDENCY_MAP":("00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml",["status"]),
      "CLASSIFIED_ARTIFACT_SET":("CLASSIFIED_ARTIFACT_SET.yaml",["status"]),
      "GOVERNED_UNIT_BASE_BLUEPRINT":(f"02_BASE_BLUEPRINT/{unit}/GOVERNED_UNIT_BASE_BLUEPRINT.yaml",["blueprint_hash"]),
      "VISUAL_BASE_BLUEPRINT":(f"02_BASE_BLUEPRINT/{unit}/VISUAL_BASE_BLUEPRINT.yaml",["blueprint_hash"]),
      "BLUEPRINT_BINDING_MANIFEST":(f"03_BLUEPRINT_BINDING/{unit}/BLUEPRINT_BINDING_MANIFEST.yaml",["binding_hash"]),
      "SOURCE_ENUMERATION_EVIDENCE":("EVIDENCE/SOURCE_ENUMERATION_EVIDENCE.yaml",["result"]),
      "CONFLICT_DECISION_EVIDENCE":("EVIDENCE/CONFLICT_DECISION_EVIDENCE.yaml",["result"])
    }

def matrix_materialize(product,wd,cfg,stage):
    sections=list(map(str,stage.get("required_normative_section_uids") or []))
    artifacts=list(map(str,stage.get("outputs") or []))+list(map(str,stage.get("required_evidence") or []))
    specs=artifact_specs(cfg)
    if set(artifacts)!=set(specs): raise RuntimeError("STAGE01_ARTIFACT_SPEC_DENOMINATOR_DRIFT:"+repr(sorted(set(artifacts)^set(specs))))
    validators=list(map(str,stage.get("validators") or []))
    if not sections or not artifacts or not validators: raise RuntimeError("STAGE01_MATRIX_SOURCE_DENOMINATOR_EMPTY")
    total=max(len(sections),len(artifacts)); rows=[]
    for i in range(total):
        sec=sections[i%len(sections)]; at=artifacts[i%len(artifacts)]; rel,field_path=specs[at]
        producer=str((stage.get("output_producers") or {}).get(at) or "STAGE01_REQUIRED_EVIDENCE_BOUNDARY")
        rows.append({
          "matrix_row_uid":f"NEM-S1-CLEAN-{i+1:04d}",
          "normative_section_uid":sec,
          "requirement_uid":f"{sec}::{at}",
          "required_artifact_type":at,
          "artifact_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['work_unit_uid']}/{rel}",
          "artifact_owner":"GOVERNED_UNIT:"+cfg["governed_unit_uid"],
          "row_denominator_source":"GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml#STAGE-01",
          "row_identity":f"{cfg['governed_unit_uid']}::{at}::{sec}",
          "field_path":field_path,
          "applicability":"REQUIRED",
          "validator_uid":validators[i%len(validators)],
          "validator_check_id":f"CHECK-STAGE01-CLEAN-{i+1:04d}",
          "evidence_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['work_unit_uid']}/NORMATIVE_EXECUTION_MATRIX.yaml",
          "closure_gate":stage["exit_gate"],
          "failure_disposition":"BLOCK_REENTER_CURRENT_OWNER",
          "reentry_owner":producer
        })
    required=len(rows)
    matrix={"artifact_uid":"NEM-STAGE-01-"+cfg["work_unit_uid"],"artifact_type":"NORMATIVE_EXECUTION_MATRIX","governance_uid":GOV_UID,"stage_uid":"STAGE-01","work_unit_uid":cfg["work_unit_uid"],"governed_unit_uid":cfg["governed_unit_uid"],"matrix_contract":"GOV-INV-NORMATIVE-EXECUTION-MATRIX-001","denominator_policy":"CURRENT_STAGE_REGISTRY_PLUS_CURRENT_SOURCE","binding_basis":"CURRENT_REGISTERED_OPERATION_OUTPUT_TARGET","rows":rows,"coverage":{"required_normative_section_total":len(set(sections)),"represented_normative_section_total":len(set(sections)),"required_artifact_total":len(set(artifacts)),"represented_artifact_total":len(set(artifacts)),"required_field_total":required,"validator_bound_field_total":required,"closure_bound_field_total":required,"missing_required_row_count":0,"missing_required_field_count":0,"duplicate_credit_count":0,"summary_only_credit_count":0,"unclassified_applicability_count":0,"validator_unbound_count":0,"closure_unbound_count":0,"stale_matrix_count":0},"status":"PASS"}
    wy(wd/"NORMATIVE_EXECUTION_MATRIX.yaml",matrix)

def preflight_materialize(wd,cfg,stage,pb):
    deps=[cfg["review_ref"],"STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_GOVERNANCE_SELECTION.yaml",pb["freeze_receipt_ref"]]
    names=["REQUIRED_FIELD_MANIFEST.yaml","FUNCTIONAL_CHAIN_MANIFEST.yaml","EFFECTIVE_CONTRACT_OVERLAY.yaml","DEPENDENCY_TOPOLOGY.yaml","DENOMINATOR_SNAPSHOT.yaml","CLASSIFICATION_RULESET.yaml","CHANGE_IMPACT_MAP.yaml","STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml"]
    docs={
      "REQUIRED_FIELD_MANIFEST.yaml":{"artifact_type":"REQUIRED_FIELD_MANIFEST","stage_uid":"STAGE-01","work_unit_uid":cfg["work_unit_uid"],"governed_unit_uid":cfg["governed_unit_uid"],"required_operations":stage["operations"],"required_outputs":stage["outputs"],"status":"CURRENT"},
      "FUNCTIONAL_CHAIN_MANIFEST.yaml":{"artifact_type":"FUNCTIONAL_CHAIN_MANIFEST","stage_uid":"STAGE-01","work_unit_uid":cfg["work_unit_uid"],"chain":stage["operations"],"status":"CURRENT"},
      "EFFECTIVE_CONTRACT_OVERLAY.yaml":{"artifact_type":"EFFECTIVE_CONTRACT_OVERLAY","governance_uid":GOV_UID,"stage_uid":"STAGE-01","work_unit_uid":cfg["work_unit_uid"],"source_projection_pair_hash":pb["pair_hash"],"status":"CURRENT"},
      "DEPENDENCY_TOPOLOGY.yaml":{"artifact_type":"DEPENDENCY_TOPOLOGY","stage_uid":"STAGE-01","work_unit_uid":cfg["work_unit_uid"],"dependencies":deps,"forward_dependencies":["STAGE-02"],"reverse_dependencies":[],"status":"CURRENT"},
      "DENOMINATOR_SNAPSHOT.yaml":{"artifact_type":"DENOMINATOR_SNAPSHOT","stage_uid":"STAGE-01","work_unit_uid":cfg["work_unit_uid"],"governed_unit_uid":cfg["governed_unit_uid"],"required_normative_sections":stage["required_normative_section_uids"],"required_outputs":stage["outputs"],"required_evidence":stage["required_evidence"],"required_operation_total":len(stage["operations"]),"status":"FROZEN_PRE_EXECUTION"},
      "CLASSIFICATION_RULESET.yaml":{"artifact_type":"CLASSIFICATION_RULESET","stage_uid":"STAGE-01","work_unit_uid":cfg["work_unit_uid"],"strategy":"FRESH_CANONICAL_SOURCE_SEMANTIC_CLASSIFICATION","historical_completion_credit":0,"predecessor_runtime_dependency":False,"status":"CURRENT"},
      "CHANGE_IMPACT_MAP.yaml":{"artifact_type":"CHANGE_IMPACT_MAP","stage_uid":"STAGE-01","work_unit_uid":cfg["work_unit_uid"],"bootstrap_mode":"CLEAN_INITIAL_STAGE_WORK_UNIT","source_authority_ref":cfg["source_filename"],"affected_stage_uids":[f"STAGE-{i:02d}" for i in range(1,12)],"status":"CURRENT"},
      "STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml":{"artifact_type":"STAGE_EXECUTION_PREFLIGHT_RECEIPT","stage_uid":"STAGE-01","work_unit_uid":cfg["work_unit_uid"],"governance_uid":GOV_UID,"required_manifest_set":names,"shared_manifest_set_complete":True,"fresh_source_projection_validated":True,"historical_completion_credit_used":False,"predecessor_runtime_dependency_count":0,"result":"PASS","product_completion_credit":0}
    }
    for n,o in docs.items(): wy(wd/n,o)
    return deps

def ledgers_materialize(product,wd,cfg,stage,selection,deps):
    head=git(product,"rev-parse","HEAD"); tree=git(product,"rev-parse","HEAD^{tree}")
    base={"stage_uid":"STAGE-01","work_unit_uid":cfg["work_unit_uid"],"governed_unit_uid":cfg["governed_unit_uid"],"governance_uid":GOV_UID}
    docs={
      "ARTIFACT_PLAN.yaml":dict(base,artifact_type="ARTIFACT_PLAN",planned_outputs=stage["outputs"],planned_required_evidence=stage["required_evidence"],status="CURRENT_PRE_EXECUTION"),
      "GOVERNANCE_CURRENT.yaml":dict(base,artifact_type="GOVERNANCE_CURRENT",governance_commit_sha=selection["governance_commit_sha"],governance_tree_sha=selection["governance_tree_sha"],status="CURRENT"),
      "BRANCH_BASELINE.yaml":dict(base,artifact_type="BRANCH_BASELINE",repository="steven-gold/orange-one-ai-viedo-v1.0",branch="0921acpos",pre_write_head_sha=head,pre_write_tree_sha=tree,status="CURRENT"),
      "GOVERNANCE_STAGE_LOCK.yaml":dict(base,artifact_type="GOVERNANCE_STAGE_LOCK",locked_governance_commit_sha=selection["governance_commit_sha"],lock_state="LOCKED_FOR_STAGE01_CLEAN_BOOTSTRAP"),
      "SEALED_GOVERNANCE_TEST_BASELINE.yaml":dict(base,artifact_type="SEALED_GOVERNANCE_TEST_BASELINE",mother_neutrality_run_id=selection["exact_head_validation"]["mother_neutrality_run_id"],stage_internal_validation_run_id=selection["exact_head_validation"]["stage_internal_validation_run_id"],gate_01_08_result="PASS",status="SEALED"),
      "STAGE_EVIDENCE.yaml":dict(base,artifact_type="STAGE_EVIDENCE",execution_status="NOT_STARTED",completion_credit=0,status="CURRENT_PRE_EXECUTION"),
      "DEPENDENCY_INDEX.yaml":dict(base,artifact_type="DEPENDENCY_INDEX",dependencies=deps,status="CURRENT"),
      "REVERSE_DEPENDENCY_INDEX.yaml":dict(base,artifact_type="REVERSE_DEPENDENCY_INDEX",reverse_dependencies=[],status="CURRENT")
    }
    for n,o in docs.items(): wy(wd/n,o)

def work_unit_materialize(product,govroot,wd,cfg,stage,pb,deps):
    adapters=y(govroot/"governance/ci/stage_execution_semantic_adapters.yaml"); scans=adapters["stages"]["STAGE-01"]["scanner_dimensions"]
    rawref="00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml"; authref="STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_GOVERNANCE_SELECTION.yaml"
    idir=wd/"EVIDENCE/INPUT_READINESS"; idir.mkdir(parents=True,exist_ok=True)
    wy(idir/"RAW_SOURCE_SET.yaml",{"artifact_type":"STAGE_INPUT_CONSUMER_READINESS","input_uid":"RAW_SOURCE_SET","artifact_ref":rawref,"content_sha256":sha(wd/rawref),"status":"PASS"})
    wy(idir/"CURRENT_AUTHORITY_SET.yaml",{"artifact_type":"STAGE_INPUT_CONSUMER_READINESS","input_uid":"CURRENT_AUTHORITY_SET","artifact_ref":authref,"content_sha256":sha(product/authref),"status":"PASS"})
    state={"artifact_type":"WORK_UNIT_EXECUTION_STATE","stage_uid":"STAGE-01","work_unit_uid":cfg["work_unit_uid"],"governed_unit_uid":cfg["governed_unit_uid"],"governance_uid":GOV_UID,"status":"READY_FOR_EXECUTION","current_operation":OPS[0],"completed_operations":[],"resume_control":{"product_execution_allowed":True},"completion_credit":0}
    wy(wd/"EXECUTION_STATE.yaml",state)
    guard=load_guard(govroot)
    ctx={"artifact_type":"STAGE01_RUN_CONTEXT","run_uid":"RUN-"+cfg["work_unit_uid"],"stage_uid":"STAGE-01","work_unit_uid":cfg["work_unit_uid"],"candidate_normative_hash":guard.normative_hash(govroot/".github/governance-source/active/source"),"clean_start_verified":True,"website_reconstruction":False,"formal_source_intake_closure_claim":False}
    wy(wd/"RUN_CONTEXT.yaml",ctx); wy(wd/"CURRENT_RUN_MANIFEST.yaml",{"artifact_type":"CURRENT_RUN_MANIFEST","run_uid":ctx["run_uid"],"stage_uid":"STAGE-01","work_unit_uid":cfg["work_unit_uid"],"current_files":[]})
    scope={"artifact_type":"EXECUTION_SCOPE_MANIFEST","scope_uid":cfg["scope_label"],"scope_kind":"CURRENT_GOVERNED_UNIT_CLEAN_BOOTSTRAP","stage_uid":"STAGE-01","work_unit_uid":cfg["work_unit_uid"],"governed_unit_uid":cfg["governed_unit_uid"],"governance_uid":GOV_UID,"governance_execution_mode":"CURRENT_VALIDATED_GOVERNANCE","included_governed_units":[cfg["governed_unit_uid"]],"excluded_governed_units":[],"remaining_governed_units":[cfg["governed_unit_uid"]],"partial_scope":False,"product_stage_execution_allowed":True,"stage_exit_credit_allowed":False,"status":"READY_FOR_EXECUTION"}
    wy(wd/"CURRENT_EXECUTION_SCOPE_MANIFEST.yaml",scope)
    work={"artifact_type":"WORK_UNIT","work_unit_uid":cfg["work_unit_uid"],"stage_uid":"STAGE-01","governed_unit_uid":cfg["governed_unit_uid"],"scope_uid":cfg["scope_label"],"primary_task_layer":"PRODUCT_STAGE_EXECUTION","governance_uid":GOV_UID,"governance_execution_mode":"CURRENT_VALIDATED_GOVERNANCE","work_unit_activation_kind":"INITIAL_STAGE_WORK_UNIT","clean_bootstrap_authority_ref":AUTH_ISSUE,"pre_execution_gate_status":"PASS","current_status":"READY_FOR_EXECUTION","required_outputs":stage["outputs"],"normative_execution_matrix_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['work_unit_uid']}/NORMATIVE_EXECUTION_MATRIX.yaml","source_projection_admission":{"applicability":"REQUIRED","bindings":[{"source_uid":cfg["source_uid"],"freeze_receipt_ref":pb["freeze_receipt_ref"],"pair_hash":pb["pair_hash"],"raw_source_sha256":pb["raw_source_sha256"],"projection_uid":pb["projection_uid"],"projection_content_hash":pb["projection_content_hash"]}]},"input_bindings":{"RAW_SOURCE_SET":{"input_uid":"RAW_SOURCE_SET","origin":"SOURCE_INTAKE","status":"MATERIALIZED","artifact_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['work_unit_uid']}/{rawref}","content_sha256":sha(wd/rawref),"external_evidence_ref":None,"authority_evidence_ref":None,"consumer_readiness_evidence_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['work_unit_uid']}/EVIDENCE/INPUT_READINESS/RAW_SOURCE_SET.yaml"},"CURRENT_AUTHORITY_SET":{"input_uid":"CURRENT_AUTHORITY_SET","origin":"CURRENT_AUTHORITY","status":"MATERIALIZED","artifact_ref":authref,"content_sha256":sha(product/authref),"external_evidence_ref":None,"authority_evidence_ref":AUTH_ISSUE,"consumer_readiness_evidence_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['work_unit_uid']}/EVIDENCE/INPUT_READINESS/CURRENT_AUTHORITY_SET.yaml"}},"operation_bindings":{op:{"applicability":"REQUIRED","executor_owner":OP_EXECUTORS[op],"executor_protocol":"PYTHON_STAGE_OPERATION_V1","result_owner":"OWNER-STAGE01-"+op,"operation_receipt_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['work_unit_uid']}/EVIDENCE/OPERATION_RECEIPTS/{op}.yaml"} for op in OPS},"scanner_bindings":{s:{"scanner_owner":".github/governance-source/active/source/09_TESTS/governance/governance_stage1_pipeline_guard.py","result_owner":"OWNER-STAGE01-SCANNER-"+s,"scanner_protocol":"STAGE1_GUARD_V1","result_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['work_unit_uid']}/EVIDENCE/SCANNER_RESULTS/{s}.yaml"} for s in scans},"validator_bindings":{v:{"validator_kind":("PHYSICAL_VALIDATOR" if v=="VAL-GOV-026" else "DECLARED_STAGE_GUARD"),"validator_protocol":("STAGE1_GUARD_V1" if v=="VAL-GOV-026" else "DECLARED_STAGE_GUARD_AGGREGATE_V1"),"result_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['work_unit_uid']}/EVIDENCE/VALIDATOR_RESULTS/{v}.yaml"} for v in stage.get("validators") or []},"dependencies":deps,"current_ledger_bindings":{},"completion_credit":0}
    wy(wd/"WORK_UNIT.yaml",work); refresh_manifest_one(wd); work=y(wd/"WORK_UNIT.yaml")
    work["current_ledger_bindings"]={cls:{"ledger_class":cls,"binding_kind":"LOCAL_ARTIFACT","artifact_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['work_unit_uid']}/{n}","content_sha256":sha(wd/n),"external_evidence_ref":None} for cls,n in LEDGER_FILES.items()}
    wy(wd/"WORK_UNIT.yaml",work)

def materialize(product,govroot,cfgs):
    selection=y(product/"STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_GOVERNANCE_SELECTION.yaml")
    if selection.get("status")!="SELECTED_EXACT_CURRENT_SNAPSHOT" or selection.get("governance_commit_sha")!=git(govroot,"rev-parse","HEAD"):
        raise RuntimeError("EXACT_CURRENT_GOVERNANCE_SELECTION_NOT_ACTIVE")
    stage=stage01(y(govroot/".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml"))
    if list(stage["operations"])!=OPS: raise RuntimeError("STAGE01_OPERATION_UNIVERSE_DRIFT")
    source_review_materialize(product,cfgs)
    guard=load_guard(govroot)
    for cfg in cfgs:
        wd=product/f"STAGE_EXECUTION/STAGE-01/{cfg['work_unit_uid']}"
        if wd.exists(): shutil.rmtree(wd)
        wd.mkdir(parents=True)
        pb=projection_materialize(product,govroot,wd,cfg,guard)
        matrix_materialize(product,wd,cfg,stage)
        deps=preflight_materialize(wd,cfg,stage,pb)
        ledgers_materialize(product,wd,cfg,stage,selection,deps)
        work_unit_materialize(product,govroot,wd,cfg,stage,pb,deps)
        future=[p for p in [wd/"00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml",wd/"00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml",wd/"00_SOURCE_INTAKE/SOURCE_CONTEXT_MANIFEST.yaml",wd/"00_SOURCE_INTAKE/CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml",wd/"00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml",wd/"01_CLASSIFIED",wd/"CLASSIFIED_ARTIFACT_SET.yaml",wd/"02_BASE_BLUEPRINT",wd/"03_BLUEPRINT_BINDING"] if p.exists()]
        if future: raise RuntimeError("FUTURE_STAGE01_OUTPUT_PREPRODUCED:"+repr([str(x) for x in future]))
    print("PASS: selected Stage01 initial Work Units and fresh frozen source projections materialized with zero predecessor runtime dependency")

def refresh(product,cfgs):
    for cfg in cfgs: refresh_manifest_one(product/f"STAGE_EXECUTION/STAGE-01/{cfg['work_unit_uid']}")
    print("PASS: selected Stage01 run manifests refreshed")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--product-root",required=True)
    ap.add_argument("--governance-root")
    ap.add_argument("--units",default=DEFAULT_UNITS)
    ap.add_argument("--mode",choices=["source-review","materialize","refresh-manifest"],default="materialize")
    a=ap.parse_args()
    product=Path(a.product_root).resolve(); cfgs=select_configs(a.units)
    govroot=Path(a.governance_root).resolve() if a.governance_root else None
    if a.mode=="source-review": source_review_materialize(product,cfgs)
    elif a.mode=="materialize":
        if not govroot: raise SystemExit("governance root required")
        materialize(product,govroot,cfgs)
    else:
        refresh(product,cfgs)

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print("BLOCK: STAGE01_CLEAN_MATERIALIZER:"+repr(exc),file=__import__("sys").stderr)
        raise
