#!/usr/bin/env python3
from pathlib import Path
import copy,hashlib,yaml,subprocess
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'; intake=run/'00_SOURCE_INTAKE'; classroot=run/'01_CLASSIFIED'; bproot=run/'02_BASE_BLUEPRINT'
def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def stable(o): return hashlib.sha256(yaml.safe_dump(o,allow_unicode=True,sort_keys=True).encode()).hexdigest()
def bphash(d):
 x=copy.deepcopy(d)
 for k in ('content_hash','artifact_hash','blueprint_hash','binding_hash','structure_manifest_hash'): x.pop(k,None)
 return stable(x)
def gitobj(path):
 r=subprocess.run(['git','rev-parse','HEAD:'+path],text=True,capture_output=True)
 if r.returncode: die('git object missing:'+path)
 return r.stdout.strip()
s=load(run/'EXECUTION_STATE.yaml'); ci=s.get('github_ci') or {}
if s.get('governance_candidate_overlay')!='v2.1.9': die('Visual candidate must use v2.1.9')
if not (s.get('page_base_blueprint_completed') is True and ci.get('current_page_blueprint_gate')=='SUCCESS'): die('Page prerequisite not PASS')
if s.get('visual_base_blueprint_started') is not True or s.get('visual_base_blueprint_completed') is not True or s.get('visual_base_blueprint_count')!=2: die('Visual flags/count incomplete')
if s.get('blueprint_binding_started') is True or s.get('website_construction_started') is True or s.get('deployment_started') is True: die('later phase started early')
if gitobj('00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml')!='0c067fb8be186a899b42115a82d71312b4014502': die('CORE Page predecessor drift')
if gitobj('00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml')!='52bb27bf7eb423ddb13bcac5bd34edbcb369de3a': die('ASSET Page predecessor drift')
sf={}
for fn in ('SOURCE_CONTEXT_MANIFEST.yaml','CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml','SOURCE_DEPENDENCY_MAP.yaml'):
 d=load(intake/fn); sf[d.get('artifact_uid')]=d.get('content_hash')
dep=load(intake/'SOURCE_DEPENDENCY_MAP.yaml'); gaps=dep.get('unresolved_authority_gaps') or []
if len(gaps)!=8: die('source gap count drift')
arts={}
for p in classroot.rglob('*.yaml'):
 d=load(p); arts[d.get('artifact_uid')]=d
visual_by_page={'CORE-01':{},'ASSET-01':{}}
for uid,a in arts.items():
 if a.get('planning_domain')=='VISUAL_CONSTRUCTION': visual_by_page[a.get('page_uid')][uid]=a
if len(visual_by_page['CORE-01'])!=2 or len(visual_by_page['ASSET-01'])!=2: die('Visual classification split drift')
source_page={x.get('source_uid'):x.get('page_uid') for x in load(intake/'SOURCE_SEGMENT_MAP.yaml').get('raw_sources') or []}
for page in ('CORE-01','ASSET-01'):
 p=bproot/page/'VISUAL_BASE_BLUEPRINT.yaml'; d=load(p)
 if d.get('blueprint_type')!='VISUAL_BASE_BLUEPRINT' or d.get('planning_domain')!='VISUAL_CONSTRUCTION' or d.get('governance_overlay')!='v2.1.9': die('Visual identity drift:'+page)
 if d.get('target_path')!=f'02_BASE_BLUEPRINT/{page}/VISUAL_BASE_BLUEPRINT.yaml' or d.get('owner_mode')!='VISUAL': die('Visual owner/path drift:'+page)
 if {x.get('artifact_uid'):x.get('content_hash') for x in d.get('input_artifacts') or []}!={k:v.get('content_hash') for k,v in visual_by_page[page].items()}: die('Visual classified input/hash drift:'+page)
 if d.get('raw_source_inputs') not in ([],None) or d.get('embedded_classification_payloads') not in ([],None): die('Visual direct source/payload duplication:'+page)
 if {x.get('artifact_uid'):x.get('content_hash') for x in d.get('source_fact_refs') or []}!=sf: die('Visual source fact drift:'+page)
 relevant=[g for g in gaps if any(source_page.get(suid)==page for suid in g.get('consumer_source_uids') or [])]
 carry=d.get('unresolved_external_authority_refs') or []
 if {(x.get('gap_uid'),x.get('authority_ref')) for x in carry}!={(g.get('gap_uid'),g.get('authority_ref')) for g in relevant}: die('Visual Authority carry drift:'+page)
 if any(x.get('resolved') is True or x.get('satisfied') is True or x.get('auto_filled') is True or x.get('inferred') is True for x in carry): die('Visual false Authority resolution:'+page)
 if d.get('authority_resolution_performed') is not False or d.get('ai_autofill_used') is not False or d.get('inference_used') is not False: die('Visual synthetic resolution:'+page)
 if d.get('blueprint_hash')!=bphash(d): die('Visual blueprint hash mismatch:'+page)
ev=load(intake/'evidence/VISUAL_BASE_BLUEPRINT_EVIDENCE.yaml'); sm=ev.get('summary') or {}
if ev.get('status') not in {'MATERIALIZED_PENDING_CI','VERIFIED_CI_PASS'}: die('Visual evidence status invalid')
if (sm.get('visual_blueprint_count'),sm.get('visual_construction_input_artifacts'),sm.get('page_construction_input_artifacts'),sm.get('direct_raw_source_inputs'))!=(2,4,0,0): die('Visual evidence denominator drift')
print('PASS: v2.1.9 VISUAL_BASE_BLUEPRINT 2/2; CORE=2 ASSET=2; Page inputs=0; direct Raw Source=0')
print('PASS: Page predecessor blobs immutable; source gaps=8 carried by page scope; false resolution/autofill/inference=0; Binding/site/deploy remain unstarted')
