#!/usr/bin/env python3
from pathlib import Path
import subprocess,sys,yaml
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'; intake=run/'00_SOURCE_INTAKE'; evdir=intake/'evidence'
def die(m): raise SystemExit(m)
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def runv(p):
 r=subprocess.run([sys.executable,p],text=True,capture_output=True)
 if r.returncode!=0:
  print(r.stdout); print(r.stderr,file=sys.stderr); die('predecessor validator failed:'+p)
for p in ['governance/ci/validate_current_v218_classification.py','governance/ci/validate_current_v218_page_base_blueprint.py','governance/ci/validate_current_v210_blueprint_binding.py','governance/ci/validate_current_v211_binding_authority_receipt_schema.py','governance/ci/validate_current_v211_closure_continuity_binding_successor.py']:
 runv(p)
se=load(evdir/'SOURCE_ENUMERATION_EVIDENCE.yaml'); ss=load(intake/'SOURCE_STRUCTURE_MANIFEST.yaml'); ref=load(evdir/'SEMANTIC_GRANULARITY_REFINEMENT_EVIDENCE.yaml'); cf=load(evdir/'CONFLICT_DECISION_EVIDENCE.yaml'); ce=load(evdir/'RESPONSIBILITY_CLASSIFICATION_EVIDENCE.yaml'); dep=load(intake/'SOURCE_DEPENDENCY_MAP.yaml'); st=load(evdir/'STAGE1_VALIDATION_EVIDENCE.yaml'); state=load(run/'EXECUTION_STATE.yaml')
if se.get('artifact_type')!='SOURCE_ENUMERATION_EVIDENCE' or se.get('status')!='MATERIALIZED_FROM_VERIFIED_PREDECESSOR_PROOFS': die('Source Enumeration evidence missing/invalid')
if ss.get('observed_node_count')!=61 or (ss.get('completion') or {}).get('mixed_terminal_units')!=0 or (ss.get('completion') or {}).get('unresolved_container_units')!=0: die('Source Structure closure drift')
if (ref.get('refinement') or {}).get('refined_node_count')!=61 or ref.get('status')!='VERIFIED_CI_PASS': die('semantic refinement evidence drift')
if cf.get('artifact_type')!='CONFLICT_DECISION_EVIDENCE' or cf.get('superseded_current_owner_residual_count')!=0: die('Conflict evidence drift')
cs=ce.get('classification_summary') or {}
if (cs.get('required_segments'),cs.get('physical_classification_artifacts'),cs.get('page_construction_artifacts'),cs.get('visual_construction_artifacts'))!=(52,52,48,4): die('Classification denominator drift')
if any(cs.get(k)!=0 for k in ('unclassified_required_segments','multi_mapped_required_segments','duplicate_canonical_owner','page_visual_cross_contamination')): die('Classification closure not clean')
# Exact unresolved Authority identity against Source Dependency Map.
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
# Dependency index disposition: Stage-01 has no registered program-artifact instance; do not invent standalone indexes.
idx=st.get('index_disposition') or {}
for k in ('dependency_index','reverse_dependency_index'):
 d=idx.get(k) or {}
 if d.get('disposition')!='NOT_APPLICABLE_NO_REGISTERED_PROGRAM_ARTIFACT_INSTANCE_IN_STAGE01' or d.get('physical_artifact_created') is not False: die(k+' N/A disposition invalid')
for p in run.rglob('*'):
 if p.is_file() and p.name in {'DEPENDENCY_INDEX.yaml','REVERSE_DEPENDENCY_INDEX.yaml'}: die('unregistered dependency index artifact created')
 if p.is_file() and (p.suffix=='.pyc' or '__pycache__' in p.parts): die('bytecode residue in Current run')
# Clean scan and run close evidence.
clean=st.get('clean_scan') or {}; close=st.get('run_close') or {}
for k in ('generated_temp_backup_copy_artifacts','pycache_or_pyc_artifacts','orphan_required_stage1_artifacts','broken_required_stage1_references','superseded_current_owner_residuals'):
 if clean.get(k)!=0: die('clean scan nonzero:'+k)
if close.get('exit_gate')!='ALL_REQUIRED_PAGES_STAGE1_CLOSED' or close.get('target_pages_closed')!=2 or close.get('next_stage_uid')!='STAGE-02' or close.get('stage2_started') is not False: die('Stage-01 run-close evidence invalid')
if not (state.get('stage1_validation_started') is True and state.get('stage1_validation_completed') is True): die('Stage-01 validation state incomplete')
if state.get('state')!='STAGE1_VALIDATION_COMPLETED_PENDING_CI' or state.get('stage1_exit_gate')!='PENDING_EXTERNAL_CI': die('Stage-01 closure state drift')
if state.get('stage2_started') is True or state.get('website_construction_started') is True or state.get('deployment_started') is True: die('later stage started early')
# Canonical v2.1.11 governance receipt must be present identically across Current ledgers.
expected={'provider':'GITHUB_ACTIONS','repository_or_project':'steven-gold/orange-one-ai-viedo-v1.0','head_sha':'74cd16e28e98a918c3f682d3b29ea7e362a19cc5','run_id':34754709362,'job_denominator':'11/11','conclusion':'SUCCESS'}
objs=[load(run/'RUN_MANIFEST.yaml'),load(run/'ARTIFACT_PLAN.yaml'),load(root/'GOVERNANCE_CURRENT.yaml'),load(root/'REBUILD_BRANCH_BASELINE.yaml'),load(root/'11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml'),load(root/'11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml')]
for o in objs:
 trs=o.get('terminal_receipts') or o.get('predecessor_terminal_receipts') or {}
 r=trs.get('v211_governance')
 if r!=expected: die('Current ledger v211 receipt drift')
print('PASS: Stage-01 CLEAN_SCAN and RUN_CLOSE candidate valid; required Source Enumeration/Conflict evidence present; semantic closure zeros satisfied')
print('PASS: 8 unresolved Authority exact tuples preserved; dependency/reverse indexes correctly N/A for Stage-01 program-artifact scope; Page/Visual/Binding predecessor gates remain valid')
print('PASS: Current ledgers project canonical v2.1.11 receipt consistently; Stage-02/site/deploy remain unstarted pending external Stage-01 closure receipt')
