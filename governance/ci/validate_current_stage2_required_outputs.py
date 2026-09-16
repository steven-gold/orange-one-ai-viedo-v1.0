#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,sys
from collections import Counter
from pathlib import Path
import yaml
ROOT=Path('.'); BASE=ROOT/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'; STAGE='STAGE-02'
LIFE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'; REG=ROOT/'governance/specifications/REGISTRY.yaml'; STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'; EVID=ROOT/'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
GENERATED=['REQUIRED_FIELD_MANIFEST','FUNCTIONAL_CHAIN_MANIFEST','EFFECTIVE_CONTRACT_OVERLAY','DEPENDENCY_TOPOLOGY','DENOMINATOR_SNAPSHOT','CLASSIFICATION_RULESET','CHANGE_IMPACT_MAP','STAGE_EXECUTION_PREFLIGHT_RECEIPT','CURRENT_PROBLEM_REGISTER','RESOLUTION_LEDGER']
ROOT_EXISTING=['DEPENDENCY_MAP','ASYNC_PROVIDER_CONTRACT','SHARED_OWNER_PORT_MAP']
PAGE={'FUNCTIONAL_CHAIN_SPEC':'FUNCTIONAL_CHAIN_SPEC.yaml','PAGE_CONSTRUCTION_SPEC_PACKAGE':'PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml','FUNCTIONAL_WORKBENCH_CONTRACT':'FUNCTIONAL_WORKBENCH_CONTRACT.yaml','INTERACTION_TOPOLOGY_SPEC':'INTERACTION_TOPOLOGY_SPEC.yaml'}
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
def st(l):
    r=[x for x in l.get('stages',[]) if x.get('stage_uid')==STAGE]
    if len(r)!=1: die(f'STAGE_RECORD_COUNT:{len(r)}')
    return r[0]
def rows(e):
    out=[]
    for pu,p in sorted((e.get('pages') or {}).items()):
        s=(p or {}).get('functional_chain_fresh_scan') or {}; gs=s.get('gaps') or []
        if s.get('gap_count')!=len(gs): die(f'PAGE_GAP_COUNT_DRIFT:{pu}')
        for g in gs: out.append((pu,g.get('uid'),g.get('category'),g.get('class'),g.get('detail'),g.get('gap_owner')))
    return out
def fp(r):
    pu,u,c,cl,d,o=r; raw=json.dumps({'stage_uid':STAGE,'page_uid':pu,'uid':u,'category':c,'class':cl,'detail':d,'gap_owner':o},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode(); return hashlib.sha256(raw).hexdigest()
def main():
    life,reg,state,e=y(LIFE),y(REG),y(STATE),j(EVID); stage=st(life); cur=(reg.get('active_specification') or {}).get('governance_uid'); att=state.get('stage02_active_attempt') or {}
    if att.get('frozen_governance_uid')!=cur or e.get('frozen_governance_uid')!=cur: die('CURRENT_GOVERNANCE_UID_DRIFT')
    if att.get('attempt_uid')!=e.get('attempt_uid'): die('ATTEMPT_UID_DRIFT')
    if ((state.get('execution') or {}).get('stage2') or {}).get('stage_exit_allowed') is not False: die('STAGE02_EXIT_MUST_REMAIN_BLOCKED')
    expected=stage.get('outputs') or []; prod=stage.get('output_producers') or {}
    if len(expected)!=17 or len(set(expected))!=17: die(f'CURRENT_STAGE02_OUTPUT_DENOMINATOR_DRIFT:{len(expected)}')
    if set(expected)!=set(e.get('official_stage_output_denominator') or []): die('EVIDENCE_OFFICIAL_OUTPUT_DENOMINATOR_DRIFT')
    if set(expected)!=set(GENERATED+ROOT_EXISTING+list(PAGE)): die('VALIDATOR_OUTPUT_MODEL_DRIFT')
    for n in ROOT_EXISTING:
        d=y(BASE/f'{n}.yaml')
        if d.get('artifact_type')!=n or d.get('stage_uid')!=STAGE: die(f'EXISTING_ROOT_OUTPUT_DRIFT:{n}')
    pages=sorted((e.get('pages') or {}).keys())
    if not pages: die('NO_PAGE_SCOPE')
    for n,f in PAGE.items():
        for pu in pages:
            d=y(BASE/pu/f)
            if d.get('artifact_type')!=n or d.get('stage_uid')!=STAGE or d.get('page_uid')!=pu: die(f'PAGE_OUTPUT_DRIFT:{pu}:{n}')
    docs={n:y(BASE/f'{n}.yaml') for n in GENERATED}
    for n,d in docs.items():
        if d.get('artifact_type')!=n or d.get('operation_uid')!=prod.get(n): die(f'GENERATED_OUTPUT_PRODUCER_DRIFT:{n}')
        if d.get('current_governance_uid')!=cur or d.get('attempt_uid')!=e.get('attempt_uid'): die(f'GENERATED_OUTPUT_IDENTITY_DRIFT:{n}')
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
        if dg.get(n)!=hashlib.sha256((BASE/f'{n}.yaml').read_bytes()).hexdigest(): die(f'PREFLIGHT_DIGEST_DRIFT:{n}')
    print(f'PASS: Current Stage-02 logical outputs={len(expected)}/17 and page scope={pages}')
    print(f'PASS: CURRENT_PROBLEM_REGISTER exact fresh projection problems={len(erows)} stable UIDs')
    print(f'PASS: RESOLUTION_LEDGER append-only entries={len(entries)} unverified product/external credit=0')
    print('PASS: Stage-02 blocked; Stage-03 forbidden')
if __name__=='__main__': main()
