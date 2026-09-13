#!/usr/bin/env python3
from pathlib import Path
import yaml,re
root=Path('.')
PKG='499aaccab4f38e089b465f98a2785dbef65faf304621db90599bc1dd55a9d24f'
TRUST='7e3c2e523484a47f02ad45e6e1d8d9ccd6624904c76c67aa5f1856583e012ae1'
SEM='531a364590e47f182f40ac3794d9b30c7ae77678423a53be787ae1cd87c70c2f'
def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load((root/p).read_text(encoding='utf-8')) or {}
cand=load('governance/current/v2.1.9/CANDIDATE_RECORD.yaml'); lock=load('governance/current/v2.1.9/FULL_PACKAGE_LOCK.yaml'); cur=load('GOVERNANCE_CURRENT.yaml'); base=load('REBUILD_BRANCH_BASELINE.yaml'); stage=load('11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml'); seal=load('11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml'); state=load('00_SOURCE_INTAKE/fresh_run_003/EXECUTION_STATE.yaml'); checks=(root/'governance/current/v2.1.9/CHECKSUMS.sha256').read_text(encoding='utf-8').splitlines()
if cand.get('version')!='v2.1.9' or cand.get('baseline')!='v2.1.8': die('v219 candidate identity drift')
if (cand.get('package_sha256'),cand.get('external_trust_root_sha256'),cand.get('semantic_authority_content_hash'))!=(PKG,TRUST,SEM): die('v219 candidate hash drift')
expected={'preformal_definition_checks':'16/16_PASS','mandatory_matrix':'11/11_PASS','high_pressure':'25/25_PASS','reference_semantic':'28/28_PASS','reference_fuzz':'46/46_BLOCKED_0_ESCAPED','execution_load':'14/14_PASS','multidirection_stress':'21/21_PASS','stage1_minimal':'33/33_PASS','cross_lifecycle':'30/30_PASS','v217_phase_authority':'25/25_PASS','v218_successor_evidence_sync':'24/24_PASS','v219_evidence_state_system_logic':'24/24_PASS'}
for k,v in expected.items():
 if (cand.get('local_verification') or {}).get(k)!=v: die('local verification drift:'+k)
for k in ('page_functional_contract','functional_chain','dependency_map','permission_runtime_data','cross_page_system_logic_slice','error_retry_resume','second_system_guard','orphan_guard'):
 if (cand.get('stage02_system_logic_detection') or {}).get(k) is not True: die('Stage-02 detector missing:'+k)
if cand.get('human_formal_review')!='PENDING' or cand.get('formal_test_executed') is not False or cand.get('formal_freeze_claimed') is not False or cand.get('production_release_claimed') is not False: die('formal state overclaim')
gv=cand.get('github_verification') or {}
if gv.get('conclusion')!='SUCCESS' or gv.get('run_id')!=34737738652 or gv.get('jobs')!='7/7_SUCCESS': die('v219 closure evidence not exact')
if lock.get('version')!='v2.1.9' or (lock.get('source_package_sha256'),lock.get('external_trust_root_sha256'),lock.get('semantic_authority_content_hash'))!=(PKG,TRUST,SEM): die('package lock drift')
if lock.get('package_regular_file_count')!=61 or lock.get('package_checksum_entry_count')!=60 or len(checks)!=60 or any(not re.match(r'^[0-9a-f]{64}  \S+',x) for x in checks): die('package denominator/checksum drift')
na=cur.get('normative_authority') or {}
if na.get('version')!='v2.1.9' or (na.get('package_sha256'),na.get('external_trust_root_sha256'),na.get('semantic_authority_content_hash'))!=(PKG,TRUST,SEM): die('GOVERNANCE_CURRENT drift')
if (base.get('governance_test') or {}).get('version')!='v2.1.9' or (stage.get('current_test_authority') or {}).get('version')!='v2.1.9' or (seal.get('sealed_governance') or {}).get('version')!='v2.1.9': die('v219 current pointer drift')
if state.get('page_base_blueprint_completed') is not True or state.get('page_base_blueprint_count')!=2: die('Page predecessor incomplete')
if state.get('unresolved_authority_gap_count')!=8: die('Authority gap count drift')
visual=state.get('visual_base_blueprint_started') is True
if visual:
 if state.get('governance_candidate_overlay')!='v2.1.9': die('Visual successor must use v2.1.9')
 if (state.get('github_ci') or {}).get('current_page_blueprint_gate')!='SUCCESS': die('Visual successor lacks Page gate PASS')
else:
 if state.get('state')!='PAGE_BASE_BLUEPRINT_COMPLETED' or state.get('governance_candidate_overlay')!='v2.1.8': die('pre-Visual checkpoint drift')
if state.get('blueprint_binding_started') is True or state.get('website_construction_started') is True or state.get('deployment_started') is True: die('later phase started early')
print('PASS: v2.1.9 evidence/system-logic closure remains valid under legal Visual successor presence')
print('PASS: Stage-02 system-logic detector remains enforced; Page predecessor closed; Binding/site/deploy remain blocked')
