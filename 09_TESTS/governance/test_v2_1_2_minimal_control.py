#!/usr/bin/env python3
import hashlib, importlib.util, json, pathlib, sys, tempfile, yaml
sys.dont_write_bytecode=True
base=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("vg", base/"validate_rebuild_governance.py")
vg=importlib.util.module_from_spec(spec); spec.loader.exec_module(vg)

def put(root, rel, data="x"):
    p=root/rel; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(data,sort_keys=False) if isinstance(data,(dict,list)) else str(data),encoding="utf-8")
    return p

def source(uid="S1", role="REFERENCE_ONLY", state="EXTRACTED_REFERENCE_ONLY", eligible=False, positive=False):
    return {"source_uid":uid,"source_role":role,"materialization_state":state,"current_load_graph_eligible":eligible,"positive_current_authority":positive,"observed_domains":["PAGE_CONSTRUCTION_DESIGN","VISUAL_CONSTRUCTION_DESIGN"]}

def extraction(uid="S1", target="00_SOURCE_INTAKE/reference/source.yaml"):
    return {"source_uid":uid,"target_path":target}

def artifact(uid,page,domain,target,owner,source_uid="S1"):
    return {"artifact_uid":uid,"page_uid":page,"planning_domain":domain,"target_path":target,"canonical_owner_ref":owner,"source_lineage":[{"source_uid":source_uid,"source_section_refs":["section-1"]}],"content_hash":hashlib.sha256(uid.encode()).hexdigest(),"current_load_graph_eligible":True,"status":"CURRENT_PLANNING"}

def domain_doc():
    return {"required_pages":["CORE-01"],"required_domains":["PAGE_CONSTRUCTION_DESIGN","VISUAL_CONSTRUCTION_DESIGN"],"source_records":[source()],"extraction_records":[extraction()],"artifacts":[]}

def eval_domain(doc, physical=()):
    with tempfile.TemporaryDirectory() as td:
        r=pathlib.Path(td); put(r,"00_SOURCE_INTAKE/SOURCE_DOMAIN_DECOMPOSITION.yaml",doc)
        for x in physical: put(r,x,"artifact")
        return vg.check_source_domain_decomposition(r)["status"]

def isolation_doc(eligible=False):
    sha="a"*40
    rec={"batch_uid":"EX-1","source_branch":"new","source_revision":sha,"source_path":"authority/source.yaml","source_blob_sha":"b"*40,"classification":"REFERENCE_ONLY_SOURCE_SNAPSHOT","authority_disposition":"REFERENCE_ONLY","dependency_reason":"provenance","target_path":"00_SOURCE_INTAKE/reference/source.yaml","target_role":"REFERENCE_ONLY_SOURCE_SNAPSHOT","current_load_graph_eligible":eligible,"status":"IMPORTED_REFERENCE_ONLY"}
    return {"rebuild_branch":"rebuild-v2.1.1","legacy_source_branch":"new","legacy_source_access":"READ_ONLY_EXTRACTION_ONLY","current_load_graph_policy":"ALLOWLIST_ONLY","bulk_import_from_legacy":False,"direct_merge_from_legacy":False,"unclassified_extraction_count":0,"duplicate_target_count":0,"current_tree_garbage_count":0,"superseded_current_path_count":0,"unreferenced_current_file_count":0,"extractions":[rec],"clean_scan":{"captured_at":"2026-09-12T00:00:00Z","captured_from_revision":sha,"evidence_ref":"SCAN","status":"PASS"}}

def eval_isolation(doc, mutate_after_scan=False):
    with tempfile.TemporaryDirectory() as td:
        r=pathlib.Path(td); put(r,"REBUILD_BRANCH_BASELINE.yaml","baseline"); put(r,"00_SOURCE_INTAKE/reference/source.yaml","source")
        doc=dict(doc); doc["clean_scan"]=dict(doc["clean_scan"]); doc["clean_scan"]["inspected_current_tree_fingerprint"]=vg.compute_current_tree_fingerprint(r)
        if mutate_after_scan: put(r,"00_SOURCE_INTAKE/new-current.yaml","new")
        put(r,"11_EVIDENCE/audit/REBUILD_BRANCH_ISOLATION.yaml",doc)
        return vg.check_rebuild_branch_isolation(r)["status"]

cases=[]
d=domain_doc(); cases.append(("mixed_reference_without_decomposition",eval_domain(d,["00_SOURCE_INTAKE/reference/source.yaml"]),"FAIL"))
d=domain_doc(); d["artifacts"]=[artifact("P","CORE-01","PAGE_CONSTRUCTION_DESIGN","01_PLAN/CORE.yaml","OWNER-P"),artifact("V","CORE-01","VISUAL_CONSTRUCTION_DESIGN","01_PLAN/CORE.yaml","OWNER-V")]; cases.append(("page_visual_same_target",eval_domain(d,["00_SOURCE_INTAKE/reference/source.yaml","01_PLAN/CORE.yaml"]),"FAIL"))
d=domain_doc(); d["artifacts"]=[artifact("P","CORE-01","PAGE_CONSTRUCTION_DESIGN","01_PLAN/P.yaml","OWNER-X"),artifact("V","CORE-01","VISUAL_CONSTRUCTION_DESIGN","02_VISUAL/V.yaml","OWNER-X")]; cases.append(("page_visual_same_owner",eval_domain(d,["00_SOURCE_INTAKE/reference/source.yaml","01_PLAN/P.yaml","02_VISUAL/V.yaml"]),"FAIL"))
d=domain_doc(); d["source_records"][0]["materialization_state"]="NOT_YET_EXTRACTED"; cases.append(("inventory_extraction_contradiction",eval_domain(d,["00_SOURCE_INTAKE/reference/source.yaml"]),"FAIL"))
d=domain_doc(); d["source_records"]=[source(role="PROPOSED_CHANGE_INPUT",positive=True)]; cases.append(("proposed_change_self_promotion",eval_domain(d,["00_SOURCE_INTAKE/reference/source.yaml"]),"FAIL"))
d=domain_doc(); d["artifacts"]=[artifact("P","CORE-01","PAGE_CONSTRUCTION_DESIGN","01_PLAN/P.yaml","OWNER-P"),artifact("V","CORE-01","VISUAL_CONSTRUCTION_DESIGN","02_VISUAL/V.yaml","OWNER-V")]; cases.append(("valid_independent_page_visual",eval_domain(d,["00_SOURCE_INTAKE/reference/source.yaml","01_PLAN/P.yaml","02_VISUAL/V.yaml"]),"PASS"))
cases.append(("stale_clean_scan_after_mutation",eval_isolation(isolation_doc(False),True),"FAIL"))
cases.append(("current_clean_scan",eval_isolation(isolation_doc(False),False),"PASS"))
cases.append(("reference_only_in_current_graph",eval_isolation(isolation_doc(True),False),"FAIL"))

out={"suite":"v2.1.2 minimal-control governance self-test","minimal_control":True,"fixture_policy":"OBSERVABLE_FACTS_ONLY","total":len(cases),"passed_expectations":sum(a==e for _,a,e in cases),"results":[{"case":n,"actual":a,"expected":e,"ok":a==e} for n,a,e in cases]}
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out["passed_expectations"]==out["total"] else 1)
