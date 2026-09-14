#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
import sys as _governance_runner_sys
if __name__ != "__main__" and "pytest" in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip("standalone governance regression executable; use registered subprocess runner", allow_module_level=True)
from pathlib import Path
import importlib.util,json,shutil,tempfile,yaml,sys,re
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent; PKG=HERE.parents[1]

def imp(name):
    spec=importlib.util.spec_from_file_location(name,HERE/f'{name}.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
sem=imp('validate_reference_semantics'); inst=imp('program_artifact_instance_guard')
def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def dump(p,d): Path(p).write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def mutate_yaml(rel,fn):
    def m(root):
        p=root/rel; d=load(p); fn(d); dump(p,d)
    return m
def sem_case(name,mutator,expected='FAIL'):
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)/'pkg'; shutil.copytree(PKG,r); mutator(r); out=sem.validate(r)
        return {'case':name,'expected':expected,'actual':out['status'],'ok':out['status']==expected,'failures':out.get('failures',[])[:4]}
def valid_fixture(root=PKG):
    idx=load(root/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'); ref=load(root/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'); rm=load(root/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml')
    pa={
      'program_artifact_uid':'PA-DEMO-PAGE-RUNTIME-001','work_unit_uid':'WU-DEMO-PAGE-001','page_uid_or_scope_uid':'DEMO-PAGE-001','construction_profile':'RUNTIME_SERVICE',
      'canonical_name':'EXAMPLE_RUNTIME_SERVICE','canonical_path':'src/example/DEMO-PAGE-001/runtime-service.ts','canonical_filename':'runtime-service.ts','owner_uid':'OWNER-DEMO-RUNTIME',
      'producer_stage_uid':'STAGE-05','input_artifact_refs':[],'required_normative_section_uids':['WEB-GOV-02-S014'],'dependency_refs':[],'reverse_dependency_refs':[],
      'acceptance_audit_blueprint_ref':'BP-GOVERNANCE-ACCEPTANCE-001','required_test_refs':['TEST-DEMO-RUNTIME-001'],'current_hash':'0'*64,'status':'PLANNED'}
    pa['profile_contracts']={'input_contract':'CoreRuntimeInputV1','output_contract':'CoreRuntimeOutputV1','state_mutation_contract':'GOVERNED_MUTATION_ONLY','error_contract':'FAIL_CLOSED_ERROR_CONTRACT','audit_contract':'AUDIT_EVENT_REQUIRED','retry_or_recovery':'IDEMPOTENT_RETRY_OR_MANUAL_RECOVERY','test_contract':'TEST-DEMO-RUNTIME-001'}
    norm_hash=inst.effective_normative_set_hash(list(idx['mandatory_common_normative_bundles'].keys()),ref['stage_reference_rules'][pa['producer_stage_uid']]['exact_required_normative_section_uids'],pa['required_normative_section_uids'])
    pa['governance_load_receipt_ref']=inst.expected_receipt_uid(pa['work_unit_uid'],rm['governance_revision'],norm_hash)
    pa['write_target_binding_ref']=inst.expected_binding_uid(pa['program_artifact_uid'],pa['work_unit_uid'],pa['canonical_path'],pa['current_hash'])
    manifest={
      'work_unit_uid':pa['work_unit_uid'],'governance_revision':rm['governance_revision'],'design_freeze_ref':'DF-DEMO-PAGE-001','program_artifacts':[pa['program_artifact_uid']],
      'dependency_closure_ref':'DEP-CLOSURE-001','acceptance_audit_blueprint_ref':pa['acceptance_audit_blueprint_ref'],'naming_registry_ref':'REG-NAMING-001',
      'section_registry_ref':'REG-NORMATIVE-SECTION-001','protected_current_artifact_registry_ref':'REG-PROTECTED-CURRENT-ARTIFACT-001','typed_identity_registry_ref':'REG-PROGRAM-IDENTITY-AUTHORITY-001',
      'common_normative_bundle_refs':list(idx['mandatory_common_normative_bundles'].keys()),
      'stage_normative_section_uids':ref['stage_reference_rules'][pa['producer_stage_uid']]['exact_required_normative_section_uids'],
      'item_specific_normative_section_uids':['WEB-GOV-02-S014'],'governance_load_receipt_ref':pa['governance_load_receipt_ref'],
      'governance_load_receipt':{'receipt_uid':pa['governance_load_receipt_ref'],'status':'PASS','work_unit_uid':pa['work_unit_uid'],'governance_revision':rm['governance_revision'],'semantic_baseline_content_hash':inst.SEMANTIC_BASELINE_CONTENT_HASH,'effective_normative_set_hash':norm_hash},
      'dependency_closure':{'closure_uid':'DEP-CLOSURE-001','program_artifact_uid':pa['program_artifact_uid'],'dependency_refs':[],'reverse_dependency_refs':[],'status':'PASS'},
      'write_target_bindings':[{'binding_uid':pa['write_target_binding_ref'],'program_artifact_uid':pa['program_artifact_uid'],'work_unit_uid':pa['work_unit_uid'],'page_uid_or_scope_uid':pa['page_uid_or_scope_uid'],
       'owner_uid':pa['owner_uid'],'construction_profile':pa['construction_profile'],'canonical_path':pa['canonical_path'],'canonical_filename':pa['canonical_filename'],
       'expected_current_hash':pa['current_hash'],'producer_stage_uid':pa['producer_stage_uid']}]
    }
    return pa,manifest
def inst_case(name,mut,expected='FAIL'):
    pa,man=valid_fixture(); mut(pa,man); out=inst.validate_instance(pa,man,PKG)
    return {'case':name,'expected':expected,'actual':out['status'],'ok':out['status']==expected,'failures':out.get('failures',[])[:4]}

# Five positive baselines: overall semantic authority plus focused invariant checks.
base=sem.validate(PKG); ref=load(PKG/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'); idx=load(PKG/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'); life=load(PKG/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'); naming=load(PKG/'10_REGISTRY/NAMING_REGISTRY.yaml')
pa,man=valid_fixture(); instbase=inst.validate_instance(pa,man,PKG)
positive=[
 {'case':'baseline_reference_semantics','expected':'PASS','actual':base['status'],'ok':base['status']=='PASS'},
 {'case':'baseline_profile_runtime_direct_clause','expected':'PASS','actual':'PASS' if 'WEB-GOV-02-S014' in idx['program_construction_profiles']['RUNTIME_SERVICE']['required_normative_section_uids'] else 'FAIL','ok':'WEB-GOV-02-S014' in idx['program_construction_profiles']['RUNTIME_SERVICE']['required_normative_section_uids']},
 {'case':'baseline_stage10_direct_dimensions','expected':'PASS','actual':'PASS' if {'WEB-GOV-02-S012','WEB-GOV-02-S016','WEB-GOV-02-S025'}.issubset(set(next(s for s in life['stages'] if s['stage_uid']=='STAGE-10')['required_normative_section_uids'])) else 'FAIL','ok':{'WEB-GOV-02-S012','WEB-GOV-02-S016','WEB-GOV-02-S025'}.issubset(set(next(s for s in life['stages'] if s['stage_uid']=='STAGE-10')['required_normative_section_uids']))},
 {'case':'baseline_naming_self_consistent','expected':'PASS','actual':'PASS' if all('code_name' in x and 'owner_file' in x and 'version' in x for x in naming['items']) else 'FAIL','ok':all('code_name' in x and 'owner_file' in x and 'version' in x for x in naming['items'])},
 {'case':'baseline_program_artifact_instance','expected':'PASS','actual':instbase['status'],'ok':instbase['status']=='PASS','failures':instbase.get('failures',[])[:4]},
]
neg=[]
# 1-15 semantic / naming / typed identity / single authority negatives
neg += [
 sem_case('profile_runtime_legal_wrong_ref',mutate_yaml('10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['program_construction_profiles']['RUNTIME_SERVICE'].__setitem__('required_normative_section_uids',['WEB-GOV-01-S002']))),
 sem_case('profile_repository_legal_wrong_ref',mutate_yaml('10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['program_construction_profiles']['REPOSITORY_DATA_ACCESS'].__setitem__('required_normative_section_uids',['WEB-GOV-04-S001']))),
 sem_case('profile_test_missing_test_layers',mutate_yaml('10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['program_construction_profiles']['TEST_IMPLEMENTATION'].__setitem__('required_normative_section_uids',['WEB-GOV-03-S046','WEB-GOV-04-S073']))),
 sem_case('stage10_legal_wrong_ref',mutate_yaml('10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:next(s for s in d['stages'] if s['stage_uid']=='STAGE-10').__setitem__('required_normative_section_uids',['WEB-GOV-01-S002']))),
 sem_case('naming_duplicate_canonical_name',mutate_yaml('10_REGISTRY/NAMING_REGISTRY.yaml',lambda d:d['items'][1].__setitem__('canonical_name',d['items'][0]['canonical_name']))),
 sem_case('naming_required_field_missing',mutate_yaml('10_REGISTRY/NAMING_REGISTRY.yaml',lambda d:d['items'][0].pop('owner_file'))),
 sem_case('naming_bad_canonical_name',mutate_yaml('10_REGISTRY/NAMING_REGISTRY.yaml',lambda d:d['items'][0].__setitem__('canonical_name','bad-name'))),
 sem_case('audit_unknown_validator_uid',mutate_yaml('10_REGISTRY/AUDIT_CATALOG.yaml',lambda d:d['items'][0].__setitem__('validator_uid','VAL-GOV-999'))),
 sem_case('audit_unknown_type_uid',mutate_yaml('10_REGISTRY/AUDIT_CATALOG.yaml',lambda d:d['items'][0].__setitem__('audit_type_uid','AUDTYPE-GOV-999'))),
 sem_case('review_unknown_type_uid',mutate_yaml('10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml',lambda d:d['required_review_plan'][0].__setitem__('review_type_uid','REVTYPE-GOV-999'))),
 sem_case('blueprint_unknown_type_uid',mutate_yaml('10_REGISTRY/BLUEPRINT_REGISTRY.yaml',lambda d:d['blueprint_types'][0].__setitem__('blueprint_type_uid','BPTYPE-GOV-999'))),
 sem_case('acceptance_second_audit_logic',mutate_yaml('10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml',lambda d:d.__setitem__('audit_items',[{'audit_item_uid':'SECOND-SYSTEM'}]))),
 sem_case('common_bundle_legal_wrong_ref',mutate_yaml('10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d:d['mandatory_common_normative_bundles']['BUNDLE-GOV-COMMON-CORE'].__setitem__('section_uids',['WEB-GOV-02-S014']))),
 sem_case('lifecycle_unknown_validator_uid',mutate_yaml('10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d:d['stages'][0]['validators'].__setitem__(0,'VAL-GOV-999'))),
 sem_case('reference_rule_profile_drift',mutate_yaml('10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml',lambda d:d['program_profile_reference_rules']['UI_COMPONENT'].__setitem__('exact_required_normative_section_uids',['WEB-GOV-01-S002']))),
]
# normative doc category mutation (case 16)
def wrong_doc_category(root):
    p=root/'12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md'; s=p.read_text(); s=s.replace('category: blueprint_design_governance','category: wrong_category',1); p.write_text(s)
neg.append(sem_case('normative_document_wrong_category',wrong_doc_category))
# 17-23 independent Program Artifact Instance negatives
neg += [
 inst_case('artifact_unsafe_path',lambda p,m:(p.__setitem__('canonical_path','../outside/evil.ts'),m['write_target_bindings'][0].__setitem__('canonical_path','../outside/evil.ts'))),
 inst_case('artifact_unknown_profile',lambda p,m:(p.__setitem__('construction_profile','UNKNOWN_PROFILE'),m['write_target_bindings'][0].__setitem__('construction_profile','UNKNOWN_PROFILE'))),
 inst_case('artifact_unknown_stage',lambda p,m:(p.__setitem__('producer_stage_uid','STAGE-99'),m['write_target_bindings'][0].__setitem__('producer_stage_uid','STAGE-99'),m.__setitem__('stage_normative_section_uids',[]))),
 inst_case('artifact_unknown_blueprint',lambda p,m:(p.__setitem__('acceptance_audit_blueprint_ref','BP-UNKNOWN'),m.__setitem__('acceptance_audit_blueprint_ref','BP-UNKNOWN'))),
 inst_case('artifact_bad_hash',lambda p,m:(p.__setitem__('current_hash','bad-hash'),m['write_target_bindings'][0].__setitem__('expected_current_hash','bad-hash'))),
 inst_case('artifact_basename_mismatch',lambda p,m:p.__setitem__('canonical_filename','other.ts')),
 inst_case('artifact_bad_canonical_name',lambda p,m:p.__setitem__('canonical_name','core-runtime-service')),
]
semantic_results=positive+neg

# Exact fuzz counts from the historical audit: 9 + 11 + 10 + 12 + 4 = 46.
fuzz=[]
profiles=list(idx['program_construction_profiles'])
for name in profiles:
    fuzz.append(sem_case('fuzz_profile_wrong_semantic_'+name,mutate_yaml('10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',lambda d,n=name:d['program_construction_profiles'][n].__setitem__('required_normative_section_uids',['WEB-GOV-01-S002']))))
stage_ids=[s['stage_uid'] for s in life['stages']]
for sid in stage_ids:
    fuzz.append(sem_case('fuzz_stage_wrong_semantic_'+sid,mutate_yaml('10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',lambda d,sid=sid:next(s for s in d['stages'] if s['stage_uid']==sid).__setitem__('required_normative_section_uids',['WEB-GOV-01-S002']))))
for i in range(1,11):
    fuzz.append(sem_case('fuzz_naming_duplicate_'+str(i),mutate_yaml('10_REGISTRY/NAMING_REGISTRY.yaml',lambda d,i=i:d['items'][i].__setitem__('canonical_name',d['items'][0]['canonical_name']))))
for i in range(12):
    fuzz.append(sem_case('fuzz_audit_unknown_validator_'+str(i),mutate_yaml('10_REGISTRY/AUDIT_CATALOG.yaml',lambda d,i=i:d['items'][i].__setitem__('validator_uid','VAL-GOV-999'))))
for docname,oldcat in [('01_BLUEPRINT_DESIGN_GOVERNANCE.md','blueprint_design_governance'),('02_IMPLEMENTATION_DELIVERY_STANDARD.md','implementation_delivery'),('03_EXECUTION_CONTROL_STANDARD.md','execution_control'),('04_AUDIT_PROGRESS_STANDARD.md','audit_progress_reporting')]:
    def mk(docname=docname,oldcat=oldcat):
        def m(root):
            p=root/'12_DOCS/mother-spec'/docname; s=p.read_text(); s=s.replace('category: '+oldcat,'category: wrong_category',1); p.write_text(s)
        return m
    fuzz.append(sem_case('fuzz_normative_category_'+docname,mk()))

out={
 'suite':'reference semantic / typed identity / artifact instance multidirection stress',
 'semantic_cases_total':len(semantic_results),'semantic_passed_expectations':sum(x['ok'] for x in semantic_results),
 'positive_baselines':len(positive),'negative_cases':len(neg),'negative_cases_blocked':sum(x['ok'] for x in neg),
 'fuzz_total':len(fuzz),'fuzz_blocked':sum(x['ok'] for x in fuzz),'escaped':sum(not x['ok'] for x in fuzz),
 'fuzz_breakdown':{'profile':9,'stage':11,'naming_duplicate':10,'audit_validator_uid':12,'normative_document_category':4},
 'semantic_results':semantic_results,'fuzz_results':fuzz
}
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['semantic_passed_expectations']==len(semantic_results) and out['fuzz_blocked']==len(fuzz) else 1)
