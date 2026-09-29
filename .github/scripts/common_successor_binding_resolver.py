#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, re, subprocess
from pathlib import Path
import yaml

LIFECYCLE=".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml"
INVARIANTS=".github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml"
SOURCE_ROOT="STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/EXACT_OPERATION_BINDING_SOURCES"
AUTH_REF="STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/FULL_STAGE_LIFECYCLE_AUTHORIZATION_CONTRACT.yaml"
PRODUCT_AUTH="STAGE_EXECUTION/SHARED_AUTHORITY/PRODUCT_IMPLEMENTATION_AUTHORITY.yaml"

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d

def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(o,sort_keys=False,allow_unicode=True),encoding="utf-8")

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(root,*args):
    cp=subprocess.run(["git","-C",str(root),*args],text=True,capture_output=True)
    if cp.returncode!=0: raise SystemExit("BLOCK:GIT:"+cp.stderr.strip())
    return cp.stdout.strip()
def tracked(root,rel):
    rel=str(rel or "").strip()
    if rel in {"",".","./"}:
        return bool(git(root,"ls-files").strip())
    p=root/rel
    if not p.exists(): return False
    cp=subprocess.run(["git","-C",str(root),"ls-files","--",rel],text=True,capture_output=True)
    return cp.returncode==0 and bool(cp.stdout.strip())

def successor_uid(predecessor_uid, successor_stage):
    m=re.fullmatch(r"WU-STAGE\d{2}-(.+)",str(predecessor_uid or ""))
    if not m: raise SystemExit("BLOCK:PREDECESSOR_WORK_UNIT_UID_PATTERN_INVALID")
    return "WU-"+successor_stage.replace("-","")+"-"+m.group(1)

def render(obj,mapping):
    if isinstance(obj,str):
        for k,v in mapping.items(): obj=obj.replace("{{"+k+"}}",str(v))
        return obj
    if isinstance(obj,list): return [render(x,mapping) for x in obj]
    if isinstance(obj,dict): return {str(k):render(v,mapping) for k,v in obj.items()}
    return obj

def matrix(stage,gov_uid,suid,governed,specs,source=None):
    sections=list(map(str,stage.get("required_normative_section_uids") or []))
    artifacts=list(map(str,stage.get("outputs") or []))+list(map(str,stage.get("required_evidence") or []))
    validators=list(map(str,stage.get("validators") or []))
    if not sections or not artifacts or not validators: raise SystemExit("BLOCK:SUCCESSOR_MATRIX_SOURCE_DENOMINATOR_EMPTY")
    checkpoint_type="BASIC_DESIGN_DOMAIN_STEPWISE_CHECKPOINT"
    special_stage04=(stage.get("stage_uid")=="STAGE-04")
    normal_artifacts=[x for x in artifacts if not (special_stage04 and x==checkpoint_type)]
    expected_specs=set(normal_artifacts)
    if set(map(str,specs))!=expected_specs:
        raise SystemExit("BLOCK:SUCCESSOR_ARTIFACT_SPEC_DENOMINATOR_DRIFT:"+repr(sorted(expected_specs^set(map(str,specs)))))
    rows=[]; total=max(len(sections),len(normal_artifacts))
    for i in range(total):
        sec=sections[i%len(sections)]; art=normal_artifacts[i%len(normal_artifacts)]; spec=specs[art] or {}
        ref=str(spec.get("artifact_ref") or ""); fields=spec.get("field_path") or []
        if not ref or not isinstance(fields,list) or not fields: raise SystemExit("BLOCK:SUCCESSOR_ARTIFACT_SPEC_INVALID:"+art)
        producer=str((stage.get("output_producers") or {}).get(art) or spec.get("reentry_owner") or "STAGE_REQUIRED_EVIDENCE_BOUNDARY")
        rows.append({"matrix_row_uid":f"NEM-{stage['stage_uid'].replace('-','')}-{i+1:04d}","normative_section_uid":sec,"requirement_uid":f"{sec}::{art}","required_artifact_type":art,"artifact_ref":ref,"artifact_owner":"GOVERNED_UNIT:"+governed,"row_denominator_source":"GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml#"+stage["stage_uid"],"row_identity":f"{governed}::{art}::{sec}","field_path":fields,"applicability":"REQUIRED","validator_uid":validators[i%len(validators)],"validator_check_id":f"CHECK-{stage['stage_uid'].replace('-','')}-{i+1:04d}","evidence_ref":f"STAGE_EXECUTION/{stage['stage_uid']}/{suid}/NORMATIVE_EXECUTION_MATRIX.yaml","closure_gate":stage["exit_gate"],"failure_disposition":"BLOCK_REENTER_CURRENT_OWNER","reentry_owner":producer})
    if special_stage04:
        domains=(source or {}).get("basic_design_domains") or []
        if not isinstance(domains,list) or not domains: raise SystemExit("BLOCK:STAGE04_BASIC_DESIGN_DOMAIN_SOURCE_EMPTY")
        ids=[]; package_ref=str(specs["BASIC_DESIGN_PACKAGE"]["artifact_ref"])
        for d in domains:
            uid=str((d or {}).get("domain_uid") or "")
            if not uid or uid in ids: raise SystemExit("BLOCK:STAGE04_BASIC_DESIGN_DOMAIN_IDENTITY_INVALID:"+uid)
            ids.append(uid)
            idx=len(rows)+1
            rows.append({"matrix_row_uid":f"NEM-STAGE04-DOMAIN-{idx:04d}","normative_section_uid":"WEB-GOV-01-S083A","requirement_uid":"WEB-GOV-01-S083A::"+uid,"required_artifact_type":checkpoint_type,"artifact_ref":f"STAGE_EXECUTION/STAGE-04/{suid}/EVIDENCE/BASIC_DESIGN_DOMAIN_STEPWISE_CHECKPOINTS/{uid}.yaml","artifact_owner":"GOVERNED_UNIT:"+governed,"row_denominator_source":package_ref+"#design_domains","row_identity":uid,"field_path":["checkpoint_state"],"applicability":"REQUIRED","validator_uid":validators[(idx-1)%len(validators)],"validator_check_id":f"CHECK-STAGE04-DOMAIN-{idx:04d}","evidence_ref":f"STAGE_EXECUTION/STAGE-04/{suid}/NORMATIVE_EXECUTION_MATRIX.yaml","closure_gate":stage["exit_gate"],"failure_disposition":"BLOCK_REENTER_CURRENT_OWNER","reentry_owner":"BASIC_DESIGN_PACKAGE_COMPILE"})
    represented_sections={str(x.get("normative_section_uid") or "") for x in rows}
    missing=set(sections)-represented_sections
    if missing: raise SystemExit("BLOCK:SUCCESSOR_MATRIX_SECTION_COVERAGE_MISSING:"+repr(sorted(missing)))
    represented_artifacts={str(x.get("required_artifact_type") or "") for x in rows}
    if set(artifacts)!=represented_artifacts: raise SystemExit("BLOCK:SUCCESSOR_MATRIX_ARTIFACT_COVERAGE_DRIFT")
    required=len(rows)
    return {"artifact_uid":"NEM-"+stage["stage_uid"]+"-"+suid,"artifact_type":"NORMATIVE_EXECUTION_MATRIX","governance_uid":gov_uid,"stage_uid":stage["stage_uid"],"work_unit_uid":suid,"governed_unit_uid":governed,"matrix_contract":"GOV-INV-NORMATIVE-EXECUTION-MATRIX-001","denominator_policy":"CURRENT_STAGE_REGISTRY_PLUS_CURRENT_SOURCE","binding_basis":"CURRENT_REGISTERED_OPERATION_OUTPUT_TARGET","rows":rows,"coverage":{"required_normative_section_total":len(set(sections)),"represented_normative_section_total":len(set(sections)&represented_sections),"required_artifact_total":len(set(artifacts)),"represented_artifact_total":len(set(artifacts)&represented_artifacts),"required_field_total":required,"validator_bound_field_total":required,"closure_bound_field_total":required,"missing_required_row_count":0,"missing_required_field_count":0,"duplicate_credit_count":0,"summary_only_credit_count":0,"unclassified_applicability_count":0,"validator_unbound_count":0,"closure_unbound_count":0,"stale_matrix_count":0},"status":"PASS"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=["validate-contract","resolve"],default="validate-contract")
    ap.add_argument("--from-stage"); ap.add_argument("--predecessor-work-unit")
    ap.add_argument("--product-root",required=True); ap.add_argument("--governance-root",required=True)
    a=ap.parse_args(); root=Path(a.product_root).resolve(); gov=Path(a.governance_root).resolve()
    life=load(gov/LIFECYCLE); stages={str(x.get("stage_uid")):x for x in life.get("stages") or []}
    inv=load(gov/INVARIANTS); policy=((inv.get("invariants") or {}).get("CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS") or {})
    expected=[f"STAGE-{i:02d}" for i in range(1,12)]
    if list(stages)!=expected: raise SystemExit("BLOCK:BINDING_RESOLVER_LIFECYCLE_ORDER_DRIFT")
    if a.mode=="validate-contract":
        reqs=policy.get("successor_execution_binding_requirements") or {}
        if set(map(str,reqs))!=set(expected[1:]): raise SystemExit("BLOCK:SUCCESSOR_EXECUTION_BINDING_REQUIREMENT_COVERAGE_DRIFT")
        if not policy.get("next_governed_unit_successor_binding_requirements"): raise SystemExit("BLOCK:NEXT_GOVERNED_UNIT_BINDING_REQUIREMENTS_EMPTY")
        print("PASS: successor binding resolver uses dynamic per-predecessor identity and registry-derived matrix")
        return
    if not a.from_stage or not a.predecessor_work_unit: raise SystemExit("BLOCK:BINDING_RESOLVER_REQUIRED_ARGUMENT_MISSING")
    if a.from_stage not in stages: raise SystemExit("BLOCK:BINDING_RESOLVER_STAGE_UNREGISTERED")
    wp=root/Path(a.predecessor_work_unit); work=load(wp); wd=wp.parent
    if str(work.get("stage_uid"))!=a.from_stage: raise SystemExit("BLOCK:BINDING_RESOLVER_PREDECESSOR_STAGE_DRIFT")
    nxt=str(stages[a.from_stage].get("next_stage_uid") or "")
    out=wd/"EVIDENCE/SUCCESSOR_EXECUTION_BINDING_RESOLUTION.yaml"
    governed=str(work.get("governed_unit_uid") or "")
    suid=successor_uid(work.get("work_unit_uid"),nxt) if nxt in stages else ""
    mapping={"WORK_UNIT_UID":suid,"GOVERNED_UNIT_UID":governed,"STAGE_UID":nxt,"PREDECESSOR_WORK_UNIT_UID":str(work.get("work_unit_uid") or "")}
    reqs=policy.get("successor_execution_binding_requirements") or {}
    expected_classes=list(map(str,reqs.get(nxt) or [])) if nxt in stages else list(map(str,policy.get("next_governed_unit_successor_binding_requirements") or []))
    src=root/SOURCE_ROOT/(f"{nxt}.yaml" if nxt in stages else "NEXT_GOVERNED_UNIT_STAGE05_OR_SCOPE_COMPLETE.yaml")
    if not src.is_file():
        write(out,{
          "artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION",
          "predecessor_stage_uid":a.from_stage,
          "successor_stage_uid":nxt,
          "successor_execution_bindings":[],
          "required_binding_classes":expected_classes,
          "ready_total":0,
          "unresolved_total":len(expected_classes),
          "unresolved_binding_classes":expected_classes,
          "status":"BLOCKED_EXACT_BINDING_SOURCE_MISSING",
          "required_binding_source_ref":str(src.relative_to(root)),
          "failure_class":"SUCCESSOR_EXECUTION_BINDING_MISSING",
        })
        raise SystemExit("BLOCK:SUCCESSOR_EXACT_BINDING_SOURCE_MISSING:"+nxt+":"+(",".join(expected_classes) if expected_classes else "NO_CLASS_DENOMINATOR"))
    source=load(src)
    if str(source.get("stage_uid") or source.get("transition_uid") or "")!=nxt or source.get("status")!="CURRENT_EXACT_BINDINGS":
        raise SystemExit("BLOCK:SUCCESSOR_BINDING_SOURCE_NOT_CURRENT:"+nxt)
    exec_rows=source.get("successor_execution_bindings") or {}
    if set(map(str,exec_rows))!=set(expected_classes):
        missing=sorted(set(expected_classes)-set(map(str,exec_rows)))
        extra=sorted(set(map(str,exec_rows))-set(expected_classes))
        write(out,{
          "artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION",
          "predecessor_stage_uid":a.from_stage,
          "successor_stage_uid":nxt,
          "required_binding_classes":expected_classes,
          "ready_total":0,
          "unresolved_total":len(missing),
          "unresolved_binding_classes":missing,
          "unexpected_binding_classes":extra,
          "status":"BLOCKED_BINDING_DENOMINATOR_DRIFT",
          "failure_class":"SUCCESSOR_EXECUTION_BINDING_MISSING",
          "required_binding_source_ref":str(src.relative_to(root)),
        })
        raise SystemExit("BLOCK:SUCCESSOR_EXECUTION_BINDING_SOURCE_DENOMINATOR_DRIFT:"+nxt)
    resolved=[]
    for cls in expected_classes:
        row=render(exec_rows.get(cls) or {},mapping); app=str(row.get("applicability") or ""); rs=str(row.get("resolution_status") or "")
        if rs=="RESOLVE_FROM_PREDECESSOR_ARTIFACT_INDEX":
            idxref=str(work.get("predecessor_artifact_index_ref") or "")
            if not idxref: raise SystemExit("BLOCK:PREDECESSOR_ARTIFACT_INDEX_REF_MISSING:"+nxt+":"+cls)
            idxdoc=load(root/idxref); auid=str(row.get("required_artifact_uid") or "")
            matches=[x for x in (idxdoc.get("artifacts") or []) if isinstance(x,dict) and str(x.get("artifact_uid") or "")==auid]
            if len(matches)!=1: raise SystemExit("BLOCK:SUCCESSOR_AUTHORITY_ARTIFACT_RESOLUTION_NOT_EXACT:"+nxt+":"+cls+":"+str(len(matches)))
            ref=str(matches[0].get("artifact_ref") or "")
            if not ref or not (root/ref).is_file(): raise SystemExit("BLOCK:SUCCESSOR_AUTHORITY_ARTIFACT_NOT_PHYSICAL:"+nxt+":"+cls)
            row.update({"applicability":"REQUIRED","resolution_status":"BOUND","target_ref":ref,"authority_evidence_ref":ref})
            receipt_stages=set(map(str,policy.get("successor_execution_target_resolution_required_stage_uids") or []))
            if nxt in receipt_stages:
                if not tracked(root,ref): raise SystemExit("BLOCK:SUCCESSOR_AUTHORITY_ARTIFACT_NOT_CURRENT_TRACKED:"+nxt+":"+cls+":"+ref)
                auth=load(root/PRODUCT_AUTH)
                head=git(root,"rev-parse","HEAD"); tree=git(root,"rev-parse","HEAD^{tree}")
                receipt_rel=f"STAGE_EXECUTION/{a.from_stage}/{wd.name}/EVIDENCE/SUCCESSOR_TARGET_RESOLUTION/{nxt}/{cls}.yaml"
                receipt={
                  "artifact_type":"EXECUTION_TARGET_RESOLUTION_RECEIPT","binding_uid":f"{nxt}::{cls}",
                  "consuming_operation_uid":str(row.get("consuming_operation_uid") or cls),"binding_class":cls,
                  "target_identity":ref,"canonical_owner_or_authority_ref":ref,"authority_evidence_ref":ref,
                  "work_unit_uid":str(work.get("work_unit_uid") or ""),"successor_stage_uid":nxt,
                  "resolution_kind":"CURRENT_REPOSITORY_PATH","resolution_status":"RESOLVED_CURRENT",
                  "current_execution_repository":str(auth.get("product_repository") or ""),
                  "current_execution_branch":str(auth.get("current_execution_branch") or ""),
                  "current_execution_head_sha":head,"current_execution_tree_sha":tree,"current_context_match":True,
                  "target_path":ref,"target_path_exists":True,"target_path_tracked_at_head":True,"status":"PASS"
                }
                write(root/receipt_rel,receipt)
                row.update({"target_identity":ref,"target_resolution_ref":receipt_rel,"target_resolution_kind":"CURRENT_REPOSITORY_PATH"})
            app="REQUIRED"; rs="BOUND"
        elif rs=="RESOLVE_FROM_PREDECESSOR_LOCAL_REF":
            local=str(row.get("local_ref") or "")
            p=(wd/local).resolve()
            try: p.relative_to(root)
            except ValueError: raise SystemExit("BLOCK:SUCCESSOR_LOCAL_AUTHORITY_REF_ESCAPES_ROOT:"+nxt+":"+cls)
            if not p.is_file(): raise SystemExit("BLOCK:FORMAL_HUMAN_APPROVAL_REQUIRED:"+str(p.relative_to(root)))
            d=load(p)
            if str(d.get("human_action_selected") or d.get("decision") or "") not in {"APPROVE","VISUAL_APPROVED"}:
                raise SystemExit("BLOCK:FORMAL_HUMAN_APPROVAL_NOT_APPROVED:"+nxt+":"+cls)
            ref=str(p.relative_to(root))
            row.update({"applicability":"REQUIRED","resolution_status":"BOUND","target_ref":ref,"authority_evidence_ref":ref})
            app="REQUIRED"; rs="BOUND"
        elif rs=="RESOLVE_FROM_PRODUCT_IMPLEMENTATION_AUTHORITY":
            auth_path=root/PRODUCT_AUTH
            auth=load(auth_path)
            if auth.get("status") not in {"CURRENT_PRODUCT_EXECUTION_AUTHORITY","CURRENT_STAGE05_AUTHORITY"}:
                raise SystemExit("BLOCK:PRODUCT_IMPLEMENTATION_AUTHORITY_NOT_CURRENT")
            source=(auth.get("toolchain_authority") or {}).get(cls)
            if source is None: source=(auth.get("execution_target_authority") or {}).get(cls)
            if source is None: source=(auth.get("verification_target_authority") or {}).get(cls)
            if source is None: source=(auth.get("build_target_authority") or {}).get(cls)
            if not isinstance(source,dict):
                raise SystemExit("BLOCK:PRODUCT_IMPLEMENTATION_AUTHORITY_CLASS_MISSING:"+cls)
            status=str(source.get("status") or "")
            authority_ref=PRODUCT_AUTH+"#"+cls
            if status=="AUTHORIZED_NOT_APPLICABLE":
                row.update({"applicability":"AUTHORIZED_NOT_APPLICABLE","resolution_status":"AUTHORIZED_NOT_APPLICABLE","authority_evidence_ref":authority_ref,"target_identity":str(source.get("authority_value") or "NOT_APPLICABLE")})
                app="AUTHORIZED_NOT_APPLICABLE"; rs="AUTHORIZED_NOT_APPLICABLE"
            elif status in {"RESOLVED","RESOLVED_BY_AUTHORIZED_TEMPLATE"}:
                kind=str(source.get("resolution_kind") or "")
                if kind not in {"CURRENT_REPOSITORY","CURRENT_REPOSITORY_PATH","AUTHORITY_VALUE"}:
                    raise SystemExit("BLOCK:PRODUCT_IMPLEMENTATION_AUTHORITY_RESOLUTION_KIND_INVALID:"+cls+":"+kind)
                if kind=="CURRENT_REPOSITORY":
                    identity=str(source.get("target_identity") or "")
                    if identity!=str(auth.get("product_repository") or ""):
                        raise SystemExit("BLOCK:PRODUCT_REPOSITORY_TARGET_DRIFT:"+cls)
                elif kind=="CURRENT_REPOSITORY_PATH":
                    identity=str(source.get("target_path") or "")
                    p=(root/identity).resolve()
                    try: p.relative_to(root)
                    except ValueError: raise SystemExit("BLOCK:PRODUCT_RUNTIME_TARGET_ESCAPES_ROOT:"+cls)
                    if not p.exists() or not tracked(root,identity):
                        raise SystemExit("BLOCK:PRODUCT_RUNTIME_TARGET_NOT_CURRENT_TRACKED:"+cls+":"+identity)
                else:
                    identity=str(source.get("authority_value") or "")
                    if not identity and source.get("authority_value_template"):
                        identity=render(str(source.get("authority_value_template")),mapping)
                    if not identity: raise SystemExit("BLOCK:PRODUCT_AUTHORITY_VALUE_EMPTY:"+cls)
                head=git(root,"rev-parse","HEAD"); tree=git(root,"rev-parse","HEAD^{tree}")
                receipt_rel=f"STAGE_EXECUTION/{a.from_stage}/{wd.name}/EVIDENCE/SUCCESSOR_TARGET_RESOLUTION/{nxt}/{cls}.yaml"
                receipt={
                  "artifact_type":"EXECUTION_TARGET_RESOLUTION_RECEIPT","binding_uid":f"{nxt}::{cls}","consuming_operation_uid":str(row.get("consuming_operation_uid") or cls),
                  "binding_class":cls,"target_identity":identity,"canonical_owner_or_authority_ref":authority_ref,"authority_evidence_ref":authority_ref,
                  "work_unit_uid":str(work.get("work_unit_uid") or ""),"successor_stage_uid":nxt,"resolution_kind":kind,"resolution_status":"RESOLVED_CURRENT",
                  "current_execution_repository":str(auth.get("product_repository") or ""),"current_execution_branch":str(auth.get("current_execution_branch") or ""),
                  "current_execution_head_sha":head,"current_execution_tree_sha":tree,"current_context_match":True,"status":"PASS"
                }
                if kind=="CURRENT_REPOSITORY":
                    receipt.update({"repository_identity":identity,"branch_ref_head_sha":head})
                elif kind=="CURRENT_REPOSITORY_PATH":
                    receipt.update({"target_path":identity,"target_path_exists":True,"target_path_tracked_at_head":True})
                else:
                    receipt.update({"authority_value":identity,"authority_current_identity_match":True})
                write(root/receipt_rel,receipt)
                row.update({"applicability":"REQUIRED","resolution_status":"BOUND","target_identity":identity,"authority_evidence_ref":authority_ref,"target_resolution_ref":receipt_rel,"target_resolution_kind":kind})
                app="REQUIRED"; rs="BOUND"
            else:
                raise SystemExit("BLOCK:PRODUCT_IMPLEMENTATION_AUTHORITY_CLASS_UNRESOLVED:"+cls+":"+status)
        if app=="REQUIRED" and rs!="BOUND": raise SystemExit("BLOCK:SUCCESSOR_REQUIRED_BINDING_UNRESOLVED:"+nxt+":"+cls)
        if app=="AUTHORIZED_NOT_APPLICABLE" and (rs!="AUTHORIZED_NOT_APPLICABLE" or not row.get("authority_evidence_ref")): raise SystemExit("BLOCK:SUCCESSOR_NA_BINDING_EVIDENCE_INVALID:"+nxt+":"+cls)
        if app not in {"REQUIRED","AUTHORIZED_NOT_APPLICABLE"}: raise SystemExit("BLOCK:SUCCESSOR_BINDING_APPLICABILITY_INVALID:"+nxt+":"+cls)
        resolved.append(dict(row,binding_class=cls))
    if nxt not in stages:
        write(out,{"artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION","predecessor_stage_uid":a.from_stage,"successor_stage_uid":nxt,"successor_execution_bindings":resolved,"ready_total":len(resolved),"unresolved_total":0,"status":"PASS"})
        print("PASS: exact next-governed-unit/scope transition bindings resolved")
        return

    if str(source.get("runtime_readiness") or "EFFECTFUL_READY")!="EFFECTFUL_READY":
        write(out,{"artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION","predecessor_stage_uid":a.from_stage,"successor_stage_uid":nxt,"successor_execution_bindings":resolved,"ready_total":len(resolved),"unresolved_total":0,"status":"BLOCKED_SUCCESSOR_EFFECTFUL_RUNTIME_NOT_MATERIALIZED","target_resolution_pass":True})
        raise SystemExit("BLOCK:SUCCESSOR_EFFECTFUL_RUNTIME_NOT_AUTHORIZED_OR_MATERIALIZED:"+nxt)
    stage=stages[nxt]; ops=list(map(str,stage.get("operations") or []))
    source_ops=source.get("operation_bindings") or {}
    if set(map(str,source_ops))!=set(ops): raise SystemExit("BLOCK:SUCCESSOR_OPERATION_BINDING_SOURCE_COVERAGE_DRIFT:"+nxt)
    manifest_ops={}
    for op in ops:
        b=render(source_ops.get(op) or {},mapping); app=str(b.get("applicability") or "REQUIRED")
        result_owner=str(b.get("result_owner") or "")
        if not result_owner: raise SystemExit("BLOCK:SUCCESSOR_RESULT_OWNER_MISSING:"+nxt+":"+op)
        receipt_ref=f"STAGE_EXECUTION/{nxt}/{suid}/EVIDENCE/OPERATION_RECEIPTS/{op}.yaml"
        if app=="AUTHORIZED_NOT_APPLICABLE":
            authority_ref=str(b.get("authority_evidence_ref") or "")
            if not authority_ref: raise SystemExit("BLOCK:SUCCESSOR_OPERATION_NA_AUTHORITY_MISSING:"+nxt+":"+op)
            manifest_ops[op]={"applicability":app,"result_owner":result_owner,"authority_evidence_ref":authority_ref,"operation_receipt_ref":receipt_ref}
            continue
        if app!="REQUIRED": raise SystemExit("BLOCK:SUCCESSOR_OPERATION_APPLICABILITY_INVALID:"+nxt+":"+op+":"+app)
        owner=str(b.get("executor_owner") or "")
        if not owner or not (root/owner).is_file(): raise SystemExit("BLOCK:SUCCESSOR_EXECUTOR_OWNER_NOT_PHYSICAL:"+nxt+":"+op+":"+owner)
        manifest_ops[op]={"applicability":"REQUIRED","executor_owner":owner,"executor_protocol":str(b.get("executor_protocol") or "PYTHON_STAGE_OPERATION_V1"),"result_owner":result_owner,"operation_receipt_ref":receipt_ref}

    scanner_owner=str(source.get("scanner_owner") or ""); scanner_protocol=str(source.get("scanner_protocol") or "")
    if not scanner_owner or not (root/scanner_owner).is_file(): raise SystemExit("BLOCK:SUCCESSOR_SCANNER_OWNER_UNRESOLVED:"+nxt)
    if not scanner_protocol: raise SystemExit("BLOCK:SUCCESSOR_SCANNER_PROTOCOL_MISSING:"+nxt)
    vals=list(map(str,stage.get("validators") or [])); vb=render(source.get("validator_bindings") or {},mapping)
    if set(map(str,vb))!=set(vals): raise SystemExit("BLOCK:SUCCESSOR_VALIDATOR_BINDING_COVERAGE_DRIFT:"+nxt)

    specs=render(source.get("artifact_specs") or {},mapping)
    nem=matrix(stage,str(work.get("governance_uid") or ""),suid,governed,specs,source)
    if not (root/AUTH_REF).is_file(): raise SystemExit("BLOCK:SUCCESSOR_REENTRY_AUTHORITY_REF_MISSING")
    manifest={"artifact_type":"SUCCESSOR_EXACT_OPERATION_BINDING_MANIFEST","status":"PASS","stage_uid":nxt,"work_unit_uid":suid,"governed_unit_uid":governed,"reentry_authority_ref":AUTH_REF,"operation_bindings":manifest_ops,"scanner_owner":scanner_owner,"scanner_protocol":scanner_protocol,"validator_bindings":vb,"normative_execution_matrix":nem}
    mrel=f"STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/GENERATED_BINDINGS/{nxt}/{governed.replace(':','_')}.yaml"
    write(root/mrel,manifest)
    write(out,{"artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION","predecessor_stage_uid":a.from_stage,"successor_stage_uid":nxt,"successor_execution_bindings":resolved,"ready_total":len(resolved),"unresolved_total":0,"status":"PASS","operation_binding_manifest_ref":mrel})
    print("PASS: exact per-predecessor successor bindings and matrix resolved",a.from_stage,"->",nxt,suid)

if __name__=="__main__": main()
