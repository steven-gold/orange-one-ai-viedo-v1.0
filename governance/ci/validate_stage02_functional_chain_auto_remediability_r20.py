#!/usr/bin/env python3
from pathlib import Path
import sys, yaml
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'governance/test/stage02/STAGE02_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY_R20.yaml'
R=ROOT/'governance/test/stage02/STAGE02_FUNCTIONAL_CONTRACT_REMEDIATION_PROBLEM_REGISTER_R19.yaml'
def die(m): print('BLOCK:',m,file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die(f'MAPPING_REQUIRED:{p.relative_to(ROOT)}')
    return o
out=load(P); r19=load(R)
records=out.get('records') or []; probs=r19.get('problems') or []
if len(records)!=150 or len(probs)!=150: die(f'DENOMINATOR:{len(records)}/{len(probs)}')
base={(p.get('blocker_uid'),p.get('scope'),p.get('category'),str(p.get('target_uid'))):p for p in probs}
if len(base)!=150: die('R19_IDENTITY_NOT_UNIQUE')
seen=set(); auto=0; ag=0; unresolved=0
for r in records:
    key=(r.get('blocker_uid'),r.get('page_uid'),r.get('category'),str(r.get('target_uid')))
    if key not in base: die(f'IDENTITY_DRIFT:{key}')
    if key in seen: die(f'DUPLICATE:{key}')
    seen.add(key)
    d=r.get('disposition')
    if d=='AUTO_REMEDIABLE_DETERMINISTIC_MINIMAL_CLOSURE':
        auto+=1
        if r.get('authorized_for_auto_completion') is not True: die(f'AUTO_NOT_AUTHORIZED:{key}')
        if r.get('authority_gap_proven') is not False or r.get('outside_frozen_closure') is not False: die(f'AUTO_BOUNDARY:{key}')
        if r.get('distinct_candidate_value_count')!=1 or r.get('candidate_value') in (None,'',[],{}): die(f'AUTO_NOT_UNIQUE:{key}')
        sc=r.get('function_admission_scorecard') or {}; le=r.get('auto_completion_scope_ledger_entry') or {}
        if sc.get('current_authority_or_deterministic_required_dependency') is not True: die(f'SCORECARD_AUTHORITY:{key}')
        if sc.get('authority_created_by_score') is not False: die(f'SCORE_CREATED_AUTHORITY:{key}')
        for f in ('outside_frozen_registered_dependency_closure','generic_crud_symmetry_expansion_used','sibling_feature_symmetry_expansion_used','semantic_similarity_used','ai_invented_business_value'):
            if le.get(f) is not False: die(f'LEDGER_FORBIDDEN:{key}:{f}')
    elif d=='AUTHORITY_GAP_MULTIPLE_REASONABLE_CLOSURES':
        ag+=1
        if r.get('authorized_for_auto_completion') is not False or r.get('authority_gap_proven') is not True: die(f'AUTHORITY_GAP_FLAGS:{key}')
        if int(r.get('distinct_candidate_value_count') or 0)<2: die(f'AUTHORITY_GAP_NOT_MULTIPLE:{key}')
    elif d=='UNRESOLVED_FUNCTIONAL_CONTRACT_GAP_NO_UNIQUE_CLOSURE':
        unresolved+=1
        if r.get('authorized_for_auto_completion') is not False or r.get('authority_gap_proven') is not False: die(f'UNRESOLVED_FLAGS:{key}')
        if int(r.get('distinct_candidate_value_count') or 0)!=0: die(f'UNRESOLVED_HAS_CANDIDATE:{key}')
    else: die(f'UNKNOWN_DISPOSITION:{key}:{d}')
if seen!=set(base): die('R19_COVERAGE_DRIFT')
den=out.get('denominators') or {}
if den.get('input_problem_total')!=150 or den.get('auto_remediable_total')!=auto or den.get('true_authority_gap_total')!=ag or den.get('unresolved_no_unique_closure_total')!=unresolved: die('SUMMARY_DRIFT')
if den.get('blocker_reduction_claimed')!=0: die('PREMATURE_BLOCKER_REDUCTION')
if out.get('current_specification_mutated') is not False or out.get('stage03_allowed') is not False: die('STAGE_BOUNDARY_VIOLATION')
cc=out.get('classification_contract') or {}
if cc.get('absence_of_materialized_contract_alone_is_authority_gap') is not False or cc.get('full_chain_unique_deterministic_closure_checked_before_block') is not True: die('CLASSIFICATION_CONTRACT_MISSING')
print(f'PASS: R20 exact R19 coverage 150/150; auto={auto}; authority_gap={ag}; unresolved={unresolved}')
print('PASS: no AUTO_REMEDIABLE record lacks one unique frozen-chain candidate')
print('PASS: classification claims zero blocker reduction before materialization')
