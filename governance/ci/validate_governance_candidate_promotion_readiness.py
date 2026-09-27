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
from source_package_successor_admission import evaluate_snapshot, validate_source_successor


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

def candidate_mutation_actors(repository:str,base:str,head:str,token:str|None)->set[str]:
    payload=api_json(f'https://api.github.com/repos/{repository}/compare/{base}...{head}?per_page=100',token)
    actors=set()
    for c in payload.get('commits') or []:
        for k in ('author','committer'):
            x=str(((c.get(k) or {}).get('login')) or '').strip()
            if x: actors.add(x)
    if not actors: raise RuntimeError('CANDIDATE_MUTATION_ACTOR_SET_EMPTY')
    return actors

def canonical_candidate_audit_snapshot(registry:dict,repository:str,candidate_head:str)->tuple[str,dict]:
    ident=registry.get('governance_identity') or {}
    vc=registry.get('candidate_validation_contract') or {}
    receipt_rel=str(vc.get('source_package_successor_admission_receipt') or '')
    receipt=load_yaml(ROOT/receipt_rel)
    snapshot={
      'repository':repository,
      'candidate_branch':str(registry.get('branch') or ''),
      'candidate_head_sha':candidate_head,
      'governance_uid':str(ident.get('governance_uid') or ''),
      'governance_revision':str(ident.get('governance_revision') or ''),
      'specification_bundle_sha256':str(ident.get('specification_bundle_sha256') or ''),
      'canonical_rule_registry_digest':str(ident.get('canonical_rule_registry_digest') or ''),
      'source_package_branch':str(receipt.get('candidate_source_branch') or ''),
      'source_package_head_sha':str(receipt.get('source_head_sha') or ''),
      'source_package_manifest_blob_sha':str(receipt.get('source_candidate_manifest_blob_sha') or ''),
    }
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
    req=set(map(str,vc.get('independent_auditor_required_provenance_fields') or []))
    expected_req={'implementation_provenance_ref','execution_receipt_provenance_ref','result_artifact_provenance_ref','evaluator_authority_ref'}
    if vc.get('independent_auditor_external_provenance_required') is not True or req!=expected_req:
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_PROVENANCE_CONTRACT_DRIFT'}
    if vc.get('independent_auditor_snapshot_hash_mode')!='SHA256_CANONICAL_JSON_CURRENT_CANDIDATE_SOURCE_SNAPSHOT_V1':
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_SNAPSHOT_HASH_MODE_DRIFT'}
    if vc.get('independent_auditor_result_fingerprint_mode')!='SHA256_CANONICAL_JSON_CANONICAL_RESULT_V1':
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_RESULT_FINGERPRINT_MODE_DRIFT'}
    ident=registry.get('governance_identity') or {}
    primary=fetch_issue(str(ident.get('authorization_record_url') or ''),token)
    primary_actor=str(((primary.get('user') or {}).get('login')) or '')
    mutations=candidate_mutation_actors(repository,str(ident.get('predecessor_head_sha') or ''),candidate_head,token)
    expected_snapshot_hash,snapshot=canonical_candidate_audit_snapshot(registry,repository,candidate_head)
    actors=[]; result_fingerprints=[]; rows=[]
    for i,r in enumerate(records):
        miss=[f for f in req if not str(r.get(f) or '').strip()]
        if miss: return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_PROVENANCE_FIELD_MISSING','index':i,'fields':miss}
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
            auth_dt=datetime.fromisoformat(str(auth.get('created_at') or '').replace('Z','+00:00')).astimezone(timezone.utc)
            first_evidence_dt=min(
              datetime.fromisoformat(t.replace('Z','+00:00')).astimezone(timezone.utc)
              for t in (impl_time,receipt_time,result_time)
            )
        except Exception:
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_AUTHORITY_TIME_INVALID','index':i}
        if not auth_dt < first_evidence_dt:
            return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_AUTHORITY_NOT_PREEXISTING_EVIDENCE','index':i}
        actors.append(ia); result_fingerprints.append(actual_result_fp)
        rows.append({'evaluator_uid':r.get('evaluator_uid'),'provenance_actor':ia,'implementation_sha256':impl_hash,'audit_snapshot_hash':expected_snapshot_hash,'result_fingerprint':actual_result_fp})
    if len(set(actors))!=3:
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_PROVENANCE_ACTORS_NOT_DISTINCT','actors':actors}
    if len(set(result_fingerprints))!=1:
        return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_RESULT_ARTIFACTS_NOT_IDENTICAL','fingerprints':result_fingerprints}
    return {'status':'PASS','independent_provenance_actor_count':3,'audit_snapshot_hash':expected_snapshot_hash,'canonical_snapshot':snapshot,'result_fingerprint':result_fingerprints[0],'rows':rows}

def evaluate_independent_auditors(evidence_path:Path|None,repository=None,token=None,registry=None,candidate_head=None) -> dict:
    ctx=audit_engine.load_context()
    if evidence_path is None:
        return {
          'status':'NOT_VERIFIED',
          'reason':'INDEPENDENT_AUDITOR_EVIDENCE_REQUIRED',
          'required_count':3,
        }
    p=evidence_path.resolve()
    records=audit_engine.load_independent_evaluator_evidence(p)
    base=audit_engine.validate_independent_evaluator_implementations(ctx,records,p.parent)
    if base.get('status')!='PASS': return base
    if not repository or registry is None or not candidate_head: return {'status':'FAIL','reason':'INDEPENDENT_AUDITOR_PROVENANCE_CONTEXT_REQUIRED'}
    prov=validate_independent_auditor_provenance(records,repository,token,registry,candidate_head)
    return {'status':'PASS','base_validation':base,'provenance_validation':prov} if prov.get('status')=='PASS' else prov


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
    add('same_name_wrong_workflow_path_blocked',[run(1,names[0],path='.github/workflows/fake.yml'),run(2,names[1])],'BLOCKED')
    add('manual_dispatch_cannot_substitute_push_gate',[run(1,names[0],event='workflow_dispatch'),run(2,names[1])],'BLOCKED')
    add('wrong_head_branch_cannot_substitute_candidate_run',[run(1,names[0],head_branch='other'),run(2,names[1])],'BLOCKED')
    for row in [
      {'case':'local_equals_live_before_and_after','local':head,'before':head,'after':head,'expected':True},
      {'case':'historical_local_head_blocked','local':head,'before':'b'*40,'after':'b'*40,'expected':False},
      {'case':'branch_moves_during_validation_blocked','local':head,'before':head,'after':'c'*40,'expected':False},
    ]:
        row['actual']=(row['local']==row['before']==row['after']); row['ok']=row['actual']==row['expected']; cases.append(row)
    synthetic_receipt={'candidate_source_branch':'source-candidate','source_head_sha':head,'source_validation_workflow_name':'Source Package Successor Validation','source_validation_run_id':77,'source_validation_status':'completed','source_validation_conclusion':'success','source_internal_status':'PASS_INTERNAL_UNSIGNED','source_candidate_manifest_blob_sha':'blob1','released_current_authority':False,'external_trust_status':'NOT_SIGNED','external_trust_evidence_ref':None}
    synthetic_manifest={'status':'UNSIGNED_NOT_CURRENT','current_authority':False,'external_trust':{'status':'NOT_SIGNED','candidate_self_sign':'FORBIDDEN'}}
    synthetic_run={'id':77,'name':'Source Package Successor Validation','head_sha':head,'status':'completed','conclusion':'success'}
    internal=evaluate_snapshot(synthetic_receipt,synthetic_manifest,'blob1',synthetic_run,head,head,False)
    cases.append({'case':'source_internal_unsigned_valid_for_candidate_validation','expected':'PASS_INTERNAL_UNSIGNED','actual':internal.get('status'),'ok':internal.get('status')=='PASS_INTERNAL_UNSIGNED'})
    promotion=evaluate_snapshot(synthetic_receipt,synthetic_manifest,'blob1',synthetic_run,head,head,True)
    cases.append({'case':'source_unsigned_blocks_promotion','expected':'BLOCKED','actual':promotion.get('status'),'ok':promotion.get('status')=='BLOCKED'})
    signed_receipt=dict(synthetic_receipt); signed_receipt.update({'source_internal_status':'PASS_INTERNAL_SIGNED','external_trust_status':'SIGNED_PASS','external_trust_evidence_ref':'external://receipt'})
    signed=evaluate_snapshot(signed_receipt,synthetic_manifest,'blob1',synthetic_run,head,head,True,{'status':'PASS','signer_identity':'SIGNER-1','mutation_actor_count':2,'failures':[]})
    cases.append({'case':'external_trust_envelope_allows_frozen_source_content','expected':'PASS','actual':signed.get('status'),'ok':signed.get('status')=='PASS'})
    moved=evaluate_snapshot(synthetic_receipt,synthetic_manifest,'blob1',synthetic_run,head,'c'*40,False)
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

    evidence_arg=args.independent_evaluator_evidence or os.environ.get('INDEPENDENT_AUDITOR_EVIDENCE','').strip()
    try:
        auditor_result=evaluate_independent_auditors(Path(evidence_arg) if evidence_arg else None,repository=repository,token=token,registry=registry,candidate_head=head)
    except Exception as exc:
        auditor_result={'status':'FAIL','reason':'INDEPENDENT_AUDITOR_EVIDENCE_INVALID','detail':type(exc).__name__+':'+str(exc)}

    try:
        source_result=validate_source_successor(repository,token,contract,require_external_trust=True)
    except Exception as exc:
        source_result={'status':'BLOCKED','failures':['SOURCE_SUCCESSOR_PROMOTION_GATE_EXCEPTION:'+type(exc).__name__+':'+str(exc)]}

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
