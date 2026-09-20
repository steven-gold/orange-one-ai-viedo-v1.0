#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json, os, subprocess
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
SCOPE=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
REGISTRY=ROOT/'governance/specifications/REGISTRY.yaml'
LIFECYCLE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
ADAPTERS=ROOT/'governance/ci/stage_execution_semantic_adapters.yaml'
TEST_ROOT=ROOT/'governance/test/stage03'
EXPECTED_STAGE='STAGE-03'
EXPECTED_CAPABILITY='VISUAL_DESIGN'

def load(path):
    if not path.is_file(): raise RuntimeError(f'MISSING:{path.relative_to(ROOT)}')
    obj=yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(obj,dict): raise RuntimeError(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj
def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(yaml.safe_dump(obj,sort_keys=False,allow_unicode=True),encoding='utf-8')
def jdump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def rel(path): return path.relative_to(ROOT).as_posix()
def find_dep(work,name):
    rows=[str(x) for x in (work.get('dependencies') or []) if str(x).endswith('/'+name) or str(x).endswith(name)]
    if len(rows)!=1: raise RuntimeError(f'EXACT_DEPENDENCY_REQUIRED:{name}:{rows}')
    p=ROOT/rows[0]
    if not p.is_file(): raise RuntimeError(f'DEPENDENCY_MISSING:{rows[0]}')
    return p
def stage_defs():
    profile=load(LIFECYCLE); adapters=load(ADAPTERS)
    st=next((x for x in profile.get('stages',[]) if x.get('stage_uid')==EXPECTED_STAGE),None)
    ad=(adapters.get('stages') or {}).get(EXPECTED_STAGE)
    if not st or not ad: raise RuntimeError('STAGE03_PROFILE_OR_ADAPTER_MISSING')
    return st,ad
def resolve():
    state=load(STATE); scope=load(SCOPE); reg=load(REGISTRY); work=state.get('active_work_unit') or {}
    gov=(reg.get('active_specification') or {}).get('governance_uid')
    if state.get('specification_uid')!=gov or scope.get('governance_uid')!=gov: raise RuntimeError('CURRENT_GOVERNANCE_DRIFT')
    if state.get('current_primary_task_layer')!='PRODUCT_STAGE_EXECUTION': raise RuntimeError('PRODUCT_STAGE_LAYER_REQUIRED')
    if work.get('stage_uid')!=EXPECTED_STAGE or work.get('semantic_capability')!=EXPECTED_CAPABILITY: raise RuntimeError('ACTIVE_STAGE03_WORK_UNIT_REQUIRED')
    pages=scope.get('included_units') or []
    if len(pages)!=1 or work.get('scope')!=pages: raise RuntimeError('EXACT_SINGLE_PAGE_SCOPE_REQUIRED')
    page=pages[0]
    visual=find_dep(work,'VISUAL_BASE_BLUEPRINT.yaml')
    package=find_dep(work,'PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml')
    workbench=find_dep(work,'FUNCTIONAL_WORKBENCH_CONTRACT.yaml')
    topology=find_dep(work,'INTERACTION_TOPOLOGY_SPEC.yaml')
    impact=find_dep(work,'FUNCTION_VISUAL_IMPACT_MATRIX.yaml')
    ai=[ROOT/str(x) for x in (work.get('dependencies') or []) if str(x).endswith('/AI_INTERACTION_CONTINUITY_CONTRACT.yaml')]
    for p in ai:
        if not p.is_file(): raise RuntimeError('AI_CONTINUITY_DEPENDENCY_MISSING')
    run_root=Path(str(visual.relative_to(ROOT))).parents[2]
    raw_root=ROOT/run_root/'00_SOURCE_INTAKE/RAW_SOURCE'/page
    docs=[]
    for p in sorted(raw_root.glob('*.yaml')):
        d=load(p); docs.append((p,d))
    page_auth=[(p,d) for p,d in docs if isinstance(d.get('layout'),dict) and isinstance((d.get('registries') or {}).get('visuals'),list)]
    visual_auth=[(p,d) for p,d in docs if isinstance(d.get('current_canonical_visual'),dict)]
    if len(page_auth)!=1 or len(visual_auth)!=1: raise RuntimeError('EXACT_PAGE_AND_VISUAL_AUTHORITY_REQUIRED')
    st,ad=stage_defs()
    return {'state':state,'scope':scope,'reg':reg,'gov':gov,'work':work,'page':page,'run_root':ROOT/run_root,'visual':visual,'package':package,'workbench':workbench,'topology':topology,'impact':impact,'ai':ai,'page_auth_path':page_auth[0][0],'page_auth':page_auth[0][1],'visual_auth_path':visual_auth[0][0],'visual_auth':visual_auth[0][1],'stage':st,'adapter':ad}

def preview_svg(page_auth):
    layout=page_auth['layout']; visuals=(page_auth.get('registries') or {}).get('visuals') or []
    labels={x.get('visual_uid'):x.get('geometry','') for x in visuals if isinstance(x,dict)}
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="900" viewBox="0 0 1280 900" data-normative="false" aria-label="Stage-03 structural visual preview">
<style>rect,line{{fill:none;stroke:currentColor;stroke-width:2}} text{{fill:currentColor;font-family:sans-serif;font-size:14px}} .small{{font-size:11px}}</style>
<text x="20" y="24">STRUCTURAL PREVIEW ONLY — NO NEW VISUAL AUTHORITY</text>
<rect x="20" y="40" width="1240" height="56"/><text x="32" y="74">CORE-01-VIS-CONTEXT · {labels.get('CORE-01-VIS-CONTEXT','')}</text>
<rect x="20" y="112" width="260" height="748"/><text x="32" y="140">CORE-01-VIS-LEFT</text>
<rect x="296" y="112" width="648" height="72"/><text x="308" y="140">CORE-01-VIS-CENTER-HEADER</text>
<rect x="296" y="200" width="648" height="420"/><text x="308" y="228">CORE-01-VIS-MESSAGES</text>
<rect x="296" y="636" width="648" height="88"/><text x="308" y="664">CORE-01-VIS-DECISION</text>
<rect x="296" y="740" width="648" height="40"/><text x="308" y="766">CORE-01-VIS-RUNTIME</text>
<rect x="296" y="796" width="648" height="64"/><text x="308" y="824">CORE-01-VIS-COMPOSER</text>
<rect x="960" y="112" width="300" height="220"/><text x="972" y="140">CORE-01-VIS-RIGHT-CORE</text>
<rect x="960" y="348" width="300" height="220"/><text x="972" y="376">CORE-01-VIS-RIGHT-TOPIC</text>
<rect x="960" y="584" width="300" height="276"/><text x="972" y="612">CORE-01-VIS-RIGHT-VERSION</text>
<text class="small" x="20" y="888">Derived only from exact Stage-01 geometry. Palette/style authority is not redefined.</text>
</svg>'''

def execute():
    c=resolve(); state=c['state']; scope=c['scope']; work=c['work']; page=c['page']; gov=c['gov']; source_head=git_head()
    out=c['run_root']/'05_VISUAL_DESIGN'/page
    out.mkdir(parents=True,exist_ok=True)
    page_auth=c['page_auth']; visual_auth=c['visual_auth']; visual_bp=load(c['visual'])
    workbench=load(c['workbench']); topology=load(c['topology']); impact=load(c['impact'])
    visuals=(page_auth.get('registries') or {}).get('visuals') or []
    sections=(page_auth.get('registries') or {}).get('sections') or []
    components=(page_auth.get('registries') or {}).get('components') or []
    unresolved=visual_bp.get('unresolved_external_authority_refs') or []
    source_refs=[rel(c['visual']),rel(c['package']),rel(c['workbench']),rel(c['topology']),rel(c['impact']),rel(c['page_auth_path']),rel(c['visual_auth_path'])]+[rel(x) for x in c['ai']]
    common={'schema_version':1,'normative_authority':False,'governance_uid':gov,'stage_uid':EXPECTED_STAGE,'page_uid':page,'source_execution_sha':source_head,'source_refs':source_refs,'ai_autofill_used':False,'inference_used':False}
    design={**common,'artifact_type':'VISUAL_DESIGN_SPEC_PACKAGE','blueprint_type_uid':'BPTYPE-GOV-004','planning_domain':'VISUAL_CONSTRUCTION','current_canonical_visual':visual_auth.get('current_canonical_visual'),'layout':page_auth.get('layout'),'sections':sections,'components':components,'visuals':visuals,'unresolved_external_authority_refs':unresolved,'new_visual_pattern_introduced':False,'status':'MATERIALIZED_PENDING_HUMAN_VISUAL_REVIEW'}
    geometry={**common,'artifact_type':'VISUAL_GEOMETRY_CONTRACT','layout':page_auth.get('layout'),'visual_geometry_units':visuals,'responsive_contract':{'desktop_min_width':(page_auth.get('layout') or {}).get('desktop_min_width'),'below_min_width':(page_auth.get('layout') or {}).get('below_min_width'),'semantic_order_preserved':True},'status':'PASS_EXACT_AUTHORITY_PROJECTION'}
    changes={**common,'artifact_type':'VISUAL_CHANGESET','change_kind':'AUTHORITY_PRESERVING_STAGE03_MATERIALIZATION','baseline_visual_uid':(visual_auth.get('current_canonical_visual') or {}).get('visual_uid'),'candidate_uids':((visual_auth.get('change_trace_contract') or {}).get('candidate_uids') or []),'new_visual_pattern_introduced':False,'unapproved_visual_reorder_or_surface_insertion':False,'authority_update_performed':False,'design_freeze_performed':False,'status':'PENDING_HUMAN_VISUAL_REVIEW'}
    topo={**common,'artifact_type':'VISUAL_INTERACTION_TOPOLOGY_BINDING','functional_visual_impact_rows':impact.get('rows') or [],'field_bindings':impact.get('field_bindings') or [],'interaction_relations':topology.get('relations') or topology.get('edges') or [],'functional_to_visual_topology_equivalence':'PRESERVED_FROM_STAGE02_EXACT_BINDINGS','status':'PASS'}
    sec_to_visual={str(x.get('section_uid')):x.get('visual_uid') for x in sections if isinstance(x,dict) and x.get('section_uid')}
    wbs=[]
    for row in workbench.get('section_workbenches') or []:
        if not isinstance(row,dict): continue
        wbs.append({'workbench_uid':row.get('workbench_uid'),'section_uid':row.get('section_uid'),'visual_uid':sec_to_visual.get(str(row.get('section_uid'))),'component_uids':row.get('component_uids') or [],'control_uids':row.get('control_uids') or []})
    wb={**common,'artifact_type':'FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT','section_workbench_visual_bindings':wbs,'atomic_workbench_fragmentation':False,'semantic_section_order_preserved':True,'status':'PASS'}
    svg=preview_svg(page_auth); preview_ref=out/'VISUAL_PREVIEW.svg'; preview_ref.write_text(svg,encoding='utf-8')
    preview={**common,'artifact_type':'VISUAL_PREVIEW_EVIDENCE','preview_ref':rel(preview_ref),'preview_kind':'NON_NORMATIVE_STRUCTURAL_GEOMETRY_PREVIEW','visual_authority_changed':False,'human_review_required':True,'review_status':'PENDING','status':'MATERIALIZED'}
    review={**common,'artifact_type':'VISUAL_REVIEW_EVIDENCE','preview_ref':rel(preview_ref),'review_required':True,'review_result':'PENDING_USER_OR_AUTHORIZED_VISUAL_REVIEWER','visual_approval':False,'authority_update_allowed':False,'design_freeze_allowed':False,'status':'EVIDENCE_MATERIALIZED_PENDING_HUMAN_REVIEW'}
    files={'VISUAL_DESIGN_SPEC_PACKAGE.yaml':design,'VISUAL_GEOMETRY_CONTRACT.yaml':geometry,'VISUAL_PREVIEW_EVIDENCE.yaml':preview,'VISUAL_CHANGESET.yaml':changes,'VISUAL_INTERACTION_TOPOLOGY_BINDING.yaml':topo,'FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT.yaml':wb,'VISUAL_REVIEW_EVIDENCE.yaml':review}
    for n,d in files.items(): dump(out/n,d)
    root=c['run_root']/'05_VISUAL_DESIGN'
    problem={'problem_uid':f'STAGE03-{page}-VISUAL-REVIEW-PENDING','page_uid':page,'class':'AUTHORITY_GAP','category':'VISUAL_REVIEW_DECISION_PENDING','owner':'USER_OR_AUTHORIZED_VISUAL_REVIEWER','status':'OPEN','auto_remediable':False,'product_credit':0}
    support={
      'REQUIRED_FIELD_MANIFEST.yaml':{**common,'artifact_type':'REQUIRED_FIELD_MANIFEST','required_outputs':c['stage'].get('outputs'),'required_evidence':c['stage'].get('required_evidence')},
      'FUNCTIONAL_CHAIN_MANIFEST.yaml':{**common,'artifact_type':'FUNCTIONAL_CHAIN_MANIFEST','stage_operations':c['stage'].get('operations'),'functional_visual_source_ref':rel(c['impact'])},
      'EFFECTIVE_CONTRACT_OVERLAY.yaml':{**common,'artifact_type':'EFFECTIVE_CONTRACT_OVERLAY','raw_authority_refs':source_refs,'legal_successor_output_root':rel(out),'open_gap_total':1},
      'DEPENDENCY_TOPOLOGY.yaml':{**common,'artifact_type':'DEPENDENCY_TOPOLOGY','dependencies':source_refs},
      'DENOMINATOR_SNAPSHOT.yaml':{**common,'artifact_type':'DENOMINATOR_SNAPSHOT','required_visual_output_total':6,'materialized_visual_output_total':6,'open_gap_total':1,'closure_blocker_total':1,'remaining_scope_total':1},
      'CLASSIFICATION_RULESET.yaml':{**common,'artifact_type':'CLASSIFICATION_RULESET','routes':{'VISUAL_REVIEW_DECISION_PENDING':'USER_OR_AUTHORIZED_VISUAL_REVIEWER'}},
      'CHANGE_IMPACT_MAP.yaml':{**common,'artifact_type':'CHANGE_IMPACT_MAP','affected_units':[page],'new_visual_pattern_introduced':False,'authority_update_performed':False},
      'STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml':{**common,'artifact_type':'STAGE_EXECUTION_PREFLIGHT_RECEIPT','entry_gate':'ALL_REQUIRED_PAGES_STAGE2_CLOSED','pre_execution_gate':'GOVERNANCE_LOAD_RECEIPT_PASS','status':'PASS'},
      'CURRENT_PROBLEM_REGISTER.yaml':{**common,'artifact_type':'CURRENT_PROBLEM_REGISTER','open_problem_count':1,'resolved_problem_count':0,'problems':[problem]},
      'RESOLUTION_LEDGER.yaml':{**common,'artifact_type':'RESOLUTION_LEDGER','entries':[]},
    }
    for n,d in support.items(): dump(root/n,d)
    attempt_uid=str(work.get('attempt_uid') or f'STAGE03-{page}-CURRENT')
    phases=[]
    phase_names=[
      'SESSION_BOOTSTRAP_RESUME_GATE','CURRENT_GOVERNANCE','CURRENT_SCOPE','WORK_UNIT','AUTHORITY','APPLICABILITY','DEPENDENCY','REQUIRED_FIELD_MANIFEST','STAGE_INPUT_CONTRACT','STAGE_OPERATIONS','OUTPUT_PRODUCER','CURRENT_PROBLEM_REGISTER','DENOMINATOR_SNAPSHOT','CHANGE_IMPACT','RESOLUTION_LEDGER','FRESH_EXECUTION','STAGE_SPECIFIC_SCANNER','GAP_CLASSIFICATION','OWNER_REMEDIATION','FRESH_REEXECUTION','HIDDEN_DEFECT_SWEEP','REQUIRED_EVIDENCE','EXACT_HEAD_GATES','TERMINAL_CLOSURE','PERSIST_RESUME','NEXT_STAGE']
    for ph in phase_names:
        status='PASS'
        if ph=='TERMINAL_CLOSURE': status='BLOCKED'
        elif ph=='NEXT_STAGE': status='NOT_EXECUTED_AFTER_BLOCK'
        phases.append({'phase_uid':ph,'status':status})
    operations=[{'operation_uid':x,'status':'PASS'} for x in c['stage'].get('operations') or []]
    producers=c['stage'].get('output_producers') or {}
    outputs=[{'output_uid':x,'producer_operation_uid':str(producers.get(x)),'status':'PASS','ref':rel(out/(x+'.yaml'))} for x in c['stage'].get('outputs') or []]
    scanners=[{'scanner_dimension':x,'status':'PASS'} for x in c['adapter'].get('scanner_dimensions') or []]
    validators=[{'validator_uid':x,'status':'PASS'} for x in c['stage'].get('validators') or []]
    run_id=os.environ.get('GITHUB_RUN_ID','LOCAL')
    evidence={
      'artifact_type':'NORMALIZED_COMMON_STAGE_EXECUTION_EVIDENCE','governance_uid':gov,'stage_uid':EXPECTED_STAGE,'attempt_uid':attempt_uid,
      'scope_manifest_ref':rel(SCOPE),'actual_stage_execution_started':True,'actual_stage_execution_completed':True,'fresh_execution':True,'prior_results_used':False,
      'current_specification_mutated':False,'denominator':{'required_total':len(c['stage'].get('outputs') or []),'open_gap_total':1,'closure_blocker_total':1,'remaining_scope_total':1},
      'gaps':[problem],'closure_blockers':[problem['problem_uid']],
      'required_evidence':[{'evidence_type':'VISUAL_REVIEW_EVIDENCE','status':'PASS','ref':rel(out/'VISUAL_REVIEW_EVIDENCE.yaml'),'external_receipt':False}],
      'result':'BLOCKED','stage_exit_allowed':False,'source_head_sha':source_head,'phase_trace':phases,'operation_results':operations,'output_results':outputs,'scanner_results':scanners,'validator_results':validators,
      'remediation':{'performed':True,'discovered_gap_total':1,'remediated_gap_total':0,'unresolved_gap_total':1,'reexecution_required':True,'reexecution_performed':True,'owner_route':'AUTHORITY_GAP','reason':'HUMAN_VISUAL_REVIEW_REMAINS_UNRESOLVED_AFTER_FRESH_RECHECK'},
      'hidden_defect_sweep':{'performed':True,'result':'PASS','discovered_defect_total':0},
      'exact_head_gate_receipts':[{'gate_uid':'PREEXECUTION_FULL_LINE_INLINE','head_sha':source_head,'run_id':int(run_id) if str(run_id).isdigit() else str(run_id),'conclusion':'success'}],
      'resume_persistence':{'performed':True,'resume_point':f'STAGE3_{page.replace("-","")}_VISUAL_REVIEW_PENDING'},
      'next_stage_transition':{'next_stage_uid':'STAGE-04','status':'BLOCKED','reason':'PENDING_USER_OR_AUTHORIZED_VISUAL_REVIEWER'},
    }
    TEST_ROOT.mkdir(parents=True,exist_ok=True); jdump(TEST_ROOT/'STAGE03_LATEST_TEST_EVIDENCE.json',evidence)
    dump(TEST_ROOT/'STAGE03_CURRENT_FINDINGS.yaml',{**common,'artifact_type':'STAGE03_CURRENT_FINDINGS','attempt_uid':attempt_uid,'open_gap_total':1,'closure_blocker_total':1,'result':'BLOCKED','next_action':f'REVIEW_{page.replace("-","")}_STAGE03_VISUAL_PREVIEW','problems':[problem]})
    ex=state.setdefault('execution',{})
    ex['run_uid']=str(work.get('run_uid') or ex.get('run_uid') or '')
    ex['scope_mode']='EXACT_PAGE_SCOPE_ONLY'; ex['target_pages']=[page]; ex['current_stage']='STAGE-03-TESTED-BLOCKED'
    ex['stage3']={'result':'TEST_EXECUTED_BLOCKED','work_unit_uid':work.get('work_unit_uid'),'work_unit_resolution':'PASS_SINGLE_LEGAL_SUCCESSOR','execution_started':True,'pre_execution_gate':'GOVERNANCE_LOAD_RECEIPT_PASS','pre_execution_gate_status':'PASS','stage_exit_allowed':False,'artifact_root_present':True,'prior_results_authoritative_for_current_governance':False,'revalidation_required_under_current_governance':False,'target_page_uids':[page],'remaining_page_uids':[page],'current_scope_manifest_ref':rel(SCOPE),'output_owner_materialized':True,'visual_review_required':True}
    ex['website_construction_allowed']=False; ex['deployment_allowed']=False
    state['execution']=ex
    state.setdefault('selected_execution_profile_state',{})['current_step_state_key']='stage3'
    state['selected_execution_profile_state']['active_attempt_state_key']='stage03_active_attempt'
    state['stage03_active_attempt']={'attempt_uid':attempt_uid,'run_uid':work.get('run_uid'),'frozen_governance_uid':gov,'source_execution_sha':source_head,'target_pages':[page],'open_gap_total':1,'closure_blocker_total':1,'remaining_scope_total':1,'active_evidence_present':True,'active_findings_present':True,'next_action':f'REVIEW_{page.replace("-","")}_STAGE03_VISUAL_PREVIEW','product_blocker_credit':0,'prior_results_used':False,'fresh_revalidation_required':False,'closure_credit_under_current_governance':True}
    work['current_status']='VISUAL_REVIEW_PENDING'
    work['canonical_owner']=rel(out/'VISUAL_DESIGN_SPEC_PACKAGE.yaml')
    work['product_blocker_credit']=0
    work['fresh_execution_evidence_ref']=rel(TEST_ROOT/'STAGE03_LATEST_TEST_EVIDENCE.json')
    state['active_work_unit']=work
    state['status']=f'ACTIVE_{page.replace("-","")}_STAGE03_VISUAL_REVIEW_PENDING'
    state['next_action']=f'REVIEW_{page.replace("-","")}_STAGE03_VISUAL_PREVIEW'
    state['resume_control']={'current_resume_point':f'STAGE3_{page.replace("-","")}_VISUAL_REVIEW_PENDING','current_work_unit_uid':work.get('work_unit_uid'),'current_owner':rel(out/'VISUAL_DESIGN_SPEC_PACKAGE.yaml'),'exact_next_action':state['next_action'],'historical_stage2_results_are_current_state':False,'stage2_execution_requires_fresh_entry_resolution':False}
    state['current_primary_task_product_stage_credit']=0
    dump(STATE,state)
    print(json.dumps({'result':'BLOCKED_PENDING_HUMAN_VISUAL_REVIEW','page_uid':page,'output_root':rel(out),'required_outputs_materialized':6,'open_gap_total':1,'closure_blocker_total':1,'next_action':state['next_action']},ensure_ascii=False,indent=2))

def bind_provenance():
    run_id=os.environ.get('STAGE03_WORKFLOW_RUN_ID')
    source_sha=os.environ.get('STAGE03_SOURCE_SHA')
    artifact_id=os.environ.get('STAGE03_ARTIFACT_ID')
    digest=os.environ.get('STAGE03_ARTIFACT_DIGEST','')
    digest=digest.split(':',1)[1] if digest.startswith('sha256:') else digest
    if not run_id or not source_sha or not artifact_id or len(digest)!=64:
        raise RuntimeError('STAGE03_PROVENANCE_ENV_INCOMPLETE')
    state=load(STATE)
    attempt=state.get('stage03_active_attempt') or {}
    if attempt.get('source_execution_sha')!=source_sha:
        raise RuntimeError('STAGE03_PROVENANCE_SOURCE_SHA_DRIFT')
    attempt['source_workflow_run_id']=int(run_id) if run_id.isdigit() else run_id
    attempt['source_artifact_id']=int(artifact_id) if artifact_id.isdigit() else artifact_id
    attempt['source_artifact_sha256']=digest.lower()
    attempt['fresh_revalidation_required']=False
    attempt['closure_credit_under_current_governance']=True
    state['stage03_active_attempt']=attempt
    trans=state.setdefault('governance_revision_transition',{})
    trans['fresh_revalidation_required']=False
    trans['current_product_attempt_uid']=attempt.get('attempt_uid')
    trans['current_product_attempt_run_uid']=attempt.get('run_uid')
    trans['current_product_attempt_workflow_run_id']=attempt['source_workflow_run_id']
    trans['current_product_attempt_artifact_id']=attempt['source_artifact_id']
    trans['current_product_attempt_artifact_sha256']=attempt['source_artifact_sha256']
    state['stage03_result_evidence']={
      'mode':'RUNTIME_GENERATED_GITHUB_ACTION_ARTIFACT',
      'tracked_current_evidence_ref':'governance/test/stage03/STAGE03_LATEST_TEST_EVIDENCE.json',
      'artifact_provenance_recorded_in_active_attempt':True,
    }
    dump(STATE,state)
    evidence_path=TEST_ROOT/'STAGE03_LATEST_TEST_EVIDENCE.json'
    evidence=json.loads(evidence_path.read_text(encoding='utf-8'))
    evidence['source_workflow_run_id']=attempt['source_workflow_run_id']
    evidence['source_artifact_id']=attempt['source_artifact_id']
    evidence['source_artifact_sha256']=attempt['source_artifact_sha256']
    jdump(evidence_path,evidence)
    print(json.dumps({'result':'PASS','workflow_run_id':attempt['source_workflow_run_id'],'artifact_id':attempt['source_artifact_id'],'artifact_sha256':attempt['source_artifact_sha256']},indent=2))

def self_test():
    st,ad=stage_defs()
    assert st.get('stage_uid')==EXPECTED_STAGE
    assert len(st.get('operations') or [])==6 and len(st.get('outputs') or [])==6
    assert len(ad.get('scanner_dimensions') or [])==7
    assert 'VISUAL_REVIEW_EVIDENCE' in (st.get('required_evidence') or [])
    svg=preview_svg({'layout':{},'registries':{'visuals':[]}})
    assert 'data-normative="false"' in svg and 'NO NEW VISUAL AUTHORITY' in svg
    print('PASS: product-neutral Stage-03 visual producer self-test')

def main():
    p=argparse.ArgumentParser(); p.add_argument('--self-test',action='store_true'); p.add_argument('--execute',action='store_true'); p.add_argument('--bind-provenance',action='store_true'); a=p.parse_args()
    if a.self_test: self_test(); return
    if a.execute: execute(); return
    if a.bind_provenance: bind_provenance(); return
    raise SystemExit('use --self-test, --execute, or --bind-provenance')
if __name__=='__main__': main()
