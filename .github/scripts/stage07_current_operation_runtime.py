#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, os, subprocess
from pathlib import Path
import yaml

STAGE="STAGE-07"
OPS=["OP-36-PRODUCTION_BUILD","RELEASE_CANDIDATE_COMPILE","MIGRATION_COMPATIBILITY_VERIFY","SECURITY_FRESHNESS_VERIFY","STAGING_APPLICABILITY_DECIDE"]
AUTH="STAGE_EXECUTION/SHARED_AUTHORITY/PRODUCT_IMPLEMENTATION_AUTHORITY.yaml"

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d

def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(yaml.safe_dump(o,sort_keys=False,allow_unicode=True,width=180),encoding="utf-8")

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def git(root,*args):
    cp=subprocess.run(["git","-C",str(root),*args],text=True,capture_output=True)
    if cp.returncode!=0: raise SystemExit("BLOCK:GIT:"+cp.stderr.strip())
    return cp.stdout.strip()

def run(root,cmd,env=None,timeout=1800):
    cp=subprocess.run(cmd,cwd=root,text=True,capture_output=True,env=env,timeout=timeout)
    if cp.returncode!=0:
        msg=((cp.stdout or "")+"\n"+(cp.stderr or "")).strip()[-4000:]
        raise SystemExit("BLOCK:STAGE07_COMMAND_FAILED:"+str(cmd)+":"+msg.replace("\n"," | "))
    return ((cp.stdout or "")+"\n"+(cp.stderr or "")).strip()

def authority(root):
    d=load(root/AUTH); r=d.get("stage07_readiness") or {}
    if d.get("status")!="CURRENT_PRODUCT_EXECUTION_AUTHORITY" or int(r.get("resolved_binding_class_total") or 0)!=5 or int(r.get("unresolved_binding_class_total") or -1)!=0:
        raise SystemExit("BLOCK:STAGE07_BUILD_AUTHORITY_NOT_READY")
    return d

def input_ref(work,uid):
    row=(work.get("input_bindings") or {}).get(uid) or {}
    ref=str(row.get("artifact_ref") or row.get("resolved_artifact_ref") or "")
    if not ref: raise SystemExit("BLOCK:STAGE07_INPUT_REF_MISSING:"+uid)
    return ref

def preflight(root,wd,work):
    write(wd/"REQUIRED_FIELD_MANIFEST.yaml",{"artifact_type":"REQUIRED_FIELD_MANIFEST","stage_uid":STAGE,"required_inputs":["VERIFIED_SOURCE_REVISION","WORK_UNIT_CLOSURE_RECORD"],
      "required_operations":OPS,"required_outputs":["BUILD_IDENTITY_MANIFEST","RELEASE_CANDIDATE","STAGING_APPLICABILITY_DECISION"],"required_evidence":["BUILD_TEST_EVIDENCE"],"status":"CURRENT"})
    write(wd/"FUNCTIONAL_CHAIN_MANIFEST.yaml",{"artifact_type":"FUNCTIONAL_CHAIN_MANIFEST","stage_uid":STAGE,
      "build_chain":["VERIFIED_SOURCE","PRODUCTION_BUILD","RELEASE_CANDIDATE","MIGRATION_COMPATIBILITY","SECURITY_FRESHNESS","STAGING_APPLICABILITY"],"status":"CURRENT"})
    write(wd/"EFFECTIVE_CONTRACT_OVERLAY.yaml",{"artifact_type":"EFFECTIVE_CONTRACT_OVERLAY","stage_uid":STAGE,"product_execution_authority_ref":AUTH,"status":"CURRENT"})
    write(wd/"DEPENDENCY_TOPOLOGY.yaml",{"artifact_type":"DEPENDENCY_TOPOLOGY","stage_uid":STAGE,
      "verified_source_revision_ref":input_ref(work,"VERIFIED_SOURCE_REVISION"),"work_unit_closure_record_ref":input_ref(work,"WORK_UNIT_CLOSURE_RECORD"),"status":"CURRENT"})
    write(wd/"DENOMINATOR_SNAPSHOT.yaml",{"artifact_type":"DENOMINATOR_SNAPSHOT","stage_uid":STAGE,"required_operation_total":len(OPS),"closure_blocker_total":0,"status":"FROZEN_FOR_CURRENT_WORK_UNIT"})
    write(wd/"CLASSIFICATION_RULESET.yaml",{"artifact_type":"CLASSIFICATION_RULESET","stage_uid":STAGE,
      "rules":{"build_failure":"BLOCK","migration_incompatible":"BLOCK","security_high_vulnerability":"BLOCK","missing_staging_external_authority":"SUCCESSOR_BOUNDARY_BLOCK","historical_completion_credit":"FORBIDDEN"},"status":"CURRENT"})
    write(wd/"CHANGE_IMPACT_MAP.yaml",{"artifact_type":"CHANGE_IMPACT_MAP","stage_uid":STAGE,"source_change_requires_rebuild":True,"migration_change_requires_reverify":True,"status":"CURRENT"})
    write(wd/"CURRENT_PROBLEM_REGISTER.yaml",{"artifact_type":"CURRENT_PROBLEM_REGISTER","stage_uid":STAGE,"problems":[],"closure_blocker_total":0,"status":"CURRENT"})
    write(wd/"RESOLUTION_LEDGER.yaml",{"artifact_type":"RESOLUTION_LEDGER","stage_uid":STAGE,"append_only":True,"entries":[],"status":"CURRENT"})
    write(wd/"STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml",{"artifact_type":"STAGE_EXECUTION_PREFLIGHT_RECEIPT","stage_uid":STAGE,"work_unit_uid":work["work_unit_uid"],
      "product_execution_authority_ref":AUTH,"historical_completion_credit_used":False,"result":"PASS","status":"PASS"})

def receipt(root,work,op):
    b=(work.get("operation_bindings") or {}).get(op) or {}; ref=str(b.get("operation_receipt_ref") or "")
    if not ref: raise SystemExit("BLOCK:STAGE07_OPERATION_RECEIPT_REF_MISSING:"+op)
    write(root/ref,{"artifact_type":"OPERATION_EXECUTION_RECEIPT","stage_uid":STAGE,"work_unit_uid":work["work_unit_uid"],"operation_uid":op,
      "governance_uid":work["governance_uid"],"status":"PASS","executor_owner":b.get("executor_owner"),"executor_protocol":b.get("executor_protocol"),
      "result_owner":b.get("result_owner"),"historical_completion_credit":0})

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--stage",required=True); ap.add_argument("--operation",required=True); ap.add_argument("--work-unit",required=True); ap.add_argument("--product-root",required=True)
    a=ap.parse_args()
    if a.stage!=STAGE or a.operation not in OPS: raise SystemExit("BLOCK:STAGE07_EXECUTOR_IDENTITY_DRIFT")
    root=Path(a.product_root).resolve(); wp=root/Path(a.work_unit); wd=wp.parent; work=load(wp); op=a.operation; auth=authority(root)
    if op=="OP-36-PRODUCTION_BUILD":
        preflight(root,wd,work)
        src=load(root/input_ref(work,"VERIFIED_SOURCE_REVISION")); close=load(root/input_ref(work,"WORK_UNIT_CLOSURE_RECORD"))
        if src.get("status")!="PASS" or close.get("status")!="PASS": raise SystemExit("BLOCK:STAGE07_PREDECESSOR_VERIFICATION_NOT_PASS")
        run(root,["npm","ci"]); output=run(root,["npm","run","build"],env={**os.environ,"NEXT_PUBLIC_ACPOS_RUNTIME_MODE":"CONTROLLED_TEST"})
        server=root/".next/standalone/server.js"; static=root/".next/static"
        if not server.is_file() or not static.is_dir(): raise SystemExit("BLOCK:STAGE07_BUILD_ARTIFACT_NOT_MATERIALIZED")
        manifest_files=sorted(p for p in (root/".next/standalone").rglob("*") if p.is_file())
        digest=hashlib.sha256()
        for p in manifest_files:
            digest.update(p.relative_to(root).as_posix().encode()); digest.update(p.read_bytes())
        write(wd/"BUILD_IDENTITY_MANIFEST.yaml",{"artifact_type":"BUILD_IDENTITY_MANIFEST","stage_uid":STAGE,"work_unit_uid":work["work_unit_uid"],
          "build_command":"npm run build","toolchain":"Node.js 22 + npm + Next.js 16.3.3","build_output_mode":"NEXT_STANDALONE_NON_VERCEL",
          "standalone_entry":".next/standalone/server.js","static_root":".next/static","build_digest_sha256":digest.hexdigest(),
          "verified_source_revision_ref":input_ref(work,"VERIFIED_SOURCE_REVISION"),"historical_completion_credit":0,"status":"PASS"})
        write(wd/"BUILD_TEST_EVIDENCE.yaml",{"artifact_type":"BUILD_TEST_EVIDENCE","stage_uid":STAGE,"work_unit_uid":work["work_unit_uid"],
          "build_command":"npm run build","build_result":"PASS","standalone_entry_exists":True,"static_root_exists":True,"build_log_tail":output[-2000:],
          "historical_completion_credit":0,"status":"PASS"})
    elif op=="RELEASE_CANDIDATE_COMPILE":
        b=load(wd/"BUILD_IDENTITY_MANIFEST.yaml")
        if b.get("status")!="PASS": raise SystemExit("BLOCK:STAGE07_BUILD_IDENTITY_NOT_PASS")
        write(wd/"RELEASE_CANDIDATE.yaml",{"artifact_type":"RELEASE_CANDIDATE","stage_uid":STAGE,"work_unit_uid":work["work_unit_uid"],
          "governed_unit_uid":work["governed_unit_uid"],"build_identity_manifest_ref":str((wd/"BUILD_IDENTITY_MANIFEST.yaml").relative_to(root)),
          "build_digest_sha256":b.get("build_digest_sha256"),"source_revision_ref":input_ref(work,"VERIFIED_SOURCE_REVISION"),
          "candidate_state":"CURRENT_BUILD_CANDIDATE","historical_completion_credit":0,"status":"PASS"})
    elif op=="MIGRATION_COMPATIBILITY_VERIFY":
        ref=str((((auth.get("build_target_authority") or {}).get("MIGRATION_COMPATIBILITY_TARGET") or {}).get("target_path") or ""))
        if not ref or not (root/ref).is_file(): raise SystemExit("BLOCK:STAGE07_MIGRATION_COMPATIBILITY_TARGET_MISSING")
        output=run(root,["node","--test",ref])
        d=load(wd/"BUILD_TEST_EVIDENCE.yaml"); d["migration_compatibility_test_ref"]=ref; d["migration_compatibility_result"]="PASS"; d["migration_test_log_tail"]=output[-1600:]; write(wd/"BUILD_TEST_EVIDENCE.yaml",d)
    elif op=="SECURITY_FRESHNESS_VERIFY":
        output=run(root,["npm","audit","--audit-level=high"])
        d=load(wd/"BUILD_TEST_EVIDENCE.yaml"); d["security_freshness_command"]="npm audit --audit-level=high"; d["security_freshness_result"]="PASS"; d["security_audit_log_tail"]=output[-1600:]; write(wd/"BUILD_TEST_EVIDENCE.yaml",d)
    elif op=="STAGING_APPLICABILITY_DECIDE":
        vercel=load(root/"vercel.json") if (root/"vercel.json").is_file() else {}
        write(wd/"STAGING_APPLICABILITY_DECISION.yaml",{"artifact_type":"STAGING_APPLICABILITY_DECISION","stage_uid":STAGE,"work_unit_uid":work["work_unit_uid"],
          "applicability":"REQUIRED_FOR_REGISTERED_STAGE08","deployment_platform_configuration_ref":"vercel.json" if vercel else None,
          "external_staging_target_authority_status":"UNRESOLVED_CURRENT_EXTERNAL_PROJECT_IDENTITY",
          "disposition":"BLOCK_AT_STAGE07_TO_STAGE08_SUCCESSOR_READINESS_UNTIL_EXTERNAL_CURRENT_TARGET_RESOLVES",
          "ai_selected_external_project":False,"historical_completion_credit":0,"status":"PASS"})
    receipt(root,work,op); print("PASS:",op,work["work_unit_uid"])

if __name__=="__main__": main()
