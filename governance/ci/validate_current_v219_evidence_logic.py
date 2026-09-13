#!/usr/bin/env python3
from pathlib import Path
import yaml,re
root=Path('.')
PKG='499aaccab4f38e089b465f98a2785dbef65faf304621db90599bc1dd55a9d24f'
TRUST='7e3c2e523484a47f02ad45e6e1d8d9ccd6624904c76c67aa5f1856583e012ae1'
SEM='531a364590e47f182f40ac3794d9b30c7ae77678423a53be787ae1cd87c70c2f'

def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load((root/p).read_text(encoding='utf-8')) or {}

cand=load('governance/current/v2.1.9/CANDIDATE_RECORD.yaml')
lock=load('governance/current/v2.1.9/FULL_PACKAGE_LOCK.yaml')
cur=load('GOVERNANCE_CURRENT.yaml')
base=load('REBUILD_BRANCH_BASELINE.yaml')
stage=load('11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml')
seal=load('11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml')
state=load('00_SOURCE_INTAKE/fresh_run_003/EXECUTION_STATE.yaml')
checks=(root/'governance/current/v2.1.9/CHECKSUMS.sha256').read_text(encoding='utf-8').splitlines()

if cand.get('version')!='v2.1.9' or cand.get('baseline')!='v2.1.8': die('v219 candidate identity drift')
if (cand.get('package_sha256'),cand.get('external_trust_root_sha256'),cand.get('semantic_authority_content_hash'))!=(PKG,TRUST,SEM): die('v219 candidate hash drift')
local=cand.get('local_verification') or {}
expected={'preformal_definition_checks':'16/16_PASS','mandatory_matrix':'11/11_PASS','high_pressure':'25/25_PASS','reference_semantic':'28/28_PASS','reference_fuzz':'46/46_BLOCKED_0_ESCAPED','execution_load':'14/14_PASS','multidirection_stress':'21/21_PASS','stage1_minimal':'33/33_PASS','cross_lifecycle':'30/30_PASS','v217_phase_authority':'25/25_PASS','v218_successor_evidence_sync':'24/24_PASS','v219_evidence_state_system_logic':'24/24_PASS'}
for k,v in expected.items():
    if local.get(k)!=v: die('local verification drift:'+k)
closed=cand.get('closed_predecessor_github_evidence') or {}
if closed!={'v218_successor_linkage_final_run':34733833659,'pre_page_replay_run':34734265713,'page_replay_run':34734528373,'content_audit_closure_run':34734730080}: die('closed predecessor GitHub evidence drift')
logic=cand.get('stage02_system_logic_detection') or {}
for k in ('page_functional_contract','functional_chain','dependency_map','permission_runtime_data','cross_page_system_logic_slice','error_retry_resume','second_system_guard','orphan_guard'):
    if logic.get(k) is not True: die('Stage-02 system logic detector missing:'+k)
if cand.get('human_formal_review')!='PENDING' or cand.get('formal_test_executed') is not False or cand.get('formal_freeze_claimed') is not False or cand.get('production_release_claimed') is not False: die('formal/human review state overclaim')

gv=cand.get('github_verification') or {}
if gv.get('conclusion') not in {'PENDING','SUCCESS'}: die('candidate GitHub conclusion invalid')
if gv.get('conclusion')=='SUCCESS' and (not isinstance(gv.get('run_id'),int) or gv.get('jobs')!='7/7_SUCCESS'): die('candidate GitHub PASS lacks exact run/jobs')

if lock.get('version')!='v2.1.9' or (lock.get('source_package_sha256'),lock.get('external_trust_root_sha256'),lock.get('semantic_authority_content_hash'))!=(PKG,TRUST,SEM): die('full package lock drift')
if lock.get('package_regular_file_count')!=61 or lock.get('package_checksum_entry_count')!=60: die('full package denominator drift')
fi=lock.get('full_fileset_integrity') or {}
if fi.get('checksum_verification')!='60/60_PASS' or fi.get('preformal_definition_checks')!='16/16_PASS' or fi.get('mandatory_regression_matrix')!='11/11_PASS' or fi.get('v2_1_9_evidence_state_system_logic_regression')!='24/24_PASS': die('full package verification drift')
if len(checks)!=60 or any(not re.match(r'^[0-9a-f]{64}  \S+',x) for x in checks): die('checksum manifest malformed/count drift')

na=cur.get('normative_authority') or {}
if na.get('version')!='v2.1.9' or (na.get('package_sha256'),na.get('external_trust_root_sha256'),na.get('semantic_authority_content_hash'))!=(PKG,TRUST,SEM): die('GOVERNANCE_CURRENT v219 drift')
if (base.get('governance_test') or {}).get('version')!='v2.1.9': die('branch baseline not v219')
if (stage.get('current_test_authority') or {}).get('version')!='v2.1.9': die('stage lock not v219')
if (seal.get('sealed_governance') or {}).get('version')!='v2.1.9': die('sealed current baseline not v219')

if state.get('state')!='PAGE_BASE_BLUEPRINT_COMPLETED': die('execution checkpoint drift')
if state.get('page_base_blueprint_completed') is not True or state.get('page_base_blueprint_count')!=2: die('page blueprint checkpoint incomplete')
if any(state.get(k) is True for k in ('visual_base_blueprint_started','blueprint_binding_started','website_construction_started','deployment_started')): die('later phase started before v219 closure')
if state.get('unresolved_authority_gap_count')!=8: die('external Authority gap count drift')
# Existing Page Blueprint artifacts were generated under v2.1.8 and remain immutable predecessor evidence.
if state.get('governance_candidate_overlay')!='v2.1.8': die('page replay predecessor overlay mutated before Visual successor start')

print('PASS: v2.1.9 evidence-state closure candidate hashes/denominators/current pointers are exact; superseded GitHub replay states are closed by exact run identities')
print('PASS: Stage-02 system-logic detector contract covers functional chain, dependency, permission/runtime/data, cross-page slice, error/retry, second-system and orphan guards')
print('PASS: Page Blueprint predecessor artifacts remain immutable v2.1.8 evidence; Visual/Binding/site/deploy remain unstarted')
