#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, re, sys
from pathlib import Path
import yaml

sys.dont_write_bytecode = True
REQUIRED_DOMAINS = {"PAGE_CONSTRUCTION_DESIGN", "VISUAL_CONSTRUCTION_DESIGN"}
CURRENT_CLASSES = {"CURRENT_AUTHORITY","CURRENT_SOURCE","CURRENT_CONTRACT","CURRENT_IMPLEMENTATION","CURRENT_TEST","CURRENT_CONFIG","CURRENT_EVIDENCE_TEMPLATE","CURRENT_SHARED_DEPENDENCY"}
REFERENCE_CLASSES = {"REFERENCE_ONLY_SOURCE_SNAPSHOT","PROPOSED_CHANGE_INPUT_REFERENCE","HISTORICAL_EVIDENCE_REFERENCE"}
FORBIDDEN_PARTS = {"__pycache__", ".next", "dist", "build", "coverage", "playwright-report", "test-results", "node_modules"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".tmp", ".bak", ".swp"}


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def result(gate: str, failures: list):
    return {"gate": gate, "status": "PASS" if not failures else "FAIL", "failures": failures}


def compute_current_tree_fingerprint(root: Path) -> str:
    entries=[]
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel=p.relative_to(root).as_posix()
        parts=Path(rel).parts
        if rel.startswith("11_EVIDENCE/"):
            continue
        if any(x in FORBIDDEN_PARTS for x in parts) or p.suffix in {".pyc", ".pyo"}:
            continue
        entries.append(f"{rel}\0{hashlib.sha256(p.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(entries).encode()).hexdigest()


def check_canonical_governance(root: Path):
    p=root/"authority/global/ACPOS_WEBSITE_CONSTRUCTION_GOVERNANCE_FINAL_LOCKED_V1.0.yaml"
    f=[]
    if not p.exists(): return result("canonical_governance_owner", ["canonical owner missing"])
    try: d=load_yaml(p)
    except Exception as e: return result("canonical_governance_owner", [f"yaml parse: {e}"])
    a=d.get("authority") or {}; v=d.get("governance_package_v2_1_2") or {}
    if a.get("id")!="ACPOS_WEBSITE_CONSTRUCTION_GOVERNANCE": f.append("wrong authority id")
    if a.get("status")!="FINAL_LOCKED" or a.get("current_only") is not True: f.append("canonical status/current_only invalid")
    if "V2.1.2" not in str(a.get("revision", "")): f.append("v2.1.2 revision not materialized")
    if str(v.get("package_version"))!="2.1.2": f.append("v2.1.2 package block missing")
    if v.get("selected_project_topology")!="MULTI_PAGE_FOUNDATION_THEN_PAGE_VERTICAL": f.append("wrong project topology")
    sd=(v.get("source_domain_decomposition_gate") or {})
    if set(sd.get("required_domains_per_page") or [])!=REQUIRED_DOMAINS: f.append("required planning domains not locked")
    mc=v.get("minimal_control_governance_self_test") or {}
    if mc.get("fixture_policy")!="OBSERVABLE_FACTS_ONLY": f.append("minimal-control fixture policy missing")
    cs=v.get("current_tree_clean_scan_freshness") or {}
    if cs.get("deterministic_tree_fingerprint_required") is not True: f.append("clean-scan fingerprint rule missing")
    return result("canonical_governance_owner", f)


def check_source_domain_decomposition(root: Path):
    p=root/"00_SOURCE_INTAKE/SOURCE_DOMAIN_DECOMPOSITION.yaml"; f=[]
    if not p.exists(): return result("source_domain_decomposition", ["decomposition ledger missing"])
    try: d=load_yaml(p)
    except Exception as e: return result("source_domain_decomposition", [f"yaml parse: {e}"])
    pages=d.get("required_pages") or []; domains=d.get("required_domains") or []
    if not pages: f.append("required_pages empty")
    if set(domains)!=REQUIRED_DOMAINS: f.append("required_domains invalid")
    sources=d.get("source_records") or []; by_uid={}
    for s in sources:
        uid=s.get("source_uid")
        if not uid or uid in by_uid: f.append({"duplicate_or_missing_source_uid":uid})
        else: by_uid[uid]=s
        observed=set(s.get("observed_domains") or [])
        if len(observed)>1 and (s.get("current_load_graph_eligible") is True or s.get("positive_current_authority") is True):
            f.append({"mixed_domain_source_promoted_current":uid})
        if s.get("source_role") in {"PROPOSED_CHANGE_INPUT","REFERENCE_ONLY","HISTORICAL"} and s.get("positive_current_authority") is True:
            f.append({"noncurrent_source_self_promoted":uid})
    extractions=d.get("extraction_records") or []; extraction_by={}
    for x in extractions:
        uid=x.get("source_uid"); tp=x.get("target_path")
        if uid not in by_uid: f.append({"extraction_unknown_source":uid})
        extraction_by.setdefault(uid,[]).append(x)
        if not tp: f.append({"extraction_target_missing":uid})
        elif not (root/tp).exists(): f.append({"extraction_target_not_physical":tp})
    for uid,s in by_uid.items():
        state=s.get("materialization_state")
        has=bool(extraction_by.get(uid))
        if state in {"NOT_YET_EXTRACTED","PENDING"} and has: f.append({"inventory_extraction_contradiction":uid})
        if state in {"EXTRACTED_REFERENCE_ONLY","EXTRACTED_CURRENT","IMPORTED_APPROVED"} and not has: f.append({"inventory_missing_extraction_record":uid})
    artifacts=d.get("artifacts") or []; matrix={}; targets={}; owners={}
    for a in artifacts:
        uid=a.get("artifact_uid"); page=a.get("page_uid"); domain=a.get("planning_domain")
        if page not in pages: f.append({"artifact_unknown_page":uid})
        if domain not in REQUIRED_DOMAINS: f.append({"artifact_invalid_domain":uid})
        if isinstance(domain,(list,dict,set,tuple)): f.append({"artifact_multi_domain":uid})
        if a.get("current_load_graph_eligible") is not True or a.get("status")!="CURRENT_PLANNING": f.append({"artifact_not_current_planning":uid})
        tp=a.get("target_path"); owner=a.get("canonical_owner_ref")
        if not tp or not (root/tp).exists(): f.append({"current_artifact_target_not_physical":tp})
        if not owner: f.append({"current_artifact_owner_missing":uid})
        lineage=a.get("source_lineage") or []
        if not lineage: f.append({"artifact_lineage_missing":uid})
        for ln in lineage:
            suid=ln.get("source_uid") if isinstance(ln,dict) else None
            if suid not in by_uid: f.append({"artifact_lineage_unknown_source":uid})
            if not (ln.get("source_section_refs") if isinstance(ln,dict) else None): f.append({"artifact_lineage_section_missing":uid})
        if not re.fullmatch(r"[0-9a-fA-F]{64}", str(a.get("content_hash", ""))): f.append({"artifact_content_hash_invalid":uid})
        matrix.setdefault((page,domain),[]).append(a)
        if tp: targets.setdefault((page,tp),[]).append(domain)
        if owner: owners.setdefault((page,owner),[]).append(domain)
    for page in pages:
        for domain in REQUIRED_DOMAINS:
            if len(matrix.get((page,domain),[]))!=1: f.append({"required_domain_owner_count":{"page_uid":page,"planning_domain":domain,"count":len(matrix.get((page,domain),[]))}})
    for (page,tp), ds in targets.items():
        if set(ds)==REQUIRED_DOMAINS: f.append({"page_visual_same_target":{"page_uid":page,"target_path":tp}})
    for (page,owner), ds in owners.items():
        if set(ds)==REQUIRED_DOMAINS: f.append({"page_visual_same_owner":{"page_uid":page,"owner":owner}})
    return result("source_domain_decomposition", f)


def check_rebuild_branch_isolation(root: Path, observed_revision: str|None=None):
    p=root/"11_EVIDENCE/audit/REBUILD_BRANCH_ISOLATION.yaml"; f=[]
    if not p.exists(): return result("rebuild_branch_isolation", ["isolation ledger missing"])
    try: d=load_yaml(p)
    except Exception as e: return result("rebuild_branch_isolation", [f"yaml parse: {e}"])
    rb=d.get("rebuild_branch"); lb=d.get("legacy_source_branch")
    if not rb or not lb or rb==lb: f.append("branch isolation invalid")
    if d.get("legacy_source_access")!="READ_ONLY_EXTRACTION_ONLY": f.append("legacy source not read-only extraction")
    if d.get("current_load_graph_policy")!="ALLOWLIST_ONLY": f.append("current load graph policy invalid")
    if d.get("bulk_import_from_legacy") is not False: f.append("bulk import not forbidden")
    if d.get("direct_merge_from_legacy") is not False: f.append("direct merge not forbidden")
    for k in ["unclassified_extraction_count","duplicate_target_count","current_tree_garbage_count","superseded_current_path_count","unreferenced_current_file_count"]:
        if d.get(k,0) not in (0,False,None): f.append({k:d.get(k)})
    seen={}
    req=["batch_uid","source_branch","source_revision","source_path","source_blob_sha","classification","authority_disposition","dependency_reason","target_path","target_role","current_load_graph_eligible","status"]
    for i,x in enumerate(d.get("extractions") or []):
        rid=x.get("source_path") or f"index:{i}"
        miss=[k for k in req if x.get(k) in (None,"")]
        if miss: f.append({"extraction_missing":{"record":rid,"fields":miss}})
        if x.get("source_branch")!=lb: f.append({"wrong_source_branch":rid})
        if not re.fullmatch(r"[0-9a-fA-F]{40}",str(x.get("source_revision",""))): f.append({"bad_source_revision":rid})
        if not re.fullmatch(r"[0-9a-fA-F]{40}",str(x.get("source_blob_sha",""))): f.append({"bad_source_blob_sha":rid})
        cls=x.get("classification")
        if cls in CURRENT_CLASSES:
            if x.get("current_load_graph_eligible") is not True or x.get("status")!="IMPORTED_APPROVED": f.append({"invalid_current_import":rid})
        elif cls in REFERENCE_CLASSES:
            if x.get("current_load_graph_eligible") is not False or x.get("status")!="IMPORTED_REFERENCE_ONLY": f.append({"reference_entered_current_graph":rid})
            if x.get("authority_disposition") not in {"REFERENCE_ONLY","NONCURRENT_REFERENCE","CHANGE_INPUT_ONLY"}: f.append({"reference_disposition_invalid":rid})
        else: f.append({"classification_invalid":cls})
        tp=x.get("target_path")
        if tp in seen: f.append({"duplicate_target":tp})
        seen[tp]=rid
        if tp and not (root/tp).exists(): f.append({"target_not_physical":tp})
    scan=d.get("clean_scan") or {}
    if scan.get("status")!="PASS" or not scan.get("captured_at") or not scan.get("evidence_ref") or not scan.get("captured_from_revision"):
        f.append({"clean_scan_incomplete":scan})
    declared=scan.get("inspected_current_tree_fingerprint"); actual=compute_current_tree_fingerprint(root)
    if not declared: f.append("clean_scan_tree_fingerprint_missing")
    elif declared!=actual: f.append({"stale_clean_scan_tree":{"declared":declared,"actual":actual}})
    if observed_revision and scan.get("captured_from_revision")!=observed_revision:
        f.append({"stale_clean_scan_revision":{"captured":scan.get("captured_from_revision"),"observed":observed_revision}})
    return result("rebuild_branch_isolation", f)


def check_branch_garbage(root: Path):
    bad=[]
    for p in root.rglob("*"):
        if not p.is_file(): continue
        rel=p.relative_to(root).as_posix(); parts=Path(rel).parts
        if any(x in FORBIDDEN_PARTS for x in parts) or p.suffix in FORBIDDEN_SUFFIXES or p.name.endswith("~"):
            bad.append(rel)
    return result("branch_garbage", sorted(bad))


def validate(root: Path, observed_revision: str|None=None):
    checks=[check_canonical_governance(root), check_source_domain_decomposition(root), check_rebuild_branch_isolation(root, observed_revision), check_branch_garbage(root)]
    return {"status":"PASS" if all(x["status"]=="PASS" for x in checks) else "FAIL", "checks":checks}

if __name__=="__main__":
    root=Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()
    out=validate(root, os.environ.get("GOV_OBSERVED_SOURCE_REVISION"))
    print(json.dumps(out,ensure_ascii=False,indent=2))
    raise SystemExit(0 if out["status"]=="PASS" else 1)
