#!/usr/bin/env python3
from pathlib import Path
import re, sys
from governance_resolver import resolve

ROOT=Path(__file__).resolve().parents[2]
errors=[]
try:
    resolved=resolve()
except Exception as e:
    print('BLOCK: '+str(e),file=sys.stderr); raise SystemExit(1)

for rel in ('governance/current','governance/candidates','governance/test-runtime','governance/test-temporary'):
    if (ROOT/rel).exists(): errors.append('LEGACY_OR_DUPLICATE_ROOT:'+rel)
for rel in ('governance/specifications/current','governance/test'):
    if not (ROOT/rel).is_dir(): errors.append('MISSING_STABLE_ROOT:'+rel)
if (ROOT/'governance/test/temporary').exists():
    files=[p for p in (ROOT/'governance/test/temporary').rglob('*') if p.is_file()]
    if files: errors.append('TEMPORARY_TEST_ARTIFACT_RESIDUAL:'+str(len(files)))
    else: errors.append('EMPTY_TEMPORARY_TEST_DIRECTORY_RESIDUAL')
shim=(ROOT/'GOVERNANCE_CURRENT.yaml').read_text(encoding='utf-8')
if re.search(r'governance/(?:current|specifications)/(?:v\d)',shim): errors.append('ROOT_SHIM_VERSION_PATH')
if 'registry_ref: governance/specifications/REGISTRY.yaml' not in shim: errors.append('ROOT_SHIM_REGISTRY_BINDING_MISSING')
for rel in ('.github/workflows/targeted-stage01-stage02.yml','governance/ci/validate_targeted_stage01_stage02.py'):
    p=ROOT/rel
    if not p.is_file(): errors.append('ACTIVE_CONSUMER_MISSING:'+rel); continue
    txt=p.read_text(encoding='utf-8')
    if re.search(r'governance/(?:current|specifications)/(?:v\d)',txt): errors.append('ACTIVE_CONSUMER_HARDCODED_VERSION_PATH:'+rel)
if errors:
    for e in errors: print('BLOCK:',e,file=sys.stderr)
    raise SystemExit(1)
print('PASS: stable registry resolves active specification without version-named path dependency')
print('PASS: formal specification and test state are separated')
print('PASS: legacy current/candidate/test-runtime roots are absent from HEAD')
print('PASS: runtime specification digest='+resolved['runtime_bundle_sha256'])
