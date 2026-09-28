#!/usr/bin/env python3
from copy import deepcopy
import external_execution_admission as ext

def expect_block(label,fn,needle):
    try: fn()
    except ext.core.StageEngineError as exc:
        if needle not in str(exc): raise SystemExit('WRONG_BLOCK:'+label+':'+str(exc))
        return
    raise SystemExit('FAIL_EXPECTED_BLOCK:'+label)

_current_reg={'status':'CURRENT','branch':'rebuild-v2.1.1','governance_identity':{'governance_uid':'GOV-CURRENT-TEST','governance_revision':'vTEST','display_version':'vTEST','status':'CURRENT','identity_state':'EXACT_HEAD_AND_BUNDLE_DIGEST_BOUND'}}
_sel={'artifact_type':'PRODUCT_SELECTED_CURRENT_GOVERNANCE','status':'SELECTED_EXACT_CURRENT_SNAPSHOT','selection_mode':'EXACT_CURRENT_GOVERNANCE_SNAPSHOT','product_branch':'0921acpos','governance_repository':'owner/repo','governance_branch':'rebuild-v2.1.1','governance_commit_sha':'a'*40,'governance_tree_sha':'b'*40,'governance_uid':'GOV-CURRENT-TEST','governance_revision':'vTEST','display_version':'vTEST','root_manifest_sha256':'d'*64,'selection_authority_ref':'authority://selection'}
assert ext._validate_selected_current_governance_data(_sel,_current_reg,{'repository':'owner/repo','head':'a'*40,'tree':'b'*40},'GOV-CURRENT-TEST','d'*64) is True
_bad=deepcopy(_sel); _bad['governance_commit_sha']='e'*40
expect_block('selected_exact_commit_mismatch',lambda:ext._validate_selected_current_governance_data(_bad,_current_reg,{'repository':'owner/repo','head':'a'*40,'tree':'b'*40},'GOV-CURRENT-TEST','d'*64),'PRODUCT_SELECTED_CURRENT_GOVERNANCE_BINDING_MISMATCH:governance_commit_sha')
assert ext._current_governance_mode_selected({}, {}) is False
assert ext._current_governance_mode_selected({'governance_execution_mode':'CURRENT_VALIDATED_GOVERNANCE'}, {}) is True
assert ext._current_governance_mode_selected({}, {'governance_execution_mode':'CURRENT_VALIDATED_GOVERNANCE'}) is True
core_text=(ext.ROOT/'governance/ci/stage_execution_engine.py').read_text(encoding='utf-8')
for token in ('PRODUCT_SELECTED_CURRENT_GOVERNANCE','PRODUCT_CURRENT_GOVERNANCE_LOAD_RECEIPT','APPLICATION_BASELINE_SNAPSHOT','PRODUCT_EXECUTION_ENVIRONMENT_ADMISSION_REGISTRY'):
    if token in core_text: raise SystemExit('STAGE_CORE_EXTERNAL_SEMANTIC_LEAK:'+token)
print('PASS: Current-governance external admission is isolated from reusable Stage Core')
