#!/usr/bin/env python3
from __future__ import annotations
import hashlib, os
from pathlib import Path
import stage_execution_engine as core

ROOT=core.ROOT
REGISTRY=core.REGISTRY
PRODUCT_ADMISSION=ROOT/'.github/governance-source/active/source/10_REGISTRY/PRODUCT_EXECUTION_ENVIRONMENT_ADMISSION_REGISTRY.yaml'
GOVERNANCE_SOURCE_ROOT_ENV='GOVERNANCE_SOURCE_ROOT'
fail=core.fail
y=core.y
_external_yaml=core._external_yaml
_git_required=core._git_required
_canonical_repository_identity=core._canonical_repository_identity

def _selection_policy():
    admission=y(PRODUCT_ADMISSION)
    policy=(admission.get('product_execution_admission_contracts') or {}).get('PRODUCT_CURRENT_GOVERNANCE_SNAPSHOT_AND_APPLICATION_BASELINE') or {}
    if not policy or policy.get('contract_uid')!='GOV-ADMISSION-PRODUCT-CURRENT-GOVERNANCE-APPLICATION-BASELINE-001':
        fail('PRODUCT_CURRENT_GOVERNANCE_SELECTION_POLICY_MISSING')
    if policy.get('scope_class')!='EXTERNAL_PRODUCT_EXECUTION_ENVIRONMENT_ADMISSION' or policy.get('reusable_common_stage_normative_denominator_inclusion')!='EXCLUDED':
        fail('PRODUCT_GOVERNANCE_SELECTION_SCOPE_ISOLATION_INVALID')
    return policy

def _sha256_file(path):
    if not path.is_file(): fail('HASH_TARGET_MISSING:'+str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _validate_selected_current_governance_data(selection,source_reg,source_ctx,current_governance_uid,root_manifest_sha256):
    policy=_selection_policy()
    missing=sorted(set(map(str,policy.get('selected_governance_required_fields') or []))-set(selection))
    if missing: fail('PRODUCT_SELECTED_CURRENT_GOVERNANCE_FIELDS_MISSING:'+repr(missing))
    if selection.get('artifact_type')!=policy.get('selected_governance_artifact_type') or selection.get('status')!=policy.get('selected_governance_status'):
        fail('PRODUCT_SELECTED_CURRENT_GOVERNANCE_ARTIFACT_INVALID')
    if selection.get('selection_mode')!=policy.get('selected_governance_selection_mode'):
        fail('PRODUCT_SELECTED_CURRENT_GOVERNANCE_MODE_INVALID')
    ident=source_reg.get('governance_identity') or {}
    if source_reg.get('status')!=policy.get('selected_registry_status'):
        fail('PRODUCT_SELECTED_CURRENT_GOVERNANCE_REGISTRY_NOT_CURRENT')
    if ident.get('status')!=policy.get('selected_identity_status') or ident.get('identity_state')!=policy.get('selected_identity_state'):
        fail('PRODUCT_SELECTED_CURRENT_GOVERNANCE_IDENTITY_INVALID')
    expected={
      'governance_repository':source_ctx.get('repository'),
      'governance_commit_sha':source_ctx.get('head'),
      'governance_tree_sha':source_ctx.get('tree'),
      'governance_uid':str(ident.get('governance_uid') or ''),
      'governance_revision':str(ident.get('governance_revision') or ''),
      'display_version':str(ident.get('display_version') or ''),
      'root_manifest_sha256':root_manifest_sha256,
    }
    for key,value in expected.items():
        if not value or str(selection.get(key) or '')!=str(value):
            fail('PRODUCT_SELECTED_CURRENT_GOVERNANCE_BINDING_MISMATCH:'+key)
    if str(selection.get('governance_uid') or '')!=str(current_governance_uid or ''):
        fail('PRODUCT_SELECTED_CURRENT_GOVERNANCE_UID_MISMATCH')
    if not str(selection.get('selection_authority_ref') or '').strip():
        fail('PRODUCT_SELECTED_CURRENT_GOVERNANCE_AUTHORITY_MISSING')
    return True

def validate_product_governance_selection(product_root,work_dir,work,stage_uid,current_governance_uid):
    policy=_selection_policy(); rel=str(policy.get('selected_governance_path') or ''); rp=Path(rel)
    if not rel or rp.is_absolute() or '..' in rp.parts: fail('PRODUCT_SELECTED_CURRENT_GOVERNANCE_REF_INVALID')
    selection=_external_yaml(product_root/rp,'PRODUCT_SELECTED_CURRENT_GOVERNANCE')
    raw=os.environ.get(str(policy.get('governance_source_root_env') or GOVERNANCE_SOURCE_ROOT_ENV),'').strip()
    if not raw: fail('PRODUCT_GOVERNANCE_SOURCE_ROOT_REQUIRED')
    source_root=Path(raw); source_root=(source_root if source_root.is_absolute() else product_root/source_root).resolve()
    if not source_root.is_dir(): fail('PRODUCT_GOVERNANCE_SOURCE_ROOT_MISSING')
    source_reg_path=source_root/'governance/specifications/REGISTRY.yaml'
    source_reg=_external_yaml(source_reg_path,'SELECTED_CURRENT_GOVERNANCE_REGISTRY')
    if REGISTRY.read_bytes()!=source_reg_path.read_bytes():
        fail('LOADED_GOVERNANCE_REGISTRY_DIFFERS_FROM_SELECTED_CHECKOUT')
    source_head=_git_required(source_root,'SELECTED_GOVERNANCE_HEAD_UNRESOLVED','rev-parse','HEAD')
    source_tree=_git_required(source_root,'SELECTED_GOVERNANCE_TREE_UNRESOLVED','rev-parse','HEAD^{tree}')
    remote=_git_required(source_root,'SELECTED_GOVERNANCE_REPOSITORY_UNRESOLVED','config','--get','remote.origin.url')
    source_ctx={'repository':_canonical_repository_identity(remote),'head':source_head,'tree':source_tree}
    root_hash=_sha256_file(source_root/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml')
    _validate_selected_current_governance_data(selection,source_reg,source_ctx,current_governance_uid,root_hash)
    load=_external_yaml(work_dir/str(policy.get('current_governance_load_receipt_filename') or 'PRODUCT_CURRENT_GOVERNANCE_LOAD_RECEIPT.yaml'),'PRODUCT_CURRENT_GOVERNANCE_LOAD_RECEIPT')
    missing=sorted(set(map(str,policy.get('current_governance_load_receipt_required_fields') or []))-set(load))
    if missing: fail('PRODUCT_CURRENT_GOVERNANCE_LOAD_RECEIPT_FIELDS_MISSING:'+repr(missing))
    expected={
      'artifact_type':str(policy.get('current_governance_load_receipt_artifact_type') or ''),
      'status':str(policy.get('current_governance_load_receipt_status') or 'PASS'),
      'stage_uid':stage_uid,
      'work_unit_uid':str(work.get('work_unit_uid') or ''),
      'selected_governance_ref':rel,
      'governance_uid':str(selection.get('governance_uid') or ''),
      'governance_revision':str(selection.get('governance_revision') or ''),
      'governance_commit_sha':source_head,
      'governance_tree_sha':source_tree,
      'governance_root_manifest_sha256':root_hash,
    }
    for key,value in expected.items():
        if not value or str(load.get(key) or '')!=str(value):
            fail('PRODUCT_CURRENT_GOVERNANCE_LOAD_RECEIPT_BINDING_MISMATCH:'+key)
    if not str(load.get('effective_normative_set_sha256') or '').strip() or not str(load.get('loader_uid') or '').strip() or not str(load.get('loaded_at') or '').strip():
        fail('PRODUCT_CURRENT_GOVERNANCE_LOAD_RECEIPT_PROVENANCE_INCOMPLETE')
    return selection

def _current_governance_mode_selected(work,current_scope=None):
    policy=_selection_policy()
    field=str(policy.get('current_governance_mode_activation_field') or '')
    value=str(policy.get('current_governance_mode_activation_value') or '')
    if not field or not value: fail('CURRENT_GOVERNANCE_MODE_ACTIVATION_CONTRACT_MISSING')
    scope_value=(current_scope or {}).get(field) if isinstance(current_scope,dict) else None
    work_value=work.get(field) if isinstance(work,dict) else None
    selected=scope_value if scope_value not in (None,'') else work_value
    return str(selected or '')==value

def validate_external_stage_admission(execution_root, work_dir, work, stage_uid, current_governance_uid, current_scope=None):
    if not _current_governance_mode_selected(work,current_scope):
        return None
    prior=(current_scope or {}).get('governance_uid') if isinstance(current_scope,dict) else None
    if prior not in (None,'',current_governance_uid):
        fail('AFFECTED_OLD_GOVERNANCE_SCOPE_REVERIFY_REQUIRED')
    return validate_product_governance_selection(execution_root,work_dir,work,stage_uid,current_governance_uid)
