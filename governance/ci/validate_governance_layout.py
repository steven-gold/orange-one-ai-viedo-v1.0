#!/usr/bin/env python3
from pathlib import Path
import re
import sys
import yaml
from governance_resolver import resolve

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'governance/specifications/REGISTRY.yaml'
errors=[]

try:
    resolved=resolve()
except Exception as e:
    print('BLOCK: '+str(e),file=sys.stderr)
    raise SystemExit(1)

if not REGISTRY.is_file():
    errors.append('CURRENT_REGISTRY_MISSING')
else:
    reg=yaml.safe_load(REGISTRY.read_text(encoding='utf-8')) or {}
    roles=reg.get('branch_role_contract') or {}
    governance_branch=str(reg.get('branch') or '')
    if roles.get(governance_branch) not in {'IMMUTABLE_GOVERNANCE_RULESET','GOVERNANCE_REVISION_CANDIDATE'}:
        errors.append('CURRENT_REGISTRY_BRANCH_OR_ROLE_DRIFT')
    product_branch=str(reg.get('product_execution_branch') or '')
    if not product_branch or roles.get(product_branch)!='PRODUCT_EXECUTION_WORKLINE':
        errors.append('CURRENT_PRODUCT_EXECUTION_BRANCH_OR_ROLE_DRIFT')
    if governance_branch==product_branch:
        errors.append('CURRENT_GOVERNANCE_PRODUCT_BRANCH_COLLISION')
    if reg.get('rules_root')!='governance/specifications/current':
        errors.append('CURRENT_RULES_ROOT_DRIFT')

required_roots=('governance/specifications/current',)
for rel in required_roots:
    if not (ROOT/rel).is_dir():
        errors.append('MISSING_CURRENT_ROOT:'+rel)

for rel in (
    'GOVERNANCE_CURRENT.yaml',
    'governance/current',
    'governance/candidates',
    'governance/test',
    'governance/test-runtime',
    'governance/test-temporary',
):
    if (ROOT/rel).exists():
        errors.append('LEGACY_OR_PRODUCT_STATE_ROOT_FORBIDDEN:'+rel)

current_consumers=(
    '.github/workflows/common-stage-execution-engine.yml',
    'governance/ci/stage_execution_engine.py',
    'governance/ci/validate_selected_execution_profile_integrity.py',
    'governance/ci/validate_active_consumer_reference_integrity.py',
)
for rel in current_consumers:
    p=ROOT/rel
    if not p.is_file():
        errors.append('CURRENT_CONSUMER_MISSING:'+rel)
        continue
    txt=p.read_text(encoding='utf-8')
    if re.search(r'governance/(?:current|specifications)/(?:v\d)',txt):
        errors.append('CURRENT_CONSUMER_HARDCODED_VERSION_PATH:'+rel)
    if 'GOVERNANCE_CURRENT.yaml' in txt and rel!='governance/ci/validate_governance_layout.py':
        errors.append('CURRENT_CONSUMER_LEGACY_SHIM_REFERENCE:'+rel)

if errors:
    for e in errors:
        print('BLOCK:',e,file=sys.stderr)
    raise SystemExit(1)

print('PASS: REGISTRY.yaml is the single Current governance entrypoint')
print('PASS: governance/specifications/current is the only Current rule root')
print('PASS: governance branch contains no product run-state/test-state root')
print('PASS: no GOVERNANCE_CURRENT shim or version-named Current path is required')
print('PASS: runtime specification digest='+resolved['runtime_bundle_sha256'])
