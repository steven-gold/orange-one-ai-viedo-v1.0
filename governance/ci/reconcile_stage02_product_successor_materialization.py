#!/usr/bin/env python3
from __future__ import annotations
import ast, json, re, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
PRODUCT = RUN / '04_PAGE_FUNCTIONAL_CONTRACT'
HISTORICAL_REPLAY_REF = '94b83f60716be3fc138790781357b22b084cb24e'
CURRENT_UID = 'GOV-REV-20260915-STAGE-EXECUTION-OPTIMIZATION'
RAW = {
    'CORE-01': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
    'ASSET-01': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
}
RAW_BLOBS = {'CORE-01':'9490f3bcc28c5511bc04d6c3ce53c026e3c4667f','ASSET-01':'9668e2307c722ea4cf64f93f07c92da1b3abcc28'}
BLUEPRINT = {p: RUN / f'02_BASE_BLUEPRINT/{p}/PAGE_BASE_BLUEPRINT.yaml' for p in RAW}
LEDGER = {p: PRODUCT / f'{p}/AUTO_COMPLETION_SCOPE_LEDGER.yaml' for p in RAW}
SCANNER = ROOT / 'governance/ci/run_current_stage2_actual_test.py'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
LATEST = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
FINDINGS = ROOT / 'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
REPLAY = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_ONLY_REPLAY_V215_R1.yaml'
CANDIDATES = ROOT / 'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
FIND028 = ROOT / 'governance/test/stage02/FIND-20260915-028_STAGE02_REMEDIATION_SUCCESSOR_STATE_MODEL.yaml'
STAGE_REGISTRY = ROOT / '.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
SPEC_MANIFEST = ROOT / 'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'
EXPECTED_GAPS = {f'GAP-{i:03}' for i in range(1,9)}
REQUIRED_STRUCTURAL = {
  'CORE-01': ['BUSINESS_ENTITY_INVENTORY.yaml','BUSINESS_ENTITY_OPERATION_MATRIX.yaml','ENTITY_HIERARCHY_MATRIX.yaml','FUNCTIONAL_WORKBENCH_CONTRACT.yaml','INTERACTION_TOPOLOGY_SPEC.yaml','FUNCTION_VISUAL_IMPACT_MATRIX.yaml','AI_INTERACTION_CONTINUITY_CONTRACT.yaml'],
  'ASSET-01': ['BUSINESS_ENTITY_INVENTORY.yaml','BUSINESS_ENTITY_OPERATION_MATRIX.yaml','ENTITY_HIERARCHY_MATRIX.yaml','FUNCTIONAL_WORKBENCH_CONTRACT.yaml','INTERACTION_TOPOLOGY_SPEC.yaml','FUNCTION_VISUAL_IMPACT_MATRIX.yaml'],
}
ALLOWED_PRODUCT = {'STATE_TRANSITION_LEDGER_FIELD_MISSING','SUCCESS_NEXT_STATE_BINDING_MISSING','POST_ACTION_VALIDATION_NODE_MISSING'}


def die(msg):
    print('BLOCK:', msg, file=sys.stderr); raise SystemExit(1)

def yload(path):
    if not path.is_file(): die(f'MISSING:{path.relative_to(ROOT)}')
    obj=yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(obj,dict): die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj

def git(*args):
    return subprocess.run(['git',*args],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()

def sig(page,g): return (page,g.get('category'),str(g.get('uid')),g.get('detail'))

def scanner_fn():
    tree=ast.parse(SCANNER.read_text(encoding='utf-8'),filename=str(SCANNER))
    keep={'idx','present','event_token','has_transition','add','fresh_scan'}; nodes=[]
    for n in tree.body:
        if isinstance(n,ast.Assign) and 'KNOWN_AUTHORITIES' in {t.id for t in n.targets if isinstance(t,ast.Name)}: nodes.append(n)
        elif isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in keep: nodes.append(n)
    found={n.name for n in nodes if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    if found!=keep: die(f'SCANNER_EXTRACTION_DRIFT:{sorted(found)}')
    mod=ast.Module(body=nodes,type_ignores=[]); ast.fix_missing_locations(mod)
    ns={'Counter':Counter,'defaultdict':defaultdict,'re':re}; exec(compile(mod,str(SCANNER),'exec'),ns,ns)
    return ns['fresh_scan']

# Exact immutable input identity: replay is forbidden if either Raw Source blob changed.
for page,path in RAW.items():
    rel=str(path.relative_to(ROOT)); actual=git('rev-parse',f'HEAD:{rel}')
    if actual!=RAW_BLOBS[page]: die(f'{page}:RAW_BLOB_DRIFT:{actual}')
state=yload(STATE)
if state.get('specification_uid')!=CURRENT_UID: die('CURRENT_GOVERNANCE_UID_DRIFT')
if (state.get('execution') or {}).get('current_stage')!='STAGE-02-TESTED-BLOCKED': die('REPLAY_REQUIRES_STAGE02_TESTED_BLOCKED')

# No historical external-authority projection may be restored into the product-only replay.
for forbidden in [PRODUCT/'EXTERNAL_AUTHORITY', PRODUCT/'SHARED_OWNER_PORT_MAP.yaml', PRODUCT/'SHARED_OWNER_PORT_MAP_R2.yaml', PRODUCT/'SHARED_OWNER_PORT_MAP_R3.yaml']:
    if forbidden.exists(): die(f'EXTERNAL_AUTHORITY_REPLAY_FORBIDDEN:{forbidden.relative_to(ROOT)}')

# Structural closure must be physical, page scoped, and complete.
structural_missing={}
for page,names in REQUIRED_STRUCTURAL.items():
    structural_missing[page]=[n for n in names if not (PRODUCT/page/n).is_file()]
if any(structural_missing.values()): die(f'STRUCTURAL_OUTPUTS_STILL_MISSING:{structural_missing}')

# Rebind non-normative replay ledgers to the currently frozen governance UID without changing closure values.
ledgers={}; product={}
expected_counts={'CORE-01':5,'ASSET-01':27}
expected_category_counts={'CORE-01':Counter({'STATE_TRANSITION_LEDGER_FIELD_MISSING':5}), 'ASSET-01':Counter({'POST_ACTION_VALIDATION_NODE_MISSING':15,'SUCCESS_NEXT_STATE_BINDING_MISSING':7,'STATE_TRANSITION_LEDGER_FIELD_MISSING':5})}
for page,path in LEDGER.items():
    d=yload(path); rows=d.get('remediations') or []
    if d.get('artifact_type')!='AUTO_COMPLETION_SCOPE_LEDGER' or d.get('page_uid')!=page: die(f'{page}:LEDGER_IDENTITY_DRIFT')
    if len(rows)!=expected_counts[page]: die(f'{page}:PRODUCT_SIGNATURE_COUNT:{len(rows)}')
    cats=Counter((r.get('defect_signature') or {}).get('category') for r in rows)
    if cats!=expected_category_counts[page]: die(f'{page}:PRODUCT_CATEGORY_DRIFT:{dict(cats)}')
    for r in rows:
        ds=r.get('defect_signature') or {}; cat=ds.get('category')
        if cat not in ALLOWED_PRODUCT: die(f'{page}:UNAPPROVED_PRODUCT_CATEGORY:{cat}')
        if r.get('external_authority_resolution_performed') is not False: die(f'{page}:EXTERNAL_AUTHORITY_RESOLUTION_PRESENT:{r.get("remediation_uid")}')
        if r.get('semantic_inference_used') is not False or r.get('ai_invented_business_value') is not False: die(f'{page}:INFERRED_OR_INVENTED_VALUE:{r.get("remediation_uid")}')
        key=(page,cat,str(ds.get('uid')),ds.get('detail'))
        if key in product: die(f'DUPLICATE_PRODUCT_SIGNATURE:{key}')
        product[key]=r
    d['frozen_governance_uid']=CURRENT_UID
    d['replay_provenance']={'source_ref':HISTORICAL_REPLAY_REF,'current_raw_blob_sha':RAW_BLOBS[page],'fresh_revalidation_required':True,'historical_result_not_authoritative':True,'external_authority_elimination_allowed':False}
    d['latest_bounded_completion_cycle']='V215_PRODUCT_ONLY_REPLAY_R1_FRESH_REVALIDATION'
    path.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
    ledgers[page]=d
if len(product)!=32: die(f'PRODUCT_SIGNATURE_DENOMINATOR:{len(product)}')

# Fresh raw discovery from the current canonical scanner. Historical counts do not populate this result.
scan=scanner_fn(); raw_scans={}; raw_signatures={}; raw_categories=Counter(); raw_classes=Counter()
for page,path in RAW.items():
    r=scan(page,yload(path)); raw_scans[page]=r
    for g in r.get('gaps') or []:
        k=sig(page,g)
        if k in raw_signatures: die(f'DUPLICATE_RAW_SIGNATURE:{k}')
        raw_signatures[k]=g; raw_categories[g.get('category')]+=1; raw_classes[g.get('class')]+=1
if len(raw_signatures)!=150: die(f'FRESH_RAW_DENOMINATOR_DRIFT:{len(raw_signatures)}')
missing_product=set(product)-set(raw_signatures)
if missing_product: die(f'REPLAY_SIGNATURE_NOT_PRESENT_IN_CURRENT_RAW:{sorted(missing_product)}')
remaining={k:g for k,g in raw_signatures.items() if k not in product}
effective_categories=Counter(g.get('category') for g in remaining.values()); effective_classes=Counter(g.get('class') for g in remaining.values())
if len(remaining)!=118: die(f'EFFECTIVE_DENOMINATOR_NOT_FRESHLY_118:{len(remaining)}')
if effective_categories.get('SHARED_OWNER_AUTHORITY_UNRESOLVED')!=4: die('EXTERNAL_GAP006_WAS_NOT_PRESERVED_AS_FOUR_RAW_GAPS')
if effective_categories.get('PAYLOAD_INPUT_CONTRACT_MISSING')!=34: die('PAYLOAD_INPUT_34_MUST_REMAIN_UNRESOLVED')
if effective_categories.get('STATE_TRANSITION_LEDGER_FIELD_MISSING')!=40: die('UNSAFE_TRANSITION_FIELDS_MUST_REMAIN_40')
if effective_categories.get('POST_ACTION_VALIDATION_NODE_MISSING')!=3: die('POST_ACTION_REMAINDER_MUST_BE_3')
if effective_categories.get('SUCCESS_NEXT_STATE_BINDING_MISSING',0)!=0: die('SEVEN_EXACT_SUCCESS_NEXT_STATE_SIGNATURES_NOT_CLOSED')

# External authority union is re-proved directly from immutable Stage-01 blueprints.
union=set(); external={}
for page,path in BLUEPRINT.items():
    bp=yload(path); refs=bp.get('unresolved_external_authority_refs') or []
    for ref in refs:
        gid=ref.get('gap_uid'); union.add(gid)
        if any(ref.get(k) is not False for k in ('resolved','satisfied','auto_filled','inferred')): die(f'{page}:FALSE_EXTERNAL_AUTHORITY_RESOLUTION:{gid}')
        external.setdefault(gid,{'authority_ref':ref.get('authority_ref'),'consumers':[]})['consumers'].append(page)
if union!=EXPECTED_GAPS: die(f'EXTERNAL_AUTHORITY_UNION_DRIFT:{sorted(union)}')

registry=yload(STAGE_REGISTRY); manifest=yload(SPEC_MANIFEST)
stage2=[x for x in (registry.get('stages') or []) if x.get('stage_uid')=='STAGE-02']
if len(stage2)!=1: die('STAGE02_REGISTRY_DENOMINATOR')
official=stage2[0].get('outputs') or []; mandatory=((manifest.get('stage02_applicability') or {}).get('always_for_target_page_stage02') or [])
if len(official)!=17 or len(set(official))!=17: die('OFFICIAL_STAGE02_OUTPUT_DENOMINATOR_DRIFT')
if len(mandatory)!=12 or not set(mandatory)<=set(official): die('MANDATORY_STAGE02_OUTPUT_SUBSET_DRIFT')

head=git('rev-parse','HEAD')
pages={}
for page in RAW:
    rraw=raw_scans[page]; er=[g for k,g in remaining.items() if k[0]==page]; ec=Counter(g.get('category') for g in er); ecl=Counter(g.get('class') for g in er)
    pages[page]={
      'blueprint_uid': yload(BLUEPRINT[page]).get('blueprint_uid'),
      'functional_chain_fresh_scan': rraw,
      'validated_product_successor_signature_count': sum(1 for k in product if k[0]==page),
      'effective_functional_gap_count': len(er),
      'effective_gap_categories': dict(sorted(ec.items())),
      'effective_gap_classes': dict(sorted(ecl.items())),
      'closure_blockers': [], 'closure_blocker_count':0,
    }
reexecution={
 'schema_version':2,'artifact_type':'NON_NORMATIVE_STAGE02_ACTUAL_TEST_EVIDENCE','normative_authority':False,
 'stage_uid':'STAGE-02','stage_name':'PAGE_FUNCTIONAL_CONTRACT','source_head_sha':head,
 'test_mode':'FRESH_RAW_DISCOVERY_PLUS_CURRENT_PRODUCT_SUCCESSOR_RECONCILIATION_NO_EXTERNAL_AUTHORITY_ELIMINATION',
 'actual_product_stage_test_started':True,'actual_product_stage_test_completed':True,'stage_entry_gate':'PASS','stage_exit_allowed':False,'result':'BLOCKED',
 'official_stage_output_denominator':sorted(official),'current_manifest_mandatory_stage_output_subset':sorted(mandatory),
 'physical_stage2_product_artifact_root_present':True,'pages':pages,
 'fresh_functional_gap_total':len(raw_signatures),'validated_product_successor_signature_count':len(product),'validated_external_authority_elimination_count':0,
 'effective_functional_gap_total':len(remaining),'fresh_effective_gap_categories':dict(sorted(effective_categories.items())),'fresh_effective_gap_classes':dict(sorted(effective_classes.items())),
 'closure_blocker_total':0,'preserved_external_authorities':dict(sorted(external.items())),'preserved_external_authority_union_count':len(union),'preserved_external_authority_union_gap_uids':sorted(union),
 'current_specification_mutated':False,'immutable_stage1_source_mutated':False,'ai_autofill_used':False,'inference_used':False,'prior_stage2_results_used':False,
 'historical_validated_materialization_used_only_as_replay_candidate':True,'historical_replay_source_ref':HISTORICAL_REPLAY_REF,
 'website_construction_allowed':False,'deployment_allowed':False,
 'notes':['Raw discovery remains 150 by design; effective remediation is evaluated separately.','Exactly 32 product-only successor signatures were freshly revalidated against unchanged Stage-1 Raw Source.','All GAP-001..GAP-008 external authority references remain unresolved; external authority elimination count is zero.']
}
LATEST.write_text(json.dumps(reexecution,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')

receipt={
 'schema_version':1,'artifact_uid':'STAGE02-PRODUCT-ONLY-REPLAY-V215-R1','artifact_type':'NON_NORMATIVE_STAGE02_MATERIAL_REMEDIATION_EVIDENCE','normative_authority':False,
 'stage_uid':'STAGE-02','frozen_governance_uid':CURRENT_UID,'historical_replay_source_ref':HISTORICAL_REPLAY_REF,'source_head_sha':head,
 'immutable_raw_blob_identity':RAW_BLOBS,'structural_closure':{'prior_closure_blocker_total':13,'current_closure_blocker_total':0,'physical_required_outputs_verified':13},
 'fresh_reconciliation':{'raw_gap_total':150,'validated_product_successor_signature_count':32,'validated_external_authority_elimination_count':0,'effective_gap_total':118,'raw_gap_categories':dict(sorted(raw_categories.items())),'effective_gap_categories':dict(sorted(effective_categories.items())),'raw_gap_classes':dict(sorted(raw_classes.items())),'effective_gap_classes':dict(sorted(effective_classes.items()))},
 'preserved_external_authority_union_gap_uids':sorted(union),'payload_input_unresolved_count':effective_categories.get('PAYLOAD_INPUT_CONTRACT_MISSING',0),'unsafe_transition_field_unresolved_count':effective_categories.get('STATE_TRANSITION_LEDGER_FIELD_MISSING',0),
 'current_specification_mutated':False,'immutable_stage1_source_mutated':False,'stage03_allowed':False,'website_construction_allowed':False,'deployment_allowed':False,
 'next_action':'REMEDIATE_REMAINING_118_EFFECTIVE_FUNCTIONAL_GAPS_WITH_8_EXTERNAL_AUTHORITY_REFS_PRESERVED'
}
REPLAY.write_text(yaml.safe_dump(receipt,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')

# Active state now truthfully records a physical remediation root while keeping Stage-02 blocked.
state['execution']['stage2']['artifact_root_present']=True
active=state.setdefault('stage02_active_attempt',{})
active.update({'material_remediation_started':True,'material_remediation_replay_ref':str(REPLAY.relative_to(ROOT)),'fresh_functional_gap_total':150,'fresh_closure_blocker_total':0,'validated_product_materialization_count':32,'validated_external_authority_elimination_count':0,'effective_functional_gap_total':118,'preserved_external_authority_union_count':8,'product_or_contract_material_remediation_started':True,'next_action':'REMEDIATE_REMAINING_118_EFFECTIVE_FUNCTIONAL_GAPS_WITH_EXTERNAL_AUTHORITY_PRESERVED'})
state['stage02_material_remediation']={'cycle':'V215_PRODUCT_ONLY_REPLAY_R1','owning_layer':'CURRENT_STAGE_PRODUCT_OR_CONTRACT_OUTPUT','material_remediation_started':True,'fresh_structural_blocker_count':0,'raw_discovery_functional_gap_count':150,'validated_product_materialization_count':32,'validated_external_authority_elimination_count':0,'remaining_effective_functional_gap_count':118,'source_external_authority_union_count':8,'all_external_authority_resolved':False,'current_specification_mutated':False}
state['stage02_current_problem_state']={'fresh_functional_gap_total':150,'effective_functional_gap_total':118,'fresh_closure_blocker_total':0,'architecture_gap_total':effective_classes.get('ARCHITECTURE_GAP',0),'input_source_gap_total':effective_classes.get('INPUT_SOURCE_GAP',0),'authority_gap_total':effective_classes.get('AUTHORITY_GAP',0),'external_authority_union_count':8,'current_specification_mutated':False,'immutable_stage1_source_mutated':False,'prior_stage2_results_used':False}
state['status']='ACTIVE_STAGE2_PRODUCT_ONLY_REPLAY_BLOCKED'; state['next_action']='REMEDIATE_REMAINING_118_EFFECTIVE_FUNCTIONAL_GAPS_WITH_EXTERNAL_AUTHORITY_PRESERVED'
STATE.write_text(yaml.safe_dump(state,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')

current_findings={'schema_version':11,'artifact_type':'STAGE02_CURRENT_FINDINGS','normative_authority':False,'stage_uid':'STAGE-02','attempt_uid':active.get('attempt_uid'),'frozen_governance_uid':CURRENT_UID,'source_cycle':'V215_PRODUCT_ONLY_REPLAY_R1','source_head_sha':head,'raw_discovery_gap_total':150,'validated_product_successor_signature_count':32,'validated_external_authority_elimination_count':0,'fresh_effective_gap_total':118,'fresh_closure_blocker_total':0,'raw_gap_categories':dict(sorted(raw_categories.items())),'effective_gap_categories':dict(sorted(effective_categories.items())),'page_results':{p:{'raw_functional_gap_count':pages[p]['functional_chain_fresh_scan']['gap_count'],'validated_product_successor_signature_count':pages[p]['validated_product_successor_signature_count'],'effective_functional_gap_count':pages[p]['effective_functional_gap_count'],'closure_blocker_count':0} for p in pages},'preserved_external_authority_union_count':8,'result':'BLOCKED','current_specification_mutated':False,'immutable_stage1_source_mutated':False,'stage03_allowed':False,'website_construction_allowed':False,'deployment_allowed':False,'next_action':'REMEDIATE_REMAINING_118_EFFECTIVE_FUNCTIONAL_GAPS_WITH_EXTERNAL_AUTHORITY_PRESERVED'}
FINDINGS.write_text(yaml.safe_dump(current_findings,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')

finding={'finding_uid':'FIND-20260915-028','class':'TEST_HARNESS_SUCCESSOR_STATE_BUG','title':'Stage-02 successor-state validator treated every BLOCKED state as audit-only with no materialization root and at least one structural closure blocker','evidence':'Fresh owning-layer remediation can legally close all 13 structural blockers while functional blockers remain; the prior validator rejected both a physical remediation root and BLOCKED with zero structural blockers.','disposition':'RESOLVED_SUCCESSOR_STATE_HARNESS','specification_change_required':False,'formal_specification_mutated_for_fix':False,'current_specification_may_be_modified_from_this_finding_alone':False,'resolution':'Allow a BLOCKED remediation successor to carry a physical Stage-02 materialization root only when material_remediation_started is true; require either effective functional blockers or structural closure blockers to remain. Stage exit, website construction, and deployment stay fail-closed.','stage03_may_advance_before_fix':False}
FIND028.write_text(yaml.safe_dump({'schema_version':1,'artifact_type':'NON_NORMATIVE_TEST_HARNESS_FINDING','normative_authority':False,**finding},allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
ledger=yload(CANDIDATES); findings=ledger.setdefault('findings',[])
if not any(x.get('finding_uid')=='FIND-20260915-028' for x in findings): findings.append(finding)
cur=ledger.setdefault('current_stage2_execution',{}); cur.update({'state':'REEXECUTED_BLOCKED','attempt_uid':active.get('attempt_uid'),'frozen_governance_uid':CURRENT_UID,'raw_discovery_gap_count':150,'validated_product_successor_signature_count':32,'external_authority_elimination_count':0,'current_functional_gap_count':118,'current_closure_blocker_count':0,'preserved_external_authority_union_count':8,'active_evidence_present':True,'active_findings_present':True,'stage_exit_allowed':False,'website_construction_allowed':False,'deployment_allowed':False,'historical_counts_may_be_treated_as_current':False,'prior_stage2_results_used':False,'source_execution_sha':head,'reexecution_cycle':'V215_PRODUCT_ONLY_REPLAY_R1','next_action':'REMEDIATE_REMAINING_118_EFFECTIVE_FUNCTIONAL_GAPS_WITH_EXTERNAL_AUTHORITY_PRESERVED'})
CANDIDATES.write_text(yaml.safe_dump(ledger,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')

print('PASS: fresh raw denominator = 150')
print('PASS: product-only successor signatures freshly validated = 32')
print('PASS: external authority eliminations = 0; GAP-001..GAP-008 preserved')
print('PASS: structural blockers = 0; effective functional blockers = 118')
