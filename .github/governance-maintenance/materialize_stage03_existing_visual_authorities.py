#!/usr/bin/env python3
from __future__ import annotations
import copy, json, os, subprocess, sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
SCOPE=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
RAW=ROOT/'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml'
CLS=ROOT/'00_SOURCE_INTAKE/run_core01_d81df9ac_stage02/01_CLASSIFIED/CORE-01/VISUAL/CLS_039_CURRENT_VISUAL_AUTHORITY.yaml'
CLEAN=ROOT/'.github/governance-maintenance/clean_stage03_generated_data.py'

GOV='GOV-REV-20260920-STAGE03-VISUAL-MATERIALIZATION-PROMOTION-CLOSURE'
PRODUCT_WU='WU-STAGE03-CORE01-VISUAL-DESIGN-001'
DEPENDENCY_WU='WU-STAGE03-GLOBAL-VISUAL-AUTHORITY-MATERIALIZATION-001'
HOME_REF='GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY@V1.9'
VISUAL_REF='GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY@V1.0'

AUTH=[
  {
    'ref':HOME_REF,
    'path':'authority/global/GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY_FINAL_LOCKED_V1.9.yaml',
    'blob':'cec94fa39c060b7de8c4be228f7958c2105d53f5',
    'id':'GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY',
    'version':'V1.9',
    'status_prefix':'FINAL_LOCKED'
  },
  {
    'ref':VISUAL_REF,
    'path':'authority/global/GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY_FINAL_LOCKED.yaml',
    'blob':'48d7bdaa46bfda16cbdf29997db126de3b9ce939',
    'id':'GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY',
    'version':'V1.0',
    'status_prefix':'FINAL_LOCKED'
  }
]

def run(*args,check=True):
    cp=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    if check and cp.returncode:
        print(cp.stdout); print(cp.stderr,file=sys.stderr); raise SystemExit(cp.returncode)
    return cp
def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def dump(p,o): Path(p).write_text(yaml.safe_dump(o,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def blob_at(ref,path): return run('git','rev-parse',f'{ref}:{path}').stdout.strip()
def show(ref,path): return run('git','show',f'{ref}:{path}').stdout

state=load(STATE); scope=load(SCOPE)
if state.get('specification_uid')!=GOV or scope.get('governance_uid')!=GOV:
    raise SystemExit('BLOCK: governance drift')
aw=state.get('active_work_unit') or {}
attempt=state.get('stage03_active_attempt') or {}
if state.get('current_primary_task_layer')!='PRODUCT_STAGE_EXECUTION' or aw.get('work_unit_uid')!=PRODUCT_WU:
    raise SystemExit('BLOCK: Stage-03 product WU not active')
if aw.get('current_status')!='BLOCKED_UNRESOLVED_VISUAL_AUTHORITY':
    raise SystemExit('BLOCK: Stage-03 not at unresolved visual Authority boundary')
if attempt.get('attempt_uid')!='STAGE03-CORE01-V2215-20260920-002':
    raise SystemExit('BLOCK: expected R2 attempt not current')
if attempt.get('source_workflow_run_id')!=35485953228 or attempt.get('source_artifact_id')!=10597700289:
    raise SystemExit('BLOCK: R2 provenance drift')
if attempt.get('open_gap_total')!=2 or attempt.get('closure_blocker_total')!=2:
    raise SystemExit('BLOCK: R2 Authority blocker denominator drift')

raw=load(RAW); cls=load(CLS)
a=raw.get('authority') or {}
if a.get('global_shell')!=HOME_REF or a.get('global_visual')!=VISUAL_REF:
    raise SystemExit('BLOCK: Raw Source Authority references drift')
facts=cls.get('facts') or []
owner=((facts[0].get('value') if facts and isinstance(facts[0],dict) else {}) or {})
if owner.get('global_visual_owner')!='authority/global/GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY_FINAL_LOCKED.yaml':
    raise SystemExit('BLOCK: classified global visual owner path drift')

run('git','fetch','origin','main','new')
source_heads={'main':run('git','rev-parse','origin/main').stdout.strip(),'new':run('git','rev-parse','origin/new').stdout.strip()}
for x in AUTH:
    p=ROOT/x['path']
    if p.exists():
        raise SystemExit(f"BLOCK: Current canonical Authority path already exists before materialization: {x['path']}")
    nb=blob_at('origin/new',x['path']); mb=blob_at('origin/main',x['path'])
    if nb!=x['blob'] or mb!=x['blob'] or nb!=mb:
        raise SystemExit(f"BLOCK: cross-branch Authority blob mismatch: {x['ref']}")
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(show('origin/new',x['path']),encoding='utf-8')
    if run('git','hash-object',x['path']).stdout.strip()!=x['blob']:
        raise SystemExit(f"BLOCK: materialized Authority byte hash drift: {x['ref']}")
    doc=load(p); auth=doc.get('authority') or {}
    if auth.get('id')!=x['id'] or auth.get('version')!=x['version'] or not str(auth.get('status') or '').startswith(x['status_prefix']):
        raise SystemExit(f"BLOCK: Authority identity/version/status mismatch: {x['ref']}")

# Use the single existing Stage-03 cleanup owner to invalidate R2 Current outputs.
cp=subprocess.run([sys.executable,str(CLEAN)],cwd=ROOT,text=True,capture_output=True,env={**os.environ,'STAGE03_AUTHORITY_MATERIALIZATION':'1'})
print(cp.stdout)
if cp.returncode:
    print(cp.stderr,file=sys.stderr); raise SystemExit(cp.returncode)

state=load(STATE)
receipt={
  'artifact_type':'STAGE03_EXTERNAL_VISUAL_AUTHORITY_MATERIALIZATION_RECEIPT',
  'normative_authority':False,
  'governance_uid':GOV,
  'dependency_work_unit_uid':DEPENDENCY_WU,
  'parent_product_work_unit_uid':PRODUCT_WU,
  'primary_task_layer':'PRODUCT_STAGE_EXECUTION',
  'authorization_basis':'EXPLICIT_USER_DIRECTIVE_CONTINUE_COMPLETE_STAGE03_20260920',
  'scope_kind':'DIRECT_DEPENDENCY_GAP_MATERIALIZATION',
  'source_branch_heads':source_heads,
  'sources_same_blob_on_main_and_new':True,
  'materialized_authorities':[
     {'authority_ref':x['ref'],'canonical_path':x['path'],'content_blob_sha1':x['blob'],'source_refs':[f"main:{x['path']}",f"new:{x['path']}"],'status':'CURRENT_PHYSICAL_AUTHORITY_MATERIALIZED'}
     for x in AUTH
  ],
  'raw_source_refs_preserved_immutable':True,
  'stage01_stage02_inputs_mutated':False,
  'ai_generated_authority_content':False,
  'product_stage_credit':0,
  'result':'PASS_EXACT_EXISTING_AUTHORITY_MATERIALIZED'
}
state['closed_product_dependency_work_unit_stage03_visual_authority_materialization']={
  'work_unit_uid':DEPENDENCY_WU,
  'canonical_name':'STAGE03_GLOBAL_VISUAL_AUTHORITY_MATERIALIZATION',
  'primary_task_layer':'PRODUCT_STAGE_EXECUTION',
  'parent_product_work_unit_uid':PRODUCT_WU,
  'canonical_owner_paths':[x['path'] for x in AUTH],
  'current_status':'CLOSED_EXACT_EXISTING_AUTHORITY_MATERIALIZED',
  'scope':[HOME_REF,VISUAL_REF],
  'definition_of_done':[
     'MAIN_AND_NEW_SOURCE_BLOBS_IDENTICAL',
     'CURRENT_CANONICAL_PATHS_MATERIALIZED_BYTE_EXACT',
     'AUTHORITY_UID_VERSION_STATUS_MATCH_CURRENT_REFERENCES',
     'R2_STAGE03_GENERATED_OUTPUTS_INVALIDATED_AND_REMOVED',
     'R3_CLEAN_BASELINE_PERSISTED',
     'PRODUCT_STAGE_CREDIT_ZERO'
  ],
  'product_stage_credit':0
}
state['stage03_external_visual_authority_materialization']=receipt
state['last_work_unit_resolution_gate']={
  'resolution_uid':'WUR-STAGE03-GLOBAL-VISUAL-AUTHORITY-MATERIALIZATION-001',
  'normative_authority':False,
  'result':'PASS_SINGLE_LEGAL_DIRECT_DEPENDENCY',
  'requested_primary_task_layer':'PRODUCT_STAGE_EXECUTION',
  'source_product_work_unit_uid':PRODUCT_WU,
  'resolved_work_unit_uid':DEPENDENCY_WU,
  'dependency_legality':'PASS',
  'reverse_dependency_action':'STAGE03_R2_OUTPUTS_CLEANED_R3_REEXECUTION_REQUIRED',
  'product_stage_credit':0
}
dump(STATE,state)
print(json.dumps(receipt,ensure_ascii=False,indent=2))
