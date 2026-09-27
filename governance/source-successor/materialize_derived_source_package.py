#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, re, subprocess, sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
SEM=SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'
REF_VALIDATOR=SOURCE/'09_TESTS/governance/validate_reference_semantics.py'
GOV_TESTS=SOURCE/'09_TESTS/governance'

def semantic_hash(doc):
    obj=copy.deepcopy(doc); obj.pop('content_hash',None)
    return hashlib.sha256(yaml.safe_dump(obj,allow_unicode=True,sort_keys=True,width=180).encode()).hexdigest()

def update_text(path,old,new):
    text=path.read_text(encoding='utf-8')
    if old not in text: raise RuntimeError('MATERIALIZER_ANCHOR_MISSING:'+str(path.relative_to(ROOT)))
    path.write_text(text.replace(old,new,1),encoding='utf-8')

def refresh_semantic_hash():
    doc=yaml.safe_load(SEM.read_text(encoding='utf-8')) or {}
    old=str(doc.get('content_hash') or '')
    new=semantic_hash(doc)
    if len(new)!=64: raise RuntimeError('SEMANTIC_HASH_INVALID')
    text=SEM.read_text(encoding='utf-8')
    text2=re.sub(r'(?m)^content_hash:\s*[0-9a-f]{64}\s*$',f'content_hash: {new}',text,count=1)
    if text2==text and old!=new: raise RuntimeError('SEMANTIC_CONTENT_HASH_REPLACE_FAILED')
    SEM.write_text(text2,encoding='utf-8')
    v=REF_VALIDATOR.read_text(encoding='utf-8')
    v2=re.sub(r"SEMANTIC_BASELINE_CONTENT_HASH = '[0-9a-f]{64}'",f"SEMANTIC_BASELINE_CONTENT_HASH = '{new}'",v,count=1)
    if v2==v and old!=new: raise RuntimeError('SEMANTIC_VALIDATOR_HASH_REPLACE_FAILED')
    REF_VALIDATOR.write_text(v2,encoding='utf-8')
    return new

def run(script):
    cp=subprocess.run([sys.executable,str(GOV_TESTS/script)],cwd=GOV_TESTS,text=True,capture_output=True)
    if cp.returncode!=0:
        raise RuntimeError(script+':'+(cp.stderr or cp.stdout)[-1200:])
    return (cp.stdout or '').strip()

def materialize():
    h=refresh_semantic_hash()
    run('compile_governance_baseline.py')
    run('refresh_governance_root_manifest.py')
    cp=subprocess.run([sys.executable,str(ROOT/'governance/source-successor/refresh_source_checksums.py')],cwd=ROOT,text=True,capture_output=True)
    if cp.returncode!=0: raise RuntimeError('CHECKSUM_REFRESH_FAILED:'+(cp.stderr or cp.stdout)[-1200:])
    return h

def tracked_paths():
    return [
      '.github/governance-source/active/source/10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml',
      '.github/governance-source/active/source/09_TESTS/governance/validate_reference_semantics.py',
      '.github/governance-source/active/source/11_EVIDENCE/audit/AUDIT_BASELINE.yaml',
      '.github/governance-source/active/source/11_EVIDENCE/audit/generated/GOVERNANCE_REQUIREMENT_INDEX.json',
      '.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml',
      '.github/governance-source/active/source/CHECKSUMS.sha256',
    ]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true'); a=ap.parse_args()
    before={p:(ROOT/p).read_bytes() if (ROOT/p).exists() else None for p in tracked_paths()}
    h=materialize()
    after={p:(ROOT/p).read_bytes() if (ROOT/p).exists() else None for p in tracked_paths()}
    changed=[p for p in tracked_paths() if before[p]!=after[p]]
    if a.check and changed:
        print('BLOCK: DERIVED_SOURCE_PACKAGE_STALE:'+','.join(changed))
        return 1
    print('PASS: derived source package '+('clean' if not changed else 'materialized')+' semantic_hash='+h+' changed='+str(len(changed)))
    return 0

if __name__=='__main__': raise SystemExit(main())
