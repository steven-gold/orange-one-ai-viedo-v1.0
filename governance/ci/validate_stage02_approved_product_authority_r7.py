#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
R6 = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_INTAKE_R6.yaml'
DEFAULT_APPROVED = ROOT / 'governance/test/stage02/STAGE02_APPROVED_PRODUCT_AUTHORITY_BINDINGS_R7.yaml'
CURRENT_MANIFEST = RUN / '04_PAGE_FUNCTIONAL_CONTRACT/EXTERNAL_AUTHORITY/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml'
RAW_CAPTURE_REF = RUN / '00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml'
EXTERNAL_MATERIALIZATION_EVIDENCE = RUN / '04_PAGE_FUNCTIONAL_CONTRACT/EXTERNAL_AUTHORITY/STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE.yaml'
RUN_PREFIX = '00_SOURCE_INTAKE/fresh_run_003/'
FORBIDDEN_PREFIXES = (
    'governance/test/',
    '.github/stage02-test/',
)


def die(msg: str) -> None:
    print(f'BLOCK: {msg}', file=sys.stderr)
    raise SystemExit(1)


def load(path: Path):
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    try:
        obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception as exc:
        die(f'YAML_PARSE:{path.relative_to(ROOT)}:{exc!r}')
    if not isinstance(obj, dict):
        die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj


def repo_path(value, field: str) -> tuple[str, Path]:
    if not isinstance(value, str) or not value.strip():
        die(f'EMPTY_PATH:{field}')
    rel = value.strip().replace('\\', '/')
    p = Path(rel)
    if p.is_absolute() or '..' in p.parts:
        die(f'UNSAFE_PATH:{field}:{rel}')
    return rel, ROOT / p


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    header = f'blob {len(data)}\0'.encode('utf-8')
    return hashlib.sha1(header + data).hexdigest()


def identity(rec: dict):
    return (
        rec.get('blocker_uid'), rec.get('scope'), rec.get('category'),
        rec.get('target_uid'), rec.get('missing_field_or_relation'),
        rec.get('required_authority_kind'),
        tuple(rec.get('required_exact_fields_or_relation') or []),
    )


def flatten_strings(value) -> set[str]:
    out: set[str] = set()
    if isinstance(value, str):
        out.add(value)
    elif isinstance(value, list):
        for item in value:
            out |= flatten_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            out |= flatten_strings(item)
    return out


def load_current_manifest() -> dict:
    manifest = load(CURRENT_MANIFEST)
    authority = manifest.get('authority') or {}
    if authority.get('current_only') is not True or authority.get('status') != 'FINAL_LOCKED':
        die('R7_CURRENT_AUTHORITY_MANIFEST_NOT_CURRENT_FINAL_LOCKED')
    load_policy = manifest.get('load_policy') or {}
    if load_policy.get('only_listed_files_are_current_authority') is not True:
        die('R7_CURRENT_AUTHORITY_MANIFEST_LOAD_POLICY_DRIFT')
    return manifest


def current_authority_set() -> set[str]:
    manifest = load_current_manifest()
    current = flatten_strings(manifest.get('current_authority_set') or {})
    if not current:
        die('R7_CURRENT_AUTHORITY_SET_EMPTY')
    return current


def current_manifest_revision() -> str:
    manifest = load_current_manifest()
    revision = (manifest.get('authority') or {}).get('revision')
    if revision in (None, ''):
        die('R7_CURRENT_AUTHORITY_MANIFEST_REVISION_MISSING')
    return str(revision)


def raw_capture_map(current: set[str]) -> dict[str, dict]:
    doc = load(RAW_CAPTURE_REF)
    if doc.get('capture_mode') != 'EXACT_EXISTING_GIT_BLOB_REUSE_NO_CONTENT_MUTATION':
        die('R7_RAW_CAPTURE_MODE_NOT_EXACT')
    out: dict[str, dict] = {}
    for rec in doc.get('records') or []:
        source = rec.get('source_path')
        target = rec.get('target_path')
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        full_target = RUN_PREFIX + target
        if full_target in out:
            die(f'R7_DUPLICATE_RAW_CAPTURE_TARGET:{full_target}')
        if source in current:
            out[full_target] = rec
    return out


def external_materialization_map(current: set[str]) -> dict[str, dict]:
    if not EXTERNAL_MATERIALIZATION_EVIDENCE.is_file():
        return {}
    doc = load(EXTERNAL_MATERIALIZATION_EVIDENCE)
    out: dict[str, dict] = {}
    for group in (doc.get('materialized_authorities') or {}).values():
        if not isinstance(group, dict):
            continue
        candidates = group.get('authority_chain') if isinstance(group.get('authority_chain'), list) else [group]
        manifest_current = group.get('manifest_current') is True
        identity_status = group.get('authority_identity_status')
        for item in candidates:
            if not isinstance(item, dict):
                continue
            source = item.get('source_path')
            materialized = item.get('materialized_path')
            if not isinstance(source, str) or not isinstance(materialized, str):
                continue
            if source not in current or not manifest_current:
                continue
            if identity_status not in ('EXACT_MATCH', 'EXACT_CHAIN_LOCATED'):
                continue
            full = RUN_PREFIX + materialized
            out[full] = {
                'source_path': source,
                'git_blob_sha': item.get('git_blob_sha'),
                'authority_identity_status': identity_status,
            }
    return out


def prove_current_admissibility(source_rel: str, source_path: Path) -> dict:
    current = current_authority_set()
    if source_rel in current:
        return {'provenance_kind': 'DIRECT_CURRENT_AUTHORITY_SET_MEMBER', 'canonical_source_path': source_rel}

    captures = raw_capture_map(current)
    if source_rel in captures:
        rec = captures[source_rel]
        if rec.get('content_mutated') is not False:
            die(f'R7_CURRENT_CAPTURE_MUTATED:{source_rel}')
        if rec.get('source_git_blob_sha') != rec.get('target_git_blob_sha'):
            die(f'R7_CURRENT_CAPTURE_SOURCE_TARGET_BLOB_DRIFT:{source_rel}')
        actual_blob = git_blob_sha1(source_path)
        if actual_blob != rec.get('target_git_blob_sha'):
            die(f'R7_CURRENT_CAPTURE_PHYSICAL_BLOB_DRIFT:{source_rel}')
        return {
            'provenance_kind': 'EXACT_STAGE1_CAPTURE_OF_CURRENT_AUTHORITY',
            'canonical_source_path': rec.get('source_path'),
            'git_blob_sha': actual_blob,
        }

    external = external_materialization_map(current)
    if source_rel in external:
        rec = external[source_rel]
        actual_blob = git_blob_sha1(source_path)
        if actual_blob != rec.get('git_blob_sha'):
            die(f'R7_EXTERNAL_CURRENT_AUTHORITY_PHYSICAL_BLOB_DRIFT:{source_rel}')
        return {
            'provenance_kind': 'EXACT_STAGE2_MATERIALIZATION_OF_CURRENT_AUTHORITY',
            'canonical_source_path': rec.get('source_path'),
            'git_blob_sha': actual_blob,
        }

    die(f'R7_AUTHORITY_SOURCE_NOT_CURRENT_ADMISSIBLE:{source_rel}')


def owner_ids(doc: dict) -> set[str]:
    out: set[str] = set()
    authority = doc.get('authority')
    for obj in (doc, authority if isinstance(authority, dict) else {}):
        for key in ('artifact_uid', 'owner_uid', 'authority_uid', 'contract_id', 'id'):
            value = obj.get(key)
            if isinstance(value, str) and value:
                out.add(value)
    return out


def revision_tokens(doc: dict) -> set[str]:
    out: set[str] = set()
    authority = doc.get('authority')
    for obj in (doc, authority if isinstance(authority, dict) else {}):
        for key in ('revision', 'version', 'governance_revision'):
            value = obj.get(key)
            if value not in (None, ''):
                out.add(str(value))
    return out


def prove_revision_provenance(source_doc: dict, provenance: dict, requested_revision, uid: str) -> str:
    requested = str(requested_revision)
    if requested in revision_tokens(source_doc):
        return 'INTRINSIC_SOURCE_REVISION_OR_VERSION'
    canonical_source = provenance.get('canonical_source_path')
    if not isinstance(canonical_source, str) or canonical_source not in current_authority_set():
        die(f'R7_REVISION_PROVENANCE_NOT_CURRENT:{uid}:{canonical_source}')
    manifest_revision = current_manifest_revision()
    if requested == manifest_revision:
        return 'CURRENT_AUTHORITY_MANIFEST_REVISION_WITH_EXACT_SOURCE_HASH'
    die(f'R7_AUTHORITY_REVISION_NOT_PROVEN:{uid}:{requested}')


def matches_subset(node, needle) -> bool:
    if isinstance(needle, dict):
        if not isinstance(node, dict):
            return False
        return all(k in node and matches_subset(node[k], v) for k, v in needle.items())
    if isinstance(needle, list):
        return node == needle
    return node == needle


def contains_binding(node, binding: dict) -> bool:
    if matches_subset(node, binding):
        return True
    if isinstance(node, dict):
        return any(contains_binding(v, binding) for v in node.values())
    if isinstance(node, list):
        return any(contains_binding(v, binding) for v in node)
    return False


def validate_binding_shape(rec: dict, binding) -> None:
    uid = rec.get('blocker_uid')
    if not isinstance(binding, dict) or not binding:
        die(f'R7_EXACT_BINDING_MAPPING_REQUIRED:{uid}')
    target = rec.get('target_uid')
    category = rec.get('category')

    if category == 'STATE_TRANSITION_LEDGER_FIELD_MISSING':
        if binding.get('transition_uid') != target:
            die(f'R7_TRANSITION_BINDING_TARGET_MISMATCH:{uid}')
        missing = rec.get('missing_field_or_relation')
        if missing not in binding or binding.get(missing) in (None, '', [], {}):
            die(f'R7_TRANSITION_BINDING_FIELD_MISSING:{uid}:{missing}')
        return

    if binding.get('action_uid') != target:
        die(f'R7_ACTION_BINDING_TARGET_MISMATCH:{uid}')

    if category == 'PAYLOAD_INPUT_CONTRACT_MISSING':
        keys = ('payload_schema', 'input_schema', 'request_schema', 'payload', 'input_contract', 'request_contract')
        if not any(binding.get(k) not in (None, '', [], {}) for k in keys):
            die(f'R7_PAYLOAD_BINDING_SCHEMA_MISSING:{uid}')
    elif category == 'AUDIT_EVENT_NODE_MISSING':
        if binding.get('audit_event_uid') in (None, ''):
            die(f'R7_AUDIT_EVENT_UID_MISSING:{uid}')
    elif category == 'FAILURE_STATE_ERROR_BINDING_MISSING':
        direct = binding.get('failure_state') not in (None, '') and binding.get('recovery') not in (None, '', [], {})
        registered = binding.get('error_uid') not in (None, '') and binding.get('recovery') not in (None, '', [], {})
        if not (direct or registered):
            die(f'R7_FAILURE_RECOVERY_BINDING_INCOMPLETE:{uid}')
    elif category == 'POST_ACTION_VALIDATION_NODE_MISSING':
        keys = ('success_contract', 'validation_contract', 'validator_uid', 'validation', 'validation_rule', 'evaluation_rule')
        if not any(binding.get(k) not in (None, '', [], {}) for k in keys):
            die(f'R7_POST_ACTION_VALIDATION_BINDING_MISSING:{uid}')
    elif category == 'ACTION_WITHOUT_CONTROL_OR_TRIGGER':
        if binding.get('control_uid') in (None, '') and binding.get('trigger_uid') in (None, ''):
            die(f'R7_CONTROL_OR_TRIGGER_BINDING_MISSING:{uid}')
    elif category == 'SUCCESS_NEXT_STATE_BINDING_MISSING':
        keys = ('next_state', 'success_next_state', 'success_state', 'to_state', 'next_state_uid')
        if not any(binding.get(k) not in (None, '', [], {}) for k in keys):
            die(f'R7_SUCCESS_NEXT_STATE_BINDING_MISSING:{uid}')
    else:
        die(f'R7_UNSUPPORTED_PRODUCT_AUTHORITY_CATEGORY:{uid}:{category}')


def validate_approval_evidence(evidence_path: Path, uid: str, inp: dict, source_rel: str, source_hash: str) -> None:
    evidence = load(evidence_path)
    if evidence.get('artifact_type') != 'PRODUCT_DESIGN_AUTHORITY_APPROVAL_EVIDENCE':
        die(f'R7_APPROVAL_EVIDENCE_WRONG_TYPE:{uid}')
    if evidence.get('normative_authority') is not False:
        die(f'R7_APPROVAL_EVIDENCE_MASQUERADES_AS_AUTHORITY:{uid}')
    if evidence.get('approval_scope') != 'STAGE02_PRODUCT_DESIGN_AUTHORITY':
        die(f'R7_APPROVAL_EVIDENCE_SCOPE_DRIFT:{uid}')
    if evidence.get('approval_state') != 'APPROVED_EXPLICIT_PRODUCT_AUTHORITY':
        die(f'R7_APPROVAL_EVIDENCE_NOT_APPROVED:{uid}')
    if evidence.get('authority_source_path') != source_rel:
        die(f'R7_APPROVAL_EVIDENCE_SOURCE_PATH_MISMATCH:{uid}')
    if evidence.get('authority_content_sha256') != source_hash:
        die(f'R7_APPROVAL_EVIDENCE_SOURCE_HASH_MISMATCH:{uid}')
    if evidence.get('approved_by') != inp.get('approved_by'):
        die(f'R7_APPROVAL_EVIDENCE_APPROVER_MISMATCH:{uid}')
    if evidence.get('approved_at') != inp.get('approved_at'):
        die(f'R7_APPROVAL_EVIDENCE_TIME_MISMATCH:{uid}')
    approved_bindings = evidence.get('approved_bindings') or {}
    bound = approved_bindings.get(uid)
    if not isinstance(bound, dict):
        die(f'R7_APPROVAL_EVIDENCE_BLOCKER_NOT_BOUND:{uid}')
    if bound.get('canonical_owner_uid') != inp.get('canonical_owner_uid'):
        die(f'R7_APPROVAL_EVIDENCE_OWNER_MISMATCH:{uid}')
    if str(bound.get('authority_revision')) != str(inp.get('authority_revision')):
        die(f'R7_APPROVAL_EVIDENCE_REVISION_MISMATCH:{uid}')
    if bound.get('exact_binding') != inp.get('exact_binding'):
        die(f'R7_APPROVAL_EVIDENCE_EXACT_BINDING_MISMATCH:{uid}')


def validate(approved_path: Path) -> tuple[dict, list[dict]]:
    r6 = load(R6)
    approved = load(approved_path)

    if approved.get('artifact_type') != 'APPROVED_PRODUCT_DESIGN_AUTHORITY_BINDING_SET':
        die('R7_WRONG_ARTIFACT_TYPE')
    if approved.get('normative_authority') is not False:
        die('R7_BINDING_SET_MASQUERADES_AS_NORMATIVE_AUTHORITY')
    if approved.get('stage_uid') != 'STAGE-02' or approved.get('cycle') != 'PRODUCT_DESIGN_AUTHORITY_INGESTION_R7':
        die('R7_STAGE_OR_CYCLE_DRIFT')

    r6_records = r6.get('records') or []
    r6_den = r6.get('denominators') or {}
    product_denominator = r6_den.get('product_design_contract_blockers_locked_for_intake')
    if not isinstance(product_denominator, int) or product_denominator < 0:
        die(f'R6_INVALID_PRODUCT_DENOMINATOR:{product_denominator}')
    if len(r6_records) != product_denominator:
        die(f'R6_DENOMINATOR_DRIFT:records={len(r6_records)}:declared={product_denominator}')
    expected = {r.get('blocker_uid'): r for r in r6_records}
    if len(expected) != product_denominator or None in expected:
        die('R6_BLOCKER_UID_SET_INVALID')

    records = approved.get('records') or []
    if not isinstance(records, list) or not records:
        die('R7_APPROVED_RECORD_SET_EMPTY')
    if len(records) > product_denominator:
        die(f'R7_APPROVED_RECORD_COUNT_EXCEEDS_CURRENT_PRODUCT_DENOMINATOR:{len(records)}>{product_denominator}')

    seen = set()
    required_input_fields = {
        'canonical_owner_uid', 'canonical_owner_file', 'authority_revision',
        'authority_source_path', 'authority_content_sha256', 'exact_binding',
        'approved_by', 'approved_at', 'approval_evidence_ref',
    }

    for rec in records:
        uid = rec.get('blocker_uid')
        if uid in seen:
            die(f'R7_DUPLICATE_BLOCKER_UID:{uid}')
        seen.add(uid)
        base = expected.get(uid)
        if base is None:
            die(f'R7_UNKNOWN_BLOCKER_UID:{uid}')
        if identity(rec) != identity(base):
            die(f'R7_BLOCKER_IDENTITY_DRIFT:{uid}')
        if rec.get('approval_state') != 'APPROVED_EXPLICIT_PRODUCT_AUTHORITY':
            die(f'R7_NOT_EXPLICITLY_APPROVED:{uid}')
        if rec.get('authority_value_supplied_by_ai') is not False:
            die(f'R7_AI_SUPPLIED_AUTHORITY_FORBIDDEN:{uid}')
        if rec.get('historical_non_current_authority_used') is not False:
            die(f'R7_HISTORICAL_NON_CURRENT_AUTHORITY_FORBIDDEN:{uid}')
        if rec.get('request_package_used_as_authority') is not False:
            die(f'R7_REQUEST_PACKAGE_USED_AS_AUTHORITY:{uid}')
        if rec.get('materialization_allowed') is not True:
            die(f'R7_MATERIALIZATION_NOT_EXPLICITLY_ALLOWED:{uid}')

        inp = rec.get('authority_input') or {}
        if set(inp) != required_input_fields:
            die(f'R7_AUTHORITY_INPUT_SCHEMA_DRIFT:{uid}')
        for key in required_input_fields:
            if inp.get(key) in (None, '', [], {}):
                die(f'R7_AUTHORITY_INPUT_MISSING:{uid}:{key}')

        owner_rel, owner_path = repo_path(inp['canonical_owner_file'], f'{uid}:canonical_owner_file')
        source_rel, source_path = repo_path(inp['authority_source_path'], f'{uid}:authority_source_path')
        if owner_rel != source_rel:
            die(f'R7_OWNER_SOURCE_PATH_MISMATCH:{uid}')
        if any(source_rel.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            die(f'R7_TEST_OR_EVIDENCE_ARTIFACT_CANNOT_BE_AUTHORITY:{uid}:{source_rel}')
        if not source_path.is_file():
            die(f'R7_AUTHORITY_SOURCE_NOT_FOUND:{uid}:{source_rel}')

        source_hash = sha256_file(source_path)
        if inp['authority_content_sha256'] != source_hash:
            die(f'R7_AUTHORITY_HASH_MISMATCH:{uid}')
        provenance = prove_current_admissibility(source_rel, source_path)

        source_doc = load(source_path)
        if inp['canonical_owner_uid'] not in owner_ids(source_doc):
            die(f'R7_CANONICAL_OWNER_UID_NOT_IN_SOURCE:{uid}:{inp["canonical_owner_uid"]}')
        prove_revision_provenance(source_doc, provenance, inp['authority_revision'], uid)

        binding = inp['exact_binding']
        validate_binding_shape(rec, binding)
        if not contains_binding(source_doc, binding):
            die(f'R7_EXACT_BINDING_NOT_PHYSICALLY_PRESENT_IN_AUTHORITY:{uid}')

        evidence_rel, evidence_path = repo_path(inp['approval_evidence_ref'], f'{uid}:approval_evidence_ref')
        if not evidence_path.is_file():
            die(f'R7_APPROVAL_EVIDENCE_NOT_FOUND:{uid}:{evidence_rel}')
        if evidence_rel == source_rel:
            die(f'R7_APPROVAL_EVIDENCE_MAY_NOT_BE_AUTHORITY_SOURCE:{uid}')
        validate_approval_evidence(evidence_path, uid, inp, source_rel, source_hash)

    return approved, records


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('approved_input', nargs='?', default=str(DEFAULT_APPROVED.relative_to(ROOT)))
    args = ap.parse_args()
    rel, path = repo_path(args.approved_input, 'approved_input')
    approved, records = validate(path)
    print(f'PASS: R7 approved authority binding set validated records={len(records)} input={rel}')
    print('PASS: every record matches an exact Current R6 product-blocker identity and carries non-AI explicit approval metadata')
    print('PASS: every authority source is Current-admissible by direct membership or verified exact capture/materialization provenance')
    print('PASS: authority revision is proven by source-intrinsic token or the revisioned Current manifest that lists the exact hashed canonical source')
    print('PASS: canonical owner and category-specific exact binding are physically represented by authority source bytes')
    print('PASS: structured approval evidence binds the exact blocker, source hash, revision and exact approved binding')


if __name__ == '__main__':
    main()
