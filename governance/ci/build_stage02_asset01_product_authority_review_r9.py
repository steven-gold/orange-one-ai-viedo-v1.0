#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import hashlib
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R6 = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_INTAKE_R6.yaml'
RAW = ROOT / '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'
RAW_REF = ROOT / '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml'
OUT = ROOT / 'governance/test/stage02/STAGE02_ASSET01_PRODUCT_AUTHORITY_REVIEW_R9.yaml'
PHYSICAL_SOURCE_REL = '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'
PAGE_UID = 'ASSET-01'


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


def collect(node, predicate) -> list[dict]:
    out: list[dict] = []
    if isinstance(node, dict):
        if predicate(node):
            out.append(node)
        for value in node.values():
            out.extend(collect(value, predicate))
    elif isinstance(node, list):
        for value in node:
            out.extend(collect(value, predicate))
    return out


def unique_mappings(rows: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for row in rows:
        frozen = yaml.safe_dump(row, allow_unicode=True, sort_keys=True)
        if frozen in seen:
            continue
        seen.add(frozen)
        out.append(row)
    return out


r6 = load(R6)
raw = load(RAW)
raw_ref = load(RAW_REF)
all_r6_records = r6.get('records') or []
product_denominator = (r6.get('denominators') or {}).get('product_design_contract_blockers_locked_for_intake')
if not isinstance(product_denominator, int) or len(all_r6_records) != product_denominator:
    die(f'R9_R6_PRODUCT_DENOMINATOR_DRIFT:records={len(all_r6_records)}:declared={product_denominator}')
records = [r for r in all_r6_records if r.get('scope') == PAGE_UID]
if not records:
    die('ASSET01_R6_CURRENT_SCOPE_EMPTY')
counts = Counter(r.get('category') for r in records)
if None in counts:
    die('ASSET01_R6_CATEGORY_MISSING')

capture = None
for rec in raw_ref.get('records') or []:
    if rec.get('page_uid') == PAGE_UID and rec.get('target_path') == '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml':
        capture = rec
        break
if not capture:
    die('ASSET01_RAW_CAPTURE_PROVENANCE_MISSING')
if capture.get('content_mutated') is not False or capture.get('source_git_blob_sha') != capture.get('target_git_blob_sha'):
    die('ASSET01_RAW_CAPTURE_NOT_BYTE_EXACT')

authority = raw.get('authority') or {}
if authority.get('id') != 'ASSET_PAGE_VISUAL_AUTHORITY_FINAL' or authority.get('current_only') is not True or authority.get('status') != 'FINAL_LOCKED':
    die('ASSET01_CURRENT_AUTHORITY_IDENTITY_DRIFT')

review_records = []
for base in records:
    uid = base.get('blocker_uid')
    category = base.get('category')
    target = base.get('target_uid')
    if not uid or not category or not target:
        die(f'ASSET01_R9_INCOMPLETE_IDENTITY:{uid}')

    context: dict = {
        'target_uid': target,
        'source_is_current_authority_exact_capture': True,
        'action_nodes': [],
        'control_nodes': [],
        'exposed_port_nodes': [],
        'referenced_error_nodes': [],
        'transition_nodes': [],
    }
    if category == 'STATE_TRANSITION_LEDGER_FIELD_MISSING':
        transition_nodes = unique_mappings(collect(raw, lambda x: x.get('transition_uid') == target))
        if len(transition_nodes) != 1:
            die(f'ASSET01_R9_TRANSITION_NODE_DENOMINATOR:{target}:{len(transition_nodes)}')
        context['transition_nodes'] = transition_nodes
    else:
        action_nodes = unique_mappings(collect(raw, lambda x: x.get('action_uid') == target))
        if not action_nodes:
            die(f'ASSET01_R9_ACTION_CONTEXT_NOT_FOUND:{target}')
        context['action_nodes'] = action_nodes
        context['control_nodes'] = unique_mappings(collect(raw, lambda x: x.get('action_uid') == target and x.get('control_uid') not in (None, '')))
        context['exposed_port_nodes'] = unique_mappings(collect(raw, lambda x: x.get('exposure') == target and x.get('port_uid') not in (None, '')))
        error_uids = {x.get('error_uid') for x in action_nodes if x.get('error_uid') not in (None, '')}
        if error_uids:
            context['referenced_error_nodes'] = unique_mappings(collect(raw, lambda x: x.get('error_uid') in error_uids))

    review_records.append({
        'blocker_uid': uid,
        'source_problem_uid': base.get('source_problem_uid'),
        'scope': base.get('scope'),
        'category': category,
        'target_uid': target,
        'missing_field_or_relation': base.get('missing_field_or_relation'),
        'required_authority_kind': base.get('required_authority_kind'),
        'required_exact_fields_or_relation': base.get('required_exact_fields_or_relation') or [],
        'current_authority_context': context,
        'review_decision_required': {
            'canonical_owner_uid': None,
            'authority_revision': None,
            'exact_binding': None,
            'approved_by': None,
            'approved_at': None,
            'approval_evidence_ref': None,
        },
        'approval_state': 'PENDING_EXPLICIT_PRODUCT_AUTHORITY',
        'authority_value_supplied_by_ai': False,
        'semantic_inference_used': False,
        'historical_non_current_authority_used': False,
        'request_package_used_as_authority': False,
        'materialization_allowed': False,
    })

head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
out = {
    'schema_version': 2,
    'artifact_type': 'NON_NORMATIVE_ASSET01_PRODUCT_AUTHORITY_REVIEW_CONTRACT_R9',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'page_uid': PAGE_UID,
    'cycle': 'ASSET01_PRODUCT_AUTHORITY_REVIEW_R9',
    'source_r6_ref': 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_INTAKE_R6.yaml',
    'source_head_sha': head,
    'current_authority_source': {
        'authority_id': authority.get('id'),
        'authority_version': authority.get('version'),
        'authority_status': authority.get('status'),
        'current_only': authority.get('current_only'),
        'physical_capture_path': PHYSICAL_SOURCE_REL,
        'physical_capture_sha256': sha256(RAW),
        'canonical_source_path': capture.get('source_path'),
        'source_git_blob_sha': capture.get('source_git_blob_sha'),
        'target_git_blob_sha': capture.get('target_git_blob_sha'),
        'content_mutated': capture.get('content_mutated'),
    },
    'purpose': 'PRESENT_EXACT_CURRENT_ASSET01_CONTEXT_FOR_CURRENT_R6_PRODUCT_AUTHORITY_DECISIONS_WITHOUT_INVENTING_ANY_MISSING_PRODUCT_VALUE',
    'safety': {
        'review_package_is_product_authority': False,
        'contains_approved_product_authority_values': False,
        'ai_may_fill_missing_product_values': False,
        'semantic_similarity_may_create_binding': False,
        'historical_non_current_authority_may_fill_values': False,
        'materialization_allowed_from_review_package': False,
        'stage02_blocker_reduction_claimed': False,
        'current_specification_mutated': False,
        'stage01_source_mutated': False,
        'stage02_product_output_mutated': False,
    },
    'denominators': {
        'asset01_open_product_authority_decisions': len(records),
        'category_counts': dict(sorted(counts.items())),
        'approved_bindings_in_review_package': 0,
        'materializable_bindings_in_review_package': 0,
        'effective_stage02_blocker_reduction_claimed': 0,
    },
    'records': review_records,
    'approval_boundary': {
        'review_context_may_be_used_to_understand_existing_current_authority': True,
        'review_context_may_not_be_treated_as_missing_value_authority': True,
        'separate_current_admissible_authority_source_required_before_r7': True,
        'separate_structured_approval_evidence_required_before_r7': True,
        'r7_must_reject_binding_not_physically_present_in_authority_source': True,
        'fresh_stage02_reexecution_required_before_any_blocker_reduction': True,
    },
    'stage02_status': 'BLOCKED',
    'stage03_allowed': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
}
OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')
print(f'PASS: built ASSET-01 R9 review package for Current R6 product-authority blockers={len(records)}')
print(f'PASS: Current category counts={dict(sorted(counts.items()))}')
print('PASS: approved values=0 materializable=0 blocker reduction=0')
