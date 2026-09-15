#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json, subprocess, sys, yaml

ROOT=Path(__file__).resolve().parents[2]
R19=ROOT/'governance/test/stage02/STAGE02_FUNCTIONAL_CONTRACT_REMEDIATION_PROBLEM_REGISTER_R19.yaml'
R22=ROOT/'governance/test/stage02/STAGE02_POST_ACTION_SIGNAL_ROLE_RECLASSIFICATION_R22.yaml'
R24=ROOT/'governance/test/stage02/STAGE02_R24_CORRECTNESS_ROLLBACK_RECEIPT.yaml'
R25_INV=ROOT/'governance/test/stage02/STAGE02_POST_ACTION_SIGNAL_INVALIDATION_R25.yaml'
R25_REC=ROOT/'governance/test/stage02/STAGE02_R25_CORRECTNESS_ROLLBACK_RECEIPT.yaml'
R25_RESULT=ROOT/'.github/stage02-test/STAGE02_R25_EFFECTIVE_REEXECUTION_RESULT.json'
OUT=ROOT/'governance/test/stage02/STAGE02_CURRENT_FUNCTIONAL_CONTRACT_PROBLEM_RECONCILIATION_R26.yaml'
EXPECTED_CATEGORIES={
 'ACTION_WITHOUT_CONTROL_OR_TRIGGER':1,
 'AUDIT_EVENT_NODE_MISSING':13,
 'FAILURE_STATE_ERROR_BINDING_MISSING':44,
 'PAYLOAD_INPUT_CONTRACT_MISSING':34,
 'POST_ACTION_VALIDATION_NODE_MISSING':18,
 'STATE_TRANSITION_LEDGER_FIELD_MISSING':40,
}

def die(msg): print(f'BLOCK: {msg}',file=sys.stderr); raise SystemExit(1)
def load_yaml(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die(f'MAPPING_REQUIRED:{p.relative_to(ROOT)}')
    return o
def load_json(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(o,dict): die(f'JSON_MAPPING_REQUIRED:{p.relative_to(ROOT)}')
    return o

r19=load_yaml(R19); r22=load_yaml(R22); r24=load_yaml(R24); r25i=load_yaml(R25_INV); r25r=load_yaml(R25_REC); result=load_json(R25_RESULT)
if (r19.get('denominators') or {}).get('total_registered_problems')!=150: die('R19_DENOMINATOR_DRIFT')
if (r19.get('denominators') or {}).get('product_authority_gaps_proven')!=0: die('R19_PRODUCT_AUTHORITY_GAP_DRIFT')
if result.get('fresh_functional_gap_total')!=150 or result.get('effective_gap_categories')!=EXPECTED_CATEGORIES: die('R25_FRESH_BASELINE_DRIFT')
if result.get('product_materialization_elimination_count')!=17 or result.get('gap006_authority_elimination_count')!=4: die('R25_ELIMINATION_DRIFT')
if result.get('current_specification_mutated') is not False or result.get('immutable_stage1_source_mutated') is not False: die('R25_MUTATION_FLAG_DRIFT')
if r24.get('removed_invalid_materialization_total')!=4 or r25r.get('removed_invalid_materialization_total')!=17: die('CORRECTION_RECEIPT_DENOMINATOR_DRIFT')

r19_idx={}
for p in r19.get('problems') or []:
    key=(p.get('scope'),p.get('category'),str(p.get('target_uid')),str(p.get('missing_field_or_relation')))
    if key in r19_idx: die(f'R19_DUPLICATE_PROBLEM_SIGNATURE:{key}')
    r19_idx[key]=p
if len(r19_idx)!=150: die(f'R19_INDEX_COUNT:{len(r19_idx)}')

fresh=[]
for page,rec in (result.get('pages') or {}).items():
    eff=rec.get('functional_chain_effective_r25_scan') or {}
    for gap in eff.get('gaps') or []:
        if gap.get('category') not in EXPECTED_CATEGORIES: continue
        fresh.append((page,gap))
if len(fresh)!=150: die(f'R25_EFFECTIVE_REGISTERABLE_COUNT:{len(fresh)}')

r24_removed=set(r24.get('removed_blocker_uids') or [])
r25_removed=set(r25r.get('removed_blocker_uids') or [])
if len(r24_removed)!=4 or len(r25_removed)!=17 or r24_removed & r25_removed: die('CORRECTION_BLOCKER_SET_DRIFT')

r22_030=[x for x in r22.get('records') or [] if x.get('blocker_uid')=='STAGE02-R5-PRODUCT-AUTH-030']
if len(r22_030)!=1: die('R22_030_DENOMINATOR_DRIFT')
r22_030=r22_030[0]
if r22_030.get('disposition')!='AUTHORITY_GAP_MULTIPLE_ACTION_RESULT_SIGNALS_AFTER_ROLE_CORRECTION' or r22_030.get('authority_gap_proven') is not True: die('R22_030_CLASSIFICATION_DRIFT')
if r22_030.get('authorized_for_auto_completion') is not False: die('R22_030_AUTO_FLAG_DRIFT')

records=[]; matched=set(); correction_counts=Counter(); scope_counts=Counter(); category_counts=Counter()
for page,gap in fresh:
    key=(page,gap.get('category'),str(gap.get('uid')),str(gap.get('detail')))
    p=r19_idx.get(key)
    if not p: die(f'R26_R19_EXACT_MATCH_MISSING:{key}')
    matched.add(key); blocker=p.get('blocker_uid'); history=[]
    if blocker in r24_removed:
        history.append({'cycle':'R24','correction':'INVALID_R20_TRANSITION_MUTATION_OWNER_MATERIALIZATION_ROLLED_BACK','receipt':str(R24.relative_to(ROOT))}); correction_counts['R24_ROLLBACK']+=1
    if blocker in r25_removed:
        history.append({'cycle':'R25','correction':'INVALID_R20_R22_POST_ACTION_SIGNAL_PROMOTION_ROLLED_BACK','receipt':str(R25_REC.relative_to(ROOT))}); correction_counts['R25_ROLLBACK']+=1
    if blocker=='STAGE02-R5-PRODUCT-AUTH-030':
        history.append({'cycle':'R26','correction':'R22_MULTIPLE_RESULT_SIGNAL_PRODUCT_AUTHORITY_CLASSIFICATION_SUPERSEDED','reason':'R15 and first-run fresh scanner do not admit result/state signals as post-action validation contracts'}); correction_counts['R22_AUTHORITY_CLASSIFICATION_SUPERSEDED']+=1
    records.append({
      'problem_uid':p.get('problem_uid'),'blocker_uid':blocker,'scope':page,'category':gap.get('category'),'target_uid':gap.get('uid'),'missing_field_or_relation':gap.get('detail'),
      'current_effective_gap_present':True,'problem_status':'OPEN_FUNCTIONAL_CONTRACT_REMEDIATION_REQUIRED','product_authority_gap_proven':False,'deterministic_materialization_candidate':False,
      'owning_layer':p.get('owning_layer'),'owning_contract':p.get('owning_contract'),'required_definition':p.get('required_definition'),'forbidden_substitutions':p.get('forbidden_substitutions'),
      'trace_ref':p.get('trace_ref'),'trace_evidence_summary':p.get('trace_evidence_summary'),'correction_history':history,
      'current_specification_mutation_allowed':False,'historical_non_current_authority_allowed':False,'ai_invented_contract_value_allowed':False,'blocker_reduction_credit':0,
      'closure_requirement':p.get('closure_requirement')
    })
    scope_counts[page]+=1; category_counts[gap.get('category')]+=1

if matched!=set(r19_idx): die(f'R26_R19_COVERAGE_DRIFT:missing={len(set(r19_idx)-matched)} extra={len(matched-set(r19_idx))}')
if dict(sorted(category_counts.items()))!=EXPECTED_CATEGORIES: die(f'R26_CATEGORY_COUNT_DRIFT:{dict(category_counts)}')
if scope_counts!=Counter({'ASSET-01':110,'CORE-01':40}): die(f'R26_SCOPE_COUNT_DRIFT:{dict(scope_counts)}')
if correction_counts!=Counter({'R25_ROLLBACK':17,'R24_ROLLBACK':4,'R22_AUTHORITY_CLASSIFICATION_SUPERSEDED':1}): die(f'R26_CORRECTION_COUNT_DRIFT:{dict(correction_counts)}')

head=subprocess.run(['git','rev-parse','HEAD'],cwd=str(ROOT),text=True,capture_output=True,check=True).stdout.strip()
out={
 'schema_version':1,'artifact_type':'NON_NORMATIVE_STAGE02_CURRENT_FUNCTIONAL_CONTRACT_PROBLEM_RECONCILIATION_R26','normative_authority':False,'stage_uid':'STAGE-02','cycle':'CURRENT_150_PROBLEM_RECONCILIATION_AFTER_CORRECTNESS_ROLLBACKS_R26','source_head_sha':head,
 'source_contracts':{'fresh_r25_result':str(R25_RESULT.relative_to(ROOT)),'r19_problem_register':str(R19.relative_to(ROOT)),'r24_rollback_receipt':str(R24.relative_to(ROOT)),'r25_invalidation':str(R25_INV.relative_to(ROOT)),'r25_rollback_receipt':str(R25_REC.relative_to(ROOT)),'r22_role_reclassification':str(R22.relative_to(ROOT))},
 'reconciliation_contract':{'fresh_effective_gap_must_exact_match_r19_problem_signature':True,'problem_signature_fields':['scope','category','target_uid','missing_field_or_relation'],'all_150_must_be_one_to_one':True,'invalid_materialization_history_preserved':True,'r22_authority_gap_classification_for_correction_execute_is_current':False,'absence_or_rollback_alone_proves_product_authority_gap':False,'ai_may_define_missing_contract_value':False,'current_specification_may_mutate_mid_stage':False,'problem_reconciliation_reduces_blocker':False},
 'denominators':{'fresh_effective_problems':150,'r19_exact_matched_problems':150,'scope_counts':dict(scope_counts),'category_counts':dict(category_counts),'r24_invalid_materializations_recorded':4,'r25_invalid_materializations_recorded':17,'r22_product_authority_classifications_superseded':1,'deterministic_materialization_candidates':0,'product_authority_gaps_proven':0,'effective_stage02_blocker_reduction_claimed':0},
 'problems':records,'current_specification_mutated':False,'immutable_stage1_source_mutated':False,'stage02_status':'BLOCKED','stage02_effective_blocker_count':150,'stage03_allowed':False,'website_construction_allowed':False,'deployment_allowed':False,
 'next_execution_gate':'FUNCTIONAL_CONTRACT_OWNING_LAYER_REMEDIATION_INPUT_REQUIRED'
}
OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(yaml.safe_dump(out,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
print('PASS: R26 fresh 150 problems exact-match R19 150/150')
print('PASS: correction history recorded R24=4 R25=17; R22 authority classification superseded=1')
print('PASS: deterministic materialization candidates=0; proven product authority gaps=0')
print('BLOCKED: next gate=FUNCTIONAL_CONTRACT_OWNING_LAYER_REMEDIATION_INPUT_REQUIRED')
