#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, datetime, hashlib, importlib.util, json, re, subprocess, sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
SCOPE=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
CURRENT=ROOT/'GOVERNANCE_CURRENT.yaml'
REGISTRY=ROOT/'governance/specifications/REGISTRY.yaml'
LIFECYCLE=SOURCE/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
INDEX=SOURCE/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'
ROOT_MANIFEST=SOURCE/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'
SECTION_REGISTRY=SOURCE/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'
ACCEPTANCE=SOURCE/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'
VALIDATOR=SOURCE/'09_TESTS/governance/validate_execution_governance_load.py'
LOADER_VERSION='STAGE-GOVERNANCE-LOAD-V1'

spec=importlib.util.spec_from_file_location('execution_governance_load',VALIDATOR)
v=importlib.util.module_from_spec(spec); spec.loader.exec_module(v)

def load(p:Path)->dict:
    d=yaml.safe_load(p.read_text(encoding='utf-8'))
    if not isinstance(d,dict): raise RuntimeError('MAPPING_REQUIRED:'+str(p))
    return d

def write(p:Path,d:dict):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=220),encoding='utf-8')

def sha_file(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def hash_obj(o)->str:
    return hashlib.sha256(json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def hash_uid_set(uids)->str:
    return hashlib.sha256(('\n'.join(sorted(set(map(str,uids))))+'\n').encode()).hexdigest()

def safe_uid(s:str)->str:
    return re.sub(r'[^A-Za-z0-9_.-]+','-',str(s)).strip('-')

def artifact_type(path:Path)->str:
    if path.suffix.lower() in {'.yaml','.yml'}:
        try:
            d=load(path)
            return str(d.get('artifact_type') or d.get('artifact_uid') or 'YAML_ARTIFACT')
        except Exception:
            return 'YAML_ARTIFACT'
    return 'FILE_ARTIFACT'

def exact_loaded_artifact_receipts(refs:list[str])->list[dict]:
    rows=[]
    seen=set()
    for rel in refs:
        rel=str(rel)
        if rel in seen: continue
        seen.add(rel)
        p=ROOT/rel
        if not p.is_file(): raise RuntimeError('DECLARED_LOAD_ARTIFACT_MISSING:'+rel)
        rows.append({
          'artifact_ref':rel,
          'artifact_type':artifact_type(p),
          'sha256':sha_file(p),
          'status':'LOADED'
        })
    return rows

def resolve_sections(uids:list[str])->list[dict]:
    sections=v.section_map(SOURCE)
    rows=[]
    for uid in sorted(set(map(str,uids))):
        rec,err=v.resolve_section(SOURCE,uid,sections)
        if err: raise RuntimeError('NORMATIVE_SECTION_RESOLUTION_FAILED:'+err)
        rows.append(rec)
    return rows

def validate_stage_receipt(receipt:dict,target:dict,state:dict,scope:dict)->dict:
    failures=[]
    idx=load(INDEX); rootm=load(ROOT_MANIFEST)
    contract=idx.get('governance_load_receipt_contract') or {}
    for f in contract.get('required_fields') or []:
        if f not in receipt: failures.append('RECEIPT_FIELD_MISSING:'+str(f))
    if receipt.get('status')!='PASS': failures.append('RECEIPT_STATUS_NOT_PASS')
    if receipt.get('governance_revision')!=rootm.get('governance_revision'): failures.append('GOVERNANCE_REVISION_DRIFT')
    if receipt.get('root_manifest_hash')!=sha_file(ROOT_MANIFEST): failures.append('ROOT_MANIFEST_HASH_DRIFT')
    if receipt.get('section_registry_hash')!=sha_file(SECTION_REGISTRY): failures.append('SECTION_REGISTRY_HASH_DRIFT')
    if receipt.get('target_manifest_hash')!=hash_obj(target): failures.append('TARGET_MANIFEST_HASH_DRIFT')
    if receipt.get('work_unit_or_stage_operation_uid')!=target.get('work_unit_uid'): failures.append('WORK_UNIT_BINDING_DRIFT')
    awu=state.get('active_work_unit') or {}
    if awu.get('work_unit_uid')!=target.get('work_unit_uid'): failures.append('ACTIVE_WORK_UNIT_DRIFT')
    if scope.get('work_unit_uid')!=target.get('work_unit_uid'): failures.append('SCOPE_WORK_UNIT_DRIFT')
    if awu.get('stage_uid')!=target.get('stage_uid'): failures.append('ACTIVE_STAGE_UID_DRIFT')
    if scope.get('product_stage_execution_allowed') is not False: failures.append('PRELOAD_SCOPE_EXECUTION_MUST_STILL_BE_BLOCKED')
    common=target.get('common_normative_bundle_refs') or []
    mandatory=list((idx.get('mandatory_common_normative_bundles') or {}).keys())
    if common!=mandatory: failures.append('COMMON_BUNDLE_SET_OR_ORDER_DRIFT')
    if receipt.get('common_bundle_uids')!=common: failures.append('RECEIPT_COMMON_BUNDLE_DRIFT')
    for k in ('stage_normative_section_uids','profile_normative_section_uids'):
        if receipt.get(k)!=(target.get(k) or []): failures.append('RECEIPT_'+k.upper()+'_DRIFT')
    if receipt.get('artifact_specific_normative_section_uids')!=(target.get('artifact_specific_normative_section_uids') or []):
        failures.append('RECEIPT_ARTIFACT_SPECIFIC_REFS_DRIFT')
    if receipt.get('dependency_normative_section_uids')!=(target.get('dependency_normative_section_uids') or []):
        failures.append('RECEIPT_DEPENDENCY_NORMATIVE_REFS_DRIFT')
    expected_effective=set()
    bundles=idx.get('mandatory_common_normative_bundles') or {}
    for bid in common:
        expected_effective.update((bundles.get(bid) or {}).get('section_uids') or [])
    for key in ('stage_normative_section_uids','profile_normative_section_uids',
                'item_specific_normative_section_uids','artifact_specific_normative_section_uids',
                'dependency_normative_section_uids'):
        expected_effective.update(target.get(key) or [])
    if receipt.get('effective_normative_set_hash')!=hash_uid_set(expected_effective):
        failures.append('EFFECTIVE_NORMATIVE_SET_HASH_DRIFT')
    resolved=receipt.get('resolved_section_receipts') or []
    by_uid={str(x.get('section_uid')):x for x in resolved if isinstance(x,dict)}
    if set(by_uid)!=expected_effective: failures.append('RESOLVED_SECTION_DENOMINATOR_DRIFT')
    sections=v.section_map(SOURCE)
    for uid in sorted(expected_effective):
        rr,err=v.resolve_section(SOURCE,uid,sections)
        if err:
            failures.append('RESOLUTION_ERROR:'+err); continue
        got=by_uid.get(uid)
        if got!=rr: failures.append('RESOLUTION_RECEIPT_DRIFT:'+uid)
    expected_loaded=exact_loaded_artifact_receipts(target.get('loaded_artifact_refs') or [])
    if receipt.get('loaded_artifact_receipts')!=expected_loaded:
        failures.append('LOADED_ARTIFACT_RECEIPTS_DRIFT')
    acceptance=load(ACCEPTANCE)
    if receipt.get('acceptance_audit_blueprint_ref')!=acceptance.get('artifact_uid'):
        failures.append('ACCEPTANCE_BLUEPRINT_DRIFT')
    return {'status':'PASS' if not failures else 'FAIL','failures':failures,'effective_normative_count':len(expected_effective),'loaded_artifact_count':len(expected_loaded)}

def build(persist:bool)->dict:
    definition=v.validate_definition(SOURCE)
    if definition.get('status')!='PASS': raise RuntimeError('GOVERNANCE_LOAD_DEFINITION_INVALID:'+json.dumps(definition))
    state=load(STATE); scope=load(SCOPE); current=load(CURRENT); registry=load(REGISTRY)
    awu=state.get('active_work_unit') or {}
    if 'GOVERNANCE_LOAD_RECEIPT' not in str(state.get('next_action') or ''):
        raise RuntimeError('CURRENT_NEXT_ACTION_NOT_GOVERNANCE_LOAD')
    if awu.get('primary_task_layer')!='PRODUCT_STAGE_EXECUTION': raise RuntimeError('ACTIVE_WU_NOT_PRODUCT_STAGE_EXECUTION')
    if awu.get('current_status')!='ACTIVE_PREEXECUTION_GOVERNANCE_LOAD_REQUIRED': raise RuntimeError('ACTIVE_WU_NOT_PREEXECUTION_LOAD_REQUIRED')
    if awu.get('execution_started') is not False: raise RuntimeError('LOAD_RECEIPT_MUST_PRECEDE_EXECUTION')
    if awu.get('pre_execution_gate')!='GOVERNANCE_LOAD_RECEIPT_PASS': raise RuntimeError('ACTIVE_WU_PREEXECUTION_GATE_DRIFT')
    if awu.get('pre_execution_gate_status')!='NOT_EXECUTED': raise RuntimeError('PREEXECUTION_GATE_ALREADY_CONSUMED')
    stage_uid=str(awu.get('stage_uid') or '')
    life=load(LIFECYCLE)
    stage=next((x for x in life.get('stages') or [] if isinstance(x,dict) and x.get('stage_uid')==stage_uid),None)
    if not stage: raise RuntimeError('LIFECYCLE_STAGE_NOT_FOUND:'+stage_uid)
    if stage.get('pre_execution_gate')!='GOVERNANCE_LOAD_RECEIPT_PASS': raise RuntimeError('LIFECYCLE_PREEXECUTION_GATE_DRIFT')
    reg_active=registry.get('active_specification') or {}
    if current.get('active_governance_uid')!=reg_active.get('governance_uid'): raise RuntimeError('CURRENT_REGISTRY_GOVERNANCE_DRIFT')
    rootm=load(ROOT_MANIFEST)
    if rootm.get('governance_revision')!=current.get('source_identity',{}).get('verified_source_revision'):
        raise RuntimeError('ROOT_MANIFEST_CURRENT_REVISION_DRIFT')
    idx=load(INDEX)
    common=list((idx.get('mandatory_common_normative_bundles') or {}).keys())
    stage_refs=list(stage.get('required_normative_section_uids') or [])
    # The selected profile binds this stage through the lifecycle registry. No separate profile-level section list
    # exists in the current profile, so this layer is explicitly empty rather than guessed.
    profile_refs=[]
    item_refs=[]
    artifact_refs=[]
    dependency_normative=[]
    dependencies=list(awu.get('dependencies') or [])
    control_refs=['GOVERNANCE_CURRENT.yaml','governance/specifications/REGISTRY.yaml',
                  'governance/test/ACTIVE_STATE.yaml','governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml',
                  '.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',
                  '.github/governance-source/active/source/10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml',
                  '.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml']
    loaded_refs=[]
    for x in control_refs+dependencies:
        if x not in loaded_refs: loaded_refs.append(x)
    effective=set()
    bundles=idx.get('mandatory_common_normative_bundles') or {}
    for bid in common: effective.update((bundles.get(bid) or {}).get('section_uids') or [])
    for rows in (stage_refs,profile_refs,item_refs,artifact_refs,dependency_normative): effective.update(rows)
    resolved=resolve_sections(sorted(effective))
    acceptance=load(ACCEPTANCE)
    work_uid=str(awu.get('work_unit_uid') or '')
    run_uid=str((state.get('execution') or {}).get('run_uid') or '')
    if not work_uid or not run_uid: raise RuntimeError('EXECUTION_OR_WORK_UNIT_IDENTITY_MISSING')
    receipt_uid='LOAD-'+safe_uid(work_uid)+'-'+rootm.get('governance_revision','').replace('.','-')
    base=ROOT/'governance/test/preexecution/stage_governance_load'/safe_uid(work_uid)
    manifest_path=base/'STAGE_EXECUTION_LOAD_TARGET_MANIFEST.yaml'
    receipt_path=base/'GOVERNANCE_LOAD_RECEIPT.yaml'
    target={
      'schema_version':1,
      'artifact_type':'STAGE_EXECUTION_LOAD_TARGET_MANIFEST',
      'normative_authority':False,
      'work_unit_uid':work_uid,
      'stage_uid':stage_uid,
      'semantic_capability':awu.get('semantic_capability'),
      'page_or_scope_uids':list(awu.get('scope') or []),
      'execution_run_uid':run_uid,
      'governance_uid':current.get('active_governance_uid'),
      'governance_revision':rootm.get('governance_revision'),
      'selected_execution_profile_uid':(current.get('selected_execution_profile') or {}).get('profile_uid'),
      'active_work_unit_hash':hash_obj(awu),
      'execution_scope_manifest_sha256':sha_file(SCOPE),
      'source_projection_admission':copy.deepcopy(awu.get('source_projection_admission')),
      'common_normative_bundle_refs':common,
      'stage_normative_section_uids':stage_refs,
      'profile_normative_section_uids':profile_refs,
      'item_specific_normative_section_uids':item_refs,
      'artifact_specific_normative_section_uids':artifact_refs,
      'dependency_normative_section_uids':dependency_normative,
      'loaded_artifact_refs':loaded_refs,
      'acceptance_audit_blueprint_ref':acceptance.get('artifact_uid'),
      'governance_load_receipt_ref':str(receipt_path.relative_to(ROOT)),
      'status':'PREEXECUTION_TARGET_FROZEN'
    }
    receipt={
      'receipt_uid':receipt_uid,
      'execution_uid':'EXEC-'+safe_uid(run_uid),
      'run_uid':run_uid,
      'work_unit_or_stage_operation_uid':work_uid,
      'governance_revision':rootm.get('governance_revision'),
      'root_manifest_hash':sha_file(ROOT_MANIFEST),
      'common_bundle_uids':common,
      'stage_normative_section_uids':stage_refs,
      'profile_normative_section_uids':profile_refs,
      'artifact_specific_normative_section_uids':artifact_refs,
      'dependency_normative_section_uids':dependency_normative,
      'effective_normative_set_hash':hash_uid_set(effective),
      'resolved_section_receipts':resolved,
      'loaded_artifact_receipts':exact_loaded_artifact_receipts(loaded_refs),
      'acceptance_audit_blueprint_ref':acceptance.get('artifact_uid'),
      'loaded_at':datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
      'loader_version':LOADER_VERSION,
      'status':'PASS',
      'section_registry_hash':sha_file(SECTION_REGISTRY),
      'target_manifest_hash':hash_obj(target)
    }
    verdict=validate_stage_receipt(receipt,target,state,scope)
    if verdict['status']!='PASS': raise RuntimeError('STAGE_LOAD_RECEIPT_VALIDATION_FAILED:'+json.dumps(verdict))
    if persist:
        if base.exists(): raise RuntimeError('PREEXECUTION_LOAD_ROOT_ALREADY_EXISTS_NO_OVERWRITE')
        write(manifest_path,target); write(receipt_path,receipt)
        # Re-read persisted files before changing the state gate.
        persisted_target=load(manifest_path); persisted_receipt=load(receipt_path)
        verdict=validate_stage_receipt(persisted_receipt,persisted_target,state,scope)
        if verdict['status']!='PASS': raise RuntimeError('PERSISTED_STAGE_LOAD_RECEIPT_INVALID:'+json.dumps(verdict))
        awu=state['active_work_unit']
        awu['governance_load_target_manifest_ref']=str(manifest_path.relative_to(ROOT))
        awu['governance_load_receipt_ref']=str(receipt_path.relative_to(ROOT))
        awu['governance_load_receipt_uid']=receipt_uid
        awu['pre_execution_gate_status']='PASS'
        awu['current_status']='ACTIVE_PREEXECUTION_GOVERNANCE_LOAD_PASS_EXECUTION_READY'
        state['status']='STAGE_PREEXECUTION_GOVERNANCE_LOAD_PASS_EXECUTION_READY'
        state['next_action']='EXECUTE_ACTIVE_STAGE_WORK_UNIT'
        rc=state.setdefault('resume_control',{})
        rc['current_resume_point']='STAGE_PREEXECUTION_GOVERNANCE_LOAD_PASS_EXECUTION_READY'
        rc['exact_next_action']='EXECUTE_ACTIVE_STAGE_WORK_UNIT'
        rc['product_execution_allowed']=True
        rc['product_execution_block_reason']=None
        ex=state.setdefault('execution',{})
        step=ex.get('stage1') if stage_uid=='STAGE-01' else None
        if isinstance(step,dict):
            step['pre_execution_gate_status']='PASS'
            step['governance_load_receipt_ref']=str(receipt_path.relative_to(ROOT))
            step['execution_started']=False
        for _ctx in state.values():
            if isinstance(_ctx,dict) and _ctx.get('role')=='FROZEN_PRESTAGE_SOURCE_PAIR_CONTEXT':
                _ctx['governance_load_status']='PASS'
                if stage_uid=='STAGE-01' and 'stage01_admission_status' in _ctx:
                    _ctx['stage01_admission_status']='GOVERNANCE_LOAD_PASS_EXECUTION_READY'
        write(STATE,state)
        scope['product_stage_execution_allowed']=True
        scope['product_stage_execution_block_reason']=None
        scope['next_action']='EXECUTE_ACTIVE_STAGE_WORK_UNIT'
        scope['closure_status']='ACTIVE_PREEXECUTION_GOVERNANCE_LOAD_PASS_EXECUTION_READY'
        scope['governance_load_target_manifest_ref']=str(manifest_path.relative_to(ROOT))
        scope['governance_load_receipt_ref']=str(receipt_path.relative_to(ROOT))
        scope['governance_load_receipt_uid']=receipt_uid
        write(SCOPE,scope)
    return {'status':'PASS','receipt_uid':receipt_uid,'target_manifest_ref':str(manifest_path.relative_to(ROOT)),
            'receipt_ref':str(receipt_path.relative_to(ROOT)),'stage_uid':stage_uid,'work_unit_uid':work_uid,
            'effective_normative_count':len(effective),'loaded_artifact_count':len(loaded_refs),'persisted':persist}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--persist',action='store_true')
    a=ap.parse_args()
    try:
        print(json.dumps(build(a.persist),ensure_ascii=False,indent=2))
    except Exception as exc:
        print('BLOCK:',repr(exc),file=sys.stderr); raise SystemExit(1)

if __name__=='__main__': main()
