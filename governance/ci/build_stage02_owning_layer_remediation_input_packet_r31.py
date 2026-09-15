#!/usr/bin/env python3
from collections import Counter, defaultdict
from pathlib import Path
import subprocess,sys,yaml
ROOT=Path(__file__).resolve().parents[2]
R30=ROOT/'governance/test/stage02/STAGE02_CURRENT_FUNCTIONAL_CONTRACT_PROBLEM_RECONCILIATION_R30.yaml'
R27=ROOT/'governance/test/stage02/STAGE02_OWNING_LAYER_REMEDIATION_INPUT_PACKET_R27.yaml'
OUT=ROOT/'governance/test/stage02/STAGE02_OWNING_LAYER_REMEDIATION_INPUT_PACKET_R31.yaml'
EXPECTED={'FAILURE_STATE_ERROR_BINDING_MISSING':23,'POST_ACTION_VALIDATION_NODE_MISSING':18,'PAYLOAD_INPUT_CONTRACT_MISSING':34,'ACTION_WITHOUT_CONTROL_OR_TRIGGER':1,'AUDIT_EVENT_NODE_MISSING':13,'STATE_TRANSITION_LEDGER_FIELD_MISSING':40}
def die(m): print(f'BLOCK: {m}',file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die(f'MAPPING_REQUIRED:{p.relative_to(ROOT)}')
    return o
r30=load(R30); r27=load(R27)
active={x.get('blocker_uid'):x for x in r30.get('problems') or []}
if len(active)!=129: die(f'R31_ACTIVE_DENOMINATOR:{len(active)}')
old={x.get('blocker_uid'):x for x in r27.get('inputs') or []}
if len(old)!=150: die(f'R31_R27_INPUT_DENOMINATOR:{len(old)}')
missing=set(active)-set(old)
if missing: die(f'R31_ACTIVE_INPUT_MISSING:{sorted(missing)[:5]}')
inputs=[]; cats=Counter(); scopes=Counter(); owners=Counter(); batches=defaultdict(list)
for blocker,problem in active.items():
    src=dict(old[blocker])
    if src.get('problem_uid')!=problem.get('problem_uid') or src.get('scope')!=problem.get('scope') or src.get('category')!=problem.get('category') or src.get('target_uid')!=problem.get('target_uid') or src.get('missing_field_or_relation')!=problem.get('missing_field_or_relation'): die(f'R31_INPUT_IDENTITY_DRIFT:{blocker}')
    if src.get('owning_layer_contract_value') is not None or src.get('input_status')!='REQUIRED_NOT_PROVIDED': die(f'R31_PREEXISTING_VALUE_DRIFT:{blocker}')
    src['current_problem_baseline']='R30_CURRENT_129'
    src['input_status']='REQUIRED_NOT_PROVIDED'
    src['blocker_reduction_credit']=0
    inputs.append(src); cats[src['category']]+=1; scopes[src['scope']]+=1; owners[src['owning_contract']]+=1; batches[src['category']].append(src['remediation_input_uid'])
retired=[]
for blocker,src in old.items():
    if blocker not in active:
        retired.append({'remediation_input_uid':src.get('remediation_input_uid'),'problem_uid':src.get('problem_uid'),'blocker_uid':blocker,'scope':src.get('scope'),'category':src.get('category'),'target_uid':src.get('target_uid'),'retirement_reason':'R29_SCANNER_FALSE_POSITIVE_EXACT_NOT_APPLICABLE','replacement_input_uid':None})
if len(retired)!=21: die(f'R31_RETIRED_INPUT_DENOMINATOR:{len(retired)}')
if dict(cats)!=EXPECTED or scopes!=Counter({'ASSET-01':89,'CORE-01':40}): die(f'R31_COUNT_DRIFT:{dict(cats)}:{dict(scopes)}')
head=subprocess.run(['git','rev-parse','HEAD'],cwd=str(ROOT),text=True,capture_output=True,check=True).stdout.strip()
out={'schema_version':1,'artifact_type':'NON_NORMATIVE_STAGE02_OWNING_LAYER_REMEDIATION_INPUT_PACKET_R31','normative_authority':False,'stage_uid':'STAGE-02','cycle':'OWNING_LAYER_REMEDIATION_INPUT_PACKET_CURRENT_129_R31','source_head_sha':head,'source_problem_reconciliation':str(R30.relative_to(ROOT)),'source_prior_input_packet':str(R27.relative_to(ROOT)),'input_contract':{'purpose':'Collect exact owning-layer contract definitions or current-admissible exact authority evidence for the 129 current Stage-02 functional gaps after R29 applicability correction.','stable_input_uids_preserved_from_r27':True,'retired_false_positive_inputs_may_not_be_reused':True,'every_current_problem_requires_one_input_record':True,'null_contract_value_means_not_yet_defined':True,'null_may_not_be_auto_filled':True,'candidate_authoring_must_remain_non_authoritative_until_role_and_chain_review_pass':True,'current_specification_mutation_forbidden':True,'historical_non_current_authority_forbidden':True,'semantic_substitution_forbidden':True,'scope_expansion_forbidden':True},'denominators':{'total_required_inputs':129,'provided_inputs':0,'pending_inputs':129,'retired_false_positive_inputs':21,'scope_counts':dict(sorted(scopes.items())),'category_counts':dict(sorted(cats.items())),'owning_contract_counts':dict(sorted(owners.items())),'deterministic_materialization_candidates_before_input':0,'blocker_reduction_claimed':0},'category_batches':[{'category':cat,'required_input_kind':next(x['required_input_kind'] for x in inputs if x['category']==cat),'count':len(uids),'input_uids':sorted(uids)} for cat,uids in sorted(batches.items())],'retired_inputs':sorted(retired,key=lambda x:x['remediation_input_uid']),'inputs':sorted(inputs,key=lambda x:x['remediation_input_uid']),'current_specification_mutated':False,'immutable_stage1_source_mutated':False,'stage02_status':'BLOCKED','stage03_allowed':False,'website_construction_allowed':False,'deployment_allowed':False,'next_execution_gate':'ROLE_SAFE_FUNCTIONAL_CHAIN_CANDIDATE_AUTHORING_AND_REVIEW_FOR_CURRENT_129_INPUTS'}
OUT.write_text(yaml.safe_dump(out,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
print('PASS: R31 owning-layer input packet current=129 pending=129 retired_false_positive=21; stable R27 input UIDs preserved')
