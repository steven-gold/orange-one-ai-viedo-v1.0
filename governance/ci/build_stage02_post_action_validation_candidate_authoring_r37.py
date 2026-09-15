#!/usr/bin/env python3
from __future__ import annotations
from collections import Counter
from pathlib import Path
import subprocess,sys,yaml
ROOT=Path(__file__).resolve().parents[2]
R15=ROOT/'governance/test/stage02/STAGE02_POST_ACTION_VALIDATION_DEPENDENCY_TRACE_R15.yaml'
R33=ROOT/'governance/test/stage02/STAGE02_CURRENT_FUNCTIONAL_CONTRACT_DECISION_STATUS_R33.yaml'
OUT=ROOT/'governance/test/stage02/STAGE02_POST_ACTION_VALIDATION_CANDIDATE_AUTHORING_R37.yaml'

def die(m): print(f'BLOCK: {m}',file=sys.stderr); raise SystemExit(1)
def load(p):
 o=yaml.safe_load(p.read_text(encoding='utf-8')) if p.is_file() else None
 if not isinstance(o,dict): die(f'MAPPING_REQUIRED:{p.relative_to(ROOT)}')
 return o
r15=load(R15); r33=load(R33)
if (r15.get('denominators') or {}).get('post_action_validation_gaps_traced')!=18: die('R37_R15_DENOMINATOR_DRIFT')
current={x.get('blocker_uid'):x for x in r33.get('problems') or [] if x.get('category')=='POST_ACTION_VALIDATION_NODE_MISSING'}
if len(current)!=18: die(f'R37_CURRENT_POST_ACTION_DENOMINATOR:{len(current)}')
trace={x.get('blocker_uid'):x for x in r15.get('records') or []}
if set(current)!=set(trace): die('R37_R15_R33_IDENTITY_DRIFT')
records=[]; classes=Counter(); sigcounts=Counter()
for bid,p in sorted(current.items()):
 t=trace[bid]; tr=t.get('trace') or {}
 evidence=t.get('result_or_state_signal_evidence') or []
 # Deduplicate exact signal identity by key + scalar value. Evidence copies from frozen/current count once.
 signals={}
 for e in evidence:
  if not isinstance(e,dict): continue
  k=e.get('key'); v=e.get('value')
  if k in {'state_event','result','result_state','state_effect','completion_state'} and v not in (None,'',[],{}): signals[(str(k),str(v))]={'key':str(k),'value':str(v)}
 vals=list(signals.values())
 candidate=None; cls='NO_UNIQUE_VALIDATION_SIGNAL'; reason='NO_EXACT_FROZEN_RESULT_OR_STATE_SIGNAL'
 if len(vals)==1:
  s=vals[0]
  candidate={
   'validation_contract_type':'EXACT_FROZEN_SUCCESS_SIGNAL_ASSERTION',
   'signal_key':s['key'],'expected_signal':s['value'],
   'assertion':'OBSERVED_POST_ACTION_SIGNAL_MUST_EQUAL_EXACT_REGISTERED_SIGNAL',
   'timing_boundary':'DIRECT_POST_ACTION_RESULT_OR_REGISTERED_PORT_STATE_SIGNAL_ONLY',
   'failure_behavior':'VALIDATION_FAIL_CLOSED_NO_SUCCESS_PROMOTION',
   'derivation':'MECHANICAL_WRAPPER_AROUND_ONE_EXACT_FROZEN_SIGNAL_NO_NEW_BUSINESS_VALUE',
  }
  cls='UNIQUE_ROLE_SAFE_VALIDATION_CANDIDATE'; reason='EXACTLY_ONE_DISTINCT_FROZEN_RESULT_OR_STATE_SIGNAL'
 elif len(vals)>1:
  cls='MULTIPLE_TEMPORAL_OR_RESULT_SIGNALS'; reason='MULTIPLE_DISTINCT_SIGNALS_REQUIRE_PRODUCT_OR_CONTRACT_TIMING_DECISION'
 classes[cls]+=1; sigcounts[len(vals)]+=1
 records.append({
  'blocker_uid':bid,'problem_uid':p.get('problem_uid'),'scope':p.get('scope'),'action_uid':p.get('target_uid'),
  'port_uid':tr.get('port_uid'),'operation_id':tr.get('operation_id'),'method_effective_path':tr.get('method_effective_path'),
  'distinct_frozen_signals':vals,'distinct_signal_count':len(vals),'classification':cls,'classification_reason':reason,'candidate':candidate,
  'invented_business_value':False,'semantic_signal_inference_used':False,'precondition_promoted_to_postcondition':False,'blocker_reduction_credit':0,
  'materialization_allowed_next_cycle':candidate is not None,
 })
head=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
out={
 'schema_version':1,'artifact_uid':'STAGE02-POST-ACTION-VALIDATION-CANDIDATE-AUTHORING-R37','artifact_type':'NON_NORMATIVE_STAGE02_POST_ACTION_VALIDATION_CANDIDATE_AUTHORING','normative_authority':False,'stage_uid':'STAGE-02','source_head_sha':head,
 'source_contracts':{'trace_r15':str(R15.relative_to(ROOT)),'current_decision_status_r33':str(R33.relative_to(ROOT))},
 'authoring_contract':{
  'one_exact_frozen_success_signal_may_be_wrapped_as_validation_assertion':True,'signal_business_value_may_be_changed':False,
  'multiple_distinct_signals_may_be_arbitrarily_collapsed':False,'precondition_gate_may_be_reused_as_postcondition':False,
  'candidate_is_non_authoritative_until_materialized_at_stage02_owning_layer':True,
 },
 'denominators':{'input_gaps':18,'candidate_count':sum(1 for x in records if x['candidate']),'classification_counts':dict(sorted(classes.items())),'distinct_signal_count_distribution':{str(k):v for k,v in sorted(sigcounts.items())},'blocker_reduction_claimed':0},
 'records':records,'current_specification_mutated':False,'immutable_stage1_source_mutated':False,'product_contract_materialized_this_cycle':False,'stage02_status':'BLOCKED','stage03_allowed':False,'website_construction_allowed':False,'deployment_allowed':False,
 'next_execution_gate':'MATERIALIZE_UNIQUE_R37_VALIDATION_CANDIDATES_AT_STAGE02_OWNING_LAYER_THEN_CLEAN_FRESH_REEXECUTION',
}
OUT.write_text(yaml.safe_dump(out,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
print(f"PASS: R37 candidates={out['denominators']['candidate_count']} classifications={dict(sorted(classes.items()))}")
print('PASS: no contract materialization or blocker reduction in candidate-authoring cycle')
