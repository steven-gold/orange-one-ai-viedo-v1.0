#!/usr/bin/env python3
from copy import deepcopy
import yaml
import external_execution_admission as ext
def expect_block(label,fn,needle):
    try: fn()
    except ext.core.StageEngineError as exc:
        if needle not in str(exc): raise SystemExit('WRONG_BLOCK:'+label+':'+str(exc))
        return
    raise SystemExit('FAIL_EXPECTED_BLOCK:'+label)
_release_reg={'status':'CURRENT_RELEASED','branch':'release-line','branch_role_contract':{'release-line':'IMMUTABLE_GOVERNANCE_RULESET'},'governance_identity':{'governance_uid':'GOV-RELEASE-TEST','governance_revision':'vTEST','display_version':'vTEST','status':'RELEASED','identity_state':'IMMUTABLE_RELEASED','released_immutable_identity':True}}
_release_sel={'artifact_type':'PRODUCT_SELECTED_GOVERNANCE_RELEASE','status':'SELECTED_VERIFIED_RELEASE','governance_repository':'owner/repo','governance_commit_sha':'a'*40,'governance_tree_sha':'b'*40,'governance_uid':'GOV-RELEASE-TEST','governance_revision':'vTEST','display_version':'vTEST','release_receipt_ref':'governance/release/RELEASE_RECEIPT.yaml','release_receipt_sha256':'c'*64,'root_manifest_sha256':'d'*64,'fresh_reverify_status':'PASS','fresh_reverify_evidence_ref':'external://fresh-reverify','selection_authority_ref':'authority://selection'}
_release_receipt={'artifact_type':'GOVERNANCE_RELEASE_RECEIPT','released_governance_uid':'GOV-RELEASE-TEST','released_governance_revision':'vTEST'}
assert ext._validate_selected_governance_release_data(_release_sel,_release_reg,_release_receipt,{'repository':'owner/repo','head':'a'*40,'tree':'b'*40},'GOV-RELEASE-TEST','d'*64) is True
_candidate=deepcopy(_release_reg); _candidate['status']='ACTIVE_SINGLE_BRANCH_VALIDATION'; _candidate['branch_role_contract']['release-line']='GOVERNANCE_REVISION_CANDIDATE'
expect_block('candidate_cannot_receive_released_governance_admission_credit',lambda:ext._validate_selected_governance_release_data(_release_sel,_candidate,_release_receipt,{'repository':'owner/repo','head':'a'*40,'tree':'b'*40},'GOV-RELEASE-TEST','d'*64),'PRODUCT_SELECTED_GOVERNANCE_NOT_RELEASED')
_bad=deepcopy(_release_sel); _bad['governance_commit_sha']='e'*40
expect_block('selected_exact_commit_mismatch',lambda:ext._validate_selected_governance_release_data(_bad,_release_reg,_release_receipt,{'repository':'owner/repo','head':'a'*40,'tree':'b'*40},'GOV-RELEASE-TEST','d'*64),'PRODUCT_SELECTED_GOVERNANCE_BINDING_MISMATCH:governance_commit_sha')
core_text=(ext.ROOT/'governance/ci/stage_execution_engine.py').read_text(encoding='utf-8')
for token in ('PRODUCT_SELECTED_GOVERNANCE_RELEASE','PRODUCT_RELEASED_GOVERNANCE_LOAD_RECEIPT','GOVERNANCE_REVISION_TRANSITION_RECEIPT','APPLICATION_BASELINE_SNAPSHOT','PRODUCT_EXECUTION_ENVIRONMENT_ADMISSION_REGISTRY'):
    if token in core_text: raise SystemExit('STAGE_CORE_EXTERNAL_SEMANTIC_LEAK:'+token)
binding=yaml.safe_load((ext.ROOT/'governance/environment/EXECUTION_WORKLINE_BINDING.yaml').read_text(encoding='utf-8')) or {}
for group in ('governance_workline','execution_workline'):
    row=binding.get(group) or {}
    for token in (row.get('repository'),row.get('branch')):
        if isinstance(token,str) and token and token in core_text:
            raise SystemExit('STAGE_CORE_EXECUTION_ENVIRONMENT_LITERAL_LEAK:'+token)
print('PASS: external execution admission is isolated from reusable Stage Core')
