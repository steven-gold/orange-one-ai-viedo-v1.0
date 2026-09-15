#!/usr/bin/env python3
from pathlib import Path
import subprocess, sys, yaml

ROOT=Path(__file__).resolve().parents[2]
R15=ROOT/'governance/test/stage02/STAGE02_POST_ACTION_VALIDATION_DEPENDENCY_TRACE_R15.yaml'
R20=ROOT/'governance/test/stage02/STAGE02_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY_R20.yaml'
R22=ROOT/'governance/test/stage02/STAGE02_POST_ACTION_SIGNAL_ROLE_RECLASSIFICATION_R22.yaml'
LEDGER=ROOT/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/ASSET-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml'
OUT=ROOT/'governance/test/stage02/STAGE02_POST_ACTION_SIGNAL_INVALIDATION_R25.yaml'

def die(msg): print(f'BLOCK: {msg}',file=sys.stderr); raise SystemExit(1)
def load(path):
    if not path.is_file(): die(f'MISSING:{path.relative_to(ROOT)}')
    obj=yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(obj,dict): die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj

r15=load(R15); r20=load(R20); r22=load(R22); ledger=load(LEDGER)
contract=r15.get('trace_contract') or {}
if contract.get('result_or_state_signal_is_validation_contract') is not False: die('R15_SIGNAL_VALIDATION_BOUNDARY_DRIFT')
if contract.get('semantic_validation_inference_allowed') is not False or contract.get('invented_validation_rule_allowed') is not False: die('R15_INFERENCE_BOUNDARY_DRIFT')
den15=r15.get('denominators') or {}
if den15.get('post_action_validation_gaps_traced')!=18 or den15.get('exact_post_action_validation_contract_found')!=0 or den15.get('frozen_result_or_state_signal_only')!=18: die(f'R15_DENOMINATOR_DRIFT:{den15}')
r15idx={x.get('blocker_uid'):x for x in r15.get('records') or []}
if len(r15idx)!=18: die(f'R15_RECORD_COUNT:{len(r15idx)}')

r20_auto=[x for x in r20.get('records') or [] if x.get('category')=='POST_ACTION_VALIDATION_NODE_MISSING' and x.get('authorized_for_auto_completion') is True]
r22_auto=[x for x in r22.get('records') or [] if x.get('category')=='POST_ACTION_VALIDATION_NODE_MISSING' and x.get('authorized_for_auto_completion') is True]
if len(r20_auto)!=15 or len(r22_auto)!=2: die(f'R20_R22_AUTO_DENOMINATOR_DRIFT:{len(r20_auto)}:{len(r22_auto)}')
selected={x.get('blocker_uid'):('R20',x) for x in r20_auto}
for x in r22_auto:
    if x.get('blocker_uid') in selected: die(f'R20_R22_BLOCKER_OVERLAP:{x.get("blocker_uid")}')
    selected[x.get('blocker_uid')]=('R22',x)
if len(selected)!=17: die(f'R25_SELECTED_DENOMINATOR:{len(selected)}')

ledger_entries={x.get('source_blocker_uid'):x for x in ledger.get('remediations') or [] if x.get('source_cycle') in {'R20_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY','R22_POST_ACTION_SIGNAL_ROLE_CORRECTION'}}
if set(ledger_entries)!=set(selected): die(f'R25_LEDGER_SELECTED_SET_DRIFT:ledger={sorted(ledger_entries)} selected={sorted(selected)}')
invalid=[]
for blocker,(cycle,row) in sorted(selected.items()):
    trace=r15idx.get(blocker)
    if not trace: die(f'R15_MATCH_MISSING:{blocker}')
    if trace.get('post_action_validation_contract_evidence') not in ([],None): die(f'R15_EXPLICIT_VALIDATION_EVIDENCE_UNEXPECTED:{blocker}')
    signals=trace.get('result_or_state_signal_evidence') or []
    if not signals: die(f'R15_SIGNAL_EVIDENCE_MISSING:{blocker}')
    current=ledger_entries[blocker]; closure=current.get('materialized_closure') or {}
    if (current.get('defect_signature') or {}).get('category')!='POST_ACTION_VALIDATION_NODE_MISSING': die(f'R25_LEDGER_CATEGORY_DRIFT:{blocker}')
    if cycle=='R20':
        if row.get('closure_type')!='POST_ACTION_VALIDATION_FROM_UNIQUE_FROZEN_SUCCESS_SIGNAL': die(f'R20_CLOSURE_TYPE_DRIFT:{blocker}')
        if closure.get('closure_type')!='POST_ACTION_VALIDATION_FROM_UNIQUE_FROZEN_SUCCESS_SIGNAL': die(f'R20_LEDGER_CLOSURE_DRIFT:{blocker}')
    else:
        if row.get('closure_type')!='POST_ACTION_VALIDATION_FROM_ROLE_CORRECT_UNIQUE_FROZEN_RESULT_SIGNAL': die(f'R22_CLOSURE_TYPE_DRIFT:{blocker}')
        if closure.get('closure_type')!='POST_ACTION_VALIDATION_FROM_ROLE_CORRECT_UNIQUE_FROZEN_RESULT_SIGNAL': die(f'R22_LEDGER_CLOSURE_DRIFT:{blocker}')
    invalid.append({
      'blocker_uid':blocker,'page_uid':'ASSET-01','action_uid':row.get('target_uid'),'source_cycle':cycle,
      'current_ledger_remediation_uid':current.get('remediation_uid'),'materialized_validation_signal':closure.get('validation_signal'),
      'r15_explicit_validation_contract_evidence':[],'r15_result_or_state_signal_evidence':signals,
      'invalidity':'RESULT_OR_STATE_SIGNAL_WAS_PROMOTED_TO_POST_ACTION_VALIDATION_CONTRACT_CONTRARY_TO_R15_AND_FRESH_SCANNER',
      'rollback_required':True,'replacement_validation_contract':None,'semantic_inference_used_for_replacement':False,'product_authority_value_invented':False,
    })

head=subprocess.run(['git','rev-parse','HEAD'],cwd=str(ROOT),text=True,capture_output=True,check=True).stdout.strip()
out={
 'schema_version':1,'artifact_type':'NON_NORMATIVE_STAGE02_POST_ACTION_SIGNAL_INVALIDATION_R25','normative_authority':False,'stage_uid':'STAGE-02','source_head_sha':head,
 'source_r15':str(R15.relative_to(ROOT)),'source_r20':str(R20.relative_to(ROOT)),'source_r22':str(R22.relative_to(ROOT)),'source_current_ledger':str(LEDGER.relative_to(ROOT)),
 'correction_basis':{'r15_exact_validation_trace_controls_validation_semantics':True,'fresh_scanner_requires_explicit_validation_contract':True,'result_or_state_signal_is_validation_contract':False,'rollback_only_no_replacement_value':True,'current_specification_mutation_forbidden':True,'stage1_raw_mutation_forbidden':True},
 'denominators':{'r20_post_action_auto_total':15,'r22_post_action_auto_total':2,'invalid_post_action_materialization_total':17,'current_product_materialization_total_before_rollback':34,'expected_product_materialization_total_after_rollback':17,'blocker_reduction_claimed_before_fresh_reexecution':0},
 'invalidations':invalid,'current_specification_mutated':False,'immutable_stage1_source_mutated':False,'stage02_status':'BLOCKED','stage03_allowed':False,'website_construction_allowed':False,'deployment_allowed':False,
 'next_execution_gate':'ROLLBACK_EXACT_17_INVALID_POST_ACTION_SIGNAL_PROMOTIONS_THEN_FRESH_STAGE02_REEXECUTION'
}
OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(yaml.safe_dump(out,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
print('PASS: R25 identified exactly 17 invalid post-action signal promotions (R20=15 R22=2)')
print('PASS: R15 explicit validation evidence is empty for every selected blocker')
print('PASS: no replacement validation contract invented')
