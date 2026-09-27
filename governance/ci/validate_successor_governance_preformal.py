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
    if not isinstance(d,dict): raise RuntimeError('MAPPING_REQUIRED:'+str(path))
    return d

def main():
    registry=load_yaml(ROOT/'governance/specifications/REGISTRY.yaml')
    resolved=resolve_governance()
    vc=registry.get('candidate_validation_contract') or {}
    mutation=registry.get('mutation_policy') or {}
    failures=[]
    current_branch=str(registry.get('branch') or '')
    role=str(resolved.get('governance_role') or '')
    if not current_branch or role not in {'GOVERNANCE_REVISION_CANDIDATE','IMMUTABLE_GOVERNANCE_RULESET'}:
        failures.append('SINGLE_BRANCH_CURRENT_IDENTITY_DRIFT')
    release_reverify=(role=='IMMUTABLE_GOVERNANCE_RULESET')
    if release_reverify:
        ident=registry.get('governance_identity') or {}
        manifest=load_yaml(ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml')
        lock=load_yaml(ROOT/'governance/BRANCH_AUTHORITY_LOCK.yaml')
        branch_lock=(lock.get('branches') or {}).get(current_branch) or {}
        if registry.get('status')!='CURRENT_RELEASED':
            failures.append('RELEASE_REVERIFY_REGISTRY_STATUS_DRIFT')
        if ident.get('status')!='RELEASED' or ident.get('identity_state')!='IMMUTABLE_RELEASED' or ident.get('released_immutable_identity') is not True:
            failures.append('RELEASE_REVERIFY_IDENTITY_DRIFT')
        if manifest.get('branch_release_state')!='RELEASED_CURRENT' or manifest.get('released_current_authority') is not True:
            failures.append('RELEASE_REVERIFY_MANIFEST_STATE_DRIFT')
        if branch_lock.get('role')!='IMMUTABLE_GOVERNANCE_RULESET' or branch_lock.get('gpt_write_policy')!='FORBIDDEN':
            failures.append('RELEASE_REVERIFY_BRANCH_LOCK_DRIFT')
    if mutation.get('single_branch_consolidation_mode') is not True or str(mutation.get('single_active_governance_branch') or '')!=current_branch:
        failures.append('SINGLE_BRANCH_CONSOLIDATION_CONTRACT_DRIFT')
    if mutation.get('branch_fanout_without_explicit_user_authorization')!='FORBIDDEN':
        failures.append('SINGLE_BRANCH_FANOUT_GUARD_MISSING')
    required=set(map(str,vc.get('required_workflow_names') or []))
    if required!={'Current Governance Cleanup Validation','Mother Spec Neutrality Audit'}:
        failures.append('REQUIRED_WORKFLOW_DENOMINATOR_DRIFT')
    bindings=vc.get('required_workflow_bindings') or {}
    for name,path in {'Current Governance Cleanup Validation':'.github/workflows/current-governance-cleanup-validation.yml','Mother Spec Neutrality Audit':'.github/workflows/mother-spec-neutrality-audit.yml'}.items():
        row=bindings.get(name) or {}
        if row.get('path')!=path or row.get('event')!='push':
            failures.append('REQUIRED_WORKFLOW_BINDING_DRIFT:'+name)
    for key in ('exact_candidate_head_required','required_workflows_run_on_every_candidate_push','live_branch_head_must_equal_validation_head','live_branch_head_recheck_after_evidence_validation_required','formal_promotion_requires_all_required_workflows_exact_head_success','formal_promotion_requires_independent_auditor_evidence','remediation_generated_successor_head_requires_fresh_exact_head_validation','remediation_producer_success_is_not_successor_head_validation','self_mutating_governance_workflow_must_declare_successor_validation_terminalization','semantic_reference_change_transaction_required'):
        if vc.get(key) is not True: failures.append('CURRENT_VALIDATION_FLAG_MISSING:'+key)
    if vc.get('prior_head_workflow_result_may_credit_successor_head') is not False: failures.append('PRIOR_HEAD_SUCCESSOR_CREDIT_NOT_BLOCKED')
    if vc.get('zero_required_workflow_runs_on_successor_head')!='BLOCK': failures.append('ZERO_RUN_SUCCESSOR_HEAD_NOT_BLOCKED')
    allowed=set(map(str,vc.get('successor_validation_terminalization_allowed_mechanisms') or []))
    if allowed!={'AUTHORIZED_COMMIT_OR_REF_UPDATE_THAT_TRIGGERS_REGISTERED_REQUIRED_PUSH_WORKFLOWS','EXPLICIT_EXACT_HEAD_VALIDATION_DISPATCH_WHEN_WORKFLOW_AND_REGISTRY_ALLOW_IT'}: failures.append('SUCCESSOR_VALIDATION_TERMINALIZATION_MECHANISM_DRIFT')
    owners=set(map(str,vc.get('semantic_reference_transaction_required_owners') or []))
    if owners!={'REFERENCE_RULE_REGISTRY','SEMANTIC_AUTHORITY_BASELINE','REFERENCE_SEMANTICS_VALIDATOR_BINDING','GOVERNANCE_ROOT_MANIFEST','CHECKSUMS','AUDIT_BASELINE','GOVERNANCE_REQUIREMENT_INDEX','REGRESSION_EXPECTATION_OWNER'} or vc.get('semantic_reference_transaction_partial_sync')!='BLOCK': failures.append('SEMANTIC_REFERENCE_TRANSACTION_CONTRACT_DRIFT')
    if vc.get('source_package_successor_required') is not False:
        failures.append('SEPARATE_SOURCE_SUCCESSOR_NOT_RETIRED')
    if vc.get('source_package_integration_mode')!='SINGLE_BRANCH_INTEGRATED' or str(vc.get('source_package_integrated_branch') or '')!=current_branch:
        failures.append('SOURCE_PACKAGE_INTEGRATION_MODE_DRIFT')
    meta=load_yaml(ROOT/'governance/source-successor/SOURCE_PACKAGE_CANDIDATE.yaml')
    if meta.get('status')!='INTEGRATED_CURRENT_WORKLINE' or meta.get('current_authority') is not True or str(meta.get('branch') or '')!=current_branch:
        failures.append('SOURCE_INTEGRATION_RECORD_DRIFT')
    retired=[SOURCE/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml',SOURCE/'11_EVIDENCE/audit/GITHUB_REPLAY_CLOSURE_RESULT.yaml',SOURCE/'11_EVIDENCE/audit/GOVERNANCE_DEFECT_LEDGER.yaml',SOURCE/'11_EVIDENCE/audit/HIGH_PRESSURE_HARDENING_RESULT.yaml',SOURCE/'11_EVIDENCE/audit/REFERENCE_SEMANTIC_REPAIR_RESULT.yaml']
    present=[p.relative_to(SOURCE).as_posix() for p in retired if p.exists()]
    if present: failures.append('RETIRED_PREDECESSOR_STATE_REAPPEARED_AS_LIVE_SOURCE:'+repr(present))
    validator=ROOT/str(vc.get('source_package_integrated_validator') or '')
    proc=subprocess.run([sys.executable,str(validator)],cwd=ROOT,text=True,capture_output=True)
    try: src=json.loads(proc.stdout)
    except Exception: src={'status':'FAIL','failures':['INTEGRATED_SOURCE_VALIDATOR_OUTPUT_UNPARSEABLE'],'stderr':proc.stderr[-3000:]}
    if proc.returncode!=0 or src.get('status')!='PASS_INTEGRATED_SOURCE':
        failures.append('INTEGRATED_SOURCE_VALIDATION_FAILED')
    result={'mode':'SINGLE_BRANCH_RELEASE_REVERIFY' if release_reverify else 'SINGLE_BRANCH_GOVERNANCE_PREFORMAL','release_reverify':release_reverify,'status':'PASS' if not failures else 'FAIL','blocking_failures':len(failures),'failures':failures,'source_package_successor_internal_validation':src,'source_package_internal_exact_head_pass':src.get('status')=='PASS_INTEGRATED_SOURCE','source_package_external_trust_status':'NOT_REQUIRED_SINGLE_BRANCH_CONSOLIDATION','source_current_admission':'INTEGRATED_CURRENT_WORKLINE' if src.get('status')=='PASS_INTEGRATED_SOURCE' else 'BLOCKED','mandatory_regression_denominator_preserved':src.get('status')=='PASS_INTEGRATED_SOURCE','historical_current_credit':0,'formal_freeze_allowed':False,'formal_test_allowed':False,'governance_promotion_allowed':False,'product_completion_credit':0}
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    return 0 if result['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
