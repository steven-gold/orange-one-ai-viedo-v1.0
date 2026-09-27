#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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


def evaluate_workflow_readiness(required_names:list[str], head_sha:str, runs:list[dict]) -> dict:
    rows=[]
    for name in required_names:
        matches=[r for r in runs if str(r.get('name') or '')==name and str(r.get('head_sha') or '')==head_sha]
        matches.sort(key=lambda r:str(r.get('created_at') or ''),reverse=True)
        if not matches:
            rows.append({'workflow_name':name,'status':'MISSING_EXACT_HEAD_RUN'})
            continue
        row=matches[0]
        status=str(row.get('status') or '')
        conclusion=str(row.get('conclusion') or '')
        ready=status=='completed' and conclusion=='success'
        rows.append({
          'workflow_name':name,
          'run_id':row.get('id'),
          'head_sha':row.get('head_sha'),
          'status':status,
          'conclusion':conclusion,
          'ready':ready,
        })
    return {
      'required_workflow_count':len(required_names),
      'ready_workflow_count':sum(1 for r in rows if r.get('ready') is True),
      'rows':rows,
      'status':'PASS' if rows and all(r.get('ready') is True for r in rows) else 'BLOCKED',
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


def evaluate_independent_auditors(evidence_path:Path|None) -> dict:
    ctx=audit_engine.load_context()
    if evidence_path is None:
        return {
          'status':'NOT_VERIFIED',
          'reason':'INDEPENDENT_AUDITOR_EVIDENCE_REQUIRED',
          'required_count':3,
        }
    p=evidence_path.resolve()
    records=audit_engine.load_independent_evaluator_evidence(p)
    return audit_engine.validate_independent_evaluator_implementations(ctx,records,p.parent)


def self_test() -> int:
    head='a'*40
    names=['Current Governance Cleanup Validation','Mother Spec Neutrality Audit']
    cases=[]
    def add(name,runs,expected):
        result=evaluate_workflow_readiness(names,head,runs)
        ok=result['status']==expected
        cases.append({'case':name,'expected':expected,'actual':result['status'],'ok':ok})
    add('missing_one_workflow',[
      {'id':1,'name':names[0],'head_sha':head,'status':'completed','conclusion':'success','created_at':'2026-01-01T00:00:00Z'}
    ],'BLOCKED')
    add('historical_head_cannot_substitute',[
      {'id':1,'name':names[0],'head_sha':'b'*40,'status':'completed','conclusion':'success','created_at':'2026-01-01T00:00:00Z'},
      {'id':2,'name':names[1],'head_sha':'b'*40,'status':'completed','conclusion':'success','created_at':'2026-01-01T00:00:00Z'}
    ],'BLOCKED')
    add('in_progress_cannot_substitute_terminal',[
      {'id':1,'name':names[0],'head_sha':head,'status':'in_progress','conclusion':None,'created_at':'2026-01-01T00:00:00Z'},
      {'id':2,'name':names[1],'head_sha':head,'status':'completed','conclusion':'success','created_at':'2026-01-01T00:00:00Z'}
    ],'BLOCKED')
    add('exact_head_terminal_success',[
      {'id':1,'name':names[0],'head_sha':head,'status':'completed','conclusion':'success','created_at':'2026-01-01T00:00:00Z'},
      {'id':2,'name':names[1],'head_sha':head,'status':'completed','conclusion':'success','created_at':'2026-01-01T00:00:00Z'}
    ],'PASS')
    live_head_cases=[
      {'case':'local_equals_live_before_and_after','local':head,'before':head,'after':head,'expected':True},
      {'case':'historical_local_head_blocked','local':head,'before':'b'*40,'after':'b'*40,'expected':False},
      {'case':'branch_moves_during_validation_blocked','local':head,'before':head,'after':'c'*40,'expected':False},
    ]
    for row in live_head_cases:
        row['actual']=(row['local']==row['before']==row['after'])
        row['ok']=row['actual']==row['expected']
    cases.extend(live_head_cases)
    synthetic_receipt={
      'candidate_source_branch':'source-candidate','source_head_sha':head,
      'source_validation_workflow_name':'Source Package Successor Validation',
      'source_validation_run_id':77,'source_validation_status':'completed',
      'source_validation_conclusion':'success','source_internal_status':'PASS_INTERNAL_UNSIGNED',
      'source_candidate_manifest_blob_sha':'blob1','released_current_authority':False,
      'external_trust_status':'NOT_SIGNED','external_trust_evidence_ref':None,
    }
    synthetic_manifest={
      'status':'UNSIGNED_NOT_CURRENT','current_authority':False,
      'external_trust':{'status':'NOT_SIGNED','candidate_self_sign':'FORBIDDEN'}
    }
    synthetic_run={'id':77,'name':'Source Package Successor Validation','head_sha':head,'status':'completed','conclusion':'success'}
    internal=evaluate_snapshot(synthetic_receipt,synthetic_manifest,'blob1',synthetic_run,head,head,False)
    cases.append({'case':'source_internal_unsigned_valid_for_candidate_validation','expected':'PASS_INTERNAL_UNSIGNED','actual':internal.get('status'),'ok':internal.get('status')=='PASS_INTERNAL_UNSIGNED'})
    promotion=evaluate_snapshot(synthetic_receipt,synthetic_manifest,'blob1',synthetic_run,head,head,True)
    cases.append({'case':'source_unsigned_blocks_promotion','expected':'BLOCKED','actual':promotion.get('status'),'ok':promotion.get('status')=='BLOCKED'})
    signed_receipt=dict(synthetic_receipt)
    signed_receipt.update({'source_internal_status':'PASS_INTERNAL_SIGNED','external_trust_status':'SIGNED_PASS','external_trust_evidence_ref':'external://receipt'})
    signed_manifest={
      'status':'SIGNED_NOT_CURRENT','current_authority':False,
      'external_trust':{
        'status':'SIGNED_PASS','candidate_self_sign':'FORBIDDEN',
        'signer_identity':'SIGNER-1','signer_authority_ref':'AUTH-1',
        'signature_or_immutable_receipt_ref':'external://receipt'
      }
    }
    signed_unverified=evaluate_snapshot(signed_receipt,signed_manifest,'blob1',synthetic_run,head,head,True)
    cases.append({'case':'source_signed_self_declaration_without_machine_verification_blocked','expected':'BLOCKED','actual':signed_unverified.get('status'),'ok':signed_unverified.get('status')=='BLOCKED'})
    signed=evaluate_snapshot(
      signed_receipt,signed_manifest,'blob1',synthetic_run,head,head,True,
      {'status':'PASS','signer_identity':'SIGNER-1','mutation_actor_count':2,'failures':[]}
    )
    cases.append({'case':'source_signed_exact_head_with_machine_verified_independent_trust_satisfies_source_gate','expected':'PASS','actual':signed.get('status'),'ok':signed.get('status')=='PASS'})
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
    workflow_result=evaluate_workflow_readiness(list(map(str,contract.get('required_workflow_names') or [])),head,runs)

    evidence_arg=args.independent_evaluator_evidence or os.environ.get('INDEPENDENT_AUDITOR_EVIDENCE','').strip()
    try:
        auditor_result=evaluate_independent_auditors(Path(evidence_arg) if evidence_arg else None)
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
