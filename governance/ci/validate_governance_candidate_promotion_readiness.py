#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import re
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'governance/specifications/REGISTRY.yaml'
sys.path.insert(0,str(ROOT/'governance/ci'))
from governance_resolver import resolve as resolve_governance
import audit_closure_engine as audit_engine
from source_package_successor_admission import evaluate_snapshot, evaluate_validation_toolchain_bindings, validate_source_successor


def load_yaml(path: Path) -> dict:
    value=yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(value,dict):
        raise RuntimeError('MAPPING_REQUIRED:'+str(path.relative_to(ROOT)))
    return value


def current_head() -> str:
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def evaluate_workflow_readiness(required_bindings:dict, head_sha:str, branch:str, runs:list[dict]) -> dict:
    rows=[]
    for name,binding in required_bindings.items():
        binding=binding if isinstance(binding,dict) else {}
        expected_path=str(binding.get('path') or '')
        expected_event=str(binding.get('event') or '')
        matches=[r for r in runs if str(r.get('name') or '')==name and str(r.get('head_sha') or '')==head_sha and str(r.get('head_branch') or '')==branch and str(r.get('path') or '')==expected_path and str(r.get('event') or '')==expected_event]
        matches.sort(key=lambda r:str(r.get('created_at') or ''),reverse=True)
        if not matches:
            rows.append({'workflow_name':name,'workflow_path':expected_path,'event':expected_event,'status':'MISSING_EXACT_BOUND_WORKFLOW_RUN'})
            continue
        row=matches[0]
        ready=str(row.get('status') or '')=='completed' and str(row.get('conclusion') or '')=='success'
        rows.append({'workflow_name':name,'workflow_path':row.get('path'),'event':row.get('event'),'head_branch':row.get('head_branch'),'run_id':row.get('id'),'head_sha':row.get('head_sha'),'status':row.get('status'),'conclusion':row.get('conclusion'),'ready':ready})
    return {'required_workflow_count':len(required_bindings),'ready_workflow_count':sum(1 for r in rows if r.get('ready') is True),'rows':rows,'status':'PASS' if rows and all(r.get('ready') is True for r in rows) else 'BLOCKED'}

def evaluate_integrated_source_readiness(contract:dict, head_sha:str, branch:str, runs:list[dict]) -> dict:
    if contract.get('source_package_integration_mode')!='SINGLE_BRANCH_INTEGRATED':
        return {'status':'BLOCKED','reason':'INTEGRATED_SOURCE_MODE_NOT_ACTIVE'}
    if contract.get('source_package_successor_required') is not False:
        return {'status':'BLOCKED','reason':'SEPARATE_SOURCE_SUCCESSOR_STILL_REQUIRED'}
    if str(contract.get('source_package_integrated_branch') or '')!=branch:
        return {'status':'BLOCKED','reason':'INTEGRATED_SOURCE_BRANCH_DRIFT'}
    name=str(contract.get('source_package_successor_workflow_name') or '')
    path=str(contract.get('source_package_successor_workflow_path') or '')
    allowed=set(map(str,contract.get('source_package_successor_workflow_allowed_events') or []))
    matches=[r for r in runs
      if str(r.get('name') or '')==name
      and str(r.get('path') or '')==path
      and str(r.get('head_branch') or '')==branch
      and str(r.get('head_sha') or '')==head_sha
      and str(r.get('event') or '') in allowed]
    matches.sort(key=lambda r:str(r.get('created_at') or ''),reverse=True)
    if not matches:
        return {'status':'BLOCKED','reason':'INTEGRATED_SOURCE_EXACT_HEAD_RUN_MISSING','workflow_name':name,'workflow_path':path}
    row=matches[0]
    ready=str(row.get('status') or '')=='completed' and str(row.get('conclusion') or '')=='success'
    return {
      'status':'PASS' if ready else 'BLOCKED',
      'mode':'SINGLE_BRANCH_INTEGRATED',
      'workflow_name':name,
      'workflow_path':str(row.get('path') or ''),
      'event':str(row.get('event') or ''),
      'head_branch':str(row.get('head_branch') or ''),
      'head_sha':str(row.get('head_sha') or ''),
      'run_id':row.get('id'),
      'run_status':row.get('status'),
      'run_conclusion':row.get('conclusion'),
      'promotion_credit':1 if ready else 0,
    }

def fetch_live_branch_head(repository:str, branch:str, token:str|None) -> str:
    url=f'https://api.github.com/repos/{repository}/branches/{urllib.parse.quote(branch,safe="")}'
    headers={'Accept':'application/vnd.github+json','User-Agent':'ACPOS-Governance-Promotion-Readiness'}
    if token:
        headers['Authorization']='Bearer '+token
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30) as response:
        payload=json.loads(response.read().decode('utf-8'))
    head=str(((payload.get('commit') or {}).get('sha')) or '')
    if len(head)!=40:
        raise RuntimeError('LIVE_BRANCH_HEAD_INVALID')
    return head


def fetch_runs(repository:str, branch:str, head_sha:str, token:str|None) -> list[dict]:
    query=urllib.parse.urlencode({'branch':branch,'head_sha':head_sha,'per_page':100})
    url=f'https://api.github.com/repos/{repository}/actions/runs?{query}'
    headers={'Accept':'application/vnd.github+json','User-Agent':'ACPOS-Governance-Promotion-Readiness'}
    if token:
        headers['Authorization']='Bearer '+token
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30) as response:
        payload=json.loads(response.read().decode('utf-8'))
    runs=payload.get('workflow_runs') or []
    if not isinstance(runs,list):
        raise RuntimeError('WORKFLOW_RUN_LIST_INVALID')
    return runs


def api_json(url:str,token:str|None)->dict:
    headers={'Accept':'application/vnd.github+json','User-Agent':'ACPOS-Governance-Promotion-Readiness'}
    if token: headers['Authorization']='Bearer '+token
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30) as response:
        value=json.loads(response.read().decode('utf-8'))
    if not isinstance(value,dict): raise RuntimeError('GITHUB_API_MAPPING_REQUIRED')
    return value

def parse_pinned_blob(ref:str)->tuple[str,str,str,str]:
    m=re.fullmatch(r'https://github\.com/([^/]+)/([^/]+)/blob/([0-9a-fA-F]{40})/(.+)',str(ref or ''))
    if not m: raise RuntimeError('PROVENANCE_REF_MUST_BE_COMMIT_PINNED_GITHUB_BLOB')
    return m.group(1),m.group(2),m.group(3),m.group(4)

def fetch_pinned_blob(ref:str,token:str|None)->tuple[bytes,str,str]:
    owner,repo_name,sha,path=parse_pinned_blob(ref)
    q=urllib.parse.urlencode({'ref':sha})
    payload=api_json(f'https://api.github.com/repos/{owner}/{repo_name}/contents/{urllib.parse.quote(path,safe="/")}?{q}',token)
    raw=base64.b64decode(str(payload.get('content') or '').replace('\n',''))
    commit=api_json(f'https://api.github.com/repos/{owner}/{repo_name}/commits/{sha}',token)
    actor=str(((commit.get('author') or {}).get('login')) or ((commit.get('committer') or {}).get('login')) or '').strip()
    committed_at=str(((commit.get('commit') or {}).get('committer') or {}).get('date') or '')
    if not raw or not actor or not committed_at: raise RuntimeError('PROVENANCE_BLOB_ACTOR_OR_TIME_MISSING')
    return raw,actor,committed_at

def fetch_issue(ref:str,token:str|None)->dict:
    m=re.fullmatch(r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)',str(ref or ''))
    if not m: raise RuntimeError('AUTHORITY_REF_MUST_BE_GITHUB_ISSUE')
    return api_json(f'https://api.github.com/repos/{m.group(1)}/{m.group(2)}/issues/{m.group(3)}',token)

def fetch_compare_commits(repository:str,base:str,head:str,token:str|None)->list[dict]:
    if len(base)!=40 or len(head)!=40:
        raise RuntimeError('CANDIDATE_MUTATION_RANGE_SHA_INVALID')
    commits=[]; seen=set(); expected_total=None; page=1
    while True:
        query=urllib.parse.urlencode({'per_page':100,'page':page})
        payload=api_json(f'https://api.github.com/repos/{repository}/compare/{base}...{head}?{query}',token)
        total=int(payload.get('total_commits') or 0)
        batch=payload.get('commits') or []
        if not isinstance(batch,list):
            raise RuntimeError('CANDIDATE_MUTATION_COMMIT_LIST_INVALID')
        if expected_total is None:
            expected_total=total
        elif total!=expected_total:
            raise RuntimeError('CANDIDATE_MUTATION_COMPARE_DENOMINATOR_DRIFT')
        for commit in batch:
            sha=str((commit or {}).get('sha') or '')
            if not sha or sha in seen:
                raise RuntimeError('CANDIDATE_MUTATION_COMMIT_DUPLICATE_OR_MISSING_SHA')
            seen.add(sha); commits.append(commit)
        if len(commits)>=expected_total:
            break
        if not batch:
            raise RuntimeError('CANDIDATE_MUTATION_COMPARE_PAGINATION_INCOMPLETE')
        page+=1
        if page>1000:
            raise RuntimeError('CANDIDATE_MUTATION_COMPARE_PAGINATION_LIMIT')
    if expected_total<=0 or len(commits)!=expected_total:
        raise RuntimeError(f'CANDIDATE_MUTATION_COMPARE_COUNT_MISMATCH:{len(commits)}!={expected_total}')
    return commits


def candidate_mutation_actors(repository:str,base:str,head:str,token:str|None)->set[str]:
    actors=set()
    for c in fetch_compare_commits(repository,base,head,token):
        for k in ('author','committer'):
            x=str(((c.get(k) or {}).get('login')) or '').strip()
            if x: actors.add(x)
    if not actors:
        raise RuntimeError('CANDIDATE_MUTATION_ACTOR_SET_EMPTY')
    return actors


def canonical_candidate_audit_snapshot(registry:dict,repository:str,candidate_head:str)->tuple[str,dict]:
    ident=registry.get('governance_identity') or {}
    vc=registry.get('candidate_validation_contract') or {}
    branch=str(registry.get('branch') or '')
    snapshot={
      'repository':repository,
      'candidate_branch':branch,
      'candidate_head_sha':candidate_head,
      'governance_uid':str(ident.get('governance_uid') or ''),
      'governance_revision':str(ident.get('governance_revision') or ''),
      'specification_bundle_sha256':str(ident.get('specification_bundle_sha256') or ''),
      'canonical_rule_registry_digest':str(ident.get('canonical_rule_registry_digest') or ''),
    }
    if vc.get('source_package_integration_mode')=='SINGLE_BRANCH_INTEGRATED':
        snapshot.update({
          'source_package_mode':'SINGLE_BRANCH_INTEGRATED',
          'source_package_branch':str(vc.get('source_package_integrated_branch') or ''),
          'source_package_head_sha':candidate_head,
          'source_package_validator':str(vc.get('source_package_integrated_validator') or ''),
        })
        if snapshot['source_package_branch']!=branch:
            raise RuntimeError('INTEGRATED_SOURCE_BRANCH_DRIFT')
    else:
        receipt_rel=str(vc.get('source_package_successor_admission_receipt') or '')
        receipt=load_yaml(ROOT/receipt_rel)
        snapshot.update({
          'source_package_mode':'SEPARATE_SUCCESSOR',
          'source_package_branch':str(receipt.get('candidate_source_branch') or ''),
          'source_package_head_sha':str(receipt.get('source_head_sha') or ''),
          'source_package_manifest_blob_sha':str(receipt.get('source_candidate_manifest_blob_sha') or ''),
        })
    if any(not value for value in snapshot.values()):
        raise RuntimeError('CANONICAL_AUDIT_SNAPSHOT_FIELD_MISSING')
    canonical=json.dumps(snapshot,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest(),snapshot


def canonical_result_fingerprint(result_doc:dict)->str:
    canonical_result=result_doc.get('canonical_result')
    if not isinstance(canonical_result,dict) or not canonical_result:
        raise RuntimeError('INDEPENDENT_AUDITOR_CANONICAL_RESULT_REQUIRED')
    raw=json.dumps(canonical_result,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def validate_independent_auditor_provenance(records,repository,token,registry,candidate_head):
    vc=registry.get('candidate_validation_contract') or {}
    provenance_required=set(map(str,vc.get('independent_auditor_required_provenance_fields') or []))
    expected_provenance={'implementation_provenance_ref','execution_receipt_provenance_ref','result_artifact_provenance_ref','evaluator_authority_ref'}
    if vc.get('independent_auditor_external_provenance_required') is not True or provenance_required!=expected_provenance:
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_PROVENANCE_CONTRACT_DRIFT'}
    if vc.get('independent_auditor_snapshot_hash_mode')!='SHA256_CANONICAL_JSON_CURRENT_CANDIDATE_SOURCE_SNAPSHOT_V1':
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_SNAPSHOT_HASH_MODE_DRIFT'}
    if vc.get('independent_auditor_result_fingerprint_mode')!='SHA256_CANONICAL_JSON_CANONICAL_RESULT_V1':
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_RESULT_FINGERPRINT_MODE_DRIFT'}
    if not isinstance(records,list) or len(records)!=3:
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_RECORD_DENOMINATOR_DRIFT','observed_count':len(records) if isinstance(records,list) else 0}

    ctx=audit_engine.load_context()
    policy=((ctx.get('current_policy') or {}).get('auditor_implementation_independence') or {})
    base_required=set(map(str,policy.get('formal_independent_evaluator_required_fields') or []))
    expected_base={'evaluator_uid','implementation_owner_uid','decision_engine_uid','implementation_ref','implementation_sha256','execution_receipt_ref','audit_snapshot_hash','result_fingerprint'}
    if base_required!=expected_base:
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_BASE_FIELD_DENOMINATOR_DRIFT'}

    ident=registry.get('governance_identity') or {}
    primary=fetch_issue(str(ident.get('authorization_record_url') or ''),token)
    primary_actor=str(((primary.get('user') or {}).get('login')) or '')
    if not primary_actor:
        return {'status':'FAIL','reason':'PRIMARY_GOVERNANCE_AUTHORITY_ACTOR_MISSING'}
    mutations=candidate_mutation_actors(repository,str(ident.get('predecessor_head_sha') or ''),candidate_head,token)
    expected_snapshot_hash,snapshot=canonical_candidate_audit_snapshot(registry,repository,candidate_head)

    actors=[]; result_fingerprints=[]; evaluator_uids=[]; owner_uids=[]; engine_uids=[]; impl_hashes=[]; evidence_times=[]; rows=[]
    for i,r in enumerate(records):
        if not isinstance(r,dict):
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_RECORD_INVALID','index':i}
        missing=[f for f in sorted(base_required|provenance_required) if not str(r.get(f) or '').strip()]
        if missing:
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_FIELD_MISSING','index':i,'fields':missing}

        impl,ia,impl_time=fetch_pinned_blob(str(r['implementation_provenance_ref']),token)
        rec,ra,receipt_time=fetch_pinned_blob(str(r['execution_receipt_provenance_ref']),token)
        result_raw,result_actor,result_time=fetch_pinned_blob(str(r['result_artifact_provenance_ref']),token)
        if len({ia,ra,result_actor})!=1:
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_PROVENANCE_ACTOR_CHAIN_MISMATCH','index':i}
        if ia in mutations:
            return {'status':'FAIL','reason':'CANDIDATE_MUTATION_ACTOR_CANNOT_BE_FORMAL_INDEPENDENT_AUDITOR','index':i,'actor':ia}

        impl_hash=hashlib.sha256(impl).hexdigest()
        if impl_hash!=str(r.get('implementation_sha256') or ''):
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_PROVENANCE_IMPLEMENTATION_HASH_MISMATCH','index':i}
        if str(r.get('audit_snapshot_hash') or '')!=expected_snapshot_hash:
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_SNAPSHOT_HASH_MISMATCH','index':i,'expected':expected_snapshot_hash,'actual':r.get('audit_snapshot_hash')}

        rd=yaml.safe_load(rec.decode('utf-8')) or {}
        result_doc=yaml.safe_load(result_raw.decode('utf-8')) or {}
        if not isinstance(rd,dict) or not isinstance(result_doc,dict):
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_PROVENANCE_MAPPING_REQUIRED','index':i}
        actual_result_fp=canonical_result_fingerprint(result_doc)
        if actual_result_fp!=str(r.get('result_fingerprint') or ''):
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_RESULT_FINGERPRINT_MISMATCH','index':i}
        for k in ('evaluator_uid','implementation_sha256','audit_snapshot_hash','result_fingerprint'):
            if str(rd.get(k) or '')!=str(r.get(k) or ''):
                return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_RECEIPT_BINDING_MISMATCH','index':i,'field':k}
        if str(rd.get('status') or '')!='PASS':
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_RECEIPT_NOT_PASS','index':i}
        if str(result_doc.get('evaluator_uid') or '')!=str(r.get('evaluator_uid') or '') or str(result_doc.get('audit_snapshot_hash') or '')!=expected_snapshot_hash:
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_RESULT_ARTIFACT_BINDING_MISMATCH','index':i}

        auth=fetch_issue(str(r['evaluator_authority_ref']),token)
        body=str(auth.get('body') or '')
        if str(((auth.get('user') or {}).get('login')) or '')!=primary_actor:
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_AUTHORITY_ACTOR_MISMATCH','index':i}
        for tok in (str(r.get('evaluator_uid') or ''),ia,str(ident.get('governance_uid') or ''),expected_snapshot_hash):
            if tok not in body:
                return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_AUTHORITY_SCOPE_MISSING','index':i,'token':tok}
        try:
            auth_created_dt=datetime.fromisoformat(str(auth.get('created_at') or '').replace('Z','+00:00')).astimezone(timezone.utc)
            auth_updated_dt=datetime.fromisoformat(str(auth.get('updated_at') or '').replace('Z','+00:00')).astimezone(timezone.utc)
            item_times=[
              datetime.fromisoformat(t.replace('Z','+00:00')).astimezone(timezone.utc)
              for t in (impl_time,receipt_time,result_time)
            ]
            first_evidence_dt=min(item_times)
        except Exception:
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_AUTHORITY_TIME_INVALID','index':i}
        if not (auth_created_dt < first_evidence_dt and auth_updated_dt < first_evidence_dt):
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_AUTHORITY_NOT_IMMUTABLY_PREEXISTING_EVIDENCE','index':i}

        actors.append(ia); result_fingerprints.append(actual_result_fp); evaluator_uids.append(str(r['evaluator_uid']))
        owner_uids.append(str(r['implementation_owner_uid'])); engine_uids.append(str(r['decision_engine_uid'])); impl_hashes.append(impl_hash)
        evidence_times.extend(item_times)
        rows.append({'evaluator_uid':r.get('evaluator_uid'),'provenance_actor':ia,'implementation_sha256':impl_hash,'audit_snapshot_hash':expected_snapshot_hash,'result_fingerprint':actual_result_fp})

    for field,values in (
      ('evaluator_uid',evaluator_uids),('implementation_owner_uid',owner_uids),('decision_engine_uid',engine_uids),
      ('implementation_sha256',impl_hashes),('provenance_actor',actors)
    ):
        if len(set(values))!=3:
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_DISTINCTNESS_NOT_PROVEN','field':field,'values':values}
    if len(set(result_fingerprints))!=1:
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_RESULT_ARTIFACTS_NOT_IDENTICAL','fingerprints':result_fingerprints}
    max_evidence=max(evidence_times)
    return {
      'status':'PASS','independent_provenance_actor_count':3,'audit_snapshot_hash':expected_snapshot_hash,
      'canonical_snapshot':snapshot,'result_fingerprint':result_fingerprints[0],
      'max_evidence_time':max_evidence.isoformat(),'rows':rows
    }


def evaluate_independent_auditors_external(evidence_ref:str,repository:str,token:str|None,registry:dict,candidate_head:str)->dict:
    vc=registry.get('candidate_validation_contract') or {}
    if vc.get('independent_auditor_formal_evidence_transport')!='COMMIT_PINNED_EXTERNAL_MANIFEST':
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_EVIDENCE_TRANSPORT_DRIFT'}
    try:
        raw,manifest_actor,manifest_time=fetch_pinned_blob(evidence_ref,token)
        manifest=yaml.safe_load(raw.decode('utf-8')) or {}
    except Exception as exc:
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_EXTERNAL_MANIFEST_UNVERIFIABLE','detail':type(exc).__name__+':'+str(exc)}
    if not isinstance(manifest,dict):
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_EXTERNAL_MANIFEST_MAPPING_REQUIRED'}
    ident=registry.get('governance_identity') or {}
    expected_snapshot_hash,_snapshot=canonical_candidate_audit_snapshot(registry,repository,candidate_head)
    expected_type=str(vc.get('independent_auditor_external_manifest_artifact_type') or '')
    expected={
      'artifact_type':expected_type,
      'candidate_head_sha':candidate_head,
      'governance_uid':str(ident.get('governance_uid') or ''),
      'audit_snapshot_hash':expected_snapshot_hash,
    }
    for key,value in expected.items():
        if not value or str(manifest.get(key) or '')!=value:
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_EXTERNAL_MANIFEST_BINDING_MISMATCH','field':key}

    primary=fetch_issue(str(ident.get('authorization_record_url') or ''),token)
    primary_actor=str(((primary.get('user') or {}).get('login')) or '')
    if vc.get('independent_auditor_external_manifest_actor_must_equal_primary_authority_actor') is not True or manifest_actor!=primary_actor:
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_EXTERNAL_MANIFEST_ACTOR_MISMATCH'}

    records=manifest.get('evaluators')
    provenance=validate_independent_auditor_provenance(records,repository,token,registry,candidate_head)
    if provenance.get('status')!='PASS':
        return provenance
    try:
        manifest_dt=datetime.fromisoformat(manifest_time.replace('Z','+00:00')).astimezone(timezone.utc)
        evidence_dt=datetime.fromisoformat(str(provenance.get('max_evidence_time') or '')).astimezone(timezone.utc)
    except Exception:
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_EXTERNAL_MANIFEST_TIME_INVALID'}
    if vc.get('independent_auditor_external_manifest_commit_must_follow_all_evaluator_evidence') is not True or manifest_dt < evidence_dt:
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_EXTERNAL_MANIFEST_PRECEDES_EVIDENCE'}
    return {
      'status':'PASS','formal_credit':1,'evidence_transport':'COMMIT_PINNED_EXTERNAL_MANIFEST',
      'manifest_ref':evidence_ref,'manifest_actor':manifest_actor,'audit_snapshot_hash':expected_snapshot_hash,
      'provenance_validation':provenance
    }


def evaluate_independent_auditors_local(evidence_path:Path|None)->dict:
    if evidence_path is None:
        return {'status':'NOT_VERIFIED','reason':'INDEPENDENT_AUDITOR_EVIDENCE_REQUIRED','required_count':3}
    ctx=audit_engine.load_context()
    p=evidence_path.resolve()
    records=audit_engine.load_independent_evaluator_evidence(p)
    base=audit_engine.validate_independent_evaluator_implementations(ctx,records,p.parent)
    return {
      'status':'NOT_VERIFIED',
      'reason':'LOCAL_AUDITOR_EVIDENCE_HAS_ZERO_FORMAL_PROMOTION_CREDIT',
      'formal_credit':0,
      'local_validation':base,
    }


def self_test() -> int:
    head='a'*40; branch='candidate'
    bindings={
      'Current Governance Cleanup Validation':{'path':'.github/workflows/current-governance-cleanup-validation.yml','event':'push'},
      'Mother Spec Neutrality Audit':{'path':'.github/workflows/mother-spec-neutrality-audit.yml','event':'push'},
    }
    names=list(bindings); cases=[]
    def run(i,name,sha=head,status='completed',conclusion='success',path=None,event='push',head_branch=branch):
        return {'id':i,'name':name,'head_sha':sha,'status':status,'conclusion':conclusion,'created_at':'2026-01-01T00:00:00Z','path':path or bindings[name]['path'],'event':event,'head_branch':head_branch}
    def add(name,runs,expected):
        result=evaluate_workflow_readiness(bindings,head,branch,runs)
        cases.append({'case':name,'expected':expected,'actual':result['status'],'ok':result['status']==expected})
    add('missing_one_workflow',[run(1,names[0])],'BLOCKED')
    add('historical_head_cannot_substitute',[run(1,names[0],'b'*40),run(2,names[1],'b'*40)],'BLOCKED')
    add('in_progress_cannot_substitute_terminal',[run(1,names[0],status='in_progress',conclusion=None),run(2,names[1])],'BLOCKED')
    add('exact_head_terminal_success',[run(1,names[0]),run(2,names[1])],'PASS')
    integrated_contract={'source_package_integration_mode':'SINGLE_BRANCH_INTEGRATED','source_package_successor_required':False,'source_package_integrated_branch':branch,'source_package_successor_workflow_name':'Integrated Source Package Validation','source_package_successor_workflow_path':'.github/workflows/source-package-successor-validation.yml','source_package_successor_workflow_allowed_events':['push','workflow_dispatch']}
    integrated_run={'id':9,'name':'Integrated Source Package Validation','path':'.github/workflows/source-package-successor-validation.yml','event':'push','head_branch':branch,'head_sha':head,'status':'completed','conclusion':'success','created_at':'2026-01-01T00:00:00Z'}
    ir=evaluate_integrated_source_readiness(integrated_contract,head,branch,[integrated_run])
    cases.append({'case':'single_branch_integrated_source_exact_head_success','expected':'PASS','actual':ir.get('status'),'ok':ir.get('status')=='PASS'})
    irm=evaluate_integrated_source_readiness(integrated_contract,head,branch,[])
    cases.append({'case':'single_branch_integrated_source_missing_run_blocked','expected':'BLOCKED','actual':irm.get('status'),'ok':irm.get('status')=='BLOCKED'})
    add('same_name_wrong_workflow_path_blocked',[run(1,names[0],path='.github/workflows/fake.yml'),run(2,names[1])],'BLOCKED')
    add('manual_dispatch_cannot_substitute_push_gate',[run(1,names[0],event='workflow_dispatch'),run(2,names[1])],'BLOCKED')
    add('wrong_head_branch_cannot_substitute_candidate_run',[run(1,names[0],head_branch='other'),run(2,names[1])],'BLOCKED')
    _tc_contract={
      'source_package_validation_toolchain_binding_mode':'GIT_BLOB_SHA1_EXACT_SET_V1',
      'source_package_validation_toolchain_exact_file_count':2,
      'source_package_validation_toolchain_exact_paths':['a.py'],
      'source_package_validation_toolchain_subtree_prefixes':['tests/'],
      'source_package_validation_toolchain_blob_bindings':{'a.py':'sha-a','tests/b.py':'sha-b'},
    }
    _tc_exact=evaluate_validation_toolchain_bindings(_tc_contract,{'a.py':'sha-a','tests/b.py':'sha-b','other.txt':'ignored'})
    cases.append({'case':'source_validation_toolchain_exact_binding_pass','expected':'PASS','actual':_tc_exact.get('status'),'ok':_tc_exact.get('status')=='PASS'})
    _tc_missing=evaluate_validation_toolchain_bindings(_tc_contract,{'a.py':'sha-a'})
    cases.append({'case':'source_validation_toolchain_missing_blocked','expected':'BLOCKED','actual':_tc_missing.get('status'),'ok':_tc_missing.get('status')=='BLOCKED'})
    _tc_extra=evaluate_validation_toolchain_bindings(_tc_contract,{'a.py':'sha-a','tests/b.py':'sha-b','tests/c.py':'sha-c'})
    cases.append({'case':'source_validation_toolchain_extra_blocked','expected':'BLOCKED','actual':_tc_extra.get('status'),'ok':_tc_extra.get('status')=='BLOCKED'})
    _tc_drift=evaluate_validation_toolchain_bindings(_tc_contract,{'a.py':'sha-a','tests/b.py':'sha-X'})
    cases.append({'case':'source_validation_toolchain_blob_drift_blocked','expected':'BLOCKED','actual':_tc_drift.get('status'),'ok':_tc_drift.get('status')=='BLOCKED'})
    for row in [
      {'case':'local_equals_live_before_and_after','local':head,'before':head,'after':head,'expected':True},
      {'case':'historical_local_head_blocked','local':head,'before':'b'*40,'after':'b'*40,'expected':False},
      {'case':'branch_moves_during_validation_blocked','local':head,'before':head,'after':'c'*40,'expected':False},
    ]:
        row['actual']=(row['local']==row['before']==row['after']); row['ok']=row['actual']==row['expected']; cases.append(row)
    synthetic_receipt={'candidate_source_branch':'source-candidate','source_head_sha':head,'source_validation_workflow_name':'Source Package Successor Validation','source_validation_run_id':77,'source_validation_status':'completed','source_validation_conclusion':'success','source_internal_status':'PASS_INTERNAL_UNSIGNED','source_candidate_manifest_blob_sha':'blob1','released_current_authority':False,'external_trust_status':'NOT_SIGNED','external_trust_evidence_ref':None}
    synthetic_manifest={'status':'UNSIGNED_NOT_CURRENT','current_authority':False,'external_trust':{'status':'NOT_SIGNED','candidate_self_sign':'FORBIDDEN'}}
    synthetic_run={'id':77,'name':'Source Package Successor Validation','path':'.github/workflows/source-package-successor-validation.yml','event':'push','head_branch':'source-candidate','head_sha':head,'status':'completed','conclusion':'success'}
    internal=evaluate_snapshot(synthetic_receipt,synthetic_manifest,'blob1',synthetic_run,head,head,False,expected_workflow_path='.github/workflows/source-package-successor-validation.yml',allowed_workflow_events=['push','workflow_dispatch'])
    cases.append({'case':'source_internal_unsigned_valid_for_candidate_validation','expected':'PASS_INTERNAL_UNSIGNED','actual':internal.get('status'),'ok':internal.get('status')=='PASS_INTERNAL_UNSIGNED'})
    promotion=evaluate_snapshot(synthetic_receipt,synthetic_manifest,'blob1',synthetic_run,head,head,True,expected_workflow_path='.github/workflows/source-package-successor-validation.yml',allowed_workflow_events=['push','workflow_dispatch'])
    cases.append({'case':'source_unsigned_blocks_promotion','expected':'BLOCKED','actual':promotion.get('status'),'ok':promotion.get('status')=='BLOCKED'})
    signed_receipt=dict(synthetic_receipt); signed_receipt.update({'source_internal_status':'PASS_INTERNAL_UNSIGNED','external_trust_status':'SIGNED_PASS','external_trust_evidence_ref':'external://receipt'})
    signed=evaluate_snapshot(signed_receipt,synthetic_manifest,'blob1',synthetic_run,head,head,True,{'status':'PASS','signer_identity':'SIGNER-1','mutation_actor_count':2,'failures':[]},expected_workflow_path='.github/workflows/source-package-successor-validation.yml',allowed_workflow_events=['push','workflow_dispatch'])
    cases.append({'case':'external_trust_envelope_allows_frozen_source_content','expected':'PASS','actual':signed.get('status'),'ok':signed.get('status')=='PASS'})
    wrong_source_path=dict(synthetic_run); wrong_source_path['path']='.github/workflows/fake-source.yml'
    wrong_path=evaluate_snapshot(synthetic_receipt,synthetic_manifest,'blob1',wrong_source_path,head,head,False,expected_workflow_path='.github/workflows/source-package-successor-validation.yml',allowed_workflow_events=['push','workflow_dispatch'])
    cases.append({'case':'source_same_name_wrong_workflow_path_blocked','expected':'BLOCKED','actual':wrong_path.get('status'),'ok':wrong_path.get('status')=='BLOCKED'})
    dispatch_source_event=dict(synthetic_run); dispatch_source_event['event']='workflow_dispatch'
    dispatch_event=evaluate_snapshot(synthetic_receipt,synthetic_manifest,'blob1',dispatch_source_event,head,head,False,expected_workflow_path='.github/workflows/source-package-successor-validation.yml',allowed_workflow_events=['push','workflow_dispatch'])
    cases.append({'case':'source_exact_head_manual_dispatch_allowed','expected':'PASS_INTERNAL_UNSIGNED','actual':dispatch_event.get('status'),'ok':dispatch_event.get('status')=='PASS_INTERNAL_UNSIGNED'})
    wrong_source_event=dict(synthetic_run); wrong_source_event['event']='schedule'
    wrong_event=evaluate_snapshot(synthetic_receipt,synthetic_manifest,'blob1',wrong_source_event,head,head,False,expected_workflow_path='.github/workflows/source-package-successor-validation.yml',allowed_workflow_events=['push','workflow_dispatch'])
    cases.append({'case':'source_unregistered_workflow_event_blocked','expected':'BLOCKED','actual':wrong_event.get('status'),'ok':wrong_event.get('status')=='BLOCKED'})
    wrong_source_branch=dict(synthetic_run); wrong_source_branch['head_branch']='other'
    wrong_branch=evaluate_snapshot(synthetic_receipt,synthetic_manifest,'blob1',wrong_source_branch,head,head,False,expected_workflow_path='.github/workflows/source-package-successor-validation.yml',allowed_workflow_events=['push','workflow_dispatch'])
    cases.append({'case':'source_wrong_branch_cannot_substitute_candidate_run','expected':'BLOCKED','actual':wrong_branch.get('status'),'ok':wrong_branch.get('status')=='BLOCKED'})
    moved=evaluate_snapshot(synthetic_receipt,synthetic_manifest,'blob1',synthetic_run,head,'c'*40,False,expected_workflow_path='.github/workflows/source-package-successor-validation.yml',allowed_workflow_events=['push','workflow_dispatch'])
    cases.append({'case':'source_branch_move_invalidates_source_snapshot','expected':'BLOCKED','actual':moved.get('status'),'ok':moved.get('status')=='BLOCKED'})
    ok=all(x['ok'] for x in cases)
    print(json.dumps({'self_test':'PASS' if ok else 'FAIL','cases':cases},ensure_ascii=False,sort_keys=True))
    return 0 if ok else 1

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--self-test',action='store_true')
    ap.add_argument('--repository')
    ap.add_argument('--token')
    ap.add_argument('--independent-evaluator-evidence')
    ap.add_argument('--independent-evaluator-evidence-ref')
    args=ap.parse_args()
    if args.self_test:
        return self_test()

    registry=load_yaml(REGISTRY)
    roles=registry.get('branch_role_contract') or {}
    branch=str(registry.get('branch') or '')
    if roles.get(branch)!='GOVERNANCE_REVISION_CANDIDATE':
        print(json.dumps({'status':'BLOCKED','reason':'NOT_GOVERNANCE_REVISION_CANDIDATE'},ensure_ascii=False))
        return 1
    contract=registry.get('candidate_validation_contract') or {}
    if contract.get('promotion_readiness_mode')!='READ_ONLY_FAIL_CLOSED' or contract.get('promotion_readiness_may_mutate_or_promote') is not False:
        print(json.dumps({'status':'BLOCKED','reason':'PROMOTION_READINESS_CONTRACT_DRIFT'},ensure_ascii=False))
        return 1
    resolved=resolve_governance()
    if resolved.get('governance_release_state')!='CANDIDATE_NOT_PROMOTED' or resolved.get('released_current_authority') is not False:
        print(json.dumps({'status':'BLOCKED','reason':'CANDIDATE_RELEASE_STATE_INVALID'},ensure_ascii=False))
        return 1

    head=current_head()
    repository=args.repository or os.environ.get('GITHUB_REPOSITORY','').strip()
    token=args.token or os.environ.get('GITHUB_TOKEN','').strip() or None
    if not repository:
        print(json.dumps({'status':'BLOCKED','reason':'GITHUB_REPOSITORY_REQUIRED'},ensure_ascii=False))
        return 1
    try:
        live_head_before=fetch_live_branch_head(repository,branch,token)
    except Exception as exc:
        print(json.dumps({'status':'BLOCKED','reason':'LIVE_BRANCH_HEAD_QUERY_FAILED','detail':type(exc).__name__+':'+str(exc)},ensure_ascii=False))
        return 1
    if live_head_before!=head:
        print(json.dumps({'status':'BLOCKED','reason':'VALIDATION_HEAD_IS_NOT_LIVE_BRANCH_HEAD','local_head':head,'live_branch_head':live_head_before},ensure_ascii=False))
        return 1
    try:
        runs=fetch_runs(repository,branch,head,token)
    except Exception as exc:
        print(json.dumps({'status':'BLOCKED','reason':'WORKFLOW_RUN_QUERY_FAILED','detail':type(exc).__name__+':'+str(exc)},ensure_ascii=False))
        return 1
    required_names=list(map(str,contract.get('required_workflow_names') or []))
    required_bindings=contract.get('required_workflow_bindings') or {}
    if set(required_bindings)!=set(required_names):
        print(json.dumps({'status':'BLOCKED','reason':'REQUIRED_WORKFLOW_BINDING_DENOMINATOR_DRIFT'},ensure_ascii=False)); return 1
    workflow_result=evaluate_workflow_readiness(required_bindings,head,branch,runs)

    evidence_ref=args.independent_evaluator_evidence_ref or os.environ.get('INDEPENDENT_AUDITOR_EVIDENCE_REF','').strip()
    evidence_arg=args.independent_evaluator_evidence or os.environ.get('INDEPENDENT_AUDITOR_EVIDENCE','').strip()
    try:
        if evidence_ref:
            auditor_result=evaluate_independent_auditors_external(evidence_ref,repository,token,registry,head)
        else:
            auditor_result=evaluate_independent_auditors_local(Path(evidence_arg) if evidence_arg else None)
    except Exception as exc:
        auditor_result={'status':'FAIL','reason':'INDEPENDENT_AUDITOR_EVIDENCE_INVALID','detail':type(exc).__name__+':'+str(exc)}

    try:
        if contract.get('source_package_integration_mode')=='SINGLE_BRANCH_INTEGRATED':
            source_result=evaluate_integrated_source_readiness(contract,head,branch,runs)
        else:
            source_result=validate_source_successor(repository,token,contract,require_external_trust=True)
    except Exception as exc:
        source_result={'status':'BLOCKED','failures':['SOURCE_PROMOTION_GATE_EXCEPTION:'+type(exc).__name__+':'+str(exc)]}

    try:
        live_head_after=fetch_live_branch_head(repository,branch,token)
    except Exception as exc:
        print(json.dumps({'status':'BLOCKED','reason':'LIVE_BRANCH_HEAD_RECHECK_FAILED','detail':type(exc).__name__+':'+str(exc)},ensure_ascii=False))
        return 1
    if live_head_after!=head or live_head_after!=live_head_before:
        print(json.dumps({'status':'BLOCKED','reason':'SNAPSHOT_INVALIDATED_BY_BRANCH_HEAD_CHANGE','local_head':head,'live_head_before':live_head_before,'live_head_after':live_head_after},ensure_ascii=False))
        return 1

    ready=(
      workflow_result.get('status')=='PASS'
      and auditor_result.get('status')=='PASS'
      and source_result.get('status')=='PASS'
    )
    result={
      'artifact_type':'GOVERNANCE_CANDIDATE_PROMOTION_READINESS',
      'read_only':True,
      'mutation_or_promotion_performed':False,
      'candidate_branch':branch,
      'candidate_head_sha':head,
      'live_branch_head_before':live_head_before,
      'live_branch_head_after':live_head_after,
      'governance_uid':resolved.get('governance_uid'),
      'governance_revision':resolved.get('governance_revision'),
      'workflow_validation':workflow_result,
      'independent_auditor_validation':auditor_result,
      'source_package_successor_validation':source_result,
      'status':'READY_FOR_EXPLICIT_PROMOTION' if ready else 'BLOCKED',
      'explicit_promotion_still_required':True,
      'product_completion_credit':0,
    }
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    return 0 if ready else 1


if __name__=='__main__':
    raise SystemExit(main())
