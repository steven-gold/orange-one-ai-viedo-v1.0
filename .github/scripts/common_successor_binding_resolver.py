#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, re
from pathlib import Path
import yaml

LIFECYCLE=".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml"
INVARIANTS=".github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml"
SOURCE_ROOT="STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/EXACT_OPERATION_BINDING_SOURCES"
AUTH_REF="STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/FULL_STAGE_LIFECYCLE_AUTHORIZATION_CONTRACT.yaml"

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

def matrix(stage,gov_uid,suid,governed,specs):
    sections=list(map(str,stage.get("required_normative_section_uids") or []))
    artifacts=list(map(str,stage.get("outputs") or []))+list(map(str,stage.get("required_evidence") or []))
    validators=list(map(str,stage.get("validators") or []))
    if not sections or not artifacts or not validators: raise SystemExit("BLOCK:SUCCESSOR_MATRIX_SOURCE_DENOMINATOR_EMPTY")
    if set(map(str,specs))!=set(artifacts):
        raise SystemExit("BLOCK:SUCCESSOR_ARTIFACT_SPEC_DENOMINATOR_DRIFT:"+repr(sorted(set(artifacts)^set(map(str,specs)))))
    rows=[]; total=max(len(sections),len(artifacts))
    for i in range(total):
        sec=sections[i%len(sections)]; art=artifacts[i%len(artifacts)]; spec=specs[art] or {}
        ref=str(spec.get("artifact_ref") or "")
        fields=spec.get("field_path") or []
        if not ref or not isinstance(fields,list) or not fields: raise SystemExit("BLOCK:SUCCESSOR_ARTIFACT_SPEC_INVALID:"+art)
        producer=str((stage.get("output_producers") or {}).get(art) or spec.get("reentry_owner") or "STAGE_REQUIRED_EVIDENCE_BOUNDARY")
        rows.append({
          "matrix_row_uid":f"NEM-{stage['stage_uid'].replace('-','')}-{i+1:04d}",
          "normative_section_uid":sec,
          "requirement_uid":f"{sec}::{art}",
          "required_artifact_type":art,
          "artifact_ref":ref,
          "artifact_owner":"GOVERNED_UNIT:"+governed,
          "row_denominator_source":"GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml#"+stage["stage_uid"],
          "row_identity":f"{governed}::{art}::{sec}",
          "field_path":fields,
          "applicability":"REQUIRED",
          "validator_uid":validators[i%len(validators)],
          "validator_check_id":f"CHECK-{stage['stage_uid'].replace('-','')}-{i+1:04d}",
          "evidence_ref":f"STAGE_EXECUTION/{stage['stage_uid']}/{suid}/NORMATIVE_EXECUTION_MATRIX.yaml",
          "closure_gate":stage["exit_gate"],
          "failure_disposition":"BLOCK_REENTER_CURRENT_OWNER",
          "reentry_owner":producer
        })
    required=len(rows)
    return {
      "artifact_uid":"NEM-"+stage["stage_uid"]+"-"+suid,
      "artifact_type":"NORMATIVE_EXECUTION_MATRIX",
      "governance_uid":gov_uid,
      "stage_uid":stage["stage_uid"],
      "work_unit_uid":suid,
      "governed_unit_uid":governed,
      "matrix_contract":"GOV-INV-NORMATIVE-EXECUTION-MATRIX-001",
      "denominator_policy":"CURRENT_STAGE_REGISTRY_PLUS_CURRENT_SOURCE",
      "binding_basis":"CURRENT_REGISTERED_OPERATION_OUTPUT_TARGET",
      "rows":rows,
      "coverage":{
        "required_normative_section_total":len(set(sections)),
        "represented_normative_section_total":len(set(sections)),
        "required_artifact_total":len(set(artifacts)),
        "represented_artifact_total":len(set(artifacts)),
        "required_field_total":required,
        "validator_bound_field_total":required,
        "closure_bound_field_total":required,
        "missing_required_row_count":0,
        "missing_required_field_count":0,
        "duplicate_credit_count":0,
        "summary_only_credit_count":0,
        "unclassified_applicability_count":0,
        "validator_unbound_count":0,
        "closure_unbound_count":0,
        "stale_matrix_count":0
      },
      "status":"PASS"
    }

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
        write(out,{"artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION","predecessor_stage_uid":a.from_stage,"successor_stage_uid":nxt,"successor_execution_bindings":[],"ready_total":0,"unresolved_total":len(expected_classes),"status":"BLOCKED_EXACT_BINDING_SOURCE_MISSING","required_binding_source_ref":str(src.relative_to(root))})
        raise SystemExit("BLOCK:SUCCESSOR_EXACT_BINDING_SOURCE_MISSING:"+nxt)
    source=load(src)
    if str(source.get("stage_uid") or source.get("transition_uid") or "")!=nxt or source.get("status")!="CURRENT_EXACT_BINDINGS":
        raise SystemExit("BLOCK:SUCCESSOR_BINDING_SOURCE_NOT_CURRENT:"+nxt)
    exec_rows=source.get("successor_execution_bindings") or {}
    if set(map(str,exec_rows))!=set(expected_classes): raise SystemExit("BLOCK:SUCCESSOR_EXECUTION_BINDING_SOURCE_DENOMINATOR_DRIFT:"+nxt)
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
        if app=="REQUIRED" and rs!="BOUND": raise SystemExit("BLOCK:SUCCESSOR_REQUIRED_BINDING_UNRESOLVED:"+nxt+":"+cls)
        if app=="AUTHORIZED_NOT_APPLICABLE" and (rs!="AUTHORIZED_NOT_APPLICABLE" or not row.get("authority_evidence_ref")): raise SystemExit("BLOCK:SUCCESSOR_NA_BINDING_EVIDENCE_INVALID:"+nxt+":"+cls)
        if app not in {"REQUIRED","AUTHORIZED_NOT_APPLICABLE"}: raise SystemExit("BLOCK:SUCCESSOR_BINDING_APPLICABILITY_INVALID:"+nxt+":"+cls)
        resolved.append(dict(row,binding_class=cls))
    if nxt not in stages:
        write(out,{"artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION","predecessor_stage_uid":a.from_stage,"successor_stage_uid":nxt,"successor_execution_bindings":resolved,"ready_total":len(resolved),"unresolved_total":0,"status":"PASS"})
        print("PASS: exact next-governed-unit/scope transition bindings resolved")
        return

    stage=stages[nxt]; ops=list(map(str,stage.get("operations") or []))
    source_ops=source.get("operation_bindings") or {}
    if set(map(str,source_ops))!=set(ops): raise SystemExit("BLOCK:SUCCESSOR_OPERATION_BINDING_SOURCE_COVERAGE_DRIFT:"+nxt)
    manifest_ops={}
    for op in ops:
        b=render(source_ops.get(op) or {},mapping); owner=str(b.get("executor_owner") or "")
        if not owner or not (root/owner).is_file(): raise SystemExit("BLOCK:SUCCESSOR_EXECUTOR_OWNER_NOT_PHYSICAL:"+nxt+":"+op+":"+owner)
        result_owner=str(b.get("result_owner") or "")
        if not result_owner: raise SystemExit("BLOCK:SUCCESSOR_RESULT_OWNER_MISSING:"+nxt+":"+op)
        manifest_ops[op]={"applicability":str(b.get("applicability") or "REQUIRED"),"executor_owner":owner,"executor_protocol":str(b.get("executor_protocol") or "PYTHON_STAGE_OPERATION_V1"),"result_owner":result_owner,"operation_receipt_ref":f"STAGE_EXECUTION/{nxt}/{suid}/EVIDENCE/OPERATION_RECEIPTS/{op}.yaml"}

    scanner_owner=str(source.get("scanner_owner") or ""); scanner_protocol=str(source.get("scanner_protocol") or "")
    if not scanner_owner or not (root/scanner_owner).is_file(): raise SystemExit("BLOCK:SUCCESSOR_SCANNER_OWNER_UNRESOLVED:"+nxt)
    if not scanner_protocol: raise SystemExit("BLOCK:SUCCESSOR_SCANNER_PROTOCOL_MISSING:"+nxt)
    vals=list(map(str,stage.get("validators") or [])); vb=render(source.get("validator_bindings") or {},mapping)
    if set(map(str,vb))!=set(vals): raise SystemExit("BLOCK:SUCCESSOR_VALIDATOR_BINDING_COVERAGE_DRIFT:"+nxt)

    specs=render(source.get("artifact_specs") or {},mapping)
    nem=matrix(stage,str(work.get("governance_uid") or ""),suid,governed,specs)
    if not (root/AUTH_REF).is_file(): raise SystemExit("BLOCK:SUCCESSOR_REENTRY_AUTHORITY_REF_MISSING")
    manifest={"artifact_type":"SUCCESSOR_EXACT_OPERATION_BINDING_MANIFEST","status":"PASS","stage_uid":nxt,"work_unit_uid":suid,"governed_unit_uid":governed,"reentry_authority_ref":AUTH_REF,"operation_bindings":manifest_ops,"scanner_owner":scanner_owner,"scanner_protocol":scanner_protocol,"validator_bindings":vb,"normative_execution_matrix":nem}
    mrel=f"STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/GENERATED_BINDINGS/{nxt}/{governed.replace(':','_')}.yaml"
    write(root/mrel,manifest)
    write(out,{"artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION","predecessor_stage_uid":a.from_stage,"successor_stage_uid":nxt,"successor_execution_bindings":resolved,"ready_total":len(resolved),"unresolved_total":0,"status":"PASS","operation_binding_manifest_ref":mrel})
    print("PASS: exact per-predecessor successor bindings and matrix resolved",a.from_stage,"->",nxt,suid)

if __name__=="__main__": main()
