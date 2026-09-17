#!/usr/bin/env python3
from pathlib import Path
import hashlib, io, lzma, re, subprocess, tarfile, zipfile, yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
OLD='v2.2.1-full-line-source-integrity'
TARGET='v2.2.2-mother-context-task-layer-hardening'
AUTH='USR-DIRECTIVE-20260918-MOTHER-SUCCESSOR-PROJECTOR-SYNC-R6'
HELPER=ROOT/'.github/governance-maintenance/materialize_mother_successor_projector_sync_r5.py'
WORKFLOW=ROOT/'.github/workflows/mother-successor-projector-sync-r5.yml'

def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def write(p,d): p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=160),encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(*a,cwd=ROOT):
    print('+',' '.join(map(str,a))); subprocess.run(a,cwd=cwd,check=True)

def deterministic(source):
    files=sorted((p for p in source.rglob('*') if p.is_file()),key=lambda p:p.relative_to(source).as_posix())
    tb=io.BytesIO()
    with tarfile.open(fileobj=tb,mode='w',format=tarfile.PAX_FORMAT) as tf:
        for p in files:
            rel=p.relative_to(source).as_posix(); info=tf.gettarinfo(str(p),arcname=rel)
            info.uid=0; info.gid=0; info.uname=''; info.gname=''; info.mtime=0
            with p.open('rb') as fh: tf.addfile(info,fh)
    bundle=hashlib.sha256(lzma.compress(tb.getvalue(),format=lzma.FORMAT_XZ,preset=9)).hexdigest()
    zb=io.BytesIO()
    with zipfile.ZipFile(zb,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for p in files:
            rel=p.relative_to(source).as_posix()
            zi=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0)); zi.compress_type=zipfile.ZIP_DEFLATED; zi.create_system=3
            mode=0o755 if (p.stat().st_mode & 0o111) else 0o644; zi.external_attr=(mode & 0xFFFF)<<16
            zf.writestr(zi,p.read_bytes())
    return bundle,hashlib.sha256(zb.getvalue()).hexdigest()

# Synchronize every Current registry projector still pinned to predecessor source revision.
changed=[]
for p in sorted((SOURCE/'10_REGISTRY').glob('*.yaml')):
    d=load(p)
    if d.get('governance_revision')==OLD:
        d['governance_revision']=TARGET; write(p,d); changed.append(p.relative_to(SOURCE).as_posix())
# Immutable semantic baseline intentionally remains its own historical/provenance revision.
for p in sorted((SOURCE/'10_REGISTRY').glob('*.yaml')):
    d=load(p)
    if d.get('governance_revision')==OLD:
        raise SystemExit('STALE_CURRENT_REGISTRY_PROJECTOR:'+p.as_posix())

candp=SOURCE/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'
cand=load(candp)
if cand.get('candidate')=='v2.2.1_FULL_LINE_SOURCE_INTEGRITY_CANDIDATE':
    cand['candidate']='v2.2.2_MOTHER_CONTEXT_TASK_LAYER_HARDENING_CANDIDATE'
fresh=cand.setdefault('fresh_revalidation',{})
if fresh.get('current_source_revision')==OLD: fresh['current_source_revision']=TARGET
write(candp,cand)

# Rebuild derived source state and hashes.
run('python',str(SOURCE/'09_TESTS/governance/compile_governance_baseline.py'),cwd=SOURCE/'09_TESTS/governance')
run('python',str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'),cwd=SOURCE/'09_TESTS/governance')
cp=SOURCE/'CHECKSUMS.sha256'
files=sorted(p for p in SOURCE.rglob('*') if p.is_file() and p!=cp)
if len(files)!=74: raise SystemExit(f'CHECKSUM_TARGET_DENOMINATOR_DRIFT:{len(files)}')
cp.write_text(''.join(f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in files),encoding='utf-8')
checksum_sha=sha(cp); bundle_sha,zip_sha=deterministic(SOURCE)

# Refresh external source identity anchors.
vp=ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py'
v=vp.read_text(encoding='utf-8')
v=re.sub(r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'",f"EXPECTED_BUNDLE_SHA256 = '{bundle_sha}'",v,count=1)
v=re.sub(r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'",f"EXPECTED_SOURCE_ZIP_SHA256 = '{zip_sha}'",v,count=1)
vp.write_text(v,encoding='utf-8')
fp=ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'
f=fp.read_text(encoding='utf-8')
f=re.sub(r"EXPECTED_CHECKSUMS_SHA256 = '[0-9a-f]+'",f"EXPECTED_CHECKSUMS_SHA256 = '{checksum_sha}'",f,count=1)
f=re.sub(r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'",f"EXPECTED_SOURCE_ZIP_SHA256 = '{zip_sha}'",f,count=1)
f=re.sub(r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'",f"EXPECTED_BUNDLE_SHA256 = '{bundle_sha}'",f,count=1)
fp.write_text(f,encoding='utf-8')

# Refresh Current identity projectors without changing Current governance UID/version.
mp=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'
m=load(mp); sl=m['source_lineage']; sl['verified_package_sha256']=zip_sha; sl['deterministic_source_bundle_sha256']=bundle_sha; sl['checksum_manifest_sha256']=checksum_sha
sl['verified_source_revision']=TARGET; sl['post_promotion_projector_sync_authorization_uid']=AUTH; write(mp,m)
gp=ROOT/'GOVERNANCE_CURRENT.yaml'
g=load(gp); si=g['source_identity']; si['verified_package_sha256']=zip_sha; si['deterministic_source_bundle_sha256']=bundle_sha; si['checksum_manifest_sha256']=checksum_sha; si['verified_source_revision']=TARGET; write(gp,g)

ap=ROOT/'governance/test/ACTIVE_STATE.yaml'
a=load(ap)
a['current_primary_task_layer']='GOVERNANCE_MAINTENANCE'
a['current_primary_task_authorization_uid']=AUTH
a['current_primary_task_product_stage_credit']=0
rc=a.setdefault('resume_control',{})
rc['current_resume_point']='GOVERNANCE_MAINTENANCE_MOTHER_SUCCESSOR_FULL_LINE_REVALIDATION'
rc['exact_next_action']='REVALIDATE_MOTHER_SUCCESSOR_PROJECTOR_SYNC_ON_EXACT_PERSISTED_HEAD; DO NOT ENTER PRODUCT_STAGE'
fl=a.setdefault('full_lifecycle_governance_system_test',{})
fl['deterministic_source_bundle_sha256']=bundle_sha
fl['persisted_head_revalidation_required']=True
fl['full_line_github_result']='REVALIDATION_REQUIRED_AFTER_MOTHER_SUCCESSOR_PROJECTOR_SYNC'
fl['terminal_run_conclusion']='REVALIDATION_REQUIRED'
fl['terminal_result_credit_allowed']=False
write(ap,a)

print('CURRENT_PROJECTORS_SYNCHRONIZED',len(changed),changed)
print('CHECKSUM_SHA',checksum_sha); print('BUNDLE_SHA',bundle_sha); print('ZIP_SHA',zip_sha)

# Exact targeted checks plus the complete 75-file local lifecycle gate.
run('python',str(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py'))
for rel in [
 '09_TESTS/governance/validate_section_registry.py',
 '09_TESTS/governance/governance_management_contract_guard.py',
 '09_TESTS/governance/validate_stage_execution_invariants.py',
 '09_TESTS/governance/validate_test_feedback_spec_evolution.py']:
    run('python',str(SOURCE/rel),cwd=SOURCE)
run('python',str(ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'))

# One-time transaction machinery must not survive the repair commit.
HELPER.unlink(); WORKFLOW.unlink()
run('git','diff','--check')
