#!/usr/bin/env python3
from pathlib import Path
import hashlib, shutil, tarfile, yaml, subprocess, json

root=Path('.')
m=yaml.safe_load((root/'governance/test-runtime/v2.1.5/STAGE1_RUNTIME_MANIFEST.yaml').read_text())
chunks=m['transport']['chunks']
if len(chunks)!=m['transport']['chunk_count']: raise SystemExit('chunk_count mismatch')
payload=[]; expected_chunk_paths=[]
for item in chunks:
    p=root/item['path']; expected_chunk_paths.append(item['path'])
    if not p.is_file(): raise SystemExit(f'missing runtime chunk: {p}')
    b=p.read_bytes()
    if len(b)!=item['size']: raise SystemExit(f'chunk size mismatch: {p}: {len(b)}')
    got=hashlib.sha256(b).hexdigest()
    if got!=item['sha256']: raise SystemExit(f'chunk sha mismatch: {p}: {got}')
    payload.append(b)
assembled=b''.join(payload)
if len(assembled)!=m['transport']['assembled_size_bytes']: raise SystemExit('assembled size mismatch')
got_bundle=hashlib.sha256(assembled).hexdigest()
if got_bundle!=m['transport']['assembled_bundle_sha256']: raise SystemExit('assembled bundle sha mismatch: '+got_bundle)
runtime_dir=root/'governance/test-runtime/v2.1.5'
actual=[p.as_posix() for p in runtime_dir.iterdir() if p.is_file() and p.name!='STAGE1_RUNTIME_MANIFEST.yaml']
if sorted(actual)!=sorted(expected_chunk_paths): raise SystemExit('runtime directory contains unregistered residue')

tar_path=Path('/tmp/acpos-v215-stage1.tar.gz'); tar_path.write_bytes(assembled)
out=Path('/tmp/acpos-gov-v215-stage1'); shutil.rmtree(out,ignore_errors=True); out.mkdir(parents=True)
expected={x['path']:x['sha256'] for x in m['files']}
with tarfile.open(tar_path,'r:gz') as tf:
    members=[x for x in tf.getmembers() if x.isfile()]
    names=sorted(x.name.lstrip('./') for x in members)
    if names!=sorted(expected): raise SystemExit(f'sealed runtime member set mismatch: {names}')
    for member in members:
        name=member.name.lstrip('./'); target=(out/name).resolve()
        if not str(target).startswith(str(out.resolve())+'/'): raise SystemExit('unsafe tar member')
    tf.extractall(out)
for rel,sha in expected.items():
    got=hashlib.sha256((out/rel).read_bytes()).hexdigest()
    if got!=sha: raise SystemExit(f'sealed file sha mismatch {rel}: {got}')
print('PASS: exact v2.1.5 runtime transport + exact six-file set + file hashes')

result=Path('/tmp/stage1.json')
with result.open('w') as f:
    subprocess.run(['python',str(out/'09_TESTS/governance/test_stage1_source_to_blueprint_minimal_control.py')],stdout=f,check=True)
r=json.load(result.open())
assert r['total']==31, r
assert r['passed_expectations']==31, r
assert all(x.get('ok') is True for x in r['results']), r
print('PASS: sealed v2.1.5 Stage-1 minimal-control = 31/31')
