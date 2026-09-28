#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, subprocess
from datetime import datetime, timezone
from pathlib import Path
import yaml

SELECTION_REL="STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_GOVERNANCE_SELECTION.yaml"

def load(path):
    obj=yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(obj,dict):
        raise SystemExit(f"BLOCK:MAPPING_REQUIRED:{path}")
    return obj

def write(path,obj):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(obj,allow_unicode=True,sort_keys=False,width=180),encoding="utf-8")

def git(root,*args):
    p=subprocess.run(["git","-C",str(root),*args],text=True,capture_output=True)
    if p.returncode!=0 or not p.stdout.strip():
        raise SystemExit("BLOCK:GIT_LOOKUP_FAILED:"+(" ".join(args))+":"+(p.stderr or p.stdout)[-400:])
    return p.stdout.strip()

def sha256_file(path):
    p=Path(path)
    if not p.is_file() or p.stat().st_size<=0:
        raise SystemExit("BLOCK:HASH_TARGET_MISSING:"+str(path))
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--product-root",required=True)
    ap.add_argument("--governance-root",required=True)
    ap.add_argument("--stage",required=True)
    ap.add_argument("--work-unit",required=True)
    a=ap.parse_args()
    product=Path(a.product_root).resolve()
    govroot=Path(a.governance_root).resolve()
    work_path=(product/a.work_unit).resolve()
    work_dir=work_path.parent
    if not work_path.is_file():
        raise SystemExit("BLOCK:SUCCESSOR_WORK_UNIT_MISSING:"+a.work_unit)

    selection_path=product/SELECTION_REL
    if not selection_path.is_file():
        raise SystemExit("BLOCK:CURRENT_GOVERNANCE_SELECTION_MISSING")
    selection=load(selection_path)
    if selection.get("artifact_type")!="PRODUCT_SELECTED_CURRENT_GOVERNANCE" or selection.get("status")!="SELECTED_EXACT_CURRENT_SNAPSHOT":
        raise SystemExit("BLOCK:CURRENT_GOVERNANCE_SELECTION_INVALID")

    reg=load(govroot/"governance/specifications/REGISTRY.yaml")
    ident=reg.get("governance_identity") or {}
    head=git(govroot,"rev-parse","HEAD")
    tree=git(govroot,"rev-parse","HEAD^{tree}")
    expected={
      "governance_commit_sha":head,
      "governance_uid":str(ident.get("governance_uid") or ""),
      "governance_revision":str(ident.get("governance_revision") or ""),
      "display_version":str(ident.get("display_version") or ""),
    }
    for key,value in expected.items():
        if not value or str(selection.get(key) or "")!=value:
            raise SystemExit("BLOCK:SELECTED_CURRENT_GOVERNANCE_BINDING_MISMATCH:"+key)

    if reg.get("status")!="CURRENT" or ident.get("status")!="CURRENT" or ident.get("identity_state")!="EXACT_HEAD_AND_BUNDLE_DIGEST_BOUND":
        raise SystemExit("BLOCK:SELECTED_GOVERNANCE_NOT_CURRENT_VALIDATED_SNAPSHOT")

    root_manifest=govroot/".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml"
    root_hash=sha256_file(root_manifest)

    bundle=str(ident.get("specification_bundle_sha256") or "")
    if not bundle:
        raise SystemExit("BLOCK:EFFECTIVE_NORMATIVE_SET_HASH_MISSING")

    work=load(work_path)
    if work.get("stage_uid")!=a.stage or work.get("work_unit_uid")!=work_dir.name:
        raise SystemExit("BLOCK:SUCCESSOR_WORK_UNIT_IDENTITY_DRIFT")
    if work.get("governance_execution_mode")!="CURRENT_VALIDATED_GOVERNANCE":
        raise SystemExit("BLOCK:SUCCESSOR_WORK_UNIT_CURRENT_GOVERNANCE_MODE_REQUIRED")
    if str(work.get("governance_uid") or work.get("current_governance_uid") or "")!=str(selection.get("governance_uid") or ""):
        raise SystemExit("BLOCK:SUCCESSOR_WORK_UNIT_GOVERNANCE_UID_DRIFT")

    receipt={
      "artifact_type":"PRODUCT_CURRENT_GOVERNANCE_LOAD_RECEIPT",
      "status":"PASS",
      "stage_uid":a.stage,
      "work_unit_uid":work_dir.name,
      "selected_governance_ref":SELECTION_REL,
      "governance_uid":selection["governance_uid"],
      "governance_revision":selection["governance_revision"],
      "governance_commit_sha":head,
      "governance_tree_sha":tree,
      "governance_root_manifest_sha256":root_hash,
      "effective_normative_set_sha256":bundle,
      "loader_uid":"ACPOS-PRODUCT-CURRENT-GOVERNANCE-LOADER-001",
      "loaded_at":datetime.now(timezone.utc).isoformat(),
    }
    write(work_dir/"PRODUCT_CURRENT_GOVERNANCE_LOAD_RECEIPT.yaml",receipt)
    print("PASS: Current governance load receipt materialized for",work_dir.name)

if __name__=="__main__":
    main()
