#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, sys
from collections import Counter
from pathlib import Path
import yaml

ROOT=Path('.')
STAGE='STAGE-02'
BASE=ROOT/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
REG=ROOT/'governance/specifications/REGISTRY.yaml'
LIFE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
INV=ROOT/'.github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
EVID=ROOT/'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
R1=ROOT/'governance/test/stage02/STAGE02_MATERIAL_REMEDIATION_RECEIPT_R1.yaml'
OUTS=['REQUIRED_FIELD_MANIFEST','FUNCTIONAL_CHAIN_MANIFEST','EFFECTIVE_CONTRACT_OVERLAY','DEPENDENCY_TOPOLOGY','DENOMINATOR_SNAPSHOT','CLASSIFICATION_RULESET','CHANGE_IMPACT_MAP','STAGE_EXECUTION_PREFLIGHT_RECEIPT','CURRENT_PROBLEM_REGISTER','RESOLUTION_LEDGER']


def die(m): print('BLOCK:',m,file=sys.stderr); raise SystemExit(1)
def y(path):
    if not path.is_file(): die(f'MISSING:{path}')
    v=yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(v,dict): die(f'MAPPING_REQUIRED:{path}')
    return v
def j(path):
    if not path.is_file(): die(f'MISSING:{path}')
    v=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(v,dict): die(f'MAPPING_REQUIRED:{path}')
    return v
def sha(raw): return hashlib.sha256(raw).hexdigest()
def fp(g):
    raw=json.dumps({'stage_uid':STAGE,'page_uid':g['page_uid'],'uid':g['uid'],'category':g['category'],'class':g['class'],'detail':g['detail'],'gap_owner':g['gap_owner']},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    return sha(raw)
def stage(life):
    rows=[x for x in life.get('stages',[]) if x.get('stage_uid')==STAGE]
    if len(rows)!=1: die(f'STAGE_RECORD_COUNT:{len(rows)}')
    return rows[0]
def gaps(e):
    out=[]
    for page_uid,page in sorted((e.get('pages') or {}).items()):
        scan=(page or {}).get('functional_chain_fresh_scan') or {}; rows=scan.get('gaps') or []
        if scan.get('gap_count')!=len(rows): die(f'PAGE_GAP_COUNT_DRIFT:{page_uid}')
        for g in rows:
            if g.get('page_uid')!=page_uid: die(f'PAGE_UID_DRIFT:{page_uid}')
            for k in ('uid','category','class','detail','gap_owner'):
                if not g.get(k): die(f'GAP_FIELD_MISSING:{page_uid}:{k}')
            out.append(dict(g))
    if e.get('fresh_functional_gap_total')!=len(out): die('GLOBAL_GAP_COUNT_DRIFT')
    return out
def old_uids():
    p=BASE/'CURRENT_PROBLEM_REGISTER.yaml'
    if not p.is_file(): return {}
    m={}
    for r in y(p).get('problems') or []:
        f,u=r.get('problem_fingerprint'),r.get('problem_uid')
        if f and u:
            if f in m and m[f]!=u: die(f'PROBLEM_FINGERPRINT_COLLISION:{f}')
            m[f]=u
    return m
def old_resolutions():
    p=BASE/'RESOLUTION_LEDGER.yaml'
    if not p.is_file(): return []
    rows=y(p).get('entries') or []; seen=set()
    if not isinstance(rows,list): die('RESOLUTION_LEDGER_ENTRIES_LIST_REQUIRED')
    for r in rows:
        u=r.get('resolution_uid') if isinstance(r,dict) else None
        if not u or u in seen: die(f'RESOLUTION_LEDGER_UID_INVALID:{u}')
        seen.add(u)
    return rows

def build():
    reg,life,inv,state,e=y(REG),y(LIFE),y(INV),y(STATE),j(EVID); st=stage(life)
    gov=(reg.get('active_specification') or {}).get('governance_uid'); att=state.get('stage02_active_attempt') or {}
    if not gov or att.get('frozen_governance_uid')!=gov or e.get('frozen_governance_uid')!=gov: die('CURRENT_GOVERNANCE_UID_DRIFT')
    if att.get('attempt_uid')!=e.get('attempt_uid'): die('ATTEMPT_UID_DRIFT')
    if (state.get('execution') or {}).get('current_stage')!='STAGE-02-TESTED-BLOCKED': die('CURRENT_STAGE_DRIFT')
    if ((state.get('execution') or {}).get('stage2') or {}).get('stage_exit_allowed') is not False: die('STAGE02_EXIT_MUST_REMAIN_BLOCKED')
    if e.get('result')!='BLOCKED' or e.get('stage_exit_allowed') is not False: die('CURRENT_EVIDENCE_MUST_BE_BLOCKED')
    if e.get('current_specification_mutated') is not False or e.get('prior_stage2_results_used') is not False: die('EVIDENCE_PROVENANCE_DRIFT')
    outputs=st.get('outputs') or []; prod=st.get('output_producers') or {}
    expected={'REQUIRED_FIELD_MANIFEST':'STAGE_EXECUTION_PREFLIGHT_COMPILE','FUNCTIONAL_CHAIN_MANIFEST':'STAGE_EXECUTION_PREFLIGHT_COMPILE','DENOMINATOR_SNAPSHOT':'STAGE_EXECUTION_PREFLIGHT_COMPILE','CLASSIFICATION_RULESET':'STAGE_EXECUTION_PREFLIGHT_COMPILE','STAGE_EXECUTION_PREFLIGHT_RECEIPT':'STAGE_EXECUTION_PREFLIGHT_COMPILE','CURRENT_PROBLEM_REGISTER':'STAGE_EXECUTION_PREFLIGHT_COMPILE','RESOLUTION_LEDGER':'STAGE_EXECUTION_PREFLIGHT_COMPILE','EFFECTIVE_CONTRACT_OVERLAY':'EFFECTIVE_CONTRACT_OVERLAY_COMPILE','DEPENDENCY_TOPOLOGY':'DEPENDENCY_TOPOLOGY_COMPILE','CHANGE_IMPACT_MAP':'CHANGE_IMPACT_MAP_COMPILE'}
    for n,p in expected.items():
        if n not in outputs or prod.get(n)!=p: die(f'LIFECYCLE_OUTPUT_PRODUCER_DRIFT:{n}')
    iv=inv.get('invariants') or {}; need=['CANONICAL_STAGE_EXECUTION_PREFLIGHT','DEPENDENCY_ORDERED_INCREMENTAL_RECONCILIATION','GAP_REMEDIATION_ADMISSIBILITY','ROLE_SAFE_FUNCTIONAL_CLOSURE','COMMON_ENGINE_DEFECT_INTERRUPT','GENERATED_OUTPUT_PERSISTENCE','FUNCTIONAL_CONTRACT_COMPLETENESS']
    for n in need:
        if not iv.get(n): die(f'INVARIANT_MISSING:{n}')
    gs=gaps(e); existing=old_uids(); problems=[]
    for g in sorted(gs,key=lambda x:(x['page_uid'],x['uid'],x['category'],x['class'],x['detail'])):
        f=fp(g); problems.append({'problem_uid':existing.get(f) or f'STAGE02-PROBLEM-{f[:16].upper()}','problem_fingerprint':f,'stage_uid':STAGE,'page_uid':g['page_uid'],'target_uid':g['uid'],'category':g['category'],'gap_class':g['class'],'gap_owner':g['gap_owner'],'detail':g['detail'],'status':'OPEN','resolution_credit':0,'source_evidence_ref':EVID.as_posix(),'external_authority_resolution_claimed':False})
    if len({p['problem_uid'] for p in problems})!=len(problems): die('PROBLEM_UID_COLLISION')
    pages=Counter(p['page_uid'] for p in problems); cats=Counter(p['category'] for p in problems); classes=Counter(p['gap_class'] for p in problems); owners=Counter(p['gap_owner'] for p in problems)
    common={'schema_version':1,'normative_authority':False,'stage_uid':STAGE,'current_governance_uid':gov,'attempt_uid':e['attempt_uid'],'source_evidence_ref':EVID.as_posix(),'source_evidence_sha256':sha(EVID.read_bytes())}
    complete=iv['FUNCTIONAL_CONTRACT_COMPLETENESS']; dep=iv['DEPENDENCY_ORDERED_INCREMENTAL_RECONCILIATION']
    docs={
      'REQUIRED_FIELD_MANIFEST':{**common,'artifact_type':'REQUIRED_FIELD_MANIFEST','operation_uid':prod['REQUIRED_FIELD_MANIFEST'],'invariant_registry_ref':INV.as_posix(),'effectful_action_required_fields':complete.get('effectful_action_required_fields') or [],'create_additional_required_fields':complete.get('create_additional_required_fields') or [],'async_additional_required_fields':complete.get('async_additional_required_fields') or [],'single_manifest_for_all_stage_consumers':True},
      'FUNCTIONAL_CHAIN_MANIFEST':{**common,'artifact_type':'FUNCTIONAL_CHAIN_MANIFEST','operation_uid':prod['FUNCTIONAL_CHAIN_MANIFEST'],'page_scope':sorted(pages),'page_gap_counts':dict(sorted(pages.items())),'fresh_functional_gap_total':len(problems),'functional_completion_claim':False},
      'EFFECTIVE_CONTRACT_OVERLAY':{**common,'artifact_type':'EFFECTIVE_CONTRACT_OVERLAY','operation_uid':prod['EFFECTIVE_CONTRACT_OVERLAY'],'formula':'IMMUTABLE_RAW_OR_PREDECESSOR_REQUIREMENT_PLUS_LEGAL_CURRENT_SUCCESSOR_OVERLAY','raw_absence_alone_is_effective_gap':False,'physical_rescan_and_signature_reconciliation_required':True,'current_discovery_gap_total':len(problems),'current_effective_gap_elimination_claimed':0,'preserved_external_authority_gap_uids':e.get('preserved_external_authority_union_gap_uids') or [],'external_authority_resolution_claimed':False},
      'DEPENDENCY_TOPOLOGY':{**common,'artifact_type':'DEPENDENCY_TOPOLOGY','operation_uid':prod['DEPENDENCY_TOPOLOGY'],'canonical_remediation_order':dep.get('order') or [],'local_reverse_dependency_validation_required_after_each_batch':bool(dep.get('local_reverse_dependency_validation_after_each_batch')),'checkpoint_full_sweep_triggers':dep.get('checkpoint_full_sweep_required_after') or [],'current_dependency_map_ref':(BASE/'DEPENDENCY_MAP.yaml').as_posix(),'shared_owner_port_map_ref':(BASE/'SHARED_OWNER_PORT_MAP.yaml').as_posix(),'problem_owner_counts':dict(sorted(owners.items()))},
      'DENOMINATOR_SNAPSHOT':{**common,'artifact_type':'DENOMINATOR_SNAPSHOT','operation_uid':prod['DENOMINATOR_SNAPSHOT'],'source':'FRESH_PHYSICAL_STAGE02_EVIDENCE','fresh_functional_gap_total':len(problems),'fresh_closure_blocker_total':int(e.get('closure_blocker_total',0)),'page_counts':dict(sorted(pages.items())),'category_counts':dict(sorted(cats.items())),'class_counts':dict(sorted(classes.items())),'official_stage_output_denominator_count':len(e.get('official_stage_output_denominator') or []),'current_manifest_mandatory_stage_output_subset_count':len(e.get('execution_profile_mandatory_output_subset') or []),'preserved_external_authority_union_count':int(e.get('preserved_external_authority_union_count',0)),'hardcoded_or_historical_denominator_used':False},
      'CLASSIFICATION_RULESET':{**common,'artifact_type':'CLASSIFICATION_RULESET','operation_uid':prod['CLASSIFICATION_RULESET'],'gap_remediation_admissibility':iv['GAP_REMEDIATION_ADMISSIBILITY'],'role_safe_functional_closure':iv['ROLE_SAFE_FUNCTIONAL_CLOSURE'],'common_engine_defect_interrupt':iv['COMMON_ENGINE_DEFECT_INTERRUPT'],'generated_output_persistence':iv['GENERATED_OUTPUT_PERSISTENCE'],'local_semantic_fork_allowed':False},
      'CHANGE_IMPACT_MAP':{**common,'artifact_type':'CHANGE_IMPACT_MAP','operation_uid':prod['CHANGE_IMPACT_MAP'],'problem_count':len(problems),'page_problem_counts':dict(sorted(pages.items())),'target_uid_count':len({p['target_uid'] for p in problems}),'local_reverse_dependency_validation_required':True,'whole_problem_register_rebuild_after_leaf_change':False,'stable_problem_uid_preservation_required':True,'common_engine_repair_requires_replay':True,'checkpoint_full_sweep_triggers':dep.get('checkpoint_full_sweep_required_after') or []},
      'CURRENT_PROBLEM_REGISTER':{**common,'artifact_type':'CURRENT_PROBLEM_REGISTER','operation_uid':prod['CURRENT_PROBLEM_REGISTER'],'current_truth_role':'SINGLE_CURRENT_PROBLEM_REGISTER','problem_uid_policy':'STABLE_FINGERPRINT_PRESERVED_ACROSS_RECOMPILE','fresh_physical_problem_count':len(problems),'page_counts':dict(sorted(pages.items())),'category_counts':dict(sorted(cats.items())),'class_counts':dict(sorted(classes.items())),'open_problem_count':len(problems),'resolved_problem_count':0,'problems':problems,'stage_exit_allowed':False,'stage03_allowed':False},
    }
    entries=old_resolutions()
    if not any(x.get('resolution_uid')=='STAGE02-RESOLUTION-R1-STRUCTURAL-CLOSURE' for x in entries):
        r1=y(R1); entries.append({'resolution_uid':'STAGE02-RESOLUTION-R1-STRUCTURAL-CLOSURE','resolution_type':'VERIFIED_STRUCTURAL_MATERIALIZATION','source_receipt_ref':R1.as_posix(),'materialized_missing_artifact_blocker_count':int(e.get('materialized_missing_artifact_blocker_count',0)),'fresh_reexecution_closure_blocker_total':int(e.get('closure_blocker_total',0)),'functional_gap_reduction_credit':0,'external_authority_resolution_credit':0,'verification_run_id':int(att.get('source_workflow_run_id',0)),'verification_status':'PASS' if e.get('materialized_structural_contract_validation')=='PASS' else 'BLOCKED','receipt_artifact_type':r1.get('artifact_type')})
    docs['RESOLUTION_LEDGER']={**common,'artifact_type':'RESOLUTION_LEDGER','operation_uid':prod['RESOLUTION_LEDGER'],'ledger_mode':'APPEND_ONLY','existing_verified_entries_preserved_on_recompile':True,'entries':entries,'functional_problem_resolution_credit_total':sum(int(x.get('functional_gap_reduction_credit',0)) for x in entries),'external_authority_resolution_credit_total':sum(int(x.get('external_authority_resolution_credit',0)) for x in entries)}
    dig={n:sha(yaml.safe_dump(d,sort_keys=False,allow_unicode=True).encode()) for n,d in docs.items()}
    docs['STAGE_EXECUTION_PREFLIGHT_RECEIPT']={**common,'artifact_type':'STAGE_EXECUTION_PREFLIGHT_RECEIPT','operation_uid':prod['STAGE_EXECUTION_PREFLIGHT_RECEIPT'],'invariant_uid':'GOV-INV-CANONICAL-STAGE-EXECUTION-OPTIMIZATION-001','required_output_types':outputs,'canonical_preflight_output_digests':dig,'fresh_problem_count':len(problems),'preserved_verified_resolution_entry_count':len(entries),'single_current_problem_register':True,'append_only_resolution_ledger':True,'dependency_ordered_remediation_required':True,'local_impact_validation_required':True,'checkpoint_full_sweep_required':True,'stage_exit_allowed':False,'stage03_allowed':False,'result':'PASS_PREFLIGHT_WITH_OPEN_PRODUCT_GAPS'}
    return docs

def write(docs):
    BASE.mkdir(parents=True,exist_ok=True)
    for n in OUTS: (BASE/f'{n}.yaml').write_text(yaml.safe_dump(docs[n],sort_keys=False,allow_unicode=True),encoding='utf-8')
def check(docs):
    for n in OUTS:
        if y(BASE/f'{n}.yaml')!=docs[n]: die(f'PREFLIGHT_OUTPUT_DRIFT:{n}')
    print(f'PASS: canonical {STAGE} preflight outputs={len(OUTS)}/{len(OUTS)} exact')
    print(f'PASS: CURRENT_PROBLEM_REGISTER fresh problems={docs["CURRENT_PROBLEM_REGISTER"]["fresh_physical_problem_count"]} stable UIDs')
    print(f'PASS: RESOLUTION_LEDGER entries={len(docs["RESOLUTION_LEDGER"]["entries"])} append-only')
def main():
    p=argparse.ArgumentParser(); p.add_argument('--stage',default=STAGE); g=p.add_mutually_exclusive_group(required=True); g.add_argument('--materialize',action='store_true'); g.add_argument('--check',action='store_true'); a=p.parse_args()
    if a.stage!=STAGE: die(f'UNSUPPORTED_STAGE_UNTIL_MATCHING_CURRENT_EVIDENCE_EXISTS:{a.stage}')
    docs=build()
    if a.materialize: write(docs)
    check(docs)
if __name__=='__main__': main()
