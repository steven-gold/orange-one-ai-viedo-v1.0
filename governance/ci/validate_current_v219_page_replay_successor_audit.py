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
print(r.stdout.strip())
s=load(run/'EXECUTION_STATE.yaml'); a=load(intake/'evidence/V218_PAGE_REPLAY_CONTENT_AUDIT.yaml'); ev=load(intake/'evidence/PAGE_BASE_BLUEPRINT_EVIDENCE.yaml')
if a.get('status')!='VERIFIED_CI_PASS' or a.get('conclusion')!='CONTENT_AND_LINEAGE_VERIFIED': die('Page content audit evidence drift')
if ev.get('status')!='VERIFIED_CI_PASS': die('Page Blueprint evidence no longer closed')
if gitobj('00_SOURCE_INTAKE/fresh_run_003/01_CLASSIFIED')!='973bfc5937cb1c06132d540654a053c4792b35a4': die('classification tree drift')
if gitobj('00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml')!='0c067fb8be186a899b42115a82d71312b4014502': die('CORE Page Blueprint bytes drift')
if gitobj('00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml')!='52bb27bf7eb423ddb13bcac5bd34edbcb369de3a': die('ASSET Page Blueprint bytes drift')
ci=s.get('github_ci') or {}
if s.get('visual_base_blueprint_started') is True and ci.get('current_page_blueprint_gate')!='SUCCESS': die('Visual successor started before Page gate PASS')
if s.get('blueprint_binding_started') is True or s.get('website_construction_started') is True or s.get('deployment_started') is True: die('post-Visual phase started before Visual gate PASS')
if s.get('unresolved_authority_gap_count')!=8: die('Authority gap universe drift')
print('PASS: Page replay content audit is successor-aware in current workspace; legal Visual presence does not invalidate immutable Page evidence')
print('PASS: Page blobs/classification tree remain exact; Binding/site/deploy remain blocked until Visual CI closes')
