#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
GOV_TESTS=SOURCE/'09_TESTS/governance'
sys.path.insert(0,str(ROOT/'governance/ci'))
from governance_resolver import resolve as resolve_governance


def import_source(name:str):
    path=GOV_TESTS/f'{name}.py'
    spec=importlib.util.spec_from_file_location('source_'+name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError('SOURCE_VALIDATOR_IMPORT_FAILED:'+name)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_yaml(path:Path)->dict:
    value=yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(value,dict):
        raise RuntimeError('MAPPING_REQUIRED:'+str(path))
    return value


def candidate_identity_check(_root:Path)->dict:
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
      'status':'PASS' if not failures else 'FAIL',
      'current_truth_source':'governance/specifications/REGISTRY.yaml',
      'retired_predecessor_state_live_count':len(present),
      'failures':failures,
    }


def exact_head_validation_contract_check(_root:Path)->dict:
    failures=[]
    registry=load_yaml(ROOT/'governance/specifications/REGISTRY.yaml')
    vc=registry.get('candidate_validation_contract') or {}
    if vc.get('exact_candidate_head_required') is not True:
        failures.append('EXACT_CANDIDATE_HEAD_NOT_REQUIRED')
    if vc.get('required_workflows_run_on_every_candidate_push') is not True:
        failures.append('REQUIRED_WORKFLOWS_EVERY_PUSH_NOT_REQUIRED')
    if vc.get('candidate_required_workflow_path_filter')!='FORBIDDEN':
        failures.append('REQUIRED_WORKFLOW_PATH_FILTER_NOT_FORBIDDEN')
    if vc.get('live_branch_head_must_equal_validation_head') is not True:
        failures.append('LIVE_BRANCH_HEAD_BINDING_NOT_REQUIRED')
    if vc.get('live_branch_head_recheck_after_evidence_validation_required') is not True:
        failures.append('LIVE_BRANCH_HEAD_RECHECK_NOT_REQUIRED')
    if vc.get('formal_promotion_requires_all_required_workflows_exact_head_success') is not True:
        failures.append('EXACT_HEAD_WORKFLOW_SUCCESS_NOT_REQUIRED')
    if vc.get('formal_promotion_requires_independent_auditor_evidence') is not True:
        failures.append('INDEPENDENT_AUDITOR_EVIDENCE_NOT_REQUIRED')
    required=set(map(str,vc.get('required_workflow_names') or []))
    if required!={'Current Governance Cleanup Validation','Mother Spec Neutrality Audit'}:
        failures.append('REQUIRED_WORKFLOW_DENOMINATOR_DRIFT')
    return {'status':'PASS' if not failures else 'FAIL','required_workflow_count':len(required),'failures':failures}


def source_package_reentry_check(_root:Path)->dict:
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
      'status':'PASS' if not failures else 'FAIL',
      'canonical_owner':'SOURCE_PACKAGE_SUCCESSOR',
      'earliest_legal_reentry':'SOURCE_PACKAGE_SUCCESSOR_MATERIALIZATION',
      'failures':failures,
    }


def classify_source_block(check:dict)->dict:
    if check.get('status')=='PASS':
        return check
    cid=str(check.get('check_id') or '')
    source_owned={
      'section_registry','execution_governance_load','acceptance_blueprint_compiled_baseline',
      'mandatory_regression_and_package_integrity','root_manifest'
    }
    if cid in source_owned:
        check=dict(check)
        check['canonical_owner']='SOURCE_PACKAGE_SUCCESSOR'
        check['failure_class']='SOURCE_PACKAGE_DEFECT'
        check['disposition']='BLOCKED_SOURCE_PACKAGE_SUCCESSOR_REQUIRED'
        check['earliest_legal_reentry']='SOURCE_PACKAGE_SUCCESSOR_MATERIALIZATION'
        check['promotion_credit']=0
    return check


def main()->int:
    gov=import_source('validate_governance')
    checks=[]
    def run(cid,fn):
        try:
            out=fn(SOURCE)
            row={'check_id':cid,**out}
        except Exception as exc:
            row={'check_id':cid,'status':'FAIL','failures':['exception:'+repr(exc)]}
        checks.append(classify_source_block(row))

    # Preserve every immutable-source definition/package check that remains applicable.
    run('external_trust_root',gov.external_trust_anchor_guard)
    run('parser_hygiene',gov.parser_hygiene)
    run('section_registry',import_source('validate_section_registry').validate)
    run('construction_artifact_index',import_source('validate_construction_artifact_index').validate)
    run('execution_governance_load',import_source('validate_execution_governance_load').validate_definition)
    run('cleanup_protection',import_source('validate_cleanup_protection').validate)
    run('lifecycle_stage_contract',import_source('governance_lifecycle_stage_contract_guard').validate)
    run('management_contract',import_source('governance_management_contract_guard').validate)
    run('reference_semantics',import_source('validate_reference_semantics').validate)
    run('program_artifact_instance_guard',import_source('program_artifact_instance_guard').validate_definition)

    # Successor Current-state checks replace retired predecessor live-state consumers.
    run('current_candidate_identity',candidate_identity_check)
    run('exact_head_validation_contract',exact_head_validation_contract_check)
    run('source_package_defect_reentry',source_package_reentry_check)

    run('closure_evidence_continuity',import_source('validate_closure_evidence_continuity').validate)
    run('stage_execution_invariants',import_source('validate_stage_execution_invariants').validate)
    run('test_feedback_spec_evolution',import_source('validate_test_feedback_spec_evolution').validate)
    run('product_neutral_entity_lifecycle',import_source('validate_product_neutral_entity_lifecycle').validate)
    run('acceptance_blueprint_compiled_baseline',gov.baseline_guard)
    run('root_manifest',gov.root_manifest_guard)
    run('mandatory_regression_and_package_integrity',gov.mandatory_regression_guard)

    failures=[x for x in checks if x.get('status')!='PASS']
    source_failures=[x for x in failures if x.get('failure_class')=='SOURCE_PACKAGE_DEFECT']
    result={
      'mode':'SUCCESSOR_GOVERNANCE_PREFORMAL',
      'status':'PASS' if not failures else 'FAIL',
      'checks_total':len(checks),
      'pass_count':len(checks)-len(failures),
      'blocking_failures':len(failures),
      'source_package_blocker_count':len(source_failures),
      'retired_predecessor_current_state_consumer_count':0,
      'mandatory_regression_denominator_preserved':True,
      'source_package_mutation_performed':False,
      'historical_current_credit':0,
      'checks':checks,
      'formal_freeze_allowed':False,
      'formal_test_allowed':False,
      'governance_promotion_allowed':False,
      'product_completion_credit':0,
    }
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
