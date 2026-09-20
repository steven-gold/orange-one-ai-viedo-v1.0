#!/usr/bin/env python3
from __future__ import annotations
import argparse, ast, copy, json, subprocess, sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
HARNESS=ROOT/'governance/ci/stress_test_stage03_core01.py'
PRODUCT_WU='WU-STAGE03-CORE01-VISUAL-DESIGN-001'
TEST_WU='WU-TEST-STAGE03-HIGH-PRESSURE-HUMAN-REVIEW-PENDING-001'
GOV='GOV-REV-20260920-STAGE03-VISUAL-MATERIALIZATION-PROMOTION-CLOSURE'
AUTH='EXPLICIT-USER-DIRECTIVE-CONTINUE-COMPLETE-STAGE03-20260920'
SUSPENDED_WU='suspended_stage03_product_work_unit_for_review_pending_harness'
SUSPENDED_RESUME='suspended_stage03_product_resume_for_review_pending_harness'
SUSPENDED_STATE='suspended_stage03_product_state_for_review_pending_harness'

def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def dump(p,o): Path(p).write_text(yaml.safe_dump(o,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def run(*args,check=True):
    cp=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    if check and cp.returncode:
        print(cp.stdout); print(cp.stderr,file=sys.stderr); raise SystemExit(cp.returncode)
    return cp
def commit_push(msg, paths):
    run('git','config','user.name','github-actions[bot]')
    run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    run('git','add','--',*paths)
    if run('git','diff','--cached','--quiet',check=False).returncode==0:
        raise RuntimeError('NO_DELTA_TO_COMMIT')
    run('git','commit','-m',msg)
    run('git','push','origin','HEAD:rebuild-v2.1.1')
    return run('git','rev-parse','HEAD').stdout.strip()

def enter():
    s=load(STATE); aw=s.get('active_work_unit') or {}; attempt=s.get('stage03_active_attempt') or {}
    if s.get('current_primary_task_layer')=='TEST_OR_VALIDATION_MAINTENANCE' and aw.get('work_unit_uid')==TEST_WU:
        print(json.dumps({'transition':'ALREADY_ENTERED','work_unit_uid':TEST_WU,'product_stage_credit':0},indent=2)); return
    if s.get('specification_uid')!=GOV: raise RuntimeError('CURRENT_GOVERNANCE_DRIFT')
    if s.get('current_primary_task_layer')!='PRODUCT_STAGE_EXECUTION' or aw.get('work_unit_uid')!=PRODUCT_WU:
        raise RuntimeError('EXPECTED_STAGE03_PRODUCT_WU')
    if aw.get('current_status')!='PENDING_HUMAN_VISUAL_REVIEW':
        raise RuntimeError('PRODUCT_WU_NOT_AT_HUMAN_VISUAL_REVIEW_PENDING_BOUNDARY')
    if attempt.get('attempt_uid')!='STAGE03-CORE01-V2215-20260920-003':
        raise RuntimeError('R3_ATTEMPT_REQUIRED')
    if attempt.get('open_gap_total')!=0 or attempt.get('closure_blocker_total')!=0 or attempt.get('remaining_scope_total')!=1:
        raise RuntimeError('R3_REVIEW_PENDING_DENOMINATOR_DRIFT')
    if attempt.get('human_visual_review_status')!='PENDING':
        raise RuntimeError('R3_HUMAN_VISUAL_REVIEW_STATUS_DRIFT')
    resume=s.get('resume_control') or {}
    if resume.get('current_resume_point')!='STAGE3_CORE01_VISUAL_REVIEW_PENDING':
        raise RuntimeError('PRODUCT_RESUME_DRIFT')

    s[SUSPENDED_WU]=copy.deepcopy(aw)
    s[SUSPENDED_RESUME]=copy.deepcopy(resume)
    s[SUSPENDED_STATE]={
      'status':s.get('status'),'next_action':s.get('next_action'),
      'current_primary_task_authorization_uid':s.get('current_primary_task_authorization_uid'),
      'current_primary_task_product_stage_credit':s.get('current_primary_task_product_stage_credit',0)
    }
    wur={
      'resolution_uid':'WUR-TEST-STAGE03-HIGH-PRESSURE-HUMAN-REVIEW-PENDING-001',
      'normative_authority':False,'result':'PASS_SINGLE_LEGAL_SUCCESSOR',
      'requested_primary_task_layer':'TEST_OR_VALIDATION_MAINTENANCE',
      'resolved_work_unit_uid':TEST_WU,'authorization_uid':AUTH,
      'source_product_work_unit_uid':PRODUCT_WU,'source_product_status':'PENDING_HUMAN_VISUAL_REVIEW',
      'source_attempt_uid':attempt.get('attempt_uid'),'source_open_gap_total':0,'source_closure_blocker_total':0,'source_remaining_scope_total':1,
      'basis':[
        'R3_CURRENT_EXTERNAL_VISUAL_AUTHORITIES_RESOLVED',
        'PRODUCT_EXECUTION_REACHED_HUMAN_VISUAL_REVIEW_PENDING',
        'EXISTING_HIGH_PRESSURE_HARNESS_EXPECTS_SUPERSEDED_AUTHORITY_BLOCKED_STATE',
        'HARNESS_ALIGNMENT_MUST_NOT_APPROVE_VISUAL_REVIEW_OR_REDUCE_PRODUCT_SCOPE'
      ],
      'product_stage_credit':0
    }
    s['work_unit_resolution_gate_stage03_high_pressure_review_pending']=wur
    s['last_work_unit_resolution_gate']=wur
    s['active_work_unit']={
      'work_unit_uid':TEST_WU,'canonical_name':'STAGE03_HIGH_PRESSURE_HUMAN_REVIEW_PENDING_ALIGNMENT',
      'primary_task_layer':'TEST_OR_VALIDATION_MAINTENANCE','canonical_owner':'governance/ci/stress_test_stage03_core01.py',
      'parent_product_work_unit_uid':PRODUCT_WU,'current_status':'ACTIVE_HARNESS_ALIGNMENT',
      'scope':[
        'ALIGN_ONLY_FIVE_SUPERSEDED_AUTHORITY_BLOCKED_ASSERTIONS_TO_R3_HUMAN_REVIEW_PENDING',
        'PRESERVE_CURRENT_DYNAMIC_75_CHECK_DENOMINATOR',
        'VERIFY_TWO_CURRENT_EXTERNAL_VISUAL_AUTHORITIES_RESOLVED',
        'VERIFY_ZERO_PRODUCT_GAP_ZERO_CLOSURE_BLOCKER_ONE_REMAINING_HUMAN_REVIEW_SCOPE',
        'VERIFY_VISUAL_APPROVAL_FALSE_AND_DESIGN_FREEZE_FALSE',
        'VERIFY_STAGE04_WEBSITE_DEPLOYMENT_REMAIN_BLOCKED'
      ],
      'out_of_scope':['MOTHER_NORMATIVE_CHANGE','CURRENT_SPECIFICATION_CHANGE','PRODUCT_AUTHORITY_CHANGE','VISUAL_APPROVAL','DESIGN_FREEZE','STAGE04','WEBSITE_CONSTRUCTION','DEPLOYMENT'],
      'definition_of_done':['AST_BOUNDED_FIVE_ASSERTION_PATCH','DYNAMIC_HIGH_PRESSURE_DENOMINATOR_75','DRY_RUN_75_OF_75_PASS','PRODUCT_STAGE_CREDIT_ZERO','ORIGINAL_PRODUCT_WU_AND_REVIEW_PENDING_RESUME_RESTORED'],
      'product_stage_credit':0
    }
    s['current_primary_task_layer']='TEST_OR_VALIDATION_MAINTENANCE'
    s['current_primary_task_authorization_uid']=AUTH
    s['current_primary_task_product_stage_credit']=0
    s['status']='ACTIVE_STAGE03_HIGH_PRESSURE_HUMAN_REVIEW_PENDING_MAINTENANCE'
    s['next_action']='PATCH_STAGE03_HIGH_PRESSURE_HUMAN_REVIEW_PENDING_ASSERTIONS'
    s['resume_control']={
      'current_resume_point':'STAGE03_HIGH_PRESSURE_HUMAN_REVIEW_PENDING_PATCH_REQUIRED',
      'current_work_unit_uid':TEST_WU,'current_owner':'governance/ci/stress_test_stage03_core01.py',
      'exact_next_action':'PATCH_STAGE03_HIGH_PRESSURE_HUMAN_REVIEW_PENDING_ASSERTIONS',
      'suspended_product_work_unit_uid':PRODUCT_WU,'suspended_product_resume_point':'STAGE3_CORE01_VISUAL_REVIEW_PENDING'
    }
    dump(STATE,s)
    sha=commit_push('chore(test): enter Stage-03 review-pending harness maintenance',['governance/test/ACTIVE_STATE.yaml'])
    print(json.dumps({'transition_commit':sha,'active_work_unit':TEST_WU,'product_stage_credit':0},indent=2))

def expr(src): return ast.parse(src,mode='eval').body

def patch():
    s=load(STATE)
    if s.get('current_primary_task_layer')!='TEST_OR_VALIDATION_MAINTENANCE' or (s.get('active_work_unit') or {}).get('work_unit_uid')!=TEST_WU:
        raise RuntimeError('TEST_MAINTENANCE_WU_REQUIRED')
    tree=ast.parse(HARNESS.read_text(encoding='utf-8'))
    replacements={
      'HP-004':'state.get("status")=="ACTIVE_CORE01_STAGE03_VISUAL_REVIEW_PENDING" and state.get("next_action")=="HUMAN_VISUAL_REVIEW_CORE01_STAGE03"',
      'HP-005':'scope.get("closure_status")=="STAGE03_VISUAL_REVIEW_PENDING" and scope.get("next_action")=="HUMAN_VISUAL_REVIEW_CORE01_STAGE03" and scope.get("remaining_units")==["CORE-01"]',
      'HP-042':'not visual_unresolved and set(map(str,(docs.get("VISUAL_INHERITANCE_MATRIX",{}).get("unresolved_applicable_visual_authority_refs") or [])))==set() and set(str(x.get("authority_ref")) for x in (docs.get("VISUAL_INHERITANCE_MATRIX",{}).get("rows") or []) if isinstance(x,dict) and x.get("resolution")=="RESOLVED_CURRENT_PHYSICAL_AUTHORITY")=={"GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY@V1.9","GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY@V1.0"} and docs.get("VISUAL_INHERITANCE_MATRIX",{}).get("status")=="PASS_READY_FOR_HUMAN_VISUAL_REVIEW" and stage3.get("stage_exit_allowed") is False',
      'HP-043':'findings_doc.get("open_gap_total")==0 and findings_doc.get("closure_blocker_total")==0 and findings_doc.get("remaining_scope_total")==1 and (findings_doc.get("problems") or [])==[] and findings_doc.get("human_visual_review_status")=="PENDING" and attempt.get("open_gap_total")==0 and attempt.get("closure_blocker_total")==0 and attempt.get("remaining_scope_total")==1',
      'HP-051':'review.get("review_result")=="PENDING_HUMAN_VISUAL_REVIEW" and review.get("visual_approval") is False and review.get("design_freeze_allowed") is False and set(map(str,review.get("resolved_authority_refs") or []))=={"GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY@V1.9","GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY@V1.0"}'
    }
    seen={k:0 for k in replacements}
    class T(ast.NodeTransformer):
        def visit_Call(self,node):
            self.generic_visit(node)
            if isinstance(node.func,ast.Name) and node.func.id=='check' and node.args and isinstance(node.args[0],ast.Constant):
                uid=node.args[0].value
                if uid in replacements:
                    if len(node.args)<2: raise RuntimeError('CHECK_ARGUMENT_SHAPE_INVALID:'+uid)
                    node.args[1]=expr(replacements[uid]); seen[uid]+=1
            return node
    tree=T().visit(tree); ast.fix_missing_locations(tree)
    if any(v!=1 for v in seen.values()):
        raise RuntimeError('HARNESS_AST_SELECTOR_DRIFT:'+repr(seen))
    src=ast.unparse(tree)+'\n'
    compile(src,str(HARNESS),'exec')
    original=HARNESS.read_text(encoding='utf-8')
    HARNESS.write_text(src,encoding='utf-8')
    run(sys.executable,'-m','py_compile',str(HARNESS))
    if src==original:
        print(json.dumps({'harness':'ALREADY_PATCHED','patched_checks':seen},indent=2)); return
    sha=commit_push('fix(test): align Stage-03 harness to human visual review pending',['governance/ci/stress_test_stage03_core01.py'])
    print(json.dumps({'harness_commit':sha,'patched_checks':seen},indent=2))

def restore_and_dry_run():
    s=load(STATE)
    if s.get('current_primary_task_layer')!='TEST_OR_VALIDATION_MAINTENANCE' or (s.get('active_work_unit') or {}).get('work_unit_uid')!=TEST_WU:
        raise RuntimeError('TEST_MAINTENANCE_WU_REQUIRED')
    product=s.get(SUSPENDED_WU); resume=s.get(SUSPENDED_RESUME); prev=s.get(SUSPENDED_STATE)
    if not isinstance(product,dict) or product.get('work_unit_uid')!=PRODUCT_WU or not isinstance(resume,dict) or not isinstance(prev,dict):
        raise RuntimeError('SUSPENDED_PRODUCT_CONTEXT_MISSING')
    test=copy.deepcopy(s.get('active_work_unit') or {})
    test.update({
      'current_status':'CLOSED_VERIFIED_NO_PRODUCT_CREDIT',
      'implementation_head_sha':run('git','rev-parse','HEAD').stdout.strip(),
      'current_dynamic_high_pressure_check_denominator':75,
      'patched_assertion_count':5,'product_stage_credit':0
    })
    s['closed_test_validation_maintenance_work_unit_stage03_high_pressure_review_pending']=test
    s['active_work_unit']=product
    s['current_primary_task_layer']='PRODUCT_STAGE_EXECUTION'
    s['current_primary_task_authorization_uid']=prev.get('current_primary_task_authorization_uid')
    s['current_primary_task_product_stage_credit']=prev.get('current_primary_task_product_stage_credit',0)
    s['resume_control']=resume
    s['status']=prev.get('status')
    s['next_action']=prev.get('next_action')
    s.pop(SUSPENDED_WU,None); s.pop(SUSPENDED_RESUME,None); s.pop(SUSPENDED_STATE,None)
    dump(STATE,s)

    cp=run(sys.executable,str(HARNESS),check=False)
    print(cp.stdout); print(cp.stderr,file=sys.stderr)
    if cp.returncode!=0: raise SystemExit(cp.returncode)
    report=ROOT/'governance/test/stage03/STAGE03_HIGH_PRESSURE_REVIEW_REPORT.json'
    data=json.loads(report.read_text(encoding='utf-8'))
    if data.get('result')!='PASS' or data.get('check_total')!=75 or data.get('pass_total')!=75 or data.get('fail_total')!=0:
        raise RuntimeError('HIGH_PRESSURE_DRY_RUN_NOT_CURRENT_75_OF_75:'+json.dumps({k:data.get(k) for k in ('result','check_total','pass_total','fail_total')}))
    report.unlink()
    sha=commit_push('chore(test): close Stage-03 review-pending harness maintenance and restore product WU',['governance/test/ACTIVE_STATE.yaml'])
    print(json.dumps({'restore_commit':sha,'dry_run':'75/75_PASS','restored_product_work_unit':PRODUCT_WU,'resume_point':resume.get('current_resume_point'),'visual_approval':False,'design_freeze':False,'product_stage_credit':0},indent=2))

def main():
    p=argparse.ArgumentParser(); p.add_argument('mode',choices=['enter','patch','restore-and-dry-run']); a=p.parse_args()
    if a.mode=='enter': enter()
    elif a.mode=='patch': patch()
    else: restore_and_dry_run()
if __name__=='__main__': main()
