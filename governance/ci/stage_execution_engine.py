#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, re, subprocess, sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'governance/specifications/REGISTRY.yaml'
LIFECYCLE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
ADAPTERS=ROOT/'governance/ci/stage_execution_semantic_adapters.yaml'
INVARIANTS=ROOT/'.github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'
SOURCE_PACKAGE_ROOT=ROOT/'.github/governance-source/active/source'
STAGE1_SOURCE_CONTRACTS=SOURCE_PACKAGE_ROOT/'10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml'
STAGE1_PIPELINE_GUARD=SOURCE_PACKAGE_ROOT/'09_TESTS/governance/governance_stage1_pipeline_guard.py'
EXECUTION_ROOT_ENV='STAGE_EXECUTION_ROOT'
ACTIVE_WORK_UNIT_ENV='STAGE_ACTIVE_WORK_UNIT'
CURRENT_SCOPE_ENV='STAGE_CURRENT_SCOPE'

EXPECTED_PHASES=[
'SESSION_BOOTSTRAP_RESUME_GATE','CURRENT_GOVERNANCE','CURRENT_SCOPE','WORK_UNIT','AUTHORITY','APPLICABILITY','DEPENDENCY',
'REQUIRED_FIELD_MANIFEST','STAGE_INPUT_CONTRACT','STAGE_OPERATIONS','OUTPUT_PRODUCER','CURRENT_PROBLEM_REGISTER',
'DENOMINATOR_SNAPSHOT','CHANGE_IMPACT','RESOLUTION_LEDGER','FRESH_EXECUTION','STAGE_SPECIFIC_SCANNER','GAP_CLASSIFICATION',
'OWNER_REMEDIATION','FRESH_REEXECUTION','HIDDEN_DEFECT_SWEEP','REQUIRED_EVIDENCE','CONTENT_VALIDATION','TERMINAL_CLOSURE',
'STATE_CHECKPOINT','NEXT_STAGE']
REQUIRED_PREFLIGHT={'REQUIRED_FIELD_MANIFEST','FUNCTIONAL_CHAIN_MANIFEST','EFFECTIVE_CONTRACT_OVERLAY','DEPENDENCY_TOPOLOGY','DENOMINATOR_SNAPSHOT','CLASSIFICATION_RULESET','CHANGE_IMPACT_MAP','STAGE_EXECUTION_PREFLIGHT_RECEIPT'}
ROUTE_KEYS={'GOVERNANCE_DEFECT','AUTHORITY_GAP','EXECUTION_CONTRACT_GAP','RUNTIME_IMPLEMENTATION_GAP','EVIDENCE_STATE_GAP','EXTERNAL_AUTHORITY_GAP'}
EVIDENCE_FIELDS={'actual_stage_execution_completed','actual_stage_execution_started','artifact_type','attempt_uid','closure_blockers','current_specification_mutated','denominator','fresh_execution','gaps','governance_uid','hidden_defect_sweep','next_stage_transition','operation_results','output_results','phase_trace','prior_results_used','remediation','required_evidence','result','state_checkpoint','scanner_results','scope_manifest_ref','source_head_sha','stage_exit_allowed','stage_uid','validator_results'}
PHASE_TERMINAL_STATUSES={'PASS','BLOCKED','NOT_APPLICABLE_WITH_PROOF','NOT_EXECUTED_AFTER_BLOCK'}
RESULT_TERMINAL_STATUSES={'PASS','BLOCKED','NOT_APPLICABLE_WITH_PROOF'}

class StageEngineError(RuntimeError): pass
def fail(msg): raise StageEngineError(msg)
def _display_path(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)
def y(path):
    if not path.is_file(): fail(f'MISSING_FILE:{_display_path(path)}')
    obj=yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(obj,dict): fail(f'MAPPING_REQUIRED:{_display_path(path)}')
    return obj
def j(path):
    if not path.is_file(): fail(f'MISSING_FILE:{_display_path(path)}')
    obj=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj,dict): fail(f'MAPPING_REQUIRED:{_display_path(path)}')
    return obj
def identity():
    reg=y(REGISTRY)
    spec_root=str(reg.get('rules_root') or '')
    if not spec_root: fail('REGISTRY_RULES_ROOT_MISSING')
    manifest_path=ROOT/spec_root/'SPECIFICATION_MANIFEST.yaml'
    manifest=y(manifest_path)
    try:
        from governance_resolver import resolve as resolve_governance
        resolved=resolve_governance()
    except Exception as exc:
        fail('CURRENT_GOVERNANCE_RESOLUTION_FAILED:'+str(exc))
    gov=str(resolved.get('governance_uid') or '')
    if not gov: fail('CURRENT_GOVERNANCE_UID_MISSING')
    if resolved.get('identity_authority')!='governance/specifications/REGISTRY.yaml':
        fail('CURRENT_GOVERNANCE_IDENTITY_AUTHORITY_DRIFT')
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

def _execution_artifact_root():
    raw=os.environ.get(EXECUTION_ROOT_ENV,'').strip()
    root=Path(raw).resolve() if raw else ROOT
    if not root.is_dir(): fail('EXECUTION_ROOT_MISSING')
    return root


def _sha256_file(path):
    if not path.is_file(): fail('HASH_TARGET_MISSING:'+str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _require_nonempty_file(path,label):
    if not path.is_file():
        fail(label+'_MISSING:'+_display_path(path))
    try:
        size=path.stat().st_size
    except OSError as exc:
        fail(label+'_STAT_FAILED:'+str(exc))
    if size<=0:
        fail(label+'_EMPTY:'+_display_path(path))
    return size

def _validate_local_file_artifact(path,label):
    """Common file-backed artifact guard.

    This is intentionally product-neutral: it validates physical existence and
    bytes for every local required artifact, and invokes the registered
    serialization parser for YAML/JSON artifacts. Domain-specific validators
    remain responsible for schema/content semantics and hash re-derivation.
    """
    _require_nonempty_file(path,label)
    suffix=path.suffix.lower()
    if suffix in {'.yaml','.yml'}:
        try:
            obj=yaml.safe_load(path.read_text(encoding='utf-8'))
        except Exception as exc:
            fail(label+'_PARSE_FAILED:'+type(exc).__name__)
        if obj is None:
            fail(label+'_PARSED_EMPTY:'+_display_path(path))
    elif suffix=='.json':
        try:
            obj=json.loads(path.read_text(encoding='utf-8'))
        except Exception as exc:
            fail(label+'_PARSE_FAILED:'+type(exc).__name__)
        if obj is None:
            fail(label+'_PARSED_EMPTY:'+_display_path(path))
    return True

def _stage1_work_dir():
    raw=os.environ.get(ACTIVE_WORK_UNIT_ENV,'').strip()
    if not raw:
        fail('STAGE_ACTIVE_WORK_UNIT_ENV_REQUIRED_FOR_PROJECTION_VALIDATION')
    rel=Path(raw)
    if rel.is_absolute() or '..' in rel.parts:
        fail('STAGE_ACTIVE_WORK_UNIT_PATH_INVALID_FOR_PROJECTION_VALIDATION')
    execution_root=_execution_artifact_root().resolve()
    work_path=(execution_root/rel).resolve()
    try:
        work_path.relative_to(execution_root)
    except ValueError:
        fail('STAGE_ACTIVE_WORK_UNIT_PATH_ESCAPES_EXECUTION_ROOT')
    return work_path.parent

def _load_stage1_pipeline_guard():
    _require_nonempty_file(STAGE1_PIPELINE_GUARD,'STAGE01_PIPELINE_GUARD')
    spec=importlib.util.spec_from_file_location('_current_stage1_pipeline_guard',STAGE1_PIPELINE_GUARD)
    if spec is None or spec.loader is None:
        fail('STAGE01_PIPELINE_GUARD_IMPORT_SPEC_INVALID')
    mod=importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        fail('STAGE01_PIPELINE_GUARD_IMPORT_FAILED:'+repr(exc))
    if not callable(getattr(mod,'validate_pre_stage_source_projection',None)):
        fail('STAGE01_PIPELINE_GUARD_VALIDATOR_MISSING')
    return mod

def _validate_stage1_projection_physical_integrity(work,bindings):
    inv=(y(INVARIANTS).get('invariants') or {}).get('PHYSICAL_ARTIFACT_INTEGRITY') or {}
    if inv.get('invariant_uid')!='GOV-INV-PHYSICAL-ARTIFACT-INTEGRITY-001' or inv.get('independent_source_rederivation_validator_must_run_when_registered') is not True:
        fail('PHYSICAL_ARTIFACT_INTEGRITY_CONTRACT_MISSING')
    work_dir=_stage1_work_dir()
    contracts=y(STAGE1_SOURCE_CONTRACTS)
    projection_contract=(contracts.get('structured_document_source_projection_contract') or {}).get('projection') or {}
    template=str(projection_contract.get('artifact_path_template') or '')
    if not template or '{source_uid}' not in template:
        fail('STAGE01_SOURCE_PROJECTION_ARTIFACT_TEMPLATE_INVALID')
    for b in bindings:
        suid=str(b.get('source_uid') or '')
        rel=template.replace('{source_uid}',suid)
        proj_path=work_dir/rel
        _require_nonempty_file(proj_path,'STAGE01_SOURCE_PROJECTION_ARTIFACT:'+suid)
        projection=_external_yaml(proj_path,'STAGE01_SOURCE_PROJECTION_ARTIFACT')
        if projection.get('artifact_type')!='CANONICAL_SOURCE_PROJECTION':
            fail('STAGE01_SOURCE_PROJECTION_ARTIFACT_TYPE_INVALID:'+suid)
    rawcap_path=work_dir/'00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml'
    capstate_path=work_dir/'00_SOURCE_INTAKE/RAW_SOURCE_CAPTURE_STATE.yaml'
    _require_nonempty_file(rawcap_path,'STAGE01_RAW_SOURCE_REFERENCE_MANIFEST')
    _require_nonempty_file(capstate_path,'STAGE01_RAW_SOURCE_CAPTURE_STATE')
    rawcap=y(rawcap_path); capstate=y(capstate_path)
    guard=_load_stage1_pipeline_guard()
    try:
        result=guard.validate_pre_stage_source_projection(SOURCE_PACKAGE_ROOT,work_dir,rawcap,capstate)
    except Exception as exc:
        fail('STAGE01_SOURCE_PROJECTION_PHYSICAL_VALIDATOR_ERROR:'+repr(exc))
    failures=result.get('failures') or []
    if failures:
        fail('STAGE01_SOURCE_PROJECTION_PHYSICAL_VALIDATION_FAILED:'+repr(failures[:20]))
    recomputed=result.get('bindings') or {}
    expected_uids={str(b.get('source_uid') or '') for b in bindings}
    if set(map(str,recomputed))!=expected_uids:
        fail('STAGE01_SOURCE_PROJECTION_RECOMPUTED_SOURCE_SET_DRIFT')
    for b in bindings:
        suid=str(b.get('source_uid') or '')
        physical=recomputed.get(suid) or {}
        for key in ('pair_hash','raw_source_sha256','projection_uid','projection_content_hash'):
            if str(physical.get(key) or '')!=str(b.get(key) or ''):
                fail('STAGE01_SOURCE_PROJECTION_RECOMPUTED_BINDING_DRIFT:'+suid+':'+key)
    return True

def execution_compatibility_adapter():
    reg=y(REGISTRY)
    rel=str(reg.get('execution_environment_binding') or '')
    if not rel:
        fail('EXECUTION_ENVIRONMENT_BINDING_MISSING')
    p=Path(rel)
    if p.is_absolute() or '..' in p.parts:
        fail('EXECUTION_ENVIRONMENT_BINDING_PATH_INVALID')
    binding=y(ROOT/p)
    if binding.get('artifact_type')!='EXECUTION_ENVIRONMENT_BINDING' or binding.get('normative_authority') is not False:
        fail('EXECUTION_ENVIRONMENT_BINDING_AUTHORITY_INVALID')
    if binding.get('common_stage_definition_credit')!=0 or binding.get('common_stage_completion_credit')!=0:
        fail('EXECUTION_ENVIRONMENT_BINDING_COMMON_STAGE_CREDIT_NONZERO')
    rules=binding.get('rules') or {}
    if (rules.get('values_may_enter_reusable_stage_semantics') is not False
        or rules.get('values_may_define_common_stage_denominator') is not False
        or rules.get('compatibility_adapter_is_external_runtime_only') is not True
        or rules.get('compatibility_adapter_values_may_enter_reusable_stage_semantics') is not False
        or rules.get('compatibility_adapter_values_may_define_common_stage_denominator') is not False):
        fail('EXECUTION_ENVIRONMENT_BINDING_STAGE_ISOLATION_INVALID')
    compat=binding.get('execution_compatibility_adapter') or {}
    required=(
      'active_work_unit_task_layer_field','active_work_unit_task_layer_value',
      'scope_execution_allowed_field','resume_control_field',
      'resume_execution_allowed_field','operation_executor_execution_root_argument'
    )
    if set(compat)!=set(required):
        fail('EXECUTION_COMPATIBILITY_ADAPTER_SCHEMA_DRIFT')
    for key in required:
        value=compat.get(key)
        if not isinstance(value,str) or not value.strip():
            fail('EXECUTION_COMPATIBILITY_ADAPTER_VALUE_INVALID:'+key)
    arg=str(compat.get('operation_executor_execution_root_argument'))
    if not re.fullmatch(r'--[a-z0-9][a-z0-9-]*',arg):
        fail('EXECUTION_COMPATIBILITY_ADAPTER_ROOT_ARGUMENT_INVALID')
    return compat

def execution_context():
    root_raw=os.environ.get(EXECUTION_ROOT_ENV,'').strip()
    work_rel=os.environ.get(ACTIVE_WORK_UNIT_ENV,'').strip()
    scope_rel=os.environ.get(CURRENT_SCOPE_ENV,'').strip()
    if not root_raw or not work_rel or not scope_rel:
        fail('EXECUTION_CONTEXT_ENV_REQUIRED')
    execution_root=Path(root_raw).resolve()
    if not execution_root.is_dir(): fail('EXECUTION_ROOT_MISSING')
    def resolve_rel(rel,label):
        p=Path(rel)
        if p.is_absolute() or '..' in p.parts: fail(label+'_PATH_INVALID')
        return execution_root/p
    work_path=resolve_rel(work_rel,'ACTIVE_WORK_UNIT')
    scope_path=resolve_rel(scope_rel,'CURRENT_SCOPE')
    return execution_root,_external_yaml(work_path,'ACTIVE_WORK_UNIT'),_external_yaml(scope_path,'CURRENT_SCOPE'),work_rel,scope_rel
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
      'definition_audit_may_claim_execution_completion':False,'governance_maintenance_execution_credit':0,
      'actual_execution_requires_active_work_unit':True,'fresh_execution_required':True,
      'prior_result_may_replace_fresh_execution':False,'fresh_reexecution_after_remediation_required':True,
      'hidden_defect_sweep_required':True,'required_evidence_presence_only_is_pass':False,
      'exact_head_outer_terminal_conclusion_required':False,'generic_ci_or_workflow_state_is_stage_closure_authority':False,'validation_product_mutation_forbidden':True,'single_current_stage_state_authority':'EXECUTION_STATE','stage_exit_requires_zero_open_gap_zero_blocker_zero_remaining_scope':True,
      'missing_stage_specific_scanner_contract':'BLOCK','missing_semantic_adapter':'BLOCK','missing_execution_evidence_in_execution_mode':'BLOCK',
      'downstream_owned_gap_requires_owner_reentry':True,'phase_trace_exact_order_required':True,
      'phase_trace_terminal_status_required':True,'operation_result_coverage_required':True,'output_result_coverage_required':True,
      'scanner_result_coverage_required':True,'validator_result_coverage_required':True,
      'remediation_reexecution_pair_required_when_gap_found':True,'zero_gap_remediation_may_be_not_applicable_with_proof':True,
      'hidden_defect_sweep_after_reexecution_required':True,'terminal_closure_requires_exact_head_gate_receipts':False,
      'terminal_closure_requires_content_evidence':True,'execution_state_checkpoint_before_next_stage_required':True,'next_stage_must_match_profile':True}
    for k,v in expected.items():
        if req.get(k)!=v: fail(f'COMMON_REQUIREMENT_DRIFT:{k}')
    if set(adapters.get('owner_remediation_routes') or {})!=ROUTE_KEYS: fail('OWNER_REMEDIATION_ROUTE_DENOMINATOR_DRIFT')
    driver=adapters.get('execution_driver_contract') or {}
    expected_driver={
      'driver_binding_source':'ACTIVE_WORK_UNIT','operation_universe_source':'SELECTED_PROFILE_STAGE_OPERATIONS_FILTERED_BY_CURRENT_AUTHORITY_AND_APPLICABILITY',
      'operation_applicability_field':'applicability','allowed_operation_applicability':['REQUIRED','AUTHORIZED_NOT_APPLICABLE'],
      'authorized_not_applicable_requires_authority_evidence':True,'authorized_not_applicable_invokes_executor':False,
      'output_producer_source':'SELECTED_PROFILE_STAGE_OUTPUT_PRODUCERS','semantic_adapter_source':'STAGE_EXECUTION_SEMANTIC_ADAPTER_REGISTRY',
      'scanner_universe_source':'STAGE_SEMANTIC_ADAPTER_SCANNER_DIMENSIONS','exact_operation_binding_coverage_required':True,
      'exact_scanner_binding_coverage_required':True,'executor_owner_required_per_operation':True,'result_owner_required_per_operation':True,
      'scanner_owner_required_per_dimension':True,'arbitrary_shell_command_from_adapter':'FORBIDDEN',
      'unregistered_operation_execution':'BLOCK','unregistered_scanner_execution':'BLOCK',
      'missing_operation_binding':'BLOCK','missing_scanner_binding':'BLOCK',
      'operation_executor_protocol_required':True,
      'allowed_operation_executor_protocols':['PYTHON_STAGE_OPERATION_V1'],
      'operation_receipt_ref_required_per_operation':True,
      'operation_receipt_terminal_statuses':['PASS','NOT_APPLICABLE_WITH_PROOF'],
      'operation_execution_unit':'ONE_OPERATION_PER_ENGINE_INVOCATION',
      'operation_checkpoint_after_pass_required':True,
      'stage_closure_may_be_auto_claimed_by_operation_executor':False}
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
        pg=st.get('pre_stage_source_projection_admission_gate')
        if pg is not None:
            if not isinstance(pg,dict) or pg.get('required') is not True or pg.get('evaluation_boundary')!='BEFORE_PROFILE_FIRST_STAGE_WORK_UNIT_ACTIVATION' or pg.get('freeze_state')!='SOURCE_PAIR_FROZEN' or pg.get('validator_uid')!='VAL-GOV-026':
                fail('PRE_STAGE_SOURCE_PROJECTION_GATE_INVALID:'+uid)
        if (st.get('semantic_granularity_gate') or {}).get('mode')!='REQUIRED': fail(f'SEMANTIC_GRANULARITY_GATE_MISSING:{uid}')
        if (st.get('closure_evidence_continuity_gate') or {}).get('mode')!='REQUIRED': fail(f'CLOSURE_EVIDENCE_CONTINUITY_GATE_MISSING:{uid}')
        opt=st.get('canonical_execution_optimization_gate') or {}
        if opt.get('required') is not True or set(opt.get('preflight_manifest_set') or [])!=REQUIRED_PREFLIGHT: fail(f'CANONICAL_EXECUTION_GATE_DRIFT:{uid}')
        for k in ('one_current_problem_register_required','append_only_resolution_ledger_required','dependency_ordered_batches_required','incremental_impact_validation_required','checkpoint_full_sweep_required','engine_defect_requires_common_engine_repair_and_replay','explicit_stage_binding_required'):
            if opt.get(k) is not True: fail(f'CANONICAL_EXECUTION_FLAG_MISSING:{uid}:{k}')
        if st.get('work_unit_scope_source')!='CURRENT_EXECUTION_SCOPE_MANIFEST': fail(f'WORK_UNIT_SCOPE_SOURCE_DRIFT:{uid}')
        if st.get('stage_exit_scope_source')!='CURRENT_GOVERNED_UNIT_STAGE_REQUIRED_UNIVERSE_RECONCILIATION': fail(f'STAGE_EXIT_SCOPE_SOURCE_DRIFT:{uid}')
        if st.get('lifecycle_owner_granularity')!='GOVERNED_UNIT': fail(f'LIFECYCLE_OWNER_GRANULARITY_DRIFT:{uid}')
        if st.get('unrelated_same_stage_units_may_block_current_unit_exit') is not False: fail(f'UNRELATED_SAME_STAGE_UNIT_BARRIER_DRIFT:{uid}')
        if st.get('cross_unit_blocking_requires_explicit_required_dependency_edge') is not True: fail(f'CROSS_UNIT_DEPENDENCY_EDGE_RULE_DRIFT:{uid}')
        if st.get('partial_work_unit_closure_may_grant_stage_exit') is not False: fail(f'PARTIAL_STAGE_EXIT_CREDIT_NOT_BLOCKED:{uid}')
        ad=ads[uid]
        if ad.get('profile_name')!=st.get('name'): fail(f'ADAPTER_PROFILE_NAME_DRIFT:{uid}')
        if ad.get('effectful_executor_owner_resolution')!='CURRENT_WORK_UNIT_OPERATION_BINDING_ONLY':
            fail(f'ADAPTER_EFFECTFUL_EXECUTOR_OWNER_RESOLUTION_DRIFT:{uid}')
        for f in ('semantic_dimensions','scanner_dimensions'):
            vals=ad.get(f)
            if not isinstance(vals,list) or not vals or len(vals)!=len(set(map(str,vals))): fail(f'ADAPTER_DIMENSIONS_INVALID:{uid}:{f}')
        if not ad.get('denominator_kind'): fail(f'ADAPTER_DENOMINATOR_KIND_MISSING:{uid}')
        if ad.get('scanner_mode') not in {'NORMALIZED_COMMON_EVIDENCE_CONTRACT','SPECIALIZED_COMPATIBILITY_PLUS_NORMALIZED_COMMON'}: fail(f'ADAPTER_SCANNER_MODE_INVALID:{uid}')
        if ad.get('execution_completion_credit_from_definition_audit')!=0: fail(f'DEFINITION_AUDIT_EXECUTION_CREDIT_LEAK:{uid}')
        if ad.get('governed_entity_gate_mode')!='CONDITIONAL_BY_CURRENT_AUTHORITY_AND_APPLICABILITY': fail(f'GOVERNED_ENTITY_GATE_MODE_DRIFT:{uid}')
        entity_gate=st.get('governed_entity_completeness_gate')
        if isinstance(entity_gate,dict):
            if entity_gate.get('applicability')!='CONDITIONAL_BY_CURRENT_AUTHORITY_AND_GOVERNED_UNIT_SEMANTICS' or entity_gate.get('required_when_applicable') is not True or entity_gate.get('not_applicable_requires_authority_evidence') is not True:
                fail(f'GOVERNED_ENTITY_GATE_APPLICABILITY_CONTRACT_DRIFT:{uid}')
            if entity_gate.get('required') is True:
                fail(f'GOVERNED_ENTITY_GATE_UNIVERSALLY_REQUIRED:{uid}')
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
    validate_current_ledger_synchronization_contract()
    return entry,reg,gov,profile,adapters,stages

def resolve_stage_range(start_stage_uid,end_stage_uid):
    _,_,_,_,_,stages=validate_definition()
    order=list(stages)
    if start_stage_uid not in stages: fail('RANGE_START_NOT_REGISTERED:'+str(start_stage_uid))
    if end_stage_uid not in stages: fail('RANGE_END_NOT_REGISTERED:'+str(end_stage_uid))
    start=order.index(start_stage_uid); end=order.index(end_stage_uid)
    if start>end: fail('RANGE_ORDER_INVALID:'+str(start_stage_uid)+'>'+str(end_stage_uid))
    selected=order[start:end+1]
    if not selected: fail('RANGE_EMPTY')
    return selected

def plan_range(start_stage_uid,end_stage_uid):
    selected=resolve_stage_range(start_stage_uid,end_stage_uid)
    plans=[plan(uid) for uid in selected]
    return {
      'artifact_type':'COMMON_STAGE_RANGE_EXECUTION_PLAN',
      'normative_authority':False,
      'requested_start_stage_uid':start_stage_uid,
      'requested_end_stage_uid':end_stage_uid,
      'range_is_inclusive':True,
      'selected_stage_uids':selected,
      'selected_stage_count':len(selected),
      'system_selected_batch_size':False,
      'normal_stage_pass_behavior':'AUTO_CONTINUE_WITHIN_REQUESTED_RANGE',
      'normal_stage_boundary_user_prompt':'FORBIDDEN',
      'stop_conditions':['FORMAL_HUMAN_APPROVAL_REQUIRED','USER_DECISION_REQUIRED','BLOCKED','CURRENT_STATE_CONFLICT','REVERIFY_REQUIRED','SNAPSHOT_INVALIDATED','EXECUTION_FAILURE'],
      'plans':plans,
      'effectful_execution_credit':0
    }

def _deterministic_stage_audit_contract():
    inv=(y(INVARIANTS).get('invariants') or {}).get('DETERMINISTIC_STAGE_AUDIT') or {}
    if inv.get('invariant_uid')!='GOV-INV-DETERMINISTIC-STAGE-AUDIT-001':
        fail('DETERMINISTIC_STAGE_AUDIT_CONTRACT_MISSING')
    return inv

def validate_current_ledger_synchronization_contract():
    contract=_deterministic_stage_audit_contract().get('current_ledger_synchronization') or {}
    if str(contract.get('mutable_state_authority') or '')!='EXECUTION_STATE':
        fail('CURRENT_STATE_AUTHORITY_DRIFT')
    expected_projections={
      'RUN_MANIFEST','ARTIFACT_PLAN','GOVERNANCE_CURRENT','BRANCH_BASELINE',
      'GOVERNANCE_STAGE_LOCK','STAGE_EVIDENCE','DEPENDENCY_INDEX','REVERSE_DEPENDENCY_INDEX'
    }
    actual=set(map(str,contract.get('non_authoritative_projections') or []))
    if actual!=expected_projections:
        fail('CURRENT_STATE_PROJECTION_DENOMINATOR_DRIFT:expected='+repr(sorted(expected_projections))+':actual='+repr(sorted(actual)))
    if contract.get('projection_disagreement_may_override_execution_state') is not False:
        fail('CURRENT_STATE_PROJECTION_OVERRIDE_NOT_FORBIDDEN')
    if str(contract.get('disagreement_finding') or '')!='CURRENT_LEDGER_SYNCHRONIZATION_DRIFT':
        fail('CURRENT_LEDGER_SYNCHRONIZATION_FINDING_DRIFT')
    return True

def validate_release_identity_continuity(records):
    contract=_deterministic_stage_audit_contract().get('release_identity_continuity') or {}
    required=list(map(str,contract.get('required_chain') or []))
    finding=str(contract.get('broken_chain_finding') or 'RELEASE_IDENTITY_CONTINUITY_BROKEN')
    if not required: fail('RELEASE_IDENTITY_CONTINUITY_CONTRACT_EMPTY')
    if not isinstance(records,dict): fail(finding+':CHAIN_MAPPING_REQUIRED')
    missing=[uid for uid in required if uid not in records]
    if missing: fail(finding+':MISSING:'+','.join(missing))
    identities=[]
    for uid in required:
        rec=records.get(uid)
        if not isinstance(rec,dict): fail(finding+':RECORD_MAPPING_REQUIRED:'+uid)
        rid=str(rec.get('release_identity') or '').strip()
        if not rid: fail(finding+':RELEASE_IDENTITY_MISSING:'+uid)
        identities.append(rid)
    if len(set(identities))!=1:
        fail(finding+':IDENTITY_DRIFT')
    return identities[0]

def validate_environment_evidence(evidence,required_environment):
    contract=_deterministic_stage_audit_contract().get('environment_evidence_separation') or {}
    allowed=set(map(str,contract.get('environments') or []))
    required=str(required_environment or '').strip()
    if required not in allowed: fail('ENVIRONMENT_REQUIREMENT_INVALID:'+required)
    if not isinstance(evidence,dict): fail('ENVIRONMENT_EVIDENCE_MAPPING_REQUIRED')
    observed=str(evidence.get('environment') or '').strip()
    if observed not in allowed: fail('ENVIRONMENT_EVIDENCE_IDENTITY_INVALID:'+observed)
    if observed!=required:
        fail('CROSS_ENVIRONMENT_SUBSTITUTION_BLOCKED:'+observed+'->'+required)
    return True

def validate_production_release_acceptance(deployment_record,acceptance_record):
    validate_environment_evidence(deployment_record,'PRODUCTION')
    validate_environment_evidence(acceptance_record,'PRODUCTION')
    deployed=str(deployment_record.get('release_identity') or '').strip()
    accepted=str(acceptance_record.get('release_identity') or '').strip()
    if not deployed or not accepted or deployed!=accepted:
        fail('PRODUCTION_RELEASE_IDENTITY_MISMATCH')
    return True

def validate_reverify_propagation(stage_statuses,impacted_predecessor_uid):
    contract=_deterministic_stage_audit_contract().get('reverify_propagation_contract') or {}
    allowed=set(map(str,contract.get('allowed_descendant_dispositions') or []))
    if not allowed: fail('REVERIFY_PROPAGATION_ALLOWED_DISPOSITIONS_EMPTY')
    _,_,_,_,_,stages=validate_definition()
    order=list(stages)
    impacted=str(impacted_predecessor_uid or '')
    if impacted not in stages: fail('REVERIFY_PROPAGATION_PREDECESSOR_NOT_REGISTERED:'+impacted)
    if not isinstance(stage_statuses,dict): fail('REVERIFY_PROPAGATION_STATUS_MAPPING_REQUIRED')
    for sid in order[order.index(impacted)+1:]:
        status=str(stage_statuses.get(sid) or '').strip()
        if status not in allowed:
            fail('DOWNSTREAM_UNCONDITIONAL_CURRENT_PASS_AFTER_IMPACTED_PREDECESSOR_REVERIFY:'+sid+':'+status)
    return True

def production_redeploy_acceptance_disposition(current_deployment_record,prior_acceptance_record):
    validate_environment_evidence(current_deployment_record,'PRODUCTION')
    validate_environment_evidence(prior_acceptance_record,'PRODUCTION')
    current=str(current_deployment_record.get('release_identity') or '').strip()
    prior=str(prior_acceptance_record.get('release_identity') or '').strip()
    if not current or not prior: fail('PRODUCTION_RELEASE_IDENTITY_MISSING')
    if current!=prior:
        contract=_deterministic_stage_audit_contract().get('environment_evidence_separation') or {}
        return str(contract.get('production_redeploy_invalidates_prior_release_acceptance') or 'REVERIFY_REQUIRED')
    return 'CURRENT'

def validate_vertical_scope_identity(stage_records):
    contract=_deterministic_stage_audit_contract().get('vertical_lifecycle_contract') or {}
    fields=list(map(str,contract.get('sticky_identity_fields') or []))
    finding=str(contract.get('drift_finding') or 'VERTICAL_SCOPE_IDENTITY_DRIFT')
    start=str(contract.get('applies_from_stage') or '').strip()
    end_stage=str(contract.get('applies_through_stage') or '').strip()
    _,_,_,_,_,stages=validate_definition()
    order=list(stages)
    if not start or not end_stage:
        fail('VERTICAL_SCOPE_STAGE_RANGE_UNDECLARED')
    if start not in stages or end_stage not in stages:
        fail('VERTICAL_SCOPE_STAGE_RANGE_INVALID')
    selected=order[order.index(start):order.index(end_stage)+1]
    if not isinstance(stage_records,dict): fail(finding+':STAGE_RECORD_MAPPING_REQUIRED')
    for sid in selected:
        if sid not in stage_records or not isinstance(stage_records[sid],dict):
            fail(finding+':STAGE_RECORD_MISSING:'+sid)
    for field in fields:
        values=[]
        for sid in selected:
            value=str(stage_records[sid].get(field) or '').strip()
            if not value: fail(finding+':FIELD_MISSING:'+sid+':'+field)
            values.append(value)
        if len(set(values))!=1: fail(finding+':'+field)
    return True

def validate_full_lifecycle_closure(stage_statuses,impacted_reverify_count,stage11_eligibility):
    contract=_deterministic_stage_audit_contract().get('full_lifecycle_closure_contract') or {}
    _,_,_,_,_,stages=validate_definition()
    if not isinstance(stage_statuses,dict): fail('FULL_LIFECYCLE_STAGE_STATUS_MAPPING_REQUIRED')
    if contract.get('all_registered_stages_must_close_under_current_governance') is True:
        for sid in stages:
            if str(stage_statuses.get(sid) or '')!='CLOSED_PASS':
                fail('FULL_LIFECYCLE_STAGE_NOT_CLOSED_PASS:'+sid+':'+str(stage_statuses.get(sid) or ''))
    required_reverify=int(contract.get('impacted_reverify_count_required') or 0)
    if int(impacted_reverify_count)!=required_reverify:
        fail('FULL_LIFECYCLE_IMPACTED_REVERIFY_NONZERO:'+str(impacted_reverify_count))
    if contract.get('next_governed_unit_or_scope_completion_requires_registered_stage11_eligibility') is True:
        if not isinstance(stage11_eligibility,dict):
            fail('FULL_LIFECYCLE_STAGE11_ELIGIBILITY_RECORD_REQUIRED')
        if str(stage11_eligibility.get('operation_uid') or '')!='NEXT_GOVERNED_UNIT_ELIGIBILITY_EVALUATE':
            fail('FULL_LIFECYCLE_STAGE11_ELIGIBILITY_OPERATION_INVALID')
        if not str(stage11_eligibility.get('result') or '').strip():
            fail('FULL_LIFECYCLE_STAGE11_ELIGIBILITY_RESULT_MISSING')
    return True

def plan(stage_uid):
    entry,reg,gov,profile,adapters,stages=validate_definition()
    if stage_uid not in stages: fail(f'UNKNOWN_STAGE:{stage_uid}')
    st,ad=stages[stage_uid],adapters['stages'][stage_uid]
    semantic_phases={'AUTHORITY','APPLICABILITY','REQUIRED_FIELD_MANIFEST','STAGE_INPUT_CONTRACT','STAGE_OPERATIONS','OUTPUT_PRODUCER','STAGE_SPECIFIC_SCANNER','GAP_CLASSIFICATION','OWNER_REMEDIATION','REQUIRED_EVIDENCE'}
    contracts=(adapters.get('common_execution_skeleton') or {}).get('phase_contracts') or {}
    return {'artifact_type':'COMMON_STAGE_EXECUTION_PLAN','normative_authority':False,'governance_uid':gov,'selected_profile_uid':profile.get('profile_uid'),'stage_uid':stage_uid,'stage_name':st.get('name'),'scope_mode':st.get('scope_mode'),'entry_gate':st.get('entry_gate'),'exit_gate':st.get('exit_gate'),'next_stage_uid':st.get('next_stage_uid'),'semantic_dimensions':ad.get('semantic_dimensions'),'scanner_dimensions':ad.get('scanner_dimensions'),'denominator_kind':ad.get('denominator_kind'),'operations':st.get('operations'),'outputs':st.get('outputs'),'output_producers':st.get('output_producers'),'validators':st.get('validators'),'required_evidence_types':st.get('required_evidence'),'phases':[{'ordinal':i+1,'phase_uid':ph,'executor_owner':'COMMON_STAGE_EXECUTION_ENGINE','semantic_owner':'STAGE_SEMANTIC_ADAPTER' if ph in semantic_phases else 'COMMON_STAGE_EXECUTION_ENGINE','required_artifact':contracts[ph]['required_artifact'],'pass_condition':contracts[ph]['pass_condition'],'definition_status':'BOUND'} for i,ph in enumerate(EXPECTED_PHASES)],'definition_audit_execution_completion_credit':0}

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
        fp=_execution_artifact_root()/rel
        if not fp.is_file(): fail('STAGE01_SOURCE_PROJECTION_FREEZE_RECEIPT_MISSING:'+suid)
        fr=y(fp)
        if fr.get('artifact_type')!='SOURCE_PROJECTION_FREEZE_RECEIPT' or fr.get('source_uid')!=suid or fr.get('status')!='FROZEN_FOR_STAGE01' or fr.get('lock_state')!='SOURCE_PAIR_FROZEN' or fr.get('raw_source_writable') is not False or fr.get('projection_writable') is not False:
            fail('STAGE01_SOURCE_PROJECTION_FREEZE_RECEIPT_INVALID:'+suid)
        for k in ('pair_hash','raw_source_sha256','projection_uid','projection_content_hash'):
            if fr.get(k)!=b.get(k): fail('STAGE01_SOURCE_PROJECTION_BINDING_HASH_DRIFT:'+suid+':'+k)
    _validate_stage1_projection_physical_integrity(work,bindings)
    return True

def validate_work_unit_bindings(stage_uid,work,stages,adapters):
    if stage_uid not in stages: fail(f'UNKNOWN_STAGE:{stage_uid}')
    if not isinstance(work,dict): fail('ACTIVE_WORK_UNIT_MISSING')
    compat=execution_compatibility_adapter()
    layer_field=str(compat['active_work_unit_task_layer_field'])
    layer_value=str(compat['active_work_unit_task_layer_value'])
    if work.get(layer_field)!=layer_value: fail('ACTIVE_WORK_UNIT_TASK_LAYER_MISMATCH')
    if work.get('stage_uid')!=stage_uid: fail('ACTIVE_WORK_UNIT_STAGE_MISMATCH')
    if stages[stage_uid].get('pre_stage_source_projection_admission_gate') is not None:
        validate_stage01_source_projection_admission(work,stages[stage_uid])
    if str(work.get('current_status') or '').startswith('CLOSED'): fail('ACTIVE_WORK_UNIT_ALREADY_CLOSED')
    req=set(map(str,work.get('required_outputs') or [])); prof=set(map(str,stages[stage_uid].get('outputs') or []))
    if req and not prof.issubset(req): fail('ACTIVE_WORK_UNIT_OUTPUT_DENOMINATOR_INCOMPLETE')
    op_bindings=work.get('operation_bindings')
    expected_ops=set(map(str,stages[stage_uid].get('operations') or []))
    if not isinstance(op_bindings,dict) or set(map(str,op_bindings))!=expected_ops:
        fail(f'ACTIVE_WORK_UNIT_OPERATION_BINDING_COVERAGE_INVALID:{stage_uid}')
    driver=adapters.get('execution_driver_contract') or {}
    allowed_protocols=set(map(str,driver.get('allowed_operation_executor_protocols') or []))
    allowed_applicability=set(map(str,driver.get('allowed_operation_applicability') or []))
    applicability_field=str(driver.get('operation_applicability_field') or 'applicability')
    for uid,binding in op_bindings.items():
        if not isinstance(binding,dict) or not binding.get('result_owner') or not binding.get('operation_receipt_ref'):
            fail(f'ACTIVE_WORK_UNIT_OPERATION_BINDING_INVALID:{uid}')
        applicability=str(binding.get(applicability_field) or '')
        if applicability not in allowed_applicability:
            fail(f'ACTIVE_WORK_UNIT_OPERATION_APPLICABILITY_INVALID:{uid}')
        if applicability=='REQUIRED':
            governance_receipt_ref=str(binding.get('governance_load_receipt_ref') or '')
            if not governance_receipt_ref:
                fail(f'ACTIVE_WORK_UNIT_GOVERNANCE_LOAD_RECEIPT_REF_MISSING:{uid}')
            governance_receipt_path=Path(governance_receipt_ref)
            if governance_receipt_path.is_absolute() or '..' in governance_receipt_path.parts:
                fail(f'ACTIVE_WORK_UNIT_GOVERNANCE_LOAD_RECEIPT_REF_INVALID:{uid}')
        receipt_rel=Path(str(binding.get('operation_receipt_ref') or ''))
        if receipt_rel.is_absolute() or '..' in receipt_rel.parts:
            fail(f'ACTIVE_WORK_UNIT_OPERATION_RECEIPT_REF_PATH_INVALID:{uid}')
        if applicability=='AUTHORIZED_NOT_APPLICABLE':
            if driver.get('authorized_not_applicable_requires_authority_evidence') is not True or not str(binding.get('authority_evidence_ref') or '').strip():
                fail(f'ACTIVE_WORK_UNIT_OPERATION_NA_AUTHORITY_MISSING:{uid}')
            if binding.get('executor_owner') or binding.get('executor_protocol'):
                fail(f'ACTIVE_WORK_UNIT_OPERATION_NA_EFFECTFUL_EXECUTOR_FORBIDDEN:{uid}')
            continue
        if not binding.get('executor_owner') or not binding.get('executor_protocol'):
            fail(f'ACTIVE_WORK_UNIT_OPERATION_BINDING_INVALID:{uid}')
        if str(binding.get('executor_protocol')) not in allowed_protocols:
            fail(f'ACTIVE_WORK_UNIT_OPERATION_EXECUTOR_PROTOCOL_INVALID:{uid}')
        rel=Path(str(binding.get('executor_owner') or ''))
        if rel.is_absolute() or '..' in rel.parts:
            fail(f'ACTIVE_WORK_UNIT_EXECUTOR_OWNER_PATH_INVALID:{uid}')
    scan_bindings=work.get('scanner_bindings')
    expected_scans=set(map(str,(adapters['stages'][stage_uid]).get('scanner_dimensions') or []))
    if not isinstance(scan_bindings,dict) or set(map(str,scan_bindings))!=expected_scans:
        fail(f'ACTIVE_WORK_UNIT_SCANNER_BINDING_COVERAGE_INVALID:{stage_uid}')
    for uid,binding in scan_bindings.items():
        if not isinstance(binding,dict) or not binding.get('scanner_owner') or not binding.get('result_owner'):
            fail(f'ACTIVE_WORK_UNIT_SCANNER_BINDING_INVALID:{uid}')
    return True

def _matrix_get(value,path_tokens):
    cur=value
    for tok in path_tokens:
        if isinstance(cur,dict):
            if tok not in cur: fail('NORMATIVE_MATRIX_REQUIRED_FIELD_MISSING:'+str(tok))
            cur=cur[tok]
        elif isinstance(cur,list):
            if not isinstance(tok,int) or tok<0 or tok>=len(cur): fail('NORMATIVE_MATRIX_FIELD_PATH_INDEX_INVALID:'+str(tok))
            cur=cur[tok]
        else:
            fail('NORMATIVE_MATRIX_FIELD_PATH_UNRESOLVABLE:'+str(tok))
    return cur

def _matrix_nonblank(value):
    if value is None: return False
    if isinstance(value,str): return bool(value.strip())
    if isinstance(value,(list,dict)): return len(value)>0
    return True

def _validate_basic_design_domain_stepwise_checkpoints(stage_uid,execution_root,work,stage,gov,rows,phase,completed):
    inv=y(INVARIANTS)
    policy=((inv.get('invariants') or {}).get('BASIC_DESIGN_DOMAIN_STEPWISE_CHECKPOINT') or {})
    applicable_stage=str(policy.get('applicable_stage_uid') or '').strip()
    if not applicable_stage:
        fail('BASIC_DESIGN_CHECKPOINT_APPLICABLE_STAGE_UNDECLARED')
    if stage_uid!=applicable_stage:
        return
    checkpoint_type=str(policy.get('artifact_type') or '')
    producer=str(policy.get('producer_operation_uid') or '')
    if checkpoint_type!='BASIC_DESIGN_DOMAIN_STEPWISE_CHECKPOINT' or producer!='BASIC_DESIGN_PACKAGE_COMPILE':
        fail('BASIC_DESIGN_CHECKPOINT_POLICY_INVALID')
    outputs=set(map(str,stage.get('outputs') or []))
    producers={str(k):str(v) for k,v in (stage.get('output_producers') or {}).items()}
    if checkpoint_type not in outputs or producers.get(checkpoint_type)!=producer:
        fail('BASIC_DESIGN_CHECKPOINT_STAGE_OUTPUT_BINDING_MISSING')
    if phase!='CLOSURE' and not (phase=='STEP' and producer in completed):
        return
    checkpoint_rows=[r for r in rows if isinstance(r,dict) and r.get('required_artifact_type')==checkpoint_type and r.get('applicability')=='REQUIRED']
    package_rows=[r for r in rows if isinstance(r,dict) and r.get('required_artifact_type')=='BASIC_DESIGN_PACKAGE' and r.get('applicability')=='REQUIRED']
    if not checkpoint_rows:
        fail('BASIC_DESIGN_CHECKPOINT_MATRIX_ROWS_MISSING')
    package_refs={str(r.get('artifact_ref') or '') for r in package_rows if str(r.get('artifact_ref') or '')}
    if len(package_refs)!=1:
        fail('BASIC_DESIGN_CHECKPOINT_PACKAGE_REF_AMBIGUOUS')
    package_ref=next(iter(package_refs))
    pp=Path(package_ref)
    if pp.is_absolute() or '..' in pp.parts:
        fail('BASIC_DESIGN_CHECKPOINT_PACKAGE_REF_INVALID')
    package_path=(execution_root/pp).resolve()
    try:
        package_path.relative_to(execution_root.resolve())
    except ValueError:
        fail('BASIC_DESIGN_CHECKPOINT_PACKAGE_REF_ESCAPES_ROOT')
    _require_nonempty_file(package_path,'BASIC_DESIGN_PACKAGE')
    package=_external_yaml(package_path,'BASIC_DESIGN_PACKAGE')
    if package.get('artifact_type')!='BASIC_DESIGN_PACKAGE':
        fail('BASIC_DESIGN_CHECKPOINT_PACKAGE_TYPE_INVALID')
    if package.get('stage_uid')!=stage_uid or package.get('work_unit_uid')!=work.get('work_unit_uid') or package.get('governed_unit_uid')!=work.get('governed_unit_uid'):
        fail('BASIC_DESIGN_CHECKPOINT_PACKAGE_IDENTITY_DRIFT')
    domains=package.get('design_domains')
    if not isinstance(domains,list) or not domains:
        fail('BASIC_DESIGN_CHECKPOINT_PACKAGE_DOMAIN_DENOMINATOR_MISSING')
    required_domains=[]
    for idx,item in enumerate(domains):
        if not isinstance(item,dict):
            fail('BASIC_DESIGN_CHECKPOINT_PACKAGE_DOMAIN_ROW_INVALID:'+str(idx))
        domain_uid=str(item.get('domain_uid') or '').strip()
        if not domain_uid:
            fail('BASIC_DESIGN_CHECKPOINT_PACKAGE_DOMAIN_UID_MISSING:'+str(idx))
        applicability=str(item.get('applicability') or '')
        if applicability=='REQUIRED':
            if item.get('resolution')!='PASS':
                fail('BASIC_DESIGN_CHECKPOINT_PACKAGE_REQUIRED_DOMAIN_NOT_PASS:'+domain_uid)
            required_domains.append(domain_uid)
        elif applicability in {'NOT_APPLICABLE_WITH_AUTHORITY','AUTHORIZED_NOT_APPLICABLE'}:
            if not str(item.get('authority_evidence_ref') or '').strip():
                fail('BASIC_DESIGN_CHECKPOINT_PACKAGE_NA_AUTHORITY_MISSING:'+domain_uid)
        else:
            fail('BASIC_DESIGN_CHECKPOINT_PACKAGE_DOMAIN_APPLICABILITY_INVALID:'+domain_uid)
    if len(required_domains)!=len(set(required_domains)):
        fail('BASIC_DESIGN_CHECKPOINT_PACKAGE_DOMAIN_UID_DUPLICATE')
    if package.get('basic_design_required_domain_total')!=len(required_domains) or package.get('basic_design_bound_domain_total')!=len(required_domains) or package.get('basic_design_missing_domain_total')!=0:
        fail('BASIC_DESIGN_CHECKPOINT_PACKAGE_DOMAIN_COUNT_DRIFT')
    matrix_domains=[]
    artifact_refs=[]
    expected_denominator_ref=package_ref+str(policy.get('denominator_resolution_suffix') or '#design_domains')
    required_fields=set(map(str,policy.get('required_fields') or []))
    package_source_head=str(package.get('source_head_sha') or '')
    for row in checkpoint_rows:
        domain_uid=str(row.get('row_identity') or '').strip()
        if not domain_uid:
            fail('BASIC_DESIGN_CHECKPOINT_MATRIX_DOMAIN_UID_MISSING')
        if str(row.get('row_denominator_source') or '')!=expected_denominator_ref:
            fail('BASIC_DESIGN_CHECKPOINT_MATRIX_DENOMINATOR_REF_DRIFT:'+domain_uid)
        ref=str(row.get('artifact_ref') or '')
        rp=Path(ref)
        if not ref or rp.is_absolute() or '..' in rp.parts:
            fail('BASIC_DESIGN_CHECKPOINT_ARTIFACT_REF_INVALID:'+domain_uid)
        full=(execution_root/rp).resolve()
        try:
            full.relative_to(execution_root.resolve())
        except ValueError:
            fail('BASIC_DESIGN_CHECKPOINT_ARTIFACT_REF_ESCAPES_ROOT:'+domain_uid)
        _require_nonempty_file(full,'BASIC_DESIGN_DOMAIN_STEPWISE_CHECKPOINT')
        obj=_external_yaml(full,'BASIC_DESIGN_DOMAIN_STEPWISE_CHECKPOINT')
        missing=sorted(required_fields-set(obj))
        if missing:
            fail('BASIC_DESIGN_CHECKPOINT_REQUIRED_FIELDS_MISSING:'+domain_uid+':'+repr(missing))
        if obj.get('artifact_type')!=checkpoint_type or obj.get('stage_uid')!=stage_uid or obj.get('work_unit_uid')!=work.get('work_unit_uid') or obj.get('governed_unit_uid')!=work.get('governed_unit_uid') or obj.get('domain_uid')!=domain_uid:
            fail('BASIC_DESIGN_CHECKPOINT_IDENTITY_DRIFT:'+domain_uid)
        if obj.get('denominator_resolution_ref')!=expected_denominator_ref:
            fail('BASIC_DESIGN_CHECKPOINT_DENOMINATOR_REF_DRIFT:'+domain_uid)
        if not str(obj.get('current_authority_ref') or '').strip() or not isinstance(obj.get('materialized_binding_refs'),list) or not obj.get('materialized_binding_refs'):
            fail('BASIC_DESIGN_CHECKPOINT_BINDING_OR_AUTHORITY_MISSING:'+domain_uid)
        if obj.get('completeness_validation_result')!='PASS' or obj.get('conflict_validation_result')!='PASS' or obj.get('checkpoint_state')!='PASS':
            fail('BASIC_DESIGN_CHECKPOINT_NOT_PASS:'+domain_uid)
        if not str(obj.get('review_evidence_ref') or '').strip():
            fail('BASIC_DESIGN_CHECKPOINT_REVIEW_EVIDENCE_MISSING:'+domain_uid)
        next_uid=str(obj.get('next_admitted_domain_uid') or '').strip()
        if not next_uid or (next_uid!=str(policy.get('terminal_next_admitted_domain_token') or 'FINAL_FREEZE') and next_uid not in set(required_domains)):
            fail('BASIC_DESIGN_CHECKPOINT_NEXT_DOMAIN_INVALID:'+domain_uid)
        if obj.get('producer_operation_uid')!=producer or obj.get('governance_uid')!=gov:
            fail('BASIC_DESIGN_CHECKPOINT_PRODUCER_OR_GOVERNANCE_DRIFT:'+domain_uid)
        source_head=str(obj.get('source_head_sha') or '')
        if len(source_head)!=40 or any(ch not in '0123456789abcdef' for ch in source_head.lower()) or (package_source_head and source_head!=package_source_head):
            fail('BASIC_DESIGN_CHECKPOINT_SOURCE_HEAD_DRIFT:'+domain_uid)
        matrix_domains.append(domain_uid)
        artifact_refs.append(ref)
    if len(matrix_domains)!=len(set(matrix_domains)):
        fail('BASIC_DESIGN_CHECKPOINT_MATRIX_DOMAIN_DUPLICATE')
    if len(artifact_refs)!=len(set(artifact_refs)):
        fail('BASIC_DESIGN_CHECKPOINT_ARTIFACT_REF_REUSED')
    if set(matrix_domains)!=set(required_domains):
        fail('BASIC_DESIGN_CHECKPOINT_DOMAIN_SET_MISMATCH')

def validate_normative_execution_matrix(stage_uid,execution_root,work,stage,gov,validation_phase='STATIC',completed_operations=None):
    inv=y(INVARIANTS)
    policy=((inv.get('invariants') or {}).get('NORMATIVE_EXECUTION_MATRIX') or {})
    if policy.get('required_before_first_effectful_operation') is not True or policy.get('required_for_stage_or_capability_closure') is not True:
        fail('NORMATIVE_EXECUTION_MATRIX_POLICY_MISSING')
    for key in (
      'pre_effectful_matrix_pass_is_registration_completeness_only',
      'future_producer_owned_target_may_be_unmaterialized_before_producer_execution',
      'completed_producer_rows_must_be_physically_materialized_before_dependent_execution',
      'closure_requires_all_required_rows_physically_materialized',
      'required_evidence_may_remain_unmaterialized_only_until_registered_evidence_boundary'
    ):
        if policy.get(key) is not True:
            fail('NORMATIVE_EXECUTION_MATRIX_MATERIALIZATION_POLICY_MISSING:'+key)
    if policy.get('future_producer_owned_target_completion_credit')!=0 or policy.get('physical_future_operation_preproduction')!='BLOCK' or policy.get('closure_future_target_or_to_materialize_state')!='BLOCK':
        fail('NORMATIVE_EXECUTION_MATRIX_MATERIALIZATION_DISPOSITION_DRIFT')
    phase=str(validation_phase or 'STATIC').upper()
    if phase not in {'STATIC','ENTRY','STEP','CLOSURE'}:
        fail('NORMATIVE_EXECUTION_MATRIX_VALIDATION_PHASE_INVALID:'+phase)
    completed=set(map(str,completed_operations or []))

    rel=str(work.get('normative_execution_matrix_ref') or '')
    if not rel: fail('NORMATIVE_EXECUTION_MATRIX_REF_MISSING')
    rp=Path(rel)
    if rp.is_absolute() or '..' in rp.parts: fail('NORMATIVE_EXECUTION_MATRIX_REF_INVALID')
    path=execution_root/rp
    _require_nonempty_file(path,'NORMATIVE_EXECUTION_MATRIX')
    matrix=_external_yaml(path,'NORMATIVE_EXECUTION_MATRIX')
    if matrix.get('artifact_type')!='NORMATIVE_EXECUTION_MATRIX': fail('NORMATIVE_EXECUTION_MATRIX_TYPE_INVALID')
    if matrix.get('stage_uid')!=stage_uid or matrix.get('work_unit_uid')!=work.get('work_unit_uid') or matrix.get('governance_uid')!=gov:
        fail('NORMATIVE_EXECUTION_MATRIX_IDENTITY_DRIFT')
    if matrix.get('status')!='PASS': fail('NORMATIVE_EXECUTION_MATRIX_NOT_PASS')
    rows=matrix.get('rows')
    if not isinstance(rows,list) or not rows: fail('NORMATIVE_EXECUTION_MATRIX_ROWS_EMPTY')
    required_row_fields=set(map(str,policy.get('matrix_row_required_fields') or []))
    output_producers={str(k):str(v) for k,v in (stage.get('output_producers') or {}).items()}
    required_evidence=set(map(str,stage.get('required_evidence') or []))
    seen=set(); section_uids=set(); artifact_types=set(); required_count=0; validator_bound=0; closure_bound=0

    def validate_physical(full,row_uid,field_path):
        _require_nonempty_file(full,'NORMATIVE_EXECUTION_MATRIX_ARTIFACT:'+row_uid)
        try:
            if full.suffix.lower()=='.json':
                obj=json.loads(full.read_text(encoding='utf-8'))
            else:
                obj=yaml.safe_load(full.read_text(encoding='utf-8'))
        except Exception as exc:
            fail('NORMATIVE_EXECUTION_MATRIX_ARTIFACT_PARSE_FAILED:'+row_uid+':'+type(exc).__name__)
        if not isinstance(obj,dict): fail('NORMATIVE_EXECUTION_MATRIX_ARTIFACT_MAPPING_REQUIRED:'+row_uid)
        val=_matrix_get(obj,field_path)
        if not _matrix_nonblank(val): fail('NORMATIVE_EXECUTION_MATRIX_REQUIRED_FIELD_BLANK:'+row_uid)

    for idx,row in enumerate(rows):
        if not isinstance(row,dict): fail(f'NORMATIVE_EXECUTION_MATRIX_ROW_INVALID:{idx}')
        missing=sorted(required_row_fields-set(row))
        if missing: fail(f'NORMATIVE_EXECUTION_MATRIX_ROW_FIELDS_MISSING:{idx}:{missing}')
        uid=str(row.get('matrix_row_uid') or '')
        if not uid or uid in seen: fail('NORMATIVE_EXECUTION_MATRIX_ROW_UID_INVALID:'+uid)
        seen.add(uid)
        section_uids.add(str(row.get('normative_section_uid') or ''))
        artifact_type=str(row.get('required_artifact_type') or '')
        artifact_types.add(artifact_type)
        applicability=row.get('applicability')
        if applicability=='NOT_APPLICABLE_WITH_AUTHORITY':
            if not row.get('authority_evidence_ref'): fail('NORMATIVE_EXECUTION_MATRIX_NA_AUTHORITY_MISSING:'+uid)
            continue
        if applicability!='REQUIRED': fail('NORMATIVE_EXECUTION_MATRIX_APPLICABILITY_INVALID:'+uid)
        required_count+=1
        if row.get('validator_uid') and row.get('validator_check_id'): validator_bound+=1
        if row.get('closure_gate')==stage.get('exit_gate'): closure_bound+=1

        aref=str(row.get('artifact_ref') or '')
        ap=Path(aref)
        if not aref or ap.is_absolute() or '..' in ap.parts: fail('NORMATIVE_EXECUTION_MATRIX_ARTIFACT_REF_INVALID:'+uid)
        full=(execution_root/ap).resolve()
        try:
            full.relative_to(execution_root.resolve())
        except ValueError:
            fail('NORMATIVE_EXECUTION_MATRIX_ARTIFACT_REF_ESCAPES_ROOT:'+uid)
        fpath=row.get('field_path')
        if not isinstance(fpath,list) or not fpath: fail('NORMATIVE_EXECUTION_MATRIX_FIELD_PATH_INVALID:'+uid)

        producer=output_producers.get(artifact_type)
        is_required_evidence=artifact_type in required_evidence
        exists=full.is_file()
        physical_required=(phase in {'STATIC','CLOSURE'})
        if phase in {'ENTRY','STEP'}:
            if producer:
                if producer in completed:
                    physical_required=True
                else:
                    physical_required=False
                    if exists:
                        fail('NORMATIVE_EXECUTION_MATRIX_FUTURE_OUTPUT_PREPRODUCED:'+uid+':'+producer)
            elif is_required_evidence:
                physical_required=False
            else:
                physical_required=True

        if physical_required:
            validate_physical(full,uid,fpath)
        elif exists:
            validate_physical(full,uid,fpath)

    required_sections=set(map(str,stage.get('required_normative_section_uids') or []))
    missing_sections=sorted(required_sections-section_uids)
    if missing_sections: fail('NORMATIVE_EXECUTION_MATRIX_SECTION_COVERAGE_MISSING:'+repr(missing_sections))
    required_artifacts=set(map(str,stage.get('outputs') or []))|required_evidence
    missing_artifacts=sorted(required_artifacts-artifact_types)
    if missing_artifacts: fail('NORMATIVE_EXECUTION_MATRIX_ARTIFACT_COVERAGE_MISSING:'+repr(missing_artifacts))
    _validate_basic_design_domain_stepwise_checkpoints(stage_uid,execution_root,work,stage,gov,rows,phase,completed)
    cov=matrix.get('coverage')
    if not isinstance(cov,dict): fail('NORMATIVE_EXECUTION_MATRIX_COVERAGE_MISSING')
    expected={
      'required_normative_section_total':len(required_sections),
      'represented_normative_section_total':len(required_sections & section_uids),
      'required_artifact_total':len(required_artifacts),
      'represented_artifact_total':len(required_artifacts & artifact_types),
      'required_field_total':required_count,
      'validator_bound_field_total':validator_bound,
      'closure_bound_field_total':closure_bound,
      'missing_required_row_count':0,
      'missing_required_field_count':0,
      'duplicate_credit_count':0,
      'summary_only_credit_count':0,
      'unclassified_applicability_count':0,
      'validator_unbound_count':0,
      'closure_unbound_count':0,
      'stale_matrix_count':0}
    for k,v in expected.items():
        if cov.get(k)!=v: fail(f'NORMATIVE_EXECUTION_MATRIX_COVERAGE_DRIFT:{k}:expected={v}:actual={cov.get(k)}')
    if required_count!=validator_bound or required_count!=closure_bound:
        fail('NORMATIVE_EXECUTION_MATRIX_BINDING_COVERAGE_INCOMPLETE')
    return True


def _validate_stage_entry_input_bindings(stage_uid,execution_root,work,stage):
    expected_inputs=list(map(str,stage.get('inputs') or []))
    expected_origins={str(k):str(v) for k,v in (stage.get('input_origins') or {}).items()}
    bindings=work.get('input_bindings')
    if not isinstance(bindings,dict):
        fail('STAGE_ENTRY_INPUT_BINDINGS_MISSING:'+stage_uid)
    if set(map(str,bindings))!=set(expected_inputs):
        fail('STAGE_ENTRY_INPUT_BINDING_DENOMINATOR_DRIFT:'+stage_uid+
             ':expected='+repr(sorted(expected_inputs))+':actual='+repr(sorted(map(str,bindings))))
    required_fields={
      'input_uid','origin','status','artifact_ref','content_sha256',
      'external_evidence_ref','authority_evidence_ref','consumer_readiness_evidence_ref'
    }
    for input_uid in expected_inputs:
        row=bindings.get(input_uid)
        if not isinstance(row,dict):
            fail('STAGE_ENTRY_INPUT_BINDING_ROW_INVALID:'+input_uid)
        missing=sorted(required_fields-set(row))
        if missing:
            fail('STAGE_ENTRY_INPUT_BINDING_FIELDS_MISSING:'+input_uid+':'+repr(missing))
        if str(row.get('input_uid') or '')!=input_uid:
            fail('STAGE_ENTRY_INPUT_BINDING_IDENTITY_DRIFT:'+input_uid)
        if str(row.get('origin') or '')!=expected_origins.get(input_uid,''):
            fail('STAGE_ENTRY_INPUT_ORIGIN_DRIFT:'+input_uid)
        status=str(row.get('status') or '')
        if status=='MATERIALIZED':
            ref=str(row.get('artifact_ref') or '').strip()
            rp=Path(ref)
            if not ref or rp.is_absolute() or '..' in rp.parts:
                fail('STAGE_ENTRY_INPUT_ARTIFACT_REF_INVALID:'+input_uid)
            full=(execution_root/rp).resolve()
            try:
                full.relative_to(execution_root.resolve())
            except ValueError:
                fail('STAGE_ENTRY_INPUT_ARTIFACT_REF_ESCAPES_ROOT:'+input_uid)
            _validate_local_file_artifact(full,'STAGE_ENTRY_INPUT_ARTIFACT:'+input_uid)
            actual_hash=_sha256_file(full)
            if str(row.get('content_sha256') or '')!=actual_hash:
                fail('STAGE_ENTRY_INPUT_CONTENT_HASH_DRIFT:'+input_uid)
            readiness_ref=str(row.get('consumer_readiness_evidence_ref') or '').strip()
            rr=Path(readiness_ref)
            if not readiness_ref or rr.is_absolute() or '..' in rr.parts:
                fail('STAGE_ENTRY_INPUT_READINESS_REF_INVALID:'+input_uid)
            readiness=(execution_root/rr).resolve()
            try:
                readiness.relative_to(execution_root.resolve())
            except ValueError:
                fail('STAGE_ENTRY_INPUT_READINESS_REF_ESCAPES_ROOT:'+input_uid)
            _validate_local_file_artifact(readiness,'STAGE_ENTRY_INPUT_READINESS:'+input_uid)
        elif status=='EXTERNAL_RECEIPT':
            if not str(row.get('external_evidence_ref') or '').strip():
                fail('STAGE_ENTRY_INPUT_EXTERNAL_EVIDENCE_MISSING:'+input_uid)
        elif status=='AUTHORIZED_NOT_APPLICABLE':
            if not str(row.get('authority_evidence_ref') or '').strip():
                fail('STAGE_ENTRY_INPUT_NA_AUTHORITY_MISSING:'+input_uid)
        else:
            fail('STAGE_ENTRY_INPUT_STATUS_INVALID:'+input_uid+':'+status)
    return True

def _validate_current_ledger_bindings(stage_uid,execution_root,work,gov):
    contract=_deterministic_stage_audit_contract().get('current_ledger_synchronization') or {}
    expected=list(map(str,contract.get('non_authoritative_projections') or []))
    if not expected:
        fail('CURRENT_PROJECTION_DIAGNOSTIC_DENOMINATOR_EMPTY')
    bindings=work.get('current_ledger_bindings')
    if not isinstance(bindings,dict):
        fail('CURRENT_PROJECTION_BINDINGS_MISSING:'+stage_uid)
    actual_non_state={str(k) for k in bindings if str(k)!='EXECUTION_STATE'}
    if actual_non_state!=set(expected):
        fail('CURRENT_LEDGER_BINDING_DENOMINATOR_DRIFT:'+stage_uid+
             ':expected='+repr(sorted(expected))+':actual='+repr(sorted(actual_non_state)))
    required={'ledger_class','binding_kind','artifact_ref','content_sha256','external_evidence_ref'}
    for ledger_class in expected:
        row=bindings.get(ledger_class)
        if not isinstance(row,dict):
            fail('CURRENT_LEDGER_BINDING_ROW_INVALID:'+ledger_class)
        missing=sorted(required-set(row))
        if missing:
            fail('CURRENT_LEDGER_BINDING_FIELDS_MISSING:'+ledger_class+':'+repr(missing))
        if str(row.get('ledger_class') or '')!=ledger_class:
            fail('CURRENT_LEDGER_BINDING_IDENTITY_DRIFT:'+ledger_class)
        kind=str(row.get('binding_kind') or '')
        if kind=='LOCAL_ARTIFACT':
            ref=str(row.get('artifact_ref') or '').strip()
            rp=Path(ref)
            if not ref or rp.is_absolute() or '..' in rp.parts:
                fail('CURRENT_LEDGER_ARTIFACT_REF_INVALID:'+ledger_class)
            full=(execution_root/rp).resolve()
            try:
                full.relative_to(execution_root.resolve())
            except ValueError:
                fail('CURRENT_LEDGER_ARTIFACT_REF_ESCAPES_ROOT:'+ledger_class)
            _validate_local_file_artifact(full,'CURRENT_LEDGER_ARTIFACT:'+ledger_class)
            actual_hash=_sha256_file(full)
            if str(row.get('content_sha256') or '')!=actual_hash:
                fail('CURRENT_LEDGER_CONTENT_HASH_DRIFT:'+ledger_class)
        elif kind=='EXTERNAL_RECEIPT':
            if not str(row.get('external_evidence_ref') or '').strip():
                fail('CURRENT_LEDGER_EXTERNAL_EVIDENCE_MISSING:'+ledger_class)
        else:
            fail('CURRENT_LEDGER_BINDING_KIND_INVALID:'+ledger_class+':'+kind)
    declared_gov=str(work.get('governance_uid') or work.get('current_governance_uid') or '')
    if declared_gov and declared_gov!=gov:
        fail('CURRENT_LEDGER_WORK_UNIT_GOVERNANCE_DRIFT:'+stage_uid)
    return True


def _validate_closed_work_unit_successor_reentry(stage_uid,execution_root,work,scope,work_rel):
    inv=y(INVARIANTS)
    policy=((inv.get('invariants') or {}).get('CLOSED_WORK_UNIT_SUCCESSOR_REENTRY') or {})
    kind_field=str(policy.get('work_unit_activation_kind_field') or 'work_unit_activation_kind')
    allowed=set(map(str,policy.get('allowed_work_unit_activation_kinds') or []))
    if allowed!={'INITIAL_STAGE_WORK_UNIT','SUCCESSOR_REENTRY_WORK_UNIT'}:
        fail('WORK_UNIT_REENTRY_POLICY_ACTIVATION_KIND_INVALID')
    current_uid=str(work.get('work_unit_uid') or '').strip()
    current_gu=str(work.get('governed_unit_uid') or '').strip()
    kind=str(work.get(kind_field) or '').strip()
    if not kind or kind not in allowed:
        fail('WORK_UNIT_ACTIVATION_KIND_INVALID:'+stage_uid+':'+kind)
    current_dir=(execution_root/Path(work_rel)).resolve().parent
    same_terminal=current_dir/'WORK_UNIT_TERMINAL_RECEIPT.yaml'
    if same_terminal.exists():
        fail('CLOSED_WORK_UNIT_REACTIVATION_FORBIDDEN:'+current_uid)
    reentry_fields=list(map(str,policy.get('required_successor_reentry_fields') or []))
    if set(reentry_fields)!={'predecessor_work_unit_uid','predecessor_work_unit_ref','predecessor_terminal_receipt_ref','reentry_authority_ref'}:
        fail('WORK_UNIT_REENTRY_POLICY_FIELDS_INVALID')
    present={key:str(work.get(key) or '').strip() for key in reentry_fields}
    if kind=='INITIAL_STAGE_WORK_UNIT':
        if any(present.values()):
            fail('INITIAL_WORK_UNIT_REENTRY_FIELDS_FORBIDDEN:'+current_uid)
        return True
    missing=sorted(k for k,v in present.items() if not v)
    if missing:
        fail('SUCCESSOR_REENTRY_FIELDS_MISSING:'+current_uid+':'+repr(missing))
    predecessor_uid=present['predecessor_work_unit_uid']
    if predecessor_uid==current_uid:
        fail('SUCCESSOR_REENTRY_WORK_UNIT_UID_REUSED:'+current_uid)
    pred_work_ref=Path(present['predecessor_work_unit_ref'])
    pred_receipt_ref=Path(present['predecessor_terminal_receipt_ref'])
    for rp,label in ((pred_work_ref,'PREDECESSOR_WORK_UNIT'),(pred_receipt_ref,'PREDECESSOR_TERMINAL_RECEIPT')):
        if rp.is_absolute() or '..' in rp.parts:
            fail('SUCCESSOR_REENTRY_'+label+'_REF_INVALID:'+str(rp))
        full=(execution_root/rp).resolve()
        try:
            full.relative_to(execution_root.resolve())
        except ValueError:
            fail('SUCCESSOR_REENTRY_'+label+'_REF_ESCAPES_ROOT:'+str(rp))
        _require_nonempty_file(full,'SUCCESSOR_REENTRY_'+label)
    pred_work=_external_yaml((execution_root/pred_work_ref).resolve(),'SUCCESSOR_REENTRY_PREDECESSOR_WORK_UNIT')
    pred_receipt=_external_yaml((execution_root/pred_receipt_ref).resolve(),'SUCCESSOR_REENTRY_PREDECESSOR_TERMINAL_RECEIPT')
    if str(pred_work.get('work_unit_uid') or '')!=predecessor_uid:
        fail('SUCCESSOR_REENTRY_PREDECESSOR_WORK_UNIT_UID_DRIFT')
    if str(pred_work.get('stage_uid') or '')!=stage_uid:
        fail('SUCCESSOR_REENTRY_PREDECESSOR_STAGE_DRIFT')
    if str(pred_work.get('governed_unit_uid') or '')!=current_gu:
        fail('SUCCESSOR_REENTRY_PREDECESSOR_GOVERNED_UNIT_DRIFT')
    if str(pred_work.get('status') or pred_work.get('current_status') or '')!='CLOSED':
        fail('SUCCESSOR_REENTRY_PREDECESSOR_NOT_CLOSED')
    if str(pred_receipt.get('work_unit_uid') or '')!=predecessor_uid or str(pred_receipt.get('stage_uid') or '')!=stage_uid:
        fail('SUCCESSOR_REENTRY_TERMINAL_RECEIPT_IDENTITY_DRIFT')
    if str(pred_receipt.get('conclusion') or '')!='success':
        fail('SUCCESSOR_REENTRY_TERMINAL_RECEIPT_NOT_SUCCESS')
    if not present['reentry_authority_ref']:
        fail('SUCCESSOR_REENTRY_AUTHORITY_REF_MISSING')
    return True

def _validate_stage_entry_control_state(stage_uid,execution_root,work,scope,work_rel,stage,gov):
    compat=execution_compatibility_adapter()
    scope_allowed_field=str(compat['scope_execution_allowed_field'])
    resume_control_field=str(compat['resume_control_field'])
    resume_allowed_field=str(compat['resume_execution_allowed_field'])

    if str(work.get('governance_uid') or '')!=gov:
        fail('STAGE_ENTRY_WORK_UNIT_GOVERNANCE_DRIFT:'+stage_uid)
    if str(scope.get('governance_uid') or '')!=gov:
        fail('STAGE_ENTRY_SCOPE_GOVERNANCE_DRIFT:'+stage_uid)

    governed_work=str(work.get('governed_unit_uid') or '').strip()
    governed_scope=str(scope.get('governed_unit_uid') or '').strip()
    if not governed_work or not governed_scope or governed_work!=governed_scope:
        fail('STAGE_ENTRY_GOVERNED_UNIT_IDENTITY_DRIFT:'+stage_uid)

    _validate_closed_work_unit_successor_reentry(stage_uid,execution_root,work,scope,work_rel)

    if work.get('pre_execution_gate_status')!='PASS':
        fail('STAGE_ENTRY_PRE_EXECUTION_GATE_NOT_PASS:'+stage_uid)
    if scope.get(scope_allowed_field) is not True:
        fail('STAGE_ENTRY_SCOPE_EXECUTION_NOT_ALLOWED:'+stage_uid)

    work_path=(execution_root/Path(work_rel)).resolve()
    state_path=work_path.parent/'EXECUTION_STATE.yaml'
    ledger_bindings=work.get('current_ledger_bindings') or {}
    state_binding=ledger_bindings.get('EXECUTION_STATE') if isinstance(ledger_bindings,dict) else None
    if isinstance(state_binding,dict) and str(state_binding.get('artifact_ref') or '').strip():
        state_ref=str(state_binding.get('artifact_ref') or '')
        state_bound=(execution_root/Path(state_ref)).resolve()
        if state_bound!=state_path:
            fail('STAGE_ENTRY_EXECUTION_STATE_LEDGER_ALIAS_DRIFT:'+stage_uid)
    _validate_local_file_artifact(state_path,'STAGE_ENTRY_EXECUTION_STATE')
    state=_external_yaml(state_path,'STAGE_ENTRY_EXECUTION_STATE')
    if str(state.get('stage_uid') or '')!=stage_uid:
        fail('STAGE_ENTRY_STATE_STAGE_DRIFT:'+stage_uid)
    if str(state.get('work_unit_uid') or '')!=str(work.get('work_unit_uid') or ''):
        fail('STAGE_ENTRY_STATE_WORK_UNIT_DRIFT:'+stage_uid)
    if str(state.get('governance_uid') or '')!=gov:
        fail('STAGE_ENTRY_STATE_GOVERNANCE_DRIFT:'+stage_uid)
    if str(state.get('governed_unit_uid') or '')!=governed_work:
        fail('STAGE_ENTRY_STATE_GOVERNED_UNIT_DRIFT:'+stage_uid)

    resume=state.get(resume_control_field)
    if not isinstance(resume,dict) or resume.get(resume_allowed_field) is not True:
        fail('STAGE_ENTRY_RESUME_NOT_ALLOWED:'+stage_uid)

    status=str(state.get('status') or state.get('current_status') or '')
    if status not in {'READY_FOR_EXECUTION','IN_PROGRESS'}:
        fail('STAGE_ENTRY_STATE_NOT_EXECUTABLE:'+stage_uid+':'+status)

    current_operation=str(state.get('current_operation') or '')
    if current_operation not in set(map(str,stage.get('operations') or [])):
        fail('STAGE_ENTRY_CURRENT_OPERATION_INVALID:'+stage_uid+':'+current_operation)
    return state


def active_execution(stage_uid):
    entry,reg,gov,profile,adapters,stages=validate_definition()
    execution_root,work,scope,work_rel,scope_rel=execution_context()
    work_dir=(execution_root/Path(work_rel)).resolve().parent
    validate_work_unit_bindings(stage_uid,work,stages,adapters)
    if scope.get('stage_uid')!=stage_uid or scope.get('work_unit_uid')!=work.get('work_unit_uid'):
        fail('CURRENT_SCOPE_WORK_UNIT_BINDING_DRIFT')
    entry_state=_validate_stage_entry_control_state(stage_uid,execution_root,work,scope,work_rel,stages[stage_uid],gov)
    _validate_stage_entry_input_bindings(stage_uid,execution_root,work,stages[stage_uid])
    # Projection synchronization is diagnostic only; EXECUTION_STATE is authoritative.
    deps=work.get('dependencies') or []
    if not isinstance(deps,list) or not deps: fail('ACTIVE_WORK_UNIT_DEPENDENCY_CLOSURE_MISSING')
    for dep in deps:
        ref=dep if isinstance(dep,str) else ((dep.get('ref') or dep.get('path') or dep.get('source_ref')) if isinstance(dep,dict) else None)
        if isinstance(ref,str) and '/' in ref:
            rp=Path(ref)
            if rp.is_absolute() or '..' in rp.parts:
                fail('ACTIVE_WORK_UNIT_DEPENDENCY_REF_INVALID:'+ref)
            full=(execution_root/rp).resolve()
            try:
                full.relative_to(execution_root.resolve())
            except ValueError:
                fail('ACTIVE_WORK_UNIT_DEPENDENCY_REF_ESCAPES_ROOT:'+ref)
            if not full.exists():
                fail('ACTIVE_WORK_UNIT_DEPENDENCY_MISSING:'+ref)
            if full.is_file():
                _validate_local_file_artifact(full,'ACTIVE_WORK_UNIT_DEPENDENCY:'+ref)
    validate_normative_execution_matrix(
        stage_uid,execution_root,work,stages[stage_uid],gov,
        validation_phase='ENTRY',completed_operations=entry_state.get('completed_operations') or []
    )
    return work

def admission(stage_uid):
    work=active_execution(stage_uid); pl=plan(stage_uid)
    print(f"PASS: common Stage-core admission context resolved for {stage_uid} work_unit={work.get('work_unit_uid')}")
    print(f"PASS: common execution skeleton phases={len(pl['phases'])}/{len(EXPECTED_PHASES)}")
    print('PASS: admission check performs no effectful execution and grants zero completion credit')

def _result_map(rows,key,label):
    if not isinstance(rows,list): fail(f'{label}_INVALID')
    out={}
    for row in rows:
        if not isinstance(row,dict) or not row.get(key): fail(f'{label}_ROW_INVALID')
        uid=str(row[key])
        if uid in out: fail(f'{label}_DUPLICATE:{uid}')
        if row.get('status') not in RESULT_TERMINAL_STATUSES: fail(f'{label}_STATUS_INVALID:{uid}')
        if row.get('status')=='NOT_APPLICABLE_WITH_PROOF' and not row.get('proof'):
            fail(f'{label}_NA_PROOF_MISSING:{uid}')
        out[uid]=row
    return out

def _validate_current_stage_state_bundle(stage_uid,e,stage,gov,validation_phase='PRE_CLOSE_CANDIDATE'):
    scope_ref=str(e.get('scope_manifest_ref') or '')
    rp=Path(scope_ref)
    if not scope_ref or rp.is_absolute() or '..' in rp.parts:
        fail('EVIDENCE_SCOPE_MANIFEST_REF_INVALID')
    execution_root=_execution_artifact_root()
    scope_path=execution_root/rp
    scope=_external_yaml(scope_path,'CURRENT_EXECUTION_SCOPE')
    if scope.get('stage_uid')!=stage_uid:
        fail('CURRENT_SCOPE_STAGE_IDENTITY_DRIFT')
    work_dir=scope_path.parent
    work=_external_yaml(work_dir/'WORK_UNIT.yaml','CURRENT_WORK_UNIT')
    state_path=work_dir/'EXECUTION_STATE.yaml'
    state=_external_yaml(state_path,'CURRENT_EXECUTION_STATE')
    state_binding=((work.get('current_ledger_bindings') or {}).get('EXECUTION_STATE') or {})
    state_ref=str(state_binding.get('artifact_ref') or '')
    if state_ref and (execution_root/Path(state_ref)).resolve()!=state_path.resolve():
        fail('CURRENT_STATE_LEDGER_ALIAS_DRIFT:'+stage_uid)
    if work.get('stage_uid')!=stage_uid or state.get('stage_uid')!=stage_uid:
        fail('CURRENT_WORK_OR_STATE_STAGE_IDENTITY_DRIFT')
    if scope.get('work_unit_uid')!=work.get('work_unit_uid') or state.get('work_unit_uid')!=work.get('work_unit_uid'):
        fail('CURRENT_SCOPE_WORK_STATE_IDENTITY_DRIFT')
    validate_normative_execution_matrix(
        stage_uid,execution_root,work,stage,gov,
        validation_phase='CLOSURE',completed_operations=state.get('completed_operations') or []
    )
    # Projection synchronization cannot deny content-evidence closure.
    if e.get('result')=='PASS':
        expected=list(map(str,stage.get('operations') or []))
        completed=state.get('completed_operations')
        if not isinstance(completed,list):
            fail('CURRENT_STATE_COMPLETED_OPERATIONS_INVALID')
        completed=list(map(str,completed))
        if len(completed)!=len(expected) or set(completed)!=set(expected):
            fail('CURRENT_STATE_OPERATION_SET_CONFLICT:expected='+repr(expected)+':actual='+repr(completed))
        state_status=str(state.get('status') or '')
        if validation_phase=='POST_CLOSE_FINAL':
            if state_status!='CLOSED_PASS':
                fail('CURRENT_STATE_STATUS_CONFLICT:'+state_status)
        elif validation_phase=='PRE_CLOSE_CANDIDATE':
            if e.get('result')=='PASS':
                if state_status!='EXECUTION_COMPLETE_CLOSURE_PENDING':
                    fail('CURRENT_STATE_STATUS_CONFLICT:'+state_status)
            elif e.get('result')=='BLOCKED':
                if state_status not in {'BLOCKED','EXECUTION_COMPLETE_CLOSURE_PENDING'}:
                    fail('CURRENT_STATE_STATUS_CONFLICT:'+state_status)
            else:
                fail('CURRENT_STATE_STATUS_CONFLICT:'+state_status)
        else:
            fail('VALIDATION_PHASE_INVALID:'+str(validation_phase))
        current_op=str(state.get('current_operation') or '')
        if current_op in set(expected) or 'READINESS' in current_op or 'PENDING' in current_op:
            fail('CURRENT_STATE_CURRENT_OPERATION_CONFLICT:'+current_op)
        # WORK_UNIT status is a non-authoritative projection. EXECUTION_STATE is
        # the only mutable Current Stage/Work Unit state authority.
    return scope,work,state,work_dir

def _git_optional(root,*args):
    cp=subprocess.run(['git','-C',str(root),*args],text=True,capture_output=True)
    return cp.stdout.strip() if cp.returncode==0 else ''

def _git_required(root,label,*args):
    cp=subprocess.run(['git','-C',str(root),*args],text=True,capture_output=True)
    if cp.returncode!=0 or not cp.stdout.strip():
        fail(label+':'+(cp.stderr or cp.stdout or 'git lookup failed').strip()[-300:])
    return cp.stdout.strip()

def _canonical_repository_identity(raw):
    s=str(raw or '').strip().replace('\\','/')
    if not s:
        return ''
    if s.startswith('git@') and ':' in s:
        s=s.split(':',1)[1]
    elif '://' in s:
        s=s.split('://',1)[1]
        s=s.split('/',1)[1] if '/' in s else s
    s=s.rstrip('/')
    if s.endswith('.git'):
        s=s[:-4]
    parts=[x for x in s.split('/') if x]
    return '/'.join(parts[-2:]) if len(parts)>=2 else s

def _current_execution_git_context(execution_root):
    head=_git_required(execution_root,'EXECUTION_HEAD_UNRESOLVED','rev-parse','HEAD')
    tree=_git_required(execution_root,'EXECUTION_TREE_UNRESOLVED','rev-parse','HEAD^{tree}')
    branch=_git_optional(execution_root,'symbolic-ref','--short','HEAD') or str(os.environ.get('GITHUB_REF_NAME') or '').strip()
    if not branch:
        fail('EXECUTION_BRANCH_UNRESOLVED')
    env_sha=str(os.environ.get('GITHUB_SHA') or '').strip()
    if execution_root.resolve()==ROOT.resolve() and env_sha and env_sha!=head:
        fail('EXECUTION_HEAD_ENV_MISMATCH')
    remote=_git_required(execution_root,'EXECUTION_REPOSITORY_UNRESOLVED','config','--get','remote.origin.url')
    repository=_canonical_repository_identity(remote)
    if not repository:
        fail('EXECUTION_REPOSITORY_IDENTITY_UNRESOLVED')
    return {'repository':repository,'branch':branch,'head':head,'tree':tree}

def _tracked_path_at_head(execution_root,head,rel):
    rel_norm=str(Path(rel).as_posix()).rstrip('/')
    if rel_norm in {'','.'}: return bool(_git_optional(execution_root,'rev-parse',head+'^{tree}'))
    cp=subprocess.run(['git','-C',str(execution_root),'ls-tree','-r','--name-only',head,'--',rel],text=True,capture_output=True)
    if cp.returncode!=0: fail('TARGET_RESOLUTION_GIT_TREE_LOOKUP_FAILED:'+str(rel))
    rows=[x.strip() for x in cp.stdout.splitlines() if x.strip()]
    return any(x==rel_norm or x.startswith(rel_norm+'/') for x in rows)

def _git_object_at_commit(execution_root,commit_sha,rel):
    rel_norm=str(Path(rel).as_posix()).strip('/')
    return _git_optional(execution_root,'rev-parse',commit_sha+'^{tree}' if rel_norm in {'','.'} else commit_sha+':'+rel_norm)

def _git_is_ancestor(execution_root,ancestor,descendant):
    return subprocess.run(['git','-C',str(execution_root),'merge-base','--is-ancestor',ancestor,descendant],text=True,capture_output=True).returncode==0

def _validate_execution_target_resolution(execution_root,ledger,successor_uid,row,policy,git_context):
    stage_key=successor_uid if successor_uid else 'NEXT_GOVERNED_UNIT'
    kind_policy=(policy.get('successor_execution_binding_resolution_kind_policy') or {}).get(stage_key) or {}
    cls=str(row.get('binding_class') or '')
    allowed=set(map(str,kind_policy.get(cls) or []))
    if not allowed:
        fail('TARGET_RESOLUTION_POLICY_MISSING:'+stage_key+':'+cls)
    ref=str(row.get('target_resolution_ref') or '').strip()
    kind=str(row.get('target_resolution_kind') or '').strip()
    if not ref or not kind:
        fail('TARGET_RESOLUTION_REF_OR_KIND_MISSING:'+cls)
    if kind not in allowed:
        fail('TARGET_RESOLUTION_KIND_NOT_ALLOWED:'+cls+':'+kind)
    rp=Path(ref)
    if rp.is_absolute() or '..' in rp.parts:
        fail('TARGET_RESOLUTION_REF_INVALID:'+cls)
    receipt=_external_yaml(execution_root/rp,'EXECUTION_TARGET_RESOLUTION_RECEIPT')
    common=set(map(str,policy.get('successor_execution_target_resolution_common_required_fields') or []))
    missing=sorted(common-set(receipt))
    if missing:
        fail('TARGET_RESOLUTION_RECEIPT_FIELDS_MISSING:'+cls+':'+repr(missing))
    expected_successor=successor_uid if successor_uid else 'NEXT_GOVERNED_UNIT'
    expected={
      'artifact_type':str(policy.get('successor_execution_target_resolution_receipt_type') or ''),
      'binding_uid':str(row.get('binding_uid') or ''),
      'consuming_operation_uid':str(row.get('consuming_operation_uid') or ''),
      'binding_class':cls,
      'target_identity':str(row.get('target_identity') or ''),
      'canonical_owner_or_authority_ref':str(row.get('canonical_owner_or_authority_ref') or ''),
      'authority_evidence_ref':str(row.get('authority_evidence_ref') or ''),
      'work_unit_uid':str(ledger.get('work_unit_uid') or ''),
      'successor_stage_uid':expected_successor,
      'resolution_kind':kind,
      'resolution_status':'PASS',
    }
    for key,value in expected.items():
        if not value or str(receipt.get(key) or '')!=value:
            fail('TARGET_RESOLUTION_RECEIPT_BINDING_MISMATCH:'+cls+':'+key)
    if receipt.get('current_context_match') is not True:
        fail('TARGET_RESOLUTION_CURRENT_CONTEXT_NOT_PROVEN:'+cls)
    if git_context is None:
        git_context=_current_execution_git_context(execution_root)
    context_expected={
      'current_execution_repository':git_context['repository'],
      'current_execution_branch':git_context['branch'],
      'current_execution_head_sha':git_context['head'],
      'current_execution_tree_sha':git_context['tree'],
    }
    for key,value in context_expected.items():
        if str(receipt.get(key) or '')!=value:
            suffix={'current_execution_branch':'BRANCH','current_execution_head_sha':'HEAD','current_execution_tree_sha':'TREE','current_execution_repository':'REPOSITORY'}[key]
            fail('TARGET_RESOLUTION_'+suffix+'_MISMATCH:'+cls)
    if kind in {'CURRENT_REPOSITORY','CURRENT_REPOSITORY_PATH'}:
        required=set(map(str,policy.get('successor_execution_target_resolution_repository_required_fields') or []))
        missing=sorted(required-set(receipt))
        if missing:
            fail('TARGET_RESOLUTION_REPOSITORY_FIELDS_MISSING:'+cls+':'+repr(missing))
        if _canonical_repository_identity(receipt.get('repository_identity'))!=git_context['repository']:
            fail('TARGET_RESOLUTION_REPOSITORY_MISMATCH:'+cls)
        if str(receipt.get('branch_ref_head_sha') or '')!=git_context['head']:
            fail('TARGET_RESOLUTION_BRANCH_REF_HEAD_MISMATCH:'+cls)
    if kind=='CURRENT_REPOSITORY_PATH':
        required=set(map(str,policy.get('successor_execution_target_resolution_repository_path_required_fields') or []))
        missing=sorted(required-set(receipt))
        if missing:
            fail('TARGET_RESOLUTION_REPOSITORY_PATH_FIELDS_MISSING:'+cls+':'+repr(missing))
        target_path=str(receipt.get('target_path') or '').strip()
        tp=Path(target_path)
        if not target_path or tp.is_absolute() or '..' in tp.parts:
            fail('TARGET_RESOLUTION_PATH_INVALID:'+cls)
        physical=execution_root/tp
        if receipt.get('target_path_exists') is not True or not physical.exists():
            fail('TARGET_RESOLUTION_PATH_MISSING:'+cls)
        tracked=_tracked_path_at_head(execution_root,git_context['head'],target_path)
        if receipt.get('target_path_tracked_at_head') is not True or not tracked:
            fail('TARGET_RESOLUTION_PATH_NOT_TRACKED_AT_HEAD:'+cls)
    elif kind=='CURRENT_REPOSITORY':
        pass
    elif kind=='EXTERNAL_CURRENT_TARGET':
        required=set(map(str,policy.get('successor_execution_target_resolution_external_required_fields') or []))
        missing=sorted(required-set(receipt))
        if missing:
            fail('TARGET_RESOLUTION_EXTERNAL_FIELDS_MISSING:'+cls+':'+repr(missing))
        if str(receipt.get('external_resource_identity') or '')!=str(row.get('target_identity') or ''):
            fail('TARGET_RESOLUTION_EXTERNAL_IDENTITY_MISMATCH:'+cls)
        if receipt.get('external_current_identity_match') is not True:
            fail('TARGET_RESOLUTION_EXTERNAL_CURRENT_IDENTITY_NOT_PROVEN:'+cls)
        if not str(receipt.get('external_evidence_ref') or '').strip() or not str(receipt.get('verifier_uid') or '').strip() or str(receipt.get('verification_status') or '')!='PASS':
            fail('TARGET_RESOLUTION_EXTERNAL_VERIFICATION_INVALID:'+cls)
    elif kind=='AUTHORITY_VALUE':
        required=set(map(str,policy.get('successor_execution_target_resolution_authority_value_required_fields') or []))
        missing=sorted(required-set(receipt))
        if missing:
            fail('TARGET_RESOLUTION_AUTHORITY_FIELDS_MISSING:'+cls+':'+repr(missing))
        if str(receipt.get('authority_value') or '')!=str(row.get('target_identity') or ''):
            fail('TARGET_RESOLUTION_AUTHORITY_VALUE_MISMATCH:'+cls)
        if receipt.get('authority_current_identity_match') is not True:
            fail('TARGET_RESOLUTION_AUTHORITY_CURRENT_IDENTITY_NOT_PROVEN:'+cls)
    else:
        fail('TARGET_RESOLUTION_KIND_UNSUPPORTED:'+cls+':'+kind)
    return git_context

def _validate_cross_stage_handoff_ledger(stage_uid,e,stage,stages):
    inv=y(INVARIANTS)
    execution_root=_execution_artifact_root()
    policy=((inv.get('invariants') or {}).get('CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS') or {})
    handoff=e.get('cross_stage_handoff') or {}
    if handoff.get('external_receipt'):
        fail('CROSS_STAGE_EXTERNAL_LEDGER_NOT_ALLOWED_FOR_LOCAL_HANDOFF')
    ref=str(handoff.get('ledger_ref') or '')
    rp=Path(ref)
    if not ref or rp.is_absolute() or '..' in rp.parts:
        fail('CROSS_STAGE_HANDOFF_LEDGER_REF_INVALID')
    _validate_local_file_artifact(execution_root/rp,'CROSS_STAGE_HANDOFF_READINESS_LEDGER')
    ledger=_external_yaml(execution_root/rp,'CROSS_STAGE_HANDOFF_READINESS_LEDGER')
    if ledger.get('artifact_type')!='CROSS_STAGE_HANDOFF_READINESS_LEDGER':
        fail('CROSS_STAGE_HANDOFF_LEDGER_TYPE_INVALID')
    if ledger.get('stage_uid')!=stage_uid or ledger.get('successor_stage_uid')!=stage.get('next_stage_uid'):
        fail('CROSS_STAGE_HANDOFF_LEDGER_IDENTITY_DRIFT')
    pass_result=e.get('result')=='PASS'
    for key in ('current_matrix_valid','current_state_consistent','denominator_reconciled'):
        if ledger.get(key) is not True:
            fail('CROSS_STAGE_HANDOFF_LEDGER_CORE_INTEGRITY_INVALID:'+key)
    if pass_result:
        for key in ('reference_resolution_complete','physical_materialization_complete','required_field_completeness_complete','consumer_readiness_complete'):
            if ledger.get(key) is not True:
                fail('CROSS_STAGE_HANDOFF_LEDGER_NOT_READY:'+key)

    successor_uid=str(stage.get('next_stage_uid') or '')
    input_rows=ledger.get('successor_required_inputs')
    if not isinstance(input_rows,list):
        fail('CROSS_STAGE_SUCCESSOR_INPUT_ROWS_INVALID')
    input_required_fields={'input_uid','status','artifact_ref','content_sha256','external_evidence_ref','authority_evidence_ref','consumer_readiness_evidence_ref'}
    seen_inputs={}
    unresolved_input_total=0
    for row in input_rows:
        if not isinstance(row,dict):
            fail('CROSS_STAGE_SUCCESSOR_INPUT_ROW_INVALID')
        missing=sorted(input_required_fields-set(row))
        if missing:
            fail('CROSS_STAGE_SUCCESSOR_INPUT_FIELDS_MISSING:'+repr(missing))
        uid=str(row.get('input_uid') or '')
        if not uid or uid in seen_inputs:
            fail('CROSS_STAGE_SUCCESSOR_INPUT_ROW_INVALID')
        seen_inputs[uid]=row

        status=str(row.get('status') or '')
        if status=='AUTHORIZED_NOT_APPLICABLE':
            if policy.get('authorized_not_applicable_requires_authority_evidence') is not True or not str(row.get('authority_evidence_ref') or '').strip():
                fail('CROSS_STAGE_SUCCESSOR_INPUT_NA_AUTHORITY_MISSING:'+uid)
        elif status=='MATERIALIZED':
            aref=str(row.get('artifact_ref') or '').strip()
            ap=Path(aref)
            if not aref or ap.is_absolute() or '..' in ap.parts:
                fail('CROSS_STAGE_SUCCESSOR_INPUT_ARTIFACT_REF_INVALID:'+uid)
            artifact_path=(execution_root/ap).resolve()
            try:
                artifact_path.relative_to(execution_root.resolve())
            except ValueError:
                fail('CROSS_STAGE_SUCCESSOR_INPUT_ARTIFACT_REF_ESCAPES_ROOT:'+uid)
            _validate_local_file_artifact(artifact_path,'CROSS_STAGE_SUCCESSOR_INPUT_ARTIFACT:'+uid)
            declared_hash=str(row.get('content_sha256') or '').strip()
            actual_hash=_sha256_file(artifact_path)
            if not declared_hash or declared_hash!=actual_hash:
                fail('CROSS_STAGE_SUCCESSOR_INPUT_CONTENT_HASH_DRIFT:'+uid)
            readiness_ref=str(row.get('consumer_readiness_evidence_ref') or '').strip()
            rr=Path(readiness_ref)
            if not readiness_ref or rr.is_absolute() or '..' in rr.parts:
                fail('CROSS_STAGE_SUCCESSOR_INPUT_READINESS_REF_INVALID:'+uid)
            readiness_path=(execution_root/rr).resolve()
            try:
                readiness_path.relative_to(execution_root.resolve())
            except ValueError:
                fail('CROSS_STAGE_SUCCESSOR_INPUT_READINESS_REF_ESCAPES_ROOT:'+uid)
            _validate_local_file_artifact(readiness_path,'CROSS_STAGE_SUCCESSOR_INPUT_READINESS:'+uid)
        elif not pass_result and status in {'UNRESOLVED','BLOCKED','MISSING'}:
            unresolved_input_total+=1
        else:
            fail('CROSS_STAGE_SUCCESSOR_INPUT_NOT_READY:'+uid+':'+status)

    if successor_uid in stages:
        expected_inputs=set(map(str,stages[successor_uid].get('inputs') or []))
        if set(seen_inputs)!=expected_inputs:
            fail('CROSS_STAGE_SUCCESSOR_INPUT_DENOMINATOR_DRIFT:expected='+repr(sorted(expected_inputs))+':actual='+repr(sorted(seen_inputs)))
    elif seen_inputs:
        fail('CROSS_STAGE_TERMINAL_SUCCESSOR_INPUTS_MUST_BE_EMPTY')

    if ledger.get('unresolved_required_dependency_total')!=unresolved_input_total:
        fail('CROSS_STAGE_SUCCESSOR_INPUT_UNRESOLVED_TOTAL_DRIFT')
    if pass_result:
        if unresolved_input_total!=0 or ledger.get('status')!='PASS':
            fail('CROSS_STAGE_HANDOFF_PASS_WITH_UNRESOLVED_INPUT')
    else:
        handoff_blocked=(unresolved_input_total>0 or any(ledger.get(k) is not True for k in ('reference_resolution_complete','physical_materialization_complete','required_field_completeness_complete','consumer_readiness_complete')))
        expected_status='BLOCKED' if handoff_blocked else 'PASS'
        if ledger.get('status')!=expected_status:
            fail('CROSS_STAGE_HANDOFF_STATUS_RESULT_DRIFT:expected='+expected_status+':actual='+str(ledger.get('status')))
    return True

def validate_evidence_data(stage_uid,e,validation_phase='PRE_CLOSE_CANDIDATE'):
    entry,reg,gov,profile,adapters,stages=validate_definition()
    if stage_uid not in stages: fail(f'UNKNOWN_STAGE:{stage_uid}')
    st=stages[stage_uid]; ad=adapters['stages'][stage_uid]
    missing=sorted(EVIDENCE_FIELDS-set(e))
    if missing: fail(f'NORMALIZED_EVIDENCE_FIELD_MISSING:{missing}')
    if e.get('governance_uid')!=gov or e.get('stage_uid')!=stage_uid: fail('EVIDENCE_IDENTITY_DRIFT')
    scope_ref=str(e.get('scope_manifest_ref') or '')
    if not scope_ref: fail('EVIDENCE_SCOPE_MANIFEST_REF_MISSING')
    if scope_ref.startswith('governance/test/'): fail('LEGACY_GOVERNANCE_TEST_SCOPE_REF_FORBIDDEN')
    _scope,_work,_state,_work_dir=_validate_current_stage_state_bundle(stage_uid,e,st,gov,validation_phase)
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
    if d['required_total']!=len(expected_ops): fail('EVIDENCE_REQUIRED_TOTAL_DRIFT')
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
    evidence_types=[]
    for item in items:
        if not isinstance(item,dict) or not str(item.get('evidence_type') or '').strip():
            fail('REQUIRED_EVIDENCE_ITEM_INVALID')
        evidence_types.append(str(item['evidence_type']))
    if len(evidence_types)!=len(set(evidence_types)):
        fail('REQUIRED_EVIDENCE_DUPLICATE')
    got=set(evidence_types)
    if got!=req:
        fail(f'REQUIRED_EVIDENCE_DENOMINATOR_DRIFT:expected={sorted(req)} actual={sorted(got)}')
    for item in items:
        status=str(item.get('status') or '')
        if status=='PASS':
            if not item.get('ref'): fail('REQUIRED_EVIDENCE_PASS_REF_MISSING:'+str(item.get('evidence_type')))
            if not item.get('external_receipt'):
                _validate_local_file_artifact(
                    _execution_artifact_root()/str(item['ref']),
                    'REQUIRED_EVIDENCE_PHYSICAL:'+str(item.get('evidence_type'))
                )
        elif status=='NOT_APPLICABLE_WITH_PROOF':
            proof=str(item.get('authority_evidence_ref') or item.get('proof') or '')
            if not proof:
                fail('REQUIRED_EVIDENCE_NA_AUTHORITY_MISSING:'+str(item.get('evidence_type')))
            if item.get('ref') and not item.get('external_receipt'):
                _validate_local_file_artifact(
                    _execution_artifact_root()/str(item['ref']),
                    'REQUIRED_EVIDENCE_NA_PHYSICAL:'+str(item.get('evidence_type'))
                )
        else:
            fail('REQUIRED_EVIDENCE_TERMINAL_DISPOSITION_INVALID:'+str(item.get('evidence_type'))+':'+status)

    if stage_uid=='STAGE-11':
        terminal=e.get('terminal_disposition')
        if not isinstance(terminal,dict):
            fail('TERMINAL_DISPOSITION_INVALID')
        required_terminal_fields={'status','next_governed_unit_eligibility_ref','scope_complete_or_next_governed_unit','unresolved_required_dependency_total'}
        if not required_terminal_fields.issubset(terminal):
            fail('TERMINAL_DISPOSITION_FIELD_MISSING')
        if terminal.get('status') not in {'PASS','BLOCKED'}:
            fail('TERMINAL_DISPOSITION_STATUS_INVALID')
        if not isinstance(terminal.get('unresolved_required_dependency_total'),int) or terminal.get('unresolved_required_dependency_total')<0:
            fail('TERMINAL_DISPOSITION_UNRESOLVED_COUNT_INVALID')
        elig_ref=str(terminal.get('next_governed_unit_eligibility_ref') or '')
        if e.get('result')=='PASS':
            if not elig_ref:
                fail('TERMINAL_DISPOSITION_ELIGIBILITY_REF_MISSING')
            _validate_local_file_artifact(_execution_artifact_root()/Path(elig_ref),'NEXT_GOVERNED_UNIT_ELIGIBILITY')
            if terminal.get('status')!='PASS' or terminal.get('unresolved_required_dependency_total')!=0:
                fail('PASS_WITH_TERMINAL_DISPOSITION_NOT_READY')
        elif elig_ref:
            _validate_local_file_artifact(_execution_artifact_root()/Path(elig_ref),'NEXT_GOVERNED_UNIT_ELIGIBILITY')
    else:
        handoff=e.get('cross_stage_handoff')
        if not isinstance(handoff,dict):
            fail('CROSS_STAGE_HANDOFF_INVALID')
        required_handoff_fields={'ledger_ref','external_receipt','successor_stage_uid','reference_resolution_complete','physical_materialization_complete','required_field_completeness_complete','denominator_reconciled','consumer_readiness_complete','current_matrix_valid','current_state_consistent','unresolved_required_dependency_total','status'}
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
            if not ref or not (_execution_artifact_root()/ref).is_file():
                fail('CROSS_STAGE_HANDOFF_LEDGER_PHYSICAL_REF_MISSING')
        _validate_cross_stage_handoff_ledger(stage_uid,e,st,stages)
        if e.get('result')=='PASS':
            for key in ('reference_resolution_complete','physical_materialization_complete','required_field_completeness_complete','denominator_reconciled','consumer_readiness_complete','current_matrix_valid','current_state_consistent'):
                if handoff.get(key) is not True:
                    fail('PASS_WITH_CROSS_STAGE_HANDOFF_NOT_READY:'+key)
            if handoff.get('unresolved_required_dependency_total')!=0 or handoff.get('status')!='PASS':
                fail('PASS_WITH_UNRESOLVED_CROSS_STAGE_HANDOFF')
    # Generic CI/workflow exact-head receipts are not Product Stage closure authority.
    # source_head_sha remains snapshot provenance only.
    checkpoint=e.get('state_checkpoint')
    if not isinstance(checkpoint,dict) or checkpoint.get('performed') is not True:
        fail('STATE_CHECKPOINT_INVALID')
    state_ref=str(checkpoint.get('state_ref') or '')
    if not state_ref:
        fail('STATE_CHECKPOINT_REF_MISSING')
    cp=(_execution_artifact_root()/Path(state_ref)).resolve()
    expected_cp=(_work_dir/'EXECUTION_STATE.yaml').resolve()
    if cp!=expected_cp:
        fail('STATE_CHECKPOINT_REF_DRIFT')
    nxt=e.get('next_stage_transition')
    if not isinstance(nxt,dict) or nxt.get('next_stage_uid')!=st.get('next_stage_uid'):
        fail('NEXT_STAGE_TRANSITION_INVALID')
    if e.get('result') not in {'PASS','BLOCKED'}: fail('EVIDENCE_RESULT_INVALID')
    if e.get('result')=='BLOCKED':
        if nxt.get('status')!='BLOCKED': fail('BLOCKED_EVIDENCE_NEXT_STAGE_TRANSITION_NOT_BLOCKED')
    elif nxt.get('status') not in {'READY','SCOPE_COMPLETE','NEXT_GOVERNED_UNIT_READY'}:
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

def validate_evidence(stage_uid,path,validation_phase='PRE_CLOSE_CANDIDATE'):
    return validate_evidence_data(stage_uid,j(path),validation_phase)

def validate_terminal(stage_uid,evidence,receipt=None,validation_phase='PRE_CLOSE_CANDIDATE'):
    e=validate_evidence(stage_uid,evidence,validation_phase)
    if e.get('result')!='PASS':
        fail('TERMINAL_CLOSURE_REQUIRES_PASS_EVIDENCE')

    # Transport/CI receipts are optional provenance only. Product Stage closure
    # is decided from Current content evidence plus the single EXECUTION_STATE.
    if receipt:
        receipt_path=Path(receipt)
        if receipt_path.exists():
            try:
                r=j(receipt_path)
            except Exception:
                r={}
            # Intentionally no closure credit or denial from provider/head/run/
            # conclusion fields. Invalid transport provenance is audited outside
            # the Product Stage content-completion denominator.

    execution_root=_execution_artifact_root()
    _,_,gov,_,_,stages=validate_definition()
    st=stages[stage_uid]
    scope_ref=Path(str(e.get('scope_manifest_ref') or ''))
    scope=_external_yaml(execution_root/scope_ref,'CURRENT_EXECUTION_SCOPE')
    work_dir=(execution_root/scope_ref).parent
    work=_external_yaml(work_dir/'WORK_UNIT.yaml','CURRENT_WORK_UNIT')
    governed_scope=str(scope.get('governed_unit_uid') or '').strip()
    governed_work=str(work.get('governed_unit_uid') or '').strip()
    if not governed_scope or not governed_work or governed_scope!=governed_work:
        fail('TERMINAL_CLOSURE_GOVERNED_UNIT_IDENTITY_DRIFT')

    denominator=e.get('denominator') or {}
    expected_ops=list(map(str,st.get('operations') or []))
    if denominator.get('required_total')!=len(expected_ops):
        fail('TERMINAL_CLOSURE_DENOMINATOR_IDENTITY_DRIFT')
    op_rows=e.get('operation_results') or []
    if [str(x.get('operation_uid') or '') for x in op_rows]!=expected_ops:
        fail('TERMINAL_CLOSURE_OPERATION_RECEIPT_CHAIN_DRIFT')
    evidence_rows=e.get('required_evidence') or []
    if not evidence_rows or any(
        row.get('status')=='PASS' and not str(row.get('ref') or '').strip()
        for row in evidence_rows
    ):
        fail('TERMINAL_CLOSURE_EVIDENCE_REFS_INCOMPLETE')
    successor=e.get('next_stage_transition')
    if not isinstance(successor,dict) or successor.get('next_stage_uid')!=st.get('next_stage_uid') or not successor.get('status'):
        fail('TERMINAL_CLOSURE_SUCCESSOR_ELIGIBILITY_INVALID')

    contract=_deterministic_stage_audit_contract().get('terminal_receipt_contract') or {}
    if contract.get('required_for_stage_closure') is not False:
        fail('TERMINAL_RECEIPT_OPTIONALITY_CONTRACT_DRIFT')
    if contract.get('may_override_content_evidence') is not False or contract.get('may_override_execution_state') is not False:
        fail('TERMINAL_RECEIPT_OVERRIDE_CONTRACT_DRIFT')
    if gov!=e.get('governance_uid'):
        fail('TERMINAL_CLOSURE_CURRENT_GOVERNANCE_DRIFT')
    print(f'PASS: content-evidence terminal closure valid for {stage_uid} governed_unit={governed_scope}')

def _validate_governance_load_receipt(execution_root,ref,work,stage_uid,operation_uid,gov):
    receipt_path=Path(str(ref or ''))
    if not ref or receipt_path.is_absolute() or '..' in receipt_path.parts:
        fail('GOVERNANCE_LOAD_RECEIPT_REF_INVALID:'+operation_uid)
    full=(execution_root/receipt_path).resolve()
    try:
        full.relative_to(execution_root.resolve())
    except ValueError:
        fail('GOVERNANCE_LOAD_RECEIPT_REF_ESCAPES_ROOT:'+operation_uid)
    receipt=_external_yaml(full,'GOVERNANCE_LOAD_RECEIPT')
    expected={
      'artifact_type':'GOVERNANCE_LOAD_RECEIPT',
      'stage_uid':stage_uid,
      'work_unit_uid':str(work.get('work_unit_uid') or ''),
      'current_operation':operation_uid,
      'governance_uid':gov,
      'status':'PASS',
    }
    for key,val in expected.items():
        if receipt.get(key)!=val:
            fail('GOVERNANCE_LOAD_RECEIPT_IDENTITY_DRIFT:'+operation_uid+':'+key)
    for key in ('execution_head','execution_tree','root_manifest_sha256','effective_normative_set_sha256','timestamp','loader_identity'):
        if not str(receipt.get(key) or '').strip():
            fail('GOVERNANCE_LOAD_RECEIPT_FIELD_MISSING:'+operation_uid+':'+key)
    if not isinstance(receipt.get('dependency_hashes'),dict):
        fail('GOVERNANCE_LOAD_RECEIPT_DEPENDENCY_HASHES_INVALID:'+operation_uid)
    return receipt

def _load_operation_receipt(path):
    _validate_local_file_artifact(path,'ACTIVE_OPERATION_RECEIPT')
    try:
        if path.suffix.lower()=='.json':
            obj=json.loads(path.read_text(encoding='utf-8'))
        else:
            obj=yaml.safe_load(path.read_text(encoding='utf-8'))
    except Exception as exc:
        fail('ACTIVE_OPERATION_RECEIPT_PARSE_FAILED:'+type(exc).__name__)
    if not isinstance(obj,dict):
        fail('ACTIVE_OPERATION_RECEIPT_MAPPING_REQUIRED')
    return obj

def _atomic_yaml_write(path,obj):
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(yaml.safe_dump(obj,sort_keys=False,allow_unicode=True),encoding='utf-8')
    tmp.replace(path)

def _refresh_canonical_state_ledger_hash(work_path,work,state_path):
    bindings=work.get('current_ledger_bindings')
    if not isinstance(bindings,dict) or not isinstance(bindings.get('EXECUTION_STATE'),dict):
        return False
    row=bindings['EXECUTION_STATE']
    expected_ref=state_path.resolve()
    actual_ref=(_execution_artifact_root()/Path(str(row.get('artifact_ref') or ''))).resolve()
    if actual_ref!=expected_ref:
        fail('CURRENT_STATE_LEDGER_ALIAS_DRIFT_DURING_CHECKPOINT')
    row['content_sha256']=_sha256_file(state_path)
    bindings['EXECUTION_STATE']=row
    work['current_ledger_bindings']=bindings
    _atomic_yaml_write(work_path,work)
    return True


def execute_active(stage_uid):
    _,_,gov,_,adapters,stages=validate_definition()
    work=active_execution(stage_uid)
    execution_root,work_ctx,scope,work_rel,scope_rel=execution_context()
    if work_ctx.get('work_unit_uid')!=work.get('work_unit_uid'):
        fail('ACTIVE_STAGE_WORK_UNIT_CONTEXT_DRIFT')
    work_path=(execution_root/Path(work_rel)).resolve()
    work_dir=work_path.parent
    state_path=work_dir/'EXECUTION_STATE.yaml'
    state=_external_yaml(state_path,'CURRENT_EXECUTION_STATE')
    compat=execution_compatibility_adapter()
    scope_allowed_field=str(compat['scope_execution_allowed_field'])
    resume_control_field=str(compat['resume_control_field'])
    resume_allowed_field=str(compat['resume_execution_allowed_field'])
    resume_control=state.get(resume_control_field) or {}
    if (work.get('pre_execution_gate_status')!='PASS'
        or scope.get(scope_allowed_field) is not True
        or not isinstance(resume_control,dict)
        or resume_control.get(resume_allowed_field) is not True):
        fail('ACTIVE_STAGE_EXECUTION_NOT_ADMITTED')
    bindings=work.get('operation_bindings') or {}
    expected_ops=list(map(str,stages[stage_uid].get('operations') or []))
    if set(map(str,bindings))!=set(expected_ops):
        fail('ACTIVE_STAGE_OPERATION_BINDING_COVERAGE_INVALID:'+stage_uid)
    completed=state.get('completed_operations')
    if not isinstance(completed,list):
        fail('ACTIVE_STAGE_COMPLETED_OPERATIONS_INVALID')
    completed=list(map(str,completed))
    if len(completed)!=len(set(completed)) or completed!=expected_ops[:len(completed)]:
        fail('ACTIVE_STAGE_COMPLETED_OPERATION_PREFIX_INVALID:'+repr(completed))
    if len(completed)>=len(expected_ops):
        if str(state.get('current_operation') or '')!='COMPLETE':
            fail('ACTIVE_STAGE_COMPLETE_STATE_OPERATION_DRIFT')
        fail('ACTIVE_STAGE_OPERATIONS_ALREADY_COMPLETE:'+stage_uid)
    operation_uid=expected_ops[len(completed)]
    if str(state.get('current_operation') or '')!=operation_uid:
        fail('ACTIVE_STAGE_CURRENT_OPERATION_DRIFT:expected='+operation_uid+':actual='+str(state.get('current_operation')))
    binding=bindings.get(operation_uid)
    if not isinstance(binding,dict):
        fail('ACTIVE_STAGE_CURRENT_OPERATION_BINDING_MISSING:'+operation_uid)
    driver=adapters.get('execution_driver_contract') or {}
    applicability=str(binding.get(str(driver.get('operation_applicability_field') or 'applicability')) or '')
    allowed_applicability=set(map(str,driver.get('allowed_operation_applicability') or []))
    if applicability not in allowed_applicability:
        fail('ACTIVE_STAGE_OPERATION_APPLICABILITY_INVALID:'+operation_uid)
    result_owner=str(binding.get('result_owner') or '')
    receipt_ref=str(binding.get('operation_receipt_ref') or '')
    if not result_owner or not receipt_ref:
        fail('ACTIVE_STAGE_OPERATION_BINDING_RESULT_OR_RECEIPT_MISSING:'+operation_uid)
    receipt_rel=Path(receipt_ref)
    if receipt_rel.is_absolute() or '..' in receipt_rel.parts:
        fail('ACTIVE_STAGE_OPERATION_RECEIPT_REF_INVALID:'+operation_uid)
    receipt_path=(execution_root/receipt_rel).resolve()
    try:
        receipt_path.relative_to(work_dir.resolve())
    except ValueError:
        fail('ACTIVE_STAGE_OPERATION_RECEIPT_OUTSIDE_WORK_UNIT:'+operation_uid)
    if receipt_path.exists():
        fail('ACTIVE_STAGE_OPERATION_RECEIPT_ALREADY_EXISTS:'+receipt_ref)
    if applicability=='REQUIRED':
        governance_receipt_ref=str(binding.get('governance_load_receipt_ref') or '')
        _validate_governance_load_receipt(execution_root,governance_receipt_ref,work,stage_uid,operation_uid,gov)
    if applicability=='AUTHORIZED_NOT_APPLICABLE':
        authority_ref=str(binding.get('authority_evidence_ref') or '')
        if driver.get('authorized_not_applicable_requires_authority_evidence') is not True or not authority_ref:
            fail('ACTIVE_STAGE_OPERATION_NA_AUTHORITY_MISSING:'+operation_uid)
        if driver.get('authorized_not_applicable_invokes_executor') is not False:
            fail('ACTIVE_STAGE_OPERATION_NA_EXECUTOR_POLICY_INVALID')
        receipt_path.parent.mkdir(parents=True,exist_ok=True)
        receipt={
          'artifact_type':'OPERATION_EXECUTION_RECEIPT',
          'stage_uid':stage_uid,
          'work_unit_uid':str(work.get('work_unit_uid') or ''),
          'operation_uid':operation_uid,
          'governance_uid':gov,
          'status':'NOT_APPLICABLE_WITH_PROOF',
          'result_owner':result_owner,
          'authority_evidence_ref':authority_ref,
          'proof':authority_ref
        }
        _atomic_yaml_write(receipt_path,receipt)
        completed.append(operation_uid)
        validate_normative_execution_matrix(
            stage_uid,execution_root,work,stages[stage_uid],gov,
            validation_phase='STEP',completed_operations=completed
        )
        next_op=expected_ops[len(completed)] if len(completed)<len(expected_ops) else 'COMPLETE'
        state['completed_operations']=completed
        state['current_operation']=next_op
        state['status']='IN_PROGRESS' if next_op!='COMPLETE' else 'EXECUTION_COMPLETE_CLOSURE_PENDING'
        if 'current_status' in state:
            state['current_status']=state['status']
        state['last_operation_uid']=operation_uid
        state['last_operation_receipt_ref']=receipt_ref
        _atomic_yaml_write(state_path,state)
        _refresh_canonical_state_ledger_hash(work_path,work,state_path)
        print(json.dumps({
          'result':'NOT_APPLICABLE_WITH_PROOF','stage_uid':stage_uid,'work_unit_uid':str(work.get('work_unit_uid') or ''),
          'operation_uid':operation_uid,'authority_evidence_ref':authority_ref,'operation_receipt_ref':receipt_ref,
          'next_operation':next_op,'stage_status':state['status'],'stage_closure_claimed':False
        },sort_keys=True))
        return True
    owner=str(binding.get('executor_owner') or '')
    protocol=str(binding.get('executor_protocol') or '')
    if protocol not in set(map(str,driver.get('allowed_operation_executor_protocols') or [])):
        fail('ACTIVE_STAGE_EXECUTOR_PROTOCOL_FORBIDDEN:'+protocol)
    if protocol!='PYTHON_STAGE_OPERATION_V1':
        fail('ACTIVE_STAGE_EXECUTOR_PROTOCOL_UNSUPPORTED:'+protocol)
    rel=Path(owner)
    if rel.is_absolute() or '..' in rel.parts or rel.suffix.lower()!='.py':
        fail('ACTIVE_STAGE_EXECUTOR_OWNER_PATH_INVALID')
    executor=(execution_root/rel).resolve()
    try:
        executor.relative_to(execution_root)
    except ValueError:
        fail('ACTIVE_STAGE_EXECUTOR_OUTSIDE_EXECUTION_ROOT')
    if not executor.is_file():
        fail('ACTIVE_STAGE_EXECUTOR_OWNER_MISSING:'+owner)
    if executor.resolve()==Path(__file__).resolve():
        fail('COMMON_ENGINE_RECURSIVE_EXECUTOR_FORBIDDEN')
    adapter=(adapters.get('stages') or {}).get(stage_uid) or {}
    if adapter.get('effectful_executor_owner_resolution')!='CURRENT_WORK_UNIT_OPERATION_BINDING_ONLY':
        fail('ACTIVE_STAGE_EXECUTOR_OWNER_RESOLUTION_POLICY_INVALID:'+stage_uid)
    ref=str(adapter.get('stepwise_execution_contract_ref') or '')
    if ref!='stepwise_execution_defaults':
        fail('ACTIVE_STAGE_STEPWISE_EXECUTION_CONTRACT_REF_INVALID:'+stage_uid)
    stepwise=adapters.get('stepwise_execution_defaults')
    if not isinstance(stepwise,dict):
        fail('ACTIVE_STAGE_STEPWISE_EXECUTION_CONTRACT_MISSING:'+stage_uid)
    if stepwise.get('mode')!='OPERATION_BY_OPERATION':
        fail('ACTIVE_STAGE_STEPWISE_EXECUTION_MODE_INVALID:'+stage_uid)
    if stepwise.get('bulk_stage_materialization')!='FORBIDDEN':
        fail('ACTIVE_STAGE_BULK_MATERIALIZATION_NOT_FORBIDDEN:'+stage_uid)
    if stepwise.get('checkpoint_after_each_operation') is not True:
        fail('ACTIVE_STAGE_OPERATION_CHECKPOINT_NOT_REQUIRED:'+stage_uid)
    if stepwise.get('successor_requires_operation_pass') is not True:
        fail('ACTIVE_STAGE_SUCCESSOR_OPERATION_PASS_NOT_REQUIRED:'+stage_uid)
    execution_root_arg=str(compat['operation_executor_execution_root_argument'])
    cmd=[sys.executable,str(executor),'--stage',stage_uid,'--operation',operation_uid,'--work-unit',work_rel,execution_root_arg,str(execution_root)]
    proc=subprocess.run(cmd,cwd=execution_root,text=True,capture_output=True)
    if proc.returncode!=0:
        msg=(proc.stderr or proc.stdout or '').strip().replace('\n',' ')[:800]
        fail('ACTIVE_STAGE_OPERATION_EXECUTOR_FAILED:'+operation_uid+':'+str(proc.returncode)+':'+msg)
    receipt=_load_operation_receipt(receipt_path)
    expected_receipt={
      'artifact_type':'OPERATION_EXECUTION_RECEIPT',
      'stage_uid':stage_uid,
      'work_unit_uid':str(work.get('work_unit_uid') or ''),
      'operation_uid':operation_uid,
      'governance_uid':gov,
      'status':'PASS',
      'executor_owner':owner,
      'executor_protocol':protocol,
      'result_owner':result_owner
    }
    for key,val in expected_receipt.items():
        if receipt.get(key)!=val:
            fail('ACTIVE_STAGE_OPERATION_RECEIPT_IDENTITY_DRIFT:'+operation_uid+':'+key)
    completed.append(operation_uid)
    validate_normative_execution_matrix(
        stage_uid,execution_root,work,stages[stage_uid],gov,
        validation_phase='STEP',completed_operations=completed
    )
    next_op=expected_ops[len(completed)] if len(completed)<len(expected_ops) else 'COMPLETE'
    state['completed_operations']=completed
    state['current_operation']=next_op
    state['status']='IN_PROGRESS' if next_op!='COMPLETE' else 'EXECUTION_COMPLETE_CLOSURE_PENDING'
    if 'current_status' in state:
        state['current_status']=state['status']
    state['last_operation_uid']=operation_uid
    state['last_operation_receipt_ref']=receipt_ref
    _atomic_yaml_write(state_path,state)
    _refresh_canonical_state_ledger_hash(work_path,work,state_path)
    print(json.dumps({
      'result':'PASS',
      'stage_uid':stage_uid,
      'work_unit_uid':work.get('work_unit_uid'),
      'operation_uid':operation_uid,
      'operation_receipt_ref':receipt_ref,
      'next_operation':next_op,
      'stage_status':state['status'],
      'stage_closure_claimed':False
    },ensure_ascii=False))
    return True


def main():
    p=argparse.ArgumentParser(); g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--definition-audit-all',action='store_true'); g.add_argument('--plan',action='store_true'); g.add_argument('--plan-range',action='store_true'); g.add_argument('--admission-check',action='store_true'); g.add_argument('--validate-evidence',action='store_true'); g.add_argument('--validate-closure',action='store_true'); g.add_argument('--execute',action='store_true')
    p.add_argument('--stage'); p.add_argument('--start-stage'); p.add_argument('--end-stage'); p.add_argument('--evidence'); p.add_argument('--receipt'); p.add_argument('--validation-phase',choices=['PRE_CLOSE_CANDIDATE','POST_CLOSE_FINAL'],default='PRE_CLOSE_CANDIDATE'); a=p.parse_args()
    try:
        if a.execute:
            if not a.stage: fail('STAGE_REQUIRED')
            execute_active(a.stage); return
        if a.plan_range:
            if not a.start_stage or not a.end_stage: fail('RANGE_ENDPOINTS_REQUIRED')
            print(json.dumps(plan_range(a.start_stage,a.end_stage),ensure_ascii=False,indent=2)); return
        if a.definition_audit_all:
            _,_,_,profile,_,stages=validate_definition()
            print(f'PASS: common Stage Execution Engine definition audit stages={len(stages)}/{profile.get("profile_local_denominator")} phases={len(EXPECTED_PHASES)}/{len(EXPECTED_PHASES)}')
            print('PASS: all profile stages have semantic adapters, scanner dimensions, denominator, operations, outputs, evidence and closure contracts')
            print('PASS: definition audit effectful_execution_credit=0; execution PASS requires fresh content evidence and single EXECUTION_STATE')
            return
        if not a.stage: fail('STAGE_REQUIRED')
        if a.plan: print(json.dumps(plan(a.stage),ensure_ascii=False,indent=2)); return
        if a.admission_check: admission(a.stage); return
        if a.validate_evidence:
            if not a.evidence: fail('EVIDENCE_PATH_REQUIRED')
            validate_evidence(a.stage,ROOT/a.evidence,a.validation_phase); print(f'PASS: normalized fresh execution evidence valid for {a.stage} phase={a.validation_phase}'); return
        if a.validate_closure:
            if not a.evidence: fail('EVIDENCE_PATH_REQUIRED')
            receipt_path=(ROOT/a.receipt) if a.receipt else None
            validate_terminal(a.stage,ROOT/a.evidence,receipt_path,a.validation_phase); return
    except StageEngineError as exc:
        print(f'BLOCK: {exc}',file=sys.stderr); raise SystemExit(1)
if __name__=='__main__': main()
