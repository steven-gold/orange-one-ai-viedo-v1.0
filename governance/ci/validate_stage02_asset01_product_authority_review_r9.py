#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import hashlib
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R6 = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_INTAKE_R6.yaml'
RAW = ROOT / '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'
RAW_REF = ROOT / '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml'
OUT = ROOT / 'governance/test/stage02/STAGE02_ASSET01_PRODUCT_AUTHORITY_REVIEW_R9.yaml'
EXPECTED_CATEGORIES = {
    'ACTION_WITHOUT_CONTROL_OR_TRIGGER': 1,
    'AUDIT_EVENT_NODE_MISSING': 9,
    'FAILURE_STATE_ERROR_BINDING_MISSING': 44,
    'PAYLOAD_INPUT_CONTRACT_MISSING': 18,
    'POST_ACTION_VALIDATION_NODE_MISSING': 18,
    'STATE_TRANSITION_LEDGER_FIELD_MISSING': 20,
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(rec: dict):
    return (
        rec.get('blocker_uid'), rec.get('scope'), rec.get('category'), rec.get('target_uid'),
        rec.get('missing_field_or_relation'), rec.get('required_authority_kind'),
        tuple(rec.get('required_exact_fields_or_relation') or []),
    )


def contains_exact_mapping(node, wanted: dict) -> bool:
    if isinstance(node, dict):
        if node == wanted:
            return True
        return any(contains_exact_mapping(v, wanted) for v in node.values())
    if isinstance(node, list):
        return any(contains_exact_mapping(v, wanted) for v in node)
    return False


r6 = load(R6)
raw = load(RAW)
raw_ref = load(RAW_REF)
out = load(OUT)

if out.get('artifact_type') != 'NON_NORMATIVE_ASSET01_PRODUCT_AUTHORITY_REVIEW_CONTRACT_R9':
    die('R9_WRONG_ARTIFACT_TYPE')
if out.get('normative_authority') is not False or out.get('page_uid') != 'ASSET-01' or out.get('stage_uid') != 'STAGE-02':
    die('R9_IDENTITY_OR_NORMATIVE_STATUS_DRIFT')
if out.get('cycle') != 'ASSET01_PRODUCT_AUTHORITY_REVIEW_R9':
    die('R9_CYCLE_DRIFT')

expected = [r for r in (r6.get('records') or []) if r.get('scope') == 'ASSET-01']
actual = out.get('records') or []
if len(expected) != 110 or len(actual) != 110:
    die(f'R9_DENOMINATOR_DRIFT:expected={len(expected)}:actual={len(actual)}')
if [identity(r) for r in actual] != [identity(r) for r in expected]:
    die('R9_BLOCKER_IDENTITY_OR_ORDER_DRIFT_FROM_R6')
if len({r.get('blocker_uid') for r in actual}) != 110:
    die('R9_DUPLICATE_BLOCKER_UID')
if dict(Counter(r.get('category') for r in actual)) != EXPECTED_CATEGORIES:
    die('R9_CATEGORY_DENOMINATOR_DRIFT')

source = out.get('current_authority_source') or {}
authority = raw.get('authority') or {}
if source.get('authority_id') != authority.get('id'):
    die('R9_CURRENT_AUTHORITY_IDENTITY_DRIFT')
if source.get('authority_status') != 'FINAL_LOCKED' or source.get('current_only') is not True:
    die('R9_SOURCE_NOT_CURRENT_FINAL_LOCKED')
if source.get('physical_capture_sha256') != sha256(RAW):
    die('R9_PHYSICAL_CAPTURE_HASH_DRIFT')

capture = None
for rec in raw_ref.get('records') or []:
    if rec.get('page_uid') == 'ASSET-01' and rec.get('target_path') == '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml':
        capture = rec
        break
if not capture:
    die('R9_CAPTURE_PROVENANCE_MISSING')
if capture.get('content_mutated') is not False or capture.get('source_git_blob_sha') != capture.get('target_git_blob_sha'):
    die('R9_CAPTURE_NOT_BYTE_EXACT')
if source.get('canonical_source_path') != capture.get('source_path') or source.get('source_git_blob_sha') != capture.get('source_git_blob_sha'):
    die('R9_CAPTURE_PROVENANCE_DRIFT')

review_fields = {'canonical_owner_uid', 'authority_revision', 'exact_binding', 'approved_by', 'approved_at', 'approval_evidence_ref'}
for rec in actual:
    uid = rec.get('blocker_uid')
    if rec.get('approval_state') != 'PENDING_EXPLICIT_PRODUCT_AUTHORITY':
        die(f'R9_PREMATURE_APPROVAL:{uid}')
    if rec.get('authority_value_supplied_by_ai') is not False or rec.get('semantic_inference_used') is not False:
        die(f'R9_AI_OR_INFERENCE_USED:{uid}')
    if rec.get('historical_non_current_authority_used') is not False or rec.get('request_package_used_as_authority') is not False:
        die(f'R9_FORBIDDEN_AUTHORITY_SOURCE_USED:{uid}')
    if rec.get('materialization_allowed') is not False:
        die(f'R9_PREMATURE_MATERIALIZATION:{uid}')
    decision = rec.get('review_decision_required') or {}
    if set(decision) != review_fields:
        die(f'R9_DECISION_SCHEMA_DRIFT:{uid}')
    if any(v not in (None, '', [], {}) for v in decision.values()):
        die(f'R9_PRODUCT_AUTHORITY_VALUE_PRESENT:{uid}')

    ctx = rec.get('current_authority_context') or {}
    if ctx.get('target_uid') != rec.get('target_uid') or ctx.get('source_is_current_authority_exact_capture') is not True:
        die(f'R9_CONTEXT_IDENTITY_DRIFT:{uid}')
    for key in ('action_nodes', 'control_nodes', 'exposed_port_nodes', 'referenced_error_nodes', 'transition_nodes'):
        rows = ctx.get(key)
        if not isinstance(rows, list):
            die(f'R9_CONTEXT_LIST_REQUIRED:{uid}:{key}')
        for row in rows:
            if not isinstance(row, dict) or not contains_exact_mapping(raw, row):
                die(f'R9_CONTEXT_NOT_EXACT_RAW_MAPPING:{uid}:{key}')

    if rec.get('category') == 'STATE_TRANSITION_LEDGER_FIELD_MISSING':
        if len(ctx['transition_nodes']) != 1 or ctx['transition_nodes'][0].get('transition_uid') != rec.get('target_uid'):
            die(f'R9_TRANSITION_CONTEXT_INVALID:{uid}')
        if ctx['action_nodes'] or ctx['control_nodes'] or ctx['exposed_port_nodes'] or ctx['referenced_error_nodes']:
            die(f'R9_TRANSITION_CONTEXT_SCOPE_EXPANDED:{uid}')
    else:
        if not ctx['action_nodes']:
            die(f'R9_ACTION_CONTEXT_EMPTY:{uid}')
        if not any(row.get('action_uid') == rec.get('target_uid') for row in ctx['action_nodes']):
            die(f'R9_ACTION_CONTEXT_TARGET_MISMATCH:{uid}')
        if ctx['transition_nodes']:
            die(f'R9_ACTION_CONTEXT_CONTAINS_TRANSITION:{uid}')

safety = out.get('safety') or {}
required_false = (
    'review_package_is_product_authority', 'contains_approved_product_authority_values',
    'ai_may_fill_missing_product_values', 'semantic_similarity_may_create_binding',
    'historical_non_current_authority_may_fill_values', 'materialization_allowed_from_review_package',
    'stage02_blocker_reduction_claimed', 'current_specification_mutated',
    'stage01_source_mutated', 'stage02_product_output_mutated',
)
for key in required_false:
    if safety.get(key) is not False:
        die(f'R9_SAFETY_NOT_FALSE:{key}')

expected_denominators = {
    'asset01_open_product_authority_decisions': 110,
    'action_without_control_or_trigger_decisions': 1,
    'audit_event_decisions': 9,
    'failure_state_error_binding_decisions': 44,
    'payload_input_decisions': 18,
    'post_action_validation_decisions': 18,
    'state_transition_field_decisions': 20,
    'approved_bindings_in_review_package': 0,
    'materializable_bindings_in_review_package': 0,
    'effective_stage02_blocker_reduction_claimed': 0,
}
if out.get('denominators') != expected_denominators:
    die(f'R9_DENOMINATOR_CLAIM_DRIFT:{out.get("denominators")}')
if out.get('stage02_status') != 'BLOCKED' or out.get('stage03_allowed') is not False or out.get('website_construction_allowed') is not False or out.get('deployment_allowed') is not False:
    die('R9_DOWNSTREAM_EXECUTION_PREMATURELY_ALLOWED')

print('PASS: R9 exact ASSET-01 blocker set is 110 and matches R6 one-for-one')
print('PASS: action-trigger=1 audit=9 failure=44 payload=18 validation=18 state-transition-fields=20')
print('PASS: all context nodes are byte-derived exact mappings from the captured Current ASSET-01 authority')
print('PASS: R9 contains zero approved/missing product values, allows zero materialization, and claims zero blocker reduction')
