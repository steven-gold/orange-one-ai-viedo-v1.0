#!/usr/bin/env python3
from pathlib import Path
import subprocess, sys, yaml
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'; evdir=run/'00_SOURCE_INTAKE/evidence'
PACKAGE='2d6602b20983a9764c2f1496f36ab20a2f0ebcd73826492c27ba67159f5ef3df'
TRUST='4c013cfc1a91142a8b4ce44830ef467c5c960f56b136a75ff670729a523f71e3'
SEM='512eb9178054d26fce807ae8b7617f06818788e23260b9f104bbb588bd5d0ee9'
STAGE1={'provider':'GITHUB_ACTIONS','repository_or_project':'steven-gold/orange-one-ai-viedo-v1.0','head_sha':'c6a9c2e5b38a189a6517d59345a0738618e8cd28','run_id':34755361339,'job_denominator':'12/12','conclusion':'SUCCESS'}
RECEIPT_FIELDS=('provider','repository_or_project','head_sha','run_id','job_denominator','conclusion')
def die(m): raise SystemExit(m)
def load(p):
 try: d=yaml.safe_load(p.read_text(encoding='utf-8'))
 except Exception as e: die('parse failure:'+str(p)+':'+str(e))
 if not isinstance(d,dict): die('root not mapping:'+str(p))
 return d
def req(d,p,fields):
 for f in fields:
  if d.get(f) in (None,''): die('required field missing:'+str(p)+':'+f)
def runv(path):
 r=subprocess.run([sys.executable,path],text=True,capture_output=True)
 if r.returncode:
  print(r.stdout); print(r.stderr,file=sys.stderr); die('predecessor validator failed:'+path)
# v2.1.12 immutable package authority.
lock=load(root/'governance/current/v2.1.12/FULL_PACKAGE_LOCK.yaml'); cand=load(root/'governance/current/v2.1.12/CANDIDATE_RECORD.yaml'); contract=load(root/'governance/current/v2.1.12/SUCCESSOR_STATE_MONOTONIC_EVIDENCE_PARSE_CONTRACT.yaml')
for d,name in ((lock,'FULL_PACKAGE_LOCK'),(cand,'CANDIDATE_RECORD'),(contract,'V212_CONTRACT')):
 if d.get('version')!='v2.1.12': die(name+' version drift')
for d,name in ((lock,'FULL_PACKAGE_LOCK'),(cand,'CANDIDATE_RECORD')):
 pkg=d.get('source_package_sha256') if name=='FULL_PACKAGE_LOCK' else d.get('package_sha256')
 if pkg!=PACKAGE or d.get('external_trust_root_sha256')!=TRUST or d.get('semantic_authority_content_hash')!=SEM: die(name+' identity drift')
pi=contract.get('package_identity') or {}
if pi.get('package_sha256')!=PACKAGE or pi.get('external_trust_root_sha256')!=TRUST or pi.get('semantic_authority_content_hash')!=SEM: die('v212 contract package identity drift')
if (contract.get('regression') or {}).get('denominator')!='60/60_PASS': die('v212 regression denominator drift')
# Required Evidence must parse and satisfy minimum schema before any closed claim.
se=load(evdir/'SOURCE_ENUMERATION_EVIDENCE.yaml'); req(se,'SOURCE_ENUMERATION_EVIDENCE',('artifact_type','run_uid','stage_uid','status'))
cf=load(evdir/'CONFLICT_DECISION_EVIDENCE.yaml'); req(cf,'CONFLICT_DECISION_EVIDENCE',('artifact_type','run_uid','stage_uid','status','decision'))
st=load(evdir/'STAGE1_VALIDATION_EVIDENCE.yaml'); req(st,'STAGE1_VALIDATION_EVIDENCE',('artifact_type','run_uid','stage_uid','status'))
for item in cf.get('checks') or []:
 req(item,'CONFLICT_DECISION_EVIDENCE.check',('check_uid','result','fact'))
 if item.get('result')!='PASS': die('Conflict evidence non-PASS check:'+str(item.get('check_uid')))
# Predecessor validators must execute successfully on the legal Stage-01 closed successor state.
for p in ('governance/ci/validate_current_v211_binding_authority_receipt_schema.py','governance/ci/validate_current_v211_closure_continuity_binding_successor.py','governance/ci/validate_current_stage1_closure.py','governance/ci/validate_current_v218_phase_authority.py'):
 runv(p)
# Static anti-pinning checks on active predecessor validators.
texts={p:(root/p).read_text(encoding='utf-8') for p in ('governance/ci/validate_current_v211_binding_authority_receipt_schema.py','governance/ci/validate_current_v211_closure_continuity_binding_successor.py','governance/ci/validate_current_stage1_closure.py')}
for p,t in texts.items():
 if "get('state')==" in t or "get('state')!=" in t or 'allowed_states=' in t or "successor_started') is False" in t: die('predecessor state pinning pattern remains:'+p)
phase_text=(root/'governance/ci/validate_current_v218_phase_authority.py').read_text(encoding='utf-8')
if 'stage1_closed=' not in phase_text or "stage2_started') is True and not stage1_closed" not in phase_text: die('Stage-01 phase gate missing closure-qualified successor logic')
# Current ledgers must carry exact Stage-01 terminal receipt and preserve v2.1.12 pointer without same-commit self-write.
state=load(run/'EXECUTION_STATE.yaml')
if state.get('stage1_validation_completed') is not True or state.get('stage1_exit_gate')!='SUCCESS_EXTERNAL_CI': die('Stage-01 closed state not materialized')
if (state.get('terminal_receipts') or {}).get('stage1_closure')!=STAGE1: die('Execution state Stage-01 receipt drift')
ledgers=[run/'RUN_MANIFEST.yaml',run/'ARTIFACT_PLAN.yaml',root/'GOVERNANCE_CURRENT.yaml',root/'REBUILD_BRANCH_BASELINE.yaml',root/'11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml',root/'11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml']
for p in ledgers:
 d=load(p); trs=d.get('terminal_receipts') or d.get('predecessor_terminal_receipts') or {}
 if trs.get('stage1_closure')!=STAGE1: die(str(p)+' Stage-01 receipt drift')
 text=yaml.safe_dump(d,sort_keys=False)
 for f in RECEIPT_FIELDS:
  if f+':' not in text: die(str(p)+' canonical receipt field missing:'+f)
# Current v2.1.12 pointer is required now; future successors may supersede it without invalidating this predecessor package.
current=load(root/'GOVERNANCE_CURRENT.yaml'); na=current.get('normative_authority') or {}
if na.get('version')=='v2.1.12':
 if na.get('package_sha256')!=PACKAGE or na.get('external_trust_root_sha256')!=TRUST or na.get('semantic_authority_content_hash')!=SEM: die('Current v2.1.12 pointer identity drift')
print('PASS: v2.1.12 package identity, 60/60 regression contract, and required-evidence parse/schema integrity are exact')
print('PASS: active predecessor validators are successor-state monotonic; Stage-01 12/12 receipt is synchronized across Current ledgers')
print('PASS: phase ordering remains fail-closed at the Phase Boundary Gate without retroactive predecessor invalidation')
