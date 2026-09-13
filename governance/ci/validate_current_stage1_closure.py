#!/usr/bin/env python3
from pathlib import Path
import subprocess,sys,yaml
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'; intake=run/'00_SOURCE_INTAKE'; evdir=intake/'evidence'
def die(m): raise SystemExit(m)
def load(p):
 try:
  data=yaml.safe_load(p.read_text(encoding='utf-8'))
 except Exception as e: die('required evidence parse failure:'+str(p)+':'+str(e))
 if not isinstance(data,dict): die('required evidence root not mapping:'+str(p))
 return data
def require_fields(d,p,fields):
 for f in fields:
  if d.get(f) in (None,''): die('required evidence field missing:'+str(p)+':'+f)
def runv(p):
 r=subprocess.run([sys.executable,p],text=True,capture_output=True)
 if r.returncode!=0:
  print(r.stdout); print(r.stderr,file=sys.stderr); die('predecessor validator failed:'+p)
for p in ['governance/ci/validate_current_v218_classification.py','governance/ci/validate_current_v218_page_base_blueprint.py','governance/ci/validate_current_v210_blueprint_binding.py','governance/ci/validate_current_v211_binding_authority_receipt_schema.py','governance/ci/validate_current_v211_closure_continuity_binding_successor.py']:
 runv(p)
se=load(evdir/'SOURCE_ENUMERATION_EVIDENCE.yaml'); require_fields(se,'SOURCE_ENUMERATION_EVIDENCE',['artifact_type','run_uid','stage_uid','status'])
ss=load(intake/'SOURCE_STRUCTURE_MANIFEST.yaml'); ref=load(evdir/'SEMANTIC_GRANULARITY_REFINEMENT_EVIDENCE.yaml')
cf=load(evdir/'CONFLICT_DECISION_EVIDENCE.yaml'); require_fields(cf,'CONFLICT_DECISION_EVIDENCE',['artifact_type','run_uid','stage_uid','status','decision'])
ce=load(evdir/'RESPONSIBILITY_CLASSIFICATION_EVIDENCE.yaml'); dep=load(intake/'SOURCE_DEPENDENCY_MAP.yaml')
st=load(evdir/'STAGE1_VALIDATION_EVIDENCE.yaml'); require_fields(st,'STAGE1_VALIDATION_EVIDENCE',['artifact_type','run_uid','stage_uid','status'])
state=load(run/'EXECUTION_STATE.yaml')
if se.get('artifact_type')!='SOURCE_ENUMERATION_EVIDENCE' or se.get('status')!='MATERIALIZED_FROM_VERIFIED_PREDECESSOR_PROOFS': die('Source Enumeration evidence invalid')
if ss.get('observed_node_count')!=61 or (ss.get('completion') or {}).get('mixed_terminal_units')!=0 or (ss.get('completion') or {}).get('unresolved_container_units')!=0: die('Source Structure closure drift')
if (ref.get('refinement') or {}).get('refined_node_count')!=61 or ref.get('status')!='VERIFIED_CI_PASS': die('semantic refinement evidence drift')
if cf.get('artifact_type')!='CONFLICT_DECISION_EVIDENCE' or cf.get('superseded_current_owner_residual_count')!=0: die('Conflict evidence drift')
for item in cf.get('checks') or []:
 require_fields(item,'CONFLICT_DECISION_EVIDENCE.check',['check_uid','result','fact'])
 if item.get('result')!='PASS': die('Conflict evidence check not PASS:'+str(item.get('check_uid')))
cs=ce.get('classification_summary') or {}
if (cs.get('required_segments'),cs.get('physical_classification_artifacts'),cs.get('page_construction_artifacts'),cs.get('visual_construction_artifacts'))!=(52,52,48,4): die('Classification denominator drift')
if any(cs.get(k)!=0 for k in ('unclassified_required_segments','multi_mapped_required_segments','duplicate_canonical_owner','page_visual_cross_contamination')): die('Classification closure not clean')
fields=('gap_uid','authority_ref','disposition','authority_evidence_ref')
source={tuple(g.get(k) for k in fields) for g in dep.get('unresolved_authority_gaps') or []}
if len(source)!=8: die('Source Authority tuple universe != 8')
union=set()
for page in ('CORE-01','ASSET-01'):
 b=load(run/f'03_BLUEPRINT_BINDING/{page}/BLUEPRINT_BINDING_MANIFEST.yaml')
 tuples={tuple(g.get(k) for k in fields) for g in b.get('unresolved_external_authority_refs') or []}
 if not tuples.issubset(source): die(page+' Authority tuple drift')
 union |= tuples
if union!=source: die('Binding Authority tuple union drift')
idx=st.get('index_disposition') or {}
for k in ('dependency_index','reverse_dependency_index'):
 d=idx.get(k) or {}
 if d.get('disposition')!='NOT_APPLICABLE_NO_REGISTERED_PROGRAM_ARTIFACT_INSTANCE_IN_STAGE01' or d.get('physical_artifact_created') is not False: die(k+' N/A disposition invalid')
for p in run.rglob('*'):
 if p.is_file() and p.name in {'DEPENDENCY_INDEX.yaml','REVERSE_DEPENDENCY_INDEX.yaml'}: die('unregistered dependency index artifact created')
 if p.is_file() and (p.suffix=='.pyc' or '__pycache__' in p.parts): die('bytecode residue in Current run')
clean=st.get('clean_scan') or {}; close=st.get('run_close') or {}
for k in ('generated_temp_backup_copy_artifacts','pycache_or_pyc_artifacts','orphan_required_stage1_artifacts','broken_required_stage1_references','superseded_current_owner_residuals'):
 if clean.get(k)!=0: die('clean scan nonzero:'+k)
if close.get('exit_gate')!='ALL_REQUIRED_PAGES_STAGE1_CLOSED' or close.get('target_pages_closed')!=2 or close.get('next_stage_uid')!='STAGE-02': die('Stage-01 run-close evidence invalid')
if not (state.get('stage1_validation_started') is True and state.get('stage1_validation_completed') is True): die('Stage-01 predecessor completion drift')
# v2.1.12 common invariant: a Stage-01 predecessor validator may not require global Current state to remain at its terminal label.
expected_v211={'provider':'GITHUB_ACTIONS','repository_or_project':'steven-gold/orange-one-ai-viedo-v1.0','head_sha':'74cd16e28e98a918c3f682d3b29ea7e362a19cc5','run_id':34754709362,'job_denominator':'11/11','conclusion':'SUCCESS'}
expected_stage1={'provider':'GITHUB_ACTIONS','repository_or_project':'steven-gold/orange-one-ai-viedo-v1.0','head_sha':'c6a9c2e5b38a189a6517d59345a0738618e8cd28','run_id':34755361339,'job_denominator':'12/12','conclusion':'SUCCESS'}
objs=[state,load(run/'RUN_MANIFEST.yaml'),load(run/'ARTIFACT_PLAN.yaml'),load(root/'GOVERNANCE_CURRENT.yaml'),load(root/'REBUILD_BRANCH_BASELINE.yaml'),load(root/'11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml'),load(root/'11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml')]
for o in objs:
 trs=o.get('terminal_receipts') or o.get('predecessor_terminal_receipts') or {}
 if trs.get('v211_governance')!=expected_v211: die('Current ledger v211 receipt drift')
 if trs.get('stage1_closure')!=expected_stage1: die('Current ledger Stage1 closure receipt drift')
print('PASS: Stage-01 CLEAN_SCAN/RUN_CLOSE predecessor remains valid; Required Evidence exact bytes parse and satisfy required fields')
print('PASS: 8 unresolved Authority exact tuples preserved; Stage-01 external 12/12 receipt is canonical and synchronized')
print('PASS: validator is successor-state monotonic; legal Stage-02/later Current state cannot retroactively invalidate Stage-01 closure')
