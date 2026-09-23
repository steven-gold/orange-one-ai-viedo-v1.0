#!/usr/bin/env python3
from pathlib import Path
import json, re, sys, yaml, hashlib
ROOT=Path(__file__).resolve().parents[2]
_YAML_CACHE={}
_TEXT_CACHE={}
_INSTANCE_GUARD=None

def _bytes(p): return Path(p).read_bytes()
def load(p):
    raw=_bytes(p); key=hashlib.sha256(raw).digest()
    if key not in _YAML_CACHE: _YAML_CACHE[key]=yaml.safe_load(raw.decode('utf-8')) or {}
    return _YAML_CACHE[key]
def text(p):
    raw=_bytes(p); key=hashlib.sha256(raw).digest()
    if key not in _TEXT_CACHE: _TEXT_CACHE[key]=raw.decode('utf-8')
    return _TEXT_CACHE[key]
def sha256_file(p): return hashlib.sha256(_bytes(p)).hexdigest()
def hash_obj(o): return hashlib.sha256(json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
def hash_uid_set(uids): return hashlib.sha256(('\n'.join(sorted(set(uids)))+'\n').encode('utf-8')).hexdigest()
def fail(reason, **extra):
    out={'status':'FAIL','failures':[reason]}; out.update(extra); return out

def section_map(root):
    reg=load(root/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml')
    out={}
    for doc in reg.get('documents') or []:
        for s in doc.get('sections') or []:
            rec=dict(s); rec['document_id']=doc.get('document_id'); out[s.get('section_uid')]=rec
    return out

def root_manifest_docs(root):
    man=load(root/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml')
    return {x.get('artifact_uid'):(x.get('path'),x.get('sha256')) for x in man.get('current_artifacts') or []}

def resolve_section(root, uid, sections=None):
    sections=sections or section_map(root)
    rec=sections.get(uid)
    if not rec: return None,'unresolved_section_uid:'+str(uid)
    p=root/rec.get('path','')
    if not p.exists(): return None,'section_document_missing:'+uid
    content=text(p); lines=content.splitlines()
    anchor=f'<!-- SECTION_UID: {uid} -->'
    anchors=[i for i,l in enumerate(lines) if l.strip()==anchor]
    if len(anchors)!=1: return None,'section_anchor_not_unique:'+uid
    heading=rec.get('heading') or ''
    headings=[i for i,l in enumerate(lines) if l==heading]
    if len(headings)!=1: return None,'section_heading_not_unique:'+uid
    if headings[0]!=anchors[0]+1 or lines[anchors[0]+1]!=heading: return None,'section_anchor_heading_binding_invalid:'+uid
    expected_binding=hashlib.sha256(f'{uid}\n{rec["document_id"]}\n{rec["path"]}\n{heading}\n'.encode()).hexdigest()
    if rec.get('binding_sha256')!=expected_binding: return None,'section_binding_hash_mismatch:'+uid
    # bind against root manifest document sha
    doc_art='DOC-'+rec['document_id'].replace('WEB-GOV-','')
    # actual root manifest uses DOC-01_BLUEPRINT... so path match is more reliable
    rm=load(root/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml')
    matches=[x for x in rm.get('current_artifacts') or [] if x.get('path')==rec.get('path')]
    if len(matches)!=1: return None,'root_manifest_document_binding_invalid:'+uid
    actual=sha256_file(p)
    if matches[0].get('sha256')!=actual: return None,'root_manifest_document_hash_stale:'+uid
    return {'section_uid':uid,'document_id':rec['document_id'],'canonical_path':rec['path'],'section_anchor':anchor,'heading':heading,'binding_sha256':expected_binding,'document_sha256':actual},None

def validate_definition(root=ROOT):
    failures=[]
    idx=load(root/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml')
    life=load(root/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml')
    sections=section_map(root)
    rules=idx.get('universal_rules') or {}
    for k in ['governance_load_receipt_required_before_execution','common_plus_specific_normative_load_required','typed_uid_resolution_required','normative_section_uid_read_only','write_target_exact_binding_required']:
        if rules.get(k) is not True: failures.append('universal_execution_load_rule_not_true:'+k)
    for k in ['stale_governance_load_receipt','undeclared_normative_reference_in_execution']:
        if rules.get(k)!='BLOCK': failures.append('universal_execution_load_rule_not_block:'+k)
    bundles=idx.get('mandatory_common_normative_bundles') or {}
    if set(bundles)!={'BUNDLE-GOV-COMMON-CORE','BUNDLE-GOV-CONSTRUCTION-BASE','BUNDLE-GOV-AUDIT-BASE'}:
        failures.append('mandatory_common_bundle_set_invalid')
    for bid,b in bundles.items():
        refs=b.get('section_uids') or []
        if not refs: failures.append('common_bundle_empty:'+bid)
        for uid in refs:
            _,e=resolve_section(root,uid,sections)
            if e: failures.append('common_bundle_'+e)
    esc=idx.get('effective_normative_set_contract') or {}
    if esc.get('all_layers_required') is not True: failures.append('effective_normative_all_layers_not_required')
    if esc.get('missing_common_bundle')!='BLOCK': failures.append('missing_common_bundle_not_block')
    if esc.get('missing_item_specific_ref')!='BLOCK': failures.append('missing_item_specific_not_block')
    gr=idx.get('governance_load_receipt_contract') or {}
    for k in ['required_before_any_stage_operation','required_before_code_write','must_precede_execution_timestamp','invalidate_on_governance_revision_change','invalidate_on_root_manifest_hash_change','invalidate_on_section_registry_hash_change','invalidate_on_target_manifest_change']:
        if gr.get(k) is not True: failures.append('load_receipt_contract_not_true:'+k)
    tr=idx.get('typed_uid_resolution_contract') or {}
    if tr.get('exactly_one_resolution_required') is not True: failures.append('typed_uid_resolution_not_exact')
    if tr.get('free_text_or_fuzzy_fallback')!='BLOCK': failures.append('fuzzy_uid_resolution_not_block')
    types=tr.get('uid_types') or {}
    if (types.get('NORMATIVE_SECTION_UID') or {}).get('write_target') is not False: failures.append('normative_section_write_target_not_false')
    wt=idx.get('write_target_lock_contract') or {}
    if wt.get('actual_target_must_equal_registered_canonical_target') is not True: failures.append('write_target_exact_match_not_required')
    if wt.get('valid_other_registered_artifact_is_not_valid_target') is not True: failures.append('other_registered_artifact_may_be_target')
    for k in ['normative_document_write_during_construction','governance_registry_write_during_construction','unregistered_write_target','prewrite_hash_mismatch']:
        if wt.get(k)!='BLOCK': failures.append('write_target_block_missing:'+k)
    gg=life.get('global_pre_execution_governance_gate') or {}
    if gg.get('no_receipt_no_execution') is not True: failures.append('lifecycle_no_receipt_no_execution_missing')
    if gg.get('common_plus_stage_plus_item_specific_required') is not True: failures.append('lifecycle_common_specific_not_required')
    for st in life.get('stages') or []:
        if st.get('pre_execution_gate')!='GOVERNANCE_LOAD_RECEIPT_PASS': failures.append('stage_pre_execution_gate_missing:'+str(st.get('stage_uid')))
        refs=st.get('required_normative_section_uids') or []
        if not refs: failures.append('stage_normative_refs_empty:'+str(st.get('stage_uid')))
        for uid in refs:
            _,e=resolve_section(root,uid,sections)
            if e: failures.append('stage_'+e)
    return {'status':'PASS' if not failures else 'FAIL','failures':failures}

def validate_receipt(receipt, manifest, program_artifact, root=ROOT):
    """Runtime-style validator used by future stage execution. Inputs are already-loaded dicts."""
    failures=[]
    idx=load(root/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml')
    sections=section_map(root)
    req=(idx.get('governance_load_receipt_contract') or {}).get('required_fields') or []
    for f in req:
        if f not in receipt: failures.append('receipt_field_missing:'+f)
    if receipt.get('status')!='PASS': failures.append('receipt_status_not_pass')
    root_manifest=load(root/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml')
    if receipt.get('governance_revision')!=root_manifest.get('governance_revision'): failures.append('receipt_governance_revision_stale')
    if receipt.get('root_manifest_hash')!=sha256_file(root/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'): failures.append('receipt_root_manifest_hash_stale')
    if receipt.get('section_registry_hash')!=sha256_file(root/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'): failures.append('receipt_section_registry_hash_stale')
    if receipt.get('target_manifest_hash')!=hash_obj(manifest): failures.append('receipt_target_manifest_hash_stale')
    # effective normative set
    common=[]
    for bid in manifest.get('common_normative_bundle_refs') or []:
        b=(idx.get('mandatory_common_normative_bundles') or {}).get(bid)
        if not b: failures.append('manifest_common_bundle_unknown:'+str(bid)); continue
        common += b.get('section_uids') or []
    if set(idx.get('mandatory_common_normative_bundles') or {})-set(manifest.get('common_normative_bundle_refs') or []):
        failures.append('manifest_missing_mandatory_common_bundle')
    stage=manifest.get('stage_normative_section_uids') or []
    specific=manifest.get('item_specific_normative_section_uids') or []
    profile=[]
    prof=(idx.get('program_construction_profiles') or {}).get(program_artifact.get('construction_profile')) or {}
    profile=prof.get('required_normative_section_uids') or []
    if receipt.get('common_bundle_uids')!=manifest.get('common_normative_bundle_refs'): failures.append('receipt_common_bundle_uids_mismatch')
    if receipt.get('stage_normative_section_uids')!=stage: failures.append('receipt_stage_normative_refs_mismatch')
    if receipt.get('profile_normative_section_uids')!=profile: failures.append('receipt_profile_normative_refs_mismatch')
    if receipt.get('artifact_specific_normative_section_uids')!=(program_artifact.get('required_normative_section_uids') or []): failures.append('receipt_artifact_specific_normative_refs_mismatch')
    if receipt.get('acceptance_audit_blueprint_ref')!=manifest.get('acceptance_audit_blueprint_ref'): failures.append('receipt_acceptance_blueprint_mismatch')
    artifact_specific=program_artifact.get('required_normative_section_uids') or []
    effective=set(common+stage+specific+profile+artifact_specific+(receipt.get('dependency_normative_section_uids') or []))
    if receipt.get('effective_normative_set_hash')!=hash_uid_set(effective): failures.append('effective_normative_set_hash_mismatch')
    receipt_resolved={x.get('section_uid') for x in receipt.get('resolved_section_receipts') or []}
    if not effective.issubset(receipt_resolved): failures.append('receipt_missing_effective_normative_refs')
    for uid in effective:
        rr,e=resolve_section(root,uid,sections)
        if e: failures.append(e); continue
        got=[x for x in receipt.get('resolved_section_receipts') or [] if x.get('section_uid')==uid]
        if len(got)!=1 or any(got[0].get(k)!=rr.get(k) for k in rr): failures.append('receipt_resolution_mismatch:'+uid)
    # write target exact binding
    bindings=manifest.get('write_target_bindings') or []
    pa=program_artifact
    matches=[b for b in bindings if b.get('program_artifact_uid')==pa.get('program_artifact_uid')]
    if len(matches)!=1: failures.append('write_target_binding_missing_or_duplicate')
    else:
        b=matches[0]
        for k in ['program_artifact_uid','work_unit_uid','page_uid_or_scope_uid','owner_uid','construction_profile','canonical_path','canonical_filename','producer_stage_uid']:
            if b.get(k)!=pa.get(k): failures.append('write_target_binding_mismatch:'+k)
    try:
        global _INSTANCE_GUARD
        if _INSTANCE_GUARD is None:
            import importlib.util
            gp=Path(__file__).resolve().parent/'program_artifact_instance_guard.py'
            spec=importlib.util.spec_from_file_location('program_artifact_instance_guard_runtime',gp); _INSTANCE_GUARD=importlib.util.module_from_spec(spec); spec.loader.exec_module(_INSTANCE_GUARD)
        gout=_INSTANCE_GUARD.validate_instance(program_artifact,manifest,root)
        failures += ['program_artifact_instance:'+x for x in gout.get('failures',[])]
    except Exception as e:
        failures.append('program_artifact_instance_guard_exception:'+repr(e))
    return {'status':'PASS' if not failures else 'FAIL','failures':failures,'effective_normative_count':len(effective)}

if __name__=='__main__':
    out=validate_definition(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
