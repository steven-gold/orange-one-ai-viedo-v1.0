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


def fetch_compare_commits(repository:str,base_sha:str,head_sha:str,token:str|None)->list[dict]:
    if len(base_sha)!=40 or len(head_sha)!=40:
        raise RuntimeError('SOURCE_MUTATION_RANGE_SHA_INVALID')
    commits=[]
    seen=set()
    expected_total=None
    page=1
    while True:
        query=urllib.parse.urlencode({'per_page':100,'page':page})
        payload=_api_json(f'https://api.github.com/repos/{repository}/compare/{base_sha}...{head_sha}?{query}',token)
        total=int(payload.get('total_commits') or 0)
        batch=payload.get('commits') or []
        if not isinstance(batch,list):
            raise RuntimeError('SOURCE_MUTATION_COMMIT_LIST_INVALID')
        if expected_total is None:
            expected_total=total
        elif total!=expected_total:
            raise RuntimeError('SOURCE_MUTATION_COMPARE_DENOMINATOR_DRIFT')
        for commit in batch:
            sha=str((commit or {}).get('sha') or '')
            if not sha or sha in seen:
                raise RuntimeError('SOURCE_MUTATION_COMMIT_DUPLICATE_OR_MISSING_SHA')
            seen.add(sha)
            commits.append(commit)
        if len(commits)>=expected_total:
            break
        if not batch:
            raise RuntimeError('SOURCE_MUTATION_COMPARE_PAGINATION_INCOMPLETE')
        page+=1
        if page>1000:
            raise RuntimeError('SOURCE_MUTATION_COMPARE_PAGINATION_LIMIT')
    if expected_total<=0 or len(commits)!=expected_total:
        raise RuntimeError(f'SOURCE_MUTATION_COMPARE_COUNT_MISMATCH:{len(commits)}!={expected_total}')
    return commits


def fetch_compare_mutation_actors(repository:str,base_sha:str,head_sha:str,token:str|None)->set[str]:
    commits=fetch_compare_commits(repository,base_sha,head_sha,token)
    actors=set()
    for commit in commits:
        for key in ('author','committer'):
            login=str(((commit.get(key) or {}).get('login')) or '').strip()
            if login:
                actors.add(login)
    if not actors:
        raise RuntimeError('SOURCE_MUTATION_ACTOR_SET_EMPTY')
    return actors


def fetch_commit_tree_and_actor(repository:str,commit_sha:str,token:str|None)->tuple[str,str,str]:
    payload=_api_json(f'https://api.github.com/repos/{repository}/commits/{commit_sha}',token)
    tree_sha=str((((payload.get('commit') or {}).get('tree') or {}).get('sha')) or '')
    actor=str(((payload.get('author') or {}).get('login')) or ((payload.get('committer') or {}).get('login')) or '').strip()
    committed_at=str((((payload.get('commit') or {}).get('committer') or {}).get('date')) or '')
    if not tree_sha or not actor or not committed_at:
        raise RuntimeError('COMMIT_TREE_ACTOR_OR_TIME_UNRESOLVED')
    return tree_sha,actor,committed_at


def fetch_github_blob_receipt(ref:str,token:str|None)->tuple[dict,str,str,str]:
    match=re.fullmatch(r'https://github\.com/([^/]+)/([^/]+)/blob/([0-9a-fA-F]{40})/(.+)',str(ref or ''))
    if not match:
        raise RuntimeError('EXTERNAL_TRUST_ARTIFACT_MUST_BE_COMMIT_PINNED_GITHUB_BLOB')
    owner,repo_name,commit_sha,path=match.groups()
    repository=f'{owner}/{repo_name}'
    quoted=urllib.parse.quote(path,safe='/')
    query=urllib.parse.urlencode({'ref':commit_sha})
    payload=_api_json(f'https://api.github.com/repos/{repository}/contents/{quoted}?{query}',token)
    encoded=str(payload.get('content') or '').replace('\n','')
    if not encoded:
        raise RuntimeError('EXTERNAL_TRUST_ARTIFACT_CONTENT_MISSING')
    raw=base64.b64decode(encoded).decode('utf-8')
    try:
        doc=yaml.safe_load(raw) or {}
    except Exception as exc:
        raise RuntimeError('EXTERNAL_TRUST_ARTIFACT_PARSE_FAILED:'+type(exc).__name__)
    if not isinstance(doc,dict):
        raise RuntimeError('EXTERNAL_TRUST_ARTIFACT_MAPPING_REQUIRED')
    _tree,actor,committed_at=fetch_commit_tree_and_actor(repository,commit_sha,token)
    return doc,actor,commit_sha,committed_at


def fetch_github_issue(ref:str,token:str|None)->dict:
    match=re.fullmatch(r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)',str(ref or ''))
    if not match:
        raise RuntimeError('SIGNER_AUTHORITY_REF_MUST_BE_GITHUB_ISSUE')
    owner,repo_name,number=match.groups()
    return _api_json(f'https://api.github.com/repos/{owner}/{repo_name}/issues/{number}',token)


def canonical_detached_signature_payload(fields:dict)->str:
    keys=(
      'signer_identity','signer_authority_ref','source_package_identity','source_package_head_sha',
      'source_package_content_hash','predecessor_trust_identity','signed_at'
    )
    payload={key:str(fields.get(key) or '') for key in keys}
    if any(not value for value in payload.values()):
        raise RuntimeError('SOURCE_DETACHED_SIGNATURE_PAYLOAD_FIELD_MISSING')
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    import hashlib
    return hashlib.sha256(raw).hexdigest()


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
        trust_doc,receipt_actor,trust_commit_sha,receipt_commit_time=fetch_github_blob_receipt(receipt_ref,token)
    except Exception as exc:
        return {'status':'NOT_VERIFIED','failures':['SOURCE_EXTERNAL_TRUST_RECEIPT_UNVERIFIABLE:'+type(exc).__name__+':'+str(exc)]}

    signer=str(trust_doc.get('signer_identity') or '').strip()
    authority_ref=str(trust_doc.get('signer_authority_ref') or '').strip()
    signature_ref=str(trust_doc.get('signature_or_immutable_receipt_ref') or '').strip()
    if signer!=receipt_actor:
        failures.append('SOURCE_EXTERNAL_TRUST_SIGNER_RECEIPT_ACTOR_MISMATCH')
    if signer in mutation_actors or receipt_actor in mutation_actors:
        failures.append('SOURCE_EXTERNAL_TRUST_SELF_SIGN_OR_MUTATION_ACTOR_COLLISION')
    if not signature_ref or signature_ref==receipt_ref:
        failures.append('SOURCE_EXTERNAL_TRUST_DETACHED_SIGNATURE_REQUIRED')

    required=(
      'artifact_type','status','signer_identity','signer_authority_ref','source_package_identity',
      'source_package_head_sha','source_package_content_hash','predecessor_trust_identity',
      'signed_at','signature_payload_sha256','signature_or_immutable_receipt_ref'
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
    }
    for key,value in expected.items():
        if str(trust_doc.get(key) or '')!=str(value):
            failures.append('SOURCE_EXTERNAL_TRUST_RECEIPT_BINDING_MISMATCH:'+key)

    try:
        expected_payload_hash=canonical_detached_signature_payload(trust_doc)
        if str(trust_doc.get('signature_payload_sha256') or '')!=expected_payload_hash:
            failures.append('SOURCE_EXTERNAL_TRUST_PAYLOAD_HASH_MISMATCH')
        signature_doc,signature_actor,signature_commit_sha,signature_commit_time=fetch_github_blob_receipt(signature_ref,token)
        if signature_actor!=signer:
            failures.append('SOURCE_DETACHED_SIGNATURE_ACTOR_MISMATCH')
        if signature_actor in mutation_actors:
            failures.append('SOURCE_DETACHED_SIGNATURE_MUTATION_ACTOR_COLLISION')
        signature_expected={
          'artifact_type':'GOVERNANCE_SOURCE_DETACHED_TRUST_SIGNATURE',
          'status':'SIGNED_PASS',
          'signer_identity':signer,
          'signer_authority_ref':authority_ref,
          'source_package_identity':expected_identity,
          'source_package_head_sha':source_head_sha,
          'source_package_content_hash':expected_content_hash,
          'predecessor_trust_identity':expected_predecessor,
          'signed_at':str(trust_doc.get('signed_at') or ''),
          'signature_payload_sha256':expected_payload_hash,
        }
        for key,value in signature_expected.items():
            if str(signature_doc.get(key) or '')!=str(value):
                failures.append('SOURCE_DETACHED_SIGNATURE_BINDING_MISMATCH:'+key)

        source_auth=fetch_github_issue(str(source_manifest.get('authorization_record') or ''),token)
        source_auth_actor=str(((source_auth.get('user') or {}).get('login')) or '')
        signer_auth=fetch_github_issue(authority_ref,token)
        signer_auth_actor=str(((signer_auth.get('user') or {}).get('login')) or '')
        authority_body=str(signer_auth.get('body') or '')
        if not source_auth_actor or signer_auth_actor!=source_auth_actor:
            failures.append('SOURCE_EXTERNAL_TRUST_AUTHORITY_ACTOR_MISMATCH')
        for token_text in (signer,expected_identity,source_head_sha,expected_content_hash):
            if token_text not in authority_body:
                failures.append('SOURCE_EXTERNAL_TRUST_AUTHORITY_SCOPE_MISSING:'+token_text)

        auth_created_dt=datetime.fromisoformat(str(signer_auth.get('created_at') or '').replace('Z','+00:00')).astimezone(timezone.utc)
        auth_updated_dt=datetime.fromisoformat(str(signer_auth.get('updated_at') or '').replace('Z','+00:00')).astimezone(timezone.utc)
        signed_dt=datetime.fromisoformat(str(trust_doc.get('signed_at') or '').replace('Z','+00:00')).astimezone(timezone.utc)
        signature_commit_dt=datetime.fromisoformat(signature_commit_time.replace('Z','+00:00')).astimezone(timezone.utc)
        receipt_commit_dt=datetime.fromisoformat(receipt_commit_time.replace('Z','+00:00')).astimezone(timezone.utc)
        if not (auth_created_dt < signed_dt and auth_updated_dt < signed_dt <= signature_commit_dt <= receipt_commit_dt):
            failures.append('SOURCE_EXTERNAL_TRUST_TEMPORAL_ORDER_INVALID')
    except Exception as exc:
        failures.append('SOURCE_EXTERNAL_TRUST_DETACHED_SIGNATURE_OR_AUTHORITY_UNVERIFIABLE:'+type(exc).__name__+':'+str(exc))

    return {
      'status':'PASS' if not failures else 'NOT_VERIFIED',
      'signer_identity':signer,
      'trust_commit_sha':trust_commit_sha,
      'detached_signature_ref':signature_ref,
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


def evaluate_snapshot(receipt:dict,source_manifest:dict,manifest_blob_sha:str,run:dict,live_before:str,live_after:str,require_external_trust:bool,external_trust_verification:dict|None=None,expected_workflow_path:str|None=None,allowed_workflow_events:list[str]|None=None)->dict:
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
    if expected_workflow_path and str(run.get('path') or '')!=expected_workflow_path:
        failures.append('SOURCE_VALIDATION_WORKFLOW_PATH_DRIFT')
    allowed_events=set(map(str,allowed_workflow_events or []))
    if allowed_events and str(run.get('event') or '') not in allowed_events:
        failures.append('SOURCE_VALIDATION_WORKFLOW_EVENT_DRIFT')
    if str(run.get('head_branch') or '')!=expected_branch:
        failures.append('SOURCE_VALIDATION_HEAD_BRANCH_DRIFT')
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
      str(receipt.get('source_internal_status') or '')=='PASS_INTERNAL_UNSIGNED'
      and not any(x in failures for x in (
        'SOURCE_SUCCESSOR_LIVE_HEAD_DRIFT','SOURCE_VALIDATION_RUN_HEAD_DRIFT',
        'SOURCE_VALIDATION_WORKFLOW_DRIFT','SOURCE_VALIDATION_WORKFLOW_PATH_DRIFT',
        'SOURCE_VALIDATION_WORKFLOW_EVENT_DRIFT','SOURCE_VALIDATION_HEAD_BRANCH_DRIFT',
        'SOURCE_VALIDATION_RUN_ID_DRIFT',
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
      'status':(
        'PASS_INTERNAL_UNSIGNED'
        if internal_ok and not require_external_trust and source_status=='UNSIGNED_NOT_CURRENT' and manifest_trust=='NOT_SIGNED' and not failures
        else ('PASS' if not failures and external_ready else 'BLOCKED')
      ),
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
    workflow_path=str(contract.get('source_package_successor_workflow_path') or '')
    workflow_events=list(map(str,contract.get('source_package_successor_workflow_allowed_events') or []))
    manifest_path=str(contract.get('source_package_successor_manifest_path') or '')
    if not workflow_path or set(workflow_events)!={'push','workflow_dispatch'} or contract.get('source_package_successor_workflow_identity_requires_name_path_allowed_event_branch_head') is not True:
        return {'status':'BLOCKED','failures':['SOURCE_WORKFLOW_IDENTITY_CONTRACT_INCOMPLETE']}
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
      and str(r.get('path') or '')==workflow_path
      and str(r.get('event') or '') in set(workflow_events)
      and str(r.get('head_branch') or '')==branch
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
      receipt,manifest,manifest_blob,matching[0],live_before,live_after,require_external_trust,external_check,
      expected_workflow_path=workflow_path,allowed_workflow_events=workflow_events
    )
