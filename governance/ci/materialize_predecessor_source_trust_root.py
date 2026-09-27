#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
CHECKSUMS=SOURCE/'CHECKSUMS.sha256'
SEMANTIC=SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_from_frozen_checksum()->dict[str,str]:
    if not CHECKSUMS.is_file():
        raise RuntimeError('PREDECESSOR_CHECKSUM_LEDGER_MISSING')
    expected={}
    for raw in CHECKSUMS.read_text(encoding='utf-8').splitlines():
        line=raw.strip()
        if not line:
            continue
        parts=line.split(None,1)
        if len(parts)!=2 or len(parts[0])!=64:
            raise RuntimeError('PREDECESSOR_CHECKSUM_LEDGER_ROW_INVALID:'+raw)
        digest,path=parts
        rel=path.strip()
        if rel.startswith('./'):
            rel=rel[2:]
        if not rel or rel in expected:
            raise RuntimeError('PREDECESSOR_CHECKSUM_LEDGER_PATH_INVALID_OR_DUPLICATE:'+rel)
        expected[rel]=digest.lower()
    expected['CHECKSUMS.sha256']=sha(CHECKSUMS)
    return expected


def current_files()->dict[str,str]:
    forbidden_parts={'__pycache__','.next','dist','build','coverage','playwright-report','test-results','node_modules'}
    forbidden_suffix={'.pyc','.pyo','.tmp','.bak','.swp'}
    out={}
    for fp in SOURCE.rglob('*'):
        if not fp.is_file():
            continue
        if any(x in fp.parts for x in forbidden_parts) or fp.suffix in forbidden_suffix or fp.name.endswith('~'):
            continue
        out[fp.relative_to(SOURCE).as_posix()]=sha(fp)
    return out


def materialize(out:Path)->dict:
    expected=expected_from_frozen_checksum()
    actual=current_files()
    missing=sorted(set(expected)-set(actual))
    extra=sorted(set(actual)-set(expected))
    drift=sorted(rel for rel,digest in expected.items() if actual.get(rel)!=digest)
    if missing or extra or drift:
        raise RuntimeError('PREDECESSOR_SOURCE_IMMUTABILITY_DRIFT:'+json.dumps({'missing':missing,'extra':extra,'hash_drift':drift},sort_keys=True))
    sem=yaml.safe_load(SEMANTIC.read_text(encoding='utf-8')) or {}
    content_hash=str(sem.get('content_hash') or '')
    if not content_hash:
        raise RuntimeError('SEMANTIC_AUTHORITY_CONTENT_HASH_MISSING')
    payload={
      'schema_version':1,
      'trust_model':'EXTERNAL_IMMUTABLE_PACKAGE_HASH_SET',
      'source':'FROZEN_PREDECESSOR_CHECKSUM_LEDGER',
      'checksum_ledger':'CHECKSUMS.sha256',
      'semantic_authority_content_hash':content_hash,
      'package_files':[{'path':rel,'sha256':expected[rel]} for rel in sorted(expected)],
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return {'status':'PASS','verified_files':len(expected),'output':str(out),'current_self_sign':False}


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    try:
        result=materialize(Path(args.out))
    except Exception as exc:
        print('BLOCK: '+str(exc),file=sys.stderr)
        return 1
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
