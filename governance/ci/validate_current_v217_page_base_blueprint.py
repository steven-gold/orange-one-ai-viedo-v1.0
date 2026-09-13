#!/usr/bin/env python3
from pathlib import Path
import hashlib,yaml,copy
root=Path('.')
run=root/'00_SOURCE_INTAKE/fresh_run_003'
intake=run/'00_SOURCE_INTAKE'
classroot=run/'01_CLASSIFIED'
bproot=run/'02_BASE_BLUEPRINT'

def die(msg): raise SystemExit(msg)
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def stable(o): return hashlib.sha256(yaml.safe_dump(o,allow_unicode=True,sort_keys=True).encode()).hexdigest()
def blueprint_hash(d):
    x=copy.deepcopy(d)
    for k in ('content_hash','artifact_hash','blueprint_hash','binding_hash','structure_manifest_hash'): x.pop(k,None)
    return stable(x)

state=load(run/'EXECUTION_STATE.yaml')
if state.get('state') not in {'PAGE_BASE_BLUEPRINT_ACTIVE','PAGE_BASE_BLUEPRINT_COMPLETED_PENDING_CI','PAGE_BASE_BLUEPRINT_COMPLETED'}: die('page base blueprint execution state mismatch')
if state.get('responsibility_classification_completed') is not True: die('classification not closed before page blueprint')
if (state.get('github_ci') or {}).get('current_classification_gate')!='SUCCESS': die('classification CI prerequisite not success')
if state.get('page_base_blueprint_started') is not True or state.get('page_base_blueprint_completed') is not True: die('page blueprint flags incomplete')
if state.get('page_base_blueprint_count')!=2: die('page blueprint count state drift')
for key in ('visual_base_blueprint_started','blueprint_binding_started','website_construction_started','deployment_started'):
    if state.get(key) is True: die('later phase started early: '+key)
if (run/'03_BLUEPRINT_BINDING').exists(): die('blueprint binding directory exists early')

sf={}
for fn in ('SOURCE_CONTEXT_MANIFEST.yaml','CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml','SOURCE_DEPENDENCY_MAP.yaml'):
    d=load(intake/fn); sf[d.get('artifact_uid')]=d.get('content_hash')
if len(sf)!=3 or None in sf or None in sf.values(): die('source fact refs incomplete')
dep=load(intake/'SOURCE_DEPENDENCY_MAP.yaml')
gaps=dep.get('unresolved_authority_gaps') or []
if len(gaps)!=8 or len({g.get('gap_uid') for g in gaps})!=8: die('external authority gap universe drift')
if any(g.get('disposition')!='UNRESOLVED_AUTHORITY_GAP' for g in gaps): die('external authority gap falsely resolved')
seg=load(intake/'SOURCE_SEGMENT_MAP.yaml')
source_page={x.get('source_uid'):x.get('page_uid') for x in seg.get('raw_sources') or []}

arts={}
for p in sorted(classroot.rglob('*.yaml')):
    d=load(p); uid=d.get('artifact_uid')
    if not uid or uid in arts: die('classification UID duplicate/missing')
    arts[uid]=d
if len(arts)!=52: die('classification artifact universe not 52')
page_arts={page:{} for page in ('CORE-01','ASSET-01')}
visual_count=0
for uid,a in arts.items():
    if a.get('planning_domain')=='PAGE_CONSTRUCTION': page_arts.setdefault(a.get('page_uid'),{})[uid]=a
    elif a.get('planning_domain')=='VISUAL_CONSTRUCTION': visual_count+=1
    else: die('classification domain invalid: '+str(uid))
if sum(len(v) for v in page_arts.values())!=48 or visual_count!=4: die('48/4 classification domain split drift')
if len(page_arts.get('CORE-01',{}))!=23 or len(page_arts.get('ASSET-01',{}))!=25: die('per-page PAGE classification count drift')

blueprints={}
for p in sorted(bproot.rglob('*.yaml')) if bproot.exists() else []:
    d=load(p); uid=d.get('blueprint_uid'); rel=p.relative_to(run).as_posix()
    if not uid or uid in blueprints: die('duplicate/missing blueprint UID')
    if d.get('blueprint_type')!='PAGE_BASE_BLUEPRINT' or d.get('planning_domain')!='PAGE_CONSTRUCTION': die('non-page blueprint exists in page blueprint phase: '+str(uid))
    if d.get('status')!='CURRENT_BASE_BLUEPRINT': die('page blueprint not current: '+str(uid))
    page=d.get('page_uid')
    if page not in {'CORE-01','ASSET-01'}: die('page blueprint scope invalid: '+str(page))
    expected_path=f'02_BASE_BLUEPRINT/{page}/PAGE_BASE_BLUEPRINT.yaml'
    if rel!=expected_path or d.get('target_path')!=expected_path: die('page blueprint path mismatch: '+str(uid))
    if d.get('editable_owner_uid')!=f'OWNER-{page}-PAGE-BASE-BLUEPRINT' or d.get('owner_mode')!='PAGE': die('page blueprint owner mismatch: '+str(uid))
    if d.get('raw_source_inputs') not in ([],None): die('page blueprint direct Raw Source input: '+str(uid))
    if d.get('embedded_classification_payloads') not in ([],None): die('page blueprint embeds classification payload: '+str(uid))
    if d.get('shared_refs') not in ([],None): die('unexpected shared refs in current page blueprint: '+str(uid))
    if d.get('authority_resolution_performed') is not False or d.get('ai_autofill_used') is not False or d.get('inference_used') is not False: die('synthetic authority resolution marker: '+str(uid))
    expected_inputs={k:v.get('content_hash') for k,v in page_arts[page].items()}
    actual_inputs={x.get('artifact_uid'):x.get('content_hash') for x in d.get('input_artifacts') or []}
    if actual_inputs!=expected_inputs: die('page blueprint input coverage/hash mismatch: '+str(uid))
    if len(actual_inputs)!=len(d.get('input_artifacts') or []): die('page blueprint duplicate input: '+str(uid))
    expected_resp={v.get('responsibility_uid') for v in page_arts[page].values()}
    actual_resp=set(d.get('required_responsibility_uids') or [])
    if actual_resp!=expected_resp or len(actual_resp)!=len(d.get('required_responsibility_uids') or []): die('page blueprint responsibility coverage mismatch: '+str(uid))
    actual_sf={x.get('artifact_uid'):x.get('content_hash') for x in d.get('source_fact_refs') or []}
    if actual_sf!=sf: die('page blueprint source fact hash binding incomplete/stale: '+str(uid))
    relevant=[]
    for g in gaps:
        if any(source_page.get(suid)==page for suid in g.get('consumer_source_uids') or []): relevant.append(g)
    expected_gap={(g.get('gap_uid'),g.get('authority_ref'),'UNRESOLVED_AUTHORITY_GAP') for g in relevant}
    carry=d.get('unresolved_external_authority_refs') or []
    actual_gap={(x.get('gap_uid'),x.get('authority_ref'),x.get('disposition')) for x in carry}
    if actual_gap!=expected_gap: die('page blueprint external Authority carry mismatch: '+str(uid))
    if len(carry)!=len(actual_gap): die('page blueprint external Authority duplicate: '+str(uid))
    for x in carry:
        if x.get('resolved') is True or x.get('satisfied') is True or x.get('auto_filled') is True or x.get('inferred') is True or x.get('substitute_authority_ref'): die('page blueprint external Authority false resolution: '+str(x.get('gap_uid')))
    if d.get('blueprint_hash')!=blueprint_hash(d): die('page blueprint hash mismatch: '+str(uid))
    blueprints[uid]=d
if len(blueprints)!=2: die('physical PAGE_BASE_BLUEPRINT count not 2: '+str(len(blueprints)))
if {d.get('page_uid') for d in blueprints.values()}!={'CORE-01','ASSET-01'}: die('page blueprint page set mismatch')

ev=load(intake/'evidence/PAGE_BASE_BLUEPRINT_EVIDENCE.yaml')
if ev.get('status') not in {'MATERIALIZED_PENDING_CI','VERIFIED_CI_PASS'}: die('page blueprint evidence status invalid')
sm=ev.get('summary') or {}
if sm.get('page_blueprint_count')!=2 or sm.get('page_construction_input_artifacts')!=48 or sm.get('visual_construction_input_artifacts')!=0 or sm.get('direct_raw_source_inputs')!=0 or sm.get('embedded_classification_payloads')!=0: die('page blueprint evidence summary mismatch')
pp=ev.get('per_page') or {}
if pp.get('CORE-01',{}).get('artifact_count')!=23 or pp.get('ASSET-01',{}).get('artifact_count')!=25: die('page blueprint evidence per-page counts mismatch')
ea=ev.get('external_authority_preservation') or {}
if ea.get('source_gap_count')!=8 or ea.get('core_01_carried_gap_count')!=7 or ea.get('asset_01_carried_gap_count')!=6 or ea.get('identity_drift')!=0 or ea.get('resolution_performed') is not False: die('page blueprint authority evidence mismatch')
print('PASS: PAGE_BASE_BLUEPRINT 2/2 current; CORE-01 inputs=23, ASSET-01 inputs=25; PAGE-only domain isolation; direct Raw Source=0')
print('PASS: 8 unresolved external Authority source gaps preserved into page-scoped carry sets CORE=7 / ASSET=6; no auto-fill/inference/false resolution; Visual/Binding/website/deployment remain unstarted')
