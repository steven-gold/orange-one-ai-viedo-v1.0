#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import sys,yaml
ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'governance/test/stage02/STAGE02_CURRENT_FUNCTIONAL_CONTRACT_PROBLEM_RECONCILIATION_R30.yaml'
EXPECTED={'FAILURE_STATE_ERROR_BINDING_MISSING':23,'POST_ACTION_VALIDATION_NODE_MISSING':18,'PAYLOAD_INPUT_CONTRACT_MISSING':34,'ACTION_WITHOUT_CONTROL_OR_TRIGGER':1,'AUDIT_EVENT_NODE_MISSING':13,'STATE_TRANSITION_LEDGER_FIELD_MISSING':40}
def die(m): print(f'BLOCK: {m}',file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die('R30_MAPPING_REQUIRED')
    return o
d=load(DOC)
if d.get('artifact_type')!='NON_NORMATIVE_STAGE02_CURRENT_FUNCTIONAL_CONTRACT_PROBLEM_RECONCILIATION_R30' or d.get('stage_uid')!='STAGE-02' or d.get('normative_authority') is not False: die('R30_IDENTITY_DRIFT')
den=d.get('denominators') or {}
if den.get('fresh_effective_problems')!=129 or den.get('prior_r26_problems')!=150 or den.get('r28_scanner_false_positives_superseded')!=21: die(f'R30_DENOMINATOR_DRIFT:{den}')
if den.get('active_scope_counts')!={'ASSET-01':89,'CORE-01':40} or den.get('active_category_counts')!=EXPECTED: die('R30_ACTIVE_COUNTS_DRIFT')
if den.get('product_authority_gaps_proven')!=0 or den.get('deterministic_materialization_candidates')!=0 or den.get('effective_stage02_blocker_reduction_claimed')!=0: die('R30_UNSAFE_CLASSIFICATION_DRIFT')
rows=d.get('problems') or []; retired=d.get('superseded_scanner_false_positives') or []
if len(rows)!=129 or len({x.get('blocker_uid') for x in rows})!=129: die('R30_ACTIVE_PROBLEM_SET_DRIFT')
if len(retired)!=21 or len({x.get('blocker_uid') for x in retired})!=21: die('R30_RETIRED_SET_DRIFT')
if {x.get('blocker_uid') for x in rows}&{x.get('blocker_uid') for x in retired}: die('R30_ACTIVE_RETIRED_OVERLAP')
if any(x.get('category')!='FAILURE_STATE_ERROR_BINDING_MISSING' or x.get('scope')!='ASSET-01' or x.get('reason')!='EXACT_FAILURE_RECOVERY_NOT_APPLICABLE' for x in retired): die('R30_RETIRED_REASON_DRIFT')
if Counter(x.get('category') for x in rows)!=Counter(EXPECTED): die('R30_CATEGORY_RECOUNT_DRIFT')
if Counter(x.get('scope') for x in rows)!=Counter({'ASSET-01':89,'CORE-01':40}): die('R30_SCOPE_RECOUNT_DRIFT')
if any(x.get('current_effective_gap_present') is not True or x.get('blocker_reduction_credit')!=0 for x in rows): die('R30_ACTIVE_ROW_STATE_DRIFT')
if d.get('current_specification_mutated') is not False or d.get('immutable_stage1_source_mutated') is not False: die('R30_MUTATION_FLAG_DRIFT')
print('PASS: R30 current active problems=129; superseded scanner false positives=21; no authority/materialization promotion')
