#!/usr/bin/env python3
from pathlib import Path
import yaml
root=Path('.')
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def die(m): raise SystemExit(m)
rec=load(root/'governance/current/v2.1.8/CANDIDATE_RECORD.yaml')
con=load(root/'governance/current/v2.1.8/STAGE1_SUCCESSOR_EVIDENCE_SYNC_CONTRACT.yaml')
cur=load(root/'GOVERNANCE_CURRENT.yaml')
base=load(root/'REBUILD_BRANCH_BASELINE.yaml')
lock=load(root/'11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml')
seal=load(root/'11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml')
if rec.get('version')!='v2.1.8' or rec.get('status') not in {'PREFORMAL_VERIFIED_GITHUB_CI_PENDING','PREFORMAL_VERIFIED_GITHUB_CI_PASS'}: die('candidate identity/status mismatch')
exp={'preformal':'15/15_PASS','mandatory_matrix':'10/10_PASS','high_pressure':'25/25_PASS','reference_semantic':'28/28_PASS','reference_fuzz':'46/46_BLOCKED_0_ESCAPED','execution_load':'14/14_PASS','multidirection_stress':'21/21_PASS','stage1_minimal':'33/33_PASS','cross_lifecycle':'30/30_PASS','v217_phase_authority':'25/25_PASS','v218_successor_evidence_sync':'24/24_PASS'}
if rec.get('local_verification')!=exp: die('local verification denominator/result drift')
sha='a108845fbde176cbd20a5f9df4217c68b6512686dedc00ffc8c44e9cc2b04753'; trust='b5c5b5776d1f0f733b1c3572f3233bde7cee3c85253aacd12a522b68a55292ac'; sem='e21c1b8cd1c2b04436fc77b5f9ac99320127bbf5535d63925731bc4e7d260da1'
if (rec.get('package_sha256'),rec.get('external_trust_root_sha256'),rec.get('semantic_authority_content_hash'))!=(sha,trust,sem): die('candidate immutable hash drift')
chain=[(x.get('predecessor'),x.get('successor'),x.get('required_gate')) for x in con.get('phase_gate_chain') or []]
expected=[('SOURCE_FACT_MATERIALIZATION','RESPONSIBILITY_CLASSIFICATION','SOURCE_FACT_GATE_PASS'),('RESPONSIBILITY_CLASSIFICATION','PAGE_BASE_BLUEPRINT','CLASSIFICATION_GATE_PASS'),('PAGE_BASE_BLUEPRINT','VISUAL_BASE_BLUEPRINT','PAGE_BASE_BLUEPRINT_GATE_PASS'),('VISUAL_BASE_BLUEPRINT','BLUEPRINT_BINDING','PAGE_AND_VISUAL_BLUEPRINT_GATES_PASS')]
if chain!=expected: die('phase gate chain drift')
pol=con.get('predecessor_validator_successor_policy') or {}; ev=con.get('current_test_evidence_sync') or {}
if (pol.get('legal_successor_presence'),pol.get('retroactive_predecessor_invalidation'),pol.get('projection_wrapper_as_primary_acceptance_gate'))!=('ALLOW','FORBIDDEN','FORBIDDEN'): die('successor policy drift')
if ev.get('required') is not True or ev.get('historical_pass_substitution')!='BLOCK' or ev.get('denominator_drift')!='BLOCK' or ev.get('human_approval_substitution')!='FORBIDDEN': die('Current Evidence sync policy drift')
if rec.get('status')=='PREFORMAL_VERIFIED_GITHUB_CI_PASS':
    gh=rec.get('github_verification') or {}
    if not isinstance(gh.get('run_id'),int) or gh.get('jobs')!='6/6_SUCCESS' or gh.get('conclusion')!='SUCCESS': die('GitHub closure evidence missing/drift')
    if rec.get('human_formal_review')!='PENDING' or rec.get('formal_test_executed') is not False or rec.get('formal_freeze_claimed') is not False: die('human/formal status drift')
    na=cur.get('normative_authority') or {}; ce=cur.get('current_execution') or {}; cs=cur.get('current_test_evidence_sync') or {}
    if na.get('version')!='v2.1.8' or (na.get('package_sha256'),na.get('external_trust_root_sha256'),na.get('semantic_authority_content_hash'))!=(sha,trust,sem): die('GOVERNANCE_CURRENT authority pointer drift')
    if ce.get('state')!='PAGE_BASE_BLUEPRINT_COMPLETED' or ce.get('unresolved_authority_gap_count')!=8 or ce.get('responsibility_classification_completed') is not True or ce.get('page_base_blueprint_completed') is not True or ce.get('visual_base_blueprint_started') is not False: die('GOVERNANCE_CURRENT execution checkpoint drift')
    if cs.get('status')!='PASS' or cs.get('human_formal_review')!='PENDING': die('GOVERNANCE_CURRENT evidence/review drift')
    gt=base.get('governance_test') or {}; wp=base.get('workspace_progress') or {}; bsync=base.get('current_test_evidence_sync') or {}
    if gt.get('version')!='v2.1.8' or (gt.get('package_sha256'),gt.get('external_trust_root_sha256'),gt.get('semantic_authority_content_hash'))!=(sha,trust,sem): die('REBUILD_BRANCH_BASELINE authority drift')
    if wp.get('responsibility_classification')!='52/52' or wp.get('page_base_blueprint')!='2/2' or wp.get('unresolved_authority_gap_count')!=8 or wp.get('visual_base_blueprint_started') is not False: die('REBUILD_BRANCH_BASELINE progress drift')
    if bsync.get('status')!='PASS' or bsync.get('human_formal_review')!='PENDING': die('REBUILD_BRANCH_BASELINE evidence drift')
    la=lock.get('current_test_authority') or {}; lx=lock.get('current_execution') or {}; ls=lock.get('current_test_evidence_sync') or {}
    if la.get('version')!='v2.1.8' or (la.get('package_sha256'),la.get('external_trust_root_sha256'),la.get('semantic_authority_content_hash'))!=(sha,trust,sem): die('GOVERNANCE_STAGE_LOCK authority drift')
    if lx.get('unresolved_authority_gap_count')!=8 or lx.get('responsibility_classification_completed') is not True or lx.get('page_base_blueprint_completed') is not True or lx.get('visual_base_blueprint_started') is not False: die('GOVERNANCE_STAGE_LOCK checkpoint drift')
    if ls.get('machine_review')!='PASS' or ls.get('human_formal_review')!='PENDING': die('GOVERNANCE_STAGE_LOCK evidence drift')
    sg=seal.get('sealed_governance') or {}; vx=seal.get('verified_test_summary') or {}; ex=seal.get('execution_checkpoint') or {}
    if sg.get('version')!='v2.1.8' or (sg.get('package_sha256'),sg.get('external_trust_root_sha256'),sg.get('semantic_authority_content_hash'))!=(sha,trust,sem): die('SEALED baseline authority drift')
    if vx.get('preformal')!='15/15_PASS' or vx.get('mandatory_matrix')!='10/10_PASS' or vx.get('v218_successor_evidence_sync')!='24/24_PASS': die('SEALED baseline denominator drift')
    if ex.get('state')!='PAGE_BASE_BLUEPRINT_COMPLETED' or ex.get('classification')!='52/52' or ex.get('page_base_blueprint')!='2/2' or ex.get('unresolved_authority_gaps')!=8: die('SEALED baseline checkpoint drift')
    if seal.get('human_formal_review')!='PENDING': die('SEALED baseline human review drift')
print('PASS: v2.1.8 candidate + phase/evidence contract are consistent')
print('PASS: Current pointers, stage lock and sealed test baseline are synchronized to v2.1.8; human formal review remains PENDING')
