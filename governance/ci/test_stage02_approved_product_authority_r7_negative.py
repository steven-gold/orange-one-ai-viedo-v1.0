#!/usr/bin/env python3
from __future__ import annotations

from contextlib import redirect_stderr
from pathlib import Path
from io import StringIO
import hashlib
import yaml

ROOT = Path(__file__).resolve().parents[2]
R6 = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_INTAKE_R6.yaml'
CORE_SOURCE_REL = '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml'
CORE_SOURCE = ROOT / CORE_SOURCE_REL
ASSET_SOURCE_REL = '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'
ASSET_SOURCE = ROOT / ASSET_SOURCE_REL
CURRENT_MANIFEST = ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/EXTERNAL_AUTHORITY/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml'
TMP_SOURCE = ROOT / 'R7_NEGATIVE_NON_CURRENT_AUTHORITY.yaml'
TMP_EVIDENCE = ROOT / 'governance/test/stage02/.R7_NEGATIVE_APPROVAL_EVIDENCE.yaml'
TMP_INPUT = ROOT / 'governance/test/stage02/.R7_NEGATIVE_APPROVED_BINDINGS.yaml'

import sys
sys.path.insert(0, str((ROOT / 'governance/ci').resolve()))
from validate_stage02_approved_product_authority_r7 import (  # noqa: E402
    load as validator_load,
    prove_current_admissibility,
    prove_revision_provenance,
    validate,
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def dump(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')


def core_payload_base() -> dict:
    r6 = load(R6)
    for rec in r6.get('records') or []:
        if rec.get('scope') == 'CORE-01' and rec.get('category') == 'PAYLOAD_INPUT_CONTRACT_MISSING':
            return rec
    raise AssertionError('CORE_PAYLOAD_R6_RECORD_NOT_FOUND')


def approved_record(base: dict, source_rel: str, source_hash: str, owner_uid: str, revision: str, binding: dict) -> dict:
    return {
        'blocker_uid': base['blocker_uid'],
        'scope': base['scope'],
        'category': base['category'],
        'target_uid': base['target_uid'],
        'missing_field_or_relation': base['missing_field_or_relation'],
        'required_authority_kind': base['required_authority_kind'],
        'required_exact_fields_or_relation': base['required_exact_fields_or_relation'],
        'approval_state': 'APPROVED_EXPLICIT_PRODUCT_AUTHORITY',
        'authority_value_supplied_by_ai': False,
        'historical_non_current_authority_used': False,
        'request_package_used_as_authority': False,
        'materialization_allowed': True,
        'authority_input': {
            'canonical_owner_uid': owner_uid,
            'canonical_owner_file': source_rel,
            'authority_revision': revision,
            'authority_source_path': source_rel,
            'authority_content_sha256': source_hash,
            'exact_binding': binding,
            'approved_by': 'NEGATIVE_REGRESSION_FIXTURE_HUMAN',
            'approved_at': '2026-09-15T00:00:00Z',
            'approval_evidence_ref': str(TMP_EVIDENCE.relative_to(ROOT)),
        },
    }


def write_evidence(rec: dict) -> None:
    inp = rec['authority_input']
    dump(TMP_EVIDENCE, {
        'schema_version': 1,
        'artifact_type': 'PRODUCT_DESIGN_AUTHORITY_APPROVAL_EVIDENCE',
        'normative_authority': False,
        'approval_scope': 'STAGE02_PRODUCT_DESIGN_AUTHORITY',
        'approval_state': 'APPROVED_EXPLICIT_PRODUCT_AUTHORITY',
        'authority_source_path': inp['authority_source_path'],
        'authority_content_sha256': inp['authority_content_sha256'],
        'approved_by': inp['approved_by'],
        'approved_at': inp['approved_at'],
        'approved_bindings': {
            rec['blocker_uid']: {
                'canonical_owner_uid': inp['canonical_owner_uid'],
                'authority_revision': inp['authority_revision'],
                'exact_binding': inp['exact_binding'],
            }
        },
    })


def write_input(rec: dict) -> None:
    dump(TMP_INPUT, {
        'schema_version': 1,
        'artifact_type': 'APPROVED_PRODUCT_DESIGN_AUTHORITY_BINDING_SET',
        'normative_authority': False,
        'stage_uid': 'STAGE-02',
        'cycle': 'PRODUCT_DESIGN_AUTHORITY_INGESTION_R7',
        'records': [rec],
    })


def expect_block(expected: str) -> None:
    buf = StringIO()
    try:
        with redirect_stderr(buf):
            validate(TMP_INPUT)
    except SystemExit as exc:
        if exc.code == 0:
            raise AssertionError(f'EXPECTED_BLOCK_BUT_EXITED_ZERO:{expected}')
        text = buf.getvalue()
        if expected not in text:
            raise AssertionError(f'WRONG_BLOCK:expected={expected}:actual={text!r}')
        return
    raise AssertionError(f'EXPECTED_BLOCK_NOT_RAISED:{expected}')


def expect_revision_block(source_doc: dict, provenance: dict, requested_revision: str, expected: str) -> None:
    buf = StringIO()
    try:
        with redirect_stderr(buf):
            prove_revision_provenance(source_doc, provenance, requested_revision, 'R7-REVISION-NEGATIVE-FIXTURE')
    except SystemExit as exc:
        if exc.code == 0:
            raise AssertionError(f'EXPECTED_REVISION_BLOCK_BUT_EXITED_ZERO:{expected}')
        text = buf.getvalue()
        if expected not in text:
            raise AssertionError(f'WRONG_REVISION_BLOCK:expected={expected}:actual={text!r}')
        return
    raise AssertionError(f'EXPECTED_REVISION_BLOCK_NOT_RAISED:{expected}')


def test_non_current_source_rejected(base: dict) -> None:
    binding = {
        'action_uid': base['target_uid'],
        'payload_schema': {'fixture_field': {'type': 'string'}},
    }
    dump(TMP_SOURCE, {
        'authority': {'id': 'R7-NEGATIVE-NON-CURRENT', 'version': 'V1.0', 'status': 'FINAL_LOCKED'},
        'bindings': [binding],
    })
    source_rel = str(TMP_SOURCE.relative_to(ROOT))
    rec = approved_record(base, source_rel, sha256_file(TMP_SOURCE), 'R7-NEGATIVE-NON-CURRENT', 'V1.0', binding)
    write_evidence(rec)
    write_input(rec)
    expect_block('R7_AUTHORITY_SOURCE_NOT_CURRENT_ADMISSIBLE')


def test_binding_not_in_current_source_rejected(base: dict) -> None:
    if not CORE_SOURCE.is_file():
        raise AssertionError('CORE_CURRENT_CAPTURE_MISSING')
    binding = {
        'action_uid': base['target_uid'],
        'payload_schema': {'invented_fixture_field': {'type': 'string'}},
    }
    rec = approved_record(base, CORE_SOURCE_REL, sha256_file(CORE_SOURCE), 'CORE_PAGE_VISUAL_AUTHORITY_FINAL', 'V2.0', binding)
    write_evidence(rec)
    write_input(rec)
    expect_block('R7_EXACT_BINDING_NOT_PHYSICALLY_PRESENT_IN_AUTHORITY')


def test_manifest_revision_provenance_for_current_asset_source() -> None:
    if not ASSET_SOURCE.is_file() or not CURRENT_MANIFEST.is_file():
        raise AssertionError('ASSET_OR_CURRENT_MANIFEST_MISSING')
    source_doc = validator_load(ASSET_SOURCE)
    if any(str(v) for v in (
        (source_doc.get('authority') or {}).get('version'),
        (source_doc.get('authority') or {}).get('revision'),
    ) if v not in (None, '')):
        raise AssertionError('ASSET_FIXTURE_UNEXPECTEDLY_HAS_INTRINSIC_REVISION')
    provenance = prove_current_admissibility(ASSET_SOURCE_REL, ASSET_SOURCE)
    manifest_revision = str((validator_load(CURRENT_MANIFEST).get('authority') or {}).get('revision'))
    kind = prove_revision_provenance(source_doc, provenance, manifest_revision, 'R7-ASSET-MANIFEST-REVISION-FIXTURE')
    if kind != 'CURRENT_AUTHORITY_MANIFEST_REVISION_WITH_EXACT_SOURCE_HASH':
        raise AssertionError(f'WRONG_MANIFEST_REVISION_PROVENANCE_KIND:{kind}')
    expect_revision_block(source_doc, provenance, 'R7-ARBITRARY-REVISION-NOT-AUTHORITY', 'R7_AUTHORITY_REVISION_NOT_PROVEN')


def cleanup() -> None:
    for path in (TMP_SOURCE, TMP_EVIDENCE, TMP_INPUT):
        path.unlink(missing_ok=True)


def main() -> None:
    cleanup()
    try:
        base = core_payload_base()
        test_non_current_source_rejected(base)
        test_binding_not_in_current_source_rejected(base)
        test_manifest_revision_provenance_for_current_asset_source()
    finally:
        cleanup()
    print('PASS: R7 rejects a physically present but non-Current authority source')
    print('PASS: R7 rejects caller-supplied exact_binding that is not physically represented in Current authority bytes')
    print('PASS: R7 accepts frozen Current manifest revision as provenance for an exact hashed Current member lacking intrinsic revision')
    print('PASS: R7 rejects arbitrary revision not proven by source or Current manifest')
    print('PASS: negative fixtures cleaned; no product/spec/Stage-01/Stage-02 output mutation performed')


if __name__ == '__main__':
    main()
