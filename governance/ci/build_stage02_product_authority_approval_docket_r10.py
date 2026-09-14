#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R6 = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_INTAKE_R6.yaml'
R8 = ROOT / 'governance/test/stage02/STAGE02_CORE01_PRODUCT_AUTHORITY_REVIEW_R8.yaml'
R9 = ROOT / 'governance/test/stage02/STAGE02_ASSET01_PRODUCT_AUTHORITY_REVIEW_R9.yaml'
OUT = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_AUTHORITY_APPROVAL_DOCKET_R10.yaml'
EXPECTED_PAGE_COUNTS = {'CORE-01': 40, 'ASSET-01': 110}
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

if r8.get('artifact_type') != 'NON_NORMATIVE_CORE01_PRODUCT_AUTHORITY_REVIEW_CONTRACT_R8':
    die('R10_CORE_R8_IDENTITY_DRIFT')
if r9.get('artifact_type') != 'NON_NORMATIVE_ASSET01_PRODUCT_AUTHORITY_REVIEW_CONTRACT_R9':
    die('R10_ASSET_R9_IDENTITY_DRIFT')
for doc, name in ((r8, 'R8'), (r9, 'R9')):
    if doc.get('normative_authority') is not False:
        die(f'R10_{name}_MASQUERADES_AS_AUTHORITY')
    den = doc.get('denominators') or {}
    if den.get('approved_bindings_in_review_package') != 0 or den.get('materializable_bindings_in_review_package') != 0 or den.get('effective_stage02_blocker_reduction_claimed') != 0:
        die(f'R10_{name}_PREMATURE_APPROVAL_OR_REDUCTION')

r6_records = r6.get('records') or []
core = r8.get('records') or []
asset = r9.get('records') or []
combined = core + asset
if len(r6_records) != 150 or len(core) != 40 or len(asset) != 110 or len(combined) != 150:
    die(f'R10_DENOMINATOR_DRIFT:r6={len(r6_records)} core={len(core)} asset={len(asset)} total={len(combined)}')

r6_by_uid = {r.get('blocker_uid'): r for r in r6_records}
combined_by_uid = {r.get('blocker_uid'): r for r in combined}
if len(r6_by_uid) != 150 or len(combined_by_uid) != 150 or None in r6_by_uid or None in combined_by_uid:
    die('R10_DUPLICATE_OR_NULL_BLOCKER_UID')
if set(r6_by_uid) != set(combined_by_uid):
    die('R10_REVIEW_COVERAGE_UID_SET_DRIFT')
for uid, review in combined_by_uid.items():
    if identity(review) != identity(r6_by_uid[uid]):
        die(f'R10_REVIEW_IDENTITY_DRIFT:{uid}')
    if review.get('approval_state') != 'PENDING_EXPLICIT_PRODUCT_AUTHORITY':
        die(f'R10_REVIEW_NOT_PENDING:{uid}')
    if review.get('materialization_allowed') is not False:
        die(f'R10_REVIEW_PREMATURE_MATERIALIZATION:{uid}')
    decision = review.get('review_decision_required') or {}
    if any(v not in (None, '', [], {}) for v in decision.values()):
        die(f'R10_REVIEW_CONTAINS_AUTHORITY_DECISION:{uid}')

page_counts = Counter(r.get('scope') for r in combined)
category_counts = Counter(r.get('category') for r in combined)
if dict(page_counts) != EXPECTED_PAGE_COUNTS:
    die(f'R10_PAGE_COUNT_DRIFT:{dict(page_counts)}')
if dict(category_counts) != EXPECTED_CATEGORIES:
    die(f'R10_CATEGORY_COUNT_DRIFT:{dict(category_counts)}')

records = []
for base in r6_records:
    uid = base['blocker_uid']
    review = combined_by_uid[uid]
    ctx = review.get('current_authority_context') or {}
    source_review = 'governance/test/stage02/STAGE02_CORE01_PRODUCT_AUTHORITY_REVIEW_R8.yaml' if base.get('scope') == 'CORE-01' else 'governance/test/stage02/STAGE02_ASSET01_PRODUCT_AUTHORITY_REVIEW_R9.yaml'
    context_counts = {
        key: len(ctx.get(key) or [])
        for key in ('action_nodes', 'control_nodes', 'exposed_port_nodes', 'referenced_error_nodes', 'transition_nodes')
        if key in ctx
    }
    records.append({
        'blocker_uid': uid,
        'scope': base.get('scope'),
        'category': base.get('category'),
        'target_uid': base.get('target_uid'),
        'missing_field_or_relation': base.get('missing_field_or_relation'),
        'required_authority_kind': base.get('required_authority_kind'),
        'required_exact_fields_or_relation': base.get('required_exact_fields_or_relation') or [],
        'verified_review_ref': source_review,
        'verified_current_context_summary': {
            'source_is_current_authority_exact_capture': ctx.get('source_is_current_authority_exact_capture') is True,
            'node_counts': context_counts,
        },
        'authority_decision_required': {
            'canonical_owner_uid': None,
            'canonical_owner_file': None,
            'authority_revision': None,
            'authority_source_path': None,
            'authority_content_sha256': None,
            'exact_binding': None,
            'approved_by': None,
            'approved_at': None,
            'approval_evidence_ref': None,
        },
        'approval_state': 'PENDING_EXPLICIT_PRODUCT_AUTHORITY',
        'r7_materialization_allowed': False,
        'blocker_reduction_credit': 0,
    })

head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
out = {
    'schema_version': 1,
    'artifact_type': 'NON_NORMATIVE_STAGE02_PRODUCT_AUTHORITY_APPROVAL_DOCKET_R10',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'cycle': 'PRODUCT_AUTHORITY_APPROVAL_DOCKET_R10',
    'source_head_sha': head,
    'source_contracts': {
        'intake_r6': 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_INTAKE_R6.yaml',
        'core01_review_r8': 'governance/test/stage02/STAGE02_CORE01_PRODUCT_AUTHORITY_REVIEW_R8.yaml',
        'asset01_review_r9': 'governance/test/stage02/STAGE02_ASSET01_PRODUCT_AUTHORITY_REVIEW_R9.yaml',
        'ingestion_validator': 'governance/ci/validate_stage02_approved_product_authority_r7.py',
        'ingestion_materializer': 'governance/ci/materialize_stage02_approved_product_authority_r7.py',
    },
    'purpose': 'SINGLE_REVIEW_ENTRY_FOR_ALL_150_STAGE02_PRODUCT_AUTHORITY_DECISIONS_AFTER_EXACT_CURRENT_CONTEXT_PREPARATION',
    'status': 'READY_FOR_EXPLICIT_PRODUCT_AUTHORITY_DECISION_BLOCKED_UNTIL_VALUES_ARE_AUTHORIZED',
    'denominators': {
        'total_product_authority_decisions': 150,
        'core01_decisions': 40,
        'asset01_decisions': 110,
        'category_counts': dict(sorted(category_counts.items())),
        'approved_decisions': 0,
        'r7_materializable_decisions': 0,
        'effective_stage02_blocker_reduction_claimed': 0,
    },
    'safety': {
        'docket_is_product_authority': False,
        'docket_is_approval_evidence': False,
        'ai_may_complete_decision_values': False,
        'semantic_inference_may_complete_decision_values': False,
        'historical_non_current_authority_may_complete_decision_values': False,
        'review_context_may_be_promoted_to_authority_without_explicit_decision': False,
        'r7_may_materialize_from_docket_directly': False,
        'current_specification_mutated': False,
        'stage01_source_mutated': False,
        'stage02_product_output_mutated': False,
    },
    'records': records,
    'required_authorization_sequence': [
        'AUTHORITATIVE_PRODUCT_OWNER_DEFINES_EXACT_MISSING_BINDING',
        'BIND_VALUE_TO_CURRENT_ADMISSIBLE_AUTHORITY_SOURCE_WITH_REVISION_PROVENANCE_AND_SHA256',
        'RECORD_STRUCTURED_EXPLICIT_APPROVAL_IDENTITY_TIME_AND_EVIDENCE',
        'BUILD_SEPARATE_APPROVED_PRODUCT_DESIGN_AUTHORITY_BINDING_SET_FOR_R7',
        'R7_VALIDATE_CURRENT_ADMISSIBILITY_SOURCE_BYTES_BINDING_AND_APPROVAL',
        'R7_MATERIALIZE_AT_STAGE02_OWNING_PRODUCT_CONTRACT_LAYER',
        'CLEAN_RESET_EXECUTION_EVIDENCE_PRESERVING_VERIFIED_REMEDIATION',
        'FULL_LINE_SYSTEM_GATE',
        'FRESH_STAGE02_REEXECUTION',
        'ONLY_ZERO_REPRODUCED_SIGNATURES_RECEIVE_BLOCKER_REDUCTION_CREDIT',
    ],
    'stage02_status': 'BLOCKED',
    'stage03_allowed': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
}
OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')
print('PASS: R10 unified exact 150-decision Product Authority approval docket built')
print('PASS: CORE-01=40 ASSET-01=110; categories=1/13/44/34/18/40')
print('PASS: approved=0 R7-materializable=0 blocker-reduction=0')
