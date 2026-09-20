#!/usr/bin/env python3
from __future__ import annotations
import argparse, ast, copy, json, subprocess, sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
HARNESS=ROOT/'governance/ci/stress_test_stage03_core01.py'
PRODUCT_WU='WU-STAGE03-CORE01-VISUAL-DESIGN-001'
TEST_WU='WU-TEST-STAGE03-HIGH-PRESSURE-HARNESS-V2215-001'
GOV='GOV-REV-20260920-STAGE03-VISUAL-MATERIALIZATION-PROMOTION-CLOSURE'
AUTH='EXPLICIT-USER-DIRECTIVE-CONTINUE-STAGE03-HIGH-PRESSURE-20260920'
SUSPENDED_KEY='suspended_stage03_product_work_unit_for_high_pressure_harness_v2215'
RESUME_KEY='suspended_stage03_product_resume_for_high_pressure_harness_v2215'

def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def dump(p,o): Path(p).write_text(yaml.safe_dump(o,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def run(*args,check=True):
    cp=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    if check and cp.returncode:
        print(cp.stdout)
        print(cp.stderr,file=sys.stderr)
        raise SystemExit(cp.returncode)
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
    s=load(STATE)
    aw=s.get('active_work_unit') or {}
    if s.get('specification_uid')!=GOV: raise RuntimeError('CURRENT_GOVERNANCE_DRIFT')
    if s.get('current_primary_task_layer')!='PRODUCT_STAGE_EXECUTION' or aw.get('work_unit_uid')!=PRODUCT_WU:
        raise RuntimeError('EXPECTED_BLOCKED_STAGE03_PRODUCT_WU')
    if aw.get('current_status')!='BLOCKED_UNRESOLVED_VISUAL_AUTHORITY':
        raise RuntimeError('PRODUCT_WU_NOT_AT_AUTHORITY_BLOCKED_BOUNDARY')
    attempt=s.get('stage03_active_attempt') or {}
    if attempt.get('open_gap_total')!=2 or attempt.get('closure_blocker_total')!=2:
        raise RuntimeError('CURRENT_STAGE03_BLOCKER_DENOMINATOR_DRIFT')
    if (s.get('resume_control') or {}).get('current_resume_point')!='STAGE3_CORE01_VISUAL_AUTHORITY_BLOCKED':
        raise RuntimeError('PRODUCT_RESUME_DRIFT')

    s[SUSPENDED_KEY]=copy.deepcopy(aw)
    s[RESUME_KEY]=copy.deepcopy(s.get('resume_control') or {})
    wur={
      'resolution_uid':'WUR-TEST-STAGE03-HIGH-PRESSURE-HARNESS-V2215-001',
      'normative_authority':False,
      'result':'PASS_SINGLE_LEGAL_SUCCESSOR',
      'requested_primary_task_layer':'TEST_OR_VALIDATION_MAINTENANCE',
      'resolved_work_unit_uid':TEST_WU,
      'authorization_uid':AUTH,
      'source_product_work_unit_uid':PRODUCT_WU,
      'source_product_status':'BLOCKED_UNRESOLVED_VISUAL_AUTHORITY',
      'source_open_gap_total':2,
      'source_closure_blocker_total':2,
      'basis':[
        'CURRENT_V2215_STAGE03_EXECUTION_PERSISTED',
        'CURRENT_HIGH_PRESSURE_HARNESS_STILL_EXPECTS_SUPERSEDED_SIX_OUTPUT_AND_HUMAN_REVIEW_STATE',
        'TEST_HARNESS_MUST_BE_ALIGNED_WITH_CURRENT_GOVERNANCE_BEFORE_REVIEW',
        'PRODUCT_AUTHORITY_AND_PRODUCT_BLOCKER_DENOMINATOR_MUST_NOT_CHANGE'
      ],
      'product_stage_credit':0,
    }
    s['work_unit_resolution_gate_stage03_high_pressure_harness_v2215']=wur
    s['last_work_unit_resolution_gate']=wur
    s['active_work_unit']={
      'work_unit_uid':TEST_WU,
      'canonical_name':'STAGE03_V2215_HIGH_PRESSURE_HARNESS_ALIGNMENT',
      'primary_task_layer':'TEST_OR_VALIDATION_MAINTENANCE',
      'canonical_owner':'governance/ci/stress_test_stage03_core01.py',
      'parent_product_work_unit_uid':PRODUCT_WU,
      'current_status':'ACTIVE_HARNESS_ALIGNMENT',
      'scope':[
        'ALIGN_EXISTING_63_CHECK_STAGE03_HIGH_PRESSURE_HARNESS_TO_CURRENT_V2215_STATE',
        'PRESERVE_63_CHECK_DENOMINATOR',
        'EXPECT_NINE_CURRENT_STAGE03_PROFILE_OUTPUTS',
        'EXPECT_COMPLETE_REQUIRED_CONTROL_UID_PREVIEW_COVERAGE',
        'EXPECT_ATOMIC_CONVERSATION_ORDER_WITH_DECISION_DOCK_DOWNSTREAM',
        'EXPECT_UNRESOLVED_VISUAL_AUTHORITY_TO_FAIL_CLOSED_AND_ENTER_DENOMINATOR',
        'EXPECT_HUMAN_VISUAL_REVIEW_NOT_REACHED_WHILE_AUTHORITY_UNRESOLVED'
      ],
      'out_of_scope':[
        'MOTHER_NORMATIVE_CHANGE','CURRENT_SPECIFICATION_CHANGE','PRODUCT_AUTHORITY_CHANGE',
        'GLOBAL_VISUAL_AUTHORITY_INVENTION','GLOBAL_SHELL_AUTHORITY_INVENTION',
        'PRODUCT_BLOCKER_REDUCTION','STAGE04','WEBSITE_CONSTRUCTION','DEPLOYMENT'
      ],
      'definition_of_done':[
        'AST_BOUNDED_HARNESS_PATCH',
        'DYNAMIC_HIGH_PRESSURE_CHECK_DENOMINATOR_REMAINS_63',
        'CURRENT_TWO_EXTERNAL_AUTHORITY_BLOCKERS_ARE_EXPECTED_FAIL_CLOSED_STATE_NOT_HARNESS_FAILURE',
        'HIGH_PRESSURE_LOCAL_DRY_RUN_63_OF_63_PASS',
        'PRODUCT_STAGE_CREDIT_ZERO',
        'ORIGINAL_PRODUCT_WU_AND_RESUME_RESTORED'
      ],
      'product_stage_credit':0
    }
    s['current_primary_task_layer']='TEST_OR_VALIDATION_MAINTENANCE'
    s['current_primary_task_authorization_uid']=AUTH
    s['current_primary_task_product_stage_credit']=0
    s['status']='ACTIVE_STAGE03_HIGH_PRESSURE_HARNESS_V2215_MAINTENANCE'
    s['next_action']='PATCH_STAGE03_HIGH_PRESSURE_HARNESS_V2215'
    s['resume_control']={
      'current_resume_point':'STAGE03_HIGH_PRESSURE_HARNESS_V2215_PATCH_REQUIRED',
      'current_work_unit_uid':TEST_WU,
      'current_owner':'governance/ci/stress_test_stage03_core01.py',
      'exact_next_action':'PATCH_STAGE03_HIGH_PRESSURE_HARNESS_V2215',
      'suspended_product_work_unit_uid':PRODUCT_WU,
      'suspended_product_resume_point':'STAGE3_CORE01_VISUAL_AUTHORITY_BLOCKED'
    }
    dump(STATE,s)
    sha=commit_push('chore(test): enter Stage-03 high-pressure harness maintenance',['governance/test/ACTIVE_STATE.yaml'])
    print(json.dumps({'transition_commit':sha,'active_work_unit':TEST_WU,'product_stage_credit':0},indent=2))

def expr(src):
    return ast.parse(src,mode='eval').body

def patch():
    s=load(STATE)
    if s.get('current_primary_task_layer')!='TEST_OR_VALIDATION_MAINTENANCE' or (s.get('active_work_unit') or {}).get('work_unit_uid')!=TEST_WU:
        raise RuntimeError('TEST_MAINTENANCE_WU_REQUIRED')
    tree=ast.parse(HARNESS.read_text(encoding='utf-8'))
    replacements={
      'HP-004':'state.get("status")=="ACTIVE_CORE01_STAGE03_AUTHORITY_BLOCKED" and state.get("next_action")=="RESOLVE_CORE01_STAGE03_VISUAL_AUTHORITY"',
      'HP-005':'scope.get("closure_status")=="STAGE03_AUTHORITY_BLOCKED" and scope.get("next_action")=="RESOLVE_CORE01_STAGE03_VISUAL_AUTHORITY" and scope.get("remaining_units")==["CORE-01"]',
      'HP-010':'len(expected)==9 and all(p.is_file() for p in out_files.values())',
      'HP-035':'bool(required_control_uids) and len(visible_control_hits)==len(required_control_uids)',
      'HP-042':'set(str(x.get("authority_ref")) for x in visual_unresolved)=={"GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY@V1.9","GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY@V1.0"} and set(map(str,(docs.get("VISUAL_INHERITANCE_MATRIX",{}).get("unresolved_applicable_visual_authority_refs") or [])))=={"GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY@V1.9","GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY@V1.0"} and docs.get("VISUAL_INHERITANCE_MATRIX",{}).get("status")=="BLOCKED_UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY" and stage3.get("stage_exit_allowed") is False',
      'HP-043':'findings_doc.get("open_gap_total")==len(findings_doc.get("problems") or [])==len(visual_unresolved) and set(str(x.get("authority_ref")) for x in (findings_doc.get("problems") or []) if isinstance(x,dict))==set(str(x.get("authority_ref")) for x in visual_unresolved)',
      'HP-051':'review.get("review_result")=="NOT_REACHED_UNRESOLVED_VISUAL_AUTHORITY" and review.get("visual_approval") is False and review.get("design_freeze_allowed") is False',
    }
    seen={k:0 for k in replacements}
    neg_seen=0
    class T(ast.NodeTransformer):
        def visit_Call(self,node):
            self.generic_visit(node)
            if isinstance(node.func,ast.Name) and node.func.id=='check' and node.args and isinstance(node.args[0],ast.Constant):
                uid=node.args[0].value
                if uid in replacements:
                    if len(node.args)<2: raise RuntimeError('CHECK_ARGUMENT_SHAPE_INVALID:'+uid)
                    node.args[1]=expr(replacements[uid]); seen[uid]+=1
            return node
        def visit_Assign(self,node):
            nonlocal neg_seen
            self.generic_visit(node)
            if len(node.targets)==1 and isinstance(node.targets[0],ast.Subscript):
                t=node.targets[0]
                if isinstance(t.value,ast.Name) and t.value.id=='negative':
                    sl=t.slice
                    key=sl.value if isinstance(sl,ast.Constant) else None
                    if key=='atomic_decision_interrupt_caught':
                        node.value=expr('bool(ordered and not interrupted and len(conv_y)>=4 and conv_y[1] < ((conv_y[1]+conv_y[2])/2) < conv_y[2])')
                        neg_seen+=1
            return node
    tree=T().visit(tree); ast.fix_missing_locations(tree)
    if any(v!=1 for v in seen.values()) or neg_seen!=1:
        raise RuntimeError('HARNESS_AST_SELECTOR_DRIFT:'+repr({'checks':seen,'negative':neg_seen}))
    src=ast.unparse(tree)+'\n'
    compile(src,str(HARNESS),'exec')
    HARNESS.write_text(src,encoding='utf-8')
    cp=run(sys.executable,'-m','py_compile',str(HARNESS))
    sha=commit_push('fix(test): align Stage-03 63-check harness to v2.2.15',['governance/ci/stress_test_stage03_core01.py'])
    print(json.dumps({'harness_commit':sha,'patched_checks':seen,'negative_patch_count':neg_seen},indent=2))

def restore_and_dry_run():
    s=load(STATE)
    if s.get('current_primary_task_layer')!='TEST_OR_VALIDATION_MAINTENANCE' or (s.get('active_work_unit') or {}).get('work_unit_uid')!=TEST_WU:
        raise RuntimeError('TEST_MAINTENANCE_WU_REQUIRED')
    product=s.get(SUSPENDED_KEY)
    resume=s.get(RESUME_KEY)
    if not isinstance(product,dict) or product.get('work_unit_uid')!=PRODUCT_WU or not isinstance(resume,dict):
        raise RuntimeError('SUSPENDED_PRODUCT_CONTEXT_MISSING')
    test=copy.deepcopy(s.get('active_work_unit') or {})
    test['current_status']='CLOSED_VERIFIED_NO_PRODUCT_CREDIT'
    test['implementation_head_sha']=run('git','rev-parse','HEAD').stdout.strip()
    test['product_stage_credit']=0
    test['dry_run_required_before_restore']=True
    s['closed_test_validation_maintenance_work_unit_stage03_high_pressure_v2215']=test
    s['active_work_unit']=product
    s['current_primary_task_layer']='PRODUCT_STAGE_EXECUTION'
    s['current_primary_task_authorization_uid']='USR-DIRECTIVE-20260920-STAGE03-VISUAL-MATERIALIZATION-HARDENING-R3'
    s['current_primary_task_product_stage_credit']=0
    s['resume_control']=resume
    s['status']='ACTIVE_CORE01_STAGE03_AUTHORITY_BLOCKED'
    s['next_action']='RESOLVE_CORE01_STAGE03_VISUAL_AUTHORITY'
    s.pop(SUSPENDED_KEY,None); s.pop(RESUME_KEY,None)
    dump(STATE,s)

    cp=run(sys.executable,str(HARNESS),check=False)
    print(cp.stdout)
    print(cp.stderr,file=sys.stderr)
    if cp.returncode!=0:
        raise SystemExit(cp.returncode)
    report=ROOT/'governance/test/stage03/STAGE03_HIGH_PRESSURE_REVIEW_REPORT.json'
    data=json.loads(report.read_text(encoding='utf-8'))
    if data.get('check_total')!=63 or data.get('pass_total')!=63 or data.get('fail_total')!=0 or data.get('result')!='PASS':
        raise RuntimeError('HIGH_PRESSURE_DRY_RUN_NOT_63_OF_63:'+json.dumps({k:data.get(k) for k in ('result','check_total','pass_total','fail_total')}))
    if report.exists():
        report.unlink()
    sha=commit_push('chore(test): close Stage-03 high-pressure harness maintenance and restore product WU',['governance/test/ACTIVE_STATE.yaml'])
    print(json.dumps({'restore_commit':sha,'dry_run':'63/63_PASS','restored_product_work_unit':PRODUCT_WU,'resume_point':resume.get('current_resume_point'),'product_stage_credit':0},indent=2))

def main():
    p=argparse.ArgumentParser(); p.add_argument('mode',choices=['enter','patch','restore-and-dry-run']); a=p.parse_args()
    if a.mode=='enter': enter()
    elif a.mode=='patch': patch()
    else: restore_and_dry_run()
if __name__=='__main__': main()
