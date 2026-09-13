#!/usr/bin/env python3
from pathlib import Path
import yaml,subprocess
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
  g=source_map.get(x.get('gap_uid'));
  if not g: die(page+' unknown Authority gap')
  if tup(x)!=tup(g): die(page+' Authority canonical tuple drift:'+str(x.get('gap_uid')))
  if any(x.get(k) is True for k in ('resolved','satisfied','auto_filled','inferred')): die(page+' false Authority resolution')
state=load(run/'EXECUTION_STATE.yaml')
if state.get('governance_candidate_overlay')!='v2.1.11' or state.get('state')!='BLUEPRINT_BINDING_COMPLETED': die('v211 current state drift')
if state.get('stage1_validation_started') is True or state.get('website_construction_started') is True or state.get('deployment_started') is True: die('later phase started early')
receipts=state.get('terminal_receipts') or {}
required={'visual_closure':('e653fbcf39a18775790c6403439b076c9ed3f534',34739267938,'8/8'),'v210_governance':('91f4271b5145f5646be07da32b5624fad7528034',34741356025,'9/9'),'blueprint_binding':('d10253d154eacabed3df967ce4aa83c71a7475f3',34741952438,'10/10')}
for name,(head,runid,denom) in required.items():
 r=receipts.get(name) or {}
 for f in RECEIPT:
  if r.get(f) in (None,''): die('canonical receipt field missing:'+name+':'+f)
 if r.get('provider')!='GITHUB_ACTIONS' or r.get('repository_or_project')!='steven-gold/orange-one-ai-viedo-v1.0' or r.get('head_sha')!=head or r.get('run_id')!=runid or r.get('job_denominator')!=denom or r.get('conclusion')!='SUCCESS': die('canonical receipt value drift:'+name)
ledger_paths=['RUN_MANIFEST.yaml','ARTIFACT_PLAN.yaml','../../GOVERNANCE_CURRENT.yaml','../../REBUILD_BRANCH_BASELINE.yaml','../../11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml','../../11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml']
for rel in ledger_paths:
 p=(run/rel).resolve(); d=load(p); text=yaml.safe_dump(d,sort_keys=False)
 for name,ref in receipts.items():
  if str(ref['run_id']) not in text or ref['head_sha'] not in text: die(str(rel)+' receipt identity missing:'+name)
 for f in RECEIPT:
  if f+':' not in text: die(str(rel)+' canonical receipt field absent:'+f)
 if 'jobs:' in text and 'job_denominator:' not in text: die(str(rel)+' jobs alias substituted for canonical denominator')
 if 'result:' in text and 'conclusion:' not in text: die(str(rel)+' result alias substituted for canonical conclusion')
print('PASS: v2.1.11 exact unresolved Authority tuples preserved against SOURCE_DEPENDENCY_MAP for CORE/ASSET Binding')
print('PASS: canonical six-field terminal receipts projected across Current ledgers; Binding receipt exact 34741952438@d10253d; Stage1/site/deploy not started')
