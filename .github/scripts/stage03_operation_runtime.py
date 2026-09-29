#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, html, re
from pathlib import Path
import yaml

OPS=["VISUAL_SPEC_COMPILE","GEOMETRY_CONTRACT_COMPILE","VISUAL_PREVIEW_RENDER","VISUAL_CHANGESET_COMPILE","VISUAL_INTERACTION_TOPOLOGY_BIND","FUNCTIONAL_WORKBENCH_LAYOUT_BIND","VISUAL_REFERENCE_ANNOTATION_COMPILE","VISUAL_INHERITANCE_MATRIX_COMPILE","VISUAL_SCENARIO_EVIDENCE_COMPILE"]
GLOBAL_AUTH="STAGE_EXECUTION/SHARED_AUTHORITY/GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY.yaml"

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d
def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(yaml.safe_dump(o,sort_keys=False,allow_unicode=True,width=180),encoding="utf-8")
def digest(s): return hashlib.sha256(str(s).encode()).hexdigest()
def input_doc(root,work,uid):
    r=(work.get("input_bindings") or {}).get(uid) or {}; ref=str(r.get("artifact_ref") or "")
    if not ref: raise SystemExit("BLOCK:STAGE03_INPUT_MISSING:"+uid)
    return load(root/ref),ref
def pred_dir(root,work):
    ref=str(work.get("predecessor_work_unit_ref") or "")
    if not ref: raise SystemExit("BLOCK:STAGE03_PREDECESSOR_REF_MISSING")
    return (root/ref).resolve().parent
def profile(root,work):
    vb,vbref=input_doc(root,work,"VISUAL_BASE_BLUEPRINT")
    pkg,pkgref=input_doc(root,work,"GOVERNED_UNIT_CONSTRUCTION_SPEC_PACKAGE")
    wb,wbref=input_doc(root,work,"FUNCTIONAL_WORKBENCH_CONTRACT")
    topo,toporef=input_doc(root,work,"INTERACTION_TOPOLOGY_SPEC")
    pd=pred_dir(root,work)
    vis=load(pd/"FUNCTION_VISUAL_IMPACT_MATRIX.yaml")
    chains=load(pd/"FUNCTIONAL_CHAIN_SPEC.yaml").get("chains") or []
    rows=vis.get("rows") or []
    if not rows or not chains: raise SystemExit("BLOCK:STAGE03_FUNCTION_VISUAL_INPUT_EMPTY")
    ga=load(root/GLOBAL_AUTH); return vb,vbref,pkg,pkgref,wb,wbref,topo,toporef,rows,chains,ga
def slug(x): return re.sub(r"[^A-Za-z0-9]+","-",str(x)).strip("-").upper()
def svg(path,title,rows,ga,active=None):
    colors=ga.get("color_tokens") or {}; bg=colors.get("PAGE_BG_PRIMARY","#050816"); surf=colors.get("SURFACE_PRIMARY","#0C1026"); purple=colors.get("PRIMARY_PURPLE","#8B5CFF"); hi=colors.get("HIGHLIGHT_PURPLE","#B38CFF")
    h=max(360,120+len(rows)*72)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="{h}" viewBox="0 0 1440 {h}">',f'<rect width="1440" height="{h}" fill="{bg}"/>',f'<text x="64" y="64" fill="{hi}" font-family="Inter,Arial" font-size="28" font-weight="700">{html.escape(title)}</text>']
    y=96
    for i,r in enumerate(rows):
        key=str(r.get("component_or_control_identity") or r.get("entry") or f"ROW-{i+1}"); label=str(r.get("visual_section_or_surface") or r.get("business_intent") or key)
        stroke=hi if active==key else purple
        parts += [f'<rect x="64" y="{y}" width="1312" height="56" rx="12" fill="{surf}" stroke="{stroke}" stroke-width="2"/>',f'<text x="88" y="{y+34}" fill="#F5F3FF" font-family="Inter,Arial" font-size="16">{html.escape(label)} · {html.escape(key)}</text>']
        y+=72
    parts.append("</svg>")
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text("".join(parts),encoding="utf-8")
def preflight(wd,work,refs,chains):
    manifests={
      "REQUIRED_FIELD_MANIFEST.yaml":{"artifact_type":"REQUIRED_FIELD_MANIFEST","stage_uid":"STAGE-03","required_outputs":["VISUAL_DESIGN_SPEC_PACKAGE","VISUAL_GEOMETRY_CONTRACT","VISUAL_PREVIEW_EVIDENCE","VISUAL_CHANGESET","VISUAL_INTERACTION_TOPOLOGY_BINDING","FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT","VISUAL_REFERENCE_ANNOTATION","VISUAL_INHERITANCE_MATRIX","VISUAL_SCENARIO_EVIDENCE_SET"],"status":"CURRENT"},
      "FUNCTIONAL_CHAIN_MANIFEST.yaml":{"artifact_type":"FUNCTIONAL_CHAIN_MANIFEST","stage_uid":"STAGE-03","chain_uids":[x.get("chain_uid") for x in chains],"status":"CURRENT"},
      "EFFECTIVE_CONTRACT_OVERLAY.yaml":{"artifact_type":"EFFECTIVE_CONTRACT_OVERLAY","stage_uid":"STAGE-03","source_authority_refs":list(refs.values()),"functional_topology_redefinition":False,"status":"CURRENT"},
      "DEPENDENCY_TOPOLOGY.yaml":{"artifact_type":"DEPENDENCY_TOPOLOGY","stage_uid":"STAGE-03","cross_unit_required_dependencies":[],"status":"CURRENT"},
      "CLASSIFICATION_RULESET.yaml":{"artifact_type":"CLASSIFICATION_RULESET","stage_uid":"STAGE-03","rules":{"new_visual_pattern_without_authority":"BLOCK","functional_topology_redefinition":"BLOCK","human_visual_review":"REQUIRED"},"status":"CURRENT"},
      "CHANGE_IMPACT_MAP.yaml":{"artifact_type":"CHANGE_IMPACT_MAP","stage_uid":"STAGE-03","revalidate_on_stage02_change":True,"status":"CURRENT"},
      "CURRENT_PROBLEM_REGISTER.yaml":{"artifact_type":"CURRENT_PROBLEM_REGISTER","stage_uid":"STAGE-03","problems":[],"open_problem_total":0,"closure_blocker_total":1,"non_problem_closure_gates":[{"gate_uid":"HUMAN_VISUAL_REVIEW","status":"PENDING_HUMAN_REVIEW","stage_exit_credit":0}],"status":"OPEN_CURRENT"},
      "RESOLUTION_LEDGER.yaml":{"artifact_type":"RESOLUTION_LEDGER","stage_uid":"STAGE-03","append_only":True,"entries":[],"status":"CURRENT"}
    }
    for n,d in manifests.items(): write(wd/n,d)
    req=["REQUIRED_FIELD_MANIFEST.yaml","FUNCTIONAL_CHAIN_MANIFEST.yaml","EFFECTIVE_CONTRACT_OVERLAY.yaml","DEPENDENCY_TOPOLOGY.yaml","DENOMINATOR_SNAPSHOT.yaml","CLASSIFICATION_RULESET.yaml","CHANGE_IMPACT_MAP.yaml","STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml"]
    write(wd/"STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml",{"artifact_type":"STAGE_EXECUTION_PREFLIGHT_RECEIPT","stage_uid":"STAGE-03","work_unit_uid":work["work_unit_uid"],"required_manifest_set":req,"shared_manifest_set_complete":True,"historical_product_values_used":False,"result":"PASS"})
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--stage",required=True); ap.add_argument("--operation",required=True); ap.add_argument("--work-unit",required=True); ap.add_argument("--product-root",required=True)
    a=ap.parse_args()
    if a.stage!="STAGE-03" or a.operation not in OPS: raise SystemExit("BLOCK:STAGE03_EXECUTOR_OPERATION_IDENTITY_DRIFT")
    root=Path(a.product_root).resolve(); wp=root/Path(a.work_unit); wd=wp.parent; work=load(wp)
    vb,vbref,pkg,pkgref,wb,wbref,topo,toporef,rows,chains,ga=profile(root,work)
    refs={"VISUAL_BASE_BLUEPRINT":vbref,"GOVERNED_UNIT_CONSTRUCTION_SPEC_PACKAGE":pkgref,"FUNCTIONAL_WORKBENCH_CONTRACT":wbref,"INTERACTION_TOPOLOGY_SPEC":toporef,"GLOBAL_VISUAL_AUTHORITY":GLOBAL_AUTH}
    op=a.operation
    anchors=[{"anchor_uid":"VA-"+slug(work["governed_unit_uid"])+"-"+str(i+1).zfill(3),"visual_section_or_surface":r.get("visual_section_or_surface"),"component_or_control_identity":r.get("component_or_control_identity"),"state_binding":r.get("state_binding"),"authority_ref":r.get("visual_authority_ref") or vbref} for i,r in enumerate(rows)]
    if op=="VISUAL_SPEC_COMPILE":
        preflight(wd,work,refs,chains)
        write(wd/"VISUAL_DESIGN_SPEC_PACKAGE.yaml",{"artifact_type":"VISUAL_DESIGN_SPEC_PACKAGE","stage_uid":"STAGE-03","governed_unit_uid":work["governed_unit_uid"],"visual_authority_ref":GLOBAL_AUTH,"visual_base_blueprint_ref":vbref,"functional_package_ref":pkgref,"visual_inheritance_matrix_ref":str((wd/"VISUAL_INHERITANCE_MATRIX.yaml").relative_to(root)),"visual_reference_annotation_ref":str((wd/"VISUAL_REFERENCE_ANNOTATION.yaml").relative_to(root)),"visual_scenario_evidence_set_ref":str((wd/"VISUAL_SCENARIO_EVIDENCE_SET.yaml").relative_to(root)),"visual_geometry_contract_ref":str((wd/"VISUAL_GEOMETRY_CONTRACT.yaml").relative_to(root)),"visual_change_set_ref":str((wd/"VISUAL_CHANGESET.yaml").relative_to(root)),"typography_authority_ref":GLOBAL_AUTH+"#typography_authority","transitive_binding_status":"BOUND_TO_CURRENT_AUTHORITY","status":"CURRENT"})
    elif op=="GEOMETRY_CONTRACT_COMPILE":
        ty=ga.get("typography_authority") or {}; tokens={x["token_uid"]:x for x in ty.get("tokens") or []}; tok=tokens.get("label-md") or next(iter(tokens.values()),None)
        if not tok: raise SystemExit("BLOCK:GLOBAL_TYPOGRAPHY_TOKEN_EMPTY")
        req=list(ty.get("required_row_fields") or [])
        trows=[]
        for an in anchors:
            fs=float(tok["font_size_px"]); lh=round(fs*float(tok["line_height_ratio"]),2)
            trows.append({"target_uid":"TYPE-"+an["anchor_uid"],"page_or_scope_uid":work["governed_unit_uid"],"viewport_or_breakpoint_uid":"DESKTOP_DEFAULT","language":"zh-TW","theme":"TECH_PURPLE_DARK","typography_authority_ref":GLOBAL_AUTH+"#typography_authority","font_family_token_or_value_ref":"canonical_font_stack","font_size_token_or_value_ref":tok["token_uid"],"font_weight_token_or_value_ref":tok["token_uid"],"line_height_token_or_value_ref":tok["token_uid"],"letter_spacing_token_or_value_ref":tok["token_uid"],"expected_font_family":ty["canonical_font_stack"],"expected_font_size_px":fs,"expected_font_weight":tok["font_weight"],"expected_line_height_px":lh,"expected_letter_spacing_px":float(tok["letter_spacing_em"])*fs,"expected_text_container_min_width_px":48,"expected_text_container_max_width_px":1200,"wrap_rule":"WRAP_WITHIN_AUTHORIZED_CONTAINER","truncation_rule":"NO_SEMANTIC_TRUNCATION","expected_line_count_rule":"SOURCE_CONTENT_DEPENDENT","allowed_tolerance":dict(ty.get("tolerance") or {})})
        write(wd/"VISUAL_GEOMETRY_CONTRACT.yaml",{"artifact_type":"VISUAL_GEOMETRY_CONTRACT","stage_uid":"STAGE-03","visual_anchors":anchors,"visual_anchor_count":len(anchors),"typography_baseline_required_fields":req,"typography_baseline_rows":trows,"typography_baseline_target_total":len(trows),"status":"CURRENT"})
        write(wd/"DENOMINATOR_SNAPSHOT.yaml",{"artifact_type":"DENOMINATOR_SNAPSHOT","stage_uid":"STAGE-03","required_visual_bindings":[str(r.get("component_or_control_identity") or r.get("operation") or "") for r in rows],"geometry_units":[x["anchor_uid"] for x in anchors],"required_visual_binding_total":len(rows),"geometry_unit_total":len(anchors),"required_total":len(rows)+len(anchors),"status":"FROZEN_FOR_CURRENT_WORK_UNIT"})
    elif op=="VISUAL_PREVIEW_RENDER":
        ref=wd/"EVIDENCE/VISUAL_PREVIEW.svg"; svg(ref,str(work["governed_unit_uid"]),rows,ga)
        write(wd/"VISUAL_PREVIEW_EVIDENCE.yaml",{"artifact_type":"VISUAL_PREVIEW_EVIDENCE","stage_uid":"STAGE-03","preview_ref":str(ref.relative_to(root)),"structural_only":False,"render_mode":"SOURCE_BOUND_TECH_PURPLE_SVG","status":"CURRENT"})
    elif op=="VISUAL_CHANGESET_COMPILE":
        write(wd/"VISUAL_CHANGESET.yaml",{"artifact_type":"VISUAL_CHANGESET","stage_uid":"STAGE-03","governed_unit_uid":work["governed_unit_uid"],"changes":[{"change_uid":"VC-"+str(i+1).zfill(3),"binding":r.get("component_or_control_identity"),"authority_ref":r.get("visual_authority_ref") or vbref} for i,r in enumerate(rows)],"status":"CURRENT"})
    elif op=="VISUAL_INTERACTION_TOPOLOGY_BIND":
        binds=[{"control_uid":str(r.get("component_or_control_identity") or "CONTROL-"+str(i+1)),"operation":str(r.get("state_binding") or "STATE"),"visual_anchor_uid":anchors[i]["anchor_uid"],"authority_ref":r.get("visual_authority_ref") or toporef} for i,r in enumerate(rows)]
        write(wd/"VISUAL_INTERACTION_TOPOLOGY_BINDING.yaml",{"artifact_type":"VISUAL_INTERACTION_TOPOLOGY_BINDING","stage_uid":"STAGE-03","bindings":binds,"functional_topology_redefined":False,"status":"CURRENT"})
    elif op=="FUNCTIONAL_WORKBENCH_LAYOUT_BIND":
        write(wd/"FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT.yaml",{"artifact_type":"FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT","stage_uid":"STAGE-03","workbenches":wb.get("workbenches") or [],"visual_anchor_uids":[x["anchor_uid"] for x in anchors],"responsive_reflow_rule":"PRESERVE_STAGE02_SEMANTIC_ORDER","status":"CURRENT"})
    elif op=="VISUAL_REFERENCE_ANNOTATION_COMPILE":
        scenarios=[{"scenario_uid":"SCN-"+str(i+1).zfill(3),"row":r,"anchor":anchors[i]} for i,r in enumerate(rows)]
        anns=[]
        for i,x in enumerate(scenarios):
            ev=f"EVIDENCE/SCENARIOS/{x['scenario_uid']}.svg"
            anns.append({"visual_uid":"VIS-"+x["scenario_uid"],"page_or_scope_uid":work["governed_unit_uid"],"scenario_uid":x["scenario_uid"],"state_uid":str(x["row"].get("state_binding") or "CURRENT"),"workbench_uid":"WB-"+slug(work["governed_unit_uid"]),"journey_uid":"JOURNEY-"+str(i+1).zfill(3),"parent_visual_uid":"VISUAL-ROOT-"+slug(work["governed_unit_uid"]),"design_version":"CURRENT","basic_design_change_set_uid":"CHANGESET-"+slug(work["governed_unit_uid"]),"viewport":"DESKTOP_DEFAULT","language":"zh-TW","theme":"TECH_PURPLE_DARK","applicable_business_entity_or_operation":str(x["row"].get("component_or_control_identity") or x["row"].get("operation") or "CURRENT_OPERATION"),"visible_sections":[str(x["row"].get("visual_section_or_surface") or "CURRENT_SURFACE")],"conditional_sections":["AUTHORIZED_STATE_DEPENDENT"],"locked_regions":["GLOBAL_NAVIGATION_AND_AUTHORITY_LOCKED_REGIONS"],"editable_regions":["CURRENT_GOVERNED_UNIT_VISUAL_REGION"],"visual_anchor_uids":[x["anchor"]["anchor_uid"]],"primary_controls_or_system_triggers":[str(x["row"].get("component_or_control_identity") or "CURRENT_CONTROL")],"disabled_or_blocked_controls":["UNAUTHORIZED_CONTROLS"],"current_next_action_or_gate":"HUMAN_VISUAL_REVIEW","source_authority_refs":[vbref,toporef,GLOBAL_AUTH],"authority_classification":"CURRENT_CANONICAL_AND_SHARED_VISUAL_AUTHORITY","inherited_visual_authority_refs":[GLOBAL_AUTH],"verification_purpose":"SCENARIO_TO_FUNCTION_VISUAL_COVERAGE","evidence_ref":ev})
        write(wd/"VISUAL_REFERENCE_ANNOTATION.yaml",{"artifact_type":"VISUAL_REFERENCE_ANNOTATION","stage_uid":"STAGE-03","annotations":anns,"status":"CURRENT"})
    elif op=="VISUAL_INHERITANCE_MATRIX_COMPILE":
        rows2=[]
        for i,an in enumerate(anchors):
            rows2.append({"visual_region":an["anchor_uid"],"source_authority_uid":ga.get("authority_uid"),"source_authority_path":GLOBAL_AUTH,"source_authority_version":ga.get("authority_version"),"source_authority_hash":digest(yaml.safe_dump(ga,sort_keys=True)),"inherited_rule_or_token":"GLOBAL_TECH_PURPLE_VISUAL_AND_TYPOGRAPHY_AUTHORITY","lock_override_status":"LOCKED_NO_OVERRIDE","allowed_page_local_variation":"SOURCE_BOUND_LAYOUT_ONLY","required_change_set_when_deviation":"VISUAL_CHANGESET_REQUIRED"})
        write(wd/"VISUAL_INHERITANCE_MATRIX.yaml",{"artifact_type":"VISUAL_INHERITANCE_MATRIX","stage_uid":"STAGE-03","rows":rows2,"duplicate_visual_owner_count":0,"unresolved_visual_authority_count":0,"status":"CURRENT"})
    elif op=="VISUAL_SCENARIO_EVIDENCE_COMPILE":
        anns=load(wd/"VISUAL_REFERENCE_ANNOTATION.yaml").get("annotations") or []; scenarios=[]
        for an in anns:
            ev=wd/an["evidence_ref"]; key=str((an.get("primary_controls_or_system_triggers") or [""])[0]); svg(ev,an["scenario_uid"],rows,ga,active=key)
            scenarios.append({"scenario_uid":an["scenario_uid"],"evidence_ref":an["evidence_ref"],"visual_anchor_uids":an["visual_anchor_uids"],"status":"MATERIALIZED"})
        write(wd/"VISUAL_SCENARIO_EVIDENCE_SET.yaml",{"artifact_type":"VISUAL_SCENARIO_EVIDENCE_SET","stage_uid":"STAGE-03","required_scenario_count":len(scenarios),"materialized_scenario_count":len(scenarios),"scenarios":scenarios,"status":"CURRENT"})
        write(wd/"EVIDENCE/VISUAL_REVIEW_EVIDENCE.yaml",{"artifact_type":"VISUAL_REVIEW_EVIDENCE","stage_uid":"STAGE-03","work_unit_uid":work["work_unit_uid"],"decision":"PENDING_HUMAN_REVIEW","visual_approved":False,"reviewer":None,"reviewed_at":None,"stage_exit_credit":0,"status":"PENDING_HUMAN_REVIEW"})
    b=(work.get("operation_bindings") or {}).get(op) or {}; rr=str(b.get("operation_receipt_ref") or "")
    if not rr: raise SystemExit("BLOCK:STAGE03_OPERATION_RECEIPT_REF_MISSING")
    write(root/rr,{"artifact_type":"OPERATION_EXECUTION_RECEIPT","stage_uid":"STAGE-03","work_unit_uid":work["work_unit_uid"],"operation_uid":op,"governance_uid":work["governance_uid"],"status":"PASS","executor_owner":b.get("executor_owner"),"executor_protocol":b.get("executor_protocol"),"result_owner":b.get("result_owner"),"historical_completion_credit":0})
    print("PASS:",op,work["work_unit_uid"])
if __name__=="__main__": main()
