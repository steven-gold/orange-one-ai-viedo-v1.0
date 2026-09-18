#!/usr/bin/env python3
from pathlib import Path
import hashlib, io, json, lzma, re, shutil, subprocess, tarfile, zipfile, yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
AUTH_UID='USR-DIRECTIVE-20260918-MOTHER-DESIGN-REMEDIATION-ROUTING-HARDENING-R2'
OLD_UID='GOV-REV-20260918-RESIDUAL-CLASSIFICATION-HARDENING'
NEW_UID='GOV-REV-20260918-DESIGN-REMEDIATION-ROUTING-HARDENING'
DISPLAY_VERSION='v2.2.5'
SOURCE_REVISION='v2.2.4-design-remediation-routing-hardening'
PACKAGE_FILENAME='AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.4_DESIGN_REMEDIATION_ROUTING_HARDENING_LOCAL_VERIFIED.zip'
AUTH=ROOT/f'governance/test/spec_change_authorizations/{AUTH_UID}.yaml'
HELPER=ROOT/'.github/governance-maintenance/materialize_design_remediation_routing_successor.py'
WORKFLOW=ROOT/'.github/workflows/design-remediation-routing-successor.yml'

M1=SOURCE/'12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md'
M2=SOURCE/'12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md'
M3=SOURCE/'12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md'
M4=SOURCE/'12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md'

def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def write(p,d): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(*a,cwd=ROOT): print('+',' '.join(map(str,a))); subprocess.run(a,cwd=cwd,check=True)
def repl(text,old,new,label):
    n=text.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected exactly one anchor, got {n}')
    return text.replace(old,new,1)

def patch_mother():
    t=M1.read_text(encoding='utf-8')
    anchor='Automatic completion is permitted only for the minimal closure set needed to close the registered REQUIRED gap. Generic CRUD completion, sibling-feature symmetry, "best practice" expansion, speculative convenience features, or adding a new Business Entity merely because a related Entity exists are forbidden. Every transitive dependency MUST independently pass admission. Auto-completion MUST traverse only the frozen registered dependency closure; discovery of a new dependency or Entity outside that closure MUST stop automation and reopen functional/visual design. Cycles MUST be detected and blocked. Completion MUST stop immediately when the seed REQUIRED gaps are closed and no unresolved REQUIRED edge remains inside the frozen closure.'
    add=anchor+'''\n\nWhen a local required functional gap is classified as \`INPUT_SOURCE_GAP\` or \`ARCHITECTURE_GAP\`, and Current Authority does not already contain one uniquely role-correct exact closure, the executor MUST NOT convert the absence of an exact value directly into field-by-field Product Authority input. The scope MUST first enter bounded review-only Design/Contract Remediation. Before proposing missing contract content, the executor MUST materialize the applicable \`FUNCTION_ADMISSION_SCORECARD\` and \`AUTO_COMPLETION_SCOPE_LEDGER\`, freeze the minimal dependency closure, reuse existing Current identities where role-correct, and produce a non-normative Design/Contract Candidate that is explicitly not Product Authority.\n\nThe candidate MAY group multiple blocker identities into one coherent review package when they share one functional design decision boundary. Candidate analysis, semantic review, package review preparation, and destructive testing receive zero product blocker reduction. If two or more materially distinct viable product behaviors remain, that decision MUST be classified \`AUTHORITY_GAP\` and requires explicit Product Authority selection. If a coherent candidate is approved, the approved content MUST first be materialized into the single Current canonical product Contract/Authority owner with revision/provenance before R7 or any equivalent authority-ingestion/materialization step may consume it. Review-only candidate bytes MUST_NOT be consumed as Current Authority.'''
    M1.write_text(repl(t,anchor,add,'M1 bounded completion'),encoding='utf-8')

    t=M2.read_text(encoding='utf-8')
    anchor='自動補齊 MUST 以「補完整前後步驟」為目的，不得只為了讓 UI 看起來完整而新增按鈕。'
    add=anchor+'''\n\n對 \`INPUT_SOURCE_GAP\` / \`ARCHITECTURE_GAP\`，Production Closure 仍 MUST BLOCK，但「缺少既有 exact value」本身不得直接等同於逐欄 Product Authority 輸入。若沒有唯一可自動補齊值，MUST 先回到正式 Design/Contract Remediation：以既有 Business Entity、Operation、Functional Chain、Topology、State、Runtime/Port、Error/Recovery 與 Visual Impact 為邊界，建立 \`FUNCTION_ADMISSION_SCORECARD\`、\`AUTO_COMPLETION_SCOPE_LEDGER\` 與 non-normative review-only Design/Contract Candidate。\n\n只有候選分析後仍存在兩種以上 materially distinct viable product behaviors 的項目才轉為 \`AUTHORITY_GAP\` 交由 Product Authority 選擇。可形成單一一致設計邊界的多筆 blocker MAY 以一份 coherent package review，而不得預設要求使用者逐欄填值。任何 approved candidate 必須先回寫到單一 Current canonical product Contract/Authority owner，再由 R7 或等價 ingestion 消費；Candidate/Test/Evidence 不得直接成為 Authority。'''
    M2.write_text(repl(t,anchor,add,'M2 54B'),encoding='utf-8')

    t=M3.read_text(encoding='utf-8')
    anchor='自動修補完成後 MUST 回到原 Gap 的上一 Gate 重新驗證，禁止只跑新增 Test。'
    add='''對被禁止自動修改的 \`INPUT_SOURCE_GAP\` / \`ARCHITECTURE_GAP\`，禁止自動「產品修改」不代表禁止分析或設計候選。若 Current Authority 沒有唯一 exact closure，執行器 MUST 先建立 bounded review-only Design/Contract Remediation Work Unit，產生 Scorecard、Scope Ledger、最小依賴閉環與 non-normative Candidate；Candidate MUST 標示未批准、不可 materialize、不可取得 product credit。\n\n只有兩種以上 materially distinct viable product behaviors 才進 \`AUTHORITY_GAP\` / \`USER_DECISION_REQUIRED\`。同一 coherent design boundary 的多筆 blocker SHOULD 合併為單一 package review，而不是預設逐欄要求使用者填入。批准後仍 MUST 先 materialize 到單一 Current canonical product owner，才能進 ingestion/implementation。\n\n'''+anchor
    M3.write_text(repl(t,anchor,add,'M3 44B'),encoding='utf-8')

    t=M4.read_text(encoding='utf-8')
    anchor='任何 Required 功能只要有未關閉 Gap，該 Capability MUST_NOT PASS。'
    add=anchor+'''\n\nFunctional Chain Audit MUST additionally verify the remediation route. A local \`INPUT_SOURCE_GAP\` or \`ARCHITECTURE_GAP\` with no unique role-correct Current closure MUST show bounded Design/Contract Remediation evidence before direct Product Authority ingestion: applicable Scorecard, Scope Ledger, frozen minimal dependency closure, review-only Candidate, blocker coverage, semantic review, and explicit non-authority/non-materializable status. The mere absence of an existing exact value is insufficient evidence for field-by-field human authority wait.\n\nAudit MUST distinguish \`REVIEW_ONLY_DESIGN_CANDIDATE\` from \`AUTHORITY_GAP\`. Two or more materially distinct viable product behaviors require explicit Authority selection; a coherent package may cover multiple blocker identities. Candidate/test/governance evidence MUST carry zero product blocker reduction until approved content is materialized at the single Current canonical product owner and fresh execution proves the affected signatures closed.'''
    M4.write_text(repl(t,anchor,add,'M4 59C'),encoding='utf-8')

def patch_machine():
    p=ROOT/'governance/specifications/current/BOUNDED_FUNCTIONAL_COMPLETION.yaml'; d=load(p)
    r=d.setdefault('rules',{}).setdefault('BOUNDED_FUNCTIONAL_COMPLETION',{})
    r['local_input_or_architecture_gap_without_unique_current_closure']='REVIEW_ONLY_DESIGN_CONTRACT_REMEDIATION'
    r['missing_exact_value_alone_is_direct_field_by_field_authority_request']=False
    r['review_only_candidate_is_product_authority']=False
    r['coherent_package_review_may_cover_multiple_blockers']=True
    r['approved_candidate_must_materialize_to_single_current_product_owner_before_ingestion']=True
    r['candidate_analysis_product_blocker_reduction_credit']=0
    write(p,d)

    p=ROOT/'governance/specifications/current/EXECUTION_CYCLE_CONTROL.yaml'; d=load(p)
    d['design_contract_remediation_routing']={
      'applies_to_local_gap_classes':['INPUT_SOURCE_GAP','ARCHITECTURE_GAP'],
      'activation':'NO_UNIQUE_ROLE_CORRECT_CURRENT_CLOSURE',
      'direct_field_by_field_authority_wait_from_missing_value':'BLOCK',
      'required_pre_candidate_artifacts':['FUNCTION_ADMISSION_SCORECARD','AUTO_COMPLETION_SCOPE_LEDGER'],
      'candidate_layer':'RUN_STATE_NON_NORMATIVE_REVIEW_ONLY',
      'candidate_may_be_product_authority':False,
      'two_or_more_materially_distinct_viable_behaviors':'AUTHORITY_GAP_EXPLICIT_SELECTION_REQUIRED',
      'coherent_package_review_for_multiple_blockers':True,
      'approved_content_target':'SINGLE_CURRENT_CANONICAL_PRODUCT_CONTRACT_OWNER',
      'ingestion_before_owner_materialization':'BLOCK',
      'product_blocker_reduction_before_fresh_reexecution':0,
    }
    write(p,d)

    p=ROOT/'governance/specifications/current/VALIDATION_REMEDIATION_CLOSURE_PROTOCOL.yaml'; d=load(p)
    d['design_remediation_candidate_boundary']={
      'input_source_or_architecture_gap_may_skip_design_remediation_to_manual_field_wait':False,
      'review_only_candidate_may_be_authority':False,
      'review_only_candidate_may_be_r7_input':False,
      'package_review_may_bind_multiple_blocker_identities':True,
      'true_authority_gap_requires_explicit_selection':True,
      'approved_candidate_requires_single_owner_materialization_before_ingestion':True,
      'governance_or_candidate_test_product_credit':0,
      'fresh_product_reexecution_required_for_blocker_reduction':True,
    }
    write(p,d)

def patch_r5():
    p=ROOT/'governance/ci/build_stage02_product_design_authority_request_r5.py'
    t=p.read_text(encoding='utf-8')
    old="""        local_requests.append({
            **common,
            'request_uid': f'R5::{p.get("problem_uid")}',
            'authority_request': authority_requirement(str(p.get('category')), str(p.get('detail'))),
            'unlock_condition': 'SEPARATELY_APPROVED_CURRENT_ADMISSIBLE_PRODUCT_AUTHORITY_SUPPLIES_THE_EXACT_MISSING_BINDING_AND_VALIDATION_ACCEPTS_IT_WITHOUT_SEMANTIC_INFERENCE',
        })"""
    new="""        gap_class = str(p.get('gap_class') or '')
        if gap_class in {'INPUT_SOURCE_GAP', 'ARCHITECTURE_GAP'}:
            routing = 'REVIEW_ONLY_DESIGN_CONTRACT_REMEDIATION_REQUIRED'
            unlock = 'BOUNDED_DESIGN_REMEDIATION_PACKAGE_IS_REVIEWED_AND_APPROVED_CONTENT_IS_MATERIALIZED_TO_THE_SINGLE_CURRENT_CANONICAL_PRODUCT_CONTRACT_OWNER'
        elif gap_class == 'AUTHORITY_GAP':
            routing = 'EXPLICIT_PRODUCT_AUTHORITY_SELECTION_REQUIRED'
            unlock = 'EXPLICIT_PRODUCT_AUTHORITY_SELECTS_THE_MATERIALLY_DISTINCT_PRODUCT_BEHAVIOR_AND_APPROVED_CONTENT_IS_MATERIALIZED_TO_THE_SINGLE_CURRENT_CANONICAL_PRODUCT_CONTRACT_OWNER'
        else:
            routing = 'SEPARATELY_APPROVED_PRODUCT_AUTHORITY_REQUIRED'
            unlock = 'SEPARATELY_APPROVED_CURRENT_ADMISSIBLE_PRODUCT_AUTHORITY_SUPPLIES_THE_EXACT_MISSING_BINDING_AND_VALIDATION_ACCEPTS_IT_WITHOUT_SEMANTIC_INFERENCE'
        local_requests.append({
            **common,
            'request_uid': f'R5::{p.get("problem_uid")}',
            'routing_disposition': routing,
            'authority_request': authority_requirement(str(p.get('category')), str(p.get('detail'))),
            'unlock_condition': unlock,
        })"""
    t=repl(t,old,new,'R5 local routing')
    old="state['next_action'] = 'AWAIT_OR_INGEST_SEPARATELY_APPROVED_CURRENT_STAGE02_AUTHORITY_REQUEST_R5_INPUTS; DO_NOT_MATERIALIZE_WITHOUT_APPROVED_AUTHORITY'"
    new="state['next_action'] = 'BUILD_AND_REVIEW_BOUNDED_NON_NORMATIVE_DESIGN_REMEDIATION_PACKAGE_FOR_LOCAL_INPUT_SOURCE_AND_ARCHITECTURE_GAPS; ROUTE_ONLY_TRUE_AUTHORITY_GAPS_TO_EXPLICIT_SELECTION; DO_NOT_R7_MATERIALIZE_REVIEW_ONLY_CANDIDATES'"
    t=repl(t,old,new,'R5 next action')
    p.write_text(t,encoding='utf-8')

def update_source_revision():
    for p in sorted((SOURCE/'10_REGISTRY').glob('*.yaml')):
        d=load(p)
        if d.get('governance_revision')=='v2.2.3-residual-classification-hardening':
            d['governance_revision']=SOURCE_REVISION; write(p,d)

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
    return hashlib.sha256(tb.getvalue()).hexdigest(),bundle,hashlib.sha256(zb.getvalue()).hexdigest()

def refresh_source():
    run('python',str(SOURCE/'09_TESTS/governance/compile_governance_baseline.py'),cwd=SOURCE/'09_TESTS/governance')
    run('python',str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'),cwd=SOURCE/'09_TESTS/governance')
    cp=SOURCE/'CHECKSUMS.sha256'
    fs=sorted(p for p in SOURCE.rglob('*') if p.is_file() and p!=cp)
    if len(fs)!=74: raise RuntimeError(f'CHECKSUM_TARGET_DENOMINATOR_DRIFT:{len(fs)}')
    cp.write_text(''.join(f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in fs),encoding='utf-8')
    checksum=sha(cp); _,bundle,zips=deterministic()
    vp=ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py'; v=vp.read_text(encoding='utf-8')
    v=re.sub(r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'",f"EXPECTED_BUNDLE_SHA256 = '{bundle}'",v,count=1)
    v=re.sub(r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'",f"EXPECTED_SOURCE_ZIP_SHA256 = '{zips}'",v,count=1)
    vp.write_text(v,encoding='utf-8')
    fp=ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'; f=fp.read_text(encoding='utf-8')
    f=re.sub(r"EXPECTED_CHECKSUMS_SHA256 = '[0-9a-f]+'",f"EXPECTED_CHECKSUMS_SHA256 = '{checksum}'",f,count=1)
    f=re.sub(r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'",f"EXPECTED_SOURCE_ZIP_SHA256 = '{zips}'",f,count=1)
    f=re.sub(r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'",f"EXPECTED_BUNDLE_SHA256 = '{bundle}'",f,count=1)
    fp.write_text(f,encoding='utf-8')
    return checksum,bundle,zips

def reset_stage02():
    ev=ROOT/'governance/test/stage02/STAGE02_CORE01_DESIGN_REMEDIATION_TEST_EVIDENCE.json'
    if ev.is_file():
        hist=ROOT/'governance/test/history/stage02/design-remediation-routing-20260918/STAGE02_CORE01_DESIGN_REMEDIATION_TEST_EVIDENCE.json'
        hist.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ev,hist)
    root=ROOT/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
    if root.exists(): shutil.rmtree(root)
    s2=ROOT/'governance/test/stage02'
    if s2.exists():
        for p in list(s2.iterdir()):
            if p.is_file(): p.unlink()
            elif p.is_dir(): shutil.rmtree(p)
    s2.mkdir(parents=True,exist_ok=True)
    reset={
      'schema_version':1,'artifact_type':'STAGE02_CLEAN_BASELINE_RESET_RECEIPT','normative_authority':False,
      'current_governance_uid':NEW_UID,'predecessor_governance_uid':OLD_UID,
      'reason':'POST_GOVERNANCE_PROMOTION_FRESH_RESTART_REQUIRED',
      'stage1_immutable_inputs_preserved':True,'current_stage02_generated_outputs_removed':True,
      'historical_design_remediation_test_evidence_ref':'governance/test/history/stage02/design-remediation-routing-20260918/STAGE02_CORE01_DESIGN_REMEDIATION_TEST_EVIDENCE.json',
      'product_stage_credit':0,'next_action':'RESOLVE_FRESH_CORE01_STAGE02_WORK_UNIT_AND_REBUILD_CANONICAL_PREFLIGHT_UNDER_CURRENT_GOVERNANCE'
    }
    write(s2/'STAGE02_CLEAN_BASELINE_RESET_RECEIPT.yaml',reset)

def patch_projectors(checksum,bundle,zips):
    p=ROOT/'governance/specifications/REGISTRY.yaml'; d=load(p); old=d['active_specification']
    if old.get('governance_uid')!=OLD_UID: raise RuntimeError('REGISTRY_CURRENT_UID_DRIFT')
    d['immediate_predecessor']={'governance_uid':OLD_UID,'display_version':old.get('display_version'),'version_role':'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY','status':'SUPERSEDED_HISTORY_ONLY_AFTER_DESIGN_REMEDIATION_ROUTING_HARDENING'}
    old['governance_uid']=NEW_UID; old['display_version']=DISPLAY_VERSION; old['status']='ACTIVE_CURRENT_GOVERNANCE'
    aliases=old.setdefault('aliases',[])
    if 'design-remediation-routing-hardening' not in aliases: aliases.append('design-remediation-routing-hardening')
    write(p,d)

    p=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'; d=load(p)
    d['artifact_uid']=NEW_UID; d['display_version']=DISPLAY_VERSION
    sl=d['source_lineage']; sl['predecessor_governance_uid']=OLD_UID; sl['promotion_authorization_uid']=AUTH_UID
    sl['verified_package_filename']=PACKAGE_FILENAME; sl['verified_package_sha256']=zips; sl['deterministic_source_bundle_sha256']=bundle; sl['checksum_manifest_sha256']=checksum
    sl['verified_source_revision']=SOURCE_REVISION; sl['source_bytes_changed_by_this_successor']=True; sl['source_identity_reused_only_because_source_bytes_are_unchanged']=False
    write(p,d)

    p=ROOT/'GOVERNANCE_CURRENT.yaml'; d=load(p); d['active_governance_uid']=NEW_UID; d['display_version']=DISPLAY_VERSION
    si=d['source_identity']; si['verified_package_sha256']=zips; si['deterministic_source_bundle_sha256']=bundle; si['checksum_manifest_sha256']=checksum; si['verified_source_revision']=SOURCE_REVISION; si['source_bytes_changed_by_current_successor']=True
    write(p,d)

    p=ROOT/'governance/test/ACTIVE_STATE.yaml'; a=load(p); a['specification_uid']=NEW_UID
    ex=a['execution']; ex['current_stage']='STAGE-01-CLOSED'; ex['website_construction_allowed']=False; ex['deployment_allowed']=False
    ex['stage2']={'result':'NOT_EXECUTED','stage_entry_gate':'REVERIFY_REQUIRED_AFTER_GOVERNANCE_PROMOTION','stage_exit_allowed':False,'prior_results_authoritative_for_next_run':False,'prior_results_used_in_current_run':False,'artifact_root_present':False,'revalidation_required_under_current_governance':True,'prior_results_authoritative_for_current_governance':False,'tested_page_uids':[],'remaining_page_uids':['CORE-01','ASSET-01'],'stage_scope_complete':False}
    a['status']='ACTIVE_STAGE1_CLOSED_STAGE2_CLEARED_AFTER_DESIGN_REMEDIATION_ROUTING_PROMOTION'
    a['next_action']='RESOLVE_FRESH_CORE01_STAGE02_WORK_UNIT_AND_REBUILD_CANONICAL_PREFLIGHT_UNDER_CURRENT_GOVERNANCE'
    a.pop('stage02_active_attempt',None); a.pop('active_work_unit',None)
    a['current_primary_task_layer']='GOVERNANCE_MAINTENANCE'; a['current_primary_task_authorization_uid']=AUTH_UID; a['current_primary_task_product_stage_credit']=0
    rc=a.setdefault('resume_control',{}); rc['current_resume_point']='POST_PROMOTION_STAGE2_FRESH_RESTART_REQUIRED'; rc['exact_next_action']=a['next_action']; rc['historical_stage2_results_are_current_state']=False; rc['stage2_execution_requires_fresh_entry_resolution']=True
    tr=a.setdefault('governance_revision_transition',{}); tr['predecessor_governance_uid']=OLD_UID; tr['current_governance_uid']=NEW_UID; tr['fresh_revalidation_required']=True; tr['fresh_revalidation_scope']='CORE01_STAGE02_FROM_CLEAN_STAGE1_BASELINE'; tr['website_construction_remains_blocked']=True; tr['deployment_remains_blocked']=True
    fl=a.setdefault('full_lifecycle_governance_system_test',{}); fl['deterministic_source_bundle_sha256']=bundle; fl['persisted_head_revalidation_required']=True; fl['full_line_github_result']='REVALIDATION_REQUIRED_AFTER_DESIGN_REMEDIATION_ROUTING_PROMOTION'; fl['terminal_run_conclusion']='REVALIDATION_REQUIRED'; fl['terminal_result_credit_allowed']=False
    proto=a.setdefault('stage_execution_remediation_closure_protocol',{}); proto['frozen_specification_uid']=NEW_UID; proto['binding_status']='CURRENT_POLICY_POST_PROMOTION_STAGE2_FRESH_RESTART_REQUIRED'
    a['stage02_reset_control']={'reset_uid':'RESET-STAGE02-20260918-DESIGN-REMEDIATION-ROUTING','directive':'CLEAR_CURRENT_STAGE02_GENERATED_OUTPUTS_AND_RERUN_AFTER_GOVERNANCE_PROMOTION','result_state':'ACTIVE_STAGE1_CLOSED_STAGE2_CLEARED','status':'ACTIVE_STAGE1_CLOSED_STAGE2_CLEARED','product_stage_output_root_removed':True,'current_stage02_runtime_evidence_removed':True,'current_stage02_findings_removed':True,'current_stage02_remediation_and_authority_request_outputs_removed':True,'current_stage02_counts_cleared':True,'preserved_stage1_immutable_inputs':True,'preserved_historical_stage02_evidence':True,'entry_receipts_must_be_regenerated_after_mother_review':True,'next_action_after_mother_review':a['next_action'],'product_stage_credit':0}
    write(p,a)

    p=ROOT/'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'; c=load(p)
    for f in c.get('findings') or []:
        if f.get('finding_uid')=='FIND-20260918-006':
            f['disposition']='ABSORBED_INTO_CANONICAL_OWNER_PENDING_PERSISTED_HEAD_REVALIDATION'; f['formal_specification_mutated_for_fix']=True; f['normative_promotion_authorization']=AUTH_UID; f['resolution_type']='CANONICAL_POLICY_AND_EXECUTION_ROUTING_ABSORPTION'
    c['current_stage2_execution']={'state':'NOT_EXECUTED','current_functional_gap_count':0,'current_closure_blocker_count':0,'active_evidence_present':False,'active_findings_present':False,'stage_exit_allowed':False,'website_construction_allowed':False,'deployment_allowed':False,'historical_counts_may_be_treated_as_current':False,'frozen_governance_uid':NEW_UID,'prior_stage2_results_used':False,'product_materialization_elimination_count':0,'external_authority_elimination_count':0,'total_fresh_elimination_count':0,'next_action':'RESOLVE_FRESH_CORE01_STAGE02_WORK_UNIT_AND_REBUILD_CANONICAL_PREFLIGHT_UNDER_CURRENT_GOVERNANCE'}
    write(p,c)

def main():
    if not AUTH.is_file(): raise RuntimeError('AUTHORIZATION_R2_MISSING')
    a=load(AUTH)
    if a.get('status')!='APPROVED_FOR_EXACT_SCOPE' or a.get('single_use') is not True: raise RuntimeError('AUTHORIZATION_R2_INVALID')
    if load(ROOT/'governance/specifications/REGISTRY.yaml')['active_specification']['governance_uid']!=OLD_UID: raise RuntimeError('CURRENT_GOVERNANCE_DRIFT')
    patch_mother(); patch_machine(); patch_r5(); update_source_revision()
    checksum,bundle,zips=refresh_source()
    reset_stage02(); patch_projectors(checksum,bundle,zips)
    run('python',str(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py'))
    run('python',str(ROOT/'governance/ci/governance_resolver.py'))
    run('python',str(ROOT/'governance/ci/validate_governance_portability.py'))
    run('python',str(ROOT/'governance/ci/validate_validation_remediation_closure_protocol.py'))
    run('python',str(SOURCE/'09_TESTS/governance/validate_section_registry.py'),cwd=SOURCE)
    run('python',str(SOURCE/'09_TESTS/governance/governance_management_contract_guard.py'),cwd=SOURCE)
    for rel in ['.github/governance-source/SOURCE_IDENTITY_REPORT.json','governance/test/ACTIVE_CONSUMER_REFERENCE_INTEGRITY_REPORT.json','governance/test/FINDING_CLOSURE_READINESS.json']:
        q=ROOT/rel
        if q.exists(): run('git','checkout','--',rel)
    if HELPER.exists(): HELPER.unlink()
    if WORKFLOW.exists(): WORKFLOW.unlink()
    run('git','diff','--check')
    print(json.dumps({'new_governance_uid':NEW_UID,'display_version':DISPLAY_VERSION,'source_revision':SOURCE_REVISION,'checksum_manifest_sha256':checksum,'deterministic_source_bundle_sha256':bundle,'deterministic_source_zip_sha256':zips},indent=2))

if __name__=='__main__': main()
