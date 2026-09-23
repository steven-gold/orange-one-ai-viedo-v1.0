#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, io, json, lzma, os, re, subprocess, sys, tarfile, zipfile
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
OLD_UID='GOV-REV-20260921-TYPOGRAPHY-COMPUTED-METRICS-HARDENING'
NEW_UID='GOV-REV-20260923-WORD-YAML-PRESTAGE01-SOURCE-FIDELITY-HARDENING'
OLD_DISPLAY='v2.2.17'
NEW_DISPLAY='v2.2.18'
OLD_REV='v2.2.17-typography-computed-metrics-hardening'
NEW_REV='v2.2.18-word-yaml-prestage01-source-fidelity-hardening'
AUTH_UID='USR-DIRECTIVE-20260923-WORD-YAML-PRESTAGE01-HARDENING-R1'
WORK_UNIT='WU-GOV-WORD-YAML-PRESTAGE01-HARDENING-001'
NEW_PACKAGE='AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.18_WORD_YAML_PRESTAGE01_SOURCE_FIDELITY_HARDENING_LOCAL_VERIFIED.zip'

SECTIONS={
'WEB-GOV-01-S090':('WEB-GOV-01','90','Immutable Structured-Document Canonical Projection / 結構化文件固定無損投影','12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md',r'''
A governed DOCX or equivalent structured human-readable design source MUST first be captured as immutable source bytes before any machine projection is produced. The captured source bytes are the Original Source Authority for source truth. In-place editing, replacement, normalization, re-save, re-export, or hidden mutation of the captured source is forbidden. Any byte change requires a new source revision/source UID and a new projection/audit cycle; a changed source MUST NOT inherit a prior reconciliation PASS.

For DOCX, the machine-readable execution input is a Canonical Source Projection. The projection is a generated non-authority mirror and MUST NOT replace, weaken, summarize, reinterpret, or supersede the Word source. Projection generation MUST preserve the complete dynamically observed DOCX package denominator: package parts, relationships, XML structural nodes, exact source order/parentage, text-bearing values, attributes, structural hashes, binary/media hashes, source-part identity, and reverse trace to the exact immutable source.

The Canonical Source Projection MUST use one registered schema UID/revision and one fixed serialization contract. Top-level fields, nested object fields, row fields, sequence ordering, null representation, encoding, line ending, anchor/alias policy, and content-hash rules are part of the contract. A producer MUST NOT add ad-hoc fields, rename fields, silently omit fields, reorder governed sequences, or create a page-specific/product-specific alternative projection schema. A field that does not apply remains present with the contract-defined null/empty value where the schema requires fixed shape.

Projection is extraction only. It MUST NOT assign page/visual responsibility, product behavior, ownership, authority satisfaction, functional classification, or downstream design conclusions. Those are Stage-01 derived interpretations. A projection row containing inferred product semantics or AI-completed source content is invalid.

Every observed OOXML XML element is representable through the generic fixed XML-node envelope. New XML qualified names therefore do not authorize schema drift. A source construct that the registered extractor cannot parse or represent MUST surface as UNSUPPORTED_SOURCE_NODE / UNSUPPORTED_SOURCE_PART and MUST block reconciliation; silent drop, best-effort omission, or summary substitution is forbidden.

Canonical ordering MUST be deterministic: package parts by canonical package path; relationships by relationship-part path then relationship ID; XML nodes by registered projection traversal order with explicit projection_order_index and parent_source_node_uid. Human-friendly layout interpretation MUST NOT be used as an implicit ordering rule. Document visual/semantic interpretation occurs later and MUST retain projection lineage.
'''),
'WEB-GOV-02-S077':('WEB-GOV-02','77','Pre-Stage Source Projection Admission and Immutable Pair Consumption / Stage-01 前投影准入與雙鎖消費','12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md',r'''
For every source to which Structured-Document Projection applies, the legal order is fixed:

RAW SOURCE CAPTURE -> RAW SOURCE IMMUTABILITY LOCK -> CANONICAL SOURCE PROJECTION -> WORD/YAML ZERO-LOSS RECONCILIATION -> SOURCE PAIR FREEZE -> STAGE-01 WORK UNIT RESOLUTION -> GOVERNANCE LOAD RECEIPT -> STAGE-01 OPERATIONS.

A Stage-01 Product Work Unit MUST NOT be activated before the applicable source pair has a PASS reconciliation receipt and a FROZEN source-pair receipt. Governance Load does not replace the pre-Stage source-fidelity gate; it follows legal Work Unit activation.

The frozen pair receipt MUST bind exact raw-source SHA-256/git-blob identity, Canonical Source Projection UID/content hash/schema UID/revision, reconciliation evidence UID/hash, complete source-denominator hash, and pair hash. After pair freeze, both the captured Word source and its Canonical YAML projection are immutable for that Stage-01 attempt. Mutation of either side invalidates the pair receipt and all descendant Stage-01 admission credit.

Stage-01 machine execution MUST consume only the exact frozen Canonical Source Projection for semantic source enumeration. Raw Word bytes remain available only for source-identity/hash/reconciliation verification and reviewer evidence; Stage-01 MUST NOT bypass the projection by reparsing Word as an alternate semantic input or by mixing a newer Word parse with an older projection.

Stage-01 derived Source Structure, Segment Mapping, Source Facts, classifications, and Blueprints MUST be written to separate derived artifacts. No Stage-01 operation may rewrite the raw source, projection, reconciliation evidence, or freeze receipt. Every derived source-structure disposition MUST retain exact projection-source-node lineage. Missing projection lineage, projection hash drift, pair-hash drift, or fallback to an unverified projection is a blocking admission defect.

If the source does not require projection, NOT_APPLICABLE is legal only with explicit source-type Authority evidence. Absence of a projection file is never implicit N/A.
'''),
'WEB-GOV-03-S072':('WEB-GOV-03','72','Source Projection Freeze, Mutation Invalidation and Re-entry Control / 來源投影鎖定、變更失效與重入控制','12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',r'''
Structured-document source control is fail-closed. Raw capture closure creates an immutable content-addressed source identity. Projection and reconciliation occur outside Product Stage execution. A legal Stage-01 Work Unit Resolution MUST verify the source-projection applicability decision and, when REQUIRED, the exact frozen-pair receipt before activation.

The source-fidelity state machine is:
RAW_CAPTURE_LOCKED -> PROJECTION_COMPLETE -> RECONCILIATION_PASS -> SOURCE_PAIR_FROZEN -> STAGE01_ELIGIBLE.
No state may be skipped, inferred from file presence, or self-declared by the projection producer.

Any change to raw-source bytes, raw-source source UID/path binding, projection schema UID/revision, projection rows, governed row ordering, projection content hash, reconciliation evidence, source denominator, or pair hash invalidates SOURCE_PAIR_FROZEN and STAGE01_ELIGIBLE. Recovery requires a fresh projection plus fresh reconciliation from the immutable/new source revision. Editing the prior locked YAML in place and recomputing only its hash is forbidden.

A Stage-01 active Work Unit MUST carry the complete applicable freeze-receipt binding set. The common execution engine MUST fail admission for missing receipt, non-PASS reconciliation, non-frozen pair state, missing physical receipt, hash mismatch, source set mismatch, or unproven N/A. Product Stage execution credit remains zero while such a defect exists.

The Canonical Projection schema is a single owner. Consumers MUST read the registered schema fields and MUST NOT maintain local alternate field-name maps, permissive alias fallback, page-specific schemas, or parser-specific optional-field interpretations. Unknown producer fields and missing required fields are schema drift and block. Sequence semantics that carry source order MUST use explicit registered indices and exact list order; YAML mapping order alone MUST NOT carry source semantics.

If a locked source pair changes after Stage-01 has started, the current Stage-01 attempt is invalid for the impacted source set, the Product Work Unit must stop, affected descendant evidence becomes REVERIFY_REQUIRED, and execution re-enters the pre-Stage projection/reconciliation boundary. No downstream patch may manufacture continuity.
'''),
'WEB-GOV-04-S087':('WEB-GOV-04','87','Word/DOCX to Canonical YAML Zero-Loss Reconciliation Audit / Word-DOCX 與 Canonical YAML 零損失對帳稽核','12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md',r'''
The source-fidelity audit MUST independently reconstruct the applicable DOCX package/source denominator from the immutable raw bytes and compare it with the Canonical Source Projection. Projection-provided summary counts are diagnostic only and MUST NOT be the audit denominator.

The audit MUST reconcile, UID/identity by UID/identity and in canonical order, at least: package-part path/content type/size/hash; relationship-part identity, relationship ID/type/target/target mode; XML-node qualified name, canonical XML locator, parent identity, projection order, document-order locator when applicable, attributes, direct/tail text, structural fragment hash, node-content hash; binary/media part hash; raw-source SHA-256/git-blob identity; projection schema UID/revision; projection content hash; and reverse trace from every projected row to the immutable raw source.

Before SOURCE_PAIR_FROZEN and Stage-01 eligibility, all of the following MUST be zero: missing package parts; duplicate package parts; package hash mismatches; missing relationships; duplicate relationships; relationship mismatches; missing source nodes; duplicate source nodes; source-node content mismatches; source-node order mismatches; untraceable projection nodes; invented projection nodes; unsupported silent drops; fixed-schema field/order mismatches; raw-source hash mismatches; projection hash mismatches; unresolved required source nodes.

The audit MUST verify that the projection contains no product-semantic interpretation fields and that every Stage-01 source-structure disposition for a projected source node is explicit, exactly-once, and traceable to the frozen projection. A projection node may be treated as structural support or non-semantic only through an explicit Stage-01 disposition/evidence record; silence is not a disposition.

Negative regression MUST include at least: Word byte mutation after lock; missing projection row; duplicate row; row-order drift; extra/unregistered field; missing required field; relationship omission; package-part hash mismatch; projection hash drift; reconciliation self-declared PASS with nonzero mismatch; freeze receipt missing; pair-hash mismatch; projection mutation after freeze; direct Stage-01 admission without a frozen pair; and semantic interpretation inserted into projection.

A PASS is valid only for the exact immutable Word/YAML pair and exact schema revision tested. It does not transfer to a re-saved Word document, regenerated YAML, different extractor revision, or modified ordering even when visible prose appears equivalent.
''')
}

PROJECTION_SCHEMA_UID='SCHEMA-DOCX-CANONICAL-SOURCE-PROJECTION-001'
PROJECTION_SCHEMA_REV=1

def run(*args,check=True,env=None):
    cp=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,env=env)
    if check and cp.returncode:
        print(cp.stdout)
        print(cp.stderr,file=sys.stderr)
        raise SystemExit(cp.returncode)
    return cp

def load(p):
    return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}

def dump(p,d):
    Path(p).write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=200),encoding='utf-8')

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def hobj(d):
    x=copy.deepcopy(d)
    x.pop('content_hash',None)
    return hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True,width=200).encode()).hexdigest()

def unique_extend(lst,items):
    for x in items:
        if x not in lst:
            lst.append(x)

def section_binding(uid,doc,path,heading):
    return hashlib.sha256(f'{uid}\n{doc}\n{path}\n{heading}\n'.encode()).hexdigest()

def replace_const(path,name,value):
    p=Path(path)
    s=p.read_text(encoding='utf-8')
    pat=re.compile(f"(?m)^{re.escape(name)}\\s*=\\s*'[^']*'$")
    ns,n=pat.subn(f"{name} = '{value}'",s,1)
    if n!=1:
        raise RuntimeError(f'constant {name} replacement count={n} in {path}')
    p.write_text(ns,encoding='utf-8')

def append_section(uid,doc,num,title,rel,body):
    p=SOURCE/rel
    s=p.read_text(encoding='utf-8')
    if f'<!-- SECTION_UID: {uid} -->' in s:
        return
    p.write_text(s.rstrip()+f'\n\n<!-- SECTION_UID: {uid} -->\n## {num}. {title}\n\n{body.strip()}\n',encoding='utf-8')

def update_section_registry():
    p=SOURCE/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'
    d=load(p)
    for uid,(doc,num,title,rel,_) in SECTIONS.items():
        entry=next(x for x in d.get('documents',[]) if x.get('document_id')==doc)
        if any(x.get('section_uid')==uid for x in entry.get('sections',[])):
            continue
        heading=f'## {num}. {title}'
        entry.setdefault('sections',[]).append({
            'section_uid':uid,'level':2,'canonical_number':num,'title':title,
            'heading':heading,'path':rel,
            'binding_sha256':section_binding(uid,doc,rel,heading)
        })
    d['governance_revision']=NEW_REV
    dump(p,d)

def projection_contract():
    return {
      'applicability': {
        'required_source_formats':['DOCX'],
        'source_format_detection':'RAW_SOURCE_REFERENCE_MANIFEST.source_format_PLUS_REGISTERED_EXTENSION_CROSSCHECK',
        'not_applicable_requires_authority_evidence':True,
        'implicit_not_applicable':'BLOCK'
      },
      'state_machine':[
        'RAW_CAPTURE_LOCKED','PROJECTION_COMPLETE','RECONCILIATION_PASS','SOURCE_PAIR_FROZEN','STAGE01_ELIGIBLE'
      ],
      'raw_source_lock':{
        'receipt_path_template':'00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{source_uid}/RAW_SOURCE_IMMUTABILITY_RECEIPT.yaml',
        'required_before_projection':True,
        'raw_source_bytes_writable_after_lock':False,
        'in_place_source_revision_change':'BLOCK',
        'byte_change_disposition':'NEW_SOURCE_REVISION_NEW_PROJECTION_NEW_RECONCILIATION',
        'required_field_order':[
          'schema_version','artifact_uid','artifact_type','source_uid','source_path',
          'source_git_blob_sha','source_sha256','lock_state','writable',
          'mutation_policy','content_hash'
        ],
        'terminal_lock_state':'RAW_CAPTURE_LOCKED'
      },
      'projection':{
        'artifact_path_template':'00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{source_uid}/CANONICAL_SOURCE_PROJECTION.yaml',
        'schema_uid':PROJECTION_SCHEMA_UID,
        'schema_revision':PROJECTION_SCHEMA_REV,
        'role':'MACHINE_READABLE_NON_AUTHORITY_MIRROR',
        'normative_authority':False,
        'semantic_interpretation_during_projection':'BLOCK',
        'manual_summary_or_rewrite':'BLOCK',
        'unknown_or_extra_field':'BLOCK',
        'missing_required_field':'BLOCK',
        'mapping_key_order_drift':'BLOCK',
        'sequence_order_drift':'BLOCK',
        'canonical_top_level_field_order':[
          'schema_version','artifact_uid','artifact_type','projection_schema_uid',
          'projection_schema_revision','projection_role','normative_authority',
          'source_identity','extraction_identity','serialization_contract',
          'denominator_rows','package_parts','relationships','source_nodes',
          'projection_content_hash','status'
        ],
        'source_identity_field_order':[
          'source_uid','source_path','source_format','source_git_blob_sha',
          'source_sha256','raw_source_lock_receipt_uid'
        ],
        'extraction_identity_field_order':[
          'extractor_uid','extractor_version','extraction_run_uid','extraction_evidence_ref'
        ],
        'serialization_contract_field_order':[
          'yaml_profile','encoding','line_ending','key_order_contract_uid',
          'anchors_aliases','implicit_custom_tags'
        ],
        'denominator_row_field_order':[
          'denominator_uid','denominator_type','required_count','projected_count'
        ],
        'required_denominator_order':['PACKAGE_PART','RELATIONSHIP','XML_NODE'],
        'package_part_row_field_order':[
          'package_part_path','content_type','size_bytes','part_sha256'
        ],
        'relationship_row_field_order':[
          'relationship_part_path','relationship_id','relationship_type','target','target_mode'
        ],
        'source_node_row_field_order':[
          'source_node_uid','source_node_kind','projection_order_index',
          'document_order_index','package_part_path','xml_qname','xml_path',
          'parent_source_node_uid','attributes_json','direct_text','tail_text',
          'element_xml_sha256','node_content_sha256','projection_status','unsupported_reason'
        ],
        'source_node_kind_contract':'REGISTERED_GENERIC_OOXML_ELEMENT_ENVELOPE_WITH_SPECIALIZED_KIND_HINTS',
        'unregistered_xml_qname_schema_expansion_required':False,
        'generic_xml_element_envelope_handles_new_qname':True,
        'unsupported_parse_or_representation':'UNSUPPORTED_SOURCE_NODE_BLOCK',
        'canonical_sequence_order':{
          'package_parts':'PACKAGE_PATH_ASC',
          'relationships':'RELATIONSHIP_PART_PATH_ASC_THEN_RELATIONSHIP_ID_ASC',
          'source_nodes':'PROJECTION_TRAVERSAL_ORDER_ASC'
        },
        'canonical_serialization':{
          'yaml_profile':'YAML_1_2_SAFE_SUBSET',
          'encoding':'UTF-8',
          'line_ending':'LF',
          'anchors_aliases':'FORBIDDEN',
          'implicit_custom_tags':'FORBIDDEN',
          'null_literal':'null'
        }
      },
      'reconciliation':{
        'evidence_path_template':'00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{source_uid}/SOURCE_PROJECTION_RECONCILIATION_EVIDENCE.yaml',
        'validator_uid':'VAL-GOV-026',
        'denominator_source':'INDEPENDENT_RAW_DOCX_RECALCULATION',
        'projection_summary_as_denominator':'FORBIDDEN',
        'required_field_order':[
          'schema_version','artifact_uid','artifact_type','validator_uid','source_uid',
          'raw_source_sha256','projection_uid','projection_content_hash',
          'projection_schema_uid','projection_schema_revision',
          'source_inventory_hashes','zero_loss_counts','reverse_trace',
          'unsupported_count','result','evidence_content_hash'
        ],
        'source_inventory_hashes_field_order':[
          'package_parts_hash','relationships_hash','source_nodes_hash'
        ],
        'zero_loss_count_field_order':[
          'missing_package_parts','duplicate_package_parts','package_hash_mismatch',
          'missing_relationships','duplicate_relationships','relationship_mismatch',
          'missing_source_nodes','duplicate_source_nodes','source_node_content_mismatch',
          'source_node_order_mismatch','untraceable_projection_nodes',
          'invented_projection_nodes','unsupported_silent_drop',
          'schema_field_order_mismatch','raw_source_hash_mismatch',
          'projection_hash_mismatch','unresolved_required_source_nodes'
        ],
        'all_zero_required_for_pass':True,
        'reverse_trace_required':True,
        'unsupported_count_required_for_pass':0,
        'pass_state':'PASS'
      },
      'pair_freeze':{
        'receipt_path_template':'00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{source_uid}/SOURCE_PROJECTION_FREEZE_RECEIPT.yaml',
        'required_field_order':[
          'schema_version','artifact_uid','artifact_type','source_uid','raw_source_sha256',
          'raw_source_git_blob_sha','projection_uid','projection_content_hash',
          'projection_schema_uid','projection_schema_revision',
          'reconciliation_evidence_uid','reconciliation_evidence_hash',
          'source_denominator_hash','pair_hash','lock_state','raw_source_writable',
          'projection_writable','mutation_disposition','next_step','status'
        ],
        'lock_state':'SOURCE_PAIR_FROZEN',
        'raw_source_writable':False,
        'projection_writable':False,
        'next_step':'STAGE01_WORK_UNIT_RESOLUTION',
        'status':'FROZEN_FOR_STAGE01',
        'mutation_disposition':'INVALIDATE_PAIR_REQUIRE_NEW_RECONCILIATION'
      },
      'stage01_consumption':{
        'raw_word_semantic_reparse':'BLOCK',
        'raw_word_access':'HASH_RECONCILIATION_REVIEW_EVIDENCE_ONLY',
        'semantic_input':'EXACT_FROZEN_CANONICAL_SOURCE_PROJECTION_ONLY',
        'projection_mutation_during_stage01':'BLOCK',
        'required_work_unit_binding_fields':[
          'source_uid','freeze_receipt_ref','pair_hash','raw_source_sha256',
          'projection_uid','projection_content_hash'
        ],
        'source_structure_projection_node_disposition_field_order':[
          'projection_source_node_uid','disposition','source_structure_node_uids','evidence_ref'
        ],
        'allowed_projection_node_dispositions':[
          'SEMANTIC_SOURCE_NODE','STRUCTURAL_SUPPORT','NON_SEMANTIC_WITH_EVIDENCE'
        ],
        'every_projection_source_node_exactly_once_disposition_required':True,
        'silent_projection_node_omission':'BLOCK',
        'derived_node_without_projection_lineage':'BLOCK'
      }
    }

def mutate_stage1_guard():
    p=SOURCE/'09_TESTS/governance/governance_stage1_pipeline_guard.py'
    s=p.read_text(encoding='utf-8')
    s=s.replace(
      "import hashlib, json, re, sys, yaml",
      "import hashlib, json, re, sys, zipfile, xml.etree.ElementTree as ET, yaml"
    )
    marker="def validate(package_root:Path,workspace:Path):"
    if 'def validate_pre_stage_source_projection' not in s:
        helper=r'''
PROJECTION_CONTRACT_REL='10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml'

def _projection_contract(package_root:Path):
    reg=load_yaml(package_root/PROJECTION_CONTRACT_REL)
    return reg.get('structured_document_source_projection_contract') or {}

def _exact_keys(obj,expected,label,failures):
    if not isinstance(obj,dict):
        failures.append(label+'_not_mapping'); return
    actual=list(obj.keys())
    if actual!=list(expected):
        failures.append(label+'_field_order_or_schema_mismatch:expected='+str(list(expected))+':actual='+str(actual))

def _hash_without(doc,key):
    d=copy_dict=dict(doc)
    d.pop(key,None)
    return stable_hash_obj(d)

def _local_name(qname:str)->str:
    return qname.rsplit('}',1)[-1] if '}' in qname else qname

def _content_types(z:zipfile.ZipFile):
    defaults={}; overrides={}
    try:
        root=ET.fromstring(z.read('[Content_Types].xml'))
        for el in list(root):
            ln=_local_name(el.tag)
            if ln=='Default':
                defaults[str(el.attrib.get('Extension') or '').lower()]=str(el.attrib.get('ContentType') or '')
            elif ln=='Override':
                overrides[str(el.attrib.get('PartName') or '').lstrip('/')]=str(el.attrib.get('ContentType') or '')
    except Exception:
        pass
    return defaults,overrides

def derive_docx_inventory(raw_path:Path):
    if not zipfile.is_zipfile(raw_path):
        raise ValueError('DOCX_NOT_ZIP_PACKAGE')
    package_parts=[]; relationships=[]; source_nodes=[]
    with zipfile.ZipFile(raw_path,'r') as z:
        names=sorted(n for n in z.namelist() if not n.endswith('/'))
        defaults,overrides=_content_types(z)
        for name in names:
            b=z.read(name); ext=name.rsplit('.',1)[-1].lower() if '.' in name else ''
            package_parts.append({
              'package_part_path':name,
              'content_type':overrides.get(name,defaults.get(ext,'')),
              'size_bytes':len(b),
              'part_sha256':sha256_bytes(b)
            })
        for name in sorted(n for n in names if n.endswith('.rels')):
            try:
                root=ET.fromstring(z.read(name))
            except Exception as exc:
                raise ValueError('DOCX_RELATIONSHIP_PARSE_FAILED:'+name+':'+str(exc))
            for el in list(root):
                if _local_name(el.tag)!='Relationship':
                    continue
                relationships.append({
                  'relationship_part_path':name,
                  'relationship_id':str(el.attrib.get('Id') or ''),
                  'relationship_type':str(el.attrib.get('Type') or ''),
                  'target':str(el.attrib.get('Target') or ''),
                  'target_mode':str(el.attrib.get('TargetMode') or 'Internal')
                })
        relationships.sort(key=lambda x:(x['relationship_part_path'],x['relationship_id']))
        global_index=0; doc_index=0
        kind_map={'p':'PARAGRAPH','tbl':'TABLE','tr':'TABLE_ROW','tc':'TABLE_CELL','r':'TEXT_RUN','t':'TEXT','drawing':'DRAWING','hyperlink':'HYPERLINK','sectPr':'SECTION_PROPERTIES','br':'BREAK','tab':'TAB'}
        for name in sorted(n for n in names if n.endswith('.xml') and n!='[Content_Types].xml'):
            try:
                root=ET.fromstring(z.read(name))
            except Exception as exc:
                raise ValueError('DOCX_XML_PARSE_FAILED:'+name+':'+str(exc))
            def walk(el,path,parent_uid):
                nonlocal global_index,doc_index
                global_index+=1
                q=str(el.tag); local=_local_name(q)
                uid='SN-'+sha256_bytes((name+'\0'+path+'\0'+q).encode())[:24].upper()
                doi=None
                if name=='word/document.xml':
                    doc_index+=1; doi=doc_index
                attrs=json.dumps({str(k):str(v) for k,v in sorted(el.attrib.items())},ensure_ascii=False,separators=(',',':'))
                base={
                  'source_node_uid':uid,
                  'source_node_kind':kind_map.get(local,'OOXML_ELEMENT'),
                  'projection_order_index':global_index,
                  'document_order_index':doi,
                  'package_part_path':name,
                  'xml_qname':q,
                  'xml_path':path,
                  'parent_source_node_uid':parent_uid,
                  'attributes_json':attrs,
                  'direct_text':el.text or '',
                  'tail_text':el.tail or '',
                  'element_xml_sha256':sha256_bytes(ET.tostring(el,encoding='utf-8'))
                }
                node_hash=stable_hash_obj(base)
                row=dict(base)
                row['node_content_sha256']=node_hash
                row['projection_status']='PROJECTED'
                row['unsupported_reason']=None
                source_nodes.append(row)
                for idx,ch in enumerate(list(el)):
                    walk(ch,path+'/'+str(idx),uid)
            walk(root,'/0',None)
    return {
      'package_parts':package_parts,
      'relationships':relationships,
      'source_nodes':source_nodes,
      'package_parts_hash':stable_hash_obj(package_parts),
      'relationships_hash':stable_hash_obj(relationships),
      'source_nodes_hash':stable_hash_obj(source_nodes)
    }

def _projection_required_records(rawcap:dict):
    out=[]
    for rec in rawcap.get('records') or []:
        fmt=str(rec.get('source_format') or '').upper()
        target=str(rec.get('target_path') or '')
        if fmt=='DOCX' or target.lower().endswith('.docx'):
            out.append(rec)
    return out

def _resolve_template(template:str,source_uid:str)->str:
    return str(template).replace('{source_uid}',str(source_uid))

def validate_pre_stage_source_projection(package_root:Path,workspace:Path,rawcap:dict,capstate:dict):
    failures=[]; contract=_projection_contract(package_root)
    recs=_projection_required_records(rawcap)
    result={'required':bool(recs),'failures':failures,'bindings':{}}
    if not recs:
        return result
    if not contract:
        failures.append('structured_document_projection_contract_missing'); return result
    if capstate.get('next_step')!='CANONICAL_SOURCE_PROJECTION':
        failures.append('raw_source_capture_next_step_not_canonical_source_projection')
    raw_lock=contract.get('raw_source_lock') or {}
    projc=contract.get('projection') or {}
    reconc=contract.get('reconciliation') or {}
    freezec=contract.get('pair_freeze') or {}
    for rec in recs:
        suid=str(rec.get('source_uid') or '')
        if not suid:
            failures.append('projection_source_uid_missing'); continue
        if str(rec.get('source_format') or '').upper()!='DOCX':
            failures.append('docx_source_format_explicit_identity_missing:'+suid)
        if rec.get('projection_required') is not True:
            failures.append('docx_projection_required_flag_missing:'+suid)
        target=str(rec.get('target_path') or '')
        raw=workspace/target
        if not raw.is_file():
            failures.append('projection_raw_source_missing:'+suid); continue
        raw_sha=file_sha(raw); blob=git_blob_sha(raw)
        lock_path=workspace/_resolve_template(raw_lock.get('receipt_path_template',''),suid)
        proj_path=workspace/_resolve_template(projc.get('artifact_path_template',''),suid)
        rec_path=workspace/_resolve_template(reconc.get('evidence_path_template',''),suid)
        freeze_path=workspace/_resolve_template(freezec.get('receipt_path_template',''),suid)
        for p,label in [(lock_path,'raw_source_immutability_receipt'),(proj_path,'canonical_source_projection'),(rec_path,'source_projection_reconciliation_evidence'),(freeze_path,'source_projection_freeze_receipt')]:
            if not p.is_file(): failures.append(label+'_missing:'+suid)
        if not all(p.is_file() for p in (lock_path,proj_path,rec_path,freeze_path)):
            continue
        lock=load_yaml(lock_path); projection=load_yaml(proj_path); evidence=load_yaml(rec_path); freeze=load_yaml(freeze_path)
        _exact_keys(lock,raw_lock.get('required_field_order') or [],'raw_source_lock:'+suid,failures)
        if lock.get('artifact_type')!='RAW_SOURCE_IMMUTABILITY_RECEIPT' or lock.get('source_uid')!=suid: failures.append('raw_source_lock_identity_invalid:'+suid)
        if lock.get('source_sha256')!=raw_sha or lock.get('source_git_blob_sha')!=blob: failures.append('raw_source_lock_hash_mismatch:'+suid)
        if lock.get('lock_state')!=raw_lock.get('terminal_lock_state') or lock.get('writable') is not False: failures.append('raw_source_not_immutable:'+suid)
        if lock.get('content_hash')!=_hash_without(lock,'content_hash'): failures.append('raw_source_lock_content_hash_mismatch:'+suid)

        _exact_keys(projection,projc.get('canonical_top_level_field_order') or [],'projection:'+suid,failures)
        if projection.get('artifact_type')!='CANONICAL_SOURCE_PROJECTION' or projection.get('projection_schema_uid')!=projc.get('schema_uid') or projection.get('projection_schema_revision')!=projc.get('schema_revision'): failures.append('projection_schema_identity_mismatch:'+suid)
        if projection.get('projection_role')!=projc.get('role') or projection.get('normative_authority') is not False: failures.append('projection_authority_role_invalid:'+suid)
        _exact_keys(projection.get('source_identity'),projc.get('source_identity_field_order') or [],'projection_source_identity:'+suid,failures)
        _exact_keys(projection.get('extraction_identity'),projc.get('extraction_identity_field_order') or [],'projection_extraction_identity:'+suid,failures)
        _exact_keys(projection.get('serialization_contract'),projc.get('serialization_contract_field_order') or [],'projection_serialization:'+suid,failures)
        sid=projection.get('source_identity') or {}
        if sid.get('source_uid')!=suid or sid.get('source_sha256')!=raw_sha or sid.get('source_git_blob_sha')!=blob or str(sid.get('source_format') or '').upper()!='DOCX': failures.append('projection_source_identity_hash_mismatch:'+suid)
        if sid.get('raw_source_lock_receipt_uid')!=lock.get('artifact_uid'): failures.append('projection_raw_lock_uid_mismatch:'+suid)
        serial=projection.get('serialization_contract') or {}
        canon=projc.get('canonical_serialization') or {}
        for k in ('yaml_profile','encoding','line_ending','anchors_aliases','implicit_custom_tags'):
            if serial.get(k)!=canon.get(k): failures.append('projection_serialization_contract_mismatch:'+suid+':'+k)

        for row in projection.get('denominator_rows') or []: _exact_keys(row,projc.get('denominator_row_field_order') or [],'projection_denominator_row:'+suid,failures)
        for row in projection.get('package_parts') or []: _exact_keys(row,projc.get('package_part_row_field_order') or [],'projection_package_part:'+suid,failures)
        for row in projection.get('relationships') or []: _exact_keys(row,projc.get('relationship_row_field_order') or [],'projection_relationship:'+suid,failures)
        for row in projection.get('source_nodes') or []:
            _exact_keys(row,projc.get('source_node_row_field_order') or [],'projection_source_node:'+suid,failures)
            forbidden={'responsibility','responsibility_uid','planning_domain','product_behavior','authority_satisfied','classification','canonical_owner_uid'}
            if forbidden & set(row or {}): failures.append('projection_semantic_interpretation_field_present:'+suid)
            if isinstance(row,dict):
                rb=dict(row); got=rb.pop('node_content_sha256',None); rb.pop('projection_status',None); rb.pop('unsupported_reason',None)
                if got!=stable_hash_obj(rb): failures.append('projection_source_node_content_hash_mismatch:'+str(row.get('source_node_uid')))
                if row.get('projection_status')!='PROJECTED' or row.get('unsupported_reason') not in (None,''): failures.append('projection_source_node_not_cleanly_projected:'+str(row.get('source_node_uid')))

        try:
            expected=derive_docx_inventory(raw)
        except Exception as exc:
            failures.append('independent_docx_inventory_failed:'+suid+':'+str(exc)); continue
        actual_parts=projection.get('package_parts') or []
        actual_rels=projection.get('relationships') or []
        actual_nodes=projection.get('source_nodes') or []
        if actual_parts!=expected['package_parts']: failures.append('projection_package_part_inventory_mismatch:'+suid)
        if actual_rels!=expected['relationships']: failures.append('projection_relationship_inventory_mismatch:'+suid)
        if actual_nodes!=expected['source_nodes']: failures.append('projection_source_node_inventory_or_order_mismatch:'+suid)
        den=projection.get('denominator_rows') or []
        expected_den=[
          {'denominator_uid':'DEN-PACKAGE-PART','denominator_type':'PACKAGE_PART','required_count':len(expected['package_parts']),'projected_count':len(actual_parts)},
          {'denominator_uid':'DEN-RELATIONSHIP','denominator_type':'RELATIONSHIP','required_count':len(expected['relationships']),'projected_count':len(actual_rels)},
          {'denominator_uid':'DEN-XML-NODE','denominator_type':'XML_NODE','required_count':len(expected['source_nodes']),'projected_count':len(actual_nodes)}
        ]
        if den!=expected_den: failures.append('projection_denominator_rows_mismatch:'+suid)
        ph=_hash_without(projection,'projection_content_hash')
        if projection.get('projection_content_hash')!=ph: failures.append('projection_content_hash_mismatch:'+suid)
        if projection.get('status')!='PROJECTION_COMPLETE': failures.append('projection_status_not_complete:'+suid)

        _exact_keys(evidence,reconc.get('required_field_order') or [],'projection_reconciliation:'+suid,failures)
        _exact_keys(evidence.get('source_inventory_hashes'),reconc.get('source_inventory_hashes_field_order') or [],'projection_reconciliation_inventory_hashes:'+suid,failures)
        _exact_keys(evidence.get('zero_loss_counts'),reconc.get('zero_loss_count_field_order') or [],'projection_reconciliation_zero_loss_counts:'+suid,failures)
        if evidence.get('validator_uid')!=reconc.get('validator_uid') or evidence.get('source_uid')!=suid: failures.append('projection_reconciliation_identity_invalid:'+suid)
        if evidence.get('raw_source_sha256')!=raw_sha or evidence.get('projection_uid')!=projection.get('artifact_uid') or evidence.get('projection_content_hash')!=ph: failures.append('projection_reconciliation_hash_binding_mismatch:'+suid)
        if evidence.get('projection_schema_uid')!=projc.get('schema_uid') or evidence.get('projection_schema_revision')!=projc.get('schema_revision'): failures.append('projection_reconciliation_schema_binding_mismatch:'+suid)
        ih=evidence.get('source_inventory_hashes') or {}
        if ih!={'package_parts_hash':expected['package_parts_hash'],'relationships_hash':expected['relationships_hash'],'source_nodes_hash':expected['source_nodes_hash']}: failures.append('projection_reconciliation_inventory_hash_mismatch:'+suid)
        zero=evidence.get('zero_loss_counts') or {}
        if any(v!=0 for v in zero.values()): failures.append('projection_reconciliation_nonzero_mismatch:'+suid)
        if evidence.get('reverse_trace')!='COMPLETE' or evidence.get('unsupported_count')!=0 or evidence.get('result')!='PASS': failures.append('projection_reconciliation_not_pass:'+suid)
        eh=_hash_without(evidence,'evidence_content_hash')
        if evidence.get('evidence_content_hash')!=eh: failures.append('projection_reconciliation_evidence_hash_mismatch:'+suid)

        _exact_keys(freeze,freezec.get('required_field_order') or [],'projection_freeze:'+suid,failures)
        denom_hash=stable_hash_obj(expected_den)
        pair_hash=sha256_bytes((raw_sha+'\n'+ph+'\n'+eh+'\n'+str(projc.get('schema_uid'))+'\n'+str(projc.get('schema_revision'))+'\n'+denom_hash+'\n').encode())
        expected_freeze={
          'schema_version':1,'artifact_uid':freeze.get('artifact_uid'),'artifact_type':'SOURCE_PROJECTION_FREEZE_RECEIPT',
          'source_uid':suid,'raw_source_sha256':raw_sha,'raw_source_git_blob_sha':blob,
          'projection_uid':projection.get('artifact_uid'),'projection_content_hash':ph,
          'projection_schema_uid':projc.get('schema_uid'),'projection_schema_revision':projc.get('schema_revision'),
          'reconciliation_evidence_uid':evidence.get('artifact_uid'),'reconciliation_evidence_hash':eh,
          'source_denominator_hash':denom_hash,'pair_hash':pair_hash,'lock_state':freezec.get('lock_state'),
          'raw_source_writable':False,'projection_writable':False,'mutation_disposition':freezec.get('mutation_disposition'),
          'next_step':freezec.get('next_step'),'status':freezec.get('status')
        }
        for k,v in expected_freeze.items():
            if k!='artifact_uid' and freeze.get(k)!=v: failures.append('projection_freeze_binding_mismatch:'+suid+':'+k)
        result['bindings'][suid]={
          'projection_uid':projection.get('artifact_uid'),'projection_content_hash':ph,
          'pair_hash':pair_hash,'raw_source_sha256':raw_sha,
          'source_node_uids':[x.get('source_node_uid') for x in expected['source_nodes']],
          'freeze_receipt_ref':freeze_path.relative_to(workspace).as_posix()
        }
    return result

def validate_projection_stage1_consumption(struct:dict,projection_result:dict,workspace:Path):
    failures=[]
    if not projection_result.get('required'): return failures
    sources={x.get('source_uid'):x for x in (struct.get('sources') or []) if isinstance(x,dict) and x.get('source_uid')}
    contract=projection_result
    for suid,b in (projection_result.get('bindings') or {}).items():
        src=sources.get(suid)
        if not src:
            failures.append('projection_source_missing_from_source_structure:'+suid); continue
        if src.get('source_projection_uid')!=b.get('projection_uid') or src.get('source_projection_content_hash')!=b.get('projection_content_hash') or src.get('source_projection_pair_hash')!=b.get('pair_hash'):
            failures.append('source_structure_projection_binding_mismatch:'+suid)
        rows=src.get('projection_node_dispositions')
        if not isinstance(rows,list):
            failures.append('projection_node_dispositions_missing:'+suid); continue
        expected=set(b.get('source_node_uids') or []); seen=set()
        for row in rows:
            if not isinstance(row,dict):
                failures.append('projection_node_disposition_not_mapping:'+suid); continue
            keys=['projection_source_node_uid','disposition','source_structure_node_uids','evidence_ref']
            if list(row.keys())!=keys: failures.append('projection_node_disposition_schema_or_order_mismatch:'+suid)
            uid=row.get('projection_source_node_uid')
            if uid in seen: failures.append('projection_node_disposition_duplicate:'+str(uid))
            if uid: seen.add(uid)
            if row.get('disposition') not in {'SEMANTIC_SOURCE_NODE','STRUCTURAL_SUPPORT','NON_SEMANTIC_WITH_EVIDENCE'}: failures.append('projection_node_disposition_invalid:'+str(uid))
            if row.get('disposition')=='NON_SEMANTIC_WITH_EVIDENCE':
                ev=row.get('evidence_ref')
                if not ev or not (workspace/str(ev)).is_file(): failures.append('projection_node_nonsemantic_evidence_missing:'+str(uid))
            elif not (row.get('source_structure_node_uids') or []):
                failures.append('projection_node_structure_lineage_missing:'+str(uid))
        if seen!=expected:
            failures.append('projection_node_disposition_denominator_mismatch:'+suid+':missing='+str(sorted(expected-seen))+':extra='+str(sorted(seen-expected)))
    return failures

'''
        s=s.replace(marker,helper+marker)
    old="""    if capstate:
        if capstate.get('state')!='CAPTURE_CLOSED': failures.append('raw_source_capture_not_closed')
        if capstate.get('next_step')!='SOURCE_STRUCTURE_ENUMERATION': failures.append('raw_source_capture_next_step_not_exact_source_structure_enumeration')
        if capstate.get('recapture_allowed') is not False: failures.append('closed_raw_source_capture_still_writable')
"""
    new="""    if capstate:
        if capstate.get('state')!='CAPTURE_CLOSED': failures.append('raw_source_capture_not_closed')
        _pr=_projection_required_records(rawcap)
        _expected_next='CANONICAL_SOURCE_PROJECTION' if _pr else 'SOURCE_STRUCTURE_ENUMERATION'
        if capstate.get('next_step')!=_expected_next: failures.append('raw_source_capture_next_step_mismatch:'+str(capstate.get('next_step'))+':expected='+_expected_next)
        if capstate.get('recapture_allowed') is not False: failures.append('closed_raw_source_capture_still_writable')
    projection_result=validate_pre_stage_source_projection(package_root,workspace,rawcap,capstate)
    failures.extend(projection_result.get('failures') or [])
    failures.extend(validate_projection_stage1_consumption(struct,projection_result,workspace))
"""
    if old in s:
        s=s.replace(old,new,1)
    if "source_projection_pair_hash" not in s.split("raw_sources={",1)[-1]:
        marker2="    raw_sources={s.get('source_uid'):s for s in (sm.get('raw_sources') or []) if s.get('source_uid')}\n"
        add="""    raw_sources={s.get('source_uid'):s for s in (sm.get('raw_sources') or []) if s.get('source_uid')}
    for _suid,_bind in (projection_result.get('bindings') or {}).items():
        _rs=raw_sources.get(_suid)
        if not _rs:
            failures.append('projection_source_missing_from_segment_map:'+_suid)
        else:
            if _rs.get('source_projection_uid')!=_bind.get('projection_uid') or _rs.get('source_projection_content_hash')!=_bind.get('projection_content_hash') or _rs.get('source_projection_pair_hash')!=_bind.get('pair_hash'):
                failures.append('segment_map_projection_binding_mismatch:'+_suid)
"""
        if marker2 not in s:
            raise RuntimeError('raw_sources marker missing')
        s=s.replace(marker2,add,1)
    p.write_text(s,encoding='utf-8')

def mutate_stage1_tests():
    p=SOURCE/'09_TESTS/governance/test_stage1_source_to_blueprint_minimal_control.py'
    s=p.read_text(encoding='utf-8')
    s=s.replace("import copy, importlib.util, json, tempfile, yaml","import copy, importlib.util, json, tempfile, zipfile, yaml")
    marker="out={'suite':'Stage-1 Source Enumeration → Classification → Dual Base Blueprint minimal-control'"
    if 'projection_fixed_schema_positive' not in s:
        block=r"""
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

"""
        if marker not in s:
            raise RuntimeError('stage1 test final marker missing')
        s=s.replace(marker,block+marker,1)
    p.write_text(s,encoding='utf-8')

def mutate_stage_execution_engine():
    p=ROOT/'governance/ci/stage_execution_engine.py'
    s=p.read_text(encoding='utf-8')
    if "PRE_STAGE_SOURCE_PROJECTION_GATE_INVALID" not in s:
        marker="        if st.get('pre_execution_gate')!='GOVERNANCE_LOAD_RECEIPT_PASS': fail(f'STAGE_PREEXECUTION_GATE_DRIFT:{uid}')\n"
        add=marker+"""        if uid=='STAGE-01':
            pg=st.get('pre_stage_source_projection_admission_gate') or {}
            if pg.get('required') is not True or pg.get('evaluation_boundary')!='BEFORE_PRODUCT_STAGE01_WORK_UNIT_ACTIVATION' or pg.get('freeze_state')!='SOURCE_PAIR_FROZEN' or pg.get('validator_uid')!='VAL-GOV-026':
                fail('PRE_STAGE_SOURCE_PROJECTION_GATE_INVALID')
"""
        if marker not in s: raise RuntimeError('stage engine definition marker missing')
        s=s.replace(marker,add,1)
    if "def validate_stage01_source_projection_admission" not in s:
        marker="def validate_work_unit_bindings(stage_uid,work,stages,adapters):\n"
        helper=r'''def validate_stage01_source_projection_admission(work,stage):
    gate=stage.get('pre_stage_source_projection_admission_gate') or {}
    adm=work.get('source_projection_admission')
    if not isinstance(adm,dict): fail('STAGE01_SOURCE_PROJECTION_ADMISSION_BINDING_MISSING')
    applicability=adm.get('applicability')
    if applicability=='NOT_APPLICABLE_WITH_AUTHORITY':
        if not adm.get('authority_evidence_ref'): fail('STAGE01_SOURCE_PROJECTION_NA_AUTHORITY_MISSING')
        return True
    if applicability!='REQUIRED': fail('STAGE01_SOURCE_PROJECTION_APPLICABILITY_UNRESOLVED')
    bindings=adm.get('bindings')
    if not isinstance(bindings,list) or not bindings: fail('STAGE01_SOURCE_PROJECTION_BINDING_SET_MISSING')
    seen=set()
    required=['source_uid','freeze_receipt_ref','pair_hash','raw_source_sha256','projection_uid','projection_content_hash']
    for b in bindings:
        if not isinstance(b,dict) or list(b.keys())!=required: fail('STAGE01_SOURCE_PROJECTION_BINDING_SCHEMA_DRIFT')
        suid=str(b.get('source_uid') or '')
        if not suid or suid in seen: fail('STAGE01_SOURCE_PROJECTION_SOURCE_UID_INVALID:'+suid)
        seen.add(suid)
        rel=str(b.get('freeze_receipt_ref') or '')
        if not rel or rel.startswith('/') or '..' in Path(rel).parts: fail('STAGE01_SOURCE_PROJECTION_RECEIPT_REF_INVALID:'+suid)
        fp=ROOT/rel
        if not fp.is_file(): fail('STAGE01_SOURCE_PROJECTION_FREEZE_RECEIPT_MISSING:'+suid)
        fr=y(fp)
        if fr.get('artifact_type')!='SOURCE_PROJECTION_FREEZE_RECEIPT' or fr.get('source_uid')!=suid or fr.get('status')!='FROZEN_FOR_STAGE01' or fr.get('lock_state')!='SOURCE_PAIR_FROZEN' or fr.get('raw_source_writable') is not False or fr.get('projection_writable') is not False:
            fail('STAGE01_SOURCE_PROJECTION_FREEZE_RECEIPT_INVALID:'+suid)
        for k in ('pair_hash','raw_source_sha256','projection_uid','projection_content_hash'):
            if fr.get(k)!=b.get(k): fail('STAGE01_SOURCE_PROJECTION_BINDING_HASH_DRIFT:'+suid+':'+k)
    return True

'''
        if marker not in s: raise RuntimeError('stage engine work binding marker missing')
        s=s.replace(marker,helper+marker,1)
    callmarker="    if work.get('stage_uid')!=stage_uid: fail('ACTIVE_WORK_UNIT_STAGE_MISMATCH')\n"
    if "validate_stage01_source_projection_admission(work,stages[stage_uid])" not in s:
        add=callmarker+"    if stage_uid=='STAGE-01': validate_stage01_source_projection_admission(work,stages[stage_uid])\n"
        if callmarker not in s: raise RuntimeError('stage engine call marker missing')
        s=s.replace(callmarker,add,1)
    p.write_text(s,encoding='utf-8')

def mutate_policy():
    for uid,args in SECTIONS.items():
        append_section(uid,*args)
    update_section_registry()
    section_uids=list(SECTIONS.keys())

    sp=SOURCE/'10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml'
    st1=load(sp)
    st1['governance_revision']=NEW_REV
    unique_extend(st1.setdefault('normative_section_uids',[]),section_uids)
    st1['structured_document_source_projection_contract']=projection_contract()
    rsc=st1.setdefault('raw_source_capture_contract',{})
    rsc['raw_source_immutable_on_capture']=True
    rsc['content_addressed_identity_required']=True
    rsc['structured_document_projection_required_formats']=['DOCX']
    rsc['structured_document_exact_next_step']='CANONICAL_SOURCE_PROJECTION'
    rsc['default_exact_next_step']=rsc.get('exact_next_step','SOURCE_STRUCTURE_ENUMERATION')
    rsc['in_place_raw_source_mutation']='BLOCK'
    dump(sp,st1)

    lp=SOURCE/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
    life=load(lp)
    s1=next(x for x in life.get('stages',[]) if x.get('stage_uid')=='STAGE-01')
    unique_extend(s1.setdefault('required_normative_section_uids',[]),section_uids)
    s1['pre_stage_source_projection_admission_gate']={
      'required':True,
      'applicability':'STRUCTURED_DOCUMENT_REQUIRING_MACHINE_PROJECTION_OR_AUTHORITY_NA',
      'evaluation_boundary':'BEFORE_PRODUCT_STAGE01_WORK_UNIT_ACTIVATION',
      'validator_uid':'VAL-GOV-026',
      'reconciliation_gate':'WORD_YAML_SOURCE_FIDELITY_GATE',
      'reconciliation_result':'PASS',
      'freeze_state':'SOURCE_PAIR_FROZEN',
      'work_unit_binding_set_required':True,
      'raw_word_semantic_reparse':'BLOCK',
      'unverified_projection':'BLOCK',
      'implicit_na':'BLOCK'
    }
    s1['source_projection_semantic_preservation_gate']={
      'required_when_projection_applicable':True,
      'semantic_input':'EXACT_FROZEN_CANONICAL_SOURCE_PROJECTION_ONLY',
      'every_projection_source_node_exactly_once_disposition_required':True,
      'projection_node_silent_omission':'BLOCK',
      'projection_mutation':'BLOCK',
      'raw_source_hash_or_projection_hash_drift':'STOP_AND_REENTER_PRE_STAGE_SOURCE_PROJECTION',
      'derived_source_structure_lineage_required':True
    }
    life['governance_revision']=NEW_REV
    dump(lp,life)

    ip=SOURCE/'10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'
    invdoc=load(ip)
    inv=invdoc.setdefault('invariants',{})
    inv['SOURCE_PROJECTION_FIDELITY']={
      'invariant_uid':'GOV-INV-SOURCE-PROJECTION-FIDELITY-001',
      'applicability':'STRUCTURED_DOCUMENT_SOURCE_REQUIRING_MACHINE_PROJECTION',
      'raw_source_authority':'IMMUTABLE_ORIGINAL_SOURCE_BYTES',
      'projection_role':'MACHINE_READABLE_NON_AUTHORITY_MIRROR',
      'projection_schema_uid':PROJECTION_SCHEMA_UID,
      'projection_schema_revision':PROJECTION_SCHEMA_REV,
      'pre_stage_reconciliation_required':True,
      'pair_freeze_required':True,
      'stage01_activation_before_pair_freeze':'BLOCK',
      'raw_word_semantic_reparse_during_stage01':'BLOCK',
      'projection_mutation_after_freeze':'BLOCK',
      'schema_or_field_order_drift':'BLOCK',
      'silent_source_omission':'BLOCK',
      'source_pair_mutation_disposition':'INVALIDATE_AND_REENTER_PRE_STAGE_PROJECTION'
    }
    invdoc['governance_revision']=NEW_REV
    dump(ip,invdoc)

    rp=SOURCE/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'
    ref=load(rp)
    _ref_audit_types=ref.setdefault('audit_type_identities',[])
    if not any(x.get('audit_type_uid')=='AUDTYPE-GOV-015' for x in _ref_audit_types):
        _ref_audit_types.append({'audit_type_uid':'AUDTYPE-GOV-015','canonical_name':'STRUCTURED_DOCUMENT_CANONICAL_PROJECTION_ZERO_LOSS_RECONCILIATION','allowed_stage_uids':['PREFORMAL'],'denominator_eligible':True})
    unique_extend(ref['stage_reference_rules']['STAGE-01']['exact_required_normative_section_uids'],section_uids)
    if 'BUNDLE-GOV-CONSTRUCTION-BASE' in ref.get('common_bundle_reference_rules',{}):
        unique_extend(ref['common_bundle_reference_rules']['BUNDLE-GOV-CONSTRUCTION-BASE']['exact_section_uids'],['WEB-GOV-01-S090','WEB-GOV-02-S077','WEB-GOV-03-S072'])
    if 'BUNDLE-GOV-AUDIT-BASE' in ref.get('common_bundle_reference_rules',{}):
        unique_extend(ref['common_bundle_reference_rules']['BUNDLE-GOV-AUDIT-BASE']['exact_section_uids'],['WEB-GOV-04-S087'])
    ref['governance_revision']=NEW_REV
    dump(rp,ref)

    semp=SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'
    sem=load(semp)
    _audit_types=sem['semantic_snapshot'].setdefault('audit_type_identities',[])
    if not any(x.get('audit_type_uid')=='AUDTYPE-GOV-015' for x in _audit_types):
        _audit_types.append({'audit_type_uid':'AUDTYPE-GOV-015','canonical_name':'STRUCTURED_DOCUMENT_CANONICAL_PROJECTION_ZERO_LOSS_RECONCILIATION','allowed_stage_uids':['PREFORMAL'],'denominator_eligible':True})
    unique_extend(sem['semantic_snapshot']['stage_reference_rules']['STAGE-01']['exact_required_normative_section_uids'],section_uids)
    cb=sem['semantic_snapshot'].get('common_bundle_reference_rules') or {}
    if 'BUNDLE-GOV-CONSTRUCTION-BASE' in cb: unique_extend(cb['BUNDLE-GOV-CONSTRUCTION-BASE']['exact_section_uids'],['WEB-GOV-01-S090','WEB-GOV-02-S077','WEB-GOV-03-S072'])
    if 'BUNDLE-GOV-AUDIT-BASE' in cb: unique_extend(cb['BUNDLE-GOV-AUDIT-BASE']['exact_section_uids'],['WEB-GOV-04-S087'])
    sem['governance_revision']=NEW_REV
    sem['content_hash']=hobj(sem)
    dump(semp,sem)

    cip=SOURCE/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'
    ci=load(cip)
    bundles=ci.setdefault('mandatory_common_normative_bundles',{})
    unique_extend(bundles['BUNDLE-GOV-CONSTRUCTION-BASE'].setdefault('section_uids',[]),['WEB-GOV-01-S090','WEB-GOV-02-S077','WEB-GOV-03-S072'])
    unique_extend(bundles['BUNDLE-GOV-AUDIT-BASE'].setdefault('section_uids',[]),['WEB-GOV-04-S087'])
    if 'governance_revision' in ci: ci['governance_revision']=NEW_REV
    dump(cip,ci)

    ap=SOURCE/'10_REGISTRY/AUDIT_CATALOG.yaml'
    aud=load(ap)
    unique_extend(aud.setdefault('normative_section_uids',[]),section_uids)
    if not any(x.get('audit_item_uid')=='AUD-GOV-015' for x in aud.get('items',[])):
        aud.setdefault('items',[]).append({
          'audit_item_uid':'AUD-GOV-015',
          'audit_type':'STRUCTURED_DOCUMENT_CANONICAL_PROJECTION_ZERO_LOSS_RECONCILIATION',
          'stage_uid':'PREFORMAL',
          'target_uid':'GOVERNANCE_PACKAGE',
          'requirement_type':'BLOCKING',
          'validator_uid':'VAL-GOV-026',
          'required_evidence':['SOURCE_PROJECTION_RECONCILIATION_EVIDENCE','SOURCE_PROJECTION_FREEZE_RECEIPT','VALIDATOR_RESULT'],
          'denominator_eligible':True,
          'status':'REQUIRED',
          'validator_name':'STAGE1_SOURCE_PIPELINE_GUARD',
          'audit_type_uid':'AUDTYPE-GOV-015',
          'applicability':'STRUCTURED_DOCUMENT_SOURCE_REQUIRING_MACHINE_PROJECTION',
          'not_applicable_requires_authority':True
        })
    aud['governance_revision']=NEW_REV
    dump(ap,aud)

    bp=SOURCE/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'
    bpd=load(bp)
    unique_extend(bpd.setdefault('normative_section_uids',[]),section_uids)
    unique_extend(bpd.setdefault('required_normative_section_uids',[]),section_uids)
    unique_extend(bpd.setdefault('audit_item_uids',[]),['AUD-GOV-015'])
    bpd['structured_document_source_projection_audit_contract']={
      'audit_item_uid':'AUD-GOV-015',
      'validator_uid':'VAL-GOV-026',
      'dynamic_raw_source_denominator_required':True,
      'projection_summary_denominator_credit':0,
      'zero_loss_reconciliation_required':True,
      'source_pair_freeze_required_before_stage01':True,
      'fixed_schema_and_field_order_required':True,
      'negative_regression_required':True
    }
    bpd['governance_revision']=NEW_REV
    dump(bp,bpd)

    mutate_stage1_guard()
    mutate_stage1_tests()

def mutate_current_components():
    p=ROOT/'governance/specifications/current/EXECUTION_CYCLE_CONTROL.yaml'
    d=load(p)
    d['pre_stage_source_projection_admission']={
      'applies_to':'STRUCTURED_DOCUMENT_SOURCE_REQUIRING_MACHINE_PROJECTION',
      'canonical_contract_ref':'.github/governance-source/active/source/10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml',
      'invariant_uid':'GOV-INV-SOURCE-PROJECTION-FIDELITY-001',
      'required_order':['RAW_CAPTURE_LOCKED','PROJECTION_COMPLETE','RECONCILIATION_PASS','SOURCE_PAIR_FROZEN','STAGE01_ELIGIBLE'],
      'stage01_work_unit_activation_before_source_pair_frozen':'BLOCK',
      'raw_source_and_projection_mutable_after_pair_freeze':False,
      'any_pair_member_mutation':'INVALIDATE_PAIR_AND_REENTER_PRE_STAGE_PROJECTION',
      'stage01_semantic_input':'EXACT_FROZEN_CANONICAL_SOURCE_PROJECTION_ONLY',
      'raw_word_semantic_reparse_during_stage01':'BLOCK',
      'schema_alias_or_optional_field_fallback':'BLOCK',
      'not_applicable_requires_authority_evidence':True
    }
    wur=d.setdefault('work_unit_resolution_gate',{})
    wur['stage01_source_projection_pre_activation_required_when_applicable']=True
    wur['stage01_source_projection_freeze_receipt_required']=True
    wur['stage01_source_projection_pair_hash_binding_required']=True
    wur['stage01_unverified_projection_activation']='BLOCK'
    d['schema_version']=int(d.get('schema_version',0))+1
    dump(p,d)

    ap=ROOT/'governance/ci/stage_execution_semantic_adapters.yaml'
    ad=load(ap)
    s1=ad['stages']['STAGE-01']
    unique_extend(s1.setdefault('semantic_dimensions',[]),['SOURCE_PROJECTION_FIDELITY'])
    unique_extend(s1.setdefault('scanner_dimensions',[]),['SOURCE_PROJECTION_LOCK'])
    dump(ap,ad)
    mutate_stage_execution_engine()

def source_checksums_and_archives():
    checks=SOURCE/'CHECKSUMS.sha256'
    files=sorted([p for p in SOURCE.rglob('*') if p.is_file() and p!=checks],key=lambda p:p.relative_to(SOURCE).as_posix())
    checks.write_text(''.join(f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in files),encoding='utf-8')
    allfiles=sorted([p for p in SOURCE.rglob('*') if p.is_file()],key=lambda p:p.relative_to(SOURCE).as_posix())
    if len(allfiles)!=75:
        raise RuntimeError(f'source file count changed:{len(allfiles)}')
    tbuf=io.BytesIO()
    with tarfile.open(fileobj=tbuf,mode='w',format=tarfile.PAX_FORMAT) as tf:
        for p in allfiles:
            rel=p.relative_to(SOURCE).as_posix()
            info=tf.gettarinfo(str(p),arcname=rel)
            info.uid=0;info.gid=0;info.uname='';info.gname='';info.mtime=0
            with p.open('rb') as fh: tf.addfile(info,fh)
    bundle=lzma.compress(tbuf.getvalue(),format=lzma.FORMAT_XZ,preset=9)
    zbuf=io.BytesIO()
    with zipfile.ZipFile(zbuf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for p in allfiles:
            rel=p.relative_to(SOURCE).as_posix()
            zi=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED;zi.create_system=3
            mode=493 if p.stat().st_mode&73 else 420;zi.external_attr=(mode&65535)<<16
            zf.writestr(zi,p.read_bytes())
    return sha(checks),hashlib.sha256(bundle).hexdigest(),hashlib.sha256(zbuf.getvalue()).hexdigest()

def refresh_source():
    sem=load(SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml')
    semantic_hash=sem['content_hash']
    for rel in [
      '10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml','10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml',
      '10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml','10_REGISTRY/BLUEPRINT_REGISTRY.yaml',
      '10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml',
      '10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml',
      '10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml','10_REGISTRY/AUDIT_CATALOG.yaml',
      '10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml'
    ]:
        p=SOURCE/rel; d=load(p)
        if 'governance_revision' in d: d['governance_revision']=NEW_REV
        dump(p,d)
    rp=SOURCE/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'; rd=load(rp); rd['governance_revision']=NEW_REV; dump(rp,rd)
    rvp=SOURCE/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml'; rv=load(rvp); rv['governance_revision']=NEW_REV; dump(rvp,rv)
    readme=SOURCE/'README.md'; rs=readme.read_text(encoding='utf-8')
    if '## v2.2.18 Word/YAML pre-Stage01 source fidelity hardening' not in rs:
        readme.write_text(rs.rstrip()+'\n\n## v2.2.18 Word/YAML pre-Stage01 source fidelity hardening\nStructured Word/DOCX source is immutable after capture; Canonical YAML uses one fixed schema and is zero-loss reconciled and pair-frozen before Stage-01 activation. Stage-01 consumes only the exact frozen projection.\n',encoding='utf-8')
    vr=SOURCE/'VERSIONING_RULE.md'; vs=vr.read_text(encoding='utf-8')
    if '## v2.2.18 structured-source projection lock rule' not in vs:
        vr.write_text(vs.rstrip()+'\n\n## v2.2.18 structured-source projection lock rule\n- Captured Word/DOCX bytes are immutable; byte changes create a new source revision.\n- Canonical YAML projection has one registered fixed schema/ordering contract and is non-authority.\n- Reconciliation PASS freezes the exact Word/YAML pair; any pair mutation invalidates admission.\n- Stage-01 may consume only the frozen projection and may not reparse Word as a semantic fallback.\n',encoding='utf-8')
    replace_const(SOURCE/'09_TESTS/governance/validate_reference_semantics.py','SEMANTIC_BASELINE_CONTENT_HASH',semantic_hash)
    run(sys.executable,str(SOURCE/'09_TESTS/governance/compile_governance_baseline.py'))
    run(sys.executable,str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'))
    checks,bundle,zips=source_checksums_and_archives()
    replace_const(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py','EXPECTED_BUNDLE_SHA256',bundle)
    replace_const(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py','EXPECTED_SOURCE_ZIP_SHA256',zips)
    for name,val in [('EXPECTED_CHECKSUMS_SHA256',checks),('EXPECTED_SEMANTIC_CONTENT_HASH',semantic_hash),('EXPECTED_SOURCE_ZIP_SHA256',zips),('EXPECTED_BUNDLE_SHA256',bundle)]:
        replace_const(ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py',name,val)
    return semantic_hash,checks,bundle,zips

def update_current(semantic,checks,bundle,zips):
    mp=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'
    m=load(mp); oldsl=copy.deepcopy(m.get('source_lineage') or {})
    m['artifact_uid']=NEW_UID; m['display_version']=NEW_DISPLAY
    m.setdefault('source_lineage',{}).update({
      'verified_package_filename':NEW_PACKAGE,'verified_package_sha256':zips,
      'predecessor_governance_uid':OLD_UID,'promotion_authorization_uid':AUTH_UID,
      'source_bytes_changed_by_this_successor':True,
      'source_identity_reused_only_because_source_bytes_are_unchanged':False,
      'deterministic_source_bundle_sha256':bundle,'checksum_manifest_sha256':checks,
      'semantic_authority_content_hash':semantic,'verified_source_revision':NEW_REV,
      'predecessor_verified_package_filename':oldsl.get('verified_package_filename'),
      'predecessor_verified_package_sha256':oldsl.get('verified_package_sha256'),
      'post_promotion_projector_sync_authorization_uid':AUTH_UID
    })
    dump(mp,m)

    rp=ROOT/'governance/specifications/REGISTRY.yaml'
    r=load(rp)
    r['active_specification']['governance_uid']=NEW_UID
    r['active_specification']['display_version']=NEW_DISPLAY
    unique_extend(r['active_specification'].setdefault('aliases',[]),['word-yaml-prestage01-source-fidelity-hardening'])
    r['immediate_predecessor']={
      'governance_uid':OLD_UID,'display_version':OLD_DISPLAY,
      'version_role':'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY',
      'status':'SUPERSEDED_HISTORY_ONLY_AFTER_WORD_YAML_PRESTAGE01_SOURCE_FIDELITY_HARDENING'
    }
    dump(rp,r)

    cp=ROOT/'GOVERNANCE_CURRENT.yaml'
    c=load(cp); c['active_governance_uid']=NEW_UID; c['display_version']=NEW_DISPLAY
    c.setdefault('source_identity',{}).update({
      'verified_package_sha256':zips,'deterministic_source_bundle_sha256':bundle,
      'checksum_manifest_sha256':checks,'semantic_authority_content_hash':semantic,
      'verified_source_revision':NEW_REV,'source_bytes_changed_by_current_successor':True
    })
    dump(cp,c)

    ap=ROOT/'governance/test/ACTIVE_STATE.yaml'
    a=load(ap)
    a['specification_uid']=NEW_UID
    a['status']='WORD_YAML_PRE_STAGE01_SUCCESSOR_PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED'
    a['next_action']='RUN_EXACT_HEAD_WORD_YAML_GOVERNANCE_VALIDATION'
    if isinstance(a.get('stage_execution_remediation_closure_protocol'),dict):
        a['stage_execution_remediation_closure_protocol']['frozen_specification_uid']=NEW_UID
    gt=a.setdefault('governance_revision_transition',{})
    gt.update({
      'predecessor_governance_uid':OLD_UID,'current_governance_uid':NEW_UID,
      'fresh_revalidation_required':True,
      'fresh_revalidation_scope':'WORD_YAML_PRE_STAGE01_POLICY_CONSUMERS_ONLY_NO_PRODUCT_STAGE_CREDIT',
      'website_construction_remains_blocked':True,'deployment_remains_blocked':True,
      'current_governance_product_credit':0,'product_fresh_replay_required_after_governance_change':True
    })
    aw=a.get('active_work_unit') or {}
    if aw.get('work_unit_uid')!=WORK_UNIT: raise RuntimeError('active governance work unit drift')
    aw['current_status']='PROMOTION_MATERIALIZED_EXACT_HEAD_REVALIDATION_REQUIRED'
    a['active_work_unit']=aw
    rc=a.setdefault('resume_control',{})
    rc['current_resume_point']='WORD_YAML_PRE_STAGE01_SUCCESSOR_PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED'
    rc['current_work_unit_uid']=WORK_UNIT
    rc['exact_next_action']='RUN_EXACT_HEAD_WORD_YAML_GOVERNANCE_VALIDATION'
    rc['product_execution_allowed']=False
    rc['product_execution_block_reason']='WORD_YAML_PROJECTION_RECONCILIATION_NOT_YET_EXECUTED'
    if isinstance(a.get('word_source_snapshot_for_future_projection'),dict):
        a['word_source_snapshot_for_future_projection']['may_be_used_as_stage01_input_before_word_yaml_reconciliation_pass']=False
    dump(ap,a)

    sc=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
    sd=load(sc); sd['governance_uid']=NEW_UID
    sd['closure_status']='PROMOTION_MATERIALIZED_EXACT_HEAD_REVALIDATION_REQUIRED'
    sd['next_action']='RUN_EXACT_HEAD_WORD_YAML_GOVERNANCE_VALIDATION'
    sd['product_stage_execution_allowed']=False
    sd['product_stage_execution_block_reason']='WORD_YAML_PROJECTION_RECONCILIATION_NOT_YET_EXECUTED'
    dump(sc,sd)

    fp=ROOT/'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
    if fp.exists():
        f=load(fp); cse=f.get('current_stage2_execution')
        if isinstance(cse,dict) and cse.get('governance_uid')==OLD_UID: cse['governance_uid']=NEW_UID
        dump(fp,f)
    sf=ROOT/'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
    if sf.exists():
        d=load(sf)
        if d.get('governance_uid')==OLD_UID: d['governance_uid']=NEW_UID
        if 'content_hash' in d: d['content_hash']=hobj(d)
        dump(sf,d)

    gp=SOURCE/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'
    g=load(gp); g['candidate']='v2.2.18_WORD_YAML_PRESTAGE01_SOURCE_FIDELITY_HARDENING_CANDIDATE'
    g['status']='CANDIDATE_UNDER_FRESH_SUCCESSOR_REVALIDATION'
    fresh=g.setdefault('fresh_revalidation',{})
    fresh.update({
      'required':True,'current_source_revision':NEW_REV,'current_closure_credit':False,
      'predecessor_evidence_current_closure_credit':False,'persisted_head_full_line_required':True,
      'historical_evidence_may_close_successor':False
    })
    dump(gp,g)

def validate_all():
    env=os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE']='1'
    env['PYTHONPYCACHEPREFIX']='/tmp/acpos-word-yaml-pycache'
    cmds=[
      [sys.executable,str(SOURCE/'09_TESTS/governance/validate_section_registry.py')],
      [sys.executable,str(SOURCE/'09_TESTS/governance/validate_reference_semantics.py')],
      [sys.executable,str(SOURCE/'09_TESTS/governance/test_stage1_source_to_blueprint_minimal_control.py')],
      [sys.executable,str(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py')],
      [sys.executable,str(ROOT/'governance/ci/governance_resolver.py')],
      [sys.executable,str(ROOT/'governance/ci/validate_governance_portability.py')],
      [sys.executable,str(ROOT/'governance/ci/validate_active_consumer_reference_integrity.py')],
      [sys.executable,str(ROOT/'governance/ci/validate_selected_execution_profile_integrity.py')],
      [sys.executable,str(ROOT/'governance/ci/stage_execution_engine.py'),'--definition-audit-all'],
      [sys.executable,str(ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py')],
    ]
    for cmd in cmds:
        cp=run(*cmd,check=False,env=env)
        print('$',' '.join(map(str,cmd)))
        print(cp.stdout[-8000:])
        if cp.returncode:
            print(cp.stderr[-12000:],file=sys.stderr)
            raise SystemExit(cp.returncode)

def apply():
    cur=load(ROOT/'GOVERNANCE_CURRENT.yaml')
    if cur.get('active_governance_uid') not in (OLD_UID,NEW_UID):
        raise RuntimeError('unexpected Current Governance')
    mutate_policy()
    mutate_current_components()
    semantic,checks,bundle,zips=refresh_source()
    update_current(semantic,checks,bundle,zips)
    return {'semantic_hash':semantic,'checksums_hash':checks,'bundle_hash':bundle,'zip_hash':zips}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--mode',choices=['promote'],required=True)
    args=ap.parse_args()
    result=apply()
    validate_all()
    for p in [
      ROOT/'.github/workflows/word-yaml-prestage01-governance-promotion.yml',
      ROOT/'.github/governance-maintenance/promote_word_yaml_prestage01_governance.py'
    ]:
        if p.exists(): p.unlink()
    run('git','config','user.name','github-actions[bot]')
    run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    run('git','add','-A')
    if run('git','diff','--cached','--quiet',check=False).returncode==0:
        raise RuntimeError('no promotion delta')
    msg='feat(governance): promote Word YAML pre-Stage01 source fidelity hardening\n\nSpec-Change-Authorization: '+AUTH_UID+'\nSpec-Change-Scope: WORD_YAML_PRESTAGE01_FIXED_SCHEMA_IMMUTABLE_PAIR_ZERO_LOSS_STAGE01_ADMISSION'
    run('git','commit','-m',msg)
    run(sys.executable,str(ROOT/'governance/ci/specification_mutation_guard.py'))
    run('git','push','origin','HEAD:rebuild-v2.1.1')
    print(json.dumps({'new_uid':NEW_UID,**result},indent=2))
    print('PROMOTION_PUSHED',run('git','rev-parse','HEAD').stdout.strip())
    return 0

if __name__=='__main__':
    raise SystemExit(main())
