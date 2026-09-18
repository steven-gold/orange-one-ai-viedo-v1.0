#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import copy, hashlib, io, json, lzma, re, subprocess, tarfile, zipfile
import yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".github/governance-source/active/source"
AUTH_UID = "USR-DIRECTIVE-20260919-MOTHER-PROMOTION-ATOMIC-SYNC-REPAIR-R2"
CURRENT_UID = "GOV-REV-20260919-SCOPE-STAGE-REENTRY-PORTABILITY-HARDENING"
SOURCE_REVISION = "v2.2.5-scope-stage-reentry-portability-hardening"
AUTH = ROOT / f"governance/test/spec_change_authorizations/{AUTH_UID}.yaml"

MOTHERS = [
    ("WEB-GOV-01", SOURCE / "12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md",
     "WEB-GOV-01-S075", "## 75. Execution Scope Authority / Capability Ownership / Upstream Re-entry"),
    ("WEB-GOV-02", SOURCE / "12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md",
     "WEB-GOV-02-S074", "## 74. Scope-Bound Delivery / Re-entry / Temporary-to-Formal Boundary"),
    ("WEB-GOV-03", SOURCE / "12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md",
     "WEB-GOV-03-S069", "## 69. Execution Scope Manifest / Dynamic Denominator / Capability Re-entry Control"),
    ("WEB-GOV-04", SOURCE / "12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md",
     "WEB-GOV-04-S083", "## 83. Dynamic Scope / Ownership / Re-entry / Consumer Portability Audit"),
]

def load(p):
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}

def write(p, d):
    p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=180), encoding="utf-8")

def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()

def sha(p):
    return sha_bytes(p.read_bytes())

def run(*args, cwd=ROOT):
    print("+", " ".join(map(str,args)))
    subprocess.run(args, cwd=cwd, check=True)

def binding_hash(uid, document_id, path, heading):
    return sha_bytes(f"{uid}\n{document_id}\n{path}\n{heading}\n".encode())

def normalize_new_mother_headings():
    for document_id, path, uid, desired in MOTHERS:
        text = path.read_text(encoding="utf-8")
        marker = f"<!-- SECTION_UID: {uid} -->"
        idx = text.find(marker)
        if idx < 0:
            raise RuntimeError(f"MISSING_NEW_MOTHER_SECTION:{uid}")
        after = idx + len(marker)
        m = re.match(r"\n(##[^\n]*)", text[after:])
        if not m:
            raise RuntimeError(f"MISSING_SECTION_HEADING:{uid}")
        current = m.group(1)
        if current != desired:
            text = text[:after] + "\n" + desired + text[after+1+len(current):]
            path.write_text(text, encoding="utf-8")

def rebuild_section_registry():
    p = SOURCE / "10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml"
    d = load(p)
    by_doc = {x.get("document_id"): x for x in d.get("documents") or []}
    for document_id, mother, _uid, _desired in MOTHERS:
        doc = by_doc.get(document_id)
        if not doc:
            raise RuntimeError(f"SECTION_REGISTRY_DOCUMENT_MISSING:{document_id}")
        rel = mother.relative_to(SOURCE).as_posix()
        lines = mother.read_text(encoding="utf-8").splitlines()
        sections=[]
        for i,line in enumerate(lines):
            mm = re.fullmatch(r"<!-- SECTION_UID: ([A-Z0-9-]+) -->", line.strip())
            if not mm:
                continue
            if i+1 >= len(lines):
                raise RuntimeError(f"SECTION_HEADING_MISSING_AFTER_ANCHOR:{mm.group(1)}")
            heading=lines[i+1]
            hm2=re.match(r"^##\s+([0-9]+[A-Z]?)\.\s+(.+)$", heading)
            hm3=re.match(r"^###\s+([0-9]+\.[0-9]+)\s+(.+)$", heading)
            hm = hm2 or hm3
            if not hm:
                # Only registered numeric H2/H3 sections belong to this registry.
                continue
            level=2 if hm2 else 3
            uid=mm.group(1)
            number=hm.group(1)
            title=hm.group(2)
            sections.append({
                "section_uid": uid,
                "level": level,
                "canonical_number": number,
                "title": title,
                "heading": heading,
                "path": rel,
                "binding_sha256": binding_hash(uid, document_id, rel, heading),
            })
        if not sections:
            raise RuntimeError(f"NO_REGISTERED_SECTIONS_PARSED:{document_id}")
        doc["path"]=rel
        doc["sections"]=sections
    d["governance_revision"]=SOURCE_REVISION
    write(p,d)

def sync_reference_and_semantic_baseline():
    life_p = SOURCE / "10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml"
    ref_p = SOURCE / "10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml"
    sem_p = SOURCE / "10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml"
    life=load(life_p); ref=load(ref_p); sem=load(sem_p)

    stage_rules=ref.get("stage_reference_rules") or {}
    for stage in life.get("stages") or []:
        uid=stage.get("stage_uid")
        if uid not in stage_rules:
            raise RuntimeError(f"REFERENCE_STAGE_RULE_MISSING:{uid}")
        stage_rules[uid]["exact_required_normative_section_uids"]=list(stage.get("required_normative_section_uids") or [])
    ref["stage_reference_rules"]=stage_rules
    ref["governance_revision"]=SOURCE_REVISION
    write(ref_p,ref)

    # Refresh semantic snapshot only from the registered reference owner. This is an authorized
    # governance-maintenance baseline update, never a candidate self-refresh.
    keys=[
      "program_profile_reference_rules","stage_reference_rules","common_bundle_reference_rules",
      "validator_identities","audit_type_identities","review_type_identities",
      "blueprint_type_identities","normative_document_rules","naming_registry_contract"
    ]
    snap=sem.setdefault("semantic_snapshot",{})
    for key in keys:
        snap[key]=copy.deepcopy(ref.get(key))
    sem["governance_revision"]=SOURCE_REVISION
    tmp=copy.deepcopy(sem); tmp.pop("content_hash",None)
    sem_hash=sha_bytes(yaml.safe_dump(tmp,allow_unicode=True,sort_keys=True,width=180).encode())
    sem["content_hash"]=sem_hash
    write(sem_p,sem)

    val_p=SOURCE/"09_TESTS/governance/validate_reference_semantics.py"
    body=val_p.read_text(encoding="utf-8")
    body2,n=re.subn(r"SEMANTIC_BASELINE_CONTENT_HASH='[0-9a-f]+'",
                    f"SEMANTIC_BASELINE_CONTENT_HASH='{sem_hash}'", body, count=1)
    if n!=1:
        raise RuntimeError("SEMANTIC_HASH_CONSTANT_ANCHOR_DRIFT")
    val_p.write_text(body2,encoding="utf-8")
    return sem_hash

def sync_current_test_evidence_identity():
    p=SOURCE/"11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml"
    d=load(p)
    d["candidate"]="v2.2.5_SCOPE_STAGE_REENTRY_PORTABILITY_HARDENING_CANDIDATE"
    fresh=d.setdefault("fresh_revalidation",{})
    fresh["required"]=True
    fresh["current_source_revision"]=SOURCE_REVISION
    fresh["current_closure_credit"]=False
    fresh["predecessor_evidence_current_closure_credit"]=False
    fresh["embedded_preformal_execution_role"]="HISTORICAL_PREDECESSOR_EVIDENCE_ONLY"
    fresh["predecessor_wrapper_result_role"]="HISTORICAL_PREDECESSOR_EVIDENCE_ONLY"
    fresh["persisted_head_full_line_required"]=True
    fresh["historical_evidence_may_close_successor"]=False
    write(p,d)

def deterministic_hashes():
    cp=SOURCE/"CHECKSUMS.sha256"
    files=sorted((p for p in SOURCE.rglob("*") if p.is_file() and p != cp),
                 key=lambda p:p.relative_to(SOURCE).as_posix())
    if len(files)!=74:
        raise RuntimeError(f"CHECKSUM_TARGET_DENOMINATOR_DRIFT:{len(files)}")
    cp.write_text("".join(f"{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n" for p in files),encoding="utf-8")
    checksum=sha(cp)

    identity_files=sorted(files+[cp], key=lambda p:p.relative_to(SOURCE).as_posix())
    tb=io.BytesIO()
    with tarfile.open(fileobj=tb,mode="w",format=tarfile.PAX_FORMAT) as tf:
        for p in identity_files:
            rel=p.relative_to(SOURCE).as_posix()
            info=tf.gettarinfo(str(p),arcname=rel)
            info.uid=0; info.gid=0; info.uname=""; info.gname=""; info.mtime=0
            with p.open("rb") as fh: tf.addfile(info,fh)
    bundle=sha_bytes(lzma.compress(tb.getvalue(),format=lzma.FORMAT_XZ,preset=9))

    zb=io.BytesIO()
    with zipfile.ZipFile(zb,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for p in identity_files:
            rel=p.relative_to(SOURCE).as_posix()
            zi=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0))
            zi.compress_type=zipfile.ZIP_DEFLATED; zi.create_system=3
            mode=0o755 if (p.stat().st_mode & 0o111) else 0o644
            zi.external_attr=(mode & 0xffff)<<16
            zf.writestr(zi,p.read_bytes())
    zhash=sha_bytes(zb.getvalue())
    return checksum,bundle,zhash

def patch_identity_consumers(checksum,bundle,zhash,sem_hash):
    vp=ROOT/".github/governance-source/VERIFY_SOURCE_IDENTITY.py"
    t=vp.read_text(encoding="utf-8")
    for pattern,value in [
      (r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'",bundle),
      (r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'",zhash),
    ]:
        t,n=re.subn(pattern,lambda m: m.group(0).split("=")[0]+"= '"+value+"'",t,count=1)
        if n!=1: raise RuntimeError(f"IDENTITY_CONSTANT_ANCHOR_DRIFT:{pattern}")
    vp.write_text(t,encoding="utf-8")

    fp=ROOT/".github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py"
    t=fp.read_text(encoding="utf-8")
    repl=[
      (r"EXPECTED_CHECKSUMS_SHA256 = '[0-9a-f]+'",checksum),
      (r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'",zhash),
      (r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'",bundle),
    ]
    for pattern,value in repl:
        t,n=re.subn(pattern,lambda m: m.group(0).split("=")[0]+"= '"+value+"'",t,count=1)
        if n!=1: raise RuntimeError(f"FULLLINE_IDENTITY_CONSTANT_ANCHOR_DRIFT:{pattern}")
    fp.write_text(t,encoding="utf-8")

    for rel in ["governance/specifications/current/SPECIFICATION_MANIFEST.yaml","GOVERNANCE_CURRENT.yaml"]:
        p=ROOT/rel; d=load(p)
        node=d["source_lineage"] if "source_lineage" in d else d["source_identity"]
        node["verified_package_sha256"]=zhash
        node["deterministic_source_bundle_sha256"]=bundle
        node["checksum_manifest_sha256"]=checksum
        node["semantic_authority_content_hash"]=sem_hash
        node["verified_source_revision"]=SOURCE_REVISION
        write(p,d)

    p=ROOT/"governance/test/ACTIVE_STATE.yaml"; d=load(p)
    fl=d.setdefault("full_lifecycle_governance_system_test",{})
    fl["deterministic_source_bundle_sha256"]=bundle
    fl["persisted_head_revalidation_required"]=True
    fl["full_line_github_result"]="REVALIDATION_REQUIRED_AFTER_PROMOTION_ATOMIC_SYNC_REPAIR"
    fl["terminal_run_conclusion"]="REVALIDATION_REQUIRED"
    fl["terminal_result_credit_allowed"]=False
    write(p,d)

def refresh_compiled_and_source():
    run("python",str(SOURCE/"09_TESTS/governance/compile_governance_baseline.py"),cwd=SOURCE/"09_TESTS/governance")
    run("python",str(SOURCE/"09_TESTS/governance/refresh_governance_root_manifest.py"),cwd=SOURCE/"09_TESTS/governance")
    checksum,bundle,zhash=deterministic_hashes()
    return checksum,bundle,zhash

def validate():
    checks=[
      ["python","-m","py_compile",str(SOURCE/"09_TESTS/governance/validate_reference_semantics.py")],
      ["python",str(ROOT/".github/governance-source/VERIFY_SOURCE_IDENTITY.py")],
      ["python",str(ROOT/"governance/ci/governance_resolver.py")],
      ["python",str(SOURCE/"09_TESTS/governance/validate_section_registry.py")],
      ["python",str(SOURCE/"09_TESTS/governance/validate_reference_semantics.py")],
      ["python",str(SOURCE/"09_TESTS/governance/validate_current_test_evidence.py")],
      ["python",str(ROOT/"governance/ci/validate_governance_portability.py")],
      ["python",str(ROOT/"governance/ci/validate_validation_remediation_closure_protocol.py")],
      ["python",str(ROOT/"governance/ci/validate_active_consumer_reference_integrity.py")],
      ["python",str(ROOT/"governance/test/validate_selected_profile_finding_closure.py")],
    ]
    for cmd in checks: run(*cmd)
    run("git","diff","--check")

def main():
    if not AUTH.is_file(): raise RuntimeError("AUTHORIZATION_MISSING")
    auth=load(AUTH)
    if auth.get("status")!="APPROVED_FOR_EXACT_SCOPE" or auth.get("single_use") is not True:
        raise RuntimeError("AUTHORIZATION_INVALID")
    reg=load(ROOT/"governance/specifications/REGISTRY.yaml")
    if (reg.get("active_specification") or {}).get("governance_uid")!=CURRENT_UID:
        raise RuntimeError("CURRENT_GOVERNANCE_DRIFT")

    normalize_new_mother_headings()
    rebuild_section_registry()
    sem_hash=sync_reference_and_semantic_baseline()
    sync_current_test_evidence_identity()
    checksum,bundle,zhash=refresh_compiled_and_source()
    patch_identity_consumers(checksum,bundle,zhash,sem_hash)

    # Root manifest must include final post-refresh source hashes.
    run("python",str(SOURCE/"09_TESTS/governance/refresh_governance_root_manifest.py"),cwd=SOURCE/"09_TESTS/governance")
    checksum,bundle,zhash=deterministic_hashes()
    patch_identity_consumers(checksum,bundle,zhash,sem_hash)

    validate()
    print(json.dumps({
      "governance_uid":CURRENT_UID,
      "source_revision":SOURCE_REVISION,
      "semantic_authority_content_hash":sem_hash,
      "checksum_manifest_sha256":checksum,
      "deterministic_source_bundle_sha256":bundle,
      "deterministic_source_zip_sha256":zhash,
      "product_stage_credit":0,
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
