#!/usr/bin/env python3
from pathlib import Path
import yaml,hashlib,copy,subprocess
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'; bindroot=run/'03_BLUEPRINT_BINDING'
def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def stable(o): return hashlib.sha256(yaml.safe_dump(o,allow_unicode=True,sort_keys=True).encode()).hexdigest()
def bhash(d):
 x=copy.deepcopy(d); x.pop('binding_hash',None); return stable(x)
def gitobj(path):
 r=subprocess.run(['git','rev-parse','HEAD:'+path],text=True,capture_output=True)
 if r.returncode: die('git object missing:'+path)
 return r.stdout.strip()
expected={
'CORE-01':{'uid':'V210-BIND-CORE-01-PAGE-VISUAL','page_uid':'V218-REPLAY-BP-CORE-01-PAGE-BASE','page_hash':'6c76ff5da65b6b000d493b74c06f6900ee53016801a73d966bd8b9569e21cd39','page_blob':'0c067fb8be186a899b42115a82d71312b4014502','visual_uid':'V219-BP-CORE-01-VISUAL-BASE','visual_hash':'011e80a21b6f2c822f5234e4af8f9e5163485c3dff862cb76a886abf04c3683e','visual_blob':'8edd134ea4610ab3cb192bca7b3a34ec24ae6368','gaps':7},
'ASSET-01':{'uid':'V210-BIND-ASSET-01-PAGE-VISUAL','page_uid':'V218-REPLAY-BP-ASSET-01-PAGE-BASE','page_hash':'ea78941da24ddedda2b0e73f0027261b0b4ceb44940e004c9997b45ca8f04376','page_blob':'52bb27bf7eb423ddb13bcac5bd34edbcb369de3a','visual_uid':'V219-BP-ASSET-01-VISUAL-BASE','visual_hash':'734e687f7798d97964b04eb7e79e579fef2e41f259c900b03c606ae6271aeef8','visual_blob':'f09ec9e4ccbedd1487c91592cb1df83ba5e62464','gaps':6}}
files=sorted(bindroot.rglob('BLUEPRINT_BINDING_MANIFEST.yaml')) if bindroot.exists() else []
if len(files)!=2: die('binding file count != 2')
seen=set(); gap_universe=set()
for p in files:
 d=load(p); page=d.get('page_uid'); e=expected.get(page)
 if not e or page in seen: die('unknown/duplicate binding page:'+str(page))
 seen.add(page)
 if d.get('binding_uid')!=e['uid'] or d.get('binding_type')!='BLUEPRINT_BINDING_MANIFEST' or d.get('governance_overlay')!='v2.1.10' or d.get('binding_mode')!='NON_OWNING_REFERENCE_ONLY' or d.get('status')!='CURRENT_BLUEPRINT_BINDING': die(page+' Binding identity drift')
 if d.get('editable_owner_uid') is not None: die(page+' Binding became editable owner')
 if d.get('target_path')!=p.relative_to(run).as_posix(): die(page+' Binding target path drift')
 pr=d.get('page_blueprint') or {}; vr=d.get('visual_blueprint') or {}
 if (pr.get('blueprint_uid'),pr.get('blueprint_hash'),pr.get('git_blob'))!=(e['page_uid'],e['page_hash'],e['page_blob']): die(page+' Page ref/hash/blob drift')
 if (vr.get('blueprint_uid'),vr.get('blueprint_hash'),vr.get('git_blob'))!=(e['visual_uid'],e['visual_hash'],e['visual_blob']): die(page+' Visual ref/hash/blob drift')
 if gitobj(f'00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/{page}/PAGE_BASE_BLUEPRINT.yaml')!=e['page_blob'] or gitobj(f'00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/{page}/VISUAL_BASE_BLUEPRINT.yaml')!=e['visual_blob']: die(page+' predecessor bytes changed')
 if d.get('embedded_blueprint_payloads') not in ([],None) or d.get('raw_source_inputs') not in ([],None): die(page+' Binding duplicated payload/raw source')
 carry=d.get('unresolved_external_authority_refs') or []
 if len(carry)!=e['gaps']: die(page+' Authority gap carry count drift')
 for g in carry:
  gap_universe.add(g.get('gap_uid'))
  if g.get('disposition')!='UNRESOLVED_AUTHORITY_GAP' or any(g.get(k) is True for k in ('resolved','satisfied','auto_filled','inferred')): die(page+' false Authority resolution')
 if d.get('authority_resolution_performed') is not False or d.get('ai_autofill_used') is not False or d.get('inference_used') is not False: die(page+' synthetic resolution')
 if d.get('binding_hash')!=bhash(d): die(page+' binding hash mismatch')
if gap_universe!={f'GAP-{i:03d}' for i in range(1,9)}: die('Authority gap universe drift')
s=load(run/'EXECUTION_STATE.yaml'); ci=s.get('github_ci') or {}
if not (s.get('blueprint_binding_started') is True and s.get('blueprint_binding_completed') is True and s.get('blueprint_binding_count')==2): die('Binding execution state incomplete')
if ci.get('v210_terminal_closure_run_id')!=34741356025 or ci.get('v210_terminal_closure_result')!='SUCCESS_9_OF_9': die('Binding lacks v210 predecessor receipt')
if s.get('website_construction_started') is True or s.get('deployment_started') is True: die('site/deploy started early')
ev=load(run/'00_SOURCE_INTAKE/evidence/BLUEPRINT_BINDING_EVIDENCE.yaml'); sm=ev.get('summary') or {}
if ev.get('status') not in {'MATERIALIZED_PENDING_CI','VERIFIED_CI_PASS'} or (sm.get('binding_count'),sm.get('page_blueprint_refs'),sm.get('visual_blueprint_refs'),sm.get('embedded_blueprint_payloads'),sm.get('direct_raw_source_inputs'))!=(2,2,2,0,0): die('Binding evidence denominator/status drift')
print('PASS: Blueprint Binding 2/2; non-owning UID/hash/blob refs exact; embedded payload=0; direct Raw Source=0')
print('PASS: Authority gaps preserved (universe=8, CORE=7, ASSET=6); false resolution/autofill/inference=0; Page/Visual predecessor bytes immutable; site/deploy blocked')
