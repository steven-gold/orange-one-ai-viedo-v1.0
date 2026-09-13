#!/usr/bin/env python3
from pathlib import Path
import yaml,subprocess,sys
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'
def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def gitobj(path):
 r=subprocess.run(['git','rev-parse','HEAD:'+path],text=True,capture_output=True);
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
if s.get('governance_candidate_overlay')!='v2.1.11' or s.get('stage1_validation_started') is True: die('successor state drift')
if s.get('website_construction_started') is True or s.get('deployment_started') is True: die('site/deploy started early')
print('PASS: v2.1.11 governance successor preserves Source->Classification->Page->Visual->Binding immutable lineage and monotonic evidence')
