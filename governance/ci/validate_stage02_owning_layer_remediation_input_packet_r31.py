#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import sys,yaml
ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'governance/test/stage02/STAGE02_OWNING_LAYER_REMEDIATION_INPUT_PACKET_R31.yaml'
EXPECTED={'FAILURE_STATE_ERROR_BINDING_MISSING':23,'POST_ACTION_VALIDATION_NODE_MISSING':18,'PAYLOAD_INPUT_CONTRACT_MISSING':34,'ACTION_WITHOUT_CONTROL_OR_TRIGGER':1,'AUDIT_EVENT_NODE_MISSING':13,'STATE_TRANSITION_LEDGER_FIELD_MISSING':40}
def die(m): print(f'BLOCK: {m}',file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die('R31_MAPPING_REQUIRED')
    return o
d=load(DOC)
if d.get('artifact_type')!='NON_NORMATIVE_STAGE02_OWNING_LAYER_REMEDIATION_INPUT_PACKET_R31' or d.get('stage_uid')!='STAGE-02' or d.get('normative_authority') is not False: die('R31_IDENTITY_DRIFT')
c=d.get('input_contract') or {}
for key in ('stable_input_uids_preserved_from_r27','retired_false_positive_inputs_may_not_be_reused','every_current_problem_requires_one_input_record','null_contract_value_means_not_yet_defined','null_may_not_be_auto_filled','candidate_authoring_must_remain_non_authoritative_until_role_and_chain_review_pass','current_specification_mutation_forbidden','historical_non_current_authority_forbidden','semantic_substitution_forbidden','scope_expansion_forbidden'):
    if c.get(key) is not True: die(f'R31_INPUT_CONTRACT_DRIFT:{key}')
den=d.get('denominators') or {}
if den.get('total_required_inputs')!=129 or den.get('provided_inputs')!=0 or den.get('pending_inputs')!=129 or den.get('retired_false_positive_inputs')!=21: die(f'R31_DENOMINATOR_DRIFT:{den}')
if den.get('scope_counts')!={'ASSET-01':89,'CORE-01':40} or den.get('category_counts')!=EXPECTED or den.get('blocker_reduction_claimed')!=0: die('R31_COUNT_DRIFT')
rows=d.get('inputs') or []; retired=d.get('retired_inputs') or []
if len(rows)!=129 or len({x.get('blocker_uid') for x in rows})!=129 or len({x.get('remediation_input_uid') for x in rows})!=129: die('R31_ACTIVE_INPUT_SET_DRIFT')
if len(retired)!=21 or len({x.get('blocker_uid') for x in retired})!=21 or len({x.get('remediation_input_uid') for x in retired})!=21: die('R31_RETIRED_INPUT_SET_DRIFT')
if {x.get('blocker_uid') for x in rows}&{x.get('blocker_uid') for x in retired}: die('R31_ACTIVE_RETIRED_OVERLAP')
if Counter(x.get('category') for x in rows)!=Counter(EXPECTED) or Counter(x.get('scope') for x in rows)!=Counter({'ASSET-01':89,'CORE-01':40}): die('R31_ACTIVE_RECOUNT_DRIFT')
for x in rows:
    if x.get('owning_layer_contract_value') is not None or x.get('input_status')!='REQUIRED_NOT_PROVIDED' or x.get('auto_fill_allowed') is not False or x.get('semantic_inference_allowed') is not False or x.get('blocker_reduction_credit')!=0: die(f'R31_ACTIVE_ROW_SAFETY_DRIFT:{x.get("blocker_uid")}')
    if x.get('current_problem_baseline')!='R30_CURRENT_129': die(f'R31_BASELINE_REF_DRIFT:{x.get("blocker_uid")}')
for x in retired:
    if x.get('retirement_reason')!='R29_SCANNER_FALSE_POSITIVE_EXACT_NOT_APPLICABLE' or x.get('replacement_input_uid') is not None: die(f'R31_RETIRED_ROW_DRIFT:{x.get("blocker_uid")}')
if d.get('current_specification_mutated') is not False or d.get('immutable_stage1_source_mutated') is not False: die('R31_MUTATION_FLAG_DRIFT')
print('PASS: R31 active inputs=129 pending=129; retired false-positive inputs=21; stable identities preserved')
