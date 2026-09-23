#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json, os, re, sys, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
PKG=ROOT/'.github/governance-source/active/source'
CONTRACT=PKG/'10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml'

def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def file_sha(p): return sha256_bytes(Path(p).read_bytes())
def git_blob_sha(p):
    b=Path(p).read_bytes()
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def stable_hash_obj(o): return sha256_bytes(yaml.safe_dump(o,allow_unicode=True,sort_keys=True).encode('utf-8'))
def hash_without(d,key):
    x=copy.deepcopy(d); x.pop(key,None); return stable_hash_obj(x)
def local(q): return q.rsplit('}',1)[-1] if '}' in q else q

def content_types(z):
    root=ET.fromstring(z.read('[Content_Types].xml')); defaults={}; overrides={}
    for e in root:
        ln=local(e.tag)
        if ln=='Default': defaults[str(e.attrib.get('Extension') or '').lower()]=str(e.attrib.get('ContentType') or '')
        elif ln=='Override': overrides[str(e.attrib.get('PartName') or '').lstrip('/')]=str(e.attrib.get('ContentType') or '')
    return defaults,overrides

def independent_inventory(raw):
    package=[]; rels=[]; nodes=[]
    with zipfile.ZipFile(raw,'r') as z:
        names=sorted(n for n in z.namelist() if not n.endswith('/'))
        defaults,overrides=content_types(z)
        for n in names:
            b=z.read(n); ext=n.rsplit('.',1)[-1].lower() if '.' in n else ''
            package.append({'package_part_path':n,'content_type':overrides.get(n,defaults.get(ext,'')),'size_bytes':len(b),'part_sha256':sha256_bytes(b)})
        for n in sorted(x for x in names if x.endswith('.rels')):
            rr=ET.fromstring(z.read(n))
            for e in list(rr):
                if local(e.tag)!='Relationship': continue
                rels.append({'relationship_part_path':n,'relationship_id':str(e.attrib.get('Id') or ''),'relationship_type':str(e.attrib.get('Type') or ''),'target':str(e.attrib.get('Target') or ''),'target_mode':str(e.attrib.get('TargetMode') or 'Internal')})
        rels.sort(key=lambda x:(x['relationship_part_path'],x['relationship_id']))
        global_index=0; doc_index=0
        kind_map={'p':'PARAGRAPH','tbl':'TABLE','tr':'TABLE_ROW','tc':'TABLE_CELL','r':'TEXT_RUN','t':'TEXT','drawing':'DRAWING','hyperlink':'HYPERLINK','sectPr':'SECTION_PROPERTIES','br':'BREAK','tab':'TAB'}
        for n in sorted(x for x in names if x.endswith('.xml') and x!='[Content_Types].xml'):
            root=ET.fromstring(z.read(n))
            def walk(e,path,parent_uid):
                nonlocal global_index,doc_index
                global_index+=1
                q=str(e.tag); ln=local(q)
                uid='SN-'+sha256_bytes((n+'\0'+path+'\0'+q).encode())[:24].upper()
                doi=None
                if n=='word/document.xml': doc_index+=1; doi=doc_index
                attrs=json.dumps({str(k):str(v) for k,v in sorted(e.attrib.items())},ensure_ascii=False,separators=(',',':'))
                base={'source_node_uid':uid,'source_node_kind':kind_map.get(ln,'OOXML_ELEMENT'),'projection_order_index':global_index,'document_order_index':doi,'package_part_path':n,'xml_qname':q,'xml_path':path,'parent_source_node_uid':parent_uid,'attributes_json':attrs,'direct_text':e.text or '','tail_text':e.tail or '','element_xml_sha256':sha256_bytes(ET.tostring(e,encoding='utf-8'))}
                row=dict(base); row['node_content_sha256']=stable_hash_obj(base); row['projection_status']='PROJECTED'; row['unsupported_reason']=None
                nodes.append(row)
                for i,ch in enumerate(list(e)): walk(ch,path+'/'+str(i),uid)
            walk(root,'/0',None)
    return {'package_parts':package,'relationships':rels,'source_nodes':nodes,'package_parts_hash':stable_hash_obj(package),'relationships_hash':stable_hash_obj(rels),'source_nodes_hash':stable_hash_obj(nodes)}

def exact_keys(d,expected,label,fail):
    actual=list(d.keys()) if isinstance(d,dict) else []
    if actual!=list(expected): fail.append(f'{label}_FIELD_ORDER_MISMATCH expected={list(expected)} actual={actual}')

def resolve_template(t,suid): return str(t).replace('{source_uid}',suid)
def is_binary(p): return not str(p).lower().endswith(('.xml','.rels'))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--workspace',required=True)
    ap.add_argument('--source-uid',required=True)
    ap.add_argument('--write-evidence')
    a=ap.parse_args(); w=Path(a.workspace).resolve(); suid=a.source_uid
    c=(load(CONTRACT).get('structured_document_source_projection_contract') or {})
    rawcap=load(w/'00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml')
    capstate=load(w/'00_SOURCE_INTAKE/RAW_SOURCE_CAPTURE_STATE.yaml')
    rec=next((x for x in rawcap.get('records') or [] if str(x.get('source_uid'))==suid),None)
    fail=[]
    if not rec: print(json.dumps({'status':'FAIL','failures':['SOURCE_RECORD_MISSING']})); raise SystemExit(1)
    target=str(rec.get('target_path') or ''); origin=str(rec.get('source_path') or ''); raw=w/target
    if not raw.is_file(): fail.append('RAW_SOURCE_MISSING')
    if not origin or origin==target: fail.append('SOURCE_ORIGIN_NOT_DISTINCT_FROM_WORKSPACE_TARGET')
    if not re.search(r'@[0-9a-f]{40}/',origin): fail.append('SOURCE_ORIGIN_EXACT_COMMIT_NOT_ENCODED')
    raw_sha=file_sha(raw) if raw.is_file() else ''; blob=git_blob_sha(raw) if raw.is_file() else ''
    if rec.get('source_git_blob_sha')!=blob or rec.get('target_git_blob_sha')!=blob: fail.append('RAW_SOURCE_BLOB_BINDING_MISMATCH')
    if rec.get('content_mutated') is not False: fail.append('RAW_SOURCE_CONTENT_MUTATION_FLAG_INVALID')
    base=w/f'00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{suid}'
    ca=load(base/'SOURCE_DOCUMENT_CONTENT_AUDIT.yaml')
    lock=load(base/'RAW_SOURCE_IMMUTABILITY_RECEIPT.yaml')
    proj=load(base/'CANONICAL_SOURCE_PROJECTION.yaml')
    ev=load(base/'SOURCE_PROJECTION_RECONCILIATION_EVIDENCE.yaml')
    freeze=load(base/'SOURCE_PROJECTION_FREEZE_RECEIPT.yaml')
    cc=c.get('source_document_content_readiness_audit') or {}; rc=c.get('raw_source_lock') or {}; pc=c.get('projection') or {}; ec=c.get('reconciliation') or {}; fc=c.get('pair_freeze') or {}; bc=c.get('frozen_binary_source_part_materialization') or {}
    exact_keys(ca,cc.get('required_field_order') or [],'CONTENT_AUDIT',fail)
    exact_keys(lock,rc.get('required_field_order') or [],'RAW_LOCK',fail)
    exact_keys(proj,pc.get('canonical_top_level_field_order') or [],'PROJECTION',fail)
    exact_keys(proj.get('source_identity') or {},pc.get('source_identity_field_order') or [],'PROJECTION_SOURCE_IDENTITY',fail)
    exact_keys(proj.get('extraction_identity') or {},pc.get('extraction_identity_field_order') or [],'PROJECTION_EXTRACTION_IDENTITY',fail)
    exact_keys(proj.get('serialization_contract') or {},pc.get('serialization_contract_field_order') or [],'PROJECTION_SERIALIZATION',fail)
    exact_keys(ev,ec.get('required_field_order') or [],'RECONCILIATION_EVIDENCE',fail)
    exact_keys(freeze,fc.get('required_field_order') or [],'FREEZE_RECEIPT',fail)
    if ca.get('result')!='PASS' or ca.get('unresolved_required_gap_count')!=0 or ca.get('contradiction_count')!=0 or (ca.get('missing_required_design_domain_uids') or []): fail.append('CONTENT_AUDIT_NOT_PASS')
    if ca.get('source_uid')!=suid or ca.get('source_sha256')!=raw_sha: fail.append('CONTENT_AUDIT_SOURCE_BINDING_MISMATCH')
    if ca.get('evidence_content_hash')!=hash_without(ca,'evidence_content_hash'): fail.append('CONTENT_AUDIT_HASH_MISMATCH')
    if lock.get('source_path')!=origin or (proj.get('source_identity') or {}).get('source_path')!=origin: fail.append('SOURCE_ORIGIN_LINEAGE_MISMATCH')
    if lock.get('source_sha256')!=raw_sha or lock.get('source_git_blob_sha')!=blob: fail.append('RAW_LOCK_HASH_MISMATCH')
    if lock.get('content_readiness_audit_uid')!=ca.get('artifact_uid'): fail.append('RAW_LOCK_CONTENT_AUDIT_UID_MISMATCH')
    if lock.get('content_hash')!=hash_without(lock,'content_hash'): fail.append('RAW_LOCK_CONTENT_HASH_MISMATCH')
    expected=independent_inventory(raw)
    if proj.get('package_parts')!=expected['package_parts']: fail.append('PACKAGE_PART_DENOMINATOR_OR_CONTENT_MISMATCH')
    if proj.get('relationships')!=expected['relationships']: fail.append('RELATIONSHIP_DENOMINATOR_OR_CONTENT_MISMATCH')
    if proj.get('source_nodes')!=expected['source_nodes']: fail.append('SOURCE_NODE_DENOMINATOR_OR_CONTENT_MISMATCH')
    den=[{'denominator_uid':'DEN-PACKAGE-PART','denominator_type':'PACKAGE_PART','required_count':len(expected['package_parts']),'projected_count':len(expected['package_parts'])},{'denominator_uid':'DEN-RELATIONSHIP','denominator_type':'RELATIONSHIP','required_count':len(expected['relationships']),'projected_count':len(expected['relationships'])},{'denominator_uid':'DEN-XML-NODE','denominator_type':'XML_NODE','required_count':len(expected['source_nodes']),'projected_count':len(expected['source_nodes'])}]
    if proj.get('denominator_rows')!=den: fail.append('PROJECTION_DENOMINATOR_ROWS_MISMATCH')
    ph=hash_without(proj,'projection_content_hash')
    if proj.get('projection_content_hash')!=ph: fail.append('PROJECTION_CONTENT_HASH_MISMATCH')
    if (proj.get('source_identity') or {}).get('source_sha256')!=raw_sha or (proj.get('source_identity') or {}).get('source_git_blob_sha')!=blob: fail.append('PROJECTION_SOURCE_HASH_MISMATCH')
    raw_yaml=(base/'CANONICAL_SOURCE_PROJECTION.yaml').read_bytes()
    if b'\r' in raw_yaml: fail.append('PROJECTION_LINE_ENDING_NOT_LF')
    if re.search(rb'(?m)(?:^|\s)[&*][A-Za-z0-9_-]+',raw_yaml): fail.append('YAML_ANCHOR_OR_ALIAS_PRESENT')
    broot=w/resolve_template(bc.get('storage_root_template',''),suid)
    expected_paths=set()
    with zipfile.ZipFile(raw,'r') as z:
        for row in expected['package_parts']:
            if not is_binary(row['package_part_path']): continue
            suffix=Path(row['package_part_path']).suffix.lower()
            bp=broot/(row['part_sha256']+suffix); expected_paths.add(bp)
            if not bp.is_file(): fail.append('FROZEN_BINARY_MISSING:'+row['package_part_path']); continue
            bb=bp.read_bytes()
            if sha256_bytes(bb)!=row['part_sha256'] or len(bb)!=row['size_bytes'] or bb!=z.read(row['package_part_path']): fail.append('FROZEN_BINARY_NOT_EXACT:'+row['package_part_path'])
    actual=set(p for p in broot.iterdir() if p.is_file()) if broot.is_dir() else set()
    if actual!=expected_paths: fail.append('FROZEN_BINARY_SET_MISMATCH')
    invh=ev.get('source_inventory_hashes') or {}
    for k in ['package_parts_hash','relationships_hash','source_nodes_hash']:
        if invh.get(k)!=expected[k]: fail.append('RECONCILIATION_INVENTORY_HASH_MISMATCH:'+k)
    zeros=ev.get('zero_loss_counts') or {}
    if any(v!=0 for v in zeros.values()): fail.append('RECONCILIATION_NONZERO_LOSS_COUNT')
    if set(zeros.keys())!=set(ec.get('zero_loss_count_field_order') or []): fail.append('RECONCILIATION_ZERO_LOSS_FIELD_SET_MISMATCH')
    if ev.get('result')!='PASS' or ev.get('reverse_trace')!='COMPLETE' or ev.get('unsupported_count')!=0: fail.append('RECONCILIATION_NOT_TERMINAL_PASS')
    eh=hash_without(ev,'evidence_content_hash')
    if ev.get('evidence_content_hash')!=eh: fail.append('RECONCILIATION_EVIDENCE_HASH_MISMATCH')
    dh=stable_hash_obj(den)
    pair=sha256_bytes((raw_sha+'\n'+ph+'\n'+eh+'\n'+str(pc.get('schema_uid'))+'\n'+str(pc.get('schema_revision'))+'\n'+dh+'\n').encode())
    if freeze.get('pair_hash')!=pair or freeze.get('source_denominator_hash')!=dh: fail.append('FREEZE_PAIR_HASH_MISMATCH')
    if freeze.get('raw_source_sha256')!=raw_sha or freeze.get('raw_source_git_blob_sha')!=blob: fail.append('FREEZE_RAW_SOURCE_HASH_MISMATCH')
    if freeze.get('projection_content_hash')!=ph or freeze.get('reconciliation_evidence_hash')!=eh: fail.append('FREEZE_DESCENDANT_HASH_MISMATCH')
    if freeze.get('lock_state')!='SOURCE_PAIR_FROZEN' or freeze.get('status')!='FROZEN_FOR_STAGE01': fail.append('FREEZE_STATE_INVALID')
    if capstate.get('state')!='CAPTURE_CLOSED' or capstate.get('next_step')!='SOURCE_DOCUMENT_CONTENT_AUDIT': fail.append('RAW_CAPTURE_STATE_SEQUENCE_MISMATCH')
    stage_paths=['01_CLASSIFIED','02_BASE_BLUEPRINT','03_BLUEPRINT_BINDING','04_PAGE_FUNCTIONAL_CONTRACT','05_VISUAL_DESIGN']
    for sp in stage_paths:
        if (w/sp).exists(): fail.append('STAGE01_OR_LATER_ARTIFACT_PRESENT:'+sp)
    out={'status':'PASS' if not fail else 'FAIL','source_uid':suid,'source_origin':origin,'raw_source_sha256':raw_sha,'raw_source_git_blob_sha':blob,'package_part_count':len(expected['package_parts']),'relationship_count':len(expected['relationships']),'source_node_count':len(expected['source_nodes']),'binary_part_count':len([x for x in expected['package_parts'] if is_binary(x['package_part_path'])]),'projection_content_hash':ph,'reconciliation_evidence_hash':eh,'pair_hash':pair,'failures':fail}
    print(json.dumps(out,ensure_ascii=False,indent=2))
    if a.write_evidence:
        e={'schema_version':1,'artifact_type':'INDEPENDENT_DOCX_PROJECTION_VALIDATION_EVIDENCE','normative_authority':False,**out}
        e['content_hash']=hash_without(e,'content_hash')
        Path(a.write_evidence).parent.mkdir(parents=True,exist_ok=True)
        Path(a.write_evidence).write_text(yaml.safe_dump(e,allow_unicode=True,sort_keys=False,width=220),encoding='utf-8')
    raise SystemExit(0 if not fail else 1)
if __name__=='__main__': main()
