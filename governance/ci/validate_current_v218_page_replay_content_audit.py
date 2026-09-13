#!/usr/bin/env python3
from pathlib import Path
import subprocess,yaml
root=Path('.')
run=root/'00_SOURCE_INTAKE/fresh_run_003'
intake=run/'00_SOURCE_INTAKE'
auditp=intake/'evidence/V218_PAGE_REPLAY_CONTENT_AUDIT.yaml'
def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def gitobj(path):
    r=subprocess.run(['git','rev-parse','HEAD:'+path],text=True,capture_output=True)
    if r.returncode: die('git object missing:'+path)
    return r.stdout.strip()
a=load(auditp); s=load(run/'EXECUTION_STATE.yaml'); ev=load(intake/'evidence/PAGE_BASE_BLUEPRINT_EVIDENCE.yaml')
if a.get('status')!='VERIFIED_CI_PASS' or a.get('conclusion')!='CONTENT_AND_LINEAGE_VERIFIED': die('content audit status invalid')
if a.get('governance',{}).get('version')!='v2.1.8' or a.get('governance',{}).get('package_sha256')!='a108845fbde176cbd20a5f9df4217c68b6512686dedc00ffc8c44e9cc2b04753': die('governance identity drift')
expected_raw={
'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_CURRENT_CANONICAL_VISUAL_FINAL_LOCKED_V1.0.yaml':'09665c0a4a6b86db912f9b44160d336bfc611ae6',
'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml':'9490f3bcc28c5511bc04d6c3ce53c026e3c4667f',
'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml':'9668e2307c722ea4cf64f93f07c92da1b3abcc28'}
expected_sf={
'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/SOURCE_CONTEXT_MANIFEST.yaml':'c30c346060b7f217721db159d837c34c96e6b12f',
'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml':'410d324489cdf9a70f0565c7fdee1c4b7233b717',
'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml':'14d99735dcb0f9647c7906592233ef1bee0fe425'}
for p,h in {**expected_raw,**expected_sf}.items():
    if gitobj(p)!=h: die('immutable source blob drift:'+p)
if gitobj('00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml')!='cc7cdda1ff6dbb5001790de60b809d76d2fd7c9b': die('structure blob drift')
if gitobj('00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml')!='ebfdb6bad3f8c67fea34f76b7ed2280a0cbc2dae': die('segment map blob drift')
if gitobj('00_SOURCE_INTAKE/fresh_run_003/01_CLASSIFIED')!='973bfc5937cb1c06132d540654a053c4792b35a4': die('classification tree drift')
corep='00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml'; assetp='00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml'
if gitobj(corep)!='0c067fb8be186a899b42115a82d71312b4014502': die('CORE replay blueprint blob drift')
if gitobj(assetp)!='52bb27bf7eb423ddb13bcac5bd34edbcb369de3a': die('ASSET replay blueprint blob drift')
if gitobj(corep)=='600f9c5f61f2bc2ba1c933080e77b65d1f512f2d' or gitobj(assetp)=='5d6a5c7d595b53aaa8ef6a10326b9a92c74dc583': die('old v2.1.7 blueprint bytes reused')
core=load(root/corep); asset=load(root/assetp)
if len(core.get('input_artifacts') or [])!=23 or len(asset.get('input_artifacts') or [])!=25: die('Page Blueprint input count drift')
if len(core.get('unresolved_external_authority_refs') or [])!=7 or len(asset.get('unresolved_external_authority_refs') or [])!=6: die('Authority carry count drift')
for bp in (core,asset):
    if bp.get('governance_overlay')!='v2.1.8' or bp.get('raw_source_inputs') not in ([],None) or bp.get('embedded_classification_payloads') not in ([],None): die('Blueprint source isolation drift')
    if bp.get('authority_resolution_performed') is not False or bp.get('ai_autofill_used') is not False or bp.get('inference_used') is not False: die('synthetic Authority resolution')
    if any(x.get('resolved') is True or x.get('satisfied') is True or x.get('auto_filled') is True or x.get('inferred') is True for x in bp.get('unresolved_external_authority_refs') or []): die('Authority gap falsely resolved')
if s.get('state')!='PAGE_BASE_BLUEPRINT_COMPLETED' or s.get('governance_candidate_overlay')!='v2.1.8': die('execution closure state drift')
if (s.get('github_ci') or {}).get('page_replay_final_run_id')!=34734528373 or (s.get('github_ci') or {}).get('current_page_blueprint_gate')!='SUCCESS': die('final CI closure missing')
if any(s.get(k) is True for k in ('visual_base_blueprint_started','blueprint_binding_started','website_construction_started','deployment_started')): die('later phase started early')
if ev.get('status')!='VERIFIED_CI_PASS' or (ev.get('final_replay_verification') or {}).get('run_id')!=34734528373: die('Page Blueprint evidence closure drift')
print('PASS: v2.1.8 CORE/ASSET replay content audit; immutable sources/facts/classification preserved; two Page Blueprints regenerated and old bytes not reused')
print('PASS: PAGE inputs 23+25=48; source gaps=8, carry CORE=7 ASSET=6; false resolution/autofill/inference=0; Visual/Binding/site/deploy remain unstarted')
