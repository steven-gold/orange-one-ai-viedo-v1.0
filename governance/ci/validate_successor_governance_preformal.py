#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
sys.path.insert(0,str(ROOT/'governance/ci'))
from governance_resolver import resolve as resolve_governance

def load_yaml(path):
    d=yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(d,dict):
        raise RuntimeError('MAPPING_REQUIRED:'+str(path))
    return d

def main():
    registry=load_yaml(ROOT/'governance/specifications/REGISTRY.yaml')
    resolved=resolve_governance()
    vc=registry.get('current_validation_contract') or {}
    mutation=registry.get('mutation_policy') or {}
    failures=[]
    current_branch=str(registry.get('branch') or '')

    if resolved.get('governance_role')!='CURRENT_GOVERNANCE_WORKLINE':
        failures.append('CURRENT_GOVERNANCE_WORKLINE_IDENTITY_DRIFT')
    if registry.get('status')!='CURRENT':
        failures.append('CURRENT_GOVERNANCE_STATUS_DRIFT')
    if mutation.get('single_branch_consolidation_mode') is not True:
        failures.append('SINGLE_BRANCH_CURRENT_GOVERNANCE_MODE_DRIFT')
    if str(mutation.get('single_active_governance_branch') or '')!=current_branch:
        failures.append('SINGLE_ACTIVE_GOVERNANCE_BRANCH_DRIFT')
    if mutation.get('branch_fanout_without_explicit_user_authorization')!='FORBIDDEN':
        failures.append('SINGLE_BRANCH_FANOUT_GUARD_MISSING')

    expected_workflows={
      'Current Governance Stage Internal Validation':'.github/workflows/current-governance-stage-internal-validation.yml',
      'Mother Spec Neutrality Audit':'.github/workflows/mother-spec-neutrality-audit.yml',
    }
    if set(map(str,vc.get('required_workflow_names') or []))!=set(expected_workflows):
        failures.append('CURRENT_REQUIRED_WORKFLOW_DENOMINATOR_DRIFT')
    bindings=vc.get('required_workflow_bindings') or {}
    for name,path in expected_workflows.items():
        row=bindings.get(name) or {}
        if row.get('path')!=path or row.get('event')!='push':
            failures.append('CURRENT_REQUIRED_WORKFLOW_BINDING_DRIFT:'+name)
        if not (ROOT/path).is_file():
            failures.append('CURRENT_REQUIRED_WORKFLOW_MISSING:'+name)

    if vc.get('exact_head_commit_status_receipts_required') is not True:
        failures.append('EXACT_HEAD_STATUS_RECEIPT_CONTRACT_MISSING')
    if set(map(str,vc.get('required_commit_status_contexts') or []))!={'Governance/Stage Internal Validation','Governance/Mother Neutrality'}:
        failures.append('CURRENT_REQUIRED_STATUS_CONTEXT_DENOMINATOR_DRIFT')
    for key in ('commit_status_sha_must_equal_validation_head','commit_status_success_required','exact_current_head_required'):
        if vc.get(key) is not True:
            failures.append('CURRENT_EXACT_HEAD_FLAG_MISSING:'+key)
    if vc.get('prior_head_workflow_result_may_credit_current_head') is not False:
        failures.append('PRIOR_HEAD_CURRENT_CREDIT_NOT_BLOCKED')
    if vc.get('historical_pass_substitution')!='FORBIDDEN':
        failures.append('HISTORICAL_PASS_SUBSTITUTION_NOT_BLOCKED')

    if vc.get('authority_model')!='WORD_DERIVED_INTERNAL_VALIDATION':
        failures.append('WORD_DERIVED_AUTHORITY_MODEL_DRIFT')
    if vc.get('word_source_is_primary_product_design_source') is not True:
        failures.append('WORD_SOURCE_PRIMARY_AUTHORITY_DRIFT')
    if vc.get('ai_supplementation_policy')!='SAME_WORD_CONTEXT_AND_EXISTING_CANONICAL_SYSTEM_RELATIONSHIPS_ONLY':
        failures.append('AI_SUPPLEMENTATION_POLICY_DRIFT')
    if vc.get('generated_content_may_become_second_source_authority') is not False:
        failures.append('GENERATED_SECOND_AUTHORITY_NOT_BLOCKED')
    for key in (
      'external_human_or_account_evidence_required','external_auditor_required','external_signer_required',
      'detached_external_trust_required','promotion_required_before_product_stage_execution',
      'released_governance_selection_required'
    ):
        if vc.get(key) is not False:
            failures.append('NON_WORD_EXTERNAL_GATE_REINTRODUCED:'+key)

    if vc.get('source_package_integration_mode')!='SINGLE_BRANCH_INTEGRATED':
        failures.append('SOURCE_PACKAGE_INTEGRATION_MODE_DRIFT')
    if str(vc.get('source_package_integrated_branch') or '')!=current_branch:
        failures.append('SOURCE_PACKAGE_INTEGRATED_BRANCH_DRIFT')
    validator_rel=str(vc.get('source_package_integrated_validator') or '')
    validator=ROOT/validator_rel
    if not validator_rel or not validator.is_file():
        failures.append('SOURCE_PACKAGE_INTEGRATED_VALIDATOR_MISSING')
        src={'status':'FAIL','failures':['SOURCE_PACKAGE_INTEGRATED_VALIDATOR_MISSING']}
    else:
        proc=subprocess.run([sys.executable,str(validator)],cwd=ROOT,text=True,capture_output=True)
        try:
            src=json.loads(proc.stdout)
        except Exception:
            src={'status':'FAIL','failures':['INTEGRATED_SOURCE_VALIDATOR_OUTPUT_UNPARSEABLE'],'diagnostics':(proc.stdout+proc.stderr)[-3000:]}
        if proc.returncode!=0 or src.get('status')!='PASS_INTEGRATED_SOURCE':
            failures.append('INTEGRATED_SOURCE_VALIDATION_FAILED')

    meta=load_yaml(ROOT/'governance/source-successor/SOURCE_PACKAGE_CANDIDATE.yaml')
    if meta.get('artifact_type')!='GOVERNANCE_SOURCE_PACKAGE_INTEGRATION_RECORD':
        failures.append('SOURCE_INTEGRATION_RECORD_TYPE_DRIFT')
    if meta.get('status')!='INTEGRATED_CURRENT_WORKLINE' or meta.get('current_authority') is not True:
        failures.append('SOURCE_INTEGRATION_RECORD_STATE_DRIFT')
    if str(meta.get('branch') or '')!=current_branch:
        failures.append('SOURCE_INTEGRATION_RECORD_BRANCH_DRIFT')
    integ=meta.get('integration') or {}
    if integ.get('mode')!='SINGLE_BRANCH_INTEGRATED' or integ.get('separate_source_branch_required') is not False:
        failures.append('SOURCE_INTEGRATION_RECORD_MODE_DRIFT')
    integrity=meta.get('source_integrity') or {}
    for key in ('word_or_registered_source_integrity_required','deterministic_hash_validation_required','exact_head_internal_validation_required'):
        if integrity.get(key) is not True:
            failures.append('SOURCE_INTEGRITY_FLAG_MISSING:'+key)
    if integrity.get('external_person_or_signer_required') is not False:
        failures.append('SOURCE_EXTERNAL_PERSON_GATE_REINTRODUCED')

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

    result={
      'artifact_type':'CURRENT_GOVERNANCE_PREFORMAL_VALIDATION',
      'mode':'WORD_DERIVED_SINGLE_BRANCH_CURRENT',
      'status':'PASS' if not failures else 'FAIL',
      'blocking_failures':len(failures),
      'failures':failures,
      'integrated_source_validation':src,
      'word_source_primary':vc.get('word_source_is_primary_product_design_source') is True,
      'external_person_account_auditor_or_signer_required':False,
      'promotion_or_release_gate_required':False,
      'historical_current_credit':0,
      'product_completion_credit':0,
    }
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':
    raise SystemExit(main())
