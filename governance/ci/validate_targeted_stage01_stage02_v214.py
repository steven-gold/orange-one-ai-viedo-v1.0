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

common_stage2 = [
 '04_PAGE_FUNCTIONAL_CONTRACT/DEPENDENCY_MAP.yaml',
 '04_PAGE_FUNCTIONAL_CONTRACT/ASYNC_PROVIDER_CONTRACT_R3_CURRENT.yaml',
 '04_PAGE_FUNCTIONAL_CONTRACT/SHARED_OWNER_PORT_MAP_R2.yaml']
page_stage2_old = ['FUNCTIONAL_CHAIN_SPEC.yaml','PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml']
page_stage2_v214 = [
 'FUNCTIONAL_WORKBENCH_CONTRACT.yaml','INTERACTION_TOPOLOGY_SPEC.yaml',
 'BUSINESS_ENTITY_INVENTORY.yaml','BUSINESS_ENTITY_OPERATION_MATRIX.yaml','ENTITY_HIERARCHY_MATRIX.yaml',
 'FUNCTION_ADMISSION_SCORECARD.yaml','AUTO_COMPLETION_SCOPE_LEDGER.yaml','FUNCTION_VISUAL_IMPACT_MATRIX.yaml']

def missing(paths): return [str(p) for p in paths if not p.exists()]

def core_specific(blockers):
 raw=(RUN/'00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml').read_text(encoding='utf-8')
 # Authority explicitly declares these editable; without the new operation matrix they cannot be closed under v2.1.14.
 for entity in ('CHAPTER','WORLD_SETTING'):
  if entity in raw and not (RUN/'04_PAGE_FUNCTIONAL_CONTRACT/CORE-01/BUSINESS_ENTITY_OPERATION_MATRIX.yaml').exists():
   blockers.append({'code':f'CORE_{entity}_LIFECYCLE_NOT_MATERIALIZED','class':'MISSING_REQUIRED_OPERATION','detail':f'{entity} is editable in authority but v2.1.14 operation matrix is absent.'})
 # Conversation atomic workbench: messages are separated from composer by decision/runtime sections.
 order=['CORE-01-SEC-04','CORE-01-SEC-05','CORE-01-SEC-06','CORE-01-SEC-07']
 pos=[raw.find(x) for x in order]
 if all(x>=0 for x in pos) and pos==sorted(pos) and not (RUN/'04_PAGE_FUNCTIONAL_CONTRACT/CORE-01/INTERACTION_TOPOLOGY_SPEC.yaml').exists():
  blockers.append({'code':'CORE_CONVERSATION_ATOMIC_WORKBENCH_UNRESOLVED','class':'FUNCTIONAL_VISUAL_FRAGMENTATION','detail':'Message Workspace -> Decision -> Runtime -> Composer requires an approved v2.1.14 topology contract.'})
 if 'single_multi_same_context: true' in raw and not (RUN/'04_PAGE_FUNCTIONAL_CONTRACT/CORE-01/AI_INTERACTION_CONTINUITY_CONTRACT.yaml').exists():
  blockers.append({'code':'CORE_AI_CONTINUITY_CONTRACT_MISSING','class':'AI_INTERACTION_CONTINUITY','detail':'CORE authority activates shared Single/Multi AI context but no rerun AI continuity contract exists.'})

def page_result(page):
 s1miss=missing([RUN/p for p in stage1_required[page]])
 stage1='PASS' if not s1miss else 'BLOCKED'
 blockers=[]
 for p in missing([RUN/p for p in common_stage2]): blockers.append({'code':'MISSING_COMMON_STAGE2_OUTPUT','path':p})
 for p in page_stage2_old:
  q=RUN/f'04_PAGE_FUNCTIONAL_CONTRACT/{page}/{p}'
  if not q.exists(): blockers.append({'code':'MISSING_STAGE2_OUTPUT','path':str(q)})
 for p in page_stage2_v214:
  q=RUN/f'04_PAGE_FUNCTIONAL_CONTRACT/{page}/{p}'
  if not q.exists(): blockers.append({'code':'MISSING_V214_REQUIRED_OUTPUT','path':str(q)})
 if page=='CORE-01': core_specific(blockers)
 if stage1!='PASS': blockers.insert(0,{'code':'STAGE1_NOT_CLOSED','missing':s1miss})
 return {'page_uid':page,'stage1_result':stage1,'stage1_missing':s1miss,'stage2_result':'PASS' if not blockers else 'BLOCKED','stage2_blocker_count':len(blockers),'stage2_blockers':blockers}

manifest=ROOT/'governance/current/v2.1.14/EFFECTIVE_TEST_GOVERNANCE_MANIFEST.yaml'
if not manifest.exists():
 print('ERROR: v2.1.14 effective test governance is not materialized',file=sys.stderr); sys.exit(2)
results=[page_result(p) for p in PAGES]
out={'schema_version':1,'run_uid':'FRESH-RUN-003-V214-TARGETED-STAGE02-RERUN','branch':os.getenv('GITHUB_REF_NAME','LOCAL'),'scope_pages':PAGES,'governance_revision':'v2.1.14-product-neutral-interaction-topology-ai-continuity','results':results,'engine_result':'PASS','closure_claim':all(r['stage2_result']=='PASS' for r in results)}
out_path=RUN/'04_PAGE_FUNCTIONAL_CONTRACT/TARGETED_STAGE2_RERUN_V214_RESULT.json'
out_path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
# The validator engine succeeds when it classifies truthfully; page BLOCKED is a valid governed result.
if any(r['stage1_result']!='PASS' for r in results): sys.exit(3)
sys.exit(0)
