#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R6 = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_INTAKE_R6.yaml'
R8 = ROOT / 'governance/test/stage02/STAGE02_CORE01_PRODUCT_AUTHORITY_REVIEW_R8.yaml'
R9 = ROOT / 'governance/test/stage02/STAGE02_ASSET01_PRODUCT_AUTHORITY_REVIEW_R9.yaml'
OUT = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_AUTHORITY_APPROVAL_DOCKET_R10.yaml'
EXPECTED_CATEGORIES = {
    'ACTION_WITHOUT_CONTROL_OR_TRIGGER': 1,
    'AUDIT_EVENT_NODE_MISSING': 13,
    'FAILURE_STATE_ERROR_BINDING_MISSING': 44,
    'PAYLOAD_INPUT_CONTRACT_MISSING': 34,
    'POST_ACTION_VALIDATION_NODE_MISSING': 18,
    'STATE_TRANSITION_LEDGER_FIELD_MISSING': 40,
}


def die(msg: str) -> None:
    print(f'BLOCK: {msg}', file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> dict:
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(obj, dict):
        die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj


def identity(rec: dict):
    return (
        rec.get('blocker_uid'), rec.get('scope'), rec.get('category'), rec.get('target_uid'),
        rec.get('missing_field_or_relation'), rec.get('required_authority_kind'),
        tuple(rec.get('required_exact_fields_or_relation') or []),
    )


r6 = load(R6)
r8 = load(R8)
r9 = load(R9)
out = load(OUT)

if out.get('artifact_type') != 'NON_NORMATIVE_STAGE02_PRODUCT_AUTHORITY_APPROVAL_DOCKET_R10':
    die('R10_WRONG_ARTIFACT_TYPE')
if out.get('normative_authority') is not False or out.get('stage_uid') != 'STAGE-02':
    die('R10_NORMATIVE_OR_STAGE_DRIFT')
if out.get('cycle') != 'PRODUCT_AUTHORITY_APPROVAL_DOCKET_R10':
    die('R10_CYCLE_DRIFT')
if out.get('status') != 'READY_FOR_EXPLICIT_PRODUCT_AUTHORITY_DECISION_BLOCKED_UNTIL_VALUES_ARE_AUTHORIZED':
    die('R10_STATUS_DRIFT')

r6_records = r6.get('records') or []
core_records = r8.get('records') or []
asset_records = r9.get('records') or []
docket_records = out.get('records') or []
if [len(r6_records), len(core_records), len(asset_records), len(docket_records)] != [150, 40, 110, 150]:
    die(f'R10_DENOMINATOR_DRIFT:{[len(r6_records), len(core_records), len(asset_records), len(docket_records)]}')

r6_by_uid = {r.get('blocker_uid'): r for r in r6_records}
review_by_uid = {r.get('blocker_uid'): r for r in core_records + asset_records}
docket_by_uid = {r.get('blocker_uid'): r for r in docket_records}
if any(len(x) != 150 or None in x for x in (r6_by_uid, review_by_uid, docket_by_uid)):
    die('R10_UID_SET_DUPLICATE_OR_NULL')
if set(r6_by_uid) != set(review_by_uid) or set(r6_by_uid) != set(docket_by_uid):
    die('R10_UID_COVERAGE_DRIFT')

for uid, rec in docket_by_uid.items():
    if identity(rec) != identity(r6_by_uid[uid]):
        die(f'R10_IDENTITY_DRIFT:{uid}')
    review = review_by_uid[uid]
    expected_ref = 'governance/test/stage02/STAGE02_CORE01_PRODUCT_AUTHORITY_REVIEW_R8.yaml' if rec.get('scope') == 'CORE-01' else 'governance/test/stage02/STAGE02_ASSET01_PRODUCT_AUTHORITY_REVIEW_R9.yaml'
    if rec.get('verified_review_ref') != expected_ref:
        die(f'R10_REVIEW_REF_DRIFT:{uid}')
    summary = rec.get('verified_current_context_summary') or {}
    ctx = review.get('current_authority_context') or {}
    if summary.get('source_is_current_authority_exact_capture') is not True or ctx.get('source_is_current_authority_exact_capture') is not True:
        die(f'R10_CONTEXT_NOT_EXACT_CURRENT_CAPTURE:{uid}')
    expected_counts = {
        key: len(ctx.get(key) or [])
        for key in ('action_nodes', 'control_nodes', 'exposed_port_nodes', 'referenced_error_nodes', 'transition_nodes')
        if key in ctx
    }
    if summary.get('node_counts') != expected_counts:
        die(f'R10_CONTEXT_COUNT_DRIFT:{uid}')
    decision = rec.get('authority_decision_required') or {}
    expected_fields = {
        'canonical_owner_uid', 'canonical_owner_file', 'authority_revision', 'authority_source_path',
        'authority_content_sha256', 'exact_binding', 'approved_by', 'approved_at', 'approval_evidence_ref',
    }
    if set(decision) != expected_fields:
        die(f'R10_DECISION_SCHEMA_DRIFT:{uid}')
    if any(v not in (None, '', [], {}) for v in decision.values()):
        die(f'R10_PREMATURE_AUTHORITY_VALUE:{uid}')
    if rec.get('approval_state') != 'PENDING_EXPLICIT_PRODUCT_AUTHORITY':
        die(f'R10_PREMATURE_APPROVAL:{uid}')
    if rec.get('r7_materialization_allowed') is not False or rec.get('blocker_reduction_credit') != 0:
        die(f'R10_PREMATURE_MATERIALIZATION_OR_CREDIT:{uid}')

page_counts = Counter(r.get('scope') for r in docket_records)
category_counts = Counter(r.get('category') for r in docket_records)
if dict(page_counts) != {'CORE-01': 40, 'ASSET-01': 110}:
    die(f'R10_PAGE_COUNTS_DRIFT:{dict(page_counts)}')
if dict(category_counts) != EXPECTED_CATEGORIES:
    die(f'R10_CATEGORY_COUNTS_DRIFT:{dict(category_counts)}')

den = out.get('denominators') or {}
if den.get('total_product_authority_decisions') != 150 or den.get('core01_decisions') != 40 or den.get('asset01_decisions') != 110:
    die('R10_TOP_DENOMINATORS_DRIFT')
if den.get('category_counts') != dict(sorted(EXPECTED_CATEGORIES.items())):
    die('R10_CATEGORY_DENOMINATOR_CLAIM_DRIFT')
if den.get('approved_decisions') != 0 or den.get('r7_materializable_decisions') != 0 or den.get('effective_stage02_blocker_reduction_claimed') != 0:
    die('R10_FALSE_APPROVAL_OR_REDUCTION_CLAIM')

safety = out.get('safety') or {}
for key in (
    'docket_is_product_authority', 'docket_is_approval_evidence', 'ai_may_complete_decision_values',
    'semantic_inference_may_complete_decision_values', 'historical_non_current_authority_may_complete_decision_values',
    'review_context_may_be_promoted_to_authority_without_explicit_decision', 'r7_may_materialize_from_docket_directly',
    'current_specification_mutated', 'stage01_source_mutated', 'stage02_product_output_mutated',
):
    if safety.get(key) is not False:
        die(f'R10_SAFETY_FIELD_NOT_FALSE:{key}')

sequence = out.get('required_authorization_sequence') or []
if len(sequence) != 10 or sequence[-1] != 'ONLY_ZERO_REPRODUCED_SIGNATURES_RECEIVE_BLOCKER_REDUCTION_CREDIT':
    die('R10_AUTHORIZATION_SEQUENCE_DRIFT')
if out.get('stage02_status') != 'BLOCKED' or out.get('stage03_allowed') is not False or out.get('website_construction_allowed') is not False or out.get('deployment_allowed') is not False:
    die('R10_DOWNSTREAM_EXECUTION_PREMATURELY_ALLOWED')

print('PASS: R10 covers exact 150 R6 blocker identities with no overlap or omission')
print('PASS: CORE-01=40 ASSET-01=110; categories action=1 audit=13 failure=44 payload=34 validation=18 transition=40')
print('PASS: every docket row points to its verified exact-current review context and carries zero authority values')
print('PASS: approved=0 R7-materializable=0 blocker-reduction=0; Stage-02 remains BLOCKED')
