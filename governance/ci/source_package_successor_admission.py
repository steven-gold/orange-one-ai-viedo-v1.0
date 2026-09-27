#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
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


def evaluate_snapshot(receipt:dict,source_manifest:dict,manifest_blob_sha:str,run:dict,live_before:str,live_after:str,require_external_trust:bool)->dict:
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
    if manifest_trust!=receipt_trust:
        failures.append('SOURCE_EXTERNAL_TRUST_RECEIPT_DRIFT')

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

    external_ready=(
      source_status=='SIGNED_NOT_CURRENT'
      and manifest_trust=='SIGNED_PASS'
      and receipt_trust=='SIGNED_PASS'
      and bool(str(receipt.get('external_trust_evidence_ref') or '').strip())
      and bool(str(trust.get('signer_identity') or '').strip())
      and bool(str(trust.get('signer_authority_ref') or '').strip())
      and bool(str(trust.get('signature_or_immutable_receipt_ref') or '').strip())
    )
    if require_external_trust and not external_ready:
        failures.append('SOURCE_INDEPENDENT_EXTERNAL_TRUST_NOT_PROVEN')

    return {
      'status':'PASS' if not failures else ('PASS_INTERNAL_UNSIGNED' if internal_ok and not require_external_trust and manifest_trust=='NOT_SIGNED' else 'BLOCKED'),
      'internal_exact_head_validation': 'PASS' if internal_ok else 'BLOCKED',
      'external_trust_validation': 'PASS' if external_ready else 'NOT_VERIFIED',
      'source_branch':expected_branch,
      'source_head_sha':expected_head,
      'source_status':source_status,
      'external_trust_status':manifest_trust,
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
    return evaluate_snapshot(receipt,manifest,manifest_blob,matching[0],live_before,live_after,require_external_trust)
