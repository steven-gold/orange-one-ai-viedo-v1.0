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
except Exception as exc:
    print('BLOCK: '+str(exc),file=sys.stderr)
    raise SystemExit(1)

reg=yaml.safe_load(REGISTRY.read_text(encoding='utf-8')) or {}
identity=reg.get('governance_identity') or {}
validation=reg.get('current_validation_contract') or {}
roles=reg.get('branch_role_contract') or {}
branch=str(reg.get('branch') or '')

if reg.get('registry_role')!='CURRENT_GOVERNANCE_ENTRYPOINT':
    errors.append('CURRENT_REGISTRY_ROLE_DRIFT')
if reg.get('status')!='CURRENT':
    errors.append('CURRENT_REGISTRY_STATUS_DRIFT')
if roles.get(branch)!='CURRENT_GOVERNANCE_WORKLINE':
    errors.append('CURRENT_GOVERNANCE_WORKLINE_ROLE_DRIFT')
if 'candidate_validation_contract' in reg:
    errors.append('LEGACY_CANDIDATE_VALIDATION_CONTRACT_PRESENT')

for key in ('governance_uid','governance_revision','display_version','identity_authority',
            'specification_bundle_sha256','canonical_rule_registry_uid','canonical_rule_registry_digest'):
    if identity.get(key) in (None,'',[]):
        errors.append('CURRENT_GOVERNANCE_IDENTITY_FIELD_MISSING:'+key)
if identity.get('status')!='CURRENT':
    errors.append('CURRENT_GOVERNANCE_IDENTITY_STATUS_DRIFT')
if identity.get('identity_state')!='EXACT_HEAD_AND_BUNDLE_DIGEST_BOUND':
    errors.append('CURRENT_GOVERNANCE_IDENTITY_STATE_DRIFT')
if identity.get('identity_authority')!='governance/specifications/REGISTRY.yaml':
    errors.append('CURRENT_GOVERNANCE_IDENTITY_AUTHORITY_DRIFT')
for key in ('governance_uid','governance_revision','display_version','identity_authority'):
    if resolved.get(key)!=identity.get(key):
        errors.append('REGISTRY_RESOLVER_IDENTITY_DRIFT:'+key)

expected_false=(
    'external_human_or_account_evidence_required',
    'external_auditor_required',
    'external_signer_required',
    'detached_external_trust_required',
    'promotion_required_before_product_stage_execution',
    'released_governance_selection_required',
)
for key in expected_false:
    if validation.get(key) is not False:
        errors.append('NON_WORD_EXTERNAL_GATE_REINTRODUCED:'+key)
if validation.get('authority_model')!='WORD_DERIVED_INTERNAL_VALIDATION':
    errors.append('WORD_DERIVED_AUTHORITY_MODEL_DRIFT')
if validation.get('word_source_is_primary_product_design_source') is not True:
    errors.append('WORD_SOURCE_PRIMARY_AUTHORITY_DRIFT')
if validation.get('ai_supplementation_policy')!='SAME_WORD_CONTEXT_AND_EXISTING_CANONICAL_SYSTEM_RELATIONSHIPS_ONLY':
    errors.append('AI_SUPPLEMENTATION_POLICY_DRIFT')
if validation.get('generated_content_may_become_second_source_authority') is not False:
    errors.append('AI_SECOND_AUTHORITY_FORBIDDEN_FLAG_DRIFT')
if validation.get('product_stage_execution_governance_binding')!='EXACT_CURRENT_VALIDATED_GOVERNANCE_SNAPSHOT':
    errors.append('PRODUCT_STAGE_CURRENT_GOVERNANCE_BINDING_DRIFT')

expected_workflows={
    'Current Governance Stage Internal Validation':('.github/workflows/current-governance-stage-internal-validation.yml','push'),
    'Mother Spec Neutrality Audit':('.github/workflows/mother-spec-neutrality-audit.yml','push'),
}
if set(validation.get('required_workflow_names') or [])!=set(expected_workflows):
    errors.append('CURRENT_REQUIRED_WORKFLOW_DENOMINATOR_DRIFT')
bindings=validation.get('required_workflow_bindings') or {}
for name,(path,event) in expected_workflows.items():
    row=bindings.get(name) or {}
    if row.get('path')!=path or row.get('event')!=event:
        errors.append('CURRENT_REQUIRED_WORKFLOW_BINDING_DRIFT:'+name)
    if not (ROOT/path).is_file():
        errors.append('CURRENT_REQUIRED_WORKFLOW_FILE_MISSING:'+path)

if (ROOT/'.github/workflows/current-governance-cleanup-validation.yml').exists():
    errors.append('LEGACY_CLEANUP_PROMOTION_WORKFLOW_PRESENT')
if (ROOT/'governance/ci/governance_promotion_transaction.py').exists():
    errors.append('LEGACY_PROMOTION_TRANSACTION_PRESENT')
if (ROOT/'governance/ci/validate_governance_candidate_promotion_readiness.py').exists():
    errors.append('LEGACY_PROMOTION_READINESS_VALIDATOR_PRESENT')

manifest=yaml.safe_load((ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml').read_text(encoding='utf-8')) or {}
if manifest.get('normative_status')!='ACTIVE_CURRENT_GOVERNANCE':
    errors.append('CURRENT_SPECIFICATION_MANIFEST_STATUS_DRIFT')
if manifest.get('branch_release_state')!='CURRENT_EXACT_HEAD_VALIDATION':
    errors.append('CURRENT_SPECIFICATION_VALIDATION_STATE_DRIFT')
if manifest.get('current_governance_identity_source')!='governance/specifications/REGISTRY.yaml':
    errors.append('SPECIFICATION_MANIFEST_IDENTITY_SOURCE_DRIFT')
if manifest.get('artifact_uid')!=identity.get('governance_uid'):
    errors.append('SPECIFICATION_MANIFEST_GOVERNANCE_UID_DRIFT')
if manifest.get('display_version')!=identity.get('display_version'):
    errors.append('SPECIFICATION_MANIFEST_DISPLAY_VERSION_DRIFT')
if manifest.get('released_current_authority') is not False:
    errors.append('RELEASED_AUTHORITY_MODEL_REINTRODUCED')

# Active Stage validation workflows must be internal and must not call removed promotion/auditor machinery.
active_paths=[
    '.github/workflows/current-governance-stage-internal-validation.yml',
    '.github/workflows/mother-spec-neutrality-audit.yml',
    '.github/workflows/common-stage-execution-engine.yml',
]
for rel in active_paths:
    p=ROOT/rel
    if not p.is_file():
        errors.append('ACTIVE_WORKFLOW_MISSING:'+rel)
        continue
    text=p.read_text(encoding='utf-8')
    for forbidden in (
        'governance_promotion_transaction.py',
        'validate_governance_candidate_promotion_readiness.py',
        'GOVERNANCE_INDEPENDENT_AUDITOR_EVIDENCE_MANIFEST',
        'independent_auditor_provenance_actor_count',
        'PRODUCT_SELECTED_GOVERNANCE_RELEASE',
    ):
        if forbidden in text:
            errors.append('ACTIVE_WORKFLOW_LEGACY_EXTERNAL_GATE_REFERENCE:'+rel+':'+forbidden)
    for ref in re.findall(r'(?m)^\s*(?:-\s*)?uses:\s*([^\s#]+)',text):
        if ref.startswith('./'):
            continue
        if not re.fullmatch(r'[^@\s]+@[0-9a-fA-F]{40}',ref):
            errors.append('WORKFLOW_EXTERNAL_ACTION_MUTABLE_REF:'+rel+':'+ref)

binding_rel=str(reg.get('execution_environment_binding') or '')
if not binding_rel or not (ROOT/binding_rel).is_file():
    errors.append('CURRENT_EXECUTION_ENVIRONMENT_BINDING_MISSING')
else:
    binding=yaml.safe_load((ROOT/binding_rel).read_text(encoding='utf-8')) or {}
    if binding.get('artifact_type')!='EXECUTION_ENVIRONMENT_BINDING' or binding.get('normative_authority') is not False:
        errors.append('CURRENT_EXECUTION_ENVIRONMENT_BINDING_AUTHORITY_INVALID')
    if binding.get('common_stage_definition_credit')!=0 or binding.get('common_stage_completion_credit')!=0:
        errors.append('CURRENT_EXECUTION_ENVIRONMENT_BINDING_COMMON_STAGE_CREDIT_NONZERO')

if errors:
    print('BLOCK: GOVERNANCE_LAYOUT_INVALID')
    for e in errors:
        print(' - '+e)
    raise SystemExit(2)

print('PASS: Current Governance entrypoint/identity/workline resolved')
print('PASS: Word-derived internal validation model active')
print('PASS: legacy candidate/promotion/external-auditor gates absent from active Stage validation')
print('PASS: exact Current governance bundle and canonical rule registry bindings valid')
