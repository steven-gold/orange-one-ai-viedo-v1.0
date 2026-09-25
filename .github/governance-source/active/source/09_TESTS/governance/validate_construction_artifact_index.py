#!/usr/bin/env python3
from pathlib import Path
import json, sys, yaml
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]

def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}

EXPECTED_ARTIFACT_UID='REG-CONSTRUCTION-ARTIFACT-001'
EXPECTED_CANONICAL_PATH='10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'
EXPECTED_STATUSES={'CURRENT_CANDIDATE','CANDIDATE_PREFORMAL'}
EXPECTED_REFERENCE_RULE_REGISTRY='REG-REFERENCE-RULE-001'
EXPECTED_SEMANTIC_BASELINE='REG-SEMANTIC-AUTHORITY-BASELINE-001'
EXPECTED_IDENTITY_REGISTRY='REG-PROGRAM-IDENTITY-AUTHORITY-001'

UNIVERSAL_TRUE=[
 'governance_load_receipt_required_before_execution','common_plus_specific_normative_load_required',
 'typed_uid_resolution_required','normative_section_uid_read_only','write_target_exact_binding_required',
 'register_before_generation','program_artifact_instance_authority_required','semantic_authority_baseline_required',
 'implementation_manifest_runtime_enforcement_required','governance_receipt_evidence_required',
 'dependency_closure_evidence_required','current_physical_hash_verification_required',
 'profile_mandatory_contract_runtime_enforcement_required','typed_runtime_reference_authority_resolution_required',
 'manifest_program_artifact_uid_uniqueness_required','framework_reserved_filename_preregistration_required',
 'profile_file_class_enforcement_required',
]
UNIVERSAL_BLOCK=[
 'stale_governance_load_receipt','undeclared_normative_reference_in_execution','unregistered_artifact_creation',
]
EXPECTED_UNIVERSAL={k:True for k in UNIVERSAL_TRUE}
EXPECTED_UNIVERSAL.update({k:'BLOCK' for k in UNIVERSAL_BLOCK})

EXPECTED_RECEIPT_TRUE=[
 'required_before_any_stage_operation','required_before_code_write','must_precede_execution_timestamp',
 'invalidate_on_governance_revision_change','invalidate_on_root_manifest_hash_change',
 'invalidate_on_section_registry_hash_change','invalidate_on_target_manifest_change',
]
EXPECTED_RECEIPT_FIELDS=[
 'receipt_uid','execution_uid','run_uid','work_unit_or_stage_operation_uid','governance_revision',
 'root_manifest_hash','section_registry_hash','target_manifest_hash','common_bundle_uids',
 'stage_normative_section_uids','profile_normative_section_uids','artifact_specific_normative_section_uids',
 'dependency_normative_section_uids','effective_normative_set_hash','resolved_section_receipts',
 'acceptance_audit_blueprint_ref','loaded_at','status',
]
EXPECTED_EFFECTIVE={'all_layers_required':True,'missing_common_bundle':'BLOCK','missing_item_specific_ref':'BLOCK'}
EXPECTED_WRITE_TARGET_TRUE=['actual_target_must_equal_registered_canonical_target','valid_other_registered_artifact_is_not_valid_target']
EXPECTED_WRITE_TARGET_BLOCK=[
 'normative_document_write_during_construction','governance_registry_write_during_construction',
 'unregistered_write_target','prewrite_hash_mismatch',
]
EXPECTED_CONTINUITY_EDGES=['edge_uid','from_artifact_uid','to_artifact_uid','relation_type','required']
EXPECTED_CLEANUP_STEPS=[
 'REGISTER_REPLACEMENT','BIND_REPLACEMENT','MIGRATE_FORWARD_DEPENDENCIES','MIGRATE_REVERSE_DEPENDENCIES',
 'MARK_PREDECESSOR_SUPERSEDED','APPEND_CLEANUP_LEDGER_EVENT','POST_DELETE_RESIDUAL_SCAN_IF_DELETE',
]
EXPECTED_ARTIFACT_FIELDS=[
 'program_artifact_uid','work_unit_uid','page_uid_or_scope_uid','construction_profile','canonical_name',
 'canonical_path','canonical_filename','owner_uid','producer_stage_uid','acceptance_audit_blueprint_ref',
 'current_hash','governance_load_receipt_ref','write_target_binding_ref','profile_contracts',
]
EXPECTED_MANIFEST_FIELDS=[
 'work_unit_uid','governance_revision','design_freeze_ref','program_artifacts','dependency_closure_ref',
 'acceptance_audit_blueprint_ref','naming_registry_ref','section_registry_ref',
 'protected_current_artifact_registry_ref','common_normative_bundle_refs','stage_normative_section_uids',
 'item_specific_normative_section_uids','governance_load_receipt_ref','write_target_bindings',
 'governance_load_receipt','dependency_closure','typed_identity_registry_ref',
]

def known_sections(root):
    reg=load(root/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'); out=set()
    for doc in reg.get('documents') or []:
        for s in doc.get('sections') or []:
            if s.get('section_uid'): out.add(s['section_uid'])
    return out

def validate(root=ROOT):
    failures=[]
    idxp=root/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'
    if not idxp.exists(): return {'status':'FAIL','failures':['construction_artifact_index_missing']}
    idx=load(idxp)
    idx_uid=idx.get('artifact_uid') or idx.get('registry_uid')
    if idx_uid!=EXPECTED_ARTIFACT_UID: failures.append('construction_artifact_index_uid_invalid')
    if idx.get('canonical_path')!=EXPECTED_CANONICAL_PATH: failures.append('construction_artifact_index_canonical_path_invalid')
    if idx.get('status') not in EXPECTED_STATUSES: failures.append('construction_artifact_index_not_candidate')
    if idx.get('reference_rule_registry_ref')!=EXPECTED_REFERENCE_RULE_REGISTRY: failures.append('construction_index_reference_rule_binding_invalid')
    if idx.get('semantic_authority_baseline_ref')!=EXPECTED_SEMANTIC_BASELINE: failures.append('construction_index_semantic_baseline_binding_invalid')
    if idx.get('typed_identity_authority_registry_ref')!=EXPECTED_IDENTITY_REGISTRY: failures.append('construction_index_typed_identity_registry_binding_invalid')

    bp=root/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'
    if not bp.exists(): return {'status':'FAIL','failures':failures+['semantic_authority_baseline_missing']}
    snap=(load(bp).get('semantic_snapshot') or {})

    # Immutable-baseline anchor: profiles / bundles must equal the semantic snapshot exactly.
    prules=snap.get('program_profile_reference_rules') or {}
    profiles=idx.get('program_construction_profiles') or {}
    if set(prules)!=set(profiles): failures.append('profile_reference_rule_set_mismatch')
    known=known_sections(root)
    for name,p in profiles.items():
        exp=prules.get(name) or {}
        if not exp: failures.append('profile_reference_rule_unknown:'+str(name)); continue
        if p.get('rule_uid')!=exp.get('rule_uid'): failures.append('profile_rule_uid_mismatch:'+str(name))
        actual=p.get('required_normative_section_uids') or []
        if actual!=list(exp.get('exact_required_normative_section_uids') or []): failures.append('profile_semantic_reference_mismatch:'+str(name))
        for uid in actual:
            if uid not in known: failures.append('profile_semantic_section_unresolved:'+str(name)+':'+str(uid))
        if not p.get('mandatory_contracts'): failures.append('profile_mandatory_contracts_empty:'+str(name))
        if not p.get('allowed_file_extensions'): failures.append('profile_allowed_file_extensions_empty:'+str(name))

    brules=snap.get('common_bundle_reference_rules') or {}
    bundles=idx.get('mandatory_common_normative_bundles') or {}
    if set(brules)!=set(bundles): failures.append('common_bundle_reference_rule_set_mismatch')
    for bid,b in bundles.items():
        exp=brules.get(bid) or {}
        if not exp: failures.append('common_bundle_reference_rule_unknown:'+str(bid)); continue
        if b.get('rule_uid')!=exp.get('rule_uid'): failures.append('common_bundle_rule_uid_mismatch:'+str(bid))
        actual=b.get('section_uids') or []
        if actual!=list(exp.get('exact_section_uids') or []): failures.append('common_bundle_semantic_reference_mismatch:'+str(bid))
        if not actual: failures.append('common_bundle_empty:'+str(bid))
        for uid in actual:
            if uid not in known: failures.append('common_bundle_semantic_section_unresolved:'+str(bid)+':'+str(uid))

    ur=idx.get('universal_rules') or {}
    for k,v in EXPECTED_UNIVERSAL.items():
        if ur.get(k)!=v: failures.append('universal_execution_load_rule_invalid:'+k)

    eff=idx.get('effective_normative_set_contract') or {}
    for k,v in EXPECTED_EFFECTIVE.items():
        if eff.get(k)!=v: failures.append('effective_normative_set_contract_invalid:'+k)

    gr=idx.get('governance_load_receipt_contract') or {}
    for k in EXPECTED_RECEIPT_TRUE:
        if gr.get(k) is not True: failures.append('load_receipt_contract_not_true:'+k)
    if list(gr.get('required_fields') or [])!=EXPECTED_RECEIPT_FIELDS: failures.append('load_receipt_required_fields_invalid')
    if gr.get('deterministic_receipt_uid_required') is not True: failures.append('load_receipt_not_deterministic')

    tr=idx.get('typed_uid_resolution_contract') or {}
    if tr.get('exactly_one_resolution_required') is not True: failures.append('typed_uid_resolution_not_exact')
    if tr.get('free_text_or_fuzzy_fallback')!='BLOCK': failures.append('fuzzy_uid_resolution_not_block')
    types=tr.get('uid_types') or {}
    for uid,rec in types.items():
        if not isinstance(rec,dict) or 'write_target' not in rec: failures.append('typed_uid_write_target_undeclared:'+str(uid))
    if (types.get('NORMATIVE_SECTION_UID') or {}).get('write_target') is not False: failures.append('normative_section_write_target_not_false')

    wt=idx.get('write_target_lock_contract') or {}
    for k in EXPECTED_WRITE_TARGET_TRUE:
        if wt.get(k) is not True: failures.append('write_target_contract_not_true:'+k)
    for k in EXPECTED_WRITE_TARGET_BLOCK:
        if wt.get(k)!='BLOCK': failures.append('write_target_block_missing:'+k)

    pac=idx.get('program_artifact_contract') or {}
    for f in EXPECTED_ARTIFACT_FIELDS:
        if f not in (pac.get('required_fields') or []): failures.append('instance_required_field_not_declared:'+f)
    if pac.get('register_before_generation')!='BLOCK': failures.append('register_before_generation_not_block')

    imc=idx.get('implementation_manifest_contract') or {}
    if imc.get('required_before_code_write') is not True: failures.append('implementation_manifest_before_code_not_required')
    for f in EXPECTED_MANIFEST_FIELDS:
        if f not in (imc.get('required_fields') or []): failures.append('manifest_required_field_not_declared:'+f)

    cc=idx.get('continuity_contract') or {}
    if list(cc.get('required_edge_fields') or [])!=EXPECTED_CONTINUITY_EDGES: failures.append('continuity_required_edge_fields_invalid')
    if cc.get('forward_and_reverse_edge_required') is not True: failures.append('continuity_reverse_edge_not_required')
    if cc.get('unresolved_required_edge')!='BLOCK': failures.append('continuity_unresolved_required_edge_not_block')

    sct=idx.get('supersession_cleanup_transaction') or {}
    if list(sct.get('ordered_steps') or [])!=EXPECTED_CLEANUP_STEPS: failures.append('supersession_cleanup_transaction_invalid')
    if sct.get('atomic') is not True: failures.append('supersession_cleanup_not_atomic')

    cpp=idx.get('canonical_path_policy') or {}
    if not cpp.get('forbidden_path_patterns'): failures.append('canonical_path_policy_empty')
    if cpp.get('relative_only') is not True: failures.append('canonical_path_not_relative_only')

    if not idx.get('forbidden_filename_tokens'): failures.append('forbidden_filename_tokens_empty')

    frfp=idx.get('framework_reserved_filename_policy') or {}
    if frfp.get('preregistration_required') is not True: failures.append('framework_reserved_preregistration_not_required')
    if not frfp.get('examples'): failures.append('framework_reserved_examples_empty')

    return {'status':'PASS' if not failures else 'FAIL','profiles':len(profiles),'bundles':len(bundles),'failures':failures}

if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
