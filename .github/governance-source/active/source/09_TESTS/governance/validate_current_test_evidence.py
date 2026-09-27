#!/usr/bin/env python3
from pathlib import Path
import json,yaml
ROOT=Path(__file__).resolve().parents[2]

def load_yaml(path):
    return yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}

def validate(root=ROOT):
    root=Path(root); failures=[]
    sem=load_yaml(root/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml')
    review=load_yaml(root/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml')
    bp=load_yaml(root/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml')
    root_manifest=load_yaml(root/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml')
    repo=root.parents[3]
    reg_path=repo/'governance/specifications/REGISTRY.yaml'
    if not reg_path.is_file():
        return {'status':'FAIL','failures':['current_registry_missing']}
    reg=load_yaml(reg_path)
    ident=reg.get('governance_identity') or {}
    vc=reg.get('candidate_validation_contract') or {}

    retired=[
      '11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml',
      '11_EVIDENCE/audit/HIGH_PRESSURE_HARDENING_RESULT.yaml',
      '11_EVIDENCE/audit/REFERENCE_SEMANTIC_REPAIR_RESULT.yaml',
      '11_EVIDENCE/audit/GITHUB_REPLAY_CLOSURE_RESULT.yaml',
      '11_EVIDENCE/audit/GOVERNANCE_DEFECT_LEDGER.yaml',
    ]
    present=[x for x in retired if (root/x).exists()]
    if present:
        failures.append('retired_predecessor_evidence_reappeared_as_current:'+repr(present))

    if reg.get('registry_role')!='GOVERNANCE_REVISION_CANDIDATE_ENTRYPOINT' or reg.get('status')!='ACTIVE_SINGLE_BRANCH_VALIDATION':
        failures.append('current_registry_candidate_role_invalid')
    if ident.get('status')!='CANDIDATE' or ident.get('released_immutable_identity') is not False:
        failures.append('current_candidate_identity_invalid')
    if ident.get('identity_authority')!='governance/specifications/REGISTRY.yaml':
        failures.append('current_candidate_identity_authority_drift')
    for key in ('exact_candidate_head_required','required_workflows_run_on_every_candidate_push','live_branch_head_must_equal_validation_head','live_branch_head_recheck_after_evidence_validation_required','formal_promotion_requires_all_required_workflows_exact_head_success'):
        if vc.get(key) is not True:
            failures.append('exact_head_validation_contract_missing:'+key)
    if vc.get('prior_head_workflow_result_may_credit_successor_head') is not False or vc.get('zero_required_workflow_runs_on_successor_head')!='BLOCK':
        failures.append('successor_head_credit_isolation_incomplete')

    contract=bp.get('current_test_evidence_sync_contract') or {}
    runner=bp.get('test_runner_isolation_contract') or {}
    required_true=[
      'required','current_revision_only','mandatory_suite_denominator_must_equal_semantic_baseline',
      'preformal_check_denominator_must_equal_runtime_validator','review_machine_sync_required',
      'human_formal_approval_must_not_be_auto_claimed','monolithic_preformal_wrapper_pass_requires_successful_wrapper_result',
      'constituent_success_must_not_substitute_monolithic_wrapper_pass','local_component_verification_may_be_recorded_separately',
      'exact_head_required_workflow_receipts_required','fresh_successor_revalidation_required_after_revision_change',
      'denominator_change_requires_snapshot_and_reverify'
    ]
    for key in required_true:
        if contract.get(key) is not True:
            failures.append('evidence_sync_contract_not_enforced:'+key)
    if contract.get('current_validation_truth_source')!='EXACT_HEAD_REQUIRED_WORKFLOW_RECEIPTS':
        failures.append('current_validation_truth_source_invalid')
    if contract.get('retired_candidate_state_required_for_current_validation') is not False or contract.get('retired_github_replay_closure_required_for_current_validation') is not False:
        failures.append('retired_evidence_still_required_for_current_validation')
    if contract.get('historical_predecessor_denominator_role')!='HISTORICAL_REFERENCE_ONLY' or contract.get('predecessor_evidence_current_closure_credit')!='BLOCK':
        failures.append('historical_predecessor_credit_isolation_incomplete')
    if contract.get('current_mandatory_denominator_source')!='SEMANTIC_AUTHORITY_BASELINE.mandatory_regression_assets':
        failures.append('current_denominator_single_authority_missing')
    if contract.get('hardcoded_historical_suite_denominator_in_consumer')!='BLOCK':
        failures.append('hardcoded_historical_denominator_not_blocked')
    if contract.get('historical_pass_substitution')!='BLOCK' or contract.get('evidence_result_denominator_drift')!='BLOCK' or contract.get('evidence_revision_drift')!='BLOCK':
        failures.append('evidence_sync_fail_closed_policy_missing')

    if runner.get('required') is not True or runner.get('mandatory_regression_runner')!='STANDALONE_SUBPROCESS_JSON':
        failures.append('test_runner_contract_invalid')
    if runner.get('generic_pytest_collection_of_standalone_regressions')!='FORBIDDEN':
        failures.append('pytest_standalone_collection_not_forbidden')
    if runner.get('mandatory_suite_denominator_source')!='SEMANTIC_AUTHORITY_BASELINE.mandatory_regression_assets' or runner.get('hardcoded_historical_suite_count')!='BLOCK':
        failures.append('test_runner_denominator_authority_invalid')
    pytest_cfg=root/str(runner.get('pytest_config_path') or '')
    pytest_contract_test=root/str(runner.get('pytest_contract_test_path') or '')
    if not pytest_cfg.is_file() or 'python_files = test_pytest_collection_contract.py' not in pytest_cfg.read_text(encoding='utf-8'):
        failures.append('pytest_collection_boundary_missing')
    if not pytest_contract_test.is_file():
        failures.append('pytest_contract_test_missing')
    marker=str(runner.get('standalone_collection_guard_marker') or '')

    specs=sem.get('mandatory_regression_assets') or []
    if not isinstance(specs,list) or not specs:
        failures.append('mandatory_suite_denominator_invalid')
        specs=[]
    for spec in specs:
        rel=str(spec.get('path') or '')
        fp=root/rel
        if not fp.is_file():
            failures.append('mandatory_regression_asset_missing:'+rel)
            continue
        if not marker or marker not in fp.read_text(encoding='utf-8'):
            failures.append('standalone_pytest_isolation_guard_missing:'+rel)
        if 'expected_total' in spec:
            if not isinstance(spec.get('expected_total'),int) or spec.get('expected_total')<1 or spec.get('expected_passed')!=spec.get('expected_total'):
                failures.append('mandatory_suite_denominator_invalid:'+rel)
        else:
            ks=('expected_semantic_total','expected_semantic_passed','expected_fuzz_total','expected_fuzz_blocked','expected_escaped')
            if any(k not in spec for k in ks):
                failures.append('mandatory_suite_semantic_denominator_incomplete:'+rel)

    human=review.get('required_review_plan') or []
    if len(human)!=1 or human[0].get('status')!='PENDING' or (review.get('progress') or {}).get('approved')!=0:
        failures.append('human_formal_review_state_invalid')
    if review.get('governance_revision')!=root_manifest.get('governance_revision') or bp.get('governance_revision')!=root_manifest.get('governance_revision'):
        failures.append('current_source_revision_projection_drift')

    return {
      'status':'PASS' if not failures else 'FAIL',
      'current_source_revision':root_manifest.get('governance_revision'),
      'current_candidate_uid':ident.get('governance_uid'),
      'current_mandatory_suite_count':len(specs),
      'current_validation_truth_source':contract.get('current_validation_truth_source'),
      'retired_evidence_present':present,
      'failures':failures
    }

if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
