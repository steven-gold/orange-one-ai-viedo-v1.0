#!/usr/bin/env python3
from pathlib import Path
import json,re,sys,yaml
ROOT=Path(__file__).resolve().parents[2]
INDEX=ROOT/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'
SECTIONS=ROOT/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'
PROTECTED=ROOT/'10_REGISTRY/PROTECTED_CURRENT_ARTIFACT_REGISTRY.yaml'
EXPECTED_PROFILES={'UI_COMPONENT','CONTROL_HANDLER','API_ENTRY','RUNTIME_SERVICE','REPOSITORY_DATA_ACCESS','DATABASE_MIGRATION','ASYNC_WORKER','EXTERNAL_ADAPTER','TEST_IMPLEMENTATION'}
EXPECTED_TRUE=['register_before_generation','profile_mandatory_contract_runtime_enforcement_required','typed_runtime_reference_authority_resolution_required','manifest_program_artifact_uid_uniqueness_required','framework_reserved_filename_preregistration_required','profile_file_class_enforcement_required','index_first_loading','lazy_load_exact_refs_only','reverse_dependency_update_required','normative_reference_by_section_uid_only','cleanup_requires_protected_registry_preload','cleanup_fail_closed','governance_load_receipt_required_before_execution','common_plus_specific_normative_load_required','typed_uid_resolution_required','normative_section_uid_read_only','write_target_exact_binding_required','semantic_reference_authority_required','program_artifact_instance_authority_required']
EXPECTED_BLOCK={'unregistered_artifact_creation','duplicate_current_owner','unresolved_reference','cross_layer_invention','cross_page_handoff_without_contract','superseded_current_residual','generated_filename_guessing','free_text_heading_reference','unsafe_relative_path','stale_governance_load_receipt','undeclared_normative_reference_in_execution','free_string_validator_identity','unregistered_audit_review_blueprint_type'}
REQUIRED_FORBIDDEN={'new','final','latest','fixed','backup','copy','temp','old'}
CLEANUP_STEPS=['REGISTER_REPLACEMENT','RESOLVE_FORWARD_REFERENCES','RESOLVE_REVERSE_DEPENDENCIES','MARK_IMPACTED_CONSUMERS_REVERIFY_REQUIRED','PROVE_ZERO_CURRENT_REFERENCE_TO_SUPERSEDED_OWNER','REMOVE_SUPERSEDED_FROM_CURRENT_INDEX','DELETE_GENERATED_DUPLICATE_TEMP_BACKUP_OR_OBSOLETE_ARTIFACTS','UPDATE_NAMING_OWNER_ARTIFACT_DEPENDENCY_INDEXES','UPDATE_CLEANUP_LEDGER','RUN_ORPHAN_RESIDUAL_BROKEN_REFERENCE_SCAN']
EDGE_FIELDS=['edge_uid','producer_uid','producer_hash','consumer_uid','consumer_stage_uid','edge_type','handoff_or_contract_ref']
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def validate(root=ROOT):
    failures=[]
    idxp=root/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'; secp=root/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'; pp=root/'10_REGISTRY/PROTECTED_CURRENT_ARTIFACT_REGISTRY.yaml'
    if not idxp.exists(): return {'status':'FAIL','failures':['construction_artifact_index_missing']}
    if not secp.exists(): return {'status':'FAIL','failures':['section_registry_missing']}
    if not pp.exists(): return {'status':'FAIL','failures':['protected_registry_missing']}
    d=load(idxp); sec=load(secp)
    rules=d.get('universal_rules') or {}
    for k in EXPECTED_TRUE:
        if rules.get(k) is not True: failures.append('rule_not_true:'+k)
    for k in EXPECTED_BLOCK:
        if rules.get(k)!='BLOCK': failures.append('rule_not_block:'+k)
    toks=set(d.get('forbidden_filename_tokens') or [])
    if not REQUIRED_FORBIDDEN.issubset(toks): failures.append('forbidden_filename_tokens_incomplete')
    if d.get('section_registry_ref')!='REG-NORMATIVE-SECTION-001': failures.append('section_registry_ref_invalid')
    if d.get('protected_current_artifact_registry_ref')!='REG-PROTECTED-CURRENT-ARTIFACT-001': failures.append('protected_registry_ref_invalid')
    if d.get('root_manifest_ref')!='REG-GOVERNANCE-ROOT-MANIFEST-001': failures.append('root_manifest_ref_invalid')
    if d.get('reference_rule_registry_ref')!='REG-REFERENCE-RULE-001': failures.append('reference_rule_registry_ref_invalid')
    if d.get('typed_identity_authority_registry_ref')!='REG-PROGRAM-IDENTITY-AUTHORITY-001': failures.append('typed_identity_authority_registry_ref_invalid')
    idp=root/'10_REGISTRY/PROGRAM_IDENTITY_AUTHORITY_REGISTRY.yaml'
    if not idp.exists(): failures.append('typed_identity_authority_registry_missing')
    sections={}
    for doc in sec.get('documents') or []:
        for s in doc.get('sections') or []: sections[s.get('section_uid')]=s
    profiles=d.get('program_construction_profiles') or {}
    if set(profiles)!=EXPECTED_PROFILES: failures.append('program_profile_set_invalid')
    for name,p in profiles.items():
        refs=p.get('required_normative_section_uids') or []
        if not refs: failures.append('profile_normative_refs_empty:'+name)
        for uid in refs:
            rec=sections.get(uid)
            if not rec: failures.append(f'profile_section_uid_unresolved:{name}:{uid}'); continue
            path=root/rec.get('path','')
            if not path.exists(): failures.append(f'profile_section_doc_missing:{name}:{uid}'); continue
            text=path.read_text(encoding='utf-8')
            if f'<!-- SECTION_UID: {uid} -->' not in text: failures.append(f'profile_section_anchor_missing:{name}:{uid}')
        if not p.get('mandatory_contracts'): failures.append('profile_mandatory_contracts_empty:'+name)
        if not p.get('allowed_file_extensions'): failures.append('profile_allowed_file_extensions_empty:'+name)
    pac=d.get('program_artifact_contract') or {}
    req=set(pac.get('required_fields') or [])
    for f in ['profile_contracts','program_artifact_uid','canonical_path','canonical_filename','owner_uid','construction_profile','required_normative_section_uids','dependency_refs','reverse_dependency_refs','acceptance_audit_blueprint_ref','governance_load_receipt_ref','write_target_binding_ref','current_hash','status']:
        if f not in req: failures.append('program_artifact_field_missing:'+f)
    im=d.get('implementation_manifest_contract') or {}
    if im.get('required_before_code_write') is not True: failures.append('manifest_not_required_before_code')
    for f in ['typed_identity_registry_ref','work_unit_uid','program_artifacts','dependency_closure_ref','acceptance_audit_blueprint_ref','naming_registry_ref','section_registry_ref','protected_current_artifact_registry_ref','common_normative_bundle_refs','stage_normative_section_uids','item_specific_normative_section_uids','governance_load_receipt_ref','write_target_bindings']:
        if f not in (im.get('required_fields') or []): failures.append('implementation_manifest_field_missing:'+f)
    bundles=d.get('mandatory_common_normative_bundles') or {}
    if set(bundles)!={'BUNDLE-GOV-COMMON-CORE','BUNDLE-GOV-CONSTRUCTION-BASE','BUNDLE-GOV-AUDIT-BASE'}: failures.append('mandatory_common_bundle_set_invalid')
    for bid,b in bundles.items():
        refs=b.get('section_uids') or []
        if not refs: failures.append('mandatory_common_bundle_empty:'+bid)
        for uid in refs:
            rec=sections.get(uid)
            if not rec: failures.append('mandatory_common_section_unresolved:'+bid+':'+uid)
    ens=d.get('effective_normative_set_contract') or {}
    if ens.get('all_layers_required') is not True: failures.append('effective_normative_layers_not_required')
    if ens.get('missing_common_bundle')!='BLOCK': failures.append('missing_common_bundle_not_block')
    if ens.get('missing_item_specific_ref')!='BLOCK': failures.append('missing_item_specific_not_block')
    gl=d.get('governance_load_receipt_contract') or {}
    for k in ['required_before_any_stage_operation','required_before_code_write','must_precede_execution_timestamp','invalidate_on_governance_revision_change','invalidate_on_root_manifest_hash_change','invalidate_on_section_registry_hash_change','invalidate_on_target_manifest_change']:
        if gl.get(k) is not True: failures.append('governance_load_receipt_rule_not_true:'+k)
    tr=d.get('typed_uid_resolution_contract') or {}
    if tr.get('exactly_one_resolution_required') is not True: failures.append('typed_uid_resolution_not_exact')
    if tr.get('free_text_or_fuzzy_fallback')!='BLOCK': failures.append('typed_uid_fuzzy_fallback_not_block')
    if ((tr.get('uid_types') or {}).get('NORMATIVE_SECTION_UID') or {}).get('write_target') is not False: failures.append('normative_uid_write_target_not_false')
    wt=d.get('write_target_lock_contract') or {}
    if wt.get('actual_target_must_equal_registered_canonical_target') is not True: failures.append('write_target_exact_match_not_required')
    if wt.get('valid_other_registered_artifact_is_not_valid_target') is not True: failures.append('other_registered_artifact_target_not_blocked')
    for k in ['normative_document_write_during_construction','governance_registry_write_during_construction','unregistered_write_target','prewrite_hash_mismatch']:
        if wt.get(k)!='BLOCK': failures.append('write_target_block_missing:'+k)
    cont=d.get('continuity_contract') or {}
    if cont.get('required_edge_fields')!=EDGE_FIELDS: failures.append('continuity_edge_fields_changed')
    if cont.get('forward_and_reverse_edge_required') is not True: failures.append('forward_reverse_not_required')
    if cont.get('unresolved_required_edge')!='BLOCK': failures.append('unresolved_edge_not_block')
    if cont.get('changed_producer_hash_marks_consumers')!='REVERIFY_REQUIRED': failures.append('changed_hash_not_reverify')
    sc=d.get('supersession_cleanup_transaction') or {}
    if sc.get('applies_to')!='ALL_CURRENT_ARTIFACT_TYPES': failures.append('cleanup_not_universal')
    if sc.get('ordered_steps')!=CLEANUP_STEPS: failures.append('cleanup_steps_incomplete_or_reordered')
    cond=sc.get('completion_conditions') or {}
    for k in ['current_reference_to_superseded_owner','duplicate_current_owner','orphan_required_artifact','unjustified_residual_file','broken_reference']:
        if cond.get(k)!=0: failures.append('cleanup_completion_not_zero:'+k)
    cp=d.get('canonical_path_policy') or {}
    for k,v in cp.items():
        if k=='forbidden_path_patterns': continue
        if isinstance(v,str) and ('../' in v or '\\..\\' in v): failures.append('unsafe_canonical_path_template:'+k)
    forbidden=cp.get('forbidden_path_patterns') or []
    if '../' not in forbidden: failures.append('unsafe_relative_path_pattern_not_forbidden')
    return {'status':'PASS' if not failures else 'FAIL','profiles':len(profiles),'resolved_section_refs':sum(len(p.get('required_normative_section_uids') or []) for p in profiles.values()),'failures':failures}
if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
