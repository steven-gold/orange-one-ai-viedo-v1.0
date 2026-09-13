#!/usr/bin/env python3
from pathlib import Path
import yaml,re
root=Path('.')
PKG='a4df779f9de5c6b368c5382779e7759aa28f363da79ebd63acc8b6bc3672d205'
TRUST='a13311408767651557160c8d2aa849a6c53271a65ca51ea73a462aa551afe895'
SEM='98c0e60aaf0ffa125def7f89fef0fdeb4198d2ebb8ea5fd89ad79af4cbc61963'
PREV_HEAD='e653fbcf39a18775790c6403439b076c9ed3f534'; PREV_RUN=34739267938

def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load((root/p).read_text(encoding='utf-8')) or {}
state=load('00_SOURCE_INTAKE/fresh_run_003/EXECUTION_STATE.yaml'); runm=load('00_SOURCE_INTAKE/fresh_run_003/RUN_MANIFEST.yaml'); plan=load('00_SOURCE_INTAKE/fresh_run_003/ARTIFACT_PLAN.yaml'); cur=load('GOVERNANCE_CURRENT.yaml'); base=load('REBUILD_BRANCH_BASELINE.yaml'); stage=load('11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml'); seal=load('11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml'); cand=load('governance/current/v2.1.10/CANDIDATE_RECORD.yaml'); lock=load('governance/current/v2.1.10/FULL_PACKAGE_LOCK.yaml'); contract=load('governance/current/v2.1.10/CLOSURE_EVIDENCE_CONTINUITY_CONTRACT.yaml')
if cand.get('version')!='v2.1.10' or cand.get('baseline')!='v2.1.9': die('v210 candidate identity drift')
if (cand.get('package_sha256'),cand.get('external_trust_root_sha256'),cand.get('semantic_authority_content_hash'))!=(PKG,TRUST,SEM): die('v210 candidate hash drift')
if cand.get('constituent_verification_sha256')!='4edb5d449a7bbb000f6233d94c54aa8db7c98d7c1c02ab7aee613bc542e0692': die('constituent verification hash drift')
loc=cand.get('local_verification') or {}
expected={'non_matrix_definition_checks':'16/16_PASS','mandatory_matrix':'12/12_PASS','v210_closure_continuity':'43/43_PASS','high_pressure':'25/25_PASS','reference_semantic':'28/28_PASS','reference_fuzz':'46/46_BLOCKED_0_ESCAPED','execution_load':'14/14_PASS','multidirection_stress':'21/21_PASS','stage1_minimal':'33/33_PASS','inherited_v210':'12/12_PASS','post_v18':'6/6_PASS','cross_lifecycle':'30/30_PASS','v217_phase_authority':'25/25_PASS','v218_successor_evidence_sync':'24/24_PASS','v219_evidence_state_system_logic':'24/24_PASS'}
for k,v in expected.items():
 if loc.get(k)!=v: die('v210 local verification drift:'+k)
if lock.get('version')!='v2.1.10' or (lock.get('source_package_sha256'),lock.get('external_trust_root_sha256'),lock.get('semantic_authority_content_hash'))!=(PKG,TRUST,SEM): die('v210 full lock drift')
if lock.get('package_regular_file_count')!=63 or lock.get('package_checksum_entry_count')!=62: die('v210 package denominator drift')
if (lock.get('verification') or {}).get('mandatory_regression_matrix')!='12/12_PASS': die('v210 mandatory matrix drift')
if set((contract.get('scope') or {}).get('applies_to_stages') or [])!={f'STAGE-{i:02d}' for i in range(1,12)}: die('continuity contract stage scope drift')
if (contract.get('closure_mutation') or {}).get('semantics')!='MERGE_APPEND_OR_EXPLICIT_SUPERSEDE' or (contract.get('closure_mutation') or {}).get('retroactive_predecessor_invalidation')!='FORBIDDEN': die('closure mutation contract drift')
tr=contract.get('terminal_ci_receipt') or {}
if tr.get('model')!='EXTERNAL_IMMUTABLE_RECEIPT' or tr.get('same_commit_self_write')!='FORBIDDEN' or tr.get('materialization_receipt_separate') is not True: die('terminal receipt contract drift')
na=cur.get('normative_authority') or {}
if na.get('version')!='v2.1.10' or (na.get('package_sha256'),na.get('external_trust_root_sha256'),na.get('semantic_authority_content_hash'))!=(PKG,TRUST,SEM): die('GOVERNANCE_CURRENT drift')
if (base.get('governance_test') or {}).get('version')!='v2.1.10' or (stage.get('current_test_authority') or {}).get('version')!='v2.1.10' or (seal.get('sealed_governance') or {}).get('version')!='v2.1.10': die('Current pointer version drift')
# predecessor facts must remain monotonic
for k in ('source_segment_mapping_started','source_segment_mapping_completed','source_fact_materialization_started','source_fact_materialization_completed','responsibility_classification_started','responsibility_classification_completed','page_base_blueprint_started','page_base_blueprint_completed','visual_base_blueprint_started','visual_base_blueprint_completed'):
 if state.get(k) is not True: die('predecessor fact missing/reverted:'+k)
if state.get('source_structure_node_count')!=61 or state.get('source_segment_count')!=61 or state.get('classification_artifact_count')!=52 or state.get('page_base_blueprint_count')!=2 or state.get('visual_base_blueprint_count')!=2 or state.get('unresolved_authority_gap_count')!=8: die('Current denominator drift')
if state.get('governance_candidate_overlay')!='v2.1.10' or state.get('state')!='VISUAL_BASE_BLUEPRINT_COMPLETED': die('Current execution identity drift')
if any(state.get(k) is True for k in ('blueprint_binding_started','website_construction_started','deployment_started')): die('later phase started before v210 governance receipt')
ci=state.get('github_ci') or {}
if ci.get('visual_terminal_closure_head_sha')!=PREV_HEAD or ci.get('visual_terminal_closure_run_id')!=PREV_RUN or ci.get('visual_terminal_closure_result')!='SUCCESS_8_OF_8': die('v219 terminal closure predecessor receipt missing')
for obj,name in ((cur,'GOVERNANCE_CURRENT'),(base,'REBUILD_BRANCH_BASELINE'),(stage,'GOVERNANCE_STAGE_LOCK'),(seal,'SEALED_GOVERNANCE_TEST_BASELINE')):
 txt=yaml.safe_dump(obj,sort_keys=False)
 if 'BLUEPRINT_BINDING' not in txt and 'blueprint_binding' not in txt: die(name+' next/binding synchronization missing')
 if str(PREV_RUN) not in txt: die(name+' predecessor terminal receipt missing')
# Manifest and plan must preserve phase/count/proof, not shrink to title-only summaries
if (runm.get('execution_policy') or {}).get('visual_blueprint_materialization')!='COMPLETED_2_VISUAL_BLUEPRINTS_V219_CI_PASS': die('RUN_MANIFEST predecessor phase drift')
if (runm.get('predecessor_terminal_receipt') or {}).get('run_id')!=PREV_RUN: die('RUN_MANIFEST terminal receipt drift')
vm=plan.get('visual_base_blueprint_materialization') or {}
if vm.get('blueprint_count')!=2 or (vm.get('terminal_closure_receipt') or {}).get('run_id')!=PREV_RUN: die('ARTIFACT_PLAN visual/receipt drift')
cr=cand.get('current_github_receipt') or {}
if cr.get('mode')!='EXTERNAL_IMMUTABLE_RECEIPT' or cr.get('receipt_required') is not True or cr.get('embedded_run_id') is not None or cr.get('same_commit_self_write')!='FORBIDDEN': die('v210 current receipt self-reference policy drift')
print('PASS: v2.1.10 closure evidence continuity is monotonic across Source -> Classification -> Page -> Visual; current ledgers synchronized and Binding/site/deploy remain unstarted')
print('PASS: Stage-01..Stage-11 common continuity contract active; predecessor Visual terminal receipt bound externally; current v2.1.10 receipt is not self-written')
