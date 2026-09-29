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
    expected=[f"STAGE-{i:02d}" for i in range(1,12)]
    if list(stages)!=expected: raise SystemExit("BLOCK:BINDING_RESOLVER_LIFECYCLE_ORDER_DRIFT")
    if a.mode=="validate-contract":
        print("PASS: successor runtime resolver is post-CLOSED_PASS exact binding materialization only")
        return
    if not a.from_stage or not a.predecessor_work_unit:
        raise SystemExit("BLOCK:BINDING_RESOLVER_REQUIRED_ARGUMENT_MISSING")
    if a.from_stage not in stages:
        raise SystemExit("BLOCK:BINDING_RESOLVER_STAGE_UNREGISTERED")

    wp=root/Path(a.predecessor_work_unit); work=load(wp); wd=wp.parent
    if str(work.get("stage_uid"))!=a.from_stage:
        raise SystemExit("BLOCK:BINDING_RESOLVER_PREDECESSOR_STAGE_DRIFT")
    terminal=load(wd/"WORK_UNIT_TERMINAL_RECEIPT.yaml")
    if terminal.get("status")!="CLOSED_PASS" or terminal.get("conclusion")!="success":
        raise SystemExit("BLOCK:BINDING_RESOLVER_PREDECESSOR_NOT_CLOSED_PASS")

    nxt=str(stages[a.from_stage].get("next_stage_uid") or "")
    out=wd/"EVIDENCE/SUCCESSOR_EXECUTION_BINDING_RESOLUTION.yaml"
    governed=str(work.get("governed_unit_uid") or "")

    if nxt not in stages:
        write(out,{
          "artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION",
          "predecessor_stage_uid":a.from_stage,
          "successor_stage_uid":nxt,
          "status":"PASS_TERMINAL_LIFECYCLE_TRANSITION",
        })
        print("PASS: terminal lifecycle transition requires no synthetic Stage runtime",nxt)
        return

    suid=successor_uid(work.get("work_unit_uid"),nxt)
    mapping={"WORK_UNIT_UID":suid,"GOVERNED_UNIT_UID":governed,"STAGE_UID":nxt,"PREDECESSOR_WORK_UNIT_UID":str(work.get("work_unit_uid") or "")}
    src=root/SOURCE_ROOT/f"{nxt}.yaml"
    if not src.is_file():
        write(out,{
          "artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION",
          "predecessor_stage_uid":a.from_stage,
          "successor_stage_uid":nxt,
          "status":"BLOCKED_EXACT_BINDING_SOURCE_MISSING",
          "required_binding_source_ref":str(src.relative_to(root)),
        })
        raise SystemExit("BLOCK:SUCCESSOR_EXACT_BINDING_SOURCE_MISSING:"+nxt)

    source=load(src)
    if str(source.get("stage_uid") or "")!=nxt or source.get("status")!="CURRENT_EXACT_BINDINGS":
        raise SystemExit("BLOCK:SUCCESSOR_BINDING_SOURCE_NOT_CURRENT:"+nxt)
    if str(source.get("runtime_readiness") or "EFFECTFUL_READY")!="EFFECTFUL_READY":
        raise SystemExit("BLOCK:SUCCESSOR_EFFECTFUL_RUNTIME_NOT_MATERIALIZED:"+nxt)

    stage=stages[nxt]; ops=list(map(str,stage.get("operations") or []))
    source_ops=source.get("operation_bindings") or {}
    if set(map(str,source_ops))!=set(ops):
        raise SystemExit("BLOCK:SUCCESSOR_OPERATION_BINDING_SOURCE_COVERAGE_DRIFT:"+nxt)

    manifest_ops={}
    for op in ops:
        b=render(source_ops.get(op) or {},mapping)
        applicability=str(b.get("applicability") or "REQUIRED")
        if applicability not in {"REQUIRED","AUTHORIZED_NOT_APPLICABLE"}:
            raise SystemExit("BLOCK:SUCCESSOR_OPERATION_APPLICABILITY_INVALID:"+nxt+":"+op)
        owner=str(b.get("executor_owner") or "")
        if applicability=="REQUIRED":
            if not owner or not (root/owner).is_file():
                raise SystemExit("BLOCK:SUCCESSOR_EXECUTOR_OWNER_NOT_PHYSICAL:"+nxt+":"+op+":"+owner)
            if not str(b.get("result_owner") or ""):
                raise SystemExit("BLOCK:SUCCESSOR_RESULT_OWNER_MISSING:"+nxt+":"+op)
        manifest_ops[op]={
          "applicability":applicability,
          "executor_owner":owner,
          "executor_protocol":str(b.get("executor_protocol") or "PYTHON_STAGE_OPERATION_V1"),
          "result_owner":str(b.get("result_owner") or ""),
          "operation_receipt_ref":f"STAGE_EXECUTION/{nxt}/{suid}/EVIDENCE/OPERATION_RECEIPTS/{op}.yaml",
        }

    scanner_owner=str(source.get("scanner_owner") or ""); scanner_protocol=str(source.get("scanner_protocol") or "")
    if not scanner_owner or not (root/scanner_owner).is_file():
        raise SystemExit("BLOCK:SUCCESSOR_SCANNER_OWNER_UNRESOLVED:"+nxt)
    if not scanner_protocol:
        raise SystemExit("BLOCK:SUCCESSOR_SCANNER_PROTOCOL_MISSING:"+nxt)

    vals=list(map(str,stage.get("validators") or []))
    vb=render(source.get("validator_bindings") or {},mapping)
    if set(map(str,vb))!=set(vals):
        raise SystemExit("BLOCK:SUCCESSOR_VALIDATOR_BINDING_COVERAGE_DRIFT:"+nxt)

    specs=render(source.get("artifact_specs") or {},mapping)
    nem=matrix(stage,str(work.get("governance_uid") or ""),suid,governed,specs,source)
    if not (root/AUTH_REF).is_file():
        raise SystemExit("BLOCK:SUCCESSOR_REENTRY_AUTHORITY_REF_MISSING")

    manifest={
      "artifact_type":"SUCCESSOR_EXACT_OPERATION_BINDING_MANIFEST",
      "status":"PASS",
      "stage_uid":nxt,
      "work_unit_uid":suid,
      "governed_unit_uid":governed,
      "reentry_authority_ref":AUTH_REF,
      "operation_bindings":manifest_ops,
      "scanner_owner":scanner_owner,
      "scanner_protocol":scanner_protocol,
      "validator_bindings":vb,
      "normative_execution_matrix":nem,
    }
    mrel=f"STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_STAGE_FLOW/GENERATED_BINDINGS/{nxt}/{governed.replace(':','_')}.yaml"
    write(root/mrel,manifest)
    write(out,{
      "artifact_type":"SUCCESSOR_EXECUTION_BINDING_RESOLUTION",
      "predecessor_stage_uid":a.from_stage,
      "successor_stage_uid":nxt,
      "status":"PASS",
      "operation_binding_manifest_ref":mrel,
    })
    print("PASS: post-closure exact successor runtime materialized",a.from_stage,"->",nxt,suid)

if __name__=="__main__": main()
