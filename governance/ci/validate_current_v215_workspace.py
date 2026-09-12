#!/usr/bin/env python3
from pathlib import Path
import hashlib,yaml
r=Path('.'); rr=r/'00_SOURCE_INTAKE/fresh_run_002'; i=rr/'00_SOURCE_INTAKE'
PKG='2bfeed2ec9bc6eac9f34fdd5eb43e2f76f1e78682c4b81bebb9e4a3e1084eecd'; TRUST='787b2be721c0d51e8fe595ceaeeb0c80a03e692952b6ff2fc139c6a914f089ee'
def die(x): raise SystemExit(x)
def gsha(p):
 b=p.read_bytes();return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def chash(d):
 x=dict(d);x.pop('structure_manifest_hash',None);return hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True).encode()).hexdigest()
def resolve(d,ref):
 if not isinstance(ref,str) or not ref.startswith('$.'): return False
 x=d
 for k in ref[2:].split('.'):
  if not isinstance(x,dict) or k not in x:return False
  x=x[k]
 return True
# sealed authority
c=yaml.safe_load((r/'GOVERNANCE_CURRENT.yaml').read_text());b=yaml.safe_load((r/'REBUILD_BRANCH_BASELINE.yaml').read_text());l=yaml.safe_load((r/'11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml').read_text());s0=yaml.safe_load((r/'11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml').read_text())
if c['normative_authority']['version']!='v2.1.5' or c['normative_authority']['package_sha256']!=PKG or c['normative_authority']['external_trust_root_sha256']!=TRUST or c['normative_authority']['normative_edit_allowed'] is not False:die('sealed current mismatch')
if c['test_runtime']['expected_stage1_minimal_control']!='31/31_PASS' or b['governance_test']['version']!='v2.1.5' or b['prior_extraction_reuse']!='FORBIDDEN' or l['lock_state']!='USER_FROZEN_READ_ONLY' or l['normative_edit_after_lock']!='FORBIDDEN' or s0['sealed_governance']['version']!='v2.1.5' or s0['sealed_governance']['package_sha256']!=PKG or s0['normative_mutation_allowed'] is not False:die('seal/lock mismatch')
if any((r/x).exists() for x in ('app','src','pages','public')):die('premature website implementation')
if not rr.is_dir() or [p.name for p in (r/'00_SOURCE_INTAKE').iterdir() if p.name!='fresh_run_002']:die('fresh run isolation mismatch')
# state
st=yaml.safe_load((rr/'EXECUTION_STATE.yaml').read_text());run=yaml.safe_load((rr/'RUN_MANIFEST.yaml').read_text())
if st.get('state')!='SOURCE_SEGMENT_MAPPING_COMPLETED' or st.get('source_segment_mapping_completed') is not True or st.get('source_fact_materialization_started') is not False or st.get('domain_decomposition_started') is not False:die('execution state mismatch')
if st.get('allowed_transition',{}).get('to')!='SOURCE_FACT_MATERIALIZATION_ACTIVE':die('next transition mismatch')
if run.get('status')!='SOURCE_SEGMENT_MAPPING_COMPLETED' or run.get('governance',{}).get('version')!='v2.1.5' or run.get('governance',{}).get('normative_edit_allowed') is not False:die('run manifest mismatch')
pol=run.get('execution_policy') or {}
if pol.get('source_structure_enumeration')!='COMPLETED_61_OF_61_FULL_SOURCE_PROVEN' or pol.get('source_segment_mapping')!='COMPLETED_61_OF_61_ONE_SEGMENT_PER_NODE' or pol.get('source_fact_materialization')!='NOT_EXECUTED':die('run phase counters mismatch')
# raw capture exact
refs=yaml.safe_load((i/'RAW_SOURCE_REFERENCE_MANIFEST.yaml').read_text());cap=yaml.safe_load((i/'RAW_SOURCE_CAPTURE_STATE.yaml').read_text())
if cap.get('state')!='CAPTURE_CLOSED' or cap.get('next_step')!='SOURCE_STRUCTURE_ENUMERATION' or cap.get('recapture_allowed') is not False:die('raw capture reopened')
rec={x['source_uid']:x for x in refs.get('records') or []}
if len(rec)!=3:die('raw source count mismatch')
expected=[]
for uid,x in rec.items():
 if x.get('source_domain_scope')=='MIXED_PAGE_VISUAL' and x.get('source_role')!='MIXED_PAGE_VISUAL_SOURCE_INPUT':die('biased mixed role:'+uid)
 p=rr/x['target_path']
 if not p.is_file() or gsha(p)!=x.get('source_git_blob_sha') or gsha(p)!=x.get('target_git_blob_sha') or x.get('content_mutated') is not False:die('raw exactness fail:'+uid)
 expected.append(x['target_path'])
actual=sorted(p.relative_to(rr).as_posix() for p in (i/'RAW_SOURCE').rglob('*') if p.is_file())
if sorted(expected)!=actual:die('raw directory purity fail')
# structure, including mixed registries split
smf=yaml.safe_load((i/'SOURCE_STRUCTURE_MANIFEST.yaml').read_text());sources=smf.get('sources') or []
if smf.get('artifact_type')!='SOURCE_STRUCTURE_MANIFEST' or smf.get('observed_node_count')!=61 or smf.get('classification_started') is not False or smf.get('segment_mapping_started') is not True:die('structure header mismatch')
by={x['source_uid']:x for x in sources}
if set(by)!=set(rec) or len(by)!=3:die('structure source set mismatch')
nodes={};reqn=refn=0
for uid,x in by.items():
 raw=yaml.safe_load((rr/rec[uid]['target_path']).read_text())
 refs_expected=[]
 for k,v in raw.items(): refs_expected.extend(['$.registries.'+str(z) for z in v.keys()] if k=='registries' and isinstance(v,dict) else ['$.'+str(k)])
 ns=x.get('observed_nodes') or []
 if [n.get('source_ref') for n in ns]!=refs_expected or x.get('observed_node_count')!=len(ns) or x.get('structure_manifest_hash')!=chash(x):die('structure enumeration mismatch:'+uid)
 if any(n.get('source_ref')=='$.registries' for n in ns):die('mixed registries container unsplit:'+uid)
 for n in ns:
  nid=n.get('source_node_uid')
  if not nid or nid in nodes or not resolve(raw,n.get('source_ref')) or n.get('classification_state')!='UNCLASSIFIED_OBSERVED_SOURCE':die('source node invalid:'+str(nid))
  nodes[nid]=(uid,n); reqn+=n.get('governance_relevance')=='REQUIRED'; refn+=n.get('governance_relevance')=='REFERENCE_ONLY'
if len(nodes)!=61 or reqn!=52 or refn!=9:die(f'structure counts {len(nodes)}/{reqn}/{refn}')
co=smf.get('completion') or {}
if co.get('required_nodes')!=52 or co.get('reference_only_nodes')!=9 or co.get('mixed_container_nodes_remaining')!=0 or co.get('missing_nodes')!=0 or co.get('extra_nodes')!=0:die('structure completion mismatch')
# segment 1:1 map
m=yaml.safe_load((i/'SOURCE_SEGMENT_MAP.yaml').read_text())
if m.get('artifact_type')!='SOURCE_SEGMENT_MAP' or m.get('status')!='CURRENT_SOURCE_SEGMENT_MAPPING' or m.get('source_structure_node_count')!=61 or m.get('classification_started') is not False or m.get('classification_materialized') is not False:die('segment header mismatch')
rm={x['source_uid']:x for x in m.get('raw_sources') or []}
if set(rm)!=set(rec):die('segment raw source set mismatch')
for uid,x in rec.items():
 for k in ('page_uid','source_role','source_domain_scope'):
  if rm[uid].get(k)!=x.get(k):die('segment raw metadata:'+uid+':'+k)
segs=m.get('source_segments') or []
if len(segs)!=61:die('segment count mismatch')
seen=set();counts={};pn=vn=rq=rf=0
for z in segs:
 sid=z.get('segment_uid');nid=z.get('source_node_uid');uid=z.get('source_uid')
 if not sid or sid in seen or nid not in nodes:die('segment identity:'+str(sid))
 seen.add(sid)
 counts[nid]=counts.get(nid,0)+1; exp,n=nodes[nid]
 if uid!=exp or z.get('page_uid')!=rec[uid].get('page_uid'):die('segment lineage:'+sid)
 dom=z.get('planning_domain'); vis=(uid=='SRC-CORE-01-CANONICAL-VISUAL-IDENTITY' or n.get('source_ref') in {'$.layout','$.registries.visuals'})
 if dom not in {'PAGE_CONSTRUCTION','VISUAL_CONSTRUCTION'} or vis!=(dom=='VISUAL_CONSTRUCTION'):die('segment domain:'+sid)
 pn+=dom=='PAGE_CONSTRUCTION';vn+=dom=='VISUAL_CONSTRUCTION';required=n.get('governance_relevance')=='REQUIRED'
 if z.get('required') is not required:die('segment required flag:'+sid)
 targets=z.get('target_artifact_uids') or []
 if required:
  rq+=1
  if z.get('disposition')!='CLASSIFIED' or len(targets)!=1:die('required disposition:'+sid)
 else:
  rf+=1
  if z.get('disposition')!='REFERENCE_ONLY' or targets or not z.get('authority_evidence_ref') or not (rr/z['authority_evidence_ref']).is_file():die('reference disposition:'+sid)
if set(counts)!=set(nodes) or any(v!=1 for v in counts.values()) or (rq,rf,pn,vn)!=(52,9,52,9):die(f'segment coverage {rq}/{rf}/{pn}/{vn}')
mc=m.get('completion') or {}
for k,v in {'segment_count':61,'required_segment_count':52,'reference_only_segment_count':9,'page_construction_segments':52,'visual_construction_segments':9,'required_nodes_unmapped':0,'duplicate_node_mappings':0,'unknown_source_nodes':0,'physical_classification_artifacts':0}.items():
 if mc.get(k)!=v:die('segment completion:'+k)
if mc.get('next_step')!='SOURCE_FACT_MATERIALIZATION':die('segment next step')
if (rr/'01_CLASSIFIED').exists() or any((i/x).exists() for x in ('SOURCE_CONTEXT_MANIFEST.yaml','CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml','SOURCE_DEPENDENCY_MAP.yaml')):die('next phase materialized early')
# garbage
for p in r.rglob('*'):
 if p.is_file() and '.git' not in p.parts and (p.name=='.DS_Store' or p.suffix in {'.pyc','.pyo'} or '__pycache__' in p.parts or p.name.endswith(('.tmp','.bak','~'))):die('garbage:'+str(p))
print('PASS: SOURCE_STRUCTURE_ENUMERATION 61/61; required=52; reference_only=9; mixed_containers=0')
print('PASS: SOURCE_SEGMENT_MAPPING 61/61; required=52; reference_only=9; PAGE=52; VISUAL=9; classification_files=0')
print('PASS: v2.1.5 seal/current/fresh-workspace contract valid')
