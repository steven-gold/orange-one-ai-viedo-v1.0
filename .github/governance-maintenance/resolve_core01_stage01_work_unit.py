#!/usr/bin/env python3
from pathlib import Path
import subprocess, sys, yaml, json

ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
SCOPE=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
LIFE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
ADAPT=ROOT/'governance/ci/stage_execution_semantic_adapters.yaml'
ENGINE=ROOT/'governance/ci/stage_execution_engine.py'

EXPECTED_GOV='GOV-REV-20260923-WORD-PROJECTION-NEXTSTEP-CONSUMER-SYNC-HARDENING'
SOURCE_UID='SRC-DOCX-CORE01-943AF192'
SOURCE_SHA='943af192004b587d6aab36e114eeb40430c9ea45614cc154d62dd9e3b5cbefeb'
PROJ_UID='PROJ-SRC-DOCX-CORE01-943AF192'
PROJ_HASH='e11b1caad15fc06a83ebb9cf99f5c19072dcad75eb84f1366787306ddd24a13f'
PAIR_HASH='5fc4838e5c04c460fec2039ab406d25083ccfa05e88c7c56f4d3e9ea47ccdb83'
FREEZE='00_SOURCE_INTAKE/prestage_core01_943af192_word_yaml/00_SOURCE_INTAKE/SOURCE_PROJECTIONS/SRC-DOCX-CORE01-943AF192/SOURCE_PROJECTION_FREEZE_RECEIPT.yaml'
PROJ='00_SOURCE_INTAKE/prestage_core01_943af192_word_yaml/00_SOURCE_INTAKE/SOURCE_PROJECTIONS/SRC-DOCX-CORE01-943AF192/CANONICAL_SOURCE_PROJECTION.yaml'
RECON='00_SOURCE_INTAKE/prestage_core01_943af192_word_yaml/00_SOURCE_INTAKE/SOURCE_PROJECTIONS/SRC-DOCX-CORE01-943AF192/SOURCE_PROJECTION_RECONCILIATION_EVIDENCE.yaml'
AUDIT='00_SOURCE_INTAKE/prestage_core01_943af192_word_yaml/00_SOURCE_INTAKE/SOURCE_PROJECTIONS/SRC-DOCX-CORE01-943AF192/SOURCE_DOCUMENT_CONTENT_AUDIT.yaml'
LOCK='00_SOURCE_INTAKE/prestage_core01_943af192_word_yaml/00_SOURCE_INTAKE/SOURCE_PROJECTIONS/SRC-DOCX-CORE01-943AF192/RAW_SOURCE_IMMUTABILITY_RECEIPT.yaml'
WU='WU-STAGE01-CORE01-943AF192-REPLAY'
WUR='WUR-CORE01-STAGE01-943AF192-FROZEN-SOURCE'
AUTH='EXPLICIT_USER_DIRECTIVE_20260923_NEXT_STEP_RESOLVE_CORE01_STAGE01_WU'
PAGE_UID='CORE-01'
SOURCE_FINGERPRINT=SOURCE_UID.rsplit('-',1)[-1].lower()
RUNROOT='00_SOURCE_INTAKE/' + 'run_' + PAGE_UID.lower().replace('-','') + '_' + SOURCE_FINGERPRINT + '_stage01'
OWNER=RUNROOT+'/00_SOURCE_INTAKE/evidence/STAGE1_VALIDATION_EVIDENCE.yaml'

def load(p): 
    d=yaml.safe_load(Path(p).read_text(encoding='utf-8'))
    if not isinstance(d,dict): raise RuntimeError('MAPPING_REQUIRED:'+str(p))
    return d
def dump(p,d): Path(p).write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=220),encoding='utf-8')
def run(*args):
    cp=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    print(cp.stdout)
    if cp.returncode:
        print(cp.stderr,file=sys.stderr); raise SystemExit(cp.returncode)
    return cp

state=load(STATE); scope=load(SCOPE); life=load(LIFE); adapt=load(ADAPT)
if state.get('specification_uid')!=EXPECTED_GOV: raise SystemExit('BLOCK:GOVERNANCE_UID_DRIFT')
if state.get('status')!='CORE01_WORD_YAML_PRESTAGE_FROZEN_VALIDATED': raise SystemExit('BLOCK:PRESTAGE_NOT_FROZEN_VALIDATED')
if state.get('next_action')!='RESOLVE_CORE01_STAGE01_WORK_UNIT': raise SystemExit('BLOCK:NEXT_ACTION_DRIFT')
pair=state.get('core01_frozen_source_pair') or {}
for k,v in [('source_uid',SOURCE_UID),('source_sha256',SOURCE_SHA),('projection_content_hash',PROJ_HASH),('pair_hash',PAIR_HASH)]:
    if pair.get(k)!=v: raise SystemExit('BLOCK:FROZEN_PAIR_DRIFT:'+k)
fr=load(ROOT/FREEZE)
if fr.get('source_uid')!=SOURCE_UID or fr.get('pair_hash')!=PAIR_HASH or fr.get('status')!='FROZEN_FOR_STAGE01' or fr.get('lock_state')!='SOURCE_PAIR_FROZEN':
    raise SystemExit('BLOCK:FREEZE_RECEIPT_INVALID')
if fr.get('raw_source_writable') is not False or fr.get('projection_writable') is not False:
    raise SystemExit('BLOCK:PAIR_NOT_IMMUTABLE')

stage=next((x for x in life.get('stages') or [] if isinstance(x,dict) and x.get('stage_uid')=='STAGE-01'),None)
if not stage: raise SystemExit('BLOCK:STAGE01_PROFILE_MISSING')
ad=(adapt.get('stages') or {}).get('STAGE-01')
if not isinstance(ad,dict): raise SystemExit('BLOCK:STAGE01_ADAPTER_MISSING')

# one legal successor only: current frozen pair + current reentry map + user next-step directive
resolution={
  'resolution_uid':WUR,'normative_authority':False,'result':'PASS_SINGLE_LEGAL_SUCCESSOR',
  'requested_primary_task_layer':'PRODUCT_STAGE_EXECUTION','resolved_work_unit_uid':WU,
  'authorization_basis':AUTH,'current_governance_uid':EXPECTED_GOV,
  'predecessor_work_unit_uid':'WU-PRESTAGE-CORE01-WORD-YAML-PROJECTION-20260923-001',
  'page_scope':['CORE-01'],'stage_uid':'STAGE-01','semantic_capability':'SOURCE_INTAKE_BASE_BLUEPRINT',
  'source_uid':SOURCE_UID,'pair_hash':PAIR_HASH,
  'basis':[
    'CURRENT_RESUME_EXACT_NEXT_ACTION_RESOLVE_CORE01_STAGE01_WORK_UNIT',
    'PRESTAGE_SOURCE_PAIR_FROZEN_AND_VALIDATED',
    'SOURCE_PROJECTION_RECONCILIATION_PASS',
    'INDEPENDENT_POST_CONVERSION_VALIDATION_PASS',
    'CURRENT_REENTRY_MAP_SOURCE_INTAKE_BASE_BLUEPRINT_TO_STAGE01',
    'USER_EXPLICITLY_REQUESTED_NEXT_STEP',
    'NO_MATERIALLY_DISTINCT_LEGAL_PRODUCT_SUCCESSOR'
  ],
  'product_stage_credit':0
}
state['last_work_unit_resolution_gate']=resolution
state['selected_execution_profile_state']['current_step_state_key']='stage1'
ex=state.setdefault('execution',{})
ex['current_stage']='STAGE-01-PREEXECUTION'
ex['run_uid']='CORE01-943AF192-STAGE01-R1'
ex['target_pages']=['CORE-01']
ex['stage1']={
  'result':'NOT_EXECUTED',
  'CORE-01':'NOT_EXECUTED',
  'work_unit_uid':WU,
  'work_unit_resolution':'PASS_SINGLE_LEGAL_SUCCESSOR',
  'execution_started':False,
  'pre_execution_gate':'GOVERNANCE_LOAD_RECEIPT_PASS',
  'pre_execution_gate_status':'NOT_EXECUTED',
  'stage_exit_allowed':False,
  'artifact_root_present':False,
  'target_page_uids':['CORE-01'],
  'remaining_page_uids':['CORE-01'],
}
ex['website_construction_allowed']=False; ex['deployment_allowed']=False

dependencies=[FREEZE,PROJ,RECON,AUDIT,LOCK,
 '.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',
 '.github/governance-source/active/source/10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml']
for rel in dependencies:
    if not (ROOT/rel).exists(): raise SystemExit('BLOCK:DEPENDENCY_MISSING:'+rel)

state['status']='CORE01_STAGE01_WORK_UNIT_RESOLVED_PREEXECUTION_GOVERNANCE_LOAD_REQUIRED'
state['next_action']='GENERATE_CORE01_STAGE01_GOVERNANCE_LOAD_RECEIPT'
state['current_primary_task_layer']='PRODUCT_STAGE_EXECUTION'
state['current_primary_task_authorization_uid']=AUTH
state['current_primary_task_product_stage_credit']=0
state['active_work_unit']={
  'work_unit_uid':WU,
  'canonical_name':'CORE-01_STAGE-01_FRESH_REPLAY',
  'primary_task_layer':'PRODUCT_STAGE_EXECUTION',
  'stage_uid':'STAGE-01',
  'semantic_capability':'SOURCE_INTAKE_BASE_BLUEPRINT',
  'scope':['CORE-01'],
  'canonical_owner':OWNER,
  'current_status':'ACTIVE_PREEXECUTION_GOVERNANCE_LOAD_REQUIRED',
  'authorization_uid':AUTH,
  'dependencies':dependencies,
  'required_outputs':list(stage.get('outputs') or []),
  'operation_bindings':{
    str(op):{'executor_owner':'.github/governance-maintenance/run_fresh_stage_replay.py','result_owner':OWNER}
    for op in (stage.get('operations') or [])
  },
  'scanner_bindings':{
    str(dim):{'scanner_owner':'.github/governance-source/active/source/09_TESTS/governance/governance_stage1_pipeline_guard.py','result_owner':OWNER}
    for dim in (ad.get('scanner_dimensions') or [])
  },
  'source_projection_admission':{
    'applicability':'REQUIRED',
    'bindings':[{
      'source_uid':SOURCE_UID,
      'freeze_receipt_ref':FREEZE,
      'pair_hash':PAIR_HASH,
      'raw_source_sha256':SOURCE_SHA,
      'projection_uid':PROJ_UID,
      'projection_content_hash':PROJ_HASH
    }]
  },
  'planned_run_root':RUNROOT,
  'pre_execution_gate':'GOVERNANCE_LOAD_RECEIPT_PASS',
  'pre_execution_gate_status':'NOT_EXECUTED',
  'execution_started':False,
  'product_blocker_credit':0,
  'out_of_scope':['ASSET-01','STAGE-02','STAGE-03','WEBSITE_CONSTRUCTION','DEPLOYMENT']
}
state['resume_control']={
  'current_resume_point':'CORE01_STAGE01_WORK_UNIT_RESOLVED_PREEXECUTION_GOVERNANCE_LOAD_REQUIRED',
  'current_work_unit_uid':WU,'current_owner':OWNER,
  'exact_next_action':'GENERATE_CORE01_STAGE01_GOVERNANCE_LOAD_RECEIPT',
  'historical_stage2_results_are_current_state':False,
  'stage2_execution_requires_fresh_entry_resolution':True,
  'product_execution_allowed':False,
  'product_execution_block_reason':'CORE01_STAGE01_GOVERNANCE_LOAD_RECEIPT_NOT_YET_PASS',
  'website_construction_allowed':False,'deployment_allowed':False
}
pair['stage01_admission_status']='WORK_UNIT_RESOLVED_GOVERNANCE_LOAD_REQUIRED'
pair['stage01_work_unit_uid']=WU
state['core01_frozen_source_pair']=pair
dump(STATE,state)

scope.update({
 'owning_capability':'SOURCE_INTAKE_BASE_BLUEPRINT',
 'scope_kind':'EXACT_SINGLE_PAGE_STAGE01_FROZEN_PROJECTION_REENTRY',
 'work_unit_uid':WU,
 'included_units':['CORE-01'],
 'excluded_units':['ASSET-01'],
 'remaining_units':['CORE-01'],
 'stage_required_units':['CORE-01'],
 'scope_selection_authority':AUTH,
 'partial_scope':False,
 'stage_exit_credit_allowed':False,
 'product_stage_execution_allowed':False,
 'product_stage_execution_block_reason':'CORE01_STAGE01_GOVERNANCE_LOAD_RECEIPT_NOT_YET_PASS',
 'next_action':'GENERATE_CORE01_STAGE01_GOVERNANCE_LOAD_RECEIPT',
 'closure_status':'ACTIVE_PREEXECUTION_GOVERNANCE_LOAD_REQUIRED',
 'fresh_revalidation_required':True,
 'product_stage_revalidation_required':False,
 'product_stage_revalidation_credit':0
})
scope['dependency_closure_refs']=dependencies
scope['denominator_source_refs']=[PROJ,FREEZE]
scope['source_projection_binding']={
 'source_uid':SOURCE_UID,'freeze_receipt_ref':FREEZE,'pair_hash':PAIR_HASH,
 'raw_source_sha256':SOURCE_SHA,'projection_uid':PROJ_UID,'projection_content_hash':PROJ_HASH
}
dump(SCOPE,scope)

# Admission only: validates WU/profile/bindings, performs no product execution.
run(sys.executable,str(ENGINE),'--admission-check','--stage','STAGE-01')
run(sys.executable,str(ROOT/'governance/ci/validate_selected_execution_profile_integrity.py'))
run(sys.executable,str(ROOT/'governance/ci/validate_active_consumer_reference_integrity.py'))

for p in [ROOT/'.github/governance-maintenance/resolve_core01_stage01_work_unit.py',
          ROOT/'.github/workflows/core01-stage01-wur-admission.yml',
          ROOT/'governance/test/CORE01_STAGE01_WUR_TRIGGER']:
    if p.exists(): p.unlink()

run('git','config','user.name','github-actions[bot]')
run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
run('git','add','-A')
_diff=subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT)
if _diff.returncode==0:
    raise SystemExit('BLOCK:NO_WUR_DELTA')
if _diff.returncode!=1:
    raise SystemExit('BLOCK:GIT_DIFF_CHECK_FAILED:'+str(_diff.returncode))
run('git','commit','-m','feat(stage1): resolve CORE-01 Stage-01 work unit after frozen source pair')
head=run('git','rev-parse','HEAD').stdout.strip()
run('git','push','origin','HEAD:rebuild-v2.1.1')
print(json.dumps({'status':'PASS_WUR_AND_ADMISSION','head':head,'work_unit_uid':WU,'next_action':'GENERATE_CORE01_STAGE01_GOVERNANCE_LOAD_RECEIPT','stage01_executed':False,'product_stage_credit':0},indent=2))
