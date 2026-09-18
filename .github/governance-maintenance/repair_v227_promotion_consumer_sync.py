#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib, io, json, lzma, re, subprocess, tarfile, zipfile
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
AUTH=ROOT/'governance/test/spec_change_authorizations/USR-DIRECTIVE-20260919-PROFILE-TOKEN-PROMOTION-CONSUMER-SYNC-R1.yaml'
CURRENT_UID='GOV-REV-20260919-PROFILE-TOKEN-DECONTAMINATION-HARDENING'
SEM=SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'

def load(p):
    return yaml.safe_load(p.read_text(encoding='utf-8')) or {}

def write(p,d):
    p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()

def run(*a,cwd=ROOT):
    print('+',' '.join(map(str,a)))
    subprocess.run(a,cwd=cwd,check=True)

def sync_semantic_consumers():
    sem=load(SEM)
    current=sem.get('content_hash')
    if not re.fullmatch(r'[0-9a-f]{64}',str(current or '')):
        raise RuntimeError('CURRENT_SEMANTIC_HASH_INVALID')
    patt=re.compile(r"SEMANTIC_BASELINE_CONTENT_HASH\s*=\s*['\"]([0-9a-f]{64})['\"]")
    changed=[]
    stale_before=[]
    for p in sorted(SOURCE.rglob('*.py')):
        text=p.read_text(encoding='utf-8')
        matches=list(patt.finditer(text))
        if not matches:
            continue
        for m in matches:
            if m.group(1)!=current:
                stale_before.append((p.relative_to(SOURCE).as_posix(),m.group(1)))
        new=patt.sub(lambda m: m.group(0).replace(m.group(1),current),text)
        if new!=text:
            p.write_text(new,encoding='utf-8')
            changed.append(p.relative_to(SOURCE).as_posix())
    stale_after=[]
    for p in sorted(SOURCE.rglob('*.py')):
        text=p.read_text(encoding='utf-8')
        for m in patt.finditer(text):
            if m.group(1)!=current:
                stale_after.append((p.relative_to(SOURCE).as_posix(),m.group(1)))
    if stale_after:
        raise RuntimeError('STALE_SEMANTIC_CONSUMERS_REMAIN:'+repr(stale_after))
    if not stale_before:
        raise RuntimeError('EXPECTED_STALE_SEMANTIC_CONSUMER_NOT_REPRODUCED')
    print(json.dumps({'semantic_hash':current,'stale_before':stale_before,'changed':changed,'stale_after':stale_after},indent=2))
    return current,changed

def deterministic_hashes():
    cp=SOURCE/'CHECKSUMS.sha256'
    files=sorted((p for p in SOURCE.rglob('*') if p.is_file() and p!=cp),key=lambda p:p.relative_to(SOURCE).as_posix())
    if len(files)!=74:
        raise RuntimeError(f'CHECKSUM_TARGET_DENOMINATOR_DRIFT:{len(files)}')
    cp.write_text(''.join(f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in files),encoding='utf-8')
    checksum=sha(cp)
    identity=sorted(files+[cp],key=lambda p:p.relative_to(SOURCE).as_posix())
    tb=io.BytesIO()
    with tarfile.open(fileobj=tb,mode='w',format=tarfile.PAX_FORMAT) as tf:
        for p in identity:
            rel=p.relative_to(SOURCE).as_posix()
            info=tf.gettarinfo(str(p),arcname=rel)
            info.uid=0; info.gid=0; info.uname=''; info.gname=''; info.mtime=0
            with p.open('rb') as fh: tf.addfile(info,fh)
    bundle=sha_bytes(lzma.compress(tb.getvalue(),format=lzma.FORMAT_XZ,preset=9))
    zb=io.BytesIO()
    with zipfile.ZipFile(zb,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for p in identity:
            rel=p.relative_to(SOURCE).as_posix()
            zi=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0))
            zi.compress_type=zipfile.ZIP_DEFLATED; zi.create_system=3
            mode=0o755 if (p.stat().st_mode & 0o111) else 0o644
            zi.external_attr=(mode & 0xffff)<<16
            zf.writestr(zi,p.read_bytes())
    return checksum,bundle,sha_bytes(zb.getvalue())

def patch_external_identity(checksum,bundle,zhash,semantic_hash):
    vp=ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py'
    t=vp.read_text(encoding='utf-8')
    repl=[
      (r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'",bundle),
      (r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'",zhash),
    ]
    for pat,val in repl:
        t,n=re.subn(pat,lambda m:m.group(0).split('=')[0]+"= '"+val+"'",t,count=1)
        if n!=1: raise RuntimeError('VERIFY_IDENTITY_ANCHOR_DRIFT:'+pat)
    vp.write_text(t,encoding='utf-8')

    fp=ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'
    t=fp.read_text(encoding='utf-8')
    for pat,val in [
      (r"EXPECTED_CHECKSUMS_SHA256 = '[0-9a-f]+'",checksum),
      (r"EXPECTED_SEMANTIC_CONTENT_HASH = '[0-9a-f]+'",semantic_hash),
      (r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'",zhash),
      (r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'",bundle),
    ]:
        t,n=re.subn(pat,lambda m:m.group(0).split('=')[0]+"= '"+val+"'",t,count=1)
        if n!=1: raise RuntimeError('FULLLINE_IDENTITY_ANCHOR_DRIFT:'+pat)
    fp.write_text(t,encoding='utf-8')

    for rel in ['governance/specifications/current/SPECIFICATION_MANIFEST.yaml','GOVERNANCE_CURRENT.yaml']:
        p=ROOT/rel; d=load(p)
        node=d.get('source_lineage') if 'source_lineage' in d else d.get('source_identity')
        if not isinstance(node,dict): raise RuntimeError('SOURCE_IDENTITY_NODE_MISSING:'+rel)
        node['verified_package_sha256']=zhash
        node['deterministic_source_bundle_sha256']=bundle
        node['checksum_manifest_sha256']=checksum
        node['semantic_authority_content_hash']=semantic_hash
        write(p,d)

    p=ROOT/'governance/test/ACTIVE_STATE.yaml'; d=load(p)
    fl=d.setdefault('full_lifecycle_governance_system_test',{})
    fl['deterministic_source_bundle_sha256']=bundle
    fl['persisted_head_revalidation_required']=True
    fl['full_line_github_result']='REVALIDATION_REQUIRED_AFTER_V227_CONSUMER_SYNC'
    fl['terminal_run_conclusion']='REVALIDATION_REQUIRED'
    fl['terminal_result_credit_allowed']=False
    repair=d.setdefault('v227_promotion_consumer_sync_repair',{})
    repair.update({
      'authorization_uid':'USR-DIRECTIVE-20260919-PROFILE-TOKEN-PROMOTION-CONSUMER-SYNC-R1',
      'current_governance_uid':CURRENT_UID,
      'semantic_authority_content_hash':semantic_hash,
      'stale_semantic_consumer_count_after_repair':0,
      'product_stage_credit':0,
      'status':'DERIVED_CONSUMER_SYNC_REPAIRED_FULL_LINE_REVERIFY_REQUIRED',
    })
    write(p,d)

def validate(semantic_hash):
    run('python','-m','py_compile',str(SOURCE/'09_TESTS/governance/program_artifact_instance_guard.py'))
    run('python',str(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py'))
    run('python',str(ROOT/'governance/ci/governance_resolver.py'))
    run('python',str(ROOT/'governance/ci/validate_governance_portability.py'))
    run('python',str(SOURCE/'09_TESTS/governance/validate_reference_semantics.py'))
    # Reproduce the exact previously failing positive artifact baseline.
    run('python',str(SOURCE/'09_TESTS/governance/test_reference_semantic_guard.py'))
    run('python',str(SOURCE/'09_TESTS/governance/test_execution_load_guard.py'))
    run('python',str(SOURCE/'09_TESTS/governance/test_bugfix_regressions.py'))
    run('git','diff','--check')

def main():
    if not AUTH.is_file(): raise RuntimeError('AUTHORIZATION_MISSING')
    auth=load(AUTH)
    if auth.get('status')!='APPROVED_FOR_EXACT_SCOPE' or auth.get('single_use') is not True:
        raise RuntimeError('AUTHORIZATION_INVALID')
    reg=load(ROOT/'governance/specifications/REGISTRY.yaml')
    if (reg.get('active_specification') or {}).get('governance_uid')!=CURRENT_UID:
        raise RuntimeError('CURRENT_GOVERNANCE_DRIFT')

    semantic_hash,changed=sync_semantic_consumers()
    # Update root-manifest hashes after validator consumer bytes change.
    run('python',str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'),cwd=SOURCE/'09_TESTS/governance')
    checksum,bundle,zhash=deterministic_hashes()
    patch_external_identity(checksum,bundle,zhash,semantic_hash)

    # External-consumer changes do not alter source bytes; re-prove final source identity.
    validate(semantic_hash)
    print(json.dumps({
      'governance_uid':CURRENT_UID,
      'semantic_authority_content_hash':semantic_hash,
      'changed_semantic_consumers':changed,
      'stale_semantic_consumer_count_after_repair':0,
      'checksum_manifest_sha256':checksum,
      'deterministic_source_bundle_sha256':bundle,
      'deterministic_source_zip_sha256':zhash,
      'product_stage_credit':0,
    },ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
