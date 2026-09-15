#!/usr/bin/env python3
from pathlib import Path
import json
import yaml
from canonical_rule_registry import load_registry, required_rule_uids, scan_policy_text
from specification_mutation_guard import prewrite_context_errors

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
if rules.get('governance_uid_role') != 'REGISTRY_MATERIALIZATION_PROVENANCE_ONLY':
    fail('CANONICAL_RULE_REGISTRY_GOVERNANCE_UID_ROLE_AMBIGUOUS')
if rules.get('governance_uid_may_select_current_governance') is not False:
    fail('CANONICAL_RULE_REGISTRY_GOVERNANCE_UID_MAY_SELECT_CURRENT')
if rules.get('current_governance_identity_source') != 'governance/specifications/REGISTRY.yaml':
    fail('CANONICAL_RULE_REGISTRY_CURRENT_IDENTITY_SOURCE_DRIFT')
support = manifest.get('support_authorities') or []
matched = [x for x in support if x.get('uid') == expected_uid]
if len(matched) != 1:
    fail('MANIFEST_CANONICAL_REGISTRY_BINDING_NOT_EXACTLY_ONE')
else:
    if matched[0].get('file') != 'CANONICAL_RULE_REGISTRY.yaml':
        fail('MANIFEST_CANONICAL_REGISTRY_PATH_DRIFT')
    if matched[0].get('digest') != expected_digest:
        fail('MANIFEST_CANONICAL_REGISTRY_DIGEST_DRIFT')
cr = registry.get('canonical_rule_registry') or {}
if cr.get('uid') != expected_uid:
    fail('ROOT_REGISTRY_CANONICAL_UID_DRIFT')
if cr.get('digest') != expected_digest:
    fail('ROOT_REGISTRY_CANONICAL_DIGEST_DRIFT')
if cr.get('ref') != 'governance/specifications/current/CANONICAL_RULE_REGISTRY.yaml':
    fail('ROOT_REGISTRY_CANONICAL_PATH_DRIFT')

required = required_rule_uids() if rules else set()
layer = yaml.safe_load((CUR/'GOVERNANCE_LAYER_SEPARATION_AND_PORTABILITY.yaml').read_text(encoding='utf-8')) or {}
layer_refs = set(layer.get('canonical_rule_refs') or [])
if not required.issubset(layer_refs):
    fail('LAYER_POLICY_MISSING_CANONICAL_RULE_REFS')
mutation = yaml.safe_load((CUR/'SPECIFICATION_MUTATION_CONTROL.yaml').read_text(encoding='utf-8')) or {}
if not {'GOV-RULE-ANTI-DRIFT-008','GOV-RULE-ANTI-DRIFT-009','GOV-RULE-ANTI-DRIFT-010'}.issubset(set(mutation.get('canonical_rule_refs') or [])):
    fail('MUTATION_POLICY_MISSING_CANONICAL_RULE_REFS')

portability = (ROOT/'governance/ci/validate_governance_portability.py').read_text(encoding='utf-8')
if 'from canonical_rule_registry import load_registry, scan_policy_text' not in portability:
    fail('PORTABILITY_VALIDATOR_NOT_USING_CANONICAL_REGISTRY')
for forbidden in ('fixed=re.compile(', 'retry=re.compile(', 'exactly eleven ordered stages|fixed lifecycle'):
    if forbidden in portability:
        fail('PORTABILITY_LOCAL_RULE_FORK:'+forbidden)

# Lexical hints are secondary. Language that forbids or requires a semantic field
# is not a concrete binding, but a real project/run/tool binding must still be caught.
negative_probes = (
    'Reusable POLICY MUST NOT bind run UID or attempt UID.',
    'workflow path in reusable policy is FORBIDDEN.',
    'may_not_define:\n  - WORKFLOW_PATH\n  - RUN_OR_ATTEMPT_ID',
    '每次正式 Validation MUST 建立唯一 `run_uid`，所有本次 Gate Evidence MUST 綁同一 `run_uid` 與 `source_revision`。',
    'Audit MUST 顯示本次 `run_uid`、Execution Cycle、Source Revision、開始/結束時間與 Terminal Status。',
)
for probe in negative_probes:
    findings = scan_policy_text(probe)
    if findings:
        fail('LEXICAL_SECONDARY_FALSE_POSITIVE:' + repr(probe) + ':' + repr(findings))

positive_probes = {
    'run_uid: FRESH-RUN-TEST-001': 'RUN_ID',
    'Bind run UID FRESH-RUN-TEST-001 for this reusable policy.': 'RUN_ID',
    'workflow_path: .github/workflows/example.yml': 'IMPLEMENTATION_PATH',
    'selected fixed work unit STAGE-02': 'FIXED_WORK_UNIT_ID',
}
for probe, semantic_type in positive_probes.items():
    findings = scan_policy_text(probe)
    if semantic_type not in {x.get('semantic_type') for x in findings}:
        fail('LEXICAL_CONFIRMED_BINDING_NOT_BLOCKED:' + semantic_type + ':' + repr(probe))

# Future protected specification mutations reuse the existing authorization
# receipt type and must prove pre-write read/owner/duplicate/conflict checks.
valid_prewrite_receipt = '''
pre_write_context_verification:
  relevant_scope_read_complete: true
  canonical_owner_resolution_complete: true
  existing_semantics_comparison_complete: true
  duplicate_search_complete: true
  conflict_search_complete: true
  second_system_search_complete: true
  gap_proven_before_write: true
  reviewed_authority_ref_count: 3
  reviewed_existing_owner_ref_count: 2
  write_disposition: MODIFY_EXISTING_CANONICAL_OWNER
  comparison_result: NO_UNRESOLVED_DUPLICATE_CONFLICT_OR_SECOND_SYSTEM
'''
if prewrite_context_errors(valid_prewrite_receipt):
    fail('PREWRITE_VALID_RECEIPT_REJECTED:' + repr(prewrite_context_errors(valid_prewrite_receipt)))
invalid_prewrite_receipt = valid_prewrite_receipt.replace('duplicate_search_complete: true', 'duplicate_search_complete: false')
if not prewrite_context_errors(invalid_prewrite_receipt):
    fail('PREWRITE_MISSING_DUPLICATE_PROOF_NOT_BLOCKED')

for rel in ('.github/workflows/governance-full-line-system-gate.yml','.github/workflows/targeted-stage01-stage02.yml'):
    p=ROOT/rel
    if not p.is_file():
        fail('ACTIVE_WORKFLOW_MISSING:'+rel)
        continue
    txt=p.read_text(encoding='utf-8')
    if 'validate_canonical_rule_registry.py' not in txt:
        fail('ACTIVE_WORKFLOW_MISSING_CANONICAL_GATE:'+rel)
    if 'validate_stage_test_remediation_closure_protocol.py' in txt:
        fail('ACTIVE_WORKFLOW_STALE_COMPAT_SHIM:'+rel)
    if 'validate_validation_remediation_closure_protocol.py' not in txt:
        fail('ACTIVE_WORKFLOW_MISSING_NEUTRAL_CLOSURE_VALIDATOR:'+rel)

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
    if (ROOT/rel).exists():
        fail('OBSOLETE_ACTIVE_CONSUMER_RESIDUAL:'+rel)

out = {
 'status':'PASS' if not FAILURES else 'FAIL',
 'registry_uid': expected_uid,
 'registry_digest': expected_digest,
 'required_rule_count': len(required),
 'lexical_secondary_regression_probes': len(negative_probes) + len(positive_probes),
 'prewrite_context_guard_regression': 'PASS' if not prewrite_context_errors(valid_prewrite_receipt) and prewrite_context_errors(invalid_prewrite_receipt) else 'FAIL',
 'failures': FAILURES,
}
print(json.dumps(out, ensure_ascii=False, indent=2))
raise SystemExit(0 if not FAILURES else 1)
