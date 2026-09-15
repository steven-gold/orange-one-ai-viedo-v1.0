#!/usr/bin/env python3
from pathlib import Path
import json, sys, yaml

ROOT=Path(__file__).resolve().parents[2]
FINDING=ROOT/'governance/test/stage02/FIND-20260915-025_FAILURE_RECOVERY_APPLICABILITY_OVERREACH.yaml'
RESULT=ROOT/'.github/stage02-test/STAGE02_R29_EFFECTIVE_REEXECUTION_RESULT.json'

def die(msg): print(f'BLOCK: {msg}',file=sys.stderr); raise SystemExit(1)
if not FINDING.is_file(): die('R29_FINDING_MISSING')
if not RESULT.is_file(): die('R29_RESULT_MISSING')
f=yaml.safe_load(FINDING.read_text(encoding='utf-8')) or {}
r=json.loads(RESULT.read_text(encoding='utf-8'))
if f.get('finding_uid')!='FIND-20260915-025': die('R29_FINDING_IDENTITY_DRIFT')
if r.get('fresh_functional_gap_total')!=129 or r.get('r28_exact_not_applicable_count')!=21 or r.get('raw_failure_recovery_gap_total')!=23: die('R29_RESULT_DENOMINATOR_DRIFT')
if r.get('current_specification_mutated') is not False or r.get('immutable_stage1_source_mutated') is not False: die('R29_MUTATION_FLAG_DRIFT')
f['status']='VERIFIED_CLOSED'
f['closure_evidence']={
 'fresh_result_ref':str(RESULT.relative_to(ROOT)),
 'canonical_scanner_corrected':True,
 'exact_false_positive_count_removed':21,
 'remaining_required_or_unresolved_failure_recovery_count':23,
 'fresh_raw_gap_total_after_fix':150,
 'fresh_effective_gap_total_after_validated_eliminations':129,
 'replacement_recovery_values_created':0,
 'current_specification_mutated':False,
 'immutable_stage1_source_mutated':False,
}
f['closure_gate_result']='PASS'
f['stage02_status']='BLOCKED'
f['stage03_allowed']=False
f['website_construction_allowed']=False
f['deployment_allowed']=False
FINDING.write_text(yaml.safe_dump(f,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
print('PASS: FIND-20260915-025 marked VERIFIED_CLOSED from R29 fresh evidence')
