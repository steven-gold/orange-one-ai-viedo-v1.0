#!/usr/bin/env python3
from pathlib import Path
import yaml,subprocess
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'
def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def gitobj(path):
 r=subprocess.run(['git','rev-parse','HEAD:'+path],text=True,capture_output=True)
 if r.returncode: die('git object missing:'+path)
 return r.stdout.strip()
expected={'CORE-01':('0c067fb8be186a899b42115a82d71312b4014502','8edd134ea4610ab3cb192bca7b3a34ec24ae6368','8180bda073fcd26e82372e6ae15b256026a5544e'),'ASSET-01':('52bb27bf7eb423ddb13bcac5bd34edbcb369de3a','f09ec9e4ccbedd1487c91592cb1df83ba5e62464','1879d88110a430fa261660ec5052e9468a6adcdd')}
for page,(pb,vb,bb) in expected.items():
 if gitobj(f'00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/{page}/PAGE_BASE_BLUEPRINT.yaml')!=pb: die(page+' Page predecessor drift')
 if gitobj(f'00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/{page}/VISUAL_BASE_BLUEPRINT.yaml')!=vb: die(page+' Visual predecessor drift')
 if gitobj(f'00_SOURCE_INTAKE/fresh_run_003/03_BLUEPRINT_BINDING/{page}/BLUEPRINT_BINDING_MANIFEST.yaml')!=bb: die(page+' Binding predecessor drift')
s=load(run/'EXECUTION_STATE.yaml')
for k in ('source_segment_mapping_started','source_segment_mapping_completed','source_fact_materialization_started','source_fact_materialization_completed','responsibility_classification_started','responsibility_classification_completed','page_base_blueprint_started','page_base_blueprint_completed','visual_base_blueprint_started','visual_base_blueprint_completed','blueprint_binding_started','blueprint_binding_completed'):
 if s.get(k) is not True: die('predecessor continuity lost:'+k)
if (s.get('source_segment_count'),s.get('classification_artifact_count'),s.get('page_base_blueprint_count'),s.get('visual_base_blueprint_count'),s.get('blueprint_binding_count'),s.get('unresolved_authority_gap_count'))!=(61,52,2,2,2,8): die('denominator drift')
if s.get('governance_candidate_overlay')!='v2.1.11': die('governance successor drift')
allowed={'BLUEPRINT_BINDING_COMPLETED','STAGE1_VALIDATION_COMPLETED_PENDING_CI'}
if s.get('state') not in allowed: die('unsupported legal successor state')
if s.get('state')=='STAGE1_VALIDATION_COMPLETED_PENDING_CI':
 if not (s.get('stage1_validation_started') is True and s.get('stage1_validation_completed') is True): die('Stage1 validation successor incomplete')
 if s.get('stage1_exit_gate')!='PENDING_EXTERNAL_CI': die('Stage1 exit-gate drift')
 ci=s.get('github_ci') or {}
 if ci.get('v211_terminal_closure_run_id')!=34754709362 or ci.get('v211_terminal_closure_head_sha')!='74cd16e28e98a918c3f682d3b29ea7e362a19cc5' or ci.get('v211_terminal_closure_result')!='SUCCESS_11_OF_11': die('Stage1 successor lacks v2.1.11 predecessor receipt')
if s.get('stage2_started') is True or s.get('website_construction_started') is True or s.get('deployment_started') is True: die('post-Stage1 phase started early')
print('PASS: v2.1.11 continuity predecessor preserves Source->Classification->Page->Visual->Binding immutable lineage under legal Stage-01 Validation successor')
print('PASS: monotonic evidence/counts remain exact; Stage2/site/deploy remain blocked pending Stage-01 external closure receipt')
