#!/usr/bin/env python3
from pathlib import Path
import hashlib,yaml
root=Path('.')
PKG='3dcc0b4b94250b7487ec923fde2604f13b6d4ce3ee1ec4636feba27bcf3c92c6'
TRUST='70b19fa78f641fb570c9c314552d518b50a358ce18075de0e5cad89edd746de2'
OLD_STRUCT='fdb397f92a89273a107c69fdabd0b5ed5ae2e48d'
OLD_SEG='58b53c18b0fd6b4223afc1703155ab03470945d4'
def die(x): raise SystemExit(x)
def gblob(p):
 b=p.read_bytes(); return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
cur=yaml.safe_load((root/'GOVERNANCE_CURRENT.yaml').read_text())
base=yaml.safe_load((root/'REBUILD_BRANCH_BASELINE.yaml').read_text())
lock=yaml.safe_load((root/'11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml').read_text())
sealed=yaml.safe_load((root/'11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml').read_text())
if cur['normative_authority']['version']!='v2.1.6' or cur['normative_authority']['package_sha256']!=PKG or cur['normative_authority']['external_trust_root_sha256']!=TRUST: die('current v216 authority mismatch')
if base['governance_test']['version']!='v2.1.6' or lock['current_test_authority']['version']!='v2.1.6' or sealed['sealed_governance']['version']!='v2.1.6': die('v216 pointer mismatch')
if (root/'governance/test-runtime/v2.1.5').exists(): die('v2.1.5 runtime remains current')
if (root/'00_SOURCE_INTAKE/fresh_run_002').exists(): die('fresh_run_002 remains current')
run=root/'00_SOURCE_INTAKE/fresh_run_003'
if not run.is_dir(): die('fresh_run_003 missing')
state=yaml.safe_load((run/'EXECUTION_STATE.yaml').read_text())
if state.get('state')!='SOURCE_SEGMENT_MAPPING_COMPLETED': die('state not segment-mapping completed')
if state.get('semantic_granularity_replay_validated') is not True or state.get('replay_mixed_terminal_units_detected')!=2: die('replay block proof missing')
refs=yaml.safe_load((run/'00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml').read_text())
cap=yaml.safe_load((run/'00_SOURCE_INTAKE/RAW_SOURCE_CAPTURE_STATE.yaml').read_text())
if cap.get('state')!='CAPTURE_CLOSED' or cap.get('recapture_allowed') is not False: die('raw capture not closed')
expected=[]; byuid={}
for rec in refs.get('records') or []:
 p=run/rec['target_path']; got=gblob(p)
 if got!=rec['source_git_blob_sha'] or got!=rec['target_git_blob_sha']: die('raw blob mismatch: '+rec['source_uid'])
 expected.append(rec['target_path']); byuid[rec['source_uid']]=rec
actual=sorted(p.relative_to(run).as_posix() for p in (run/'00_SOURCE_INTAKE/RAW_SOURCE').rglob('*') if p.is_file())
if sorted(expected)!=actual: die('raw source purity mismatch')
replay=yaml.safe_load((run/'00_SOURCE_INTAKE/evidence/SEMANTIC_GRANULARITY_REPLAY_EVIDENCE.yaml').read_text())
if replay['result']['expected_block_observed'] is not True or replay['result']['mixed_terminal_units_detected']!=2: die('replay evidence mismatch')
struct_p=run/'00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml'; seg_p=run/'00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml'
if gblob(struct_p)==OLD_STRUCT or gblob(seg_p)==OLD_SEG: die('old v2.1.5 corrected artifact bytes were reused')
struct=yaml.safe_load(struct_p.read_text()); seg=yaml.safe_load(seg_p.read_text())
if struct.get('governance_version')!='v2.1.6' or struct.get('observed_node_count')!=61: die('refined structure count/version mismatch')
if struct.get('syntax_level_is_not_governance_granularity') is not True: die('semantic granularity invariant missing')
all_nodes=[]; req=ref=0
for s in struct.get('sources') or []:
 raw=yaml.safe_load((run/byuid[s['source_uid']]['target_path']).read_text())
 expected_refs=[]
 for k,v in raw.items():
  if k=='registries' and isinstance(v,dict) and 'visuals' in v and len(v)>1:
   expected_refs += ['$.registries.'+ck for ck in v.keys()]
  else: expected_refs.append('$.'+k)
 declared=[n['source_ref'] for n in s.get('observed_nodes') or []]
 if declared!=expected_refs: die('semantic refinement mismatch: '+s['source_uid'])
 for n in s.get('observed_nodes') or []:
  if n.get('terminality_state')!='TERMINAL_HOMOGENEOUS' or n.get('semantic_responsibility_count')!=1 or n.get('unresolved_child_responsibility_count')!=0: die('non-homogeneous terminal: '+n.get('source_node_uid','?'))
  if n.get('classification_state')!='UNCLASSIFIED_OBSERVED_SOURCE': die('classification contamination')
  all_nodes.append(n['source_node_uid']); req += n.get('governance_relevance')=='REQUIRED'; ref += n.get('governance_relevance')=='REFERENCE_ONLY'
if len(all_nodes)!=61 or len(set(all_nodes))!=61 or req!=52 or ref!=9: die('61/52/9 structure totals mismatch')
comp=struct.get('completion') or {}
if comp.get('mixed_terminal_units')!=0 or comp.get('unresolved_container_units')!=0: die('mixed/unresolved units remain')
segments=seg.get('source_segments') or []
if len(segments)!=61: die('segment count not 61')
node_refs=[x['source_node_uid'] for x in segments]
if set(node_refs)!=set(all_nodes) or len(node_refs)!=len(set(node_refs)): die('segment coverage/duplicate mismatch')
page=sum(x.get('planning_domain')=='PAGE_CONSTRUCTION' for x in segments); visual=sum(x.get('planning_domain')=='VISUAL_CONSTRUCTION' for x in segments)
required=sum(bool(x.get('required')) for x in segments); reference=sum(not bool(x.get('required')) for x in segments)
if (required,reference,page,visual)!=(52,9,52,9): die('segment totals mismatch')
sc=seg.get('completion') or {}
for k in ('required_nodes_unmapped','duplicate_node_mappings','unknown_source_nodes','physical_classification_artifacts','mixed_terminal_units','unresolved_container_units'):
 if sc.get(k)!=0: die('segment completion defect '+k)
if state.get('source_fact_materialization_started') or state.get('blueprint_materialization_started') or state.get('website_construction_started') or state.get('deployment_started'): die('downstream phase started early')
print('PASS: v2.1.6 replay blocked 34-node mixed terminals, then refined 61/61 with mixed=0 unresolved=0')
print('PASS: SOURCE_SEGMENT_MAPPING 61/61; required=52; reference_only=9; PAGE=52; VISUAL=9; old_v215_bytes_reused=false')
