#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import sys,yaml
ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'governance/test/stage02/STAGE02_TRANSITION_LEDGER_REQUIRED_APPLICABILITY_R34.yaml'
FIELDS={'mutation_owner','failure_state','recovery','audit_event_uid'}
def die(m): print(f'BLOCK: {m}',file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die('R34_MAPPING_REQUIRED')
    return o
d=load(DOC)
if d.get('schema_version')!=2 or d.get('artifact_type')!='NON_NORMATIVE_STAGE02_TRANSITION_LEDGER_REQUIRED_APPLICABILITY_R34' or d.get('stage_uid')!='STAGE-02' or d.get('normative_authority') is not False: die('R34_IDENTITY_DRIFT')
c=d.get('normative_contract') or {}
if c.get('page_with_state_stage_transition_registry_requires_machine_readable_state_transition_ledger') is not True: die('R34_LEDGER_REQUIREMENT_DRIFT')
if c.get('required_optional_na_general_rule_does_not_override_explicit_s060_must') is not True or c.get('cross_role_substitution_for_missing_field_forbidden') is not True or c.get('missing_required_value_may_not_be_invented') is not True: die('R34_BOUNDARY_DRIFT')
if c.get('successor_materialization_must_be_applied_before_effective_gap_counting') is not True: die('R34_SUCCESSOR_AWARENESS_DRIFT')
required=set(c.get('every_transition_must_bind') or [])
for key in {'mutation_owner','failure_state','recovery','audit_or_event','illegal_transition_tests'}:
    if key not in required: die(f'R34_MANDATORY_FIELD_CONTRACT_DRIFT:{key}')
den=d.get('denominators') or {}
if den.get('raw_transition_required_field_gaps_r35')!=50 or den.get('already_materialized_illegal_transition_test_gaps')!=10: die(f'R34_RAW_SUCCESSOR_DENOMINATOR_DRIFT:{den}')
if den.get('current_transition_ledger_field_problems')!=40 or den.get('transition_count')!=10 or den.get('required_missing_fields_per_transition')!=4: die(f'R34_DENOMINATOR_DRIFT:{den}')
if den.get('not_applicable_count')!=0 or den.get('optional_count')!=0 or den.get('required_count')!=40 or den.get('candidate_values_materialized_this_cycle')!=0 or den.get('blocker_reduction_claimed_this_cycle')!=0: die('R34_APPLICABILITY_RESULT_DRIFT')
if den.get('field_counts')!={f:10 for f in sorted(FIELDS)}: die(f'R34_FIELD_COUNT_DRIFT:{den.get("field_counts")}')
rows=d.get('records') or []
if len(rows)!=40 or len({x.get('blocker_uid') for x in rows})!=40: die('R34_RECORD_SET_DRIFT')
transition_set={(x.get('scope'),x.get('transition_uid')) for x in rows}
if len(transition_set)!=10: die('R34_TRANSITION_SET_DRIFT')
if Counter((x.get('scope'),x.get('transition_uid')) for x in rows)!=Counter({k:4 for k in transition_set}): die('R34_TRANSITION_FOUR_FIELD_MATRIX_DRIFT')
if {x.get('missing_field') for x in rows}!=FIELDS: die('R34_FIELD_SET_DRIFT')
for x in rows:
    if x.get('normative_applicability')!='REQUIRED' or x.get('same_transition_field_value_present') is not False or x.get('cross_role_substitution_allowed') is not False or x.get('candidate_value') is not None or x.get('blocker_reduction_credit')!=0: die(f'R34_ROW_SAFETY_DRIFT:{x.get("blocker_uid")}')
    if x.get('illegal_transition_tests_present_in_raw') is not False: die(f'R34_RAW_ILLEGAL_TEST_EXPECTED_MISSING:{x.get("transition_uid")}')
    if x.get('illegal_transition_tests_materialized_successor') is not True or x.get('illegal_transition_tests_effectively_present') is not True: die(f'R34_ILLEGAL_TEST_SUCCESSOR_MISSING:{x.get("transition_uid")}')
    if not x.get('illegal_transition_tests_successor_remediation_uid') or int(x.get('illegal_transition_tests_successor_test_count') or 0)<1: die(f'R34_ILLEGAL_TEST_SUCCESSOR_EVIDENCE_DRIFT:{x.get("transition_uid")}')
if len({x.get('illegal_transition_tests_successor_remediation_uid') for x in rows})!=10: die('R34_ILLEGAL_TEST_SUCCESSOR_UID_DENOMINATOR')
if d.get('current_specification_mutated') is not False or d.get('immutable_stage1_source_mutated') is not False or d.get('stage02_status')!='BLOCKED': die('R34_FAIL_CLOSED_DRIFT')
print('PASS: R34 validates raw 50 transition-field gaps, 10 existing illegal-transition-test successors, and 40 unresolved REQUIRED ledger fields')
