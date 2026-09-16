#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import yaml

ROOT=Path('.')
STAGE='STAGE-02'
BASE=ROOT/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
ENTRY=ROOT/'GOVERNANCE_CURRENT.yaml'
REG=ROOT/'governance/specifications/REGISTRY.yaml'
RULE=ROOT/'governance/specifications/current/CANONICAL_RULE_REGISTRY.yaml'
CYCLE=ROOT/'governance/specifications/current/EXECUTION_CYCLE_CONTROL.yaml'
CLOSURE=ROOT/'governance/specifications/current/VALIDATION_REMEDIATION_CLOSURE_PROTOCOL.yaml'
LIFE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
INV=ROOT/'.github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'
ROOT_MANIFEST=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'
SECTION_REGISTRY=ROOT/'.github/governance-source/active/source/10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'
ACCEPTANCE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'
MOTHERS=[
 ROOT/'.github/governance-source/active/source/12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md',
 ROOT/'.github/governance-source/active/source/12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md',
 ROOT/'.github/governance-source/active/source/12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',
 ROOT/'.github/governance-source/active/source/12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md',
]
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
EVID=ROOT/'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
FROZEN=ROOT/'governance/test/stage02/STAGE02_STAGE_FROZEN_GOVERNANCE_RECEIPT.yaml'
R1=ROOT/'governance/test/stage02/STAGE02_MATERIAL_REMEDIATION_RECEIPT_R1.yaml'
CAL=ROOT/'governance/test/STAGE02_EXECUTION_OPTIMIZATION_DEFECT_CONSOLIDATION.yaml'
OUTS=['REQUIRED_FIELD_MANIFEST','FUNCTIONAL_CHAIN_MANIFEST','EFFECTIVE_CONTRACT_OVERLAY','DEPENDENCY_TOPOLOGY','DENOMINATOR_SNAPSHOT','CLASSIFICATION_RULESET','CHANGE_IMPACT_MAP','STAGE_EXECUTION_PREFLIGHT_RECEIPT','CURRENT_PROBLEM_REGISTER','RESOLUTION_LEDGER']
SUPPORTS=['GOVERNANCE_EXECUTION_CONTEXT_RECEIPT','EXECUTION_CYCLE_PREFLIGHT_RECEIPT']
WORK_UNIT='STAGE02-CALIBRATION-GOVERNANCE-LOAD-CONTEXT-001'
OWNER_OPERATION='STAGE_EXECUTION_PREFLIGHT_COMPILE'
SEMANTIC_CONCERN='STAGE2_CANONICAL_PREFLIGHT_GOVERNANCE_LOAD_AND_CONTEXT'
SECTION_BINDINGS={
 'WEB-GOV-01-S073':MOTHERS[0],
 'WEB-GOV-02-S070':MOTHERS[1],
 'WEB-GOV-02-S073':MOTHERS[1],
 'WEB-GOV-03-S062':MOTHERS[2],
 'WEB-GOV-04-S078':MOTHERS[3],
 'WEB-GOV-04-S074':MOTHERS[3],
}

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
def file_sha(p):
    if not p.is_file(): die(f'MISSING:{p}')
    return sha(p.read_bytes())
def git(*args):
    try: return subprocess.check_output(['git',*args],text=True,stderr=subprocess.DEVNULL).strip()
    except Exception as exc: die(f'GIT_IDENTITY_UNRESOLVED:{args}:{exc}')
def repo_identity():
    head=git('rev-parse','HEAD'); tree=git('rev-parse','HEAD^{tree}')
    branch=os.environ.get('GITHUB_REF_NAME') or git('rev-parse','--abbrev-ref','HEAD')
    repo=os.environ.get('GITHUB_REPOSITORY')
    if not repo:
        remote=git('config','--get','remote.origin.url')
        remote=remote.removesuffix('.git').rstrip('/')
        if remote.startswith('git@github.com:'): repo=remote.split(':',1)[1]
        elif 'github.com/' in remote: repo=remote.split('github.com/',1)[1]
    if not repo or '/' not in repo: die('REPOSITORY_IDENTITY_UNRESOLVED')
    return {'repository':repo,'branch':branch,'head_sha':head,'tree_sha':tree}
def persisted_check_identity():
    current=repo_identity(); p=BASE/'GOVERNANCE_EXECUTION_CONTEXT_RECEIPT.yaml'
    if not p.is_file(): return current
    prior=(y(p).get('repository_identity') or {})
    if prior.get('head_sha')==current['head_sha']: return current
    if prior.get('repository')!=current['repository'] or prior.get('branch')!=current['branch']: return current
    parent=git('rev-parse','HEAD^')
    if prior.get('head_sha')!=parent: return current
    allowed={(BASE/f'{n}.yaml').as_posix() for n in OUTS+SUPPORTS}
    changed={x for x in git('diff','--name-only',f'{parent}..{current["head_sha"]}').splitlines() if x}
    if not changed or not changed.issubset(allowed): return current
    if prior.get('tree_sha')!=git('rev-parse',f'{parent}^{{tree}}'): return current
    return prior
def stable_loaded_at(identity):
    p=BASE/'GOVERNANCE_EXECUTION_CONTEXT_RECEIPT.yaml'
    if p.is_file():
        old=y(p); rid=old.get('repository_identity') or {}
        if rid.get('head_sha')==identity['head_sha'] and old.get('loaded_at_utc'): return old['loaded_at_utc']
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
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
def validate_sections():
    registry_text=SECTION_REGISTRY.read_text(encoding='utf-8')
    receipts=[]
    for uid,p in SECTION_BINDINGS.items():
        if uid not in registry_text: die(f'SECTION_UID_NOT_REGISTERED:{uid}')
        if f'SECTION_UID: {uid}' not in p.read_text(encoding='utf-8'): die(f'SECTION_UID_NOT_PHYSICAL:{uid}:{p}')
        receipts.append({'section_uid':uid,'document_ref':p.as_posix(),'document_sha256':file_sha(p)})
    return receipts
def canonical_read_set():
    paths=[ENTRY,REG,RULE,CYCLE,CLOSURE,LIFE,INV,ROOT_MANIFEST,SECTION_REGISTRY,ACCEPTANCE,*MOTHERS,STATE,EVID,FROZEN,R1,CAL]
    return [{'path':p.as_posix(),'sha256':file_sha(p)} for p in paths]
def normative_set_digest(read_set):
    normative={x['path']:x['sha256'] for x in read_set if x['path'] in {p.as_posix() for p in [ENTRY,REG,RULE,CYCLE,CLOSURE,LIFE,INV,ROOT_MANIFEST,SECTION_REGISTRY,ACCEPTANCE,*MOTHERS]}}
    return sha(json.dumps(normative,sort_keys=True,separators=(',',':')).encode())

def build(identity_override=None):
    entry,reg,rule,cycle,closure,life,inv,state,e,frozen,cal=y(ENTRY),y(REG),y(RULE),y(CYCLE),y(CLOSURE),y(LIFE),y(INV),y(STATE),j(EVID),y(FROZEN),y(CAL); st=stage(life)
    gov=(reg.get('active_specification') or {}).get('governance_uid'); att=state.get('stage02_active_attempt') or {}
    if not gov or entry.get('active_governance_uid')!=gov or att.get('frozen_governance_uid')!=gov or e.get('frozen_governance_uid')!=gov or frozen.get('frozen_governance_uid')!=gov: die('CURRENT_GOVERNANCE_UID_DRIFT')
    if att.get('attempt_uid')!=e.get('attempt_uid') or frozen.get('attempt_uid')!=e.get('attempt_uid'): die('ATTEMPT_UID_DRIFT')
    if (state.get('execution') or {}).get('current_stage')!='STAGE-02-TESTED-BLOCKED': die('CURRENT_STAGE_DRIFT')
    if ((state.get('execution') or {}).get('stage2') or {}).get('stage_exit_allowed') is not False: die('STAGE02_EXIT_MUST_REMAIN_BLOCKED')
    if e.get('result')!='BLOCKED' or e.get('stage_exit_allowed') is not False: die('CURRENT_EVIDENCE_MUST_BE_BLOCKED')
    if e.get('current_specification_mutated') is not False or e.get('prior_stage2_results_used') is not False: die('EVIDENCE_PROVENANCE_DRIFT')
    cc=(cal.get('current_calibration') or {}); sub=[x for x in ((cc.get('newly_confirmed_common_engine_gap') or {}).get('confirmed_subgaps') or []) if x.get('subgap_uid')==WORK_UNIT]
    if len(sub)!=1 or sub[0].get('status')!='OPEN_RECORDED_BEFORE_FIX': die('RECORDED_COMMON_ENGINE_WORK_UNIT_MISSING')
    outputs=st.get('outputs') or []; prod=st.get('output_producers') or {}
    expected={'REQUIRED_FIELD_MANIFEST':'STAGE_EXECUTION_PREFLIGHT_COMPILE','FUNCTIONAL_CHAIN_MANIFEST':'STAGE_EXECUTION_PREFLIGHT_COMPILE','DENOMINATOR_SNAPSHOT':'STAGE_EXECUTION_PREFLIGHT_COMPILE','CLASSIFICATION_RULESET':'STAGE_EXECUTION_PREFLIGHT_COMPILE','STAGE_EXECUTION_PREFLIGHT_RECEIPT':'STAGE_EXECUTION_PREFLIGHT_COMPILE','CURRENT_PROBLEM_REGISTER':'STAGE_EXECUTION_PREFLIGHT_COMPILE','RESOLUTION_LEDGER':'STAGE_EXECUTION_PREFLIGHT_COMPILE','EFFECTIVE_CONTRACT_OVERLAY':'EFFECTIVE_CONTRACT_OVERLAY_COMPILE','DEPENDENCY_TOPOLOGY':'DEPENDENCY_TOPOLOGY_COMPILE','CHANGE_IMPACT_MAP':'CHANGE_IMPACT_MAP_COMPILE'}
    for n,p in expected.items():
        if n not in outputs or prod.get(n)!=p: die(f'LIFECYCLE_OUTPUT_PRODUCER_DRIFT:{n}')
    if len(outputs)!=17 or len(set(outputs))!=17: die(f'OFFICIAL_STAGE_OUTPUT_DENOMINATOR_DRIFT:{len(outputs)}')
    iv=inv.get('invariants') or {}; need=['CANONICAL_STAGE_EXECUTION_PREFLIGHT','DEPENDENCY_ORDERED_INCREMENTAL_RECONCILIATION','GAP_REMEDIATION_ADMISSIBILITY','ROLE_SAFE_FUNCTIONAL_CLOSURE','COMMON_ENGINE_DEFECT_INTERRUPT','GENERATED_OUTPUT_PERSISTENCE','FUNCTIONAL_CONTRACT_COMPLETENESS']
    for n in need:
        if not iv.get(n): die(f'INVARIANT_MISSING:{n}')
    preflight=cycle.get('canonical_preflight') or {}
    req_artifacts=set(preflight.get('artifacts') or [])
    if not {'EXECUTION_CYCLE_PREFLIGHT_RECEIPT','GOVERNANCE_EXECUTION_CONTEXT_RECEIPT'}.issubset(req_artifacts): die('POLICY_SUPPORT_RECEIPT_REQUIREMENT_DRIFT')
    gs=gaps(e); existing=old_uids(); problems=[]
    for g in sorted(gs,key=lambda x:(x['page_uid'],x['uid'],x['category'],x['class'],x['detail'])):
        f=fp(g); problems.append({'problem_uid':existing.get(f) or f'STAGE02-PROBLEM-{f[:16].upper()}','problem_fingerprint':f,'stage_uid':STAGE,'page_uid':g['page_uid'],'target_uid':g['uid'],'category':g['category'],'gap_class':g['class'],'gap_owner':g['gap_owner'],'detail':g['detail'],'status':'OPEN','resolution_credit':0,'source_evidence_ref':EVID.as_posix(),'external_authority_resolution_claimed':False})
    if len({p['problem_uid'] for p in problems})!=len(problems): die('PROBLEM_UID_COLLISION')
    pages=Counter(p['page_uid'] for p in problems); cats=Counter(p['category'] for p in problems); classes=Counter(p['gap_class'] for p in problems); owners=Counter(p['gap_owner'] for p in problems)
    common={'schema_version':1,'normative_authority':False,'stage_uid':STAGE,'current_governance_uid':gov,'attempt_uid':e['attempt_uid'],'source_evidence_ref':EVID.as_posix(),'source_evidence_sha256':file_sha(EVID)}
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

    identity=identity_override or repo_identity(); loaded_at=stable_loaded_at(identity); read_set=canonical_read_set(); section_receipts=validate_sections(); norm_digest=normative_set_digest(read_set)
    entry_source=entry.get('source_identity') or {}; rule_digest=((reg.get('canonical_rule_registry') or {}).get('digest'))
    if not rule_digest or entry.get('canonical_rule_registry_digest')!=rule_digest: die('CANONICAL_RULE_DIGEST_DRIFT')
    writes=[(BASE/f'{n}.yaml').as_posix() for n in OUTS+SUPPORTS]
    docs['GOVERNANCE_EXECUTION_CONTEXT_RECEIPT']={
      **common,'artifact_type':'GOVERNANCE_EXECUTION_CONTEXT_RECEIPT','producer_operation_uid':OWNER_OPERATION,'policy_ref':CYCLE.as_posix(),'active_work_unit_ref':WORK_UNIT,'semantic_concern':SEMANTIC_CONCERN,'canonical_owner_operation':OWNER_OPERATION,
      'repository_identity':identity,'current_registry':{'entry_ref':ENTRY.as_posix(),'entry_sha256':file_sha(ENTRY),'registry_ref':REG.as_posix(),'registry_sha256':file_sha(REG),'canonical_rule_registry_ref':RULE.as_posix(),'canonical_rule_registry_sha256':file_sha(RULE),'canonical_rule_registry_digest':rule_digest,'verified_source_revision':entry_source.get('verified_source_revision'),'deterministic_source_bundle_sha256':entry_source.get('deterministic_source_bundle_sha256')},
      'exact_read_set':read_set,'exact_write_targets':writes,'duplicate_search_result':'EXISTING_CANONICAL_COMPILER_OWNER_REUSED_NO_PRIOR_SUPPORT_RECEIPT_OWNER_FOUND','confirmed_gap_uid':WORK_UNIT,'loaded_at_utc':loaded_at,'product_blocker_credit':0,'stage03_allowed':False,'result':'PASS_CONTEXT_RESOLVED'}
    dep_hashes={p.as_posix():file_sha(p) for p in [EVID,FROZEN,R1,LIFE,INV,STATE,CAL]}
    docs['EXECUTION_CYCLE_PREFLIGHT_RECEIPT']={
      **common,'artifact_type':'EXECUTION_CYCLE_PREFLIGHT_RECEIPT','producer_operation_uid':OWNER_OPERATION,'policy_ref':CYCLE.as_posix(),'active_work_unit_ref':WORK_UNIT,'selected_execution_profile_uid':((entry.get('selected_execution_profile') or {}).get('profile_uid')),'execution_identity':identity,
      'governance_load':{'governance_uid':gov,'root_manifest_ref':ROOT_MANIFEST.as_posix(),'root_manifest_sha256':file_sha(ROOT_MANIFEST),'effective_normative_set_sha256':norm_digest,'resolved_section_uid_receipts':section_receipts,'dependency_artifact_hashes':dep_hashes,'acceptance_blueprint_ref':ACCEPTANCE.as_posix(),'acceptance_blueprint_sha256':file_sha(ACCEPTANCE),'loader_identity':'governance/ci/compile_stage_execution_preflight.py','loader_version':'2','loaded_at_utc':loaded_at},
      'canonical_stage_output_denominator_count':len(outputs),'canonical_stage_output_denominator':outputs,'canonical_preflight_generated_output_refs':[(BASE/f'{n}.yaml').as_posix() for n in OUTS],'support_receipt_refs':[(BASE/f'{n}.yaml').as_posix() for n in SUPPORTS],'fresh_problem_count':len(problems),'common_engine_repair_requires_replay':True,'product_blocker_credit':0,'stage_exit_allowed':False,'stage03_allowed':False,'result':'PASS_GOVERNANCE_LOADED_FOR_PREFLIGHT'}
    support_dig={n:sha(yaml.safe_dump(docs[n],sort_keys=False,allow_unicode=True).encode()) for n in SUPPORTS}
    dig={n:sha(yaml.safe_dump(d,sort_keys=False,allow_unicode=True).encode()) for n,d in docs.items() if n not in {'STAGE_EXECUTION_PREFLIGHT_RECEIPT',*SUPPORTS}}
    docs['STAGE_EXECUTION_PREFLIGHT_RECEIPT']={**common,'artifact_type':'STAGE_EXECUTION_PREFLIGHT_RECEIPT','operation_uid':prod['STAGE_EXECUTION_PREFLIGHT_RECEIPT'],'invariant_uid':'GOV-INV-CANONICAL-STAGE-EXECUTION-OPTIMIZATION-001','required_output_types':outputs,'canonical_preflight_output_digests':dig,'policy_support_receipt_digests':support_dig,'policy_support_receipt_refs':[(BASE/f'{n}.yaml').as_posix() for n in SUPPORTS],'fresh_problem_count':len(problems),'preserved_verified_resolution_entry_count':len(entries),'single_current_problem_register':True,'append_only_resolution_ledger':True,'dependency_ordered_remediation_required':True,'local_impact_validation_required':True,'checkpoint_full_sweep_required':True,'stage_exit_allowed':False,'stage03_allowed':False,'result':'PASS_PREFLIGHT_WITH_OPEN_PRODUCT_GAPS'}
    return docs

def write(docs):
    BASE.mkdir(parents=True,exist_ok=True)
    for n in OUTS+SUPPORTS: (BASE/f'{n}.yaml').write_text(yaml.safe_dump(docs[n],sort_keys=False,allow_unicode=True),encoding='utf-8')
def check(docs):
    for n in OUTS+SUPPORTS:
        if y(BASE/f'{n}.yaml')!=docs[n]: die(f'PREFLIGHT_OUTPUT_DRIFT:{n}')
    print(f'PASS: canonical {STAGE} logical outputs={len(OUTS)}/{len(OUTS)} plus policy support receipts={len(SUPPORTS)}/{len(SUPPORTS)} exact')
    print(f'PASS: official Stage-02 output denominator remains {docs["EXECUTION_CYCLE_PREFLIGHT_RECEIPT"]["canonical_stage_output_denominator_count"]}')
    print(f'PASS: CURRENT_PROBLEM_REGISTER fresh problems={docs["CURRENT_PROBLEM_REGISTER"]["fresh_physical_problem_count"]} stable UIDs')
    print(f'PASS: RESOLUTION_LEDGER entries={len(docs["RESOLUTION_LEDGER"]["entries"])} append-only')
def main():
    p=argparse.ArgumentParser(); p.add_argument('--stage',default=STAGE); g=p.add_mutually_exclusive_group(required=True); g.add_argument('--materialize',action='store_true'); g.add_argument('--check',action='store_true'); a=p.parse_args()
    if a.stage!=STAGE: die(f'UNSUPPORTED_STAGE_UNTIL_MATCHING_CURRENT_EVIDENCE_EXISTS:{a.stage}')
    docs=build(persisted_check_identity() if a.check else None)
    if a.materialize: write(docs)
    check(docs)
if __name__=='__main__': main()
