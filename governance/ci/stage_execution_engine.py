#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib, json, subprocess, sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
CURRENT=ROOT/'GOVERNANCE_CURRENT.yaml'
REGISTRY=ROOT/'governance/specifications/REGISTRY.yaml'
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
SCOPE=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
LIFECYCLE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
ADAPTERS=ROOT/'governance/ci/stage_execution_semantic_adapters.yaml'
LEGACY_WRAPPER=ROOT/'governance/ci/compile_stage_execution_preflight.py'

EXPECTED_PHASES=[
'SESSION_BOOTSTRAP_RESUME_GATE','CURRENT_GOVERNANCE','CURRENT_SCOPE','WORK_UNIT','AUTHORITY','APPLICABILITY','DEPENDENCY',
'REQUIRED_FIELD_MANIFEST','STAGE_INPUT_CONTRACT','STAGE_OPERATIONS','OUTPUT_PRODUCER','CURRENT_PROBLEM_REGISTER',
'DENOMINATOR_SNAPSHOT','CHANGE_IMPACT','RESOLUTION_LEDGER','FRESH_EXECUTION','STAGE_SPECIFIC_SCANNER','GAP_CLASSIFICATION',
'OWNER_REMEDIATION','FRESH_REEXECUTION','HIDDEN_DEFECT_SWEEP','REQUIRED_EVIDENCE','EXACT_HEAD_GATES','TERMINAL_CLOSURE',
'PERSIST_RESUME','NEXT_STAGE']
REQUIRED_PREFLIGHT={'REQUIRED_FIELD_MANIFEST','FUNCTIONAL_CHAIN_MANIFEST','EFFECTIVE_CONTRACT_OVERLAY','DEPENDENCY_TOPOLOGY','DENOMINATOR_SNAPSHOT','CLASSIFICATION_RULESET','CHANGE_IMPACT_MAP','STAGE_EXECUTION_PREFLIGHT_RECEIPT'}
ROUTE_KEYS={'GOVERNANCE_DEFECT','AUTHORITY_GAP','PRODUCT_CONTRACT_GAP','RUNTIME_IMPLEMENTATION_GAP','EVIDENCE_STATE_GAP','EXTERNAL_AUTHORITY_GAP'}
EVIDENCE_FIELDS={'artifact_type','governance_uid','stage_uid','attempt_uid','scope_manifest_ref','actual_stage_execution_started','actual_stage_execution_completed','fresh_execution','prior_results_used','current_specification_mutated','denominator','gaps','closure_blockers','required_evidence','result','stage_exit_allowed','source_head_sha'}

class StageEngineError(RuntimeError): pass
def fail(msg): raise StageEngineError(msg)
def y(path):
    if not path.is_file(): fail(f'MISSING_FILE:{path.relative_to(ROOT)}')
    obj=yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(obj,dict): fail(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj
def j(path):
    if not path.is_file(): fail(f'MISSING_FILE:{path.relative_to(ROOT)}')
    obj=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj,dict): fail(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj
def identity():
    entry,reg=y(CURRENT),y(REGISTRY)
    gov=(reg.get('active_specification') or {}).get('governance_uid')
    if not gov or entry.get('active_governance_uid')!=gov: fail('CURRENT_GOVERNANCE_UID_DRIFT')
    if (entry.get('selected_execution_profile') or {}).get('registry')!=str(LIFECYCLE.relative_to(ROOT)): fail('SELECTED_PROFILE_REGISTRY_DRIFT')
    return entry,reg,str(gov)
def data():
    entry,reg,gov=identity()
    return entry,reg,gov,y(LIFECYCLE),y(ADAPTERS)
def stage_map(profile):
    rows=profile.get('stages') or []
    if not isinstance(rows,list) or not rows: fail('PROFILE_STAGES_EMPTY')
    out={}
    for row in rows:
        if not isinstance(row,dict) or not row.get('stage_uid'): fail('PROFILE_STAGE_RECORD_INVALID')
        uid=str(row['stage_uid'])
        if uid in out: fail(f'PROFILE_STAGE_DUPLICATE:{uid}')
        out[uid]=row
    return out

def validate_definition_data(profile,adapters):
    stages=stage_map(profile)
    if int(profile.get('profile_local_denominator') or -1)!=len(stages): fail('PROFILE_DENOMINATOR_DRIFT')
    common=adapters.get('common_execution_skeleton') or {}
    if common.get('phases')!=EXPECTED_PHASES or int(common.get('phase_count') or -1)!=len(EXPECTED_PHASES): fail('COMMON_EXECUTION_SKELETON_DRIFT')
    req=adapters.get('common_requirements') or {}
    expected={
      'definition_audit_may_claim_product_completion':False,'governance_maintenance_product_stage_credit':0,
      'actual_product_execution_requires_active_product_work_unit':True,'fresh_execution_required':True,
      'prior_result_may_replace_fresh_execution':False,'fresh_reexecution_after_remediation_required':True,
      'hidden_defect_sweep_required':True,'required_evidence_presence_only_is_pass':False,
      'exact_head_outer_terminal_conclusion_required':True,'stage_exit_requires_zero_open_gap_zero_blocker_zero_remaining_scope':True,
      'missing_stage_specific_scanner_contract':'BLOCK','missing_semantic_adapter':'BLOCK','missing_product_evidence_in_execution_mode':'BLOCK',
      'downstream_owned_gap_requires_owner_reentry':True}
    for k,v in expected.items():
        if req.get(k)!=v: fail(f'COMMON_REQUIREMENT_DRIFT:{k}')
    if set(adapters.get('owner_remediation_routes') or {})!=ROUTE_KEYS: fail('OWNER_REMEDIATION_ROUTE_DENOMINATOR_DRIFT')
    ads=adapters.get('stages') or {}
    if set(ads)!=set(stages): fail('SEMANTIC_ADAPTER_DENOMINATOR_DRIFT')
    if adapters.get('derived_from_profile_uid')!=profile.get('profile_uid'): fail('SEMANTIC_ADAPTER_PROFILE_UID_DRIFT')
    scalars=('stage_uid','name','scope_mode','entry_gate','exit_gate','next_stage_uid','pre_execution_gate')
    for uid,st in stages.items():
        for f in scalars:
            if not st.get(f): fail(f'STAGE_FIELD_MISSING:{uid}:{f}')
        for f in ('inputs','operations','outputs','validators','required_evidence','required_normative_section_uids'):
            vals=st.get(f)
            if not isinstance(vals,list) or not vals or len(vals)!=len(set(map(str,vals))): fail(f'STAGE_LIST_INVALID:{uid}:{f}')
        ins=list(map(str,st['inputs'])); origins=st.get('input_origins') or {}
        if not isinstance(origins,dict) or set(origins)!=set(ins): fail(f'STAGE_INPUT_ORIGIN_COVERAGE_INVALID:{uid}')
        outs=list(map(str,st['outputs'])); ops=set(map(str,st['operations'])); producers=st.get('output_producers') or {}
        if not isinstance(producers,dict) or set(producers)!=set(outs): fail(f'STAGE_OUTPUT_PRODUCER_COVERAGE_INVALID:{uid}')
        bad=sorted(set(map(str,producers.values()))-ops)
        if bad: fail(f'STAGE_OUTPUT_PRODUCER_NOT_OPERATION:{uid}:{bad}')
        if st.get('pre_execution_gate')!='GOVERNANCE_LOAD_RECEIPT_PASS': fail(f'STAGE_PREEXECUTION_GATE_DRIFT:{uid}')
        if (st.get('semantic_granularity_gate') or {}).get('mode')!='REQUIRED': fail(f'SEMANTIC_GRANULARITY_GATE_MISSING:{uid}')
        if (st.get('closure_evidence_continuity_gate') or {}).get('mode')!='REQUIRED': fail(f'CLOSURE_EVIDENCE_CONTINUITY_GATE_MISSING:{uid}')
        opt=st.get('canonical_execution_optimization_gate') or {}
        if opt.get('required') is not True or set(opt.get('preflight_manifest_set') or [])!=REQUIRED_PREFLIGHT: fail(f'CANONICAL_EXECUTION_GATE_DRIFT:{uid}')
        for k in ('one_current_problem_register_required','append_only_resolution_ledger_required','dependency_ordered_batches_required','incremental_impact_validation_required','checkpoint_full_sweep_required','engine_defect_requires_common_engine_repair_and_replay','explicit_stage_binding_required'):
            if opt.get(k) is not True: fail(f'CANONICAL_EXECUTION_FLAG_MISSING:{uid}:{k}')
        if st.get('work_unit_scope_source')!='CURRENT_EXECUTION_SCOPE_MANIFEST': fail(f'WORK_UNIT_SCOPE_SOURCE_DRIFT:{uid}')
        if st.get('stage_exit_scope_source')!='DECLARED_STAGE_REQUIRED_UNIVERSE_RECONCILIATION': fail(f'STAGE_EXIT_SCOPE_SOURCE_DRIFT:{uid}')
        if st.get('partial_work_unit_closure_may_grant_stage_exit') is not False: fail(f'PARTIAL_STAGE_EXIT_CREDIT_NOT_BLOCKED:{uid}')
        ad=ads[uid]
        if ad.get('profile_name')!=st.get('name'): fail(f'ADAPTER_PROFILE_NAME_DRIFT:{uid}')
        for f in ('semantic_dimensions','scanner_dimensions'):
            vals=ad.get(f)
            if not isinstance(vals,list) or not vals or len(vals)!=len(set(map(str,vals))): fail(f'ADAPTER_DIMENSIONS_INVALID:{uid}:{f}')
        if not ad.get('denominator_kind'): fail(f'ADAPTER_DENOMINATOR_KIND_MISSING:{uid}')
        if ad.get('scanner_mode') not in {'NORMALIZED_COMMON_EVIDENCE_CONTRACT','SPECIALIZED_COMPATIBILITY_PLUS_NORMALIZED_COMMON'}: fail(f'ADAPTER_SCANNER_MODE_INVALID:{uid}')
        if ad.get('product_completion_credit_from_definition_audit')!=0: fail(f'DEFINITION_AUDIT_PRODUCT_CREDIT_LEAK:{uid}')
        if ad.get('business_entity_gate_required') is True and not isinstance(st.get('business_entity_completeness_gate'),dict): fail(f'BUSINESS_ENTITY_GATE_REQUIRED_BUT_MISSING:{uid}')
    for uid,st in stages.items():
        nxt=str(st.get('next_stage_uid') or '')
        if nxt in stages:
            predecessor_exit=str(st.get('exit_gate') or '')
            successor_entry=str(stages[nxt].get('entry_gate') or '')
            exact_or_stricter=(
                successor_entry==predecessor_exit
                or successor_entry.startswith(predecessor_exit+'_AND_')
            )
            if not exact_or_stricter:
                fail(f'SUCCESSOR_GATE_MISMATCH:{uid}->{nxt}:{predecessor_exit}:{successor_entry}')
    return stages

def validate_definition():
    entry,reg,gov,profile,adapters=data()
    stages=validate_definition_data(profile,adapters)
    wrapper=LEGACY_WRAPPER.read_text(encoding='utf-8')
    if 'UNSUPPORTED_STAGE_UNTIL_MATCHING_CURRENT_EVIDENCE_EXISTS' in wrapper or "STAGE='STAGE-02'" in wrapper: fail('LEGACY_STAGE02_COMMON_ENGINE_LOGIC_STILL_IN_WRAPPER')
    if 'compatibility_main' not in wrapper: fail('STAGE02_COMPATIBILITY_WRAPPER_NOT_DELEGATING')
    return entry,reg,gov,profile,adapters,stages

def plan(stage_uid):
    entry,reg,gov,profile,adapters,stages=validate_definition()
    if stage_uid not in stages: fail(f'UNKNOWN_STAGE:{stage_uid}')
    st,ad=stages[stage_uid],adapters['stages'][stage_uid]
    semantic_phases={'AUTHORITY','APPLICABILITY','REQUIRED_FIELD_MANIFEST','STAGE_INPUT_CONTRACT','STAGE_OPERATIONS','OUTPUT_PRODUCER','STAGE_SPECIFIC_SCANNER','GAP_CLASSIFICATION','OWNER_REMEDIATION','REQUIRED_EVIDENCE'}
    return {'artifact_type':'COMMON_STAGE_EXECUTION_PLAN','normative_authority':False,'governance_uid':gov,'selected_profile_uid':profile.get('profile_uid'),'stage_uid':stage_uid,'stage_name':st.get('name'),'scope_mode':st.get('scope_mode'),'entry_gate':st.get('entry_gate'),'exit_gate':st.get('exit_gate'),'next_stage_uid':st.get('next_stage_uid'),'semantic_dimensions':ad.get('semantic_dimensions'),'scanner_dimensions':ad.get('scanner_dimensions'),'denominator_kind':ad.get('denominator_kind'),'operations':st.get('operations'),'outputs':st.get('outputs'),'output_producers':st.get('output_producers'),'validators':st.get('validators'),'required_evidence_types':st.get('required_evidence'),'phases':[{'ordinal':i+1,'phase_uid':ph,'executor_owner':'COMMON_STAGE_EXECUTION_ENGINE','semantic_owner':'STAGE_SEMANTIC_ADAPTER' if ph in semantic_phases else 'COMMON_STAGE_EXECUTION_ENGINE','definition_status':'BOUND'} for i,ph in enumerate(EXPECTED_PHASES)],'definition_audit_product_completion_credit':0}

def active_product(stage_uid):
    entry,reg,gov,profile,adapters,stages=validate_definition()
    state,scope=y(STATE),y(SCOPE)
    if state.get('current_primary_task_layer')!='PRODUCT_STAGE_EXECUTION': fail('PRODUCT_EXECUTION_REQUIRES_PRODUCT_STAGE_PRIMARY_TASK')
    work=state.get('active_work_unit')
    if not isinstance(work,dict): fail('ACTIVE_PRODUCT_WORK_UNIT_MISSING')
    if work.get('primary_task_layer')!='PRODUCT_STAGE_EXECUTION': fail('ACTIVE_WORK_UNIT_NOT_PRODUCT_STAGE_EXECUTION')
    if work.get('stage_uid')!=stage_uid: fail('ACTIVE_WORK_UNIT_STAGE_MISMATCH')
    if str(work.get('current_status') or '').startswith('CLOSED'): fail('ACTIVE_PRODUCT_WORK_UNIT_ALREADY_CLOSED')
    if scope.get('governance_uid')!=gov or not scope.get('included_units'): fail('CURRENT_SCOPE_INVALID')
    deps=work.get('dependencies') or []
    if not isinstance(deps,list) or not deps: fail('ACTIVE_PRODUCT_WORK_UNIT_DEPENDENCY_CLOSURE_MISSING')
    for rel in deps:
        if isinstance(rel,str) and '/' in rel and not (ROOT/rel).exists(): fail(f'ACTIVE_PRODUCT_WORK_UNIT_DEPENDENCY_MISSING:{rel}')
    req=set(map(str,work.get('required_outputs') or [])); prof=set(map(str,stages[stage_uid].get('outputs') or []))
    if req and not prof.issubset(req): fail('ACTIVE_WORK_UNIT_OUTPUT_DENOMINATOR_INCOMPLETE')
    return work
def admission(stage_uid):
    work=active_product(stage_uid); pl=plan(stage_uid)
    print(f"PASS: common engine admission context resolved for {stage_uid} work_unit={work.get('work_unit_uid')}")
    print(f"PASS: common execution skeleton phases={len(pl['phases'])}/{len(EXPECTED_PHASES)}")
    print('PASS: admission check performs no product execution and grants zero completion credit')

def validate_evidence(stage_uid,path):
    entry,reg,gov,profile,adapters,stages=validate_definition()
    e=j(path); missing=sorted(EVIDENCE_FIELDS-set(e))
    if missing: fail(f'NORMALIZED_EVIDENCE_FIELD_MISSING:{missing}')
    if e.get('governance_uid')!=gov or e.get('stage_uid')!=stage_uid: fail('EVIDENCE_IDENTITY_DRIFT')
    if e.get('scope_manifest_ref')!=str(SCOPE.relative_to(ROOT)): fail('EVIDENCE_SCOPE_MANIFEST_REF_DRIFT')
    if e.get('actual_stage_execution_started') is not True or e.get('actual_stage_execution_completed') is not True: fail('EVIDENCE_ACTUAL_EXECUTION_NOT_COMPLETE')
    if e.get('fresh_execution') is not True or e.get('prior_results_used') is not False: fail('EVIDENCE_FRESH_EXECUTION_PROVENANCE_INVALID')
    if e.get('current_specification_mutated') is not False: fail('EVIDENCE_CURRENT_SPECIFICATION_MUTATION_FORBIDDEN')
    d=e.get('denominator')
    if not isinstance(d,dict): fail('EVIDENCE_DENOMINATOR_INVALID')
    for k in ('required_total','open_gap_total','closure_blocker_total','remaining_scope_total'):
        if not isinstance(d.get(k),int) or d.get(k)<0: fail(f'EVIDENCE_DENOMINATOR_FIELD_INVALID:{k}')
    if not isinstance(e.get('gaps'),list) or len(e['gaps'])!=d['open_gap_total']: fail('EVIDENCE_OPEN_GAP_DENOMINATOR_DRIFT')
    if not isinstance(e.get('closure_blockers'),list) or len(e['closure_blockers'])!=d['closure_blocker_total']: fail('EVIDENCE_BLOCKER_DENOMINATOR_DRIFT')
    req=set(map(str,stages[stage_uid].get('required_evidence') or [])); items=e.get('required_evidence')
    if not isinstance(items,list): fail('REQUIRED_EVIDENCE_LEDGER_INVALID')
    got={str(x.get('evidence_type')) for x in items if isinstance(x,dict)}
    if not req.issubset(got): fail(f'REQUIRED_EVIDENCE_TYPE_MISSING:{sorted(req-got)}')
    for item in items:
        if not isinstance(item,dict) or item.get('status')!='PASS' or not item.get('ref'): fail('REQUIRED_EVIDENCE_ITEM_INVALID')
        if not item.get('external_receipt') and not (ROOT/str(item['ref'])).is_file(): fail(f'REQUIRED_EVIDENCE_PHYSICAL_REF_MISSING:{item["ref"]}')
    if e.get('result') not in {'PASS','BLOCKED'}: fail('EVIDENCE_RESULT_INVALID')
    if e['result']=='PASS':
        if any(d[k]!=0 for k in ('open_gap_total','closure_blocker_total','remaining_scope_total')): fail('PASS_WITH_NONZERO_DENOMINATOR')
        if e.get('stage_exit_allowed') is not True: fail('PASS_WITH_STAGE_EXIT_BLOCKED')
    elif e.get('stage_exit_allowed') is not False: fail('BLOCKED_WITH_STAGE_EXIT_ALLOWED')
    return e

def validate_terminal(stage_uid,evidence,receipt):
    e=validate_evidence(stage_uid,evidence)
    if e.get('result')!='PASS': fail('TERMINAL_CLOSURE_REQUIRES_PASS_EVIDENCE')
    r=j(receipt)
    for k in ('provider','repository_or_project','head_sha','run_id','job_denominator','conclusion','governance_uid','stage_uid'):
        if r.get(k) in (None,'',[]): fail(f'TERMINAL_RECEIPT_FIELD_MISSING:{k}')
    if r.get('governance_uid')!=e.get('governance_uid') or r.get('stage_uid')!=stage_uid or r.get('conclusion')!='success': fail('TERMINAL_RECEIPT_IDENTITY_OR_RESULT_DRIFT')
    if not isinstance(r.get('job_denominator'),list) or not r['job_denominator']: fail('TERMINAL_RECEIPT_JOB_DENOMINATOR_INVALID')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if r.get('head_sha')!=head: fail('TERMINAL_RECEIPT_HEAD_MISMATCH')
    print(f'PASS: terminal receipt exact-head closure valid for {stage_uid} head={head}')

def compatibility_main(stage_uid):
    _,_,_,_,adapters,stages=validate_definition()
    if stage_uid not in stages: fail(f'UNKNOWN_STAGE:{stage_uid}')
    module_name=(adapters['stages'][stage_uid]).get('python_compatibility_module')
    if not module_name: fail(f'NO_COMPATIBILITY_MODULE_REGISTERED:{stage_uid}')
    mod=importlib.import_module(str(module_name))
    if not hasattr(mod,'main'): fail('COMPATIBILITY_MODULE_MAIN_MISSING')
    mod.main()

def main():
    p=argparse.ArgumentParser(); g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--definition-audit-all',action='store_true'); g.add_argument('--plan',action='store_true'); g.add_argument('--admission-check',action='store_true'); g.add_argument('--validate-evidence',action='store_true'); g.add_argument('--validate-terminal-receipt',action='store_true')
    p.add_argument('--stage'); p.add_argument('--evidence'); p.add_argument('--receipt'); a=p.parse_args()
    try:
        if a.definition_audit_all:
            _,_,_,profile,_,stages=validate_definition()
            print(f'PASS: common Stage Execution Engine definition audit stages={len(stages)}/{profile.get("profile_local_denominator")} phases={len(EXPECTED_PHASES)}/{len(EXPECTED_PHASES)}')
            print('PASS: all profile stages have semantic adapters, scanner dimensions, denominator, operations, outputs, evidence and closure contracts')
            print('PASS: definition audit product_stage_credit=0; product PASS requires fresh evidence and exact-head terminal receipt')
            return
        if not a.stage: fail('STAGE_REQUIRED')
        if a.plan: print(json.dumps(plan(a.stage),ensure_ascii=False,indent=2)); return
        if a.admission_check: admission(a.stage); return
        if a.validate_evidence:
            if not a.evidence: fail('EVIDENCE_PATH_REQUIRED')
            validate_evidence(a.stage,ROOT/a.evidence); print(f'PASS: normalized fresh execution evidence valid for {a.stage}'); return
        if a.validate_terminal_receipt:
            if not a.evidence or not a.receipt: fail('EVIDENCE_AND_RECEIPT_REQUIRED')
            validate_terminal(a.stage,ROOT/a.evidence,ROOT/a.receipt); return
    except StageEngineError as exc:
        print(f'BLOCK: {exc}',file=sys.stderr); raise SystemExit(1)
if __name__=='__main__': main()
