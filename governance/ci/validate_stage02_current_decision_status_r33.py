#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import sys,yaml
ROOT=Path(__file__).resolve().parents[2]
STATUS=ROOT/'governance/test/stage02/STAGE02_CURRENT_FUNCTIONAL_CONTRACT_DECISION_STATUS_R33.yaml'
INPUT=ROOT/'governance/test/stage02/STAGE02_OWNING_LAYER_REMEDIATION_INPUT_PACKET_R33.yaml'
TARGET='STAGE02-R5-PRODUCT-AUTH-032'; INPUT_UID='STAGE02-R27-INPUT-032'
def die(m): print(f'BLOCK: {m}',file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die(f'MAPPING_REQUIRED:{p.relative_to(ROOT)}')
    return o
s=load(STATUS); i=load(INPUT)
if s.get('artifact_type')!='NON_NORMATIVE_STAGE02_CURRENT_FUNCTIONAL_CONTRACT_DECISION_STATUS_R33' or s.get('stage_uid')!='STAGE-02' or s.get('normative_authority') is not False: die('R33_STATUS_IDENTITY_DRIFT')
c=s.get('decision_contract') or {}
for k in ('candidate_review_may_prove_authority_decision_required_without_selecting_behavior','product_authority_gap_does_not_reduce_blocker','product_authority_gap_does_not_create_contract_value','nonreviewed_problems_remain_unresolved_not_authority','current_specification_mutation_forbidden','stage1_raw_mutation_forbidden'):
    if c.get(k) is not True: die(f'R33_DECISION_CONTRACT_DRIFT:{k}')
d=s.get('denominators') or {}
if d!={'current_effective_problems':129,'true_product_authority_gaps_proven':1,'unresolved_functional_contract_gaps':128,'deterministic_materialization_candidates':0,'provided_contract_values':0,'effective_stage02_blocker_reduction_claimed':0}: die(f'R33_STATUS_DENOMINATOR_DRIFT:{d}')
rows=s.get('problems') or []
if len(rows)!=129 or Counter(x.get('current_decision_classification') for x in rows)!=Counter({'UNRESOLVED_FUNCTIONAL_CONTRACT_GAP':128,'TRUE_PRODUCT_AUTHORITY_GAP':1}): die('R33_PROBLEM_PARTITION_DRIFT')
pa=[x for x in rows if x.get('current_decision_classification')=='TRUE_PRODUCT_AUTHORITY_GAP']
if len(pa)!=1 or pa[0].get('blocker_uid')!=TARGET or pa[0].get('product_authority_gap_proven') is not True or pa[0].get('product_authority_decision_status')!='PENDING_SELECTION' or pa[0].get('blocker_reduction_credit')!=0: die('R33_AUTHORITY_PROBLEM_DRIFT')
if set(pa[0].get('candidate_behavior_uids') or [])!={'R32-CANDIDATE-A-MANUAL-CONTROL','R32-CANDIDATE-B-EVALUATION-SYSTEM-TRIGGER'}: die('R33_AUTHORITY_CANDIDATE_SET_DRIFT')
if any(x.get('product_authority_gap_proven') is not False for x in rows if x.get('blocker_uid')!=TARGET): die('R33_NONREVIEWED_AUTHORITY_PROMOTION')
pa_dec=s.get('product_authority_decisions') or []
if len(pa_dec)!=1 or pa_dec[0].get('blocker_uid')!=TARGET or pa_dec[0].get('remediation_input_uid')!=INPUT_UID or pa_dec[0].get('decision_status')!='PENDING_SELECTION' or pa_dec[0].get('selected_behavior_uid') is not None or pa_dec[0].get('owning_layer_contract_value') is not None or pa_dec[0].get('blocker_reduction_credit')!=0: die('R33_AUTHORITY_DECISION_RECORD_DRIFT')
if i.get('artifact_type')!='NON_NORMATIVE_STAGE02_OWNING_LAYER_REMEDIATION_INPUT_PACKET_R33' or i.get('stage_uid')!='STAGE-02': die('R33_INPUT_IDENTITY_DRIFT')
idn=i.get('denominators') or {}
for k,v in {'total_required_inputs':129,'provided_inputs':0,'pending_inputs':129,'pending_product_authority_decisions':1,'pending_owning_layer_contract_inputs':128,'deterministic_materialization_candidates_before_input':0,'blocker_reduction_claimed':0}.items():
    if idn.get(k)!=v: die(f'R33_INPUT_DENOMINATOR_DRIFT:{k}:{idn.get(k)}')
inputs=i.get('inputs') or []
if len(inputs)!=129: die('R33_INPUT_RECORD_COUNT_DRIFT')
targets=[x for x in inputs if x.get('remediation_input_uid')==INPUT_UID]
if len(targets)!=1: die('R33_TARGET_INPUT_DENOMINATOR')
t=targets[0]
if t.get('blocker_uid')!=TARGET or t.get('input_status')!='PENDING_PRODUCT_AUTHORITY_DECISION' or t.get('product_authority_gap_proven') is not True or t.get('owning_layer_contract_value') is not None or t.get('auto_fill_allowed') is not False or t.get('blocker_reduction_credit')!=0: die('R33_TARGET_INPUT_STATE_DRIFT')
if sum(x.get('input_status')=='REQUIRED_NOT_PROVIDED' for x in inputs)!=128: die('R33_GENERAL_PENDING_INPUT_COUNT_DRIFT')
if any(x.get('product_authority_gap_proven') is not False for x in inputs if x.get('remediation_input_uid')!=INPUT_UID): die('R33_NON_TARGET_INPUT_AUTHORITY_DRIFT')
if s.get('current_specification_mutated') is not False or s.get('immutable_stage1_source_mutated') is not False or s.get('stage02_status')!='BLOCKED' or s.get('stage03_allowed') is not False: die('R33_STATUS_SAFETY_DRIFT')
if i.get('current_specification_mutated') is not False or i.get('immutable_stage1_source_mutated') is not False or i.get('stage02_status')!='BLOCKED' or i.get('stage03_allowed') is not False: die('R33_INPUT_SAFETY_DRIFT')
print('PASS: R33 current 129 partition validated: 1 true Product Authority decision pending + 128 unresolved contract inputs')
print('PASS: no product behavior selected, no contract value provided, blocker reduction=0')
