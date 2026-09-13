#!/usr/bin/env python3
from pathlib import Path
import hashlib,yaml,copy
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'; intake=run/'00_SOURCE_INTAKE'; classroot=run/'01_CLASSIFIED'; bproot=run/'02_BASE_BLUEPRINT'
def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def stable(o): return hashlib.sha256(yaml.safe_dump(o,allow_unicode=True,sort_keys=True).encode()).hexdigest()
def blueprint_hash(d):
    x=copy.deepcopy(d)
    for k in ('content_hash','artifact_hash','blueprint_hash','binding_hash','structure_manifest_hash'): x.pop(k,None)
    return stable(x)
state=load(run/'EXECUTION_STATE.yaml'); ci=state.get('github_ci') or {}
if state.get('responsibility_classification_completed') is not True or ci.get('current_classification_gate')!='SUCCESS': die('classification prerequisite not closed/PASS')
if state.get('page_base_blueprint_started') is not True or state.get('page_base_blueprint_completed') is not True or state.get('page_base_blueprint_count')!=2: die('page blueprint flags/count incomplete')
if any(state.get(k) is True for k in ('visual_base_blueprint_started','blueprint_binding_started')) and ci.get('current_page_blueprint_gate')!='SUCCESS': die('legal successor started before Page Blueprint CI PASS')
sf={}
for fn in ('SOURCE_CONTEXT_MANIFEST.yaml','CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml','SOURCE_DEPENDENCY_MAP.yaml'):
    d=load(intake/fn); sf[d.get('artifact_uid')]=d.get('content_hash')
if len(sf)!=3 or None in sf or None in sf.values(): die('source fact refs incomplete')
dep=load(intake/'SOURCE_DEPENDENCY_MAP.yaml'); gaps=dep.get('unresolved_authority_gaps') or []
if len(gaps)!=8 or len({g.get('gap_uid') for g in gaps})!=8 or any(g.get('disposition')!='UNRESOLVED_AUTHORITY_GAP' for g in gaps): die('external Authority gap drift')
seg=load(intake/'SOURCE_SEGMENT_MAP.yaml'); source_page={x.get('source_uid'):x.get('page_uid') for x in seg.get('raw_sources') or []}
arts={}
for p in sorted(classroot.rglob('*.yaml')):
    d=load(p); uid=d.get('artifact_uid')
    if not uid or uid in arts: die('classification UID duplicate/missing')
    arts[uid]=d
if len(arts)!=52: die('classification universe not 52')
page_arts={p:{} for p in ('CORE-01','ASSET-01')}; visual=0
for uid,a in arts.items():
    if a.get('planning_domain')=='PAGE_CONSTRUCTION': page_arts[a.get('page_uid')][uid]=a
    elif a.get('planning_domain')=='VISUAL_CONSTRUCTION': visual+=1
    else: die('classification domain invalid:'+uid)
if len(page_arts['CORE-01'])!=23 or len(page_arts['ASSET-01'])!=25 or visual!=4: die('48/4 classification split drift')
blueprints={}
for p in sorted(bproot.rglob('PAGE_BASE_BLUEPRINT.yaml')):
    d=load(p); uid=d.get('blueprint_uid'); page=d.get('page_uid'); rel=p.relative_to(run).as_posix()
    if not uid or uid in blueprints or page not in {'CORE-01','ASSET-01'}: die('page blueprint identity drift')
    if d.get('blueprint_type')!='PAGE_BASE_BLUEPRINT' or d.get('planning_domain')!='PAGE_CONSTRUCTION' or d.get('status')!='CURRENT_BASE_BLUEPRINT': die('page blueprint type/status drift:'+str(uid))
    exp=f'02_BASE_BLUEPRINT/{page}/PAGE_BASE_BLUEPRINT.yaml'
    if rel!=exp or d.get('target_path')!=exp or d.get('editable_owner_uid')!=f'OWNER-{page}-PAGE-BASE-BLUEPRINT' or d.get('owner_mode')!='PAGE': die('page blueprint owner/path drift:'+uid)
    if d.get('raw_source_inputs') not in ([],None) or d.get('embedded_classification_payloads') not in ([],None): die('page blueprint direct source/payload duplication:'+uid)
    if d.get('authority_resolution_performed') is not False or d.get('ai_autofill_used') is not False or d.get('inference_used') is not False: die('synthetic Authority resolution:'+uid)
    if {x.get('artifact_uid'):x.get('content_hash') for x in d.get('input_artifacts') or []}!={k:v.get('content_hash') for k,v in page_arts[page].items()}: die('page blueprint classified input/hash drift:'+uid)
    if {x.get('artifact_uid'):x.get('content_hash') for x in d.get('source_fact_refs') or []}!=sf: die('page blueprint source fact drift:'+uid)
    relevant=[g for g in gaps if any(source_page.get(suid)==page for suid in g.get('consumer_source_uids') or [])]
    expected={(g.get('gap_uid'),g.get('authority_ref'),'UNRESOLVED_AUTHORITY_GAP') for g in relevant}; carry=d.get('unresolved_external_authority_refs') or []
    actual={(x.get('gap_uid'),x.get('authority_ref'),x.get('disposition')) for x in carry}
    if actual!=expected or len(carry)!=len(actual): die('page blueprint Authority carry drift:'+uid)
    if any(x.get('resolved') is True or x.get('satisfied') is True or x.get('auto_filled') is True or x.get('inferred') is True or x.get('substitute_authority_ref') for x in carry): die('page blueprint false Authority resolution:'+uid)
    if d.get('blueprint_hash')!=blueprint_hash(d): die('page blueprint hash mismatch:'+uid)
    blueprints[uid]=d
if len(blueprints)!=2 or {d.get('page_uid') for d in blueprints.values()}!={'CORE-01','ASSET-01'}: die('physical Page Blueprint set drift')
ev=load(intake/'evidence/PAGE_BASE_BLUEPRINT_EVIDENCE.yaml'); sm=ev.get('summary') or {}; ea=ev.get('external_authority_preservation') or {}
if ev.get('status') not in {'MATERIALIZED_PENDING_CI','VERIFIED_CI_PASS'} or (sm.get('page_blueprint_count'),sm.get('page_construction_input_artifacts'),sm.get('visual_construction_input_artifacts'),sm.get('direct_raw_source_inputs'))!=(2,48,0,0): die('Page Blueprint evidence drift')
if (ea.get('source_gap_count'),ea.get('core_01_carried_gap_count'),ea.get('asset_01_carried_gap_count'),ea.get('identity_drift'))!=(8,7,6,0) or ea.get('resolution_performed') is not False: die('Page Blueprint Authority evidence drift')
print('PASS: v2.1.8 successor-aware PAGE_BASE_BLUEPRINT 2/2; CORE=23, ASSET=25; direct Raw Source=0')
print('PASS: legal Visual/Binding successor presence does not retroactively invalidate closed Page Blueprint; phase order is owned by Phase Boundary Gate')
