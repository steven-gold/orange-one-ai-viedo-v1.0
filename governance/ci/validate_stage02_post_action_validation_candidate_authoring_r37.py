#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import sys,yaml
ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'governance/test/stage02/STAGE02_POST_ACTION_VALIDATION_CANDIDATE_AUTHORING_R37.yaml'
R33=ROOT/'governance/test/stage02/STAGE02_CURRENT_FUNCTIONAL_CONTRACT_DECISION_STATUS_R33.yaml'
def die(m): print(f'BLOCK: {m}',file=sys.stderr); raise SystemExit(1)
def load(p):
 o=yaml.safe_load(p.read_text(encoding='utf-8')) if p.is_file() else None
 if not isinstance(o,dict): die(f'MAPPING_REQUIRED:{p.relative_to(ROOT)}')
 return o
d=load(DOC); r33=load(R33)
if d.get('artifact_type')!='NON_NORMATIVE_STAGE02_POST_ACTION_VALIDATION_CANDIDATE_AUTHORING' or d.get('normative_authority') is not False or d.get('stage_uid')!='STAGE-02': die('R37_IDENTITY_DRIFT')
c=d.get('authoring_contract') or {}
if c.get('one_exact_frozen_success_signal_may_be_wrapped_as_validation_assertion') is not True or c.get('signal_business_value_may_be_changed') is not False or c.get('multiple_distinct_signals_may_be_arbitrarily_collapsed') is not False or c.get('precondition_gate_may_be_reused_as_postcondition') is not False or c.get('candidate_is_non_authoritative_until_materialized_at_stage02_owning_layer') is not True: die('R37_BOUNDARY_DRIFT')
rows=d.get('records') or []
if len(rows)!=18 or len({x.get('blocker_uid') for x in rows})!=18: die('R37_RECORD_DENOMINATOR_DRIFT')
current={x.get('blocker_uid') for x in r33.get('problems') or [] if x.get('category')=='POST_ACTION_VALIDATION_NODE_MISSING'}
if {x.get('blocker_uid') for x in rows}!=current: die('R37_R33_IDENTITY_COVERAGE_DRIFT')
classes=Counter(); cand=0; dist=Counter()
for x in rows:
 cls=x.get('classification'); n=int(x.get('distinct_signal_count') or 0); candidate=x.get('candidate'); vals=x.get('distinct_frozen_signals') or []
 if n!=len(vals): die(f'R37_SIGNAL_COUNT_DRIFT:{x.get("blocker_uid")}')
 if len({(v.get('key'),v.get('value')) for v in vals if isinstance(v,dict)})!=n: die(f'R37_SIGNAL_DEDUP_DRIFT:{x.get("blocker_uid")}')
 dist[n]+=1; classes[cls]+=1
 if x.get('invented_business_value') is not False or x.get('semantic_signal_inference_used') is not False or x.get('precondition_promoted_to_postcondition') is not False or x.get('blocker_reduction_credit')!=0: die(f'R37_SAFETY_DRIFT:{x.get("blocker_uid")}')
 if cls=='UNIQUE_ROLE_SAFE_VALIDATION_CANDIDATE':
  if n!=1 or not isinstance(candidate,dict): die(f'R37_UNIQUE_CANDIDATE_SHAPE:{x.get("blocker_uid")}')
  s=vals[0]
  if candidate.get('signal_key')!=s.get('key') or candidate.get('expected_signal')!=s.get('value'): die(f'R37_CANDIDATE_SIGNAL_DRIFT:{x.get("blocker_uid")}')
  if candidate.get('derivation')!='MECHANICAL_WRAPPER_AROUND_ONE_EXACT_FROZEN_SIGNAL_NO_NEW_BUSINESS_VALUE': die('R37_DERIVATION_DRIFT')
  if x.get('materialization_allowed_next_cycle') is not True: die('R37_MATERIALIZATION_FLAG_DRIFT')
  cand+=1
 elif cls=='MULTIPLE_TEMPORAL_OR_RESULT_SIGNALS':
  if n<2 or candidate is not None or x.get('materialization_allowed_next_cycle') is not False: die(f'R37_MULTI_SIGNAL_SAFETY_DRIFT:{x.get("blocker_uid")}')
 elif cls=='NO_UNIQUE_VALIDATION_SIGNAL':
  if n!=0 or candidate is not None or x.get('materialization_allowed_next_cycle') is not False: die(f'R37_NO_SIGNAL_SAFETY_DRIFT:{x.get("blocker_uid")}')
 else: die(f'R37_CLASSIFICATION_INVALID:{cls}')
den=d.get('denominators') or {}
if den.get('input_gaps')!=18 or den.get('candidate_count')!=cand or den.get('classification_counts')!=dict(sorted(classes.items())) or den.get('distinct_signal_count_distribution')!={str(k):v for k,v in sorted(dist.items())}: die('R37_DENOMINATOR_RECOMPUTE_DRIFT')
if den.get('blocker_reduction_claimed')!=0 or d.get('product_contract_materialized_this_cycle') is not False: die('R37_PREMATURE_MATERIALIZATION')
if d.get('current_specification_mutated') is not False or d.get('immutable_stage1_source_mutated') is not False or d.get('stage02_status')!='BLOCKED': die('R37_FAIL_CLOSED_DRIFT')
print(f'PASS: R37 validates {cand} unique post-action validation candidates; no materialization/reduction')
print(f'PASS: classifications={dict(sorted(classes.items()))}')
