#!/usr/bin/env python3
from pathlib import Path
import yaml
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'
def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load((root/p).read_text(encoding='utf-8')) or {}
cand=load('governance/current/v2.1.9/CANDIDATE_RECORD.yaml'); lock=load('governance/current/v2.1.9/FULL_PACKAGE_LOCK.yaml'); s=load('00_SOURCE_INTAKE/fresh_run_003/EXECUTION_STATE.yaml'); ci=s.get('github_ci') or {}
if cand.get('version')!='v2.1.9' or cand.get('package_sha256')!='499aaccab4f38e089b465f98a2785dbef65faf304621db90599bc1dd55a9d24f' or lock.get('version')!='v2.1.9': die('v2.1.9 historical authority drift')
for k in ('page_base_blueprint_completed','visual_base_blueprint_completed'):
 if s.get(k) is not True: die('predecessor no longer complete:'+k)
if ci.get('v219_evidence_state_run_id')!=34737738652 or ci.get('visual_terminal_closure_run_id')!=34739267938: die('v2.1.9 evidence receipt drift')
if s.get('blueprint_binding_started') is True:
 if ci.get('v210_terminal_closure_run_id')!=34741356025 or ci.get('v210_terminal_closure_result')!='SUCCESS_9_OF_9': die('Binding successor lacks v2.1.10 terminal receipt')
if s.get('website_construction_started') is True or s.get('deployment_started') is True: die('site/deploy started early')
print('PASS: v2.1.9 evidence/system-logic predecessor remains valid under v2.1.10 Blueprint Binding successor')
