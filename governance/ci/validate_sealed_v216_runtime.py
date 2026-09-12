#!/usr/bin/env python3
from pathlib import Path
import hashlib, yaml, tarfile, tempfile, subprocess, sys, json
root=Path('.')
manifest=yaml.safe_load((root/'governance/test-runtime/v2.1.6/STAGE1_RUNTIME_MANIFEST.yaml').read_text())
chunks=manifest['transport']['chunks']; parts=[]
for c in chunks:
 p=root/c['path']; b=p.read_bytes()
 if len(b)!=c['size']: raise SystemExit(f'chunk size mismatch: {p}')
 if hashlib.sha256(b).hexdigest()!=c['sha256']: raise SystemExit(f'chunk sha mismatch: {p}')
 parts.append(b)
bundle=b''.join(parts)
if len(bundle)!=manifest['transport']['assembled_size_bytes']: raise SystemExit('assembled size mismatch')
if hashlib.sha256(bundle).hexdigest()!=manifest['transport']['assembled_bundle_sha256']: raise SystemExit('assembled sha mismatch')
with tempfile.TemporaryDirectory() as td:
 t=Path(td); arc=t/'runtime.tar.gz'; arc.write_bytes(bundle)
 with tarfile.open(arc,'r:gz') as tf:
  names=sorted(m.name for m in tf.getmembers() if m.isfile())
  expected=sorted(x['path'] for x in manifest['files'])
  if names!=expected: raise SystemExit('runtime member set mismatch')
  tf.extractall(t/'pkg')
 pkg=t/'pkg'
 for f in manifest['files']:
  p=pkg/f['path']; got=hashlib.sha256(p.read_bytes()).hexdigest()
  if got!=f['sha256']: raise SystemExit('sealed file sha mismatch: '+f['path'])
 r=subprocess.run([sys.executable,'09_TESTS/governance/test_stage1_source_to_blueprint_minimal_control.py'],cwd=pkg,text=True,capture_output=True)
 if r.returncode!=0: print(r.stdout); print(r.stderr); raise SystemExit('Stage-1 minimal-control failed')
 try: o=json.loads(r.stdout)
 except Exception: raise SystemExit('Stage-1 output not JSON')
 if o.get('passed')!=33 or o.get('total')!=33: raise SystemExit('Stage-1 not 33/33')
 r2=subprocess.run([sys.executable,'09_TESTS/governance/governance_lifecycle_stage_contract_guard.py'],cwd=pkg,text=True,capture_output=True)
 if r2.returncode!=0: print(r2.stdout); print(r2.stderr); raise SystemExit('lifecycle guard failed')
 o2=json.loads(r2.stdout)
 if o2.get('status')!='PASS' or o2.get('stage_count')!=11 or o2.get('failures'): raise SystemExit('lifecycle semantic granularity not 11/11 clean')
 print('PASS: sealed v2.1.6 runtime exact; Stage-1 33/33; semantic-granularity lifecycle 11/11')
