#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import subprocess,sys,yaml
ROOT=Path(__file__).resolve().parents[2]
R30=ROOT/'governance/test/stage02/STAGE02_CURRENT_FUNCTIONAL_CONTRACT_PROBLEM_RECONCILIATION_R30.yaml'
R31=ROOT/'governance/test/stage02/STAGE02_OWNING_LAYER_REMEDIATION_INPUT_PACKET_R31.yaml'
R32=ROOT/'governance/test/stage02/STAGE02_FINDING_CREATE_CONTROL_TRIGGER_CANDIDATE_REVIEW_R32.yaml'
OUT_STATUS=ROOT/'governance/test/stage02/STAGE02_CURRENT_FUNCTIONAL_CONTRACT_DECISION_STATUS_R33.yaml'
OUT_INPUT=ROOT/'governance/test/stage02/STAGE02_OWNING_LAYER_REMEDIATION_INPUT_PACKET_R33.yaml'
TARGET='STAGE02-R5-PRODUCT-AUTH-032'
INPUT_UID='STAGE02-R27-INPUT-032'

def die(m): print(f'BLOCK: {m}',file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die(f'MAPPING_REQUIRED:{p.relative_to(ROOT)}')
    return o
r30=load(R30); r31=load(R31); r32=load(R32)
if (r30.get('denominators') or {}).get('fresh_effective_problems')!=129: die('R33_R30_DENOMINATOR_DRIFT')
if (r31.get('denominators') or {}).get('total_required_inputs')!=129: die('R33_R31_DENOMINATOR_DRIFT')
rr=r32.get('review_result') or {}
if rr.get('classification')!='AUTHORITY_GAP_MULTIPLE_REASONABLE_PRODUCT_BEHAVIORS' or rr.get('product_authority_decision_required') is not True or rr.get('blocker_reduction_credit')!=0: die('R33_R32_REVIEW_DRIFT')
problems=[]; counts=Counter()
for p in r30.get('problems') or []:
    q=dict(p)
    if q.get('blocker_uid')==TARGET:
        q['current_decision_classification']='TRUE_PRODUCT_AUTHORITY_GAP'
        q['product_authority_gap_proven']=True
        q['product_authority_review_ref']=str(R32.relative_to(ROOT))
        q['product_authority_decision_status']='PENDING_SELECTION'
        q['candidate_behavior_uids']=['R32-CANDIDATE-A-MANUAL-CONTROL','R32-CANDIDATE-B-EVALUATION-SYSTEM-TRIGGER']
        q['deterministic_materialization_candidate']=False
        q['blocker_reduction_credit']=0
    else:
        q['current_decision_classification']='UNRESOLVED_FUNCTIONAL_CONTRACT_GAP'
        q['product_authority_gap_proven']=False
        q['product_authority_decision_status']='NOT_PROVEN_REQUIRED'
        q['deterministic_materialization_candidate']=False
        q['blocker_reduction_credit']=0
    counts[q['current_decision_classification']]+=1
    problems.append(q)
if counts!=Counter({'UNRESOLVED_FUNCTIONAL_CONTRACT_GAP':128,'TRUE_PRODUCT_AUTHORITY_GAP':1}): die(f'R33_CLASS_COUNTS_DRIFT:{dict(counts)}')
head=subprocess.run(['git','rev-parse','HEAD'],cwd=str(ROOT),text=True,capture_output=True,check=True).stdout.strip()
status={'schema_version':1,'artifact_type':'NON_NORMATIVE_STAGE02_CURRENT_FUNCTIONAL_CONTRACT_DECISION_STATUS_R33','normative_authority':False,'stage_uid':'STAGE-02','cycle':'CURRENT_DECISION_STATUS_AFTER_FINDING_CREATE_CANDIDATE_REVIEW_R33','source_head_sha':head,'source_problem_baseline':str(R30.relative_to(ROOT)),'source_candidate_review':str(R32.relative_to(ROOT)),'decision_contract':{'candidate_review_may_prove_authority_decision_required_without_selecting_behavior':True,'product_authority_gap_does_not_reduce_blocker':True,'product_authority_gap_does_not_create_contract_value':True,'nonreviewed_problems_remain_unresolved_not_authority':True,'current_specification_mutation_forbidden':True,'stage1_raw_mutation_forbidden':True},'denominators':{'current_effective_problems':129,'true_product_authority_gaps_proven':1,'unresolved_functional_contract_gaps':128,'deterministic_materialization_candidates':0,'provided_contract_values':0,'effective_stage02_blocker_reduction_claimed':0},'product_authority_decisions':[{'blocker_uid':TARGET,'remediation_input_uid':INPUT_UID,'target_uid':'ASSET-01-ACT-FINDING-CREATE','category':'ACTION_WITHOUT_CONTROL_OR_TRIGGER','review_ref':str(R32.relative_to(ROOT)),'candidate_behavior_uids':['R32-CANDIDATE-A-MANUAL-CONTROL','R32-CANDIDATE-B-EVALUATION-SYSTEM-TRIGGER'],'decision_status':'PENDING_SELECTION','selected_behavior_uid':None,'owning_layer_contract_value':None,'blocker_reduction_credit':0}],'problems':problems,'current_specification_mutated':False,'immutable_stage1_source_mutated':False,'stage02_status':'BLOCKED','stage03_allowed':False,'website_construction_allowed':False,'deployment_allowed':False,'next_execution_gate':'CONTINUE_ROLE_SAFE_CANDIDATE_AUTHORING_FOR_128_UNRESOLVED_PROBLEMS_WHILE_HOLDING_FINDING_CREATE_FOR_PRODUCT_AUTHORITY_DECISION'}
OUT_STATUS.write_text(yaml.safe_dump(status,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')

packet=dict(r31); packet['schema_version']=2; packet['artifact_type']='NON_NORMATIVE_STAGE02_OWNING_LAYER_REMEDIATION_INPUT_PACKET_R33'; packet['cycle']='OWNING_LAYER_REMEDIATION_INPUT_PACKET_WITH_AUTHORITY_DECISION_STATUS_R33'; packet['source_head_sha']=head; packet['source_problem_reconciliation']=str(OUT_STATUS.relative_to(ROOT)); packet['source_prior_input_packet']=str(R31.relative_to(ROOT)); packet['source_candidate_review']=str(R32.relative_to(ROOT))
newinputs=[]; authority_pending=0; normal_pending=0
for x in r31.get('inputs') or []:
    y=dict(x)
    if y.get('remediation_input_uid')==INPUT_UID:
        if y.get('blocker_uid')!=TARGET: die('R33_INPUT_TARGET_IDENTITY_DRIFT')
        y['input_status']='PENDING_PRODUCT_AUTHORITY_DECISION'
        y['product_authority_gap_proven']=True
        y['product_authority_review_ref']=str(R32.relative_to(ROOT))
        y['candidate_behavior_uids']=['R32-CANDIDATE-A-MANUAL-CONTROL','R32-CANDIDATE-B-EVALUATION-SYSTEM-TRIGGER']
        y['owning_layer_contract_value']=None
        y['auto_fill_allowed']=False
        y['blocker_reduction_credit']=0
        authority_pending+=1
    else:
        if y.get('input_status')!='REQUIRED_NOT_PROVIDED': die(f'R33_UNEXPECTED_PRIOR_INPUT_STATUS:{y.get("remediation_input_uid")}:{y.get("input_status")}')
        y['product_authority_gap_proven']=False
        normal_pending+=1
    newinputs.append(y)
if authority_pending!=1 or normal_pending!=128: die(f'R33_INPUT_PARTITION_DRIFT:{authority_pending}:{normal_pending}')
packet['inputs']=newinputs
packet['denominators']=dict(packet.get('denominators') or {})
packet['denominators'].update({'total_required_inputs':129,'provided_inputs':0,'pending_inputs':129,'pending_product_authority_decisions':1,'pending_owning_layer_contract_inputs':128,'deterministic_materialization_candidates_before_input':0,'blocker_reduction_claimed':0})
packet['input_contract']=dict(packet.get('input_contract') or {})
packet['input_contract']['proven_product_authority_decision_may_not_be_auto_filled']=True
packet['input_contract']['candidate_review_does_not_supply_contract_value']=True
packet['next_execution_gate']='CONTINUE_ROLE_SAFE_CANDIDATE_AUTHORING_FOR_128_UNRESOLVED_INPUTS_AND_HOLD_ONE_AUTHORITY_DECISION_PENDING_SELECTION'
packet['stage02_status']='BLOCKED'; packet['stage03_allowed']=False; packet['website_construction_allowed']=False; packet['deployment_allowed']=False
OUT_INPUT.write_text(yaml.safe_dump(packet,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
print('PASS: R33 current problems=129 => true authority=1 unresolved=128; blocker reduction=0')
print('PASS: R33 inputs=129 => authority decision pending=1 owning-layer contract pending=128 provided=0')
