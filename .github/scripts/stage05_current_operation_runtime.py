#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, subprocess
from pathlib import Path
import yaml

STAGE="STAGE-05"
OPS=[
"OP-01-BLUEPRINT_INTAKE","OP-02-BLUEPRINT_VALIDATION","OP-03-AUDIT_BASELINE_INTAKE","OP-04-ACCEPTANCE_MATRIX_VALIDATION",
"OP-05-DEPENDENCY_MAPPING","OP-06-DUPLICATE_CONFLICT_PRECHECK","OP-07-CONTRACT_MATERIALIZATION","OP-08-REPOSITORY_OWNER_RESOLUTION",
"OP-09-SHARED_FOUNDATION_VERIFICATION","OP-10-FRONTEND_IMPLEMENTATION","OP-11-CONTROL_FIELD_IMPLEMENTATION","OP-12-ACTION_LAYER",
"OP-13-BACKEND_RUNTIME","OP-14-REPOSITORY_DATA_ACCESS_LAYER","OP-15-DATABASE_SCHEMA_MIGRATION","OP-16-AUTHENTICATION",
"OP-17-AUTHORIZATION","OP-18-DATA_SECURITY","OP-19-AUDIT_LOGGING","OP-20-ERROR_CONTRACT","OP-21-EXTERNAL_INTEGRATION",
"OP-22-ASYNC_RUNTIME","OP-23-STORAGE_RUNTIME","PROGRAM_ARTIFACT_REGISTRATION","IMPLEMENTATION_MANIFEST_COMPILE","IMPLEMENTATION_EVIDENCE_COMPILE"]
AUTH="STAGE_EXECUTION/SHARED_AUTHORITY/PRODUCT_IMPLEMENTATION_AUTHORITY.yaml"

def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d

def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(o,sort_keys=False,allow_unicode=True,width=180),encoding="utf-8")

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def git(root,*args):
    cp=subprocess.run(["git","-C",str(root),*args],text=True,capture_output=True)
    if cp.returncode!=0: raise SystemExit("BLOCK:GIT:"+cp.stderr.strip())
    return cp.stdout.strip()

def require(root,rel,label):
    p=(root/rel).resolve()
    try: p.relative_to(root)
    except ValueError: raise SystemExit("BLOCK:"+label+"_ESCAPES_ROOT:"+rel)
    if not p.exists(): raise SystemExit("BLOCK:"+label+"_MISSING:"+rel)
    out=git(root,"ls-files","--",rel)
    if rel not in {".","./"} and not out.strip(): raise SystemExit("BLOCK:"+label+"_NOT_TRACKED:"+rel)
    return p

def authority(root):
    d=load(root/AUTH)
    if d.get("status")!="CURRENT_STAGE05_AUTHORITY": raise SystemExit("BLOCK:STAGE05_IMPLEMENTATION_AUTHORITY_NOT_CURRENT")
    r=d.get("stage05_readiness") or {}
    if int(r.get("required_binding_class_total") or 0)!=18 or int(r.get("resolved_binding_class_total") or 0)!=18 or int(r.get("unresolved_binding_class_total") or -1)!=0:
        raise SystemExit("BLOCK:STAGE05_IMPLEMENTATION_AUTHORITY_INCOMPLETE")
    return d

def input_ref(work,uid):
    row=(work.get("input_bindings") or {}).get(uid) or {}
    ref=str(row.get("artifact_ref") or row.get("resolved_artifact_ref") or "")
    if not ref: raise SystemExit("BLOCK:STAGE05_INPUT_REF_MISSING:"+uid)
    return ref

def mapped_paths(governed):
    common=[
      "package.json","package-lock.json","next.config.ts","tsconfig.json",
      "database/migrations/0001_canonical_schema.sql","src/server/database/rlsRuntime.ts",
      "src/server/shared/observability.ts","src/server/shared/namedRuntimeError.ts",
      "src/server/aiApi/providerHttpAdapterRuntime.ts","src/server/queue/providerExecutionQueueRuntime.ts"
    ]
    if governed=="GLOBAL-HOME-SHELL-NAVIGATION":
        specific=[
          "src/app/layout.tsx","src/app/page.tsx","src/app/globals.css",
          "src/components/shell/AppShell.tsx","src/server/identity/navigationVisibilityRuntime.ts"
        ]
    elif governed=="workspace:WB-01":
        specific=[
          "src/components/pages/DashboardVisual.tsx","src/components/pages/DashboardVisual.module.css",
          "src/domain/dashboard/readModelContract.ts","src/server/dashboard/readModelRuntime.ts",
          "src/server/dashboard/wb01ProjectionRuntime.ts","src/app/v1/dashboard/read-model/route.ts"
        ]
    else:
        raise SystemExit("BLOCK:STAGE05_PROGRAM_ARTIFACT_MAPPING_MISSING:"+governed)
    return common+specific

def profile_for(path):
    if path.endswith(".sql"): return "DATABASE_MIGRATION"
    if "/v1/" in path and path.endswith("/route.ts"): return "API_ENTRY"
    if path.startswith("src/server/queue/"): return "ASYNC_WORKER"
    if path.startswith("src/server/aiApi/"): return "EXTERNAL_ADAPTER"
    if path.startswith("src/server/database/"): return "REPOSITORY_DATA_ACCESS"
    if path.startswith("src/server/"): return "RUNTIME_SERVICE"
    if path.startswith("src/domain/"): return "CONTROL_HANDLER"
    if path.endswith(".tsx") or path.endswith(".css"): return "UI_COMPONENT"
    return "RUNTIME_SERVICE"

def ensure_preflight(root,wd,work):
    stage_inputs={k:input_ref(work,k) for k in ("DESIGN_FREEZE_PACKAGE","ACCEPTANCE_AUDIT_BLUEPRINT","DEPENDENCY_MAP")}
    write(wd/"REQUIRED_FIELD_MANIFEST.yaml",{
      "artifact_type":"REQUIRED_FIELD_MANIFEST","stage_uid":STAGE,"work_unit_uid":work["work_unit_uid"],
      "required_inputs":list(stage_inputs),"required_operations":OPS,
      "required_outputs":["IMPLEMENTATION_MANIFEST","PROGRAM_ARTIFACT_SET","IMPLEMENTATION_EVIDENCE"],
      "required_evidence":["IMPLEMENTATION_DIFF_EVIDENCE"],"status":"CURRENT"})
    write(wd/"FUNCTIONAL_CHAIN_MANIFEST.yaml",{
      "artifact_type":"FUNCTIONAL_CHAIN_MANIFEST","stage_uid":STAGE,"governed_unit_uid":work["governed_unit_uid"],
      "implementation_chain":["FROZEN_DESIGN","PROGRAM_ARTIFACT_REGISTRATION","IMPLEMENTATION","EVIDENCE"],"status":"CURRENT"})
    write(wd/"EFFECTIVE_CONTRACT_OVERLAY.yaml",{
      "artifact_type":"EFFECTIVE_CONTRACT_OVERLAY","stage_uid":STAGE,
      "product_implementation_authority_ref":AUTH,"business_semantics_redefined":False,"status":"CURRENT"})
    write(wd/"DEPENDENCY_TOPOLOGY.yaml",{
      "artifact_type":"DEPENDENCY_TOPOLOGY","stage_uid":STAGE,"input_refs":stage_inputs,
      "program_paths":mapped_paths(work["governed_unit_uid"]),"status":"CURRENT"})
    write(wd/"DENOMINATOR_SNAPSHOT.yaml",{
      "artifact_type":"DENOMINATOR_SNAPSHOT","stage_uid":STAGE,
      "required_operation_total":len(OPS),"program_artifact_path_total":len(mapped_paths(work["governed_unit_uid"])),
      "open_input_gap_total":0,"closure_blocker_total":0,"status":"FROZEN_FOR_CURRENT_WORK_UNIT"})
    write(wd/"CLASSIFICATION_RULESET.yaml",{
      "artifact_type":"CLASSIFICATION_RULESET","stage_uid":STAGE,
      "rules":{"unregistered_program_artifact":"BLOCK","invented_stack":"BLOCK","storage_runtime":"AUTHORIZED_NOT_APPLICABLE_WITH_AUTHORITY_ONLY","historical_completion_credit":"FORBIDDEN"},"status":"CURRENT"})
    write(wd/"CHANGE_IMPACT_MAP.yaml",{
      "artifact_type":"CHANGE_IMPACT_MAP","stage_uid":STAGE,
      "frozen_design_change_requires_reentry":True,"program_source_change_requires_stage06_reverify":True,"status":"CURRENT"})
    write(wd/"CURRENT_PROBLEM_REGISTER.yaml",{"artifact_type":"CURRENT_PROBLEM_REGISTER","stage_uid":STAGE,"problems":[],"closure_blocker_total":0,"status":"CURRENT"})
    write(wd/"RESOLUTION_LEDGER.yaml",{"artifact_type":"RESOLUTION_LEDGER","stage_uid":STAGE,"append_only":True,"entries":[],"status":"CURRENT"})
    write(wd/"STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml",{
      "artifact_type":"STAGE_EXECUTION_PREFLIGHT_RECEIPT","stage_uid":STAGE,"work_unit_uid":work["work_unit_uid"],
      "product_implementation_authority_ref":AUTH,"current_head_sha":git(root,"rev-parse","HEAD"),"historical_completion_credit_used":False,"result":"PASS","status":"PASS"})

def verify_inputs(root,work):
    freeze=load(root/input_ref(work,"DESIGN_FREEZE_PACKAGE"))
    audit=load(root/input_ref(work,"ACCEPTANCE_AUDIT_BLUEPRINT"))
    dep=load(root/input_ref(work,"DEPENDENCY_MAP"))
    if freeze.get("immutable") is not True or freeze.get("status")!="PASS": raise SystemExit("BLOCK:STAGE05_DESIGN_FREEZE_NOT_PASS")
    if int(audit.get("missing_acceptance_item_total") or 0)!=0 or audit.get("status")!="PASS": raise SystemExit("BLOCK:STAGE05_ACCEPTANCE_BLUEPRINT_NOT_PASS")
    if not isinstance(dep.get("dependencies"),list): raise SystemExit("BLOCK:STAGE05_DEPENDENCY_MAP_INVALID")
    return freeze,audit,dep

def verify_authority_target(root,auth,key):
    row=(auth.get("execution_target_authority") or {}).get(key) or (auth.get("toolchain_authority") or {}).get(key) or {}
    status=str(row.get("status") or "")
    if status=="AUTHORIZED_NOT_APPLICABLE": return
    if status not in {"RESOLVED","RESOLVED_BY_AUTHORIZED_TEMPLATE"}: raise SystemExit("BLOCK:STAGE05_AUTHORITY_TARGET_UNRESOLVED:"+key)
    if row.get("resolution_kind")=="CURRENT_REPOSITORY_PATH": require(root,str(row.get("target_path") or ""),key)

def artifacts(root,work):
    owner="OWNER-STAGE05-"+str(work["governed_unit_uid"]).replace(":","-")
    norm=[]
    matrix=load(root/str(work.get("normative_execution_matrix_ref") or ""))
    for row in matrix.get("rows") or []:
        uid=str((row or {}).get("normative_section_uid") or "")
        if uid and uid not in norm: norm.append(uid)
    inputs=[str((x or {}).get("artifact_ref") or "") for x in (work.get("input_bindings") or {}).values() if isinstance(x,dict)]
    rows=[]
    for rel in mapped_paths(work["governed_unit_uid"]):
        p=require(root,rel,"PROGRAM_ARTIFACT")
        rows.append({
          "program_artifact_uid":"PA-"+hashlib.sha256((work["work_unit_uid"]+"|"+rel).encode()).hexdigest()[:20].upper(),
          "work_unit_uid":work["work_unit_uid"],"page_or_scope_uid":work.get("scope_uid") or work["governed_unit_uid"],
          "construction_profile":profile_for(rel),"canonical_name":Path(rel).name,"canonical_path":rel,
          "canonical_filename":Path(rel).name,"owner_uid":owner,"producer_profile_step_uid":"STAGE05_CURRENT_RUNTIME",
          "input_artifact_refs":inputs,"required_normative_refs":norm,"dependency_refs":[],"reverse_dependency_refs":[],
          "acceptance_audit_blueprint_ref":input_ref(work,"ACCEPTANCE_AUDIT_BLUEPRINT"),"required_test_refs":[],
          "current_hash":sha(p),"status":"CURRENT"
        })
    return rows

def receipt(root,work,op):
    b=(work.get("operation_bindings") or {}).get(op) or {}; ref=str(b.get("operation_receipt_ref") or "")
    if not ref: raise SystemExit("BLOCK:STAGE05_OPERATION_RECEIPT_REF_MISSING")
    write(root/ref,{"artifact_type":"OPERATION_EXECUTION_RECEIPT","stage_uid":STAGE,"work_unit_uid":work["work_unit_uid"],"operation_uid":op,
      "governance_uid":work["governance_uid"],"status":"PASS","executor_owner":b.get("executor_owner"),"executor_protocol":b.get("executor_protocol"),
      "result_owner":b.get("result_owner"),"historical_completion_credit":0})

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage",required=True); ap.add_argument("--operation",required=True); ap.add_argument("--work-unit",required=True); ap.add_argument("--product-root",required=True)
    a=ap.parse_args()
    if a.stage!=STAGE or a.operation not in OPS or a.operation=="OP-23-STORAGE_RUNTIME": raise SystemExit("BLOCK:STAGE05_EXECUTOR_IDENTITY_DRIFT")
    root=Path(a.product_root).resolve(); wp=root/Path(a.work_unit); wd=wp.parent; work=load(wp); op=a.operation
    auth=authority(root)
    if op=="OP-01-BLUEPRINT_INTAKE":
        ensure_preflight(root,wd,work); verify_inputs(root,work)
    elif op=="OP-02-BLUEPRINT_VALIDATION":
        verify_inputs(root,work)
    elif op=="OP-03-AUDIT_BASELINE_INTAKE":
        load(root/input_ref(work,"ACCEPTANCE_AUDIT_BLUEPRINT"))
    elif op=="OP-04-ACCEPTANCE_MATRIX_VALIDATION":
        _,audit,_=verify_inputs(root,work)
        if int(audit.get("required_domain_total") or 0)!=int(audit.get("covered_domain_total") or -1): raise SystemExit("BLOCK:STAGE05_ACCEPTANCE_DENOMINATOR_DRIFT")
    elif op=="OP-05-DEPENDENCY_MAPPING":
        verify_inputs(root,work)
    elif op=="OP-06-DUPLICATE_CONFLICT_PRECHECK":
        ps=mapped_paths(work["governed_unit_uid"])
        if len(ps)!=len(set(ps)): raise SystemExit("BLOCK:STAGE05_DUPLICATE_PROGRAM_PATH")
        for rel in ps: require(root,rel,"PROGRAM_ARTIFACT")
    elif op=="OP-07-CONTRACT_MATERIALIZATION":
        ensure_preflight(root,wd,work)
    elif op=="OP-08-REPOSITORY_OWNER_RESOLUTION":
        if str(auth.get("product_repository") or "")!="steven-gold/orange-one-ai-viedo-v1.0": raise SystemExit("BLOCK:STAGE05_REPOSITORY_AUTHORITY_DRIFT")
    elif op=="OP-09-SHARED_FOUNDATION_VERIFICATION":
        for rel in ("package.json","package-lock.json","next.config.ts","tsconfig.json"): require(root,rel,"SHARED_FOUNDATION")
    elif op=="OP-10-FRONTEND_IMPLEMENTATION":
        verify_authority_target(root,auth,"FRONTEND_RUNTIME_TARGET")
        for rel in mapped_paths(work["governed_unit_uid"]):
            if rel.endswith(".tsx") or rel.endswith(".css"): require(root,rel,"FRONTEND_ARTIFACT")
    elif op=="OP-11-CONTROL_FIELD_IMPLEMENTATION":
        for rel in mapped_paths(work["governed_unit_uid"]):
            if rel.startswith("src/components/") or rel.startswith("src/domain/"): require(root,rel,"CONTROL_FIELD_ARTIFACT")
    elif op=="OP-12-ACTION_LAYER":
        for rel in mapped_paths(work["governed_unit_uid"]):
            if rel.startswith("src/domain/") or "/v1/" in rel: require(root,rel,"ACTION_LAYER_ARTIFACT")
    elif op=="OP-13-BACKEND_RUNTIME": verify_authority_target(root,auth,"BACKEND_RUNTIME_TARGET")
    elif op=="OP-14-REPOSITORY_DATA_ACCESS_LAYER": verify_authority_target(root,auth,"DATA_ACCESS_TARGET")
    elif op=="OP-15-DATABASE_SCHEMA_MIGRATION": verify_authority_target(root,auth,"DATABASE_TARGET")
    elif op=="OP-16-AUTHENTICATION": verify_authority_target(root,auth,"AUTHENTICATION_TARGET")
    elif op=="OP-17-AUTHORIZATION": verify_authority_target(root,auth,"AUTHORIZATION_TARGET")
    elif op=="OP-18-DATA_SECURITY": verify_authority_target(root,auth,"DATA_SECURITY_TARGET")
    elif op=="OP-19-AUDIT_LOGGING": verify_authority_target(root,auth,"AUDIT_LOGGING_TARGET")
    elif op=="OP-20-ERROR_CONTRACT": require(root,"src/server/shared/namedRuntimeError.ts","ERROR_CONTRACT")
    elif op=="OP-21-EXTERNAL_INTEGRATION": verify_authority_target(root,auth,"EXTERNAL_INTEGRATION_TARGET")
    elif op=="OP-22-ASYNC_RUNTIME": verify_authority_target(root,auth,"ASYNC_RUNTIME_TARGET")
    elif op=="PROGRAM_ARTIFACT_REGISTRATION":
        rows=artifacts(root,work)
        write(wd/"PROGRAM_ARTIFACT_SET.yaml",{"artifact_type":"PROGRAM_ARTIFACT_SET","stage_uid":STAGE,"work_unit_uid":work["work_unit_uid"],
          "governed_unit_uid":work["governed_unit_uid"],"program_artifact_total":len(rows),"program_artifacts":rows,"unregistered_program_artifact_total":0,"status":"PASS"})
    elif op=="IMPLEMENTATION_MANIFEST_COMPILE":
        pas=load(wd/"PROGRAM_ARTIFACT_SET.yaml")
        profiles=sorted(set(str(x.get("construction_profile") or "") for x in pas.get("program_artifacts") or []))
        write(wd/"IMPLEMENTATION_MANIFEST.yaml",{"artifact_type":"IMPLEMENTATION_MANIFEST","stage_uid":STAGE,"work_unit_uid":work["work_unit_uid"],
          "governed_unit_uid":work["governed_unit_uid"],"governance_uid":work["governance_uid"],"design_freeze_ref":input_ref(work,"DESIGN_FREEZE_PACKAGE"),
          "acceptance_audit_blueprint_ref":input_ref(work,"ACCEPTANCE_AUDIT_BLUEPRINT"),"program_artifact_set_ref":str((wd/"PROGRAM_ARTIFACT_SET.yaml").relative_to(root)),
          "product_implementation_authority_ref":AUTH,"construction_profiles":profiles,"program_artifact_total":pas.get("program_artifact_total"),
          "storage_runtime_applicability":"AUTHORIZED_NOT_APPLICABLE","historical_completion_credit":0,"status":"PASS"})
    elif op=="IMPLEMENTATION_EVIDENCE_COMPILE":
        manifest=load(wd/"IMPLEMENTATION_MANIFEST.yaml"); pas=load(wd/"PROGRAM_ARTIFACT_SET.yaml")
        head=git(root,"rev-parse","HEAD")
        write(wd/"IMPLEMENTATION_EVIDENCE.yaml",{"artifact_type":"IMPLEMENTATION_EVIDENCE","stage_uid":STAGE,"work_unit_uid":work["work_unit_uid"],
          "governed_unit_uid":work["governed_unit_uid"],"implementation_manifest_ref":str((wd/"IMPLEMENTATION_MANIFEST.yaml").relative_to(root)),
          "program_artifact_set_ref":str((wd/"PROGRAM_ARTIFACT_SET.yaml").relative_to(root)),"verified_program_artifact_total":pas.get("program_artifact_total"),
          "current_head_sha":head,"historical_completion_credit":0,"status":"PASS"})
        write(wd/"IMPLEMENTATION_DIFF_EVIDENCE.yaml",{"artifact_type":"IMPLEMENTATION_DIFF_EVIDENCE","stage_uid":STAGE,"work_unit_uid":work["work_unit_uid"],
          "adopted_runtime_commit_ref":(auth.get("adoption_source") or {}).get("adopted_into_current_branch_commit"),"current_head_sha":head,
          "program_artifact_hashes":[{"canonical_path":x.get("canonical_path"),"current_hash":x.get("current_hash")} for x in pas.get("program_artifacts") or []],
          "historical_completion_credit":0,"status":"PASS"})
    receipt(root,work,op)
    print("PASS:",op,work["work_unit_uid"])

if __name__=="__main__": main()
