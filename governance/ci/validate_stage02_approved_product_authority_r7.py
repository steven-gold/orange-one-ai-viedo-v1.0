#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R6 = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_INTAKE_R6.yaml'
DEFAULT_APPROVED = ROOT / 'governance/test/stage02/STAGE02_APPROVED_PRODUCT_AUTHORITY_BINDINGS_R7.yaml'
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


def identity(rec: dict):
    return (
        rec.get('blocker_uid'), rec.get('scope'), rec.get('category'),
        rec.get('target_uid'), rec.get('missing_field_or_relation'),
        rec.get('required_authority_kind'),
        tuple(rec.get('required_exact_fields_or_relation') or []),
    )


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
    if len(r6_records) != 150:
        die(f'R6_DENOMINATOR_DRIFT:{len(r6_records)}')
    expected = {r.get('blocker_uid'): r for r in r6_records}
    if len(expected) != 150 or None in expected:
        die('R6_BLOCKER_UID_SET_INVALID')

    records = approved.get('records') or []
    if not isinstance(records, list) or not records:
        die('R7_APPROVED_RECORD_SET_EMPTY')
    if len(records) > 150:
        die(f'R7_APPROVED_RECORD_COUNT_EXCEEDS_150:{len(records)}')

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
        actual_hash = sha256_file(source_path)
        if inp['authority_content_sha256'] != actual_hash:
            die(f'R7_AUTHORITY_HASH_MISMATCH:{uid}')

        evidence_rel, evidence_path = repo_path(inp['approval_evidence_ref'], f'{uid}:approval_evidence_ref')
        if not evidence_path.is_file():
            die(f'R7_APPROVAL_EVIDENCE_NOT_FOUND:{uid}:{evidence_rel}')
        if evidence_rel == source_rel:
            die(f'R7_APPROVAL_EVIDENCE_MAY_NOT_BE_AUTHORITY_SOURCE:{uid}')

    return approved, records


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('approved_input', nargs='?', default=str(DEFAULT_APPROVED.relative_to(ROOT)))
    args = ap.parse_args()
    rel, path = repo_path(args.approved_input, 'approved_input')
    approved, records = validate(path)
    print(f'PASS: R7 approved authority binding set validated records={len(records)} input={rel}')
    print('PASS: every record matches an exact R6 blocker identity and carries non-AI explicit approval metadata')
    print('PASS: authority source content hashes and approval evidence paths are physically present')


if __name__ == '__main__':
    main()
