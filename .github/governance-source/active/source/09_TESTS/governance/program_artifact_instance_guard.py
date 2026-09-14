#!/usr/bin/env python3
from pathlib import Path
import json,re,yaml,hashlib,sys,copy
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
SEMANTIC_BASELINE_CONTENT_HASH='e7e1eec7d4beb8f78f901d403c2494e62c1e9e117b97a09a5f56c13f6971bab1'
IDENTITY_REGISTRY_UID='REG-PROGRAM-IDENTITY-AUTHORITY-001'

def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def hobj(d):
    x=copy.deepcopy(d); x.pop('content_hash',None)
    return hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True,width=180).encode()).hexdigest()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def effective_normative_set_hash(common_bundles,stage_refs,item_refs):
    payload={'common_normative_bundle_refs':list(common_bundles or []),'stage_normative_section_uids':list(stage_refs or []),'item_specific_normative_section_uids':list(item_refs or [])}
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def expected_receipt_uid(work_unit_uid,governance_revision,normative_hash):
    raw=f'{work_unit_uid}|{governance_revision}|{normative_hash}|{SEMANTIC_BASELINE_CONTENT_HASH}'
    return 'GLR-'+hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
def expected_binding_uid(program_artifact_uid,work_unit_uid,canonical_path,current_hash):
    raw=f'{program_artifact_uid}|{work_unit_uid}|{canonical_path}|{current_hash}'
    return 'WTB-'+hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
def _nonempty(v):
    if v is None: return False
    if isinstance(v,str): return bool(v.strip())
    if isinstance(v,(list,dict,set,tuple)): return len(v)>0
    return True

def _identity_records(root):
    p=root/'10_REGISTRY/PROGRAM_IDENTITY_AUTHORITY_REGISTRY.yaml'
    if not p.exists(): return [],['typed_identity_authority_registry_missing']
    d=load(p); failures=[]
    if d.get('registry_uid')!=IDENTITY_REGISTRY_UID: failures.append('typed_identity_authority_registry_uid_invalid')
    if (d.get('policy') or {}).get('register_before_generation') is not True: failures.append('typed_identity_register_before_generation_not_true')
    rows=d.get('identities') or []; seen={}
    for r in rows:
        u=r.get('uid')
        if not u: failures.append('typed_identity_uid_missing'); continue
        if u in seen: failures.append('typed_identity_uid_duplicate:'+str(u))
        seen[u]=r
        if r.get('status') not in {'PLANNED','CURRENT','SUPERSEDED','RETIRED'}: failures.append('typed_identity_status_invalid:'+str(u))
    return rows,failures

def _resolve(identity_map, uid, expected_types, failures, field):
    exp=set(expected_types if isinstance(expected_types,(list,tuple,set)) else [expected_types])
    rec=identity_map.get(uid)
    if rec is None:
        failures.append(f'typed_reference_unresolved:{field}:{uid}'); return None
    if rec.get('identity_type') not in exp:
        failures.append(f'typed_reference_wrong_type:{field}:{uid}:{rec.get("identity_type")}'); return None
    if rec.get('status') not in {'PLANNED','CURRENT'}:
        failures.append(f'typed_reference_not_current_or_planned:{field}:{uid}:{rec.get("status")}'); return None
    return rec

def validate_instance(program_artifact, manifest, root=ROOT):
    failures=[]
    idx=load(root/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'); ref=load(root/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml')
    life=load(root/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'); bpr=load(root/'10_REGISTRY/BLUEPRINT_REGISTRY.yaml'); rm=load(root/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml')
    baseline=load(root/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml')
    pa=program_artifact or {}; man=manifest or {}

    if baseline.get('content_hash')!=SEMANTIC_BASELINE_CONTENT_HASH or hobj(baseline)!=SEMANTIC_BASELINE_CONTENT_HASH:
        failures.append('semantic_authority_baseline_invalid_or_mutated')

    rows,id_fail=_identity_records(root); failures += id_fail
    identity_map={r.get('uid'):r for r in rows if r.get('uid')}

    pa_req=(idx.get('program_artifact_contract') or {}).get('required_fields') or []
    for f in pa_req:
        if f not in pa: failures.append('program_artifact_field_missing:'+f)
    scalar_required=['program_artifact_uid','work_unit_uid','page_uid_or_scope_uid','construction_profile','canonical_name','canonical_path','canonical_filename','owner_uid','producer_stage_uid','acceptance_audit_blueprint_ref','current_hash','status','governance_load_receipt_ref','write_target_binding_ref']
    for f in scalar_required:
        if not _nonempty(pa.get(f)): failures.append('program_artifact_field_empty:'+f)
    for f in ['input_artifact_refs','required_normative_section_uids','dependency_refs','reverse_dependency_refs','required_test_refs']:
        if f in pa and not isinstance(pa.get(f),list): failures.append('program_artifact_field_not_list:'+f)
    if 'profile_contracts' in pa and not isinstance(pa.get('profile_contracts'),dict): failures.append('profile_contracts_not_mapping')

    uid=pa.get('program_artifact_uid',''); name=pa.get('canonical_name',''); path=pa.get('canonical_path',''); fn=pa.get('canonical_filename',''); profile=pa.get('construction_profile')
    if not re.fullmatch(r'PA-[A-Z0-9]+(?:-[A-Z0-9]+)*-[0-9]{3}',str(uid)): failures.append('program_artifact_uid_format_invalid')
    if not re.fullmatch(r'[A-Z][A-Z0-9_]*',str(name)): failures.append('canonical_name_not_upper_snake_case')
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9._:-]*',str(pa.get('work_unit_uid',''))): failures.append('work_unit_uid_invalid')
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9._:-]*',str(pa.get('page_uid_or_scope_uid',''))): failures.append('page_uid_or_scope_uid_invalid')
    if not isinstance(path,str) or not path or '..' in path or path.startswith('/') or '//' in path or '\\' in path: failures.append('canonical_path_unsafe')
    if Path(path).name!=fn: failures.append('canonical_filename_path_basename_mismatch')
    tokens=set(re.split(r'[^a-z0-9]+',str(fn).lower()))
    if tokens.intersection(set(idx.get('forbidden_filename_tokens') or [])): failures.append('canonical_filename_forbidden_token')

    profiles=idx.get('program_construction_profiles') or {}
    prof=profiles.get(profile)
    if not prof: failures.append('construction_profile_unknown')
    else:
        if profile=='TEST_IMPLEMENTATION' and not str(path).startswith('tests/'): failures.append('canonical_path_profile_root_mismatch')
        elif profile=='DATABASE_MIGRATION' and not str(path).startswith('migrations/'): failures.append('canonical_path_profile_root_mismatch')
        elif profile not in ('TEST_IMPLEMENTATION','DATABASE_MIGRATION') and not str(path).startswith('src/'): failures.append('canonical_path_profile_root_mismatch')
        ext=Path(str(fn)).suffix.lower()
        allowed=set(prof.get('allowed_file_extensions') or [])
        if not allowed or ext not in allowed: failures.append('profile_file_class_not_allowed:'+str(profile)+':'+ext)
        contracts=pa.get('profile_contracts') if isinstance(pa.get('profile_contracts'),dict) else {}
        for c in prof.get('mandatory_contracts') or []:
            if c in pa:
                continue  # explicit top-level governed contract such as dependency_refs
            if c not in contracts: failures.append('profile_mandatory_contract_missing:'+str(profile)+':'+str(c))
            elif contracts.get(c) in (None,'',[],{}): failures.append('profile_mandatory_contract_empty:'+str(profile)+':'+str(c))

    stages={s.get('stage_uid') for s in life.get('stages') or []}
    if pa.get('producer_stage_uid') not in stages: failures.append('producer_stage_uid_unknown')
    bp_uids={x.get('blueprint_uid') for x in bpr.get('current_governance_blueprints') or []}
    if pa.get('acceptance_audit_blueprint_ref') not in bp_uids: failures.append('acceptance_audit_blueprint_unknown')
    h=str(pa.get('current_hash',''))
    if not re.fullmatch(r'[0-9a-fA-F]{64}',h): failures.append('current_hash_invalid')
    if not pa.get('required_test_refs'): failures.append('required_test_refs_empty')
    if pa.get('status') not in {'PLANNED','CURRENT','SUPERSEDED','RETIRED'}: failures.append('program_artifact_status_invalid')

    # Authoritative typed identity resolution. Program artifact registration is the write-target authority.
    pa_auth=_resolve(identity_map,uid,'PROGRAM_ARTIFACT',failures,'program_artifact_uid') if uid else None
    _resolve(identity_map,pa.get('work_unit_uid'),'WORK_UNIT',failures,'work_unit_uid')
    _resolve(identity_map,pa.get('page_uid_or_scope_uid'),'PAGE_OR_SCOPE',failures,'page_uid_or_scope_uid')
    _resolve(identity_map,pa.get('owner_uid'),'OWNER',failures,'owner_uid')
    for x in pa.get('dependency_refs') or []: _resolve(identity_map,x,'PROGRAM_ARTIFACT',failures,'dependency_refs')
    for x in pa.get('reverse_dependency_refs') or []: _resolve(identity_map,x,'PROGRAM_ARTIFACT',failures,'reverse_dependency_refs')
    for x in pa.get('required_test_refs') or []: _resolve(identity_map,x,'TEST',failures,'required_test_refs')
    for x in pa.get('input_artifact_refs') or []: _resolve(identity_map,x,['INPUT_ARTIFACT','PROGRAM_ARTIFACT'],failures,'input_artifact_refs')
    if pa_auth:
        for k in ['canonical_name','canonical_path','canonical_filename','construction_profile','work_unit_uid','page_uid_or_scope_uid','owner_uid','producer_stage_uid']:
            if pa_auth.get(k)!=pa.get(k): failures.append('program_artifact_preregistration_binding_mismatch:'+k)
        reserved=set((idx.get('framework_reserved_filename_policy') or {}).get('examples') or [])
        if fn in reserved and pa_auth.get('framework_reserved_filename_allowed') is not True:
            failures.append('framework_reserved_filename_not_explicitly_preregistered:'+str(fn))

    # Artifact-specific refs must be independently anchored by immutable profile minima.
    sec=load(root/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'); sections=set()
    for doc in sec.get('documents') or []:
        for s in doc.get('sections') or []: sections.add(s.get('section_uid'))
    item_refs=pa.get('required_normative_section_uids') or []
    for s in item_refs:
        if s not in sections: failures.append('program_artifact_normative_section_unresolved:'+str(s))
    minimum=((baseline.get('program_artifact_item_specific_minimum_rules') or {}).get(profile) or [])
    if minimum and not set(minimum).issubset(set(item_refs)): failures.append('program_artifact_item_specific_semantic_minimum_missing')

    # Implementation Manifest required fields are executed, not merely declared.
    man_req=(idx.get('implementation_manifest_contract') or {}).get('required_fields') or []
    for f in man_req:
        if f not in man: failures.append('implementation_manifest_field_missing:'+f)
    for f in ['work_unit_uid','governance_revision','design_freeze_ref','dependency_closure_ref','acceptance_audit_blueprint_ref','naming_registry_ref','section_registry_ref','protected_current_artifact_registry_ref','governance_load_receipt_ref','typed_identity_registry_ref']:
        if not _nonempty(man.get(f)): failures.append('implementation_manifest_field_empty:'+f)
    for f in ['program_artifacts','common_normative_bundle_refs','stage_normative_section_uids','item_specific_normative_section_uids','write_target_bindings']:
        if f in man and not isinstance(man.get(f),list): failures.append('implementation_manifest_field_not_list:'+f)
    if isinstance(man.get('program_artifacts'),list) and len(man['program_artifacts'])!=len(set(man['program_artifacts'])): failures.append('manifest_program_artifact_duplicate_uid')

    if man.get('governance_revision')!=rm.get('governance_revision'): failures.append('manifest_governance_revision_stale')
    if (man.get('program_artifacts') or []).count(pa.get('program_artifact_uid'))!=1: failures.append('manifest_program_artifact_binding_not_exactly_once')
    if man.get('acceptance_audit_blueprint_ref')!=pa.get('acceptance_audit_blueprint_ref'): failures.append('manifest_acceptance_blueprint_mismatch')
    if man.get('naming_registry_ref')!='REG-NAMING-001': failures.append('manifest_naming_registry_ref_invalid')
    if man.get('section_registry_ref')!='REG-NORMATIVE-SECTION-001': failures.append('manifest_section_registry_ref_invalid')
    if man.get('protected_current_artifact_registry_ref')!='REG-PROTECTED-CURRENT-ARTIFACT-001': failures.append('manifest_protected_registry_ref_invalid')
    if man.get('typed_identity_registry_ref')!=IDENTITY_REGISTRY_UID: failures.append('manifest_typed_identity_registry_ref_invalid')
    required_bundles=set(idx.get('mandatory_common_normative_bundles') or {})
    if set(man.get('common_normative_bundle_refs') or [])!=required_bundles: failures.append('manifest_common_bundle_set_invalid')
    expected_stage=((baseline.get('semantic_snapshot') or {}).get('stage_reference_rules') or {}).get(pa.get('producer_stage_uid'),{}).get('exact_required_normative_section_uids') or []
    if man.get('stage_normative_section_uids')!=expected_stage: failures.append('manifest_stage_normative_semantic_mismatch')
    if man.get('item_specific_normative_section_uids')!=item_refs: failures.append('manifest_item_specific_normative_mismatch')
    if minimum and not set(minimum).issubset(set(man.get('item_specific_normative_section_uids') or [])): failures.append('manifest_item_specific_semantic_minimum_missing')
    if man.get('work_unit_uid')!=pa.get('work_unit_uid'): failures.append('manifest_work_unit_binding_mismatch')

    receipt=man.get('governance_load_receipt') if isinstance(man.get('governance_load_receipt'),dict) else {}
    receipt_ref=man.get('governance_load_receipt_ref')
    if receipt_ref!=pa.get('governance_load_receipt_ref'): failures.append('artifact_manifest_governance_receipt_ref_mismatch')
    if not re.fullmatch(r'GLR-[A-Z0-9][A-Z0-9-]*',str(receipt_ref or '')): failures.append('governance_load_receipt_ref_invalid')
    if receipt.get('receipt_uid')!=receipt_ref: failures.append('governance_load_receipt_uid_mismatch')
    if receipt.get('status')!='PASS': failures.append('governance_load_receipt_not_pass')
    if receipt.get('work_unit_uid')!=pa.get('work_unit_uid'): failures.append('governance_load_receipt_work_unit_mismatch')
    if receipt.get('governance_revision')!=rm.get('governance_revision'): failures.append('governance_load_receipt_revision_stale')
    if receipt.get('semantic_baseline_content_hash')!=SEMANTIC_BASELINE_CONTENT_HASH: failures.append('governance_load_receipt_semantic_baseline_mismatch')
    expected_norm_hash=effective_normative_set_hash(man.get('common_normative_bundle_refs'),man.get('stage_normative_section_uids'),man.get('item_specific_normative_section_uids'))
    if receipt.get('effective_normative_set_hash')!=expected_norm_hash: failures.append('governance_load_receipt_effective_normative_set_hash_mismatch')
    deterministic_receipt=expected_receipt_uid(pa.get('work_unit_uid'),rm.get('governance_revision'),expected_norm_hash)
    if receipt_ref!=deterministic_receipt: failures.append('governance_load_receipt_uid_not_deterministically_bound')

    closure=man.get('dependency_closure') if isinstance(man.get('dependency_closure'),dict) else {}
    if closure.get('closure_uid')!=man.get('dependency_closure_ref'): failures.append('dependency_closure_uid_mismatch')
    if closure.get('program_artifact_uid')!=pa.get('program_artifact_uid'): failures.append('dependency_closure_artifact_mismatch')
    if closure.get('dependency_refs')!=(pa.get('dependency_refs') or []): failures.append('dependency_closure_dependency_mismatch')
    if closure.get('reverse_dependency_refs')!=(pa.get('reverse_dependency_refs') or []): failures.append('dependency_closure_reverse_dependency_mismatch')
    if closure.get('status')!='PASS': failures.append('dependency_closure_not_pass')
    if pa.get('program_artifact_uid') in (pa.get('dependency_refs') or []) or pa.get('program_artifact_uid') in (pa.get('reverse_dependency_refs') or []): failures.append('dependency_self_reference')

    bindings=[x for x in man.get('write_target_bindings') or [] if x.get('program_artifact_uid')==pa.get('program_artifact_uid')]
    if len(bindings)!=1: failures.append('write_target_binding_missing_or_duplicate')
    else:
        b=bindings[0]
        if b.get('binding_uid')!=pa.get('write_target_binding_ref'): failures.append('write_target_binding_uid_mismatch')
        if not re.fullmatch(r'WTB-[A-Z0-9][A-Z0-9-]*',str(pa.get('write_target_binding_ref') or '')): failures.append('write_target_binding_ref_invalid')
        deterministic_binding=expected_binding_uid(pa.get('program_artifact_uid'),pa.get('work_unit_uid'),pa.get('canonical_path'),pa.get('current_hash'))
        if pa.get('write_target_binding_ref')!=deterministic_binding: failures.append('write_target_binding_uid_not_deterministically_bound')
        for k in ['program_artifact_uid','work_unit_uid','page_uid_or_scope_uid','owner_uid','construction_profile','canonical_path','canonical_filename','producer_stage_uid']:
            if b.get(k)!=pa.get(k): failures.append('write_target_binding_mismatch:'+k)
        if b.get('expected_current_hash')!=pa.get('current_hash'): failures.append('write_target_binding_mismatch:expected_current_hash')

    if pa.get('status')=='CURRENT':
        fp=root/str(path)
        if not fp.exists() or not fp.is_file(): failures.append('current_program_artifact_physical_file_missing')
        elif re.fullmatch(r'[0-9a-fA-F]{64}',h) and sha(fp).lower()!=h.lower(): failures.append('current_program_artifact_physical_hash_mismatch')

    return {'status':'PASS' if not failures else 'FAIL','failures':failures}

def validate_definition(root=ROOT):
    failures=[]; idx=load(root/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml')
    refp=root/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'; bp=root/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'; idp=root/'10_REGISTRY/PROGRAM_IDENTITY_AUTHORITY_REGISTRY.yaml'
    if not refp.exists(): failures.append('reference_rule_registry_missing')
    if not idp.exists(): failures.append('typed_identity_authority_registry_missing')
    if not bp.exists(): failures.append('semantic_authority_baseline_missing')
    else:
        b=load(bp)
        if b.get('content_hash')!=SEMANTIC_BASELINE_CONTENT_HASH or hobj(b)!=SEMANTIC_BASELINE_CONTENT_HASH: failures.append('semantic_authority_baseline_invalid_or_mutated')
    if idx.get('reference_rule_registry_ref')!='REG-REFERENCE-RULE-001': failures.append('construction_index_reference_rule_binding_invalid')
    if idx.get('semantic_authority_baseline_ref')!='REG-SEMANTIC-AUTHORITY-BASELINE-001': failures.append('construction_index_semantic_baseline_binding_invalid')
    if idx.get('typed_identity_authority_registry_ref')!=IDENTITY_REGISTRY_UID: failures.append('construction_index_typed_identity_registry_binding_invalid')
    rows,id_fail=_identity_records(root); failures += id_fail
    ur=idx.get('universal_rules') or {}
    for key in ['program_artifact_instance_authority_required','semantic_authority_baseline_required','implementation_manifest_runtime_enforcement_required','governance_receipt_evidence_required','dependency_closure_evidence_required','current_physical_hash_verification_required','profile_mandatory_contract_runtime_enforcement_required','typed_runtime_reference_authority_resolution_required','manifest_program_artifact_uid_uniqueness_required','framework_reserved_filename_preregistration_required','profile_file_class_enforcement_required']:
        if ur.get(key) is not True: failures.append('required_universal_rule_not_true:'+key)
    pac=idx.get('program_artifact_contract') or {}; imc=idx.get('implementation_manifest_contract') or {}
    for f in ['program_artifact_uid','work_unit_uid','page_uid_or_scope_uid','construction_profile','canonical_name','canonical_path','canonical_filename','owner_uid','producer_stage_uid','acceptance_audit_blueprint_ref','current_hash','governance_load_receipt_ref','write_target_binding_ref','profile_contracts']:
        if f not in (pac.get('required_fields') or []): failures.append('instance_required_field_not_declared:'+f)
    for f in ['work_unit_uid','governance_revision','design_freeze_ref','program_artifacts','dependency_closure_ref','acceptance_audit_blueprint_ref','naming_registry_ref','section_registry_ref','protected_current_artifact_registry_ref','common_normative_bundle_refs','stage_normative_section_uids','item_specific_normative_section_uids','governance_load_receipt_ref','write_target_bindings','governance_load_receipt','dependency_closure','typed_identity_registry_ref']:
        if f not in (imc.get('required_fields') or []): failures.append('manifest_required_field_not_declared:'+f)
    for name,p in (idx.get('program_construction_profiles') or {}).items():
        if not p.get('mandatory_contracts'): failures.append('profile_mandatory_contracts_empty:'+name)
        if not p.get('allowed_file_extensions'): failures.append('profile_allowed_file_extensions_empty:'+name)
    return {'status':'PASS' if not failures else 'FAIL','identity_count':len(rows),'failures':failures}

if __name__=='__main__':
    out=validate_definition(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
