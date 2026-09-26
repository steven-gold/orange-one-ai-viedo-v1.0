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
    product_branch=str(reg.get('product_execution_branch') or '')
    if not product_branch or roles.get(product_branch)!='PRODUCT_EXECUTION_WORKLINE':
        errors.append('CURRENT_PRODUCT_EXECUTION_BRANCH_OR_ROLE_DRIFT')
    if governance_branch==product_branch:
        errors.append('CURRENT_GOVERNANCE_PRODUCT_BRANCH_COLLISION')
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
        required=('predecessor_branch','predecessor_head_sha','predecessor_governance_revision','authorization_record_url','authorized_scope')
        for key in required:
            if identity.get(key) in (None,'',[]):
                errors.append('CANDIDATE_BOOTSTRAP_FIELD_MISSING:'+key)
        if identity.get('predecessor_branch')==governance_branch:
            errors.append('CANDIDATE_PREDECESSOR_BRANCH_COLLISION')
        if not str(identity.get('authorization_record_url') or '').startswith('https://github.com/'):
            errors.append('CANDIDATE_AUTHORIZATION_RECORD_NOT_PERSISTED_GITHUB_RECORD')

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
    headers={'Accept':'application/vnd.github+json','User-Agent':'ACPOS-Governance-Validator'}
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
    try:
        subprocess.check_call(['git','merge-base','--is-ancestor',predecessor,'HEAD'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        commits=subprocess.check_output(['git','rev-list','--reverse',predecessor+'..HEAD'],cwd=ROOT,text=True).splitlines()
    except Exception:
        errors.append('CANDIDATE_PREDECESSOR_ANCESTRY_UNVERIFIABLE')
        return
    if not commits:
        errors.append('CANDIDATE_MUTATION_COMMIT_SET_EMPTY')
        return
    first_commit=commits[0].strip()
    first_time_text=subprocess.check_output(['git','show','-s','--format=%cI',first_commit],cwd=ROOT,text=True).strip()
    try:
        first_time=datetime.fromisoformat(first_time_text.replace('Z','+00:00')).astimezone(timezone.utc)
        created=datetime.fromisoformat(str(issue.get('created_at') or '').replace('Z','+00:00')).astimezone(timezone.utc)
        updated=datetime.fromisoformat(str(issue.get('updated_at') or '').replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception:
        errors.append('CANDIDATE_AUTHORIZATION_TIMESTAMP_INVALID')
        return
    if not (created < first_time and updated < first_time):
        errors.append('CANDIDATE_AUTHORIZATION_NOT_IMMUTABLY_PREEXISTING')
    ref_name=os.environ.get('GITHUB_REF_NAME','').strip()
    if ref_name and ref_name!=branch:
        errors.append('CANDIDATE_REGISTRY_BRANCH_RUNTIME_REF_MISMATCH:'+ref_name+'!='+branch)

manifest=yaml.safe_load((ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml').read_text(encoding='utf-8')) or {}
if manifest.get('current_governance_identity_source')!='governance/specifications/REGISTRY.yaml':
    errors.append('SPECIFICATION_MANIFEST_IDENTITY_SOURCE_DRIFT')
if manifest.get('artifact_uid_may_select_current_governance') is not False:
    errors.append('SPECIFICATION_MANIFEST_ARTIFACT_UID_CURRENT_AUTHORITY_LEAK')
if manifest.get('display_version_may_select_current_governance') is not False:
    errors.append('SPECIFICATION_MANIFEST_DISPLAY_VERSION_CURRENT_AUTHORITY_LEAK')

verify_candidate_authorization(reg,resolved)

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
