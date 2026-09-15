#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / 'governance/test/stage02/STAGE02_POST_ACTION_VALIDATION_MATERIALIZATION_R38.yaml'
R37 = ROOT / 'governance/test/stage02/STAGE02_POST_ACTION_VALIDATION_CANDIDATE_AUTHORING_R37.yaml'
ASSET_LEDGER = ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/ASSET-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml'
DETAIL = 'no explicit success/validation/evaluation contract'


def die(msg: str) -> None:
    print(f'BLOCK: {msg}', file=sys.stderr)
    raise SystemExit(1)


def load(path: Path):
    obj = yaml.safe_load(path.read_text(encoding='utf-8')) if path.is_file() else None
    if not isinstance(obj, dict):
        die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj


d = load(DOC)
r37 = load(R37)
ledger = load(ASSET_LEDGER)
if d.get('artifact_type') != 'NON_NORMATIVE_STAGE02_MATERIAL_REMEDIATION_EVIDENCE' or d.get('normative_authority') is not False or d.get('stage_uid') != 'STAGE-02':
    die('R38_IDENTITY_DRIFT')
mc = d.get('materialization_contract') or {}
if mc.get('candidate_count') != 15 or mc.get('new_materialization_count') != 15 or mc.get('closure_type') != 'POST_ACTION_VALIDATION_CONTRACT':
    die(f'R38_MATERIALIZATION_DENOMINATOR_DRIFT:{mc}')
for k in ('exact_signal_value_preserved',):
    if mc.get(k) is not True:
        die(f'R38_REQUIRED_TRUE:{k}')
for k in ('new_business_value_introduced','precondition_promoted_to_postcondition','semantic_similarity_used','raw_source_mutated','current_specification_mutated'):
    if mc.get(k) is not False:
        die(f'R38_REQUIRED_FALSE:{k}')

r37_candidates = {x.get('action_uid'): x for x in r37.get('records') or [] if x.get('classification') == 'UNIQUE_ROLE_SAFE_VALIDATION_CANDIDATE'}
if len(r37_candidates) != 15:
    die('R38_R37_CANDIDATE_DRIFT')
rems = ledger.get('remediations') or []
if ledger.get('materialized_remediation_count') != len(rems):
    die('R38_LEDGER_SELF_COUNT_DRIFT')
r38 = []
seen = set()
for rem in rems:
    ds = rem.get('defect_signature') or {}
    sig = (ds.get('category'), str(ds.get('uid')), ds.get('detail'))
    if sig in seen:
        die(f'R38_DUPLICATE_LEDGER_SIGNATURE:{sig}')
    seen.add(sig)
    if ds.get('category') == 'POST_ACTION_VALIDATION_NODE_MISSING':
        r38.append(rem)
if len(r38) != 15:
    die(f'R38_LEDGER_POST_ACTION_COUNT:{len(r38)}')
if ledger.get('materialized_remediation_count') != 27:
    die(f'R38_LEDGER_TOTAL_EXPECTED_27:{ledger.get("materialized_remediation_count")}')

for rem in r38:
    ds = rem.get('defect_signature') or {}
    action = str(ds.get('uid'))
    if ds.get('detail') != DETAIL or action not in r37_candidates:
        die(f'R38_LEDGER_SIGNATURE_DRIFT:{action}')
    src = r37_candidates[action]
    cand = src.get('candidate') or {}
    closure = rem.get('materialized_closure') or {}
    vc = closure.get('validation_contract') or {}
    if closure.get('closure_type') != 'POST_ACTION_VALIDATION_CONTRACT' or closure.get('action_uid') != action:
        die(f'R38_CLOSURE_IDENTITY_DRIFT:{action}')
    for key in ('validation_contract_type','signal_key','expected_signal','assertion','timing_boundary','failure_behavior','derivation'):
        if vc.get(key) != cand.get(key):
            die(f'R38_CANDIDATE_COPY_DRIFT:{action}:{key}')
    if rem.get('semantic_inference_used') is not False or rem.get('ai_invented_business_value') is not False or rem.get('precondition_promoted_to_postcondition') is not False or rem.get('external_authority_resolution_performed') is not False:
        die(f'R38_SAFETY_FLAG_DRIFT:{action}')

fresh = d.get('fresh_physical_reexecution') or {}
base = d.get('baseline_comparison') or {}
if fresh.get('new_r38_signatures_present_in_raw_count') != 15 or fresh.get('new_r38_signatures_eliminated_from_effective_count') != 15 or fresh.get('new_r38_signatures_remaining_effective_count') != 0:
    die(f'R38_FRESH_SIGNATURE_CLOSURE_DRIFT:{fresh}')
if fresh.get('raw_gap_total') != 150:
    die(f'R38_RAW_DENOMINATOR_DRIFT:{fresh.get("raw_gap_total")}')
if fresh.get('validated_product_successor_signature_count') != 32 or fresh.get('validated_gap006_signature_count') != 4:
    die(f'R38_SUCCESSOR_DENOMINATOR_DRIFT:{fresh}')
if fresh.get('effective_gap_total') != fresh.get('raw_gap_total') - fresh.get('validated_product_successor_signature_count') - fresh.get('validated_gap006_signature_count'):
    die('R38_EFFECTIVE_ARITHMETIC_DRIFT')
if base.get('prior_effective_gap_total_r35') != 129 or base.get('current_effective_gap_total') != fresh.get('effective_gap_total'):
    die(f'R38_BASELINE_DRIFT:{base}')
if base.get('proven_blocker_reduction_this_cycle') != 15:
    die(f'R38_REDUCTION_NOT_15:{base.get("proven_blocker_reduction_this_cycle")}')
if base.get('current_post_action_validation_gap_total') != 3 or base.get('prior_post_action_validation_gap_total') != 18:
    die(f'R38_POST_ACTION_DENOMINATOR_DRIFT:{base}')
if fresh.get('effective_gap_categories', {}).get('POST_ACTION_VALIDATION_NODE_MISSING') != 3:
    die('R38_POST_ACTION_EFFECTIVE_CATEGORY_DRIFT')
if len(d.get('materialized_actions') or []) != 15 or len({x.get('action_uid') for x in d.get('materialized_actions') or []}) != 15:
    die('R38_MATERIALIZED_ACTION_SET_DRIFT')
if d.get('stage02_status') != 'BLOCKED' or d.get('stage03_allowed') is not False or d.get('website_construction_allowed') is not False or d.get('deployment_allowed') is not False:
    die('R38_FAIL_CLOSED_DRIFT')
print(f"PASS: R38 validates 15 materialized post-action validation contracts; fresh effective={fresh['effective_gap_total']}; post-action remaining=3")
