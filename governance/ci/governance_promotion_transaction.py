#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, json, os, re, subprocess, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/'governance/specifications/REGISTRY.yaml'
MAN=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'
LOCK=ROOT/'governance/BRANCH_AUTHORITY_LOCK.yaml'
READY=ROOT/'governance/ci/validate_governance_candidate_promotion_readiness.py'
SELF='governance/ci/governance_promotion_transaction.py'
RECEIPT='governance/release/RELEASE_RECEIPT.yaml'
HANDOFF='governance/release/FRESH_REVERIFY_HANDOFF.yaml'
MARK='EXPLICIT_PROMOTION_AUTHORIZED'

def ly(p):
    d=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(d,dict): raise RuntimeError('YAML_MAPPING_REQUIRED:'+str(p))
    return d

def dy(d): return yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=120)
def git(*a): return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
def parts(repo):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo): raise RuntimeError('GITHUB_REPOSITORY_INVALID')
    return repo.split('/',1)

def api(url,token=None,method='GET',payload=None):
    h={'Accept':'application/vnd.github+json','User-Agent':'ACPOS-Governance-Promotion','X-GitHub-Api-Version':'2022-11-28'}
    if token: h['Authorization']='Bearer '+token
    body=None
    if payload is not None:
        body=json.dumps(payload,separators=(',',':'),ensure_ascii=False).encode(); h['Content-Type']='application/json'
    with urllib.request.urlopen(urllib.request.Request(url,headers=h,data=body,method=method),timeout=30) as r:
        raw=r.read().decode()
    return json.loads(raw) if raw else {}

def branch_head(repo,branch,token):
    o,r=parts(repo); b=urllib.parse.quote(branch,safe='')
    sha=str(((api(f'https://api.github.com/repos/{o}/{r}/branches/{b}',token).get('commit') or {}).get('sha')) or '')
    if not re.fullmatch(r'[0-9a-f]{40}',sha): raise RuntimeError('LIVE_BRANCH_HEAD_INVALID')
    return sha

def issue(url,token,repo):
    m=re.fullmatch(r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)',url)
    if not m or f'{m[1]}/{m[2]}'!=repo: raise RuntimeError('PROMOTION_AUTHORIZATION_URL_OR_REPOSITORY_INVALID')
    return api(f'https://api.github.com/repos/{m[1]}/{m[2]}/issues/{m[3]}',token)

def auth_ok(i,actor,head,branch,uid,rev):
    body=str(i.get('body') or ''); got=str(((i.get('user') or {}).get('login')) or '')
    miss=[x for x in [MARK,head,branch,uid,rev] if x not in body]
    if got!=actor:return {'status':'BLOCKED','reason':'PROMOTION_AUTHORIZATION_ACTOR_MISMATCH'}
    if str(i.get('state') or '')!='open':return {'status':'BLOCKED','reason':'PROMOTION_AUTHORIZATION_NOT_OPEN'}
    if miss:return {'status':'BLOCKED','reason':'PROMOTION_AUTHORIZATION_SCOPE_MISSING','missing':miss}
    return {'status':'PASS'}

def contract_ok(reg):
    c=reg.get('candidate_validation_contract') or {}
    exact={
      'promotion_transaction_executor':SELF,
      'promotion_transaction_mode':'SAME_BRANCH_ATOMIC_PROMOTION_COMMIT',
      'promotion_transaction_candidate_branch_mutation':'ALLOWED_ONLY_AT_ATOMIC_PROMOTION_COMMIT',
      'promotion_transaction_predecessor_history_mutation':'FORBIDDEN',
      'promotion_transaction_atomic_visibility_point':'ACTIVE_GOVERNANCE_REF_FAST_FORWARD',
      'promotion_transaction_release_receipt_path':RECEIPT,
      'promotion_transaction_reverify_handoff_path':HANDOFF,
      'promotion_transaction_product_completion_credit':0,
    }
    bad=[k for k,v in exact.items() if c.get(k)!=v]
    for k in ['promotion_transaction_requires_explicit_promotion_authorization','promotion_transaction_requires_fresh_readiness','promotion_transaction_requires_integrated_source_validation','promotion_transaction_requires_independent_auditor_evidence','promotion_transaction_requires_new_release_uid','promotion_transaction_execution_authorization_must_be_distinct_from_implementation_authorization','promotion_transaction_pre_publish_reconciliation_required','promotion_transaction_post_write_reconciliation_required','promotion_transaction_release_delta_exact','promotion_transaction_fresh_reverify_handoff_required','promotion_transaction_post_promotion_same_branch_reverify_supported']:
        if c.get(k) is not True: bad.append(k)
    if c.get('promotion_transaction_requires_source_external_trust') is not False:
        bad.append('promotion_transaction_requires_source_external_trust')
    if c.get('source_package_integration_mode')!='SINGLE_BRANCH_INTEGRATED' or c.get('source_package_successor_required') is not False:
        bad.append('single_branch_integrated_source_contract')
    if c.get('promotion_transaction_branch_fanout')!='FORBIDDEN':
        bad.append('promotion_transaction_branch_fanout')
    if c.get('promotion_transaction_in_place_branch')!=str(reg.get('branch') or ''):
        bad.append('promotion_transaction_in_place_branch')
    if c.get('promotion_transaction_single_branch_authorization_record')!='https://github.com/steven-gold/orange-one-ai-viedo-v1.0/issues/57':
        bad.append('promotion_transaction_single_branch_authorization_record')
    if not re.fullmatch(r'https://github\.com/[^/]+/[^/]+/issues/\d+',str(c.get('promotion_transaction_implementation_authorization_record') or '')): bad.append('promotion_transaction_implementation_authorization_record')
    return {'status':'PASS' if not bad else 'BLOCKED','failures':sorted(set(bad))}

def readiness(ref,token):
    e=os.environ.copy(); e['GITHUB_TOKEN']=token
    p=subprocess.run([sys.executable,str(READY),'--independent-evaluator-evidence-ref',ref],cwd=ROOT,env=e,text=True,capture_output=True)
    try:d=json.loads(p.stdout)
    except Exception:return {'status':'BLOCKED','reason':'PROMOTION_READINESS_OUTPUT_UNPARSEABLE','stderr':p.stderr[-3000:]}
    return {'status':'PASS','readiness':d} if p.returncode==0 and d.get('status')=='READY_FOR_EXPLICIT_PROMOTION' else {'status':'BLOCKED','reason':'PROMOTION_READINESS_NOT_READY','readiness':d}

def digest(man_text):
    root=ROOT/'governance/specifications/current'; h=hashlib.sha256()
    for p in sorted(x for x in root.rglob('*') if x.is_file()):
        rel=p.relative_to(root).as_posix(); data=man_text.encode() if p==MAN else p.read_bytes()
        h.update(rel.encode());h.update(b'\0');h.update(data);h.update(b'\0')
    return h.hexdigest()

def docs(reg,man,lock,head,tree,rbranch,uid,rev,authref,audref,rd):
    reg=json.loads(json.dumps(reg));man=json.loads(json.dumps(man));lock=json.loads(json.dumps(lock))
    cbranch=str(reg.get('branch') or ''); ident=reg.get('governance_identity') or {}; cuid=str(ident.get('governance_uid') or ''); disp=str(ident.get('display_version') or '')
    reg.setdefault('branch_role_contract',{})[rbranch]='IMMUTABLE_GOVERNANCE_RULESET';reg['branch']=rbranch;reg['registry_role']='GOVERNANCE_RELEASED_ENTRYPOINT';reg['status']='CURRENT_RELEASED'
    ident=reg.setdefault('governance_identity',{});ident.update({'governance_uid':uid,'governance_revision':rev,'status':'RELEASED','identity_state':'IMMUTABLE_RELEASED','released_immutable_identity':True,'promotion_candidate_branch':cbranch,'promotion_candidate_head_sha':head,'promotion_candidate_tree_sha':tree,'promotion_authorization_record_url':authref,'candidate_governance_uid':cuid})
    cv=reg.setdefault('candidate_validation_contract',{});cv.update({'candidate_rule_bundle_release_state':'RELEASED_CURRENT','candidate_rule_bundle_released_current_authority':True,'release_branch':rbranch,'release_governance_uid':uid,'release_governance_revision':rev,'release_candidate_head_sha':head,'release_promotion_authorization_ref':authref,'release_independent_auditor_evidence_ref':audref})
    man.update({'artifact_uid':uid,'branch_release_state':'RELEASED_CURRENT','released_current_authority':True,'candidate_branch_local_current_rule_bundle':False,'version_role':'RELEASED_GOVERNANCE_DISPLAY_VERSION'})
    sl=man.setdefault('source_lineage',{});sl.update({'lineage_authority_source':'governance/specifications/REGISTRY.yaml#governance_identity','lineage_projection_role':'NON_NORMATIVE_PROVENANCE_ONLY','concrete_repository_branch_head_or_issue_reference_may_define_common_policy':False,'promotion_transaction_evidence_source':'governance/release/RELEASE_RECEIPT.yaml','post_promotion_projector_sync_authorization_uid':'PROMOTION_TRANSACTION','post_promotion_projector_sync_authorization_state':'REVERIFY_REQUIRED'})
    mt=dy(man); ident['specification_bundle_sha256']=digest(mt); cv['specification_bundle_sha256']=ident['specification_bundle_sha256'];cv['candidate_manifest_artifact_uid_expected']=uid;cv['candidate_manifest_display_version_expected']=disp
    lock.setdefault('branches',{})[rbranch]={'role':'IMMUTABLE_GOVERNANCE_RULESET','preserve':True,'gpt_write_policy':'FORBIDDEN','product_execution':'FORBIDDEN','additions':'FORBIDDEN','modifications':'FORBIDDEN','deletions':'FORBIDDEN','single_branch_release':True,'promotion_candidate_head_sha':head,'promotion_authorization_record':authref}
    rec={'schema_version':1,'artifact_type':'GOVERNANCE_RELEASE_RECEIPT','status':'PROMOTED_PENDING_FRESH_REVERIFY','authority':False,'candidate_branch':cbranch,'candidate_head_sha':head,'candidate_tree_sha':tree,'candidate_governance_uid':cuid,'release_branch':rbranch,'released_governance_uid':uid,'released_governance_revision':rev,'display_version':disp,'canonical_rule_registry_uid':str(ident.get('canonical_rule_registry_uid') or ''),'canonical_rule_registry_digest':str(ident.get('canonical_rule_registry_digest') or ''),'promotion_authorization_ref':authref,'independent_auditor_evidence_ref':audref,'workflow_validation':rd.get('workflow_validation') or {},'source_package_successor_validation':rd.get('source_package_successor_validation') or {},'integrated_source_validation':rd.get('source_package_successor_validation') or {},'independent_auditor_validation':rd.get('independent_auditor_validation') or {},'self_commit_reference_forbidden':True,'product_completion_credit':0,'fresh_reverification_required':True}
    hand={'schema_version':1,'artifact_type':'GOVERNANCE_POST_PROMOTION_REVERIFY_HANDOFF','status':'REVERIFY_REQUIRED','released_governance_uid':uid,'released_governance_revision':rev,'release_branch':rbranch,'source_candidate_head_sha':head,'reason':'GOVERNANCE_PROMOTION_INVALIDATES_AFFECTED_OLD_CLOSURE_EVIDENCE','required_next_actions':['VERIFY_PERSISTED_RELEASE_BRANCH_HEAD','VERIFY_ACTIVE_CONSUMER_PROJECTIONS','RUN_CONTAMINATION_CONTRADICTION_PORTABILITY_GATES','RUN_GOVERNANCE_REGRESSION_AND_STRESS_GATES','FRESHLY_REVERIFY_AFFECTED_EXECUTION_SCOPE'],'product_execution_authorized':False,'product_completion_credit':0}
    return {'governance/specifications/REGISTRY.yaml':dy(reg),'governance/specifications/current/SPECIFICATION_MANIFEST.yaml':mt,'governance/BRANCH_AUTHORITY_LOCK.yaml':dy(lock),RECEIPT:dy(rec),HANDOFF:dy(hand)}

def blob(repo,token,text):
    o,r=parts(repo);s=str(api(f'https://api.github.com/repos/{o}/{r}/git/blobs',token,'POST',{'content':text,'encoding':'utf-8'}).get('sha') or '')
    if not re.fullmatch(r'[0-9a-f]{40}',s):raise RuntimeError('CREATE_BLOB_SHA_INVALID')
    return s

def tree(repo,token,base,files):
    o,r=parts(repo); ents=[{'path':p,'mode':'100644','type':'blob','sha':blob(repo,token,t)} for p,t in sorted(files.items())]
    s=str(api(f'https://api.github.com/repos/{o}/{r}/git/trees',token,'POST',{'base_tree':base,'tree':ents}).get('sha') or '')
    if not re.fullmatch(r'[0-9a-f]{40}',s):raise RuntimeError('CREATE_TREE_SHA_INVALID')
    return s

def commit(repo,token,tr,parent,msg):
    o,r=parts(repo);s=str(api(f'https://api.github.com/repos/{o}/{r}/git/commits',token,'POST',{'message':msg,'tree':tr,'parents':[parent]}).get('sha') or '')
    if not re.fullmatch(r'[0-9a-f]{40}',s):raise RuntimeError('CREATE_COMMIT_SHA_INVALID')
    return s

def ref(repo,token,branch):
    o,r=parts(repo);b=urllib.parse.quote(branch,safe='')
    try:d=api(f'https://api.github.com/repos/{o}/{r}/git/ref/heads/{b}',token)
    except urllib.error.HTTPError as e:
        if e.code==404:return None
        raise
    s=str(((d.get('object') or {}).get('sha')) or '');return s if re.fullmatch(r'[0-9a-f]{40}',s) else None

def update_ref(repo,token,branch,sha):
    o,r=parts(repo);b=urllib.parse.quote(branch,safe='')
    api(f'https://api.github.com/repos/{o}/{r}/git/refs/heads/{b}',token,'PATCH',{'sha':sha,'force':False})

def file_at(repo,token,branch,path):
    o,r=parts(repo);p='/'.join(urllib.parse.quote(x,safe='') for x in path.split('/'));q=urllib.parse.urlencode({'ref':branch})
    try:d=api(f'https://api.github.com/repos/{o}/{r}/contents/{p}?{q}',token)
    except urllib.error.HTTPError as e:
        if e.code==404:return None
        raise
    return base64.b64decode(str(d.get('content') or '')).decode()

def existing_in_place_release(repo,token,branch,head,uid,authref):
    h=ref(repo,token,branch)
    if not h:return {'status':'ABSENT'}
    txt=file_at(repo,token,branch,RECEIPT)
    if not txt:return {'status':'BLOCKED','reason':'EXISTING_RELEASE_BRANCH_RECEIPT_MISSING'}
    d=yaml.safe_load(txt) or {}; exp={'candidate_head_sha':head,'released_governance_uid':uid,'promotion_authorization_ref':authref}
    bad=[k for k,v in exp.items() if str(d.get(k) or '')!=v]
    return {'status':'ALREADY_PROMOTED_IDEMPOTENT','head':h} if not bad else {'status':'BLOCKED','reason':'EXISTING_RELEASE_BRANCH_IDENTITY_MISMATCH','fields':bad}

def reconcile_release_projection(repo,token,candidate_head,rbranch,rhead,uid,rev,authref,require_persisted_ref:bool):
    if require_persisted_ref and ref(repo,token,rbranch)!=rhead:
        return {'status':'BLOCKED','reason':'RELEASE_HEAD_NOT_PERSISTED'}
    o,r=parts(repo)
    cmp=api(f'https://api.github.com/repos/{o}/{r}/compare/{candidate_head}...{rhead}',token)
    expected={
      'governance/specifications/REGISTRY.yaml',
      'governance/specifications/current/SPECIFICATION_MANIFEST.yaml',
      'governance/BRANCH_AUTHORITY_LOCK.yaml',
      RECEIPT,HANDOFF,
    }
    got=set(str(x.get('filename') or '') for x in (cmp.get('files') or []))
    if str(cmp.get('status') or '')!='ahead' or int(cmp.get('total_commits') or 0)!=1 or got!=expected:
        return {'status':'BLOCKED','reason':'RELEASE_DELTA_NOT_EXACT','expected':sorted(expected),'actual':sorted(got),'total_commits':cmp.get('total_commits'),'compare_status':cmp.get('status')}
    docs={}
    try:
        for path in expected:
            raw=file_at(repo,token,rhead,path)
            doc=yaml.safe_load(raw or '') or {}
            if not isinstance(doc,dict): raise RuntimeError('MAPPING_REQUIRED:'+path)
            docs[path]=doc
    except Exception as exc:
        return {'status':'BLOCKED','reason':'RELEASE_PROJECTION_READ_FAILED','detail':type(exc).__name__+':'+str(exc)}
    rg=docs['governance/specifications/REGISTRY.yaml']; ident=rg.get('governance_identity') or {}
    man=docs['governance/specifications/current/SPECIFICATION_MANIFEST.yaml']
    lock=docs['governance/BRANCH_AUTHORITY_LOCK.yaml']; lr=(lock.get('branches') or {}).get(rbranch) or {}
    rec=docs[RECEIPT]; hand=docs[HANDOFF]
    checks={
      'registry_branch':str(rg.get('branch') or '')==rbranch,
      'registry_role':str((rg.get('branch_role_contract') or {}).get(rbranch) or '')=='IMMUTABLE_GOVERNANCE_RULESET',
      'registry_status':str(rg.get('status') or '')=='CURRENT_RELEASED',
      'identity_uid':str(ident.get('governance_uid') or '')==uid,
      'identity_revision':str(ident.get('governance_revision') or '')==rev,
      'identity_state':str(ident.get('identity_state') or '')=='IMMUTABLE_RELEASED' and ident.get('released_immutable_identity') is True,
      'manifest_uid':str(man.get('artifact_uid') or '')==uid,
      'manifest_release':str(man.get('branch_release_state') or '')=='RELEASED_CURRENT' and man.get('released_current_authority') is True,
      'branch_lock':str(lr.get('role') or '')=='IMMUTABLE_GOVERNANCE_RULESET' and lr.get('gpt_write_policy')=='FORBIDDEN' and lr.get('modifications')=='FORBIDDEN',
      'receipt_binding':str(rec.get('candidate_head_sha') or '')==candidate_head and str(rec.get('released_governance_uid') or '')==uid and str(rec.get('promotion_authorization_ref') or '')==authref and rec.get('fresh_reverification_required') is True,
      'handoff_binding':str(hand.get('released_governance_uid') or '')==uid and str(hand.get('release_branch') or '')==rbranch and hand.get('status')=='REVERIFY_REQUIRED' and hand.get('product_execution_authorized') is False,
    }
    bad=sorted(k for k,v in checks.items() if not v)
    return {
      'status':'PASS' if not bad else 'BLOCKED',
      'reason':None if not bad else 'RELEASE_PROJECTION_MISMATCH',
      'phase':'POST_WRITE' if require_persisted_ref else 'PRE_PUBLISH',
      'failed_checks':bad,
      'release_delta_paths':sorted(got),
      'release_head_sha':rhead,
    }

def prepublish_check(repo,token,candidate_head,rbranch,rhead,uid,rev,authref):
    return reconcile_release_projection(repo,token,candidate_head,rbranch,rhead,uid,rev,authref,False)

def postcheck(repo,token,candidate_head,rbranch,rhead,uid,rev,authref):
    return reconcile_release_projection(repo,token,candidate_head,rbranch,rhead,uid,rev,authref,True)

def selftest():
    i={'state':'open','user':{'login':'a'},'body':' '.join([MARK,'b'*40,'r','U','V'])}; a=auth_ok(i,'a','b'*40,'r','U','V')
    cases=[a.get('status')=='PASS',auth_ok(i,'x','b'*40,'r','U','V').get('status')=='BLOCKED',not RECEIPT.startswith('governance/specifications/current/')]
    if REG.is_file():
        reg=ly(REG); c=reg.get('candidate_validation_contract') or {}
        cases.extend([
          c.get('promotion_transaction_branch_fanout')=='FORBIDDEN',
          c.get('promotion_transaction_in_place_branch')==str(reg.get('branch') or ''),
          c.get('promotion_transaction_mode')=='SAME_BRANCH_ATOMIC_PROMOTION_COMMIT',
        ])
    if REG.is_file():cases.append(contract_ok(ly(REG)).get('status')=='PASS')
    print(json.dumps({'self_test':'PASS' if all(cases) else 'FAIL','cases':cases}));return 0 if all(cases) else 1

def main():
    p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true');p.add_argument('--execute',action='store_true');p.add_argument('--repository',default=os.environ.get('GITHUB_REPOSITORY',''));p.add_argument('--candidate-head',default='');p.add_argument('--release-branch',default='');p.add_argument('--release-governance-uid',default='');p.add_argument('--release-governance-revision',default='');p.add_argument('--promotion-authorization-ref',default='');p.add_argument('--independent-evaluator-evidence-ref',default='');a=p.parse_args()
    if a.self_test:return selftest()
    if not a.execute:print(json.dumps({'status':'BLOCKED','reason':'EXPLICIT_EXECUTE_FLAG_REQUIRED'}));return 2
    token=os.environ.get('GITHUB_TOKEN','').strip(); vals=vars(a); miss=[k for k in ['repository','candidate_head','release_governance_uid','release_governance_revision','promotion_authorization_ref','independent_evaluator_evidence_ref'] if not str(vals[k] or '').strip()]
    if not token or miss:print(json.dumps({'status':'BLOCKED','reason':'GITHUB_TOKEN_OR_INPUT_MISSING','fields':miss}));return 2
    if not re.fullmatch(r'[0-9a-f]{40}',a.candidate_head):print(json.dumps({'status':'BLOCKED','reason':'CANDIDATE_HEAD_INVALID'}));return 2
    reg=ly(REG); lock=ly(LOCK); ident=reg.get('governance_identity') or {}
    cbranch=str(reg.get('branch') or ''); roles=reg.get('branch_role_contract') or {}
    release_branch=cbranch
    if a.release_branch and a.release_branch!=cbranch:
        print(json.dumps({'status':'BLOCKED','reason':'BRANCH_FANOUT_FORBIDDEN','required_branch':cbranch,'requested_branch':a.release_branch}));return 2
    live_now=branch_head(a.repository,cbranch,token)
    if live_now!=a.candidate_head:
        ex=existing_in_place_release(a.repository,token,cbranch,a.candidate_head,a.release_governance_uid,a.promotion_authorization_ref)
        if ex.get('status')=='ALREADY_PROMOTED_IDEMPOTENT':
            pc=postcheck(a.repository,token,a.candidate_head,cbranch,str(ex.get('head') or ''),a.release_governance_uid,a.release_governance_revision,a.promotion_authorization_ref)
            out=dict(ex);out['post_write_reconciliation']=pc;print(json.dumps(out,sort_keys=True));return 0 if pc.get('status')=='PASS' else 2
        print(json.dumps({'status':'BLOCKED','reason':'CANDIDATE_HEAD_DRIFT','candidate_head':a.candidate_head,'live_head':live_now,'existing_release':ex}));return 2
    if a.release_governance_uid==str(ident.get('governance_uid') or '') or a.release_governance_revision==str(ident.get('governance_revision') or ''):
        print(json.dumps({'status':'BLOCKED','reason':'RELEASE_IDENTITY_NOT_NEW'}));return 2
    co=contract_ok(reg)
    if co.get('status')!='PASS':print(json.dumps({'status':'BLOCKED','reason':'PROMOTION_TRANSACTION_CONTRACT_DRIFT','detail':co}));return 2
    if roles.get(cbranch)!='GOVERNANCE_REVISION_CANDIDATE':print(json.dumps({'status':'BLOCKED','reason':'NOT_GOVERNANCE_REVISION_CANDIDATE'}));return 2
    local=git('rev-parse','HEAD')
    if local!=a.candidate_head:print(json.dumps({'status':'BLOCKED','reason':'LOCAL_CANDIDATE_HEAD_DRIFT','local_head':local,'candidate_head':a.candidate_head}));return 2
    primary=issue(str(ident.get('authorization_record_url') or ''),token,a.repository); actor=str(((primary.get('user') or {}).get('login')) or '')
    au=auth_ok(issue(a.promotion_authorization_ref,token,a.repository),actor,a.candidate_head,release_branch,a.release_governance_uid,a.release_governance_revision)
    if au.get('status')!='PASS':print(json.dumps(au));return 2
    rr=readiness(a.independent_evaluator_evidence_ref,token)
    if rr.get('status')!='PASS' or str((rr.get('readiness') or {}).get('candidate_head_sha') or '')!=a.candidate_head:print(json.dumps(rr));return 2
    if branch_head(a.repository,cbranch,token)!=a.candidate_head:print(json.dumps({'status':'BLOCKED','reason':'CANDIDATE_HEAD_MOVED_AFTER_READINESS'}));return 2
    base=git('rev-parse','HEAD^{tree}'); files=docs(reg,ly(MAN),lock,a.candidate_head,base,release_branch,a.release_governance_uid,a.release_governance_revision,a.promotion_authorization_ref,a.independent_evaluator_evidence_ref,rr['readiness']); tr=tree(a.repository,token,base,files); cm=commit(a.repository,token,tr,a.candidate_head,f'promote(governance): release {a.release_governance_revision} in-place from {a.candidate_head}')
    pre=prepublish_check(a.repository,token,a.candidate_head,cbranch,cm,a.release_governance_uid,a.release_governance_revision,a.promotion_authorization_ref)
    if pre.get('status')!='PASS':
        print(json.dumps({'status':'BLOCKED_PRE_PUBLISH_RECONCILIATION','candidate_head_sha':a.candidate_head,'unpublished_release_commit_sha':cm,'pre_publish_reconciliation':pre,'branch_ref_mutated':False,'product_completion_credit':0},sort_keys=True));return 2
    if branch_head(a.repository,cbranch,token)!=a.candidate_head:
        print(json.dumps({'status':'BLOCKED','reason':'SNAPSHOT_INVALIDATED_BEFORE_ATOMIC_PROMOTION','branch_ref_mutated':False}));return 2
    update_ref(a.repository,token,cbranch,cm); created=ref(a.repository,token,cbranch)
    if created!=cm:print(json.dumps({'status':'BLOCKED','reason':'ACTIVE_GOVERNANCE_REF_POST_WRITE_MISMATCH'}));return 2
    pc=postcheck(a.repository,token,a.candidate_head,cbranch,cm,a.release_governance_uid,a.release_governance_revision,a.promotion_authorization_ref)
    if pc.get('status')!='PASS':
        print(json.dumps({'status':'BLOCKED_POST_WRITE_RECONCILIATION','release_branch':cbranch,'release_head_sha':cm,'post_write_reconciliation':pc,'product_completion_credit':0},sort_keys=True));return 2
    print(json.dumps({'status':'PROMOTED_PENDING_FRESH_REVERIFY','candidate_head_sha':a.candidate_head,'release_branch':cbranch,'release_head_sha':cm,'released_governance_uid':a.release_governance_uid,'released_governance_revision':a.release_governance_revision,'branch_fanout_performed':False,'post_write_reconciliation':pc,'product_completion_credit':0,'fresh_reverification_required':True},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
