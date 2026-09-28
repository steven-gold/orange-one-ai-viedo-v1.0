#!/usr/bin/env python3
from __future__ import annotations
import hashlib, os
from pathlib import Path
import yaml
import stage_execution_engine as core

ROOT=core.ROOT
REGISTRY=core.REGISTRY
PRODUCT_ADMISSION=ROOT/'.github/governance-source/active/source/10_REGISTRY/PRODUCT_EXECUTION_ENVIRONMENT_ADMISSION_REGISTRY.yaml'
GOVERNANCE_SOURCE_ROOT_ENV='EXTERNAL_GOVERNANCE_SOURCE_ROOT'
fail=core.fail
y=core.y
_external_yaml=core._external_yaml
_git_required=core._git_required
_git_is_ancestor=core._git_is_ancestor
_git_object_at_commit=core._git_object_at_commit
_canonical_repository_identity=core._canonical_repository_identity

def _selection_policy():
    admission=y(PRODUCT_ADMISSION)
    policy=(admission.get('product_execution_admission_contracts') or {}).get('PRODUCT_GOVERNANCE_RELEASE_SELECTION_AND_APPLICATION_BASELINE') or {}
    if not policy or policy.get('contract_uid')!='GOV-ADMISSION-PRODUCT-GOVERNANCE-RELEASE-APPLICATION-BASELINE-001':
        fail('PRODUCT_GOVERNANCE_SELECTION_POLICY_MISSING')
    if policy.get('scope_class')!='EXTERNAL_PRODUCT_EXECUTION_ENVIRONMENT_ADMISSION' or policy.get('reusable_page_stage_normative_denominator_inclusion')!='EXCLUDED':
        fail('PRODUCT_GOVERNANCE_SELECTION_SCOPE_ISOLATION_INVALID')
    return policy

def _sha256_file(path):
    if not path.is_file(): fail('HASH_TARGET_MISSING:'+str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _validate_selected_governance_release_data(selection,source_reg,release_receipt,source_ctx,current_governance_uid,root_manifest_sha256):
    policy=_selection_policy()
    missing=sorted(set(map(str,policy.get('selected_governance_release_required_fields') or []))-set(selection))
    if missing: fail('PRODUCT_SELECTED_GOVERNANCE_FIELDS_MISSING:'+repr(missing))
    if selection.get('artifact_type')!=policy.get('selected_governance_release_artifact_type') or selection.get('status')!=policy.get('selected_governance_release_status'): fail('PRODUCT_SELECTED_GOVERNANCE_ARTIFACT_INVALID')
    ident=source_reg.get('governance_identity') or {}; branch=str(source_reg.get('branch') or ''); roles=source_reg.get('branch_role_contract') or {}
    if source_reg.get('status')!=policy.get('selected_release_registry_status') or roles.get(branch)!=policy.get('selected_release_branch_role'): fail('PRODUCT_SELECTED_GOVERNANCE_NOT_RELEASED')
    if ident.get('status')!=policy.get('selected_release_identity_status') or ident.get('identity_state')!=policy.get('selected_release_identity_state') or ident.get('released_immutable_identity') is not True: fail('PRODUCT_SELECTED_GOVERNANCE_IDENTITY_NOT_IMMUTABLE_RELEASED')
    expected={'governance_repository':source_ctx.get('repository'),'governance_commit_sha':source_ctx.get('head'),'governance_tree_sha':source_ctx.get('tree'),'governance_uid':str(ident.get('governance_uid') or ''),'governance_revision':str(ident.get('governance_revision') or ''),'display_version':str(ident.get('display_version') or ''),'root_manifest_sha256':root_manifest_sha256}
    for key,value in expected.items():
        if not value or str(selection.get(key) or '')!=str(value): fail('PRODUCT_SELECTED_GOVERNANCE_BINDING_MISMATCH:'+key)
    if str(selection.get('governance_uid') or '')!=str(current_governance_uid or ''): fail('PRODUCT_SELECTED_GOVERNANCE_CURRENT_UID_MISMATCH')
    if selection.get('fresh_reverify_status')!=policy.get('selected_release_fresh_reverify_status') or not str(selection.get('fresh_reverify_evidence_ref') or '').strip(): fail('PRODUCT_SELECTED_GOVERNANCE_FRESH_REVERIFY_MISSING')
    if release_receipt.get('artifact_type')!='GOVERNANCE_RELEASE_RECEIPT' or str(release_receipt.get('released_governance_uid') or '')!=str(selection.get('governance_uid') or '') or str(release_receipt.get('released_governance_revision') or '')!=str(selection.get('governance_revision') or ''): fail('PRODUCT_SELECTED_GOVERNANCE_RELEASE_RECEIPT_MISMATCH')
    return True

def validate_product_governance_selection(product_root,work_dir,work,stage_uid,current_governance_uid):
    policy=_selection_policy(); rel=str(policy.get('selected_governance_release_path') or ''); rp=Path(rel)
    if not rel or rp.is_absolute() or '..' in rp.parts: fail('PRODUCT_SELECTED_GOVERNANCE_REF_INVALID')
    selection=_external_yaml(product_root/rp,'PRODUCT_SELECTED_GOVERNANCE_RELEASE')
    raw=os.environ.get(str(policy.get('governance_source_root_env') or GOVERNANCE_SOURCE_ROOT_ENV),'').strip()
    if not raw: fail('PRODUCT_GOVERNANCE_SOURCE_ROOT_REQUIRED')
    source_root=Path(raw); source_root=(source_root if source_root.is_absolute() else product_root/source_root).resolve()
    if not source_root.is_dir(): fail('PRODUCT_GOVERNANCE_SOURCE_ROOT_MISSING')
    source_reg_path=source_root/'governance/specifications/REGISTRY.yaml'; source_reg=_external_yaml(source_reg_path,'SELECTED_GOVERNANCE_REGISTRY')
    if REGISTRY.read_bytes()!=source_reg_path.read_bytes(): fail('LOADED_GOVERNANCE_REGISTRY_DIFFERS_FROM_SELECTED_CHECKOUT')
    source_head=_git_required(source_root,'SELECTED_GOVERNANCE_HEAD_UNRESOLVED','rev-parse','HEAD'); source_tree=_git_required(source_root,'SELECTED_GOVERNANCE_TREE_UNRESOLVED','rev-parse','HEAD^{tree}')
    remote=_git_required(source_root,'SELECTED_GOVERNANCE_REPOSITORY_UNRESOLVED','config','--get','remote.origin.url')
    source_ctx={'repository':_canonical_repository_identity(remote),'head':source_head,'tree':source_tree}
    receipt_path=source_root/str(selection.get('release_receipt_ref') or ''); release_receipt=_external_yaml(receipt_path,'SELECTED_GOVERNANCE_RELEASE_RECEIPT')
    if _sha256_file(receipt_path)!=str(selection.get('release_receipt_sha256') or ''): fail('PRODUCT_SELECTED_GOVERNANCE_RELEASE_RECEIPT_HASH_MISMATCH')
    root_hash=_sha256_file(source_root/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml')
    _validate_selected_governance_release_data(selection,source_reg,release_receipt,source_ctx,current_governance_uid,root_hash)
    load=_external_yaml(work_dir/str(policy.get('product_released_governance_load_receipt_filename') or 'PRODUCT_RELEASED_GOVERNANCE_LOAD_RECEIPT.yaml'),'PRODUCT_RELEASED_GOVERNANCE_LOAD_RECEIPT')
    missing=sorted(set(map(str,policy.get('product_released_governance_load_receipt_required_fields') or []))-set(load))
    if missing: fail('PRODUCT_RELEASED_GOVERNANCE_LOAD_RECEIPT_FIELDS_MISSING:'+repr(missing))
    expected={'artifact_type':str(policy.get('product_released_governance_load_receipt_artifact_type') or ''),'status':str(policy.get('product_released_governance_load_receipt_status') or 'PASS'),'stage_uid':stage_uid,'work_unit_uid':str(work.get('work_unit_uid') or ''),'selected_governance_ref':rel,'governance_uid':str(selection.get('governance_uid') or ''),'governance_revision':str(selection.get('governance_revision') or ''),'governance_commit_sha':source_head,'governance_tree_sha':source_tree,'governance_root_manifest_sha256':root_hash}
    for key,value in expected.items():
        if not value or str(load.get(key) or '')!=str(value): fail('PRODUCT_RELEASED_GOVERNANCE_LOAD_RECEIPT_BINDING_MISMATCH:'+key)
    if not str(load.get('effective_normative_set_sha256') or '').strip() or not str(load.get('loader_uid') or '').strip() or not str(load.get('loaded_at') or '').strip(): fail('PRODUCT_RELEASED_GOVERNANCE_LOAD_RECEIPT_PROVENANCE_INCOMPLETE')
    return selection

def _block_for_governance_revision_transition(product_root,work,stage_uid,from_uid,to_uid):
    policy=_selection_policy(); rel=str(policy.get('governance_revision_transition_receipt_path') or ''); rp=Path(rel)
    if not rel or rp.is_absolute() or '..' in rp.parts or not (product_root/rp).is_file(): fail('GOVERNANCE_REVISION_TRANSITION_REQUIRED:'+str(from_uid)+'->'+str(to_uid))
    receipt=_external_yaml(product_root/rp,'GOVERNANCE_REVISION_TRANSITION_RECEIPT')
    missing=sorted(set(map(str,policy.get('governance_revision_transition_required_fields') or []))-set(receipt))
    if missing: fail('GOVERNANCE_REVISION_TRANSITION_FIELDS_MISSING:'+repr(missing))
    if receipt.get('artifact_type')!=policy.get('governance_revision_transition_receipt_type') or receipt.get('status')!=policy.get('governance_revision_transition_status_when_old_uid_present'): fail('GOVERNANCE_REVISION_TRANSITION_RECEIPT_INVALID')
    if str(receipt.get('from_governance_uid') or '')!=str(from_uid) or str(receipt.get('to_governance_uid') or '')!=str(to_uid): fail('GOVERNANCE_REVISION_TRANSITION_UID_MISMATCH')
    if str(receipt.get('selected_governance_ref') or '')!=str(policy.get('selected_governance_release_path') or ''): fail('GOVERNANCE_REVISION_TRANSITION_SELECTED_RELEASE_REF_MISMATCH')
    affected=receipt.get('affected_work_unit_uids'); invalidated=receipt.get('invalidated_artifact_classes'); preserved=receipt.get('preserved_artifact_refs')
    if not isinstance(affected,list) or not affected: fail('GOVERNANCE_REVISION_TRANSITION_AFFECTED_WORK_UNITS_INVALID')
    if not isinstance(invalidated,list): fail('GOVERNANCE_REVISION_TRANSITION_INVALIDATED_ARTIFACT_CLASSES_INVALID')
    if not isinstance(preserved,list): fail('GOVERNANCE_REVISION_TRANSITION_PRESERVED_ARTIFACT_REFS_INVALID')
    if not str(receipt.get('reverse_dependency_evidence_ref') or '').strip() or not str(receipt.get('transition_authority_ref') or '').strip(): fail('GOVERNANCE_REVISION_TRANSITION_PROVENANCE_INCOMPLETE')
    if str(work.get('work_unit_uid') or '') not in list(map(str,affected)): fail('GOVERNANCE_REVISION_TRANSITION_WORK_UNIT_NOT_CLASSIFIED')
    earliest=str(receipt.get('earliest_reentry_stage_uid') or '')
    if not re.fullmatch(r'STAGE-(?:0[1-9]|1[01])',earliest): fail('GOVERNANCE_REVISION_TRANSITION_REENTRY_STAGE_INVALID')
    fail('GOVERNANCE_REVISION_TRANSITION_REENTRY_REQUIRED:'+earliest)


def _validate_application_baseline_snapshot(product_root,git_context,target_path,receipt):
    policy=_selection_policy(); ref=str(receipt.get('application_baseline_snapshot_ref') or '').strip()
    if not ref: fail('APPLICATION_BASELINE_SNAPSHOT_REF_MISSING')
    rp=Path(ref)
    if rp.is_absolute() or '..' in rp.parts: fail('APPLICATION_BASELINE_SNAPSHOT_REF_INVALID')
    snap=_external_yaml(product_root/rp,'APPLICATION_BASELINE_SNAPSHOT')
    missing=sorted(set(map(str,policy.get('application_baseline_snapshot_required_fields') or []))-set(snap))
    if missing: fail('APPLICATION_BASELINE_SNAPSHOT_FIELDS_MISSING:'+repr(missing))
    if snap.get('artifact_type')!=policy.get('application_baseline_snapshot_type') or snap.get('status')!=policy.get('application_baseline_snapshot_status'): fail('APPLICATION_BASELINE_SNAPSHOT_INVALID')
    if _canonical_repository_identity(snap.get('product_repository'))!=git_context['repository'] or str(snap.get('product_branch') or '')!=git_context['branch']: fail('APPLICATION_BASELINE_SNAPSHOT_PRODUCT_CONTEXT_MISMATCH')
    if str(snap.get('application_root') or '')!=str(target_path): fail('APPLICATION_BASELINE_SNAPSHOT_ROOT_MISMATCH')
    baseline=str(snap.get('baseline_commit_sha') or '')
    if len(baseline)!=40 or not _git_is_ancestor(product_root,baseline,git_context['head']): fail('APPLICATION_BASELINE_COMMIT_NOT_ANCESTOR')
    rows=snap.get('tracked_path_set')
    if not isinstance(rows,list) or not rows: fail('APPLICATION_BASELINE_TRACKED_PATH_SET_EMPTY')
    req=set(map(str,policy.get('application_baseline_snapshot_path_row_required_fields') or [])); seen=set()
    for row in rows:
        if not isinstance(row,dict) or not req.issubset(row): fail('APPLICATION_BASELINE_PATH_ROW_INVALID')
        p=str(row.get('path') or '').strip(); pp=Path(p)
        if not p or pp.is_absolute() or '..' in pp.parts or p in seen: fail('APPLICATION_BASELINE_PATH_IDENTITY_INVALID:'+p)
        seen.add(p); obj=_git_object_at_commit(product_root,git_context['head'],p)
        if not obj or obj!=str(row.get('git_object_sha') or ''): fail('APPLICATION_BASELINE_PATH_OBJECT_MISMATCH:'+p)
    kind=str(snap.get('baseline_source_kind') or '')
    if kind not in set(map(str,policy.get('application_baseline_allowed_source_kinds') or [])): fail('APPLICATION_BASELINE_SOURCE_KIND_INVALID:'+kind)
    if snap.get('implementation_diff_anchor') is not True or not str(snap.get('baseline_authority_ref') or '').strip(): fail('APPLICATION_BASELINE_DIFF_ANCHOR_OR_AUTHORITY_MISSING')
    if kind=='AUTHORIZED_MIGRATION':
        mr=str(snap.get('application_baseline_materialization_ref') or '').strip(); mp=Path(mr)
        if not mr: fail('APPLICATION_BASELINE_MATERIALIZATION_REF_MISSING')
        if mp.is_absolute() or '..' in mp.parts: fail('APPLICATION_BASELINE_MATERIALIZATION_REF_INVALID')
        mat=_external_yaml(product_root/mp,'APPLICATION_BASELINE_MATERIALIZATION_RECEIPT')
        mm=sorted(set(map(str,policy.get('application_baseline_materialization_receipt_required_fields') or []))-set(mat))
        if mm: fail('APPLICATION_BASELINE_MATERIALIZATION_FIELDS_MISSING:'+repr(mm))
        if mat.get('artifact_type')!=policy.get('application_baseline_materialization_receipt_type') or mat.get('status')!=policy.get('application_baseline_materialization_status') or mat.get('conflict_result')!=policy.get('application_baseline_conflict_result'): fail('APPLICATION_BASELINE_MATERIALIZATION_NOT_PASS')
        if _canonical_repository_identity(mat.get('target_repository'))!=git_context['repository'] or str(mat.get('target_branch') or '')!=git_context['branch'] or str(mat.get('application_root') or '')!=str(target_path): fail('APPLICATION_BASELINE_MATERIALIZATION_TARGET_MISMATCH')
        mc=str(mat.get('materialization_commit_sha') or '')
        if len(mc)!=40 or not _git_is_ancestor(product_root,mc,git_context['head']): fail('APPLICATION_BASELINE_MATERIALIZATION_COMMIT_NOT_ANCESTOR')
        ar=str(mat.get('admission_manifest_ref') or '').strip(); ap=Path(ar)
        if not ar or ap.is_absolute() or '..' in ap.parts: fail('APPLICATION_BASELINE_ADMISSION_MANIFEST_REF_INVALID')
        man=_external_yaml(product_root/ap,'APPLICATION_BASELINE_ADMISSION_MANIFEST')
        am=sorted(set(map(str,policy.get('application_baseline_admission_manifest_required_fields') or []))-set(man))
        if am: fail('APPLICATION_BASELINE_ADMISSION_MANIFEST_FIELDS_MISSING:'+repr(am))
        if man.get('artifact_type')!=policy.get('application_baseline_admission_manifest_type') or man.get('status')!='APPROVED': fail('APPLICATION_BASELINE_ADMISSION_MANIFEST_NOT_APPROVED')
        if _canonical_repository_identity(man.get('target_repository'))!=git_context['repository'] or str(man.get('target_branch') or '')!=git_context['branch'] or str(man.get('application_root') or '')!=str(target_path): fail('APPLICATION_BASELINE_ADMISSION_TARGET_MISMATCH')
        for k in ('source_repository','source_branch','source_head_sha','source_tree_sha'):
            if str(man.get(k) or '')!=str(mat.get(k) or ''): fail('APPLICATION_BASELINE_SOURCE_PROVENANCE_MISMATCH:'+k)
        parent=str(mat.get('target_parent_head_sha') or '')
        if str(man.get('target_expected_head_sha') or '')!=parent: fail('APPLICATION_BASELINE_TARGET_PREWRITE_HEAD_MISMATCH')
        if len(parent)!=40 or not _git_is_ancestor(product_root,parent,mc): fail('APPLICATION_BASELINE_TARGET_PARENT_NOT_ANCESTOR_OF_MATERIALIZATION')
        for k in ('source_path_set','include_path_set','allowed_write_path_set','preserve_path_set'):
            if not isinstance(man.get(k),list) or not man.get(k): fail('APPLICATION_BASELINE_ADMISSION_PATH_SET_INVALID:'+k)
        if not isinstance(man.get('exclude_path_set'),list): fail('APPLICATION_BASELINE_ADMISSION_PATH_SET_INVALID:exclude_path_set')
        if not str(man.get('conflict_policy') or '').strip() or not str(man.get('transition_authority_ref') or '').strip(): fail('APPLICATION_BASELINE_ADMISSION_POLICY_OR_AUTHORITY_MISSING')
        result_rows=mat.get('resulting_path_object_set')
        if not isinstance(result_rows,list) or not result_rows: fail('APPLICATION_BASELINE_MATERIALIZATION_RESULT_SET_EMPTY')
        result_map={str(x.get('path') or ''):str(x.get('git_object_sha') or '') for x in result_rows if isinstance(x,dict)}
        if not result_map or len(result_map)!=len(result_rows): fail('APPLICATION_BASELINE_MATERIALIZATION_RESULT_SET_INVALID')
        snapshot_map={str(x.get('path') or ''):str(x.get('git_object_sha') or '') for x in rows if isinstance(x,dict)}
        if result_map!=snapshot_map: fail('APPLICATION_BASELINE_MATERIALIZATION_SNAPSHOT_OBJECT_SET_MISMATCH')
    return True


def _released_governance_mode_selected(work,current_scope=None):
    policy=_selection_policy()
    field=str(policy.get('released_governance_mode_activation_field') or '')
    value=str(policy.get('released_governance_mode_activation_value') or '')
    if not field or not value:
        fail('RELEASED_GOVERNANCE_MODE_ACTIVATION_CONTRACT_MISSING')
    scope_value=(current_scope or {}).get(field) if isinstance(current_scope,dict) else None
    work_value=work.get(field) if isinstance(work,dict) else None
    selected=scope_value if scope_value not in (None,'') else work_value
    return str(selected or '')==value

def validate_external_stage_admission(execution_root, work_dir, work, stage_uid, current_governance_uid, current_scope=None):
    if not _released_governance_mode_selected(work,current_scope):
        return None
    selection=validate_product_governance_selection(execution_root,work_dir,work,stage_uid,current_governance_uid)
    if isinstance(current_scope,dict):
        prior=current_scope.get('governance_uid')
        if prior not in (None,current_governance_uid):
            _block_for_governance_revision_transition(execution_root,work,stage_uid,prior,current_governance_uid)
    return selection
