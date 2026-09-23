#!/usr/bin/env python3
from copy import deepcopy
from pathlib import Path
import ast
import importlib.util
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
sample['cross_stage_handoff']={'ledger_ref':'synthetic://external','external_receipt':True,'successor_stage_uid':st['next_stage_uid'],'reference_resolution_complete':True,'physical_materialization_complete':True,'required_field_completeness_complete':True,'denominator_reconciled':True,'consumer_readiness_complete':True,'unresolved_required_dependency_total':0,'status':'PASS'}
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
 'operation_bindings':{x:{'executor_owner':'synthetic.executor','result_owner':'synthetic.results'} for x in wst['operations']},
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
block_work('scanner_owner_missing',lambda x:x['scanner_bindings'][next(iter(x['scanner_bindings']))].pop('scanner_owner'))
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
print(f'PASS: common Stage Execution Engine negative regression {cases}/39')
print('PASS: Stage-02 entrypoint is compatibility-only; common engine has no Stage-02-only execution rejection')


# Full selected-profile multidirectional audit: 9 modes x all 11 stages.
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
      'scope_manifest_ref':'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml',
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
        'ledger_ref':'synthetic://external','external_receipt':True,
        'successor_stage_uid':st['next_stage_uid'],
        'reference_resolution_complete':True,
        'physical_materialization_complete':not blocked,
        'required_field_completeness_complete':not blocked,
        'denominator_reconciled':True,
        'consumer_readiness_complete':not blocked,
        'unresolved_required_dependency_total':1 if blocked else 0,
        'status':'BLOCKED' if blocked else 'PASS',
      },
      'exact_head_gate_receipts':[{'gate_uid':'SYNTHETIC-GATE','head_sha':head,'run_id':'1','conclusion':'success'}],
      'resume_persistence':{'performed':True,'resume_point':f'SYNTH-{stage_uid}-NEXT'},
      'next_stage_transition':{'next_stage_uid':st['next_stage_uid'],'status':next_status},
      'result':result,'stage_exit_allowed':not blocked,
    }

for uid in expected_stage_uids:
    pass_ev=synthetic_evidence(uid,'PASS')
    blocked_ev=synthetic_evidence(uid,'BLOCKED')
    eng.validate_evidence_data(uid,deepcopy(pass_ev))
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

# Mode 5: State / Resume / Projector.
active_state=eng.y(eng.STATE)
profile_state=active_state.get('selected_execution_profile_state') or {}
if profile_state.get('owner_ref')!='GOVERNANCE_CURRENT.yaml':
    audit_error('STATE_RESUME_PROJECTOR','PROFILE_STATE_OWNER_DRIFT')
if active_state.get('specification_uid')!=gov:
    audit_error('STATE_RESUME_PROJECTOR','ACTIVE_STATE_GOVERNANCE_UID_DRIFT')
if not isinstance(active_state.get('resume_control'),dict) or not active_state['resume_control'].get('current_resume_point'):
    audit_error('STATE_RESUME_PROJECTOR','CURRENT_RESUME_POINT_MISSING')

# Mode 6: Negative Fail-Closed.
if all_stage_negative_cases!=11:
    audit_error('NEGATIVE_FAIL_CLOSED',f'ALL_STAGE_NEGATIVE_CASE_COUNT:{all_stage_negative_cases}/11')

# Mode 7: Residual / Stale Consumer.
consumer=(ROOT/'governance/ci/validate_active_consumer_reference_integrity.py').read_text(encoding='utf-8')
if 'STALE_PRODUCT_RUN_ROOT_LITERAL' not in consumer:
    audit_error('RESIDUAL_STALE_CONSUMER','STALE_PRODUCT_RUN_ROOT_GUARD_MISSING')
for wf in ('governance-selected-profile-integrity.yml','governance-full-line-system-gate.yml'):
    text=(ROOT/'.github/workflows'/wf).read_text(encoding='utf-8')
    if 'validate_active_consumer_reference_integrity.py' not in text:
        audit_error('RESIDUAL_STALE_CONSUMER',f'ACTIVE_CONSUMER_GATE_NOT_WIRED:{wf}')

# Mode 8: Source-Truth Contamination.
registry_sep=reg.get('test_layer_separation') or {}
if registry_sep.get('test_state_may_be_normative_authority') is not False:
    audit_error('SOURCE_TRUTH_CONTAMINATION','TEST_STATE_NORMATIVE_AUTHORITY_NOT_BLOCKED')
if registry_sep.get('temporary_test_artifact_may_be_normative_authority') is not False:
    audit_error('SOURCE_TRUTH_CONTAMINATION','TEMP_TEST_NORMATIVE_AUTHORITY_NOT_BLOCKED')
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
