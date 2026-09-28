from pathlib import Path
import yaml, sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
def load(root,rel): return yaml.safe_load((root/rel).read_text(encoding='utf-8')) or {}
def validate(root=ROOT):
    failures=[]; rel='10_REGISTRY/PRODUCT_EXECUTION_ENVIRONMENT_ADMISSION_REGISTRY.yaml'; p=root/rel
    if not p.exists(): return {'status':'FAIL','failures':['external_execution_admission_registry_missing']}
    admission=load(root,rel)
    if admission.get('artifact_uid')!='REG-PRODUCT-EXECUTION-ENVIRONMENT-ADMISSION-001' or admission.get('artifact_type')!='PRODUCT_EXECUTION_ENVIRONMENT_ADMISSION_REGISTRY': failures.append('external_execution_admission_registry_identity_invalid')
    scope=admission.get('scope') or {}
    if scope.get('layer_classification')!='EXTERNAL_PRODUCT_EXECUTION_ENVIRONMENT_ADMISSION' or scope.get('reusable_common_stage_normative_denominator_inclusion')!='EXCLUDED' or scope.get('reusable_common_stage_definition_credit')!=0 or scope.get('reusable_common_stage_completion_credit')!=0: failures.append('external_execution_admission_scope_isolation_missing')
    contracts=admission.get('product_execution_admission_contracts') or {}
    if set(contracts)!={'PRODUCT_CURRENT_GOVERNANCE_SNAPSHOT_AND_APPLICATION_BASELINE'}: failures.append('external_execution_admission_contract_set_drift')
    c=contracts.get('PRODUCT_CURRENT_GOVERNANCE_SNAPSHOT_AND_APPLICATION_BASELINE') or {}
    if c.get('scope_class')!='EXTERNAL_PRODUCT_EXECUTION_ENVIRONMENT_ADMISSION' or c.get('reusable_common_stage_normative_denominator_inclusion')!='EXCLUDED' or c.get('reusable_common_stage_definition_credit')!=0 or c.get('reusable_common_stage_completion_credit')!=0: failures.append('external_execution_admission_contract_scope_invalid')
    if c.get('product_specific_branch_repository_or_framework_may_enter_common_stage_semantics') is not False: failures.append('external_execution_identity_leak_not_blocked')
    if c.get('product_governance_selection_applicability')!='REQUIRED_FOR_PRODUCT_STAGE_EXECUTION': failures.append('current_governance_selection_applicability_drift')
    if c.get('current_governance_mode_activation_field')!='governance_execution_mode' or c.get('current_governance_mode_activation_value')!='CURRENT_VALIDATED_GOVERNANCE': failures.append('current_governance_mode_activation_contract_drift')
    if c.get('selected_governance_artifact_type')!='PRODUCT_SELECTED_CURRENT_GOVERNANCE' or c.get('selected_governance_status')!='SELECTED_EXACT_CURRENT_SNAPSHOT' or c.get('selected_governance_selection_mode')!='EXACT_CURRENT_GOVERNANCE_SNAPSHOT': failures.append('selected_current_governance_contract_drift')
    if c.get('governance_source_checkout_exact_commit_required') is not True or c.get('loaded_governance_registry_must_equal_selected_checkout_registry') is not True: failures.append('selected_current_governance_exact_checkout_not_enforced')
    if c.get('external_human_or_account_precondition') is not False: failures.append('external_human_or_account_precondition_present')
    if c.get('moving_governance_branch_ref_may_grant_product_execution_credit') is not False: failures.append('moving_governance_ref_credit_not_blocked')
    if c.get('product_stage_workflow_governance_checkout_mode')!='EXACT_SELECTED_CURRENT_COMMIT_ONLY': failures.append('current_governance_checkout_mode_drift')
    if c.get('current_governance_load_receipt_artifact_type')!='PRODUCT_CURRENT_GOVERNANCE_LOAD_RECEIPT': failures.append('current_governance_load_receipt_identity_drift')
    if c.get('current_governance_load_receipt_filename')!='PRODUCT_CURRENT_GOVERNANCE_LOAD_RECEIPT.yaml' or c.get('current_governance_load_receipt_status')!='PASS': failures.append('current_governance_load_receipt_contract_drift')
    if c.get('application_baseline_source_branch_may_be_auto_selected') is not False: failures.append('external_baseline_source_auto_selection_not_blocked')
    if c.get('application_baseline_materialization_product_stage_completion_credit')!=0: failures.append('external_admission_completion_credit_nonzero')
    legacy_keys=(
        'external_precondition_applicability',
        'common_stage_execution_outside_released_governance_mode_blocked_by_this_contract',
        'released_governance_mode_activation_field',
        'released_governance_mode_activation_value',
        'absence_of_explicit_released_governance_mode_selection',
        'candidate_current_governance_may_drive_common_stage_when_released_mode_not_selected',
        'candidate_governance_released_mode_admission_credit',
        'product_released_governance_load_receipt_artifact_type',
        'product_released_governance_load_receipt_filename',
    )
    if any(k in c for k in legacy_keys): failures.append('legacy_released_governance_semantics_present')
    return {'status':'PASS' if not failures else 'FAIL','failures':failures}
if __name__=='__main__':
    out=validate(); print(yaml.safe_dump(out,sort_keys=False),end=''); raise SystemExit(0 if out['status']=='PASS' else 1)
