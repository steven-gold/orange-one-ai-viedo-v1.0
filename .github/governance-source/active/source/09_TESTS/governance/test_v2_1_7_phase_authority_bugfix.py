#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
import sys as _governance_runner_sys
if __name__ != "__main__" and "pytest" in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip("standalone governance regression executable; use registered subprocess runner", allow_module_level=True)
from pathlib import Path
import importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'09_TESTS/governance/governance_stage1_pipeline_guard.py'
spec=importlib.util.spec_from_file_location('g',P); g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

def case(name,ok,detail=None): return {'case':name,'ok':bool(ok),'detail':detail or {}}
def phase(name,state,expect_pass):
    f=g.validate_stage1_phase_boundary_state(state); return case(name,(not f)==expect_pass,{'failures':f})

def dep_fixture():
    refs=[f'AUTH-{i:02d}' for i in range(1,9)]
    return {'invented_dependency_count':0,'unresolved_authority_gaps':[{'gap_uid':f'GAP-{i:03d}','authority_ref':r,'consumer_source_uids':['RAW1'],'disposition':'UNRESOLVED_AUTHORITY_GAP','authority_evidence_ref':f'00_SOURCE_INTAKE/evidence/GAP-{i:03d}.yaml'} for i,r in enumerate(refs,1)]}
def depcase(name,mut,expect_pass,exact=False):
    d=dep_fixture(); expected={x['authority_ref'] for x in d['unresolved_authority_gaps']} if exact else None; mut(d); f=g.validate_unresolved_authority_gaps(d,{'RAW1','RAW2'},expected); return case(name,(not f)==expect_pass,{'failures':f})
def bp_fixture(dep=None):
    dep=dep or dep_fixture(); raw={'RAW1':{'page_uid':'CORE-01'},'RAW2':{'page_uid':'ASSET-01'}}
    carry=[{'gap_uid':x['gap_uid'],'authority_ref':x['authority_ref'],'disposition':'UNRESOLVED_AUTHORITY_GAP'} for x in dep['unresolved_authority_gaps'] if 'RAW1' in x['consumer_source_uids']]
    return {'blueprint_uid':'BP-CORE-PAGE','page_uid':'CORE-01','unresolved_external_authority_refs':carry},raw
def bpcase(name,mut,expect_pass):
    d=dep_fixture(); bp,raw=bp_fixture(d); mut(bp,d,raw); f=g.validate_blueprint_external_authority_carry(bp,d,raw); return case(name,(not f)==expect_pass,{'failures':f})

results=[]
results += [
 phase('segment_closed_source_fact_start_allowed',{'source_segment_mapping_completed':True,'source_fact_materialization_started':True},True),
 phase('segment_closed_source_fact_complete_allowed',{'source_segment_mapping_completed':True,'source_fact_materialization_started':True,'source_fact_materialization_completed':True},True),
 phase('source_fact_before_segment_close_blocked',{'source_segment_mapping_completed':False,'source_fact_materialization_started':True},False),
 phase('source_fact_complete_without_start_blocked',{'source_segment_mapping_completed':True,'source_fact_materialization_completed':True},False),
 phase('domain_extraction_before_source_fact_close_blocked',{'source_segment_mapping_completed':True,'source_fact_materialization_started':True,'domain_extraction_started':True},False),
 phase('responsibility_classification_before_source_fact_close_blocked',{'source_segment_mapping_completed':True,'source_fact_materialization_started':True,'responsibility_classification_started':True},False),
 phase('blueprint_before_source_fact_close_blocked',{'source_segment_mapping_completed':True,'source_fact_materialization_started':True,'blueprint_materialization_started':True},False),
 phase('classification_after_source_fact_close_allowed',{'source_segment_mapping_completed':True,'source_fact_materialization_started':True,'source_fact_materialization_completed':True,'responsibility_classification_started':True},True),
 phase('website_in_stage1_blocked',{'source_segment_mapping_completed':True,'source_fact_materialization_started':True,'source_fact_materialization_completed':True,'website_construction_started':True},False),
 phase('deployment_in_stage1_blocked',{'source_segment_mapping_completed':True,'source_fact_materialization_started':True,'source_fact_materialization_completed':True,'deployment_started':True},False),
]
results += [
 depcase('eight_unresolved_external_authorities_preserved',lambda d:None,True),
 depcase('exact_observed_gap_set_drop_blocked',lambda d:d['unresolved_authority_gaps'].pop(),False,exact=True),
 depcase('duplicate_gap_uid_blocked',lambda d:d['unresolved_authority_gaps'][1].__setitem__('gap_uid',d['unresolved_authority_gaps'][0]['gap_uid']),False),
 depcase('duplicate_authority_ref_blocked',lambda d:d['unresolved_authority_gaps'][1].__setitem__('authority_ref',d['unresolved_authority_gaps'][0]['authority_ref']),False),
 depcase('false_resolved_disposition_blocked',lambda d:d['unresolved_authority_gaps'][0].__setitem__('disposition','RESOLVED'),False),
 depcase('auto_fill_flag_blocked',lambda d:d['unresolved_authority_gaps'][0].__setitem__('auto_filled',True),False),
 depcase('substitute_authority_blocked',lambda d:d['unresolved_authority_gaps'][0].__setitem__('substitute_authority_ref','DEFAULT-AUTH'),False),
 depcase('unknown_consumer_blocked',lambda d:d['unresolved_authority_gaps'][0].__setitem__('consumer_source_uids',['RAW-UNKNOWN']),False),
 depcase('missing_evidence_ref_blocked',lambda d:d['unresolved_authority_gaps'][0].pop('authority_evidence_ref'),False),
 depcase('invented_dependency_count_blocked',lambda d:d.__setitem__('invented_dependency_count',1),False),
]
# Count preservation must be an explicit gate at the real known 8-reference boundary.
d=dep_fixture(); f=g.validate_unresolved_authority_gaps(d,{'RAW1'}); results.append(case('exact_eight_gap_identity_set_stable',not f and len(d['unresolved_authority_gaps'])==8 and len({x['authority_ref'] for x in d['unresolved_authority_gaps']})==8,{'failures':f}))
results += [
 bpcase('blueprint_carries_all_unresolved_authorities',lambda bp,d,raw:None,True),
 bpcase('blueprint_drops_one_unresolved_authority_blocked',lambda bp,d,raw:bp['unresolved_external_authority_refs'].pop(),False),
 bpcase('blueprint_false_resolution_blocked',lambda bp,d,raw:bp['unresolved_external_authority_refs'][0].__setitem__('resolved',True),False),
 bpcase('blueprint_alias_substitution_blocked',lambda bp,d,raw:bp['unresolved_external_authority_refs'][0].__setitem__('authority_ref','ALIAS-AUTH'),False),
]
out={'suite':'v2.1.7 Stage-1 phase-boundary and unresolved external authority preservation bugfix regression','total':len(results),'passed_expectations':sum(x['ok'] for x in results),'results':results}
print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['passed_expectations']==out['total'] else 1)
