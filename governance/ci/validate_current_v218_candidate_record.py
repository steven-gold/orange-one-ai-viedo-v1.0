#!/usr/bin/env python3
from pathlib import Path
import yaml
root=Path('.'); rec=yaml.safe_load((root/'governance/current/v2.1.8/CANDIDATE_RECORD.yaml').read_text()); con=yaml.safe_load((root/'governance/current/v2.1.8/STAGE1_SUCCESSOR_EVIDENCE_SYNC_CONTRACT.yaml').read_text())
def die(m): raise SystemExit(m)
if rec.get('version')!='v2.1.8' or rec.get('status') not in {'PREFORMAL_VERIFIED_GITHUB_CI_PENDING','PREFORMAL_VERIFIED_GITHUB_CI_PASS'}: die('candidate identity/status mismatch')
if rec.get('status')=='PREFORMAL_VERIFIED_GITHUB_CI_PASS':
    gh=rec.get('github_verification') or {}
    if not isinstance(gh.get('run_id'), int) or gh.get('jobs')!='6/6_SUCCESS' or gh.get('conclusion')!='SUCCESS': die('GitHub closure evidence missing/drift')
exp={'preformal':'15/15_PASS','mandatory_matrix':'10/10_PASS','high_pressure':'25/25_PASS','reference_semantic':'28/28_PASS','reference_fuzz':'46/46_BLOCKED_0_ESCAPED','execution_load':'14/14_PASS','multidirection_stress':'21/21_PASS','stage1_minimal':'33/33_PASS','cross_lifecycle':'30/30_PASS','v217_phase_authority':'25/25_PASS','v218_successor_evidence_sync':'24/24_PASS'}
if rec.get('local_verification')!=exp: die('local verification denominator/result drift')
if rec.get('package_sha256')!='a108845fbde176cbd20a5f9df4217c68b6512686dedc00ffc8c44e9cc2b04753': die('package SHA drift')
if rec.get('external_trust_root_sha256')!='b5c5b5776d1f0f733b1c3572f3233bde7cee3c85253aacd12a522b68a55292ac': die('trust root SHA drift')
if rec.get('semantic_authority_content_hash')!='e21c1b8cd1c2b04436fc77b5f9ac99320127bbf5535d63925731bc4e7d260da1': die('semantic authority anchor drift')
chain=con.get('phase_gate_chain') or []
expected=[('SOURCE_FACT_MATERIALIZATION','RESPONSIBILITY_CLASSIFICATION','SOURCE_FACT_GATE_PASS'),('RESPONSIBILITY_CLASSIFICATION','PAGE_BASE_BLUEPRINT','CLASSIFICATION_GATE_PASS'),('PAGE_BASE_BLUEPRINT','VISUAL_BASE_BLUEPRINT','PAGE_BASE_BLUEPRINT_GATE_PASS'),('VISUAL_BASE_BLUEPRINT','BLUEPRINT_BINDING','PAGE_AND_VISUAL_BLUEPRINT_GATES_PASS')]
actual=[(x.get('predecessor'),x.get('successor'),x.get('required_gate')) for x in chain]
if actual!=expected: die('phase gate chain drift')
pol=con.get('predecessor_validator_successor_policy') or {}
if pol.get('legal_successor_presence')!='ALLOW' or pol.get('retroactive_predecessor_invalidation')!='FORBIDDEN' or pol.get('projection_wrapper_as_primary_acceptance_gate')!='FORBIDDEN': die('successor-aware validator policy drift')
ev=con.get('current_test_evidence_sync') or {}
if ev.get('required') is not True or ev.get('historical_pass_substitution')!='BLOCK' or ev.get('denominator_drift')!='BLOCK' or ev.get('human_approval_substitution')!='FORBIDDEN': die('Current Evidence sync policy drift')
print('PASS: v2.1.8 candidate record matches local 15/15 + 10/10 verified package and immutable hashes')
print('PASS: successor-aware phase chain and Current Evidence synchronization contract are active')
