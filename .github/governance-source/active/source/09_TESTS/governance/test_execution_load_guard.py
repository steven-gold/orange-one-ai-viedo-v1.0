#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
import sys as _governance_runner_sys
if __name__ != "__main__" and "pytest" in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip("standalone governance regression executable; use registered subprocess runner", allow_module_level=True)
from pathlib import Path
import copy, json, tempfile, shutil, yaml, hashlib, sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str((ROOT/'09_TESTS/governance').resolve()))
import validate_execution_governance_load as v
import program_artifact_instance_guard as inst

def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def write(p,d): Path(p).write_text(yaml.safe_dump(d,sort_keys=False,allow_unicode=True,width=140),encoding='utf-8')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hash_obj(o): return hashlib.sha256(json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def hash_uid_set(uids): return hashlib.sha256(('\n'.join(sorted(set(uids)))+'\n').encode()).hexdigest()

def mutate_case(name, rel, mut):
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)/'pkg'; r.mkdir()
        for sub in ['10_REGISTRY','12_DOCS/mother-spec']:
            shutil.copytree(ROOT/sub,r/sub,dirs_exist_ok=True)
        p=r/rel; d=load(p); mut(d); write(p,d)
        out=v.validate_definition(r)
        return {'case':name,'actual':out['status'],'expected':'FAIL','ok':out['status']=='FAIL','failures':out['failures'][:4]}

def build_valid_runtime_fixture():
    idx=load(ROOT/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml')
    life=load(ROOT/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml')
    st5=[s for s in life['stages'] if s['stage_uid']=='STAGE-05'][0]
    pa={
      'program_artifact_uid':'PA-DEMO-PAGE-RUNTIME-001','work_unit_uid':'WU-DEMO-PAGE-001','page_uid_or_scope_uid':'DEMO-PAGE-001',
      'construction_profile':'RUNTIME_SERVICE','canonical_name':'EXAMPLE_RUNTIME_SERVICE','canonical_path':'src/example/DEMO-PAGE-001/runtime-service.ts',
      'canonical_filename':'runtime-service.ts','owner_uid':'OWNER-DEMO-RUNTIME','producer_stage_uid':'STAGE-05','input_artifact_refs':[],
      'required_normative_section_uids':['WEB-GOV-02-S014'],'dependency_refs':[],'reverse_dependency_refs':[],
      'acceptance_audit_blueprint_ref':'BP-GOVERNANCE-ACCEPTANCE-001','required_test_refs':['TEST-DEMO-RUNTIME-001'],
      'current_hash':'0'*64,'status':'PLANNED'
    }
    pa['profile_contracts']={'input_contract':'CoreRuntimeInputV1','output_contract':'CoreRuntimeOutputV1','state_mutation_contract':'GOVERNED_MUTATION_ONLY','error_contract':'FAIL_CLOSED_ERROR_CONTRACT','audit_contract':'AUDIT_EVENT_REQUIRED','retry_or_recovery':'IDEMPOTENT_RETRY_OR_MANUAL_RECOVERY','test_contract':'TEST-DEMO-RUNTIME-001'}
    rm=load(ROOT/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml')
    bundles=list(idx['mandatory_common_normative_bundles'].keys()); stage_refs=st5['required_normative_section_uids']; item_refs=['WEB-GOV-02-S014']
    inst_norm_hash=inst.effective_normative_set_hash(bundles,stage_refs,item_refs)
    pa['governance_load_receipt_ref']=inst.expected_receipt_uid(pa['work_unit_uid'],rm['governance_revision'],inst_norm_hash)
    pa['write_target_binding_ref']=inst.expected_binding_uid(pa['program_artifact_uid'],pa['work_unit_uid'],pa['canonical_path'],pa['current_hash'])
    manifest={
      'work_unit_uid':'WU-DEMO-PAGE-001','governance_revision':rm['governance_revision'],
      'design_freeze_ref':'DF-DEMO-PAGE-001','program_artifacts':['PA-DEMO-PAGE-RUNTIME-001'],'dependency_closure_ref':'DEP-CLOSURE-001',
      'acceptance_audit_blueprint_ref':'BP-GOVERNANCE-ACCEPTANCE-001','naming_registry_ref':'REG-NAMING-001','section_registry_ref':'REG-NORMATIVE-SECTION-001',
      'protected_current_artifact_registry_ref':'REG-PROTECTED-CURRENT-ARTIFACT-001','typed_identity_registry_ref':'REG-PROGRAM-IDENTITY-AUTHORITY-001',
      'common_normative_bundle_refs':bundles,
      'stage_normative_section_uids':stage_refs,'item_specific_normative_section_uids':item_refs,
      'governance_load_receipt_ref':pa['governance_load_receipt_ref'],
      'governance_load_receipt':{'receipt_uid':pa['governance_load_receipt_ref'],'status':'PASS','work_unit_uid':pa['work_unit_uid'],'governance_revision':rm['governance_revision'],'semantic_baseline_content_hash':inst.SEMANTIC_BASELINE_CONTENT_HASH,'effective_normative_set_hash':inst_norm_hash},
      'dependency_closure':{'closure_uid':'DEP-CLOSURE-001','program_artifact_uid':pa['program_artifact_uid'],'dependency_refs':[],'reverse_dependency_refs':[],'status':'PASS'},
      'write_target_bindings':[{
        'binding_uid':pa['write_target_binding_ref'],'program_artifact_uid':pa['program_artifact_uid'],'work_unit_uid':pa['work_unit_uid'],'page_uid_or_scope_uid':pa['page_uid_or_scope_uid'],
        'owner_uid':pa['owner_uid'],'construction_profile':pa['construction_profile'],'canonical_path':pa['canonical_path'],
        'canonical_filename':pa['canonical_filename'],'expected_current_hash':pa['current_hash'],'producer_stage_uid':pa['producer_stage_uid']}]
    }
    common=[]
    for bid in manifest['common_normative_bundle_refs']: common+=idx['mandatory_common_normative_bundles'][bid]['section_uids']
    prof=idx['program_construction_profiles'][pa['construction_profile']]['required_normative_section_uids']
    effective=set(common+manifest['stage_normative_section_uids']+manifest['item_specific_normative_section_uids']+prof+pa['required_normative_section_uids'])
    sections=v.section_map(ROOT)
    resolved=[]
    for uid in sorted(effective):
        rr,e=v.resolve_section(ROOT,uid,sections)
        assert not e,e; resolved.append(rr)
    receipt={
      'receipt_uid':pa['governance_load_receipt_ref'],'execution_uid':'EXEC-001','run_uid':'RUN-001','work_unit_or_stage_operation_uid':'WU-DEMO-PAGE-001',
      'governance_revision':load(ROOT/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml')['governance_revision'],
      'root_manifest_hash':sha(ROOT/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'),'section_registry_hash':sha(ROOT/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'),
      'target_manifest_hash':hash_obj(manifest),'common_bundle_uids':manifest['common_normative_bundle_refs'],
      'stage_normative_section_uids':manifest['stage_normative_section_uids'],'profile_normative_section_uids':prof,
      'artifact_specific_normative_section_uids':pa['required_normative_section_uids'],'dependency_normative_section_uids':[],
      'effective_normative_set_hash':hash_uid_set(effective),'resolved_section_receipts':resolved,'loaded_artifact_receipts':[],
      'acceptance_audit_blueprint_ref':'BP-GOVERNANCE-ACCEPTANCE-001','loaded_at':'2026-09-12T00:00:00Z','loader_version':'TEST-1','status':'PASS'
    }
    return receipt,manifest,pa

def runtime_case(name,mut,expected='FAIL'):
    receipt,manifest,pa=build_valid_runtime_fixture(); mut(receipt,manifest,pa)
    out=v.validate_receipt(receipt,manifest,pa,ROOT)
    return {'case':name,'actual':out['status'],'expected':expected,'ok':out['status']==expected,'failures':out['failures'][:4]}

cases=[]
cases.append({'case':'definition_valid','actual':v.validate_definition(ROOT)['status'],'expected':'PASS','ok':v.validate_definition(ROOT)['status']=='PASS'})
cases += [
 mutate_case('common_bundle_removed','10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['mandatory_common_normative_bundles'].pop('BUNDLE-GOV-COMMON-CORE')),
 mutate_case('common_plus_specific_disabled','10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['universal_rules'].__setitem__('common_plus_specific_normative_load_required',False)),
 mutate_case('receipt_not_required','10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['governance_load_receipt_contract'].__setitem__('required_before_any_stage_operation',False)),
 mutate_case('normative_uid_write_enabled','10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['typed_uid_resolution_contract']['uid_types']['NORMATIVE_SECTION_UID'].__setitem__('write_target',True)),
 mutate_case('write_other_registered_target_allowed','10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['write_target_lock_contract'].__setitem__('valid_other_registered_artifact_is_not_valid_target',False)),
 mutate_case('stage_preload_gate_removed','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['stages'][4].pop('pre_execution_gate')),
 mutate_case('stage_normative_refs_removed','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['stages'][4].__setitem__('required_normative_section_uids',[])),
]
cases += [
 runtime_case('runtime_valid',lambda r,m,p:None,'PASS'),
 runtime_case('missing_common_bundle_runtime',lambda r,m,p:m.__setitem__('common_normative_bundle_refs',m['common_normative_bundle_refs'][1:])),
 runtime_case('stale_root_manifest_receipt',lambda r,m,p:r.__setitem__('root_manifest_hash','0'*64)),
 runtime_case('wrong_section_resolution_receipt',lambda r,m,p:r['resolved_section_receipts'][0].__setitem__('canonical_path','wrong.md')),
 runtime_case('write_target_points_to_other_artifact',lambda r,m,p:m['write_target_bindings'][0].__setitem__('canonical_path','src/example/DEMO-PAGE-001/other-valid.ts')),
 runtime_case('effective_set_hash_stale',lambda r,m,p:r.__setitem__('effective_normative_set_hash','0'*64)),
]
out={'suite':'execution governance load / common+specific / typed UID / write-target guard','total':len(cases),'passed_expectations':sum(c['ok'] for c in cases),'results':cases}
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['passed_expectations']==out['total'] else 1)
