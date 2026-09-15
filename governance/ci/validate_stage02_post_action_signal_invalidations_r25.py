#!/usr/bin/env python3
from pathlib import Path
import sys,yaml
ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'governance/test/stage02/STAGE02_POST_ACTION_SIGNAL_INVALIDATION_R25.yaml'
def die(msg): print(f'BLOCK: {msg}',file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die('R25_MAPPING_REQUIRED')
    return o
d=load(DOC)
if d.get('artifact_type')!='NON_NORMATIVE_STAGE02_POST_ACTION_SIGNAL_INVALIDATION_R25' or d.get('stage_uid')!='STAGE-02' or d.get('normative_authority') is not False: die('R25_IDENTITY_DRIFT')
b=d.get('correction_basis') or {}
required={'r15_exact_validation_trace_controls_validation_semantics':True,'fresh_scanner_requires_explicit_validation_contract':True,'result_or_state_signal_is_validation_contract':False,'rollback_only_no_replacement_value':True,'current_specification_mutation_forbidden':True,'stage1_raw_mutation_forbidden':True}
for k,v in required.items():
    if b.get(k) is not v: die(f'R25_BASIS_DRIFT:{k}:{b.get(k)}')
den=d.get('denominators') or {}
if den.get('r20_post_action_auto_total')!=15 or den.get('r22_post_action_auto_total')!=2 or den.get('invalid_post_action_materialization_total')!=17: die(f'R25_DENOMINATOR_DRIFT:{den}')
if den.get('current_product_materialization_total_before_rollback')!=34 or den.get('expected_product_materialization_total_after_rollback')!=17: die('R25_PRODUCT_ARITHMETIC_DRIFT')
if den.get('blocker_reduction_claimed_before_fresh_reexecution')!=0: die('R25_PREMATURE_REDUCTION')
rows=d.get('invalidations') or []
if len(rows)!=17 or len({x.get('blocker_uid') for x in rows})!=17: die('R25_INVALIDATION_SET_COUNT_DRIFT')
cycles={x.get('source_cycle') for x in rows}
if cycles!={'R20','R22'}: die(f'R25_SOURCE_CYCLES_DRIFT:{cycles}')
if sum(x.get('source_cycle')=='R20' for x in rows)!=15 or sum(x.get('source_cycle')=='R22' for x in rows)!=2: die('R25_SOURCE_CYCLE_DENOMINATOR_DRIFT')
for x in rows:
    if x.get('page_uid')!='ASSET-01' or not str(x.get('action_uid') or '').startswith('ASSET-01-ACT-'): die(f'R25_ROW_SCOPE_DRIFT:{x.get("blocker_uid")}')
    if x.get('r15_explicit_validation_contract_evidence')!=[] or not x.get('r15_result_or_state_signal_evidence'): die(f'R25_R15_EVIDENCE_DRIFT:{x.get("blocker_uid")}')
    if x.get('rollback_required') is not True or x.get('replacement_validation_contract') is not None: die(f'R25_ROLLBACK_CONTRACT_DRIFT:{x.get("blocker_uid")}')
    if x.get('semantic_inference_used_for_replacement') is not False or x.get('product_authority_value_invented') is not False: die(f'R25_SAFETY_DRIFT:{x.get("blocker_uid")}')
if d.get('current_specification_mutated') is not False or d.get('immutable_stage1_source_mutated') is not False: die('R25_MUTATION_FLAG_DRIFT')
print('PASS: R25 exact invalidation set=17 (R20=15 R22=2); rollback-only; no replacement validation authority invented')
