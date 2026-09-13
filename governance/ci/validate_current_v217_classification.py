#!/usr/bin/env python3
from pathlib import Path
import hashlib,re,yaml
root=Path('.')
run=root/'00_SOURCE_INTAKE/fresh_run_003'
intake=run/'00_SOURCE_INTAKE'
classroot=run/'01_CLASSIFIED'
def die(msg): raise SystemExit(msg)
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def stable_hash(o): return hashlib.sha256(yaml.safe_dump(o,allow_unicode=True,sort_keys=True).encode()).hexdigest()
def content_hash(d):
    x=dict(d); x.pop('content_hash',None); return stable_hash(x)
def artifact_hash(d):
    x=dict(d); x.pop('content_hash',None); x.pop('artifact_hash',None); return stable_hash(x)
def resp_from_ref(ref):
    x=ref[2:] if str(ref).startswith('$.') else str(ref)
    return re.sub(r'[^A-Za-z0-9]+','_',x).strip('_').upper()
state=load(run/'EXECUTION_STATE.yaml')
if state.get('state') not in {'RESPONSIBILITY_CLASSIFICATION_ACTIVE','RESPONSIBILITY_CLASSIFICATION_COMPLETED_PENDING_CI','RESPONSIBILITY_CLASSIFICATION_COMPLETED'}: die('classification execution state mismatch')
if state.get('source_fact_materialization_completed') is not True: die('source facts not closed before classification')
if state.get('responsibility_classification_started') is not True or state.get('responsibility_classification_completed') is not True: die('classification flags incomplete')
for key in ('blueprint_materialization_started','website_construction_started','deployment_started'):
    if state.get(key) is True: die('downstream phase started early: '+key)
for rel in ('02_BASE_BLUEPRINT','03_BLUEPRINT_BINDING'):
    if (run/rel).exists(): die('blueprint artifact directory exists before classification CI close: '+rel)
struct=load(intake/'SOURCE_STRUCTURE_MANIFEST.yaml')
seg=load(intake/'SOURCE_SEGMENT_MAP.yaml')
dep=load(intake/'SOURCE_DEPENDENCY_MAP.yaml')
ctx=load(intake/'SOURCE_CONTEXT_MANIFEST.yaml')
if struct.get('observed_node_count')!=61: die('structure count drift')
nodes={}
source_page={}
for s in struct.get('sources') or []:
    source_page[s['source_uid']]=s['page_uid']
    for n in s.get('observed_nodes') or []:
        nodes[n['source_node_uid']]={'source_uid':s['source_uid'],'page_uid':s['page_uid'],'source_ref':n['source_ref'],'governance_relevance':n['governance_relevance']}
if len(nodes)!=61: die('structure node universe drift')
segments=seg.get('source_segments') or []
required=[s for s in segments if s.get('required') is True and s.get('disposition')=='CLASSIFIED']
if len(required)!=52: die('required classified segment count drift: '+str(len(required)))
if any(len(s.get('target_artifact_uids') or [])!=1 for s in required): die('required segment target cardinality not one')
lineage={x.get('source_uid'):x for x in ctx.get('source_lineage_refs') or []}
if not lineage: die('source lineage refs missing')
gaps=dep.get('unresolved_authority_gaps') or []
if len(gaps)!=8 or len({g.get('gap_uid') for g in gaps})!=8: die('unresolved authority gap set drift')
if any(g.get('disposition')!='UNRESOLVED_AUTHORITY_GAP' for g in gaps): die('false authority resolution in source facts')
gap_by_source={}
for g in gaps:
    for suid in g.get('consumer_source_uids') or []:
        gap_by_source.setdefault(suid,[]).append(g)
expected_sf={}
for fn in ('SOURCE_CONTEXT_MANIFEST.yaml','CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml','SOURCE_DEPENDENCY_MAP.yaml'):
    d=load(intake/fn)
    expected_sf[d.get('artifact_uid')]=d.get('content_hash')
arts={}
paths={}
for p in sorted(classroot.rglob('*.yaml')) if classroot.exists() else []:
    d=load(p)
    uid=d.get('artifact_uid')
    if not uid or uid in arts: die('duplicate/missing artifact uid: '+str(uid))
    if d.get('artifact_type')!='CANONICAL_CLASSIFICATION_ARTIFACT' or d.get('status')!='CURRENT_CLASSIFICATION': die('classification identity/status mismatch: '+str(uid))
    rel=p.relative_to(run).as_posix()
    if d.get('target_path')!=rel: die('target path mismatch: '+str(uid))
    if d.get('artifact_hash')!=artifact_hash(d): die('artifact hash mismatch: '+str(uid))
    if d.get('content_hash')!=content_hash(d): die('content hash mismatch: '+str(uid))
    if d.get('authority_resolution_performed') is not False or d.get('ai_autofill_used') is not False or d.get('inference_used') is not False: die('synthetic resolution marker: '+str(uid))
    arts[uid]=d; paths[uid]=rel
if len(arts)!=52: die('physical classification artifact count not 52: '+str(len(arts)))
owners={}
seen_segments={}
for s in required:
    node=nodes.get(s.get('source_node_uid'))
    if not node: die('segment node missing: '+s['segment_uid'])
    uid=(s.get('target_artifact_uids') or [None])[0]
    a=arts.get(uid)
    if not a: die('segment target not physical: '+str(uid))
    if a.get('page_uid')!=s.get('page_uid') or a.get('planning_domain')!=s.get('planning_domain'): die('page/domain mismatch: '+uid)
    resp=resp_from_ref(node['source_ref'])
    if a.get('responsibility_uid')!=resp or a.get('responsibility_class')!=resp or a.get('responsibilities')!=[resp]: die('responsibility identity mismatch: '+uid)
    expected_owner='OWNER-'+s['page_uid']+'-'+resp
    if a.get('canonical_owner_uid')!=expected_owner: die('canonical owner mismatch: '+uid)
    folder='VISUAL' if s['planning_domain']=='VISUAL_CONSTRUCTION' else 'PAGE'
    expected_path=f"01_CLASSIFIED/{s['page_uid']}/{folder}/{resp}.yaml"
    if a.get('target_path')!=expected_path: die('canonical classification path mismatch: '+uid)
    expected_scopes={'lifecycle_uid':'LC-'+s['page_uid']+'-'+resp,'approval_scope_uid':'AP-'+s['page_uid']+'-'+resp,'version_scope_uid':'VER-'+s['page_uid']+'-'+resp,'test_scope_uid':'TEST-'+s['page_uid']+'-'+resp}
    for k,v in expected_scopes.items():
        if a.get(k)!=v: die(k+' mismatch: '+uid)
    lin=a.get('source_lineage') or []
    if len(lin)!=1: die('source lineage cardinality mismatch: '+uid)
    l=lin[0]
    if l.get('source_uid')!=s.get('source_uid') or l.get('source_node_uid')!=s.get('source_node_uid') or l.get('source_ref')!=node['source_ref'] or l.get('source_segment_uids')!=[s['segment_uid']]: die('source lineage mismatch: '+uid)
    if l.get('raw_source_git_blob_sha')!=lineage.get(s['source_uid'],{}).get('source_git_blob_sha'): die('raw source blob binding mismatch: '+uid)
    b=a.get('source_truth_binding') or {}
    if b.get('binding_mode')!='EXACT_REFERENCE_BOUND_NO_INFERENCE' or b.get('payload_mutation_allowed') is not False: die('source truth binding policy mismatch: '+uid)
    if b.get('source_uid')!=s['source_uid'] or b.get('source_node_uid')!=s['source_node_uid'] or b.get('source_ref')!=node['source_ref']: die('source truth binding identity mismatch: '+uid)
    sf={x.get('artifact_uid'):x.get('content_hash') for x in (a.get('source_fact_refs') or [])}
    if sf!=expected_sf: die('source fact binding incomplete/stale: '+uid)
    expected_gap_uids={g['gap_uid'] for g in gap_by_source.get(s['source_uid'],[])}
    actual_gap_uids=set(a.get('unresolved_external_authority_gap_uids') or [])
    if actual_gap_uids!=expected_gap_uids: die('unresolved authority carry-forward mismatch: '+uid)
    if a.get('unresolved_authority_source_fact_hash')!=expected_sf.get('FRESH-RUN-003-SOURCE-DEPENDENCY-MAP-V216'): die('unresolved authority source-fact hash mismatch: '+uid)
    key=(a['page_uid'],a['responsibility_uid'])
    if key in owners and owners[key]!=a['canonical_owner_uid']: die('duplicate canonical owner: '+str(key))
    owners[key]=a['canonical_owner_uid']
    seen_segments[s['segment_uid']]=seen_segments.get(s['segment_uid'],0)+1
if set(seen_segments)!=set(s['segment_uid'] for s in required) or any(v!=1 for v in seen_segments.values()): die('required segment coverage/multiplicity defect')
ev=load(intake/'evidence/RESPONSIBILITY_CLASSIFICATION_EVIDENCE.yaml')
sm=ev.get('classification_summary') or {}
if ev.get('status') not in {'MATERIALIZED_PENDING_CI','VERIFIED_CI_PASS'}: die('classification evidence status invalid')
if sm.get('required_segments')!=52 or sm.get('physical_classification_artifacts')!=52 or sm.get('page_construction_artifacts')!=48 or sm.get('visual_construction_artifacts')!=4: die('classification evidence counts mismatch')
ep=ev.get('external_authority_preservation') or {}
if ep.get('source_gap_count')!=8 or ep.get('identity_drift')!=0 or ep.get('resolution_performed') is not False: die('classification evidence authority preservation mismatch')
if state.get('classification_artifact_count')!=52 or state.get('classification_page_artifact_count')!=48 or state.get('classification_visual_artifact_count')!=4: die('execution state classification counts mismatch')
print('PASS: RESPONSIBILITY_CLASSIFICATION 52/52 physical; PAGE=48; VISUAL=4; required segment coverage exact; canonical owner uniqueness clean')
print('PASS: unresolved external Authority refs preserved by consumer source with 8 source gaps; no AI autofill/inference/false resolution; Blueprint/website/deployment remain unstarted')
