#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'governance/specifications/REGISTRY.yaml'
LIFECYCLE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
ADAPTERS=ROOT/'governance/ci/stage_execution_semantic_adapters.yaml'
PRODUCT_ROOT_ENV='ACPOS_PRODUCT_ROOT'
ACTIVE_WORK_UNIT_ENV='ACPOS_ACTIVE_WORK_UNIT'
CURRENT_SCOPE_ENV='ACPOS_CURRENT_SCOPE'

EXPECTED_PHASES=[
'SESSION_BOOTSTRAP_RESUME_GATE','CURRENT_GOVERNANCE','CURRENT_SCOPE','WORK_UNIT','AUTHORITY','APPLICABILITY','DEPENDENCY',
'REQUIRED_FIELD_MANIFEST','STAGE_INPUT_CONTRACT','STAGE_OPERATIONS','OUTPUT_PRODUCER','CURRENT_PROBLEM_REGISTER',
'DENOMINATOR_SNAPSHOT','CHANGE_IMPACT','RESOLUTION_LEDGER','FRESH_EXECUTION','STAGE_SPECIFIC_SCANNER','GAP_CLASSIFICATION',
'OWNER_REMEDIATION','FRESH_REEXECUTION','HIDDEN_DEFECT_SWEEP','REQUIRED_EVIDENCE','EXACT_HEAD_GATES','TERMINAL_CLOSURE',
'PERSIST_RESUME','NEXT_STAGE']
REQUIRED_PREFLIGHT={'REQUIRED_FIELD_MANIFEST','FUNCTIONAL_CHAIN_MANIFEST','EFFECTIVE_CONTRACT_OVERLAY','DEPENDENCY_TOPOLOGY','DENOMINATOR_SNAPSHOT','CLASSIFICATION_RULESET','CHANGE_IMPACT_MAP','STAGE_EXECUTION_PREFLIGHT_RECEIPT'}
ROUTE_KEYS={'GOVERNANCE_DEFECT','AUTHORITY_GAP','PRODUCT_CONTRACT_GAP','RUNTIME_IMPLEMENTATION_GAP','EVIDENCE_STATE_GAP','EXTERNAL_AUTHORITY_GAP'}
EVIDENCE_FIELDS={'actual_stage_execution_completed','actual_stage_execution_started','artifact_type','attempt_uid','closure_blockers','cross_stage_handoff','current_specification_mutated','denominator','exact_head_gate_receipts','fresh_execution','gaps','governance_uid','hidden_defect_sweep','next_stage_transition','operation_results','output_results','phase_trace','prior_results_used','remediation','required_evidence','result','resume_persistence','scanner_results','scope_manifest_ref','source_head_sha','stage_exit_allowed','stage_uid','validator_results'}
PHASE_TERMINAL_STATUSES={'PASS','BLOCKED','NOT_APPLICABLE_WITH_PROOF','NOT_EXECUTED_AFTER_BLOCK'}
RESULT_TERMINAL_STATUSES={'PASS','BLOCKED','NOT_APPLICABLE_WITH_PROOF'}

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
    reg=y(REGISTRY)
    spec_root=str(reg.get('rules_root') or '')
    if not spec_root: fail('REGISTRY_RULES_ROOT_MISSING')
    manifest_path=ROOT/spec_root/'SPECIFICATION_MANIFEST.yaml'
    manifest=y(manifest_path)
    gov=str(manifest.get('artifact_uid') or '')
    if not gov: fail('CURRENT_GOVERNANCE_UID_MISSING')
    if reg.get('lifecycle_registry')!=str(LIFECYCLE.relative_to(ROOT)): fail('SELECTED_PROFILE_REGISTRY_DRIFT')
    if (manifest.get('resolution_contract') or {}).get('canonical_root')!=spec_root: fail('CURRENT_SPECIFICATION_ROOT_DRIFT')
    return manifest,reg,gov
def data():
    entry,reg,gov=identity()
    return entry,reg,gov,y(LIFECYCLE),y(ADAPTERS)

def _external_yaml(path,label):
    if not path.is_file(): fail(label+'_MISSING:'+str(path))
    obj=yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(obj,dict): fail(label+'_MAPPING_REQUIRED')
    return obj

def product_execution_context():
    root_raw=os.environ.get(PRODUCT_ROOT_ENV,'').strip()
    work_rel=os.environ.get(ACTIVE_WORK_UNIT_ENV,'').strip()
    scope_rel=os.environ.get(CURRENT_SCOPE_ENV,'').strip()
    if not root_raw or not work_rel or not scope_rel:
        fail('PRODUCT_EXECUTION_CONTEXT_ENV_REQUIRED')
    product_root=Path(root_raw).resolve()
    if not product_root.is_dir(): fail('PRODUCT_EXECUTION_ROOT_MISSING')
    def resolve_rel(rel,label):
        p=Path(rel)
        if p.is_absolute() or '..' in p.parts: fail(label+'_PATH_INVALID')
        return product_root/p
    work_path=resolve_rel(work_rel,'ACTIVE_WORK_UNIT')
    scope_path=resolve_rel(scope_rel,'CURRENT_SCOPE')
    return product_root,_external_yaml(work_path,'ACTIVE_WORK_UNIT'),_external_yaml(scope_path,'CURRENT_SCOPE'),work_rel,scope_rel
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
    phase_contracts=common.get('phase_contracts') or {}
    if set(phase_contracts)!=set(EXPECTED_PHASES): fail('COMMON_PHASE_CONTRACT_DENOMINATOR_DRIFT')
    for ph in EXPECTED_PHASES:
        contract=phase_contracts.get(ph)
        if not isinstance(contract,dict) or not contract.get('required_artifact') or not contract.get('pass_condition'):
            fail(f'COMMON_PHASE_CONTRACT_INVALID:{ph}')
    req=adapters.get('common_requirements') or {}
    expected={
      'definition_audit_may_claim_product_completion':False,'governance_maintenance_product_stage_credit':0,
      'actual_product_execution_requires_active_product_work_unit':True,'fresh_execution_required':True,
      'prior_result_may_replace_fresh_execution':False,'fresh_reexecution_after_remediation_required':True,
      'hidden_defect_sweep_required':True,'required_evidence_presence_only_is_pass':False,
      'exact_head_outer_terminal_conclusion_required':True,'stage_exit_requires_zero_open_gap_zero_blocker_zero_remaining_scope':True,
      'missing_stage_specific_scanner_contract':'BLOCK','missing_semantic_adapter':'BLOCK','missing_product_evidence_in_execution_mode':'BLOCK',
      'downstream_owned_gap_requires_owner_reentry':True,'phase_trace_exact_order_required':True,
      'phase_trace_terminal_status_required':True,'operation_result_coverage_required':True,'output_result_coverage_required':True,
      'scanner_result_coverage_required':True,'validator_result_coverage_required':True,
      'remediation_reexecution_pair_required_when_gap_found':True,'zero_gap_remediation_may_be_not_applicable_with_proof':True,
      'hidden_defect_sweep_after_reexecution_required':True,'terminal_closure_requires_exact_head_gate_receipts':True,
      'persist_resume_before_next_stage_required':True,'next_stage_must_match_profile':True}
    for k,v in expected.items():
        if req.get(k)!=v: fail(f'COMMON_REQUIREMENT_DRIFT:{k}')
    if set(adapters.get('owner_remediation_routes') or {})!=ROUTE_KEYS: fail('OWNER_REMEDIATION_ROUTE_DENOMINATOR_DRIFT')
    driver=adapters.get('execution_driver_contract') or {}
    expected_driver={
      'driver_binding_source':'ACTIVE_WORK_UNIT','operation_universe_source':'SELECTED_PROFILE_STAGE_OPERATIONS',
      'output_producer_source':'SELECTED_PROFILE_STAGE_OUTPUT_PRODUCERS','semantic_adapter_source':'STAGE_EXECUTION_SEMANTIC_ADAPTER_REGISTRY',
      'scanner_universe_source':'STAGE_SEMANTIC_ADAPTER_SCANNER_DIMENSIONS','exact_operation_binding_coverage_required':True,
      'exact_scanner_binding_coverage_required':True,'executor_owner_required_per_operation':True,'result_owner_required_per_operation':True,
      'scanner_owner_required_per_dimension':True,'arbitrary_shell_command_from_adapter':'FORBIDDEN',
      'unregistered_operation_execution':'BLOCK','unregistered_scanner_execution':'BLOCK',
      'missing_operation_binding':'BLOCK','missing_scanner_binding':'BLOCK'}
    for k,v in expected_driver.items():
        if driver.get(k)!=v: fail(f'EXECUTION_DRIVER_CONTRACT_DRIFT:{k}')
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
        if uid=='STAGE-01':
            pg=st.get('pre_stage_source_projection_admission_gate') or {}
            if pg.get('required') is not True or pg.get('evaluation_boundary')!='BEFORE_PRODUCT_STAGE01_WORK_UNIT_ACTIVATION' or pg.get('freeze_state')!='SOURCE_PAIR_FROZEN' or pg.get('validator_uid')!='VAL-GOV-026':
                fail('PRE_STAGE_SOURCE_PROJECTION_GATE_INVALID')
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
    for _sid,_stage in stages.items():
        _gate=_stage.get('cross_stage_materialization_gate') or {}
        if _gate.get('required') is not True or _gate.get('invariant_uid')!='GOV-INV-CROSS-STAGE-MATERIALIZATION-CONSUMER-READINESS-001':
            fail(f'CROSS_STAGE_GATE_INVALID:{_sid}')
        for _k in ('reference_resolution_required','physical_materialization_required','parse_schema_required_field_completeness_required','denominator_inclusion_required','successor_consumer_readiness_required','successor_required_input_reconciliation_before_exit'):
            if _gate.get(_k) is not True:
                fail(f'CROSS_STAGE_GATE_FLAG_MISSING:{_sid}:{_k}')
        if _gate.get('reference_only_completion_credit')!=0:
            fail(f'CROSS_STAGE_REFERENCE_ONLY_CREDIT_LEAK:{_sid}')
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
    return entry,reg,gov,profile,adapters,stages

def plan(stage_uid):
    entry,reg,gov,profile,adapters,stages=validate_definition()
    if stage_uid not in stages: fail(f'UNKNOWN_STAGE:{stage_uid}')
    st,ad=stages[stage_uid],adapters['stages'][stage_uid]
    semantic_phases={'AUTHORITY','APPLICABILITY','REQUIRED_FIELD_MANIFEST','STAGE_INPUT_CONTRACT','STAGE_OPERATIONS','OUTPUT_PRODUCER','STAGE_SPECIFIC_SCANNER','GAP_CLASSIFICATION','OWNER_REMEDIATION','REQUIRED_EVIDENCE'}
    contracts=(adapters.get('common_execution_skeleton') or {}).get('phase_contracts') or {}
    return {'artifact_type':'COMMON_STAGE_EXECUTION_PLAN','normative_authority':False,'governance_uid':gov,'selected_profile_uid':profile.get('profile_uid'),'stage_uid':stage_uid,'stage_name':st.get('name'),'scope_mode':st.get('scope_mode'),'entry_gate':st.get('entry_gate'),'exit_gate':st.get('exit_gate'),'next_stage_uid':st.get('next_stage_uid'),'semantic_dimensions':ad.get('semantic_dimensions'),'scanner_dimensions':ad.get('scanner_dimensions'),'denominator_kind':ad.get('denominator_kind'),'operations':st.get('operations'),'outputs':st.get('outputs'),'output_producers':st.get('output_producers'),'validators':st.get('validators'),'required_evidence_types':st.get('required_evidence'),'phases':[{'ordinal':i+1,'phase_uid':ph,'executor_owner':'COMMON_STAGE_EXECUTION_ENGINE','semantic_owner':'STAGE_SEMANTIC_ADAPTER' if ph in semantic_phases else 'COMMON_STAGE_EXECUTION_ENGINE','required_artifact':contracts[ph]['required_artifact'],'pass_condition':contracts[ph]['pass_condition'],'definition_status':'BOUND'} for i,ph in enumerate(EXPECTED_PHASES)],'definition_audit_product_completion_credit':0}

def validate_stage01_source_projection_admission(work,stage):
    gate=stage.get('pre_stage_source_projection_admission_gate') or {}
    adm=work.get('source_projection_admission')
    if not isinstance(adm,dict): fail('STAGE01_SOURCE_PROJECTION_ADMISSION_BINDING_MISSING')
    applicability=adm.get('applicability')
    if applicability=='NOT_APPLICABLE_WITH_AUTHORITY':
        if not adm.get('authority_evidence_ref'): fail('STAGE01_SOURCE_PROJECTION_NA_AUTHORITY_MISSING')
        return True
    if applicability!='REQUIRED': fail('STAGE01_SOURCE_PROJECTION_APPLICABILITY_UNRESOLVED')
    bindings=adm.get('bindings')
    if not isinstance(bindings,list) or not bindings: fail('STAGE01_SOURCE_PROJECTION_BINDING_SET_MISSING')
    seen=set()
    required=['source_uid','freeze_receipt_ref','pair_hash','raw_source_sha256','projection_uid','projection_content_hash']
    for b in bindings:
        if not isinstance(b,dict) or list(b.keys())!=required: fail('STAGE01_SOURCE_PROJECTION_BINDING_SCHEMA_DRIFT')
        suid=str(b.get('source_uid') or '')
        if not suid or suid in seen: fail('STAGE01_SOURCE_PROJECTION_SOURCE_UID_INVALID:'+suid)
        seen.add(suid)
        rel=str(b.get('freeze_receipt_ref') or '')
        if not rel or rel.startswith('/') or '..' in Path(rel).parts: fail('STAGE01_SOURCE_PROJECTION_RECEIPT_REF_INVALID:'+suid)
        fp=ROOT/rel
        if not fp.is_file(): fail('STAGE01_SOURCE_PROJECTION_FREEZE_RECEIPT_MISSING:'+suid)
        fr=y(fp)
        if fr.get('artifact_type')!='SOURCE_PROJECTION_FREEZE_RECEIPT' or fr.get('source_uid')!=suid or fr.get('status')!='FROZEN_FOR_STAGE01' or fr.get('lock_state')!='SOURCE_PAIR_FROZEN' or fr.get('raw_source_writable') is not False or fr.get('projection_writable') is not False:
            fail('STAGE01_SOURCE_PROJECTION_FREEZE_RECEIPT_INVALID:'+suid)
        for k in ('pair_hash','raw_source_sha256','projection_uid','projection_content_hash'):
            if fr.get(k)!=b.get(k): fail('STAGE01_SOURCE_PROJECTION_BINDING_HASH_DRIFT:'+suid+':'+k)
    return True

def validate_work_unit_bindings(stage_uid,work,stages,adapters):
    if stage_uid not in stages: fail(f'UNKNOWN_STAGE:{stage_uid}')
    if not isinstance(work,dict): fail('ACTIVE_PRODUCT_WORK_UNIT_MISSING')
    if work.get('primary_task_layer')!='PRODUCT_STAGE_EXECUTION': fail('ACTIVE_WORK_UNIT_NOT_PRODUCT_STAGE_EXECUTION')
    if work.get('stage_uid')!=stage_uid: fail('ACTIVE_WORK_UNIT_STAGE_MISMATCH')
    if stage_uid=='STAGE-01': validate_stage01_source_projection_admission(work,stages[stage_uid])
    if str(work.get('current_status') or '').startswith('CLOSED'): fail('ACTIVE_PRODUCT_WORK_UNIT_ALREADY_CLOSED')
    req=set(map(str,work.get('required_outputs') or [])); prof=set(map(str,stages[stage_uid].get('outputs') or []))
    if req and not prof.issubset(req): fail('ACTIVE_WORK_UNIT_OUTPUT_DENOMINATOR_INCOMPLETE')
    op_bindings=work.get('operation_bindings')
    expected_ops=set(map(str,stages[stage_uid].get('operations') or []))
    if not isinstance(op_bindings,dict) or set(map(str,op_bindings))!=expected_ops:
        fail(f'ACTIVE_WORK_UNIT_OPERATION_BINDING_COVERAGE_INVALID:{stage_uid}')
    for uid,binding in op_bindings.items():
        if not isinstance(binding,dict) or not binding.get('executor_owner') or not binding.get('result_owner'):
            fail(f'ACTIVE_WORK_UNIT_OPERATION_BINDING_INVALID:{uid}')
    scan_bindings=work.get('scanner_bindings')
    expected_scans=set(map(str,(adapters['stages'][stage_uid]).get('scanner_dimensions') or []))
    if not isinstance(scan_bindings,dict) or set(map(str,scan_bindings))!=expected_scans:
        fail(f'ACTIVE_WORK_UNIT_SCANNER_BINDING_COVERAGE_INVALID:{stage_uid}')
    for uid,binding in scan_bindings.items():
        if not isinstance(binding,dict) or not binding.get('scanner_owner') or not binding.get('result_owner'):
            fail(f'ACTIVE_WORK_UNIT_SCANNER_BINDING_INVALID:{uid}')
    return True

def active_product(stage_uid):
    entry,reg,gov,profile,adapters,stages=validate_definition()
    product_root,work,scope,work_rel,scope_rel=product_execution_context()
    validate_work_unit_bindings(stage_uid,work,stages,adapters)
    if scope.get('stage_uid')!=stage_uid or scope.get('work_unit_uid')!=work.get('work_unit_uid'):
        fail('CURRENT_SCOPE_WORK_UNIT_BINDING_DRIFT')
    if scope.get('governance_uid') not in {None,gov}: fail('CURRENT_SCOPE_GOVERNANCE_UID_DRIFT')
    deps=work.get('dependencies') or []
    if not isinstance(deps,list) or not deps: fail('ACTIVE_PRODUCT_WORK_UNIT_DEPENDENCY_CLOSURE_MISSING')
    for dep in deps:
        if isinstance(dep,str) and '/' in dep and not (product_root/dep).exists():
            fail(f'ACTIVE_PRODUCT_WORK_UNIT_DEPENDENCY_MISSING:{dep}')
        if isinstance(dep,dict):
            ref=dep.get('ref') or dep.get('path') or dep.get('source_ref')
            if isinstance(ref,str) and '/' in ref and not (product_root/ref).exists():
                fail(f'ACTIVE_PRODUCT_WORK_UNIT_DEPENDENCY_MISSING:{ref}')
    return work

def admission(stage_uid):
    work=active_product(stage_uid); pl=plan(stage_uid)
    print(f"PASS: common engine admission context resolved for {stage_uid} work_unit={work.get('work_unit_uid')}")
    print(f"PASS: common execution skeleton phases={len(pl['phases'])}/{len(EXPECTED_PHASES)}")
    print('PASS: admission check performs no product execution and grants zero completion credit')

def _result_map(rows,key,label):
    if not isinstance(rows,list): fail(f'{label}_INVALID')
    out={}
    for row in rows:
        if not isinstance(row,dict) or not row.get(key): fail(f'{label}_ROW_INVALID')
        uid=str(row[key])
        if uid in out: fail(f'{label}_DUPLICATE:{uid}')
        if row.get('status') not in RESULT_TERMINAL_STATUSES: fail(f'{label}_STATUS_INVALID:{uid}')
        out[uid]=row
    return out

def validate_evidence_data(stage_uid,e):
    entry,reg,gov,profile,adapters,stages=validate_definition()
    if stage_uid not in stages: fail(f'UNKNOWN_STAGE:{stage_uid}')
    st=stages[stage_uid]; ad=adapters['stages'][stage_uid]
    missing=sorted(EVIDENCE_FIELDS-set(e))
    if missing: fail(f'NORMALIZED_EVIDENCE_FIELD_MISSING:{missing}')
    if e.get('governance_uid')!=gov or e.get('stage_uid')!=stage_uid: fail('EVIDENCE_IDENTITY_DRIFT')
    scope_ref=str(e.get('scope_manifest_ref') or '')
    if not scope_ref: fail('EVIDENCE_SCOPE_MANIFEST_REF_MISSING')
    if scope_ref.startswith('governance/test/'): fail('LEGACY_GOVERNANCE_TEST_SCOPE_REF_FORBIDDEN')
    if e.get('actual_stage_execution_started') is not True or e.get('actual_stage_execution_completed') is not True: fail('EVIDENCE_ACTUAL_EXECUTION_NOT_COMPLETE')
    if e.get('fresh_execution') is not True or e.get('prior_results_used') is not False: fail('EVIDENCE_FRESH_EXECUTION_PROVENANCE_INVALID')
    if e.get('current_specification_mutated') is not False: fail('EVIDENCE_CURRENT_SPECIFICATION_MUTATION_FORBIDDEN')
    head=str(e.get('source_head_sha') or '')
    if len(head)!=40 or any(ch not in '0123456789abcdef' for ch in head.lower()): fail('EVIDENCE_SOURCE_HEAD_SHA_INVALID')

    trace=e.get('phase_trace')
    if not isinstance(trace,list) or len(trace)!=len(EXPECTED_PHASES): fail('PHASE_TRACE_DENOMINATOR_DRIFT')
    seen=[]
    blocked_seen=False
    for idx,row in enumerate(trace):
        if not isinstance(row,dict) or row.get('phase_uid')!=EXPECTED_PHASES[idx]: fail(f'PHASE_TRACE_ORDER_DRIFT:{idx+1}')
        status=row.get('status')
        if status not in PHASE_TERMINAL_STATUSES: fail(f'PHASE_TRACE_STATUS_INVALID:{EXPECTED_PHASES[idx]}')
        if status=='NOT_APPLICABLE_WITH_PROOF' and not row.get('proof'): fail(f'PHASE_NA_PROOF_MISSING:{EXPECTED_PHASES[idx]}')
        if status=='BLOCKED': blocked_seen=True
        if status=='NOT_EXECUTED_AFTER_BLOCK' and not blocked_seen: fail(f'PHASE_NOT_EXECUTED_BEFORE_BLOCK:{EXPECTED_PHASES[idx]}')
        seen.append(status)

    ops=_result_map(e.get('operation_results'),'operation_uid','OPERATION_RESULTS')
    expected_ops=set(map(str,st.get('operations') or []))
    if set(ops)!=expected_ops: fail(f'OPERATION_RESULT_COVERAGE_DRIFT:expected={sorted(expected_ops)} actual={sorted(ops)}')
    outs=_result_map(e.get('output_results'),'output_uid','OUTPUT_RESULTS')
    expected_outs=set(map(str,st.get('outputs') or []))
    if set(outs)!=expected_outs: fail(f'OUTPUT_RESULT_COVERAGE_DRIFT:expected={sorted(expected_outs)} actual={sorted(outs)}')
    for uid,row in outs.items():
        if row.get('producer_operation_uid')!=str((st.get('output_producers') or {}).get(uid)): fail(f'OUTPUT_PRODUCER_RESULT_DRIFT:{uid}')
    scans=_result_map(e.get('scanner_results'),'scanner_dimension','SCANNER_RESULTS')
    expected_scans=set(map(str,ad.get('scanner_dimensions') or []))
    if set(scans)!=expected_scans: fail(f'SCANNER_RESULT_COVERAGE_DRIFT:expected={sorted(expected_scans)} actual={sorted(scans)}')
    vals=_result_map(e.get('validator_results'),'validator_uid','VALIDATOR_RESULTS')
    expected_vals=set(map(str,st.get('validators') or []))
    if set(vals)!=expected_vals: fail(f'VALIDATOR_RESULT_COVERAGE_DRIFT:expected={sorted(expected_vals)} actual={sorted(vals)}')

    d=e.get('denominator')
    if not isinstance(d,dict): fail('EVIDENCE_DENOMINATOR_INVALID')
    for k in ('required_total','open_gap_total','closure_blocker_total','remaining_scope_total'):
        if not isinstance(d.get(k),int) or d.get(k)<0: fail(f'EVIDENCE_DENOMINATOR_FIELD_INVALID:{k}')
    if not isinstance(e.get('gaps'),list) or len(e['gaps'])!=d['open_gap_total']: fail('EVIDENCE_OPEN_GAP_DENOMINATOR_DRIFT')
    if not isinstance(e.get('closure_blockers'),list) or len(e['closure_blockers'])!=d['closure_blocker_total']: fail('EVIDENCE_BLOCKER_DENOMINATOR_DRIFT')

    remediation=e.get('remediation')
    if not isinstance(remediation,dict): fail('REMEDIATION_RESULT_INVALID')
    for k in ('discovered_gap_total','remediated_gap_total','unresolved_gap_total'):
        if not isinstance(remediation.get(k),int) or remediation.get(k)<0: fail(f'REMEDIATION_FIELD_INVALID:{k}')
    if remediation['discovered_gap_total'] != remediation['remediated_gap_total'] + remediation['unresolved_gap_total']:
        fail('REMEDIATION_DENOMINATOR_DRIFT')
    if remediation['discovered_gap_total']>0:
        if remediation.get('reexecution_required') is not True or remediation.get('reexecution_performed') is not True:
            fail('REMEDIATION_FRESH_REEXECUTION_MISSING')
    else:
        if remediation.get('reexecution_required') not in {False,None}: fail('ZERO_GAP_REEXECUTION_REQUIREMENT_INVALID')
    sweep=e.get('hidden_defect_sweep')
    if not isinstance(sweep,dict) or sweep.get('performed') is not True or sweep.get('result') not in {'PASS','BLOCKED'}:
        fail('HIDDEN_DEFECT_SWEEP_INVALID')
    if not isinstance(sweep.get('discovered_defect_total'),int) or sweep['discovered_defect_total']<0: fail('HIDDEN_DEFECT_COUNT_INVALID')

    req=set(map(str,st.get('required_evidence') or [])); items=e.get('required_evidence')
    if not isinstance(items,list): fail('REQUIRED_EVIDENCE_LEDGER_INVALID')
    got={str(x.get('evidence_type')) for x in items if isinstance(x,dict)}
    if not req.issubset(got): fail(f'REQUIRED_EVIDENCE_TYPE_MISSING:{sorted(req-got)}')
    for item in items:
        if not isinstance(item,dict) or item.get('status')!='PASS' or not item.get('ref'): fail('REQUIRED_EVIDENCE_ITEM_INVALID')
        if not item.get('external_receipt') and not (ROOT/str(item['ref'])).is_file(): fail(f'REQUIRED_EVIDENCE_PHYSICAL_REF_MISSING:{item["ref"]}')

    handoff=e.get('cross_stage_handoff')
    if not isinstance(handoff,dict):
        fail('CROSS_STAGE_HANDOFF_INVALID')
    required_handoff_fields={'ledger_ref','external_receipt','successor_stage_uid','reference_resolution_complete','physical_materialization_complete','required_field_completeness_complete','denominator_reconciled','consumer_readiness_complete','unresolved_required_dependency_total','status'}
    if not required_handoff_fields.issubset(handoff):
        fail('CROSS_STAGE_HANDOFF_FIELD_MISSING')
    if handoff.get('successor_stage_uid')!=st.get('next_stage_uid'):
        fail('CROSS_STAGE_HANDOFF_SUCCESSOR_DRIFT')
    if handoff.get('status') not in {'PASS','BLOCKED'}:
        fail('CROSS_STAGE_HANDOFF_STATUS_INVALID')
    if not isinstance(handoff.get('unresolved_required_dependency_total'),int) or handoff.get('unresolved_required_dependency_total')<0:
        fail('CROSS_STAGE_HANDOFF_UNRESOLVED_COUNT_INVALID')
    if not handoff.get('external_receipt'):
        ref=str(handoff.get('ledger_ref') or '')
        if not ref or not (ROOT/ref).is_file():
            fail('CROSS_STAGE_HANDOFF_LEDGER_PHYSICAL_REF_MISSING')
    if e.get('result')=='PASS':
        for key in ('reference_resolution_complete','physical_materialization_complete','required_field_completeness_complete','denominator_reconciled','consumer_readiness_complete'):
            if handoff.get(key) is not True:
                fail('PASS_WITH_CROSS_STAGE_HANDOFF_NOT_READY:'+key)
        if handoff.get('unresolved_required_dependency_total')!=0 or handoff.get('status')!='PASS':
            fail('PASS_WITH_UNRESOLVED_CROSS_STAGE_HANDOFF')
    gates=e.get('exact_head_gate_receipts')
    if not isinstance(gates,list) or not gates: fail('EXACT_HEAD_GATE_RECEIPTS_MISSING')
    for gate in gates:
        if not isinstance(gate,dict) or gate.get('head_sha')!=head or gate.get('conclusion')!='success' or not gate.get('run_id') or not gate.get('gate_uid'):
            fail('EXACT_HEAD_GATE_RECEIPT_INVALID')
    resume=e.get('resume_persistence')
    if not isinstance(resume,dict) or resume.get('performed') is not True or not resume.get('resume_point'):
        fail('RESUME_PERSISTENCE_INVALID')
    nxt=e.get('next_stage_transition')
    if not isinstance(nxt,dict) or nxt.get('next_stage_uid')!=st.get('next_stage_uid'):
        fail('NEXT_STAGE_TRANSITION_INVALID')
    if e.get('result') not in {'PASS','BLOCKED'}: fail('EVIDENCE_RESULT_INVALID')
    if e.get('result')=='BLOCKED':
        if nxt.get('status')!='BLOCKED': fail('BLOCKED_EVIDENCE_NEXT_STAGE_TRANSITION_NOT_BLOCKED')
    elif nxt.get('status') not in {'READY','PROJECT_COMPLETE','NEXT_PAGE_READY'}:
        fail('PASS_EVIDENCE_NEXT_STAGE_TRANSITION_INVALID')

    if e['result']=='PASS':
        if any(d[k]!=0 for k in ('open_gap_total','closure_blocker_total','remaining_scope_total')): fail('PASS_WITH_NONZERO_DENOMINATOR')
        if e.get('stage_exit_allowed') is not True: fail('PASS_WITH_STAGE_EXIT_BLOCKED')
        if any(x in {'BLOCKED','NOT_EXECUTED_AFTER_BLOCK'} for x in seen): fail('PASS_WITH_NONPASS_PHASE')
        for label,rows in [('OPERATION',ops),('OUTPUT',outs),('SCANNER',scans),('VALIDATOR',vals)]:
            bad=[uid for uid,row in rows.items() if row.get('status')!='PASS']
            if bad: fail(f'PASS_WITH_NONPASS_{label}:{bad}')
        if remediation['unresolved_gap_total']!=0: fail('PASS_WITH_UNRESOLVED_REMEDIATION')
        if sweep.get('result')!='PASS' or sweep.get('discovered_defect_total')!=0: fail('PASS_WITH_HIDDEN_DEFECT')
    else:
        if e.get('stage_exit_allowed') is not False: fail('BLOCKED_WITH_STAGE_EXIT_ALLOWED')
        if 'BLOCKED' not in seen: fail('BLOCKED_WITHOUT_BLOCKED_PHASE')
    return e

def validate_evidence(stage_uid,path):
    return validate_evidence_data(stage_uid,j(path))

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

def execute_active(stage_uid):
    _,_,_,_,adapters,stages=validate_definition()
    work=active_product(stage_uid)
    state=y(STATE); scope=y(SCOPE)
    if (work.get('pre_execution_gate_status')!='PASS'
        or scope.get('product_stage_execution_allowed') is not True
        or (state.get('resume_control') or {}).get('product_execution_allowed') is not True):
        fail('ACTIVE_STAGE_EXECUTION_NOT_ADMITTED')
    bindings=work.get('operation_bindings') or {}
    owners=sorted({str(v.get('executor_owner') or '') for v in bindings.values() if isinstance(v,dict)})
    if not owners or any(not x for x in owners): fail('ACTIVE_STAGE_EXECUTOR_OWNER_SET_INVALID')
    if len(owners)!=1: fail('ACTIVE_STAGE_MULTIPLE_EFFECTFUL_EXECUTOR_OWNERS_FORBIDDEN:'+repr(owners))
    owner=owners[0]
    rel=Path(owner)
    if rel.is_absolute() or '..' in rel.parts: fail('ACTIVE_STAGE_EXECUTOR_OWNER_PATH_INVALID')
    path=ROOT/rel
    if not path.is_file(): fail('ACTIVE_STAGE_EXECUTOR_OWNER_MISSING:'+owner)
    if path.resolve()==Path(__file__).resolve(): fail('COMMON_ENGINE_RECURSIVE_EXECUTOR_FORBIDDEN')
    adapter=(adapters.get('stages') or {}).get(stage_uid) or {}
    if adapter.get('effectful_executor_owner_resolution')!='CURRENT_WORK_UNIT_OPERATION_BINDING_ONLY':
        fail('ACTIVE_STAGE_EXECUTOR_OWNER_RESOLUTION_POLICY_INVALID:'+stage_uid)
    ref=str(adapter.get('stepwise_execution_contract_ref') or '')
    if ref!='stepwise_execution_defaults': fail('ACTIVE_STAGE_STEPWISE_EXECUTION_CONTRACT_REF_INVALID:'+stage_uid)
    stepwise=adapters.get('stepwise_execution_defaults')
    if not isinstance(stepwise,dict): fail('ACTIVE_STAGE_STEPWISE_EXECUTION_CONTRACT_MISSING:'+stage_uid)
    if stepwise.get('mode')!='OPERATION_BY_OPERATION': fail('ACTIVE_STAGE_STEPWISE_EXECUTION_MODE_INVALID:'+stage_uid)
    if stepwise.get('bulk_stage_materialization')!='FORBIDDEN': fail('ACTIVE_STAGE_BULK_MATERIALIZATION_NOT_FORBIDDEN:'+stage_uid)
    if stepwise.get('checkpoint_after_each_operation') is not True: fail('ACTIVE_STAGE_OPERATION_CHECKPOINT_NOT_REQUIRED:'+stage_uid)
    if stepwise.get('successor_requires_operation_pass') is not True: fail('ACTIVE_STAGE_SUCCESSOR_OPERATION_PASS_NOT_REQUIRED:'+stage_uid)
    fail('ACTIVE_STAGE_EFFECTFUL_ADAPTER_REQUIRES_OPERATION_LEVEL_ENGINE_MIGRATION:'+stage_uid)


def main():
    p=argparse.ArgumentParser(); g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--definition-audit-all',action='store_true'); g.add_argument('--plan',action='store_true'); g.add_argument('--admission-check',action='store_true'); g.add_argument('--validate-evidence',action='store_true'); g.add_argument('--validate-terminal-receipt',action='store_true'); g.add_argument('--execute',action='store_true')
    p.add_argument('--stage'); p.add_argument('--evidence'); p.add_argument('--receipt'); a=p.parse_args()
    try:
        if a.execute:
            if not a.stage: fail('STAGE_REQUIRED')
            execute_active(a.stage); return
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
