#!/usr/bin/env python3
from pathlib import Path
import json,yaml
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
INDEX=ROOT/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def validate(root=ROOT):
    failures=[]
    pp=root/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
    if not pp.exists(): return {'status':'FAIL','failures':['lifecycle_stage_registry_missing']}
    d=load(pp); stages=d.get('stages') or []
    if len(stages)!=11: failures.append(f'stage_count:{len(stages)}')
    expected=[f'STAGE-{i:02d}' for i in range(1,12)]
    ids=[s.get('stage_uid') for s in stages]
    if ids!=expected: failures.append('stage_order_or_identity_invalid')
    all_ops={}
    for s in stages:
        sid=s.get('stage_uid'); ops=s.get('operations') or []
        if not all([s.get('entry_gate'),s.get('exit_gate'),s.get('scope_mode'),s.get('next_stage_uid')]): failures.append('stage_core_contract_missing:'+str(sid))
        for field in ['inputs','input_origins','operations','outputs','output_producers','validators','required_evidence']:
            if field not in s: failures.append(f'stage_field_missing:{sid}:{field}')
        if len(s.get('inputs') or [])!=len(set(s.get('inputs') or [])): failures.append('duplicate_stage_input:'+str(sid))
        if len(s.get('outputs') or [])!=len(set(s.get('outputs') or [])): failures.append('duplicate_stage_output:'+str(sid))
        origins=s.get('input_origins') or {}
        for inp in s.get('inputs') or []:
            if not origins.get(inp): failures.append(f'input_origin_missing:{sid}:{inp}')
        producers=s.get('output_producers') or {}
        for out in s.get('outputs') or []:
            op=producers.get(out)
            if not op: failures.append(f'output_producer_missing:{sid}:{out}')
            elif op not in ops: failures.append(f'output_producer_not_operation:{sid}:{out}:{op}')
        for op in ops:
            if op in all_ops: failures.append(f'duplicate_operation_uid:{op}')
            all_ops[op]=sid
    stage1=stages[0] if stages else {}
    expected_stage1_prefix=['SOURCE_STRUCTURE_ENUMERATION','SOURCE_SEGMENT_MAPPING','SOURCE_CONTEXT_COMPILATION','SOURCE_SUPERSESSION_CONFLICT_RESOLUTION','SOURCE_DEPENDENCY_EXTRACTION','RESPONSIBILITY_CLASSIFICATION','PAGE_BASE_BLUEPRINT_COMPILE','VISUAL_BASE_BLUEPRINT_COMPILE','BLUEPRINT_BINDING_COMPILE']
    if stage1.get('operations')!=expected_stage1_prefix: failures.append('stage1_operation_order_invalid')
    if 'SOURCE_SEGMENT_MAP' not in (stage1.get('outputs') or []) or (stage1.get('output_producers') or {}).get('SOURCE_SEGMENT_MAP')!='SOURCE_SEGMENT_MAPPING': failures.append('stage1_segment_mapping_not_registered')
    pb=stage1.get('stage1_phase_boundary_contract') or {}
    if pb.get('phase_order')!=['SOURCE_STRUCTURE_ENUMERATION','SOURCE_SEGMENT_MAPPING','SOURCE_FACT_MATERIALIZATION','RESPONSIBILITY_CLASSIFICATION','PAGE_BASE_BLUEPRINT_COMPILE','VISUAL_BASE_BLUEPRINT_COMPILE','BLUEPRINT_BINDING_COMPILE']: failures.append('stage1_phase_order_invalid')
    if pb.get('source_fact_materialization_operations')!=['SOURCE_CONTEXT_COMPILATION','SOURCE_SUPERSESSION_CONFLICT_RESOLUTION','SOURCE_DEPENDENCY_EXTRACTION']: failures.append('stage1_source_fact_phase_operations_invalid')
    for k,v in [('segment_mapping_to_source_fact_transition','LEGAL'),('source_fact_start_before_segment_mapping_close','BLOCK'),('classification_or_blueprint_before_source_fact_close','BLOCK'),('website_or_deployment_in_stage_01','BLOCK')]:
        if pb.get(k)!=v: failures.append('stage1_phase_boundary_rule_invalid:'+k)
    eag=stage1.get('unresolved_external_authority_gate') or {}
    for k in ['preserve_explicit_out_of_capture_authority_refs','blueprint_carry_forward_required','affected_closure_requires_resolution_evidence']:
        if eag.get(k) is not True: failures.append('stage1_external_authority_rule_not_true:'+k)
    if eag.get('source_fact_disposition')!='UNRESOLVED_AUTHORITY_GAP' or eag.get('source_fact_closure_with_preserved_unresolved_refs')!='ALLOW' or eag.get('ai_auto_fill_or_inference')!='BLOCK' or eag.get('drop_ignore_or_false_resolution')!='BLOCK': failures.append('stage1_external_authority_fail_closed_contract_invalid')

    inv=((d.get('cross_stage_invariants') or {}).get('semantic_granularity') or {})
    expected_units={'STAGE-01':'SOURCE_STRUCTURE_OR_SEGMENT_UNIT','STAGE-02':'FUNCTIONAL_CONTRACT_OR_DEPENDENCY_UNIT','STAGE-03':'VISUAL_SPEC_OR_GEOMETRY_UNIT','STAGE-04':'FOUNDATION_FREEZE_OR_ACCEPTANCE_UNIT','STAGE-05':'PROGRAM_ARTIFACT_OR_WORK_UNIT','STAGE-06':'VERIFICATION_OR_ACCEPTANCE_MATRIX_UNIT','STAGE-07':'BUILD_OR_RELEASE_CANDIDATE_UNIT','STAGE-08':'STAGING_APPLICABILITY_OR_ACCEPTANCE_UNIT','STAGE-09':'CUTOVER_MIGRATION_DEPLOYMENT_OR_ROLLBACK_UNIT','STAGE-10':'PRODUCTION_ACCEPTANCE_DIMENSION_UNIT','STAGE-11':'CLOSURE_OPERATIONS_OR_NEXT_PAGE_ELIGIBILITY_UNIT'}
    if inv.get('invariant_uid')!='GOV-INV-SEMANTIC-GRANULARITY-001': failures.append('semantic_granularity_invariant_missing_or_wrong')
    if inv.get('normative_section_uid')!='WEB-GOV-03-S052': failures.append('semantic_granularity_normative_section_wrong')
    if inv.get('applies_to_stages')!=expected: failures.append('semantic_granularity_not_all_stages')
    for k in ['syntax_level_is_not_governance_granularity','terminal_unit_must_be_semantically_homogeneous','recursive_decomposition_required','parent_child_responsibility_conservation_required','downstream_universe_shrink_forbidden','later_stage_revalidation_required']:
        if inv.get(k) is not True: failures.append('semantic_granularity_rule_not_true:'+k)
    if inv.get('mixed_terminal_unit')!='BLOCK' or inv.get('unresolved_container_unit')!='BLOCK': failures.append('semantic_granularity_fail_closed_missing')
    if inv.get('allowed_exception')!='MIXED_ALLOWED_WITH_COMPLETE_PROOF': failures.append('semantic_granularity_exception_invalid')
    reqproof=['same_owner','same_lifecycle','same_approval','same_version','same_test_or_acceptance_scope','same_stage_identity']
    if inv.get('mixed_allowed_required_proofs')!=reqproof: failures.append('semantic_granularity_mixed_allowed_proof_set_invalid')
    counters=inv.get('closure_counters') or {}
    for k in ['MIXED_TERMINAL_UNITS','UNRESOLVED_CONTAINER_UNITS','LOST_REQUIRED_RESPONSIBILITIES','DUPLICATE_REQUIRED_RESPONSIBILITIES']:
        if counters.get(k)!=0: failures.append('semantic_granularity_counter_not_zero:'+k)
    for st in stages:
        sid=st.get('stage_uid'); g=st.get('semantic_granularity_gate') or {}
        if g.get('mode')!='REQUIRED': failures.append('semantic_granularity_stage_gate_missing:'+str(sid))
        if g.get('terminal_unit_type')!=expected_units.get(sid): failures.append('semantic_granularity_terminal_unit_wrong:'+str(sid))
        if g.get('mixed_terminal_unit')!='BLOCK' or g.get('unresolved_container_unit')!='BLOCK': failures.append('semantic_granularity_stage_not_fail_closed:'+str(sid))
        for k in ['recursive_decomposition_required','parent_child_responsibility_conservation_required','downstream_universe_shrink_forbidden','later_stage_revalidation_required']:
            if g.get(k) is not True: failures.append(f'semantic_granularity_stage_rule_not_true:{sid}:{k}')
        if g.get('closure_requires_zero')!=['MIXED_TERMINAL_UNITS','UNRESOLVED_CONTAINER_UNITS','LOST_REQUIRED_RESPONSIBILITIES','DUPLICATE_REQUIRED_RESPONSIBILITIES']:
            failures.append('semantic_granularity_stage_closure_counters_invalid:'+str(sid))
    idxp=root/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'
    if not idxp.exists(): failures.append('construction_artifact_index_missing_for_semantic_granularity')
    else:
        idx=load(idxp); common=((idx.get('mandatory_common_normative_bundles') or {}).get('BUNDLE-GOV-COMMON-CORE') or {}).get('section_uids') or []
        if 'WEB-GOV-03-S052' not in common: failures.append('semantic_granularity_not_loaded_by_common_bundle')
        if 'WEB-GOV-03-S058' not in common: failures.append('closure_continuity_not_loaded_by_common_bundle')


    cinv=((d.get('cross_stage_invariants') or {}).get('closure_evidence_continuity') or {})
    if cinv.get('invariant_uid')!='GOV-INV-CLOSURE-EVIDENCE-CONTINUITY-001': failures.append('closure_continuity_invariant_missing')
    if cinv.get('normative_section_uid')!='WEB-GOV-03-S058': failures.append('closure_continuity_normative_section_wrong')
    if cinv.get('applies_to_stages')!=expected: failures.append('closure_continuity_not_all_stages')
    if cinv.get('closure_mutation_semantics')!='MERGE_APPEND_OR_EXPLICIT_SUPERSEDE': failures.append('closure_continuity_mutation_semantics_wrong')
    ua=cinv.get('unresolved_authority_identity') or {}
    if ua.get('canonical_tuple_fields')!=['gap_uid','authority_ref','disposition','authority_evidence_ref'] or ua.get('carry_forward_exact_tuple_required') is not True or ua.get('count_only_or_uid_only_validation')!='BLOCK': failures.append('closure_authority_identity_tuple_contract_wrong')
    tr=cinv.get('terminal_ci_receipt') or {}
    if tr.get('ledger_projection_required_fields')!=['provider','repository_or_project','head_sha','run_id','job_denominator','conclusion'] or tr.get('canonical_projection_required') is not True or tr.get('alias_field_substitution')!='BLOCK': failures.append('closure_terminal_receipt_projection_contract_wrong')
    if cinv.get('retroactive_predecessor_invalidation')!='FORBIDDEN' or cinv.get('established_predecessor_fact_deletion')!='BLOCK' or cinv.get('established_predecessor_fact_reversion')!='BLOCK': failures.append('closure_continuity_not_fail_closed')
    if cinv.get('current_ledger_synchronization_required') is not True or cinv.get('synchronization_drift')!='BLOCK': failures.append('closure_ledger_sync_not_fail_closed')
    tr=cinv.get('terminal_ci_receipt') or {}
    if tr.get('model')!='EXTERNAL_IMMUTABLE_RECEIPT' or tr.get('self_write_same_commit_run_identity')!='FORBIDDEN' or tr.get('materialization_and_terminal_receipt_are_distinct') is not True: failures.append('terminal_receipt_contract_invalid')
    for st in stages:
        g=st.get('closure_evidence_continuity_gate') or {}
        if g.get('mode')!='REQUIRED' or g.get('invariant_uid')!='GOV-INV-CLOSURE-EVIDENCE-CONTINUITY-001' or g.get('normative_section_uid')!='WEB-GOV-03-S058': failures.append('closure_continuity_stage_gate_missing:'+str(st.get('stage_uid')))

    top=d.get('topology') or {}
    if top.get('foundation_stages')!=expected[:4] or top.get('foundation_barrier_mode')!='PER_GOVERNED_UNIT': failures.append('foundation_barrier_invalid')
    if top.get('vertical_stages')!=expected[4:] or top.get('vertical_concurrency')!=1: failures.append('vertical_topology_invalid')
    if top.get('page_uid_sticky_from_stage')!='STAGE-05' or top.get('page_uid_sticky_through_stage')!='STAGE-11': failures.append('page_uid_sticky_contract_invalid')
    if any((x.get('scope_mode')=='ALL_REQUIRED_PAGES' for x in stages)): failures.append('all_required_pages_scope_mode_forbidden')
    if any(('ALL_REQUIRED_PAGES' in str(x.get('entry_gate') or '') or 'ALL_REQUIRED_PAGES' in str(x.get('exit_gate') or '') for x in stages)): failures.append('all_required_pages_stage_gate_forbidden')
    for x in stages:
        if x.get('stage_exit_scope_source')!='CURRENT_GOVERNED_UNIT_STAGE_REQUIRED_UNIVERSE_RECONCILIATION': failures.append('stage_exit_scope_not_current_governed_unit:'+str(x.get('stage_uid')))
        if x.get('unrelated_same_stage_units_may_block_current_unit_exit') is not False: failures.append('unrelated_same_stage_unit_block_not_forbidden:'+str(x.get('stage_uid')))
        if x.get('cross_unit_blocking_requires_explicit_required_dependency_edge') is not True: failures.append('cross_unit_dependency_edge_rule_missing:'+str(x.get('stage_uid')))
        if x.get('lifecycle_owner_granularity')!='PAGE_OR_SYSTEM_LOGIC_UNIT': failures.append('lifecycle_owner_granularity_invalid:'+str(x.get('stage_uid')))
    binds=d.get('delivery_step_bindings') or []
    nums=[x.get('step') for x in binds]
    if nums!=list(range(1,55)): failures.append('delivery_steps_not_exact_1_54')
    for x in binds:
        if x.get('operation_uid') not in all_ops: failures.append('delivery_step_operation_missing:'+str(x.get('step')))
        elif all_ops[x.get('operation_uid')]!=x.get('stage_uid'): failures.append('delivery_step_stage_mismatch:'+str(x.get('step')))
    if set(d.get('validation_modes') or [])!={'PRE_FORMAL_DEFINITION_AUDIT','STAGE_EXECUTION_VALIDATION','RELEASE_FINAL_VALIDATION'}: failures.append('validation_modes_invalid')
    return {'status':'PASS' if not failures else 'FAIL','stage_count':len(stages),'delivery_steps':len(binds),'operation_count':len(all_ops),'failures':failures}
if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
