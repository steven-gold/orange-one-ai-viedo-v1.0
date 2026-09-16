#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R5 = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_REQUEST_R5.yaml'
R6 = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_INTAKE_R6.yaml'


def die(msg: str) -> None:
    print(f'BLOCK: {msg}', file=sys.stderr)
    raise SystemExit(1)


def load(path: Path):
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


r5 = load(R5)
r6 = load(R6)

if r6.get('artifact_type') != 'NON_NORMATIVE_PRODUCT_DESIGN_AUTHORITY_INTAKE_CONTRACT':
    die('R6_WRONG_ARTIFACT_TYPE')
if r6.get('normative_authority') is not False:
    die('R6_MASQUERADES_AS_NORMATIVE_AUTHORITY')
if r6.get('stage_uid') != 'STAGE-02' or r6.get('cycle') != 'PRODUCT_DESIGN_AUTHORITY_INTAKE_R6':
    die('R6_STAGE_OR_CYCLE_DRIFT')

safety = r6.get('safety') or {}
required_false = (
    'contains_product_authority_values',
    'may_be_used_as_product_authority',
    'may_reduce_stage02_blocker_count',
    'may_materialize_without_separate_approved_authority',
    'ai_may_fill_product_values',
    'historical_non_current_final_locked_source_may_fill_values',
    'current_specification_mutation_allowed',
    'stage01_source_mutation_allowed',
    'stage02_existing_output_mutation_performed',
)
for field in required_false:
    if safety.get(field) is not False:
        die(f'R6_SAFETY_FIELD_NOT_FALSE:{field}')

r5_reqs = r5.get('product_design_authority_requests') or []
r5_den = r5.get('denominators') or {}
product_denominator = r5_den.get('product_design_authority_requests')
external_denominator = r5_den.get('external_authority_requests')
current_total = r5_den.get('current_open_problems')
r6_recs = r6.get('records') or []

for name, value in (
    ('product', product_denominator),
    ('external', external_denominator),
    ('current_total', current_total),
):
    if not isinstance(value, int) or value < 0:
        die(f'R5_INVALID_{name.upper()}_DENOMINATOR:{value}')
if len(r5_reqs) != product_denominator:
    die(f'R5_PRODUCT_REQUEST_COUNT_DRIFT:records={len(r5_reqs)}:declared={product_denominator}')
if product_denominator + external_denominator != current_total:
    die(f'R5_AUTHORITY_PARTITION_DRIFT:product={product_denominator}:external={external_denominator}:total={current_total}')
if len(r6_recs) != product_denominator:
    die(f'R6_PRODUCT_DENOMINATOR_DRIFT:r5={product_denominator}:r6={len(r6_recs)}')


def identity_from_r5(x):
    a = x.get('authority_request') or {}
    problem_uid = x.get('problem_uid')
    return (
        problem_uid, problem_uid, x.get('scope'), x.get('category'), x.get('target_uid'),
        x.get('missing_field_or_relation'), a.get('required_authority_kind'),
        tuple(a.get('required_exact_fields_or_relation') or []),
    )


def identity_from_r6(x):
    return (
        x.get('blocker_uid'), x.get('source_problem_uid'), x.get('scope'), x.get('category'), x.get('target_uid'),
        x.get('missing_field_or_relation'), x.get('required_authority_kind'),
        tuple(x.get('required_exact_fields_or_relation') or []),
    )


expected = [identity_from_r5(x) for x in r5_reqs]
actual = [identity_from_r6(x) for x in r6_recs]
if actual != expected:
    die('R6_REQUEST_IDENTITY_OR_ORDER_DRIFT_FROM_R5')
if len(set(actual)) != product_denominator:
    die('R6_DUPLICATE_REQUEST_IDENTITY')

input_fields = (
    'canonical_owner_uid', 'canonical_owner_file', 'authority_revision',
    'authority_source_path', 'authority_content_sha256', 'exact_binding',
    'approved_by', 'approved_at', 'approval_evidence_ref',
)
for rec in r6_recs:
    uid = rec.get('blocker_uid')
    if rec.get('approval_state') != 'PENDING_EXPLICIT_PRODUCT_AUTHORITY':
        die(f'R6_UNAUTHORIZED_APPROVAL_STATE:{uid}')
    if rec.get('authority_value_supplied_by_ai') is not False:
        die(f'R6_AI_AUTHORITY_VALUE:{uid}')
    if rec.get('request_package_used_as_authority') is not False:
        die(f'R6_REQUEST_USED_AS_AUTHORITY:{uid}')
    if rec.get('historical_non_current_authority_used') is not False:
        die(f'R6_HISTORICAL_AUTHORITY_USED:{uid}')
    if rec.get('materialization_allowed') is not False:
        die(f'R6_PREMATURE_MATERIALIZATION:{uid}')
    inp = rec.get('authority_input') or {}
    if set(inp) != set(input_fields):
        die(f'R6_AUTHORITY_INPUT_SCHEMA_DRIFT:{uid}')
    nonempty = {k: v for k, v in inp.items() if v not in (None, '', [], {})}
    if nonempty:
        die(f'R6_UNAPPROVED_AUTHORITY_VALUE_PRESENT:{uid}:{sorted(nonempty)}')

expected_den = {
    'current_open_stage02_problems': current_total,
    'product_design_contract_blockers_locked_for_intake': product_denominator,
    'external_authority_blockers_preserved_outside_product_intake': external_denominator,
    'approved_product_authority_bindings_present_in_this_package': 0,
    'materializable_from_this_package': 0,
    'effective_stage02_blocker_reduction_claimed': 0,
}
if r6.get('denominators') != expected_den:
    die(f'R6_DENOMINATOR_CLAIM_DRIFT:{r6.get("denominators")}')
partition = r6.get('external_authority_partition') or {}
if partition != {
    'count': external_denominator,
    'source': 'R5_DENOMINATORS_EXTERNAL_AUTHORITY_REQUESTS',
    'included_in_product_authority_records': False,
    'resolution_claimed': False,
}:
    die(f'R6_EXTERNAL_AUTHORITY_PARTITION_DRIFT:{partition}')
if r6.get('stage02_status') != 'BLOCKED':
    die('R6_STAGE02_MUST_REMAIN_BLOCKED')
if r6.get('stage03_allowed') is not False or r6.get('website_construction_allowed') is not False or r6.get('deployment_allowed') is not False:
    die('R6_DOWNSTREAM_EXECUTION_PREMATURELY_ALLOWED')

contract = r6.get('approved_authority_ingestion_contract') or {}
for k, v in contract.items():
    if v is not True:
        die(f'R6_INGESTION_CONTRACT_NOT_FAIL_CLOSED:{k}')

print(f'PASS: R6 exact {product_denominator} Current product-authority identities match R5 one-for-one')
print(f'PASS: R6 preserves {external_denominator} external-authority blockers outside the product intake partition')
print('PASS: R6 contains 0 approved product-authority values and cannot masquerade as authority')
print('PASS: Stage-02 remains BLOCKED; Stage-03/construction/deployment remain prohibited')
