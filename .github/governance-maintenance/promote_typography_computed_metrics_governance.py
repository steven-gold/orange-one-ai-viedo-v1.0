#!/usr/bin/env python3
from __future__ import annotations
import argparse,copy,hashlib,io,json,lzma,os,re,subprocess,sys,tarfile,zipfile
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
OLD_UID='GOV-REV-20260920-CROSS-STAGE-MATERIALIZATION-CONSUMER-READINESS-HARDENING'
NEW_UID='GOV-REV-20260921-TYPOGRAPHY-COMPUTED-METRICS-HARDENING'
OLD_DISPLAY='v2.2.16'
NEW_DISPLAY='v2.2.17'
OLD_REV='v2.2.16-cross-stage-materialization-consumer-readiness-hardening'
NEW_REV='v2.2.17-typography-computed-metrics-hardening'
AUTH_UID='USR-DIRECTIVE-20260921-CONTENT-INTEGRITY-TYPOGRAPHY-CONSUMER-HARDENING-R1'
WORK_UNIT='WU-GOV-CONTENT-INTEGRITY-TYPOGRAPHY-CONSUMER-HARDENING-001'
NEW_PACKAGE='AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.17_TYPOGRAPHY_COMPUTED_METRICS_HARDENING_LOCAL_VERIFIED.zip'

SECTIONS={
'WEB-GOV-01-S089':('WEB-GOV-01','89','Typography Computed Metrics Baseline Gate / 字體計算值基準 Gate','12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md',r'''
Every text-bearing target in the applicable Current Design denominator MUST have one machine-readable typography baseline row. The denominator is derived from Current Design/Visual Authority and the selected scope; a representative sample, screenshot count, page count, control count, or hand-picked subset MUST_NOT substitute for the complete text-target universe.

Each baseline row MUST bind at least: target_uid; page_or_scope_uid; viewport_or_breakpoint_uid; language; theme when applicable; typography_authority_ref; font_family_token_or_value_ref; font_size_token_or_value_ref; font_weight_token_or_value_ref; line_height_token_or_value_ref; letter_spacing_token_or_value_ref; expected_font_family; expected_font_size_px; expected_font_weight; expected_line_height_px; expected_letter_spacing_px; expected_text_container_min_width_px; expected_text_container_max_width_px; wrap_rule; truncation_rule; expected_line_count_rule when applicable; and allowed_tolerance.

A text-bearing target MAY be NOT_APPLICABLE only with exact Authority evidence proving that no rendered typography is present for that target/state. Missing baseline rows, missing required metric fields, duplicate target credit, representative-sample credit, or baseline values inferred from the current rendered result rather than Design Authority are blocking defects.

The typography baseline is part of the Visual Geometry Contract and MUST be frozen with the approved design. Typography intent MUST NOT be reduced to a visual-diff-only assertion.
'''),
'WEB-GOV-02-S076':('WEB-GOV-02','76','Typography Computed Metrics Runtime Verification / 字體計算值執行驗證','12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md',r'''
Verification and Production Browser Acceptance MUST capture actual computed typography for every REQUIRED text-bearing target in every Required Viewport and applicable language/theme state. Capture MUST come from Browser DOM measurement, getComputedStyle, or an equivalent runtime source that exposes the effective rendered values.

For each target, runtime evidence MUST record at least: target_uid; typography_authority_ref; viewport_uid; language; theme; computed_font_family; computed_font_size_px; computed_font_weight; computed_line_height_px; computed_letter_spacing_px; actual_text_container_width_px; actual_text_container_height_px; scroll_width_px; scroll_height_px; rendered_line_count; wrap_state; truncation_state; clipping_state; overflow_state; expected metric references; tolerance; and reconciliation_result.

Expected and actual values MUST be compared per target against the frozen typography baseline and tolerance. Missing targets, missing computed values, unexpected clipping/overflow/wrap/truncation, font-family or weight mismatch, or numeric metrics outside tolerance MUST FAIL. A successful screenshot, page render, build, or aggregate typography visual-diff score MUST_NOT substitute for target-level computed evidence.

Localization verification MUST re-run the applicable typography target denominator for each Required language context whose rendered text can change geometry.
'''),
'WEB-GOV-04-S086':('WEB-GOV-04','86','Typography Computed Metrics Evidence Audit / 字體計算值證據稽核','12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md',r'''
Typography audit MUST reconcile the complete applicable text-bearing target denominator from frozen Design Authority to runtime evidence. The audit denominator is UID-based and MUST report required target total, baseline-complete total, runtime-captured total, tolerance-reconciled total, pass total, blocked total, NOT_APPLICABLE total with Authority evidence, and missing target total.

Each evidence row MUST preserve the exact expected metrics, actual computed metrics, viewport/language/theme context, tolerance, capture source, and reconciliation result. Browser DOM getComputedStyle/layout measurement or an equivalent verifiable runtime capture is required; manually entered computed values, count-only summaries, screenshots without target rows, or self-declared zero-overflow claims MUST_NOT receive acceptance credit.

Audit MUST fail for any REQUIRED target with missing baseline, missing runtime capture, missing computed metric, duplicate credit, unresolved typography Authority, font-family/weight mismatch, numeric tolerance breach, unexpected wrap/truncation, clipping, overflow, or text-container dimension violation. Representative samples MUST_NOT satisfy the complete denominator.

Typography evidence MUST remain traceable to the same Current Canonical Visual/Geometry baseline and exact deployed/source revision used by the surrounding Visual Geometry and Production Acceptance evidence.
''')
}

def run(*args,check=True,env=None):
    cp=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,env=env)
    if check and cp.returncode:
        print(cp.stdout);print(cp.stderr,file=sys.stderr);raise SystemExit(cp.returncode)
    return cp
def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def dump(p,d): Path(p).write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hobj(d):
    x=copy.deepcopy(d);x.pop('content_hash',None)
    return hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True,width=180).encode()).hexdigest()
def unique_extend(lst,items):
    for x in items:
        if x not in lst: lst.append(x)
def section_binding(uid,doc,path,heading): return hashlib.sha256(f'{uid}\n{doc}\n{path}\n{heading}\n'.encode()).hexdigest()
def replace_const(path,name,value):
    p=Path(path);s=p.read_text(encoding='utf-8');pat=re.compile(f"(?m)^{re.escape(name)}\\s*=\\s*'[^']*'$")
    ns,n=pat.subn(f"{name} = '{value}'",s,1)
    if n!=1: raise RuntimeError(f'constant {name} replacement count={n} in {path}')
    p.write_text(ns,encoding='utf-8')
def append_section(uid,doc,num,title,rel,body):
    p=SOURCE/rel;s=p.read_text(encoding='utf-8')
    if f'<!-- SECTION_UID: {uid} -->' in s:return
    p.write_text(s.rstrip()+f'\n\n<!-- SECTION_UID: {uid} -->\n## {num}. {title}\n\n{body.strip()}\n',encoding='utf-8')
def update_section_registry():
    p=SOURCE/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml';d=load(p)
    for uid,(doc,num,title,rel,_) in SECTIONS.items():
        entry=next(x for x in d.get('documents',[]) if x.get('document_id')==doc)
        if any(x.get('section_uid')==uid for x in entry.get('sections',[])):continue
        heading=f'## {num}. {title}'
        entry.setdefault('sections',[]).append({'section_uid':uid,'level':2,'canonical_number':num,'title':title,'heading':heading,'path':rel,'binding_sha256':section_binding(uid,doc,rel,heading)})
    if 'governance_revision' in d:d['governance_revision']=NEW_REV
    dump(p,d)

def mutate_policy():
    for uid,args in SECTIONS.items(): append_section(uid,*args)
    update_section_registry()

    ip=SOURCE/'10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml';invdoc=load(ip);inv=invdoc.setdefault('invariants',{})
    inv['TYPOGRAPHY_COMPUTED_METRICS']={
      'invariant_uid':'GOV-INV-TYPOGRAPHY-COMPUTED-METRICS-001',
      'target_denominator':'EVERY_APPLICABLE_TEXT_BEARING_TARGET_FROM_CURRENT_DESIGN_AUTHORITY',
      'baseline_owner':'VISUAL_DESIGN',
      'runtime_capture_owner':'VERIFICATION_AND_PRODUCTION_ACCEPTANCE',
      'baseline_carrier':'VISUAL_GEOMETRY_CONTRACT',
      'runtime_evidence_artifact_type':'TYPOGRAPHY_COMPUTED_METRICS_EVIDENCE',
      'required_context_fields':['target_uid','page_or_scope_uid','viewport_uid','language','theme','typography_authority_ref'],
      'required_expected_fields':['font_family','font_size_px','font_weight','line_height_px','letter_spacing_px','text_container_min_width_px','text_container_max_width_px','wrap_rule','truncation_rule','expected_line_count_rule_when_applicable'],
      'required_computed_fields':['font_family','font_size_px','font_weight','line_height_px','letter_spacing_px','text_container_width_px','text_container_height_px','scroll_width_px','scroll_height_px','rendered_line_count','wrap_state','truncation_state','clipping','overflow'],
      'required_tolerance_fields':['font_size_px','line_height_px','letter_spacing_px','container_width_px'],
      'runtime_capture_source':'BROWSER_DOM_GETCOMPUTEDSTYLE_AND_LAYOUT_OR_EQUIVALENT_VERIFIABLE_RUNTIME_CAPTURE',
      'representative_sample_may_satisfy_denominator':False,
      'screenshot_only_may_satisfy_evidence':False,
      'manual_computed_value_may_satisfy_evidence':False,
      'not_applicable_requires_authority_evidence':True,
      'missing_required_target':'BLOCK',
      'missing_required_metric':'BLOCK',
      'unexpected_clipping_or_overflow':'BLOCK',
      'unexpected_wrap_or_truncation':'BLOCK',
      'font_family_or_weight_mismatch':'BLOCK',
      'numeric_tolerance_breach':'BLOCK',
    }
    invdoc['governance_revision']=NEW_REV;dump(ip,invdoc)

    lp=SOURCE/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml';life=load(lp)
    adds={'STAGE-03':['WEB-GOV-01-S089'],'STAGE-04':['WEB-GOV-01-S089'],'STAGE-06':['WEB-GOV-02-S076','WEB-GOV-04-S086'],'STAGE-10':['WEB-GOV-02-S076','WEB-GOV-04-S086']}
    for st in life.get('stages',[]):
        uid=st.get('stage_uid');unique_extend(st.setdefault('required_normative_section_uids',[]),adds.get(uid,[]))
        if uid=='STAGE-03':st['typography_computed_metrics_gate']={'required':True,'phase':'EXPECTED_BASELINE','invariant_uid':'GOV-INV-TYPOGRAPHY-COMPUTED-METRICS-001','carrier':'VISUAL_GEOMETRY_CONTRACT','complete_text_target_denominator_required':True,'runtime_capture_credit':0}
        elif uid=='STAGE-04':st['typography_computed_metrics_gate']={'required':True,'phase':'FREEZE','invariant_uid':'GOV-INV-TYPOGRAPHY-COMPUTED-METRICS-001','freeze_expected_baseline_required':True}
        elif uid=='STAGE-06':st['typography_computed_metrics_gate']={'required':True,'phase':'RUNTIME_VERIFICATION','invariant_uid':'GOV-INV-TYPOGRAPHY-COMPUTED-METRICS-001','evidence_artifact_type':'TYPOGRAPHY_COMPUTED_METRICS_EVIDENCE','capture_source':'BROWSER_DOM_GETCOMPUTEDSTYLE_AND_LAYOUT_OR_EQUIVALENT','all_required_viewports_languages_themes':True}
        elif uid=='STAGE-10':st['typography_computed_metrics_gate']={'required':True,'phase':'PRODUCTION_ACCEPTANCE','invariant_uid':'GOV-INV-TYPOGRAPHY-COMPUTED-METRICS-001','evidence_artifact_type':'TYPOGRAPHY_COMPUTED_METRICS_EVIDENCE','deployed_revision_binding_required':True}
    cross=life.setdefault('cross_stage_invariants',{}).setdefault('stage_execution_invariant_hardening',{})
    cross['typography_computed_metrics_required']=True;cross['typography_target_denominator_must_be_dynamic']=True;cross['typography_representative_sample_completion']='BLOCK'
    life['governance_revision']=NEW_REV;dump(lp,life)

    rp=SOURCE/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml';ref=load(rp)
    for uid,items in adds.items():unique_extend(ref['stage_reference_rules'][uid]['exact_required_normative_section_uids'],items)
    unique_extend(ref['common_bundle_reference_rules']['BUNDLE-GOV-CONSTRUCTION-BASE']['exact_section_uids'],['WEB-GOV-01-S089','WEB-GOV-02-S076'])
    unique_extend(ref['common_bundle_reference_rules']['BUNDLE-GOV-AUDIT-BASE']['exact_section_uids'],['WEB-GOV-04-S086'])
    ref['governance_revision']=NEW_REV;dump(rp,ref)

    sp=SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml';sem=load(sp)
    for uid,items in adds.items():unique_extend(sem['semantic_snapshot']['stage_reference_rules'][uid]['exact_required_normative_section_uids'],items)
    cb=sem['semantic_snapshot'].get('common_bundle_reference_rules') or {}
    if 'BUNDLE-GOV-CONSTRUCTION-BASE' in cb:unique_extend(cb['BUNDLE-GOV-CONSTRUCTION-BASE']['exact_section_uids'],['WEB-GOV-01-S089','WEB-GOV-02-S076'])
    if 'BUNDLE-GOV-AUDIT-BASE' in cb:unique_extend(cb['BUNDLE-GOV-AUDIT-BASE']['exact_section_uids'],['WEB-GOV-04-S086'])
    sem['governance_revision']=NEW_REV;sem['content_hash']=hobj(sem);dump(sp,sem)

    ap=SOURCE/'10_REGISTRY/AUDIT_CATALOG.yaml';aud=load(ap)
    unique_extend(aud.setdefault('normative_section_uids',[]),['WEB-GOV-01-S089','WEB-GOV-02-S076','WEB-GOV-04-S086'])
    item=next(x for x in aud.get('items',[]) if x.get('audit_item_uid')=='AUD-GOV-013')
    unique_extend(item.setdefault('coverage_extensions',[]),['TYPOGRAPHY_COMPUTED_METRICS'])
    aud['governance_revision']=NEW_REV;dump(ap,aud)

    bp=SOURCE/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml';bpd=load(bp)
    unique_extend(bpd.setdefault('normative_section_uids',[]),['WEB-GOV-01-S089','WEB-GOV-02-S076','WEB-GOV-04-S086'])
    unique_extend(bpd.setdefault('required_normative_section_uids',[]),['WEB-GOV-01-S089','WEB-GOV-02-S076','WEB-GOV-04-S086'])
    c=bpd.setdefault('product_neutral_entity_lifecycle_contract',{})
    c.update({'typography_computed_metrics_required':True,'typography_target_denominator':'EVERY_APPLICABLE_TEXT_BEARING_TARGET','typography_representative_sample_credit':'BLOCK','typography_runtime_computed_capture_required':True,'typography_not_applicable_requires_authority':True})
    bpd['governance_revision']=NEW_REV;dump(bp,bpd)

    vp=SOURCE/'09_TESTS/governance/validate_product_neutral_entity_lifecycle.py';s=vp.read_text(encoding='utf-8')
    marker="    return {'status':'PASS' if not failures else 'FAIL'"
    if 'typography_computed_metrics_contract_invalid' not in s:
        insert=r'''    tm=inv.get('TYPOGRAPHY_COMPUTED_METRICS') or {}
    req_expected={'font_family','font_size_px','font_weight','line_height_px','letter_spacing_px','text_container_min_width_px','text_container_max_width_px','wrap_rule','truncation_rule','expected_line_count_rule_when_applicable'}
    req_actual={'font_family','font_size_px','font_weight','line_height_px','letter_spacing_px','text_container_width_px','text_container_height_px','scroll_width_px','scroll_height_px','rendered_line_count','wrap_state','truncation_state','clipping','overflow'}
    if tm.get('invariant_uid')!='GOV-INV-TYPOGRAPHY-COMPUTED-METRICS-001' or tm.get('target_denominator')!='EVERY_APPLICABLE_TEXT_BEARING_TARGET_FROM_CURRENT_DESIGN_AUTHORITY': failures.append('typography_computed_metrics_contract_invalid')
    if set(tm.get('required_expected_fields') or [])!=req_expected or set(tm.get('required_computed_fields') or [])!=req_actual: failures.append('typography_metric_field_denominator_invalid')
    if tm.get('representative_sample_may_satisfy_denominator') is not False or tm.get('screenshot_only_may_satisfy_evidence') is not False or tm.get('manual_computed_value_may_satisfy_evidence') is not False or tm.get('not_applicable_requires_authority_evidence') is not True: failures.append('typography_evidence_fail_closed_contract_invalid')
    if c.get('typography_computed_metrics_required') is not True or c.get('typography_runtime_computed_capture_required') is not True or c.get('typography_representative_sample_credit')!='BLOCK' or c.get('typography_not_applicable_requires_authority') is not True: failures.append('acceptance_typography_computed_metrics_contract_missing')
    for stage_uid in ['STAGE-03','STAGE-04','STAGE-06','STAGE-10']:
        tg=(stage_map.get(stage_uid) or {}).get('typography_computed_metrics_gate') or {}
        if tg.get('required') is not True or tg.get('invariant_uid')!='GOV-INV-TYPOGRAPHY-COMPUTED-METRICS-001': failures.append('stage_typography_gate_missing:'+stage_uid)
    for uid in ['WEB-GOV-01-S089','WEB-GOV-02-S076','WEB-GOV-04-S086']:
        if not any(uid in (root/rel).read_text(encoding='utf-8') for rel in common_docs): failures.append('mother_typography_section_missing:'+uid)

'''
        if marker not in s:raise RuntimeError('product-neutral validator insertion marker missing')
        s=s.replace(marker,insert+marker)
        vp.write_text(s,encoding='utf-8')

def mutate_current_components():
    p=ROOT/'governance/specifications/current/INTERACTION_TOPOLOGY_AI_CONTINUITY.yaml';d=load(p)
    d.setdefault('common_invariants',{})['TYPOGRAPHY_COMPUTED_METRICS']={
      'invariant_uid':'GOV-INV-TYPOGRAPHY-COMPUTED-METRICS-001','target_denominator':'EVERY_APPLICABLE_TEXT_BEARING_TARGET_FROM_CURRENT_DESIGN_AUTHORITY','expected_baseline_owner':'VISUAL_DESIGN','runtime_capture_owner':'VERIFICATION_AND_PRODUCTION_ACCEPTANCE','runtime_evidence_artifact_type':'TYPOGRAPHY_COMPUTED_METRICS_EVIDENCE','representative_sample_completion':'BLOCK','screenshot_only_completion':'BLOCK','not_applicable_requires_authority_evidence':True,'unexpected_clipping_or_overflow':'BLOCK','numeric_tolerance_breach':'BLOCK'}
    d['schema_version']=int(d.get('schema_version',0))+1;dump(p,d)
    p=ROOT/'governance/specifications/current/BOUNDED_FUNCTIONAL_COMPLETION.yaml';d=load(p)
    d.setdefault('rules',{})['TYPOGRAPHY_COMPUTED_METRICS_COMPLETENESS']={'target_denominator':'EVERY_APPLICABLE_TEXT_BEARING_TARGET','complete_expected_baseline_required_before_freeze':True,'complete_runtime_capture_required_for_verification_and_production_acceptance':True,'representative_sample_credit':'BLOCK','not_applicable_requires_authority_evidence':True,'missing_target_or_metric':'BLOCK'}
    d['schema_version']=int(d.get('schema_version',0))+1;dump(p,d)

def source_checksums_and_archives():
    checks=SOURCE/'CHECKSUMS.sha256'
    files=sorted([p for p in SOURCE.rglob('*') if p.is_file() and p!=checks],key=lambda p:p.relative_to(SOURCE).as_posix())
    checks.write_text(''.join(f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in files),encoding='utf-8')
    allfiles=sorted([p for p in SOURCE.rglob('*') if p.is_file()],key=lambda p:p.relative_to(SOURCE).as_posix())
    if len(allfiles)!=75:raise RuntimeError(f'source file count changed:{len(allfiles)}')
    tbuf=io.BytesIO()
    with tarfile.open(fileobj=tbuf,mode='w',format=tarfile.PAX_FORMAT) as tf:
        for p in allfiles:
            rel=p.relative_to(SOURCE).as_posix();info=tf.gettarinfo(str(p),arcname=rel);info.uid=0;info.gid=0;info.uname='';info.gname='';info.mtime=0
            with p.open('rb') as fh:tf.addfile(info,fh)
    bundle=lzma.compress(tbuf.getvalue(),format=lzma.FORMAT_XZ,preset=9)
    zbuf=io.BytesIO()
    with zipfile.ZipFile(zbuf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for p in allfiles:
            rel=p.relative_to(SOURCE).as_posix();zi=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED;zi.create_system=3;mode=493 if p.stat().st_mode&73 else 420;zi.external_attr=(mode&65535)<<16;zf.writestr(zi,p.read_bytes())
    return sha(checks),hashlib.sha256(bundle).hexdigest(),hashlib.sha256(zbuf.getvalue()).hexdigest()

def refresh_source():
    sem=load(SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml');semantic_hash=sem['content_hash']
    for rel in ['10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml','10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml','10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml','10_REGISTRY/BLUEPRINT_REGISTRY.yaml','10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml','10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml','10_REGISTRY/AUDIT_CATALOG.yaml']:
        p=SOURCE/rel;d=load(p)
        if 'governance_revision' in d:d['governance_revision']=NEW_REV
        dump(p,d)
    rp=SOURCE/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml';rd=load(rp);rd['governance_revision']=NEW_REV;dump(rp,rd)
    rvp=SOURCE/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml';rv=load(rvp);rv['governance_revision']=NEW_REV;dump(rvp,rv)
    readme=SOURCE/'README.md';rs=readme.read_text(encoding='utf-8')
    if '## v2.2.17 typography computed metrics hardening' not in rs:readme.write_text(rs.rstrip()+'\n\n## v2.2.17 typography computed metrics hardening\nThis successor requires complete per-target typography baselines and Browser/runtime computed-metric evidence across applicable viewports, languages, and themes. It remains product-neutral and denominator-dynamic.\n',encoding='utf-8')
    vr=SOURCE/'VERSIONING_RULE.md';vs=vr.read_text(encoding='utf-8')
    if '## v2.2.17 typography computed metrics hardening rule' not in vs:vr.write_text(vs.rstrip()+'\n\n## v2.2.17 typography computed metrics hardening rule\n- Typography intent, overflow checks, and screenshots alone do not prove computed-style conformance.\n- Every applicable text-bearing target requires Authority-derived expected metrics and runtime computed evidence.\n- Representative samples, manually entered computed values, and missing-target denominators are blocking.\n',encoding='utf-8')
    replace_const(SOURCE/'09_TESTS/governance/validate_reference_semantics.py','SEMANTIC_BASELINE_CONTENT_HASH',semantic_hash)
    run(sys.executable,str(SOURCE/'09_TESTS/governance/compile_governance_baseline.py'))
    run(sys.executable,str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'))
    checks,bundle,zips=source_checksums_and_archives()
    replace_const(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py','EXPECTED_BUNDLE_SHA256',bundle)
    replace_const(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py','EXPECTED_SOURCE_ZIP_SHA256',zips)
    for name,val in [('EXPECTED_CHECKSUMS_SHA256',checks),('EXPECTED_SEMANTIC_CONTENT_HASH',semantic_hash),('EXPECTED_SOURCE_ZIP_SHA256',zips),('EXPECTED_BUNDLE_SHA256',bundle)]:
        replace_const(ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py',name,val)
    return semantic_hash,checks,bundle,zips

def update_current(semantic,checks,bundle,zips):
    mp=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml';m=load(mp);oldsl=copy.deepcopy(m.get('source_lineage') or {})
    m['artifact_uid']=NEW_UID;m['display_version']=NEW_DISPLAY
    m.setdefault('source_lineage',{}).update({'verified_package_filename':NEW_PACKAGE,'verified_package_sha256':zips,'predecessor_governance_uid':OLD_UID,'promotion_authorization_uid':AUTH_UID,'source_bytes_changed_by_this_successor':True,'source_identity_reused_only_because_source_bytes_are_unchanged':False,'deterministic_source_bundle_sha256':bundle,'checksum_manifest_sha256':checks,'semantic_authority_content_hash':semantic,'verified_source_revision':NEW_REV,'predecessor_verified_package_filename':oldsl.get('verified_package_filename'),'predecessor_verified_package_sha256':oldsl.get('verified_package_sha256'),'post_promotion_projector_sync_authorization_uid':AUTH_UID})
    dump(mp,m)
    rp=ROOT/'governance/specifications/REGISTRY.yaml';r=load(rp);r['active_specification']['governance_uid']=NEW_UID;r['active_specification']['display_version']=NEW_DISPLAY;unique_extend(r['active_specification'].setdefault('aliases',[]),['typography-computed-metrics-hardening']);r['immediate_predecessor']={'governance_uid':OLD_UID,'display_version':OLD_DISPLAY,'version_role':'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY','status':'SUPERSEDED_HISTORY_ONLY_AFTER_TYPOGRAPHY_COMPUTED_METRICS_HARDENING'};dump(rp,r)
    cp=ROOT/'GOVERNANCE_CURRENT.yaml';c=load(cp);c['active_governance_uid']=NEW_UID;c['display_version']=NEW_DISPLAY;c.setdefault('source_identity',{}).update({'verified_package_sha256':zips,'deterministic_source_bundle_sha256':bundle,'checksum_manifest_sha256':checks,'semantic_authority_content_hash':semantic,'verified_source_revision':NEW_REV,'source_bytes_changed_by_current_successor':True});dump(cp,c)
    ap=ROOT/'governance/test/ACTIVE_STATE.yaml';a=load(ap);a['specification_uid']=NEW_UID;a['status']='TYPOGRAPHY_COMPUTED_METRICS_SUCCESSOR_PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED';a['next_action']='RUN_EXACT_HEAD_SELECTED_PROFILE_FULL_LINE_AND_TYPOGRAPHY_REGRESSION'
    gt=a.setdefault('governance_revision_transition',{});gt.update({'predecessor_governance_uid':OLD_UID,'current_governance_uid':NEW_UID,'fresh_revalidation_required':True,'fresh_revalidation_scope':'TYPOGRAPHY_COMPUTED_METRICS_POLICY_CONSUMERS_AND_INTERRUPTED_CORE01_CONTENT_INTEGRITY_TEST','website_construction_remains_blocked':True,'deployment_remains_blocked':True})
    aw=a.get('active_work_unit') or {}
    if aw.get('work_unit_uid')!=WORK_UNIT:raise RuntimeError('active governance work unit drift')
    aw['current_status']='PROMOTION_MATERIALIZED_EXACT_HEAD_REVALIDATION_REQUIRED';a['active_work_unit']=aw
    rc=a.setdefault('resume_control',{});rc['current_resume_point']='TYPOGRAPHY_COMPUTED_METRICS_SUCCESSOR_PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED';rc['current_work_unit_uid']=WORK_UNIT;rc['exact_next_action']='RUN_EXACT_HEAD_SELECTED_PROFILE_FULL_LINE_AND_TYPOGRAPHY_REGRESSION';dump(ap,a)
    sp=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml';sd=load(sp);sd['governance_uid']=NEW_UID;sd['closure_status']='PROMOTION_MATERIALIZED_EXACT_HEAD_REVALIDATION_REQUIRED';sd['next_action']='RUN_EXACT_HEAD_SELECTED_PROFILE_FULL_LINE_AND_TYPOGRAPHY_REGRESSION';dump(sp,sd)
    fp=ROOT/'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml';f=load(fp)
    cse=f.get('current_stage2_execution')
    if isinstance(cse,dict) and cse.get('governance_uid')==OLD_UID:cse['governance_uid']=NEW_UID
    for row in f.get('findings') or []:
        if row.get('finding_uid')=='FIND-20260921-003':
            row['disposition']='GOVERNANCE_PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED';row['formal_specification_mutated_for_fix']=True;row['successor_governance_uid']=NEW_UID
    dump(fp,f)
    sf=ROOT/'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
    if sf.exists():
        d=load(sf)
        if d.get('governance_uid')==OLD_UID:d['governance_uid']=NEW_UID
        if 'content_hash' in d:d['content_hash']=hobj(d)
        dump(sf,d)
    gp=SOURCE/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml';g=load(gp);g['candidate']='v2.2.17_TYPOGRAPHY_COMPUTED_METRICS_HARDENING_CANDIDATE';g['status']='CANDIDATE_UNDER_FRESH_SUCCESSOR_REVALIDATION';fresh=g.setdefault('fresh_revalidation',{});fresh.update({'required':True,'current_source_revision':NEW_REV,'current_closure_credit':False,'predecessor_evidence_current_closure_credit':False,'persisted_head_full_line_required':True,'historical_evidence_may_close_successor':False});dump(gp,g)

def validate_all():
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONPYCACHEPREFIX']='/tmp/acpos-typography-pycache'
    cmds=[
      [sys.executable,str(SOURCE/'09_TESTS/governance/validate_section_registry.py')],
      [sys.executable,str(SOURCE/'09_TESTS/governance/validate_reference_semantics.py')],
      [sys.executable,str(SOURCE/'09_TESTS/governance/validate_product_neutral_entity_lifecycle.py')],
      [sys.executable,str(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py')],
      [sys.executable,str(ROOT/'governance/ci/governance_resolver.py')],
      [sys.executable,str(ROOT/'governance/ci/validate_governance_portability.py')],
      [sys.executable,str(ROOT/'governance/ci/validate_active_consumer_reference_integrity.py')],
      [sys.executable,str(ROOT/'governance/ci/validate_selected_execution_profile_integrity.py')],
      [sys.executable,str(ROOT/'governance/ci/stage_execution_engine.py'),'--definition-audit-all'],
      [sys.executable,str(ROOT/'governance/ci/test_content_integrity_engine.py')],
      [sys.executable,str(ROOT/'governance/ci/test_typography_metrics_evidence.py')],
      [sys.executable,str(ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py')],
    ]
    for cmd in cmds:
        cp=run(*cmd,check=False,env=env);print('$',' '.join(map(str,cmd)));print(cp.stdout[-5000:])
        if cp.returncode:print(cp.stderr[-7000:],file=sys.stderr);raise SystemExit(cp.returncode)

def apply():
    cur=load(ROOT/'GOVERNANCE_CURRENT.yaml')
    if cur.get('active_governance_uid') not in (OLD_UID,NEW_UID):raise RuntimeError('unexpected Current Governance')
    mutate_policy();mutate_current_components()
    semantic,checks,bundle,zips=refresh_source();update_current(semantic,checks,bundle,zips)
    return {'semantic_hash':semantic,'checksums_hash':checks,'bundle_hash':bundle,'zip_hash':zips}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['promote'],required=True);args=ap.parse_args()
    result=apply();validate_all()
    for p in [ROOT/'.github/workflows/typography-computed-metrics-governance-promotion.yml',ROOT/'.github/governance-maintenance/promote_typography_computed_metrics_governance.py']:
        if p.exists():p.unlink()
    run('git','config','user.name','github-actions[bot]');run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com');run('git','add','-A')
    if run('git','diff','--cached','--quiet',check=False).returncode==0:raise RuntimeError('no promotion delta')
    msg='feat(governance): promote typography computed metrics hardening\n\nSpec-Change-Authorization: '+AUTH_UID+'\nSpec-Change-Scope: TYPOGRAPHY_COMPUTED_METRICS_PRODUCT_NEUTRAL_BASELINE_RUNTIME_EVIDENCE_AUDIT'
    run('git','commit','-m',msg)
    run(sys.executable,str(ROOT/'governance/ci/specification_mutation_guard.py'))
    run('git','push','origin','HEAD:rebuild-v2.1.1')
    print(json.dumps({'new_uid':NEW_UID,**result},indent=2));print('PROMOTION_PUSHED',run('git','rev-parse','HEAD').stdout.strip());return 0
if __name__=='__main__':raise SystemExit(main())
