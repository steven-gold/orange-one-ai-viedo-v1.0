#!/usr/bin/env python3
from pathlib import Path
import json, os, sys

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
PAGES = ['CORE-01','ASSET-01']

stage1_required = {
 'CORE-01': [
  '00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
  '01_CLASSIFIED/CORE-01/PAGE/AUTHORITY.yaml','01_CLASSIFIED/CORE-01/VISUAL/LAYOUT.yaml',
  '02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml','02_BASE_BLUEPRINT/CORE-01/VISUAL_BASE_BLUEPRINT.yaml',
  '03_BLUEPRINT_BINDING/CORE-01/BLUEPRINT_BINDING_MANIFEST.yaml'],
 'ASSET-01': [
  '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
  '01_CLASSIFIED/ASSET-01/PAGE/AUTHORITY.yaml','01_CLASSIFIED/ASSET-01/VISUAL/LAYOUT.yaml',
  '02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml','02_BASE_BLUEPRINT/ASSET-01/VISUAL_BASE_BLUEPRINT.yaml',
  '03_BLUEPRINT_BINDING/ASSET-01/BLUEPRINT_BINDING_MANIFEST.yaml']}

RAW = {
 'CORE-01': RUN/'00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
 'ASSET-01': RUN/'00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
}

common_always = [
 '04_PAGE_FUNCTIONAL_CONTRACT/DEPENDENCY_MAP.yaml',
 '04_PAGE_FUNCTIONAL_CONTRACT/SHARED_OWNER_PORT_MAP_R2.yaml']
page_always = ['FUNCTIONAL_CHAIN_SPEC.yaml','PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml']

def missing(paths): return [str(p) for p in paths if not p.exists()]

def add_missing(blockers, path, code, applies=True, basis=None, aliases=()):
    if not applies: return
    candidates=[path, *aliases]
    if not any(p.exists() for p in candidates):
        b={'code':code,'class':'MISSING_APPLICABLE_REQUIRED_OUTPUT','path':str(path),'applicability':'APPLIES'}
        if basis: b['applicability_basis']=basis
        blockers.append(b)

def page_result(page):
    raw=RAW[page].read_text(encoding='utf-8')
    page_dir=RUN/f'04_PAGE_FUNCTIONAL_CONTRACT/{page}'
    s1miss=missing([RUN/p for p in stage1_required[page]])
    stage1='PASS' if not s1miss else 'BLOCKED'
    blockers=[]

    for p in missing([RUN/p for p in common_always]):
        blockers.append({'code':'MISSING_COMMON_STAGE2_OUTPUT','class':'MISSING_APPLICABLE_REQUIRED_OUTPUT','path':p,'applicability':'APPLIES'})
    for name in page_always:
        add_missing(blockers,page_dir/name,'MISSING_STAGE2_OUTPUT',True,'ALL_TARGET_PAGE_STAGE02')

    async_applies = any(t in raw for t in ('Provider','Callback','Retry','queued','running','Runtime / Provider'))
    add_missing(blockers,RUN/'04_PAGE_FUNCTIONAL_CONTRACT/ASYNC_PROVIDER_CONTRACT_R3_CURRENT.yaml','MISSING_ASYNC_PROVIDER_CONTRACT',async_applies,'ASYNC_PROVIDER_SCOPE_DECLARED')

    entity_applies = any(t in raw for t in ('asset_types:','PROJECT_CORE','TOPIC','CHAPTER','WORLD_SETTING','Layer / Patch'))
    add_missing(blockers,page_dir/'BUSINESS_ENTITY_INVENTORY.yaml','MISSING_BUSINESS_ENTITY_INVENTORY',entity_applies,'GOVERNED_BUSINESS_ENTITY_SCOPE_PRESENT')
    add_missing(blockers,page_dir/'BUSINESS_ENTITY_OPERATION_MATRIX.yaml','MISSING_BUSINESS_ENTITY_OPERATION_MATRIX',entity_applies,'GOVERNED_BUSINESS_ENTITY_SCOPE_PRESENT')

    hierarchy_applies = any(t in raw for t in ('parent layer','CHAPTER','WORLD_SETTING','Topic','Project','parent','child'))
    add_missing(blockers,page_dir/'ENTITY_HIERARCHY_MATRIX.yaml','MISSING_ENTITY_HIERARCHY_MATRIX',hierarchy_applies,'ENTITY_RELATIONSHIP_OR_HIERARCHY_DECLARED')

    workbench_applies = 'registries:' in raw and 'sections:' in raw
    add_missing(blockers,page_dir/'FUNCTIONAL_WORKBENCH_CONTRACT.yaml','MISSING_FUNCTIONAL_WORKBENCH_CONTRACT',workbench_applies,'CONTINUOUS_PAGE_WORK_UNITS_PRESENT')
    add_missing(blockers,page_dir/'INTERACTION_TOPOLOGY_MATRIX.yaml','MISSING_INTERACTION_TOPOLOGY_MATRIX',workbench_applies,'CONTINUOUS_PAGE_WORK_UNITS_PRESENT',aliases=(page_dir/'INTERACTION_TOPOLOGY_SPEC.yaml',))

    visual_applies = True
    add_missing(blockers,page_dir/'FUNCTION_VISUAL_IMPACT_MATRIX.yaml','MISSING_FUNCTION_VISUAL_IMPACT_MATRIX',visual_applies,'USER_VISIBLE_PAGE_OPERATIONS')

    admission_activation=(page_dir/'FUNCTION_ADMISSION_ACTIVATION.yaml').exists()
    add_missing(blockers,page_dir/'FUNCTION_ADMISSION_SCORECARD.yaml','MISSING_FUNCTION_ADMISSION_SCORECARD',admission_activation,'AI_OR_AUTO_PROPOSED_FUNCTIONAL_ADDITION_ACTIVATED')

    auto_activation=(page_dir/'AUTO_COMPLETION_ACTIVATION.yaml').exists()
    add_missing(blockers,page_dir/'AUTO_COMPLETION_SCOPE_LEDGER.yaml','MISSING_AUTO_COMPLETION_SCOPE_LEDGER',auto_activation,'BOUNDED_AUTO_COMPLETION_ACTIVATED_FROM_SEED_GAP')

    ai_applies = any(t in raw for t in ('single_multi_same_context: true','Multi AI','AI Conversation','Assigned AI','MULTI_AI'))
    add_missing(blockers,page_dir/'AI_INTERACTION_CONTINUITY_CONTRACT.yaml','MISSING_AI_INTERACTION_CONTINUITY_CONTRACT',ai_applies,'AI_INTERACTION_PROFILE_DECLARED')

    if stage1!='PASS':
        blockers.insert(0,{'code':'STAGE1_NOT_CLOSED','class':'PREREQUISITE','missing':s1miss})

    applicability={
      'async_provider':async_applies,
      'business_entity':entity_applies,
      'entity_hierarchy':hierarchy_applies,
      'continuous_workbench':workbench_applies,
      'function_visual_impact':visual_applies,
      'function_admission':admission_activation,
      'bounded_auto_completion':auto_activation,
      'ai_interaction_continuity':ai_applies,
    }
    return {
      'page_uid':page,
      'stage1_result':stage1,
      'stage1_missing':s1miss,
      'stage2_result':'PASS' if not blockers else 'BLOCKED',
      'stage2_blocker_count':len(blockers),
      'stage2_blockers':blockers,
      'applicability':applicability,
    }

manifest=ROOT/'governance/current/v2.1.14/EFFECTIVE_TEST_GOVERNANCE_MANIFEST.yaml'
if not manifest.exists():
    print('ERROR: v2.1.14 effective test governance is not materialized',file=sys.stderr); sys.exit(2)
manifest_text=manifest.read_text(encoding='utf-8')
for token in ('applicability_must_be_proven_before_missing_output_is_counted_as_blocker: true','TEST_FEEDBACK_TEMPORARY_ARTIFACT_LIFECYCLE_DELTA.yaml'):
    if token not in manifest_text:
        print('ERROR: current v2.1.14 manifest missing applicability/test-feedback guard: '+token,file=sys.stderr); sys.exit(2)

results=[page_result(p) for p in PAGES]
out={
 'schema_version':2,
 'run_uid':'FRESH-RUN-003-V214-TARGETED-STAGE02-RERUN',
 'branch':os.getenv('GITHUB_REF_NAME','LOCAL'),
 'scope_pages':PAGES,
 'governance_revision':'v2.1.14-product-neutral-interaction-topology-ai-continuity',
 'applicability_model':'V214_EXACT_APPLICABILITY_BEFORE_BLOCKER_COUNT',
 'results':results,
 'engine_result':'PASS',
 'closure_claim':all(r['stage2_result']=='PASS' for r in results),
}
out_path=RUN/'04_PAGE_FUNCTIONAL_CONTRACT/TARGETED_STAGE2_RERUN_V214_RESULT.json'
out_path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
if any(r['stage1_result']!='PASS' for r in results): sys.exit(3)
sys.exit(0)
