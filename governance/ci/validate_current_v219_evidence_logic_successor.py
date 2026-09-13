#!/usr/bin/env python3
from pathlib import Path
import yaml
root=Path('.')
def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load((root/p).read_text(encoding='utf-8')) or {}
cand=load('governance/current/v2.1.9/CANDIDATE_RECORD.yaml'); lock=load('governance/current/v2.1.9/FULL_PACKAGE_LOCK.yaml'); state=load('00_SOURCE_INTAKE/fresh_run_003/EXECUTION_STATE.yaml')
if cand.get('version')!='v2.1.9' or cand.get('package_sha256')!='499aaccab4f38e089b465f98a2785dbef65faf304621db90599bc1dd55a9d24f': die('v219 historical candidate drift')
if lock.get('version')!='v2.1.9': die('v219 historical package lock drift')
if state.get('governance_candidate_overlay') not in {'v2.1.9','v2.1.10'}: die('unsupported governance successor overlay')
for k in ('page_base_blueprint_completed','visual_base_blueprint_completed'):
 if state.get(k) is not True: die('v219 predecessor artifact no longer completed:'+k)
ci=state.get('github_ci') or {}
if ci.get('v219_evidence_state_run_id')!=34737738652: die('v219 evidence closure run drift')
if ci.get('visual_terminal_closure_run_id')!=34739267938 or ci.get('visual_terminal_closure_head_sha')!='e653fbcf39a18775790c6403439b076c9ed3f534': die('v219 Visual terminal closure receipt drift')
if state.get('blueprint_binding_started') is True or state.get('website_construction_started') is True or state.get('deployment_started') is True: die('post-Visual phase started early')
print('PASS: historical v2.1.9 evidence/system-logic closure remains valid under v2.1.10 governance successor; exact Visual terminal receipt preserved')
