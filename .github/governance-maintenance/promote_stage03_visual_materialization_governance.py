#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, os, subprocess, sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
BASE_PATH=ROOT/'.github/governance-maintenance/promote_blueprint_traceability_governance.py'
spec=importlib.util.spec_from_file_location('acpos_promotion_base',BASE_PATH)
base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

OLD_UID='GOV-REV-20260919-ASSET-STAGE01-STAGE02-SHARED-CONTRACT-HARDENING'
NEW_UID='GOV-REV-20260920-STAGE03-VISUAL-MATERIALIZATION-HARDENING'
OLD_DISPLAY='v2.2.13'
NEW_DISPLAY='v2.2.14'
NEW_SOURCE_REV='v2.2.14-stage03-visual-materialization-hardening'
AUTH_UID='USR-DIRECTIVE-20260920-STAGE03-VISUAL-MATERIALIZATION-HARDENING-R1'
WORK_UNIT='WU-GOV-STAGE03-VISUAL-MATERIALIZATION-HARDENING-001'
NEW_PACKAGE='AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.14_STAGE03_VISUAL_MATERIALIZATION_HARDENING_LOCAL_VERIFIED.zip'
PRODUCT_WU='WU-STAGE03-CORE01-VISUAL-DESIGN-001'
for k,v in {'OLD_UID':OLD_UID,'NEW_UID':NEW_UID,'OLD_DISPLAY':OLD_DISPLAY,'NEW_DISPLAY':NEW_DISPLAY,'NEW_SOURCE_REV':NEW_SOURCE_REV,'AUTH_UID':AUTH_UID,'WORK_UNIT':WORK_UNIT,'NEW_PACKAGE':NEW_PACKAGE}.items():
    setattr(base,k,v)

def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def dump(p,o):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(yaml.safe_dump(o,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def run(*args,check=True):
    env=os.environ.copy(); env['PYTHONDONTWRITEBYTECODE']='1'; env['PYTHONPYCACHEPREFIX']='/tmp/acpos-stage03-gov'
    cp=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,env=env)
    if check and cp.returncode:
        print(cp.stdout); print(cp.stderr,file=sys.stderr); raise SystemExit(cp.returncode)
    return cp
def unique_extend(lst,items):
    for x in items:
        if x not in lst: lst.append(x)
def commit_push(msg):
    run('git','config','user.name','github-actions[bot]')
    run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    run('git','add','-A')
    if run('git','diff','--cached','--quiet',check=False).returncode==0: raise RuntimeError('NO_DELTA_TO_COMMIT')
    run('git','commit','-m',msg); run('git','push','origin','HEAD:rebuild-v2.1.1')
    return run('git','rev-parse','HEAD').stdout.strip()

def prepare():
    cur=load(ROOT/'GOVERNANCE_CURRENT.yaml')
    if cur.get('active_governance_uid')!=OLD_UID: raise RuntimeError('PREPARE_CURRENT_GOVERNANCE_DRIFT')
    receipt=load(ROOT/f'governance/test/spec_change_authorizations/{AUTH_UID}.yaml')
    if receipt.get('status')!='APPROVED_FOR_EXACT_SCOPE' or receipt.get('current_governance_uid')!=OLD_UID: raise RuntimeError('AUTHORIZATION_RECEIPT_INVALID')
    sp=ROOT/'governance/test/ACTIVE_STATE.yaml'; s=load(sp); old=s.get('active_work_unit') or {}
    if old.get('work_unit_uid')!=PRODUCT_WU: raise RuntimeError('EXPECTED_STAGE03_PRODUCT_WU')
    s['preserved_stage03_product_work_unit']={
      'work_unit_uid':old.get('work_unit_uid'),'canonical_name':old.get('canonical_name'),'primary_task_layer':old.get('primary_task_layer'),
      'stage_uid':old.get('stage_uid'),'semantic_capability':old.get('semantic_capability'),'canonical_owner':old.get('canonical_owner'),
      'output_root':old.get('output_root'),'current_status':'SUSPENDED_FOR_AUTHORIZED_GOVERNANCE_SUCCESSOR',
      'resume_point':'STAGE3_CORE01_VISUAL_REVIEW_PENDING','next_action_after_governance_successor':'DELETE_STAGE03_GENERATED_OUTPUTS_THEN_FRESH_REPLAY',
      'predecessor_governance_uid':OLD_UID,'product_stage_credit':0}
    wur={'resolution_uid':'WUR-GOV-STAGE03-VISUAL-MATERIALIZATION-HARDENING-20260920-001','normative_authority':False,'authorization_uid':AUTH_UID,
      'requested_primary_task_layer':'GOVERNANCE_MAINTENANCE','predecessor_work_unit_uid':PRODUCT_WU,
      'predecessor_disposition':'LEGALLY_SUSPENDED_GOVERNANCE_DEFECT_REQUIRES_SUCCESSOR','candidate_successor_work_unit_uid':WORK_UNIT,
      'canonical_owner':'.github/governance-source/active/source/12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md',
      'dependency_legality':'PASS','reverse_dependency_legality':'PASS','applicability':'PASS','duplicate_parallel_work_unit':'NONE',
      'result':'PASS_SINGLE_LEGAL_SUCCESSOR','product_stage_credit':0}
    s['work_unit_resolution_gate_stage03_visual_materialization_hardening']=wur; s['last_work_unit_resolution_gate']=wur
    s['active_work_unit']={'work_unit_uid':WORK_UNIT,'canonical_name':'STAGE03_VISUAL_MATERIALIZATION_GOVERNANCE_HARDENING',
      'primary_task_layer':'GOVERNANCE_MAINTENANCE','semantic_capability':'GOVERNANCE_POLICY_AND_EXECUTION_PROFILE_HARDENING',
      'canonical_policy_owner':'governance/specifications/current/SPECIFICATION_MUTATION_CONTROL.yaml',
      'canonical_owner':'.github/governance-source/active/source/12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md',
      'authorization_uid':AUTH_UID,'current_status':'WUR_RESOLVED_READY_FOR_GOVERNANCE_SUCCESSOR',
      'scope':['MOTHER_STAGE03_VISUAL_REQUIRED_OUTPUT_MATERIALIZATION_CONTRACT','STAGE03_PROFILE_REQUIRED_SECTION_OUTPUT_PRODUCER_AND_DENOMINATOR_RECONCILIATION',
        'VISUAL_REFERENCE_ANNOTATION_REQUIRED_OUTPUT','VISUAL_INHERITANCE_MATRIX_REQUIRED_OUTPUT','VISUAL_SCENARIO_EVIDENCE_SET_REQUIRED_OUTPUT',
        'ATOMIC_WORKBENCH_VISUAL_BINDING_ENFORCEMENT','CURRENT_SCOPE_PROJECTOR_SYNCHRONIZATION','CURRENT_PROBLEM_REGISTER_AND_DENOMINATOR_RECOMPUTATION'],
      'out_of_scope':['PRODUCT_AUTHORITY_AUTOFILL','GLOBAL_VISUAL_AUTHORITY_INVENTION','GLOBAL_SHELL_AUTHORITY_INVENTION','STAGE02_FUNCTIONAL_TOPOLOGY_REDEFINITION','STAGE04_EXECUTION','WEBSITE_IMPLEMENTATION','DEPLOYMENT'],
      'dependencies':['GOVERNANCE_CURRENT.yaml','governance/specifications/REGISTRY.yaml','.github/governance-source/active/source/12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md',
        '.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml','governance/test/spec_change_authorizations/'+AUTH_UID+'.yaml'],
      'definition_of_done':['NEW_IMMUTABLE_GOVERNANCE_UID_PROMOTED','STAGE03_PROFILE_MATERIALIZES_ALL_APPLICABLE_MOTHER_VISUAL_OUTPUTS','SOURCE_IDENTITY_REBUILT',
        'CURRENT_PROJECTORS_ATOMICALLY_MIGRATED','FULL_LINE_SUCCESS_ON_SUCCESSOR','SELECTED_PROFILE_SUCCESS_ON_SUCCESSOR','PRODUCT_STAGE_CREDIT_ZERO'],
      'product_stage_credit':0,'legal_next_transition':'RESTORE_PRESERVED_STAGE03_PRODUCT_WORK_UNIT_FOR_CLEAN_FRESH_REPLAY'}
    s['current_primary_task_layer']='GOVERNANCE_MAINTENANCE'; s['current_primary_task_authorization_uid']=AUTH_UID; s['current_primary_task_product_stage_credit']=0
    s['status']='ACTIVE_GOVERNANCE_STAGE03_VISUAL_MATERIALIZATION_HARDENING_WUR_RESOLVED'; s['next_action']='PROMOTE_V2_2_14_STAGE03_VISUAL_MATERIALIZATION_HARDENING'
    s['resume_control']={'current_resume_point':'STAGE03_VISUAL_MATERIALIZATION_HARDENING_WUR_RESOLVED_READY_FOR_SUCCESSOR','current_work_unit_uid':WORK_UNIT,
      'current_owner':'.github/governance-source/active/source/12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md','historical_stage2_results_are_current_state':False,
      'stage2_execution_requires_fresh_entry_resolution':False,'exact_next_action':'PROMOTE_V2_2_14_STAGE03_VISUAL_MATERIALIZATION_HARDENING',
      'preserved_product_work_unit_uid':PRODUCT_WU,'preserved_product_resume_point':'STAGE3_CORE01_VISUAL_REVIEW_PENDING'}
    att=s.get('stage03_active_attempt') or {}; att['fresh_revalidation_required']=True; att['closure_credit_under_current_governance']=False; att['next_action']='SUSPENDED_PENDING_GOVERNANCE_SUCCESSOR'; s['stage03_active_attempt']=att
    ex=s.setdefault('execution',{}); st3=ex.setdefault('stage3',{}); st3['stage_exit_allowed']=False; st3['prior_results_authoritative_for_current_governance']=False; st3['revalidation_required_under_current_governance']=True
    ex['stage3']=st3; ex['website_construction_allowed']=False; ex['deployment_allowed']=False; s['execution']=ex
    dump(sp,s); print(json.dumps({'prepare_commit':commit_push('governance: enter Stage-03 visual materialization hardening')},indent=2))

def mutate_mother():
    p=SOURCE/'12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md'; marker='<!-- SECTION_UID: WEB-GOV-01-S087 -->'
    if marker in p.read_text(encoding='utf-8'): return
    text='''<!-- SECTION_UID: WEB-GOV-01-S087 -->
## 87. 視覺設計 Profile 實體化與分母對帳 Gate / Visual Design Profile Materialization and Denominator Reconciliation

Every selected Execution Profile that binds the VISUAL_DESIGN capability MUST project every applicable Mother-required visual deliverable into explicit profile outputs, producer bindings, applicability rules, Current denominator accounting, validation evidence, and fail-closed behavior. A profile-local output list MUST_NOT weaken or silently omit a reusable Mother requirement.

For every applicable visual-design scope, the profile MUST materialize at least VISUAL_REFERENCE_ANNOTATION, VISUAL_INHERITANCE_MATRIX, and VISUAL_SCENARIO_EVIDENCE_SET in addition to the page/surface Visual Design Spec, Geometry, topology/workbench bindings, preview evidence, and Change Set. VISUAL_PREVIEW_EVIDENCE, a screenshot, a structural wireframe, or a high-level design package MUST_NOT substitute for those separate required artifacts.

VISUAL_STYLE_DEFINITION remains conditionally required by WEB-GOV-01-S080 only when Current evidence proves that no applicable Current visual authority exists. An unresolved, external, missing-from-capture, or not-yet-resolved authority reference is UNRESOLVED_AUTHORITY, not AUTHORITY_ABSENT; it MUST remain a blocker and MUST_NOT authorize AI to invent a replacement global style, shell, palette, token set, component system, or visual semantics.

Before a candidate can reach the human Visual Review boundary, reviewable visual evidence MUST expose the applicable required Controls/System Triggers, Fields/Inputs, States, Visual Anchors, Workbench boundaries, and legal semantic order at sufficient fidelity for review. A preview self-classified as structural-only, or one that omits the applicable required interaction denominator, is not a complete Visual Review candidate.

For every ATOMIC_WORKBENCH, visual materialization MUST include an explicit atomic-workbench visual binding and prove required order, adjacency, same-surface/context continuity, interruption boundary, and permitted downstream docks/surfaces. A section-level binding summary alone MUST_NOT support functional-to-visual topology equivalence PASS.

The Stage/Capability Current Problem Register and Denominator Snapshot MUST include every unresolved applicable visual Authority gap and every missing required visual deliverable. Human review pending is an additional state and MUST_NOT replace or hide other open blockers.

Any mismatch between Mother-required applicable deliverables and profile outputs/producers/denominators is PROFILE_MATERIALIZATION_UNDERCOVERAGE and MUST block Stage closure, Visual Approval, Design Freeze, and downstream transition.'''
    p.write_text(p.read_text(encoding='utf-8').rstrip()+'\n\n'+text+'\n',encoding='utf-8')

def mutate_section_registry():
    p=SOURCE/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'; d=load(p); doc=next((x for x in d.get('documents',[]) if x.get('document_id')=='WEB-GOV-01'),None)
    if not doc: raise RuntimeError('WEB_GOV_01_SECTION_REGISTRY_MISSING')
    uid='WEB-GOV-01-S087'
    if not any(x.get('section_uid')==uid for x in doc.get('sections',[])):
        title='視覺設計 Profile 實體化與分母對帳 Gate / Visual Design Profile Materialization and Denominator Reconciliation'; heading='## 87. '+title; path='12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md'
        doc.setdefault('sections',[]).append({'section_uid':uid,'level':2,'canonical_number':'87','title':title,'heading':heading,'path':path,'binding_sha256':base.section_binding(uid,'WEB-GOV-01',path,heading)})
    if 'governance_revision' in d: d['governance_revision']=NEW_SOURCE_REV
    dump(p,d)

def mutate_stage_profile_and_refs():
    lp=SOURCE/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'; life=load(lp); st=next((x for x in life.get('stages',[]) if x.get('stage_uid')=='STAGE-03'),None)
    if not st: raise RuntimeError('STAGE03_PROFILE_MISSING')
    ops=['VISUAL_REFERENCE_ANNOTATION_COMPILE','VISUAL_INHERITANCE_MATRIX_COMPILE','VISUAL_SCENARIO_EVIDENCE_COMPILE']; outs=['VISUAL_REFERENCE_ANNOTATION','VISUAL_INHERITANCE_MATRIX','VISUAL_SCENARIO_EVIDENCE_SET']
    unique_extend(st.setdefault('operations',[]),ops); unique_extend(st.setdefault('outputs',[]),outs)
    st.setdefault('output_producers',{}).update({'VISUAL_REFERENCE_ANNOTATION':'VISUAL_REFERENCE_ANNOTATION_COMPILE','VISUAL_INHERITANCE_MATRIX':'VISUAL_INHERITANCE_MATRIX_COMPILE','VISUAL_SCENARIO_EVIDENCE_SET':'VISUAL_SCENARIO_EVIDENCE_COMPILE'})
    unique_extend(st.setdefault('required_normative_section_uids',[]),['WEB-GOV-01-S080','WEB-GOV-01-S087'])
    app=st.setdefault('required_output_applicability',{}); unique_extend(app.setdefault('always_for_target_scope',[]),['VISUAL_DESIGN_SPEC_PACKAGE','VISUAL_GEOMETRY_CONTRACT','VISUAL_PREVIEW_EVIDENCE','VISUAL_CHANGESET','VISUAL_INTERACTION_TOPOLOGY_BINDING','FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT','VISUAL_REFERENCE_ANNOTATION','VISUAL_INHERITANCE_MATRIX','VISUAL_SCENARIO_EVIDENCE_SET'])
    st['visual_materialization_gate']={'required':True,'mother_section_uid':'WEB-GOV-01-S087','required_outputs':outs,'structural_only_preview_may_reach_visual_review':False,'explicit_atomic_workbench_visual_binding_required':True,'unresolved_visual_authority_is_authority_absent':False,'unresolved_visual_authority_must_enter_current_problem_denominator':True,'profile_materialization_undercoverage':'BLOCK'}
    be=st.setdefault('business_entity_completeness_gate',{}); be['visual_reference_annotation_required']=True; be['visual_inheritance_matrix_required']=True; be['visual_scenario_evidence_set_required']=True
    cross=life.setdefault('cross_stage_invariants',{}).setdefault('stage_execution_invariant_hardening',{}); cross.update({'mother_required_visual_outputs_profile_materialized':True,'stage03_visual_reference_annotation_output_required':True,'stage03_visual_inheritance_matrix_output_required':True,'stage03_visual_scenario_evidence_set_output_required':True,'unresolved_visual_authority_not_equivalent_to_absent':True})
    dump(lp,life)
    rp=SOURCE/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'; ref=load(rp); unique_extend(ref['stage_reference_rules']['STAGE-03']['exact_required_normative_section_uids'],['WEB-GOV-01-S080','WEB-GOV-01-S087']); dump(rp,ref)
    sp=SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'; sem=load(sp); unique_extend(sem['semantic_snapshot']['stage_reference_rules']['STAGE-03']['exact_required_normative_section_uids'],['WEB-GOV-01-S080','WEB-GOV-01-S087']); sem['governance_revision']=NEW_SOURCE_REV; sem['content_hash']=base.hobj(sem); dump(sp,sem); return sem['content_hash']

def mutate_invariant_and_audit():
    p=SOURCE/'10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'; d=load(p)
    d.setdefault('invariants',{})['VISUAL_DESIGN_PROFILE_MATERIALIZATION_COMPLETENESS']={'capability':'VISUAL_DESIGN','mother_section_uid':'WEB-GOV-01-S087','required_stage03_outputs':['VISUAL_DESIGN_SPEC_PACKAGE','VISUAL_GEOMETRY_CONTRACT','VISUAL_PREVIEW_EVIDENCE','VISUAL_CHANGESET','VISUAL_INTERACTION_TOPOLOGY_BINDING','FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT','VISUAL_REFERENCE_ANNOTATION','VISUAL_INHERITANCE_MATRIX','VISUAL_SCENARIO_EVIDENCE_SET'],'every_required_output_has_explicit_producer':True,'mother_required_output_may_be_omitted_by_profile':False,'structural_only_preview_may_satisfy_human_visual_review':False,'atomic_workbench_visual_binding_required':True,'unresolved_authority_is_authority_absent':False,'unresolved_applicable_visual_authority_in_denominator_required':True,'profile_materialization_undercoverage':'BLOCK'}
    d['governance_revision']=NEW_SOURCE_REV; dump(p,d)
    p=SOURCE/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'; d=load(p); unique_extend(d.setdefault('required_normative_section_uids',[]),['WEB-GOV-01-S087']); c=d.setdefault('stage_execution_invariant_contract',{})
    c.update({'visual_design_profile_materialization_completeness_required':True,'stage03_visual_reference_annotation_output_required':True,'stage03_visual_inheritance_matrix_output_required':True,'stage03_visual_scenario_evidence_set_output_required':True,'structural_only_visual_review_candidate_blocked':True,'unresolved_visual_authority_not_equivalent_to_absent':True}); dump(p,d)

def harden_validator():
    p=SOURCE/'09_TESTS/governance/validate_stage_execution_invariants.py'; s=p.read_text(encoding='utf-8')
    old="'TASK_LAYER_EFFECTFUL_TRANSITION_ORDER']"; new="'TASK_LAYER_EFFECTFUL_TRANSITION_ORDER','VISUAL_DESIGN_PROFILE_MATERIALIZATION_COMPLETENESS']"
    if new not in s:
        if s.count(old)!=1: raise RuntimeError('VALIDATOR_REQUIRED_LIST_DRIFT')
        s=s.replace(old,new,1)
    anchor="    rv=inv.get('REVIEW_VS_CLOSURE_SEPARATION') or {}\n"
    extra="    vm=inv.get('VISUAL_DESIGN_PROFILE_MATERIALIZATION_COMPLETENESS') or {}\n    vm_req={'VISUAL_DESIGN_SPEC_PACKAGE','VISUAL_GEOMETRY_CONTRACT','VISUAL_PREVIEW_EVIDENCE','VISUAL_CHANGESET','VISUAL_INTERACTION_TOPOLOGY_BINDING','FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT','VISUAL_REFERENCE_ANNOTATION','VISUAL_INHERITANCE_MATRIX','VISUAL_SCENARIO_EVIDENCE_SET'}\n    if set(vm.get('required_stage03_outputs') or [])!=vm_req or vm.get('every_required_output_has_explicit_producer') is not True or vm.get('mother_required_output_may_be_omitted_by_profile') is not False or vm.get('structural_only_preview_may_satisfy_human_visual_review') is not False or vm.get('atomic_workbench_visual_binding_required') is not True or vm.get('unresolved_authority_is_authority_absent') is not False or vm.get('unresolved_applicable_visual_authority_in_denominator_required') is not True or vm.get('profile_materialization_undercoverage')!='BLOCK': failures.append('visual_design_profile_materialization_incomplete')\n"
    if extra.strip() not in s:
        if s.count(anchor)!=1: raise RuntimeError('VALIDATOR_INSERT_ANCHOR_DRIFT')
        s=s.replace(anchor,extra+anchor,1)
    anchor2="    st2=next((x for x in life.get('stages') or [] if x.get('stage_uid')=='STAGE-02'),{})\n"
    extra2="    st3=next((x for x in life.get('stages') or [] if x.get('stage_uid')=='STAGE-03'),{})\n    stage3_required={'VISUAL_DESIGN_SPEC_PACKAGE','VISUAL_GEOMETRY_CONTRACT','VISUAL_PREVIEW_EVIDENCE','VISUAL_CHANGESET','VISUAL_INTERACTION_TOPOLOGY_BINDING','FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT','VISUAL_REFERENCE_ANNOTATION','VISUAL_INHERITANCE_MATRIX','VISUAL_SCENARIO_EVIDENCE_SET'}\n    if not stage3_required.issubset(set(st3.get('outputs') or [])): failures.append('stage03_mother_required_visual_outputs_missing')\n    st3prod=st3.get('output_producers') or {}\n    if any(not st3prod.get(x) for x in stage3_required): failures.append('stage03_required_output_producer_missing')\n    if not {'WEB-GOV-01-S080','WEB-GOV-01-S087'}.issubset(set(st3.get('required_normative_section_uids') or [])): failures.append('stage03_visual_materialization_normative_binding_missing')\n    va=st3.get('visual_materialization_gate') or {}\n    if va.get('required') is not True or va.get('structural_only_preview_may_reach_visual_review') is not False or va.get('explicit_atomic_workbench_visual_binding_required') is not True or va.get('unresolved_visual_authority_is_authority_absent') is not False or va.get('unresolved_visual_authority_must_enter_current_problem_denominator') is not True: failures.append('stage03_visual_materialization_gate_incomplete')\n"
    if extra2.strip() not in s:
        if s.count(anchor2)!=1: raise RuntimeError('VALIDATOR_STAGE3_ANCHOR_DRIFT')
        s=s.replace(anchor2,extra2+anchor2,1)
    p.write_text(s,encoding='utf-8')

def mutate_current_components():
    p=ROOT/'governance/specifications/current/INTERACTION_TOPOLOGY_AI_CONTINUITY.yaml'; d=load(p)
    d.setdefault('common_invariants',{})['VISUAL_DESIGN_PROFILE_MATERIALIZATION_COMPLETENESS']={'mother_section_uid':'WEB-GOV-01-S087','required_stage_outputs':['VISUAL_REFERENCE_ANNOTATION','VISUAL_INHERITANCE_MATRIX','VISUAL_SCENARIO_EVIDENCE_SET'],'explicit_output_producer_binding_required':True,'structural_only_preview_may_reach_human_visual_review':False,'atomic_workbench_visual_binding_required':True,'unresolved_visual_authority_is_authority_absent':False,'unresolved_visual_authority_must_remain_blocker':True,'profile_materialization_undercoverage':'BLOCK'}
    d['schema_version']=5; dump(p,d)
    p=ROOT/'governance/specifications/current/EXECUTION_CYCLE_CONTROL.yaml'; d=load(p)
    d['mother_profile_materialization_reconciliation']={'applicable_mother_required_output_must_be_profile_output':True,'explicit_producer_binding_required':True,'required_output_denominator_must_include_all_applicable_mother_outputs':True,'profile_local_output_subset_may_weaken_mother_policy':False,'missing_required_profile_projection':'PROFILE_MATERIALIZATION_UNDERCOVERAGE','unresolved_authority_is_not_absent':True}
    d['schema_version']=6; dump(p,d)

def docs_and_candidate():
    base.append_once(SOURCE/'README.md','## v2.2.14 Stage-03 visual materialization hardening','## v2.2.14 Stage-03 visual materialization hardening\nThis successor closes the Mother-to-Execution-Profile undercoverage that allowed Stage-03 to report all declared outputs materialized while required Visual Reference Annotation, Visual Inheritance, multi-state evidence, reviewable controls/fields, atomic Workbench visual binding, and unresolved visual-Authority blockers were absent from the profile denominator. Product behavior and unresolved external visual Authority remain unchanged.')
    base.append_once(SOURCE/'VERSIONING_RULE.md','## v2.2.14 Stage-03 visual materialization hardening rule','## v2.2.14 Stage-03 visual materialization hardening rule\n- v2.2.13 remains immutable predecessor history.\n- A selected profile may specialize sequence and artifact names but may not omit applicable Mother-required deliverables.\n- Stage-03 Visual Review requires reviewable visual evidence, explicit annotation/inheritance/scenario artifacts, atomic Workbench projection, and a Current denominator that preserves unresolved visual Authority blockers.\n- UNRESOLVED visual Authority is not AUTHORITY_ABSENT and never authorizes AI style invention.')
    p=SOURCE/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'; d=load(p); d['candidate']='v2.2.14_STAGE03_VISUAL_MATERIALIZATION_HARDENING_CANDIDATE'; d['status']='CANDIDATE_UNDER_FRESH_SUCCESSOR_REVALIDATION'; fr=d.setdefault('fresh_revalidation',{}); fr['required']=True; fr['current_source_revision']=NEW_SOURCE_REV; fr['persisted_head_full_line_required']=True; fr['historical_evidence_may_close_successor']=False; dump(p,d)
    p=SOURCE/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml'; d=load(p); d['governance_revision']=NEW_SOURCE_REV; dump(p,d)

def patch_projection(semantic_hash,bundle,zips,checks):
    base.update_current_projection(semantic_hash,bundle,zips,checks)
    rp=ROOT/'governance/specifications/REGISTRY.yaml'; r=load(rp); unique_extend(r['active_specification'].setdefault('aliases',[]),['stage03-visual-materialization-hardening']); r['immediate_predecessor']['status']='SUPERSEDED_HISTORY_ONLY_AFTER_STAGE03_VISUAL_MATERIALIZATION_HARDENING'; dump(rp,r)
    ap=ROOT/'governance/test/ACTIVE_STATE.yaml'; a=load(ap); aw=a.get('active_work_unit') or {}
    if aw.get('work_unit_uid')!=WORK_UNIT: raise RuntimeError('ACTIVE_GOVERNANCE_WU_DRIFT')
    aw['current_status']='PROMOTION_MATERIALIZED_EXACT_HEAD_REVALIDATION_REQUIRED'; a['active_work_unit']=aw
    a['current_primary_task_layer']='GOVERNANCE_MAINTENANCE'; a['current_primary_task_authorization_uid']=AUTH_UID; a['current_primary_task_product_stage_credit']=0
    a['status']='ACTIVE_GOVERNANCE_STAGE03_VISUAL_MATERIALIZATION_HARDENING_PROMOTED_REVALIDATION_REQUIRED'; a['next_action']='RUN_V2_2_14_EXACT_HEAD_VALIDATION_THEN_DELETE_STAGE03_GENERATED_OUTPUTS_AND_FRESH_REPLAY'
    a['resume_control']={'current_resume_point':'STAGE03_VISUAL_MATERIALIZATION_SUCCESSOR_PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED','current_work_unit_uid':WORK_UNIT,'current_owner':'.github/governance-source/active/source/12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md','historical_stage2_results_are_current_state':False,'stage2_execution_requires_fresh_entry_resolution':False,'exact_next_action':'RUN_V2_2_14_EXACT_HEAD_VALIDATION_THEN_DELETE_STAGE03_GENERATED_OUTPUTS_AND_FRESH_REPLAY','preserved_product_work_unit_uid':PRODUCT_WU,'preserved_product_resume_point':'STAGE3_CORE01_VISUAL_REVIEW_PENDING'}
    gt=a.setdefault('governance_revision_transition',{}); gt.update({'predecessor_governance_uid':OLD_UID,'current_governance_uid':NEW_UID,'fresh_revalidation_required':True,'fresh_revalidation_scope':'STAGE03_VISUAL_MATERIALIZATION_PROFILE_AND_AFFECTED_VISUAL_CONSUMERS','mother_machine_revalidation_complete':False,'mother_machine_revalidation_run_id':None,'mother_machine_revalidation_head':None,'mother_machine_revalidation_result':'REVALIDATION_REQUIRED','selected_execution_profile_preserved':True,'selected_execution_profile_run_id':None,'product_fresh_replay_required_after_governance_change':True,'website_construction_remains_blocked':True,'deployment_remains_blocked':True})
    att=a.get('stage03_active_attempt') or {}; att['fresh_revalidation_required']=True; att['closure_credit_under_current_governance']=False; att['next_action']='DELETE_STAGE03_GENERATED_OUTPUTS_AFTER_SUCCESSOR_EXACT_HEAD_VALIDATION'; a['stage03_active_attempt']=att
    ex=a.setdefault('execution',{}); st3=ex.setdefault('stage3',{}); st3['stage_exit_allowed']=False; st3['prior_results_authoritative_for_current_governance']=False; st3['revalidation_required_under_current_governance']=True; ex['stage3']=st3; ex['website_construction_allowed']=False; ex['deployment_allowed']=False; a['execution']=ex; dump(ap,a)
    sp=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'; sc=load(sp); sc['governance_uid']=NEW_UID; sc['fresh_revalidation_required']=True; sc['stage_exit_credit_allowed']=False; sc['closure_status']='STAGE03_GOVERNANCE_SUCCESSOR_PROMOTED_REVALIDATION_REQUIRED'; sc['next_action']='DELETE_STAGE03_GENERATED_OUTPUTS_AFTER_SUCCESSOR_EXACT_HEAD_VALIDATION'; sc['content_hash']=base.hobj(sc); dump(sp,sc)

def promote():
    if load(ROOT/'GOVERNANCE_CURRENT.yaml').get('active_governance_uid')!=OLD_UID: raise RuntimeError('PROMOTION_CURRENT_GOVERNANCE_DRIFT')
    if not (ROOT/f'governance/test/spec_change_authorizations/{AUTH_UID}.yaml').is_file(): raise RuntimeError('PREEXISTING_AUTHORIZATION_MISSING')
    s=load(ROOT/'governance/test/ACTIVE_STATE.yaml')
    if s.get('current_primary_task_layer')!='GOVERNANCE_MAINTENANCE' or (s.get('active_work_unit') or {}).get('work_unit_uid')!=WORK_UNIT: raise RuntimeError('GOVERNANCE_WORK_UNIT_REQUIRED')
    mutate_mother(); mutate_section_registry(); semantic_hash=mutate_stage_profile_and_refs(); mutate_invariant_and_audit(); harden_validator(); mutate_current_components(); docs_and_candidate()
    sem=load(SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'); sem['governance_revision']=NEW_SOURCE_REV; sem['content_hash']=base.hobj(sem); dump(SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml',sem); semantic_hash=sem['content_hash']
    checks,bundle,zips=base.refresh_source(semantic_hash); patch_projection(semantic_hash,bundle,zips,checks)
    base.validate_all()
    for p in [ROOT/'.github/workflows/stage03-visual-governance-promotion.yml',ROOT/'.github/governance-maintenance/promote_stage03_visual_materialization_governance.py']:
        if p.exists(): p.unlink()
    sha=commit_push('feat(governance): promote Stage-03 visual materialization hardening\n\nSpec-Change-Authorization: '+AUTH_UID+'\nSpec-Change-Scope: STAGE03_MOTHER_PROFILE_OUTPUT_PRODUCER_DENOMINATOR_VISUAL_MATERIALIZATION')
    run(sys.executable,str(ROOT/'governance/ci/specification_mutation_guard.py'))
    print(json.dumps({'promotion_commit':sha,'new_uid':NEW_UID,'display_version':NEW_DISPLAY,'semantic_hash':semantic_hash,'checksums_hash':checks,'bundle_hash':bundle,'zip_hash':zips},indent=2))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--prepare',action='store_true'); ap.add_argument('--promote',action='store_true'); a=ap.parse_args()
    if a.prepare: prepare()
    elif a.promote: promote()
    else: raise SystemExit('use --prepare or --promote')
if __name__=='__main__': main()
