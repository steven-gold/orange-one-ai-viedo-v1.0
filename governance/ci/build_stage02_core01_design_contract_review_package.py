#!/usr/bin/env python3
from __future__ import annotations
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib, json, subprocess, sys
import yaml

ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
FINDINGS=ROOT/'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
CANDIDATES=ROOT/'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
REGISTRY=ROOT/'governance/specifications/REGISTRY.yaml'
R2=ROOT/'governance/test/stage02/STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION_R2.yaml'
PROBLEMS=ROOT/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/CURRENT_PROBLEM_REGISTER.yaml'
RAW=ROOT/'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml'
OUT=ROOT/'governance/test/stage02'
SCORE=OUT/'STAGE02_CORE01_FUNCTION_ADMISSION_SCORECARD.json'
LEDGER=OUT/'STAGE02_CORE01_AUTO_COMPLETION_SCOPE_LEDGER.json'
CANDIDATE=OUT/'STAGE02_CORE01_DESIGN_CONTRACT_CANDIDATE.json'
SEMANTIC=OUT/'STAGE02_CORE01_DESIGN_CONTRACT_SEMANTIC_REVIEW.json'
PACKAGE=OUT/'STAGE02_CORE01_DESIGN_CONTRACT_REVIEW_PACKAGE.json'
CURRENT_UID='GOV-REV-20260918-DESIGN-REMEDIATION-ROUTING-HARDENING'
ATTEMPT='STAGE02-FRESH-20260918-007'
WORK='WU-STAGE02-CORE01-FUNCTIONAL-REMEDIATION-002'
RAW_BLOB='9490f3bcc28c5511bc04d6c3ce53c026e3c4667f'
HIST={
 'score':'01cb8f05e27b53a8da57f6138ce6b80600415cad',
 'ledger':'2f604e984dc2872d03c606d7c60ce05af6bb7ff1',
 'candidate':'af8daae83fc9d3f4a099170498ecaf0347480081',
 'validation':'7dfbc9d02a693afa54ffa3d6f3db8798bc2b1324',
 'reference':'34fee3c38973ee43cdb6f5450e793f5e320b346c',
 'negative':'eab5121afa745dd2060f7a72805c7f5db7914e51',
 'semantic':'110574d03ae2549163c81b3dfea6034135067f31',
 'semantic_negative':'2c233f6a6c260609e36a86cd232bd9fd44c42761',
}
NEXT='REVIEW_CURRENT_CORE01_DESIGN_CONTRACT_REMEDIATION_PACKAGE'

def die(msg):
    print('BLOCK:',msg,file=sys.stderr); raise SystemExit(1)
def git(*args):
    cp=subprocess.run(['git',*args],cwd=ROOT,text=True,capture_output=True)
    if cp.returncode: die('GIT:'+cp.stderr.strip())
    return cp.stdout.strip()
def y(path):
    if not path.is_file(): die('MISSING:'+str(path.relative_to(ROOT)))
    o=yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(o,dict): die('MAPPING_REQUIRED:'+str(path.relative_to(ROOT)))
    return o
def jblob(sha):
    raw=git('cat-file','blob',sha)
    try: o=json.loads(raw)
    except Exception as exc: die(f'HISTORICAL_BLOB_JSON_INVALID:{sha}:{exc}')
    if not isinstance(o,dict): die('HISTORICAL_BLOB_MAPPING_REQUIRED:'+sha)
    return o
def dumpj(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=False)+'\n',encoding='utf-8')
def dumpy(path,obj):
    path.write_text(yaml.safe_dump(obj,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def coverage(units):
    return [uid for u in units for uid in (u.get('blocker_uids') or [])]
def semantic_payload(doc):
    rows=[]
    for u in doc.get('units') or []:
        rows.append({
          'target_uid':u.get('target_uid'),'category':u.get('category'),
          'blocker_uids':sorted(u.get('blocker_uids') or []),
          'missing_fields_or_relations':u.get('missing_fields_or_relations') or [],
          'current_context':u.get('current_context') or {},
          'proposal':u.get('proposal') or {},
        })
    rows.sort(key=lambda x:(x['category'] or '',x['target_uid'] or ''))
    return rows
def digest(obj):
    b=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(b).hexdigest()
def common(doc,uid,atype,head,sources):
    doc=deepcopy(doc)
    for k in ('test_candidate_only','source_candidate_ref','supporting_evidence'):
        doc.pop(k,None)
    doc.update({
      'schema_version':2,'artifact_uid':uid,'artifact_type':atype,
      'layer_classification':'RUN_STATE','normative_authority':False,
      'review_only_candidate':True,'current_governance_uid':CURRENT_UID,
      'attempt_uid':ATTEMPT,'source_head_sha':head,'work_unit_uid':WORK,'page_uid':'CORE-01',
      'sources':sources,
      'authority_safety':{
        'current_specification_mutated':False,'mother_governance_mutated':False,
        'raw_source_mutated':False,'canonical_product_contract_mutated':False,
        'candidate_is_product_authority':False,'candidate_may_materialize':False,
        'product_blocker_reduction_credit':0,'new_business_entity_created':False,
        'new_runtime_created':False,'new_api_or_port_created':False,
      },
    })
    return doc

registry=y(REGISTRY); state=y(STATE); r2=y(R2); problems=y(PROBLEMS)
gov=(registry.get('active_specification') or {}).get('governance_uid')
if gov!=CURRENT_UID or state.get('specification_uid')!=CURRENT_UID: die('CURRENT_GOVERNANCE_UID_DRIFT')
work=state.get('active_work_unit') or {}
if work.get('work_unit_uid')!=WORK or work.get('current_status')!='REVIEW_ONLY_DESIGN_CONTRACT_REMEDIATION_REQUIRED': die('CURRENT_WORK_UNIT_NOT_READY_FOR_REVIEW_ONLY_DESIGN_REMEDIATION')
if state.get('next_action')!='BUILD_CORE01_REVIEW_ONLY_DESIGN_CONTRACT_REMEDIATION_PACKAGE': die('CURRENT_NEXT_ACTION_DRIFT')
summary=r2.get('classification_summary') or {}
if int(r2.get('fresh_functional_gap_denominator') or 0)!=45 or int(r2.get('closure_blocker_denominator'))!=0: die('R2_DENOMINATOR_DRIFT')
if summary!={'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS':45}: die('R2_CLASSIFICATION_SUMMARY_DRIFT:'+repr(summary))
if r2.get('current_governance_uid')!=CURRENT_UID or r2.get('attempt_uid')!=ATTEMPT: die('R2_IDENTITY_DRIFT')
rows=problems.get('problems') or []
if len(rows)!=45 or int(problems.get('open_problem_count') or 0)!=45 or int(problems.get('resolved_problem_count') or 0)!=0: die('CURRENT_PROBLEM_REGISTER_DENOMINATOR_DRIFT')
if problems.get('current_governance_uid')!=CURRENT_UID or problems.get('attempt_uid')!=ATTEMPT: die('CURRENT_PROBLEM_REGISTER_IDENTITY_DRIFT')
problem_uids=[r.get('problem_uid') for r in rows]
if len(set(problem_uids))!=45 or any(not x for x in problem_uids): die('CURRENT_PROBLEM_UID_SET_INVALID')
classes=Counter(r.get('gap_class') for r in rows); cats=Counter(r.get('category') for r in rows)
if classes!=Counter({'ARCHITECTURE_GAP':29,'INPUT_SOURCE_GAP':16}): die('CURRENT_PROBLEM_CLASS_DRIFT:'+repr(classes))
if cats!=Counter({'STATE_TRANSITION_LEDGER_FIELD_MISSING':25,'PAYLOAD_INPUT_CONTRACT_MISSING':16,'AUDIT_EVENT_NODE_MISSING':4}): die('CURRENT_PROBLEM_CATEGORY_DRIFT:'+repr(cats))
if git('rev-parse','HEAD:'+str(RAW.relative_to(ROOT)))!=RAW_BLOB: die('CURRENT_RAW_BLOB_DRIFT')
head=git('rev-parse','HEAD')
hist={k:jblob(v) for k,v in HIST.items()}
hist_candidate=hist['candidate']; hist_score=hist['score']; hist_ledger=hist['ledger']
if set(coverage(hist_candidate.get('units') or []))!=set(problem_uids) or len(coverage(hist_candidate.get('units') or []))!=45: die('HISTORICAL_CANDIDATE_CURRENT_PROBLEM_IDENTITY_MISMATCH')
if set(coverage(hist_score.get('records') or []))!=set(problem_uids) or len(coverage(hist_score.get('records') or []))!=45: die('HISTORICAL_SCORECARD_CURRENT_PROBLEM_IDENTITY_MISMATCH')
scope=(hist_ledger.get('frozen_scope') or {})
if set(scope.get('source_blocker_uids') or [])!=set(problem_uids) or int(scope.get('source_blocker_count') or 0)!=45: die('HISTORICAL_SCOPE_LEDGER_CURRENT_PROBLEM_IDENTITY_MISMATCH')

sources={
 'current_problem_register':str(PROBLEMS.relative_to(ROOT)),
 'remediability_classification':str(R2.relative_to(ROOT)),
 'current_raw_authority_capture':str(RAW.relative_to(ROOT)),
 'current_raw_git_blob_sha':RAW_BLOB,
 'historical_test_template_candidate_blob_sha':HIST['candidate'],
 'historical_design_remediation_test_evidence':'governance/test/history/stage02/design-remediation-routing-20260918/STAGE02_CORE01_DESIGN_REMEDIATION_TEST_EVIDENCE.json',
}
score=common(hist_score,'STAGE02-CORE01-FUNCTION-ADMISSION-SCORECARD-CURRENT','FUNCTION_ADMISSION_SCORECARD',head,sources)
score['activation_reason']='CURRENT_V2_2_5_LOCAL_INPUT_OR_ARCHITECTURE_GAPS_REQUIRE_REVIEW_ONLY_DESIGN_CONTRACT_REMEDIATION'
score['denominator']={'source_blockers':45,'design_units':25}
score['review_status']='MACHINE_ADMISSION_PASS_PENDING_COHERENT_PACKAGE_REVIEW'
for rec in score.get('records') or []:
    rec['admission_result']='ADMIT_CURRENT_REVIEW_ONLY'
    rec['authority_effect']='NONE_UNTIL_EXPLICIT_PACKAGE_REVIEW_AND_CANONICAL_OWNER_PROMOTION'

ledger=common(hist_ledger,'STAGE02-CORE01-AUTO-COMPLETION-SCOPE-LEDGER-CURRENT','AUTO_COMPLETION_SCOPE_LEDGER',head,sources)
fs=ledger.get('frozen_scope') or {}
fs['source_blocker_uids']=sorted(problem_uids); fs['source_blocker_count']=45; fs['design_unit_count']=25
ledger['frozen_scope']=fs
ledger['closure_accounting']={
 'review_only_candidate_coverage':45,'current_product_blocker_reduction':0,
 'materializable_now':0,'stage02_status':'BLOCKED','stage03_allowed':False,
}
for rec in ledger.get('candidate_units') or []: rec['status']='REVIEW_ONLY_PROPOSED_NOT_AUTHORITY'
ledger['review_status']='FROZEN_MINIMAL_SCOPE_PENDING_COHERENT_PACKAGE_REVIEW'

candidate=common(hist_candidate,'STAGE02-CORE01-DESIGN-CONTRACT-CANDIDATE-CURRENT','NON_NORMATIVE_CORE01_DESIGN_CONTRACT_REVIEW_CANDIDATE',head,sources)
candidate['purpose']='REVIEWABLE_MINIMAL_DESIGN_CONTRACT_CANDIDATE_FOR_CURRENT_45_LOCAL_CORE01_GAPS_BEFORE_ANY_PRODUCT_AUTHORITY_PROMOTION'
candidate['status']='READY_FOR_EXPLICIT_COHERENT_PACKAGE_REVIEW'
candidate['materialization_allowed']=False
candidate['product_blocker_credit']=0
for unit in candidate.get('units') or []:
    unit['status']='REVIEW_ONLY_PROPOSED_NOT_AUTHORITY'
    unit['materialization_allowed']=False; unit['product_blocker_credit']=0
    unit['promotion_requirements']=[
      'CURRENT_REVIEW_ONLY_CANDIDATE_VALIDATION_PASS',
      'EXPLICIT_COHERENT_PRODUCT_CONTRACT_PACKAGE_REVIEW',
      'PROMOTE_APPROVED_CONTENT_TO_SINGLE_CURRENT_CANONICAL_PRODUCT_CONTRACT_OWNER_WITH_EXACT_PROVENANCE',
      'R7_OR_EQUIVALENT_INGESTION_ONLY_AFTER_CURRENT_OWNER_MATERIALIZATION',
      'FRESH_STAGE02_REEXECUTION_BEFORE_ANY_BLOCKER_REDUCTION',
    ]

hist_sig=semantic_payload(hist_candidate); cur_sig=semantic_payload(candidate)
if cur_sig!=hist_sig: die('CURRENT_CANDIDATE_PRODUCT_SEMANTIC_PAYLOAD_DRIFT_FROM_TESTED_TEMPLATE')
sem_digest=digest(cur_sig)
hval=hist['validation']; href=hist['reference']; hneg=hist['negative']; hsem=hist['semantic']; hsneg=hist['semantic_negative']
if (hval.get('validation') or {}).get('result')!='PASS' or (hval.get('validation') or {}).get('check_count')!=34 or (hval.get('validation') or {}).get('failed_check_count')!=0: die('HISTORICAL_CANDIDATE_VALIDATION_ANCHOR_INVALID')
if (href.get('result') or {}).get('object_ref_exact_current_identity_pass')!=23 or (href.get('result') or {}).get('opaque_ref_non_entity_pass')!=17: die('HISTORICAL_REFERENCE_IDENTITY_ANCHOR_INVALID')
if (hneg.get('result') or {}).get('pass')!=17 or (hneg.get('result') or {}).get('fail')!=0: die('HISTORICAL_NEGATIVE_ANCHOR_INVALID')
if (hsem.get('denominator') or {}).get('semantic_pass_units')!=25 or (hsem.get('denominator') or {}).get('semantic_fail_units')!=0: die('HISTORICAL_SEMANTIC_REVIEW_ANCHOR_INVALID')
if (hsneg.get('result') or {}).get('pass')!=12 or (hsneg.get('result') or {}).get('fail')!=0: die('HISTORICAL_SEMANTIC_NEGATIVE_ANCHOR_INVALID')

semantic={
 'schema_version':2,'artifact_uid':'STAGE02-CORE01-DESIGN-CONTRACT-SEMANTIC-REVIEW-CURRENT',
 'artifact_type':'NON_NORMATIVE_DESIGN_CONTRACT_SEMANTIC_REVIEW_RESULT','layer_classification':'RUN_STATE',
 'normative_authority':False,'review_only_candidate':True,'current_governance_uid':CURRENT_UID,
 'attempt_uid':ATTEMPT,'source_head_sha':head,'work_unit_uid':WORK,'page_uid':'CORE-01',
 'source_candidate_ref':str(CANDIDATE.relative_to(ROOT)),'source_candidate_semantic_sha256':sem_digest,
 'current_revalidation':{
   'current_problem_uid_set_exact_match_to_tested_template':True,'current_problem_count':45,
   'current_raw_git_blob_sha':RAW_BLOB,'raw_blob_exact_match_to_tested_template':True,
   'candidate_product_semantic_payload_exact_match_to_tested_template':True,
   'design_units':25,'blocker_coverage':45,'duplicate_blocker_coverage':0,
   'candidate_is_product_authority':False,'candidate_materialization_allowed':False,
   'product_blocker_reduction_credit':0,
 },
 'regression_anchors':{
   'historical_candidate_blob_sha':HIST['candidate'],
   'candidate_validation_34_of_34_blob_sha':HIST['validation'],
   'reference_identity_23_object_17_opaque_blob_sha':HIST['reference'],
   'destructive_negative_17_of_17_blob_sha':HIST['negative'],
   'semantic_review_25_of_25_blob_sha':HIST['semantic'],
   'semantic_negative_12_of_12_blob_sha':HIST['semantic_negative'],
 },
 'records':deepcopy(hsem.get('records') or []),
 'machine_review_result':'PASS_CURRENT_IDENTITY_AND_TESTED_SEMANTIC_TEMPLATE_REVALIDATION',
 'human_product_contract_review_status':'PENDING_EXPLICIT_COHERENT_PACKAGE_REVIEW',
 'authority_effect':'NONE','stage02_status':'BLOCKED','stage03_allowed':False,
}
for rec in semantic['records']:
    rec['semantic_disposition']='PASS_AS_CURRENT_REVIEW_ONLY_COHERENT_DESIGN_PROPOSAL_PENDING_SINGLE_PACKAGE_REVIEW'
    rec['authority_boundary']={'proposal_is_current_authority':False,'proposal_is_approved':False,'materialization_allowed':False,'product_blocker_reduction_credit':0}

package={
 'schema_version':2,'artifact_uid':'STAGE02-CORE01-DESIGN-CONTRACT-REVIEW-PACKAGE-CURRENT',
 'artifact_type':'NON_NORMATIVE_COHERENT_DESIGN_CONTRACT_REVIEW_PACKAGE','layer_classification':'RUN_STATE',
 'normative_authority':False,'review_only_candidate':True,'current_governance_uid':CURRENT_UID,
 'attempt_uid':ATTEMPT,'source_head_sha':head,'work_unit_uid':WORK,'page_uid':'CORE-01',
 'package_scope':{'source_blockers':45,'design_units':25,'categories':dict(cats),'gap_classes':dict(classes)},
 'artifact_refs':{
   'function_admission_scorecard':str(SCORE.relative_to(ROOT)),
   'auto_completion_scope_ledger':str(LEDGER.relative_to(ROOT)),
   'design_contract_candidate':str(CANDIDATE.relative_to(ROOT)),
   'semantic_review':str(SEMANTIC.relative_to(ROOT)),
 },
 'review_model':{
   'one_coherent_package_review_supported':True,'field_by_field_user_approval_required':False,
   'reviewer_role':'USER_OR_AUTHORIZED_PRODUCT_CONTRACT_REVIEWER',
   'status':'PENDING_EXPLICIT_COHERENT_PACKAGE_REVIEW',
   'approval_does_not_auto_materialize':True,
   'approved_content_requires_separate_current_canonical_owner_promotion':True,
 },
 'safety':{
   'candidate_is_product_authority':False,'candidate_may_be_used_as_current_authority':False,
   'candidate_materialization_allowed':False,'product_blocker_reduction_credit':0,
   'current_specification_mutated':False,'raw_source_mutated':False,'stage03_allowed':False,
   'website_construction_allowed':False,'deployment_allowed':False,
 },
 'machine_validation_expectations':{
   'current_problem_coverage':'45/45','design_units':25,'historical_candidate_validation':'34/34',
   'reference_identity':'23/23 object refs + 17/17 opaque refs','destructive_negative':'17/17',
   'semantic_review':'25/25','semantic_negative':'12/12',
 },
 'next_action':'EXPLICIT_COHERENT_PACKAGE_REVIEW_DECISION_REQUIRED',
}

OUT.mkdir(parents=True,exist_ok=True)
for path,obj in ((SCORE,score),(LEDGER,ledger),(CANDIDATE,candidate),(SEMANTIC,semantic),(PACKAGE,package)): dumpj(path,obj)

state['next_action']=NEXT
work=state.setdefault('active_work_unit',{})
work['current_status']='PENDING_EXPLICIT_COHERENT_PACKAGE_REVIEW'
work['entry_action']=NEXT
work['function_admission_scorecard_ref']=str(SCORE.relative_to(ROOT))
work['auto_completion_scope_ledger_ref']=str(LEDGER.relative_to(ROOT))
work['design_contract_candidate_ref']=str(CANDIDATE.relative_to(ROOT))
work['design_contract_semantic_review_ref']=str(SEMANTIC.relative_to(ROOT))
work['coherent_review_package_ref']=str(PACKAGE.relative_to(ROOT))
work['human_product_contract_review_status']='PENDING_EXPLICIT_COHERENT_PACKAGE_REVIEW'
work['product_blocker_credit']=0
active=state.setdefault('stage02_active_attempt',{})
active['next_action']=NEXT
active['review_only_design_contract_package_ref']=str(PACKAGE.relative_to(ROOT))
active['candidate_materialization_allowed']=False
resume=state.setdefault('resume_control',{})
resume['current_resume_point']='STAGE2_CORE01_COHERENT_DESIGN_CONTRACT_PACKAGE_REVIEW'
resume['exact_next_action']=NEXT
dumpy(STATE,state)

findings=y(FINDINGS); findings['next_action']=NEXT; findings['review_only_design_contract_package_ref']=str(PACKAGE.relative_to(ROOT)); dumpy(FINDINGS,findings)
candidates=y(CANDIDATES); cur=candidates.setdefault('current_stage2_execution',{}); cur['next_action']=NEXT; cur['review_only_design_contract_package_ref']=str(PACKAGE.relative_to(ROOT)); cur['product_blocker_reduction_credit']=0; dumpy(CANDIDATES,candidates)

print('PASS: current v2.2.5 CORE-01 review-only design/contract package materialized')
print('PASS: current 45 problem identities exactly equal tested candidate blocker coverage')
print('PASS: candidate product semantic payload exactly equals tested template under unchanged CORE-01 raw blob')
print('PASS: 25 coherent design units, zero Authority effect, zero materialization, zero product blocker credit')
print('NEXT_ACTION='+NEXT)
