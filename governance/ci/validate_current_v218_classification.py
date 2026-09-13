#!/usr/bin/env python3
from pathlib import Path
import hashlib,re,yaml
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'; intake=run/'00_SOURCE_INTAKE'; classroot=run/'01_CLASSIFIED'
def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def stable(o): return hashlib.sha256(yaml.safe_dump(o,allow_unicode=True,sort_keys=True).encode()).hexdigest()
def content_hash(d): x=dict(d); x.pop('content_hash',None); return stable(x)
def artifact_hash(d): x=dict(d); x.pop('content_hash',None); x.pop('artifact_hash',None); return stable(x)
def resp(ref): return re.sub(r'[^A-Za-z0-9]+','_',str(ref)[2:] if str(ref).startswith('$.') else str(ref)).strip('_').upper()
state=load(run/'EXECUTION_STATE.yaml'); ci=state.get('github_ci') or {}
if state.get('source_fact_materialization_completed') is not True: die('source facts not closed before classification')
if state.get('responsibility_classification_started') is not True or state.get('responsibility_classification_completed') is not True: die('classification flags incomplete')
successor_started=any(state.get(k) is True for k in ('page_base_blueprint_started','visual_base_blueprint_started','blueprint_binding_started'))
if successor_started and ci.get('current_classification_gate')!='SUCCESS': die('legal successor started before classification CI PASS')
struct=load(intake/'SOURCE_STRUCTURE_MANIFEST.yaml'); seg=load(intake/'SOURCE_SEGMENT_MAP.yaml'); dep=load(intake/'SOURCE_DEPENDENCY_MAP.yaml'); ctx=load(intake/'SOURCE_CONTEXT_MANIFEST.yaml')
if struct.get('observed_node_count')!=61: die('structure count drift')
nodes={}; source_page={}
for s in struct.get('sources') or []:
    source_page[s['source_uid']]=s['page_uid']
    for n in s.get('observed_nodes') or []: nodes[n['source_node_uid']]={'source_uid':s['source_uid'],'page_uid':s['page_uid'],'source_ref':n['source_ref']}
if len(nodes)!=61: die('structure node universe drift')
required=[s for s in (seg.get('source_segments') or []) if s.get('required') is True and s.get('disposition')=='CLASSIFIED']
if len(required)!=52 or any(len(s.get('target_artifact_uids') or [])!=1 for s in required): die('required classification mapping drift')
lineage={x.get('source_uid'):x for x in ctx.get('source_lineage_refs') or []}
gaps=dep.get('unresolved_authority_gaps') or []
if len(gaps)!=8 or len({g.get('gap_uid') for g in gaps})!=8 or len({g.get('authority_ref') for g in gaps})!=8: die('external Authority gap universe drift')
if any(g.get('disposition')!='UNRESOLVED_AUTHORITY_GAP' for g in gaps): die('false Authority resolution')
gap_by_source={}
for g in gaps:
    for suid in g.get('consumer_source_uids') or []: gap_by_source.setdefault(suid,[]).append(g)
expected_sf={}
for fn in ('SOURCE_CONTEXT_MANIFEST.yaml','CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml','SOURCE_DEPENDENCY_MAP.yaml'):
    d=load(intake/fn); expected_sf[d.get('artifact_uid')]=d.get('content_hash')
arts={}
for p in sorted(classroot.rglob('*.yaml')):
    d=load(p); uid=d.get('artifact_uid'); rel=p.relative_to(run).as_posix()
    if not uid or uid in arts: die('duplicate/missing artifact uid:'+str(uid))
    if d.get('artifact_type')!='CANONICAL_CLASSIFICATION_ARTIFACT' or d.get('status')!='CURRENT_CLASSIFICATION': die('classification identity/status mismatch:'+uid)
    if d.get('target_path')!=rel or d.get('artifact_hash')!=artifact_hash(d) or d.get('content_hash')!=content_hash(d): die('classification path/hash mismatch:'+uid)
    if d.get('authority_resolution_performed') is not False or d.get('ai_autofill_used') is not False or d.get('inference_used') is not False: die('synthetic Authority resolution:'+uid)
    arts[uid]=d
if len(arts)!=52: die('physical classification artifact count not 52')
seen=set(); owners={}
for s in required:
    node=nodes.get(s.get('source_node_uid')); uid=(s.get('target_artifact_uids') or [None])[0]; a=arts.get(uid)
    if not node or not a: die('segment target missing:'+str(uid))
    r=resp(node['source_ref']); folder='VISUAL' if s['planning_domain']=='VISUAL_CONSTRUCTION' else 'PAGE'
    if a.get('page_uid')!=s.get('page_uid') or a.get('planning_domain')!=s.get('planning_domain') or a.get('responsibility_uid')!=r or a.get('responsibilities')!=[r]: die('classification scope mismatch:'+uid)
    if a.get('canonical_owner_uid')!='OWNER-'+s['page_uid']+'-'+r or a.get('target_path')!=f"01_CLASSIFIED/{s['page_uid']}/{folder}/{r}.yaml": die('owner/path mismatch:'+uid)
    lin=a.get('source_lineage') or []
    if len(lin)!=1 or lin[0].get('source_uid')!=s.get('source_uid') or lin[0].get('source_node_uid')!=s.get('source_node_uid') or lin[0].get('source_segment_uids')!=[s['segment_uid']]: die('lineage mismatch:'+uid)
    if lin[0].get('raw_source_git_blob_sha')!=lineage.get(s['source_uid'],{}).get('source_git_blob_sha'): die('raw source blob binding mismatch:'+uid)
    if {x.get('artifact_uid'):x.get('content_hash') for x in (a.get('source_fact_refs') or [])}!=expected_sf: die('source fact binding drift:'+uid)
    expected={g['gap_uid'] for g in gap_by_source.get(s['source_uid'],[])}
    if set(a.get('unresolved_external_authority_gap_uids') or [])!=expected: die('Authority carry-forward drift:'+uid)
    key=(a['page_uid'],r)
    if key in owners and owners[key]!=a['canonical_owner_uid']: die('duplicate canonical owner:'+str(key))
    owners[key]=a['canonical_owner_uid']; seen.add(s['segment_uid'])
if seen!={s['segment_uid'] for s in required}: die('required segment coverage drift')
ev=load(intake/'evidence/RESPONSIBILITY_CLASSIFICATION_EVIDENCE.yaml'); sm=ev.get('classification_summary') or {}; ep=ev.get('external_authority_preservation') or {}
if ev.get('status') not in {'MATERIALIZED_PENDING_CI','VERIFIED_CI_PASS'} or (sm.get('required_segments'),sm.get('physical_classification_artifacts'),sm.get('page_construction_artifacts'),sm.get('visual_construction_artifacts'))!=(52,52,48,4): die('classification evidence drift')
if ep.get('source_gap_count')!=8 or ep.get('identity_drift')!=0 or ep.get('resolution_performed') is not False: die('classification Authority evidence drift')
print('PASS: v2.1.8 successor-aware RESPONSIBILITY_CLASSIFICATION integrity 52/52; PAGE=48; VISUAL=4')
print('PASS: legal Page/Visual/Binding successor presence does not retroactively invalidate closed Classification; phase order is owned by Phase Boundary Gate')
