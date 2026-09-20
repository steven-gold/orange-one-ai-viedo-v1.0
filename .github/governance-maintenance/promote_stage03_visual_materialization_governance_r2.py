#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
BASE_PATH=ROOT/'.github/governance-maintenance/promote_blueprint_traceability_governance.py'
spec=importlib.util.spec_from_file_location('acpos_promotion_base',BASE_PATH)
base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

OLD_UID='GOV-REV-20260920-STAGE03-VISUAL-MATERIALIZATION-HARDENING'
NEW_UID='GOV-REV-20260920-STAGE03-VISUAL-MATERIALIZATION-PROMOTION-CLOSURE'
OLD_DISPLAY='v2.2.14'
NEW_DISPLAY='v2.2.15'
NEW_SOURCE_REV='v2.2.15-stage03-visual-materialization-promotion-closure'
AUTH_UID='USR-DIRECTIVE-20260920-STAGE03-VISUAL-MATERIALIZATION-HARDENING-R3'
WORK_UNIT='WU-GOV-STAGE03-VISUAL-MATERIALIZATION-HARDENING-001'
NEW_PACKAGE='AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.15_STAGE03_VISUAL_MATERIALIZATION_PROMOTION_CLOSURE_LOCAL_VERIFIED.zip'
for k,v in {'OLD_UID':OLD_UID,'NEW_UID':NEW_UID,'OLD_DISPLAY':OLD_DISPLAY,'NEW_DISPLAY':NEW_DISPLAY,'NEW_SOURCE_REV':NEW_SOURCE_REV,'AUTH_UID':AUTH_UID,'WORK_UNIT':WORK_UNIT,'NEW_PACKAGE':NEW_PACKAGE}.items():
    setattr(base,k,v)

def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def dump(p,o):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(yaml.safe_dump(o,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def run(*args,check=True):
    env=os.environ.copy(); env['PYTHONDONTWRITEBYTECODE']='1'; env['PYTHONPYCACHEPREFIX']='/tmp/acpos-stage03-gov-r2'
    cp=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,env=env)
    if check and cp.returncode:
        print(cp.stdout); print(cp.stderr,file=sys.stderr); raise SystemExit(cp.returncode)
    return cp
def unique_extend(lst,items):
    for x in items:
        if x not in lst: lst.append(x)

def promote():
    cur=load(ROOT/'GOVERNANCE_CURRENT.yaml')
    if cur.get('active_governance_uid')!=OLD_UID:
        raise RuntimeError(f'CURRENT_GOVERNANCE_DRIFT:{cur.get("active_governance_uid")}')
    state=load(ROOT/'governance/test/ACTIVE_STATE.yaml')
    if state.get('current_primary_task_layer')!='GOVERNANCE_MAINTENANCE':
        raise RuntimeError('GOVERNANCE_MAINTENANCE_PRIMARY_LAYER_REQUIRED')
    if (state.get('active_work_unit') or {}).get('work_unit_uid')!=WORK_UNIT:
        raise RuntimeError('GOVERNANCE_WORK_UNIT_REQUIRED')
    receipt=load(ROOT/f'governance/test/spec_change_authorizations/{AUTH_UID}.yaml')
    if receipt.get('status')!='APPROVED_FOR_EXACT_SCOPE' or receipt.get('current_governance_uid')!=OLD_UID:
        raise RuntimeError('AUTHORIZATION_RECEIPT_INVALID')

    base.append_once(
      SOURCE/'README.md',
      '## v2.2.15 Stage-03 visual materialization promotion closure',
      '## v2.2.15 Stage-03 visual materialization promotion closure\nThis successor preserves the v2.2.14 Stage-03 visual materialization semantics while repairing the promotion transaction boundary so Current Governance is backed by a valid pre-existing authorization, exact baseline identity, governance-maintenance Work Unit, and pre-push mutation guard. No product Authority or unresolved Global Visual/Shell Authority is invented.'
    )
    base.append_once(
      SOURCE/'VERSIONING_RULE.md',
      '## v2.2.15 Stage-03 visual materialization promotion closure rule',
      '## v2.2.15 Stage-03 visual materialization promotion closure rule\n- v2.2.14 is retained as invalid-promotion predecessor provenance and receives no Current closure credit.\n- v2.2.15 preserves the approved Stage-03 Mother/Profile materialization rules and reissues them through a valid atomic successor transaction.\n- Product Stage-03 must restart from preserved Stage-01/02 immutable inputs after exact-head governance closure.'
    )
    sem=load(SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml')
    sem['governance_revision']=NEW_SOURCE_REV
    sem['content_hash']=base.hobj(sem)
    dump(SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml',sem)
    semantic_hash=sem['content_hash']

    candidate_path=SOURCE/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'
    candidate=load(candidate_path)
    candidate['candidate']='v2.2.15_STAGE03_VISUAL_MATERIALIZATION_PROMOTION_CLOSURE_CANDIDATE'
    candidate['status']='CANDIDATE_UNDER_FRESH_SUCCESSOR_REVALIDATION'
    fresh=candidate.setdefault('fresh_revalidation',{})
    fresh['required']=True
    fresh['current_source_revision']=NEW_SOURCE_REV
    fresh['current_closure_credit']=False
    fresh['predecessor_evidence_current_closure_credit']=False
    fresh['embedded_preformal_execution_role']='HISTORICAL_PREDECESSOR_EVIDENCE_ONLY'
    fresh['predecessor_wrapper_result_role']='HISTORICAL_PREDECESSOR_EVIDENCE_ONLY'
    fresh['persisted_head_full_line_required']=True
    fresh['historical_evidence_may_close_successor']=False
    dump(candidate_path,candidate)

    review_path=SOURCE/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml'
    review=load(review_path)
    review['governance_revision']=NEW_SOURCE_REV
    dump(review_path,review)

    checks,bundle,zips=base.refresh_source(semantic_hash)
    base.update_current_projection(semantic_hash,bundle,zips,checks)

    rp=ROOT/'governance/specifications/REGISTRY.yaml'
    reg=load(rp)
    unique_extend(reg['active_specification'].setdefault('aliases',[]),['stage03-visual-materialization-promotion-closure'])
    reg['immediate_predecessor']['status']='SUPERSEDED_INVALID_PROMOTION_HISTORY_ONLY_AFTER_STAGE03_VISUAL_MATERIALIZATION_PROMOTION_CLOSURE'
    dump(rp,reg)

    ap=ROOT/'governance/test/ACTIVE_STATE.yaml'
    state=load(ap)
    aw=state.get('active_work_unit') or {}
    aw['authorization_uid']=AUTH_UID
    aw['current_status']='PROMOTION_MATERIALIZED_EXACT_HEAD_REVALIDATION_REQUIRED'
    state['active_work_unit']=aw
    state['current_primary_task_layer']='GOVERNANCE_MAINTENANCE'
    state['current_primary_task_authorization_uid']=AUTH_UID
    state['current_primary_task_product_stage_credit']=0
    state['status']='ACTIVE_GOVERNANCE_STAGE03_VISUAL_MATERIALIZATION_PROMOTION_CLOSURE_REVALIDATION_REQUIRED'
    state['next_action']='RUN_V2_2_15_EXACT_HEAD_VALIDATION_THEN_DELETE_STAGE03_GENERATED_OUTPUTS_AND_FRESH_REPLAY'
    state['resume_control']={
      'current_resume_point':'STAGE03_VISUAL_MATERIALIZATION_PROMOTION_CLOSURE_EXACT_HEAD_REVALIDATION_REQUIRED',
      'current_work_unit_uid':WORK_UNIT,
      'current_owner':'.github/governance-source/active/source/12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md',
      'historical_stage2_results_are_current_state':False,
      'stage2_execution_requires_fresh_entry_resolution':False,
      'exact_next_action':'RUN_V2_2_15_EXACT_HEAD_VALIDATION_THEN_DELETE_STAGE03_GENERATED_OUTPUTS_AND_FRESH_REPLAY',
      'preserved_product_work_unit_uid':'WU-STAGE03-CORE01-VISUAL-DESIGN-001',
      'preserved_product_resume_point':'STAGE3_CORE01_VISUAL_REVIEW_PENDING'
    }
    gt=state.setdefault('governance_revision_transition',{})
    gt.update({
      'predecessor_governance_uid':OLD_UID,
      'current_governance_uid':NEW_UID,
      'fresh_revalidation_required':True,
      'fresh_revalidation_scope':'STAGE03_VISUAL_MATERIALIZATION_PROFILE_AND_AFFECTED_VISUAL_CONSUMERS',
      'mother_machine_revalidation_complete':False,
      'mother_machine_revalidation_run_id':None,
      'mother_machine_revalidation_head':None,
      'mother_machine_revalidation_result':'REVALIDATION_REQUIRED',
      'selected_execution_profile_preserved':True,
      'selected_execution_profile_run_id':None,
      'product_fresh_replay_required_after_governance_change':True,
      'website_construction_remains_blocked':True,
      'deployment_remains_blocked':True,
      'invalid_predecessor_promotion_commit':'bf2c4de90fbc80003bfdcebc30732bcf25abd20d',
      'invalid_predecessor_promotion_workflow_run_id':35483077720,
      'invalid_predecessor_promotion_guard_result':'FAIL'
    })
    att=state.get('stage03_active_attempt') or {}
    att['fresh_revalidation_required']=True
    att['closure_credit_under_current_governance']=False
    att['next_action']='DELETE_STAGE03_GENERATED_OUTPUTS_AFTER_V2_2_15_EXACT_HEAD_VALIDATION'
    state['stage03_active_attempt']=att
    ex=state.setdefault('execution',{})
    st3=ex.setdefault('stage3',{})
    st3['stage_exit_allowed']=False
    st3['prior_results_authoritative_for_current_governance']=False
    st3['revalidation_required_under_current_governance']=True
    ex['stage3']=st3
    ex['website_construction_allowed']=False
    ex['deployment_allowed']=False
    state['execution']=ex
    dump(ap,state)

    sp=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
    scope=load(sp)
    scope['governance_uid']=NEW_UID
    scope['fresh_revalidation_required']=True
    scope['stage_exit_credit_allowed']=False
    scope['closure_status']='STAGE03_GOVERNANCE_PROMOTION_CLOSURE_REVALIDATION_REQUIRED'
    scope['next_action']='DELETE_STAGE03_GENERATED_OUTPUTS_AFTER_V2_2_15_EXACT_HEAD_VALIDATION'
    scope['content_hash']=base.hobj(scope)
    dump(sp,scope)

    base.validate_all()

    for p in [ROOT/'.github/workflows/stage03-visual-governance-promotion-r2.yml',ROOT/'.github/governance-maintenance/promote_stage03_visual_materialization_governance_r2.py']:
        if p.exists(): p.unlink()

    run('git','config','user.name','github-actions[bot]')
    run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    run('git','add','-A')
    if run('git','diff','--cached','--quiet',check=False).returncode==0:
        raise RuntimeError('NO_PROMOTION_DELTA')
    msg='feat(governance): close Stage-03 visual materialization promotion transaction\n\nSpec-Change-Authorization: '+AUTH_UID+'\nSpec-Change-Scope: STAGE03_VISUAL_MATERIALIZATION_PROMOTION_TRANSACTION_CLOSURE'
    run('git','commit','-m',msg)
    promotion_sha=run('git','rev-parse','HEAD').stdout.strip()

    run(sys.executable,str(ROOT/'governance/ci/specification_mutation_guard.py'))
    run(sys.executable,str(ROOT/'governance/ci/validate_active_consumer_reference_integrity.py'))
    run(sys.executable,str(ROOT/'governance/ci/validate_selected_execution_profile_integrity.py'))
    run(sys.executable,str(ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'))

    run('git','fetch','origin','rebuild-v2.1.1')
    parent=run('git','rev-parse','HEAD^').stdout.strip()
    remote=run('git','rev-parse','origin/rebuild-v2.1.1').stdout.strip()
    if parent!=remote:
        raise RuntimeError(f'REMOTE_MOVED_BEFORE_PROMOTION_PUSH:{parent}:{remote}')
    run('git','push','origin','HEAD:rebuild-v2.1.1')
    print(json.dumps({'promotion_commit':promotion_sha,'new_uid':NEW_UID,'display_version':NEW_DISPLAY,'semantic_hash':semantic_hash,'checksums_hash':checks,'bundle_hash':bundle,'zip_hash':zips,'mutation_guard':'PASS','full_line':'PASS'},indent=2))

if __name__=='__main__':
    promote()
