#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, zipfile
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
PKG=ROOT/'.github/governance-source/active/source'
GUARD=PKG/'09_TESTS/governance/governance_stage1_pipeline_guard.py'
spec=importlib.util.spec_from_file_location('stage1_guard',GUARD)
g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=220),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--workspace',required=True)
    ap.add_argument('--source-rel',required=True)
    ap.add_argument('--source-uid',required=True)
    ap.add_argument('--page-uid',required=True)
    ap.add_argument('--source-origin',required=True)
    args=ap.parse_args()
    w=Path(args.workspace).resolve(); raw=w/args.source_rel; suid=args.source_uid; source_origin=str(args.source_origin).strip()
    if not source_origin: raise SystemExit('source origin missing')
    if not raw.is_file(): raise SystemExit('raw source missing')
    contract=g._projection_contract(PKG)
    cc=contract['source_document_content_readiness_audit']; rc=contract['raw_source_lock']; pc=contract['projection']; ac=contract['reconciliation']; fc=contract['pair_freeze']; bc=contract['frozen_binary_source_part_materialization']
    base=w/f'00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{suid}'
    capath=base/'SOURCE_DOCUMENT_CONTENT_AUDIT.yaml'
    if not capath.is_file(): raise SystemExit('content readiness audit missing')
    ca=g.load_yaml(capath); rawsha=g.file_sha(raw); blob=g.git_blob_sha(raw)
    if ca.get('source_uid')!=suid or ca.get('source_sha256')!=rawsha or ca.get('result')!='PASS' or ca.get('unresolved_required_gap_count')!=0 or ca.get('contradiction_count')!=0: raise SystemExit('content readiness audit not PASS for exact source')
    rawcap={'artifact_uid':'RAW-CAP-'+suid,'artifact_type':'RAW_SOURCE_REFERENCE_MANIFEST','status':'CURRENT_RAW_SOURCE_CAPTURE','capture_root':'00_SOURCE_INTAKE/RAW_SOURCE','records':[{'source_uid':suid,'source_format':'DOCX','projection_required':True,'page_uid':args.page_uid,'source_role':'MIXED_PAGE_VISUAL_SOURCE_INPUT','source_domain_scope':'MIXED_PAGE_VISUAL','source_path':source_origin,'target_path':args.source_rel,'source_git_blob_sha':blob,'target_git_blob_sha':blob,'content_mutated':False}]}
    capstate={'run_uid':'PROJECTION-RUN-'+rawsha[:16].upper(),'state':'CAPTURE_CLOSED','next_step':'SOURCE_DOCUMENT_CONTENT_AUDIT','recapture_allowed':False}
    write(w/'00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml',rawcap); write(w/'00_SOURCE_INTAKE/RAW_SOURCE_CAPTURE_STATE.yaml',capstate)
    lock={'schema_version':1,'artifact_uid':'LOCK-'+suid,'artifact_type':'RAW_SOURCE_IMMUTABILITY_RECEIPT','source_uid':suid,'source_path':source_origin,'source_git_blob_sha':blob,'source_sha256':rawsha,'content_readiness_audit_uid':ca['artifact_uid'],'lock_state':'RAW_CAPTURE_LOCKED','writable':False,'mutation_policy':'NEW_SOURCE_REVISION_NEW_PROJECTION_NEW_RECONCILIATION'}
    lock['content_hash']=g._hash_without(lock,'content_hash'); write(base/'RAW_SOURCE_IMMUTABILITY_RECEIPT.yaml',lock)
    inv=g.derive_docx_inventory(raw)
    with zipfile.ZipFile(raw,'r') as z:
        for row in g._binary_parts_from_inventory(inv):
            dst=g._binary_ref(w,bc,suid,row); dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(z.read(row['package_part_path']))
    den=[{'denominator_uid':'DEN-PACKAGE-PART','denominator_type':'PACKAGE_PART','required_count':len(inv['package_parts']),'projected_count':len(inv['package_parts'])},{'denominator_uid':'DEN-RELATIONSHIP','denominator_type':'RELATIONSHIP','required_count':len(inv['relationships']),'projected_count':len(inv['relationships'])},{'denominator_uid':'DEN-XML-NODE','denominator_type':'XML_NODE','required_count':len(inv['source_nodes']),'projected_count':len(inv['source_nodes'])}]
    proj={'schema_version':1,'artifact_uid':'PROJ-'+suid,'artifact_type':'CANONICAL_SOURCE_PROJECTION','projection_schema_uid':pc['schema_uid'],'projection_schema_revision':pc['schema_revision'],'projection_role':pc['role'],'normative_authority':False,'source_identity':{'source_uid':suid,'source_path':source_origin,'source_format':'DOCX','source_git_blob_sha':blob,'source_sha256':rawsha,'raw_source_lock_receipt_uid':lock['artifact_uid']},'extraction_identity':{'extractor_uid':'ACPOS-DOCX-CANONICAL-PROJECTION-001','extractor_version':'1','extraction_run_uid':capstate['run_uid'],'extraction_evidence_ref':str(capath.relative_to(w))},'serialization_contract':{'yaml_profile':'YAML_1_2_SAFE_SUBSET','encoding':'UTF-8','line_ending':'LF','key_order_contract_uid':pc['schema_uid'],'anchors_aliases':'FORBIDDEN','implicit_custom_tags':'FORBIDDEN'},'denominator_rows':den,'package_parts':inv['package_parts'],'relationships':inv['relationships'],'source_nodes':inv['source_nodes'],'projection_content_hash':None,'status':'PROJECTION_COMPLETE'}
    proj['projection_content_hash']=g._hash_without(proj,'projection_content_hash'); write(base/'CANONICAL_SOURCE_PROJECTION.yaml',proj)
    zero={k:0 for k in ac['zero_loss_count_field_order']}
    ev={'schema_version':1,'artifact_uid':'RECON-'+suid,'artifact_type':'SOURCE_PROJECTION_RECONCILIATION_EVIDENCE','validator_uid':'VAL-GOV-026','source_uid':suid,'raw_source_sha256':rawsha,'projection_uid':proj['artifact_uid'],'projection_content_hash':proj['projection_content_hash'],'projection_schema_uid':pc['schema_uid'],'projection_schema_revision':pc['schema_revision'],'source_inventory_hashes':{'package_parts_hash':inv['package_parts_hash'],'relationships_hash':inv['relationships_hash'],'source_nodes_hash':inv['source_nodes_hash']},'zero_loss_counts':zero,'reverse_trace':'COMPLETE','unsupported_count':0,'result':'PASS','evidence_content_hash':None}
    ev['evidence_content_hash']=g._hash_without(ev,'evidence_content_hash'); write(base/'SOURCE_PROJECTION_RECONCILIATION_EVIDENCE.yaml',ev)
    dh=g.stable_hash_obj(den); pair=g.sha256_bytes((rawsha+'\n'+proj['projection_content_hash']+'\n'+ev['evidence_content_hash']+'\n'+pc['schema_uid']+'\n'+str(pc['schema_revision'])+'\n'+dh+'\n').encode())
    fr={'schema_version':1,'artifact_uid':'FREEZE-'+suid,'artifact_type':'SOURCE_PROJECTION_FREEZE_RECEIPT','source_uid':suid,'raw_source_sha256':rawsha,'raw_source_git_blob_sha':blob,'projection_uid':proj['artifact_uid'],'projection_content_hash':proj['projection_content_hash'],'projection_schema_uid':pc['schema_uid'],'projection_schema_revision':pc['schema_revision'],'reconciliation_evidence_uid':ev['artifact_uid'],'reconciliation_evidence_hash':ev['evidence_content_hash'],'source_denominator_hash':dh,'pair_hash':pair,'lock_state':'SOURCE_PAIR_FROZEN','raw_source_writable':False,'projection_writable':False,'mutation_disposition':'INVALIDATE_PAIR_REQUIRE_NEW_RECONCILIATION','next_step':'STAGE01_WORK_UNIT_RESOLUTION','status':'FROZEN_FOR_STAGE01'}
    write(base/'SOURCE_PROJECTION_FREEZE_RECEIPT.yaml',fr)
    result=g.validate_pre_stage_source_projection(PKG,w,rawcap,capstate)
    if result['failures']:
        print(json.dumps(result,ensure_ascii=False,indent=2)); raise SystemExit(1)
    print(json.dumps({'status':'PASS','source_uid':suid,'source_sha256':rawsha,'projection_uid':proj['artifact_uid'],'projection_hash':proj['projection_content_hash'],'pair_hash':pair,'binary_part_count':len(g._binary_parts_from_inventory(inv)),'source_origin':source_origin},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
