#!/usr/bin/env python3
from __future__ import annotations
from collections import Counter
from pathlib import Path
import hashlib, json, re, subprocess, sys
import yaml

ROOT=Path(__file__).resolve().parents[2]
CURRENT_UID='GOV-REV-20260918-DESIGN-REMEDIATION-ROUTING-HARDENING'
ATTEMPT='STAGE02-FRESH-20260918-007'
WORK='WU-STAGE02-CORE01-FUNCTIONAL-REMEDIATION-002'
RAW_BLOB='9490f3bcc28c5511bc04d6c3ce53c026e3c4667f'
NEXT='REVIEW_CURRENT_CORE01_DESIGN_CONTRACT_REMEDIATION_PACKAGE'
HIST={
 'candidate':'af8daae83fc9d3f4a099170498ecaf0347480081',
 'validation':'7dfbc9d02a693afa54ffa3d6f3db8798bc2b1324',
 'reference':'34fee3c38973ee43cdb6f5450e793f5e320b346c',
 'negative':'eab5121afa745dd2060f7a72805c7f5db7914e51',
 'semantic':'110574d03ae2549163c81b3dfea6034135067f31',
 'semantic_negative':'2c233f6a6c260609e36a86cd232bd9fd44c42761',
}
P={
 'state':ROOT/'governance/test/ACTIVE_STATE.yaml',
 'findings':ROOT/'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml',
 'candidates':ROOT/'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml',
 'registry':ROOT/'governance/specifications/REGISTRY.yaml',
 'r2':ROOT/'governance/test/stage02/STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION_R2.yaml',
 'problems':ROOT/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/CURRENT_PROBLEM_REGISTER.yaml',
 'raw':ROOT/'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
 'score':ROOT/'governance/test/stage02/STAGE02_CORE01_FUNCTION_ADMISSION_SCORECARD.json',
 'ledger':ROOT/'governance/test/stage02/STAGE02_CORE01_AUTO_COMPLETION_SCOPE_LEDGER.json',
 'candidate':ROOT/'governance/test/stage02/STAGE02_CORE01_DESIGN_CONTRACT_CANDIDATE.json',
 'semantic':ROOT/'governance/test/stage02/STAGE02_CORE01_DESIGN_CONTRACT_SEMANTIC_REVIEW.json',
 'package':ROOT/'governance/test/stage02/STAGE02_CORE01_DESIGN_CONTRACT_REVIEW_PACKAGE.json',
}
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
def j(path):
    if not path.is_file(): die('MISSING:'+str(path.relative_to(ROOT)))
    o=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(o,dict): die('JSON_MAPPING_REQUIRED:'+str(path.relative_to(ROOT)))
    return o
def jblob(sha):
    o=json.loads(git('cat-file','blob',sha))
    if not isinstance(o,dict): die('HISTORICAL_BLOB_MAPPING_REQUIRED:'+sha)
    return o
def coverage(units): return [x for u in units for x in (u.get('blocker_uids') or [])]
def semantic_payload(doc):
    rows=[]
    for u in doc.get('units') or []:
        rows.append({'target_uid':u.get('target_uid'),'category':u.get('category'),'blocker_uids':sorted(u.get('blocker_uids') or []),'missing_fields_or_relations':u.get('missing_fields_or_relations') or [],'current_context':u.get('current_context') or {},'proposal':u.get('proposal') or {}})
    rows.sort(key=lambda x:(x['category'] or '',x['target_uid'] or ''))
    return rows
def digest(obj): return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def walk(obj):
    if isinstance(obj,dict):
        yield obj
        for v in obj.values(): yield from walk(v)
    elif isinstance(obj,list):
        for v in obj: yield from walk(v)

state=y(P['state']); findings=y(P['findings']); candidates=y(P['candidates']); registry=y(P['registry']); r2=y(P['r2']); problems=y(P['problems'])
score=j(P['score']); ledger=j(P['ledger']); candidate=j(P['candidate']); semantic=j(P['semantic']); package=j(P['package'])
gov=(registry.get('active_specification') or {}).get('governance_uid')
if gov!=CURRENT_UID or state.get('specification_uid')!=CURRENT_UID: die('CURRENT_GOVERNANCE_IDENTITY_DRIFT')
work=state.get('active_work_unit') or {}
if work.get('work_unit_uid')!=WORK or work.get('current_status')!='PENDING_EXPLICIT_COHERENT_PACKAGE_REVIEW': die('CURRENT_WORK_UNIT_REVIEW_STATE_DRIFT')
if state.get('next_action')!=NEXT or (state.get('stage02_active_attempt') or {}).get('next_action')!=NEXT or findings.get('next_action')!=NEXT or (candidates.get('current_stage2_execution') or {}).get('next_action')!=NEXT: die('CURRENT_PROJECTOR_NEXT_ACTION_DRIFT')
if (state.get('resume_control') or {}).get('exact_next_action')!=NEXT: die('CURRENT_RESUME_NEXT_ACTION_DRIFT')
if int(r2.get('fresh_functional_gap_denominator') or 0)!=45 or int(r2.get('closure_blocker_denominator') or -1)!=0: die('R2_DENOMINATOR_DRIFT')
if (r2.get('classification_summary') or {})!={'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS':45}: die('R2_SUMMARY_DRIFT')
rows=problems.get('problems') or []; pids=[r.get('problem_uid') for r in rows]
if len(rows)!=45 or len(set(pids))!=45 or int(problems.get('open_problem_count') or 0)!=45: die('CURRENT_PROBLEM_DENOMINATOR_DRIFT')
classes=Counter(r.get('gap_class') for r in rows); cats=Counter(r.get('category') for r in rows)
if classes!=Counter({'ARCHITECTURE_GAP':29,'INPUT_SOURCE_GAP':16}): die('CURRENT_GAP_CLASS_DRIFT')
if cats!=Counter({'STATE_TRANSITION_LEDGER_FIELD_MISSING':25,'PAYLOAD_INPUT_CONTRACT_MISSING':16,'AUDIT_EVENT_NODE_MISSING':4}): die('CURRENT_GAP_CATEGORY_DRIFT')
if git('rev-parse','HEAD:'+str(P['raw'].relative_to(ROOT)))!=RAW_BLOB: die('CURRENT_RAW_BLOB_DRIFT')
raw_text=P['raw'].read_text(encoding='utf-8')

for name,doc,atype in [
 ('score',score,'FUNCTION_ADMISSION_SCORECARD'),('ledger',ledger,'AUTO_COMPLETION_SCOPE_LEDGER'),
 ('candidate',candidate,'NON_NORMATIVE_CORE01_DESIGN_CONTRACT_REVIEW_CANDIDATE'),
 ('semantic',semantic,'NON_NORMATIVE_DESIGN_CONTRACT_SEMANTIC_REVIEW_RESULT'),
 ('package',package,'NON_NORMATIVE_COHERENT_DESIGN_CONTRACT_REVIEW_PACKAGE')]:
    if doc.get('artifact_type')!=atype or doc.get('normative_authority') is not False or doc.get('review_only_candidate') is not True: die('ARTIFACT_AUTHORITY_BOUNDARY_DRIFT:'+name)
    if doc.get('current_governance_uid')!=CURRENT_UID or doc.get('attempt_uid')!=ATTEMPT or doc.get('work_unit_uid')!=WORK: die('ARTIFACT_IDENTITY_DRIFT:'+name)

units=candidate.get('units') or []
if len(units)!=25: die('CANDIDATE_DESIGN_UNIT_DENOMINATOR_DRIFT')
cuids=coverage(units)
if len(cuids)!=45 or len(set(cuids))!=45 or set(cuids)!=set(pids): die('CANDIDATE_BLOCKER_COVERAGE_DRIFT')
if set(coverage(score.get('records') or []))!=set(pids) or len(coverage(score.get('records') or []))!=45: die('SCORECARD_BLOCKER_COVERAGE_DRIFT')
fs=ledger.get('frozen_scope') or {}
if set(fs.get('source_blocker_uids') or [])!=set(pids) or int(fs.get('source_blocker_count') or 0)!=45 or int(fs.get('design_unit_count') or 0)!=25: die('SCOPE_LEDGER_FROZEN_SCOPE_DRIFT')
if any(u.get('materialization_allowed') is not False or int(u.get('product_blocker_credit') or 0)!=0 or u.get('status')!='REVIEW_ONLY_PROPOSED_NOT_AUTHORITY' for u in units): die('CANDIDATE_PREMATURE_AUTHORITY_OR_MATERIALIZATION')
if (candidate.get('authority_safety') or {}).get('candidate_is_product_authority') is not False or candidate.get('materialization_allowed') is not False or int(candidate.get('product_blocker_credit') or 0)!=0: die('CANDIDATE_AUTHORITY_BOUNDARY_DRIFT')

hist_candidate=jblob(HIST['candidate'])
if semantic_payload(candidate)!=semantic_payload(hist_candidate): die('CANDIDATE_PRODUCT_SEMANTIC_PAYLOAD_DRIFT_FROM_TESTED_TEMPLATE')
sem_digest=digest(semantic_payload(candidate))
if semantic.get('source_candidate_semantic_sha256')!=sem_digest or (semantic.get('current_revalidation') or {}).get('candidate_product_semantic_payload_exact_match_to_tested_template') is not True: die('CURRENT_SEMANTIC_REVALIDATION_DRIFT')

nodes=list(walk(candidate.get('units') or []))
objrefs=[n for n in nodes if n.get('kind')=='object_ref']; opaque=[n for n in nodes if n.get('kind')=='opaque_ref']
if len(objrefs)!=23 or any(n.get('no_new_entity') is not True or not n.get('object_uid') or str(n.get('object_uid')) not in raw_text for n in objrefs): die('CURRENT_OBJECT_REFERENCE_REVALIDATION_FAIL')
if len(opaque)!=17 or any(n.get('no_new_entity') is not True or not n.get('source_authority_term') for n in opaque): die('CURRENT_OPAQUE_REFERENCE_REVALIDATION_FAIL')
payload=[u for u in units if u.get('category')=='PAYLOAD_INPUT_CONTRACT_MISSING']; audits=[u for u in units if u.get('category')=='AUDIT_EVENT_NODE_MISSING']; transitions=[u for u in units if u.get('category')=='STATE_TRANSITION_LEDGER_FIELD_MISSING']
if (len(payload),len(audits),len(transitions))!=(16,4,5): die('CURRENT_CANDIDATE_UNIT_CATEGORY_DRIFT')
for u in payload:
    p=u.get('proposal') or {}; schema=p.get('schema') or {}; fields=schema.get('fields') or {}
    if p.get('proposal_kind')!='ACTION_PAYLOAD_INPUT_SCHEMA' or p.get('action_uid') not in raw_text or p.get('port_uid') not in raw_text: die('PAYLOAD_PROPOSAL_IDENTITY_DRIFT:'+str(u.get('candidate_uid')))
    if any(re.search(r'(provider|model)',str(k),re.I) for k in fields): die('FORBIDDEN_PROVIDER_MODEL_WRITABLE_FIELD:'+str(u.get('candidate_uid')))
events=[]
for u in audits:
    p=u.get('proposal') or {}
    if p.get('proposal_kind')!='AUDIT_EVENT_BINDING_AND_EVENT_REGISTRY_ENTRY' or p.get('action_uid') not in raw_text or p.get('port_uid') not in raw_text: die('AUDIT_PROPOSAL_IDENTITY_DRIFT:'+str(u.get('candidate_uid')))
    ev=p.get('event_uid'); events.append(ev)
    if not ev or ev in raw_text: die('AUDIT_EVENT_PROPOSAL_COLLIDES_WITH_CURRENT:'+str(ev))
if len(set(events))!=4: die('AUDIT_EVENT_PROPOSAL_DUPLICATE')
illegal=[]
for u in transitions:
    ctx=u.get('current_context') or {}; p=u.get('proposal') or {}
    for k in ('transition_uid','from_stage','to_stage','trigger_event_uid','gate_uid'):
        if not ctx.get(k) or str(ctx.get(k)) not in raw_text or p.get(k)!=ctx.get(k): die('TRANSITION_CURRENT_IDENTITY_DRIFT:'+str(u.get('candidate_uid'))+':'+k)
    if p.get('mutation_owner')!='CORE-01' or str(p.get('failure_state')) not in raw_text or str(p.get('audit_event_uid')) not in raw_text: die('TRANSITION_OWNER_FAILURE_AUDIT_DRIFT:'+str(u.get('candidate_uid')))
    if (p.get('recovery') or {}).get('retain_stage')!=ctx.get('from_stage'): die('TRANSITION_RECOVERY_STAGE_DRIFT:'+str(u.get('candidate_uid')))
    tests=p.get('illegal_transition_tests') or []
    if len(tests)!=4: die('TRANSITION_ILLEGAL_TEST_DENOMINATOR:'+str(u.get('candidate_uid')))
    illegal.extend(t.get('test_uid') for t in tests)
if len(illegal)!=20 or len(set(illegal))!=20: die('TRANSITION_ILLEGAL_TEST_UID_DRIFT')

hval=jblob(HIST['validation']); href=jblob(HIST['reference']); hneg=jblob(HIST['negative']); hsem=jblob(HIST['semantic']); hsneg=jblob(HIST['semantic_negative'])
if (hval.get('validation') or {}).get('check_count')!=34 or (hval.get('validation') or {}).get('failed_check_count')!=0: die('HISTORICAL_34_OF_34_REGRESSION_ANCHOR_INVALID')
rr=href.get('result') or {}
if rr.get('object_ref_exact_current_identity_pass')!=23 or rr.get('opaque_ref_non_entity_pass')!=17 or rr.get('new_business_entity_created') is not False or rr.get('new_runtime_created') is not False or rr.get('new_api_or_port_created') is not False: die('HISTORICAL_REFERENCE_REGRESSION_ANCHOR_INVALID')
if (hneg.get('result') or {}).get('pass')!=17 or (hneg.get('result') or {}).get('fail')!=0: die('HISTORICAL_17_OF_17_REGRESSION_ANCHOR_INVALID')
if (hsem.get('denominator') or {}).get('semantic_pass_units')!=25 or (hsem.get('denominator') or {}).get('semantic_fail_units')!=0: die('HISTORICAL_25_OF_25_REGRESSION_ANCHOR_INVALID')
if (hsneg.get('result') or {}).get('pass')!=12 or (hsneg.get('result') or {}).get('fail')!=0: die('HISTORICAL_12_OF_12_REGRESSION_ANCHOR_INVALID')

review=package.get('review_model') or {}; safety=package.get('safety') or {}
if review.get('status')!='PENDING_EXPLICIT_COHERENT_PACKAGE_REVIEW' or review.get('field_by_field_user_approval_required') is not False or review.get('approval_does_not_auto_materialize') is not True: die('COHERENT_PACKAGE_REVIEW_MODEL_DRIFT')
if safety.get('candidate_is_product_authority') is not False or safety.get('candidate_may_be_used_as_current_authority') is not False or safety.get('candidate_materialization_allowed') is not False or int(safety.get('product_blocker_reduction_credit') or 0)!=0: die('REVIEW_PACKAGE_AUTHORITY_BOUNDARY_DRIFT')
print('PASS: Current v2.2.5 CORE-01 review-only Design/Contract remediation package')
print('PASS: 45/45 blockers -> 25 coherent design units; zero duplicate/omission')
print('PASS: fresh reference checks object_ref=23/23 opaque_ref=17/17 audit=4 transition=5 illegal_tests=20/20')
print('PASS: current candidate product semantic payload exactly equals tested template under unchanged raw blob')
print('PASS: historical regression anchors 34/34, 17/17, 25/25, 12/12 are identity-bound; Current validator independently rechecked applicable identities')
print('PASS: coherent package review PENDING; candidate is not Authority, not materializable, product credit=0')
