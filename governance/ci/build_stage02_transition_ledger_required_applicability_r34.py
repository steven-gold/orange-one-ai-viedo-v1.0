#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import subprocess,sys,yaml
ROOT=Path(__file__).resolve().parents[2]
R17=ROOT/'governance/test/stage02/STAGE02_STATE_TRANSITION_LEDGER_DEPENDENCY_TRACE_R17.yaml'
R33=ROOT/'governance/test/stage02/STAGE02_CURRENT_FUNCTIONAL_CONTRACT_DECISION_STATUS_R33.yaml'
R35=ROOT/'governance/test/stage02/STAGE02_INDEPENDENT_DENOMINATOR_RECOMPUTATION_R35.yaml'
RAW={
 'ASSET-01':ROOT/'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
 'CORE-01':ROOT/'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
}
LEDGERS={
 page:ROOT/f'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/{page}/AUTO_COMPLETION_SCOPE_LEDGER.yaml'
 for page in RAW
}
OUT=ROOT/'governance/test/stage02/STAGE02_TRANSITION_LEDGER_REQUIRED_APPLICABILITY_R34.yaml'
FIELDS=('mutation_owner','failure_state','recovery','audit_event_uid')

def die(m): print(f'BLOCK: {m}',file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die(f'MAPPING_REQUIRED:{p.relative_to(ROOT)}')
    return o

def idx(items,key):
    out={}
    for x in items or []:
        if isinstance(x,dict) and x.get(key):
            if x[key] in out: die(f'DUPLICATE_{key}:{x[key]}')
            out[x[key]]=x
    return out

r17=load(R17); r33=load(R33); r35=load(R35)
if (r17.get('denominators') or {}).get('state_transition_ledger_field_gaps_traced')!=40: die('R34_R17_DENOMINATOR_DRIFT')
if (r33.get('denominators') or {}).get('current_effective_problems')!=129: die('R34_R33_BASELINE_DRIFT')
if r35.get('effective_gap_total')!=129 or r35.get('transition_required_field_gap_total')!=50: die('R34_R35_INDEPENDENT_BASELINE_DRIFT')
if (r35.get('transition_missing_field_counts') or {}).get('illegal_transition_tests')!=10: die('R34_R35_ILLEGAL_TEST_RAW_COUNT_DRIFT')
current={x.get('blocker_uid'):x for x in r33.get('problems') or [] if x.get('category')=='STATE_TRANSITION_LEDGER_FIELD_MISSING'}
if len(current)!=40: die(f'R34_CURRENT_TRANSITION_PROBLEM_COUNT:{len(current)}')
trace={x.get('blocker_uid'):x for x in r17.get('records') or []}
if not set(current)<=set(trace): die('R34_TRACE_COVERAGE_DRIFT')
rawtrans={}
for page,path in RAW.items():
    reg=(load(path).get('registries') or {})
    for tid,t in idx(reg.get('stage_transitions'),'transition_uid').items(): rawtrans[(page,tid)]=t

materialized_illegal_tests={}
for page,path in LEDGERS.items():
    ledger=load(path)
    for rem in ledger.get('remediations') or []:
        sig=rem.get('defect_signature') or {}
        closure=rem.get('materialized_closure') or {}
        if sig.get('category')=='STATE_TRANSITION_LEDGER_FIELD_MISSING' and sig.get('detail')=='illegal_transition_tests':
            tid=str(sig.get('uid'))
            tests=closure.get('illegal_transition_tests') or []
            if closure.get('closure_type')!='ILLEGAL_TRANSITION_NEGATIVE_TESTS' or not tests: die(f'R34_INVALID_ILLEGAL_TEST_MATERIALIZATION:{page}:{tid}')
            key=(page,tid)
            if key in materialized_illegal_tests: die(f'R34_DUPLICATE_ILLEGAL_TEST_MATERIALIZATION:{page}:{tid}')
            materialized_illegal_tests[key]={'remediation_uid':rem.get('remediation_uid'),'test_count':len(tests),'tests':tests}
if len(materialized_illegal_tests)!=10: die(f'R34_ILLEGAL_TEST_SUCCESSOR_DENOMINATOR:{len(materialized_illegal_tests)}')

records=[]; transitions=Counter(); fields=Counter(); scopes=Counter()
for blocker,p in sorted(current.items()):
    tr=trace[blocker]
    page=p.get('scope'); tid=p.get('target_uid'); field=p.get('missing_field_or_relation')
    if field not in FIELDS: die(f'R34_UNEXPECTED_FIELD:{blocker}:{field}')
    t=rawtrans.get((page,tid))
    if not t: die(f'R34_RAW_TRANSITION_MISSING:{page}:{tid}')
    if tr.get('scope')!=page or tr.get('target_uid')!=tid or tr.get('missing_field_or_relation')!=field: die(f'R34_TRACE_IDENTITY_DRIFT:{blocker}')
    if t.get(field) not in (None,'',[],{}): die(f'R34_FIELD_NOT_MISSING:{page}:{tid}:{field}')
    succ=materialized_illegal_tests.get((page,tid))
    if not succ: die(f'R34_ILLEGAL_TRANSITION_TEST_SUCCESSOR_MISSING:{page}:{tid}')
    records.append({
      'blocker_uid':blocker,'problem_uid':p.get('problem_uid'),'scope':page,'transition_uid':tid,'missing_field':field,
      'from_stage':t.get('from_stage'),'to_stage':t.get('to_stage'),'trigger':t.get('action_uid') or t.get('trigger_event_uid') or t.get('trigger'),'gate_uid':t.get('gate_uid') or t.get('gate'),
      'illegal_transition_tests_present_in_raw':t.get('illegal_transition_tests') not in (None,'',[],{}),
      'illegal_transition_tests_materialized_successor':True,
      'illegal_transition_tests_successor_remediation_uid':succ.get('remediation_uid'),
      'illegal_transition_tests_successor_test_count':succ.get('test_count'),
      'illegal_transition_tests_effectively_present':True,
      'normative_applicability':'REQUIRED',
      'normative_basis':'WEB-GOV-01-S060_EVERY_TRANSITION_MUST_BIND_MUTATION_OWNER_FAILURE_STATE_RECOVERY_AUDIT_EVENT_AND_ILLEGAL_TRANSITION_TESTS',
      'same_transition_field_value_present':False,
      'cross_role_substitution_allowed':False,
      'candidate_value':None,
      'blocker_reduction_credit':0,
    })
    transitions[(page,tid)]+=1; fields[field]+=1; scopes[page]+=1
if len(records)!=40 or len(transitions)!=10 or any(v!=4 for v in transitions.values()): die(f'R34_TRANSITION_MATRIX_DRIFT:{len(records)}:{len(transitions)}:{dict(transitions)}')
if fields!=Counter({f:10 for f in FIELDS}): die(f'R34_FIELD_COUNTS_DRIFT:{dict(fields)}')
head=subprocess.run(['git','rev-parse','HEAD'],cwd=str(ROOT),text=True,capture_output=True,check=True).stdout.strip()
out={'schema_version':2,'artifact_type':'NON_NORMATIVE_STAGE02_TRANSITION_LEDGER_REQUIRED_APPLICABILITY_R34','normative_authority':False,'stage_uid':'STAGE-02','cycle':'TRANSITION_LEDGER_REQUIRED_APPLICABILITY_CONFIRMATION_R34','source_head_sha':head,'source_contracts':{'exact_trace_r17':str(R17.relative_to(ROOT)),'current_decision_status_r33':str(R33.relative_to(ROOT)),'independent_denominator_r35':str(R35.relative_to(ROOT)),'auto_completion_scope_ledgers':[str(x.relative_to(ROOT)) for x in LEDGERS.values()],'normative_section':'WEB-GOV-01-S060'},'normative_contract':{'page_with_state_stage_transition_registry_requires_machine_readable_state_transition_ledger':True,'every_transition_must_bind':['transition_uid','from_state_or_stage','to_state_or_stage','trigger_or_action','gate_or_preconditions','mutation_owner','failure_state','recovery','audit_or_event','illegal_transition_tests'],'required_optional_na_general_rule_does_not_override_explicit_s060_must':True,'cross_role_substitution_for_missing_field_forbidden':True,'missing_required_value_may_not_be_invented':True,'successor_materialization_must_be_applied_before_effective_gap_counting':True},'denominators':{'raw_transition_required_field_gaps_r35':50,'already_materialized_illegal_transition_test_gaps':10,'current_transition_ledger_field_problems':40,'transition_count':10,'required_missing_fields_per_transition':4,'scope_counts':dict(sorted(scopes.items())),'field_counts':dict(sorted(fields.items())),'not_applicable_count':0,'optional_count':0,'required_count':40,'candidate_values_materialized_this_cycle':0,'blocker_reduction_claimed_this_cycle':0},'records':records,'current_specification_mutated':False,'immutable_stage1_source_mutated':False,'stage02_status':'BLOCKED','stage03_allowed':False,'website_construction_allowed':False,'deployment_allowed':False,'next_execution_gate':'ROLE_SAFE_SAME_TRANSITION_CANDIDATE_AUTHORING_FOR_40_REQUIRED_FIELDS'}
OUT.write_text(yaml.safe_dump(out,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
print('PASS: R34 proves all 40 current transition-ledger gaps are REQUIRED under WEB-GOV-01-S060')
print('PASS: R35 raw transition fields=50; 10 illegal-transition-test closures already materialized; current effective transition gaps=40')
print('PASS: 10 transitions x 4 unresolved required fields; N/A=0 optional=0 new materialization=0 reduction=0')
