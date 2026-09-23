#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
import sys as _governance_runner_sys
if __name__ != "__main__" and "pytest" in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip("standalone governance regression executable; use registered subprocess runner", allow_module_level=True)
from pathlib import Path
import importlib.util,json,shutil,tempfile,yaml,sys,hashlib,subprocess,os
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent; PKG=HERE.parents[1]

def imp(name):
    spec=importlib.util.spec_from_file_location(name,HERE/f'{name}.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
sem=imp('validate_reference_semantics'); inst=imp('program_artifact_instance_guard'); clean=imp('validate_cleanup_protection'); gov=imp('validate_governance')
def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def dump(p,d): Path(p).write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def checksums(root):
    rows=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(root).as_posix()
        if rel=='CHECKSUMS.sha256' or '__pycache__' in p.parts or p.suffix in {'.pyc','.pyo'}: continue
        rows.append(f'{sha(p)}  ./{rel}')
    (root/'CHECKSUMS.sha256').write_text('\n'.join(rows)+'\n',encoding='utf-8')
def official_refresh(root):
    env=dict(os.environ); env['PYTHONDONTWRITEBYTECODE']='1'; env['PYTHONPYCACHEPREFIX']='/tmp/acpos-no-pycache'
    govdir=root/'09_TESTS/governance'
    for script in ['compile_governance_baseline.py','refresh_governance_root_manifest.py']:
        cp=subprocess.run([sys.executable,str(govdir/script)],cwd=str(govdir),env=env,capture_output=True,text=True,timeout=45)
        if cp.returncode!=0: return False,script+':'+cp.stderr[-500:]
    checksums(root); return True,''
def case(name,ok,details=None): return {'case':name,'ok':bool(ok),'details':details or {}}

def joint_mutations(root):
    ref=load(root/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'); idx=load(root/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'); life=load(root/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml')
    wrong=['WEB-GOV-01-S002']
    ref['program_profile_reference_rules']['RUNTIME_SERVICE']['exact_required_normative_section_uids']=wrong; idx['program_construction_profiles']['RUNTIME_SERVICE']['required_normative_section_uids']=wrong
    ref['stage_reference_rules']['STAGE-10']['exact_required_normative_section_uids']=wrong; next(x for x in life['stages'] if x['stage_uid']=='STAGE-10')['required_normative_section_uids']=wrong
    ref['common_bundle_reference_rules']['BUNDLE-GOV-COMMON-CORE']['exact_section_uids']=['WEB-GOV-02-S014']; idx['mandatory_common_normative_bundles']['BUNDLE-GOV-COMMON-CORE']['section_uids']=['WEB-GOV-02-S014']
    dump(root/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml',ref); dump(root/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',idx); dump(root/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',life)
def typed_mutations(root):
    ref=load(root/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'); cat=load(root/'10_REGISTRY/AUDIT_CATALOG.yaml'); rev=load(root/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml'); bpr=load(root/'10_REGISTRY/BLUEPRINT_REGISTRY.yaml'); naming=load(root/'10_REGISTRY/NAMING_REGISTRY.yaml')
    ref['validator_identities'][1]['canonical_name']='WRONG_CLEANUP_GUARD'; ref['validator_identities'][1]['allowed_usage']=ref['validator_identities'][1]['allowed_usage']+['WRONG_USAGE']; next(x for x in cat['items'] if x['validator_uid']=='VAL-GOV-002')['validator_name']='WRONG_CLEANUP_GUARD'
    ref['audit_type_identities'][0]['canonical_name']='WRONG_AUDIT_TYPE'; cat['items'][0]['audit_type']='WRONG_AUDIT_TYPE'; cat['items'][0]['stage_uid']='STAGE-99'
    ref['review_type_identities'][0]['canonical_name']='WRONG_REVIEW'; rev['required_review_plan'][0]['review_type']='WRONG_REVIEW'
    ref['blueprint_type_identities'][0]['canonical_name']='WRONG_BLUEPRINT'; bpr['blueprint_types'][0]['blueprint_type']='WRONG_BLUEPRINT'
    ref['normative_document_rules'][0]['expected_category']='wrong_category'; p=root/'12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md'; p.write_text(p.read_text().replace('category: blueprint_design_governance','category: wrong_category',1))
    ref['naming_registry_contract']['governance_fixed_filename_exception_authority']='WEB-GOV-01-S002'; [x.__setitem__('filename_exception_authority','WEB-GOV-01-S002') for x in naming['items'] if x.get('filename_policy')=='REGISTERED_GOVERNANCE_FIXED_NAME']
    dump(root/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml',ref); dump(root/'10_REGISTRY/AUDIT_CATALOG.yaml',cat); dump(root/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml',rev); dump(root/'10_REGISTRY/BLUEPRINT_REGISTRY.yaml',bpr); dump(root/'10_REGISTRY/NAMING_REGISTRY.yaml',naming)

def valid_fixture(root=PKG):
    idx=load(root/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'); ref=load(root/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'); rm=load(root/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml')
    pa={'program_artifact_uid':'PA-DEMO-PAGE-RUNTIME-001','work_unit_uid':'WU-DEMO-PAGE-001','page_uid_or_scope_uid':'DEMO-PAGE-001','construction_profile':'RUNTIME_SERVICE','canonical_name':'EXAMPLE_RUNTIME_SERVICE','canonical_path':'src/example/DEMO-PAGE-001/runtime-service.ts','canonical_filename':'runtime-service.ts','owner_uid':'OWNER-DEMO-RUNTIME','producer_stage_uid':'STAGE-05','input_artifact_refs':[],'required_normative_section_uids':['WEB-GOV-02-S014'],'dependency_refs':[],'reverse_dependency_refs':[],'acceptance_audit_blueprint_ref':'BP-GOVERNANCE-ACCEPTANCE-001','required_test_refs':['TEST-DEMO-RUNTIME-001'],'current_hash':'0'*64,'status':'PLANNED'}
    pa['profile_contracts']={'input_contract':'CoreRuntimeInputV1','output_contract':'CoreRuntimeOutputV1','state_mutation_contract':'GOVERNED_MUTATION_ONLY','error_contract':'FAIL_CLOSED_ERROR_CONTRACT','audit_contract':'AUDIT_EVENT_REQUIRED','retry_or_recovery':'IDEMPOTENT_RETRY_OR_MANUAL_RECOVERY','test_contract':'TEST-DEMO-RUNTIME-001'}
    bundles=list(idx['mandatory_common_normative_bundles'].keys()); stage=ref['stage_reference_rules'][pa['producer_stage_uid']]['exact_required_normative_section_uids']; norm=inst.effective_normative_set_hash(bundles,stage,pa['required_normative_section_uids'])
    pa['governance_load_receipt_ref']=inst.expected_receipt_uid(pa['work_unit_uid'],rm['governance_revision'],norm); pa['write_target_binding_ref']=inst.expected_binding_uid(pa['program_artifact_uid'],pa['work_unit_uid'],pa['canonical_path'],pa['current_hash'])
    man={'work_unit_uid':pa['work_unit_uid'],'governance_revision':rm['governance_revision'],'design_freeze_ref':'DF-DEMO-PAGE-001','program_artifacts':[pa['program_artifact_uid']],'dependency_closure_ref':'DEP-CLOSURE-001','acceptance_audit_blueprint_ref':pa['acceptance_audit_blueprint_ref'],'naming_registry_ref':'REG-NAMING-001','section_registry_ref':'REG-NORMATIVE-SECTION-001','protected_current_artifact_registry_ref':'REG-PROTECTED-CURRENT-ARTIFACT-001','typed_identity_registry_ref':'REG-PROGRAM-IDENTITY-AUTHORITY-001','common_normative_bundle_refs':bundles,'stage_normative_section_uids':stage,'item_specific_normative_section_uids':list(pa['required_normative_section_uids']),'governance_load_receipt_ref':pa['governance_load_receipt_ref'],'governance_load_receipt':{'receipt_uid':pa['governance_load_receipt_ref'],'status':'PASS','work_unit_uid':pa['work_unit_uid'],'governance_revision':rm['governance_revision'],'semantic_baseline_content_hash':inst.SEMANTIC_BASELINE_CONTENT_HASH,'effective_normative_set_hash':norm},'dependency_closure':{'closure_uid':'DEP-CLOSURE-001','program_artifact_uid':pa['program_artifact_uid'],'dependency_refs':[],'reverse_dependency_refs':[],'status':'PASS'},'write_target_bindings':[{'binding_uid':pa['write_target_binding_ref'],'program_artifact_uid':pa['program_artifact_uid'],'work_unit_uid':pa['work_unit_uid'],'page_uid_or_scope_uid':pa['page_uid_or_scope_uid'],'owner_uid':pa['owner_uid'],'construction_profile':pa['construction_profile'],'canonical_path':pa['canonical_path'],'canonical_filename':pa['canonical_filename'],'expected_current_hash':pa['current_hash'],'producer_stage_uid':pa['producer_stage_uid']} ]}
    return pa,man
def refresh_fixture(pa,man):
    rm=load(PKG/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'); norm=inst.effective_normative_set_hash(man.get('common_normative_bundle_refs'),man.get('stage_normative_section_uids'),man.get('item_specific_normative_section_uids'))
    rid=inst.expected_receipt_uid(pa.get('work_unit_uid'),rm['governance_revision'],norm); bid=inst.expected_binding_uid(pa.get('program_artifact_uid'),pa.get('work_unit_uid'),pa.get('canonical_path'),pa.get('current_hash'))
    pa['governance_load_receipt_ref']=rid; man['governance_load_receipt_ref']=rid; man['governance_load_receipt']={'receipt_uid':rid,'status':'PASS','work_unit_uid':pa.get('work_unit_uid'),'governance_revision':rm['governance_revision'],'semantic_baseline_content_hash':inst.SEMANTIC_BASELINE_CONTENT_HASH,'effective_normative_set_hash':norm}; pa['write_target_binding_ref']=bid
    if man.get('write_target_bindings'):
        b=man['write_target_bindings'][0]; b.update({'binding_uid':bid,'work_unit_uid':pa.get('work_unit_uid'),'page_uid_or_scope_uid':pa.get('page_uid_or_scope_uid'),'canonical_path':pa.get('canonical_path'),'canonical_filename':pa.get('canonical_filename'),'expected_current_hash':pa.get('current_hash')})
def inst_check(name,mut):
    pa,man=valid_fixture(); mut(pa,man); out=inst.validate_instance(pa,man,PKG); return case(name,out['status']=='FAIL',{'failures':out.get('failures',[])[:8]})

results=[]
base=sem.validate(PKG); results.append(case('baseline_semantic_anchor',base['status']=='PASS',{'failures':base.get('failures',[])[:3]}))
with tempfile.TemporaryDirectory() as td:
    r=Path(td)/'pkg'; shutil.copytree(PKG,r); joint_mutations(r); out=sem.validate(r); fails=out.get('failures',[])
    required=['reference_rule_registry_drift_from_immutable_baseline:program_profile_reference_rules','reference_rule_registry_drift_from_immutable_baseline:stage_reference_rules','reference_rule_registry_drift_from_immutable_baseline:common_bundle_reference_rules']
    results.append(case('joint_authority_consumer_mutations_blocked',out['status']=='FAIL' and all(x in fails for x in required),{'failures':fails[:10]}))
with tempfile.TemporaryDirectory() as td:
    r=Path(td)/'pkg'; shutil.copytree(PKG,r); joint_mutations(r); ok,why=official_refresh(r)
    if not ok: results.append(case('joint_mutation_full_official_resign_blocked',True,{'refresh_blocked':why}))
    else:
        old_child=os.environ.get('WEB_GOVERNANCE_PREFORMAL_SUITE_CHILD'); os.environ['WEB_GOVERNANCE_PREFORMAL_SUITE_CHILD']='1'
        try: out=gov.preformal(r)
        finally:
            if old_child is None: os.environ.pop('WEB_GOVERNANCE_PREFORMAL_SUITE_CHILD',None)
            else: os.environ['WEB_GOVERNANCE_PREFORMAL_SUITE_CHILD']=old_child
        results.append(case('joint_mutation_full_official_resign_blocked',out['status']=='FAIL' and any(x['check_id']=='reference_semantics' and x['status']=='FAIL' for x in out['checks']),{'failed_checks':[x['check_id'] for x in out['checks'] if x['status']!='PASS']}))
with tempfile.TemporaryDirectory() as td:
    r=Path(td)/'pkg'; shutil.copytree(PKG,r); typed_mutations(r); out=sem.validate(r); fails=out.get('failures',[])
    keys=['validator_identities','audit_type_identities','review_type_identities','blueprint_type_identities','normative_document_rules','naming_registry_contract']
    results.append(case('typed_identity_joint_mutations_blocked',out['status']=='FAIL' and all('reference_rule_registry_drift_from_immutable_baseline:'+k in fails for k in keys) and any(x.startswith('audit_type_stage_usage_invalid:') for x in fails),{'failures':fails[:15]}))

results += [
 inst_check('instance_empty_work_unit',lambda p,m:(p.__setitem__('work_unit_uid',''),m.__setitem__('work_unit_uid',''),refresh_fixture(p,m))),
 inst_check('instance_empty_scope',lambda p,m:(p.__setitem__('page_uid_or_scope_uid',''),m['write_target_bindings'][0].__setitem__('page_uid_or_scope_uid',''),refresh_fixture(p,m))),
 inst_check('instance_wrong_item_specific_joint',lambda p,m:(p.__setitem__('required_normative_section_uids',['WEB-GOV-02-S011']),m.__setitem__('item_specific_normative_section_uids',['WEB-GOV-02-S011']),refresh_fixture(p,m))),
 inst_check('instance_fake_receipt_uid',lambda p,m:(p.__setitem__('governance_load_receipt_ref','GLR-FAKE'),m.__setitem__('governance_load_receipt_ref','GLR-FAKE'),m['governance_load_receipt'].__setitem__('receipt_uid','GLR-FAKE'))),
 inst_check('instance_fake_binding_uid',lambda p,m:(p.__setitem__('write_target_binding_ref','WTB-FAKE'),m['write_target_bindings'][0].__setitem__('binding_uid','WTB-FAKE'))),
 inst_check('manifest_missing_design_freeze',lambda p,m:m.pop('design_freeze_ref')),
 inst_check('manifest_missing_dependency_closure_ref',lambda p,m:m.pop('dependency_closure_ref')),
 inst_check('manifest_missing_item_specific_refs',lambda p,m:m.pop('item_specific_normative_section_uids')),
 inst_check('manifest_missing_governance_receipt_ref',lambda p,m:m.pop('governance_load_receipt_ref')),
 inst_check('dependency_closure_not_bound',lambda p,m:p.__setitem__('dependency_refs',['PA-OTHER-001'])),
 inst_check('current_missing_physical_file',lambda p,m:(p.__setitem__('status','CURRENT'),p.__setitem__('canonical_path','src/missing/missing.ts'),p.__setitem__('canonical_filename','missing.ts'),p.__setitem__('current_hash','1'*64),refresh_fixture(p,m))),
]

results.append(case('cleanup_string_only_proofs_blocked',clean.validate(PKG,[{'path':'scratch.tmp','proofs':clean.REQUIRED_PROOF}])['status']=='FAIL'))
fullfake={k:{'recomputed':True} for k in clean.REQUIRED_PROOF}; fullfake['REPLACEMENT_VALID_IF_SUPERSEDED']={'not_applicable':True}; fullfake['CLEANUP_LEDGER_ENTRY']={'event_uid':'FAKE'}; fullfake['POST_DELETE_RESIDUAL_SCAN']={'required_after_delete':True,'validator':'validate_cleanup_protection.py'}
for target in ['09_TESTS/governance/test_v2_1_0_regressions.py','09_TESTS/governance/test_v2_1_0_post_v1_8_regressions.py','CHECKSUMS.sha256']:
    results.append(case('cleanup_protected_'+Path(target).name,clean.validate(PKG,[{'path':target,'proof_evidence':fullfake}])['status']=='FAIL'))
with tempfile.TemporaryDirectory() as td:
    r=Path(td)/'pkg'; shutil.copytree(PKG,r); target='scratch/'+'delete-me.txt'; (r/target).parent.mkdir(parents=True,exist_ok=True); (r/target).write_text('temporary')
    led=load(r/'11_EVIDENCE/audit/CLEANUP_LEDGER.yaml'); led['events'].append({'event_uid':'CLEANUP-TEST-VALID-001','event_type':'DELETE_NON_CURRENT_TEMPORARY_ARTIFACT','target_path':target,'result':'PRE_DELETE_PROOFS_RECORDED'}); dump(r/'11_EVIDENCE/audit/CLEANUP_LEDGER.yaml',led)
    ev={'NOT_PROTECTED_CURRENT':{'recomputed':True},'NOT_IMMUTABLE_RAW_SOURCE':{'recomputed':True},'ZERO_CURRENT_OWNER_REFERENCE':{'recomputed':True},'ZERO_UNMIGRATED_REVERSE_DEPENDENCY':{'recomputed':True},'REPLACEMENT_VALID_IF_SUPERSEDED':{'not_applicable':True},'CLEANUP_LEDGER_ENTRY':{'event_uid':'CLEANUP-TEST-VALID-001'},'POST_DELETE_RESIDUAL_SCAN':{'required_after_delete':True,'validator':'validate_cleanup_protection.py'}}
    results.append(case('cleanup_evidence_backed_valid_authorization',clean.validate(r,[{'path':target,'proof_evidence':ev}])['status']=='PASS'))

for target in ['10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml','09_TESTS/governance/validate_reference_semantics.py','09_TESTS/governance/test_v2_1_0_regressions.py','11_EVIDENCE/audit/HIGH_PRESSURE_HARDENING_RESULT.yaml']:
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)/'pkg'; shutil.copytree(PKG,r); d=load(r/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml')
        for g in ['current_artifacts','validators']: d[g]=[x for x in d[g] if x.get('path')!=target]
        dump(r/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml',d); out=gov.root_manifest_guard(r)
        results.append(case('root_manifest_omission_'+Path(target).name,out['status']=='FAIL',{'failures':out.get('failures',[])[:2]}))

with tempfile.TemporaryDirectory() as td:
    r=Path(td)/'pkg'; shutil.copytree(PKG,r); govdir=r/'09_TESTS/governance'; [shutil.rmtree(p,ignore_errors=True) for p in govdir.rglob('__pycache__')]
    cp=subprocess.run([sys.executable,str(govdir/'compile_governance_baseline.py')],cwd=str(govdir),capture_output=True,text=True,timeout=45); garbage=list(govdir.rglob('*.pyc'))+list(govdir.rglob('__pycache__'))
    results.append(case('compiler_no_package_bytecode_pollution',cp.returncode==0 and not garbage,{'garbage':[str(x.relative_to(r)) for x in garbage]}))

out={'suite':'v2.1.8 high pressure hardening regression','total':len(results),'passed_expectations':sum(x['ok'] for x in results),'results':results}
print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['passed_expectations']==out['total'] else 1)
