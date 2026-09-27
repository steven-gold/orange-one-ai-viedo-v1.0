#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
OUT=SOURCE/'CHECKSUMS.sha256'
FORBIDDEN_PARTS={'__pycache__','.next','dist','build','coverage','playwright-report','test-results','node_modules'}
FORBIDDEN_SUFFIX={'.pyc','.pyo','.tmp','.bak','.swp'}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rows():
    out=[]
    for p in SOURCE.rglob('*'):
        if not p.is_file() or p==OUT: continue
        if any(x in p.parts for x in FORBIDDEN_PARTS) or p.suffix in FORBIDDEN_SUFFIX or p.name.endswith('~'): continue
        out.append((p.relative_to(SOURCE).as_posix(),sha(p)))
    return sorted(out)
def render():
    return ''.join(f'{digest}  {rel}\n' for rel,digest in rows())
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true'); a=ap.parse_args()
    expected=render()
    if a.check:
        actual=OUT.read_text(encoding='utf-8') if OUT.is_file() else ''
        if actual!=expected:
            print('BLOCK: SOURCE_CHECKSUM_LEDGER_STALE')
            return 1
        print(f'PASS: source checksum ledger exact rows={len(rows())}')
        return 0
    OUT.write_text(expected,encoding='utf-8')
    print(f'PASS: source checksum ledger refreshed rows={len(rows())}')
    return 0
if __name__=='__main__': raise SystemExit(main())
