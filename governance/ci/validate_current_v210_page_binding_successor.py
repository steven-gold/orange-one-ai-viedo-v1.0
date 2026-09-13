#!/usr/bin/env python3
from pathlib import Path
import subprocess,yaml,sys
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'; intake=run/'00_SOURCE_INTAKE'
def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def gitobj(path):
 r=subprocess.run(['git','rev-parse','HEAD:'+path],text=True,capture_output=True)
 if r.returncode: die('git object missing:'+path)
 return r.stdout.strip()
r=subprocess.run([sys.executable,'governance/ci/validate_current_v218_page_base_blueprint.py'],text=True,capture_output=True)
if r.returncode!=0:
 print(r.stdout); print(r.stderr,file=sys.stderr); die('Page Blueprint predecessor validator failed')
s=load(run/'EXECUTION_STATE.yaml'); a=load(intake/'evidence/V218_PAGE_REPLAY_CONTENT_AUDIT.yaml'); ev=load(intake/'evidence/PAGE_BASE_BLUEPRINT_EVIDENCE.yaml'); ci=s.get('github_ci') or {}
if a.get('status')!='VERIFIED_CI_PASS' or a.get('conclusion')!='CONTENT_AND_LINEAGE_VERIFIED' or ev.get('status')!='VERIFIED_CI_PASS': die('Page predecessor evidence drift')
if gitobj('00_SOURCE_INTAKE/fresh_run_003/01_CLASSIFIED')!='973bfc5937cb1c06132d540654a053c4792b35a4': die('classification tree drift')
if gitobj('00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml')!='0c067fb8be186a899b42115a82d71312b4014502': die('CORE Page Blueprint drift')
if gitobj('00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml')!='52bb27bf7eb423ddb13bcac5bd34edbcb369de3a': die('ASSET Page Blueprint drift')
if s.get('blueprint_binding_started') is True:
 if not (s.get('visual_base_blueprint_completed') is True and ci.get('current_visual_blueprint_gate')=='SUCCESS'): die('Binding successor lacks Visual gate PASS')
 if ci.get('v210_terminal_closure_run_id')!=34741356025 or ci.get('v210_terminal_closure_head_sha')!='91f4271b5145f5646be07da32b5624fad7528034': die('Binding successor lacks v2.1.10 predecessor terminal receipt')
if s.get('website_construction_started') is True or s.get('deployment_started') is True: die('site/deploy started in Stage-01')
if s.get('unresolved_authority_gap_count')!=8: die('Authority gap universe drift')
print('PASS: Page predecessor remains immutable under legal Blueprint Binding successor; Classification/Page evidence exact; site/deploy blocked')
