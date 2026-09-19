#!/usr/bin/env python3
from copy import deepcopy
from pathlib import Path
import ast
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'governance/ci'))
import stage_execution_engine as eng
entry,reg,gov,profile,adapters=eng.data()
eng.validate_definition_data(profile,adapters)
cases=0
def block(label,mutator):
    global cases
    p=deepcopy(profile); a=deepcopy(adapters); mutator(p,a)
    try: eng.validate_definition_data(p,a)
    except eng.StageEngineError:
        cases+=1; return
    raise SystemExit('FAIL_EXPECTED_BLOCK:'+label)
block('missing_adapter',lambda p,a:a['stages'].pop(next(iter(a['stages']))))
block('missing_phase',lambda p,a:a['common_execution_skeleton']['phases'].pop())
block('phase_count_drift',lambda p,a:a['common_execution_skeleton'].__setitem__('phase_count',25))
block('input_origin_missing',lambda p,a:p['stages'][0]['input_origins'].pop(p['stages'][0]['inputs'][0]))
block('output_producer_unknown',lambda p,a:p['stages'][0]['output_producers'].__setitem__(p['stages'][0]['outputs'][0],'NOT_A_REGISTERED_OPERATION'))
block('scanner_dimensions_missing',lambda p,a:a['stages'][p['stages'][0]['stage_uid']].__setitem__('scanner_dimensions',[]))
block('definition_credit_leak',lambda p,a:a['stages'][p['stages'][0]['stage_uid']].__setitem__('product_completion_credit_from_definition_audit',1))
block('canonical_preflight_missing',lambda p,a:p['stages'][0]['canonical_execution_optimization_gate']['preflight_manifest_set'].pop())
block('partial_stage_exit_allowed',lambda p,a:p['stages'][0].__setitem__('partial_work_unit_closure_may_grant_stage_exit',True))
block('successor_gate_mismatch',lambda p,a:p['stages'][1].__setitem__('entry_gate','WRONG_PREDECESSOR_GATE'))
block('missing_phase_contract',lambda p,a:a['common_execution_skeleton']['phase_contracts'].pop('CURRENT_SCOPE'))
block('phase_contract_artifact_missing',lambda p,a:a['common_execution_skeleton']['phase_contracts']['CURRENT_SCOPE'].__setitem__('required_artifact',''))
block('execution_trace_requirement_missing',lambda p,a:a['common_requirements'].__setitem__('phase_trace_exact_order_required',False))

stage_uid='STAGE-01'
st=eng.stage_map(profile)[stage_uid]
ad=adapters['stages'][stage_uid]
head='1'*40
phase_trace=[]
for ph in eng.EXPECTED_PHASES:
    if ph in {'OWNER_REMEDIATION','FRESH_REEXECUTION'}:
        phase_trace.append({'phase_uid':ph,'status':'NOT_APPLICABLE_WITH_PROOF','proof':'ZERO_DISCOVERED_GAPS'})
    else:
        phase_trace.append({'phase_uid':ph,'status':'PASS'})
sample={
 'artifact_type':'NORMALIZED_STAGE_EXECUTION_EVIDENCE','governance_uid':gov,'stage_uid':stage_uid,'attempt_uid':'SYNTHETIC-NEGATIVE-TEST',
 'scope_manifest_ref':'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml','actual_stage_execution_started':True,'actual_stage_execution_completed':True,
 'fresh_execution':True,'prior_results_used':False,'current_specification_mutated':False,'source_head_sha':head,
 'denominator':{'required_total':len(st['operations']),'open_gap_total':0,'closure_blocker_total':0,'remaining_scope_total':0},
 'gaps':[],'closure_blockers':[],'phase_trace':phase_trace,
 'operation_results':[{'operation_uid':x,'status':'PASS'} for x in st['operations']],
 'output_results':[{'output_uid':x,'producer_operation_uid':st['output_producers'][x],'status':'PASS'} for x in st['outputs']],
 'scanner_results':[{'scanner_dimension':x,'status':'PASS'} for x in ad['scanner_dimensions']],
 'validator_results':[{'validator_uid':x,'status':'PASS'} for x in st['validators']],
 'remediation':{'discovered_gap_total':0,'remediated_gap_total':0,'unresolved_gap_total':0,'reexecution_required':False,'reexecution_performed':False},
 'hidden_defect_sweep':{'performed':True,'result':'PASS','discovered_defect_total':0},
 'required_evidence':[{'evidence_type':x,'status':'PASS','ref':'synthetic://external','external_receipt':True} for x in st['required_evidence']],
 'exact_head_gate_receipts':[{'gate_uid':'SYNTHETIC-GATE','head_sha':head,'run_id':'1','conclusion':'success'}],
 'resume_persistence':{'performed':True,'resume_point':'SYNTHETIC_NEXT'},
 'next_stage_transition':{'next_stage_uid':st['next_stage_uid'],'status':'READY'},
 'result':'PASS','stage_exit_allowed':True
}
eng.validate_evidence_data(stage_uid,deepcopy(sample))
def block_evidence(label,mutator):
    global cases
    x=deepcopy(sample); mutator(x)
    try: eng.validate_evidence_data(stage_uid,x)
    except eng.StageEngineError:
        cases+=1; return
    raise SystemExit('FAIL_EXPECTED_EVIDENCE_BLOCK:'+label)
block_evidence('phase_order_drift',lambda x:x['phase_trace'].__setitem__(0,{'phase_uid':'CURRENT_GOVERNANCE','status':'PASS'}))
block_evidence('operation_coverage_drift',lambda x:x['operation_results'].pop())
block_evidence('scanner_coverage_drift',lambda x:x['scanner_results'].pop())
block_evidence('remediation_without_reexecution',lambda x:x.__setitem__('remediation',{'discovered_gap_total':1,'remediated_gap_total':1,'unresolved_gap_total':0,'reexecution_required':True,'reexecution_performed':False}))
block_evidence('hidden_defect_on_pass',lambda x:x.__setitem__('hidden_defect_sweep',{'performed':True,'result':'PASS','discovered_defect_total':1}))
block_evidence('next_stage_drift',lambda x:x['next_stage_transition'].__setitem__('next_stage_uid','WRONG-STAGE'))
wrapper=(ROOT/'governance/ci/compile_stage_execution_preflight.py').read_text(encoding='utf-8')
assert 'compatibility_main' in wrapper
assert 'UNSUPPORTED_STAGE_UNTIL_MATCHING_CURRENT_EVIDENCE_EXISTS' not in wrapper
common=(ROOT/'governance/ci/stage_execution_engine.py').read_text(encoding='utf-8')
tree=ast.parse(common)
for node in ast.walk(tree):
    if isinstance(node,(ast.Assign,ast.AnnAssign)):
        targets=node.targets if isinstance(node,ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target,ast.Name) and target.id=='STAGE':
                value=node.value
                if isinstance(value,ast.Constant) and value.value=='STAGE-02':
                    raise AssertionError('COMMON_ENGINE_STAGE02_LITERAL_ASSIGNMENT')
for node in ast.walk(tree):
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='fail':
        for arg in node.args:
            if isinstance(arg,ast.Constant) and isinstance(arg.value,str) and arg.value.startswith('UNSUPPORTED_STAGE_UNTIL_MATCHING_CURRENT_EVIDENCE_EXISTS'):
                raise AssertionError('COMMON_ENGINE_STAGE02_ONLY_REJECTION')
print(f'PASS: common Stage Execution Engine negative regression {cases}/19')
print('PASS: Stage-02 entrypoint is compatibility-only; common engine has no Stage-02-only execution rejection')
