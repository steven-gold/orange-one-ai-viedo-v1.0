#!/usr/bin/env python3
from copy import deepcopy
from pathlib import Path
import ast
import importlib.util
import tempfile
import yaml
import json
import subprocess
import sys
import os
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'governance/ci'))
import stage_execution_engine as eng
entry,reg,gov,profile,adapters=eng.data()
eng.validate_definition_data(profile,adapters)
assert eng.validate_current_ledger_synchronization_contract() is True
cases=0
def expect_stage_engine_block(label, fn, expected_prefix=None):
    global cases
    try:
        fn()
    except eng.StageEngineError as exc:
        if expected_prefix and expected_prefix not in str(exc):
            raise SystemExit(f'FAIL_WRONG_BLOCK:{label}:{exc}')
        cases += 1
        return
    raise SystemExit('FAIL_EXPECTED_STAGE_ENGINE_BLOCK:'+label)

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
block('cross_stage_gate_missing',lambda p,a:p['stages'][0].pop('cross_stage_materialization_gate'))
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
 'scope_manifest_ref':'STAGE_EXECUTION/<STAGE_UID>/<WORK_UNIT_UID>/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml','actual_stage_execution_started':True,'actual_stage_execution_completed':True,
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
_orig_product_root=os.environ.get(eng.PRODUCT_ROOT_ENV)
_sample_tmp=tempfile.TemporaryDirectory()
_sample_root=Path(_sample_tmp.name)
os.environ[eng.PRODUCT_ROOT_ENV]=str(_sample_root)
_synthetic_wu='SYNTHETIC-WU-STAGE01'
_synthetic_dir=_sample_root/'STAGE_EXECUTION'/'STAGE-01'/_synthetic_wu
_synthetic_dir.mkdir(parents=True)
_scope_rel=f'STAGE_EXECUTION/STAGE-01/{_synthetic_wu}/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
_matrix_rel=f'STAGE_EXECUTION/STAGE-01/{_synthetic_wu}/NORMATIVE_EXECUTION_MATRIX.yaml'
_handoff_rel=f'STAGE_EXECUTION/STAGE-01/{_synthetic_wu}/CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml'
sample['scope_manifest_ref']=_scope_rel
sample['cross_stage_handoff']={
 'ledger_ref':_handoff_rel,'external_receipt':False,'successor_stage_uid':st['next_stage_uid'],
 'reference_resolution_complete':True,'physical_materialization_complete':True,'required_field_completeness_complete':True,
 'denominator_reconciled':True,'consumer_readiness_complete':True,
 'successor_execution_binding_total':0,'successor_execution_binding_ready_total':0,'successor_execution_binding_unresolved_total':0,
 'current_matrix_valid':True,'current_state_consistent':True,'unresolved_required_dependency_total':0,'status':'PASS'
}
yaml.safe_dump({'artifact_type':'EXECUTION_SCOPE_MANIFEST','stage_uid':stage_uid,'work_unit_uid':_synthetic_wu,'governed_unit_uid':'synthetic:STAGE01','governance_uid':gov},(_synthetic_dir/'CURRENT_EXECUTION_SCOPE_MANIFEST.yaml').open('w',encoding='utf-8'),sort_keys=False)
yaml.safe_dump({
 'artifact_type':'WORK_UNIT','work_unit_uid':_synthetic_wu,'stage_uid':stage_uid,'governed_unit_uid':'synthetic:STAGE01','primary_task_layer':'PRODUCT_STAGE_EXECUTION',
 'status':'CLOSED','current_status':'CLOSED','normative_execution_matrix_ref':_matrix_rel,
 'required_outputs':list(st['outputs']),
 'operation_bindings':{x:{'executor_owner':'synthetic.executor','result_owner':'synthetic.result'} for x in st['operations']},
 'scanner_bindings':{x:{'scanner_owner':'synthetic.scanner','result_owner':'synthetic.scan'} for x in ad['scanner_dimensions']}
},(_synthetic_dir/'WORK_UNIT.yaml').open('w',encoding='utf-8'),sort_keys=False)
yaml.safe_dump({
 'artifact_type':'WORK_UNIT_EXECUTION_STATE','stage_uid':stage_uid,'work_unit_uid':_synthetic_wu,
 'completed_operations':list(st['operations']),'current_operation':'COMPLETE','status':'CLOSED'
},(_synthetic_dir/'EXECUTION_STATE.yaml').open('w',encoding='utf-8'),sort_keys=False)
_required_sections=list(map(str,st.get('required_normative_section_uids') or []))
_required_artifacts=list(map(str,st.get('outputs') or []))+list(map(str,st.get('required_evidence') or []))
_row_total=max(len(_required_sections),len(_required_artifacts))
_synth_payload={'fields':{f'f{i}':f'VALUE-{i}' for i in range(_row_total)}}
yaml.safe_dump(_synth_payload,(_synthetic_dir/'synthetic-artifact.yaml').open('w',encoding='utf-8'),sort_keys=False)
_matrix_rows=[]
for i in range(_row_total):
    _matrix_rows.append({
      'matrix_row_uid':f'S1-MATRIX-ROW-{i+1:03d}','normative_section_uid':_required_sections[i % len(_required_sections)],
      'requirement_uid':f'S1-REQ-{i+1:03d}','required_artifact_type':_required_artifacts[i % len(_required_artifacts)],
      'artifact_ref':f'STAGE_EXECUTION/STAGE-01/{_synthetic_wu}/synthetic-artifact.yaml','artifact_owner':'SYNTHETIC-OWNER',
      'row_denominator_source':'SYNTHETIC-DENOMINATOR','row_identity':f'S1-SYNTHETIC-ROW-{i+1:03d}','field_path':['fields',f'f{i}'],
      'applicability':'REQUIRED','validator_uid':st['validators'][0],'validator_check_id':f'S1-MATRIX-FIELD-{i+1:03d}',
      'evidence_ref':'synthetic://matrix-evidence','closure_gate':st['exit_gate'],'failure_disposition':'BLOCK','reentry_owner':'SYNTHETIC-OWNER'
    })
yaml.safe_dump({
 'artifact_uid':'SYNTHETIC-NEM-STAGE01','artifact_type':'NORMATIVE_EXECUTION_MATRIX','governance_uid':gov,'stage_uid':stage_uid,
 'work_unit_uid':_synthetic_wu,'rows':_matrix_rows,'coverage':{
   'required_normative_section_total':len(_required_sections),'represented_normative_section_total':len(_required_sections),
   'required_artifact_total':len(set(_required_artifacts)),'represented_artifact_total':len(set(_required_artifacts)),
   'required_field_total':_row_total,'validator_bound_field_total':_row_total,'closure_bound_field_total':_row_total,
   'missing_required_row_count':0,'missing_required_field_count':0,'duplicate_credit_count':0,'summary_only_credit_count':0,
   'unclassified_applicability_count':0,'validator_unbound_count':0,'closure_unbound_count':0,'stale_matrix_count':0},
 'status':'PASS'
},(_synthetic_dir/'NORMATIVE_EXECUTION_MATRIX.yaml').open('w',encoding='utf-8'),sort_keys=False)
_successor=eng.stage_map(profile)[st['next_stage_uid']]
yaml.safe_dump({
 'artifact_uid':'SYNTHETIC-HANDOFF-STAGE01','artifact_type':'CROSS_STAGE_HANDOFF_READINESS_LEDGER','stage_uid':stage_uid,
 'work_unit_uid':_synthetic_wu,'successor_stage_uid':st['next_stage_uid'],
 'successor_required_inputs':[{'input_uid':x,'status':'MATERIALIZED'} for x in _successor.get('inputs') or []],
 'successor_execution_bindings':[],
 'successor_execution_binding_total':0,'successor_execution_binding_ready_total':0,'successor_execution_binding_unresolved_total':0,
 'reference_resolution_complete':True,'physical_materialization_complete':True,'required_field_completeness_complete':True,
 'denominator_reconciled':True,'consumer_readiness_complete':True,'current_matrix_valid':True,'current_state_consistent':True,
 'unresolved_required_dependency_total':0,'status':'PASS'
},(_synthetic_dir/'CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml').open('w',encoding='utf-8'),sort_keys=False)
eng.validate_evidence_data(stage_uid,deepcopy(sample))
blocked_sample=deepcopy(sample)
blocked_sample['denominator']={'required_total':len(st['operations']),'open_gap_total':1,'closure_blocker_total':1,'remaining_scope_total':1}
blocked_sample['gaps']=[{'problem_uid':'SYNTHETIC-REVIEW-PENDING'}]
blocked_sample['closure_blockers']=['SYNTHETIC-REVIEW-PENDING']
blocked_sample['remediation']={'discovered_gap_total':1,'remediated_gap_total':0,'unresolved_gap_total':1,'reexecution_required':True,'reexecution_performed':True}
blocked_sample['phase_trace']=[{'phase_uid':ph,'status':('BLOCKED' if ph=='TERMINAL_CLOSURE' else ('NOT_EXECUTED_AFTER_BLOCK' if ph=='NEXT_STAGE' else 'PASS'))} for ph in eng.EXPECTED_PHASES]
blocked_sample['next_stage_transition']={'next_stage_uid':st['next_stage_uid'],'status':'BLOCKED'}
blocked_sample['result']='BLOCKED'
blocked_sample['stage_exit_allowed']=False
eng.validate_evidence_data(stage_uid,blocked_sample)
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
block('driver_contract_missing',lambda p,a:a.pop('execution_driver_contract'))
block('driver_operation_coverage_disabled',lambda p,a:a['execution_driver_contract'].__setitem__('exact_operation_binding_coverage_required',False))
block_evidence('output_producer_result_drift',lambda x:x['output_results'][0].__setitem__('producer_operation_uid','WRONG'))
block_evidence('validator_coverage_drift',lambda x:x['validator_results'].pop())
block_evidence('required_evidence_missing',lambda x:x['required_evidence'].clear())
block_evidence('exact_head_gate_drift',lambda x:x['exact_head_gate_receipts'][0].__setitem__('head_sha','2'*40))
block_evidence('resume_persistence_missing',lambda x:x.__setitem__('resume_persistence',{'performed':False,'resume_point':None}))
block_evidence('pass_nonzero_denominator',lambda x:x['denominator'].__setitem__('remaining_scope_total',1))
def make_blocked_without_phase(x):
    x['result']='BLOCKED'; x['stage_exit_allowed']=False
block_evidence('blocked_without_blocked_phase',make_blocked_without_phase)
block_evidence('handoff_reference_resolution_false',lambda x:x['cross_stage_handoff'].__setitem__('reference_resolution_complete',False))
block_evidence('handoff_physical_materialization_false',lambda x:x['cross_stage_handoff'].__setitem__('physical_materialization_complete',False))
block_evidence('handoff_required_field_completeness_false',lambda x:x['cross_stage_handoff'].__setitem__('required_field_completeness_complete',False))
block_evidence('handoff_denominator_not_reconciled',lambda x:x['cross_stage_handoff'].__setitem__('denominator_reconciled',False))
block_evidence('handoff_consumer_not_ready',lambda x:x['cross_stage_handoff'].__setitem__('consumer_readiness_complete',False))
block_evidence('handoff_unresolved_required_dependency',lambda x:x['cross_stage_handoff'].__setitem__('unresolved_required_dependency_total',1))

# Terminal receipt pressure: missing receipt, wrong exact HEAD, and failed conclusion must never close a PASS stage.
_sample_evidence_path=_synthetic_dir/'SYNTHETIC_NORMALIZED_EVIDENCE.json'
_sample_receipt_path=_synthetic_dir/'SYNTHETIC_TERMINAL_RECEIPT.json'
_sample_evidence_path.write_text(json.dumps(sample,ensure_ascii=False,indent=2),encoding='utf-8')
_current_git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
_valid_receipt={
  'provider':'github-actions',
  'repository_or_project':'synthetic/repository',
  'head_sha':_current_git_head,
  'run_id':'SYNTHETIC-RUN',
  'job_denominator':['synthetic-job'],
  'conclusion':'success',
  'governance_uid':gov,
  'stage_uid':stage_uid,
  'evidence_ref':str(_sample_evidence_path.relative_to(_sample_root))
}
_sample_receipt_path.write_text(json.dumps(_valid_receipt,ensure_ascii=False,indent=2),encoding='utf-8')
eng.validate_terminal(stage_uid,_sample_evidence_path,_sample_receipt_path)
_missing_evidence_ref=deepcopy(_valid_receipt); _missing_evidence_ref.pop('evidence_ref')
_sample_receipt_path.write_text(json.dumps(_missing_evidence_ref,ensure_ascii=False,indent=2),encoding='utf-8')
expect_stage_engine_block(
  'terminal_receipt_evidence_ref_missing',
  lambda:eng.validate_terminal(stage_uid,_sample_evidence_path,_sample_receipt_path),
  'TERMINAL_RECEIPT_FIELD_MISSING:evidence_ref'
)
_wrong_evidence_ref=deepcopy(_valid_receipt); _wrong_evidence_ref['evidence_ref']='STAGE_EXECUTION/STAGE-01/WRONG/EVIDENCE.json'
_sample_receipt_path.write_text(json.dumps(_wrong_evidence_ref,ensure_ascii=False,indent=2),encoding='utf-8')
expect_stage_engine_block(
  'terminal_receipt_evidence_ref_drift',
  lambda:eng.validate_terminal(stage_uid,_sample_evidence_path,_sample_receipt_path),
  'TERMINAL_RECEIPT_EVIDENCE_REF_DRIFT'
)
_sample_receipt_path.write_text(json.dumps(_valid_receipt,ensure_ascii=False,indent=2),encoding='utf-8')
_bad_denominator_evidence=deepcopy(sample)
_bad_denominator_evidence['denominator']['required_total']+=1
_sample_evidence_path.write_text(json.dumps(_bad_denominator_evidence,ensure_ascii=False,indent=2),encoding='utf-8')
expect_stage_engine_block(
  'terminal_closure_denominator_identity_drift',
  lambda:eng.validate_terminal(stage_uid,_sample_evidence_path,_sample_receipt_path),
  'TERMINAL_CLOSURE_DENOMINATOR_IDENTITY_DRIFT'
)
_sample_evidence_path.write_text(json.dumps(sample,ensure_ascii=False,indent=2),encoding='utf-8')
_sample_receipt_path.unlink()
expect_stage_engine_block(
  'terminal_receipt_missing',
  lambda:eng.validate_terminal(stage_uid,_sample_evidence_path,_sample_receipt_path),
  'MISSING_FILE'
)
_wrong_head=deepcopy(_valid_receipt); _wrong_head['head_sha']='0'*40
_sample_receipt_path.write_text(json.dumps(_wrong_head,ensure_ascii=False,indent=2),encoding='utf-8')
expect_stage_engine_block(
  'terminal_receipt_wrong_head',
  lambda:eng.validate_terminal(stage_uid,_sample_evidence_path,_sample_receipt_path),
  'TERMINAL_RECEIPT_HEAD_MISMATCH'
)
_wrong_result=deepcopy(_valid_receipt); _wrong_result['conclusion']='failure'
_sample_receipt_path.write_text(json.dumps(_wrong_result,ensure_ascii=False,indent=2),encoding='utf-8')
expect_stage_engine_block(
  'terminal_receipt_wrong_conclusion',
  lambda:eng.validate_terminal(stage_uid,_sample_evidence_path,_sample_receipt_path),
  'TERMINAL_RECEIPT_IDENTITY_OR_RESULT_DRIFT'
)
if _orig_product_root is None:
    os.environ.pop(eng.PRODUCT_ROOT_ENV,None)
else:
    os.environ[eng.PRODUCT_ROOT_ENV]=_orig_product_root
_sample_tmp.cleanup()
plans=[eng.plan(uid) for uid in eng.stage_map(profile)]
assert len(plans)==11
assert all(len(x['phases'])==26 for x in plans)
assert all([p['phases'][i]['phase_uid'] for i in range(26)]==eng.EXPECTED_PHASES for p in plans)

wstage='STAGE-03'
wst=eng.stage_map(profile)[wstage]
wad=adapters['stages'][wstage]
work={
 'work_unit_uid':'SYNTHETIC-WU','primary_task_layer':'PRODUCT_STAGE_EXECUTION','stage_uid':wstage,'current_status':'ACTIVE_PREEXECUTION',
 'required_outputs':list(wst['outputs']),
 'operation_bindings':{x:{
    'executor_owner':'synthetic.executor',
    'result_owner':'synthetic.results',
    'executor_protocol':'PYTHON_STAGE_OPERATION_V1',
    'operation_receipt_ref':f'STAGE_EXECUTION/{wstage}/SYNTHETIC-WU/EVIDENCE/OPERATION_RECEIPTS/{x}.yaml'
  } for x in wst['operations']},
 'scanner_bindings':{x:{'scanner_owner':'synthetic.scanner','result_owner':'synthetic.scan.results'} for x in wad['scanner_dimensions']},
}
eng.validate_work_unit_bindings(wstage,deepcopy(work),eng.stage_map(profile),adapters)
def block_work(label,mutator):
    global cases
    x=deepcopy(work); mutator(x)
    try: eng.validate_work_unit_bindings(wstage,x,eng.stage_map(profile),adapters)
    except eng.StageEngineError:
        cases+=1; return
    raise SystemExit('FAIL_EXPECTED_WORK_UNIT_BLOCK:'+label)
block_work('missing_operation_binding',lambda x:x['operation_bindings'].pop(next(iter(x['operation_bindings']))))
block_work('missing_scanner_binding',lambda x:x['scanner_bindings'].pop(next(iter(x['scanner_bindings']))))
block_work('operation_executor_owner_missing',lambda x:x['operation_bindings'][next(iter(x['operation_bindings']))].pop('executor_owner'))
block_work('operation_executor_protocol_missing',lambda x:x['operation_bindings'][next(iter(x['operation_bindings']))].pop('executor_protocol'))
block_work('operation_receipt_ref_missing',lambda x:x['operation_bindings'][next(iter(x['operation_bindings']))].pop('operation_receipt_ref'))
block_work('scanner_owner_missing',lambda x:x['scanner_bindings'][next(iter(x['scanner_bindings']))].pop('scanner_owner'))

# Normative execution matrix admission + destructive required-field regression.
with tempfile.TemporaryDirectory() as td:
    product_root=Path(td)
    matrix_stage='STAGE-03'
    matrix_st=eng.stage_map(profile)[matrix_stage]
    required_sections=list(map(str,matrix_st.get('required_normative_section_uids') or []))
    required_artifacts=list(map(str,matrix_st.get('outputs') or []))+list(map(str,matrix_st.get('required_evidence') or []))
    row_total=max(len(required_sections),len(required_artifacts))
    payload={'fields':{f'f{i}':f'VALUE-{i}' for i in range(row_total)}}
    (product_root/'synthetic.yaml').write_text(yaml.safe_dump(payload,sort_keys=False),encoding='utf-8')
    rows=[]
    for i in range(row_total):
        rows.append({
          'matrix_row_uid':f'MATRIX-ROW-{i+1:03d}',
          'normative_section_uid':required_sections[i % len(required_sections)],
          'requirement_uid':f'REQ-{i+1:03d}',
          'required_artifact_type':required_artifacts[i % len(required_artifacts)],
          'artifact_ref':'synthetic.yaml',
          'artifact_owner':'SYNTHETIC-OWNER',
          'row_denominator_source':'SYNTHETIC-DENOMINATOR',
          'row_identity':f'SYNTHETIC-ROW-{i+1:03d}',
          'field_path':['fields',f'f{i}'],
          'applicability':'REQUIRED',
          'validator_uid':matrix_st['validators'][0],
          'validator_check_id':f'MATRIX-FIELD-CHECK-{i+1:03d}',
          'evidence_ref':'synthetic://matrix-evidence',
          'closure_gate':matrix_st['exit_gate'],
          'failure_disposition':'BLOCK',
          'reentry_owner':'SYNTHETIC-OWNER',
        })
    matrix={
      'artifact_uid':'SYNTHETIC-NORMATIVE-EXECUTION-MATRIX',
      'artifact_type':'NORMATIVE_EXECUTION_MATRIX',
      'governance_uid':gov,
      'stage_uid':matrix_stage,
      'work_unit_uid':'SYNTHETIC-WU-MATRIX',
      'rows':rows,
      'coverage':{
        'required_normative_section_total':len(required_sections),
        'represented_normative_section_total':len(required_sections),
        'required_artifact_total':len(set(required_artifacts)),
        'represented_artifact_total':len(set(required_artifacts)),
        'required_field_total':row_total,
        'validator_bound_field_total':row_total,
        'closure_bound_field_total':row_total,
        'missing_required_row_count':0,
        'missing_required_field_count':0,
        'duplicate_credit_count':0,
        'summary_only_credit_count':0,
        'unclassified_applicability_count':0,
        'validator_unbound_count':0,
        'closure_unbound_count':0,
        'stale_matrix_count':0,
      },
      'status':'PASS',
    }
    (product_root/'NORMATIVE_EXECUTION_MATRIX.yaml').write_text(yaml.safe_dump(matrix,sort_keys=False),encoding='utf-8')
    matrix_work={'work_unit_uid':'SYNTHETIC-WU-MATRIX','normative_execution_matrix_ref':'NORMATIVE_EXECUTION_MATRIX.yaml'}
    eng.validate_normative_execution_matrix(matrix_stage,product_root,matrix_work,matrix_st,gov)
    broken=deepcopy(payload)
    del broken['fields']['f0']
    (product_root/'synthetic.yaml').write_text(yaml.safe_dump(broken,sort_keys=False),encoding='utf-8')
    try:
        eng.validate_normative_execution_matrix(matrix_stage,product_root,matrix_work,matrix_st,gov)
    except eng.StageEngineError as exc:
        if 'NORMATIVE_MATRIX_REQUIRED_FIELD_MISSING' not in str(exc):
            raise
        cases+=1
    else:
        raise SystemExit('FAIL_EXPECTED_MATRIX-DESTRUCTIVE-REQUIRED-FIELD')

# Stage-01..11 governance pressure tests using the real common validators.
# Synthetic fixtures live only in a temporary product root and grant zero product completion credit.
with tempfile.TemporaryDirectory() as td:
    pressure_root=Path(td)
    old_root=os.environ.get(eng.PRODUCT_ROOT_ENV)
    os.environ[eng.PRODUCT_ROOT_ENV]=str(pressure_root)
    stages=eng.stage_map(profile)
    invdoc=eng.y(eng.INVARIANTS)
    cross_policy=((invdoc.get('invariants') or {}).get('CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS') or {})
    binding_requirements=cross_policy.get('successor_execution_binding_requirements') or {}
    binding_maps=cross_policy.get('successor_execution_binding_operation_map') or {}
    binding_fields=list(map(str,cross_policy.get('successor_execution_binding_required_row_fields') or []))

    def _binding_row(binding_class, consuming_operation_uid):
        row={k:'SYNTHETIC' for k in binding_fields}
        row.update({
          'binding_class':binding_class,
          'consuming_operation_uid':consuming_operation_uid,
          'canonical_owner_or_authority_ref':'SYNTHETIC-CURRENT-AUTHORITY',
          'applicability':'REQUIRED',
          'resolution_status':'BOUND',
          'authority_evidence_ref':'synthetic://authority',
          'target_identity':'synthetic://target/'+binding_class.lower(),
          'denominator_inclusion_status':'INCLUDED',
          'consumer_readiness_status':'READY',
          'failure_disposition':'BLOCK_AND_REENTER_OWNER',
          'reentry_owner':'SYNTHETIC-CURRENT-AUTHORITY',
        })
        return row

    def _write_valid_handoff(predecessor_uid):
        predecessor=stages[predecessor_uid]
        successor_uid=str(predecessor.get('next_stage_uid') or '')
        if successor_uid in stages:
            successor=stages[successor_uid]
            required_inputs=[{'input_uid':x,'status':'MATERIALIZED'} for x in successor.get('inputs') or []]
            classes=list(map(str,binding_requirements.get(successor_uid) or []))
            op_map=binding_maps.get(successor_uid) or {}
            rows=[_binding_row(cls,str(op_map.get(cls) or successor['operations'][0])) for cls in classes]
        else:
            required_inputs=[]
            classes=list(map(str,cross_policy.get('next_page_successor_binding_requirements') or []))
            rows=[_binding_row(cls,'NEXT_PAGE_ELIGIBILITY_EVALUATE') for cls in classes]
        rel=f'{predecessor_uid}-handoff.yaml'
        ledger={
          'artifact_uid':'SYNTHETIC-'+predecessor_uid+'-HANDOFF',
          'artifact_type':'CROSS_STAGE_HANDOFF_READINESS_LEDGER',
          'stage_uid':predecessor_uid,
          'work_unit_uid':'SYNTHETIC-'+predecessor_uid+'-WU',
          'successor_stage_uid':successor_uid,
          'successor_required_inputs':required_inputs,
          'successor_execution_bindings':rows,
          'successor_execution_binding_total':len(classes),
          'successor_execution_binding_ready_total':len(classes),
          'successor_execution_binding_unresolved_total':0,
          'reference_resolution_complete':True,
          'physical_materialization_complete':True,
          'required_field_completeness_complete':True,
          'denominator_reconciled':True,
          'consumer_readiness_complete':True,
          'current_matrix_valid':True,
          'current_state_consistent':True,
          'unresolved_required_dependency_total':0,
          'status':'PASS',
        }
        (pressure_root/rel).write_text(yaml.safe_dump(ledger,sort_keys=False),encoding='utf-8')
        evidence={'result':'PASS','cross_stage_handoff':{'ledger_ref':rel,'external_receipt':False}}
        return predecessor,successor_uid,rel,ledger,evidence

    # Every downstream handoff STAGE-04..11 must accept a complete denominator,
    # then reject a missing binding class. This proves the validator is not artifact-presence-only.
    for predecessor_uid in [f'STAGE-{i:02d}' for i in range(4,12)]:
        predecessor,successor_uid,rel,ledger,evidence=_write_valid_handoff(predecessor_uid)
        eng._validate_cross_stage_handoff_ledger(predecessor_uid,deepcopy(evidence),predecessor,stages)
        if ledger['successor_execution_bindings']:
            broken=deepcopy(ledger)
            removed=broken['successor_execution_bindings'].pop()
            broken['successor_execution_binding_total']-=1
            broken['successor_execution_binding_ready_total']-=1
            (pressure_root/rel).write_text(yaml.safe_dump(broken,sort_keys=False),encoding='utf-8')
            expect_stage_engine_block(
              f'{predecessor_uid}_missing_successor_binding_{removed["binding_class"]}',
              lambda p=predecessor_uid,e=deepcopy(evidence),st=predecessor: eng._validate_cross_stage_handoff_ledger(p,e,st,stages),
              'CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_DENOMINATOR_DRIFT'
            )
            (pressure_root/rel).write_text(yaml.safe_dump(ledger,sort_keys=False),encoding='utf-8')

    # STAGE-04 -> STAGE-05: technology stack must be Current Authority, never an AI recommendation.
    predecessor,successor_uid,rel,ledger,evidence=_write_valid_handoff('STAGE-04')
    for cls in ('IMPLEMENTATION_LANGUAGE_AUTHORITY','FRONTEND_FRAMEWORK_AUTHORITY','BACKEND_FRAMEWORK_AUTHORITY','PACKAGE_MANAGER_AUTHORITY','DATABASE_TARGET','AUTHENTICATION_TARGET','AUTHORIZATION_TARGET'):
        broken=deepcopy(ledger)
        row=next(x for x in broken['successor_execution_bindings'] if x['binding_class']==cls)
        row['resolution_status']='UNRESOLVED'
        row['canonical_owner_or_authority_ref']=''
        row['authority_evidence_ref']=''
        row['target_identity']=''
        row['consumer_readiness_status']='NOT_READY'
        broken['successor_execution_binding_ready_total']-=1
        broken['successor_execution_binding_unresolved_total']=1
        (pressure_root/rel).write_text(yaml.safe_dump(broken,sort_keys=False),encoding='utf-8')
        expect_stage_engine_block(
          'stage05_unbound_'+cls.lower(),
          lambda e=deepcopy(evidence),st=predecessor: eng._validate_cross_stage_handoff_ledger('STAGE-04',e,st,stages),
          'CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_NOT_READY'
        )
    (pressure_root/rel).write_text(yaml.safe_dump(ledger,sort_keys=False),encoding='utf-8')

    # AUTHORIZED_NOT_APPLICABLE is legal only with exact authority evidence.
    broken=deepcopy(ledger)
    row=next(x for x in broken['successor_execution_bindings'] if x['binding_class']=='EXTERNAL_INTEGRATION_TARGET')
    row.update({
      'applicability':'AUTHORIZED_NOT_APPLICABLE',
      'resolution_status':'AUTHORIZED_NOT_APPLICABLE',
      'authority_evidence_ref':'',
      'target_identity':'',
      'consumer_readiness_status':'NOT_APPLICABLE_WITH_AUTHORITY'
    })
    (pressure_root/rel).write_text(yaml.safe_dump(broken,sort_keys=False),encoding='utf-8')
    expect_stage_engine_block(
      'stage05_na_without_authority',
      lambda e=deepcopy(evidence),st=predecessor: eng._validate_cross_stage_handoff_ledger('STAGE-04',e,st,stages),
      'CROSS_STAGE_SUCCESSOR_EXECUTION_BINDING_NA_AUTHORITY_MISSING'
    )

    # A PASS handoff can never mask invalid Matrix or Current State.
    for field in ('current_matrix_valid','current_state_consistent'):
        broken=deepcopy(ledger)
        broken[field]=False
        (pressure_root/rel).write_text(yaml.safe_dump(broken,sort_keys=False),encoding='utf-8')
        expect_stage_engine_block(
          'stage04_pass_masks_'+field,
          lambda e=deepcopy(evidence),st=predecessor: eng._validate_cross_stage_handoff_ledger('STAGE-04',e,st,stages),
          'CROSS_STAGE_HANDOFF_LEDGER_CORE_INTEGRITY_INVALID'
        )
    (pressure_root/rel).write_text(yaml.safe_dump(ledger,sort_keys=False),encoding='utf-8')

    # Matrix pressure: empty row set and stale status must both fail closed.
    matrix_stage='STAGE-05'
    matrix_st=stages[matrix_stage]
    wu='SYNTHETIC-PRESSURE-STAGE05'
    wd=pressure_root/'STAGE_EXECUTION'/matrix_stage/wu
    wd.mkdir(parents=True,exist_ok=True)
    sections=list(map(str,matrix_st.get('required_normative_section_uids') or []))
    arts=list(map(str,matrix_st.get('outputs') or []))+list(map(str,matrix_st.get('required_evidence') or []))
    total=max(len(sections),len(arts))
    payload={'fields':{f'f{i}':f'VALUE-{i}' for i in range(total)}}
    (wd/'payload.yaml').write_text(yaml.safe_dump(payload,sort_keys=False),encoding='utf-8')
    rows=[]
    for i in range(total):
        rows.append({
          'matrix_row_uid':f'PRESSURE-MATRIX-{i+1:03d}','normative_section_uid':sections[i % len(sections)],
          'requirement_uid':f'PRESSURE-REQ-{i+1:03d}','required_artifact_type':arts[i % len(arts)],
          'artifact_ref':f'STAGE_EXECUTION/{matrix_stage}/{wu}/payload.yaml','artifact_owner':'SYNTHETIC-OWNER',
          'row_denominator_source':'SYNTHETIC-PRESSURE','row_identity':f'PRESSURE-ROW-{i+1:03d}',
          'field_path':['fields',f'f{i}'],'applicability':'REQUIRED','validator_uid':matrix_st['validators'][0],
          'validator_check_id':f'PRESSURE-CHECK-{i+1:03d}','evidence_ref':'synthetic://pressure',
          'closure_gate':matrix_st['exit_gate'],'failure_disposition':'BLOCK','reentry_owner':'SYNTHETIC-OWNER'
        })
    matrix={
      'artifact_uid':'SYNTHETIC-PRESSURE-NEM','artifact_type':'NORMATIVE_EXECUTION_MATRIX','governance_uid':gov,
      'stage_uid':matrix_stage,'work_unit_uid':wu,'rows':rows,'coverage':{
        'required_normative_section_total':len(sections),'represented_normative_section_total':len(sections),
        'required_artifact_total':len(set(arts)),'represented_artifact_total':len(set(arts)),
        'required_field_total':total,'validator_bound_field_total':total,'closure_bound_field_total':total,
        'missing_required_row_count':0,'missing_required_field_count':0,'duplicate_credit_count':0,'summary_only_credit_count':0,
        'unclassified_applicability_count':0,'validator_unbound_count':0,'closure_unbound_count':0,'stale_matrix_count':0},
      'status':'PASS'
    }
    mpath=wd/'NORMATIVE_EXECUTION_MATRIX.yaml'
    mpath.write_text(yaml.safe_dump(matrix,sort_keys=False),encoding='utf-8')
    mwork={'work_unit_uid':wu,'normative_execution_matrix_ref':f'STAGE_EXECUTION/{matrix_stage}/{wu}/NORMATIVE_EXECUTION_MATRIX.yaml'}
    eng.validate_normative_execution_matrix(matrix_stage,pressure_root,mwork,matrix_st,gov)
    empty=deepcopy(matrix); empty['rows']=[]
    mpath.write_text(yaml.safe_dump(empty,sort_keys=False),encoding='utf-8')
    expect_stage_engine_block('matrix_rows_empty',lambda:eng.validate_normative_execution_matrix(matrix_stage,pressure_root,mwork,matrix_st,gov),'NORMATIVE_EXECUTION_MATRIX_ROWS_EMPTY')
    stale=deepcopy(matrix); stale['coverage']['stale_matrix_count']=1
    mpath.write_text(yaml.safe_dump(stale,sort_keys=False),encoding='utf-8')
    expect_stage_engine_block('matrix_stale_count',lambda:eng.validate_normative_execution_matrix(matrix_stage,pressure_root,mwork,matrix_st,gov),'NORMATIVE_EXECUTION_MATRIX_COVERAGE_DRIFT')
    mpath.write_text(yaml.safe_dump(matrix,sort_keys=False),encoding='utf-8')

    # Current-state pressure: a PASS stage cannot be CLOSED while operations are incomplete
    # or while current_operation still points at readiness/pending work.
    scope_rel=f'STAGE_EXECUTION/{matrix_stage}/{wu}/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
    yaml.safe_dump({'artifact_type':'EXECUTION_SCOPE_MANIFEST','stage_uid':matrix_stage,'work_unit_uid':wu,'governance_uid':gov},(wd/'CURRENT_EXECUTION_SCOPE_MANIFEST.yaml').open('w',encoding='utf-8'),sort_keys=False)
    yaml.safe_dump({
      'artifact_type':'WORK_UNIT','work_unit_uid':wu,'stage_uid':matrix_stage,'status':'CLOSED','current_status':'CLOSED',
      'normative_execution_matrix_ref':mwork['normative_execution_matrix_ref']
    },(wd/'WORK_UNIT.yaml').open('w',encoding='utf-8'),sort_keys=False)
    valid_state={'artifact_type':'WORK_UNIT_EXECUTION_STATE','stage_uid':matrix_stage,'work_unit_uid':wu,'completed_operations':list(matrix_st['operations']),'current_operation':'COMPLETE','status':'CLOSED'}
    yaml.safe_dump(valid_state,(wd/'EXECUTION_STATE.yaml').open('w',encoding='utf-8'),sort_keys=False)
    state_e={'scope_manifest_ref':scope_rel,'result':'PASS'}
    eng._validate_current_stage_state_bundle(matrix_stage,state_e,matrix_st,gov)
    incomplete=deepcopy(valid_state); incomplete['completed_operations']=incomplete['completed_operations'][:-1]
    yaml.safe_dump(incomplete,(wd/'EXECUTION_STATE.yaml').open('w',encoding='utf-8'),sort_keys=False)
    expect_stage_engine_block('state_closed_incomplete_operations',lambda:eng._validate_current_stage_state_bundle(matrix_stage,state_e,matrix_st,gov),'CURRENT_STATE_OPERATION_SET_CONFLICT')
    pending=deepcopy(valid_state); pending['current_operation']='STAGE05_INPUT_READINESS_PENDING'
    yaml.safe_dump(pending,(wd/'EXECUTION_STATE.yaml').open('w',encoding='utf-8'),sort_keys=False)
    expect_stage_engine_block('state_closed_but_readiness_pending',lambda:eng._validate_current_stage_state_bundle(matrix_stage,state_e,matrix_st,gov),'CURRENT_STATE_CURRENT_OPERATION_CONFLICT')
    badstatus=deepcopy(valid_state); badstatus['status']='IN_PROGRESS'
    yaml.safe_dump(badstatus,(wd/'EXECUTION_STATE.yaml').open('w',encoding='utf-8'),sort_keys=False)
    expect_stage_engine_block('state_pass_but_in_progress',lambda:eng._validate_current_stage_state_bundle(matrix_stage,state_e,matrix_st,gov),'CURRENT_STATE_STATUS_CONFLICT')

    if old_root is None:
        os.environ.pop(eng.PRODUCT_ROOT_ENV,None)
    else:
        os.environ[eng.PRODUCT_ROOT_ENV]=old_root


# Operation-level effectful dispatch migration pressure test.
# Uses only a temporary product root and a synthetic registered Python executor.
with tempfile.TemporaryDirectory() as _exec_td:
    _exec_root=Path(_exec_td)
    _entry,_reg,_gov,_profile,_adapters,_stages=eng.validate_definition()
    _sid='STAGE-05'
    _st=_stages[_sid]
    _wu='SYNTHETIC-EFFECTFUL-STAGE05'
    _wd=_exec_root/'STAGE_EXECUTION'/_sid/_wu
    (_wd/'EVIDENCE'/'OPERATION_RECEIPTS').mkdir(parents=True,exist_ok=True)
    (_exec_root/'tools').mkdir(parents=True,exist_ok=True)
    (_exec_root/'dependency.yaml').write_text('status: PASS\n',encoding='utf-8')

    _sections=list(map(str,_st.get('required_normative_section_uids') or []))
    _arts=list(map(str,_st.get('outputs') or []))+list(map(str,_st.get('required_evidence') or []))
    _total=max(len(_sections),len(_arts))
    _payload={'fields':{f'f{i}':f'VALUE-{i}' for i in range(_total)}}
    (_wd/'payload.yaml').write_text(yaml.safe_dump(_payload,sort_keys=False),encoding='utf-8')
    _rows=[]
    for _i in range(_total):
        _rows.append({
          'matrix_row_uid':f'EXEC-MATRIX-{_i+1:03d}','normative_section_uid':_sections[_i % len(_sections)],
          'requirement_uid':f'EXEC-REQ-{_i+1:03d}','required_artifact_type':_arts[_i % len(_arts)],
          'artifact_ref':f'STAGE_EXECUTION/{_sid}/{_wu}/payload.yaml','artifact_owner':'SYNTHETIC-OWNER',
          'row_denominator_source':'SYNTHETIC-EFFECTFUL','row_identity':f'EXEC-ROW-{_i+1:03d}',
          'field_path':['fields',f'f{_i}'],'applicability':'REQUIRED','validator_uid':_st['validators'][0],
          'validator_check_id':f'EXEC-CHECK-{_i+1:03d}','evidence_ref':'synthetic://effectful',
          'closure_gate':_st['exit_gate'],'failure_disposition':'BLOCK','reentry_owner':'SYNTHETIC-OWNER'
        })
    _matrix={
      'artifact_uid':'SYNTHETIC-EFFECTFUL-NEM','artifact_type':'NORMATIVE_EXECUTION_MATRIX','governance_uid':_gov,
      'stage_uid':_sid,'work_unit_uid':_wu,'rows':_rows,'coverage':{
        'required_normative_section_total':len(_sections),'represented_normative_section_total':len(_sections),
        'required_artifact_total':len(set(_arts)),'represented_artifact_total':len(set(_arts)),
        'required_field_total':_total,'validator_bound_field_total':_total,'closure_bound_field_total':_total,
        'missing_required_row_count':0,'missing_required_field_count':0,'duplicate_credit_count':0,'summary_only_credit_count':0,
        'unclassified_applicability_count':0,'validator_unbound_count':0,'closure_unbound_count':0,'stale_matrix_count':0},
      'status':'PASS'
    }
    _matrix_rel=f'STAGE_EXECUTION/{_sid}/{_wu}/NORMATIVE_EXECUTION_MATRIX.yaml'
    (_wd/'NORMATIVE_EXECUTION_MATRIX.yaml').write_text(yaml.safe_dump(_matrix,sort_keys=False),encoding='utf-8')

    _executor_rel='tools/synthetic_stage_executor.py'
    _executor_code='''#!/usr/bin/env python3
import argparse
from pathlib import Path
import yaml
p=argparse.ArgumentParser()
p.add_argument("--stage",required=True); p.add_argument("--operation",required=True)
p.add_argument("--work-unit",required=True); p.add_argument("--product-root",required=True)
a=p.parse_args()
root=Path(a.product_root)
work=yaml.safe_load((root/a.work_unit).read_text(encoding="utf-8")) or {}
binding=(work.get("operation_bindings") or {}).get(a.operation) or {}
receipt=root/str(binding.get("operation_receipt_ref") or "")
receipt.parent.mkdir(parents=True,exist_ok=True)
obj={
 "artifact_type":"OPERATION_EXECUTION_RECEIPT",
 "stage_uid":a.stage,
 "work_unit_uid":work.get("work_unit_uid"),
 "operation_uid":a.operation,
 "governance_uid":work.get("governance_uid"),
 "status":"PASS",
 "executor_owner":binding.get("executor_owner"),
 "executor_protocol":binding.get("executor_protocol"),
 "result_owner":binding.get("result_owner")
}
receipt.write_text(yaml.safe_dump(obj,sort_keys=False),encoding="utf-8")
'''
    (_exec_root/_executor_rel).write_text(_executor_code,encoding='utf-8')

    _ops=list(map(str,_st.get('operations') or []))
    _operation_bindings={}
    for _op in _ops:
        _operation_bindings[_op]={
          'executor_owner':_executor_rel,
          'result_owner':'SYNTHETIC_RESULT_OWNER',
          'executor_protocol':'PYTHON_STAGE_OPERATION_V1',
          'operation_receipt_ref':f'STAGE_EXECUTION/{_sid}/{_wu}/EVIDENCE/OPERATION_RECEIPTS/{_op}.yaml'
        }
    _scanner_bindings={
      str(_dim):{'scanner_owner':'SYNTHETIC_SCANNER_OWNER','result_owner':'SYNTHETIC_RESULT_OWNER'}
      for _dim in (_adapters['stages'][_sid].get('scanner_dimensions') or [])
    }
    _work={
      'artifact_type':'WORK_UNIT','work_unit_uid':_wu,'governance_uid':_gov,
      'primary_task_layer':'PRODUCT_STAGE_EXECUTION','stage_uid':_sid,'current_status':'ACTIVE',
      'pre_execution_gate_status':'PASS','required_outputs':list(_st.get('outputs') or []),
      'dependencies':['dependency.yaml'],'normative_execution_matrix_ref':_matrix_rel,
      'operation_bindings':_operation_bindings,'scanner_bindings':_scanner_bindings
    }
    _work_rel=f'STAGE_EXECUTION/{_sid}/{_wu}/WORK_UNIT.yaml'
    (_wd/'WORK_UNIT.yaml').write_text(yaml.safe_dump(_work,sort_keys=False),encoding='utf-8')
    _scope={
      'artifact_type':'EXECUTION_SCOPE_MANIFEST','stage_uid':_sid,'work_unit_uid':_wu,
      'governance_uid':_gov,'product_stage_execution_allowed':True
    }
    _scope_rel=f'STAGE_EXECUTION/{_sid}/{_wu}/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
    (_wd/'CURRENT_EXECUTION_SCOPE_MANIFEST.yaml').write_text(yaml.safe_dump(_scope,sort_keys=False),encoding='utf-8')
    _state={
      'artifact_type':'WORK_UNIT_EXECUTION_STATE','stage_uid':_sid,'work_unit_uid':_wu,
      'completed_operations':[],'current_operation':_ops[0],'status':'IN_PROGRESS',
      'resume_control':{'product_execution_allowed':True}
    }
    (_wd/'EXECUTION_STATE.yaml').write_text(yaml.safe_dump(_state,sort_keys=False),encoding='utf-8')

    _old_root=os.environ.get(eng.PRODUCT_ROOT_ENV)
    _old_work=os.environ.get(eng.ACTIVE_WORK_UNIT_ENV)
    _old_scope=os.environ.get(eng.CURRENT_SCOPE_ENV)
    os.environ[eng.PRODUCT_ROOT_ENV]=str(_exec_root)
    os.environ[eng.ACTIVE_WORK_UNIT_ENV]=_work_rel
    os.environ[eng.CURRENT_SCOPE_ENV]=_scope_rel
    try:
        _bad=deepcopy(_work)
        _bad['operation_bindings'][_ops[0]]['executor_protocol']='SHELL'
        (_wd/'WORK_UNIT.yaml').write_text(yaml.safe_dump(_bad,sort_keys=False),encoding='utf-8')
        expect_stage_engine_block('effectful_executor_protocol_forbidden',lambda:eng.execute_active(_sid),'ACTIVE_WORK_UNIT_OPERATION_EXECUTOR_PROTOCOL_INVALID')

        _bad=deepcopy(_work)
        _bad['operation_bindings'][_ops[0]]['executor_owner']='tools/missing_executor.py'
        (_wd/'WORK_UNIT.yaml').write_text(yaml.safe_dump(_bad,sort_keys=False),encoding='utf-8')
        expect_stage_engine_block('effectful_executor_missing',lambda:eng.execute_active(_sid),'ACTIVE_STAGE_EXECUTOR_OWNER_MISSING')

        _bad=deepcopy(_work)
        _bad['operation_bindings'][_ops[0]]['operation_receipt_ref']='outside-receipt.yaml'
        (_wd/'WORK_UNIT.yaml').write_text(yaml.safe_dump(_bad,sort_keys=False),encoding='utf-8')
        expect_stage_engine_block('effectful_receipt_outside_work_unit',lambda:eng.execute_active(_sid),'ACTIVE_STAGE_OPERATION_RECEIPT_OUTSIDE_WORK_UNIT')

        (_wd/'WORK_UNIT.yaml').write_text(yaml.safe_dump(_work,sort_keys=False),encoding='utf-8')
        assert eng.execute_active(_sid) is True
        _state_after=yaml.safe_load((_wd/'EXECUTION_STATE.yaml').read_text(encoding='utf-8')) or {}
        assert _state_after.get('completed_operations')==[_ops[0]]
        assert _state_after.get('current_operation')==_ops[1]
        assert _state_after.get('status')=='IN_PROGRESS'
        assert _state_after.get('last_operation_uid')==_ops[0]
        assert _state_after.get('last_operation_receipt_ref')==_operation_bindings[_ops[0]]['operation_receipt_ref']
        assert (_exec_root/_operation_bindings[_ops[0]]['operation_receipt_ref']).is_file()
        assert not (_exec_root/_operation_bindings[_ops[1]]['operation_receipt_ref']).exists()
    finally:
        for _key,_value in (
            (eng.PRODUCT_ROOT_ENV,_old_root),(eng.ACTIVE_WORK_UNIT_ENV,_old_work),(eng.CURRENT_SCOPE_ENV,_old_scope)
        ):
            if _value is None: os.environ.pop(_key,None)
            else: os.environ[_key]=_value

assert not (ROOT/'governance/ci/compile_stage_execution_preflight.py').exists()
assert not (ROOT/'governance/ci/stage_execution_adapters/stage02_functional_contract.py').exists()
s2=adapters['stages']['STAGE-02']
assert s2.get('scanner_mode')=='NORMALIZED_COMMON_EVIDENCE_CONTRACT'
for forbidden in ('python_compatibility_module','compatibility_current_execution_authority','compatibility_may_resolve_current_scope','compatibility_state_source'):
    assert forbidden not in s2, f'LEGACY_STAGE02_COMPATIBILITY_FIELD_STILL_PRESENT:{forbidden}'
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
print(f'PASS: common Stage Execution Engine negative regression cases={cases}; matrix_destructive_required_field=PASS')
print('PASS: Stage-02 current execution has no historical compatibility module or test-state scope resolver')


# Full selected-profile multidirectional audit: 9 modes x all 11 stages.
# Exact user-controlled Stage range semantics.
assert eng.resolve_stage_range('STAGE-01','STAGE-01') == ['STAGE-01']
assert eng.resolve_stage_range('STAGE-01','STAGE-05') == ['STAGE-01','STAGE-02','STAGE-03','STAGE-04','STAGE-05']
assert eng.resolve_stage_range('STAGE-03','STAGE-08') == ['STAGE-03','STAGE-04','STAGE-05','STAGE-06','STAGE-07','STAGE-08']
# High-level lifecycle runtime pressure tests that require no product deployment.
_release_chain=(eng._deterministic_stage_audit_contract().get('release_identity_continuity') or {}).get('required_chain') or []
_release_records={uid:{'release_identity':'REL-SYNTHETIC-001'} for uid in _release_chain}
assert eng.validate_release_identity_continuity(_release_records)=='REL-SYNTHETIC-001'
_bad_release=deepcopy(_release_records)
_bad_release['CURRENT_RELEASE_IDENTITY']['release_identity']='REL-SYNTHETIC-DRIFT'
expect_stage_engine_block('release_identity_chain_drift',lambda:eng.validate_release_identity_continuity(_bad_release),'RELEASE_IDENTITY_CONTINUITY_BROKEN')
_missing_release=deepcopy(_release_records); _missing_release.pop('STAGING_CLOSURE_RECORD')
expect_stage_engine_block('release_identity_chain_missing_artifact',lambda:eng.validate_release_identity_continuity(_missing_release),'RELEASE_IDENTITY_CONTINUITY_BROKEN')

assert eng.validate_environment_evidence({'environment':'PRODUCTION'},'PRODUCTION') is True
expect_stage_engine_block('staging_evidence_cannot_substitute_production',lambda:eng.validate_environment_evidence({'environment':'STAGING'},'PRODUCTION'),'CROSS_ENVIRONMENT_SUBSTITUTION_BLOCKED')
expect_stage_engine_block('unknown_environment_evidence',lambda:eng.validate_environment_evidence({'environment':'SYNTHETIC'},'PRODUCTION'),'ENVIRONMENT_EVIDENCE_IDENTITY_INVALID')
assert eng.validate_production_release_acceptance(
    {'environment':'PRODUCTION','release_identity':'REL-PROD-001'},
    {'environment':'PRODUCTION','release_identity':'REL-PROD-001'}
) is True
expect_stage_engine_block(
    'production_acceptance_release_identity_mismatch',
    lambda:eng.validate_production_release_acceptance(
        {'environment':'PRODUCTION','release_identity':'REL-PROD-001'},
        {'environment':'PRODUCTION','release_identity':'REL-PROD-002'}
    ),
    'PRODUCTION_RELEASE_IDENTITY_MISMATCH'
)

_all_stage_uids=list(eng.stage_map(profile))
_reverify_statuses={uid:('REVERIFY_REQUIRED' if uid!='STAGE-01' else 'CLOSED_PASS') for uid in _all_stage_uids}
assert eng.validate_reverify_propagation(_reverify_statuses,'STAGE-01') is True
_bad_reverify=deepcopy(_reverify_statuses); _bad_reverify['STAGE-07']='CLOSED_PASS'
expect_stage_engine_block(
    'impacted_predecessor_cannot_leave_descendant_current_pass',
    lambda:eng.validate_reverify_propagation(_bad_reverify,'STAGE-01'),
    'DOWNSTREAM_UNCONDITIONAL_CURRENT_PASS_AFTER_IMPACTED_PREDECESSOR_REVERIFY'
)

assert eng.production_redeploy_acceptance_disposition(
    {'environment':'PRODUCTION','release_identity':'REL-PROD-002'},
    {'environment':'PRODUCTION','release_identity':'REL-PROD-001'}
)=='REVERIFY_REQUIRED'
assert eng.production_redeploy_acceptance_disposition(
    {'environment':'PRODUCTION','release_identity':'REL-PROD-001'},
    {'environment':'PRODUCTION','release_identity':'REL-PROD-001'}
)=='CURRENT'

_sticky_fields=(eng._deterministic_stage_audit_contract().get('vertical_lifecycle_contract') or {}).get('sticky_identity_fields') or []
_vertical_records={}
for _sid in [f'STAGE-{i:02d}' for i in range(5,12)]:
    _vertical_records[_sid]={field:'SYNTHETIC-STICKY-'+field for field in _sticky_fields}
assert eng.validate_vertical_scope_identity(_vertical_records) is True
_bad_vertical=deepcopy(_vertical_records); _bad_vertical['STAGE-09']['release_identity']='SYNTHETIC-DRIFT'
expect_stage_engine_block('vertical_release_identity_drift',lambda:eng.validate_vertical_scope_identity(_bad_vertical),'VERTICAL_SCOPE_IDENTITY_DRIFT')

_closed={uid:'CLOSED_PASS' for uid in _all_stage_uids}
assert eng.validate_full_lifecycle_closure(_closed,0,{'operation_uid':'NEXT_PAGE_ELIGIBILITY_EVALUATE','result':'SYNTHETIC-REGISTERED-ELIGIBILITY'}) is True
_bad_closed=deepcopy(_closed); _bad_closed['STAGE-08']='REVERIFY_REQUIRED'
expect_stage_engine_block('full_lifecycle_requires_all_stage_closed_pass',lambda:eng.validate_full_lifecycle_closure(_bad_closed,0,{'operation_uid':'NEXT_PAGE_ELIGIBILITY_EVALUATE','result':'SYNTHETIC-REGISTERED-ELIGIBILITY'}),'FULL_LIFECYCLE_STAGE_NOT_CLOSED_PASS')
expect_stage_engine_block('full_lifecycle_requires_zero_impacted_reverify',lambda:eng.validate_full_lifecycle_closure(_closed,1,{'operation_uid':'NEXT_PAGE_ELIGIBILITY_EVALUATE','result':'SYNTHETIC-REGISTERED-ELIGIBILITY'}),'FULL_LIFECYCLE_IMPACTED_REVERIFY_NONZERO')
expect_stage_engine_block('full_lifecycle_requires_registered_stage11_eligibility',lambda:eng.validate_full_lifecycle_closure(_closed,0,{'operation_uid':'AI_SELECTED_OPERATION','result':'SYNTHETIC'}),'FULL_LIFECYCLE_STAGE11_ELIGIBILITY_OPERATION_INVALID')

_range_plan=eng.plan_range('STAGE-01','STAGE-05')
assert _range_plan['selected_stage_count']==5
assert _range_plan['normal_stage_boundary_user_prompt']=='FORBIDDEN'
assert _range_plan['system_selected_batch_size'] is False
for _label,_a,_b in [
    ('range_start_not_registered','STAGE-00','STAGE-01'),
    ('range_end_not_registered','STAGE-01','STAGE-18'),
    ('range_order_invalid','STAGE-05','STAGE-01'),
]:
    try:
        eng.resolve_stage_range(_a,_b)
    except eng.StageEngineError:
        pass
    else:
        raise SystemExit('FAIL_EXPECTED_'+_label.upper())
stage_rows=eng.stage_map(profile)
expected_stage_uids=[f'STAGE-{i:02d}' for i in range(1,12)]
assert list(stage_rows)==expected_stage_uids, f'STAGE_PROFILE_ORDER_DRIFT:{list(stage_rows)}'
all_stage_evidence_cases=0
all_stage_negative_cases=0

def synthetic_evidence(stage_uid,result):
    st=stage_rows[stage_uid]
    ad=adapters['stages'][stage_uid]
    blocked=result=='BLOCKED'
    head='3'*40
    phase_trace=[]
    for ph in eng.EXPECTED_PHASES:
        if blocked and ph=='TERMINAL_CLOSURE':
            status='BLOCKED'
        elif blocked and ph=='NEXT_STAGE':
            status='NOT_EXECUTED_AFTER_BLOCK'
        elif not blocked and ph in {'OWNER_REMEDIATION','FRESH_REEXECUTION'}:
            status='NOT_APPLICABLE_WITH_PROOF'
        else:
            status='PASS'
        row={'phase_uid':ph,'status':status}
        if status=='NOT_APPLICABLE_WITH_PROOF':
            row['proof']='ZERO_DISCOVERED_GAPS'
        phase_trace.append(row)
    gap=[{'problem_uid':f'SYNTH-{stage_uid}-BLOCKER'}] if blocked else []
    closure=[f'SYNTH-{stage_uid}-BLOCKER'] if blocked else []
    next_status='BLOCKED' if blocked else ('PROJECT_COMPLETE' if stage_uid=='STAGE-11' else 'READY')
    return {
      'artifact_type':'NORMALIZED_STAGE_EXECUTION_EVIDENCE',
      'governance_uid':gov,'stage_uid':stage_uid,'attempt_uid':f'SYNTH-{stage_uid}',
      'scope_manifest_ref':f'STAGE_EXECUTION/{stage_uid}/SYNTH-WU-{stage_uid}-{result}/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml',
      'actual_stage_execution_started':True,'actual_stage_execution_completed':True,
      'fresh_execution':True,'prior_results_used':False,'current_specification_mutated':False,
      'source_head_sha':head,
      'denominator':{
        'required_total':len(st['outputs']),
        'open_gap_total':1 if blocked else 0,
        'closure_blocker_total':1 if blocked else 0,
        'remaining_scope_total':1 if blocked else 0,
      },
      'gaps':gap,'closure_blockers':closure,'phase_trace':phase_trace,
      'operation_results':[{'operation_uid':x,'status':'PASS'} for x in st['operations']],
      'output_results':[{'output_uid':x,'producer_operation_uid':st['output_producers'][x],'status':'PASS'} for x in st['outputs']],
      'scanner_results':[{'scanner_dimension':x,'status':'PASS'} for x in ad['scanner_dimensions']],
      'validator_results':[{'validator_uid':x,'status':'PASS'} for x in st['validators']],
      'remediation':{
        'discovered_gap_total':1 if blocked else 0,
        'remediated_gap_total':0,
        'unresolved_gap_total':1 if blocked else 0,
        'reexecution_required':True if blocked else False,
        'reexecution_performed':True if blocked else False,
      },
      'hidden_defect_sweep':{'performed':True,'result':'PASS','discovered_defect_total':0},
      'required_evidence':[{'evidence_type':x,'status':'PASS','ref':'synthetic://external','external_receipt':True} for x in st['required_evidence']],
      'cross_stage_handoff':{
        'ledger_ref':f'STAGE_EXECUTION/{stage_uid}/SYNTH-WU-{stage_uid}-{result}/CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml','external_receipt':False,
        'successor_stage_uid':st['next_stage_uid'],
        'reference_resolution_complete':not blocked,
        'physical_materialization_complete':not blocked,
        'required_field_completeness_complete':not blocked,
        'denominator_reconciled':True,
        'consumer_readiness_complete':not blocked,
        'successor_execution_binding_total':0,
        'successor_execution_binding_ready_total':0,
        'successor_execution_binding_unresolved_total':0,
        'current_matrix_valid':True,
        'current_state_consistent':True,
        'unresolved_required_dependency_total':0,
        'status':'BLOCKED' if blocked else 'PASS',
      },
      'exact_head_gate_receipts':[{'gate_uid':'SYNTHETIC-GATE','head_sha':head,'run_id':'1','conclusion':'success'}],
      'resume_persistence':{'performed':True,'resume_point':f'SYNTH-{stage_uid}-NEXT'},
      'next_stage_transition':{'next_stage_uid':st['next_stage_uid'],'status':next_status},
      'result':result,'stage_exit_allowed':not blocked,
    }

_allstage_orig_product_root=os.environ.get(eng.PRODUCT_ROOT_ENV)
_allstage_tmp=tempfile.TemporaryDirectory()
_allstage_root=Path(_allstage_tmp.name)
os.environ[eng.PRODUCT_ROOT_ENV]=str(_allstage_root)
_cross_policy=((eng.y(eng.INVARIANTS).get('invariants') or {}).get('CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS') or {})
_cross_requirements=_cross_policy.get('successor_execution_binding_requirements') or {}
_cross_operation_map=_cross_policy.get('successor_execution_binding_operation_map') or {}
_next_requirements=list(map(str,_cross_policy.get('next_page_successor_binding_requirements') or []))

def materialize_synthetic_stage_context(stage_uid,evidence,result):
    st=stage_rows[stage_uid]
    ad=adapters['stages'][stage_uid]
    wu=f'SYNTH-WU-{stage_uid}-{result}'
    wd=_allstage_root/'STAGE_EXECUTION'/stage_uid/wu
    wd.mkdir(parents=True,exist_ok=True)
    scope_rel=f'STAGE_EXECUTION/{stage_uid}/{wu}/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
    matrix_rel=f'STAGE_EXECUTION/{stage_uid}/{wu}/NORMATIVE_EXECUTION_MATRIX.yaml'
    ledger_rel=f'STAGE_EXECUTION/{stage_uid}/{wu}/CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml'
    evidence['scope_manifest_ref']=scope_rel
    evidence['cross_stage_handoff']['ledger_ref']=ledger_rel

    yaml.safe_dump({
      'artifact_type':'EXECUTION_SCOPE_MANIFEST','stage_uid':stage_uid,'work_unit_uid':wu,
      'governance_uid':gov,'status':'CLOSED' if result=='PASS' else 'BLOCKED'
    },(wd/'CURRENT_EXECUTION_SCOPE_MANIFEST.yaml').open('w',encoding='utf-8'),sort_keys=False)
    yaml.safe_dump({
      'artifact_type':'WORK_UNIT','work_unit_uid':wu,'stage_uid':stage_uid,'primary_task_layer':'PRODUCT_STAGE_EXECUTION',
      'status':'CLOSED' if result=='PASS' else 'BLOCKED','current_status':'CLOSED' if result=='PASS' else 'BLOCKED',
      'normative_execution_matrix_ref':matrix_rel,'required_outputs':list(st['outputs']),
      'operation_bindings':{x:{'executor_owner':'synthetic.executor','result_owner':'synthetic.result'} for x in st['operations']},
      'scanner_bindings':{x:{'scanner_owner':'synthetic.scanner','result_owner':'synthetic.scan'} for x in ad['scanner_dimensions']}
    },(wd/'WORK_UNIT.yaml').open('w',encoding='utf-8'),sort_keys=False)
    yaml.safe_dump({
      'artifact_type':'WORK_UNIT_EXECUTION_STATE','stage_uid':stage_uid,'work_unit_uid':wu,
      'completed_operations':list(st['operations']) if result=='PASS' else [],
      'current_operation':'COMPLETE' if result=='PASS' else 'BLOCKED_HANDOFF',
      'status':'CLOSED' if result=='PASS' else 'BLOCKED'
    },(wd/'EXECUTION_STATE.yaml').open('w',encoding='utf-8'),sort_keys=False)

    sections=list(map(str,st.get('required_normative_section_uids') or []))
    artifacts=list(map(str,st.get('outputs') or []))+list(map(str,st.get('required_evidence') or []))
    row_total=max(len(sections),len(artifacts))
    payload={'fields':{f'f{i}':f'VALUE-{stage_uid}-{i}' for i in range(row_total)}}
    artifact_rel=f'STAGE_EXECUTION/{stage_uid}/{wu}/synthetic-artifact.yaml'
    yaml.safe_dump(payload,(wd/'synthetic-artifact.yaml').open('w',encoding='utf-8'),sort_keys=False)
    rows=[]
    for i in range(row_total):
        rows.append({
          'matrix_row_uid':f'{stage_uid}-MATRIX-{i+1:03d}',
          'normative_section_uid':sections[i % len(sections)],
          'requirement_uid':f'{stage_uid}-REQ-{i+1:03d}',
          'required_artifact_type':artifacts[i % len(artifacts)],
          'artifact_ref':artifact_rel,'artifact_owner':'SYNTHETIC-OWNER',
          'row_denominator_source':'SYNTHETIC-DENOMINATOR','row_identity':f'{stage_uid}-ROW-{i+1:03d}',
          'field_path':['fields',f'f{i}'],'applicability':'REQUIRED',
          'validator_uid':st['validators'][0],'validator_check_id':f'{stage_uid}-FIELD-{i+1:03d}',
          'evidence_ref':'synthetic://matrix-evidence','closure_gate':st['exit_gate'],
          'failure_disposition':'BLOCK','reentry_owner':'SYNTHETIC-OWNER'
        })
    yaml.safe_dump({
      'artifact_uid':f'SYNTHETIC-NEM-{stage_uid}','artifact_type':'NORMATIVE_EXECUTION_MATRIX',
      'governance_uid':gov,'stage_uid':stage_uid,'work_unit_uid':wu,'rows':rows,
      'coverage':{
        'required_normative_section_total':len(sections),'represented_normative_section_total':len(sections),
        'required_artifact_total':len(set(artifacts)),'represented_artifact_total':len(set(artifacts)),
        'required_field_total':row_total,'validator_bound_field_total':row_total,'closure_bound_field_total':row_total,
        'missing_required_row_count':0,'missing_required_field_count':0,'duplicate_credit_count':0,
        'summary_only_credit_count':0,'unclassified_applicability_count':0,'validator_unbound_count':0,
        'closure_unbound_count':0,'stale_matrix_count':0},
      'status':'PASS'
    },(wd/'NORMATIVE_EXECUTION_MATRIX.yaml').open('w',encoding='utf-8'),sort_keys=False)

    successor_uid=str(st['next_stage_uid'])
    if successor_uid in stage_rows:
        successor_inputs=list(map(str,stage_rows[successor_uid].get('inputs') or []))
        binding_classes=list(map(str,_cross_requirements.get(successor_uid) or []))
        opmap=_cross_operation_map.get(successor_uid) or {}
    else:
        successor_inputs=[]
        binding_classes=list(_next_requirements)
        opmap={}
    input_rows=[{'input_uid':x,'status':'MATERIALIZED'} for x in successor_inputs]
    binding_rows=[]
    unresolved_bindings=0
    unresolved_inputs=0
    blocked=result=='BLOCKED'
    block_by_binding=blocked and bool(binding_classes)
    if blocked and not block_by_binding and input_rows:
        input_rows[0]['status']='UNRESOLVED'
        unresolved_inputs=1
    for idx,cls in enumerate(binding_classes):
        is_blocked=block_by_binding and idx==0
        binding_rows.append({
          'binding_uid':f'SYNTH-{stage_uid}-{cls}',
          'consuming_operation_uid':str(opmap.get(cls) or 'NEXT_PAGE_ELIGIBILITY_EVALUATE'),
          'binding_class':cls,'applicability':'REQUIRED',
          'canonical_owner_or_authority_ref':'' if is_blocked else 'SYNTHETIC-CURRENT-AUTHORITY',
          'authority_evidence_ref':'' if is_blocked else 'synthetic://authority',
          'target_identity':'' if is_blocked else f'SYNTHETIC-TARGET:{cls}',
          'resolution_status':'UNRESOLVED' if is_blocked else 'BOUND',
          'denominator_inclusion_status':'INCLUDED',
          'consumer_readiness_status':'BLOCKED' if is_blocked else 'READY'
        })
        if is_blocked: unresolved_bindings+=1
    ready_bindings=len(binding_rows)-unresolved_bindings
    core_ready=not blocked
    ledger={
      'artifact_uid':f'SYNTH-HANDOFF-{stage_uid}','artifact_type':'CROSS_STAGE_HANDOFF_READINESS_LEDGER',
      'stage_uid':stage_uid,'work_unit_uid':wu,'successor_stage_uid':successor_uid,
      'successor_required_inputs':input_rows,'successor_execution_bindings':binding_rows,
      'successor_execution_binding_total':len(binding_rows),
      'successor_execution_binding_ready_total':ready_bindings,
      'successor_execution_binding_unresolved_total':unresolved_bindings,
      'reference_resolution_complete':core_ready,'physical_materialization_complete':core_ready,
      'required_field_completeness_complete':core_ready,'denominator_reconciled':True,
      'consumer_readiness_complete':core_ready,'current_matrix_valid':True,'current_state_consistent':True,
      'unresolved_required_dependency_total':unresolved_inputs,
      'status':'BLOCKED' if blocked else 'PASS'
    }
    yaml.safe_dump(ledger,(wd/'CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml').open('w',encoding='utf-8'),sort_keys=False)
    evidence['cross_stage_handoff'].update({
      'external_receipt':False,'reference_resolution_complete':core_ready,
      'physical_materialization_complete':core_ready,'required_field_completeness_complete':core_ready,
      'denominator_reconciled':True,'consumer_readiness_complete':core_ready,
      'successor_execution_binding_total':len(binding_rows),
      'successor_execution_binding_ready_total':ready_bindings,
      'successor_execution_binding_unresolved_total':unresolved_bindings,
      'current_matrix_valid':True,'current_state_consistent':True,
      'unresolved_required_dependency_total':unresolved_inputs,
      'status':'BLOCKED' if blocked else 'PASS'
    })
    return evidence

for uid in expected_stage_uids:
    pass_ev=synthetic_evidence(uid,'PASS')
    blocked_ev=synthetic_evidence(uid,'BLOCKED')
    pass_ev=materialize_synthetic_stage_context(uid,pass_ev,'PASS')
    eng.validate_evidence_data(uid,deepcopy(pass_ev))
    blocked_ev=materialize_synthetic_stage_context(uid,blocked_ev,'BLOCKED')
    eng.validate_evidence_data(uid,deepcopy(blocked_ev))
    all_stage_evidence_cases+=2
    bad=deepcopy(pass_ev)
    bad['cross_stage_handoff']['consumer_readiness_complete']=False
    try:
        eng.validate_evidence_data(uid,bad)
    except eng.StageEngineError:
        all_stage_negative_cases+=1
    else:
        raise SystemExit('FAIL_EXPECTED_ALL_STAGE_HANDOFF_BLOCK:'+uid)

# Keep the same physical synthetic product contexts alive for the later high-volume
# generic-flow evidence regressions. They are one reusable test context, not a second execution system.

# Modes 1-9: aggregate every defect before failing so one run exposes the complete profile denominator.
audit_errors=[]
def audit_error(mode,detail):
    audit_errors.append(f'{mode}:{detail}')

# Mode 1: Forward Lifecycle.
for idx,uid in enumerate(expected_stage_uids[:-1]):
    st=stage_rows[uid]
    nxt=stage_rows[expected_stage_uids[idx+1]]
    if not (nxt['entry_gate']==st['exit_gate'] or nxt['entry_gate'].startswith(st['exit_gate']+'_AND_')):
        audit_error('FORWARD_LIFECYCLE',f'GATE_DRIFT:{uid}->{expected_stage_uids[idx+1]}:{st["exit_gate"]}:{nxt["entry_gate"]}')

# Mode 2: Reverse Consumer -> Producer.
for uid,st in stage_rows.items():
    for input_uid,origin in (st.get('input_origins') or {}).items():
        origin_text=str(origin)
        import re as _re
        m=_re.match(r'^(STAGE-\d{2})',origin_text)
        if not m:
            continue
        producer_uid=m.group(1)
        if producer_uid not in stage_rows:
            audit_error('REVERSE_CONSUMER_PRODUCER',f'ORIGIN_STAGE_MISSING:{uid}:{input_uid}:{origin_text}')
            continue
        if int(producer_uid.split('-')[1]) >= int(uid.split('-')[1]):
            audit_error('REVERSE_CONSUMER_PRODUCER',f'ORIGIN_NOT_UPSTREAM:{uid}:{input_uid}:{origin_text}')
        producer_outputs=set(stage_rows[producer_uid].get('outputs') or []) | set((stage_rows[producer_uid].get('conditional_outputs') or {}).keys())
        if input_uid not in producer_outputs and not any(token in origin_text for token in ('PERSISTED','IMMUTABLE_REFERENCE_ONLY')):
            audit_error('REVERSE_CONSUMER_PRODUCER',f'OUTPUT_UNRESOLVED:{uid}:{input_uid}:{origin_text}')

# Mode 3: Producer <-> Consumer Schema Symmetry.
for uid,st in stage_rows.items():
    outputs=set(st.get('outputs') or [])
    producers=st.get('output_producers') or {}
    operations=set(st.get('operations') or [])
    if set(producers)!=outputs:
        audit_error('PRODUCER_CONSUMER_SCHEMA',f'OUTPUT_PRODUCER_DENOMINATOR:{uid}:missing={sorted(outputs-set(producers))}:extra={sorted(set(producers)-outputs)}')
    unknown=set(producers.values())-operations
    if unknown:
        audit_error('PRODUCER_CONSUMER_SCHEMA',f'OUTPUT_PRODUCER_OPERATION:{uid}:{sorted(unknown)}')

# Mode 4: Denominator & Applicability.
# Required artifacts may be either top-level lifecycle outputs or explicitly bound package members.
# Package membership is implementation metadata owned by the existing semantic adapter; it is not a second Authority.
for uid,st in stage_rows.items():
    all_outputs=set(st.get('outputs') or []) | set((st.get('conditional_outputs') or {}).keys())
    ad=adapters['stages'][uid]
    packaged_contract=ad.get('packaged_required_artifact_contract') or {}
    packaged=dict(packaged_contract.get('artifacts') or {})
    owner_output=packaged_contract.get('owner_output')
    if packaged:
        if owner_output not in all_outputs:
            audit_error('DENOMINATOR_APPLICABILITY',f'PACKAGE_OWNER_OUTPUT_NOT_REGISTERED:{uid}:{owner_output}')
        materializer=str(packaged_contract.get('materializer_owner') or '')
        materializer_path=ROOT/materializer if materializer else None
        if not materializer or not materializer_path.is_file():
            audit_error('DENOMINATOR_APPLICABILITY',f'PACKAGE_MATERIALIZER_MISSING:{uid}:{materializer}')
        else:
            spec=importlib.util.spec_from_file_location('stage_packaged_materializer_'+uid.replace('-','_'),materializer_path)
            if spec is None or spec.loader is None:
                audit_error('DENOMINATOR_APPLICABILITY',f'PACKAGE_MATERIALIZER_IMPORT_UNRESOLVED:{uid}:{materializer}')
            else:
                module=importlib.util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)
                except BaseException as exc:
                    audit_error('DENOMINATOR_APPLICABILITY',f'PACKAGE_MATERIALIZER_IMPORT_FAILED:{uid}:{materializer}:{type(exc).__name__}')
                else:
                    producer_contract=getattr(module,'PACKAGED_ARTIFACT_CONTRACT',None)
                    if not isinstance(producer_contract,dict):
                        audit_error('DENOMINATOR_APPLICABILITY',f'PACKAGE_MATERIALIZER_CONTRACT_MISSING:{uid}:{materializer}')
                    else:
                        if producer_contract.get('package_manifest_field')!=packaged_contract.get('package_manifest_field'):
                            audit_error('DENOMINATOR_APPLICABILITY',f'PACKAGE_MANIFEST_FIELD_DRIFT:{uid}')
                        producer_artifacts=producer_contract.get('artifacts') or {}
                        if producer_artifacts!=packaged:
                            audit_error('DENOMINATOR_APPLICABILITY',f'PACKAGE_MATERIALIZER_ARTIFACT_CONTRACT_DRIFT:{uid}')
    for applicability_key,rows in (st.get('required_output_applicability') or {}).items():
        required=set(rows or [])
        unbound=sorted(required-all_outputs-set(packaged))
        if unbound:
            audit_error('DENOMINATOR_APPLICABILITY',f'REQUIRED_ARTIFACT_HAS_NO_TOP_LEVEL_OR_PACKAGE_OWNER:{uid}:{applicability_key}:{unbound}')

# Mode 5: Product run-state ownership / scope locator contract.
scope_contract=profile.get('execution_scope_contract') or {}
if scope_contract.get('current_scope_artifact')!='PRODUCT_STAGE_EXECUTION_CURRENT_SCOPE_MANIFEST':
    audit_error('STATE_RESUME_PROJECTOR','CURRENT_SCOPE_ARTIFACT_NOT_PRODUCT_OWNED')
if scope_contract.get('current_scope_owner_layer')!='PRODUCT_EXECUTION_WORKLINE':
    audit_error('STATE_RESUME_PROJECTOR','CURRENT_SCOPE_OWNER_LAYER_DRIFT')
if scope_contract.get('governance_branch_may_persist_current_product_scope') is not False:
    audit_error('STATE_RESUME_PROJECTOR','GOVERNANCE_BRANCH_PRODUCT_SCOPE_PERSISTENCE_NOT_BLOCKED')
if reg.get('product_execution_branch')!='0921acpos':
    audit_error('STATE_RESUME_PROJECTOR','PRODUCT_EXECUTION_BRANCH_DRIFT')
for legacy in ('GOVERNANCE_CURRENT.yaml','governance/test/ACTIVE_STATE.yaml','governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'):
    if (ROOT/legacy).exists():
        audit_error('STATE_RESUME_PROJECTOR','LEGACY_PRODUCT_STATE_STILL_PERSISTED:'+legacy)

# Mode 6: Negative Fail-Closed.
if all_stage_negative_cases!=11:
    audit_error('NEGATIVE_FAIL_CLOSED',f'ALL_STAGE_NEGATIVE_CASE_COUNT:{all_stage_negative_cases}/11')

# Mode 7: Residual / Stale Consumer.
consumer=(ROOT/'governance/ci/validate_active_consumer_reference_integrity.py').read_text(encoding='utf-8')
if 'STALE_PRODUCT_RUN_ROOT_LITERAL' not in consumer:
    audit_error('RESIDUAL_STALE_CONSUMER','STALE_PRODUCT_RUN_ROOT_GUARD_MISSING')
workflow_paths=sorted((ROOT/'.github/workflows').glob('*.yml'))+sorted((ROOT/'.github/workflows').glob('*.yaml'))
if not workflow_paths:
    audit_error('RESIDUAL_STALE_CONSUMER','ACTIVE_WORKFLOW_SET_EMPTY')
for wfpath in workflow_paths:
    text=wfpath.read_text(encoding='utf-8')
    for stale in ('GOVERNANCE_CURRENT.yaml','governance/test/ACTIVE_STATE.yaml','governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'):
        if stale in text:
            audit_error('RESIDUAL_STALE_CONSUMER',f'ACTIVE_WORKFLOW_STALE_RUNSTATE_REF:{wfpath.name}:{stale}')
common_wf=ROOT/'.github/workflows/common-stage-execution-engine.yml'
if not common_wf.is_file() or 'stage_execution_engine.py' not in common_wf.read_text(encoding='utf-8'):
    audit_error('RESIDUAL_STALE_CONSUMER','COMMON_STAGE_ENGINE_WORKFLOW_NOT_WIRED')

# Mode 8: Source-Truth Contamination.
forbidden=set(reg.get('forbidden_in_ruleset_branch') or [])
for required in ('ACTIVE_WORK_UNIT','CURRENT_EXECUTION_SCOPE','PRODUCT_EXECUTION_EVIDENCE','PREEXECUTION_RECEIPT','PRODUCT_HISTORY'):
    if required not in forbidden:
        audit_error('SOURCE_TRUTH_CONTAMINATION','RULESET_BRANCH_FORBIDDEN_STATE_MISSING:'+required)
mutation=reg.get('mutation_policy') or {}
if mutation.get('product_execution_on_rebuild')!='FORBIDDEN':
    audit_error('SOURCE_TRUTH_CONTAMINATION','PRODUCT_EXECUTION_ON_RULESET_BRANCH_NOT_BLOCKED')
if mutation.get('product_execution_target')!='0921acpos':
    audit_error('SOURCE_TRUTH_CONTAMINATION','PRODUCT_EXECUTION_TARGET_DRIFT')
mother1=(ROOT/'.github/governance-source/active/source/12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md').read_text(encoding='utf-8')
for required_token in ('Generated Content','SOURCE_CAPTURE_GAP','跨階段來源實體化與後繼可用性 Gate'):
    if required_token not in mother1:
        audit_error('SOURCE_TRUTH_CONTAMINATION',f'MOTHER01_REQUIRED_POLICY_TOKEN_MISSING:{required_token}')
mother3=(ROOT/'.github/governance-source/active/source/12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md').read_text(encoding='utf-8')
mother4=(ROOT/'.github/governance-source/active/source/12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md').read_text(encoding='utf-8')
if 'CROSS_STAGE_HANDOFF_READINESS_LEDGER' not in mother3:
    audit_error('SOURCE_TRUTH_CONTAMINATION','MOTHER03_CROSS_STAGE_HANDOFF_LEDGER_OWNER_MISSING')
if 'CROSS_STAGE_HANDOFF_READINESS_LEDGER' not in mother4:
    audit_error('SOURCE_TRUTH_CONTAMINATION','MOTHER04_CROSS_STAGE_HANDOFF_AUDIT_OWNER_MISSING')

# Mode 9: Cross-Stage Handoff.
for uid in expected_stage_uids:
    st=stage_rows[uid]
    gate=st.get('cross_stage_materialization_gate') or {}
    if gate.get('required') is not True:
        audit_error('CROSS_STAGE_HANDOFF',f'GATE_NOT_REQUIRED:{uid}')
    if gate.get('successor_consumer_readiness_required') is not True:
        audit_error('CROSS_STAGE_HANDOFF',f'CONSUMER_READINESS_NOT_REQUIRED:{uid}')
    if gate.get('successor_required_input_reconciliation_before_exit') is not True:
        audit_error('CROSS_STAGE_HANDOFF',f'SUCCESSOR_INPUT_RECONCILIATION_NOT_REQUIRED:{uid}')

mother4=(ROOT/'.github/governance-source/active/source/12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md').read_text(encoding='utf-8')
for required_token in ('forward and reverse dependency','CROSS_STAGE_HANDOFF_READINESS_LEDGER'):
    if required_token not in mother4:
        audit_error('MOTHER_AUDIT_POLICY',f'MOTHER04_REQUIRED_POLICY_TOKEN_MISSING:{required_token}')

print(f'PASS: selected profile all-stage normalized evidence contracts {all_stage_evidence_cases}/22 (PASS+BLOCKED for STAGE-01..STAGE-11)')
print(f'PASS: selected profile all-stage cross-stage fail-closed negative cases {all_stage_negative_cases}/11')
if audit_errors:
    for error in audit_errors:
        print('BLOCK: MULTIDIRECTIONAL_AUDIT:'+error)
    raise SystemExit(f'FAIL_MULTIDIRECTIONAL_AUDIT:{len(audit_errors)}')
print('PASS: multidirectional governance audit modes 9/9 applied to Mother, Current execution profile, state, consumers and cross-stage handoffs')


# GENERIC WEB FLOW HIGH-PRESSURE PORTABILITY MATRIX
# Non-normative synthetic fixtures only. The canonical web-page complexity taxonomy comes from Mother 01.
import itertools as _itertools
import json as _json
import re as _re

_complexity_profiles = (
    'P1_READ_ONLY','P2_INTERACTIVE','P3_EFFECTFUL',
    'P4_CROSS_PAGE','P5_ASYNC_EXTERNAL','P6_SECURITY_SENSITIVE',
)
for _token in _complexity_profiles:
    if _token not in mother1:
        raise SystemExit('FAIL_MOTHER_PAGE_COMPLEXITY_PROFILE_MISSING:'+_token)

_identity_variants = (
    ('CATALOG','/catalog','ITEM'),
    ('BILLING','/billing','RECORD'),
    ('OPERATIONS','/operations','WORK_ITEM'),
    ('KNOWLEDGE','/knowledge','ENTRY'),
)
_required_fixture_key = {
    'P1_READ_ONLY':'read_only_surface',
    'P2_INTERACTIVE':'interactive_surface',
    'P3_EFFECTFUL':'effectful_chain',
    'P4_CROSS_PAGE':'cross_page_flow',
    'P5_ASYNC_EXTERNAL':'async_external_contract',
    'P6_SECURITY_SENSITIVE':'security_contract',
}
_cross_page_required = {
    'source_page','exit_state','exported_identity','transition_trigger','navigation_contract',
    'target_page','target_entry_state','required_permission','shared_dependency',
    'failure_resume','back_cancel','audit_evidence',
}
_forbidden_product_literal = _re.compile(r'\\b(?:CORE|ASSET|VIDEO|EDIT|VOICE|QA|IAM|ERP|AIAPI)-\\d+\\b')

def _web_flow_fixture(combo, identity):
    namespace, route_root, entity = identity
    profiles=set(combo)
    page_count=2 if 'P4_CROSS_PAGE' in profiles else 1
    pages=[f'{namespace}-PAGE-{i+1}' for i in range(page_count)]
    f={
      'flow_uid':f'{namespace}-FLOW-'+'-'.join(x.split('_',1)[0] for x in combo),
      'scope_uid':f'{namespace}-SCOPE-'+'-'.join(x.split('_',1)[0] for x in combo),
      'route_root':route_root,'entity_kind':entity,'profiles':sorted(profiles),'pages':pages,
    }
    if 'P1_READ_ONLY' in profiles:
        f['read_only_surface']={'list_or_detail':True,'mutation_required':False}
    if 'P2_INTERACTIVE' in profiles:
        f['interactive_surface']={'input':True,'filter_or_dialog':True,'local_state':True}
    if 'P3_EFFECTFUL' in profiles:
        f['effectful_chain']={'action':'MUTATE','validation':'REQUIRED','payload':'REQUIRED','audit':'REQUIRED','recovery':'REQUIRED'}
    if 'P4_CROSS_PAGE' in profiles:
        f['cross_page_flow']={
          'source_page':pages[0],'exit_state':'READY_FOR_HANDOFF','exported_identity':f'{namespace}-ENTITY-001',
          'transition_trigger':'CONTINUE','navigation_contract':route_root+'/next','target_page':pages[1],
          'target_entry_state':'HANDOFF_RECEIVED','required_permission':'FLOW_READ',
          'shared_dependency':f'{namespace}-SHARED-STATE','failure_resume':'RESUME_SOURCE',
          'back_cancel':'RETURN_SOURCE','audit_evidence':'FLOW_HANDOFF_RECEIPT',
        }
    if 'P5_ASYNC_EXTERNAL' in profiles:
        f['async_external_contract']={'queue_or_provider':'REGISTERED_OWNER','job_identity':'REQUIRED','status_poll_or_webhook':'REQUIRED','recovery':'REQUIRED'}
    if 'P6_SECURITY_SENSITIVE' in profiles:
        f['security_contract']={'permission':'REQUIRED','sensitive_data_classification':'REQUIRED','row_or_scope_policy':'REQUIRED','audit':'REQUIRED'}
    return f

_flow_fixtures=[]
for _r in range(1,len(_complexity_profiles)+1):
    for _combo in _itertools.combinations(_complexity_profiles,_r):
        for _identity in _identity_variants:
            _f=_web_flow_fixture(_combo,_identity)
            for _p in _combo:
                if _required_fixture_key[_p] not in _f:
                    raise SystemExit(f'FAIL_WEB_FLOW_PROFILE_FIXTURE_MISSING:{_p}:{_f["flow_uid"]}')
            if 'P4_CROSS_PAGE' in _combo:
                if len(_f['pages']) < 2 or set(_f['cross_page_flow']) != _cross_page_required:
                    raise SystemExit('FAIL_CROSS_PAGE_FIXTURE_CONTRACT:'+_f['flow_uid'])
            if _forbidden_product_literal.search(_json.dumps(_f,sort_keys=True)):
                raise SystemExit('FAIL_SYNTHETIC_FLOW_PRODUCT_IDENTITY_CONTAMINATION:'+_f['flow_uid'])
            _flow_fixtures.append(_f)

if len(_flow_fixtures) != 252:
    raise SystemExit(f'FAIL_GENERIC_WEB_FLOW_FIXTURE_DENOMINATOR:{len(_flow_fixtures)}/252')

# Every synthetic web-flow fixture must traverse every selected-profile Stage binding.
_flow_stage_binding_checks=0
for _f in _flow_fixtures:
    for _uid in expected_stage_uids:
        _st=stage_rows[_uid]
        if not (_st.get('operations') and _st.get('outputs') and _st.get('validators') and _st.get('required_evidence')):
            raise SystemExit(f'FAIL_GENERIC_FLOW_STAGE_BINDING_INCOMPLETE:{_f["flow_uid"]}:{_uid}')
        _flow_stage_binding_checks += 1
if _flow_stage_binding_checks != 2772:
    raise SystemExit(f'FAIL_GENERIC_FLOW_STAGE_BINDING_DENOMINATOR:{_flow_stage_binding_checks}/2772')

# Cache the already validated definition so the high-volume evidence mutations test evidence semantics,
# not YAML parser throughput.
_original_validate_definition = eng.validate_definition
_cached_definition = _original_validate_definition()
eng.validate_definition = lambda: _cached_definition

_generic_evidence_cases=0
for _f in _flow_fixtures:
    for _uid in expected_stage_uids:
        for _result in ('PASS','BLOCKED'):
            _ev=synthetic_evidence(_uid,_result)
            _ev['attempt_uid']=f'{_f["flow_uid"]}-{_uid}-{_result}'
            _ev['synthetic_web_flow_context']=deepcopy(_f)
            eng.validate_evidence_data(_uid,_ev)
            _generic_evidence_cases += 1

def _expect_generic_block(label, stage_uid, evidence):
    global _generic_negative_cases
    try:
        eng.validate_evidence_data(stage_uid,evidence)
    except eng.StageEngineError:
        _generic_negative_cases += 1
        return
    raise SystemExit('FAIL_EXPECTED_GENERIC_WEB_FLOW_BLOCK:'+label)

_generic_negative_cases=0
_phase_block_cases=0
_phase_na_proof_cases=0
_element_negative_cases=0
for _uid in expected_stage_uids:
    _base=synthetic_evidence(_uid,'PASS')
    # Every one of the 26 common execution phases is independently fail-closed.
    for _idx,_phase in enumerate(eng.EXPECTED_PHASES):
        _bad=deepcopy(_base)
        _bad['phase_trace'][_idx]['status']='BLOCKED'
        _expect_generic_block(f'phase_block:{_uid}:{_phase}',_uid,_bad)
        _phase_block_cases += 1

        _bad=deepcopy(_base)
        _bad['phase_trace'][_idx]['status']='NOT_APPLICABLE_WITH_PROOF'
        _bad['phase_trace'][_idx].pop('proof',None)
        _expect_generic_block(f'phase_na_without_proof:{_uid}:{_phase}',_uid,_bad)
        _phase_na_proof_cases += 1

    # Element-wise denominator integrity across operations, outputs, scanners and validators.
    for _label,_key,_rows in (
        ('operation','operation_results',_base['operation_results']),
        ('output','output_results',_base['output_results']),
        ('scanner','scanner_results',_base['scanner_results']),
        ('validator','validator_results',_base['validator_results']),
    ):
        for _idx in range(len(_rows)):
            _bad=deepcopy(_base)
            _bad[_key][_idx]['status']='BLOCKED'
            _expect_generic_block(f'{_label}_blocked:{_uid}:{_idx}',_uid,_bad)
            _element_negative_cases += 1

    # Cross-stage materialization/consumer-readiness fields must each independently block PASS.
    for _key in (
        'reference_resolution_complete','physical_materialization_complete',
        'required_field_completeness_complete','denominator_reconciled','consumer_readiness_complete',
    ):
        _bad=deepcopy(_base)
        _bad['cross_stage_handoff'][_key]=False
        _expect_generic_block(f'handoff_not_ready:{_uid}:{_key}',_uid,_bad)
        _element_negative_cases += 1
    _bad=deepcopy(_base)
    _bad['cross_stage_handoff']['unresolved_required_dependency_total']=1
    _expect_generic_block(f'handoff_unresolved:{_uid}',_uid,_bad)
    _element_negative_cases += 1

    # Every closure denominator independently blocks a false PASS.
    for _key in ('open_gap_total','closure_blocker_total','remaining_scope_total'):
        _bad=deepcopy(_base)
        _bad['denominator'][_key]=1
        if _key=='open_gap_total':
            _bad['gaps']=[{'problem_uid':'SYNTH-DENOMINATOR-GAP'}]
        elif _key=='closure_blocker_total':
            _bad['closure_blockers']=['SYNTH-DENOMINATOR-BLOCKER']
        _expect_generic_block(f'denominator_nonzero:{_uid}:{_key}',_uid,_bad)
        _element_negative_cases += 1

    # Missing each required-evidence type must fail.
    for _idx in range(len(_base['required_evidence'])):
        _bad=deepcopy(_base)
        _bad['required_evidence'].pop(_idx)
        _expect_generic_block(f'required_evidence_missing:{_uid}:{_idx}',_uid,_bad)
        _element_negative_cases += 1

    _bad=deepcopy(_base)
    _bad['next_stage_transition']['next_stage_uid']='SYNTH-WRONG-NEXT'
    _expect_generic_block(f'next_stage_drift:{_uid}',_uid,_bad)
    _element_negative_cases += 1

eng.validate_definition = _original_validate_definition

if _phase_block_cases != 286 or _phase_na_proof_cases != 286:
    raise SystemExit(f'FAIL_COMMON_PHASE_NEGATIVE_DENOMINATOR:{_phase_block_cases}/286:{_phase_na_proof_cases}/286')

if _allstage_orig_product_root is None:
    os.environ.pop(eng.PRODUCT_ROOT_ENV,None)
else:
    os.environ[eng.PRODUCT_ROOT_ENV]=_allstage_orig_product_root
_allstage_tmp.cleanup()

# Plans and reusable engine surfaces must not leak concrete ACPOS page identities.
for _uid in expected_stage_uids:
    _plan_blob=_json.dumps(eng.plan(_uid),ensure_ascii=False,sort_keys=True)
    if _forbidden_product_literal.search(_plan_blob):
        raise SystemExit('FAIL_COMMON_PLAN_PRODUCT_IDENTITY_LEAK:'+_uid)

print('PASS: Mother page-complexity taxonomy P1-P6 verified and all 63 non-empty combinations exercised')
print(f'PASS: generic web-flow synthetic fixtures {len(_flow_fixtures)}/252 across four unrelated identity/route namespaces')
print(f'PASS: generic web-flow -> selected-profile stage binding checks {_flow_stage_binding_checks}/2772')
print(f'PASS: generic web-flow normalized evidence PASS+BLOCKED cases {_generic_evidence_cases}/5544')
print(f'PASS: every common execution phase fail-closed BLOCK cases {_phase_block_cases}/286')
print(f'PASS: every common execution phase NOT_APPLICABLE proof enforcement cases {_phase_na_proof_cases}/286')
print(f'PASS: operation/output/scanner/validator/handoff/denominator/evidence element-wise negative cases {_element_negative_cases}')
print(f'PASS: total generic high-pressure negative cases {_generic_negative_cases}')
print('PASS: common Stage Execution Engine remains product-identity neutral across P1-P6 web-flow taxonomy; product execution credit=0')
