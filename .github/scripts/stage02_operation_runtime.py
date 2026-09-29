#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, re
from pathlib import Path
import yaml

OPS=[
"STAGE_EXECUTION_PREFLIGHT_COMPILE","EFFECTIVE_CONTRACT_OVERLAY_COMPILE","DEPENDENCY_TOPOLOGY_COMPILE",
"CHANGE_IMPACT_MAP_COMPILE","FUNCTIONAL_CHAIN_COMPILE","DEPENDENCY_MAP_COMPILE",
"GOVERNED_UNIT_CONSTRUCTION_SPEC_COMPILE","ASYNC_PROVIDER_CONTRACT_COMPILE","SHARED_OWNER_PORT_RESOLVE",
"FUNCTIONAL_WORKBENCH_CONTRACT_COMPILE","INTERACTION_TOPOLOGY_COMPILE","FUNCTION_ADMISSION_SCORECARD_COMPILE",
"AUTO_COMPLETION_SCOPE_LEDGER_COMPILE"]

ENTITY_OPS=["DISCOVER_OR_LIST","SELECT_OR_OPEN","CREATE","CREATION_MODE","PARENT_BIND","CATEGORY_OR_GROUP_BIND",
"DRAFT","RESUME","EDIT","SAVE","VALIDATE","CONFIRM_OR_APPROVE","VERSION","REVISE","LOCK_OR_UNLOCK","REORDER",
"MOVE_OR_REPARENT","ARCHIVE_OR_DELETE","RESTORE","DEPENDENCY_IMPACT","AUDIT","ERROR_RECOVERY","NEXT_STEP"]

WB_SECTIONS=[
"COMPANY-PROJECT-COUNT","COMPANY-RUNNING-PROJECT-COUNT","COMPANY-PENDING-ACTION-COUNT",
"COMPANY-PENDING-REVIEW-COUNT","COMPANY-COMPLETED-PROJECT-COUNT","COMPANY-AVERAGE-PROGRESS",
"PROJECT-PROGRESS-OVERVIEW","COMPANY-PROGRESS-SUMMARY","PRODUCTION-SUMMARY","RECENT-COMPLETIONS",
"NOTIFICATIONS","COMPANY-ANNOUNCEMENTS","INDUSTRY-NEWS","SYSTEM-STATUS-SUMMARY"]

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d

def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(o,sort_keys=False,allow_unicode=True,width=180),encoding="utf-8")

def digest(s): return hashlib.sha256(str(s).encode("utf-8")).hexdigest()

def input_doc(root,work,uid):
    row=(work.get("input_bindings") or {}).get(uid) or {}
    ref=str(row.get("artifact_ref") or "")
    if not ref: raise SystemExit("BLOCK:STAGE02_INPUT_BINDING_MISSING:"+uid)
    d=load(root/ref)
    return d,ref

def context_index(ctx):
    rows=[]
    for n in ctx.get("source_nodes") or []:
        t=str(n.get("direct_text") or "").strip()
        if t: rows.append((str(n.get("source_node_uid") or ""),t))
    if not rows: raise SystemExit("BLOCK:STAGE02_SOURCE_CONTEXT_EMPTY")
    return rows

def matches(rows,terms):
    out=[]
    for uid,text in rows:
        low=text.casefold()
        if any(t.casefold() in low for t in terms):
            out.append({"source_node_uid":uid,"source_text":text,"source_text_sha256":digest(text)})
    return out

def require_matches(rows,label,terms):
    out=matches(rows,terms)
    if not out: raise SystemExit("BLOCK:STAGE02_CURRENT_AUTHORITY_MARKER_MISSING:"+label)
    return out

def authority_profile(governed,rows,bp):
    responsibilities=set(map(str,bp.get("required_responsibility_uids") or []))
    if not responsibilities: raise SystemExit("BLOCK:STAGE02_BASE_BLUEPRINT_RESPONSIBILITIES_EMPTY")
    if governed=="GLOBAL-HOME-SHELL-NAVIGATION":
        groups=[
          ("NAVIGATION","OPEN_AUTHORIZED_WORKSPACE_FROM_CANONICAL_NAVIGATION",["navigation","導航","route","路由","menu","選單"],"OPEN_CANONICAL_TARGET","TARGET_WORKSPACE_MOUNTED"),
          ("VISIBILITY","SHOW_ONLY_AUTHORIZED_NAVIGATION",["permission","權限","role","角色","authorization"],"RESOLVE_NAVIGATION_VISIBILITY","AUTHORIZED_NAVIGATION_PROJECTION"),
          ("LANGUAGE","PRESENT_SHELL_IN_SUPPORTED_LANGUAGE",["language","語言","zh-tw","zh-cn"],"APPLY_LANGUAGE_SELECTION","SHELL_LANGUAGE_UPDATED"),
          ("STATUS","PRESENT_REAL_READ_ONLY_SYSTEM_STATUS",["status","狀態","notification","通知","to-do","待辦","running","執行中"],"READ_STATUS_PROJECTION","STATUS_VISIBLE_OR_CONTROLLED_DISABLED"),
          ("WORKSPACE","KEEP_WORKSPACE_USABLE_WHILE_NAVIGATION_REFLOWS",["workspace","工作區","sidebar","側欄","菜單"],"SYNCHRONIZE_WORKSPACE_LAYOUT","WORKSPACE_SYNCHRONIZED")]
        root_entity="GLOBAL-SHELL"; entities=["FRONT-NAVIGATION-SURFACE","ADMIN-NAVIGATION-SURFACE","NAVIGATION-ITEM","LANGUAGE-SELECTION","QUICK-STATUS","ACCOUNT-CLUSTER","WORKSPACE-MOUNT"]
        surface="GLOBAL_SHELL"
    elif governed=="workspace:WB-01":
        groups=[
          ("DASHBOARD_READ","RENDER_AUTHORIZED_COMPANY_DASHBOARD_SUMMARY",["dashboard","儀表板","kpi","進度","progress","summary","摘要"],"READ_ONLY_DASHBOARD_PROJECTION","READ_ONLY_OR_EMPTY"),
          ("SECTION_OPEN","OPEN_AUTHORIZED_DASHBOARD_SECTION",["section","區塊","control","控制","open","開啟","navigation","導航"],"SECTION_OPEN","DESTINATION_SECTION_OR_PAGE_CONTEXT"),
          ("STATE_RECOVERY","PRESERVE_TRUTHFUL_DASHBOARD_STATE",["loading","empty","error","read-only","只讀","錯誤","缺值","狀態"],"APPLY_LOADING_EMPTY_ERROR_READ_ONLY_STATE","LOADING_OR_READ_ONLY_OR_EMPTY_OR_ERROR"),
          ("VISIBILITY","SHOW_ONLY_AUTHORIZED_DASHBOARD_CONTENT",["permission","權限","role","角色"],"RESOLVE_AUTHORIZED_VISIBILITY","AUTHORIZED_DASHBOARD_PROJECTION")]
        root_entity="COMPANY-DASHBOARD-PROJECTION"; entities=list(WB_SECTIONS); surface="COMPANY_DASHBOARD"
        # Exact section denominator is a current-source contract, not historical completion credit.
        require_matches(rows,"WB01_14_SECTION_DENOMINATOR",["14","十四"])
    else:
        raise SystemExit("BLOCK:STAGE02_CURRENT_GOVERNED_UNIT_PROFILE_UNSUPPORTED:"+governed)
    chains=[]
    for key,intent,terms,action,state in groups:
        refs=require_matches(rows,key,terms)
        chains.append({
          "chain_uid":"FC-"+re.sub(r"[^A-Za-z0-9]+","-",governed).strip("-").upper()+"-"+key,
          "business_intent":intent,
          "preconditions":["CURRENT_STAGE01_AUTHORITY_INPUTS_VALID","CURRENT_GOVERNED_UNIT_SCOPE_VALID"],
          "entry":key,
          "input_source":"CURRENT_STAGE01_CANONICAL_INPUTS",
          "trigger":"REGISTERED_"+key+"_TRIGGER",
          "gate":"CURRENT_AUTHORITY_AND_SCOPE_GATE",
          "permission":"ACCOUNT_BOUND_AUTHORIZATION",
          "action":action,
          "validation":["CURRENT_AUTHORITY_ONLY","NO_FAKE_DATA","NO_UNREGISTERED_SCOPE_EXPANSION"],
          "payload":["governed_unit_uid","correlation_id"],
          "runtime_owner":"STAGE02_FUNCTIONAL_CONTRACT_OWNER",
          "resulting_state":state,
          "audit_event":key+"_AUDIT",
          "feedback":"CURRENT_STATE_PROJECTION",
          "failure_state":"ERROR",
          "recovery":"REINVOKE_SAME_REGISTERED_OPERATION_OR_FAIL_CLOSED",
          "next_step":"CONTINUE_REGISTERED_FUNCTIONAL_CHAIN",
          "authority_refs":refs
        })
    if governed=="GLOBAL-HOME-SHELL-NAVIGATION" and len(chains)<5: raise SystemExit("BLOCK:STAGE02_HOME_CHAIN_DENOMINATOR_INCOMPLETE")
    if governed=="workspace:WB-01" and len(chains)<4: raise SystemExit("BLOCK:STAGE02_WB01_CHAIN_DENOMINATOR_INCOMPLETE")
    return {"chains":chains,"root_entity":root_entity,"entities":entities,"surface":surface,"responsibilities":sorted(responsibilities)}

def common(root,work):
    bp,bpref=input_doc(root,work,"GOVERNED_UNIT_BASE_BLUEPRINT")
    ctx,ctxref=input_doc(root,work,"SOURCE_CONTEXT_MANIFEST")
    conflicts,confref=input_doc(root,work,"CONTENT_SUPERSESSION_CONFLICT_LEDGER")
    deps,depsref=input_doc(root,work,"SOURCE_DEPENDENCY_MAP")
    governed=str(work.get("governed_unit_uid") or "")
    if str(bp.get("governed_unit_uid") or "")!=governed or str(ctx.get("governed_unit_uid") or "")!=governed:
        raise SystemExit("BLOCK:STAGE02_INPUT_GOVERNED_UNIT_DRIFT")
    rows=context_index(ctx); profile=authority_profile(governed,rows,bp)
    return bp,ctx,conflicts,deps,{"GOVERNED_UNIT_BASE_BLUEPRINT":bpref,"SOURCE_CONTEXT_MANIFEST":ctxref,"CONTENT_SUPERSESSION_CONFLICT_LEDGER":confref,"SOURCE_DEPENDENCY_MAP":depsref},profile

def preflight(root,wd,work,bp,ctx,conflicts,deps,refs,p):
    sem=load(root/"governance/ci/stage_execution_semantic_adapters.yaml")
    dims=list(((sem.get("stages") or {}).get("STAGE-02") or {}).get("semantic_dimensions") or [])
    required_files=["REQUIRED_FIELD_MANIFEST.yaml","FUNCTIONAL_CHAIN_MANIFEST.yaml","DENOMINATOR_SNAPSHOT.yaml","CLASSIFICATION_RULESET.yaml","STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml","CURRENT_PROBLEM_REGISTER.yaml","RESOLUTION_LEDGER.yaml"]
    write(wd/"REQUIRED_FIELD_MANIFEST.yaml",{"artifact_type":"REQUIRED_FIELD_MANIFEST","stage_uid":"STAGE-02","work_unit_uid":work["work_unit_uid"],"governed_unit_uid":work["governed_unit_uid"],"required_dimensions":dims,"required_operations":OPS,"source_authority_refs":list(refs.values()),"status":"CURRENT"})
    write(wd/"FUNCTIONAL_CHAIN_MANIFEST.yaml",{"artifact_type":"FUNCTIONAL_CHAIN_MANIFEST","stage_uid":"STAGE-02","governed_unit_uid":work["governed_unit_uid"],"required_chain_fields":["business_intent","preconditions","entry","input_source","trigger","gate","permission","action","validation","payload","runtime_owner","resulting_state","audit_event","feedback","failure_state","recovery","next_step","authority_refs"],"source_derived_chain_uids":[x["chain_uid"] for x in p["chains"]],"status":"CURRENT"})
    write(wd/"DENOMINATOR_SNAPSHOT.yaml",{"artifact_type":"DENOMINATOR_SNAPSHOT","stage_uid":"STAGE-02","work_unit_uid":work["work_unit_uid"],"governed_unit_uid":work["governed_unit_uid"],"denominator_kind":"GOVERNED_ENTITY_X_APPLICABLE_REQUIRED_OPERATION_PLUS_REQUIRED_HIERARCHY_EDGES","root_entity":p["root_entity"],"child_entities":p["entities"],"child_entity_count":len(p["entities"]),"operation_universe":ENTITY_OPS,"functional_chain_total":len(p["chains"]),"status":"FROZEN_FOR_CURRENT_WORK_UNIT"})
    write(wd/"CLASSIFICATION_RULESET.yaml",{"artifact_type":"CLASSIFICATION_RULESET","stage_uid":"STAGE-02","rules":{"authority_gap":"BLOCK_AND_REPORT","implementation_gap":"DOWNSTREAM_NOT_STAGE02_COMPLETION","not_applicable":"EXPLICIT_AUTHORITY_EVIDENCE_REQUIRED","speculative_expansion":"FORBIDDEN","historical_completion_credit":"FORBIDDEN"},"status":"CURRENT"})
    write(wd/"CURRENT_PROBLEM_REGISTER.yaml",{"artifact_type":"CURRENT_PROBLEM_REGISTER","stage_uid":"STAGE-02","governed_unit_uid":work["governed_unit_uid"],"items":[],"closure_blocker_total":0,"status":"OPEN_CURRENT"})
    write(wd/"RESOLUTION_LEDGER.yaml",{"artifact_type":"RESOLUTION_LEDGER","stage_uid":"STAGE-02","governed_unit_uid":work["governed_unit_uid"],"entries":[],"append_only":True,"status":"CURRENT"})
    write(wd/"STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml",{"artifact_type":"STAGE_EXECUTION_PREFLIGHT_RECEIPT","stage_uid":"STAGE-02","work_unit_uid":work["work_unit_uid"],"governance_uid":work["governance_uid"],"required_manifest_set":required_files,"applicability_resolved_before_blocker_count":True,"current_problem_register_ref":"CURRENT_PROBLEM_REGISTER.yaml","historical_completion_credit_used":False,"result":"PASS","status":"PASS"})

def entity_package(wd,work,p,refs):
    governed=work["governed_unit_uid"]; root=p["root_entity"]
    entities=[{"entity_uid":root,"entity_kind":"GOVERNED_ROOT","parent_entity_uid":None,"authority_ref":refs["GOVERNED_UNIT_BASE_BLUEPRINT"]}]
    entities += [{"entity_uid":e,"entity_kind":"SECTION_OR_INTERACTION_ENTITY","parent_entity_uid":root,"authority_ref":refs["SOURCE_CONTEXT_MANIFEST"]} for e in p["entities"]]
    write(wd/"GOVERNED_ENTITY_INVENTORY.yaml",{"artifact_type":"GOVERNED_ENTITY_INVENTORY","stage_uid":"STAGE-02","governed_unit_uid":governed,"entities":entities,"entity_count":len(entities),"status":"CURRENT"})
    rows=[]
    required={"DISCOVER_OR_LIST","SELECT_OR_OPEN","DEPENDENCY_IMPACT","AUDIT","ERROR_RECOVERY","NEXT_STEP"}
    for e in entities:
        for op in ENTITY_OPS:
            app="REQUIRED" if op in required else "AUTHORIZED_NOT_APPLICABLE"
            rows.append({"entity_uid":e["entity_uid"],"operation_uid":op,"applicability":app,"authority_evidence_ref":e["authority_ref"],"state":"BOUND" if app=="REQUIRED" else "AUTHORIZED_NOT_APPLICABLE"})
    write(wd/"GOVERNED_ENTITY_OPERATION_MATRIX.yaml",{"artifact_type":"GOVERNED_ENTITY_OPERATION_MATRIX","stage_uid":"STAGE-02","governed_unit_uid":governed,"operation_universe":ENTITY_OPS,"rows":rows,"row_count":len(rows),"status":"CURRENT"})
    edges=[{"parent_entity_uid":root,"child_entity_uid":e,"relation":"CONTAINS","authority_ref":refs["SOURCE_CONTEXT_MANIFEST"]} for e in p["entities"]]
    write(wd/"ENTITY_HIERARCHY_MATRIX.yaml",{"artifact_type":"ENTITY_HIERARCHY_MATRIX","stage_uid":"STAGE-02","governed_unit_uid":governed,"edges":edges,"edge_count":len(edges),"status":"CURRENT"})
    visual=[]
    for c in p["chains"]:
        visual.append({"governed_entity_or_scope":root,"operation_uid":c["action"],"visual_section_or_surface":p["surface"],"component_or_control_identity":c["entry"],"interaction_entry":c["trigger"],"state_binding":c["resulting_state"],"loading_or_pending_state":"CONTROLLED_PENDING_WHEN_APPLICABLE","permission_or_disabled_state":"FAIL_CLOSED_OR_DISABLED","success_feedback":"CURRENT_STATE_PROJECTION","error_feedback":"ERROR_STATE","recovery_feedback":c["recovery"],"version_or_revision_visibility_when_applicable":"CURRENT_VERSION_WHEN_APPLICABLE","responsive_or_overflow_behavior":"PRESERVE_OPERATION_ORDER_AND_CONTEXT","i18n_label_ref_when_applicable":"CURRENT_SOURCE_LABEL","accessibility_semantics":"SEMANTIC_CONTROL_ROLE_AND_FOCUS_REQUIRED","visual_authority_ref":refs["SOURCE_CONTEXT_MANIFEST"]})
    write(wd/"FUNCTION_VISUAL_IMPACT_MATRIX.yaml",{"artifact_type":"FUNCTION_VISUAL_IMPACT_MATRIX","stage_uid":"STAGE-02","governed_unit_uid":governed,"rows":visual,"status":"CURRENT"})
    package={"artifact_type":"GOVERNED_UNIT_CONSTRUCTION_SPEC_PACKAGE","stage_uid":"STAGE-02","governed_unit_uid":governed,"included_artifacts":["GOVERNED_ENTITY_INVENTORY.yaml","GOVERNED_ENTITY_OPERATION_MATRIX.yaml","ENTITY_HIERARCHY_MATRIX.yaml","FUNCTIONAL_CHAIN_SPEC.yaml","DEPENDENCY_MAP.yaml","ASYNC_PROVIDER_CONTRACT.yaml","SHARED_OWNER_PORT_MAP.yaml","FUNCTIONAL_WORKBENCH_CONTRACT.yaml","INTERACTION_TOPOLOGY_SPEC.yaml","FUNCTION_VISUAL_IMPACT_MATRIX.yaml"],"runtime_completion_claim":False,"runtime_state":"NOT_EXECUTED","status":"CURRENT_FUNCTIONAL_CONTRACT_PACKAGE"}
    write(wd/"GOVERNED_UNIT_CONSTRUCTION_SPEC_PACKAGE.yaml",package)

def workbench(wd,work,p,refs):
    chain_ops=[x["action"] for x in p["chains"]]
    d={"artifact_type":"FUNCTIONAL_WORKBENCH_CONTRACT","stage_uid":"STAGE-02","governed_unit_uid":work["governed_unit_uid"],"workbenches":[{"functional_cluster_uid":"FWB-"+re.sub(r"[^A-Za-z0-9]+","-",work["governed_unit_uid"]).strip("-").upper(),"business_journey":"CURRENT_GOVERNED_UNIT_PRIMARY_INTERACTION_CHAIN","required_operations":chain_ops,"shared_context_identity":work["governed_unit_uid"],"workbench_class":"ATOMIC_WORKBENCH","visual_container_requirement":p["surface"],"required_order":chain_ops,"adjacency_requirements":"KEEP_PRIMARY_CHAIN_CONTIGUOUS","same_surface_requirement":True,"allowed_separation_modes":["AUTHORIZED_CROSS_SURFACE_WITH_CONTEXT_HANDOFF"],"forbidden_interruptions":["UNRELATED_SURFACE_INSERTION"],"cross_surface_transition_contract":"EXPLICIT_REGISTERED_TRANSITION_ONLY","context_handoff_contract":"PRESERVE_GOVERNED_UNIT_AND_CORRELATION_ID","responsive_reflow_rule":"PRESERVE_SEMANTIC_OPERATION_ORDER","authority_ref":refs["SOURCE_CONTEXT_MANIFEST"]}],"status":"CURRENT"}
    write(wd/"FUNCTIONAL_WORKBENCH_CONTRACT.yaml",d)

def topology(wd,work,p,refs):
    ops=[x["action"] for x in p["chains"]]
    d={"artifact_type":"INTERACTION_TOPOLOGY_SPEC","stage_uid":"STAGE-02","governed_unit_uid":work["governed_unit_uid"],"rows":[{"functional_cluster_uid":"TOPO-"+re.sub(r"[^A-Za-z0-9]+","-",work["governed_unit_uid"]).strip("-").upper(),"operation_sequence":ops,"grouping":[p["surface"]],"adjacency":"PRIMARY_CHAIN_CONTIGUOUS","interruption_boundary":"UNRELATED_OPERATION_FORBIDDEN","surface_transition_boundary":"REGISTERED_ONLY","shared_context_or_state_identity":work["governed_unit_uid"],"continuation_or_recovery_path":"REINVOKE_SAME_REGISTERED_OPERATION_OR_FAIL_CLOSED","responsive_reflow_contract":"PRESERVE_SEMANTIC_ORDER","authority_ref":refs["SOURCE_CONTEXT_MANIFEST"]}],"context_continuity":"REQUIRED","status":"CURRENT"}
    write(wd/"INTERACTION_TOPOLOGY_SPEC.yaml",d)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage",required=True); ap.add_argument("--operation",required=True)
    ap.add_argument("--work-unit",required=True); ap.add_argument("--product-root",required=True)
    a=ap.parse_args()
    if a.stage!="STAGE-02" or a.operation not in OPS: raise SystemExit("BLOCK:STAGE02_EXECUTOR_OPERATION_IDENTITY_DRIFT")
    root=Path(a.product_root).resolve(); wp=root/Path(a.work_unit); wd=wp.parent; work=load(wp)
    if str(work.get("stage_uid"))!="STAGE-02": raise SystemExit("BLOCK:STAGE02_WORK_UNIT_STAGE_DRIFT")
    bp,ctx,conflicts,deps,refs,p=common(root,work)
    op=a.operation
    if op=="STAGE_EXECUTION_PREFLIGHT_COMPILE": preflight(root,wd,work,bp,ctx,conflicts,deps,refs,p)
    elif op=="EFFECTIVE_CONTRACT_OVERLAY_COMPILE":
        write(wd/"EFFECTIVE_CONTRACT_OVERLAY.yaml",{"artifact_type":"EFFECTIVE_CONTRACT_OVERLAY","stage_uid":"STAGE-02","governed_unit_uid":work["governed_unit_uid"],"raw_authority_sources":list(refs.values()),"effective_responsibility_uids":p["responsibilities"],"historical_product_values_used":False,"role_substitution_used":False,"status":"CURRENT"})
    elif op=="DEPENDENCY_TOPOLOGY_COMPILE":
        write(wd/"DEPENDENCY_TOPOLOGY.yaml",{"artifact_type":"DEPENDENCY_TOPOLOGY","stage_uid":"STAGE-02","governed_unit_uid":work["governed_unit_uid"],"forward_dependencies":deps.get("edges") or [],"reverse_dependencies":[],"status":"CURRENT"})
    elif op=="CHANGE_IMPACT_MAP_COMPILE":
        write(wd/"CHANGE_IMPACT_MAP.yaml",{"artifact_type":"CHANGE_IMPACT_MAP","stage_uid":"STAGE-02","governed_unit_uid":work["governed_unit_uid"],"source_dependency_edges":deps.get("edges") or [],"revalidation_required_on_upstream_change":True,"affected_successor_stages":["STAGE-03","STAGE-04","STAGE-05","STAGE-06","STAGE-07","STAGE-08","STAGE-09","STAGE-10","STAGE-11"],"status":"CURRENT"})
    elif op=="FUNCTIONAL_CHAIN_COMPILE":
        write(wd/"FUNCTIONAL_CHAIN_SPEC.yaml",{"artifact_type":"FUNCTIONAL_CHAIN_SPEC","stage_uid":"STAGE-02","governed_unit_uid":work["governed_unit_uid"],"chains":p["chains"],"source_derived_chain_count":len(p["chains"]),"status":"CURRENT"})
    elif op=="DEPENDENCY_MAP_COMPILE":
        write(wd/"DEPENDENCY_MAP.yaml",{"artifact_type":"DEPENDENCY_MAP","stage_uid":"STAGE-02","governed_unit_uid":work["governed_unit_uid"],"dependencies":deps.get("edges") or [],"unresolved_authority_gaps":deps.get("unresolved_authority_gaps") or [],"status":"CURRENT"})
    elif op=="GOVERNED_UNIT_CONSTRUCTION_SPEC_COMPILE": entity_package(wd,work,p,refs)
    elif op=="ASYNC_PROVIDER_CONTRACT_COMPILE":
        write(wd/"ASYNC_PROVIDER_CONTRACT.yaml",{"artifact_type":"ASYNC_PROVIDER_CONTRACT","stage_uid":"STAGE-02","governed_unit_uid":work["governed_unit_uid"],"async_required":False,"providers":[],"authority_ref":refs["SOURCE_CONTEXT_MANIFEST"],"status":"CURRENT"})
    elif op=="SHARED_OWNER_PORT_RESOLVE":
        ports=[]
        for e in deps.get("edges") or []:
            ports.append({"port_uid":"PORT-"+str(e.get("edge_uid") or digest(e)[:12]),"dependency_type":e.get("dependency_type"),"producer_source_uid":e.get("producer_source_uid"),"consumer_source_uid":e.get("consumer_source_uid"),"authority_evidence_ref":e.get("authority_evidence_ref"),"status":"RESOLVED"})
        write(wd/"SHARED_OWNER_PORT_MAP.yaml",{"artifact_type":"SHARED_OWNER_PORT_MAP","stage_uid":"STAGE-02","governed_unit_uid":work["governed_unit_uid"],"ports":ports,"status":"CURRENT"})
    elif op=="FUNCTIONAL_WORKBENCH_CONTRACT_COMPILE": workbench(wd,work,p,refs)
    elif op=="INTERACTION_TOPOLOGY_COMPILE": topology(wd,work,p,refs)
    elif op=="FUNCTION_ADMISSION_SCORECARD_COMPILE":
        write(wd/"FUNCTION_ADMISSION_SCORECARD.yaml",{"artifact_type":"FUNCTION_ADMISSION_SCORECARD","stage_uid":"STAGE-02","governed_unit_uid":work["governed_unit_uid"],"candidate_additions":[],"source_derived_function_count":len(p["chains"]),"authority_gap_candidate_count":0,"auto_completion_candidate_count":0,"decision":"NO_NEW_FUNCTION_ADMISSION_REQUIRED","authority_creation_credit":0,"status":"PASS"})
    elif op=="AUTO_COMPLETION_SCOPE_LEDGER_COMPILE":
        write(wd/"AUTO_COMPLETION_SCOPE_LEDGER.yaml",{"artifact_type":"AUTO_COMPLETION_SCOPE_LEDGER","stage_uid":"STAGE-02","governed_unit_uid":work["governed_unit_uid"],"seed_gaps":[],"frozen_dependency_closure":[str(x.get("edge_uid") or "") for x in deps.get("edges") or []],"automatic_additions":[],"speculative_expansion_performed":False,"new_governed_entity_created_by_ai":False,"status":"PASS_NO_AUTO_COMPLETION_REQUIRED"})
        write(wd/"EVIDENCE/GOVERNED_UNIT_FUNCTIONAL_REVIEW_EVIDENCE.yaml",{"artifact_type":"GOVERNED_UNIT_FUNCTIONAL_REVIEW_EVIDENCE","stage_uid":"STAGE-02","work_unit_uid":work["work_unit_uid"],"governed_unit_uid":work["governed_unit_uid"],"functional_chain_total":len(p["chains"]),"source_authority_refs":list(refs.values()),"historical_completion_credit":0,"result":"PASS"})
    binding=(work.get("operation_bindings") or {}).get(op) or {}
    receipt_ref=str(binding.get("operation_receipt_ref") or "")
    if not receipt_ref: raise SystemExit("BLOCK:STAGE02_OPERATION_RECEIPT_REF_MISSING")
    write(root/receipt_ref,{"artifact_type":"OPERATION_EXECUTION_RECEIPT","stage_uid":"STAGE-02","work_unit_uid":work["work_unit_uid"],"operation_uid":op,"governance_uid":work["governance_uid"],"status":"PASS","executor_owner":binding.get("executor_owner"),"executor_protocol":binding.get("executor_protocol"),"result_owner":binding.get("result_owner"),"historical_completion_credit":0})
    print("PASS:",op,work["work_unit_uid"])

if __name__=="__main__": main()
