#!/usr/bin/env python3
from pathlib import Path
import yaml,subprocess
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'; bp=run/'02_BASE_BLUEPRINT'
def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def gitobj(path):
 r=subprocess.run(['git','rev-parse','HEAD:'+path],text=True,capture_output=True)
 if r.returncode: die('git object missing:'+path)
 return r.stdout.strip()
state=load(run/'EXECUTION_STATE.yaml')
if state.get('governance_candidate_overlay') not in {'v2.1.9','v2.1.10'}: die('unsupported Visual successor governance overlay')
expected={
 'CORE-01':('8edd134ea4610ab3cb192bca7b3a34ec24ae6368','011e80a21b6f2c822f5234e4af8f9e5163485c3dff862cb76a886abf04c3683e',2,7),
 'ASSET-01':('f09ec9e4ccbedd1487c91592cb1df83ba5e62464','734e687f7798d97964b04eb7e79e579fef2e41f259c900b03c606ae6271aeef8',2,6)}
for page,(blob,bphash,count,gaps) in expected.items():
 path=f'00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/{page}/VISUAL_BASE_BLUEPRINT.yaml'
 if gitobj(path)!=blob: die(page+' Visual Blueprint immutable blob drift')
 d=load(root/path)
 if d.get('governance_overlay')!='v2.1.9' or d.get('blueprint_type')!='VISUAL_BASE_BLUEPRINT' or d.get('planning_domain')!='VISUAL_CONSTRUCTION': die(page+' Visual historical identity drift')
 if d.get('blueprint_hash')!=bphash or len(d.get('input_artifacts') or [])!=count or len(d.get('unresolved_external_authority_refs') or [])!=gaps: die(page+' Visual denominator/hash drift')
 if d.get('raw_source_inputs') not in ([],None) or d.get('embedded_classification_payloads') not in ([],None): die(page+' Visual source isolation drift')
if state.get('visual_base_blueprint_completed') is not True or state.get('visual_base_blueprint_count')!=2: die('Visual completion state drift')
ci=state.get('github_ci') or {}
if ci.get('visual_terminal_closure_run_id')!=34739267938 or ci.get('visual_terminal_closure_head_sha')!='e653fbcf39a18775790c6403439b076c9ed3f534': die('Visual terminal receipt missing')
if state.get('blueprint_binding_started') is True or state.get('website_construction_started') is True or state.get('deployment_started') is True: die('post-Visual phase started early')
print('PASS: v2.1.9 Visual Base Blueprints remain immutable and valid under v2.1.10 governance successor; terminal closure receipt exact')
