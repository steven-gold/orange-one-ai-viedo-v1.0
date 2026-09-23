#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
import sys as _governance_runner_sys
if __name__ != "__main__" and "pytest" in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip("standalone governance regression executable; use registered subprocess runner", allow_module_level=True)
import importlib.util, tempfile, pathlib, yaml, json, sys
base=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(base))
spec=importlib.util.spec_from_file_location('vg', base/'validate_governance.py')
vg=importlib.util.module_from_spec(spec); spec.loader.exec_module(vg)

def write(root, rel, data):
    p=root/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(yaml.safe_dump(data,sort_keys=False,allow_unicode=True),encoding='utf-8')

def case(name, rel, data, fn, expect='FAIL'):
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td); write(root,rel,data); vg.ROOT=root; vg.RESULTS=[]; fn(); r=vg.RESULTS[-1]
        return {'case':name,'actual':r['status'],'expected':expect,'ok':r['status']==expect,'details':r.get('details')}

base_nodes={k:'ok' for k in ['business_intent','preconditions','entry','input_source','trigger','gate','permission','action','validation','response_feedback','success_state','next_state','next_step','next_gate','failure_state','recovery','terminal_outcome']}
results=[]
# 1 CORE effect semantics: fake N/A on effectful chain must fail
n=dict(base_nodes); n.update({'payload':'N/A','api_entry':'N/A','runtime_owner':'N/A','data_provider':'N/A','audit_event':'N/A'})
results.append(case('effectful_NA_bypass_blocked','11_EVIDENCE/audit/FUNCTIONAL_CHAIN_MATRIX.yaml',{'chains':[{'flow_uid':'CORE-SEND','effect_type':'CONVERSATION_WRITE','required':True,'production_required':True,'classification':'COMPLETE','nodes':n}]},vg.check_functional_chain))
# 2 UI_ONLY may omit API only with authority evidence and should pass
n2=dict(base_nodes); n2.update({'payload':'NOT_APPLICABLE','api_entry':'NOT_APPLICABLE','runtime_owner':'NOT_APPLICABLE','data_provider':'NOT_APPLICABLE','audit_event':'local'})
results.append(case('CORE_UI_ONLY_authority_NA_allowed','11_EVIDENCE/audit/FUNCTIONAL_CHAIN_MATRIX.yaml',{'chains':[{'flow_uid':'CORE-MSG-COPY','effect_type':'UI_ONLY','required':True,'production_required':True,'classification':'COMPLETE','not_applicable_authority_evidence':'CORE authority effect_type=UI_ONLY','nodes':n2}]},vg.check_functional_chain,'PASS'))
# 3 fail-closed required production cannot pass
results.append(case('required_fail_closed_blocked','11_EVIDENCE/audit/FUNCTIONAL_CHAIN_MATRIX.yaml',{'chains':[{'flow_uid':'ASSET-EXPORT','effect_type':'EXTERNAL_EFFECTS_REQUIRED','required':True,'production_required':True,'classification':'INTENTIONAL_FAIL_CLOSED','nodes':dict(n)}]},vg.check_functional_chain))
# 4 geometry self-reported PASS cannot hide mismatch
results.append(case('geometry_mismatch_recomputed','11_EVIDENCE/audit/VISUAL_GEOMETRY_BASELINE.yaml',{'viewports':[{'viewport_uid':'1280','width':1280,'height':800,'measurement_source':'BROWSER_DOM','captured_at':'2026-09-12T00:00:00Z','targets':[{'target_uid':'CORE-GRID','expected_geometry':{'width':1280},'actual_geometry':{'width':900},'tolerance':2,'overlap_count':0,'clipping_count':0,'overflow_count':0,'occlusion_count':0,'unexpected_wrap_count':0,'text_overflow_count':0,'dimension_violation_count':0,'anchor_drift_count':0,'visual_diff_result':'PASS'}]}]},vg.check_visual_geometry))
# 5 production freshness requires run binding/capture
results.append(case('production_no_run_freshness_blocked','11_EVIDENCE/audit/DEPLOYMENT_RENDER_IDENTITY.yaml',{'expected_source_revision':'abc','build_source_revision':'abc','deployed_source_revision':'abc','runtime_reported_revision':'abc','route_manifest_hash':'r','production_route_manifest_hash':'r','client_asset_manifest_hash':'a','production_client_asset_manifest_hash':'a','expected_dom_fingerprint':'d','dom_fingerprint':'d','visual_geometry_result':'PASS','stale_release_fingerprint_detected':False},vg.check_production_render_identity))
# 6 self-declared cross-page N/A blocked
results.append(case('cross_page_self_NA_blocked','11_EVIDENCE/audit/CROSS_PAGE_FLOW_MATRIX.yaml',{'not_applicable':True,'flows':[]},vg.check_cross_page_flow))
# 7 source-truth conflicting current owners recomputed
src={'sources':[{'source_uid':'S1','source_path':'a','source_hash':'1','source_type':'AUTHORITY','authority_role':'CURRENT','authority_status':'CURRENT','canonical_uid':'CORE-01','owner_claim':'A','current_owner_uid':'A','positive_ui_authority':True,'revision':'1','current_authority_membership':True,'conflict_state':'NONE','contamination_state':'CLEAN','resolution_result':'RESOLVED','evidence_ref':'E1'},{'source_uid':'S2','source_path':'b','source_hash':'2','source_type':'AUTHORITY','authority_role':'CURRENT','authority_status':'CURRENT','canonical_uid':'CORE-01','owner_claim':'B','current_owner_uid':'B','positive_ui_authority':True,'revision':'2','current_authority_membership':True,'conflict_state':'NONE','contamination_state':'CLEAN','resolution_result':'RESOLVED','evidence_ref':'E2'}],'metrics':{'unresolved_source_truth':0,'current_owner_conflict':0,'current_source_contamination':0,'unmapped_superseded_content':0}}
results.append(case('source_metrics_cannot_hide_conflict','11_EVIDENCE/audit/SOURCE_TRUTH_LEDGER.yaml',src,vg.check_source_truth))
# 8 JOB_START missing lifecycle blocked
nj=dict(base_nodes); nj.update({'payload':'p','api_entry':'api','runtime_owner':'rt','data_provider':'provider','audit_event':'evt'})
results.append(case('ASSET_JOB_START_requires_async_lifecycle','11_EVIDENCE/audit/FUNCTIONAL_CHAIN_MATRIX.yaml',{'chains':[{'flow_uid':'ASSET-EXECUTE','effect_type':'JOB_START','required':True,'production_required':True,'classification':'COMPLETE','nodes':nj}]},vg.check_functional_chain))
# 9 State machine missing precondition/illegal test blocked
results.append(case('ASSET_transition_incomplete_blocked','11_EVIDENCE/audit/STATE_TRANSITION_LEDGER.yaml',{'required':True,'transitions':[{'transition_uid':'ASSET-STTR-01','from_state':'RESOLVE','to_state':'GENERATE','trigger':'EXECUTE','gate':'GATE','status':'PASS'}]},vg.check_state_transition))
# 10 generated identity must be readonly/no client generation
results.append(case('ASSET_generated_id_mutation_blocked','11_EVIDENCE/audit/FIELD_IDENTITY_LEDGER.yaml',{'required':True,'mappings':[{'concept_object':'AssetVersion','canonical_field':'asset_version_id','ui_label':'Version','localization_key':'asset.version','validation_contract':'uuid','generated_identity':True,'read_only':False,'client_generated':True}]},vg.check_field_identity))

# 11 ASSET shared operation reference must not force a duplicate page-local API/runtime
ns=dict(base_nodes); ns.update({'payload':'CorrectionCandidateRef','api_entry':'NOT_APPLICABLE','runtime_owner':'SHARED_RUNTIME_OPERATION_AUTHORITY','data_provider':'NOT_APPLICABLE','audit_event':'shared audit contract'})
results.append(case('ASSET_shared_owner_reference_no_duplicate_api','11_EVIDENCE/audit/FUNCTIONAL_CHAIN_MATRIX.yaml',{'chains':[{'flow_uid':'ASSET-CORRECTION-GENERATE','effect_type':'CANDIDATE_CREATE','binding_kind':'SHARED_OPERATION_REFERENCE','shared_owner_reference':'SHARED_RUNTIME_OPERATION_AUTHORITY','shared_operation_id':'generateCorrectionScriptCandidate','not_applicable_authority_evidence':'ASSET authority delegates page-local API/data ownership to exact shared operation','required':True,'production_required':True,'classification':'SHARED_OWNER_REFERENCE','nodes':ns}]},vg.check_functional_chain,'PASS'))


# 12 machine encoding mirror cannot silently become a second editable Authority
mirror={'sources':[{'source_uid':'CORE-DOC','source_path':'CORE.docx','source_hash':'h1','source_type':'AUTHORITY','representation_role':'CANONICAL_EDITABLE_OWNER','authority_role':'CURRENT_CANONICAL','authority_status':'CURRENT','canonical_uid':'CORE-01','owner_claim':'CORE-DOC','current_owner_uid':'CORE-DOC','positive_ui_authority':True,'authority_scope':'PAGE','revision':'D1','current_authority_membership':True,'conflict_state':'NONE','contamination_state':'CLEAN','resolution_result':'RESOLVED','evidence_ref':'E-DOC'},{'source_uid':'CORE-YAML','source_path':'CORE.yaml','source_hash':'h2','source_type':'MACHINE_ENCODING','representation_role':'MACHINE_ENCODING_MIRROR','authority_role':'CURRENT','authority_status':'CURRENT','canonical_uid':'CORE-01','owner_claim':'CORE-YAML','positive_ui_authority':True,'authority_scope':'PAGE','revision':'D1','current_authority_membership':True,'canonical_owner_ref':'CORE-DOC','semantic_sync_evidence':'SEMANTIC-EQ-1','conflict_state':'NONE','contamination_state':'CLEAN','resolution_result':'RESOLVED','evidence_ref':'E-YAML'}]}
results.append(case('CORE_machine_encoding_cannot_be_second_editable_owner','11_EVIDENCE/audit/SOURCE_TRUTH_LEDGER.yaml',mirror,vg.check_source_truth))

print(json.dumps({'total':len(results),'passed_expectations':sum(x['ok'] for x in results),'results':results},ensure_ascii=False,indent=2))
if not all(x['ok'] for x in results): raise SystemExit(1)
