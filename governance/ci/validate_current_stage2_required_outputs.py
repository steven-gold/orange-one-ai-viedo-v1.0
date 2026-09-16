#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,subprocess,sys
from collections import Counter
from pathlib import Path
import yaml
ROOT=Path('.'); BASE=ROOT/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'; STAGE='STAGE-02'
ENTRY=ROOT/'GOVERNANCE_CURRENT.yaml'; LIFE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'; REG=ROOT/'governance/specifications/REGISTRY.yaml'; RULE=ROOT/'governance/specifications/current/CANONICAL_RULE_REGISTRY.yaml'; CYCLE=ROOT/'governance/specifications/current/EXECUTION_CYCLE_CONTROL.yaml'; STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'; EVID=ROOT/'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
ROOT_MANIFEST=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'; SECTION_REGISTRY=ROOT/'.github/governance-source/active/source/10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'; ACCEPTANCE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'
GENERATED=['REQUIRED_FIELD_MANIFEST','FUNCTIONAL_CHAIN_MANIFEST','EFFECTIVE_CONTRACT_OVERLAY','DEPENDENCY_TOPOLOGY','DENOMINATOR_SNAPSHOT','CLASSIFICATION_RULESET','CHANGE_IMPACT_MAP','STAGE_EXECUTION_PREFLIGHT_RECEIPT','CURRENT_PROBLEM_REGISTER','RESOLUTION_LEDGER']
SUPPORTS=['GOVERNANCE_EXECUTION_CONTEXT_RECEIPT','EXECUTION_CYCLE_PREFLIGHT_RECEIPT']
ROOT_EXISTING=['DEPENDENCY_MAP','ASYNC_PROVIDER_CONTRACT','SHARED_OWNER_PORT_MAP']
PAGE={
    'FUNCTIONAL_CHAIN_SPEC':('FUNCTIONAL_CHAIN_SPEC.yaml','FUNCTIONAL_CHAIN_SPEC'),
    'PAGE_CONSTRUCTION_SPEC_PACKAGE':('PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml','PAGE_CONSTRUCTION_SPEC_PACKAGE'),
    'FUNCTIONAL_WORKBENCH_CONTRACT':('FUNCTIONAL_WORKBENCH_CONTRACT.yaml','FUNCTIONAL_WORKBENCH_CONTRACT'),
    'INTERACTION_TOPOLOGY_SPEC':('INTERACTION_TOPOLOGY_SPEC.yaml','INTERACTION_TOPOLOGY_MATRIX'),
}
OWNER_OPERATION='STAGE_EXECUTION_PREFLIGHT_COMPILE'
PARENT_STATUS='ACTIVE_STAGE2_TESTED_BLOCKED_CURRENT_GOVERNANCE'
PARENT_RESUME_POINT='STAGE2_TESTED_BLOCKED_OWNING_LAYER_REMEDIATION'
PARENT_NEXT_ACTION='MATERIAL_REMEDIATION_AT_OWNING_LAYER_FOR_REMAINING_FRESH_FUNCTIONAL_GAPS'
def die(m): print('BLOCK:',m,file=sys.stderr); raise SystemExit(1)
def y(p):
    if not p.is_file(): die(f'MISSING_REQUIRED_OUTPUT:{p}')
    v=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(v,dict): die(f'MAPPING_REQUIRED:{p}')
    return v
def j(p):
    if not p.is_file(): die(f'MISSING:{p}')
    v=json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(v,dict): die(f'MAPPING_REQUIRED:{p}')
    return v
def h(p):
    if not p.is_file(): die(f'MISSING_HASH_TARGET:{p}')
    return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):
    try: return subprocess.check_output(['git',*args],text=True,stderr=subprocess.DEVNULL).strip()
    except Exception as exc: die(f'GIT_IDENTITY_UNRESOLVED:{args}:{exc}')
def st(l):
    r=[x for x in l.get('stages',[]) if x.get('stage_uid')==STAGE]
    if len(r)!=1: die(f'STAGE_RECORD_COUNT:{len(r)}')
    return r[0]
def execution_context(state):
    work=state.get('active_work_unit') or {}; resume=state.get('resume_control') or {}
    if work:
        uid=work.get('work_unit_uid'); owner=work.get('canonical_owner'); name=work.get('canonical_name')
        if not uid or not owner or not name: die('CURRENT_ACTIVE_WORK_UNIT_IDENTITY_MISSING')
        if resume.get('current_work_unit_uid')!=uid: die('CURRENT_ACTIVE_WORK_UNIT_RESUME_DRIFT')
        if resume.get('current_owner')!=owner: die('CURRENT_ACTIVE_WORK_UNIT_OWNER_DRIFT')
        return {'mode':'ACTIVE_WORK_UNIT','work_unit_uid':uid,'canonical_owner':owner,'semantic_concern':name,'resume_point':resume.get('current_resume_point')}
    if state.get('status')!=PARENT_STATUS: die('CURRENT_EXECUTION_CONTEXT_MODE_UNRESOLVED')
    if resume.get('current_resume_point')!=PARENT_RESUME_POINT: die('PARENT_RESUME_POINT_DRIFT')
    if state.get('next_action')!=PARENT_NEXT_ACTION: die('PARENT_NEXT_ACTION_DRIFT')
    if resume.get('current_work_unit_uid') or resume.get('current_owner'): die('STALE_INTERRUPT_WORK_UNIT_BINDING_IN_PARENT_MODE')
    return {'mode':'PARENT_OWNING_LAYER_REMEDIATION','work_unit_uid':None,'canonical_owner':None,'semantic_concern':PARENT_NEXT_ACTION,'resume_point':PARENT_RESUME_POINT}
def rows(e):
    out=[]
    for pu,p in sorted((e.get('pages') or {}).items()):
        s=(p or {}).get('functional_chain_fresh_scan') or {}; gs=s.get('gaps') or []
        if s.get('gap_count')!=len(gs): die(f'PAGE_GAP_COUNT_DRIFT:{pu}')
        for g in gs: out.append((pu,g.get('uid'),g.get('category'),g.get('class'),g.get('detail'),g.get('gap_owner')))
    return out
def fp(r):
    pu,u,c,cl,d,o=r; raw=json.dumps({'stage_uid':STAGE,'page_uid':pu,'uid':u,'category':c,'class':cl,'detail':d,'gap_owner':o},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode(); return hashlib.sha256(raw).hexdigest()
def runtime_repo():
    repo=os.environ.get('GITHUB_REPOSITORY')
    if repo: return repo
    remote=git('config','--get','remote.origin.url').removesuffix('.git').rstrip('/')
    if remote.startswith('git@github.com:'): return remote.split(':',1)[1]
    if 'github.com/' in remote: return remote.split('github.com/',1)[1]
    die('REPOSITORY_IDENTITY_UNRESOLVED')
def validate_execution_identity(identity,allowed_persistence_paths):
    if identity.get('repository')!=runtime_repo(): die('CONTEXT_REPOSITORY_DRIFT')
    branch=os.environ.get('GITHUB_REF_NAME') or git('rev-parse','--abbrev-ref','HEAD')
    if identity.get('branch')!=branch: die('CONTEXT_BRANCH_DRIFT')
    head=git('rev-parse','HEAD')
    if identity.get('head_sha')==head:
        if identity.get('tree_sha')!=git('rev-parse','HEAD^{tree}'): die('CONTEXT_TREE_DRIFT')
        return 'EXACT_HEAD'
    parent=git('rev-parse','HEAD^')
    if identity.get('head_sha')!=parent: die(f'CONTEXT_HEAD_DRIFT:receipt={identity.get("head_sha")}:current={head}')
    changed=set(x for x in git('diff','--name-only',f'{parent}..{head}').splitlines() if x)
    if not changed or not changed.issubset(allowed_persistence_paths): die(f'CONTEXT_PERSISTENCE_CHILD_SCOPE_DRIFT:{sorted(changed)}')
    if identity.get('tree_sha')!=git('rev-parse',f'{parent}^{{tree}}'): die('CONTEXT_PARENT_TREE_DRIFT')
    return 'EXACT_PERSISTENCE_CHILD'
def main():
    life,reg,entry,state,e=y(LIFE),y(REG),y(ENTRY),y(STATE),j(EVID); stage=st(life); cur=(reg.get('active_specification') or {}).get('governance_uid'); att=state.get('stage02_active_attempt') or {}; context=execution_context(state); work_unit=context['work_unit_uid']; work_owner=context['canonical_owner']
    if entry.get('active_governance_uid')!=cur or att.get('frozen_governance_uid')!=cur or e.get('frozen_governance_uid')!=cur: die('CURRENT_GOVERNANCE_UID_DRIFT')
    if att.get('attempt_uid')!=e.get('attempt_uid'): die('ATTEMPT_UID_DRIFT')
    if ((state.get('execution') or {}).get('stage2') or {}).get('stage_exit_allowed') is not False: die('STAGE02_EXIT_MUST_REMAIN_BLOCKED')
    expected=stage.get('outputs') or []; prod=stage.get('output_producers') or {}
    if not expected or len(set(expected))!=len(expected): die(f'CURRENT_STAGE02_OUTPUT_DENOMINATOR_INVALID:{len(expected)}')
    if set(expected)!=set(e.get('official_stage_output_denominator') or []): die('EVIDENCE_OFFICIAL_OUTPUT_DENOMINATOR_DRIFT')
    if set(expected)!=set(GENERATED+ROOT_EXISTING+list(PAGE)): die('VALIDATOR_OUTPUT_MODEL_DRIFT')
    for n in ROOT_EXISTING:
        d=y(BASE/f'{n}.yaml')
        if d.get('artifact_type')!=n or d.get('stage_uid')!=STAGE: die(f'EXISTING_ROOT_OUTPUT_DRIFT:{n}')
    pages=sorted((e.get('pages') or {}).keys())
    if not pages: die('NO_PAGE_SCOPE')
    for n,(f,artifact_type) in PAGE.items():
        for pu in pages:
            d=y(BASE/pu/f)
            if d.get('artifact_type')!=artifact_type or d.get('stage_uid')!=STAGE or d.get('page_uid')!=pu: die(f'PAGE_OUTPUT_DRIFT:{pu}:{n}')
    docs={n:y(BASE/f'{n}.yaml') for n in GENERATED}; support={n:y(BASE/f'{n}.yaml') for n in SUPPORTS}
    for n,d in docs.items():
        if d.get('artifact_type')!=n or d.get('operation_uid')!=prod.get(n): die(f'GENERATED_OUTPUT_PRODUCER_DRIFT:{n}')
        if d.get('current_governance_uid')!=cur or d.get('attempt_uid')!=e.get('attempt_uid'): die(f'GENERATED_OUTPUT_IDENTITY_DRIFT:{n}')
    for n,d in support.items():
        if d.get('artifact_type')!=n or d.get('producer_operation_uid')!=OWNER_OPERATION: die(f'SUPPORT_RECEIPT_PRODUCER_DRIFT:{n}')
        if d.get('current_governance_uid')!=cur or d.get('attempt_uid')!=e.get('attempt_uid'): die(f'SUPPORT_RECEIPT_IDENTITY_DRIFT:{n}')
        if d.get('active_work_unit_ref')!=work_unit or d.get('product_blocker_credit')!=0 or d.get('stage03_allowed') is not False: die(f'SUPPORT_RECEIPT_SCOPE_DRIFT:{n}')
        if context['mode']=='PARENT_OWNING_LAYER_REMEDIATION' and (d.get('execution_context_mode')!=context['mode'] or d.get('current_resume_point')!=context['resume_point']): die(f'PARENT_SUPPORT_RECEIPT_CONTEXT_DRIFT:{n}')
    allowed={(BASE/f'{n}.yaml').as_posix() for n in GENERATED+SUPPORTS}
    ctx=support['GOVERNANCE_EXECUTION_CONTEXT_RECEIPT']; identity_mode=validate_execution_identity(ctx.get('repository_identity') or {},allowed)
    if ctx.get('canonical_owner_operation')!=OWNER_OPERATION or ctx.get('resolved_current_work_unit_owner')!=work_owner or ctx.get('duplicate_search_result')!='EXISTING_CANONICAL_COMPILER_OWNER_REUSED_NO_PRIOR_SUPPORT_RECEIPT_OWNER_FOUND' or ctx.get('result')!='PASS_CONTEXT_RESOLVED': die('GOVERNANCE_CONTEXT_RECEIPT_DRIFT')
    if ctx.get('semantic_concern')!=context['semantic_concern']: die('GOVERNANCE_CONTEXT_SEMANTIC_CONCERN_DRIFT')
    if context['mode']=='PARENT_OWNING_LAYER_REMEDIATION' and ctx.get('confirmed_gap_uid') is not None: die('PARENT_CONTEXT_MUST_NOT_INVENT_GAP_UID')
    if set(ctx.get('exact_write_targets') or [])!=allowed: die('GOVERNANCE_CONTEXT_WRITE_SET_DRIFT')
    read_set=ctx.get('exact_read_set') or []
    if not read_set or len({r.get('path') for r in read_set})!=len(read_set): die('GOVERNANCE_CONTEXT_READ_SET_INVALID')
    for r in read_set:
        p=ROOT/str(r.get('path') or '')
        if r.get('sha256')!=h(p): die(f'GOVERNANCE_CONTEXT_READ_HASH_DRIFT:{p}')
    cr=ctx.get('current_registry') or {}; spec_rule=((reg.get('canonical_rule_registry') or {}).get('digest'))
    if cr.get('entry_sha256')!=h(ENTRY) or cr.get('registry_sha256')!=h(REG) or cr.get('canonical_rule_registry_sha256')!=h(RULE) or cr.get('canonical_rule_registry_digest')!=spec_rule or entry.get('canonical_rule_registry_digest')!=spec_rule: die('GOVERNANCE_CONTEXT_REGISTRY_DRIFT')
    cyc=support['EXECUTION_CYCLE_PREFLIGHT_RECEIPT']
    if cyc.get('result')!='PASS_GOVERNANCE_LOADED_FOR_PREFLIGHT' or cyc.get('common_engine_repair_requires_replay') is not True or cyc.get('stage_exit_allowed') is not False: die('EXECUTION_CYCLE_RECEIPT_DRIFT')
    if cyc.get('execution_identity')!=ctx.get('repository_identity'): die('SUPPORT_RECEIPT_EXECUTION_IDENTITY_DRIFT')
    if cyc.get('canonical_stage_output_denominator_count')!=len(expected) or set(cyc.get('canonical_stage_output_denominator') or [])!=set(expected): die('SUPPORT_RECEIPT_DENOMINATOR_DRIFT')
    gl=cyc.get('governance_load') or {}
    if gl.get('governance_uid')!=cur or gl.get('work_unit_uid')!=work_unit or gl.get('resolved_work_unit_owner')!=work_owner or gl.get('root_manifest_sha256')!=h(ROOT_MANIFEST) or gl.get('acceptance_blueprint_sha256')!=h(ACCEPTANCE): die('GOVERNANCE_LOAD_AUTHORITY_DRIFT')
    if context['mode']=='PARENT_OWNING_LAYER_REMEDIATION':
        if gl.get('execution_context_mode')!=context['mode'] or gl.get('current_resume_point')!=context['resume_point'] or gl.get('loader_version')!='4': die('PARENT_GOVERNANCE_LOAD_CONTEXT_DRIFT')
    sections=gl.get('resolved_section_uid_receipts') or []
    if len(sections)<6 or len({x.get('section_uid') for x in sections})!=len(sections): die('GOVERNANCE_LOAD_SECTION_RECEIPTS_INVALID')
    registry_text=SECTION_REGISTRY.read_text(encoding='utf-8')
    for x in sections:
        uid=x.get('section_uid'); p=ROOT/str(x.get('document_ref') or '')
        if not uid or uid not in registry_text or f'SECTION_UID: {uid}' not in p.read_text(encoding='utf-8') or x.get('document_sha256')!=h(p): die(f'GOVERNANCE_LOAD_SECTION_DRIFT:{uid}')
    for path,digest in (gl.get('dependency_artifact_hashes') or {}).items():
        if digest!=h(ROOT/path): die(f'GOVERNANCE_LOAD_DEPENDENCY_HASH_DRIFT:{path}')
    erows=rows(e)
    if len(erows)!=e.get('fresh_functional_gap_total'): die('FRESH_EVIDENCE_GAP_TOTAL_DRIFT')
    problem=docs['CURRENT_PROBLEM_REGISTER']; probs=problem.get('problems') or []
    if problem.get('fresh_physical_problem_count')!=len(erows) or len(probs)!=len(erows): die('CURRENT_PROBLEM_REGISTER_DENOMINATOR_DRIFT')
    seen=set(); actual=[]
    for p in probs:
        u=p.get('problem_uid'); r=(p.get('page_uid'),p.get('target_uid'),p.get('category'),p.get('gap_class'),p.get('detail'),p.get('gap_owner'))
        if not u or u in seen or p.get('problem_fingerprint')!=fp(r): die(f'PROBLEM_IDENTITY_DRIFT:{u}')
        if p.get('status')!='OPEN' or p.get('resolution_credit')!=0: die(f'UNVERIFIED_PROBLEM_CREDIT:{u}')
        seen.add(u); actual.append(r)
    if sorted(actual)!=sorted(erows): die('CURRENT_PROBLEM_REGISTER_NOT_FRESH_EVIDENCE_PROJECTION')
    denom=docs['DENOMINATOR_SNAPSHOT']; checks={'fresh_functional_gap_total':len(erows),'fresh_closure_blocker_total':int(e.get('closure_blocker_total',0)),'page_counts':dict(sorted(Counter(x[0] for x in erows).items())),'category_counts':dict(sorted(Counter(x[2] for x in erows).items())),'class_counts':dict(sorted(Counter(x[3] for x in erows).items())),'official_stage_output_denominator_count':len(expected),'current_manifest_mandatory_stage_output_subset_count':len(e.get('execution_profile_mandatory_output_subset') or []),'preserved_external_authority_union_count':int(e.get('preserved_external_authority_union_count',0))}
    for k,v in checks.items():
        if denom.get(k)!=v: die(f'DENOMINATOR_DRIFT:{k}:expected={v}:actual={denom.get(k)}')
    if denom.get('hardcoded_or_historical_denominator_used') is not False: die('HARDCODED_DENOMINATOR_FORBIDDEN')
    ledger=docs['RESOLUTION_LEDGER']; entries=ledger.get('entries') or []; ids=[x.get('resolution_uid') for x in entries]
    if not ids or len(ids)!=len(set(ids)) or ledger.get('ledger_mode')!='APPEND_ONLY' or ledger.get('existing_verified_entries_preserved_on_recompile') is not True: die('RESOLUTION_LEDGER_CONTRACT_DRIFT')
    if ledger.get('functional_problem_resolution_credit_total')!=0 or ledger.get('external_authority_resolution_credit_total')!=0: die('UNVERIFIED_RESOLUTION_CREDIT')
    receipt=docs['STAGE_EXECUTION_PREFLIGHT_RECEIPT']
    if receipt.get('result')!='PASS_PREFLIGHT_WITH_OPEN_PRODUCT_GAPS' or receipt.get('fresh_problem_count')!=len(erows) or receipt.get('stage_exit_allowed') is not False or receipt.get('stage03_allowed') is not False: die('PREFLIGHT_RECEIPT_DRIFT')
    dg=receipt.get('canonical_preflight_output_digests') or {}
    for n in [x for x in GENERATED if x!='STAGE_EXECUTION_PREFLIGHT_RECEIPT']:
        if dg.get(n)!=h(BASE/f'{n}.yaml'): die(f'PREFLIGHT_DIGEST_DRIFT:{n}')
    sd=receipt.get('policy_support_receipt_digests') or {}; sr=set(receipt.get('policy_support_receipt_refs') or [])
    if sr!={(BASE/f'{n}.yaml').as_posix() for n in SUPPORTS}: die('PREFLIGHT_SUPPORT_REF_DRIFT')
    for n in SUPPORTS:
        if sd.get(n)!=h(BASE/f'{n}.yaml'): die(f'PREFLIGHT_SUPPORT_DIGEST_DRIFT:{n}')
    print(f'PASS: Current Stage-02 logical outputs={len(expected)}/{len(expected)} and page scope={pages}')
    print(f'PASS: policy support receipts={len(SUPPORTS)}/2 identity_mode={identity_mode} execution_context_mode={context["mode"]} work_unit={work_unit}')
    print(f'PASS: CURRENT_PROBLEM_REGISTER exact fresh projection problems={len(erows)} stable UIDs')
    print(f'PASS: RESOLUTION_LEDGER append-only entries={len(entries)} unverified product/external credit=0')
    print('PASS: Stage-02 blocked; Stage-03 forbidden')
if __name__=='__main__': main()
