#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import io
import json
import lzma
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '.github' / 'governance-source' / 'active' / 'source'
EXPECTED_FILE_COUNT = 75
EXPECTED_CHECKSUM_ENTRIES = 74
EXPECTED_BUNDLE_SHA256 = '196d2d6be84f904daa3b206e2d8ac3664a79df6f8c6033dbb27914e90027e310'
EXPECTED_SOURCE_ZIP_SHA256 = 'adbb39e42b1d091afbe2ff8836f5293dfff31feeb79148110382f25b4988b61d'
CRITICAL = {
    '10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',
    '10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml',
    '09_TESTS/governance/validate_governance.py',
    'CHECKSUMS.sha256',
    'pytest.ini',
}
REPORT = ROOT / '.github' / 'governance-source' / 'SOURCE_IDENTITY_REPORT.json'

errors: list[str] = []

def fail(msg: str) -> None:
    errors.append(msg)

if not SOURCE.is_dir():
    fail('ACTIVE_SOURCE_ROOT_MISSING')
    files = []
else:
    files = sorted((p for p in SOURCE.rglob('*') if p.is_file()), key=lambda p: p.relative_to(SOURCE).as_posix())

relpaths = [p.relative_to(SOURCE).as_posix() for p in files]
if len(files) != EXPECTED_FILE_COUNT:
    fail(f'FILE_COUNT_MISMATCH expected={EXPECTED_FILE_COUNT} actual={len(files)}')
if len(relpaths) != len(set(relpaths)):
    fail('DUPLICATE_RELATIVE_PATH')

residual = [r for r in relpaths if r.endswith('.pyc') or '/__pycache__/' in f'/{r}/' or r.startswith('__pycache__/')]
if residual:
    fail('FORBIDDEN_RUNTIME_RESIDUAL:' + ','.join(residual))

missing_critical = sorted(CRITICAL - set(relpaths))
if missing_critical:
    fail('CRITICAL_FILE_MISSING:' + ','.join(missing_critical))

checksum_entries: dict[str, str] = {}
checksum_path = SOURCE / 'CHECKSUMS.sha256'
if checksum_path.is_file():
    for lineno, raw in enumerate(checksum_path.read_text(encoding='utf-8').splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            fail(f'INVALID_CHECKSUM_LINE line={lineno}')
            continue
        expected, rel = parts[0], parts[1].lstrip('* ')
        if rel in checksum_entries:
            fail(f'DUPLICATE_CHECKSUM_PATH:{rel}')
            continue
        checksum_entries[rel] = expected
        target = SOURCE / rel
        if not target.is_file():
            fail(f'CHECKSUM_TARGET_MISSING:{rel}')
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected:
            fail(f'CHECKSUM_MISMATCH:{rel}:expected={expected}:actual={actual}')
else:
    fail('CHECKSUMS_FILE_MISSING')

if len(checksum_entries) != EXPECTED_CHECKSUM_ENTRIES:
    fail(f'CHECKSUM_ENTRY_COUNT_MISMATCH expected={EXPECTED_CHECKSUM_ENTRIES} actual={len(checksum_entries)}')
expected_checksum_paths = set(relpaths) - {'CHECKSUMS.sha256'}
if set(checksum_entries) != expected_checksum_paths:
    missing = sorted(expected_checksum_paths - set(checksum_entries))
    extra = sorted(set(checksum_entries) - expected_checksum_paths)
    fail(f'CHECKSUM_PATH_SET_MISMATCH missing={missing} extra={extra}')

# Rebuild exactly the deterministic source bundle used for bootstrap. This proves
# the materialized GitHub path set, file bytes, executable modes, and normalized tar metadata agree.
bundle_sha = None
bundle_size = None
if not errors:
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode='w', format=tarfile.PAX_FORMAT) as tf:
        for p in files:
            rel = p.relative_to(SOURCE).as_posix()
            info = tf.gettarinfo(str(p), arcname=rel)
            info.uid = 0
            info.gid = 0
            info.uname = ''
            info.gname = ''
            info.mtime = 0
            with p.open('rb') as fh:
                tf.addfile(info, fh)
    bundle = lzma.compress(tar_buf.getvalue(), format=lzma.FORMAT_XZ, preset=9)
    bundle_sha = hashlib.sha256(bundle).hexdigest()
    bundle_size = len(bundle)
    if bundle_sha != EXPECTED_BUNDLE_SHA256:
        fail(f'DETERMINISTIC_BUNDLE_SHA_MISMATCH expected={EXPECTED_BUNDLE_SHA256} actual={bundle_sha}')

source_zip_sha = None
if not errors:
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files:
            rel = p.relative_to(SOURCE).as_posix()
            zi = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 3
            mode = 0o755 if (p.stat().st_mode & 0o111) else 0o644
            zi.external_attr = (mode & 0xFFFF) << 16
            zf.writestr(zi, p.read_bytes())
    source_zip_sha = hashlib.sha256(zbuf.getvalue()).hexdigest()
    if source_zip_sha != EXPECTED_SOURCE_ZIP_SHA256:
        fail(f'DETERMINISTIC_SOURCE_ZIP_SHA_MISMATCH expected={EXPECTED_SOURCE_ZIP_SHA256} actual={source_zip_sha}')

report = {
    'artifact_type': 'NON_NORMATIVE_SOURCE_IDENTITY_EVIDENCE',
    'source_root': '.github/governance-source/active/source',
    'file_count_expected': EXPECTED_FILE_COUNT,
    'file_count_actual': len(files),
    'checksum_entries_expected': EXPECTED_CHECKSUM_ENTRIES,
    'checksum_entries_actual': len(checksum_entries),
    'critical_files_present': not missing_critical,
    'runtime_residual_count': len(residual),
    'deterministic_bundle_sha256_expected': EXPECTED_BUNDLE_SHA256,
    'deterministic_bundle_sha256_actual': bundle_sha,
    'deterministic_source_zip_sha256_expected': EXPECTED_SOURCE_ZIP_SHA256,
    'deterministic_source_zip_sha256_actual': source_zip_sha,
    'deterministic_bundle_size': bundle_size,
    'result': 'PASS' if not errors else 'FAIL',
    'errors': errors,
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

if errors:
    for error in errors:
        print('BLOCK:', error, file=sys.stderr)
    raise SystemExit(1)

print(f'PASS: exact file count={len(files)}')
print(f'PASS: checksum entries={len(checksum_entries)} and path set is exact')
print('PASS: every listed source checksum matches')
print('PASS: critical registry/baseline/validator files present')
print('PASS: no pyc/__pycache__ residual')
print(f'PASS: deterministic bundle sha256={bundle_sha}')
print(f'PASS: deterministic source zip sha256={source_zip_sha}')
print('PASS: GITHUB_MATERIALIZED_SOURCE_IDENTICAL_TO_VERIFIED_75_FILE_SOURCE')
