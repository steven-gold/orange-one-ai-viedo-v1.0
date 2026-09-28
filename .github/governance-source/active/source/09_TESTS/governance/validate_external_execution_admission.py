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
    if scope.get('layer_classification')!='EXTERNAL_PRODUCT_EXECUTION_ENVIRONMENT_ADMISSION' or scope.get('reusable_page_stage_normative_denominator_inclusion')!='EXCLUDED' or scope.get('reusable_page_stage_definition_credit')!=0 or scope.get('reusable_page_stage_completion_credit')!=0: failures.append('external_execution_admission_scope_isolation_missing')
    contracts=admission.get('product_execution_admission_contracts') or {}
    if set(contracts)!={'PRODUCT_GOVERNANCE_RELEASE_SELECTION_AND_APPLICATION_BASELINE'}: failures.append('external_execution_admission_contract_set_drift')
    c=contracts.get('PRODUCT_GOVERNANCE_RELEASE_SELECTION_AND_APPLICATION_BASELINE') or {}
    if c.get('scope_class')!='EXTERNAL_PRODUCT_EXECUTION_ENVIRONMENT_ADMISSION' or c.get('reusable_page_stage_normative_denominator_inclusion')!='EXCLUDED': failures.append('external_execution_admission_contract_scope_invalid')
    if c.get('product_specific_branch_repository_or_framework_may_enter_common_stage_semantics') is not False: failures.append('external_execution_identity_leak_not_blocked')
    if c.get('external_precondition_applicability')!='CONDITIONAL_WHEN_PRODUCT_EXECUTION_EXPLICITLY_SELECTS_RELEASED_GOVERNANCE_MODE' or c.get('common_stage_execution_outside_released_governance_mode_blocked_by_this_contract') is not False: failures.append('released_governance_mode_applicability_not_isolated')
    if c.get('application_baseline_source_branch_may_be_auto_selected') is not False: failures.append('external_baseline_source_auto_selection_not_blocked')
    if c.get('candidate_governance_formal_product_execution_credit')!=0 or c.get('application_baseline_materialization_product_stage_completion_credit')!=0: failures.append('external_admission_completion_credit_nonzero')
    if c.get('product_released_governance_load_receipt_artifact_type')!='PRODUCT_RELEASED_GOVERNANCE_LOAD_RECEIPT': failures.append('external_product_governance_receipt_identity_not_isolated')
    if c.get('product_released_governance_load_receipt_filename')!='PRODUCT_RELEASED_GOVERNANCE_LOAD_RECEIPT.yaml': failures.append('external_product_governance_receipt_filename_not_isolated')
    if any(k in c for k in ('governance_load_receipt_artifact_type','governance_load_receipt_filename','governance_load_receipt_required_fields','governance_load_receipt_status')): failures.append('external_product_governance_receipt_legacy_collision_present')
    return {'status':'PASS' if not failures else 'FAIL','failures':failures}
if __name__=='__main__':
    out=validate(); print(yaml.safe_dump(out,sort_keys=False),end=''); raise SystemExit(0 if out['status']=='PASS' else 1)
