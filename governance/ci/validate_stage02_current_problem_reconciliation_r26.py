#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import sys,yaml
ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'governance/test/stage02/STAGE02_CURRENT_FUNCTIONAL_CONTRACT_PROBLEM_RECONCILIATION_R26.yaml'
EXPECTED={
 'ACTION_WITHOUT_CONTROL_OR_TRIGGER':1,
 'AUDIT_EVENT_NODE_MISSING':13,
 'FAILURE_STATE_ERROR_BINDING_MISSING':44,
 'PAYLOAD_INPUT_CONTRACT_MISSING':34,
 'POST_ACTION_VALIDATION_NODE_MISSING':18,
 'STATE_TRANSITION_LEDGER_FIELD_MISSING':40,
}
def die(msg): print(f'BLOCK: {msg}',file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die('R26_MAPPING_REQUIRED')
    return o
d=load(DOC)
if d.get('artifact_type')!='NON_NORMATIVE_STAGE02_CURRENT_FUNCTIONAL_CONTRACT_PROBLEM_RECONCILIATION_R26' or d.get('stage_uid')!='STAGE-02' or d.get('normative_authority') is not False: die('R26_IDENTITY_DRIFT')
r=d.get('reconciliation_contract') or {}
for k in ('fresh_effective_gap_must_exact_match_r19_problem_signature','all_150_must_be_one_to_one','invalid_materialization_history_preserved'):
    if r.get(k) is not True: die(f'R26_CONTRACT_DRIFT:{k}')
for k in ('r22_authority_gap_classification_for_correction_execute_is_current','absence_or_rollback_alone_proves_product_authority_gap','ai_may_define_missing_contract_value','current_specification_may_mutate_mid_stage','problem_reconciliation_reduces_blocker'):
    if r.get(k) is not False: die(f'R26_SAFETY_CONTRACT_DRIFT:{k}')
den=d.get('denominators') or {}
if den.get('fresh_effective_problems')!=150 or den.get('r19_exact_matched_problems')!=150: die('R26_TOTAL_DENOMINATOR_DRIFT')
if den.get('category_counts')!=EXPECTED: die(f'R26_CATEGORY_DRIFT:{den.get("category_counts")}')
if den.get('scope_counts')!={'ASSET-01':110,'CORE-01':40}: die(f'R26_SCOPE_DRIFT:{den.get("scope_counts")}')
if den.get('r24_invalid_materializations_recorded')!=4 or den.get('r25_invalid_materializations_recorded')!=17 or den.get('r22_product_authority_classifications_superseded')!=1: die('R26_CORRECTION_DENOMINATOR_DRIFT')
if den.get('deterministic_materialization_candidates')!=0 or den.get('product_authority_gaps_proven')!=0 or den.get('effective_stage02_blocker_reduction_claimed')!=0: die('R26_PREMATURE_CLOSURE_DRIFT')
rows=d.get('problems') or []
if len(rows)!=150 or len({x.get('problem_uid') for x in rows})!=150 or len({x.get('blocker_uid') for x in rows})!=150: die('R26_PROBLEM_UID_DENOMINATOR_DRIFT')
cc=Counter(); sc=Counter(); hist=Counter(); correction_execute=[]
for x in rows:
    if x.get('current_effective_gap_present') is not True or x.get('problem_status')!='OPEN_FUNCTIONAL_CONTRACT_REMEDIATION_REQUIRED': die(f'R26_PROBLEM_STATUS_DRIFT:{x.get("problem_uid")}')
    if x.get('product_authority_gap_proven') is not False or x.get('deterministic_materialization_candidate') is not False: die(f'R26_CLASSIFICATION_DRIFT:{x.get("problem_uid")}')
    if x.get('current_specification_mutation_allowed') is not False or x.get('historical_non_current_authority_allowed') is not False or x.get('ai_invented_contract_value_allowed') is not False: die(f'R26_SAFETY_DRIFT:{x.get("problem_uid")}')
    if x.get('blocker_reduction_credit')!=0: die(f'R26_BLOCKER_REDUCTION_DRIFT:{x.get("problem_uid")}')
    cc[x.get('category')]+=1; sc[x.get('scope')]+=1
    for h in x.get('correction_history') or []: hist[h.get('correction')]+=1
    if x.get('blocker_uid')=='STAGE02-R5-PRODUCT-AUTH-030': correction_execute.append(x)
if dict(cc)!=EXPECTED or sc!=Counter({'ASSET-01':110,'CORE-01':40}): die('R26_RECOUNT_DRIFT')
if hist['INVALID_R20_TRANSITION_MUTATION_OWNER_MATERIALIZATION_ROLLED_BACK']!=4 or hist['INVALID_R20_R22_POST_ACTION_SIGNAL_PROMOTION_ROLLED_BACK']!=17 or hist['R22_MULTIPLE_RESULT_SIGNAL_PRODUCT_AUTHORITY_CLASSIFICATION_SUPERSEDED']!=1: die(f'R26_HISTORY_RECOUNT_DRIFT:{dict(hist)}')
if len(correction_execute)!=1 or not any(h.get('correction')=='R22_MULTIPLE_RESULT_SIGNAL_PRODUCT_AUTHORITY_CLASSIFICATION_SUPERSEDED' for h in correction_execute[0].get('correction_history') or []): die('R26_CORRECTION_EXECUTE_SUPERSESSION_MISSING')
if d.get('stage02_status')!='BLOCKED' or d.get('stage02_effective_blocker_count')!=150 or d.get('next_execution_gate')!='FUNCTIONAL_CONTRACT_OWNING_LAYER_REMEDIATION_INPUT_REQUIRED': die('R26_STAGE_STATE_DRIFT')
if d.get('stage03_allowed') is not False or d.get('website_construction_allowed') is not False or d.get('deployment_allowed') is not False: die('R26_FAIL_CLOSED_DRIFT')
print('PASS: R26 current problem reconciliation validated 150/150')
print('PASS: R24=4 and R25=17 rollback history preserved; R22 authority classification superseded=1')
print('BLOCKED: owning-layer remediation input required; no invented contract values')
