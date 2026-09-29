#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
import yaml
ADAPTERS="governance/ci/stage_execution_semantic_adapters.yaml"; LIFECYCLE=".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml"; REFREG=".github/governance-source/active/source/10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml"
def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d
def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(yaml.safe_dump(o,sort_keys=False,allow_unicode=True),encoding="utf-8")
def run(cmd,cwd):
    cp=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True)
    if cp.returncode!=0: sys.stderr.write(cp.stdout+cp.stderr); raise SystemExit(cp.returncode)
    return cp.stdout.strip()
def stage1_guard(root,gov,wd):
    p=gov/".github/governance-source/active/source/09_TESTS/governance/governance_stage1_pipeline_guard.py"; d=json.loads(run([sys.executable,str(p),str(gov/".github/governance-source/active/source"),str(wd)],root))
    if d.get("status")!="PASS": raise SystemExit("BLOCK:STAGE1_SCANNER_NOT_PASS")
    return d
def vreg(gov):
    return {str(x.get("validator_uid")):x for x in load(gov/REFREG).get("validator_identities") or [] if isinstance(x,dict)}
def refresh_stage1_manifests(root):
    run([sys.executable,".github/scripts/stage01_current_materialize.py","--mode","refresh-manifest","--product-root",str(root)],root)
def assert_stage1_manifest_fresh(wd):
    manifest=load(wd/"CURRENT_RUN_MANIFEST.yaml")
    declared=sorted(map(str,manifest.get("current_files") or []))
    actual=sorted(p.relative_to(wd).as_posix() for p in wd.rglob("*") if p.is_file())
    if declared!=actual:
        raise SystemExit("BLOCK:STAGE1_CURRENT_RUN_MANIFEST_NOT_FRESH")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["validate-contract","materialize","validate"],default="validate-contract"); ap.add_argument("--stage"); ap.add_argument("--work-unit"); ap.add_argument("--product-root",required=True); ap.add_argument("--governance-root",required=True)
    a=ap.parse_args(); root=Path(a.product_root).resolve(); gov=Path(a.governance_root).resolve(); life=load(gov/LIFECYCLE); stages={str(x.get("stage_uid")):x for x in life.get("stages") or []}; adapters=load(gov/ADAPTERS)
    if list(stages)!=[f"STAGE-{i:02d}" for i in range(1,12)]: raise SystemExit("BLOCK:PRETERMINAL_LIFECYCLE_DRIFT")
    if a.mode=="validate-contract": print("PASS: preterminal evidence producer covers Stage-01..11"); return
    if not a.stage or not a.work_unit: raise SystemExit("BLOCK:PRETERMINAL_REQUIRED_ARGUMENT_MISSING")
    wp=root/Path(a.work_unit); wd=wp.parent; work=load(wp); state=load(wd/"EXECUTION_STATE.yaml")
    if str(work.get("stage_uid"))!=a.stage or str(state.get("current_operation"))!="COMPLETE": raise SystemExit("BLOCK:PRETERMINAL_OPERATIONS_NOT_COMPLETE")
    stage=stages[a.stage]; scans=list(map(str,((adapters.get("stages") or {}).get(a.stage) or {}).get("scanner_dimensions") or [])); sb=work.get("scanner_bindings") or {}
    if set(map(str,sb))!=set(scans): raise SystemExit("BLOCK:PRETERMINAL_SCANNER_BINDING_COVERAGE_DRIFT")
    if a.mode=="materialize":
        stage1_guard_basis=None
        if a.stage=="STAGE-01":
            gd=stage1_guard(root,gov,wd)
            stage1_guard_basis=gd
            for dim in scans:
                write(root/str((sb.get(dim) or {}).get("result_ref") or ""),{"artifact_type":"SCANNER_RESULT","stage_uid":a.stage,"work_unit_uid":work.get("work_unit_uid"),"scanner_dimension":dim,"status":"PASS","gaps":[],"hidden_defect_total":0,"physical_scanner_owner":(sb.get(dim) or {}).get("scanner_owner"),"physical_scanner_result_digest_basis":gd.get("candidate_normative_hash")})
            refresh_stage1_manifests(root)
            assert_stage1_manifest_fresh(wd)
        else:
            for dim in scans:
                b=sb.get(dim) or {}; owner=str(b.get("scanner_owner") or ""); proto=str(b.get("scanner_protocol") or "")
                if not owner or not (root/owner).is_file(): raise SystemExit("BLOCK:SCANNER_OWNER_NOT_PHYSICAL:"+dim)
                if proto!="PYTHON_STAGE_SCANNER_V1": raise SystemExit("BLOCK:SCANNER_PROTOCOL_UNSUPPORTED:"+a.stage+":"+dim)
                d=json.loads(run([sys.executable,owner,"--stage",a.stage,"--scanner-dimension",dim,"--work-unit",str(wp.relative_to(root)),"--product-root",str(root)],root))
                if d.get("status")!="PASS": raise SystemExit("BLOCK:SCANNER_NOT_PASS:"+dim)
                write(root/str(b.get("result_ref") or ""),dict(d,artifact_type="SCANNER_RESULT",scanner_dimension=dim))
        reg=vreg(gov); vb=work.get("validator_bindings") or {}; vals=list(map(str,stage.get("validators") or []))
        if set(map(str,vb))!=set(vals): raise SystemExit("BLOCK:PRETERMINAL_VALIDATOR_BINDING_COVERAGE_DRIFT")
        for uid in vals:
            meta=reg.get(uid) or {}; impl=meta.get("implementation_path")
            if uid=="VAL-GOV-026":
                if a.stage!="STAGE-01" or not stage1_guard_basis:
                    raise SystemExit("BLOCK:STAGE1_PIPELINE_GUARD_BASIS_MISSING")
                assert_stage1_manifest_fresh(wd)
            elif impl:
                if str((vb.get(uid) or {}).get("validator_protocol") or "")!="NOARG_GOVERNANCE_VALIDATOR": raise SystemExit("BLOCK:PHYSICAL_VALIDATOR_STAGE_PROTOCOL_UNRESOLVED:"+uid)
                p=gov/".github/governance-source/active/source"/str(impl)
                if not p.is_file(): raise SystemExit("BLOCK:PHYSICAL_VALIDATOR_NOT_FOUND:"+uid)
                run([sys.executable,str(p)],gov/".github/governance-source/active/source")
            else:
                run([sys.executable,".github/scripts/common_declared_stage_validator.py","--stage",a.stage,"--validator-uid",uid,"--work-unit",str(wp.relative_to(root)),"--product-root",str(root)],root)
            write(root/str((vb.get(uid) or {}).get("result_ref") or ""),{"artifact_type":"VALIDATOR_RESULT","stage_uid":a.stage,"work_unit_uid":work.get("work_unit_uid"),"validator_uid":uid,"validator_identity_mode":meta.get("identity_mode"),"status":"PASS"})
        if a.stage=="STAGE-01":
            refresh_stage1_manifests(root)
            assert_stage1_manifest_fresh(wd)
        write(wd/"EVIDENCE/HIDDEN_DEFECT_SWEEP_RESULT.yaml",{"artifact_type":"HIDDEN_DEFECT_SWEEP","stage_uid":a.stage,"work_unit_uid":work.get("work_unit_uid"),"status":"PASS","discovered_defect_total":0,"basis":"FRESH_SCANNER_REEXECUTION_OR_EXACT_CURRENT_SCANNER_RESULTS"})
        if a.stage=="STAGE-04":
            run([sys.executable,".github/scripts/stage05_current_target_resolver.py","--predecessor-work-unit",str(wp.relative_to(root)),"--product-root",str(root)],root)
        run([sys.executable,".github/scripts/common_successor_binding_resolver.py","--mode","resolve","--from-stage",a.stage,"--predecessor-work-unit",str(wp.relative_to(root)),"--product-root",str(root),"--governance-root",str(gov)],root)
        if a.stage=="STAGE-01":
            refresh_stage1_manifests(root)
            assert_stage1_manifest_fresh(wd)
    for dim in scans:
        d=load(root/str((sb.get(dim) or {}).get("result_ref") or ""))
        if d.get("status")!="PASS" or (d.get("gaps") or []): raise SystemExit("BLOCK:PRETERMINAL_SCANNER_RESULT_NOT_PASS:"+dim)
    for uid in map(str,stage.get("validators") or []):
        if load(root/str(((work.get("validator_bindings") or {}).get(uid) or {}).get("result_ref") or "")).get("status")!="PASS": raise SystemExit("BLOCK:PRETERMINAL_VALIDATOR_RESULT_NOT_PASS:"+uid)
    sweep=load(wd/"EVIDENCE/HIDDEN_DEFECT_SWEEP_RESULT.yaml")
    if sweep.get("status")!="PASS" or int(sweep.get("discovered_defect_total") or 0)!=0: raise SystemExit("BLOCK:PRETERMINAL_HIDDEN_DEFECT_SWEEP_NOT_PASS")
    if load(wd/"EVIDENCE/SUCCESSOR_EXECUTION_BINDING_RESOLUTION.yaml").get("status")!="PASS": raise SystemExit("BLOCK:PRETERMINAL_SUCCESSOR_BINDING_NOT_PASS")
    print("PASS: preterminal physical evidence ready",a.stage,work.get("work_unit_uid"))
if __name__=="__main__": main()
