#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import json, subprocess, sys, yaml

ROOT=Path(__file__).resolve().parents[2]
R29=ROOT/'.github/stage02-test/STAGE02_R29_EFFECTIVE_REEXECUTION_RESULT.json'
R26=ROOT/'governance/test/stage02/STAGE02_CURRENT_FUNCTIONAL_CONTRACT_PROBLEM_RECONCILIATION_R26.yaml'
R28=ROOT/'governance/test/stage02/STAGE02_FAILURE_RECOVERY_APPLICABILITY_AUDIT_R28.yaml'
FIND=ROOT/'governance/test/stage02/FIND-20260915-025_FAILURE_RECOVERY_APPLICABILITY_OVERREACH.yaml'
OUT=ROOT/'governance/test/stage02/STAGE02_CURRENT_FUNCTIONAL_CONTRACT_PROBLEM_RECONCILIATION_R30.yaml'
EXPECTED={'FAILURE_STATE_ERROR_BINDING_MISSING':23,'POST_ACTION_VALIDATION_NODE_MISSING':18,'PAYLOAD_INPUT_CONTRACT_MISSING':34,'ACTION_WITHOUT_CONTROL_OR_TRIGGER':1,'AUDIT_EVENT_NODE_MISSING':13,'STATE_TRANSITION_LEDGER_FIELD_MISSING':40}

def die(m): print(f'BLOCK: {m}',file=sys.stderr); raise SystemExit(1)
def ly(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die(f'MAPPING_REQUIRED:{p.relative_to(ROOT)}')
    return o
def lj(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(o,dict): die(f'JSON_MAPPING_REQUIRED:{p.relative_to(ROOT)}')
    return o

def sig(scope,cat,uid,detail): return (scope,cat,str(uid),detail)

r29=lj(R29); r26=ly(R26); r28=ly(R28); finding=ly(FIND)
if r29.get('fresh_functional_gap_total')!=129 or r29.get('effective_gap_categories')!=EXPECTED: die('R30_R29_BASELINE_DRIFT')
if finding.get('status')!='VERIFIED_CLOSED' or (finding.get('closure_evidence') or {}).get('exact_false_positive_count_removed')!=21: die('R30_FIND025_NOT_CLOSED')
base={sig(x.get('scope'),x.get('category'),x.get('target_uid'),x.get('missing_field_or_relation')):x for x in r26.get('problems') or []}
if len(base)!=150: die(f'R30_R26_PROBLEM_DENOMINATOR:{len(base)}')
fresh={}
for page,prec in (r29.get('pages') or {}).items():
    for g in ((prec.get('functional_chain_effective_r29_scan') or {}).get('gaps') or []):
        k=sig(page,g.get('category'),g.get('uid'),g.get('detail'))
        if k in fresh: die(f'R30_DUPLICATE_FRESH_SIGNATURE:{k}')
        fresh[k]=g
if len(fresh)!=129: die(f'R30_FRESH_SIGNATURE_COUNT:{len(fresh)}')
if not set(fresh)<=set(base): die(f'R30_FRESH_NOT_IN_R26:{sorted(set(fresh)-set(base))[:5]}')
superseded=set(base)-set(fresh)
na_blockers={x.get('blocker_uid') for x in r28.get('records') or [] if x.get('applicability_classification')=='NOT_APPLICABLE_NON_EFFECTFUL_CLIENT_NO_API_NO_TRANSITION'}
sup_blockers={base[k].get('blocker_uid') for k in superseded}
if len(superseded)!=21 or sup_blockers!=na_blockers: die('R30_SUPERSEDED_FALSE_POSITIVE_SET_DRIFT')
if any(k[1]!='FAILURE_STATE_ERROR_BINDING_MISSING' or k[0]!='ASSET-01' for k in superseded): die('R30_SUPERSEDED_SCOPE_CATEGORY_DRIFT')
problems=[]
for k in sorted(fresh):
    p=dict(base[k]); p['current_effective_gap_present']=True; p['current_baseline_cycle']='R30_AFTER_FAILURE_RECOVERY_APPLICABILITY_FIX'; problems.append(p)
sc=Counter(x['scope'] for x in problems); cc=Counter(x['category'] for x in problems)
if sc!=Counter({'ASSET-01':89,'CORE-01':40}) or dict(cc)!=EXPECTED: die(f'R30_COUNTS_DRIFT:{dict(sc)}:{dict(cc)}')
head=subprocess.run(['git','rev-parse','HEAD'],cwd=str(ROOT),text=True,capture_output=True,check=True).stdout.strip()
out={'schema_version':1,'artifact_type':'NON_NORMATIVE_STAGE02_CURRENT_FUNCTIONAL_CONTRACT_PROBLEM_RECONCILIATION_R30','normative_authority':False,'stage_uid':'STAGE-02','cycle':'CURRENT_129_PROBLEM_RECONCILIATION_AFTER_R29_APPLICABILITY_FIX','source_head_sha':head,'source_contracts':{'fresh_r29_result':str(R29.relative_to(ROOT)),'prior_r26_register':str(R26.relative_to(ROOT)),'r28_applicability_audit':str(R28.relative_to(ROOT)),'finding_025':str(FIND.relative_to(ROOT))},'reconciliation_contract':{'fresh_effective_gap_must_exact_match_prior_problem_signature':True,'false_positive_signatures_must_exact_match_r28_na_set':True,'superseded_false_positive_is_not_a_closed_product_contract':True,'ai_may_define_missing_contract_value':False,'current_specification_may_mutate_mid_stage':False,'problem_reconciliation_reduces_blocker':False},'denominators':{'fresh_effective_problems':129,'prior_r26_problems':150,'active_scope_counts':dict(sorted(sc.items())),'active_category_counts':dict(sorted(cc.items())),'r28_scanner_false_positives_superseded':21,'product_authority_gaps_proven':0,'deterministic_materialization_candidates':0,'effective_stage02_blocker_reduction_claimed':0},'superseded_scanner_false_positives':[{'problem_uid':base[k].get('problem_uid'),'blocker_uid':base[k].get('blocker_uid'),'scope':k[0],'category':k[1],'target_uid':k[2],'missing_field_or_relation':k[3],'superseded_by':'FIND-20260915-025/R29','reason':'EXACT_FAILURE_RECOVERY_NOT_APPLICABLE'} for k in sorted(superseded)],'problems':problems,'current_specification_mutated':False,'immutable_stage1_source_mutated':False,'stage02_status':'BLOCKED','stage03_allowed':False,'website_construction_allowed':False,'deployment_allowed':False,'next_execution_gate':'REBUILD_OWNING_LAYER_INPUT_PACKET_FROM_CURRENT_129_THEN_ROLE_SAFE_CANDIDATE_AUTHORING'}
OUT.write_text(yaml.safe_dump(out,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
print('PASS: R30 current problem register=129; exact R28 false-positive supersession=21')
