#!/usr/bin/env python3
from pathlib import Path
import hashlib, io, lzma, re, subprocess, tarfile, zipfile, yaml
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
AUTH='USR-DIRECTIVE-20260918-MOTHER-RESIDUAL-CLASSIFICATION-HARDENING-R1'
OLD_UID='GOV-REV-20260918-MOTHER-CONTEXT-TASK-LAYER-HARDENING'
NEW_UID='GOV-REV-20260918-RESIDUAL-CLASSIFICATION-HARDENING'
OLD_SOURCE='v2.2.2-mother-context-task-layer-hardening'
NEW_SOURCE='v2.2.3-residual-classification-hardening'
DISPLAY_VERSION='v2.2.4'
PACKAGE='AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.3_RESIDUAL_CLASSIFICATION_HARDENING_LOCAL_VERIFIED.zip'
HELPER=ROOT/'.github/governance-maintenance/materialize_mother_residual_classification_hardening.py'
WORKFLOW=ROOT/'.github/workflows/mother-residual-classification-hardening.yml'
MOTHER_DIR=SOURCE/'12_DOCS/mother-spec'
S68='''

<!-- SECTION_UID: WEB-GOV-03-S068 -->
## 68. Semantic Residual Classification / Disposition Gate

Before any Current artifact, validator, runner, workflow helper, generated projector, temporary file, backup, intermediate, superseded implementation, or other residual content may be kept, migrated, or deleted, the owning Work Unit MUST classify that residual by content and execution role. Filename age, naming pattern, file count, directory location, historical Stage number, or absence from a partial search MUST_NOT be treated as deletion proof.

Every residual classification MUST evaluate all six dimensions:

1. CANONICAL_OWNER
2. FORWARD_REFERENCE
3. REVERSE_REFERENCE
4. RUNTIME_OR_WORKFLOW_REACHABILITY
5. TEST_REGRESSION_ROLE
6. HISTORICAL_RETENTION_ROLE

The legal disposition vocabulary is closed:

- CURRENT_REQUIRED -> KEEP_ACTIVE
- HISTORICAL_PROVENANCE -> KEEP_NON_CURRENT
- NEGATIVE_REGRESSION_PATTERN -> KEEP_AS_NON_CURRENT_TEST_OR_SIGNATURE
- SUPERSEDED_ACTIVE_CONTENT -> REMOVE_OR_MIGRATE
- DEAD_OR_UNREFERENCED_ACTIVE_CONTENT -> REMOVE
- TEMP_BACKUP_INTERMEDIATE -> REMOVE
- UNKNOWN -> BLOCK

UNKNOWN is fail-closed. AI MUST_NOT silently convert uncertainty into REMOVE, KEEP, SATISFIED, or product completion.

For executable/validator/runner cleanup, deletion additionally requires proof that the candidate is not an active direct or transitive workflow consumer, not a Current registry/projector/owner target, not required by Current Authority materialization, not the sole preserved negative-regression signature for a known defect, and not required historical provenance. A validator MAY remain even when its former producer is gone when it directly protects a Current invariant or negative-regression signature.

A removable cohort SHOULD be mutated atomically when the files share one proven disposition and dependency closure. The transaction MUST preserve required Authority machinery, Current owners, Current projectors, historical provenance, and required regression signatures; then run post-delete reference/residual scans and exact-head terminal validation under the applicable gates.

This section classifies residuals before WEB-GOV-03-S053 and WEB-GOV-03-S055 perform supersession/delete operations. It does not replace those owners.

Governance residual cleanup is governed by WEB-GOV-03-S066 and receives zero product-stage gap reduction or completion credit unless separate fresh product-owner evidence independently changes a product denominator.
'''
S82='''

<!-- SECTION_UID: WEB-GOV-04-S082 -->
## 82. Semantic Residual Classification / Cleanup Cohort Audit

Audit MUST verify that every residual keep/migrate/delete decision has evidence for all six WEB-GOV-03-S068 classification dimensions: Canonical Owner, forward reference, reverse reference, runtime/workflow reachability, test-regression role, and historical-retention role.

Audit MUST reject deletion justified only by filename, version-looking name, directory location, file age, builder disappearance, missing output, file-count reduction, or a partial direct-reference scan.

For each removed executable/validator/runner cohort, Audit MUST prove:

- no active direct or transitive workflow/runtime consumer remains;
- no Current registry, projector, Canonical Owner, Authority materializer, or required evidence owner resolves to the removed content;
- required negative-regression signatures and historical provenance remain available in their legal non-current role;
- every removed item has a non-UNKNOWN disposition;
- Authority-critical machinery excluded from the cohort remains present;
- post-delete stale Current reference, broken reference, superseded active content, and unjustified residual counts are zero;
- the exact persisted head/tree receives the required outer terminal validation result.

A cleanup cohort PASS is governance-maintenance evidence only. Audit MUST_NOT convert it into product-stage gap reduction, product completion, Stage exit, or Authority satisfaction.

This audit extends WEB-GOV-04-S022A and WEB-GOV-04-S065; it does not replace their denominators.
'''
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def write(p,d): p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=160),encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(*a,cwd=ROOT):
    print('+',' '.join(map(str,a))); subprocess.run(a,cwd=cwd,check=True)
def binding(uid,doc,path,heading):
    return hashlib.sha256(f'{uid}\n{doc}\n{path}\n{heading}\n'.encode()).hexdigest()
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
            rel=p.relative_to(SOURCE).as_posix()
            zi=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0)); zi.compress_type=zipfile.ZIP_DEFLATED; zi.create_system=3
            mode=0o755 if (p.stat().st_mode & 0o111) else 0o644; zi.external_attr=(mode & 0xFFFF)<<16
            zf.writestr(zi,p.read_bytes())
    return bundle,hashlib.sha256(zb.getvalue()).hexdigest()

for fn in ['01_BLUEPRINT_DESIGN_GOVERNANCE.md','02_IMPLEMENTATION_DELIVERY_STANDARD.md','03_EXECUTION_CONTROL_STANDARD.md','04_AUDIT_PROGRESS_STANDARD.md']:
    p=MOTHER_DIR/fn; t=p.read_text(encoding='utf-8')
    if 'version: 2.2.2' not in t: raise SystemExit('MOTHER_VERSION_DRIFT:'+fn)
    p.write_text(t.replace('version: 2.2.2','version: 2.2.3',1),encoding='utf-8')
p3=MOTHER_DIR/'03_EXECUTION_CONTROL_STANDARD.md'; t3=p3.read_text(encoding='utf-8')
if 'WEB-GOV-03-S068' in t3: raise SystemExit('S068_ALREADY_EXISTS')
p3.write_text((t3.rstrip()+S68).rstrip()+'\n',encoding='utf-8')
p4=MOTHER_DIR/'04_AUDIT_PROGRESS_STANDARD.md'; t4=p4.read_text(encoding='utf-8')
if 'WEB-GOV-04-S082' in t4: raise SystemExit('S082_ALREADY_EXISTS')
p4.write_text((t4.rstrip()+S82).rstrip()+'\n',encoding='utf-8')

sp=SOURCE/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'; sd=load(sp); sd['governance_revision']=NEW_SOURCE
docs={x['document_id']:x for x in sd['documents']}
for doc,uid,num,title in [('WEB-GOV-03','WEB-GOV-03-S068','68','Semantic Residual Classification / Disposition Gate'),('WEB-GOV-04','WEB-GOV-04-S082','82','Semantic Residual Classification / Cleanup Cohort Audit')]:
    d=docs[doc]; rel=d['path']; heading=f'## {num}. {title}'
    if any(x.get('section_uid')==uid for x in d.get('sections') or []): raise SystemExit('SECTION_DUPLICATE:'+uid)
    d.setdefault('sections',[]).append({'section_uid':uid,'level':2,'canonical_number':num,'title':title,'heading':heading,'path':rel,'binding_sha256':binding(uid,doc,rel,heading)})
write(sp,sd)
for p in sorted((SOURCE/'10_REGISTRY').glob('*.yaml')):
    d=load(p)
    if d.get('governance_revision')==OLD_SOURCE:
        d['governance_revision']=NEW_SOURCE; write(p,d)
for p in sorted((SOURCE/'10_REGISTRY').glob('*.yaml')):
    if load(p).get('governance_revision')==OLD_SOURCE: raise SystemExit('STALE_CURRENT_PROJECTOR:'+p.as_posix())
candp=SOURCE/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'; cand=load(candp)
cand['candidate']='v2.2.3_RESIDUAL_CLASSIFICATION_HARDENING_CANDIDATE'
cand.setdefault('fresh_revalidation',{})['current_source_revision']=NEW_SOURCE
write(candp,cand)

mg=SOURCE/'09_TESTS/governance/governance_management_contract_guard.py'; mt=mg.read_text(encoding='utf-8')
needle="    for token in required_m4:\n        if token not in m4: failures.append('mother_context_task_layer_audit_missing:WEB-GOV-04:'+token)\n"
insert=needle+"    residual_m3=['WEB-GOV-03-S068','CANONICAL_OWNER','FORWARD_REFERENCE','REVERSE_REFERENCE','RUNTIME_OR_WORKFLOW_REACHABILITY','TEST_REGRESSION_ROLE','HISTORICAL_RETENTION_ROLE','NEGATIVE_REGRESSION_PATTERN -> KEEP_AS_NON_CURRENT_TEST_OR_SIGNATURE','DEAD_OR_UNREFERENCED_ACTIVE_CONTENT -> REMOVE','UNKNOWN -> BLOCK']\n    residual_m4=['WEB-GOV-04-S082','partial direct-reference scan','active direct or transitive workflow/runtime consumer','negative-regression signatures','exact persisted head/tree','governance-maintenance evidence only']\n    for token in residual_m3:\n        if token not in m3: failures.append('mother_residual_classification_rule_missing:WEB-GOV-03:'+token)\n    for token in residual_m4:\n        if token not in m4: failures.append('mother_residual_classification_audit_missing:WEB-GOV-04:'+token)\n"
if needle not in mt: raise SystemExit('MANAGEMENT_GUARD_PATCH_TARGET_DRIFT')
mg.write_text(mt.replace(needle,insert,1),encoding='utf-8')

cp=ROOT/'governance/specifications/current/VALIDATION_REMEDIATION_CLOSURE_PROTOCOL.yaml'; cd=load(cp)
cd.setdefault('residual_classification',{})['mother_policy_refs']=['WEB-GOV-03-S068','WEB-GOV-04-S082']
write(cp,cd)

run('python',str(SOURCE/'09_TESTS/governance/compile_governance_baseline.py'),cwd=SOURCE/'09_TESTS/governance')
rmp=SOURCE/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'; rm=load(rmp); rm['governance_revision']=NEW_SOURCE; write(rmp,rm)
run('python',str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'),cwd=SOURCE/'09_TESTS/governance')
checks=SOURCE/'CHECKSUMS.sha256'; files=sorted(p for p in SOURCE.rglob('*') if p.is_file() and p!=checks)
if len(files)!=74: raise SystemExit(f'CHECKSUM_TARGET_DENOMINATOR_DRIFT:{len(files)}')
checks.write_text(''.join(f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in files),encoding='utf-8')
checksum_sha=sha(checks); bundle_sha,zip_sha=deterministic()
vp=ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py'; vt=vp.read_text(encoding='utf-8')
vt=re.sub(r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'",f"EXPECTED_BUNDLE_SHA256 = '{bundle_sha}'",vt,count=1)
vt=re.sub(r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'",f"EXPECTED_SOURCE_ZIP_SHA256 = '{zip_sha}'",vt,count=1); vp.write_text(vt,encoding='utf-8')
fp=ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'; ft=fp.read_text(encoding='utf-8')
ft=re.sub(r"EXPECTED_CHECKSUMS_SHA256 = '[0-9a-f]+'",f"EXPECTED_CHECKSUMS_SHA256 = '{checksum_sha}'",ft,count=1)
ft=re.sub(r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'",f"EXPECTED_SOURCE_ZIP_SHA256 = '{zip_sha}'",ft,count=1)
ft=re.sub(r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'",f"EXPECTED_BUNDLE_SHA256 = '{bundle_sha}'",ft,count=1); fp.write_text(ft,encoding='utf-8')

regp=ROOT/'governance/specifications/REGISTRY.yaml'; reg=load(regp)
if reg['active_specification']['governance_uid']!=OLD_UID: raise SystemExit('CURRENT_UID_DRIFT')
old_display=reg['active_specification']['display_version']
reg['immediate_predecessor']={'governance_uid':OLD_UID,'display_version':old_display,'version_role':'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY','status':'SUPERSEDED_HISTORY_ONLY_AFTER_RESIDUAL_CLASSIFICATION_HARDENING'}
reg['active_specification']['governance_uid']=NEW_UID; reg['active_specification']['display_version']=DISPLAY_VERSION
if 'residual-classification-hardening' not in reg['active_specification'].setdefault('aliases',[]): reg['active_specification']['aliases'].append('residual-classification-hardening')
write(regp,reg)

mp=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'; m=load(mp)
m['artifact_uid']=NEW_UID; m['display_version']=DISPLAY_VERSION
sl=m['source_lineage']; sl['predecessor_governance_uid']=OLD_UID; sl['promotion_authorization_uid']=AUTH; sl['verified_package_filename']=PACKAGE; sl['verified_package_sha256']=zip_sha; sl['deterministic_source_bundle_sha256']=bundle_sha; sl['checksum_manifest_sha256']=checksum_sha; sl['verified_source_revision']=NEW_SOURCE
m.setdefault('closure_policy',{})['mother_semantic_residual_classification_required']=True
write(mp,m)

gp=ROOT/'GOVERNANCE_CURRENT.yaml'; g=load(gp); g['active_governance_uid']=NEW_UID; g['display_version']=DISPLAY_VERSION
si=g['source_identity']; si['verified_package_sha256']=zip_sha; si['deterministic_source_bundle_sha256']=bundle_sha; si['checksum_manifest_sha256']=checksum_sha; si['verified_source_revision']=NEW_SOURCE
write(gp,g)

ap=ROOT/'governance/test/ACTIVE_STATE.yaml'; a=load(ap); a['specification_uid']=NEW_UID
a.setdefault('stage_execution_remediation_closure_protocol',{})['frozen_specification_uid']=NEW_UID
tr=a.setdefault('governance_revision_transition',{}); tr['predecessor_governance_uid']=OLD_UID; tr['current_governance_uid']=NEW_UID; tr['fresh_revalidation_required']=True
a['current_primary_task_layer']='GOVERNANCE_MAINTENANCE'; a['current_primary_task_authorization_uid']=AUTH; a['current_primary_task_product_stage_credit']=0
res=a.setdefault('resume_control',{}); res['current_resume_point']='GOVERNANCE_MAINTENANCE_RESIDUAL_CLASSIFICATION_HARDENING_REVALIDATION'; res['exact_next_action']='REVALIDATE_RESIDUAL_CLASSIFICATION_MOTHER_SUCCESSOR_ON_EXACT_PERSISTED_HEAD; THEN_RESUME_R26_R38_SEMANTIC_RESIDUAL_CLASSIFICATION'
fl=a.setdefault('full_lifecycle_governance_system_test',{}); fl['deterministic_source_bundle_sha256']=bundle_sha; fl['persisted_head_revalidation_required']=True; fl['full_line_github_result']='REVALIDATION_REQUIRED_AFTER_RESIDUAL_CLASSIFICATION_MOTHER_SUCCESSOR'; fl['terminal_run_conclusion']='REVALIDATION_REQUIRED'; fl['terminal_result_credit_allowed']=False
write(ap,a)

print('CHECKSUM_SHA',checksum_sha); print('BUNDLE_SHA',bundle_sha); print('ZIP_SHA',zip_sha)
run('python',str(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py'))
run('python',str(SOURCE/'09_TESTS/governance/validate_section_registry.py'),cwd=SOURCE)
run('python',str(SOURCE/'09_TESTS/governance/governance_management_contract_guard.py'),cwd=SOURCE)
run('python',str(ROOT/'governance/ci/validate_governance_portability.py'))
run('python',str(ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'))
HELPER.unlink(); WORKFLOW.unlink()
run('git','diff','--check')
