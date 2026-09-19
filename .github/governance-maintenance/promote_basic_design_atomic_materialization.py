from __future__ import annotations
import copy, hashlib, io, json, lzma, os, re, subprocess, sys, tarfile, zipfile
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
OLD_UID='GOV-REV-20260919-BASIC-DESIGN-VISUAL-INTEGRATION-HARDENING'
NEW_UID='GOV-REV-20260919-BASIC-DESIGN-ATOMIC-MATERIALIZATION-HARDENING'
OLD_DISPLAY='v2.2.11'
NEW_DISPLAY='v2.2.12'
NEW_SOURCE_REV='v2.2.12-basic-design-atomic-materialization-hardening'
AUTH_UID='USR-DIRECTIVE-20260919-BASIC-DESIGN-ATOMIC-MATERIALIZATION-HARDENING-R1'
NEW_PACKAGE='AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.12_BASIC_DESIGN_ATOMIC_MATERIALIZATION_HARDENING_LOCAL_VERIFIED.zip'

SECTIONS={
'WEB-GOV-01-S084':('84','基本設計原子化實體化與禁止摘要替代 Gate / Atomic Basic Design Materialization and No-Summary Substitution',"""
Basic Design completeness is measured by executable-detail coverage of the complete applicable denominator, not by document page count, prose length, visual attractiveness, section count, or a high-level declaration that an area is covered.

Every REQUIRED denominator item MUST be individually materialized as an identifiable row/record/object in the applicable design artifact. Representative examples, selected key controls, capability-group summaries, prose-only descriptions, or one aggregate statement MUST_NOT substitute for the complete denominator.

At minimum, every applicable governed item MUST preserve exact identity and relationships sufficient to execute and review its design semantics. Depending on item class, the materialized row MUST include the applicable subset of: canonical UID/name/item type/owner; parent and dependency identities; Business Entity and Operation; Journey and Functional Workbench; preconditions and required inputs/source identities; output/result and mutation/read-only classification; Section/Component/Control or System Trigger/Field; Gate/Permission/Role; legal State/Transition and state effect; Visual Anchor/Visual Candidate/visible or non-visual classification; Next Step/downstream handoff; Error/blocked reason/Recovery Path; Acceptance/Design Review Item; Authority refs and version/hash where required.

A field that is not applicable MUST be explicitly classified NOT_APPLICABLE with Authority/design evidence when the field belongs to the required schema. Blank, omitted, unknown-by-silence, or inferred values MUST_NOT receive completeness credit.

The labels MAPPED, COVERED, COMPLETE, PASS, SUPPORTED, IMPLEMENTED, percentage-only claims, checklist ticks, section titles, screenshots without binding rows, or prose that says all items are included MUST_NOT receive denominator credit by themselves.

Any missing applicable row, missing required row field, missing required binding, silent omission, representative-sample substitution, or aggregate-summary substitution is BASIC_DESIGN_ATOMIC_MATERIALIZATION_INCOMPLETE and MUST block Basic Design Freeze.
"""),
'WEB-GOV-01-S085':('85','基本設計分母完整性與交付物對帳 Gate / Basic Design Denominator Integrity and Deliverable Reconciliation',"""
Before Basic Design Freeze, the scope MUST materialize one BASIC_DESIGN_DENOMINATOR_SNAPSHOT and one BASIC_DESIGN_DELIVERABLE_RECONCILIATION.

The denominator snapshot MUST enumerate the complete applicable set and exact count for every required design category, including at least: Requirements; Business Entities; Operations; Entity hierarchy relations; Journeys; Workbenches; Interaction topology relations; Sections; Components; Controls/System Triggers; Fields/Inputs; Gates; Permissions/Roles; States; Transitions; Errors; Recovery Paths; Data Objects; functional-chain nodes/edges; Cross-page relationships; Visual Anchors; required Visual Scenarios/Candidates; Visual Reference Annotations; Design Review/Acceptance Items; and any additional category required by Current Authority.

The reconciliation MUST prove, category by category and UID by UID: denominator item exists in the machine-readable design source; required row-level bindings are complete; the human-readable Basic Design deliverable contains the same required design detail directly or in an embedded complete appendix/table; visual evidence and annotations reference the same identities; no required item is silently hidden behind a summary, collapsed count, representative sample, or external-only reference; duplicate rows do not inflate coverage; and NOT_APPLICABLE items have explicit evidence.

Human-readable documents MAY use pagination, appendices, repeated table headers, or cross-references for readability, but MUST_NOT reduce the governed denominator. Machine-readable registries MAY supplement the human-readable document, but MUST_NOT be used as an excuse to omit required reviewable detail from the self-contained Basic Design deliverable.

Required conditions before Freeze: machine denominator count equals classified applicable denominator count; human-deliverable represented denominator count equals machine required denominator count; missing required UID count=0; duplicate-credit count=0; summary-only-credit count=0; representative-sample-credit count=0; human/machine denominator mismatch count=0; unclassified applicability count=0.

Any mismatch is BASIC_DESIGN_DENOMINATOR_RECONCILIATION_FAILED and MUST block Basic Design Freeze.
"""),
'WEB-GOV-01-S086':('86','基本設計執行細節完整度 Gate / Basic Design Execution-Detail Completeness',"""
Basic Design MUST define enough exact behavior that a later implementation owner can determine what must be built without inventing product semantics, guessing missing interaction logic, or selecting among multiple materially different behaviors.

For every REQUIRED Business Entity Operation and every user-visible or user-observable utility operation, the design contract MUST resolve as applicable:
Identity -> Owner -> Preconditions -> Inputs/Sources -> Operation/Action -> Output -> State Effect -> Gate -> Permission -> Workbench -> Section -> Component -> Control/Trigger -> Field -> Visual State/Anchor -> Next Step -> Error/Blocked Condition -> Recovery -> Cross-page/Handoff -> Acceptance.

For state-bearing behavior, legal transitions and illegal/blocked transitions MUST both be explicit. For effectful behavior, mutation target and resulting identity/version semantics MUST be explicit. For read-only behavior, exact source/read model and stale/missing behavior MUST be explicit. For conditional behavior, branch condition and each legal branch outcome MUST be explicit. For asynchronous behavior, pending/processing/success/failure/retry/cancel-or-no-cancel semantics MUST be explicit when applicable. For permission-controlled behavior, enabled/disabled/hidden behavior and reason source MUST be explicit. For cross-page behavior, source exit state, exported identity, trigger, target entry state, failure/resume, and return/back semantics MUST be explicit when applicable.

A design that names a control or function but leaves its input source, ownership, gate, state effect, next step, failure behavior, recovery, or acceptance undefined MUST be classified as a design gap rather than treated as complete.

AI MUST_NOT fill a missing product decision merely to complete the matrix. If Current Authority does not uniquely determine the required detail, the row MUST remain AUTHORITY_GAP, DESIGN_DECISION_REQUIRED, or another governed fail-closed disposition and MUST block Freeze where the detail is REQUIRED.

No downstream implementation, test, runtime, or deployment artifact may be used to retroactively claim that an incomplete Basic Design row was complete at Freeze time.
""")
}

def run(*args,check=True,env=None):
    cp=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,env=env)
    if check and cp.returncode:
        print(cp.stdout); print(cp.stderr,file=sys.stderr); raise SystemExit(cp.returncode)
    return cp
def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def dump(p,o): Path(p).write_text(yaml.safe_dump(o,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def section_binding(uid,doc_id,path,heading): return hashlib.sha256(f'{uid}\n{doc_id}\n{path}\n{heading}\n'.encode()).hexdigest()
def unique_extend(lst,items):
    for x in items:
        if x not in lst: lst.append(x)
def replace_const(path,name,value):
    p=Path(path); s=p.read_text(encoding='utf-8'); pat=re.compile(f"(?m)^{re.escape(name)}\\s*=\\s*'[^']*'$")
    ns,n=pat.subn(f"{name} = '{value}'",s,1)
    if n!=1: raise RuntimeError(f'constant {name} replacement count={n} in {path}')
    p.write_text(ns,encoding='utf-8')
def deep_replace(obj,old,new):
    if isinstance(obj,dict): return {k:deep_replace(v,old,new) for k,v in obj.items()}
    if isinstance(obj,list): return [deep_replace(v,old,new) for v in obj]
    return new if obj==old else obj

def mutate_mother():
    p=SOURCE/'12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md'; s=p.read_text(encoding='utf-8')
    for uid,(num,title,body) in SECTIONS.items():
        marker=f'<!-- SECTION_UID: {uid} -->'
        if marker not in s: s=s.rstrip()+f'\n\n{marker}\n## {num}. {title}\n\n{body.strip()}\n'
    p.write_text(s,encoding='utf-8')

def mutate_section_registry():
    p=SOURCE/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'; d=load(p)
    doc=next(x for x in d['documents'] if x.get('document_id')=='WEB-GOV-01'); existing={x.get('section_uid') for x in doc.get('sections',[])}
    rel='12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md'
    for uid,(num,title,_) in SECTIONS.items():
        if uid not in existing:
            heading=f'## {num}. {title}'
            doc.setdefault('sections',[]).append({'section_uid':uid,'level':2,'canonical_number':num,'title':title,'heading':heading,'path':rel,'binding_sha256':section_binding(uid,'WEB-GOV-01',rel,heading)})
    d['governance_revision']=NEW_SOURCE_REV; dump(p,d)

def mutate_invariants_acceptance():
    p=SOURCE/'10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'; d=load(p); inv=d.setdefault('invariants',{})
    inv['ATOMIC_BASIC_DESIGN_MATERIALIZATION']={'required_artifact':'BASIC_DESIGN_ATOMIC_MATERIALIZATION_LEDGER','complete_applicable_denominator_must_be_individually_materialized':True,'representative_sample_may_satisfy_denominator':False,'group_or_capability_summary_may_replace_rows':False,'status_label_only_may_receive_coverage_credit':False,'required_row_fields':['canonical_identity','owner','entity_operation_or_utility','preconditions','inputs_or_sources','output_or_result','state_effect','gate','permission_or_role','workbench','section','component','control_or_trigger','field_or_input','visual_binding_or_non_visual_classification','next_step','error_or_blocked_condition','recovery','acceptance_or_design_review','authority_refs'],'not_applicable_requires_evidence':True,'blank_or_silent_omission_credit':False,'missing_applicable_row':'BLOCK','missing_required_row_field':'BLOCK','missing_required_binding':'BLOCK','summary_only_substitution':'BLOCK','representative_sample_substitution':'BLOCK'}
    inv['BASIC_DESIGN_DENOMINATOR_RECONCILIATION']={'required_artifacts':['BASIC_DESIGN_DENOMINATOR_SNAPSHOT','BASIC_DESIGN_DELIVERABLE_RECONCILIATION'],'machine_and_human_denominator_identity_required':True,'uid_level_reconciliation_required':True,'machine_required_count_equals_human_represented_count':True,'missing_required_uid_count':0,'duplicate_credit_count':0,'summary_only_credit_count':0,'representative_sample_credit_count':0,'human_machine_denominator_mismatch_count':0,'unclassified_applicability_count':0,'external_only_detail_may_substitute_human_review_detail':False,'mismatch':'BLOCK'}
    inv['BASIC_DESIGN_EXECUTION_DETAIL_COMPLETENESS']={'required_chain':['IDENTITY','OWNER','PRECONDITIONS','INPUTS_OR_SOURCES','OPERATION_OR_ACTION','OUTPUT','STATE_EFFECT','GATE','PERMISSION','WORKBENCH','SECTION','COMPONENT','CONTROL_OR_TRIGGER','FIELD','VISUAL_STATE_OR_ANCHOR','NEXT_STEP','ERROR_OR_BLOCKED_CONDITION','RECOVERY','CROSS_PAGE_OR_HANDOFF_WHEN_APPLICABLE','ACCEPTANCE'],'legal_and_blocked_transitions_required_when_state_bearing':True,'async_pending_success_failure_retry_semantics_required_when_applicable':True,'permission_enabled_disabled_hidden_reason_semantics_required_when_applicable':True,'cross_page_exit_identity_trigger_entry_failure_resume_back_required_when_applicable':True,'undefined_required_detail_is_design_gap':True,'ai_may_invent_missing_product_decision':False,'downstream_evidence_may_retroactively_close_incomplete_basic_design':False}
    d['governance_revision']=NEW_SOURCE_REV; dump(p,d)
    p=SOURCE/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'; a=load(p); c=a.setdefault('product_neutral_entity_lifecycle_contract',{})
    for k in ['atomic_basic_design_materialization_required','complete_denominator_enumeration_required','row_level_design_binding_required','basic_design_denominator_snapshot_required','human_machine_design_deliverable_reconciliation_required','no_summary_substitution_required','no_representative_sample_credit_required','execution_detail_chain_complete_required','zero_silent_omission_required','zero_summary_only_credit_required','zero_representative_sample_credit_required','zero_human_machine_denominator_mismatch_required','zero_unclassified_applicability_required']: c[k]=True
    c['missing_atomic_design_row']='BLOCK'; c['missing_required_design_binding']='BLOCK'; c['summary_only_design_completion_claim']='BLOCK'; a['governance_revision']=NEW_SOURCE_REV; dump(p,a)

def mutate_current_policy():
    p=ROOT/'governance/specifications/current/BOUNDED_FUNCTIONAL_COMPLETION.yaml'; d=load(p); r=d.setdefault('rules',{})
    r['ATOMIC_BASIC_DESIGN_MATERIALIZATION']={'required_artifact':'BASIC_DESIGN_ATOMIC_MATERIALIZATION_LEDGER','complete_applicable_denominator_row_level_required':True,'representative_sample_substitution':'BLOCK','summary_only_substitution':'BLOCK','status_label_only_credit':False,'missing_applicable_row':'BLOCK','missing_required_binding':'BLOCK','not_applicable_requires_evidence':True}
    r['BASIC_DESIGN_DENOMINATOR_RECONCILIATION']={'required_artifacts':['BASIC_DESIGN_DENOMINATOR_SNAPSHOT','BASIC_DESIGN_DELIVERABLE_RECONCILIATION'],'uid_level_human_machine_reconciliation_required':True,'missing_required_uid_count':0,'duplicate_credit_count':0,'summary_only_credit_count':0,'representative_sample_credit_count':0,'human_machine_denominator_mismatch_count':0,'unclassified_applicability_count':0}
    r['BASIC_DESIGN_EXECUTION_DETAIL_COMPLETENESS']={'complete_operation_chain_required':True,'undefined_required_detail_is_design_gap':True,'ai_invention_of_missing_product_decision':'BLOCK','downstream_evidence_retroactive_design_completion':'BLOCK'}
    d['schema_version']=6; dump(p,d)

def mutate_stage_refs():
    mapping={'STAGE-02':['WEB-GOV-01-S084'],'STAGE-03':['WEB-GOV-01-S084'],'STAGE-04':['WEB-GOV-01-S084','WEB-GOV-01-S085','WEB-GOV-01-S086']}
    p=SOURCE/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'; d=load(p)
    for st in d.get('stages',[]): unique_extend(st.setdefault('required_normative_section_uids',[]),mapping.get(st.get('stage_uid'),[]))
    d['governance_revision']=NEW_SOURCE_REV; dump(p,d)
    p=SOURCE/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'; d=load(p)
    for uid,vals in mapping.items(): unique_extend(d['stage_reference_rules'][uid]['exact_required_normative_section_uids'],vals)
    d['governance_revision']=NEW_SOURCE_REV; dump(p,d)

def harden_validator():
    p=SOURCE/'09_TESTS/governance/validate_product_neutral_entity_lifecycle.py'; s=p.read_text(encoding='utf-8')
    anchor="    for uid in ['WEB-GOV-01-S076','WEB-GOV-01-S077','WEB-GOV-01-S078','WEB-GOV-01-S079','WEB-GOV-01-S080','WEB-GOV-01-S081','WEB-GOV-01-S082','WEB-GOV-01-S083']:"
    block="""    am=inv.get('ATOMIC_BASIC_DESIGN_MATERIALIZATION') or {}
    if am.get('complete_applicable_denominator_must_be_individually_materialized') is not True or am.get('representative_sample_may_satisfy_denominator') is not False or am.get('group_or_capability_summary_may_replace_rows') is not False or am.get('status_label_only_may_receive_coverage_credit') is not False or am.get('missing_applicable_row')!='BLOCK' or am.get('summary_only_substitution')!='BLOCK' or len(am.get('required_row_fields') or [])<20: failures.append('atomic_basic_design_materialization_invalid')
    dr=inv.get('BASIC_DESIGN_DENOMINATOR_RECONCILIATION') or {}
    if set(dr.get('required_artifacts') or [])!={'BASIC_DESIGN_DENOMINATOR_SNAPSHOT','BASIC_DESIGN_DELIVERABLE_RECONCILIATION'} or dr.get('machine_and_human_denominator_identity_required') is not True or dr.get('uid_level_reconciliation_required') is not True or any(int(dr.get(k,-1))!=0 for k in ['missing_required_uid_count','duplicate_credit_count','summary_only_credit_count','representative_sample_credit_count','human_machine_denominator_mismatch_count','unclassified_applicability_count']) or dr.get('mismatch')!='BLOCK': failures.append('basic_design_denominator_reconciliation_invalid')
    ed=inv.get('BASIC_DESIGN_EXECUTION_DETAIL_COMPLETENESS') or {}
    if len(ed.get('required_chain') or [])<20 or ed.get('undefined_required_detail_is_design_gap') is not True or ed.get('ai_may_invent_missing_product_decision') is not False or ed.get('downstream_evidence_may_retroactively_close_incomplete_basic_design') is not False: failures.append('basic_design_execution_detail_completeness_invalid')
    for k in ['atomic_basic_design_materialization_required','complete_denominator_enumeration_required','row_level_design_binding_required','basic_design_denominator_snapshot_required','human_machine_design_deliverable_reconciliation_required','no_summary_substitution_required','no_representative_sample_credit_required','execution_detail_chain_complete_required','zero_silent_omission_required','zero_summary_only_credit_required','zero_representative_sample_credit_required','zero_human_machine_denominator_mismatch_required','zero_unclassified_applicability_required']:
        if c.get(k) is not True: failures.append('acceptance_atomic_design_rule_missing:'+k)
    if c.get('missing_atomic_design_row')!='BLOCK' or c.get('missing_required_design_binding')!='BLOCK' or c.get('summary_only_design_completion_claim')!='BLOCK': failures.append('acceptance_atomic_design_fail_closed_invalid')
"""
    if 'atomic_basic_design_materialization_invalid' not in s:
        if anchor not in s: raise RuntimeError('validator anchor missing')
        newanchor=anchor.replace("'WEB-GOV-01-S083']","'WEB-GOV-01-S083','WEB-GOV-01-S084','WEB-GOV-01-S085','WEB-GOV-01-S086']")
        s=s.replace(anchor,block+newanchor,1)
    p.write_text(s,encoding='utf-8')

def update_source_revisions():
    targets=['10_REGISTRY/AUDIT_CATALOG.yaml','10_REGISTRY/BLUEPRINT_REGISTRY.yaml','10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml','10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml','10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml','10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml','10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml','10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml','10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml','10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml','11_EVIDENCE/audit/AUDIT_BASELINE.yaml','11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml']
    for rel in targets:
        p=SOURCE/rel
        if p.exists():
            d=load(p)
            if 'governance_revision' in d: d['governance_revision']=NEW_SOURCE_REV
            dump(p,d)

def append_version_notes():
    notes=[('README.md','v2.2.12 atomic basic design materialization','## v2.2.12 atomic basic design materialization\nBasic Design completeness requires full row-level denominator materialization, no summary/sample substitution, exact human/machine denominator reconciliation, and execution-detail completeness before Freeze. Page count is never a completeness metric.'),('VERSIONING_RULE.md','v2.2.12 basic design atomic materialization rule','## v2.2.12 basic design atomic materialization rule\n- v2.2.11 remains immutable predecessor history.\n- Normative content changed, therefore Current Governance UID and display version must change.\n- Required design denominators must be enumerated row-by-row; summary-only or representative-sample completion is forbidden.\n- Human and machine design deliverables must reconcile to the same exact required denominator before Basic Design Freeze.')]
    for rel,marker,text in notes:
        p=SOURCE/rel; s=p.read_text(encoding='utf-8')
        if marker not in s: p.write_text(s.rstrip()+'\n\n'+text+'\n',encoding='utf-8')

def regenerate_source_identity():
    run(sys.executable,str(SOURCE/'09_TESTS/governance/compile_governance_baseline.py'))
    sem=load(SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'); semantic_hash=sem.get('content_hash')
    if not semantic_hash: raise RuntimeError('semantic baseline hash missing')
    replace_const(SOURCE/'09_TESTS/governance/validate_reference_semantics.py','SEMANTIC_BASELINE_CONTENT_HASH',semantic_hash)
    run(sys.executable,str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'))
    checks=SOURCE/'CHECKSUMS.sha256'; files=sorted([p for p in SOURCE.rglob('*') if p.is_file() and p!=checks],key=lambda p:p.relative_to(SOURCE).as_posix())
    checks.write_text(''.join(f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in files),encoding='utf-8')
    allfiles=sorted([p for p in SOURCE.rglob('*') if p.is_file()],key=lambda p:p.relative_to(SOURCE).as_posix())
    if len(allfiles)!=75: raise RuntimeError(f'source file count changed: {len(allfiles)}')
    tb=io.BytesIO()
    with tarfile.open(fileobj=tb,mode='w',format=tarfile.PAX_FORMAT) as tf:
        for p in allfiles:
            rel=p.relative_to(SOURCE).as_posix(); info=tf.gettarinfo(str(p),arcname=rel); info.uid=info.gid=0; info.uname=info.gname=''; info.mtime=0
            with p.open('rb') as fh: tf.addfile(info,fh)
    bundle_hash=hashlib.sha256(lzma.compress(tb.getvalue(),format=lzma.FORMAT_XZ,preset=9)).hexdigest()
    zb=io.BytesIO()
    with zipfile.ZipFile(zb,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for p in allfiles:
            rel=p.relative_to(SOURCE).as_posix(); zi=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0)); zi.compress_type=zipfile.ZIP_DEFLATED; zi.create_system=3
            mode=0o755 if (p.stat().st_mode & 0o111) else 0o644; zi.external_attr=(mode&0xFFFF)<<16; zf.writestr(zi,p.read_bytes())
    zip_hash=hashlib.sha256(zb.getvalue()).hexdigest(); checks_hash=sha(checks)
    replace_const(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py','EXPECTED_BUNDLE_SHA256',bundle_hash); replace_const(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py','EXPECTED_SOURCE_ZIP_SHA256',zip_hash)
    for name,val in [('EXPECTED_CHECKSUMS_SHA256',checks_hash),('EXPECTED_SEMANTIC_CONTENT_HASH',semantic_hash),('EXPECTED_SOURCE_ZIP_SHA256',zip_hash),('EXPECTED_BUNDLE_SHA256',bundle_hash)]: replace_const(ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py',name,val)
    return semantic_hash,checks_hash,bundle_hash,zip_hash

def update_current(semantic_hash,checks_hash,bundle_hash,zip_hash):
    p=ROOT/'GOVERNANCE_CURRENT.yaml'; d=load(p); d['active_governance_uid']=NEW_UID; d['display_version']=NEW_DISPLAY; d['source_identity'].update({'verified_package_sha256':zip_hash,'deterministic_source_bundle_sha256':bundle_hash,'checksum_manifest_sha256':checks_hash,'semantic_authority_content_hash':semantic_hash,'verified_source_revision':NEW_SOURCE_REV,'source_bytes_changed_by_current_successor':True}); dump(p,d)
    p=ROOT/'governance/specifications/REGISTRY.yaml'; d=load(p); d['active_specification']['governance_uid']=NEW_UID; d['active_specification']['display_version']=NEW_DISPLAY; unique_extend(d['active_specification'].setdefault('aliases',[]),['basic-design-atomic-materialization-hardening']); d['immediate_predecessor']={'governance_uid':OLD_UID,'display_version':OLD_DISPLAY,'version_role':'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY','status':'SUPERSEDED_HISTORY_ONLY_AFTER_BASIC_DESIGN_ATOMIC_MATERIALIZATION_HARDENING'}; dump(p,d)
    p=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'; d=load(p); oldsl=copy.deepcopy(d.get('source_lineage') or {}); d['artifact_uid']=NEW_UID; d['display_version']=NEW_DISPLAY; d['source_lineage'].update({'verified_package_filename':NEW_PACKAGE,'verified_package_sha256':zip_hash,'predecessor_governance_uid':OLD_UID,'promotion_authorization_uid':AUTH_UID,'source_bytes_changed_by_this_successor':True,'source_identity_reused_only_because_source_bytes_are_unchanged':False,'deterministic_source_bundle_sha256':bundle_hash,'checksum_manifest_sha256':checks_hash,'semantic_authority_content_hash':semantic_hash,'verified_source_revision':NEW_SOURCE_REV,'predecessor_verified_package_filename':oldsl.get('verified_package_filename'),'predecessor_verified_package_sha256':oldsl.get('verified_package_sha256'),'post_promotion_projector_sync_authorization_uid':AUTH_UID}); dump(p,d)
    for rel in ['governance/test/ACTIVE_STATE.yaml','governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml','governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml','governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml']:
        p=ROOT/rel
        if p.exists():
            d=deep_replace(load(p),OLD_UID,NEW_UID)
            if rel.endswith('ACTIVE_STATE.yaml'):
                d['specification_uid']=NEW_UID; d['status']='ACTIVE_GOVERNANCE_BASIC_DESIGN_ATOMIC_MATERIALIZATION_PROMOTED_REVALIDATION_REQUIRED'; d['next_action']='RUN_SUCCESSOR_EXACT_HEAD_VALIDATION_THEN_REEXECUTE_BASIC_DESIGN_WITH_ATOMIC_FULL_DENOMINATOR_DETAIL'; d.setdefault('governance_revision_transition',{}).update({'predecessor_governance_uid':OLD_UID,'current_governance_uid':NEW_UID,'fresh_revalidation_required':True})
            dump(p,d)

def validate_all():
    env=os.environ.copy(); env['PYTHONDONTWRITEBYTECODE']='1'; env['PYTHONPYCACHEPREFIX']='/tmp/acpos-basic-design-atomic-pycache'
    cmds=[[sys.executable,str(SOURCE/'09_TESTS/governance/validate_section_registry.py')],[sys.executable,str(SOURCE/'09_TESTS/governance/validate_reference_semantics.py')],[sys.executable,str(SOURCE/'09_TESTS/governance/validate_product_neutral_entity_lifecycle.py')],[sys.executable,str(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py')],[sys.executable,str(ROOT/'governance/ci/governance_resolver.py')],[sys.executable,str(ROOT/'governance/ci/validate_governance_portability.py')],[sys.executable,str(ROOT/'governance/ci/validate_active_consumer_reference_integrity.py')],[sys.executable,str(ROOT/'governance/ci/validate_structured_mutation_safety.py')],[sys.executable,str(ROOT/'governance/ci/validate_selected_execution_profile_integrity.py')],[sys.executable,str(ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py')]]
    for cmd in cmds:
        cp=run(*cmd,check=False,env=env); print('$',' '.join(map(str,cmd))); print(cp.stdout[-4000:])
        if cp.returncode: print(cp.stderr[-6000:],file=sys.stderr); raise SystemExit(cp.returncode)

def main():
    if not (ROOT/f'governance/test/spec_change_authorizations/{AUTH_UID}.yaml').exists(): raise RuntimeError('PREEXISTING_AUTHORIZATION_MISSING')
    if load(ROOT/'GOVERNANCE_CURRENT.yaml').get('active_governance_uid')!=OLD_UID: raise RuntimeError('CURRENT_GOVERNANCE_DRIFT')
    mutate_mother(); mutate_section_registry(); mutate_invariants_acceptance(); mutate_current_policy(); mutate_stage_refs(); harden_validator(); update_source_revisions(); append_version_notes()
    semantic_hash,checks_hash,bundle_hash,zip_hash=regenerate_source_identity(); update_current(semantic_hash,checks_hash,bundle_hash,zip_hash); validate_all()
    for p in [ROOT/'.github/governance-maintenance/BASIC_DESIGN_ATOMIC_MATERIALIZATION_PROMOTE_TRIGGER',ROOT/'.github/workflows/basic-design-atomic-materialization-promotion.yml',ROOT/'.github/governance-maintenance/promote_basic_design_atomic_materialization.py']:
        if p.exists(): p.unlink()
    run('git','config','user.name','github-actions[bot]'); run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'); run('git','add','-A')
    msg='feat(governance): enforce atomic basic-design materialization\n\nSpec-Change-Authorization: '+AUTH_UID+'\nSpec-Change-Scope: BASIC_DESIGN_ATOMIC_DENOMINATOR_ROW_LEVEL_DETAIL_NO_SUMMARY_SUBSTITUTION_AND_DELIVERABLE_RECONCILIATION'
    run('git','commit','-m',msg); run(sys.executable,str(ROOT/'governance/ci/specification_mutation_guard.py')); run('git','push','origin','HEAD:rebuild-v2.1.1')
    print('PROMOTION_PUSHED',run('git','rev-parse','HEAD').stdout.strip()); print(json.dumps({'new_uid':NEW_UID,'display_version':NEW_DISPLAY,'semantic_hash':semantic_hash,'checksums_hash':checks_hash,'bundle_hash':bundle_hash,'zip_hash':zip_hash},indent=2))
if __name__=='__main__': main()
