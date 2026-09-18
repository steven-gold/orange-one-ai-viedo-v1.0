#!/usr/bin/env python3
from pathlib import Path
import hashlib, io, lzma, re, subprocess, tarfile, zipfile, yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
AUTH='USR-DIRECTIVE-20260918-DESIGN-REMEDIATION-SUCCESSOR-PROJECTOR-SYNC-R5'
CURRENT_UID='GOV-REV-20260918-DESIGN-REMEDIATION-ROUTING-HARDENING'
SOURCE_REVISION='v2.2.4-design-remediation-routing-hardening'
CANDIDATE='v2.2.4_DESIGN_REMEDIATION_ROUTING_HARDENING_CANDIDATE'
HELPER=ROOT/'.github/governance-maintenance/sync_design_remediation_successor_projectors.py'
WORKFLOW=ROOT/'.github/workflows/design-remediation-successor-projector-sync.yml'

def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def write(p,d): p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(*a,cwd=ROOT): print('+',' '.join(map(str,a))); subprocess.run(a,cwd=cwd,check=True)

def deterministic():
    files=sorted((p for p in SOURCE.rglob('*') if p.is_file()),key=lambda p:p.relative_to(SOURCE).as_posix())
    tb=io.BytesIO()
    with tarfile.open(fileobj=tb,mode='w',format=tarfile.PAX_FORMAT) as tf:
        for p in files:
            rel=p.relative_to(SOURCE).as_posix(); info=tf.gettarinfo(str(p),arcname=rel)
            info.uid=0; info.gid=0; info.uname=''; info.gname=''; info.mtime=0
            with p.open('rb') as fh: tf.addfile(info,fh)
    bundle=hashlib.sha256(lzma.compress(tb.getvalue(),format=lzma.FORMAT_XZ,preset=9)).hexdigest()
    zb=io.BytesIO()
    with zipfile.ZipFile(zb,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for p in files:
            rel=p.relative_to(SOURCE).as_posix(); zi=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0))
            zi.compress_type=zipfile.ZIP_DEFLATED; zi.create_system=3
            mode=0o755 if (p.stat().st_mode & 0o111) else 0o644; zi.external_attr=(mode & 0xffff)<<16
            zf.writestr(zi,p.read_bytes())
    return bundle,hashlib.sha256(zb.getvalue()).hexdigest()

def main():
    reg=load(ROOT/'governance/specifications/REGISTRY.yaml')
    if (reg.get('active_specification') or {}).get('governance_uid')!=CURRENT_UID:
        raise SystemExit('CURRENT_GOVERNANCE_UID_DRIFT')
    candp=SOURCE/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'
    cand=load(candp)
    cand['candidate']=CANDIDATE
    fresh=cand.setdefault('fresh_revalidation',{})
    fresh['required']=True
    fresh['current_source_revision']=SOURCE_REVISION
    fresh['current_closure_credit']=False
    fresh['predecessor_evidence_current_closure_credit']=False
    fresh['persisted_head_full_line_required']=True
    fresh['historical_evidence_may_close_successor']=False
    write(candp,cand)

    run('python',str(SOURCE/'09_TESTS/governance/compile_governance_baseline.py'),cwd=SOURCE/'09_TESTS/governance')
    run('python',str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'),cwd=SOURCE/'09_TESTS/governance')
    cp=SOURCE/'CHECKSUMS.sha256'
    fs=sorted(p for p in SOURCE.rglob('*') if p.is_file() and p!=cp)
    if len(fs)!=74: raise SystemExit(f'CHECKSUM_TARGET_DENOMINATOR_DRIFT:{len(fs)}')
    cp.write_text(''.join(f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in fs),encoding='utf-8')
    checksum=sha(cp); bundle,zips=deterministic()

    vp=ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py'
    v=vp.read_text(encoding='utf-8')
    v=re.sub(r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'",f"EXPECTED_BUNDLE_SHA256 = '{bundle}'",v,count=1)
    v=re.sub(r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'",f"EXPECTED_SOURCE_ZIP_SHA256 = '{zips}'",v,count=1)
    vp.write_text(v,encoding='utf-8')
    fp=ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'
    f=fp.read_text(encoding='utf-8')
    f=re.sub(r"EXPECTED_CHECKSUMS_SHA256 = '[0-9a-f]+'",f"EXPECTED_CHECKSUMS_SHA256 = '{checksum}'",f,count=1)
    f=re.sub(r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'",f"EXPECTED_SOURCE_ZIP_SHA256 = '{zips}'",f,count=1)
    f=re.sub(r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'",f"EXPECTED_BUNDLE_SHA256 = '{bundle}'",f,count=1)
    fp.write_text(f,encoding='utf-8')

    mp=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'
    m=load(mp); sl=m['source_lineage']
    sl['verified_package_sha256']=zips
    sl['deterministic_source_bundle_sha256']=bundle
    sl['checksum_manifest_sha256']=checksum
    sl['verified_source_revision']=SOURCE_REVISION
    sl['post_promotion_projector_sync_authorization_uid']=AUTH
    write(mp,m)

    gp=ROOT/'GOVERNANCE_CURRENT.yaml'
    g=load(gp); si=g['source_identity']
    si['verified_package_sha256']=zips
    si['deterministic_source_bundle_sha256']=bundle
    si['checksum_manifest_sha256']=checksum
    si['verified_source_revision']=SOURCE_REVISION
    write(gp,g)

    ap=ROOT/'governance/test/ACTIVE_STATE.yaml'
    a=load(ap)
    a['current_primary_task_layer']='GOVERNANCE_MAINTENANCE'
    a['current_primary_task_authorization_uid']=AUTH
    a['current_primary_task_product_stage_credit']=0
    fl=a.setdefault('full_lifecycle_governance_system_test',{})
    fl['deterministic_source_bundle_sha256']=bundle
    fl['persisted_head_revalidation_required']=True
    fl['full_line_github_result']='REVALIDATION_REQUIRED_AFTER_SUCCESSOR_PROJECTOR_SYNC'
    fl['terminal_run_conclusion']='REVALIDATION_REQUIRED'
    fl['terminal_result_credit_allowed']=False
    rc=a.setdefault('resume_control',{})
    rc['current_resume_point']='GOVERNANCE_MAINTENANCE_SUCCESSOR_PROJECTOR_SYNC_REVALIDATION'
    rc['exact_next_action']='REVALIDATE_SUCCESSOR_PROJECTOR_SYNC_ON_EXACT_PERSISTED_HEAD_THEN_RESOLVE_FRESH_CORE01_STAGE02_WORK_UNIT'
    write(ap,a)

    run('python',str(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py'))
    run('python',str(SOURCE/'09_TESTS/governance/validate_current_test_evidence.py'),cwd=SOURCE)
    run('python',str(ROOT/'governance/ci/validate_governance_portability.py'))
    run('python',str(ROOT/'governance/ci/validate_validation_remediation_closure_protocol.py'))
    run('python',str(ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'))

    for rel in ['.github/governance-source/SOURCE_IDENTITY_REPORT.json','governance/test/ACTIVE_CONSUMER_REFERENCE_INTEGRITY_REPORT.json','governance/test/FINDING_CLOSURE_READINESS.json']:
        p=ROOT/rel
        if p.exists(): run('git','checkout','--',rel)
    if HELPER.exists(): HELPER.unlink()
    if WORKFLOW.exists(): WORKFLOW.unlink()
    run('git','diff','--check')
    print('CHECKSUM_SHA',checksum); print('BUNDLE_SHA',bundle); print('ZIP_SHA',zips)

if __name__=='__main__': main()
