#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def replace_once(path, old, new):
    p=ROOT/path
    s=p.read_text(encoding='utf-8')
    if old not in s:
        raise SystemExit('ISSUE60_ANCHOR_MISSING:'+path)
    if s.count(old)!=1:
        raise SystemExit('ISSUE60_ANCHOR_NOT_UNIQUE:'+path+':'+str(s.count(old)))
    p.write_text(s.replace(old,new,1),encoding='utf-8')

m3='.github/governance-source/active/source/12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md'
anchor3="""When the Current Product scope/matrix/evidence is still bound to an older governance UID and no valid transition receipt exists, execution MUST fail as `GOVERNANCE_REVISION_TRANSITION_REQUIRED`. When a valid transition receipt exists but the affected Work Unit has not yet been freshly rebound/reverified, execution MUST fail as `GOVERNANCE_REVISION_TRANSITION_REENTRY_REQUIRED` at the receipt's earliest owner. The transition transaction occurs before normal Stage execution and grants zero Product completion credit by itself."""
add3=anchor3+"""

A governance-remediation workflow that creates a successor governance-candidate HEAD MUST NOT treat the producer workflow's own success as validation of that successor HEAD. The successor HEAD remains `CANDIDATE_UNVALIDATED` until every Registry-required governance validation workflow has a fresh terminal result bound to that exact successor HEAD, branch, registered workflow path and allowed event. Parent-head PASS/FAIL, prior-head validation, producer-job success, or a zero-run/check state MUST_NOT receive successor-head validation credit.

A self-mutating governance workflow MUST declare a successor-head validation terminalization path before mutation. The terminalization path MUST either end on an authorized commit/ref update that deterministically triggers the Registry-required validations, or use an explicitly Registry-authorized exact-head validation dispatch mechanism supported by both the workflow and validation contract. Token/event recursion suppression, bot-authored push behavior, or an assumed downstream trigger MUST_NOT be treated as evidence that validation occurred.

Any authorized change to a Stage normative-reference set MUST be synchronized as one bounded governance transaction across the canonical reference owner, semantic authority snapshot/baseline, validator hash/binding, Root Manifest/checksum projections, generated audit requirement index and registered regression expectations. Partial synchronization, consumer-local expected-count repair, or a semantic baseline that still represents the predecessor Stage reference set is `STAGE_NORMATIVE_REFERENCE_TRANSACTION_INCOMPLETE` and blocks candidate closure."""
replace_once(m3,anchor3,add3)

m4='.github/governance-source/active/source/12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md'
anchor4="""Negative regression MUST include at least: selected SHA differs from loaded governance checkout; selected identity is candidate/not released; selected release lacks fresh reverification evidence; old-governance scope/evidence reused without transition receipt; transition receipt bound to another Work Unit; and impacted closure retained as PASS instead of `REVERIFY_REQUIRED`."""
add4=anchor4+"""

Audit MUST also verify governance-candidate successor-head terminalization. When a governance remediation or materializer creates a new candidate HEAD, required validation evidence MUST belong to that exact successor HEAD; producer-workflow success, parent-head results, prior-head results, or zero required workflow runs/checks are non-credit. A successor HEAD without the Registry-required fresh terminal workflow set is `CANDIDATE_EXACT_HEAD_VALIDATION_MISSING` and MUST remain blocked.

For any authorized Stage normative-reference change, Audit MUST reconstruct one synchronization transaction covering the canonical reference rules, semantic authority baseline/snapshot, validator binding, Root Manifest/checksums, generated requirement index and regression expectations. A legal Mother/Reference Rule expansion with stale semantic/regression consumers is not a Stage-spec closure; it is `STAGE_NORMATIVE_REFERENCE_TRANSACTION_INCOMPLETE`."""
replace_once(m4,anchor4,add4)

inv='.github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'
old_inv="""  PRODUCT_GOVERNANCE_RELEASE_SELECTION_AND_APPLICATION_BASELINE:
    invariant_uid: GOV-INV-PRODUCT-GOVERNANCE-RELEASE-APPLICATION-BASELINE-001
    applies_to_formal_product_stage_execution: true"""
new_inv="""  PRODUCT_GOVERNANCE_RELEASE_SELECTION_AND_APPLICATION_BASELINE:
    invariant_uid: GOV-INV-PRODUCT-GOVERNANCE-RELEASE-APPLICATION-BASELINE-001
    normative_section_uids:
    - WEB-GOV-03-S073
    - WEB-GOV-03-S074
    - WEB-GOV-04-S088
    - WEB-GOV-04-S089
    applies_to_stages:
    - STAGE-01
    - STAGE-02
    - STAGE-03
    - STAGE-04
    - STAGE-05
    - STAGE-06
    - STAGE-07
    - STAGE-08
    - STAGE-09
    - STAGE-10
    - STAGE-11
    product_governance_selection_scope: ALL_FORMAL_PRODUCT_STAGES
    application_baseline_stage_scope:
    - STAGE-05
    candidate_validation_terminalization_authority_ref: governance/specifications/REGISTRY.yaml#candidate_validation_contract
    applies_to_formal_product_stage_execution: true"""
replace_once(inv,old_inv,new_inv)

reg='governance/specifications/REGISTRY.yaml'
old_auth="""    - WORKFLOW_BINDING_REGRESSION
product_execution_branch: 0921acpos"""
new_auth="""    - WORKFLOW_BINDING_REGRESSION
  - record_url: https://github.com/steven-gold/orange-one-ai-viedo-v1.0/issues/60
    record_kind: GITHUB_GOVERNANCE_CHANGE_RECORD
    authorization_base_head: 66a77b1697c16593e6c0fc4bd755afc81b5b6101
    preexists_normative_mutation_after_base: true
    candidate_branch: rebuild-v2.1.1
    authorized_scope:
    - STAGE_SPECIFICATION_COMPLETENESS
    - STAGE_INVARIANT_NORMATIVE_BINDING
    - GOVERNANCE_SUCCESSOR_HEAD_VALIDATION_TERMINALIZATION
    - STAGE_NORMATIVE_REFERENCE_TRANSACTION_CLOSURE
    - GOVERNANCE_ONLY_NEGATIVE_REGRESSION
    - NO_PRODUCT_STAGE_EXECUTION
product_execution_branch: 0921acpos"""
replace_once(reg,old_auth,new_auth)

old_cv="""  exact_candidate_head_required: true
  required_workflow_names:"""
new_cv="""  exact_candidate_head_required: true
  remediation_generated_successor_head_requires_fresh_exact_head_validation: true
  remediation_producer_success_is_not_successor_head_validation: true
  prior_head_workflow_result_may_credit_successor_head: false
  zero_required_workflow_runs_on_successor_head: BLOCK
  self_mutating_governance_workflow_must_declare_successor_validation_terminalization: true
  successor_validation_terminalization_allowed_mechanisms:
  - AUTHORIZED_COMMIT_OR_REF_UPDATE_THAT_TRIGGERS_REGISTERED_REQUIRED_PUSH_WORKFLOWS
  - EXPLICIT_EXACT_HEAD_VALIDATION_DISPATCH_WHEN_WORKFLOW_AND_REGISTRY_ALLOW_IT
  semantic_reference_change_transaction_required: true
  semantic_reference_transaction_required_owners:
  - REFERENCE_RULE_REGISTRY
  - SEMANTIC_AUTHORITY_BASELINE
  - REFERENCE_SEMANTICS_VALIDATOR_BINDING
  - GOVERNANCE_ROOT_MANIFEST
  - CHECKSUMS
  - AUDIT_BASELINE
  - GOVERNANCE_REQUIREMENT_INDEX
  - REGRESSION_EXPECTATION_OWNER
  semantic_reference_transaction_partial_sync: BLOCK
  required_workflow_names:"""
replace_once(reg,old_cv,new_cv)

eng='governance/ci/stage_execution_engine.py'
old_eng="""    if not policy or policy.get('invariant_uid')!='GOV-INV-PRODUCT-GOVERNANCE-RELEASE-APPLICATION-BASELINE-001':
        fail('PRODUCT_GOVERNANCE_SELECTION_POLICY_MISSING')
    return policy"""
new_eng="""    if not policy or policy.get('invariant_uid')!='GOV-INV-PRODUCT-GOVERNANCE-RELEASE-APPLICATION-BASELINE-001':
        fail('PRODUCT_GOVERNANCE_SELECTION_POLICY_MISSING')
    expected_refs={'WEB-GOV-03-S073','WEB-GOV-03-S074','WEB-GOV-04-S088','WEB-GOV-04-S089'}
    if set(map(str,policy.get('normative_section_uids') or []))!=expected_refs:
        fail('PRODUCT_GOVERNANCE_SELECTION_NORMATIVE_BINDING_DRIFT')
    profile=y(LIFECYCLE)
    registered={str(row.get('stage_uid') or '') for row in (profile.get('stages') or []) if isinstance(row,dict) and row.get('stage_uid')}
    if not registered or set(map(str,policy.get('applies_to_stages') or []))!=registered:
        fail('PRODUCT_GOVERNANCE_SELECTION_STAGE_APPLICABILITY_DRIFT')
    if list(map(str,policy.get('application_baseline_stage_scope') or []))!=['STAGE-05']:
        fail('APPLICATION_BASELINE_STAGE_SCOPE_DRIFT')
    if policy.get('candidate_validation_terminalization_authority_ref')!='governance/specifications/REGISTRY.yaml#candidate_validation_contract':
        fail('PRODUCT_GOVERNANCE_SELECTION_TERMINALIZATION_AUTHORITY_DRIFT')
    return policy"""
replace_once(eng,old_eng,new_eng)

pre='governance/ci/validate_successor_governance_preformal.py'
old_pre="""    vc=registry.get('candidate_validation_contract') or {}
    mutation=registry.get('mutation_policy') or {}
    failures=[]"""
new_pre="""    vc=registry.get('candidate_validation_contract') or {}
    mutation=registry.get('mutation_policy') or {}
    failures=[]
    issue60_expected={
      'remediation_generated_successor_head_requires_fresh_exact_head_validation': True,
      'remediation_producer_success_is_not_successor_head_validation': True,
      'prior_head_workflow_result_may_credit_successor_head': False,
      'zero_required_workflow_runs_on_successor_head': 'BLOCK',
      'self_mutating_governance_workflow_must_declare_successor_validation_terminalization': True,
      'semantic_reference_change_transaction_required': True,
      'semantic_reference_transaction_partial_sync': 'BLOCK',
    }
    for key,value in issue60_expected.items():
        if vc.get(key)!=value: failures.append('ISSUE60_CANDIDATE_VALIDATION_CONTRACT_DRIFT:'+key)
    allowed=set(map(str,vc.get('successor_validation_terminalization_allowed_mechanisms') or []))
    if allowed!={'AUTHORIZED_COMMIT_OR_REF_UPDATE_THAT_TRIGGERS_REGISTERED_REQUIRED_PUSH_WORKFLOWS','EXPLICIT_EXACT_HEAD_VALIDATION_DISPATCH_WHEN_WORKFLOW_AND_REGISTRY_ALLOW_IT'}:
        failures.append('ISSUE60_TERMINALIZATION_MECHANISM_DRIFT')
    sync=set(map(str,vc.get('semantic_reference_transaction_required_owners') or []))
    expected_sync={'REFERENCE_RULE_REGISTRY','SEMANTIC_AUTHORITY_BASELINE','REFERENCE_SEMANTICS_VALIDATOR_BINDING','GOVERNANCE_ROOT_MANIFEST','CHECKSUMS','AUDIT_BASELINE','GOVERNANCE_REQUIREMENT_INDEX','REGRESSION_EXPECTATION_OWNER'}
    if sync!=expected_sync: failures.append('ISSUE60_SEMANTIC_REFERENCE_TRANSACTION_OWNER_DRIFT')
    inv=load_yaml(SOURCE/'10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml')
    policy=(inv.get('invariants') or {}).get('PRODUCT_GOVERNANCE_RELEASE_SELECTION_AND_APPLICATION_BASELINE') or {}
    expected_refs={'WEB-GOV-03-S073','WEB-GOV-03-S074','WEB-GOV-04-S088','WEB-GOV-04-S089'}
    if set(map(str,policy.get('normative_section_uids') or []))!=expected_refs:
        failures.append('ISSUE60_STAGE_INVARIANT_NORMATIVE_BINDING_DRIFT')
    life=load_yaml(SOURCE/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml')
    registered={str(row.get('stage_uid') or '') for row in (life.get('stages') or []) if isinstance(row,dict) and row.get('stage_uid')}
    if not registered or set(map(str,policy.get('applies_to_stages') or []))!=registered:
        failures.append('ISSUE60_STAGE_INVARIANT_APPLICABILITY_DRIFT')
    if list(map(str,policy.get('application_baseline_stage_scope') or []))!=['STAGE-05']:
        failures.append('ISSUE60_APPLICATION_BASELINE_STAGE_SCOPE_DRIFT')"""
replace_once(pre,old_pre,new_pre)

ready='governance/ci/validate_governance_candidate_promotion_readiness.py'
old_ready="""    add('missing_one_workflow',[run(1,names[0])],'BLOCKED')"""
new_ready="""    add('missing_one_workflow',[run(1,names[0])],'BLOCKED')
    add('zero_required_workflow_runs_blocked',[],'BLOCKED')"""
replace_once(ready,old_ready,new_ready)

test='governance/ci/test_stage_execution_engine.py'
old_test="""eng.validate_definition_data(profile,adapters)
assert eng.validate_current_ledger_synchronization_contract() is True"""
new_test="""eng.validate_definition_data(profile,adapters)
_issue60_policy=eng._selection_policy()
assert set(map(str,_issue60_policy.get('normative_section_uids') or []))=={'WEB-GOV-03-S073','WEB-GOV-03-S074','WEB-GOV-04-S088','WEB-GOV-04-S089'}
assert set(map(str,_issue60_policy.get('applies_to_stages') or []))==set(eng.stage_map(profile))
assert list(map(str,_issue60_policy.get('application_baseline_stage_scope') or []))==['STAGE-05']
assert _issue60_policy.get('candidate_validation_terminalization_authority_ref')=='governance/specifications/REGISTRY.yaml#candidate_validation_contract'
assert eng.validate_current_ledger_synchronization_contract() is True"""
replace_once(test,old_test,new_test)

print('PASS: issue60 bounded governance mutations applied')
