#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
import sys as _governance_runner_sys
if __name__ != "__main__" and "pytest" in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip("standalone governance regression executable; use registered subprocess runner", allow_module_level=True)
from pathlib import Path
import importlib.util, json, shutil, tempfile, yaml, os, sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent; PKG=HERE.parents[1]

def imp(name):
    spec=importlib.util.spec_from_file_location(name,HERE/f'{name}.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
sec=imp('validate_section_registry'); inst=imp('program_artifact_instance_guard'); clean=imp('validate_cleanup_protection'); gov=imp('validate_governance'); life=imp('governance_lifecycle_stage_contract_guard')
def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def dump(p,d): Path(p).write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def case(name,ok,details=None): return {'case':name,'ok':bool(ok),'details':details or {}}

def fixture():
    idx=load(PKG/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'); ref=load(PKG/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'); rm=load(PKG/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml')
    pa={'program_artifact_uid':'PA-DEMO-PAGE-RUNTIME-001','work_unit_uid':'WU-DEMO-PAGE-001','page_uid_or_scope_uid':'DEMO-PAGE-001','construction_profile':'RUNTIME_SERVICE','canonical_name':'EXAMPLE_RUNTIME_SERVICE','canonical_path':'src/example/DEMO-PAGE-001/runtime-service.ts','canonical_filename':'runtime-service.ts','owner_uid':'OWNER-DEMO-RUNTIME','producer_stage_uid':'STAGE-05','input_artifact_refs':[],'required_normative_section_uids':['WEB-GOV-02-S014'],'dependency_refs':[],'reverse_dependency_refs':[],'acceptance_audit_blueprint_ref':'BP-GOVERNANCE-ACCEPTANCE-001','required_test_refs':['TEST-DEMO-RUNTIME-001'],'current_hash':'0'*64,'status':'PLANNED','profile_contracts':{'input_contract':'CoreRuntimeInputV1','output_contract':'CoreRuntimeOutputV1','state_mutation_contract':'GOVERNED_MUTATION_ONLY','error_contract':'FAIL_CLOSED_ERROR_CONTRACT','audit_contract':'AUDIT_EVENT_REQUIRED','retry_or_recovery':'IDEMPOTENT_RETRY_OR_MANUAL_RECOVERY','test_contract':'TEST-DEMO-RUNTIME-001'}}
    bundles=list(idx['mandatory_common_normative_bundles'].keys()); stage=ref['stage_reference_rules'][pa['producer_stage_uid']]['exact_required_normative_section_uids']; norm=inst.effective_normative_set_hash(bundles,stage,pa['required_normative_section_uids'])
    pa['governance_load_receipt_ref']=inst.expected_receipt_uid(pa['work_unit_uid'],rm['governance_revision'],norm); pa['write_target_binding_ref']=inst.expected_binding_uid(pa['program_artifact_uid'],pa['work_unit_uid'],pa['canonical_path'],pa['current_hash'])
    man={'work_unit_uid':pa['work_unit_uid'],'governance_revision':rm['governance_revision'],'design_freeze_ref':'DF-DEMO-PAGE-001','program_artifacts':[pa['program_artifact_uid']],'dependency_closure_ref':'DEP-CLOSURE-001','acceptance_audit_blueprint_ref':pa['acceptance_audit_blueprint_ref'],'naming_registry_ref':'REG-NAMING-001','section_registry_ref':'REG-NORMATIVE-SECTION-001','protected_current_artifact_registry_ref':'REG-PROTECTED-CURRENT-ARTIFACT-001','typed_identity_registry_ref':'REG-PROGRAM-IDENTITY-AUTHORITY-001','common_normative_bundle_refs':bundles,'stage_normative_section_uids':stage,'item_specific_normative_section_uids':list(pa['required_normative_section_uids']),'governance_load_receipt_ref':pa['governance_load_receipt_ref'],'governance_load_receipt':{'receipt_uid':pa['governance_load_receipt_ref'],'status':'PASS','work_unit_uid':pa['work_unit_uid'],'governance_revision':rm['governance_revision'],'semantic_baseline_content_hash':inst.SEMANTIC_BASELINE_CONTENT_HASH,'effective_normative_set_hash':norm},'dependency_closure':{'closure_uid':'DEP-CLOSURE-001','program_artifact_uid':pa['program_artifact_uid'],'dependency_refs':[],'reverse_dependency_refs':[],'status':'PASS'},'write_target_bindings':[{'binding_uid':pa['write_target_binding_ref'],'program_artifact_uid':pa['program_artifact_uid'],'work_unit_uid':pa['work_unit_uid'],'page_uid_or_scope_uid':pa['page_uid_or_scope_uid'],'owner_uid':pa['owner_uid'],'construction_profile':pa['construction_profile'],'canonical_path':pa['canonical_path'],'canonical_filename':pa['canonical_filename'],'expected_current_hash':pa['current_hash'],'producer_stage_uid':pa['producer_stage_uid']}]}
    return pa,man

def refresh(pa,man):
    rm=load(PKG/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'); ref=load(PKG/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml')
    man['stage_normative_section_uids']=ref['stage_reference_rules'][pa['producer_stage_uid']]['exact_required_normative_section_uids']; man['item_specific_normative_section_uids']=list(pa['required_normative_section_uids'])
    norm=inst.effective_normative_set_hash(man['common_normative_bundle_refs'],man['stage_normative_section_uids'],man['item_specific_normative_section_uids'])
    rid=inst.expected_receipt_uid(pa['work_unit_uid'],rm['governance_revision'],norm); pa['governance_load_receipt_ref']=rid; man['governance_load_receipt_ref']=rid; man['governance_load_receipt']={'receipt_uid':rid,'status':'PASS','work_unit_uid':pa['work_unit_uid'],'governance_revision':rm['governance_revision'],'semantic_baseline_content_hash':inst.SEMANTIC_BASELINE_CONTENT_HASH,'effective_normative_set_hash':norm}
    bid=inst.expected_binding_uid(pa['program_artifact_uid'],pa['work_unit_uid'],pa['canonical_path'],pa['current_hash']); pa['write_target_binding_ref']=bid
    b=man['write_target_bindings'][0]; b.update({'binding_uid':bid,'program_artifact_uid':pa['program_artifact_uid'],'work_unit_uid':pa['work_unit_uid'],'page_uid_or_scope_uid':pa['page_uid_or_scope_uid'],'owner_uid':pa['owner_uid'],'construction_profile':pa['construction_profile'],'canonical_path':pa['canonical_path'],'canonical_filename':pa['canonical_filename'],'expected_current_hash':pa['current_hash'],'producer_stage_uid':pa['producer_stage_uid']})
    man['dependency_closure']['program_artifact_uid']=pa['program_artifact_uid']; man['dependency_closure']['dependency_refs']=list(pa['dependency_refs']); man['dependency_closure']['reverse_dependency_refs']=list(pa['reverse_dependency_refs'])

def inst_mut(name,mut):
    pa,man=fixture(); mut(pa,man); refresh(pa,man); out=inst.validate_instance(pa,man,PKG); return case(name,out['status']=='FAIL',{'failures':out.get('failures',[])[:8]})

results=[]
base_sec=sec.validate(PKG); results.append(case('baseline_section_exact_binding',base_sec['status']=='PASS',{'failures':base_sec.get('failures',[])[:3]}))
with tempfile.TemporaryDirectory() as td:
    r=Path(td)/'pkg'; shutil.copytree(PKG,r); p=r/'12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md'; p.write_text(p.read_text(encoding='utf-8')+'\n<!-- SECTION_UID: WEB-GOV-01-S001 -->\n',encoding='utf-8'); out=sec.validate(r); results.append(case('duplicate_section_anchor_blocked',out['status']=='FAIL',{'failures':out.get('failures',[])[:4]}))
with tempfile.TemporaryDirectory() as td:
    r=Path(td)/'pkg'; shutil.copytree(PKG,r); p=r/'12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md'; s=p.read_text(encoding='utf-8'); a='<!-- SECTION_UID: WEB-GOV-01-S001 -->'; b='<!-- SECTION_UID: WEB-GOV-01-S002 -->'; s=s.replace(a,'<!-- TMP_SWAP -->',1).replace(b,a,1).replace('<!-- TMP_SWAP -->',b,1); p.write_text(s,encoding='utf-8'); out=sec.validate(r); results.append(case('section_anchor_swap_blocked',out['status']=='FAIL',{'failures':out.get('failures',[])[:4]}))
pa,man=fixture(); out=inst.validate_instance(pa,man,PKG); results.append(case('baseline_program_artifact_instance',out['status']=='PASS',{'failures':out.get('failures',[])[:6]}))
results += [
 inst_mut('mandatory_profile_contract_missing',lambda p,m:p['profile_contracts'].pop('audit_contract')),
 inst_mut('unresolved_dependency_blocked',lambda p,m:p.__setitem__('dependency_refs',['PA-DOES-NOT-EXIST-999'])),
 inst_mut('unresolved_reverse_dependency_blocked',lambda p,m:p.__setitem__('reverse_dependency_refs',['PA-DOES-NOT-EXIST-999'])),
 inst_mut('unresolved_input_artifact_blocked',lambda p,m:p.__setitem__('input_artifact_refs',['ARTIFACT-DOES-NOT-EXIST'])),
 inst_mut('unresolved_test_blocked',lambda p,m:p.__setitem__('required_test_refs',['TEST-DOES-NOT-EXIST'])),
 inst_mut('unresolved_owner_blocked',lambda p,m:p.__setitem__('owner_uid','OWNER-NOT-REGISTERED')),
 inst_mut('unresolved_scope_blocked',lambda p,m:p.__setitem__('page_uid_or_scope_uid','FAKE-SCOPE-999')),
]
pa,man=fixture(); man['program_artifacts']=[pa['program_artifact_uid'],pa['program_artifact_uid']]; out=inst.validate_instance(pa,man,PKG); results.append(case('duplicate_manifest_program_artifact_blocked',out['status']=='FAIL',{'failures':out.get('failures',[])[:5]}))
results.append(inst_mut('framework_reserved_filename_wrong_preregistration_blocked',lambda p,m:(p.__setitem__('canonical_path','src/random/page.tsx'),p.__setitem__('canonical_filename','page.tsx'))))
results.append(inst_mut('runtime_config_file_class_blocked',lambda p,m:(p.__setitem__('canonical_path','src/package.json'),p.__setitem__('canonical_filename','package.json'))))
with tempfile.TemporaryDirectory() as td:
    r=Path(td)/'pkg'; shutil.copytree(PKG,r); target='scratch/bugfix-delete-target.txt'; tp=r/target; tp.parent.mkdir(parents=True,exist_ok=True); tp.write_text('x',encoding='utf-8'); led=load(r/'11_EVIDENCE/audit/CLEANUP_LEDGER.yaml'); led['events'].append({'event_uid':'CLEANUP-BUGFIX-FAIL-001','event_type':'DELETE_NON_CURRENT_TEMPORARY_ARTIFACT','target_path':target,'delete_state':'CLOSED','delete_executed':True,'post_delete_residual_scan':{'status':'FAIL','validator':'validate_cleanup_protection.py','residual_reference_count':1,'target_absent':True},'result':'POST_DELETE_RESIDUAL_SCAN_FAIL'}); dump(r/'11_EVIDENCE/audit/CLEANUP_LEDGER.yaml',led); tp.unlink(); (r/'scratch/residual.txt').write_text('ref '+target,encoding='utf-8'); out=clean.validate(r); results.append(case('cleanup_post_delete_fail_blocks_prefomal_guard',out['status']=='FAIL',{'failures':out.get('failures',[])[:6]}))
life_base=life.validate(PKG); results.append(case('cross_lifecycle_semantic_granularity_baseline',life_base['status']=='PASS',{'failures':life_base.get('failures',[])[:6]}))
for sid in [f'STAGE-{i:02d}' for i in range(1,12)]:
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)/'pkg'; shutil.copytree(PKG,r); lp=r/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'; ld=load(lp); st=next(x for x in ld['stages'] if x['stage_uid']==sid); st.pop('semantic_granularity_gate',None); dump(lp,ld); out=life.validate(r); results.append(case('semantic_granularity_gate_required_'+sid,out['status']=='FAIL',{'failures':out.get('failures',[])[:5]}))
with tempfile.TemporaryDirectory() as td:
    r=Path(td)/'pkg'; shutil.copytree(PKG,r); lp=r/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'; ld=load(lp); ld['cross_stage_invariants']['semantic_granularity']['mixed_terminal_unit']='ALLOW'; dump(lp,ld); out=life.validate(r); results.append(case('mixed_terminal_unit_must_fail_closed_all_stages',out['status']=='FAIL',{'failures':out.get('failures',[])[:5]}))
with tempfile.TemporaryDirectory() as td:
    r=Path(td)/'pkg'; shutil.copytree(PKG,r); ip=r/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'; idx=load(ip); idx['mandatory_common_normative_bundles']['BUNDLE-GOV-COMMON-CORE']['section_uids'].remove('WEB-GOV-03-S052'); dump(ip,idx); out=life.validate(r); results.append(case('semantic_granularity_rule_must_load_in_common_bundle',out['status']=='FAIL',{'failures':out.get('failures',[])[:5]}))

trust_base=gov.external_trust_anchor_guard(PKG)
with tempfile.TemporaryDirectory() as td:
    r=Path(td)/'pkg'; shutil.copytree(PKG,r); (r/'README.md').write_text((r/'README.md').read_text(encoding='utf-8')+'\nTAMPER\n',encoding='utf-8'); tout=gov.external_trust_anchor_guard(r); results.append(case('external_trust_root_blocks_candidate_self_resign',trust_base['status']=='PASS' and tout['status']=='FAIL',{'base':trust_base.get('status'),'tamper_failures':tout.get('failures',[])[:4]}))

out={'suite':'v2.1.6 cross-lifecycle semantic granularity bugfix regression','total':len(results),'passed_expectations':sum(x['ok'] for x in results),'results':results}
print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['passed_expectations']==out['total'] else 1)
