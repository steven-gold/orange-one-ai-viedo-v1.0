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
s=load(run/'EXECUTION_STATE.yaml'); ci=s.get('github_ci') or {}
expected={'CORE-01':('8edd134ea4610ab3cb192bca7b3a34ec24ae6368','011e80a21b6f2c822f5234e4af8f9e5163485c3dff862cb76a886abf04c3683e',7),'ASSET-01':('f09ec9e4ccbedd1487c91592cb1df83ba5e62464','734e687f7798d97964b04eb7e79e579fef2e41f259c900b03c606ae6271aeef8',6)}
for page,(blob,bphash,gaps) in expected.items():
 p=root/f'00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/{page}/VISUAL_BASE_BLUEPRINT.yaml'; d=load(p)
 if gitobj(p.relative_to(root).as_posix())!=blob: die(page+' Visual blob drift')
 if d.get('blueprint_hash')!=bphash or len(d.get('unresolved_external_authority_refs') or [])!=gaps: die(page+' Visual hash/gap drift')
 if d.get('raw_source_inputs') not in ([],None) or d.get('embedded_classification_payloads') not in ([],None): die(page+' Visual isolation drift')
if s.get('visual_base_blueprint_completed') is not True or s.get('visual_base_blueprint_count')!=2: die('Visual completion drift')
if ci.get('visual_terminal_closure_run_id')!=34739267938 or ci.get('visual_terminal_closure_head_sha')!='e653fbcf39a18775790c6403439b076c9ed3f534': die('Visual terminal receipt drift')
if s.get('blueprint_binding_started') is True:
 if ci.get('current_visual_blueprint_gate')!='SUCCESS': die('Binding began without Visual Gate SUCCESS')
 if ci.get('v210_terminal_closure_run_id')!=34741356025 or ci.get('v210_terminal_closure_head_sha')!='91f4271b5145f5646be07da32b5624fad7528034': die('Binding began without v210 external terminal receipt')
if s.get('website_construction_started') is True or s.get('deployment_started') is True: die('post-Binding site/deploy started early')
print('PASS: Visual predecessor remains immutable and valid under legal Blueprint Binding successor; exact v2.1.9/v2.1.10 terminal receipts preserved')
