#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = HERE / 'apply_full_line_source_integrity_successor.py'
R2_SELF = HERE / 'apply_full_line_source_integrity_successor_r2.py'
R2_WORKFLOW = ROOT / '.github/workflows/full-line-source-integrity-successor-r2.yml'
OLD_WORKFLOW = ROOT / '.github/workflows/full-line-source-integrity-successor.yml'

spec = importlib.util.spec_from_file_location('full_line_successor_base', BASE)
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)

m.AUTH_UID = 'USR-DIRECTIVE-20260916-FULL-LINE-SOURCE-INTEGRITY-CLOSURE-R2'

_original_update_source_versions = m.update_source_versions
_original_fix_source_validators = m.fix_source_validators
_original_update_candidate_state = m.update_candidate_state
_original_append_source_defects = m.append_source_defects
_original_commit_validate_and_push = m.commit_validate_and_push


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def _save(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')


def update_source_versions_r2() -> None:
    _original_update_source_versions()

    # Every live 10_REGISTRY Current owner that declares package governance_revision
    # advances with the source successor. The immutable semantic baseline is creation-
    # identity evidence and is intentionally excluded. 11_EVIDENCE is never relabeled.
    for path in sorted((m.SOURCE / '10_REGISTRY').glob('*.yaml')):
        if path.name == 'SEMANTIC_AUTHORITY_BASELINE.yaml':
            continue
        data = _load(path)
        if 'governance_revision' in data:
            data['governance_revision'] = m.NEW_SOURCE_REV
            _save(path, data)

    bp_path = m.SOURCE / '10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'
    bp = _load(bp_path)
    contract = bp.setdefault('current_test_evidence_sync_contract', {})
    contract['predecessor_evidence_may_be_retained_as_history'] = True
    contract['predecessor_evidence_current_closure_credit'] = 'BLOCK'
    contract['fresh_successor_revalidation_required_after_revision_change'] = True
    contract['registered_predecessor_revision_identity_required'] = True
    _save(bp_path, bp)


def update_candidate_state_r2() -> None:
    _original_update_candidate_state()
    path = m.SOURCE / '11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'
    data = _load(path)
    data['fresh_revalidation'] = {
        'required': True,
        'current_source_revision': m.NEW_SOURCE_REV,
        'current_closure_credit': False,
        'predecessor_evidence_current_closure_credit': False,
        'embedded_preformal_execution_role': 'HISTORICAL_PREDECESSOR_EVIDENCE_ONLY',
        'predecessor_wrapper_result_role': 'HISTORICAL_PREDECESSOR_EVIDENCE_ONLY',
        'predecessor_evidence_revisions': {
            'high_pressure': 'v2.1.15-stage-execution-optimization',
            'reference_semantic': 'v2.1.15-stage-execution-optimization',
            'machine_review_target_revision': 'v2.1.15',
        },
        'persisted_head_full_line_required': True,
        'historical_evidence_may_close_successor': False,
    }
    _save(path, data)


def _write_successor_aware_current_evidence_validator() -> None:
    path = m.SOURCE / '09_TESTS/governance/validate_current_test_evidence.py'
    path.write_text(r'''#!/usr/bin/env python3
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
    if not current or current!=root_current: failures.append('candidate_revision_not_current_source:'+str(current)+':'+str(root_current))
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
    specs=sem.get('mandatory_regression_assets') or []
    for spec in specs:
        rel=spec.get('path') or ''
        fp=root/rel
        if not fp.exists(): failures.append('mandatory_regression_asset_missing_for_runner_contract:'+rel)
        elif not guard_marker or guard_marker not in fp.read_text(encoding='utf-8'): failures.append('standalone_pytest_isolation_guard_missing:'+rel)
    suite_count=len(specs)
    if suite_count<1: failures.append('mandatory_suite_denominator_invalid:'+str(suite_count))
    expected={Path(x.get('path','')).name:x for x in specs}
    req={'test_high_pressure_hardening.py':(25,25),'test_execution_load_guard.py':(14,14),'test_prefomal_stress_repairs.py':(21,21),'test_stage1_source_to_blueprint_minimal_control.py':(33,33),'test_v2_1_0_regressions.py':(12,12),'test_v2_1_0_post_v1_8_regressions.py':(6,6),'test_bugfix_regressions.py':(30,30),'test_v2_1_7_phase_authority_bugfix.py':(25,25),'test_v2_1_8_successor_evidence_sync_bugfix.py':(24,24),'test_v2_1_9_evidence_state_closure.py':(24,24),'test_v2_1_10_closure_evidence_continuity.py':(43,43),'test_v2_1_11_binding_authority_receipt_schema.py':(54,54),'test_v2_1_12_successor_state_evidence_parse.py':(60,60),'test_v2_1_13_stage_execution_invariants.py':(26,26),'test_v2_1_14_test_feedback_spec_evolution.py':(21,21),'test_v2_1_14_product_neutral_entity_lifecycle.py':(68,68)}
    for fn,(tot,pas) in req.items():
        s=expected.get(fn) or {}
        if s.get('expected_total')!=tot or s.get('expected_passed')!=pas: failures.append('mandatory_suite_denominator_drift:'+fn)
    rs=expected.get('test_reference_semantic_guard.py') or {}
    if (rs.get('expected_semantic_total'),rs.get('expected_semantic_passed'),rs.get('expected_fuzz_total'),rs.get('expected_fuzz_blocked'),rs.get('expected_escaped'))!=(28,28,46,46,0): failures.append('reference_semantic_denominator_drift')
    pe=state.get('preformal_execution') or {}; hr=hp.get('results') or {}; rr=ref.get('results') or {}
    exact={
      'mandatory_regression_matrix':f'{suite_count}/{suite_count} SUITES PASS','high_pressure_suite':'25/25 PASS','execution_governance_load':'14/14 PASS','multidirection_stress_repair':'21/21 PASS','stage1_minimal_control':'33/33 PASS','v2_1_0_inherited_regression':'12/12 PASS','post_v1_8_regression':'6/6 PASS','v2_1_6_cross_lifecycle_regression':'30/30 PASS','v2_1_7_phase_authority_regression':'25/25 PASS','v2_1_8_successor_evidence_sync_regression':'24/24 PASS','v2_1_9_evidence_state_closure_regression':'24/24 PASS','v2_1_10_closure_evidence_continuity_regression':'43/43 PASS','v2_1_11_binding_authority_receipt_schema_regression':'54/54 PASS','v2_1_12_successor_state_evidence_parse_regression':'60/60 PASS','v2_1_13_stage_execution_invariant_regression':'26/26 PASS','v2_1_14_test_feedback_spec_evolution_regression':'21/21 PASS','v2_1_14_product_neutral_entity_lifecycle_regression':'68/68 PASS'}
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
    expected_review_target=(fresh.get('predecessor_evidence_revisions') or {}).get('machine_review_target_revision') if fresh_required else current
    if len(mr)!=1 or mr[0].get('status')!='PASS' or mr[0].get('target_revision')!=expected_review_target or mr[0].get('verification_method')!='MACHINE_RECOMPUTED_BY_VAL-GOV-032': failures.append('machine_review_identity_not_exact')
    if fresh_required and (review.get('machine_review_policy') or {}).get('historical_revision_evidence')!='REVERIFY_REQUIRED': failures.append('machine_review_historical_reverify_policy_missing')
    mp=review.get('machine_review_progress') or {}
    if (mp.get('required'),mp.get('approved'),mp.get('pending'),mp.get('percentage'))!=(1,1,0,100): failures.append('machine_review_progress_not_closed')
    hpgr=review.get('progress') or {}; current_results=review.get('current_results') or []
    if hpgr.get('approved',0)>0 and not current_results: failures.append('human_review_self_claim_without_evidence')
    return {'status':'PASS' if not failures else 'FAIL','current_revision':current,'current_source_revision':root_revision,'fresh_revalidation_required':fresh_required,'mandatory_suite_count':suite_count,'failures':failures}
if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
''', encoding='utf-8')


def _update_regression_fixtures() -> None:
    p10 = m.SOURCE / '09_TESTS/governance/test_v2_1_10_closure_evidence_continuity.py'
    body = p10.read_text(encoding='utf-8')
    old = "mutate_text('normative_self_reference_rule_removal_blocked','12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',lambda t:t.replace('infinite self-reference loop','self reference'))"
    new = "mutate_text('normative_self_reference_rule_removal_blocked','12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',lambda t:t.replace('Materialization evidence and terminal CI receipt are separate identities.','Materialization and receipt evidence exist.'))"
    if body.count(old) != 1: raise RuntimeError('V210_FIXTURE_PATCH_POINT_MISSING')
    p10.write_text(body.replace(old, new, 1), encoding='utf-8')

    p11 = m.SOURCE / '09_TESTS/governance/test_v2_1_11_binding_authority_receipt_schema.py'
    body = p11.read_text(encoding='utf-8')
    old1 = "mutate_text('normative_authority_tuple_text_removal_blocked','12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',lambda t:t.replace('canonical tuple `gap_uid`, `authority_ref`, `disposition`, and `authority_evidence_ref`','canonical identity'))"
    new1 = "mutate_text('normative_authority_tuple_text_removal_blocked','12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',lambda t:t.replace('Unresolved Authority continuity is exact, not count-only.','Unresolved Authority continuity may be count-only.'))"
    old2 = "mutate_text('normative_receipt_schema_text_removal_blocked','12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',lambda t:t.replace('canonical six fields `provider`, `repository_or_project`, `head_sha`, `run_id`, `job_denominator`, and `conclusion`','canonical fields'))"
    new2 = "mutate_text('normative_receipt_schema_text_removal_blocked','12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',lambda t:t.replace('provider, repository/project, head SHA, evidence-cycle identity, job denominator, and conclusion','provider and conclusion'))"
    if body.count(old1) != 1 or body.count(old2) != 1: raise RuntimeError('V211_FIXTURE_PATCH_POINT_MISSING')
    p11.write_text(body.replace(old1, new1, 1).replace(old2, new2, 1), encoding='utf-8')


def fix_source_validators_r2() -> None:
    _original_fix_source_validators()
    _write_successor_aware_current_evidence_validator()
    _update_regression_fixtures()


def append_source_defects_r2() -> None:
    _original_append_source_defects()
    path = m.SOURCE / '11_EVIDENCE/audit/GOVERNANCE_DEFECT_LEDGER.yaml'
    data = _load(path)
    defects = data.setdefault('defects', [])
    uid = 'GOV-DEFECT-V221-CURRENT-EVIDENCE-SUCCESSOR-AWARENESS'
    if not any(isinstance(x,dict) and x.get('defect_uid')==uid for x in defects):
        defects.append({
            'defect_uid': uid,
            'status': 'REMEDIATED_LOCAL_PREFORMAL_PERSISTED_HEAD_REVERIFY_REQUIRED',
            'scope': 'CURRENT_TEST_EVIDENCE_SYNCHRONIZATION',
            'reproduced_problem': 'The Current Test Evidence validator required all evidence artifacts and machine-review targets to equal v2.1.15, so a legal new source successor could not retain predecessor evidence truthfully while entering fresh revalidation.',
            'correction': 'Bind Current candidate identity to the Root Manifest revision, register exact predecessor evidence revisions as history-only with zero successor closure credit, require fresh persisted-head Full-Line revalidation, and preserve all mandatory suite denominators.',
        })
    _save(path, data)


def commit_validate_and_push_r2() -> None:
    # The R1 builder/auth attempt failed before mutation and remains historical setup evidence.
    # A successful R2 successor removes every one-shot builder/workflow implementation file.
    for path in (BASE, OLD_WORKFLOW):
        if path.exists():
            path.unlink()
    m.BUILDER_PATH = R2_SELF
    m.WORKFLOW_PATH = R2_WORKFLOW
    _original_commit_validate_and_push()


m.update_source_versions = update_source_versions_r2
m.fix_source_validators = fix_source_validators_r2
m.update_candidate_state = update_candidate_state_r2
m.append_source_defects = append_source_defects_r2
m.commit_validate_and_push = commit_validate_and_push_r2

if __name__ == '__main__':
    m.main()
