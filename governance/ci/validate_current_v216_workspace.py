#!/usr/bin/env python3
from pathlib import Path
import hashlib,yaml
root=Path('.')
PKG='3dcc0b4b94250b7487ec923fde2604f13b6d4ce3ee1ec4636feba27bcf3c92c6'
TRUST='70b19fa78f641fb570c9c314552d518b50a358ce18075de0e5cad89edd746de2'
def die(x): raise SystemExit(x)
def gblob(p):
 b=p.read_bytes(); return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
cur=yaml.safe_load((root/'GOVERNANCE_CURRENT.yaml').read_text()); base=yaml.safe_load((root/'REBUILD_BRANCH_BASELINE.yaml').read_text()); lock=yaml.safe_load((root/'11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml').read_text()); sealed=yaml.safe_load((root/'11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml').read_text())
if cur['normative_authority']['version']!='v2.1.6' or cur['normative_authority']['package_sha256']!=PKG or cur['normative_authority']['external_trust_root_sha256']!=TRUST: die('current v216 authority mismatch')
if base['governance_test']['version']!='v2.1.6' or lock['current_test_authority']['version']!='v2.1.6' or sealed['sealed_governance']['version']!='v2.1.6': die('v216 pointer mismatch')
if (root/'governance/test-runtime/v2.1.5').exists(): die('v2.1.5 runtime remains current')
if (root/'00_SOURCE_INTAKE/fresh_run_002').exists(): die('fresh_run_002 remains current')
run=root/'00_SOURCE_INTAKE/fresh_run_003'
if not run.is_dir(): die('fresh_run_003 missing')
if any(p.name!='fresh_run_003' for p in (root/'00_SOURCE_INTAKE').iterdir()): die('unexpected intake sibling')
state=yaml.safe_load((run/'EXECUTION_STATE.yaml').read_text()); rm=yaml.safe_load((run/'RUN_MANIFEST.yaml').read_text())
if state.get('state')!='SOURCE_STRUCTURE_ENUMERATION_REPLAY_READY': die('replay state mismatch')
if state.get('source_segment_mapping_started') is not False: die('segment mapping started before v216 replay gate')
if rm.get('governance',{}).get('version')!='v2.1.6': die('run governance not v216')
refs=yaml.safe_load((run/'00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml').read_text()); cap=yaml.safe_load((run/'00_SOURCE_INTAKE/RAW_SOURCE_CAPTURE_STATE.yaml').read_text())
if cap.get('state')!='CAPTURE_CLOSED' or cap.get('recapture_allowed') is not False: die('raw capture not closed')
expected=[]
for rec in refs.get('records') or []:
 p=run/rec['target_path']; got=gblob(p)
 if got!=rec['source_git_blob_sha'] or got!=rec['target_git_blob_sha']: die('raw blob mismatch: '+rec['source_uid'])
 expected.append(rec['target_path'])
rawroot=run/'00_SOURCE_INTAKE/RAW_SOURCE'; actual=sorted(p.relative_to(run).as_posix() for p in rawroot.rglob('*') if p.is_file())
if sorted(expected)!=actual: die('raw source directory purity mismatch')
struct=yaml.safe_load((run/'00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml').read_text())
if struct.get('observed_node_count')!=34 or struct.get('segment_mapping_started') is not False: die('previous-stage 34-node replay not restored')
if (run/'00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml').exists(): die('old source segment map was reused')
# Verify exact old syntactic enumeration, then detect mixed terminal containers from live raw bytes.
mixed=[]; total=0
byuid={r['source_uid']:r for r in refs['records']}
for s in struct.get('sources') or []:
 rec=byuid[s['source_uid']]; raw=yaml.safe_load((run/rec['target_path']).read_text())
 keys=list(raw.keys()); declared=[n['source_top_level_key'] for n in s.get('observed_nodes') or []]
 if keys!=declared: die('replay is not exact previous top-level enumeration: '+s['source_uid'])
 total+=len(declared)
 for n in s.get('observed_nodes') or []:
  k=n['source_top_level_key']; val=raw.get(k)
  if k=='registries' and isinstance(val,dict) and 'visuals' in val and len(val)>1:
   mixed.append((s['source_uid'],n['source_node_uid'],sorted(val.keys())))
if total!=34: die('replay node total not 34')
if len(mixed)!=2: die('v216 replay did not expose exactly two known mixed registries terminals: '+repr(mixed))
print('PASS: v2.1.6 correctly BLOCKED previous 34-node replay; mixed_terminal_units=2; segment_mapping_not_started=true')
for x in mixed: print('BLOCKED_MIXED_TERMINAL:',x[0],x[1],','.join(x[2]))
