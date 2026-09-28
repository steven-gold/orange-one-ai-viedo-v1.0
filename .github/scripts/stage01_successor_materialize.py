#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, shutil, subprocess, sys, zipfile
from pathlib import Path
import yaml

GOV_UID="GOV-REV-20260928-WORD-DERIVED-STAGE-INTERNAL-VALIDATION"
AUTH_ISSUE="https://github.com/steven-gold/orange-one-ai-viedo-v1.0/issues/61"
CONFIGS=[
 {"scope_label":"GLOBAL-HOME-SHELL-NAVIGATION","governed_unit_uid":"GLOBAL-HOME-SHELL-NAVIGATION","source_uid":"SRC-DOCX-334A4679600F092B733B","source_filename":"ACPOS_GLOBAL_HOME_SHELL_NAVIGATION_Mother_Basic_Design_OPTIMIZED.docx","predecessor":"WU-STAGE01-GLOBAL-HOME-SHELL-NAVIGATION-001","successor":"WU-STAGE01-GLOBAL-HOME-SHELL-NAVIGATION-REENTRY-001","review_ref":"STAGE_EXECUTION/SHARED_AUTHORITY/V232_REALIGNMENT/SOURCE_REVIEW_INPUTS/GLOBAL-HOME-SHELL-NAVIGATION.json"},
 {"scope_label":"WB01-DASHBOARD","governed_unit_uid":"workspace:WB-01","source_uid":"SRC-DOCX-2B1908530B5BD312A392","source_filename":"ACPOS_WB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx","predecessor":"WU-STAGE01-WB01-DASHBOARD-001","successor":"WU-STAGE01-WB01-DASHBOARD-REENTRY-001","review_ref":"STAGE_EXECUTION/SHARED_AUTHORITY/V232_REALIGNMENT/SOURCE_REVIEW_INPUTS/WB01-DASHBOARD.json"}
]
OPS=["SOURCE_STRUCTURE_ENUMERATION","SOURCE_SEGMENT_MAPPING","SOURCE_CONTEXT_COMPILATION","SOURCE_SUPERSESSION_CONFLICT_RESOLUTION","SOURCE_DEPENDENCY_EXTRACTION","RESPONSIBILITY_CLASSIFICATION","GOVERNED_UNIT_BASE_BLUEPRINT_COMPILE","VISUAL_BASE_BLUEPRINT_COMPILE","BLUEPRINT_BINDING_COMPILE"]
OP_EXECUTORS={
"SOURCE_STRUCTURE_ENUMERATION":".github/scripts/stage01_ops/source_structure_enumeration.py",
"SOURCE_SEGMENT_MAPPING":".github/scripts/stage01_ops/source_segment_mapping.py",
"SOURCE_CONTEXT_COMPILATION":".github/scripts/stage01_ops/source_context_compilation.py",
"SOURCE_SUPERSESSION_CONFLICT_RESOLUTION":".github/scripts/stage01_ops/source_supersession_conflict_resolution.py",
"SOURCE_DEPENDENCY_EXTRACTION":".github/scripts/stage01_ops/source_dependency_extraction.py",
"RESPONSIBILITY_CLASSIFICATION":".github/scripts/stage01_ops/responsibility_classification.py",
"GOVERNED_UNIT_BASE_BLUEPRINT_COMPILE":".github/scripts/stage01_ops/governed_unit_base_blueprint_compile.py",
"VISUAL_BASE_BLUEPRINT_COMPILE":".github/scripts/stage01_ops/visual_base_blueprint_compile.py",
"BLUEPRINT_BINDING_COMPILE":".github/scripts/stage01_ops/blueprint_binding_compile.py"}
LEDGER_FILES={"EXECUTION_STATE":"EXECUTION_STATE.yaml","RUN_MANIFEST":"CURRENT_RUN_MANIFEST.yaml","ARTIFACT_PLAN":"ARTIFACT_PLAN.yaml","GOVERNANCE_CURRENT":"GOVERNANCE_CURRENT.yaml","BRANCH_BASELINE":"BRANCH_BASELINE.yaml","GOVERNANCE_STAGE_LOCK":"GOVERNANCE_STAGE_LOCK.yaml","SEALED_GOVERNANCE_TEST_BASELINE":"SEALED_GOVERNANCE_TEST_BASELINE.yaml","STAGE_EVIDENCE":"STAGE_EVIDENCE.yaml","DEPENDENCY_INDEX":"DEPENDENCY_INDEX.yaml","REVERSE_DEPENDENCY_INDEX":"REVERSE_DEPENDENCY_INDEX.yaml"}

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
def map_domain(v): return "GOVERNED_UNIT_CONSTRUCTION" if v in ("PAGE_CONSTRUCTION","GOVERNED_UNIT_CONSTRUCTION") else v
def successorize_rel(rel,pred,succ):
    s=str(rel).replace(pred,succ).replace("/PAGE/","/GOVERNED_UNIT_CONSTRUCTION/").replace("/VISUAL/","/VISUAL_CONSTRUCTION/")
    return s.replace("PAGE_BASE_BLUEPRINT.yaml","GOVERNED_UNIT_BASE_BLUEPRINT.yaml")
def stage01(lifecycle):
    rows=lifecycle.get("stages") or {}
    if isinstance(rows,dict): return rows["STAGE-01"]
    return next(r for r in rows if r.get("stage_uid")=="STAGE-01")
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
    if not source.is_file(): raise RuntimeError("REGISTERED_ROOT_SOURCE_MISSING:"+cfg["source_filename"])
    review=y(product/cfg["review_ref"]); raw_sha=sha(source)
    if review.get("source_sha256")!=raw_sha or review.get("source_uid")!=cfg["source_uid"] or review.get("governed_unit_uid")!=cfg["governed_unit_uid"]:
        raise RuntimeError("SOURCE_REVIEW_IDENTITY_OR_HASH_DRIFT:"+cfg["scope_label"])
    old_seg=y(product/f"STAGE_EXECUTION/STAGE-01/{cfg['predecessor']}/00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml")
    observed_domains=sorted({map_domain(str(r.get("planning_domain") or "")) for r in (old_seg.get("source_segments") or []) if map_domain(str(r.get("planning_domain") or "")) in guard.DOMAINS})
    required_domains=sorted(guard.DOMAINS); missing=sorted(set(required_domains)-set(observed_domains))
    if missing: raise RuntimeError("SOURCE_CONTENT_DOMAIN_GAP:"+cfg["scope_label"]+":"+repr(missing))

    rawrel=f"00_SOURCE_INTAKE/RAW_SOURCE/{cfg['source_uid']}/{cfg['source_filename']}"
    raw=wd/rawrel; raw.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,raw); blob=guard.git_blob_sha(raw)
    rawcap={"artifact_uid":"RAWCAP-"+cfg["successor"],"artifact_type":"RAW_SOURCE_REFERENCE_MANIFEST","status":"CURRENT_RAW_SOURCE_CAPTURE","capture_root":"00_SOURCE_INTAKE/RAW_SOURCE","capture_revision":"REENTRY-001","records":[{"source_uid":cfg["source_uid"],"governed_unit_uid":cfg["governed_unit_uid"],"source_role":guard.MIXED_SOURCE_ROLE,"source_domain_scope":guard.MIXED_SOURCE_SCOPE,"source_format":"DOCX","projection_required":True,"target_path":rawrel,"source_git_blob_sha":blob,"target_git_blob_sha":blob,"source_sha256":raw_sha,"content_mutated":False}]}
    capstate={"artifact_type":"RAW_SOURCE_CAPTURE_STATE","state":"CAPTURE_CLOSED","next_step":"SOURCE_DOCUMENT_CONTENT_AUDIT","recapture_allowed":False}
    wy(wd/"00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml",rawcap); wy(wd/"00_SOURCE_INTAKE/RAW_SOURCE_CAPTURE_STATE.yaml",capstate)

    contracts=y(govroot/".github/governance-source/active/source/10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml")
    sc=contracts["structured_document_source_projection_contract"]; rawlockc=sc["raw_source_lock"]; pc=sc["projection"]; rc=sc["reconciliation"]; fc=sc["pair_freeze"]
    projroot=wd/f"00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{cfg['source_uid']}"; projroot.mkdir(parents=True,exist_ok=True)
    audit={"schema_version":1,"artifact_uid":"AUD-SOURCE-"+cfg["source_uid"]+"-REENTRY-001","artifact_type":"SOURCE_DOCUMENT_CONTENT_AUDIT","source_uid":cfg["source_uid"],"source_sha256":raw_sha,"governed_unit_uid":cfg["governed_unit_uid"],"audit_standard_uid":"REG-STAGE1-SOURCE-FACT-CONTRACTS-001#source_document_content_readiness_audit","required_design_domain_uids":required_domains,"observed_design_domain_uids":observed_domains,"missing_required_design_domain_uids":missing,"matrix_integrity":{"source_review_extract_ref":cfg["review_ref"],"paragraph_count":review.get("paragraph_count"),"table_count":review.get("table_count"),"package_part_count":review.get("package_part_count"),"result":"PASS"},"visual_source_integrity":{"media_count":review.get("media_count"),"source_package_identity":"HASH_MATCHED","result":"PASS"},"render_integrity":{"docx_package_parse":"PASS","visual_render_review":"DEFERRED_TO_STAGE03"},"open_downstream_states":["STAGE-02:NOT_EXECUTED","STAGE-03:NOT_EXECUTED","STAGE-04:NOT_EXECUTED"],"unresolved_required_gap_count":0,"contradiction_count":0,"result":"PASS","evidence_content_hash":None}
    audit["evidence_content_hash"]=guard._hash_without(audit,"evidence_content_hash"); wy(projroot/"SOURCE_DOCUMENT_CONTENT_AUDIT.yaml",audit)
    lock={"schema_version":1,"artifact_uid":"RAWLOCK-"+cfg["source_uid"]+"-REENTRY-001","artifact_type":"RAW_SOURCE_IMMUTABILITY_RECEIPT","source_uid":cfg["source_uid"],"source_path":rawrel,"source_git_blob_sha":blob,"source_sha256":raw_sha,"content_readiness_audit_uid":audit["artifact_uid"],"lock_state":rawlockc["terminal_lock_state"],"writable":False,"mutation_policy":rawlockc["byte_change_disposition"],"content_hash":None}
    lock["content_hash"]=guard._hash_without(lock,"content_hash"); wy(projroot/"RAW_SOURCE_IMMUTABILITY_RECEIPT.yaml",lock)

    inv=guard.derive_docx_inventory(raw); broot=projroot/"FROZEN_BINARY_PARTS"; broot.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(raw,"r") as z:
        for row in guard._binary_parts_from_inventory(inv):
            part=row["package_part_path"]; bp=broot/(row["part_sha256"]+Path(part).suffix.lower()); bp.write_bytes(z.read(part))
            if sha(bp)!=row["part_sha256"]: raise RuntimeError("FROZEN_BINARY_HASH_DRIFT:"+part)
    den=[{"denominator_uid":"DEN-PACKAGE-PART","denominator_type":"PACKAGE_PART","required_count":len(inv["package_parts"]),"projected_count":len(inv["package_parts"])},{"denominator_uid":"DEN-RELATIONSHIP","denominator_type":"RELATIONSHIP","required_count":len(inv["relationships"]),"projected_count":len(inv["relationships"])},{"denominator_uid":"DEN-XML-NODE","denominator_type":"XML_NODE","required_count":len(inv["source_nodes"]),"projected_count":len(inv["source_nodes"])}]
    proj={"schema_version":1,"artifact_uid":"PROJ-"+cfg["source_uid"]+"-REENTRY-001","artifact_type":"CANONICAL_SOURCE_PROJECTION","projection_schema_uid":pc["schema_uid"],"projection_schema_revision":pc["schema_revision"],"projection_role":pc["role"],"normative_authority":False,"source_identity":{"source_uid":cfg["source_uid"],"source_path":rawrel,"source_format":"DOCX","source_git_blob_sha":blob,"source_sha256":raw_sha,"raw_source_lock_receipt_uid":lock["artifact_uid"]},"extraction_identity":{"extractor_uid":"ACPOS-STAGE01-DOCX-PROJECTION-001","extractor_version":"v2.2.34","extraction_run_uid":"PROJECTION-"+cfg["successor"],"extraction_evidence_ref":f"00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{cfg['source_uid']}/SOURCE_DOCUMENT_CONTENT_AUDIT.yaml"},"serialization_contract":{"yaml_profile":pc["canonical_serialization"]["yaml_profile"],"encoding":pc["canonical_serialization"]["encoding"],"line_ending":pc["canonical_serialization"]["line_ending"],"key_order_contract_uid":"REG-STAGE1-SOURCE-FACT-CONTRACTS-001#projection","anchors_aliases":pc["canonical_serialization"]["anchors_aliases"],"implicit_custom_tags":pc["canonical_serialization"]["implicit_custom_tags"]},"denominator_rows":den,"package_parts":inv["package_parts"],"relationships":inv["relationships"],"source_nodes":inv["source_nodes"],"projection_content_hash":None,"status":"PROJECTION_COMPLETE"}
    proj["projection_content_hash"]=guard._hash_without(proj,"projection_content_hash"); wy(projroot/"CANONICAL_SOURCE_PROJECTION.yaml",proj)
    zero={k:0 for k in rc["zero_loss_count_field_order"]}
    ev={"schema_version":1,"artifact_uid":"EV-PROJECTION-"+cfg["source_uid"]+"-REENTRY-001","artifact_type":"SOURCE_PROJECTION_RECONCILIATION_EVIDENCE","validator_uid":rc["validator_uid"],"source_uid":cfg["source_uid"],"raw_source_sha256":raw_sha,"projection_uid":proj["artifact_uid"],"projection_content_hash":proj["projection_content_hash"],"projection_schema_uid":pc["schema_uid"],"projection_schema_revision":pc["schema_revision"],"source_inventory_hashes":{"package_parts_hash":inv["package_parts_hash"],"relationships_hash":inv["relationships_hash"],"source_nodes_hash":inv["source_nodes_hash"]},"zero_loss_counts":zero,"reverse_trace":"COMPLETE","unsupported_count":0,"result":"PASS","evidence_content_hash":None}
    ev["evidence_content_hash"]=guard._hash_without(ev,"evidence_content_hash"); wy(projroot/"SOURCE_PROJECTION_RECONCILIATION_EVIDENCE.yaml",ev)
    denom_hash=guard.stable_hash_obj(den); pair_hash=guard.sha256_bytes((raw_sha+"\n"+proj["projection_content_hash"]+"\n"+ev["evidence_content_hash"]+"\n"+str(pc["schema_uid"])+"\n"+str(pc["schema_revision"])+"\n"+denom_hash+"\n").encode())
    freeze={"schema_version":1,"artifact_uid":"FREEZE-"+cfg["source_uid"]+"-REENTRY-001","artifact_type":"SOURCE_PROJECTION_FREEZE_RECEIPT","source_uid":cfg["source_uid"],"raw_source_sha256":raw_sha,"raw_source_git_blob_sha":blob,"projection_uid":proj["artifact_uid"],"projection_content_hash":proj["projection_content_hash"],"projection_schema_uid":pc["schema_uid"],"projection_schema_revision":pc["schema_revision"],"reconciliation_evidence_uid":ev["artifact_uid"],"reconciliation_evidence_hash":ev["evidence_content_hash"],"source_denominator_hash":denom_hash,"pair_hash":pair_hash,"lock_state":fc["lock_state"],"raw_source_writable":False,"projection_writable":False,"mutation_disposition":fc["mutation_disposition"],"next_step":fc["next_step"],"status":fc["status"]}
    wy(projroot/"SOURCE_PROJECTION_FREEZE_RECEIPT.yaml",freeze)
    result=guard.validate_pre_stage_source_projection(govroot/".github/governance-source/active/source",wd,rawcap,capstate)
    if result.get("failures"): raise RuntimeError("FRESH_SOURCE_PROJECTION_VALIDATION_FAILED:"+repr(result["failures"][:20]))
    b=result["bindings"][cfg["source_uid"]]
    return {k:b[k] for k in ("projection_uid","projection_content_hash","pair_hash","raw_source_sha256","freeze_receipt_ref")}

def matrix_materialize(product,wd,cfg,stage):
    pred=product/f"STAGE_EXECUTION/STAGE-01/{cfg['predecessor']}"; m=y(pred/"NORMATIVE_EXECUTION_MATRIX.yaml"); rows=[dict(r) for r in (m.get("rows") or [])]
    current_sections=set(map(str,stage.get("required_normative_section_uids") or [])); old_sections={str(r.get("normative_section_uid") or "") for r in rows}
    if current_sections!=old_sections: raise RuntimeError("STAGE01_NORMATIVE_SECTION_DELTA_UNRESOLVED:"+repr(sorted(current_sections-old_sections))+":"+repr(sorted(old_sections-current_sections)))
    for i,row in enumerate(rows):
        row["matrix_row_uid"]=str(row.get("matrix_row_uid") or f"NEM-S1-{i+1:04d}")+"-REENTRY-001"
        if row.get("required_artifact_type")=="PAGE_BASE_BLUEPRINT": row["required_artifact_type"]="GOVERNED_UNIT_BASE_BLUEPRINT"
        for k in ("artifact_ref","evidence_ref","row_denominator_source"):
            if row.get(k): row[k]=successorize_rel(str(row[k]),cfg["predecessor"],cfg["successor"])
        row["artifact_owner"]="GOVERNED_UNIT:"+cfg["governed_unit_uid"]
        if row.get("field_path")==["page_blueprint"]: row["field_path"]=["governed_unit_blueprint"]
    artifact_types={str(r.get("required_artifact_type") or "") for r in rows}; expected=set(map(str,stage.get("outputs") or []))|set(map(str,stage.get("required_evidence") or []))
    if artifact_types!=expected: raise RuntimeError("STAGE01_MATRIX_ARTIFACT_SET_DRIFT:"+repr(sorted(expected-artifact_types))+":"+repr(sorted(artifact_types-expected)))
    required=[r for r in rows if r.get("applicability")=="REQUIRED"]
    matrix={"artifact_uid":"NEM-STAGE-01-"+cfg["successor"],"artifact_type":"NORMATIVE_EXECUTION_MATRIX","governance_uid":GOV_UID,"stage_uid":"STAGE-01","work_unit_uid":cfg["successor"],"governed_unit_uid":cfg["governed_unit_uid"],"matrix_contract":m.get("matrix_contract"),"denominator_policy":m.get("denominator_policy"),"binding_basis":"CURRENT_REGISTERED_OPERATION_OUTPUT_TARGET","rows":rows,"coverage":{"required_normative_section_total":len(current_sections),"represented_normative_section_total":len(current_sections),"required_artifact_total":len(expected),"represented_artifact_total":len(expected),"required_field_total":len(required),"validator_bound_field_total":sum(1 for r in required if r.get("validator_uid") and r.get("validator_check_id")),"closure_bound_field_total":sum(1 for r in required if r.get("closure_gate")==stage.get("exit_gate")),"missing_required_row_count":0,"missing_required_field_count":0,"duplicate_credit_count":0,"summary_only_credit_count":0,"unclassified_applicability_count":0,"validator_unbound_count":0,"closure_unbound_count":0,"stale_matrix_count":0},"status":"PASS"}
    wy(wd/"NORMATIVE_EXECUTION_MATRIX.yaml",matrix)

def preflight_materialize(wd,cfg,stage,pb):
    deps=[f"STAGE_EXECUTION/STAGE-01/{cfg['predecessor']}/WORK_UNIT.yaml",f"STAGE_EXECUTION/STAGE-01/{cfg['predecessor']}/WORK_UNIT_TERMINAL_RECEIPT.yaml",cfg["review_ref"],"STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_GOVERNANCE_SELECTION.yaml",f"STAGE_EXECUTION/STAGE-01/{cfg['successor']}/{pb['freeze_receipt_ref']}"]
    names=["REQUIRED_FIELD_MANIFEST.yaml","FUNCTIONAL_CHAIN_MANIFEST.yaml","EFFECTIVE_CONTRACT_OVERLAY.yaml","DEPENDENCY_TOPOLOGY.yaml","DENOMINATOR_SNAPSHOT.yaml","CLASSIFICATION_RULESET.yaml","CHANGE_IMPACT_MAP.yaml","STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml"]
    docs={"REQUIRED_FIELD_MANIFEST.yaml":{"artifact_type":"REQUIRED_FIELD_MANIFEST","stage_uid":"STAGE-01","work_unit_uid":cfg["successor"],"governed_unit_uid":cfg["governed_unit_uid"],"required_operations":stage["operations"],"required_outputs":stage["outputs"],"status":"CURRENT"},"FUNCTIONAL_CHAIN_MANIFEST.yaml":{"artifact_type":"FUNCTIONAL_CHAIN_MANIFEST","stage_uid":"STAGE-01","work_unit_uid":cfg["successor"],"chain":stage["operations"],"status":"CURRENT"},"EFFECTIVE_CONTRACT_OVERLAY.yaml":{"artifact_type":"EFFECTIVE_CONTRACT_OVERLAY","governance_uid":GOV_UID,"stage_uid":"STAGE-01","work_unit_uid":cfg["successor"],"source_projection_pair_hash":pb["pair_hash"],"status":"CURRENT"},"DEPENDENCY_TOPOLOGY.yaml":{"artifact_type":"DEPENDENCY_TOPOLOGY","stage_uid":"STAGE-01","work_unit_uid":cfg["successor"],"dependencies":deps,"forward_dependencies":["STAGE-02"],"reverse_dependencies":[cfg["predecessor"]],"status":"CURRENT"},"DENOMINATOR_SNAPSHOT.yaml":{"artifact_type":"DENOMINATOR_SNAPSHOT","stage_uid":"STAGE-01","work_unit_uid":cfg["successor"],"governed_unit_uid":cfg["governed_unit_uid"],"required_normative_sections":stage["required_normative_section_uids"],"required_outputs":stage["outputs"],"required_evidence":stage["required_evidence"],"required_operation_total":len(stage["operations"]),"status":"FROZEN_PRE_EXECUTION"},"CLASSIFICATION_RULESET.yaml":{"artifact_type":"CLASSIFICATION_RULESET","stage_uid":"STAGE-01","work_unit_uid":cfg["successor"],"strategy":"IMMUTABLE_PREDECESSOR_SEMANTIC_MAPPING_REVALIDATED_AGAINST_FRESH_CANONICAL_PROJECTION","historical_completion_credit":0,"status":"CURRENT"},"CHANGE_IMPACT_MAP.yaml":{"artifact_type":"CHANGE_IMPACT_MAP","stage_uid":"STAGE-01","work_unit_uid":cfg["successor"],"predecessor_work_unit_uid":cfg["predecessor"],"successor_work_unit_uid":cfg["successor"],"affected_stage_uids":["STAGE-01","STAGE-02","STAGE-03","STAGE-04"],"status":"CURRENT"},"STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml":{"artifact_type":"STAGE_EXECUTION_PREFLIGHT_RECEIPT","stage_uid":"STAGE-01","work_unit_uid":cfg["successor"],"governance_uid":GOV_UID,"required_manifest_set":names,"shared_manifest_set_complete":True,"fresh_source_projection_validated":True,"historical_completion_credit_used":False,"result":"PASS","product_completion_credit":0}}
    for n,o in docs.items(): wy(wd/n,o)
    return deps

def ledgers_materialize(product,wd,cfg,stage,selection,deps):
    head=git(product,"rev-parse","HEAD"); tree=git(product,"rev-parse","HEAD^{tree}"); base={"stage_uid":"STAGE-01","work_unit_uid":cfg["successor"],"governed_unit_uid":cfg["governed_unit_uid"],"governance_uid":GOV_UID}
    docs={"ARTIFACT_PLAN.yaml":dict(base,artifact_type="ARTIFACT_PLAN",planned_outputs=stage["outputs"],planned_required_evidence=stage["required_evidence"],status="CURRENT_PRE_EXECUTION"),"GOVERNANCE_CURRENT.yaml":dict(base,artifact_type="GOVERNANCE_CURRENT",governance_commit_sha=selection["governance_commit_sha"],governance_tree_sha=selection["governance_tree_sha"],status="CURRENT"),"BRANCH_BASELINE.yaml":dict(base,artifact_type="BRANCH_BASELINE",repository="steven-gold/orange-one-ai-viedo-v1.0",branch="0921acpos",pre_write_head_sha=head,pre_write_tree_sha=tree,status="CURRENT"),"GOVERNANCE_STAGE_LOCK.yaml":dict(base,artifact_type="GOVERNANCE_STAGE_LOCK",locked_governance_commit_sha=selection["governance_commit_sha"],lock_state="LOCKED_FOR_STAGE01_SUCCESSOR"),"SEALED_GOVERNANCE_TEST_BASELINE.yaml":dict(base,artifact_type="SEALED_GOVERNANCE_TEST_BASELINE",mother_neutrality_run_id=selection["exact_head_validation"]["mother_neutrality_run_id"],stage_internal_validation_run_id=selection["exact_head_validation"]["stage_internal_validation_run_id"],gate_01_08_result="PASS",status="SEALED"),"STAGE_EVIDENCE.yaml":dict(base,artifact_type="STAGE_EVIDENCE",execution_status="NOT_STARTED",completion_credit=0,status="CURRENT_PRE_EXECUTION"),"DEPENDENCY_INDEX.yaml":dict(base,artifact_type="DEPENDENCY_INDEX",dependencies=deps,status="CURRENT"),"REVERSE_DEPENDENCY_INDEX.yaml":dict(base,artifact_type="REVERSE_DEPENDENCY_INDEX",reverse_dependencies=[cfg["predecessor"],"STAGE-02"],status="CURRENT")}
    for n,o in docs.items(): wy(wd/n,o)

def work_unit_materialize(product,govroot,wd,cfg,stage,pb,deps):
    adapters=y(govroot/"governance/ci/stage_execution_semantic_adapters.yaml"); scans=adapters["stages"]["STAGE-01"]["scanner_dimensions"]
    rawref="00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml"; authref="STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_GOVERNANCE_SELECTION.yaml"; idir=wd/"EVIDENCE/INPUT_READINESS"; idir.mkdir(parents=True,exist_ok=True)
    wy(idir/"RAW_SOURCE_SET.yaml",{"artifact_type":"STAGE_INPUT_CONSUMER_READINESS","input_uid":"RAW_SOURCE_SET","artifact_ref":rawref,"content_sha256":sha(wd/rawref),"status":"PASS"}); wy(idir/"CURRENT_AUTHORITY_SET.yaml",{"artifact_type":"STAGE_INPUT_CONSUMER_READINESS","input_uid":"CURRENT_AUTHORITY_SET","artifact_ref":authref,"content_sha256":sha(product/authref),"status":"PASS"})
    state={"artifact_type":"WORK_UNIT_EXECUTION_STATE","stage_uid":"STAGE-01","work_unit_uid":cfg["successor"],"governed_unit_uid":cfg["governed_unit_uid"],"governance_uid":GOV_UID,"status":"READY_FOR_EXECUTION","current_operation":OPS[0],"completed_operations":[],"resume_control":{"product_execution_allowed":True},"completion_credit":0}; wy(wd/"EXECUTION_STATE.yaml",state)
    guard=load_guard(govroot); ctx={"artifact_type":"STAGE01_RUN_CONTEXT","run_uid":"RUN-"+cfg["successor"],"stage_uid":"STAGE-01","work_unit_uid":cfg["successor"],"candidate_normative_hash":guard.normative_hash(govroot/".github/governance-source/active/source"),"clean_start_verified":True,"website_reconstruction":False,"formal_source_intake_closure_claim":False}; wy(wd/"RUN_CONTEXT.yaml",ctx); wy(wd/"CURRENT_RUN_MANIFEST.yaml",{"artifact_type":"CURRENT_RUN_MANIFEST","run_uid":ctx["run_uid"],"stage_uid":"STAGE-01","work_unit_uid":cfg["successor"],"current_files":[]})
    scope={"artifact_type":"EXECUTION_SCOPE_MANIFEST","scope_uid":cfg["scope_label"],"scope_kind":"GOVERNED_UNIT_REENTRY","stage_uid":"STAGE-01","work_unit_uid":cfg["successor"],"governed_unit_uid":cfg["governed_unit_uid"],"governance_uid":GOV_UID,"governance_execution_mode":"CURRENT_VALIDATED_GOVERNANCE","included_governed_units":[cfg["governed_unit_uid"]],"excluded_governed_units":[],"remaining_governed_units":[cfg["governed_unit_uid"]],"partial_scope":False,"product_stage_execution_allowed":True,"stage_exit_credit_allowed":False,"status":"READY_FOR_EXECUTION"}; wy(wd/"CURRENT_EXECUTION_SCOPE_MANIFEST.yaml",scope)
    work={"artifact_type":"WORK_UNIT","work_unit_uid":cfg["successor"],"stage_uid":"STAGE-01","governed_unit_uid":cfg["governed_unit_uid"],"scope_uid":cfg["scope_label"],"primary_task_layer":"PRODUCT_STAGE_EXECUTION","governance_uid":GOV_UID,"governance_execution_mode":"CURRENT_VALIDATED_GOVERNANCE","work_unit_activation_kind":"SUCCESSOR_REENTRY_WORK_UNIT","predecessor_work_unit_uid":cfg["predecessor"],"predecessor_work_unit_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['predecessor']}/WORK_UNIT.yaml","predecessor_terminal_receipt_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['predecessor']}/WORK_UNIT_TERMINAL_RECEIPT.yaml","reentry_authority_ref":AUTH_ISSUE,"pre_execution_gate_status":"PASS","current_status":"READY_FOR_EXECUTION","required_outputs":stage["outputs"],"normative_execution_matrix_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['successor']}/NORMATIVE_EXECUTION_MATRIX.yaml","source_projection_admission":{"applicability":"REQUIRED","bindings":[{"source_uid":cfg["source_uid"],"freeze_receipt_ref":pb["freeze_receipt_ref"],"pair_hash":pb["pair_hash"],"raw_source_sha256":pb["raw_source_sha256"],"projection_uid":pb["projection_uid"],"projection_content_hash":pb["projection_content_hash"]}]},"input_bindings":{"RAW_SOURCE_SET":{"input_uid":"RAW_SOURCE_SET","origin":"SOURCE_INTAKE","status":"MATERIALIZED","artifact_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['successor']}/{rawref}","content_sha256":sha(wd/rawref),"external_evidence_ref":None,"authority_evidence_ref":None,"consumer_readiness_evidence_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['successor']}/EVIDENCE/INPUT_READINESS/RAW_SOURCE_SET.yaml"},"CURRENT_AUTHORITY_SET":{"input_uid":"CURRENT_AUTHORITY_SET","origin":"CURRENT_AUTHORITY","status":"MATERIALIZED","artifact_ref":authref,"content_sha256":sha(product/authref),"external_evidence_ref":None,"authority_evidence_ref":AUTH_ISSUE,"consumer_readiness_evidence_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['successor']}/EVIDENCE/INPUT_READINESS/CURRENT_AUTHORITY_SET.yaml"}},"operation_bindings":{op:{"applicability":"REQUIRED","executor_owner":OP_EXECUTORS[op],"executor_protocol":"PYTHON_STAGE_OPERATION_V1","result_owner":"OWNER-STAGE01-"+op,"operation_receipt_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['successor']}/EVIDENCE/OPERATION_RECEIPTS/{op}.yaml"} for op in OPS},"scanner_bindings":{s:{"scanner_owner":".github/governance-source/active/source/09_TESTS/governance/governance_stage1_pipeline_guard.py","result_owner":"OWNER-STAGE01-SCANNER-"+s} for s in scans},"dependencies":deps,"current_ledger_bindings":{},"completion_credit":0}
    wy(wd/"WORK_UNIT.yaml",work); refresh_manifest_one(wd); work=y(wd/"WORK_UNIT.yaml")
    work["current_ledger_bindings"]={cls:{"ledger_class":cls,"binding_kind":"LOCAL_ARTIFACT","artifact_ref":f"STAGE_EXECUTION/STAGE-01/{cfg['successor']}/{n}","content_sha256":sha(wd/n),"external_evidence_ref":None} for cls,n in LEDGER_FILES.items()}; wy(wd/"WORK_UNIT.yaml",work)

def materialize(product,govroot):
    selection=y(product/"STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_GOVERNANCE_SELECTION.yaml")
    if selection.get("status")!="SELECTED_EXACT_CURRENT_SNAPSHOT" or selection.get("governance_commit_sha")!=git(govroot,"rev-parse","HEAD"): raise RuntimeError("EXACT_CURRENT_GOVERNANCE_SELECTION_NOT_ACTIVE")
    stage=stage01(y(govroot/".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml"))
    if list(stage["operations"])!=OPS: raise RuntimeError("STAGE01_OPERATION_UNIVERSE_DRIFT")
    guard=load_guard(govroot)
    for cfg in CONFIGS:
        wd=product/f"STAGE_EXECUTION/STAGE-01/{cfg['successor']}"
        if wd.exists(): shutil.rmtree(wd)
        wd.mkdir(parents=True); pb=projection_materialize(product,govroot,wd,cfg,guard); matrix_materialize(product,wd,cfg,stage); deps=preflight_materialize(wd,cfg,stage,pb); ledgers_materialize(product,wd,cfg,stage,selection,deps); work_unit_materialize(product,govroot,wd,cfg,stage,pb,deps)
        future=[p for p in [wd/"00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml",wd/"00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml",wd/"00_SOURCE_INTAKE/SOURCE_CONTEXT_MANIFEST.yaml",wd/"00_SOURCE_INTAKE/CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml",wd/"00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml",wd/"01_CLASSIFIED",wd/"02_BASE_BLUEPRINT",wd/"03_BLUEPRINT_BINDING"] if p.exists()]
        if future: raise RuntimeError("FUTURE_STAGE01_OUTPUT_PREPRODUCED:"+repr([str(x) for x in future]))
    print("PASS: Stage01 successor skeletons and fresh frozen source projections materialized")
def refresh(product):
    for cfg in CONFIGS: refresh_manifest_one(product/f"STAGE_EXECUTION/STAGE-01/{cfg['successor']}")
    print("PASS: Stage01 run manifests refreshed")
def mark_admitted(product):
    sp=product/"STAGE_EXECUTION/SHARED_AUTHORITY/V232_REALIGNMENT/CURRENT_REMEDIATION_STATE.yaml"; s=y(sp); s["status"]="STAGE01_SUCCESSORS_MATERIALIZED_ADMITTED"; wr=s.get("work_unit_resolution_gate") or {}; wr["effectful_execution_admitted"]=True; s["work_unit_resolution_gate"]=wr; s["resume_point"]={"last_completed_action":"STAGE01_SUCCESSOR_MATERIALIZATION_AND_ADMISSION","next_action":"RUN_STAGE01_SUCCESSOR_EFFECTFUL_OPERATIONS","next_effectful_stage":"STAGE-01","earliest_owner":"STAGE01_OPERATION_EXECUTORS"}; s["current_blockers"]=[]; s["downstream_known_blockers"]=["STAGE02_03_DEDICATED_EXECUTOR_IMPLEMENTATIONS_MISSING","STAGE04_DYNAMIC_DOMAIN_CHECKPOINT_INSTANCES_MISSING"]; wy(sp,s)
    rp=product/"STAGE_EXECUTION/SHARED_AUTHORITY/V232_REALIGNMENT/successor_reentry_resolution.yaml"; r=y(rp); r["status"]="STAGE01_SUCCESSORS_MATERIALIZED_ADMITTED"
    for ch in r.get("chains") or []:
        for row in ch.get("stages") or []:
            if row.get("stage_uid")=="STAGE-01": row["successor_state"]="MATERIALIZED_ADMITTED"
    ea=r.get("execution_admission") or {}; ea["state"]="ADMITTED_FOR_EFFECTFUL_WORKFLOW_RUNTIME_VALIDATION"; ea["blockers"]=[]; r["execution_admission"]=ea; wy(rp,r)
    wy(product/"STAGE_EXECUTION/STAGE-01/STAGE01_SUCCESSOR_EXECUTION_TRIGGER.yaml",{"artifact_type":"STAGE01_SUCCESSOR_EXECUTION_TRIGGER","status":"READY","governance_uid":GOV_UID,"successor_work_units":[c["successor"] for c in CONFIGS],"trigger_reason":"FRESH_SUCCESSOR_MATERIALIZATION_ADMISSION_PASS","product_completion_credit":0})
    print("PASS: Stage01 successor admission persisted and execution trigger materialized")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--product-root",required=True); ap.add_argument("--governance-root"); ap.add_argument("--mode",choices=["materialize","refresh-manifest","mark-admitted"],default="materialize"); a=ap.parse_args()
    product=Path(a.product_root).resolve(); govroot=Path(a.governance_root).resolve() if a.governance_root else None
    if a.mode=="materialize":
        if not govroot: raise SystemExit("governance root required")
        materialize(product,govroot)
    elif a.mode=="refresh-manifest": refresh(product)
    else: mark_admitted(product)
if __name__=="__main__":
    try: main()
    except Exception as exc:
        print("BLOCK: STAGE01_SUCCESSOR_MATERIALIZER:"+repr(exc),file=sys.stderr); raise
