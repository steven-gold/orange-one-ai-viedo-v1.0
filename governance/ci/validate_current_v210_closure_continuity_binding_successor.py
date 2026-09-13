#!/usr/bin/env python3
from pathlib import Path
import yaml
root=Path('.')
PKG='a4df779f9de5c6b368c5382779e7759aa28f363da79ebd63acc8b6bc3672d205'; TRUST='a13311408767651557160c8d2aa849a6c53271a65ca51ea73a462aa551afe895'; SEM='98c0e60aaf0ffa125def7f89fef0fdeb4198d2ebb8ea5fd89ad79af4cbc61963'
def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load((root/p).read_text(encoding='utf-8')) or {}
s=load('00_SOURCE_INTAKE/fresh_run_003/EXECUTION_STATE.yaml'); runm=load('00_SOURCE_INTAKE/fresh_run_003/RUN_MANIFEST.yaml'); plan=load('00_SOURCE_INTAKE/fresh_run_003/ARTIFACT_PLAN.yaml'); cur=load('GOVERNANCE_CURRENT.yaml'); base=load('REBUILD_BRANCH_BASELINE.yaml'); stage=load('11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml'); seal=load('11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml'); cand=load('governance/current/v2.1.10/CANDIDATE_RECORD.yaml'); contract=load('governance/current/v2.1.10/CLOSURE_EVIDENCE_CONTINUITY_CONTRACT.yaml')
if (cand.get('package_sha256'),cand.get('external_trust_root_sha256'),cand.get('semantic_authority_content_hash'))!=(PKG,TRUST,SEM): die('v210 authority drift')
if set((contract.get('scope') or {}).get('applies_to_stages') or [])!={f'STAGE-{i:02d}' for i in range(1,12)}: die('continuity stage scope drift')
for k in ('source_segment_mapping_started','source_segment_mapping_completed','source_fact_materialization_started','source_fact_materialization_completed','responsibility_classification_started','responsibility_classification_completed','page_base_blueprint_started','page_base_blueprint_completed','visual_base_blueprint_started','visual_base_blueprint_completed'):
 if s.get(k) is not True: die('predecessor continuity lost:'+k)
if (s.get('source_structure_node_count'),s.get('source_segment_count'),s.get('classification_artifact_count'),s.get('page_base_blueprint_count'),s.get('visual_base_blueprint_count'),s.get('unresolved_authority_gap_count'))!=(61,61,52,2,2,8): die('predecessor denominator drift')
ci=s.get('github_ci') or {}
if ci.get('v210_terminal_closure_run_id')!=34741356025 or ci.get('v210_terminal_closure_head_sha')!='91f4271b5145f5646be07da32b5624fad7528034' or ci.get('v210_terminal_closure_result')!='SUCCESS_9_OF_9': die('v210 predecessor terminal receipt missing')
if s.get('blueprint_binding_started') is True:
 if s.get('state')!='BLUEPRINT_BINDING_COMPLETED' or s.get('blueprint_binding_completed') is not True or s.get('blueprint_binding_count')!=2: die('Binding state/denominator drift')
 if s.get('governance_candidate_overlay')!='v2.1.10': die('Binding governance overlay drift')
for obj,name in ((cur,'GOVERNANCE_CURRENT'),(base,'REBUILD_BRANCH_BASELINE'),(stage,'GOVERNANCE_STAGE_LOCK'),(seal,'SEALED_GOVERNANCE_TEST_BASELINE')):
 txt=yaml.safe_dump(obj,sort_keys=False)
 if '34741356025' not in txt or '91f4271b5145f5646be07da32b5624fad7528034' not in txt: die(name+' v210 predecessor receipt missing')
 if 'blueprint_binding' not in txt.lower(): die(name+' Binding synchronization missing')
if (runm.get('execution_policy') or {}).get('blueprint_binding')!='MATERIALIZED_2_BINDINGS_V210_PENDING_CI': die('RUN_MANIFEST Binding drift')
bm=plan.get('blueprint_binding_materialization') or {}
if bm.get('binding_count')!=2 or bm.get('mode')!='NON_OWNING_REFERENCE_ONLY': die('ARTIFACT_PLAN Binding drift')
if s.get('website_construction_started') is True or s.get('deployment_started') is True: die('site/deploy started in Stage-01')
print('PASS: v2.1.10 closure evidence continuity remains monotonic through Blueprint Binding; Current ledgers synchronized; predecessor receipts exact; site/deploy blocked')
