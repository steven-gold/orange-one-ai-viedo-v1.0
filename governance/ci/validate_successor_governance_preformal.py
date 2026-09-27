#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
sys.path.insert(0,str(ROOT/'governance/ci'))
from governance_resolver import resolve as resolve_governance
from source_package_successor_admission import validate_source_successor


def load_yaml(path:Path)->dict:
    value=yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(value,dict):
        raise RuntimeError('MAPPING_REQUIRED:'+str(path))
    return value


def candidate_identity_check()->dict:
    failures=[]
    resolved=resolve_governance()
    if resolved.get('governance_role')!='GOVERNANCE_REVISION_CANDIDATE':
        failures.append('NOT_GOVERNANCE_REVISION_CANDIDATE')
    if resolved.get('governance_release_state')!='CANDIDATE_NOT_PROMOTED':
        failures.append('CANDIDATE_RELEASE_STATE_DRIFT')
    if resolved.get('released_current_authority') is not False:
        failures.append('CANDIDATE_RELEASE_AUTHORITY_LEAK')
    retired=[
      SOURCE/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml',
      SOURCE/'11_EVIDENCE/audit/GITHUB_REPLAY_CLOSURE_RESULT.yaml',
      SOURCE/'11_EVIDENCE/audit/GOVERNANCE_DEFECT_LEDGER.yaml',
      SOURCE/'11_EVIDENCE/audit/HIGH_PRESSURE_HARDENING_RESULT.yaml',
      SOURCE/'11_EVIDENCE/audit/REFERENCE_SEMANTIC_REPAIR_RESULT.yaml',
    ]
    present=[p.relative_to(SOURCE).as_posix() for p in retired if p.exists()]
    if present:
        failures.append('RETIRED_PREDECESSOR_STATE_REAPPEARED_AS_LIVE_SOURCE:'+repr(present))
    return {
      'check_id':'current_candidate_identity',
      'status':'PASS' if not failures else 'FAIL',
      'current_truth_source':'governance/specifications/REGISTRY.yaml',
      'retired_predecessor_state_live_count':len(present),
      'failures':failures,
    }


def exact_head_validation_contract_check(registry:dict)->dict:
    failures=[]
    vc=registry.get('candidate_validation_contract') or {}
    expected_true=(
      'exact_candidate_head_required','required_workflows_run_on_every_candidate_push',
      'live_branch_head_must_equal_validation_head','live_branch_head_recheck_after_evidence_validation_required',
      'formal_promotion_requires_all_required_workflows_exact_head_success',
      'formal_promotion_requires_independent_auditor_evidence',
      'source_package_successor_required','source_package_successor_internal_exact_head_success_required',
      'source_package_successor_live_head_must_equal_receipt_head','source_package_successor_live_head_recheck_required',
      'source_package_successor_external_trust_required_for_promotion','source_package_successor_unsigned_blocks_promotion',
      'source_internal_pass_may_satisfy_candidate_validation_without_promotion_credit',
      'source_package_successor_workflow_identity_requires_name_path_allowed_event_branch_head',
    )
    for key in expected_true:
        if vc.get(key) is not True:
            failures.append('CANDIDATE_VALIDATION_FLAG_MISSING:'+key)
    if vc.get('candidate_required_workflow_path_filter')!='FORBIDDEN':
        failures.append('REQUIRED_WORKFLOW_PATH_FILTER_NOT_FORBIDDEN')
    if vc.get('source_internal_pass_may_imply_current_source_admission') is not False:
        failures.append('SOURCE_INTERNAL_PASS_CURRENT_ADMISSION_LEAK')
    if vc.get('source_internal_pass_may_imply_governance_promotion') is not False:
        failures.append('SOURCE_INTERNAL_PASS_PROMOTION_LEAK')
    if vc.get('source_package_successor_workflow_path')!='.github/workflows/source-package-successor-validation.yml':
        failures.append('SOURCE_SUCCESSOR_WORKFLOW_PATH_DRIFT')
    if set(map(str,vc.get('source_package_successor_workflow_allowed_events') or []))!={'push','workflow_dispatch'}:
        failures.append('SOURCE_SUCCESSOR_WORKFLOW_ALLOWED_EVENTS_DRIFT')
    if vc.get('source_package_successor_workflow_identity_requires_name_path_allowed_event_branch_head') is not True:
        failures.append('SOURCE_SUCCESSOR_WORKFLOW_IDENTITY_GATE_MISSING')
    if vc.get('source_package_validation_toolchain_binding_mode')!='GIT_BLOB_SHA1_EXACT_SET_V1':
        failures.append('SOURCE_VALIDATION_TOOLCHAIN_BINDING_MODE_DRIFT')
    toolchain_bindings=vc.get('source_package_validation_toolchain_blob_bindings') or {}
    if not isinstance(toolchain_bindings,dict) or len(toolchain_bindings)!=44 or int(vc.get('source_package_validation_toolchain_exact_file_count') or 0)!=44:
        failures.append('SOURCE_VALIDATION_TOOLCHAIN_DENOMINATOR_DRIFT')
    if vc.get('source_package_validation_toolchain_missing_extra_or_blob_drift')!='BLOCK':
        failures.append('SOURCE_VALIDATION_TOOLCHAIN_FAIL_CLOSED_MISSING')
    if vc.get('source_package_validation_toolchain_rebind_requires_governance_candidate_review') is not True:
        failures.append('SOURCE_VALIDATION_TOOLCHAIN_REBIND_GATE_MISSING')
    required=set(map(str,vc.get('required_workflow_names') or []))
    if required!={'Current Governance Cleanup Validation','Mother Spec Neutrality Audit'}:
        failures.append('REQUIRED_WORKFLOW_DENOMINATOR_DRIFT')
    bindings=vc.get('required_workflow_bindings') or {}
    if set(bindings)!=required:
        failures.append('REQUIRED_WORKFLOW_BINDING_SET_DRIFT')
    for name,path in {'Current Governance Cleanup Validation':'.github/workflows/current-governance-cleanup-validation.yml','Mother Spec Neutrality Audit':'.github/workflows/mother-spec-neutrality-audit.yml'}.items():
        row=bindings.get(name) or {}
        if row.get('path')!=path or row.get('event')!='push':
            failures.append('REQUIRED_WORKFLOW_BINDING_DRIFT:'+name)
    if vc.get('workflow_name_only_may_grant_validation_credit') is not False or vc.get('workflow_path_event_head_branch_binding_required') is not True:
        failures.append('REQUIRED_WORKFLOW_IDENTITY_HARDENING_MISSING')
    if vc.get('workflow_external_action_ref_mode')!='FULL_40_HEX_COMMIT_SHA_ONLY' or vc.get('workflow_external_action_mutable_ref')!='BLOCK':
        failures.append('WORKFLOW_EXTERNAL_ACTION_PINNING_CONTRACT_DRIFT')
    if set(map(str,vc.get('workflow_action_pinning_required_paths') or []))!={
        '.github/workflows/current-governance-cleanup-validation.yml',
        '.github/workflows/mother-spec-neutrality-audit.yml',
        '.github/workflows/common-stage-execution-engine.yml',
    }:
        failures.append('WORKFLOW_ACTION_PINNING_PATH_DENOMINATOR_DRIFT')
    if vc.get('source_successor_workflow_action_pinning_required') is not True:
        failures.append('SOURCE_SUCCESSOR_WORKFLOW_ACTION_PINNING_GATE_MISSING')
    if vc.get('governance_ci_runner_label')!='ubuntu-24.04':
        failures.append('GOVERNANCE_CI_RUNNER_LABEL_DRIFT')
    if vc.get('governance_ci_python_version')!='3.11.16':
        failures.append('GOVERNANCE_CI_PYTHON_VERSION_DRIFT')
    if vc.get('governance_ci_dependency_lock_path')!='governance/ci/requirements-governance.lock':
        failures.append('GOVERNANCE_CI_DEPENDENCY_LOCK_PATH_DRIFT')
    if vc.get('governance_ci_dependency_install_mode')!='PIP_REQUIRE_HASHES':
        failures.append('GOVERNANCE_CI_DEPENDENCY_INSTALL_MODE_DRIFT')
    if vc.get('governance_ci_pyyaml_version')!='6.0.2' or vc.get('governance_ci_pyyaml_sha256')!='3ad2a3decf9aaba3d29c8f537ac4b243e36bef957511b4766cb0057d32b0be85':
        failures.append('GOVERNANCE_CI_DEPENDENCY_IDENTITY_DRIFT')
    if vc.get('governance_ci_environment_drift')!='BLOCK':
        failures.append('GOVERNANCE_CI_ENVIRONMENT_FAIL_CLOSED_MISSING')
    if vc.get('independent_auditor_external_provenance_required') is not True:
        failures.append('INDEPENDENT_AUDITOR_EXTERNAL_PROVENANCE_NOT_REQUIRED')
    if set(map(str,vc.get('independent_auditor_required_provenance_fields') or []))!={'implementation_provenance_ref','execution_receipt_provenance_ref','result_artifact_provenance_ref','evaluator_authority_ref'}:
        failures.append('INDEPENDENT_AUDITOR_PROVENANCE_FIELD_DENOMINATOR_DRIFT')
    if vc.get('independent_auditor_snapshot_hash_mode')!='SHA256_CANONICAL_JSON_CURRENT_CANDIDATE_SOURCE_SNAPSHOT_V1':
        failures.append('INDEPENDENT_AUDITOR_SNAPSHOT_HASH_MODE_DRIFT')
    if vc.get('independent_auditor_result_fingerprint_mode')!='SHA256_CANONICAL_JSON_CANONICAL_RESULT_V1' or vc.get('independent_auditor_result_artifact_required') is not True:
        failures.append('INDEPENDENT_AUDITOR_RESULT_ARTIFACT_CONTRACT_DRIFT')
    if vc.get('independent_auditor_authority_must_preexist_evidence_commit') is not True:
        failures.append('INDEPENDENT_AUDITOR_AUTHORITY_TEMPORAL_GATE_MISSING')
    if vc.get('independent_auditor_formal_evidence_transport')!='COMMIT_PINNED_EXTERNAL_MANIFEST':
        failures.append('INDEPENDENT_AUDITOR_FORMAL_EVIDENCE_TRANSPORT_DRIFT')
    if int(vc.get('independent_auditor_local_evidence_formal_credit') or 0)!=0:
        failures.append('LOCAL_AUDITOR_EVIDENCE_FORMAL_CREDIT_LEAK')
    if vc.get('independent_auditor_external_manifest_artifact_type')!='GOVERNANCE_INDEPENDENT_AUDITOR_EVIDENCE_MANIFEST':
        failures.append('INDEPENDENT_AUDITOR_EXTERNAL_MANIFEST_TYPE_DRIFT')
    for key in ('independent_auditor_external_manifest_must_bind_candidate_head','independent_auditor_external_manifest_actor_must_equal_primary_authority_actor','independent_auditor_external_manifest_commit_must_follow_all_evaluator_evidence','mutation_actor_inventory_pagination_complete_required','mutation_actor_inventory_count_must_match_compare_total'):
        if vc.get(key) is not True:
            failures.append('CANDIDATE_VALIDATION_FLAG_MISSING:'+key)
    if vc.get('source_external_trust_mode')!='DETACHED_SIGNATURE_ENVELOPE':
        failures.append('SOURCE_EXTERNAL_TRUST_MODE_DRIFT')
    if vc.get('source_external_trust_receipt_self_reference')!='FORBIDDEN':
        failures.append('SOURCE_EXTERNAL_TRUST_SELF_REFERENCE_NOT_FORBIDDEN')
    if int(vc.get('independent_auditor_provenance_actor_count') or 0)!=3 or vc.get('candidate_mutation_actor_may_be_formal_independent_auditor') is not False or vc.get('same_external_actor_may_supply_multiple_formal_independent_evaluators') is not False:
        failures.append('INDEPENDENT_AUDITOR_PROVENANCE_INDEPENDENCE_DRIFT')
    return {
      'check_id':'exact_head_validation_contract',
      'status':'PASS' if not failures else 'FAIL',
      'required_workflow_count':len(required),
      'failures':failures,
    }


def source_package_reentry_check()->dict:
    failures=[]
    mutation=load_yaml(ROOT/'governance/specifications/current/SPECIFICATION_MUTATION_CONTROL.yaml')
    cycle=load_yaml(ROOT/'governance/specifications/current/EXECUTION_CYCLE_CONTROL.yaml')
    src=mutation.get('immutable_source_package_successor_control') or {}
    migration=mutation.get('predecessor_evidence_consumer_migration_control') or {}
    reentry=cycle.get('immutable_source_package_defect_reentry') or {}
    state=cycle.get('successor_candidate_state_resolution') or {}
    required_true=[
      (src,'successor_source_package_required'),
      (src,'independent_external_trust_signer_required'),
      (src,'trust_signer_must_be_distinct_from_candidate_mutation_actor'),
      (src,'historical_predecessor_source_remains_immutable'),
      (migration,'successor_consumer_contract_must_be_current_identity_bound'),
      (migration,'legacy_regression_must_use_isolated_historical_fixture_when_historical_semantics_remain_required'),
      (reentry,'independent_resign_required_before_current_admission'),
    ]
    for obj,key in required_true:
        if obj.get(key) is not True:
            failures.append('SOURCE_SUCCESSOR_CONTRACT_FLAG_MISSING:'+key)
    if src.get('predecessor_source_package_mutation')!='FORBIDDEN':
        failures.append('PREDECESSOR_SOURCE_MUTATION_NOT_FORBIDDEN')
    if src.get('candidate_self_refresh_external_trust_root')!='FORBIDDEN':
        failures.append('CANDIDATE_SELF_SIGN_NOT_FORBIDDEN')
    if migration.get('missing_retired_predecessor_evidence_disposition')!='MIGRATE_CONSUMER_NOT_RESTORE_ARTIFACT':
        failures.append('RETIRED_EVIDENCE_RESTORE_NOT_FORBIDDEN')
    if reentry.get('required_state')!='BLOCKED_SOURCE_PACKAGE_SUCCESSOR_REQUIRED':
        failures.append('SOURCE_PACKAGE_REENTRY_STATE_DRIFT')
    if state.get('current_candidate_identity_source')!='governance/specifications/REGISTRY.yaml':
        failures.append('CURRENT_CANDIDATE_IDENTITY_SOURCE_DRIFT')
    return {
      'check_id':'source_package_defect_reentry',
      'status':'PASS' if not failures else 'FAIL',
      'canonical_owner':'SOURCE_PACKAGE_SUCCESSOR',
      'earliest_legal_reentry':'SOURCE_PACKAGE_SUCCESSOR_MATERIALIZATION',
      'failures':failures,
    }


def main()->int:
    registry=load_yaml(ROOT/'governance/specifications/REGISTRY.yaml')
    repository=os.environ.get('GITHUB_REPOSITORY','').strip()
    token=os.environ.get('GITHUB_TOKEN','').strip() or None
    checks=[candidate_identity_check(),exact_head_validation_contract_check(registry),source_package_reentry_check()]
    if not repository:
        source_result={'status':'BLOCKED','failures':['GITHUB_REPOSITORY_REQUIRED_FOR_SOURCE_SUCCESSOR_ADMISSION']}
    else:
        try:
            source_result=validate_source_successor(
              repository,token,registry.get('candidate_validation_contract') or {},require_external_trust=False
            )
        except Exception as exc:
            source_result={'status':'BLOCKED','failures':['SOURCE_SUCCESSOR_ADMISSION_EXCEPTION:'+type(exc).__name__+':'+str(exc)]}
    checks.append({'check_id':'source_package_successor_internal_validation',**source_result})

    failures=[x for x in checks if x.get('status') not in {'PASS','PASS_INTERNAL_UNSIGNED'}]
    source_internal_ok=source_result.get('internal_exact_head_validation')=='PASS'
    external_ready=source_result.get('external_trust_validation')=='PASS'
    result={
      'mode':'SUCCESSOR_GOVERNANCE_PREFORMAL',
      'status':'PASS' if not failures and source_internal_ok else 'FAIL',
      'checks_total':len(checks),
      'pass_count':sum(1 for x in checks if x.get('status') in {'PASS','PASS_INTERNAL_UNSIGNED'}),
      'blocking_failures':len(failures),
      'source_package_successor_internal_validation':source_result,
      'source_package_internal_exact_head_pass':source_internal_ok,
      'source_package_external_trust_status':source_result.get('external_trust_status'),
      'source_current_admission':'READY' if external_ready else 'BLOCKED_PENDING_INDEPENDENT_EXTERNAL_TRUST',
      'mandatory_regression_denominator_preserved':source_internal_ok,
      'retired_predecessor_current_state_consumer_count':0,
      'historical_current_credit':0,
      'formal_freeze_allowed':False,
      'formal_test_allowed':False,
      'governance_promotion_allowed':False,
      'product_completion_credit':0,
    }
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
