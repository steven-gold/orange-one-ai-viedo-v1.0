#!/usr/bin/env python3
from collections import Counter, defaultdict
from pathlib import Path
import subprocess,sys,yaml
ROOT=Path(__file__).resolve().parents[2]
R26=ROOT/'governance/test/stage02/STAGE02_CURRENT_FUNCTIONAL_CONTRACT_PROBLEM_RECONCILIATION_R26.yaml'
OUT=ROOT/'governance/test/stage02/STAGE02_OWNING_LAYER_REMEDIATION_INPUT_PACKET_R27.yaml'
EXPECTED={
 'ACTION_WITHOUT_CONTROL_OR_TRIGGER':1,
 'AUDIT_EVENT_NODE_MISSING':13,
 'FAILURE_STATE_ERROR_BINDING_MISSING':44,
 'PAYLOAD_INPUT_CONTRACT_MISSING':34,
 'POST_ACTION_VALIDATION_NODE_MISSING':18,
 'STATE_TRANSITION_LEDGER_FIELD_MISSING':40,
}
INPUT_KIND={
 'ACTION_WITHOUT_CONTROL_OR_TRIGGER':'REGISTERED_CONTROL_OR_EXACT_TRIGGER_BINDING',
 'AUDIT_EVENT_NODE_MISSING':'PHYSICAL_AUDIT_EVENT_UID_BINDING',
 'FAILURE_STATE_ERROR_BINDING_MISSING':'EXACT_FAILURE_ERROR_RECOVERY_BINDING',
 'PAYLOAD_INPUT_CONTRACT_MISSING':'EXPLICIT_PAYLOAD_INPUT_CONTRACT',
 'POST_ACTION_VALIDATION_NODE_MISSING':'EXPLICIT_POST_ACTION_VALIDATION_CONTRACT',
 'STATE_TRANSITION_LEDGER_FIELD_MISSING':'EXACT_SAME_TRANSITION_LEDGER_FIELD_VALUE',
}
def die(m): print(f'BLOCK: {m}',file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die('R27_SOURCE_MAPPING_REQUIRED')
    return o
r=load(R26); d=r.get('denominators') or {}
if d.get('fresh_effective_problems')!=150 or d.get('r19_exact_matched_problems')!=150 or d.get('category_counts')!=EXPECTED: die('R26_BASELINE_DRIFT')
if d.get('deterministic_materialization_candidates')!=0 or d.get('product_authority_gaps_proven')!=0: die('R26_CLASSIFICATION_DRIFT')
if r.get('next_execution_gate')!='FUNCTIONAL_CONTRACT_OWNING_LAYER_REMEDIATION_INPUT_REQUIRED': die('R26_NEXT_GATE_DRIFT')
rows=r.get('problems') or []
if len(rows)!=150: die(f'R26_PROBLEM_COUNT:{len(rows)}')
inputs=[]; cat=Counter(); owner=Counter(); scope=Counter(); groups=defaultdict(list)
for i,p in enumerate(rows,1):
    c=p.get('category'); oc=p.get('owning_contract')
    if c not in INPUT_KIND or not oc or not p.get('required_definition'): die(f'R27_SOURCE_PROBLEM_INCOMPLETE:{p.get("problem_uid")}')
    rec={
      'remediation_input_uid':f'STAGE02-R27-INPUT-{i:03d}','problem_uid':p.get('problem_uid'),'blocker_uid':p.get('blocker_uid'),'scope':p.get('scope'),'category':c,'target_uid':p.get('target_uid'),'missing_field_or_relation':p.get('missing_field_or_relation'),'owning_layer':p.get('owning_layer'),'owning_contract':oc,
      'required_input_kind':INPUT_KIND[c],'required_definition':p.get('required_definition'),'forbidden_substitutions':p.get('forbidden_substitutions'),'trace_ref':p.get('trace_ref'),'current_correction_history':p.get('correction_history') or [],
      'owning_layer_contract_value':None,'current_admissible_authority_evidence_refs':[],'input_status':'REQUIRED_NOT_PROVIDED','auto_fill_allowed':False,'semantic_inference_allowed':False,'historical_non_current_authority_allowed':False,'score_may_create_authority':False,'blocker_reduction_credit':0,
      'post_input_validation_required':['EXACT_IDENTITY_MATCH','CURRENT_ADMISSIBLE_AUTHORITY_OR_OWNING_LAYER_DEFINITION','NO_SCOPE_EXPANSION','NO_SEMANTIC_SUBSTITUTION','NO_HISTORICAL_NON_CURRENT_SUBSTITUTE']
    }
    inputs.append(rec); cat[c]+=1; owner[oc]+=1; scope[p.get('scope')]+=1; groups[c].append(rec['remediation_input_uid'])
if cat!=Counter(EXPECTED) or scope!=Counter({'ASSET-01':110,'CORE-01':40}): die('R27_RECOUNT_DRIFT')
head=subprocess.run(['git','rev-parse','HEAD'],cwd=str(ROOT),text=True,capture_output=True,check=True).stdout.strip()
out={
 'schema_version':1,'artifact_type':'NON_NORMATIVE_STAGE02_OWNING_LAYER_REMEDIATION_INPUT_PACKET_R27','normative_authority':False,'stage_uid':'STAGE-02','cycle':'OWNING_LAYER_REMEDIATION_INPUT_PACKET_R27','source_head_sha':head,'source_problem_reconciliation':str(R26.relative_to(ROOT)),
 'input_contract':{'purpose':'Collect exact owning-layer contract definitions or current-admissible exact authority evidence for the 150 current Stage-02 functional gaps without AI inventing product behavior.','every_current_problem_requires_one_input_record':True,'null_contract_value_means_not_yet_defined':True,'null_may_not_be_auto_filled':True,'input_packet_itself_is_not_product_authority':True,'input_packet_itself_reduces_blocker':False,'current_specification_mutation_forbidden':True,'historical_non_current_authority_forbidden':True,'semantic_substitution_forbidden':True,'scope_expansion_forbidden':True},
 'denominators':{'total_required_inputs':150,'provided_inputs':0,'pending_inputs':150,'scope_counts':dict(scope),'category_counts':dict(cat),'owning_contract_counts':dict(sorted(owner.items())),'deterministic_materialization_candidates_before_input':0,'blocker_reduction_claimed':0},
 'category_batches':[{'category':c,'required_input_kind':INPUT_KIND[c],'count':cat[c],'input_uids':groups[c]} for c in EXPECTED],
 'inputs':inputs,'current_specification_mutated':False,'immutable_stage1_source_mutated':False,'stage02_status':'BLOCKED','stage02_effective_blocker_count':150,'stage03_allowed':False,'website_construction_allowed':False,'deployment_allowed':False,
 'next_execution_gate':'INGEST_AND_VALIDATE_OWNING_LAYER_CONTRACT_DEFINITIONS_OR_CURRENT_ADMISSIBLE_EXACT_EVIDENCE'
}
OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(yaml.safe_dump(out,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
print('PASS: R27 generated exact owning-layer input records=150')
print('PASS: provided=0 pending=150; no contract values invented')
print('BLOCKED: next gate=INGEST_AND_VALIDATE_OWNING_LAYER_CONTRACT_DEFINITIONS_OR_CURRENT_ADMISSIBLE_EXACT_EVIDENCE')
