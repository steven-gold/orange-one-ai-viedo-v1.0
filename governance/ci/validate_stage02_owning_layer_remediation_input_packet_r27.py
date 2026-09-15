#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import sys,yaml
ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'governance/test/stage02/STAGE02_OWNING_LAYER_REMEDIATION_INPUT_PACKET_R27.yaml'
EXPECTED={'ACTION_WITHOUT_CONTROL_OR_TRIGGER':1,'AUDIT_EVENT_NODE_MISSING':13,'FAILURE_STATE_ERROR_BINDING_MISSING':44,'PAYLOAD_INPUT_CONTRACT_MISSING':34,'POST_ACTION_VALIDATION_NODE_MISSING':18,'STATE_TRANSITION_LEDGER_FIELD_MISSING':40}
def die(m): print(f'BLOCK: {m}',file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die('R27_MAPPING_REQUIRED')
    return o
d=load(DOC)
if d.get('artifact_type')!='NON_NORMATIVE_STAGE02_OWNING_LAYER_REMEDIATION_INPUT_PACKET_R27' or d.get('stage_uid')!='STAGE-02' or d.get('normative_authority') is not False: die('R27_IDENTITY_DRIFT')
c=d.get('input_contract') or {}
for k in ('every_current_problem_requires_one_input_record','null_contract_value_means_not_yet_defined','null_may_not_be_auto_filled','input_packet_itself_is_not_product_authority','current_specification_mutation_forbidden','historical_non_current_authority_forbidden','semantic_substitution_forbidden','scope_expansion_forbidden'):
    if c.get(k) is not True: die(f'R27_CONTRACT_DRIFT:{k}')
if c.get('input_packet_itself_reduces_blocker') is not False: die('R27_PREMATURE_REDUCTION_CONTRACT_DRIFT')
den=d.get('denominators') or {}
if den.get('total_required_inputs')!=150 or den.get('provided_inputs')!=0 or den.get('pending_inputs')!=150: die('R27_INPUT_DENOMINATOR_DRIFT')
if den.get('category_counts')!=EXPECTED or den.get('scope_counts')!={'ASSET-01':110,'CORE-01':40}: die('R27_SCOPE_OR_CATEGORY_DRIFT')
if den.get('deterministic_materialization_candidates_before_input')!=0 or den.get('blocker_reduction_claimed')!=0: die('R27_PREMATURE_CLOSURE_DRIFT')
rows=d.get('inputs') or []
if len(rows)!=150 or len({x.get('remediation_input_uid') for x in rows})!=150 or len({x.get('problem_uid') for x in rows})!=150 or len({x.get('blocker_uid') for x in rows})!=150: die('R27_INPUT_UID_DENOMINATOR_DRIFT')
cc=Counter(); sc=Counter()
for x in rows:
    if x.get('input_status')!='REQUIRED_NOT_PROVIDED' or x.get('owning_layer_contract_value') is not None or x.get('current_admissible_authority_evidence_refs')!=[]: die(f'R27_INPUT_PREPOPULATED:{x.get("remediation_input_uid")}')
    if x.get('auto_fill_allowed') is not False or x.get('semantic_inference_allowed') is not False or x.get('historical_non_current_authority_allowed') is not False or x.get('score_may_create_authority') is not False: die(f'R27_SAFETY_DRIFT:{x.get("remediation_input_uid")}')
    if x.get('blocker_reduction_credit')!=0: die(f'R27_BLOCKER_CREDIT_DRIFT:{x.get("remediation_input_uid")}')
    if not x.get('required_input_kind') or not x.get('required_definition') or not x.get('owning_contract'): die(f'R27_REQUIRED_METADATA_MISSING:{x.get("remediation_input_uid")}')
    cc[x.get('category')]+=1; sc[x.get('scope')]+=1
if dict(cc)!=EXPECTED or sc!=Counter({'ASSET-01':110,'CORE-01':40}): die('R27_RECOUNT_DRIFT')
if d.get('stage02_status')!='BLOCKED' or d.get('stage02_effective_blocker_count')!=150: die('R27_STAGE_STATE_DRIFT')
if d.get('next_execution_gate')!='INGEST_AND_VALIDATE_OWNING_LAYER_CONTRACT_DEFINITIONS_OR_CURRENT_ADMISSIBLE_EXACT_EVIDENCE': die('R27_NEXT_GATE_DRIFT')
if d.get('stage03_allowed') is not False or d.get('website_construction_allowed') is not False or d.get('deployment_allowed') is not False: die('R27_FAIL_CLOSED_DRIFT')
print('PASS: R27 owning-layer remediation input packet validated 150/150')
print('PASS: all 150 contract values remain unfilled; no AI inference or historical substitute allowed')
