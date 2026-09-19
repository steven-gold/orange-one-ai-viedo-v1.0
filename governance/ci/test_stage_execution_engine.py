#!/usr/bin/env python3
from copy import deepcopy
from pathlib import Path
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
wrapper=(ROOT/'governance/ci/compile_stage_execution_preflight.py').read_text(encoding='utf-8')
assert 'compatibility_main' in wrapper
assert 'UNSUPPORTED_STAGE_UNTIL_MATCHING_CURRENT_EVIDENCE_EXISTS' not in wrapper
common=(ROOT/'governance/ci/stage_execution_engine.py').read_text(encoding='utf-8')
assert "STAGE='STAGE-02'" not in common
assert 'UNSUPPORTED_STAGE_UNTIL_MATCHING_CURRENT_EVIDENCE_EXISTS' not in common
print(f'PASS: common Stage Execution Engine negative regression {cases}/10')
print('PASS: Stage-02 entrypoint is compatibility-only; common engine has no Stage-02-only execution rejection')
