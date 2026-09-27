#!/usr/bin/env python3
from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]


def load_yaml(path:Path)->dict:
    value=yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(value,dict):
        raise RuntimeError('MAPPING_REQUIRED:'+str(path))
    return value


def _headers(token:str|None)->dict:
    headers={'Accept':'application/vnd.github+json','User-Agent':'ACPOS-Source-Successor-Admission'}
    if token:
        headers['Authorization']='Bearer '+token
    return headers


def _api_json(url:str,token:str|None)->dict:
    with urllib.request.urlopen(urllib.request.Request(url,headers=_headers(token)),timeout=30) as response:
        value=json.loads(response.read().decode('utf-8'))
    if not isinstance(value,dict):
        raise RuntimeError('GITHUB_API_MAPPING_REQUIRED')
    return value


def fetch_live_head(repository:str,branch:str,token:str|None)->str:
    payload=_api_json(
      f'https://api.github.com/repos/{repository}/branches/{urllib.parse.quote(branch,safe="")}',
      token
    )
    head=str(((payload.get('commit') or {}).get('sha')) or '')
    if len(head)!=40:
        raise RuntimeError('SOURCE_LIVE_BRANCH_HEAD_INVALID')
    return head


def fetch_runs(repository:str,branch:str,head_sha:str,token:str|None)->list[dict]:
    query=urllib.parse.urlencode({'branch':branch,'head_sha':head_sha,'per_page':100})
    payload=_api_json(f'https://api.github.com/repos/{repository}/actions/runs?{query}',token)
    runs=payload.get('workflow_runs') or []
    if not isinstance(runs,list):
        raise RuntimeError('SOURCE_WORKFLOW_RUN_LIST_INVALID')
    return runs


def fetch_compare_mutation_actors(repository:str,base_sha:str,head_sha:str,token:str|None)->set[str]:
    if len(base_sha)!=40 or len(head_sha)!=40:
        raise RuntimeError('SOURCE_MUTATION_RANGE_SHA_INVALID')
    url=f'https://api.github.com/repos/{repository}/compare/{base_sha}...{head_sha}?per_page=100'
    payload=_api_json(url,token)
    commits=payload.get('commits') or []
    if not isinstance(commits,list):
        raise RuntimeError('SOURCE_MUTATION_COMMIT_LIST_INVALID')
    actors=set()
    for commit in commits:
        if not isinstance(commit,dict):
            continue
        for key in ('author','committer'):
            login=str(((commit.get(key) or {}).get('login')) or '').strip()
            if login:
                actors.add(login)
    if not commits:
        raise RuntimeError('SOURCE_MUTATION_COMMIT_SET_EMPTY')
    return actors


def fetch_commit_tree_and_actor(repository:str,commit_sha:str,token:str|None)->tuple[str,str]:
    payload=_api_json(f'https://api.github.com/repos/{repository}/commits/{commit_sha}',token)
    tree_sha=str((((payload.get('commit') or {}).get('tree') or {}).get('sha')) or '')
    actor=str(((payload.get('author') or {}).get('login')) or ((payload.get('committer') or {}).get('login')) or '').strip()
    if not tree_sha or not actor:
        raise RuntimeError('COMMIT_TREE_OR_ACTOR_UNRESOLVED')
    return tree_sha,actor


def fetch_github_blob_receipt(ref:str,token:str|None)->tuple[dict,str,str]:
    match=re.fullmatch(r'https://github\.com/([^/]+)/([^/]+)/blob/([0-9a-fA-F]{40})/(.+)',str(ref or ''))
    if not match:
        raise RuntimeError('EXTERNAL_TRUST_RECEIPT_MUST_BE_COMMIT_PINNED_GITHUB_BLOB')
    owner,repo_name,commit_sha,path=match.groups()
    repository=f'{owner}/{repo_name}'
    quoted=urllib.parse.quote(path,safe='/')
    query=urllib.parse.urlencode({'ref':commit_sha})
    payload=_api_json(f'https://api.github.com/repos/{repository}/contents/{quoted}?{query}',token)
    encoded=str(payload.get('content') or '').replace('\n','')
    if not encoded:
        raise RuntimeError('EXTERNAL_TRUST_RECEIPT_CONTENT_MISSING')
    raw=base64.b64decode(encoded).decode('utf-8')
    try:
        doc=yaml.safe_load(raw) or {}
    except Exception as exc:
        raise RuntimeError('EXTERNAL_TRUST_RECEIPT_PARSE_FAILED:'+type(exc).__name__)
    if not isinstance(doc,dict):
        raise RuntimeError('EXTERNAL_TRUST_RECEIPT_MAPPING_REQUIRED')
    _tree,actor=fetch_commit_tree_and_actor(repository,commit_sha,token)
    return doc,actor,commit_sha


def fetch_github_issue(ref:str,token:str|None)->dict:
    match=re.fullmatch(r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)',str(ref or ''))
    if not match:
        raise RuntimeError('SIGNER_AUTHORITY_REF_MUST_BE_GITHUB_ISSUE')
    owner,repo_name,number=match.groups()
    return _api_json(f'https://api.github.com/repos/{owner}/{repo_name}/issues/{number}',token)


def verify_external_trust(
    repository:str,
    token:str|None,
    source_manifest:dict,
    receipt:dict,
    source_head_sha:str,
    source_tree_sha:str,
    mutation_actors:set[str],
)->dict:
    receipt_ref=str(receipt.get('external_trust_evidence_ref') or '').strip()
    failures=[]
    if not receipt_ref:
        return {'status':'NOT_VERIFIED','failures':['SOURCE_EXTERNAL_TRUST_EVIDENCE_REF_MISSING']}
    try:
        trust_doc,commit_actor,trust_commit_sha=fetch_github_blob_receipt(receipt_ref,token)
    except Exception as exc:
        return {'status':'NOT_VERIFIED','failures':['SOURCE_EXTERNAL_TRUST_RECEIPT_UNVERIFIABLE:'+type(exc).__name__+':'+str(exc)]}

    signer=str(trust_doc.get('signer_identity') or '').strip()
    authority_ref=str(trust_doc.get('signer_authority_ref') or '').strip()
    if signer!=commit_actor:
        failures.append('SOURCE_EXTERNAL_TRUST_SIGNER_COMMIT_ACTOR_MISMATCH')
    if signer in mutation_actors or commit_actor in mutation_actors:
        failures.append('SOURCE_EXTERNAL_TRUST_SELF_SIGN_OR_MUTATION_ACTOR_COLLISION')

    required=(
      'artifact_type','status','signer_identity','signer_authority_ref','source_package_identity',
      'source_package_head_sha','source_package_content_hash','predecessor_trust_identity',
      'signed_at','signature_or_immutable_receipt_ref'
    )
    missing=[key for key in required if trust_doc.get(key) in (None,'',[])]
    if missing:
        failures.append('SOURCE_EXTERNAL_TRUST_RECEIPT_FIELD_MISSING:'+','.join(missing))

    expected_identity=str(source_manifest.get('artifact_uid') or '')
    expected_content_hash='git-tree-sha1:'+source_tree_sha
    expected_predecessor=str(source_manifest.get('predecessor_root_manifest_uid') or '')+'@'+str(source_manifest.get('predecessor_governance_head') or '')
    expected={
      'artifact_type':'GOVERNANCE_SOURCE_EXTERNAL_TRUST_RECEIPT',
      'status':'SIGNED_PASS',
      'signer_identity':signer,
      'signer_authority_ref':authority_ref,
      'source_package_identity':expected_identity,
      'source_package_head_sha':source_head_sha,
      'source_package_content_hash':expected_content_hash,
      'predecessor_trust_identity':expected_predecessor,
      'signature_or_immutable_receipt_ref':receipt_ref,
    }
    for key,value in expected.items():
        if str(trust_doc.get(key) or '')!=str(value):
            failures.append('SOURCE_EXTERNAL_TRUST_RECEIPT_BINDING_MISMATCH:'+key)

    # Authority must come from the same explicit governance authority actor that authorized
    # the source-successor scope, and must pre-exist signing.
    try:
        source_auth=fetch_github_issue(str(source_manifest.get('authorization_record') or ''),token)
        source_auth_actor=str(((source_auth.get('user') or {}).get('login')) or '')
        signer_auth=fetch_github_issue(authority_ref,token)
        signer_auth_actor=str(((signer_auth.get('user') or {}).get('login')) or '')
        authority_body=str(signer_auth.get('body') or '')
        if not source_auth_actor or signer_auth_actor!=source_auth_actor:
            failures.append('SOURCE_EXTERNAL_TRUST_AUTHORITY_ACTOR_MISMATCH')
        if signer not in authority_body or expected_identity not in authority_body or source_head_sha not in authority_body or expected_content_hash not in authority_body:
            failures.append('SOURCE_EXTERNAL_TRUST_AUTHORITY_SCOPE_MISSING')
        trust_commit=_api_json(
          'https://api.github.com/repos/'+receipt_ref.split('/')[3]+'/'+receipt_ref.split('/')[4]+'/commits/'+trust_commit_sha,
          token
        )
        signed_commit_time=str(((trust_commit.get('commit') or {}).get('committer') or {}).get('date') or '')
        authority_created=str(signer_auth.get('created_at') or '')
        authority_updated=str(signer_auth.get('updated_at') or '')
        signed_at=str(trust_doc.get('signed_at') or '')
        auth_created_dt=datetime.fromisoformat(authority_created.replace('Z','+00:00')).astimezone(timezone.utc)
        auth_updated_dt=datetime.fromisoformat(authority_updated.replace('Z','+00:00')).astimezone(timezone.utc)
        signed_dt=datetime.fromisoformat(signed_at.replace('Z','+00:00')).astimezone(timezone.utc)
        commit_dt=datetime.fromisoformat(signed_commit_time.replace('Z','+00:00')).astimezone(timezone.utc)
        if not (auth_created_dt < signed_dt <= commit_dt and auth_updated_dt < signed_dt):
            failures.append('SOURCE_EXTERNAL_TRUST_TEMPORAL_ORDER_INVALID')
    except Exception as exc:
        failures.append('SOURCE_EXTERNAL_TRUST_AUTHORITY_UNVERIFIABLE:'+type(exc).__name__+':'+str(exc))

    return {
      'status':'PASS' if not failures else 'NOT_VERIFIED',
      'signer_identity':signer,
      'trust_commit_sha':trust_commit_sha,
      'source_package_content_hash':expected_content_hash,
      'source_package_head_sha':source_head_sha,
      'mutation_actor_count':len(mutation_actors),
      'failures':failures,
    }


def fetch_source_manifest(repository:str,path:str,head_sha:str,token:str|None)->tuple[str,dict]:
    quoted=urllib.parse.quote(path,safe='/')
    query=urllib.parse.urlencode({'ref':head_sha})
    payload=_api_json(f'https://api.github.com/repos/{repository}/contents/{quoted}?{query}',token)
    blob_sha=str(payload.get('sha') or '')
    encoded=str(payload.get('content') or '').replace('\n','')
    if not blob_sha or not encoded:
        raise RuntimeError('SOURCE_CANDIDATE_MANIFEST_CONTENT_MISSING')
    raw=base64.b64decode(encoded).decode('utf-8')
    doc=yaml.safe_load(raw) or {}
    if not isinstance(doc,dict):
        raise RuntimeError('SOURCE_CANDIDATE_MANIFEST_MAPPING_REQUIRED')
    return blob_sha,doc


def evaluate_snapshot(receipt:dict,source_manifest:dict,manifest_blob_sha:str,run:dict,live_before:str,live_after:str,require_external_trust:bool,external_trust_verification:dict|None=None)->dict:
    failures=[]
    expected_head=str(receipt.get('source_head_sha') or '')
    expected_branch=str(receipt.get('candidate_source_branch') or '')
    if not expected_branch:
        failures.append('SOURCE_RECEIPT_BRANCH_MISSING')
    if len(expected_head)!=40:
        failures.append('SOURCE_RECEIPT_HEAD_INVALID')
    if live_before!=expected_head or live_after!=expected_head or live_before!=live_after:
        failures.append('SOURCE_SUCCESSOR_LIVE_HEAD_DRIFT')
    if str(run.get('head_sha') or '')!=expected_head:
        failures.append('SOURCE_VALIDATION_RUN_HEAD_DRIFT')
    if str(run.get('name') or '')!=str(receipt.get('source_validation_workflow_name') or ''):
        failures.append('SOURCE_VALIDATION_WORKFLOW_DRIFT')
    if int(run.get('id') or 0)!=int(receipt.get('source_validation_run_id') or 0):
        failures.append('SOURCE_VALIDATION_RUN_ID_DRIFT')
    if str(run.get('status') or '')!='completed' or str(run.get('conclusion') or '')!='success':
        failures.append('SOURCE_VALIDATION_NOT_TERMINAL_SUCCESS')
    if str(receipt.get('source_validation_status') or '')!='completed' or str(receipt.get('source_validation_conclusion') or '')!='success':
        failures.append('SOURCE_RECEIPT_VALIDATION_RESULT_DRIFT')
    if manifest_blob_sha!=str(receipt.get('source_candidate_manifest_blob_sha') or ''):
        failures.append('SOURCE_MANIFEST_BLOB_DRIFT')
    if source_manifest.get('current_authority') is not False or receipt.get('released_current_authority') is not False:
        failures.append('UNPROMOTED_SOURCE_CURRENT_AUTHORITY_LEAK')

    source_status=str(source_manifest.get('status') or '')
    trust=source_manifest.get('external_trust') or {}
    manifest_trust=str(trust.get('status') or '')
    receipt_trust=str(receipt.get('external_trust_status') or '')
    if source_status!='UNSIGNED_NOT_CURRENT' or manifest_trust!='NOT_SIGNED':
        failures.append('SOURCE_PACKAGE_SELF_DECLARED_EXTERNAL_TRUST_FORBIDDEN')
    if trust.get('candidate_self_sign')!='FORBIDDEN':
        failures.append('SOURCE_PACKAGE_SELF_SIGN_POLICY_DRIFT')

    internal_ok=(
      str(receipt.get('source_internal_status') or '') in {'PASS_INTERNAL_UNSIGNED','PASS_INTERNAL_SIGNED'}
      and not any(x in failures for x in (
        'SOURCE_SUCCESSOR_LIVE_HEAD_DRIFT','SOURCE_VALIDATION_RUN_HEAD_DRIFT',
        'SOURCE_VALIDATION_WORKFLOW_DRIFT','SOURCE_VALIDATION_RUN_ID_DRIFT',
        'SOURCE_VALIDATION_NOT_TERMINAL_SUCCESS','SOURCE_RECEIPT_VALIDATION_RESULT_DRIFT',
        'SOURCE_MANIFEST_BLOB_DRIFT'
      ))
    )
    if not internal_ok:
        failures.append('SOURCE_INTERNAL_EXACT_HEAD_VALIDATION_NOT_PROVEN')

    external_check=external_trust_verification or {'status':'NOT_VERIFIED','failures':['SOURCE_EXTERNAL_TRUST_MACHINE_VERIFICATION_NOT_PERFORMED']}
    external_ready=(
      source_status=='UNSIGNED_NOT_CURRENT'
      and manifest_trust=='NOT_SIGNED'
      and receipt_trust=='SIGNED_PASS'
      and bool(str(receipt.get('external_trust_evidence_ref') or '').strip())
      and external_check.get('status')=='PASS'
    )
    if require_external_trust and not external_ready:
        failures.append('SOURCE_INDEPENDENT_EXTERNAL_TRUST_NOT_PROVEN')
        failures.extend([x for x in (external_check.get('failures') or []) if x not in failures])

    return {
      'status':'PASS' if not failures else ('PASS_INTERNAL_UNSIGNED' if internal_ok and not require_external_trust and manifest_trust=='NOT_SIGNED' else 'BLOCKED'),
      'internal_exact_head_validation': 'PASS' if internal_ok else 'BLOCKED',
      'external_trust_validation': 'PASS' if external_ready else 'NOT_VERIFIED',
      'source_branch':expected_branch,
      'source_head_sha':expected_head,
      'source_status':source_status,
      'source_self_trust_status':manifest_trust,
      'external_trust_status':receipt_trust,
      'external_trust_machine_verification':external_check,
      'source_validation_run_id':run.get('id'),
      'failures':failures,
      'promotion_credit':0 if not external_ready else 1,
    }


def validate_source_successor(repository:str,token:str|None,contract:dict,require_external_trust:bool=False)->dict:
    receipt_rel=str(contract.get('source_package_successor_admission_receipt') or '')
    if not receipt_rel:
        return {'status':'BLOCKED','failures':['SOURCE_ADMISSION_RECEIPT_CONTRACT_MISSING']}
    receipt_path=ROOT/receipt_rel
    if not receipt_path.is_file():
        return {'status':'BLOCKED','failures':['SOURCE_ADMISSION_RECEIPT_MISSING:'+receipt_rel]}
    receipt=load_yaml(receipt_path)
    branch=str(contract.get('source_package_successor_branch') or '')
    workflow=str(contract.get('source_package_successor_workflow_name') or '')
    manifest_path=str(contract.get('source_package_successor_manifest_path') or '')
    if receipt.get('candidate_source_branch')!=branch:
        return {'status':'BLOCKED','failures':['SOURCE_RECEIPT_BRANCH_CONTRACT_DRIFT']}
    if receipt.get('source_validation_workflow_name')!=workflow:
        return {'status':'BLOCKED','failures':['SOURCE_RECEIPT_WORKFLOW_CONTRACT_DRIFT']}
    if receipt.get('source_candidate_manifest_path')!=manifest_path:
        return {'status':'BLOCKED','failures':['SOURCE_RECEIPT_MANIFEST_PATH_DRIFT']}

    live_before=fetch_live_head(repository,branch,token)
    runs=fetch_runs(repository,branch,live_before,token)
    matching=[
      r for r in runs
      if str(r.get('name') or '')==workflow
      and str(r.get('head_sha') or '')==live_before
      and int(r.get('id') or 0)==int(receipt.get('source_validation_run_id') or 0)
    ]
    if len(matching)!=1:
        return {
          'status':'BLOCKED',
          'source_branch':branch,
          'source_head_sha':live_before,
          'failures':['SOURCE_EXACT_VALIDATION_RUN_NOT_UNIQUE_OR_MISSING']
        }
    manifest_blob,manifest=fetch_source_manifest(repository,manifest_path,live_before,token)
    live_after=fetch_live_head(repository,branch,token)
    external_check=None
    if str(receipt.get('external_trust_status') or '')=='SIGNED_PASS' or require_external_trust:
        try:
            base_sha=str(manifest.get('parent_governance_candidate_head_at_branch_creation') or '')
            mutation_actors=fetch_compare_mutation_actors(repository,base_sha,live_before,token)
            source_tree_sha,_source_head_actor=fetch_commit_tree_and_actor(repository,live_before,token)
            external_check=verify_external_trust(
              repository,token,manifest,receipt,live_before,source_tree_sha,mutation_actors
            )
        except Exception as exc:
            external_check={'status':'NOT_VERIFIED','failures':['SOURCE_EXTERNAL_TRUST_MACHINE_VERIFICATION_EXCEPTION:'+type(exc).__name__+':'+str(exc)]}
    return evaluate_snapshot(
      receipt,manifest,manifest_blob,matching[0],live_before,live_after,require_external_trust,external_check
    )
