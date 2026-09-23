#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, io, json, lzma, os, re, subprocess, sys, tarfile, zipfile
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
OLD_UID='GOV-REV-20260923-WORD-CONTENT-BINARY-SOURCE-PROJECTION-HARDENING'
NEW_UID='GOV-REV-20260923-WORD-PROJECTION-NEXTSTEP-CONSUMER-SYNC-HARDENING'
OLD_DISPLAY='v2.2.21'
NEW_DISPLAY='v2.2.22'
NEW_REV='v2.2.22-word-projection-nextstep-consumer-sync-hardening'
AUTH_UID='USR-DIRECTIVE-20260923-WORD-PROJECTION-NEXTSTEP-CONSUMER-SYNC-R5'
WORK_UNIT='WU-GOV-WORD-PROJECTION-NEXTSTEP-CONSUMER-SYNC-001'
NEW_PACKAGE='AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.22_WORD_PROJECTION_NEXTSTEP_CONSUMER_SYNC_HARDENING_LOCAL_VERIFIED.zip'

def run(*args,check=True,env=None):
    cp=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,env=env)
    if check and cp.returncode:
        print(cp.stdout)
        print(cp.stderr,file=sys.stderr)
        raise SystemExit(cp.returncode)
    return cp

def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def dump(p,d): Path(p).write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=220),encoding='utf-8')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hobj(d):
    x=copy.deepcopy(d); x.pop('content_hash',None)
    return hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True,width=220).encode()).hexdigest()
def unique_extend(lst,items):
    for x in items:
        if x not in lst: lst.append(x)
def replace_const(path,name,value):
    p=Path(path); s=p.read_text(encoding='utf-8')
    pat=re.compile(r"(?m)^"+re.escape(name)+r"\s*=\s*'[^']*'$")
    ns,n=pat.subn(f"{name} = '{value}'",s,1)
    if n!=1: raise RuntimeError(f'constant replacement {name} count={n} path={path}')
    p.write_text(ns,encoding='utf-8')

def mutate_guard_and_test():
    p=SOURCE/'09_TESTS/governance/governance_stage1_pipeline_guard.py'
    s=p.read_text(encoding='utf-8')
    if 'def _raw_capture_contract(package_root:Path):' not in s:
        anchor="def _projection_contract(package_root:Path):\n    reg=load_yaml(package_root/PROJECTION_CONTRACT_REL)\n    return reg.get('structured_document_source_projection_contract') or {}\n"
        add=anchor+"\ndef _raw_capture_contract(package_root:Path):\n    reg=load_yaml(package_root/PROJECTION_CONTRACT_REL)\n    return reg.get('raw_source_capture_contract') or {}\n"
        if anchor not in s: raise RuntimeError('projection contract helper anchor missing')
        s=s.replace(anchor,add,1)
    old="""        _pr=_projection_required_records(rawcap)
        _expected_next='CANONICAL_SOURCE_PROJECTION' if _pr else 'SOURCE_STRUCTURE_ENUMERATION'
        if capstate.get('next_step')!=_expected_next: failures.append('raw_source_capture_next_step_mismatch:'+str(capstate.get('next_step'))+':expected='+_expected_next)
"""
    new="""        _pr=_projection_required_records(rawcap)
        _rcc=_raw_capture_contract(package_root)
        _expected_next=(_rcc.get('structured_document_exact_next_step') if _pr else _rcc.get('default_exact_next_step')) or ('CANONICAL_SOURCE_PROJECTION' if _pr else 'SOURCE_STRUCTURE_ENUMERATION')
        if capstate.get('next_step')!=_expected_next: failures.append('raw_source_capture_next_step_mismatch:'+str(capstate.get('next_step'))+':expected='+str(_expected_next))
"""
    if old not in s: raise RuntimeError('legacy next-step consumer block missing')
    s=s.replace(old,new,1)
    p.write_text(s,encoding='utf-8')

    p=SOURCE/'09_TESTS/governance/test_stage1_source_to_blueprint_minimal_control.py'
    s=p.read_text(encoding='utf-8')
    old="capstate={'run_uid':'PROJ1','state':'CAPTURE_CLOSED','next_step':'CANONICAL_SOURCE_PROJECTION','recapture_allowed':False}"
    new="capstate={'run_uid':'PROJ1','state':'CAPTURE_CLOSED','next_step':'SOURCE_DOCUMENT_CONTENT_AUDIT','recapture_allowed':False}"
    if old not in s: raise RuntimeError('projection fixture legacy next step missing')
    s=s.replace(old,new,1)
    marker="c('projection_content_readiness_audit_required',_prun(_p_content_audit_missing),'FAIL')\n"
    if "projection_legacy_next_step_drift_blocked" not in s:
        add=marker+"""def _p_legacy_projection_next_step(r,rawcap,capstate,f): capstate['next_step']='CANONICAL_SOURCE_PROJECTION'
c('projection_legacy_next_step_drift_blocked',_prun(_p_legacy_projection_next_step),'FAIL')
"""
        if marker not in s: raise RuntimeError('projection content audit case anchor missing')
        s=s.replace(marker,add,1)
    p.write_text(s,encoding='utf-8')

def source_checksums_and_archives():
    checks=SOURCE/'CHECKSUMS.sha256'
    files=sorted([p for p in SOURCE.rglob('*') if p.is_file() and p!=checks],key=lambda p:p.relative_to(SOURCE).as_posix())
    checks.write_text(''.join(f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in files),encoding='utf-8')
    allfiles=sorted([p for p in SOURCE.rglob('*') if p.is_file()],key=lambda p:p.relative_to(SOURCE).as_posix())
    if len(allfiles)!=75: raise RuntimeError(f'source file count changed:{len(allfiles)}')
    tb=io.BytesIO()
    with tarfile.open(fileobj=tb,mode='w',format=tarfile.PAX_FORMAT) as tf:
        for p in allfiles:
            rel=p.relative_to(SOURCE).as_posix(); info=tf.gettarinfo(str(p),arcname=rel)
            info.uid=0;info.gid=0;info.uname='';info.gname='';info.mtime=0
            with p.open('rb') as fh: tf.addfile(info,fh)
    bundle=lzma.compress(tb.getvalue(),format=lzma.FORMAT_XZ,preset=9)
    zb=io.BytesIO()
    with zipfile.ZipFile(zb,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for p in allfiles:
            rel=p.relative_to(SOURCE).as_posix(); zi=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED;zi.create_system=3
            mode=493 if p.stat().st_mode&73 else 420;zi.external_attr=(mode&65535)<<16
            zf.writestr(zi,p.read_bytes())
    return sha(checks),hashlib.sha256(bundle).hexdigest(),hashlib.sha256(zb.getvalue()).hexdigest()

def refresh_source():
    for rel in ['10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml','10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml','10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml','10_REGISTRY/BLUEPRINT_REGISTRY.yaml','10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml','10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml','10_REGISTRY/AUDIT_CATALOG.yaml','10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml']:
        p=SOURCE/rel; d=load(p)
        if 'governance_revision' in d: d['governance_revision']=NEW_REV
        dump(p,d)
    sem=load(SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml')
    suite=next(x for x in sem.get('mandatory_regression_assets') or [] if Path(str(x.get('path') or '')).name=='test_stage1_source_to_blueprint_minimal_control.py')
    if suite.get('expected_total')!=47 or suite.get('expected_passed')!=47: raise RuntimeError('unexpected Stage-1 regression denominator before v2.2.22:'+str(suite))
    suite['expected_total']=48; suite['expected_passed']=48
    sem['governance_revision']=NEW_REV; sem['content_hash']=hobj(sem); dump(SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml',sem)
    replace_const(SOURCE/'09_TESTS/governance/validate_reference_semantics.py','SEMANTIC_BASELINE_CONTENT_HASH',sem['content_hash'])
    for rel in ['10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml','10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml']:
        p=SOURCE/rel; d=load(p); d['governance_revision']=NEW_REV; dump(p,d)
    readme=SOURCE/'README.md'; rs=readme.read_text(encoding='utf-8')
    if '## v2.2.22 Word projection next-step consumer sync hardening' not in rs:
        readme.write_text(rs.rstrip()+"\n\n## v2.2.22 Word projection next-step consumer sync hardening\nThe DOCX projection validator now resolves the structured-document raw-capture next step from the canonical Stage-01 source contract instead of retaining a legacy literal. Producer, validator and regression fixture therefore share one owner.\n",encoding='utf-8')
    vr=SOURCE/'VERSIONING_RULE.md'; vs=vr.read_text(encoding='utf-8')
    if '## v2.2.22 projection next-step consumer sync rule' not in vs:
        vr.write_text(vs.rstrip()+"\n\n## v2.2.22 projection next-step consumer sync rule\n- Reusable projection consumers MUST resolve structured-document next-step identity from the canonical source contract.\n- Legacy local next-step literals are forbidden when a canonical contract field exists.\n- Positive and negative regression fixtures MUST consume the same canonical sequence.\n",encoding='utf-8')
    gp=SOURCE/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'; g=load(gp)
    g['candidate']='v2.2.22_WORD_PROJECTION_NEXTSTEP_CONSUMER_SYNC_HARDENING_CANDIDATE'; g['status']='CANDIDATE_UNDER_FRESH_SUCCESSOR_REVALIDATION'
    g.setdefault('fresh_revalidation',{}).update({'required':True,'current_source_revision':NEW_REV,'current_closure_credit':False,'predecessor_evidence_current_closure_credit':False,'persisted_head_full_line_required':True,'historical_evidence_may_close_successor':False})
    dump(gp,g)
    run(sys.executable,str(SOURCE/'09_TESTS/governance/compile_governance_baseline.py'))
    run(sys.executable,str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'))
    checks,bundle,zips=source_checksums_and_archives()
    replace_const(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py','EXPECTED_BUNDLE_SHA256',bundle)
    replace_const(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py','EXPECTED_SOURCE_ZIP_SHA256',zips)
    full=ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'; ft=full.read_text(encoding='utf-8')
    old="'test_stage1_source_to_blueprint_minimal_control.py': {'total': 47, 'passed_expectations': 47}"
    new="'test_stage1_source_to_blueprint_minimal_control.py': {'total': 48, 'passed_expectations': 48}"
    if old not in ft: raise RuntimeError('full-line Stage-1 denominator 47 projection missing')
    full.write_text(ft.replace(old,new,1),encoding='utf-8')
    for name,val in [('EXPECTED_CHECKSUMS_SHA256',checks),('EXPECTED_SEMANTIC_CONTENT_HASH',sem['content_hash']),('EXPECTED_SOURCE_ZIP_SHA256',zips),('EXPECTED_BUNDLE_SHA256',bundle)]:
        replace_const(ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py',name,val)
    return sem['content_hash'],checks,bundle,zips

def update_current(semantic,checks,bundle,zips):
    p=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'; d=load(p); old=copy.deepcopy(d.get('source_lineage') or {})
    d['artifact_uid']=NEW_UID; d['display_version']=NEW_DISPLAY
    d.setdefault('source_lineage',{}).update({'verified_package_filename':NEW_PACKAGE,'verified_package_sha256':zips,'predecessor_governance_uid':OLD_UID,'promotion_authorization_uid':AUTH_UID,'source_bytes_changed_by_this_successor':True,'source_identity_reused_only_because_source_bytes_are_unchanged':False,'deterministic_source_bundle_sha256':bundle,'checksum_manifest_sha256':checks,'semantic_authority_content_hash':semantic,'verified_source_revision':NEW_REV,'predecessor_verified_package_filename':old.get('verified_package_filename'),'predecessor_verified_package_sha256':old.get('verified_package_sha256'),'post_promotion_projector_sync_authorization_uid':AUTH_UID})
    dump(p,d)
    p=ROOT/'governance/specifications/REGISTRY.yaml'; d=load(p)
    d['active_specification']['governance_uid']=NEW_UID; d['active_specification']['display_version']=NEW_DISPLAY; unique_extend(d['active_specification'].setdefault('aliases',[]),['word-projection-nextstep-consumer-sync-hardening'])
    d['immediate_predecessor']={'governance_uid':OLD_UID,'display_version':OLD_DISPLAY,'version_role':'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY','status':'SUPERSEDED_HISTORY_ONLY_AFTER_WORD_PROJECTION_NEXTSTEP_CONSUMER_SYNC_HARDENING'}
    dump(p,d)
    p=ROOT/'GOVERNANCE_CURRENT.yaml'; d=load(p); d['active_governance_uid']=NEW_UID; d['display_version']=NEW_DISPLAY
    d.setdefault('source_identity',{}).update({'verified_package_sha256':zips,'deterministic_source_bundle_sha256':bundle,'checksum_manifest_sha256':checks,'semantic_authority_content_hash':semantic,'verified_source_revision':NEW_REV,'source_bytes_changed_by_current_successor':True})
    dump(p,d)
    p=ROOT/'governance/test/ACTIVE_STATE.yaml'; d=load(p)
    d['specification_uid']=NEW_UID; d['status']='WORD_PROJECTION_NEXTSTEP_CONSUMER_SYNC_SUCCESSOR_PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED'; d['next_action']='RUN_EXACT_HEAD_WORD_PROJECTION_NEXTSTEP_CONSUMER_SYNC_VALIDATION'
    d['current_primary_task_layer']='GOVERNANCE_MAINTENANCE'; d['current_primary_task_authorization_uid']=AUTH_UID; d['current_primary_task_product_stage_credit']=0
    d['active_work_unit']={'work_unit_uid':WORK_UNIT,'canonical_name':'WORD_PROJECTION_NEXTSTEP_CONSUMER_SYNC_GOVERNANCE_HARDENING','primary_task_layer':'GOVERNANCE_MAINTENANCE','semantic_capability':'SOURCE_INTAKE_STAGE1_GOVERNANCE','canonical_owner_refs':['.github/governance-source/active/source/10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml','.github/governance-source/active/source/09_TESTS/governance/governance_stage1_pipeline_guard.py','.github/governance-source/active/source/09_TESTS/governance/test_stage1_source_to_blueprint_minimal_control.py','governance/ci/build_docx_source_projection.py'],'current_status':'PROMOTION_MATERIALIZED_EXACT_HEAD_REVALIDATION_REQUIRED','authorization_uid':AUTH_UID,'exact_scope':['CANONICAL_STRUCTURED_DOCUMENT_NEXTSTEP_CONSUMER_SYNC','PRODUCER_VALIDATOR_FIXTURE_ALIGNMENT','LEGACY_NEXTSTEP_NEGATIVE_REGRESSION'],'product_data_mutation_allowed':False,'product_authority_mutation_allowed':False,'product_stage_credit':0}
    rc=d['resume_control']; rc['current_resume_point']='WORD_PROJECTION_NEXTSTEP_CONSUMER_SYNC_SUCCESSOR_PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED';rc['current_work_unit_uid']=WORK_UNIT;rc['current_owner']='SOURCE_INTAKE_STAGE1_GOVERNANCE';rc['exact_next_action']='RUN_EXACT_HEAD_WORD_PROJECTION_NEXTSTEP_CONSUMER_SYNC_VALIDATION';rc['product_execution_allowed']=False;rc['product_execution_block_reason']='CORE01_WORD_PROJECTION_WAITS_FOR_NEXTSTEP_CONSUMER_SYNC_EXACT_HEAD'
    d['governance_revision_transition'].update({'current_governance_uid':NEW_UID,'predecessor_governance_uid':OLD_UID,'fresh_revalidation_required':False,'governance_policy_consumer_revalidation_required':True,'product_stage_revalidation_required':False,'product_stage_revalidation_credit':0,'fresh_revalidation_scope':'WORD_PROJECTION_NEXTSTEP_CONSUMER_SYNC_POLICY_CONSUMERS_ONLY_NO_PRODUCT_STAGE_CREDIT','current_governance_product_credit':0})
    dump(p,d)
    p=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'; d=load(p)
    d['governance_uid']=NEW_UID;d['owning_capability']='GOVERNANCE_MAINTENANCE';d['scope_kind']='EXACT_GOVERNANCE_MAINTENANCE_WORD_PROJECTION_NEXTSTEP_CONSUMER_SYNC';d['work_unit_uid']=WORK_UNIT;d['included_units']=['CANONICAL_STRUCTURED_DOCUMENT_NEXTSTEP_CONSUMER_SYNC','PRODUCER_VALIDATOR_FIXTURE_ALIGNMENT','LEGACY_NEXTSTEP_NEGATIVE_REGRESSION'];d['remaining_units']=[];d['stage_required_units']=[];d['scope_selection_authority']=AUTH_UID;d['product_stage_execution_allowed']=False;d['product_stage_execution_block_reason']='CORE01_WORD_PROJECTION_WAITS_FOR_NEXTSTEP_CONSUMER_SYNC_EXACT_HEAD';d['fresh_revalidation_required']=False;d['product_stage_revalidation_required']=False;d['product_stage_revalidation_credit']=0;d['next_action']='RUN_EXACT_HEAD_WORD_PROJECTION_NEXTSTEP_CONSUMER_SYNC_VALIDATION';d['closure_status']='PROMOTION_MATERIALIZED_EXACT_HEAD_REVALIDATION_REQUIRED'
    dump(p,d)

def validate_all():
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONPYCACHEPREFIX']='/tmp/acpos-v222-pycache'
    cmds=[
      [sys.executable,str(SOURCE/'09_TESTS/governance/validate_section_registry.py')],
      [sys.executable,str(SOURCE/'09_TESTS/governance/validate_reference_semantics.py')],
      [sys.executable,str(SOURCE/'09_TESTS/governance/test_stage1_source_to_blueprint_minimal_control.py')],
      [sys.executable,str(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py')],
      [sys.executable,str(ROOT/'governance/ci/governance_resolver.py')],
      [sys.executable,str(ROOT/'governance/ci/validate_governance_portability.py')],
      [sys.executable,str(ROOT/'governance/ci/validate_active_consumer_reference_integrity.py')],
      [sys.executable,str(ROOT/'governance/ci/validate_validation_remediation_closure_protocol.py')],
      [sys.executable,str(ROOT/'governance/ci/validate_selected_execution_profile_integrity.py')],
      [sys.executable,str(ROOT/'governance/ci/stage_execution_engine.py'),'--definition-audit-all'],
      [sys.executable,str(ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py')],
    ]
    for cmd in cmds:
        cp=run(*cmd,check=False,env=env);print('$',' '.join(map(str,cmd)));print(cp.stdout[-9000:])
        if cp.returncode: print(cp.stderr[-16000:],file=sys.stderr);raise SystemExit(cp.returncode)

def main():
    mutate_guard_and_test()
    semantic,checks,bundle,zips=refresh_source()
    update_current(semantic,checks,bundle,zips)
    validate_all()
    for p in [ROOT/'.github/workflows/word-projection-nextstep-consumer-sync-promotion.yml',ROOT/'.github/governance-maintenance/promote_word_projection_nextstep_consumer_sync.py']:
        if p.exists(): p.unlink()
    run('git','config','user.name','github-actions[bot]');run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com');run('git','add','-A')
    if run('git','diff','--cached','--quiet',check=False).returncode==0: raise RuntimeError('no promotion delta')
    msg='feat(governance): synchronize Word projection next-step consumers\n\nSpec-Change-Authorization: '+AUTH_UID+'\nSpec-Change-Scope: WORD_PROJECTION_NEXTSTEP_CONSUMER_SYNC'
    run('git','commit','-m',msg);run(sys.executable,str(ROOT/'governance/ci/specification_mutation_guard.py'));run('git','push','origin','HEAD:rebuild-v2.1.1')
    print(json.dumps({'new_uid':NEW_UID,'semantic_hash':semantic,'checksums_hash':checks,'bundle_hash':bundle,'zip_hash':zips},indent=2))
    print('PROMOTION_PUSHED',run('git','rev-parse','HEAD').stdout.strip())
if __name__=='__main__': main()
