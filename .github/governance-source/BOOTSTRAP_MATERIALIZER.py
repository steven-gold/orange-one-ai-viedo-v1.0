#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, io, lzma, os, shutil, subprocess, sys, tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GS = ROOT / '.github' / 'governance-source'
ACTIVE = GS / 'active' / 'source'
TMP = GS / '.materialize_tmp'
EXPECTED_BUNDLE_SHA256 = 'b5bf1af1817e41832e53aeb6e4b78f7fa0c24ac41204fe6de2a69eb663ceb625'
EXPECTED_FILE_COUNT = 75
ORDER = [
 'bootstrap/part_000.b64','bootstrap/part_001.b64','bootstrap/part_002.b64',
 *[f'bootstrap2/part_{i:03}.b64' for i in range(3,18)],
 'bootstrap2/pair_018_019.b64','bootstrap2/pair_020_021.b64','bootstrap2/pair_022_023.b64',
 'bootstrap2/pair_024_025.b64','bootstrap2/pair_026_027.b64','bootstrap2/pair_028_029.b64','bootstrap2/pair_030_031.b64',
 *[f'bootstrap2/part_{i:03}.b64' for i in range(32,40)],
]

def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr); raise SystemExit(1)

for rel in ORDER:
    if not (GS / rel).is_file(): die(f'missing transport segment: {rel}')
stream = ''.join((GS / rel).read_text(encoding='ascii').strip() for rel in ORDER)
try: bundle = base64.b64decode(stream, validate=True)
except Exception as exc: die(f'base64 decode failed: {exc}')
sha = hashlib.sha256(bundle).hexdigest()
if sha != EXPECTED_BUNDLE_SHA256: die(f'bundle sha mismatch expected={EXPECTED_BUNDLE_SHA256} actual={sha}')
try: tar_bytes = lzma.decompress(bundle, format=lzma.FORMAT_XZ)
except Exception as exc: die(f'xz decode failed: {exc}')
if TMP.exists(): shutil.rmtree(TMP)
TMP.mkdir(parents=True)
with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode='r:') as tf:
    members = tf.getmembers()
    unsafe = [m.name for m in members if Path(m.name).is_absolute() or '..' in Path(m.name).parts]
    if unsafe: die(f'unsafe tar paths: {unsafe[:5]}')
    tf.extractall(TMP, filter='data')
files = sorted(p for p in TMP.rglob('*') if p.is_file())
if len(files) != EXPECTED_FILE_COUNT: die(f'file count expected=75 actual={len(files)}')
residual = [str(p.relative_to(TMP)) for p in files if p.suffix == '.pyc' or '__pycache__' in p.parts]
if residual: die(f'forbidden residual files: {residual}')
checksums = TMP / 'CHECKSUMS.sha256'
if not checksums.is_file(): die('CHECKSUMS.sha256 missing')
for line in checksums.read_text(encoding='utf-8').splitlines():
    line=line.strip()
    if not line: continue
    parts=line.split(None,1)
    if len(parts)!=2: die(f'invalid checksum line: {line}')
    expected, rel = parts[0], parts[1].lstrip('* ')
    p=TMP/rel
    if not p.is_file(): die(f'checksum target missing: {rel}')
    actual=hashlib.sha256(p.read_bytes()).hexdigest()
    if actual != expected: die(f'checksum mismatch: {rel}')
if ACTIVE.exists(): shutil.rmtree(ACTIVE)
ACTIVE.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(TMP, ACTIVE)
shutil.rmtree(TMP)
# Recheck exact count after copy.
active_files=sorted(p for p in ACTIVE.rglob('*') if p.is_file())
if len(active_files) != EXPECTED_FILE_COUNT: die(f'active source count expected=75 actual={len(active_files)}')
print(f'PASS: deterministic bundle sha256={sha}')
print(f'PASS: exact source files={len(active_files)}')
print('PASS: CHECKSUMS.sha256 verified for all listed source files')
print('PASS: no pyc/__pycache__ residual')
