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
    candidate=str(state.get('candidate',''))
    m=re.match(r'(v\d+\.\d+\.\d+)',candidate)
    current=m.group(1) if m else None
    if current!='v2.1.14': failures.append('candidate_revision_not_v214:'+str(current))
    contract=bp.get('current_test_evidence_sync_contract') or {}
    runner_contract=bp.get('test_runner_isolation_contract') or {}
    if runner_contract.get('required') is not True: failures.append('test_runner_isolation_contract_not_required')
    if runner_contract.get('mandatory_regression_runner')!='STANDALONE_SUBPROCESS_JSON': failures.append('test_runner_mode_wrong')
    if runner_contract.get('generic_pytest_collection_of_standalone_regressions')!='FORBIDDEN': failures.append('pytest_standalone_collection_not_forbidden')
    if runner_contract.get('collector_triggered_system_exit')!='BLOCK' or runner_contract.get('pytest_internal_error')!='BLOCK': failures.append('pytest_collection_fail_closed_policy_missing')
    if runner_contract.get('collection_result_is_acceptance_evidence') is not False: failures.append('pytest_collection_misclassified_as_acceptance_evidence')
    if runner_contract.get('mandatory_suite_denominator_source')!='SEMANTIC_AUTHORITY_BASELINE.mandatory_regression_assets' or runner_contract.get('hardcoded_historical_suite_count')!='BLOCK': failures.append('pytest_collection_denominator_authority_missing')
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
    if contract.get('historical_pass_substitution')!='BLOCK' or contract.get('evidence_result_denominator_drift')!='BLOCK' or contract.get('evidence_revision_drift')!='BLOCK': failures.append('evidence_sync_fail_closed_policy_missing')
    if contract.get('wrapper_timeout_evidence_status')!='BLOCKED_TOOL_TIMEOUT': failures.append('wrapper_timeout_evidence_status_missing')
    revs=[hp.get('governance_revision'),ref.get('governance_revision'),review.get('governance_revision'),bp.get('governance_revision')]
    if any(not str(x).startswith(current or '<none>') for x in revs): failures.append('current_evidence_revision_drift:'+str(revs))
    specs=sem.get('mandatory_regression_assets') or []
    for spec in specs:
        rel=spec.get('path') or ''
        fp=root/rel
        if not fp.exists(): failures.append('mandatory_regression_asset_missing_for_runner_contract:'+rel)
        elif not guard_marker or guard_marker not in fp.read_text(encoding='utf-8'): failures.append('standalone_pytest_isolation_guard_missing:'+rel)
    suite_count=len(specs)
    if suite_count!=len(specs) or suite_count<1: failures.append('mandatory_suite_denominator_invalid:'+str(suite_count))
    expected={Path(x.get('path','')).name:x for x in specs}
    req={'test_high_pressure_hardening.py':(25,25),'test_execution_load_guard.py':(14,14),'test_prefomal_stress_repairs.py':(21,21),'test_stage1_source_to_blueprint_minimal_control.py':(33,33),'test_v2_1_0_regressions.py':(12,12),'test_v2_1_0_post_v1_8_regressions.py':(6,6),'test_bugfix_regressions.py':(30,30),'test_v2_1_7_phase_authority_bugfix.py':(25,25),'test_v2_1_8_successor_evidence_sync_bugfix.py':(24,24),'test_v2_1_9_evidence_state_closure.py':(24,24),'test_v2_1_10_closure_evidence_continuity.py':(43,43),'test_v2_1_11_binding_authority_receipt_schema.py':(54,54),'test_v2_1_12_successor_state_evidence_parse.py':(60,60),'test_v2_1_13_stage_execution_invariants.py':(18,18),'test_v2_1_14_test_feedback_spec_evolution.py':(21,21),'test_v2_1_14_product_neutral_entity_lifecycle.py':(68,68)}
    for fn,(tot,pas) in req.items():
        s=expected.get(fn) or {}
        if s.get('expected_total')!=tot or s.get('expected_passed')!=pas: failures.append('mandatory_suite_denominator_drift:'+fn)
    rs=expected.get('test_reference_semantic_guard.py') or {}
    if (rs.get('expected_semantic_total'),rs.get('expected_semantic_passed'),rs.get('expected_fuzz_total'),rs.get('expected_fuzz_blocked'),rs.get('expected_escaped'))!=(28,28,46,46,0): failures.append('reference_semantic_denominator_drift')
    pe=state.get('preformal_execution') or {}; hr=hp.get('results') or {}; rr=ref.get('results') or {}
    exact={
      'mandatory_regression_matrix':f'{suite_count}/{suite_count} SUITES PASS','high_pressure_suite':'25/25 PASS','execution_governance_load':'14/14 PASS','multidirection_stress_repair':'21/21 PASS','stage1_minimal_control':'33/33 PASS','v2_1_0_inherited_regression':'12/12 PASS','post_v1_8_regression':'6/6 PASS','v2_1_6_cross_lifecycle_regression':'30/30 PASS','v2_1_7_phase_authority_regression':'25/25 PASS','v2_1_8_successor_evidence_sync_regression':'24/24 PASS','v2_1_9_evidence_state_closure_regression':'24/24 PASS','v2_1_10_closure_evidence_continuity_regression':'43/43 PASS','v2_1_11_binding_authority_receipt_schema_regression':'54/54 PASS','v2_1_12_successor_state_evidence_parse_regression':'60/60 PASS','v2_1_13_stage_execution_invariant_regression':'18/18 PASS','v2_1_14_test_feedback_spec_evolution_regression':'21/21 PASS','v2_1_14_product_neutral_entity_lifecycle_regression':'68/68 PASS'}
    for k,v in exact.items():
        if pe.get(k)!=v: failures.append('candidate_test_evidence_drift:'+k+':'+str(pe.get(k)))
        if hr.get(k)!=v: failures.append('high_pressure_evidence_drift:'+k+':'+str(hr.get(k)))
    for k in ['mandatory_regression_matrix','stage1_minimal_control','v2_1_6_cross_lifecycle_regression','v2_1_7_phase_authority_regression','v2_1_8_successor_evidence_sync_regression','v2_1_9_evidence_state_closure_regression','v2_1_10_closure_evidence_continuity_regression','v2_1_11_binding_authority_receipt_schema_regression','v2_1_12_successor_state_evidence_parse_regression','v2_1_13_stage_execution_invariant_regression','v2_1_14_test_feedback_spec_evolution_regression','v2_1_14_product_neutral_entity_lifecycle_regression']:
        if rr.get(k)!=exact[k]: failures.append('reference_evidence_drift:'+k+':'+str(rr.get(k)))
    if pe.get('reference_semantic_cases')!='28/28 PASS' or hr.get('reference_semantic_cases')!='28/28 PASS' or rr.get('reference_semantic_cases')!='28/28 PASS': failures.append('reference_semantic_case_result_drift')
    if pe.get('reference_semantic_fuzz')!='46/46 BLOCKED; 0 ESCAPED' or hr.get('reference_semantic_fuzz')!='46/46 BLOCKED; 0 ESCAPED' or rr.get('fuzz_total')!='46/46 BLOCKED; 0 ESCAPED': failures.append('reference_fuzz_result_drift')
    if pe.get('preformal_definition_audit')!='BLOCKED_TOOL_TIMEOUT': failures.append('candidate_preformal_wrapper_truth_drift')
    if pe.get('preformal_constituent_checks')!='19/19 PASS' or pe.get('preformal_total_constituents')!='20/20 PASS INCLUDING MANDATORY REGRESSION MATRIX CONSTITUENT' or pe.get('monolithic_wrapper_result')!='NOT_COMPLETED_TOOL_TIMEOUT': failures.append('candidate_preformal_constituent_evidence_drift')
    expected_wrapper='BLOCKED_TOOL_TIMEOUT; MONOLITHIC WRAPPER NOT COMPLETED'
    expected_constituents='19/19 PASS; MANDATORY REGRESSION MATRIX 17/17 SUITES PASS'
    if hr.get('preformal_global')!=expected_wrapper or rr.get('preformal_global')!=expected_wrapper: failures.append('formal_evidence_preformal_wrapper_truth_drift')
    if hr.get('preformal_constituent_checks')!=expected_constituents or rr.get('preformal_constituent_checks')!=expected_constituents: failures.append('formal_evidence_preformal_constituent_drift')
    mr=review.get('machine_review_plan') or []
    if len(mr)!=1 or mr[0].get('status')!='PASS' or mr[0].get('target_revision')!=current or mr[0].get('verification_method')!='MACHINE_RECOMPUTED_BY_VAL-GOV-032': failures.append('machine_review_not_current_pass')
    mp=review.get('machine_review_progress') or {}
    if (mp.get('required'),mp.get('approved'),mp.get('pending'),mp.get('percentage'))!=(1,1,0,100): failures.append('machine_review_progress_not_closed')
    # Human approval remains separate; if it claims approval, actual evidence must exist.
    hpgr=review.get('progress') or {}; current_results=review.get('current_results') or []
    if hpgr.get('approved',0)>0 and not current_results: failures.append('human_review_self_claim_without_evidence')
    return {'status':'PASS' if not failures else 'FAIL','current_revision':current,'mandatory_suite_count':suite_count,'failures':failures}
if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
