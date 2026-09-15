#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import sys,yaml
ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'governance/test/stage02/STAGE02_TRANSITION_ROLE_SAFE_CANDIDATE_AUTHORING_R36.yaml'
R34=ROOT/'governance/test/stage02/STAGE02_TRANSITION_LEDGER_REQUIRED_APPLICABILITY_R34.yaml'
FIELDS={'mutation_owner','failure_state','recovery','audit_event_uid'}
ALLOWED={'UNIQUE_ROLE_SAFE_CANDIDATE','ROLE_ADJACENT_EVIDENCE_ONLY','MULTIPLE_REASONABLE_CANDIDATES','NO_ROLE_SAFE_CANDIDATE'}
def die(m): print(f'BLOCK: {m}',file=sys.stderr); raise SystemExit(1)
def load(p):
 o=yaml.safe_load(p.read_text(encoding='utf-8')) if p.is_file() else None
 if not isinstance(o,dict): die(f'MAPPING_REQUIRED:{p.relative_to(ROOT)}')
 return o
d=load(DOC); r34=load(R34)
if d.get('artifact_type')!='NON_NORMATIVE_STAGE02_TRANSITION_ROLE_SAFE_CANDIDATE_AUTHORING' or d.get('normative_authority') is not False or d.get('stage_uid')!='STAGE-02': die('R36_IDENTITY_DRIFT')
c=d.get('authoring_contract') or {}
for k in ('candidate_requires_unique_exact_role_safe_chain','recovery_candidate_requires_direct_trigger_action_exact_gate_match_exact_error_recovery','audit_candidate_requires_exact_registered_event_identity_match','candidate_is_authoring_output_not_materialized_contract'):
 if c.get(k) is not True: die(f'R36_CONTRACT_REQUIRED:{k}')
for k in ('action_owner_directly_promoted_to_mutation_owner','page_error_state_directly_promoted_to_failure_state','dotted_event_token_directly_promoted_to_audit_event_uid'):
 if c.get(k) is not False: die(f'R36_CROSS_ROLE_BOUNDARY_DRIFT:{k}')
rows=d.get('records') or []
if len(rows)!=40 or len({x.get('blocker_uid') for x in rows})!=40: die('R36_RECORD_DENOMINATOR')
r34_ids={x.get('blocker_uid') for x in r34.get('records') or []}
if {x.get('blocker_uid') for x in rows}!=r34_ids: die('R36_R34_IDENTITY_COVERAGE_DRIFT')
if {x.get('missing_field') for x in rows}!=FIELDS: die('R36_FIELD_SET_DRIFT')
classes=Counter(); candidate_fields=Counter(); candidates=0
for x in rows:
 cls=x.get('classification'); field=x.get('missing_field'); cand=x.get('candidate')
 if cls not in ALLOWED: die(f'R36_CLASSIFICATION_INVALID:{x.get("blocker_uid")}:{cls}')
 classes[cls]+=1
 if x.get('cross_role_substitution_used') is not False or x.get('semantic_similarity_used') is not False or x.get('invented_uid_used') is not False: die(f'R36_SAFETY_DRIFT:{x.get("blocker_uid")}')
 if x.get('blocker_reduction_credit')!=0: die('R36_PREMATURE_REDUCTION')
 if cls=='UNIQUE_ROLE_SAFE_CANDIDATE':
  if not isinstance(cand,dict) or cand.get('value') in (None,'',[],{}): die(f'R36_CANDIDATE_MISSING:{x.get("blocker_uid")}')
  if x.get('materialization_allowed_next_cycle') is not True: die('R36_MATERIALIZATION_FLAG_DRIFT')
  if field=='recovery' and cand.get('derivation')!='EXACT_DIRECT_TRIGGER_ACTION_ERROR_RECOVERY_WITH_MATCHING_TRANSITION_GATE': die('R36_RECOVERY_DERIVATION_DRIFT')
  if field=='audit_event_uid' and cand.get('derivation')!='EXACT_DIRECT_RUNTIME_PORT_EVENT_TOKEN_TO_REGISTERED_EVENT_IDENTITY': die('R36_AUDIT_DERIVATION_DRIFT')
  if field in {'mutation_owner','failure_state'}: die(f'R36_FORBIDDEN_CANDIDATE_FIELD_WITHOUT_ROLE_EQUIVALENCE:{field}')
  candidates+=1; candidate_fields[field]+=1
 else:
  if cand is not None or x.get('materialization_allowed_next_cycle') is not False: die(f'R36_NONCANDIDATE_VALUE_DRIFT:{x.get("blocker_uid")}')
den=d.get('denominators') or {}
if den.get('input_required_fields')!=40 or den.get('transition_count')!=10: die('R36_DENOMINATOR_DRIFT')
if den.get('candidate_count')!=candidates or den.get('candidate_field_counts')!=dict(sorted(candidate_fields.items())): die('R36_CANDIDATE_COUNT_DRIFT')
if den.get('classification_counts')!=dict(sorted(classes.items())): die('R36_CLASS_COUNT_DRIFT')
if den.get('blocker_reduction_claimed')!=0 or d.get('product_contract_materialized_this_cycle') is not False: die('R36_PREMATURE_MATERIALIZATION')
if d.get('current_specification_mutated') is not False or d.get('immutable_stage1_source_mutated') is not False or d.get('stage02_status')!='BLOCKED': die('R36_FAIL_CLOSED_DRIFT')
print(f'PASS: R36 validates {candidates} unique role-safe candidates across 40 required transition fields; reduction=0')
print(f'PASS: classifications={dict(sorted(classes.items()))}')
