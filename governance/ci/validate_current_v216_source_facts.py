#!/usr/bin/env python3
from pathlib import Path
import hashlib, yaml
root=Path('.')
run=root/'00_SOURCE_INTAKE/fresh_run_003'
intake=run/'00_SOURCE_INTAKE'
ALLOWED_REL={'PARENT_CHILD','PREVIOUS_NEXT','CROSS_FILE_REFERENCE','PAGE_SCOPE','MODULE_SCOPE','SHARED_CONTEXT'}
ALLOWED_DEP={'SEQUENCE','INPUT_OUTPUT','GATE','HANDOFF','SHARED_OWNER','PROVIDER_ASYNC','DATA_RUNTIME'}
REQ_FACTS={'SOURCE_CONTEXT_MANIFEST':'SOURCE_CONTEXT_MANIFEST.yaml','CONTENT_SUPERSESSION_CONFLICT_LEDGER':'CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml','SOURCE_DEPENDENCY_MAP':'SOURCE_DEPENDENCY_MAP.yaml'}
def die(x): raise SystemExit(x)
def load(p): return yaml.safe_load(p.read_text()) or {}
def stable_hash(o): return hashlib.sha256(yaml.safe_dump(o,allow_unicode=True,sort_keys=True).encode()).hexdigest()
def content_hash(d):
 x=dict(d); x.pop('content_hash',None); return stable_hash(x)
def evidence_path(ref): return intake/str(ref).split('#',1)[0].replace('00_SOURCE_INTAKE/','',1)
if not run.is_dir(): die('fresh_run_003 missing')
state=load(run/'EXECUTION_STATE.yaml'); rm=load(run/'RUN_MANIFEST.yaml')
if state.get('state') not in {'SOURCE_FACT_MATERIALIZATION_COMPLETED_PENDING_CI','SOURCE_FACT_MATERIALIZATION_COMPLETED'}: die('source fact execution state mismatch')
if not state.get('source_fact_materialization_started') or not state.get('source_fact_materialization_completed'): die('source fact materialization flags incomplete')
if state.get('domain_decomposition_started') or state.get('blueprint_materialization_started') or state.get('website_construction_started') or state.get('deployment_started'): die('downstream stage started early')
if rm.get('governance',{}).get('version')!='v2.1.6': die('run governance mismatch')
struct=load(intake/'SOURCE_STRUCTURE_MANIFEST.yaml'); sm=load(intake/'SOURCE_SEGMENT_MAP.yaml')
if struct.get('observed_node_count')!=61 or struct.get('completion',{}).get('mixed_terminal_units')!=0 or struct.get('completion',{}).get('unresolved_container_units')!=0: die('61-node semantic structure not closed')
if sm.get('completion',{}).get('segment_count')!=61 or sm.get('completion',{}).get('required_nodes_unmapped')!=0: die('61/61 segment mapping not closed')
all_nodes={}
for s in struct.get('sources') or []:
 for n in s.get('observed_nodes') or []:
  all_nodes[n['source_node_uid']]={'source_uid':s['source_uid'],'page_uid':s['page_uid'],'source_ref':n['source_ref'],'governance_relevance':n['governance_relevance']}
if len(all_nodes)!=61: die('structure node index not 61')
raw_src={s['source_uid'] for s in sm.get('raw_sources') or []}; raw_pages={s['page_uid'] for s in sm.get('raw_sources') or []}
facts={}
for ftype,fn in REQ_FACTS.items():
 p=intake/fn
 if not p.exists(): die('source fact missing '+ftype)
 d=load(p); facts[ftype]=d
 if d.get('artifact_type')!=ftype or d.get('status')!='CURRENT_SOURCE_FACT': die('source fact identity/status mismatch '+ftype)
 if d.get('content_hash')!=content_hash(d): die('source fact hash mismatch '+ftype)
 if not raw_pages.issubset(set(d.get('page_uids') or [])): die('source fact page scope incomplete '+ftype)
 if not d.get('page_uid_or_scope_uid'): die('source fact scope uid missing '+ftype)
ctx=facts['SOURCE_CONTEXT_MANIFEST']; ctxnodes=ctx.get('source_nodes') or []
if len(ctxnodes)!=61: die('source context node count not 61')
seen=set()
for n in ctxnodes:
 uid=n.get('source_node_uid')
 if uid in seen or uid not in all_nodes: die('source context unknown/duplicate node '+str(uid))
 seen.add(uid); base=all_nodes[uid]
 for k in ('source_uid','page_uid','source_ref','governance_relevance'):
  if n.get(k)!=base[k]: die('source context node mismatch '+uid+':'+k)
 if n.get('terminality_state')!='TERMINAL_HOMOGENEOUS' or n.get('semantic_responsibility_count')!=1 or n.get('unresolved_child_responsibility_count')!=0: die('source context semantic granularity regression '+uid)
if seen!=set(all_nodes): die('source context universe shrink')
if ctx.get('unresolved_references') not in ([],None): die('source context has unresolved references')
for e in ctx.get('context_edges') or []:
 if not all(e.get(k) for k in ('edge_uid','from_source_node_uid','to_source_node_uid','relation_type','source_evidence_ref')): die('context edge field missing')
 if e['from_source_node_uid'] not in all_nodes or e['to_source_node_uid'] not in all_nodes: die('context edge unknown node '+e['edge_uid'])
 if e['relation_type'] not in ALLOWED_REL: die('context relation illegal '+e['edge_uid'])
 if not evidence_path(e['source_evidence_ref']).is_file(): die('context evidence missing '+e['edge_uid'])
lin=ctx.get('source_lineage_refs') or []
if {x.get('source_uid') for x in lin}!=raw_src: die('context lineage source set mismatch')
for x in lin:
 if not (run/x['raw_source_path']).is_file(): die('lineage raw source missing '+x['source_uid'])
ledger=facts['CONTENT_SUPERSESSION_CONFLICT_LEDGER']
if ledger.get('scan_summary',{}).get('superseded_current_owner_residual_count')!=0: die('superseded current owner residual')
if not evidence_path(ledger.get('decision_evidence_ref')).is_file(): die('conflict decision evidence missing')
canon=load(intake/'RAW_SOURCE/CORE-01/CORE_CURRENT_CANONICAL_VISUAL_FINAL_LOCKED_V1.0.yaml'); core=load(intake/'RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml'); asset=load(intake/'RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml')
if canon.get('authority',{}).get('owns_page_layout') is not False or canon.get('authority',{}).get('owns_child_visual_definitions') is not False: die('canonical visual ownership boundary changed')
if core.get('authority',{}).get('legacy_merge')!='FORBIDDEN' or asset.get('authority',{}).get('legacy_merge')!='FORBIDDEN': die('legacy merge policy changed')
if core.get('authority',{}).get('parallel_authority_for_same_page')!='FORBIDDEN' or asset.get('authority',{}).get('parallel_authority_for_same_page')!='FORBIDDEN': die('parallel authority policy changed')
dep=facts['SOURCE_DEPENDENCY_MAP']
for e in dep.get('edges') or []:
 if e.get('producer_source_uid') not in raw_src or e.get('consumer_source_uid') not in raw_src: die('invented/unknown dependency source '+str(e.get('edge_uid')))
 if e.get('dependency_type') not in ALLOWED_DEP: die('illegal dependency type '+str(e.get('edge_uid')))
 if not evidence_path(e.get('authority_evidence_ref')).is_file(): die('dependency evidence missing '+str(e.get('edge_uid')))
if dep.get('invented_dependency_count')!=0: die('invented dependency count nonzero')
edgekeys={(x['producer_source_uid'],x['consumer_source_uid'],x['dependency_type']) for x in dep.get('edges') or []}
if ('SRC-CORE-01-PAGE-VISUAL-AUTHORITY','SRC-CORE-01-CANONICAL-VISUAL-IDENTITY','SHARED_OWNER') not in edgekeys: die('explicit CORE visual owner dependency missing')
if ('SRC-CORE-01-PAGE-VISUAL-AUTHORITY','SRC-ASSET-01-PAGE-VISUAL-AUTHORITY','HANDOFF') not in edgekeys: die('explicit CORE to ASSET handoff dependency missing')
canon_text=(intake/'RAW_SOURCE/CORE-01/CORE_CURRENT_CANONICAL_VISUAL_FINAL_LOCKED_V1.0.yaml').read_text(); core_text=(intake/'RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml').read_text(); asset_text=(intake/'RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml').read_text()
for token in ['page_design_owner: authority/pages/workspace/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml','visual_registry_owner: authority/pages/workspace/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml','children_remain_owned_by: authority/pages/workspace/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml']:
 if token not in canon_text: die('DEP-E001 raw evidence missing: '+token)
if 'downstream_rule: Expose read-only ASSET / VIDEO / EDIT boundary readiness only' not in core_text: die('DEP-E002 CORE raw evidence missing')
for token in ['gate_uid: ASSET-01-GATE-CHILD-LOCK','gate_uid: ASSET-01-GATE-SCRIPT','gate_uid: ASSET-01-GATE-MANIFEST']:
 if token not in asset_text: die('DEP-E002 ASSET raw evidence missing: '+token)
gaps=dep.get('unresolved_authority_gaps') or []
if len(gaps)!=8 or any(g.get('disposition')!='UNRESOLVED_AUTHORITY_GAP' for g in gaps): die('unresolved authority gaps mismatch')
expected_refs={'GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY@V1.9','GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY@V1.0','ACPOS_SYSTEM_AUTHORITY@V1.0','ACPOS_CURRENT_NAVIGATION_PERMISSION_AUTHORITY@V1.0','ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT@V1.3','ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY','IAM-01 / account permission runtime','ACPOS shared AI Router/Capability Assignment'}
if {g.get('authority_ref') for g in gaps}!=expected_refs: die('unresolved authority gap set mismatch')
for ref in expected_refs:
 if ref not in core_text+'\n'+asset_text: die('gap raw evidence missing: '+ref)
for rel in ['01_CLASSIFIED','02_BASE_BLUEPRINT','03_BLUEPRINT_BINDING']:
 if (run/rel).exists(): die('downstream artifact directory exists early: '+rel)
print('PASS: SOURCE_FACT_MATERIALIZATION 3/3 current source facts; context_nodes=61; conflict_items=0; dependency_edges=2; unresolved_authority_gaps=8; invented_dependencies=0')
print('PASS: source facts preserve 61-node universe and do not start classification/blueprint/website/deployment')
