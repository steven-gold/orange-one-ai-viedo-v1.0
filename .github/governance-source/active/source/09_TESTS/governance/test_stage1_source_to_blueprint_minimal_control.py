#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
import sys as _governance_runner_sys
if __name__ != "__main__" and "pytest" in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip("standalone governance regression executable; use registered subprocess runner", allow_module_level=True)
from pathlib import Path
import copy, importlib.util, json, tempfile, zipfile, yaml
HERE=Path(__file__).resolve().parent; PKG=HERE.parents[1]
spec=importlib.util.spec_from_file_location('guard',HERE/'governance_stage1_pipeline_guard.py'); g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

def write(p,data): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(yaml.safe_dump(data,allow_unicode=True,sort_keys=False) if isinstance(data,(dict,list)) else str(data),encoding='utf-8')
def finalize(d,key):
    d=copy.deepcopy(d); d[key]=g.content_hash(d); return d

def build(root):
    nh=g.normative_hash(PKG)
    write(root/'RUN_CONTEXT.yaml',{'run_uid':'MC2','stage_uid':'STAGE-01','candidate_normative_hash':nh,'clean_start_verified':True,'website_reconstruction':False})
    raw_path='00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/SOURCE.yaml'
    write(root/raw_path,'fixture raw page+visual source\n')
    raw_sha=g.git_blob_sha(root/raw_path)
    raw=[{'source_uid':'RAW1','page_uid':'CORE-01','source_role':'MIXED_PAGE_VISUAL_SOURCE_INPUT','source_domain_scope':'MIXED_PAGE_VISUAL','current_owner':False}]
    write(root/'00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml',{
      'artifact_uid':'RAW-CAPTURE-MC2','artifact_type':'RAW_SOURCE_REFERENCE_MANIFEST','status':'CURRENT_RAW_SOURCE_CAPTURE','capture_root':'00_SOURCE_INTAKE/RAW_SOURCE','records':[
        {'source_uid':'RAW1','page_uid':'CORE-01','source_role':'MIXED_PAGE_VISUAL_SOURCE_INPUT','source_domain_scope':'MIXED_PAGE_VISUAL','source_path':'fixture://raw1','target_path':raw_path,'source_git_blob_sha':raw_sha,'target_git_blob_sha':raw_sha,'content_mutated':False}]})
    write(root/'00_SOURCE_INTAKE/RAW_SOURCE_CAPTURE_STATE.yaml',{'run_uid':'MC2','state':'CAPTURE_CLOSED','next_step':'SOURCE_STRUCTURE_ENUMERATION','recapture_allowed':False})
    src={'source_uid':'RAW1','source_identity':'fixture://raw1','enumeration_method':'fixture-observed-structure','evidence_ref':'00_SOURCE_INTAKE/evidence/E1.yaml','enumeration_state':'FULL_SOURCE_ENUMERATION_PROVEN','observed_nodes':[
      {'source_node_uid':'N-P1','source_ref':'§1','governance_relevance':'REQUIRED','terminality_state':'TERMINAL_HOMOGENEOUS','semantic_responsibility_count':1,'unresolved_child_responsibility_count':0},
      {'source_node_uid':'N-P2','source_ref':'§2','governance_relevance':'REQUIRED','terminality_state':'TERMINAL_HOMOGENEOUS','semantic_responsibility_count':1,'unresolved_child_responsibility_count':0},
      {'source_node_uid':'N-V1','source_ref':'§3','governance_relevance':'REQUIRED','terminality_state':'TERMINAL_HOMOGENEOUS','semantic_responsibility_count':1,'unresolved_child_responsibility_count':0}]}
    src['structure_manifest_hash']=g.content_hash(src)
    write(root/'00_SOURCE_INTAKE/evidence/E1.yaml',{'evidence_uid':'E1','source_uid':'RAW1','status':'OBSERVED'})
    write(root/'00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml',{'sources':[src]})
    segs=[
      {'segment_uid':'S-P1','source_uid':'RAW1','source_node_uid':'N-P1','page_uid':'CORE-01','planning_domain':'PAGE_CONSTRUCTION','responsibility_uid':'PAGE_IDENTITY','required':True,'disposition':'CLASSIFIED','target_artifact_uids':['A-P1']},
      {'segment_uid':'S-P2','source_uid':'RAW1','source_node_uid':'N-P2','page_uid':'CORE-01','planning_domain':'PAGE_CONSTRUCTION','responsibility_uid':'PAGE_STRUCTURE','required':True,'disposition':'CLASSIFIED','target_artifact_uids':['A-P2']},
      {'segment_uid':'S-V1','source_uid':'RAW1','source_node_uid':'N-V1','page_uid':'CORE-01','planning_domain':'VISUAL_CONSTRUCTION','responsibility_uid':'LAYOUT_GEOMETRY','required':True,'disposition':'CLASSIFIED','target_artifact_uids':['A-V1']},]
    sm={'raw_sources':raw,'source_segments':segs,'status':'PASS'}; write(root/'00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml',sm)
    source_facts=[]
    for ftype,uid,extra in [
      ('SOURCE_CONTEXT_MANIFEST','SF-CONTEXT',{'context_edges':[{'edge_uid':'CTX-1','from_source_node_uid':'N-P1','to_source_node_uid':'N-P2','relation_type':'PREVIOUS_NEXT','source_evidence_ref':'00_SOURCE_INTAKE/evidence/E1.yaml'}]}),
      ('CONTENT_SUPERSESSION_CONFLICT_LEDGER','SF-CONFLICT',{'items':[]}),
      ('SOURCE_DEPENDENCY_MAP','SF-DEPENDENCY',{'edges':[{'edge_uid':'DEP-1','producer_source_uid':'RAW1','consumer_source_uid':'RAW1','dependency_type':'SEQUENCE','authority_evidence_ref':'00_SOURCE_INTAKE/evidence/E1.yaml'}],'unresolved_authority_gaps':[]})]:
        d={'artifact_uid':uid,'artifact_type':ftype,'page_uids':['CORE-01'],'status':'CURRENT_SOURCE_FACT',**extra}
        d['content_hash']=g.content_hash(d); source_facts.append(d); write(root/f'00_SOURCE_INTAKE/{ftype}.yaml',d)
    arts=[]
    for uid,domain,resp,seg,path in [
      ('A-P1','PAGE_CONSTRUCTION','PAGE_IDENTITY','S-P1','01_CLASSIFIED/CORE-01/PAGE/PAGE_IDENTITY.yaml'),
      ('A-P2','PAGE_CONSTRUCTION','PAGE_STRUCTURE','S-P2','01_CLASSIFIED/CORE-01/PAGE/PAGE_STRUCTURE.yaml'),
      ('A-V1','VISUAL_CONSTRUCTION','LAYOUT_GEOMETRY','S-V1','01_CLASSIFIED/CORE-01/VISUAL/LAYOUT_GEOMETRY.yaml')]:
        d={'artifact_uid':uid,'page_uid':'CORE-01','planning_domain':domain,'responsibility_uid':resp,'responsibility_class':resp,'responsibilities':[resp],'canonical_owner_uid':'OWNER-'+uid,'target_path':path,'lifecycle_uid':'LC-'+resp,'approval_scope_uid':'AP-'+resp,'version_scope_uid':'VER-'+resp,'test_scope_uid':'TEST-'+resp,'source_lineage':[{'source_uid':'RAW1','source_segment_uids':[seg]}],'facts':[{'k':resp,'v':'x'}],'status':'CURRENT_CLASSIFICATION'}
        d=finalize(d,'content_hash'); arts.append(d); write(root/path,d)
    bp_page={'blueprint_uid':'BP-P','page_uid':'CORE-01','blueprint_type':'PAGE_BASE_BLUEPRINT','planning_domain':'PAGE_CONSTRUCTION','target_path':'02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml','input_artifacts':[{'artifact_uid':a['artifact_uid'],'content_hash':a['content_hash']} for a in arts if a['planning_domain']=='PAGE_CONSTRUCTION'],'required_responsibility_uids':['PAGE_IDENTITY','PAGE_STRUCTURE'],'shared_refs':[],'source_fact_refs':[{'artifact_uid':x['artifact_uid'],'content_hash':x['content_hash']} for x in source_facts],'raw_source_inputs':[],'embedded_classification_payloads':[],'status':'CURRENT_BASE_BLUEPRINT'}
    bp_page=finalize(bp_page,'blueprint_hash'); write(root/bp_page['target_path'],bp_page)
    bp_vis={'blueprint_uid':'BP-V','page_uid':'CORE-01','blueprint_type':'VISUAL_BASE_BLUEPRINT','planning_domain':'VISUAL_CONSTRUCTION','target_path':'02_BASE_BLUEPRINT/CORE-01/VISUAL_BASE_BLUEPRINT.yaml','input_artifacts':[{'artifact_uid':'A-V1','content_hash':[a for a in arts if a['artifact_uid']=='A-V1'][0]['content_hash']}],'required_responsibility_uids':['LAYOUT_GEOMETRY'],'shared_refs':[],'source_fact_refs':[{'artifact_uid':x['artifact_uid'],'content_hash':x['content_hash']} for x in source_facts],'raw_source_inputs':[],'embedded_classification_payloads':[],'status':'CURRENT_BASE_BLUEPRINT'}
    bp_vis=finalize(bp_vis,'blueprint_hash'); write(root/bp_vis['target_path'],bp_vis)
    bind={'binding_uid':'BIND-CORE','page_uid':'CORE-01','target_path':'03_BLUEPRINT_BINDING/CORE-01/BLUEPRINT_BINDING_MANIFEST.yaml','page_blueprint':{'blueprint_uid':'BP-P','blueprint_hash':bp_page['blueprint_hash']},'visual_blueprint':{'blueprint_uid':'BP-V','blueprint_hash':bp_vis['blueprint_hash']},'embedded_blueprint_payloads':[],'status':'CURRENT_BLUEPRINT_BINDING'}
    bind=finalize(bind,'binding_hash'); write(root/bind['target_path'],bind)
    files=sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()); files.append('CURRENT_RUN_MANIFEST.yaml'); files=sorted(set(files)); write(root/'CURRENT_RUN_MANIFEST.yaml',{'run_uid':'MC2','current_files':files})
    return {'src':src,'sm':sm,'source_facts':source_facts,'arts':arts,'bp_page':bp_page,'bp_vis':bp_vis,'bind':bind}

def remanifest(r):
    files=sorted(p.relative_to(r).as_posix() for p in r.rglob('*') if p.is_file()); write(r/'CURRENT_RUN_MANIFEST.yaml',{'run_uid':'MC2','current_files':files})
def run(mut=None,residual=False):
    with tempfile.TemporaryDirectory() as td:
        r=Path(td); f=build(r)
        if mut: mut(r,f)
        if not residual: remanifest(r)
        return g.validate(PKG,r)['status']

cases=[]
def c(n,a,e): cases.append({'case':n,'actual':a,'expected':e,'ok':a==e})
c('valid_source_to_dual_blueprint_pipeline',run(),'PASS')

def missing_structure(r,f): (r/'00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml').unlink()
c('source_structure_manifest_required',run(missing_structure),'FAIL')

def omitted_required_node(r,f):
    f['sm']['source_segments']=[s for s in f['sm']['source_segments'] if s['source_node_uid']!='N-P2']; write(r/'00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml',f['sm'])
c('required_source_node_omission_detected',run(omitted_required_node),'FAIL')

def duplicate_node_segment(r,f):
    x=copy.deepcopy(f['sm']['source_segments'][0]); x['segment_uid']='S-P1B'; f['sm']['source_segments'].append(x); write(r/'00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml',f['sm'])
c('required_source_node_duplicate_segment_detected',run(duplicate_node_segment),'FAIL')

def domain_only(r,f):
    for p in list((r/'01_CLASSIFIED').rglob('*.yaml')): p.unlink()
c('domain_level_only_without_classification',run(domain_only),'FAIL')

def mixed_no_proof(r,f):
    p=r/f['arts'][0]['target_path']; d=yaml.safe_load(p.read_text()); d['responsibilities']=['PAGE_IDENTITY','PAGE_STRUCTURE']; d['content_hash']=g.content_hash(d); write(p,d)
c('multiple_responsibilities_without_scope_proof',run(mixed_no_proof),'FAIL')

def cross_domain_artifact(r,f):
    p=r/f['arts'][0]['target_path']; d=yaml.safe_load(p.read_text()); d['planning_domain']='VISUAL_CONSTRUCTION'; d['content_hash']=g.content_hash(d); write(p,d)
c('classification_cross_domain_detected',run(cross_domain_artifact),'FAIL')

def combined_blueprint(r,f):
    # replace two legal blueprints by one combined editable blueprint
    for p in list((r/'02_BASE_BLUEPRINT/CORE-01').glob('*.yaml')): p.unlink()
    d={'blueprint_uid':'BP-COMB','page_uid':'CORE-01','blueprint_type':'BASE_BLUEPRINT','planning_domain':'MIXED','target_path':'02_BASE_BLUEPRINT/CORE-01/BASE_BLUEPRINT.yaml','input_artifacts':[],'required_responsibility_uids':[],'raw_source_inputs':[],'embedded_classification_payloads':[],'status':'CURRENT_BASE_BLUEPRINT'}; d['blueprint_hash']=g.content_hash(d); write(r/d['target_path'],d)
c('combined_page_visual_blueprint_forbidden',run(combined_blueprint),'FAIL')

def page_consumes_visual(r,f):
    p=r/f['bp_page']['target_path']; d=yaml.safe_load(p.read_text()); av=[a for a in f['arts'] if a['artifact_uid']=='A-V1'][0]; d['input_artifacts'].append({'artifact_uid':'A-V1','content_hash':av['content_hash']}); d['required_responsibility_uids'].append('LAYOUT_GEOMETRY'); d['blueprint_hash']=g.content_hash(d); write(p,d)
c('page_blueprint_cannot_consume_visual_artifact',run(page_consumes_visual),'FAIL')

def raw_input(r,f):
    p=r/f['bp_page']['target_path']; d=yaml.safe_load(p.read_text()); d['raw_source_inputs']=['RAW1']; d['blueprint_hash']=g.content_hash(d); write(p,d)
c('blueprint_direct_raw_source_forbidden',run(raw_input),'FAIL')

def stale_binding(r,f):
    p=r/f['bind']['target_path']; d=yaml.safe_load(p.read_text()); d['page_blueprint']['blueprint_hash']='0'*64; d['binding_hash']=g.content_hash(d); write(p,d)
c('binding_stale_hash_detected',run(stale_binding),'FAIL')

def self_pass(r,f):
    f['sm']['status']='PASS'; f['sm']['complete']=True; f['sm']['source_segments']=[s for s in f['sm']['source_segments'] if s['source_node_uid']!='N-P2']; write(r/'00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml',f['sm'])
c('self_declared_pass_cannot_hide_source_omission',run(self_pass),'FAIL')

def norm_mismatch(r,f):
    p=r/'RUN_CONTEXT.yaml'; d=yaml.safe_load(p.read_text()); d['candidate_normative_hash']='f'*64; write(p,d)
c('candidate_hash_mismatch_detected',run(norm_mismatch),'FAIL')

def residual(r,f): write(r/'01_CLASSIFIED/CORE-01/PAGE/old-copy.bak','garbage')
c('residual_garbage_detected',run(residual,True),'FAIL')

def mixed_allowed(r,f):
    p=r/f['arts'][0]['target_path']; d=yaml.safe_load(p.read_text()); d['responsibilities']=['PAGE_IDENTITY','PAGE_IDENTITY_ALIAS']; d['mixed_allowed']=True; d['mixed_allowed_proof']={'same_owner':True,'same_lifecycle':True,'same_approval':True,'same_version':True,'same_test_scope':True}; d['content_hash']=g.content_hash(d); write(p,d)
    bp=r/f['bp_page']['target_path']; b=yaml.safe_load(bp.read_text());
    for rec in b['input_artifacts']:
        if rec['artifact_uid']==d['artifact_uid']: rec['content_hash']=d['content_hash']
    b['blueprint_hash']=g.content_hash(b); write(bp,b)
    bind=r/f['bind']['target_path']; bd=yaml.safe_load(bind.read_text()); bd['page_blueprint']['blueprint_hash']=b['blueprint_hash']; bd['binding_hash']=g.content_hash(bd); write(bind,bd)
c('mixed_allowed_same_scope_proof_is_legal',run(mixed_allowed),'PASS')

def partial_cannot_claim_full_closure(r,f):
    cp=r/'RUN_CONTEXT.yaml'; c=yaml.safe_load(cp.read_text()); c['formal_source_intake_closure_claim']=True; write(cp,c)
    sp=r/'00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml'; sd=yaml.safe_load(sp.read_text()); sd['sources'][0]['enumeration_state']='PARTIAL_SOURCE_ENUMERATION_PILOT'; sd['sources'][0]['structure_manifest_hash']=g.content_hash(sd['sources'][0]); write(sp,sd)
c('partial_enumeration_cannot_claim_full_source_closure',run(partial_cannot_claim_full_closure),'FAIL')


def classification_page_uid_drift(r,f):
    p=r/f['arts'][0]['target_path']; d=yaml.safe_load(p.read_text()); d['page_uid']='ASSET-01'; d['content_hash']=g.content_hash(d); write(p,d)
c('classification_page_uid_drift_detected',run(classification_page_uid_drift),'FAIL')

def lineage_unknown_source(r,f):
    p=r/f['arts'][0]['target_path']; d=yaml.safe_load(p.read_text()); d['source_lineage'][0]['source_uid']='MISSING'; d['content_hash']=g.content_hash(d); write(p,d)
c('artifact_lineage_unknown_source_detected',run(lineage_unknown_source),'FAIL')

def unresolved_shared_ref(r,f):
    p=r/f['bp_page']['target_path']; d=yaml.safe_load(p.read_text()); d['shared_refs']=[{'artifact_uid':'MISSING-SHARED'}]; d['blueprint_hash']=g.content_hash(d); write(p,d)
c('blueprint_unresolved_shared_ref_detected',run(unresolved_shared_ref),'FAIL')

def shared_fact_no_target(r,f):
    sm=yaml.safe_load((r/'00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml').read_text()); sm['source_segments'][0]['disposition']='SHARED_FACT_REFERENCE'; sm['source_segments'][0]['target_artifact_uids']=[]; sm['source_segments'][0]['authority_evidence_ref']='00_SOURCE_INTAKE/evidence/E1.yaml'; write(r/'00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml',sm)
c('shared_fact_without_physical_target_detected',run(shared_fact_no_target),'FAIL')

def run_uid_mismatch(r,f):
    p=r/'RUN_CONTEXT.yaml'; d=yaml.safe_load(p.read_text()); d['run_uid']='DIFFERENT'; write(p,d)
c('run_uid_mismatch_detected',run(run_uid_mismatch),'FAIL')

def invalid_stage_uid(r,f):
    p=r/'RUN_CONTEXT.yaml'; d=yaml.safe_load(p.read_text()); d['stage_uid']='STAGE-99'; write(p,d)
c('invalid_stage_uid_detected',run(invalid_stage_uid),'FAIL')

def source_node_missing_ref(r,f):
    p=r/'00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml'; d=yaml.safe_load(p.read_text()); del d['sources'][0]['observed_nodes'][0]['source_ref']; d['sources'][0]['structure_manifest_hash']=g.content_hash(d['sources'][0]); write(p,d)
c('source_node_missing_source_ref_detected',run(source_node_missing_ref),'FAIL')

def evidence_not_physical(r,f):
    p=r/'00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml'; d=yaml.safe_load(p.read_text()); d['sources'][0]['evidence_ref']='00_SOURCE_INTAKE/evidence/MISSING.yaml'; d['sources'][0]['structure_manifest_hash']=g.content_hash(d['sources'][0]); write(p,d)
c('source_enumeration_evidence_physicality_detected',run(evidence_not_physical),'FAIL')

def manifested_old_copy(r,f):
    write(r/'01_CLASSIFIED/CORE-01/PAGE/PAGE_IDENTITY_old-copy.yaml',yaml.safe_load((r/f['arts'][0]['target_path']).read_text()))
c('manifested_old_copy_filename_detected',run(manifested_old_copy),'FAIL')

def raw_source_missing_page_uid(r,f):
    p=r/'00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml'; d=yaml.safe_load(p.read_text()); d['raw_sources'][0].pop('page_uid',None); write(p,d)
c('raw_source_missing_page_uid_detected',run(raw_source_missing_page_uid),'FAIL')

def source_fact_missing(r,f):
    (r/'00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml').unlink()
c('required_source_fact_missing_detected',run(source_fact_missing),'FAIL')

def raw_capture_not_closed(r,f):
    p=r/'00_SOURCE_INTAKE/RAW_SOURCE_CAPTURE_STATE.yaml'; d=yaml.safe_load(p.read_text()); d['state']='CAPTURE_ACTIVE'; write(p,d)
c('raw_capture_must_be_terminally_closed',run(raw_capture_not_closed),'FAIL')

def raw_capture_wrong_next_step_alias(r,f):
    p=r/'00_SOURCE_INTAKE/RAW_SOURCE_CAPTURE_STATE.yaml'; d=yaml.safe_load(p.read_text()); d['next_step']='SOURCE_STRUCTURE_CLASSIFICATION'; write(p,d)
c('raw_capture_next_step_must_be_exact_enumeration_identity',run(raw_capture_wrong_next_step_alias),'FAIL')

def mixed_source_biased_role(r,f):
    p=r/'00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml'; d=yaml.safe_load(p.read_text()); d['records'][0]['source_role']='PAGE_SOURCE_INPUT'; write(p,d)
    sp=r/'00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml'; sd=yaml.safe_load(sp.read_text()); sd['raw_sources'][0]['source_role']='PAGE_SOURCE_INPUT'; write(sp,sd)
c('mixed_page_visual_source_role_must_be_neutral',run(mixed_source_biased_role),'FAIL')

def raw_source_directory_metadata_pollution(r,f):
    write(r/'00_SOURCE_INTAKE/RAW_SOURCE/README.md','control metadata must not be here')
c('raw_source_directory_must_contain_source_bytes_only',run(raw_source_directory_metadata_pollution),'FAIL')

def mixed_terminal_source_node(r,f):
    p=r/'00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml'; d=yaml.safe_load(p.read_text()); n=d['sources'][0]['observed_nodes'][0]; n['semantic_responsibility_count']=2; d['sources'][0]['structure_manifest_hash']=g.content_hash(d['sources'][0]); write(p,d)
c('mixed_terminal_source_node_must_be_recursively_decomposed',run(mixed_terminal_source_node),'FAIL')

def unresolved_container_source_node(r,f):
    p=r/'00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml'; d=yaml.safe_load(p.read_text()); n=d['sources'][0]['observed_nodes'][0]; n['terminality_state']='UNRESOLVED_CONTAINER'; n['unresolved_child_responsibility_count']=1; d['sources'][0]['structure_manifest_hash']=g.content_hash(d['sources'][0]); write(p,d)
c('unresolved_container_node_blocks_stage1_closure',run(unresolved_container_source_node),'FAIL')


def _make_minimal_docx(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    ct='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'''
    rootrels='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
    doc='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>固定來源</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>表格內容</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:sectPr/></w:body></w:document>'''
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',ct); z.writestr('_rels/.rels',rootrels); z.writestr('word/document.xml',doc)

def _projection_fixture(root):
    rawrel='00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/SOURCE.docx'; raw=root/rawrel; _make_minimal_docx(raw)
    rawsha=g.file_sha(raw); blob=g.git_blob_sha(raw); suid='DOCX1'
    rawcap={'artifact_uid':'RAW-CAP-DOCX','artifact_type':'RAW_SOURCE_REFERENCE_MANIFEST','status':'CURRENT_RAW_SOURCE_CAPTURE','capture_root':'00_SOURCE_INTAKE/RAW_SOURCE','records':[{'source_uid':suid,'source_format':'DOCX','projection_required':True,'page_uid':'CORE-01','source_role':'MIXED_PAGE_VISUAL_SOURCE_INPUT','source_domain_scope':'MIXED_PAGE_VISUAL','source_path':'fixture://docx1','target_path':rawrel,'source_git_blob_sha':blob,'target_git_blob_sha':blob,'content_mutated':False}]}
    capstate={'run_uid':'PROJ1','state':'CAPTURE_CLOSED','next_step':'CANONICAL_SOURCE_PROJECTION','recapture_allowed':False}
    contract=g._projection_contract(PKG); rc=contract['raw_source_lock']; pc=contract['projection']; ac=contract['reconciliation']; fc=contract['pair_freeze']; base=f"00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{suid}"
    lock={'schema_version':1,'artifact_uid':'LOCK-DOCX1','artifact_type':'RAW_SOURCE_IMMUTABILITY_RECEIPT','source_uid':suid,'source_path':rawrel,'source_git_blob_sha':blob,'source_sha256':rawsha,'lock_state':'RAW_CAPTURE_LOCKED','writable':False,'mutation_policy':'NEW_SOURCE_REVISION_NEW_PROJECTION_NEW_RECONCILIATION'}
    lock['content_hash']=g._hash_without(lock,'content_hash'); write(root/f'{base}/RAW_SOURCE_IMMUTABILITY_RECEIPT.yaml',lock)
    inv=g.derive_docx_inventory(raw)
    den=[{'denominator_uid':'DEN-PACKAGE-PART','denominator_type':'PACKAGE_PART','required_count':len(inv['package_parts']),'projected_count':len(inv['package_parts'])},{'denominator_uid':'DEN-RELATIONSHIP','denominator_type':'RELATIONSHIP','required_count':len(inv['relationships']),'projected_count':len(inv['relationships'])},{'denominator_uid':'DEN-XML-NODE','denominator_type':'XML_NODE','required_count':len(inv['source_nodes']),'projected_count':len(inv['source_nodes'])}]
    proj={'schema_version':1,'artifact_uid':'PROJ-DOCX1','artifact_type':'CANONICAL_SOURCE_PROJECTION','projection_schema_uid':pc['schema_uid'],'projection_schema_revision':pc['schema_revision'],'projection_role':pc['role'],'normative_authority':False,'source_identity':{'source_uid':suid,'source_path':rawrel,'source_format':'DOCX','source_git_blob_sha':blob,'source_sha256':rawsha,'raw_source_lock_receipt_uid':lock['artifact_uid']},'extraction_identity':{'extractor_uid':'TEST-EXTRACTOR','extractor_version':'1','extraction_run_uid':'RUN-1','extraction_evidence_ref':'fixture://extract'},'serialization_contract':{'yaml_profile':'YAML_1_2_SAFE_SUBSET','encoding':'UTF-8','line_ending':'LF','key_order_contract_uid':pc['schema_uid'],'anchors_aliases':'FORBIDDEN','implicit_custom_tags':'FORBIDDEN'},'denominator_rows':den,'package_parts':inv['package_parts'],'relationships':inv['relationships'],'source_nodes':inv['source_nodes']}
    proj['projection_content_hash']=None; proj['status']='PROJECTION_COMPLETE'; proj['projection_content_hash']=g._hash_without(proj,'projection_content_hash'); write(root/f'{base}/CANONICAL_SOURCE_PROJECTION.yaml',proj)
    zero={k:0 for k in ac['zero_loss_count_field_order']}
    ev={'schema_version':1,'artifact_uid':'RECON-DOCX1','artifact_type':'SOURCE_PROJECTION_RECONCILIATION_EVIDENCE','validator_uid':'VAL-GOV-026','source_uid':suid,'raw_source_sha256':rawsha,'projection_uid':proj['artifact_uid'],'projection_content_hash':proj['projection_content_hash'],'projection_schema_uid':pc['schema_uid'],'projection_schema_revision':pc['schema_revision'],'source_inventory_hashes':{'package_parts_hash':inv['package_parts_hash'],'relationships_hash':inv['relationships_hash'],'source_nodes_hash':inv['source_nodes_hash']},'zero_loss_counts':zero,'reverse_trace':'COMPLETE','unsupported_count':0,'result':'PASS'}
    ev['evidence_content_hash']=g._hash_without(ev,'evidence_content_hash'); write(root/f'{base}/SOURCE_PROJECTION_RECONCILIATION_EVIDENCE.yaml',ev)
    dh=g.stable_hash_obj(den); pair=g.sha256_bytes((rawsha+'\n'+proj['projection_content_hash']+'\n'+ev['evidence_content_hash']+'\n'+pc['schema_uid']+'\n'+str(pc['schema_revision'])+'\n'+dh+'\n').encode())
    fr={'schema_version':1,'artifact_uid':'FREEZE-DOCX1','artifact_type':'SOURCE_PROJECTION_FREEZE_RECEIPT','source_uid':suid,'raw_source_sha256':rawsha,'raw_source_git_blob_sha':blob,'projection_uid':proj['artifact_uid'],'projection_content_hash':proj['projection_content_hash'],'projection_schema_uid':pc['schema_uid'],'projection_schema_revision':pc['schema_revision'],'reconciliation_evidence_uid':ev['artifact_uid'],'reconciliation_evidence_hash':ev['evidence_content_hash'],'source_denominator_hash':dh,'pair_hash':pair,'lock_state':'SOURCE_PAIR_FROZEN','raw_source_writable':False,'projection_writable':False,'mutation_disposition':'INVALIDATE_PAIR_REQUIRE_NEW_RECONCILIATION','next_step':'STAGE01_WORK_UNIT_RESOLUTION','status':'FROZEN_FOR_STAGE01'}; write(root/f'{base}/SOURCE_PROJECTION_FREEZE_RECEIPT.yaml',fr)
    return rawcap,capstate,{'base':base,'raw':raw,'proj':proj,'ev':ev,'freeze':fr}

def _prun(mut=None):
    with tempfile.TemporaryDirectory() as td:
        r=Path(td); rawcap,capstate,f=_projection_fixture(r)
        if mut: mut(r,rawcap,capstate,f)
        return 'PASS' if not g.validate_pre_stage_source_projection(PKG,r,rawcap,capstate)['failures'] else 'FAIL'

c('projection_fixed_schema_positive',_prun(),'PASS')
def _p_word_mutation(r,rawcap,capstate,f): f['raw'].write_bytes(f['raw'].read_bytes()+b'X')
c('projection_word_byte_mutation_after_lock',_prun(_p_word_mutation),'FAIL')
def _p_missing_node(r,rawcap,capstate,f):
    p=r/f"{f['base']}/CANONICAL_SOURCE_PROJECTION.yaml"; d=yaml.safe_load(p.read_text()); d['source_nodes']=d['source_nodes'][:-1]; d['projection_content_hash']=g._hash_without(d,'projection_content_hash'); write(p,d)
c('projection_missing_source_node',_prun(_p_missing_node),'FAIL')
def _p_duplicate_node(r,rawcap,capstate,f):
    p=r/f"{f['base']}/CANONICAL_SOURCE_PROJECTION.yaml"; d=yaml.safe_load(p.read_text()); d['source_nodes'].append(copy.deepcopy(d['source_nodes'][0])); d['projection_content_hash']=g._hash_without(d,'projection_content_hash'); write(p,d)
c('projection_duplicate_source_node',_prun(_p_duplicate_node),'FAIL')
def _p_order_drift(r,rawcap,capstate,f):
    p=r/f"{f['base']}/CANONICAL_SOURCE_PROJECTION.yaml"; d=yaml.safe_load(p.read_text()); d['source_nodes'][0],d['source_nodes'][1]=d['source_nodes'][1],d['source_nodes'][0]; d['projection_content_hash']=g._hash_without(d,'projection_content_hash'); write(p,d)
c('projection_source_order_drift',_prun(_p_order_drift),'FAIL')
def _p_extra_field(r,rawcap,capstate,f):
    p=r/f"{f['base']}/CANONICAL_SOURCE_PROJECTION.yaml"; d=yaml.safe_load(p.read_text()); d['source_nodes'][0]['ad_hoc']='x'; d['projection_content_hash']=g._hash_without(d,'projection_content_hash'); write(p,d)
c('projection_extra_field_schema_drift',_prun(_p_extra_field),'FAIL')
def _p_relation_omit(r,rawcap,capstate,f):
    p=r/f"{f['base']}/CANONICAL_SOURCE_PROJECTION.yaml"; d=yaml.safe_load(p.read_text()); d['relationships']=[]; d['projection_content_hash']=g._hash_without(d,'projection_content_hash'); write(p,d)
c('projection_relationship_omission',_prun(_p_relation_omit),'FAIL')
def _p_fake_pass(r,rawcap,capstate,f):
    p=r/f"{f['base']}/SOURCE_PROJECTION_RECONCILIATION_EVIDENCE.yaml"; d=yaml.safe_load(p.read_text()); d['zero_loss_counts']['missing_source_nodes']=1; d['evidence_content_hash']=g._hash_without(d,'evidence_content_hash'); write(p,d)
c('projection_self_declared_pass_nonzero_mismatch',_prun(_p_fake_pass),'FAIL')
def _p_freeze_missing(r,rawcap,capstate,f): (r/f"{f['base']}/SOURCE_PROJECTION_FREEZE_RECEIPT.yaml").unlink()
c('projection_freeze_receipt_required',_prun(_p_freeze_missing),'FAIL')
def _p_pair_hash(r,rawcap,capstate,f):
    p=r/f"{f['base']}/SOURCE_PROJECTION_FREEZE_RECEIPT.yaml"; d=yaml.safe_load(p.read_text()); d['pair_hash']='0'*64; write(p,d)
c('projection_pair_hash_mismatch',_prun(_p_pair_hash),'FAIL')
def _p_semantic_field(r,rawcap,capstate,f):
    p=r/f"{f['base']}/CANONICAL_SOURCE_PROJECTION.yaml"; d=yaml.safe_load(p.read_text()); d['source_nodes'][0]['responsibility_uid']='PAGE'; d['projection_content_hash']=g._hash_without(d,'projection_content_hash'); write(p,d)
c('projection_semantic_interpretation_forbidden',_prun(_p_semantic_field),'FAIL')

out={'suite':'Stage-1 Source Enumeration → Classification → Dual Base Blueprint minimal-control','fixture_policy':'OBSERVABLE_FACTS_ONLY','validator_receives_expected_outcome':False,'total':len(cases),'passed_expectations':sum(x['ok'] for x in cases),'results':cases}
print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['passed_expectations']==out['total'] else 1)
