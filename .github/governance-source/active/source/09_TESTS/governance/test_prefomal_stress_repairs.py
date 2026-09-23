#!/usr/bin/env python3
from __future__ import annotations
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
import sys as _governance_runner_sys
if __name__ != "__main__" and "pytest" in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip("standalone governance regression executable; use registered subprocess runner", allow_module_level=True)
from pathlib import Path
import copy,importlib.util,json,shutil,tempfile,yaml,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent; PKG=HERE.parents[1]
def imp(name):
    spec=importlib.util.spec_from_file_location(name,HERE/f'{name}.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
idxv=imp('validate_construction_artifact_index'); secv=imp('validate_section_registry'); clnv=imp('validate_cleanup_protection'); lifev=imp('governance_lifecycle_stage_contract_guard'); mgmtv=imp('governance_management_contract_guard')
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def dump(p,d): p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=160),encoding='utf-8')
def run_case(name,validator,mutator,expected='FAIL'):
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)/'pkg'; shutil.copytree(PKG,r)
        mutator(r)
        out=validator(r)
        actual=out.get('status')
        return {'case':name,'actual':actual,'expected':expected,'ok':actual==expected,'sample_failures':out.get('failures',[])[:3]}
cases=[]
def c(*args,**kwargs): cases.append(run_case(*args,**kwargs))
# Construction index semantic mutations (previous stress blind spots)
def mut_yaml(rel,fn):
    def m(r):
        p=r/rel; d=load(p); fn(d); dump(p,d)
    return m
c('index_nonexistent_section_uid',idxv.validate,mut_yaml('10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['program_construction_profiles']['UI_COMPONENT'].__setitem__('required_normative_section_uids',['WEB-GOV-99-S999'])))
c('index_register_before_generation_disabled',idxv.validate,mut_yaml('10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['universal_rules'].__setitem__('register_before_generation',False)))
c('index_unregistered_creation_allowed',idxv.validate,mut_yaml('10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['universal_rules'].__setitem__('unregistered_artifact_creation','ALLOW')))
c('index_forbidden_filename_policy_removed',idxv.validate,mut_yaml('10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d.__setitem__('forbidden_filename_tokens',[])))
c('index_manifest_before_code_disabled',idxv.validate,mut_yaml('10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['implementation_manifest_contract'].__setitem__('required_before_code_write',False)))
c('index_continuity_fields_removed',idxv.validate,mut_yaml('10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['continuity_contract'].__setitem__('required_edge_fields',['edge_uid'])))
c('index_reverse_dependency_disabled',idxv.validate,mut_yaml('10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['continuity_contract'].__setitem__('forward_and_reverse_edge_required',False)))
c('index_unresolved_dependency_allowed',idxv.validate,mut_yaml('10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['continuity_contract'].__setitem__('unresolved_required_edge','ALLOW')))
c('index_cleanup_transaction_truncated',idxv.validate,mut_yaml('10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['supersession_cleanup_transaction'].__setitem__('ordered_steps',['REGISTER_REPLACEMENT'])))
c('index_unsafe_relative_path_allowed',idxv.validate,mut_yaml('10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['canonical_path_policy'].__setitem__('forbidden_path_patterns',[])))
# Section numbering/reference integrity
def duplicate_heading(r):
    p=r/'12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md'; s=p.read_text(); s=s.replace('## 70. Canonical Management Artifact Materialization','## 69. Canonical Management Artifact Materialization'); p.write_text(s)
c('duplicate_numeric_section_detected',secv.validate,duplicate_heading)
# Cleanup protection: even full generic proofs may not delete protected current artifact.
def delete_protected(r): pass
with tempfile.TemporaryDirectory() as td:
    r=Path(td)/'pkg'; shutil.copytree(PKG,r)
    proofs=['NOT_PROTECTED_CURRENT','NOT_IMMUTABLE_RAW_SOURCE','ZERO_CURRENT_OWNER_REFERENCE','ZERO_UNMIGRATED_REVERSE_DEPENDENCY','REPLACEMENT_VALID_IF_SUPERSEDED','CLEANUP_LEDGER_ENTRY','POST_DELETE_RESIDUAL_SCAN']
    out=clnv.validate(r,[{'path':'10_REGISTRY/NAMING_REGISTRY.yaml','proofs':proofs}]); cases.append({'case':'protected_current_delete_blocked','actual':out['status'],'expected':'FAIL','ok':out['status']=='FAIL','sample_failures':out.get('failures',[])[:3]})
c('cleanup_default_allow_detected',clnv.validate,mut_yaml('10_REGISTRY/PROTECTED_CURRENT_ARTIFACT_REGISTRY.yaml',lambda d:d['delete_gate'].__setitem__('default','ALLOW')))
# Lifecycle semantic mutations
c('lifecycle_stage_removed',lifev.validate,mut_yaml('10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d.__setitem__('stages',d['stages'][:-1])))
def drop_input_origin(d): d['stages'][1]['input_origins'].pop(d['stages'][1]['inputs'][0],None)
c('lifecycle_input_origin_missing',lifev.validate,mut_yaml('10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',drop_input_origin))
def bad_producer(d): d['stages'][4]['output_producers'][d['stages'][4]['outputs'][0]]='MISSING-OP'
c('lifecycle_output_producer_invalid',lifev.validate,mut_yaml('10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',bad_producer))
c('lifecycle_step_binding_removed',lifev.validate,mut_yaml('10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d.__setitem__('delivery_step_bindings',d['delivery_step_bindings'][:-1])))
c('lifecycle_foundation_barrier_loosened',lifev.validate,mut_yaml('10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['topology'].__setitem__('foundation_barrier_mode','PER_PAGE')))
c('lifecycle_page_uid_sticky_broken',lifev.validate,mut_yaml('10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['topology'].__setitem__('page_uid_sticky_through_stage','STAGE-08')))
# Management materialization / closed-loop mutations
def remove_naming(r): (r/'10_REGISTRY/NAMING_REGISTRY.yaml').unlink()
c('management_naming_registry_missing',mgmtv.validate,remove_naming)
def denominator_drift(d): d['audit_item_uids']=d['audit_item_uids'][:-1]
c('management_acceptance_denominator_drift',mgmtv.validate,mut_yaml('10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml',denominator_drift))
out={'suite':'v2.1.4 preformal multidirection stress repair','fixture_policy':'DESTRUCTIVE_SEMANTIC_MUTATION','total':len(cases),'passed_expectations':sum(x['ok'] for x in cases),'results':cases}
print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['passed_expectations']==out['total'] else 1)
