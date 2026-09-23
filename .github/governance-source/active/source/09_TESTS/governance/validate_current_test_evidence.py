#!/usr/bin/env python3
from pathlib import Path
import re,yaml,json
ROOT=Path(__file__).resolve().parents[2]
def load(rel): return yaml.safe_load((ROOT/rel).read_text(encoding='utf-8')) or {}
def validate(root=ROOT):
    failures=[]
    def L(rel): return yaml.safe_load((root/rel).read_text(encoding='utf-8')) or {}
    state=L('11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml')
    sem=L('10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml')
    hp=L('11_EVIDENCE/audit/HIGH_PRESSURE_HARDENING_RESULT.yaml')
    ref=L('11_EVIDENCE/audit/REFERENCE_SEMANTIC_REPAIR_RESULT.yaml')
    review=L('10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml')
    bp=L('10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml')
    root_manifest=L('10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml')
    candidate=str(state.get('candidate',''))
    m=re.match(r'(v\d+\.\d+\.\d+)',candidate)
    current=m.group(1) if m else None
    root_revision=str(root_manifest.get('governance_revision') or '')
    rm=re.match(r'(v\d+\.\d+\.\d+)',root_revision)
    root_current=rm.group(1) if rm else None
    if not current or current!=root_current:
        failures.append('candidate_revision_not_current_source:'+str(current)+':'+str(root_current))

    fresh=state.get('fresh_revalidation') or {}
    fresh_required=fresh.get('required') is True
    if fresh_required:
        if fresh.get('current_source_revision')!=root_revision: failures.append('fresh_revalidation_source_revision_drift')
        if fresh.get('current_closure_credit') is not False: failures.append('fresh_revalidation_current_closure_credit_not_false')
        if fresh.get('predecessor_evidence_current_closure_credit') is not False: failures.append('predecessor_evidence_current_closure_credit_not_false')
        if fresh.get('embedded_preformal_execution_role')!='HISTORICAL_PREDECESSOR_EVIDENCE_ONLY': failures.append('embedded_preformal_execution_role_invalid')
        if fresh.get('predecessor_wrapper_result_role')!='HISTORICAL_PREDECESSOR_EVIDENCE_ONLY': failures.append('predecessor_wrapper_result_role_invalid')
        if fresh.get('persisted_head_full_line_required') is not True: failures.append('persisted_head_full_line_not_required')
        if fresh.get('historical_evidence_may_close_successor') is not False: failures.append('historical_evidence_may_close_successor')

    contract=bp.get('current_test_evidence_sync_contract') or {}
    runner_contract=bp.get('test_runner_isolation_contract') or {}
    if runner_contract.get('required') is not True: failures.append('test_runner_isolation_contract_not_required')
    if runner_contract.get('mandatory_regression_runner')!='STANDALONE_SUBPROCESS_JSON': failures.append('test_runner_mode_wrong')
    if runner_contract.get('generic_pytest_collection_of_standalone_regressions')!='FORBIDDEN': failures.append('pytest_standalone_collection_not_forbidden')
    if runner_contract.get('collector_triggered_system_exit')!='BLOCK' or runner_contract.get('pytest_internal_error')!='BLOCK': failures.append('pytest_collection_fail_closed_policy_missing')
    if runner_contract.get('collection_result_is_acceptance_evidence') is not False: failures.append('pytest_collection_misclassified_as_acceptance_evidence')
    if runner_contract.get('mandatory_suite_denominator_source')!='SEMANTIC_AUTHORITY_BASELINE.mandatory_regression_assets' or runner_contract.get('hardcoded_historical_suite_count')!='BLOCK':
        failures.append('pytest_collection_denominator_authority_missing')
    if contract.get('current_mandatory_denominator_source')!='SEMANTIC_AUTHORITY_BASELINE.mandatory_regression_assets':
        failures.append('current_denominator_single_authority_missing')
    if contract.get('predecessor_evidence_denominator_source')!='GOVERNANCE_CANDIDATE_STATE.fresh_revalidation.predecessor_mandatory_regression_assets':
        failures.append('predecessor_denominator_snapshot_authority_missing')
    if contract.get('hardcoded_historical_suite_denominator_in_consumer')!='BLOCK':
        failures.append('hardcoded_historical_denominator_not_blocked')
    if contract.get('denominator_change_requires_snapshot_and_reverify') is not True:
        failures.append('denominator_change_snapshot_reverify_not_required')

    pytest_cfg=root/str(runner_contract.get('pytest_config_path') or '')
    pytest_contract_test=root/str(runner_contract.get('pytest_contract_test_path') or '')
    if not pytest_cfg.exists(): failures.append('pytest_config_missing')
    else:
        cfg_text=pytest_cfg.read_text(encoding='utf-8')
        if 'python_files = test_pytest_collection_contract.py' not in cfg_text: failures.append('pytest_collection_boundary_missing')
    if not pytest_contract_test.exists(): failures.append('pytest_contract_test_missing')
    guard_marker=str(runner_contract.get('standalone_collection_guard_marker') or '')

    required_true=['required','current_revision_only','mandatory_suite_denominator_must_equal_semantic_baseline','preformal_check_denominator_must_equal_runtime_validator','review_machine_sync_required','human_formal_approval_must_not_be_auto_claimed','monolithic_preformal_wrapper_pass_requires_successful_wrapper_result','constituent_success_must_not_substitute_monolithic_wrapper_pass','local_component_verification_may_be_recorded_separately']
    for k in required_true:
        if contract.get(k) is not True: failures.append('evidence_sync_contract_not_enforced:'+k)
    if contract.get('historical_pass_substitution')!='BLOCK' or contract.get('evidence_result_denominator_drift')!='BLOCK' or contract.get('evidence_revision_drift')!='BLOCK':
        failures.append('evidence_sync_fail_closed_policy_missing')
    if contract.get('wrapper_timeout_evidence_status')!='BLOCKED_TOOL_TIMEOUT':
        failures.append('wrapper_timeout_evidence_status_missing')

    if fresh_required:
        if contract.get('predecessor_evidence_may_be_retained_as_history') is not True: failures.append('predecessor_evidence_history_retention_not_enabled')
        if contract.get('predecessor_evidence_current_closure_credit')!='BLOCK': failures.append('predecessor_evidence_closure_credit_not_blocked')
        if contract.get('fresh_successor_revalidation_required_after_revision_change') is not True: failures.append('fresh_successor_revalidation_not_required')
        if contract.get('registered_predecessor_revision_identity_required') is not True: failures.append('registered_predecessor_identity_not_required')
        pred=fresh.get('predecessor_evidence_revisions') or {}
        if hp.get('governance_revision')!=pred.get('high_pressure'): failures.append('high_pressure_predecessor_revision_drift:'+str(hp.get('governance_revision')))
        if ref.get('governance_revision')!=pred.get('reference_semantic'): failures.append('reference_predecessor_revision_drift:'+str(ref.get('governance_revision')))
        if review.get('governance_revision')!=root_revision: failures.append('review_registry_revision_drift:'+str(review.get('governance_revision')))
        if bp.get('governance_revision')!=root_revision: failures.append('acceptance_blueprint_revision_drift:'+str(bp.get('governance_revision')))
    else:
        revs=[hp.get('governance_revision'),ref.get('governance_revision'),review.get('governance_revision'),bp.get('governance_revision')]
        if any(not str(x).startswith(current or '<none>') for x in revs): failures.append('current_evidence_revision_drift:'+str(revs))

    current_specs=sem.get('mandatory_regression_assets') or []
    if not current_specs:
        failures.append('mandatory_suite_denominator_invalid:0')
    for spec in current_specs:
        rel=spec.get('path') or ''
        fp=root/rel
        if not fp.exists(): failures.append('mandatory_regression_asset_missing_for_runner_contract:'+rel)
        elif not guard_marker or guard_marker not in fp.read_text(encoding='utf-8'): failures.append('standalone_pytest_isolation_guard_missing:'+rel)
        if 'expected_total' in spec:
            if not isinstance(spec.get('expected_total'),int) or spec.get('expected_total')<1 or spec.get('expected_passed')!=spec.get('expected_total'):
                failures.append('mandatory_suite_current_denominator_invalid:'+rel)
        else:
            ks=('expected_semantic_total','expected_semantic_passed','expected_fuzz_total','expected_fuzz_blocked','expected_escaped')
            if any(k not in spec for k in ks): failures.append('mandatory_suite_current_semantic_denominator_incomplete:'+rel)

    evidence_specs=fresh.get('predecessor_mandatory_regression_assets') if fresh_required else current_specs
    if not isinstance(evidence_specs,list) or not evidence_specs:
        failures.append('predecessor_mandatory_regression_denominator_snapshot_missing' if fresh_required else 'current_mandatory_regression_denominator_missing')
        evidence_specs=[]
    expected={Path(x.get('path','')).name:x for x in evidence_specs}
    current_expected={Path(x.get('path','')).name:x for x in current_specs}
    if fresh_required:
        changed=[n for n in expected if n in current_expected and expected[n]!=current_expected[n]]
        added=sorted(set(current_expected)-set(expected))
        removed=sorted(set(expected)-set(current_expected))
        if not changed and not added and not removed:
            failures.append('fresh_revalidation_denominator_change_not_recorded')
    suite_count=len(evidence_specs)

    result_key_to_suite={
      'high_pressure_suite':'test_high_pressure_hardening.py',
      'execution_governance_load':'test_execution_load_guard.py',
      'multidirection_stress_repair':'test_prefomal_stress_repairs.py',
      'stage1_minimal_control':'test_stage1_source_to_blueprint_minimal_control.py',
      'v2_1_0_inherited_regression':'test_v2_1_0_regressions.py',
      'post_v1_8_regression':'test_v2_1_0_post_v1_8_regressions.py',
      'v2_1_6_cross_lifecycle_regression':'test_bugfix_regressions.py',
      'v2_1_7_phase_authority_regression':'test_v2_1_7_phase_authority_bugfix.py',
      'v2_1_8_successor_evidence_sync_regression':'test_v2_1_8_successor_evidence_sync_bugfix.py',
      'v2_1_9_evidence_state_closure_regression':'test_v2_1_9_evidence_state_closure.py',
      'v2_1_10_closure_evidence_continuity_regression':'test_v2_1_10_closure_evidence_continuity.py',
      'v2_1_11_binding_authority_receipt_schema_regression':'test_v2_1_11_binding_authority_receipt_schema.py',
      'v2_1_12_successor_state_evidence_parse_regression':'test_v2_1_12_successor_state_evidence_parse.py',
      'v2_1_13_stage_execution_invariant_regression':'test_v2_1_13_stage_execution_invariants.py',
      'v2_1_14_test_feedback_spec_evolution_regression':'test_v2_1_14_test_feedback_spec_evolution.py',
      'v2_1_14_product_neutral_entity_lifecycle_regression':'test_v2_1_14_product_neutral_entity_lifecycle.py'
    }
    exact={}
    for key,filename in result_key_to_suite.items():
        spec=expected.get(filename) or {}
        if not isinstance(spec.get('expected_total'),int) or spec.get('expected_passed')!=spec.get('expected_total'):
            failures.append('evidence_denominator_snapshot_invalid:'+filename)
            continue
        exact[key]=f"{spec['expected_total']}/{spec['expected_passed']} PASS"
    exact['mandatory_regression_matrix']=f'{suite_count}/{suite_count} SUITES PASS'

    pe=state.get('preformal_execution') or {}
    hr=hp.get('results') or {}
    rr=ref.get('results') or {}
    for k,v in exact.items():
        if pe.get(k)!=v: failures.append('candidate_test_evidence_drift:'+k+':'+str(pe.get(k)))
        if hr.get(k)!=v: failures.append('high_pressure_evidence_drift:'+k+':'+str(hr.get(k)))
    reference_only_keys=set(exact)-{'high_pressure_suite','execution_governance_load'}
    for k in reference_only_keys:
        if rr.get(k)!=exact[k]: failures.append('reference_evidence_drift:'+k+':'+str(rr.get(k)))

    rs=expected.get('test_reference_semantic_guard.py') or {}
    sem_label=f"{rs.get('expected_semantic_total')}/{rs.get('expected_semantic_passed')} PASS"
    fuzz_label=f"{rs.get('expected_fuzz_total')}/{rs.get('expected_fuzz_blocked')} BLOCKED; {rs.get('expected_escaped')} ESCAPED"
    if pe.get('reference_semantic_cases')!=sem_label or hr.get('reference_semantic_cases')!=sem_label or rr.get('reference_semantic_cases')!=sem_label:
        failures.append('reference_semantic_case_result_drift')
    if pe.get('reference_semantic_fuzz')!=fuzz_label or hr.get('reference_semantic_fuzz')!=fuzz_label or rr.get('fuzz_total')!=fuzz_label:
        failures.append('reference_fuzz_result_drift')

    if pe.get('preformal_definition_audit')!='BLOCKED_TOOL_TIMEOUT': failures.append('candidate_preformal_wrapper_truth_drift')
    if pe.get('preformal_constituent_checks')!='19/19 PASS' or pe.get('preformal_total_constituents')!='20/20 PASS INCLUDING MANDATORY REGRESSION MATRIX CONSTITUENT' or pe.get('monolithic_wrapper_result')!='NOT_COMPLETED_TOOL_TIMEOUT':
        failures.append('candidate_preformal_constituent_evidence_drift')
    expected_wrapper='BLOCKED_TOOL_TIMEOUT; MONOLITHIC WRAPPER NOT COMPLETED'
    expected_constituents=f'19/19 PASS; MANDATORY REGRESSION MATRIX {suite_count}/{suite_count} SUITES PASS'
    if hr.get('preformal_global')!=expected_wrapper or rr.get('preformal_global')!=expected_wrapper:
        failures.append('formal_evidence_preformal_wrapper_truth_drift')
    if hr.get('preformal_constituent_checks')!=expected_constituents or rr.get('preformal_constituent_checks')!=expected_constituents:
        failures.append('formal_evidence_preformal_constituent_drift')

    mr=review.get('machine_review_plan') or []
    expected_review_target=(fresh.get('predecessor_evidence_revisions') or {}).get('machine_review_target_revision') if fresh_required else current
    if len(mr)!=1 or mr[0].get('status')!='PASS' or mr[0].get('target_revision')!=expected_review_target or mr[0].get('verification_method')!='MACHINE_RECOMPUTED_BY_VAL-GOV-032':
        failures.append('machine_review_identity_not_exact')
    if fresh_required and (review.get('machine_review_policy') or {}).get('historical_revision_evidence')!='REVERIFY_REQUIRED':
        failures.append('machine_review_historical_reverify_policy_missing')
    mp=review.get('machine_review_progress') or {}
    if (mp.get('required'),mp.get('approved'),mp.get('pending'),mp.get('percentage'))!=(1,1,0,100):
        failures.append('machine_review_progress_not_closed')
    hpgr=review.get('progress') or {}
    current_results=review.get('current_results') or []
    if hpgr.get('approved',0)>0 and not current_results:
        failures.append('human_review_self_claim_without_evidence')
    return {
      'status':'PASS' if not failures else 'FAIL',
      'current_revision':current,
      'current_source_revision':root_revision,
      'fresh_revalidation_required':fresh_required,
      'current_mandatory_suite_count':len(current_specs),
      'historical_evidence_suite_count':suite_count,
      'failures':failures
    }
if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
