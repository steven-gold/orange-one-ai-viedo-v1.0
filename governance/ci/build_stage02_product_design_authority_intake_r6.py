#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R5 = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_REQUEST_R5.yaml'
OUT = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_INTAKE_R6.yaml'


def die(msg: str) -> None:
    print(f'BLOCK: {msg}', file=sys.stderr)
    raise SystemExit(1)


def load(path: Path):
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


r5 = load(R5)
requests = r5.get('product_design_authority_requests') or []
if len(requests) != 150:
    die(f'R5_PRODUCT_AUTHORITY_REQUEST_DENOMINATOR_NOT_150:{len(requests)}')
if r5.get('normative_authority') is not False or r5.get('request_is_product_authority') is not False:
    die('R5_REQUEST_MASQUERADES_AS_AUTHORITY')

seen = set()
records = []
for req in requests:
    blocker_uid = req.get('blocker_uid')
    scope = req.get('scope')
    category = req.get('category')
    target_uid = req.get('target_uid')
    missing = req.get('missing_field_or_relation')
    auth_req = req.get('authority_request') or {}
    key = (blocker_uid, scope, category, target_uid, missing)
    if any(v in (None, '') for v in key):
        die(f'INCOMPLETE_R5_REQUEST_IDENTITY:{key}')
    if key in seen:
        die(f'DUPLICATE_R5_REQUEST_IDENTITY:{key}')
    seen.add(key)
    required_kind = auth_req.get('required_authority_kind')
    required_relation = auth_req.get('required_exact_fields_or_relation') or []
    if not required_kind or not required_relation:
        die(f'INCOMPLETE_R5_AUTHORITY_REQUEST:{blocker_uid}')

    records.append({
        'blocker_uid': blocker_uid,
        'scope': scope,
        'category': category,
        'target_uid': target_uid,
        'missing_field_or_relation': missing,
        'required_authority_kind': required_kind,
        'required_exact_fields_or_relation': required_relation,
        'approval_state': 'PENDING_EXPLICIT_PRODUCT_AUTHORITY',
        'authority_input': {
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
        'authority_value_supplied_by_ai': False,
        'request_package_used_as_authority': False,
        'historical_non_current_authority_used': False,
        'materialization_allowed': False,
    })

head = subprocess.run(
    ['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), text=True,
    capture_output=True, check=True,
).stdout.strip()

out = {
    'schema_version': 1,
    'artifact_type': 'NON_NORMATIVE_PRODUCT_DESIGN_AUTHORITY_INTAKE_CONTRACT',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'cycle': 'PRODUCT_DESIGN_AUTHORITY_INTAKE_R6',
    'source_request_ref': 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_REQUEST_R5.yaml',
    'source_head_sha': head,
    'purpose': 'LOCK_THE_150_EXACT_PRODUCT_CONTRACT_GAP_IDENTITIES_AND_DEFINE_FAIL_CLOSED_INGESTION_FIELDS_FOR_A_SEPARATELY_APPROVED_CANONICAL_PRODUCT_AUTHORITY',
    'safety': {
        'contains_product_authority_values': False,
        'may_be_used_as_product_authority': False,
        'may_reduce_stage02_blocker_count': False,
        'may_materialize_without_separate_approved_authority': False,
        'ai_may_fill_product_values': False,
        'historical_non_current_final_locked_source_may_fill_values': False,
        'current_specification_mutation_allowed': False,
        'stage01_source_mutation_allowed': False,
        'stage02_existing_output_mutation_performed': False,
    },
    'approved_authority_ingestion_contract': {
        'approved_input_must_be_separate_from_this_package': True,
        'approved_input_must_resolve_exact_blocker_uid': True,
        'approved_input_must_match_scope_category_target_uid_and_missing_relation': True,
        'approved_input_must_supply_required_authority_kind': True,
        'approved_input_must_name_canonical_owner_uid_and_owner_file': True,
        'approved_input_must_supply_authority_revision_and_content_sha256': True,
        'approved_input_must_supply_exact_binding_without_semantic_inference': True,
        'approved_input_must_supply_approval_identity_time_and_evidence': True,
        'approved_owner_must_be_current_admissible_product_authority_at_ingestion_time': True,
        'generated_test_evidence_or_runtime_snapshot_cannot_be_product_authority': True,
        'all_category_specific_validation_must_pass_before_materialization': True,
        'partial_approved_sets_may_not_be_counted_closed_until_fresh_reexecution_proves_each_signature_zero': True,
    },
    'denominators': {
        'product_design_contract_blockers_locked_for_intake': 150,
        'approved_product_authority_bindings_present_in_this_package': 0,
        'materializable_from_this_package': 0,
        'effective_stage02_blocker_reduction_claimed': 0,
    },
    'records': records,
    'next_legal_sequence': [
        'INGEST_SEPARATE_APPROVED_CANONICAL_PRODUCT_AUTHORITY',
        'VALIDATE_EXACT_UID_FIELD_RELATIONS_AND_CURRENT_AUTHORITY_ADMISSIBILITY',
        'MATERIALIZE_ONLY_VALIDATED_BINDINGS_AT_STAGE02_OWNING_CONTRACT_LAYER',
        'CLEAN_RESET_EXECUTION_OUTPUTS_TO_SAME_STAGE01_BASELINE',
        'RUN_FULL_LINE_SYSTEM_HIGH_PRESSURE_GATE',
        'RUN_FRESH_STAGE02_REEXECUTION',
        'REQUIRE_KNOWN_DEFECT_SIGNATURE_REPRODUCTION_ZERO',
        'ONLY_THEN_RECALCULATE_EFFECTIVE_BLOCKER_DENOMINATOR',
    ],
    'stage02_status': 'BLOCKED',
    'stage03_allowed': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
}

OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')
print('PASS: built fail-closed R6 intake contract for exact 150 product-design/functional-contract blockers')
print('PASS: product authority values supplied=0; materializable=0; blocker reduction claimed=0')
