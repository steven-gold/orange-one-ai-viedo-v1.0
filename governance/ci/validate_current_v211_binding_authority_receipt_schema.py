#!/usr/bin/env python3
from pathlib import Path
import yaml
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'
AUTH=['gap_uid','authority_ref','disposition','authority_evidence_ref']; RECEIPT=['provider','repository_or_project','head_sha','run_id','job_denominator','conclusion']
def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def tup(x): return tuple(x.get(k) for k in AUTH)
source=load(run/'00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml'); gaps=source.get('unresolved_authority_gaps') or []; source_map={g.get('gap_uid'):g for g in gaps}
if len(source_map)!=8: die('source Authority gap universe drift')
expected_by_page={'CORE-01':{'GAP-001','GAP-002','GAP-003','GAP-004','GAP-005','GAP-007','GAP-008'},'ASSET-01':{'GAP-001','GAP-002','GAP-003','GAP-004','GAP-005','GAP-006'}}
for page,want in expected_by_page.items():
 d=load(run/f'03_BLUEPRINT_BINDING/{page}/BLUEPRINT_BINDING_MANIFEST.yaml'); carry=d.get('unresolved_external_authority_refs') or []
 got={x.get('gap_uid') for x in carry}
 if got!=want: die(page+' Authority gap set drift')
 for x in carry:
  g=source_map.get(x.get('gap_uid'))
  if not g: die(page+' unknown Authority gap')
  if tup(x)!=tup(g): die(page+' Authority canonical tuple drift:'+str(x.get('gap_uid')))
  if any(x.get(k) is True for k in ('resolved','satisfied','auto_filled','inferred')): die(page+' false Authority resolution')
state=load(run/'EXECUTION_STATE.yaml')
if not (state.get('blueprint_binding_started') is True and state.get('blueprint_binding_completed') is True and state.get('blueprint_binding_count')==2): die('Binding predecessor completion drift')
# v2.1.12 common invariant: this predecessor validator owns Binding proof, not global Current phase/state.
# A legal successor may be Stage-01 closed, Stage-02 active, or later; phase order is owned by the Phase Boundary Gate.
receipts=state.get('terminal_receipts') or {}
required={'visual_closure':('e653fbcf39a18775790c6403439b076c9ed3f534',34739267938,'8/8'),'v210_governance':('91f4271b5145f5646be07da32b5624fad7528034',34741356025,'9/9'),'blueprint_binding':('d10253d154eacabed3df967ce4aa83c71a7475f3',34741952438,'10/10'),'v211_governance':('74cd16e28e98a918c3f682d3b29ea7e362a19cc5',34754709362,'11/11')}
for name,(head,runid,denom) in required.items():
 r=receipts.get(name) or {}
 for f in RECEIPT:
  if r.get(f) in (None,''): die('canonical receipt field missing:'+name+':'+f)
 if r.get('provider')!='GITHUB_ACTIONS' or r.get('repository_or_project')!='steven-gold/orange-one-ai-viedo-v1.0' or r.get('head_sha')!=head or r.get('run_id')!=runid or r.get('job_denominator')!=denom or r.get('conclusion')!='SUCCESS': die('canonical receipt value drift:'+name)
ledger_paths=['RUN_MANIFEST.yaml','ARTIFACT_PLAN.yaml','../../GOVERNANCE_CURRENT.yaml','../../REBUILD_BRANCH_BASELINE.yaml','../../11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml','../../11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml']
for rel in ledger_paths:
 p=(run/rel).resolve(); d=load(p); text=yaml.safe_dump(d,sort_keys=False)
 for name,(head,runid,denom) in required.items():
  if str(runid) not in text or head not in text: die(str(rel)+' receipt identity missing:'+name)
 for f in RECEIPT:
  if f+':' not in text: die(str(rel)+' canonical receipt field absent:'+f)
 if 'jobs:' in text and 'job_denominator:' not in text: die(str(rel)+' jobs alias substituted for canonical denominator')
 if 'result:' in text and 'conclusion:' not in text: die(str(rel)+' result alias substituted for canonical conclusion')
print('PASS: v2.1.11 Binding predecessor exact Authority tuples and canonical receipts remain intact under legal successor states')
print('PASS: validator is successor-state monotonic; global phase/state ordering is delegated to the Phase Boundary Gate')
