#!/usr/bin/env python3
from pathlib import Path
import json
import sys
import yaml
from canonical_rule_registry import load_registry, required_rule_uids

ROOT = Path(__file__).resolve().parents[2]
CUR = ROOT / 'governance/specifications/current'
REGISTRY = ROOT / 'governance/specifications/REGISTRY.yaml'
MANIFEST = CUR / 'SPECIFICATION_MANIFEST.yaml'
FAILURES = []


def fail(msg: str) -> None:
    FAILURES.append(msg)

try:
    rules = load_registry()
except Exception as exc:
    rules = {}
    fail('CANONICAL_RULE_REGISTRY_INVALID:' + str(exc))

manifest = yaml.safe_load(MANIFEST.read_text(encoding='utf-8')) or {}
registry = yaml.safe_load(REGISTRY.read_text(encoding='utf-8')) or {}
expected_uid = rules.get('registry_uid')
expected_digest = rules.get('registry_digest')
support = manifest.get('support_authorities') or []
matched = [x for x in support if x.get('uid') == expected_uid]
if len(matched) != 1:
    fail('MANIFEST_CANONICAL_REGISTRY_BINDING_NOT_EXACTLY_ONE')
else:
    if matched[0].get('file') != 'CANONICAL_RULE_REGISTRY.yaml': fail('MANIFEST_CANONICAL_REGISTRY_PATH_DRIFT')
    if matched[0].get('digest') != expected_digest: fail('MANIFEST_CANONICAL_REGISTRY_DIGEST_DRIFT')
cr = registry.get('canonical_rule_registry') or {}
if cr.get('uid') != expected_uid: fail('ROOT_REGISTRY_CANONICAL_UID_DRIFT')
if cr.get('digest') != expected_digest: fail('ROOT_REGISTRY_CANONICAL_DIGEST_DRIFT')
if cr.get('ref') != 'governance/specifications/current/CANONICAL_RULE_REGISTRY.yaml': fail('ROOT_REGISTRY_CANONICAL_PATH_DRIFT')

required = required_rule_uids() if rules else set()
layer = yaml.safe_load((CUR/'GOVERNANCE_LAYER_SEPARATION_AND_PORTABILITY.yaml').read_text(encoding='utf-8')) or {}
layer_refs = set(layer.get('canonical_rule_refs') or [])
if not required.issubset(layer_refs): fail('LAYER_POLICY_MISSING_CANONICAL_RULE_REFS')
mutation = yaml.safe_load((CUR/'SPECIFICATION_MUTATION_CONTROL.yaml').read_text(encoding='utf-8')) or {}
if not {'GOV-RULE-ANTI-DRIFT-008','GOV-RULE-ANTI-DRIFT-009','GOV-RULE-ANTI-DRIFT-010'}.issubset(set(mutation.get('canonical_rule_refs') or [])):
    fail('MUTATION_POLICY_MISSING_CANONICAL_RULE_REFS')

portability = (ROOT/'governance/ci/validate_governance_portability.py').read_text(encoding='utf-8')
if 'from canonical_rule_registry import load_registry, scan_policy_text' not in portability:
    fail('PORTABILITY_VALIDATOR_NOT_USING_CANONICAL_REGISTRY')
for forbidden in ('fixed=re.compile(', 'retry=re.compile(', 'exactly eleven ordered stages|fixed lifecycle'):
    if forbidden in portability: fail('PORTABILITY_LOCAL_RULE_FORK:'+forbidden)

for rel in ('.github/workflows/governance-full-line-system-gate.yml','.github/workflows/targeted-stage01-stage02.yml'):
    p=ROOT/rel
    if not p.is_file(): fail('ACTIVE_WORKFLOW_MISSING:'+rel); continue
    txt=p.read_text(encoding='utf-8')
    if 'validate_canonical_rule_registry.py' not in txt: fail('ACTIVE_WORKFLOW_MISSING_CANONICAL_GATE:'+rel)
    if 'validate_stage_test_remediation_closure_protocol.py' in txt: fail('ACTIVE_WORKFLOW_STALE_COMPAT_SHIM:'+rel)
    if 'validate_validation_remediation_closure_protocol.py' not in txt: fail('ACTIVE_WORKFLOW_MISSING_NEUTRAL_CLOSURE_VALIDATOR:'+rel)

obsolete = [
 '.github/workflows/fix-mother-neutrality-normalizer.yml',
 '.github/workflows/mother-spec-neutrality-empty-section-diagnostic.yml',
 '.github/workflows/mother-spec-neutrality-promotion.yml',
 '.github/workflows/mother-spec-neutrality-promotion-executor.yml',
 '.github/workflows/mother-spec-neutrality-promotion-executor-r2.yml',
 '.github/workflows/mother-spec-neutrality-promotion-executor-r3.yml',
 '.github/workflows/mother-spec-neutrality-promotion-executor-r4.yml',
 '.github/workflows/mother-spec-neutrality-promotion-executor-r5.yml',
 '.github/workflows/mother-spec-neutrality-promotion-executor-r6.yml',
 'governance/ci/validate_stage_test_remediation_closure_protocol.py',
]
for rel in obsolete:
    if (ROOT/rel).exists(): fail('OBSOLETE_ACTIVE_CONSUMER_RESIDUAL:'+rel)

out = {
 'status':'PASS' if not FAILURES else 'FAIL',
 'registry_uid': expected_uid,
 'registry_digest': expected_digest,
 'required_rule_count': len(required),
 'failures': FAILURES,
}
print(json.dumps(out, ensure_ascii=False, indent=2))
raise SystemExit(0 if not FAILURES else 1)
