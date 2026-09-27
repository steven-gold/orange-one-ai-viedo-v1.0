#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import re
import subprocess
import sys
import urllib.request
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
    governance_role=str(roles.get(governance_branch) or '')
    if governance_role not in {'IMMUTABLE_GOVERNANCE_RULESET','GOVERNANCE_REVISION_CANDIDATE'}:
        errors.append('CURRENT_REGISTRY_BRANCH_OR_ROLE_DRIFT')
    binding_rel=str(reg.get('execution_environment_binding') or '')
    if not binding_rel:
        errors.append('CURRENT_EXECUTION_ENVIRONMENT_BINDING_MISSING')
    else:
        binding_path=ROOT/binding_rel
        if not binding_path.is_file():
            errors.append('CURRENT_EXECUTION_ENVIRONMENT_BINDING_TARGET_MISSING')
        else:
            binding=yaml.safe_load(binding_path.read_text(encoding='utf-8')) or {}
            if binding.get('artifact_type')!='EXECUTION_ENVIRONMENT_BINDING' or binding.get('normative_authority') is not False:
                errors.append('CURRENT_EXECUTION_ENVIRONMENT_BINDING_AUTHORITY_INVALID')
            if binding.get('common_stage_definition_credit')!=0 or binding.get('common_stage_completion_credit')!=0:
                errors.append('CURRENT_EXECUTION_ENVIRONMENT_BINDING_COMMON_STAGE_CREDIT_NONZERO')
    if reg.get('rules_root')!='governance/specifications/current':
        errors.append('CURRENT_RULES_ROOT_DRIFT')
    identity=reg.get('governance_identity') or {}
    for key in ('governance_uid','governance_revision','display_version','identity_authority'):
        if not identity.get(key):
            errors.append('CURRENT_GOVERNANCE_IDENTITY_FIELD_MISSING:'+key)
    if identity.get('identity_authority')!='governance/specifications/REGISTRY.yaml':
        errors.append('CURRENT_GOVERNANCE_IDENTITY_AUTHORITY_DRIFT')
    for key in ('governance_uid','governance_revision','display_version','identity_authority'):
        if resolved.get(key)!=identity.get(key):
            errors.append('REGISTRY_RESOLVER_IDENTITY_DRIFT:'+key)
    if governance_role=='GOVERNANCE_REVISION_CANDIDATE':
        required=('predecessor_branch','predecessor_head_sha','predecessor_governance_revision','authorization_record_url','authorized_scope','specification_bundle_sha256','specification_bundle_digest_algorithm')
        for key in required:
            if identity.get(key) in (None,'',[]):
                errors.append('CANDIDATE_BOOTSTRAP_FIELD_MISSING:'+key)
        if identity.get('predecessor_branch')==governance_branch and (reg.get('mutation_policy') or {}).get('single_branch_consolidation_mode') is not True:
            errors.append('CANDIDATE_PREDECESSOR_BRANCH_COLLISION')
        if not str(identity.get('authorization_record_url') or '').startswith('https://github.com/'):
            errors.append('CANDIDATE_AUTHORIZATION_RECORD_NOT_PERSISTED_GITHUB_RECORD')
        if identity.get('identity_state')!='PROVISIONAL_EXACT_HEAD_AND_BUNDLE_DIGEST_BOUND':
            errors.append('CANDIDATE_IDENTITY_STATE_DRIFT')
        if identity.get('released_immutable_identity') is not False:
            errors.append('CANDIDATE_IDENTITY_PREMATURELY_RELEASED')
        if identity.get('immutable_release_identity_assigned_only_at_explicit_promotion') is not True:
            errors.append('CANDIDATE_IMMUTABLE_RELEASE_IDENTITY_TIMING_DRIFT')
        if identity.get('specification_bundle_digest_algorithm')!='SHA256_RELATIVE_PATH_NUL_BYTES_NUL_SORTED_V1':
            errors.append('CANDIDATE_SPECIFICATION_BUNDLE_DIGEST_ALGORITHM_DRIFT')
        if resolved.get('runtime_bundle_sha256')!=identity.get('specification_bundle_sha256'):
            errors.append('CANDIDATE_SPECIFICATION_BUNDLE_DIGEST_DRIFT')

def verify_candidate_authorization(reg, resolved):
    roles=reg.get('branch_role_contract') or {}
    branch=str(reg.get('branch') or '')
    if roles.get(branch)!='GOVERNANCE_REVISION_CANDIDATE':
        return
    identity=reg.get('governance_identity') or {}
    url=str(identity.get('authorization_record_url') or '')
    match=re.fullmatch(r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)',url)
    if not match:
        errors.append('CANDIDATE_AUTHORIZATION_URL_INVALID')
        return
    owner,repo_name,issue_number=match.groups()
    api=f'https://api.github.com/repos/{owner}/{repo_name}/issues/{issue_number}'
    headers={'Accept':'application/vnd.github+json','User-Agent':'Governance-Validator'}
    token=os.environ.get('GITHUB_TOKEN','').strip()
    if token:
        headers['Authorization']='Bearer '+token
    try:
        with urllib.request.urlopen(urllib.request.Request(api,headers=headers),timeout=20) as response:
            issue=json.loads(response.read().decode('utf-8'))
    except Exception as exc:
        errors.append('CANDIDATE_AUTHORIZATION_RECORD_UNVERIFIABLE:'+type(exc).__name__)
        return
    if str((issue.get('user') or {}).get('login') or '')!=owner:
        errors.append('CANDIDATE_AUTHORIZATION_ACTOR_MISMATCH')
    body=str(issue.get('body') or '')
    required_body=[
      'Predecessor immutable governance branch: '+str(identity.get('predecessor_branch') or ''),
      'Predecessor exact HEAD: '+str(identity.get('predecessor_head_sha') or ''),
      'Successor candidate branch: '+branch,
    ]+list(map(str,identity.get('authorized_scope') or []))
    for token_text in required_body:
        if token_text not in body:
            errors.append('CANDIDATE_AUTHORIZATION_SCOPE_OR_IDENTITY_MISSING:'+token_text)
    predecessor=str(identity.get('predecessor_head_sha') or '')
    single_mode=(reg.get('mutation_policy') or {}).get('single_branch_consolidation_mode') is True
    try:
        subprocess.check_call(['git','merge-base','--is-ancestor',predecessor,'HEAD'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if single_mode:
            first_time_text=subprocess.check_output(['git','show','-s','--format=%cI','HEAD'],cwd=ROOT,text=True).strip()
        else:
            commits=subprocess.check_output(['git','rev-list','--reverse',predecessor+'..HEAD'],cwd=ROOT,text=True).splitlines()
            if not commits:
                errors.append('CANDIDATE_MUTATION_COMMIT_SET_EMPTY')
                return
            first_time_text=subprocess.check_output(['git','show','-s','--format=%cI',commits[0].strip()],cwd=ROOT,text=True).strip()
    except Exception:
        errors.append('CANDIDATE_PREDECESSOR_ANCESTRY_UNVERIFIABLE')
        return
    try:
        first_time=datetime.fromisoformat(first_time_text.replace('Z','+00:00')).astimezone(timezone.utc)
        created=datetime.fromisoformat(str(issue.get('created_at') or '').replace('Z','+00:00')).astimezone(timezone.utc)
        updated=datetime.fromisoformat(str(issue.get('updated_at') or '').replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception:
        errors.append('CANDIDATE_AUTHORIZATION_TIMESTAMP_INVALID')
        return
    if not (created < first_time and updated < first_time):
        errors.append('CANDIDATE_AUTHORIZATION_NOT_PREEXISTING_CONSOLIDATION_OR_MUTATION')
    ref_name=os.environ.get('GITHUB_REF_NAME','').strip()
    if ref_name and ref_name!=branch:
        errors.append('CANDIDATE_REGISTRY_BRANCH_RUNTIME_REF_MISMATCH:'+ref_name+'!='+branch)

def verify_supplemental_authorizations(reg):
    if (reg.get('mutation_policy') or {}).get('single_branch_consolidation_mode') is True:
        return
    roles=reg.get('branch_role_contract') or {}
    branch=str(reg.get('branch') or '')
    if roles.get(branch)!='GOVERNANCE_REVISION_CANDIDATE':
        return
    identity=reg.get('governance_identity') or {}
    records=identity.get('supplemental_authorization_records') or []
    if not isinstance(records,list):
        errors.append('SUPPLEMENTAL_AUTHORIZATION_RECORDS_INVALID')
        return
    token=os.environ.get('GITHUB_TOKEN','').strip()
    headers={'Accept':'application/vnd.github+json','User-Agent':'Governance-Validator'}
    if token:
        headers['Authorization']='Bearer '+token
    for idx,record in enumerate(records):
        if not isinstance(record,dict):
            errors.append('SUPPLEMENTAL_AUTHORIZATION_RECORD_INVALID:'+str(idx)); continue
        url=str(record.get('record_url') or '')
        match=re.fullmatch(r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)',url)
        if not match:
            errors.append('SUPPLEMENTAL_AUTHORIZATION_URL_INVALID:'+str(idx)); continue
        owner,repo_name,issue_number=match.groups()
        try:
            with urllib.request.urlopen(urllib.request.Request(f'https://api.github.com/repos/{owner}/{repo_name}/issues/{issue_number}',headers=headers),timeout=20) as response:
                issue=json.loads(response.read().decode('utf-8'))
        except Exception as exc:
            errors.append('SUPPLEMENTAL_AUTHORIZATION_UNVERIFIABLE:'+str(idx)+':'+type(exc).__name__); continue
        if str((issue.get('user') or {}).get('login') or '')!=owner:
            errors.append('SUPPLEMENTAL_AUTHORIZATION_ACTOR_MISMATCH:'+str(idx))
        body=str(issue.get('body') or '')
        if str(record.get('candidate_branch') or '')!=branch:
            errors.append('SUPPLEMENTAL_AUTHORIZATION_BRANCH_DRIFT:'+str(idx))
        for scope in map(str,record.get('authorized_scope') or []):
            if scope not in body:
                errors.append('SUPPLEMENTAL_AUTHORIZATION_SCOPE_MISSING:'+str(idx)+':'+scope)
        base=str(record.get('authorization_base_head') or '')
        if len(base)!=40:
            errors.append('SUPPLEMENTAL_AUTHORIZATION_BASE_HEAD_INVALID:'+str(idx)); continue
        try:
            subprocess.check_call(['git','merge-base','--is-ancestor',base,'HEAD'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            commits=subprocess.check_output(['git','rev-list','--reverse',base+'..HEAD'],cwd=ROOT,text=True).splitlines()
            created=datetime.fromisoformat(str(issue.get('created_at') or '').replace('Z','+00:00')).astimezone(timezone.utc)
            updated=datetime.fromisoformat(str(issue.get('updated_at') or '').replace('Z','+00:00')).astimezone(timezone.utc)
        except Exception:
            errors.append('SUPPLEMENTAL_AUTHORIZATION_ANCESTRY_OR_TIME_INVALID:'+str(idx)); continue
        if not commits:
            errors.append('SUPPLEMENTAL_AUTHORIZATION_MUTATION_COMMIT_SET_EMPTY:'+str(idx)); continue
        first_time_text=subprocess.check_output(['git','show','-s','--format=%cI',commits[0]],cwd=ROOT,text=True).strip()
        first_time=datetime.fromisoformat(first_time_text.replace('Z','+00:00')).astimezone(timezone.utc)
        if not (created < first_time and updated < first_time):
            errors.append('SUPPLEMENTAL_AUTHORIZATION_NOT_PREEXISTING:'+str(idx))

registry_doc=yaml.safe_load(REGISTRY.read_text(encoding='utf-8')) or {}
_candidate_contract=registry_doc.get('candidate_validation_contract') or {}
if _candidate_contract.get('workflow_external_action_ref_mode')!='FULL_40_HEX_COMMIT_SHA_ONLY':
    errors.append('WORKFLOW_EXTERNAL_ACTION_REF_MODE_DRIFT')
if _candidate_contract.get('workflow_external_action_mutable_ref')!='BLOCK':
    errors.append('WORKFLOW_EXTERNAL_ACTION_MUTABLE_REF_FAIL_CLOSED_MISSING')
_action_paths=list(map(str,_candidate_contract.get('workflow_action_pinning_required_paths') or []))
if set(_action_paths)!={
    '.github/workflows/current-governance-cleanup-validation.yml',
    '.github/workflows/mother-spec-neutrality-audit.yml',
    '.github/workflows/common-stage-execution-engine.yml',
    '.github/workflows/source-package-successor-materialization.yml',
    '.github/workflows/source-package-successor-validation.yml',
}:
    errors.append('WORKFLOW_ACTION_PINNING_PATH_DENOMINATOR_DRIFT')
_action_ref_re=re.compile(r'^\s*(?:-\s*)?uses:\s*([^\s#]+)',re.M)
_full_sha_ref_re=re.compile(r'^[^@\s]+@[0-9a-fA-F]{40}$')
for _rel in _action_paths:
    _wf=ROOT/_rel
    if not _wf.is_file():
        errors.append('WORKFLOW_ACTION_PINNING_TARGET_MISSING:'+_rel)
        continue
    _text=_wf.read_text(encoding='utf-8')
    for _ref in _action_ref_re.findall(_text):
        if _ref.startswith('./'):
            continue
        if not _full_sha_ref_re.fullmatch(_ref):
            errors.append('WORKFLOW_EXTERNAL_ACTION_MUTABLE_REF:'+_rel+':'+_ref)

_runner=str(_candidate_contract.get('governance_ci_runner_label') or '')
_python=str(_candidate_contract.get('governance_ci_python_version') or '')
_lock=str(_candidate_contract.get('governance_ci_dependency_lock_path') or '')
_hash=str(_candidate_contract.get('governance_ci_pyyaml_sha256') or '')
if _runner!='ubuntu-24.04':
    errors.append('GOVERNANCE_CI_RUNNER_LABEL_DRIFT')
if _python!='3.11.16':
    errors.append('GOVERNANCE_CI_PYTHON_VERSION_DRIFT')
if _lock!='governance/ci/requirements-governance.lock':
    errors.append('GOVERNANCE_CI_DEPENDENCY_LOCK_PATH_DRIFT')
if _candidate_contract.get('governance_ci_dependency_install_mode')!='PIP_REQUIRE_HASHES':
    errors.append('GOVERNANCE_CI_DEPENDENCY_INSTALL_MODE_DRIFT')
if _candidate_contract.get('governance_ci_pyyaml_version')!='6.0.2' or _hash!='3ad2a3decf9aaba3d29c8f537ac4b243e36bef957511b4766cb0057d32b0be85':
    errors.append('GOVERNANCE_CI_DEPENDENCY_IDENTITY_DRIFT')
_lock_path=ROOT/_lock
if not _lock_path.is_file():
    errors.append('GOVERNANCE_CI_DEPENDENCY_LOCK_MISSING')
else:
    _lock_text=_lock_path.read_text(encoding='utf-8')
    if 'PyYAML==6.0.2 --hash=sha256:'+_hash not in _lock_text:
        errors.append('GOVERNANCE_CI_DEPENDENCY_LOCK_CONTENT_DRIFT')
for _rel in _action_paths:
    _wf=ROOT/_rel
    if not _wf.is_file():
        continue
    _text=_wf.read_text(encoding='utf-8')
    if 'runs-on: '+_runner not in _text:
        errors.append('GOVERNANCE_CI_RUNNER_NOT_LOCKED:'+_rel)
    if "python-version: '"+_python+"'" not in _text:
        errors.append('GOVERNANCE_CI_PYTHON_NOT_LOCKED:'+_rel)
    if '--require-hashes -r '+_lock not in _text:
        errors.append('GOVERNANCE_CI_DEPENDENCY_HASH_LOCK_NOT_USED:'+_rel)

# Single-branch workflow write-surface invariants.
_common_rel='.github/workflows/common-stage-execution-engine.yml'
_materialize_rel='.github/workflows/source-package-successor-materialization.yml'
_common_text=(ROOT/_common_rel).read_text(encoding='utf-8') if (ROOT/_common_rel).is_file() else ''
_materialize_text=(ROOT/_materialize_rel).read_text(encoding='utf-8') if (ROOT/_materialize_rel).is_file() else ''
if _candidate_contract.get('common_stage_workflow_contents_permission')!='read':
    errors.append('COMMON_STAGE_WORKFLOW_PERMISSION_CONTRACT_DRIFT')
if re.search(r'(?m)^\s*contents:\s*write\s*$',_common_text):
    errors.append('COMMON_STAGE_WORKFLOW_WRITE_PERMISSION_FORBIDDEN')
if not re.search(r'(?m)^\s*contents:\s*read\s*$',_common_text):
    errors.append('COMMON_STAGE_WORKFLOW_READ_PERMISSION_MISSING')
for _key in (
    'source_materialization_workflow_candidate_only',
    'source_materialization_workflow_dispatch_ref_must_equal_active_governance_branch',
    'source_materialization_workflow_remote_head_cas_required',
    'source_materialization_workflow_forbidden_when_released',
):
    if _candidate_contract.get(_key) is not True:
        errors.append('SOURCE_MATERIALIZATION_GUARD_CONTRACT_DRIFT:'+_key)
if _candidate_contract.get('source_materialization_workflow_contents_permission')!='write':
    errors.append('SOURCE_MATERIALIZATION_PERMISSION_CONTRACT_DRIFT')
if _candidate_contract.get('source_materialization_workflow_actions_permission')!='none':
    errors.append('SOURCE_MATERIALIZATION_ACTIONS_PERMISSION_CONTRACT_DRIFT')
if _candidate_contract.get('source_materialization_validation_trigger_mode')!='PUSH_EVENT_ONLY':
    errors.append('SOURCE_MATERIALIZATION_VALIDATION_TRIGGER_MODE_DRIFT')
if not re.search(r'(?m)^\s*contents:\s*write\s*$',_materialize_text):
    errors.append('SOURCE_MATERIALIZATION_WRITE_PERMISSION_MISSING')
if re.search(r'(?m)^\s*actions:\s*write\s*$',_materialize_text):
    errors.append('SOURCE_MATERIALIZATION_ACTIONS_WRITE_PERMISSION_FORBIDDEN')
if 'gh workflow run' in _materialize_text:
    errors.append('SOURCE_MATERIALIZATION_DUPLICATE_MANUAL_VALIDATION_TRIGGER_FORBIDDEN')
_active_branch=str(registry_doc.get('branch') or '')
_guard_tokens=(
    "github.ref_name == '"+_active_branch+"'",
    "roles.get(branch)!='GOVERNANCE_REVISION_CANDIDATE'",
    "d.get('status')!='ACTIVE_SINGLE_BRANCH_VALIDATION'",
    "mutation.get('single_active_governance_branch')!='"+_active_branch+"'",
    "contract.get('source_package_integration_mode')!='SINGLE_BRANCH_INTEGRATED'",
    'REMOTE_HEAD="$(git ls-remote origin refs/heads/'+_active_branch,
    'REMOTE_HEAD_BEFORE_PUSH="$(git ls-remote origin refs/heads/'+_active_branch,
    'test "$REMOTE_HEAD" = "$BASE_HEAD"',
    'test "$REMOTE_HEAD_BEFORE_PUSH" = "$BASE_HEAD"',
    'git push origin HEAD:'+_active_branch,
)
for _tok in _guard_tokens:
    if _tok not in _materialize_text:
        errors.append('SOURCE_MATERIALIZATION_WRITE_GUARD_MISSING:'+_tok)

manifest=yaml.safe_load((ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml').read_text(encoding='utf-8')) or {}
if manifest.get('current_governance_identity_source')!='governance/specifications/REGISTRY.yaml':
    errors.append('SPECIFICATION_MANIFEST_IDENTITY_SOURCE_DRIFT')
if manifest.get('artifact_uid_may_select_current_governance') is not False:
    errors.append('SPECIFICATION_MANIFEST_ARTIFACT_UID_CURRENT_AUTHORITY_LEAK')
if manifest.get('display_version_may_select_current_governance') is not False:
    errors.append('SPECIFICATION_MANIFEST_DISPLAY_VERSION_CURRENT_AUTHORITY_LEAK')
if (reg.get('branch_role_contract') or {}).get(str(reg.get('branch') or ''))=='GOVERNANCE_REVISION_CANDIDATE':
    if manifest.get('branch_release_state')!='CANDIDATE_NOT_PROMOTED':
        errors.append('CANDIDATE_RULE_BUNDLE_RELEASE_STATE_DRIFT')
    if manifest.get('released_current_authority') is not False:
        errors.append('CANDIDATE_RULE_BUNDLE_RELEASED_AUTHORITY_LEAK')
    if manifest.get('release_state_authority')!='governance/specifications/REGISTRY.yaml':
        errors.append('CANDIDATE_RULE_BUNDLE_RELEASE_STATE_AUTHORITY_DRIFT')
    if resolved.get('governance_release_state')!='CANDIDATE_NOT_PROMOTED' or resolved.get('released_current_authority') is not False:
        errors.append('CANDIDATE_RESOLVER_RELEASE_STATE_DRIFT')
    identity=reg.get('governance_identity') or {}
    if manifest.get('artifact_uid')!=identity.get('governance_uid'):
        errors.append('CANDIDATE_MANIFEST_GOVERNANCE_UID_PROJECTION_DRIFT')
    if manifest.get('display_version')!=identity.get('display_version'):
        errors.append('CANDIDATE_MANIFEST_DISPLAY_VERSION_PROJECTION_DRIFT')
    lineage=manifest.get('source_lineage') or {}
    if lineage.get('promotion_authorization_ref')!=identity.get('authorization_record_url'):
        errors.append('CANDIDATE_MANIFEST_AUTHORIZATION_PROJECTION_DRIFT')
    if lineage.get('candidate_predecessor_head_sha')!=identity.get('predecessor_head_sha'):
        errors.append('CANDIDATE_MANIFEST_PREDECESSOR_HEAD_PROJECTION_DRIFT')
    if lineage.get('source_bytes_changed_by_this_successor') is not False or lineage.get('source_identity_reused_only_because_source_bytes_are_unchanged') is not True:
        errors.append('CANDIDATE_MANIFEST_SOURCE_LINEAGE_DRIFT')
    vc=reg.get('candidate_validation_contract') or {}
    if vc.get('candidate_manifest_projection_must_match_registry_identity') is not True:
        errors.append('CANDIDATE_MANIFEST_PROJECTION_BINDING_NOT_REQUIRED')
    if vc.get('candidate_manifest_artifact_uid_expected')!=identity.get('governance_uid') or vc.get('candidate_manifest_display_version_expected')!=identity.get('display_version'):
        errors.append('CANDIDATE_MANIFEST_EXPECTED_IDENTITY_DRIFT')
    if vc.get('candidate_identity_binding_mode')!='PROVISIONAL_EXACT_HEAD_AND_BUNDLE_DIGEST_BOUND':
        errors.append('CANDIDATE_IDENTITY_BINDING_MODE_DRIFT')
    if vc.get('candidate_identity_may_be_reported_as_released_immutable') is not False:
        errors.append('CANDIDATE_RELEASED_IDENTITY_OVERCLAIM_NOT_BLOCKED')
    if vc.get('immutable_release_identity_must_be_assigned_during_explicit_promotion') is not True:
        errors.append('CANDIDATE_EXPLICIT_PROMOTION_RELEASE_IDENTITY_NOT_REQUIRED')
    if vc.get('specification_bundle_digest_algorithm')!=identity.get('specification_bundle_digest_algorithm') or vc.get('specification_bundle_sha256')!=identity.get('specification_bundle_sha256'):
        errors.append('CANDIDATE_VALIDATION_BUNDLE_DIGEST_PROJECTION_DRIFT')

verify_candidate_authorization(reg,resolved)
verify_supplemental_authorizations(reg)

try:
    import stage_execution_engine as _stage_engine
    _stage_identity=_stage_engine.identity()[2]
    if _stage_identity!=resolved.get('governance_uid'):
        errors.append('STAGE_ENGINE_CURRENT_GOVERNANCE_IDENTITY_DRIFT')
    import audit_closure_engine as _audit_engine
    _audit_receipt=_audit_engine.run_closure(_audit_engine.load_context())
    for _key in ('governance_uid','governance_revision','display_version'):
        if _audit_receipt.get(_key)!=resolved.get(_key):
            errors.append('AUDIT_ENGINE_CURRENT_GOVERNANCE_IDENTITY_DRIFT:'+_key)
except Exception as exc:
    errors.append('CURRENT_IDENTITY_CONSUMER_RUNTIME_VALIDATION_FAILED:'+type(exc).__name__+':'+str(exc))

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
    'governance/ci/governance_resolver.py',
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

print('PASS: REGISTRY.yaml is the single Current governance identity and rule entrypoint')
print('PASS: resolver identity equals Registry identity for governance_uid/revision/display_version')
print('PASS: successor candidate bootstrap binds predecessor and pre-existing authorization record')
print('PASS: governance/specifications/current is the only Current rule root')
print('PASS: governance branch contains no product run-state/test-state root')
print('PASS: runtime specification digest='+resolved['runtime_bundle_sha256'])
