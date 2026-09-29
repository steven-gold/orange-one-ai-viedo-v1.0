#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,subprocess,os
from pathlib import Path
import yaml
CLASSES=["REPOSITORY_TARGET","APPLICATION_ROOT","IMPLEMENTATION_OWNER","IMPLEMENTATION_LANGUAGE_AUTHORITY","FRONTEND_FRAMEWORK_AUTHORITY","BACKEND_FRAMEWORK_AUTHORITY","PACKAGE_MANAGER_AUTHORITY","FRONTEND_RUNTIME_TARGET","BACKEND_RUNTIME_TARGET","DATA_ACCESS_TARGET","DATABASE_TARGET","AUTHENTICATION_TARGET","AUTHORIZATION_TARGET","DATA_SECURITY_TARGET","AUDIT_LOGGING_TARGET","EXTERNAL_INTEGRATION_TARGET","ASYNC_RUNTIME_TARGET","STORAGE_RUNTIME_TARGET"]
AUTH="STAGE_EXECUTION/SHARED_AUTHORITY/IMPLEMENTATION_EXECUTION_TARGET_AUTHORITY.yaml"
def load(p):
    p=Path(p)
    if not p.is_file(): raise SystemExit("BLOCK:MISSING:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d
def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(yaml.safe_dump(o,sort_keys=False,allow_unicode=True,width=180),encoding="utf-8")
def git(root,*args):
    cp=subprocess.run(["git","-C",str(root),*args],text=True,capture_output=True)
    if cp.returncode!=0: raise SystemExit("BLOCK:GIT:"+cp.stderr.strip())
    return cp.stdout.strip()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--predecessor-work-unit",required=True); ap.add_argument("--product-root",required=True)
    a=ap.parse_args(); root=Path(a.product_root).resolve(); wp=root/Path(a.predecessor_work_unit); wd=wp.parent; work=load(wp)
    auth=load(root/AUTH); proto=auth.get("authority") or {}
    if proto.get("status")!="CURRENT_DYNAMIC_RESOLUTION_CONTRACT": raise SystemExit("BLOCK:STAGE05_TARGET_AUTHORITY_PROTOCOL_NOT_CURRENT")
    head=git(root,"rev-parse","HEAD"); tree=git(root,"rev-parse","HEAD^{tree}"); branch=git(root,"rev-parse","--abbrev-ref","HEAD"); branch=(os.environ.get("GITHUB_REF_NAME") or "0921acpos") if branch=="HEAD" else branch
    remote=git(root,"config","--get","remote.origin.url")
    tracked=git(root,"ls-tree","-r","--name-only","HEAD").splitlines()
    app_markers=[p for p in tracked if Path(p).name in {"package.json","pyproject.toml","requirements.txt","go.mod","Cargo.toml"}]
    roots=sorted(set(str(Path(p).parent) if str(Path(p).parent)!="." else "." for p in app_markers))
    bindings=[]; unresolved=[]
    repo_identity=remote[:-4] if remote.endswith(".git") else remote
    if repo_identity.startswith("git@github.com:"): repo_identity=repo_identity.split(":",1)[1]
    elif "github.com/" in repo_identity: repo_identity=repo_identity.split("github.com/",1)[1]
    base={"current_execution_repository":repo_identity,"current_execution_branch":branch,"current_execution_head_sha":head,"current_execution_tree_sha":tree,"current_context_match":True,"successor_stage_uid":"STAGE-05"}
    def add(cls,status,target=None,evidence=None,reason=None):
        row=dict(base,binding_uid="STAGE05-TARGET-"+cls,consuming_operation_uid="",binding_class=cls,applicability="REQUIRED",target_identity=target or "",canonical_owner_or_authority_ref=evidence or AUTH,authority_evidence_ref=evidence or AUTH,work_unit_uid=work.get("work_unit_uid"),resolution_kind="CURRENT_REPOSITORY_FRESH_SCAN",resolution_status=status)
        if reason: row["unresolved_reason"]=reason
        bindings.append(row)
        if status!="RESOLVED_CURRENT": unresolved.append(cls)
    add("REPOSITORY_TARGET","RESOLVED_CURRENT",repo_identity,AUTH)
    if len(roots)==1: add("APPLICATION_ROOT","RESOLVED_CURRENT",roots[0],app_markers[0])
    else: add("APPLICATION_ROOT","AUTHORITY_GAP",reason="NO_UNIQUE_CURRENT_APPLICATION_ROOT; markers="+repr(app_markers))
    for cls in CLASSES:
        if cls in {"REPOSITORY_TARGET","APPLICATION_ROOT"}: continue
        add(cls,"AUTHORITY_GAP",reason="NO_CURRENT_EXACT_AUTHORITY_IN_0921acpos_TREE")
    receipt={"artifact_type":"STAGE05_CURRENT_TARGET_RESOLUTION","predecessor_stage_uid":"STAGE-04","predecessor_work_unit_uid":work.get("work_unit_uid"),"successor_stage_uid":"STAGE-05","source_authority_ref":AUTH,"current_execution_repository":repo_identity,"current_execution_branch":branch,"current_execution_head_sha":head,"current_execution_tree_sha":tree,"application_markers":app_markers,"application_root_candidates":roots,"bindings":bindings,"resolved_total":len(CLASSES)-len(unresolved),"unresolved_total":len(unresolved),"unresolved_binding_classes":unresolved,"status":"PASS" if not unresolved else "BLOCKED_CURRENT_AUTHORITY_GAP","completion_credit":0}
    out=wd/"EVIDENCE/STAGE05_CURRENT_TARGET_RESOLUTION.yaml"; write(out,receipt)
    if unresolved: raise SystemExit("BLOCK:STAGE05_CURRENT_TARGET_AUTHORITY_GAP:"+",".join(unresolved))
    print("PASS: Stage05 Current target authority resolved",out.relative_to(root))
if __name__=="__main__": main()
