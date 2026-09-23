#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, io, json, lzma, os, re, subprocess, sys, tarfile, zipfile
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
OLD_UID='GOV-REV-20260923-WORD-YAML-CROSS-PAGE-PORTABILITY-REGRESSION-CLOSURE'
NEW_UID='GOV-REV-20260923-WORD-CONTENT-BINARY-SOURCE-PROJECTION-HARDENING'
OLD_DISPLAY='v2.2.20'
NEW_DISPLAY='v2.2.21'
NEW_REV='v2.2.21-word-content-binary-source-projection-hardening'
AUTH_UID='USR-DIRECTIVE-20260923-WORD-CONTENT-BINARY-SOURCE-PROJECTION-R4'
WORK_UNIT='WU-GOV-WORD-CONTENT-BINARY-SOURCE-PROJECTION-001'
NEW_PACKAGE='AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.21_WORD_CONTENT_BINARY_SOURCE_PROJECTION_HARDENING_LOCAL_VERIFIED.zip'

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
    Path(p).write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=220),encoding='utf-8')

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def hobj(d):
    x=copy.deepcopy(d); x.pop('content_hash',None)
    return hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True,width=220).encode()).hexdigest()

def unique_extend(lst,items):
    for x in items:
        if x not in lst: lst.append(x)

def replace_const(path,name,value):
    p=Path(path); s=p.read_text(encoding='utf-8')
    pat=re.compile(r"(?m)^"+re.escape(name)+r"\s*=\s*'[^']*'$")
    ns,n=pat.subn(f"{name} = '{value}'",s,1)
    if n!=1: raise RuntimeError(f'constant replacement {name} count={n} path={path}')
    p.write_text(ns,encoding='utf-8')

def append_once(path,marker,text):
    p=Path(path); s=p.read_text(encoding='utf-8')
    if marker in s: return
    p.write_text(s.rstrip()+"\n\n"+text.strip()+"\n",encoding='utf-8')

def mutate_mother():
    append_once(SOURCE/'12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md',
      '### Source Document Content Readiness and Frozen Binary Source Parts',
      r'''
### Source Document Content Readiness and Frozen Binary Source Parts / 來源文件內容就緒與凍結二進位來源

Before a governed Word/DOCX becomes immutable source input, the document MUST receive a per-document Source Document Content Readiness Audit. The audit is a review/evidence artifact, not Product Authority and not a replacement for the Word. It MUST verify the applicable Basic Design requirement domains against the actual document, identify missing required design content, duplicate or contradictory identities, incomplete required matrices, visual-source presence/traceability, and render/readability evidence. If a REQUIRED design gap is found, the Word remains a mutable candidate, the gap is repaired in the Word, the Word receives a new exact source identity, and the audit is rerun. A document with unresolved required design gaps MUST NOT receive the raw-source immutable lock.

A PASS content-readiness audit does not approve Product behavior, Visual Review, Runtime, or Stage completion. It proves only that the selected Word is sufficiently self-contained to become the immutable source for projection. Downstream review/runtime states such as NOT_EXECUTED or PENDING_REVIEW are not themselves missing Word content when the Word explicitly defines them as downstream states.

For any non-XML binary package part contained in the accepted DOCX, projection MUST materialize the exact bytes into the projection-owned frozen binary-part store using a deterministic content-addressed path. This includes embedded raster images, package thumbnails, embedded objects, and other non-XML package parts. The binary bytes remain source evidence only; their existence MUST NOT assign Product responsibility or semantic meaning.

For visual or embedded-source interpretation, downstream source-intake execution MAY dereference only the exact frozen binary part resolved from Canonical Projection package-part hash + relationship/source-node lineage. It MUST NOT reopen or re-extract the Word package as a semantic fallback. XML/text semantics continue to come from the Canonical Projection source-node rows. Every binary dereference MUST verify the content hash immediately before use.
''')
    append_once(SOURCE/'12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md',
      '### Content Audit, Source Lock and Frozen Binary Delivery Order',
      r'''
### Content Audit, Source Lock and Frozen Binary Delivery Order / 內容稽核、來源鎖定與二進位交付順序

For structured Word/DOCX input, the exact pre-execution order is:
SOURCE DOCUMENT CONTENT REVIEW -> REPAIR WORD IF REQUIRED -> CONTENT_READINESS_PASS -> RAW SOURCE IMMUTABILITY LOCK -> CANONICAL YAML PROJECTION -> FROZEN BINARY SOURCE-PART MATERIALIZATION -> ZERO-LOSS RECONCILIATION -> SOURCE PAIR FREEZE -> WORK UNIT RESOLUTION.

The immutable source lock MUST bind the PASS content-readiness audit UID. No producer may create a valid lock receipt for a Word whose content-readiness audit is missing, non-PASS, stale, or bound to a different source hash.

Frozen binary source parts are projection-owned evidence. The delivery producer MUST copy exact source bytes, never screenshot/re-render/re-encode them, and MUST create exactly one deterministic frozen binary path per binary package-part hash. Derived thumbnails, OCR text, image descriptions, annotations, or AI visual interpretations are separate derived evidence and MUST NOT replace the exact frozen binary bytes.

The common DOCX projection producer MUST be product/page neutral. It MUST derive every count and source row from the current immutable document and MUST NOT contain page-specific field vocabularies, page IDs, function names, control names, or expected content counts.
''')
    append_once(SOURCE/'12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',
      '### Frozen Binary Part Admission and Mutation Invalidation',
      r'''
### Frozen Binary Part Admission and Mutation Invalidation / 凍結二進位來源准入與失效

CONTENT_READINESS_PASS is required before RAW_CAPTURE_LOCKED for structured Word/DOCX. Any Word repair after audit invalidates the audit and requires a fresh audit before locking.

At reconciliation and selected source-intake/base-blueprint admission, every expected non-XML binary package part MUST exist at the deterministic frozen-binary location and its bytes MUST match the package-part SHA-256. Missing, extra, duplicate, re-encoded, hash-mismatched, or path-mismatched frozen binary parts are blocking source-fidelity defects.

After SOURCE_PAIR_FROZEN, the Word, Canonical YAML projection, content-readiness audit binding, and frozen binary-part set are immutable for that attempt. Mutation of any member invalidates selected source-intake/base-blueprint eligibility and requires pre-stage re-entry.

Selected source-intake/base-blueprint execution may read binary pixels/bytes only through the frozen-binary resolver defined by the projection contract. Direct DOCX unzip/reparse for semantic recovery is forbidden.
''')
    append_once(SOURCE/'12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md',
      '### Content Readiness and Frozen Binary Source Audit',
      r'''
### Content Readiness and Frozen Binary Source Audit / 內容就緒與凍結二進位來源稽核

Audit MUST verify that the exact Word selected for projection has a PASS Source Document Content Readiness Audit bound to the same source UID/hash, with zero unresolved REQUIRED design-content gaps and zero unresolved document-level contradictions. Product-specific denominators are source-derived; Audit MUST NOT substitute universal page counts.

For every non-XML binary package part independently observed in the raw DOCX package, Audit MUST verify exactly one frozen binary file at the deterministic content-addressed path, byte length equality, SHA-256 equality, and continued traceability through package part + relationship + XML source-node evidence where applicable. Absence of relationship/source-node use is not permission to drop the binary package part; semantic disposition occurs later.

Destructive regression MUST include missing content-readiness audit and missing or hash-mismatched frozen binary source part. A source-fidelity PASS with unavailable pixels/bytes for an embedded visual is false completion and MUST be blocked.
''')

def mutate_contracts():
    p=SOURCE/'10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml'
    d=load(p); c=d['structured_document_source_projection_contract']
    c['source_document_content_readiness_audit']={
      'evidence_path_template':'00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{source_uid}/SOURCE_DOCUMENT_CONTENT_AUDIT.yaml',
      'required_before_raw_source_lock':True,
      'artifact_type':'SOURCE_DOCUMENT_CONTENT_AUDIT',
      'required_field_order':[
        'schema_version','artifact_uid','artifact_type','source_uid','source_sha256','page_uid',
        'audit_standard_uid','required_design_domain_uids','observed_design_domain_uids',
        'missing_required_design_domain_uids','matrix_integrity','visual_source_integrity',
        'render_integrity','open_downstream_states','unresolved_required_gap_count',
        'contradiction_count','result','evidence_content_hash'
      ],
      'pass_state':'PASS',
      'unresolved_required_gap_count_required':0,
      'contradiction_count_required':0,
      'product_specific_counts':'DYNAMIC_FROM_DOCUMENT',
      'downstream_not_executed_or_review_pending_is_automatic_content_gap':False
    }
    sm=c.get('state_machine') or []
    if 'CONTENT_READINESS_PASS' not in sm: sm.insert(0,'CONTENT_READINESS_PASS')
    c['state_machine']=sm
    r=c['raw_source_lock']; fields=r['required_field_order']
    if 'content_readiness_audit_uid' not in fields:
        fields.insert(fields.index('lock_state'),'content_readiness_audit_uid')
    r['content_readiness_pass_required']=True
    r['word_repair_after_pass_invalidates_audit']=True
    c['frozen_binary_source_part_materialization']={
      'required_for_non_xml_binary_package_parts':True,
      'storage_root_template':'00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{source_uid}/FROZEN_BINARY_PARTS',
      'filename_rule':'{part_sha256}{lowercase_original_suffix}',
      'source_bytes':'EXACT_DOCX_PACKAGE_PART_BYTES',
      'reencode_or_render_or_resample':'BLOCK',
      'expected_set':'EVERY_PACKAGE_PART_NOT_ENDING_XML_OR_RELS',
      'extra_file':'BLOCK',
      'missing_file':'BLOCK',
      'hash_mismatch':'BLOCK',
      'semantic_interpretation_during_materialization':'BLOCK',
      'stage01_binary_access':'PROJECTION_PACKAGE_PART_HASH_TO_FROZEN_BINARY_PATH_ONLY',
      'direct_docx_binary_reextract_during_stage01':'BLOCK',
      'hash_verify_before_each_semantic_use':True
    }
    z=c['reconciliation']['zero_loss_count_field_order']
    for k in ['missing_frozen_binary_parts','unexpected_frozen_binary_parts','frozen_binary_hash_mismatch','frozen_binary_path_mismatch']:
        if k not in z: z.append(k)
    s=c['stage01_consumption']
    s['binary_source_access']='EXACT_FROZEN_BINARY_PART_RESOLVED_FROM_PROJECTION_ONLY'
    s['direct_docx_binary_reextract']='BLOCK'
    s['binary_hash_verification_before_use']=True
    s['derived_visual_description_may_replace_frozen_binary_bytes']=False
    d['raw_source_capture_contract']['structured_document_exact_next_step']='SOURCE_DOCUMENT_CONTENT_AUDIT'
    d['governance_revision']=NEW_REV
    dump(p,d)

    p=SOURCE/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
    d=load(p); s1=next(x for x in d['stages'] if x.get('stage_uid')=='STAGE-01')
    gate=s1['pre_stage_source_projection_admission_gate']
    gate['content_readiness_audit_required']=True
    gate['content_readiness_result']='PASS'
    gate['frozen_binary_source_parts_required_when_present']=True
    gate['frozen_binary_hash_verification_required']=True
    gate['direct_docx_binary_reextract']='BLOCK'
    sp=s1['source_projection_semantic_preservation_gate']
    sp['binary_visual_semantics_source']='FROZEN_BINARY_PART_RESOLVED_FROM_PROJECTION'
    sp['binary_visual_source_hash_verification_required']=True
    d['governance_revision']=NEW_REV; dump(p,d)

    p=SOURCE/'10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'
    d=load(p); inv=d['invariants']['SOURCE_PROJECTION_FIDELITY']
    inv['content_readiness_audit_before_raw_lock']=True
    inv['content_readiness_required_gap_count']=0
    inv['frozen_binary_source_parts_required_when_present']=True
    inv['frozen_binary_bytes_exact_hash_required']=True
    inv['stage01_direct_docx_binary_reextract']='BLOCK'
    inv['stage01_binary_access']='PROJECTION_RESOLVED_FROZEN_BINARY_ONLY'
    d['governance_revision']=NEW_REV; dump(p,d)

    p=SOURCE/'10_REGISTRY/AUDIT_CATALOG.yaml'
    d=load(p); item=next(x for x in d['items'] if x.get('audit_item_uid')=='AUD-GOV-015')
    unique_extend(item['required_evidence'],['SOURCE_DOCUMENT_CONTENT_AUDIT','FROZEN_BINARY_SOURCE_PART_SET'])
    unique_extend(item.setdefault('coverage_extensions',[]),['SOURCE_DOCUMENT_CONTENT_READINESS','FROZEN_BINARY_SOURCE_PART_FIDELITY','STAGE01_BINARY_SEMANTIC_ACCESS'])
    d['governance_revision']=NEW_REV; dump(p,d)

    p=SOURCE/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'
    d=load(p); q=d['structured_document_source_projection_audit_contract']
    q['source_document_content_readiness_audit_required']=True
    q['zero_unresolved_required_word_content_gap_required']=True
    q['frozen_binary_source_parts_required_when_present']=True
    q['frozen_binary_exact_hash_required']=True
    q['stage01_direct_docx_binary_reextract']='BLOCK'
    d['governance_revision']=NEW_REV; dump(p,d)

def mutate_guard():
    p=SOURCE/'09_TESTS/governance/governance_stage1_pipeline_guard.py'
    s=p.read_text(encoding='utf-8')
    if "def _binary_parts_from_inventory" not in s:
        anchor="def _resolve_template(template:str,source_uid:str)->str:\n    return str(template).replace('{source_uid}',str(source_uid))\n"
        add=anchor+'''

def _content_audit_contract(package_root:Path):
    return (_projection_contract(package_root).get('source_document_content_readiness_audit') or {})

def _binary_contract(package_root:Path):
    return (_projection_contract(package_root).get('frozen_binary_source_part_materialization') or {})

def _is_binary_package_part(path:str)->bool:
    q=str(path).lower()
    return not (q.endswith('.xml') or q.endswith('.rels'))

def _binary_parts_from_inventory(inv:dict):
    return [x for x in (inv.get('package_parts') or []) if _is_binary_package_part(x.get('package_part_path') or '')]

def _binary_ref(workspace:Path,contract:dict,source_uid:str,row:dict)->Path:
    root=workspace/_resolve_template(contract.get('storage_root_template',''),source_uid)
    suffix=Path(str(row.get('package_part_path') or '')).suffix.lower()
    return root/(str(row.get('part_sha256'))+suffix)
'''
        if anchor not in s: raise RuntimeError('guard resolve template anchor missing')
        s=s.replace(anchor,add,1)

    marker="        lock_path=workspace/_resolve_template(raw_lock.get('receipt_path_template',''),suid)\n"
    if "content_audit_path=" not in s:
        repl="        contentc=contract.get('source_document_content_readiness_audit') or {}\n        binaryc=contract.get('frozen_binary_source_part_materialization') or {}\n        content_audit_path=workspace/_resolve_template(contentc.get('evidence_path_template',''),suid)\n"+marker
        s=s.replace(marker,repl,1)

    marker="        for p,label in [(lock_path,'raw_source_immutability_receipt'),(proj_path,'canonical_source_projection'),(rec_path,'source_projection_reconciliation_evidence'),(freeze_path,'source_projection_freeze_receipt')]:\n"
    if "source_document_content_audit" not in s[s.index(marker):s.index(marker)+600]:
        repl="        for p,label in [(content_audit_path,'source_document_content_audit'),(lock_path,'raw_source_immutability_receipt'),(proj_path,'canonical_source_projection'),(rec_path,'source_projection_reconciliation_evidence'),(freeze_path,'source_projection_freeze_receipt')]:\n"
        s=s.replace(marker,repl,1)
        s=s.replace("        if not all(p.is_file() for p in (lock_path,proj_path,rec_path,freeze_path)):\n",
                    "        if not all(p.is_file() for p in (content_audit_path,lock_path,proj_path,rec_path,freeze_path)):\n",1)

    marker="        lock=load_yaml(lock_path); projection=load_yaml(proj_path); evidence=load_yaml(rec_path); freeze=load_yaml(freeze_path)\n"
    if "content_audit=load_yaml" not in s:
        repl="        content_audit=load_yaml(content_audit_path); lock=load_yaml(lock_path); projection=load_yaml(proj_path); evidence=load_yaml(rec_path); freeze=load_yaml(freeze_path)\n        _exact_keys(content_audit,contentc.get('required_field_order') or [],'source_document_content_audit:'+suid,failures)\n        if content_audit.get('artifact_type')!=contentc.get('artifact_type') or content_audit.get('source_uid')!=suid or content_audit.get('source_sha256')!=raw_sha: failures.append('source_document_content_audit_identity_hash_mismatch:'+suid)\n        if content_audit.get('result')!=contentc.get('pass_state') or content_audit.get('unresolved_required_gap_count')!=0 or content_audit.get('contradiction_count')!=0 or (content_audit.get('missing_required_design_domain_uids') or []): failures.append('source_document_content_readiness_not_pass:'+suid)\n        if content_audit.get('evidence_content_hash')!=_hash_without(content_audit,'evidence_content_hash'): failures.append('source_document_content_audit_hash_mismatch:'+suid)\n"
        s=s.replace(marker,repl,1)

    marker="        if lock.get('artifact_type')!='RAW_SOURCE_IMMUTABILITY_RECEIPT' or lock.get('source_uid')!=suid: failures.append('raw_source_lock_identity_invalid:'+suid)\n"
    if "content_readiness_audit_uid" not in s[s.index(marker):s.index(marker)+900]:
        repl=marker+"        if lock.get('content_readiness_audit_uid')!=content_audit.get('artifact_uid'): failures.append('raw_source_lock_content_readiness_audit_uid_mismatch:'+suid)\n"
        s=s.replace(marker,repl,1)

    marker="        actual_parts=projection.get('package_parts') or []\n"
    if "expected_binary=_binary_parts_from_inventory" not in s:
        add="        expected_binary=_binary_parts_from_inventory(expected)\n        expected_binary_paths=set()\n        for _row in expected_binary:\n            _bp=_binary_ref(workspace,binaryc,suid,_row); expected_binary_paths.add(_bp)\n            if not _bp.is_file(): failures.append('frozen_binary_source_part_missing:'+suid+':'+str(_row.get('package_part_path'))); continue\n            if _bp.stat().st_size!=_row.get('size_bytes'): failures.append('frozen_binary_source_part_size_mismatch:'+suid+':'+str(_row.get('package_part_path')))\n            if file_sha(_bp)!=_row.get('part_sha256'): failures.append('frozen_binary_source_part_hash_mismatch:'+suid+':'+str(_row.get('package_part_path')))\n        _broot=workspace/_resolve_template(binaryc.get('storage_root_template',''),suid)\n        actual_binary_paths=set(p for p in _broot.iterdir() if p.is_file()) if _broot.is_dir() else set()\n        for _extra in sorted(actual_binary_paths-expected_binary_paths): failures.append('frozen_binary_source_part_unexpected:'+suid+':'+_extra.name)\n"
        s=s.replace(marker,add+marker,1)

    p.write_text(s,encoding='utf-8')

def mutate_tests():
    p=SOURCE/'09_TESTS/governance/test_stage1_source_to_blueprint_minimal_control.py'
    s=p.read_text(encoding='utf-8')
    # make minimal DOCX contain a binary package part via thumbnail relationship
    old="        ct='''<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/><Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/></Types>'''\n"
    new="        ct='''<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/><Default Extension=\"png\" ContentType=\"image/png\"/><Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/></Types>'''\n"
    if old in s: s=s.replace(old,new,1)
    old="        rootrels='''<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/></Relationships>'''\n"
    new="        rootrels='''<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/><Relationship Id=\"rId2\" Type=\"http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail\" Target=\"docProps/thumbnail.png\"/></Relationships>'''\n"
    if old in s: s=s.replace(old,new,1)
    old="        z.writestr('[Content_Types].xml',ct); z.writestr('_rels/.rels',rootrels); z.writestr('word/document.xml',doc)\n"
    new="        z.writestr('[Content_Types].xml',ct); z.writestr('_rels/.rels',rootrels); z.writestr('word/document.xml',doc); z.writestr('docProps/thumbnail.png',b'\\x89PNG\\r\\n\\x1a\\nTEST_BINARY_SOURCE_PART')\n"
    if old in s: s=s.replace(old,new,1)

    marker="    lock={'schema_version':1,'artifact_uid':'LOCK-DOCX1','artifact_type':'RAW_SOURCE_IMMUTABILITY_RECEIPT','source_uid':suid,'source_path':rawrel,'source_git_blob_sha':blob,'source_sha256':rawsha,'lock_state':'RAW_CAPTURE_LOCKED','writable':False,'mutation_policy':'NEW_SOURCE_REVISION_NEW_PROJECTION_NEW_RECONCILIATION'}\n"
    if marker in s:
        repl="    contentc=contract['source_document_content_readiness_audit']; binaryc=contract['frozen_binary_source_part_materialization']\n    ca={'schema_version':1,'artifact_uid':'CONTENT-AUDIT-DOCX1','artifact_type':'SOURCE_DOCUMENT_CONTENT_AUDIT','source_uid':suid,'source_sha256':rawsha,'page_uid':'SYNTH-PAGE-A','audit_standard_uid':'WEB-GOV-01-S090','required_design_domain_uids':['PAGE_IDENTITY'],'observed_design_domain_uids':['PAGE_IDENTITY'],'missing_required_design_domain_uids':[],'matrix_integrity':{'required_rows':1,'complete_rows':1,'missing_rows':0,'duplicate_uid_count':0},'visual_source_integrity':{'embedded_visual_count':0,'missing_visual_count':0},'render_integrity':{'render_required':False,'render_result':'NOT_APPLICABLE_SYNTHETIC_FIXTURE'},'open_downstream_states':[],'unresolved_required_gap_count':0,'contradiction_count':0,'result':'PASS'}\n    ca['evidence_content_hash']=g._hash_without(ca,'evidence_content_hash'); write(root/f'{base}/SOURCE_DOCUMENT_CONTENT_AUDIT.yaml',ca)\n    lock={'schema_version':1,'artifact_uid':'LOCK-DOCX1','artifact_type':'RAW_SOURCE_IMMUTABILITY_RECEIPT','source_uid':suid,'source_path':rawrel,'source_git_blob_sha':blob,'source_sha256':rawsha,'content_readiness_audit_uid':ca['artifact_uid'],'lock_state':'RAW_CAPTURE_LOCKED','writable':False,'mutation_policy':'NEW_SOURCE_REVISION_NEW_PROJECTION_NEW_RECONCILIATION'}\n"
        s=s.replace(marker,repl,1)

    marker="    inv=g.derive_docx_inventory(raw)\n"
    if marker in s and "FROZEN_BINARY_PARTS" not in s[s.index(marker):s.index(marker)+1800]:
        add=marker+"    with zipfile.ZipFile(raw,'r') as _z:\n        for _row in g._binary_parts_from_inventory(inv):\n            _dst=g._binary_ref(root,binaryc,suid,_row); _dst.parent.mkdir(parents=True,exist_ok=True); _dst.write_bytes(_z.read(_row['package_part_path']))\n"
        s=s.replace(marker,add,1)

    # new zero-loss fields are generated from contract already by dict comprehension in fixture.
    test_anchor="c('projection_fixed_schema_positive',_prun(),'PASS')\n"
    if "projection_content_readiness_audit_required" not in s:
        extra=test_anchor+"""
def _p_content_audit_missing(r,rawcap,capstate,f): (r/f\"{f['base']}/SOURCE_DOCUMENT_CONTENT_AUDIT.yaml\").unlink()
c('projection_content_readiness_audit_required',_prun(_p_content_audit_missing),'FAIL')
def _p_frozen_binary_missing(r,rawcap,capstate,f):
    for p in (r/f\"{f['base']}/FROZEN_BINARY_PARTS\").iterdir():
        if p.is_file(): p.unlink(); break
c('projection_frozen_binary_part_required',_prun(_p_frozen_binary_missing),'FAIL')
"""
        if test_anchor not in s: raise RuntimeError('projection positive test anchor missing')
        s=s.replace(test_anchor,extra,1)
    p.write_text(s,encoding='utf-8')

def write_producer():
    p=ROOT/'governance/ci/build_docx_source_projection.py'
    body=r'''#!/usr/bin/env python3
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
    args=ap.parse_args()
    w=Path(args.workspace).resolve(); raw=w/args.source_rel; suid=args.source_uid
    if not raw.is_file(): raise SystemExit('raw source missing')
    contract=g._projection_contract(PKG)
    cc=contract['source_document_content_readiness_audit']; rc=contract['raw_source_lock']; pc=contract['projection']; ac=contract['reconciliation']; fc=contract['pair_freeze']; bc=contract['frozen_binary_source_part_materialization']
    base=w/f'00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{suid}'
    capath=base/'SOURCE_DOCUMENT_CONTENT_AUDIT.yaml'
    if not capath.is_file(): raise SystemExit('content readiness audit missing')
    ca=g.load_yaml(capath); rawsha=g.file_sha(raw); blob=g.git_blob_sha(raw)
    if ca.get('source_uid')!=suid or ca.get('source_sha256')!=rawsha or ca.get('result')!='PASS' or ca.get('unresolved_required_gap_count')!=0 or ca.get('contradiction_count')!=0: raise SystemExit('content readiness audit not PASS for exact source')
    rawcap={'artifact_uid':'RAW-CAP-'+suid,'artifact_type':'RAW_SOURCE_REFERENCE_MANIFEST','status':'CURRENT_RAW_SOURCE_CAPTURE','capture_root':'00_SOURCE_INTAKE/RAW_SOURCE','records':[{'source_uid':suid,'source_format':'DOCX','projection_required':True,'page_uid':args.page_uid,'source_role':'MIXED_PAGE_VISUAL_SOURCE_INPUT','source_domain_scope':'MIXED_PAGE_VISUAL','source_path':args.source_rel,'target_path':args.source_rel,'source_git_blob_sha':blob,'target_git_blob_sha':blob,'content_mutated':False}]}
    capstate={'run_uid':'PROJECTION-RUN-'+rawsha[:16].upper(),'state':'CAPTURE_CLOSED','next_step':'SOURCE_DOCUMENT_CONTENT_AUDIT','recapture_allowed':False}
    write(w/'00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml',rawcap); write(w/'00_SOURCE_INTAKE/RAW_SOURCE_CAPTURE_STATE.yaml',capstate)
    lock={'schema_version':1,'artifact_uid':'LOCK-'+suid,'artifact_type':'RAW_SOURCE_IMMUTABILITY_RECEIPT','source_uid':suid,'source_path':args.source_rel,'source_git_blob_sha':blob,'source_sha256':rawsha,'content_readiness_audit_uid':ca['artifact_uid'],'lock_state':'RAW_CAPTURE_LOCKED','writable':False,'mutation_policy':'NEW_SOURCE_REVISION_NEW_PROJECTION_NEW_RECONCILIATION'}
    lock['content_hash']=g._hash_without(lock,'content_hash'); write(base/'RAW_SOURCE_IMMUTABILITY_RECEIPT.yaml',lock)
    inv=g.derive_docx_inventory(raw)
    with zipfile.ZipFile(raw,'r') as z:
        for row in g._binary_parts_from_inventory(inv):
            dst=g._binary_ref(w,bc,suid,row); dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(z.read(row['package_part_path']))
    den=[{'denominator_uid':'DEN-PACKAGE-PART','denominator_type':'PACKAGE_PART','required_count':len(inv['package_parts']),'projected_count':len(inv['package_parts'])},{'denominator_uid':'DEN-RELATIONSHIP','denominator_type':'RELATIONSHIP','required_count':len(inv['relationships']),'projected_count':len(inv['relationships'])},{'denominator_uid':'DEN-XML-NODE','denominator_type':'XML_NODE','required_count':len(inv['source_nodes']),'projected_count':len(inv['source_nodes'])}]
    proj={'schema_version':1,'artifact_uid':'PROJ-'+suid,'artifact_type':'CANONICAL_SOURCE_PROJECTION','projection_schema_uid':pc['schema_uid'],'projection_schema_revision':pc['schema_revision'],'projection_role':pc['role'],'normative_authority':False,'source_identity':{'source_uid':suid,'source_path':args.source_rel,'source_format':'DOCX','source_git_blob_sha':blob,'source_sha256':rawsha,'raw_source_lock_receipt_uid':lock['artifact_uid']},'extraction_identity':{'extractor_uid':'ACPOS-DOCX-CANONICAL-PROJECTION-001','extractor_version':'1','extraction_run_uid':capstate['run_uid'],'extraction_evidence_ref':str(capath.relative_to(w))},'serialization_contract':{'yaml_profile':'YAML_1_2_SAFE_SUBSET','encoding':'UTF-8','line_ending':'LF','key_order_contract_uid':pc['schema_uid'],'anchors_aliases':'FORBIDDEN','implicit_custom_tags':'FORBIDDEN'},'denominator_rows':den,'package_parts':inv['package_parts'],'relationships':inv['relationships'],'source_nodes':inv['source_nodes'],'projection_content_hash':None,'status':'PROJECTION_COMPLETE'}
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
    print(json.dumps({'status':'PASS','source_uid':suid,'source_sha256':rawsha,'projection_uid':proj['artifact_uid'],'projection_hash':proj['projection_content_hash'],'pair_hash':pair,'binary_part_count':len(g._binary_parts_from_inventory(inv))},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
'''
    p.write_text(body,encoding='utf-8')

def mutate_portability():
    p=ROOT/'governance/ci/validate_governance_portability.py'; s=p.read_text(encoding='utf-8')
    if 'docx_projection_producer_product_identity_leak' not in s:
        marker="out={\n"
        ins=r'''_producer=ROOT/'governance/ci/build_docx_source_projection.py'
if not _producer.is_file():
    failures.append('docx_projection_producer_missing')
else:
    _pt=_producer.read_text(encoding='utf-8')
    if literal_product_identity.search(_pt):
        failures.append('docx_projection_producer_product_identity_leak')
    for _token in ('CORE-01','ASSET-01','VIDEO-01','EDIT-01'):
        if _token in _pt:
            failures.append('docx_projection_producer_literal_page_identity:'+_token)
'''
        if marker not in s: raise RuntimeError('portability output marker missing')
        s=s.replace(marker,ins+marker,1)
        p.write_text(s,encoding='utf-8')

def mutate_current_control():
    p=ROOT/'governance/specifications/current/EXECUTION_CYCLE_CONTROL.yaml'
    d=load(p); q=d['pre_stage_source_projection_admission']
    order=q['required_order']
    if 'CONTENT_READINESS_PASS' not in order: order.insert(0,'CONTENT_READINESS_PASS')
    q['source_document_content_readiness_audit_required']=True
    q['frozen_binary_source_part_materialization_required_when_present']=True
    q['stage01_binary_source_access']='PROJECTION_RESOLVED_FROZEN_BINARY_ONLY'
    q['direct_docx_binary_reextract']='BLOCK'
    q['projection_producer_ref']='governance/ci/build_docx_source_projection.py'
    d['schema_version']=int(d.get('schema_version',0))+1
    dump(p,d)

def source_checksums_and_archives():
    checks=SOURCE/'CHECKSUMS.sha256'
    files=sorted([p for p in SOURCE.rglob('*') if p.is_file() and p!=checks],key=lambda p:p.relative_to(SOURCE).as_posix())
    checks.write_text(''.join(f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in files),encoding='utf-8')
    allfiles=sorted([p for p in SOURCE.rglob('*') if p.is_file()],key=lambda p:p.relative_to(SOURCE).as_posix())
    if len(allfiles)!=75: raise RuntimeError(f'source file count changed:{len(allfiles)}')
    tb=io.BytesIO()
    with tarfile.open(fileobj=tb,mode='w',format=tarfile.PAX_FORMAT) as tf:
        for p in allfiles:
            rel=p.relative_to(SOURCE).as_posix(); info=tf.gettarinfo(str(p),arcname=rel)
            info.uid=0;info.gid=0;info.uname='';info.gname='';info.mtime=0
            with p.open('rb') as fh: tf.addfile(info,fh)
    bundle=lzma.compress(tb.getvalue(),format=lzma.FORMAT_XZ,preset=9)
    zb=io.BytesIO()
    with zipfile.ZipFile(zb,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for p in allfiles:
            rel=p.relative_to(SOURCE).as_posix(); zi=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0)); zi.compress_type=zipfile.ZIP_DEFLATED;zi.create_system=3
            mode=493 if p.stat().st_mode&73 else 420; zi.external_attr=(mode&65535)<<16
            zf.writestr(zi,p.read_bytes())
    return sha(checks),hashlib.sha256(bundle).hexdigest(),hashlib.sha256(zb.getvalue()).hexdigest()

def refresh_source():
    # keep all source registries on the new revision
    for rel in ['10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml','10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml','10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml','10_REGISTRY/BLUEPRINT_REGISTRY.yaml','10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml','10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml','10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml','10_REGISTRY/AUDIT_CATALOG.yaml','10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml']:
        p=SOURCE/rel; d=load(p)
        if 'governance_revision' in d: d['governance_revision']=NEW_REV
        dump(p,d)
    sem=load(SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml')
    sem['governance_revision']=NEW_REV
    # two new Stage-1 regression cases
    suite=next(x for x in sem.get('mandatory_regression_assets') or [] if Path(str(x.get('path') or '')).name=='test_stage1_source_to_blueprint_minimal_control.py')
    if suite.get('expected_total')!=45 or suite.get('expected_passed')!=45: raise RuntimeError('unexpected Stage-1 regression denominator before v2.2.21')
    suite['expected_total']=47; suite['expected_passed']=47
    sem['content_hash']=hobj(sem); dump(SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml',sem)
    replace_const(SOURCE/'09_TESTS/governance/validate_reference_semantics.py','SEMANTIC_BASELINE_CONTENT_HASH',sem['content_hash'])
    for rel in ['10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml','10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml']:
        p=SOURCE/rel; d=load(p); d['governance_revision']=NEW_REV; dump(p,d)
    gp=SOURCE/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'
    g=load(gp); g['candidate']='v2.2.21_WORD_CONTENT_BINARY_SOURCE_PROJECTION_HARDENING_CANDIDATE'; g['status']='CANDIDATE_UNDER_FRESH_SUCCESSOR_REVALIDATION'
    g.setdefault('fresh_revalidation',{}).update({'required':True,'current_source_revision':NEW_REV,'current_closure_credit':False,'predecessor_evidence_current_closure_credit':False,'persisted_head_full_line_required':True,'historical_evidence_may_close_successor':False})
    dump(gp,g)
    run(sys.executable,str(SOURCE/'09_TESTS/governance/compile_governance_baseline.py'))
    run(sys.executable,str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'))
    checks,bundle,zips=source_checksums_and_archives()
    replace_const(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py','EXPECTED_BUNDLE_SHA256',bundle)
    replace_const(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py','EXPECTED_SOURCE_ZIP_SHA256',zips)
    full=ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'; ft=full.read_text(encoding='utf-8')
    old="'test_stage1_source_to_blueprint_minimal_control.py': {'total': 45, 'passed_expectations': 45}"
    new="'test_stage1_source_to_blueprint_minimal_control.py': {'total': 47, 'passed_expectations': 47}"
    if old not in ft: raise RuntimeError('full-line Stage-1 denominator projection missing')
    full.write_text(ft.replace(old,new,1),encoding='utf-8')
    for name,val in [('EXPECTED_CHECKSUMS_SHA256',checks),('EXPECTED_SEMANTIC_CONTENT_HASH',sem['content_hash']),('EXPECTED_SOURCE_ZIP_SHA256',zips),('EXPECTED_BUNDLE_SHA256',bundle)]:
        replace_const(ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py',name,val)
    return sem['content_hash'],checks,bundle,zips

def update_current(semantic,checks,bundle,zips):
    p=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'; d=load(p); old=copy.deepcopy(d.get('source_lineage') or {})
    d['artifact_uid']=NEW_UID; d['display_version']=NEW_DISPLAY
    d.setdefault('source_lineage',{}).update({'verified_package_filename':NEW_PACKAGE,'verified_package_sha256':zips,'predecessor_governance_uid':OLD_UID,'promotion_authorization_uid':AUTH_UID,'source_bytes_changed_by_this_successor':True,'source_identity_reused_only_because_source_bytes_are_unchanged':False,'deterministic_source_bundle_sha256':bundle,'checksum_manifest_sha256':checks,'semantic_authority_content_hash':semantic,'verified_source_revision':NEW_REV,'predecessor_verified_package_filename':old.get('verified_package_filename'),'predecessor_verified_package_sha256':old.get('verified_package_sha256'),'post_promotion_projector_sync_authorization_uid':AUTH_UID})
    dump(p,d)
    p=ROOT/'governance/specifications/REGISTRY.yaml'; d=load(p)
    d['active_specification']['governance_uid']=NEW_UID; d['active_specification']['display_version']=NEW_DISPLAY; unique_extend(d['active_specification'].setdefault('aliases',[]),['word-content-binary-source-projection-hardening'])
    d['immediate_predecessor']={'governance_uid':OLD_UID,'display_version':OLD_DISPLAY,'version_role':'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY','status':'SUPERSEDED_HISTORY_ONLY_AFTER_WORD_CONTENT_BINARY_SOURCE_PROJECTION_HARDENING'}
    dump(p,d)
    p=ROOT/'GOVERNANCE_CURRENT.yaml'; d=load(p); d['active_governance_uid']=NEW_UID; d['display_version']=NEW_DISPLAY
    d.setdefault('source_identity',{}).update({'verified_package_sha256':zips,'deterministic_source_bundle_sha256':bundle,'checksum_manifest_sha256':checks,'semantic_authority_content_hash':semantic,'verified_source_revision':NEW_REV,'source_bytes_changed_by_current_successor':True})
    dump(p,d)
    p=ROOT/'governance/test/ACTIVE_STATE.yaml'; d=load(p)
    d['specification_uid']=NEW_UID; d['status']='WORD_CONTENT_BINARY_SOURCE_PROJECTION_SUCCESSOR_PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED'; d['next_action']='RUN_EXACT_HEAD_WORD_CONTENT_BINARY_SOURCE_PROJECTION_VALIDATION'
    d['current_primary_task_layer']='GOVERNANCE_MAINTENANCE'; d['current_primary_task_authorization_uid']=AUTH_UID; d['current_primary_task_product_stage_credit']=0
    d['active_work_unit']={'work_unit_uid':WORK_UNIT,'canonical_name':'WORD_CONTENT_READINESS_BINARY_SOURCE_PROJECTION_GOVERNANCE_HARDENING','primary_task_layer':'GOVERNANCE_MAINTENANCE','semantic_capability':'SOURCE_INTAKE_STAGE1_GOVERNANCE','canonical_owner_refs':['.github/governance-source/active/source/12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md','.github/governance-source/active/source/12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md','.github/governance-source/active/source/12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md','.github/governance-source/active/source/12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md','.github/governance-source/active/source/10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml'],'current_status':'PROMOTION_MATERIALIZED_EXACT_HEAD_REVALIDATION_REQUIRED','authorization_uid':AUTH_UID,'exact_scope':['SOURCE_DOCUMENT_CONTENT_READINESS_AUDIT','RAW_WORD_POST_AUDIT_IMMUTABILITY','FROZEN_BINARY_SOURCE_PART_MATERIALIZATION','STAGE01_FROZEN_BINARY_SEMANTIC_ACCESS','PRODUCT_NEUTRAL_DOCX_PROJECTION_PRODUCER'],'product_data_mutation_allowed':False,'product_authority_mutation_allowed':False,'product_stage_credit':0}
    d['resume_control']['current_resume_point']='WORD_CONTENT_BINARY_SOURCE_PROJECTION_SUCCESSOR_PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED'; d['resume_control']['current_work_unit_uid']=WORK_UNIT; d['resume_control']['current_owner']='SOURCE_INTAKE_STAGE1_GOVERNANCE'; d['resume_control']['exact_next_action']='RUN_EXACT_HEAD_WORD_CONTENT_BINARY_SOURCE_PROJECTION_VALIDATION'; d['resume_control']['product_execution_allowed']=False; d['resume_control']['product_execution_block_reason']='CORE01_WORD_CONTENT_AUDIT_AND_PROJECTION_NOT_YET_MATERIALIZED'
    d['governance_revision_transition'].update({'current_governance_uid':NEW_UID,'predecessor_governance_uid':OLD_UID,'fresh_revalidation_required':False,'governance_policy_consumer_revalidation_required':True,'product_stage_revalidation_required':False,'product_stage_revalidation_credit':0,'fresh_revalidation_scope':'WORD_CONTENT_BINARY_SOURCE_PROJECTION_POLICY_CONSUMERS_ONLY_NO_PRODUCT_STAGE_CREDIT','current_governance_product_credit':0})
    dump(p,d)
    p=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'; d=load(p); d['governance_uid']=NEW_UID; d['scope_kind']='EXACT_GOVERNANCE_MAINTENANCE_WORD_CONTENT_BINARY_SOURCE_PROJECTION'; d['work_unit_uid']=WORK_UNIT; d['scope_selection_authority']=AUTH_UID; d['included_units']=['SOURCE_DOCUMENT_CONTENT_READINESS_AUDIT','RAW_WORD_POST_AUDIT_IMMUTABILITY','CANONICAL_YAML_PROJECTION','FROZEN_BINARY_SOURCE_PART_MATERIALIZATION','WORD_YAML_RECONCILIATION','SOURCE_PAIR_FREEZE','STAGE01_FROZEN_BINARY_SEMANTIC_ACCESS','PRODUCT_NEUTRAL_DOCX_PROJECTION_PRODUCER']; d['product_stage_execution_allowed']=False; d['product_stage_execution_block_reason']='CORE01_WORD_CONTENT_AUDIT_AND_PROJECTION_NOT_YET_MATERIALIZED'; d['next_action']='RUN_EXACT_HEAD_WORD_CONTENT_BINARY_SOURCE_PROJECTION_VALIDATION'; d['closure_status']='PROMOTION_MATERIALIZED_EXACT_HEAD_REVALIDATION_REQUIRED'; d['fresh_revalidation_required']=False; d['product_stage_revalidation_required']=False; d['product_stage_revalidation_credit']=0
    dump(p,d)

def validate_all():
    env=os.environ.copy(); env['PYTHONDONTWRITEBYTECODE']='1'; env['PYTHONPYCACHEPREFIX']='/tmp/acpos-v221-pycache'
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
        cp=run(*cmd,check=False,env=env); print('$',' '.join(map(str,cmd))); print(cp.stdout[-9000:])
        if cp.returncode: print(cp.stderr[-16000:],file=sys.stderr); raise SystemExit(cp.returncode)

def main():
    mutate_mother(); mutate_contracts(); mutate_guard(); mutate_tests(); write_producer(); mutate_portability(); mutate_current_control()
    semantic,checks,bundle,zips=refresh_source(); update_current(semantic,checks,bundle,zips); validate_all()
    for p in [ROOT/'.github/workflows/word-content-binary-source-projection-promotion.yml',ROOT/'.github/governance-maintenance/promote_word_content_binary_source_projection.py']:
        if p.exists(): p.unlink()
    run('git','config','user.name','github-actions[bot]'); run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'); run('git','add','-A')
    if run('git','diff','--cached','--quiet',check=False).returncode==0: raise RuntimeError('no promotion delta')
    msg='feat(governance): harden Word content and frozen binary source projection\\n\\nSpec-Change-Authorization: '+AUTH_UID+'\\nSpec-Change-Scope: WORD_CONTENT_READINESS_FROZEN_BINARY_SOURCE_PROJECTION'
    run('git','commit','-m',msg); run(sys.executable,str(ROOT/'governance/ci/specification_mutation_guard.py')); run('git','push','origin','HEAD:rebuild-v2.1.1')
    print(json.dumps({'new_uid':NEW_UID,'semantic_hash':semantic,'checksums_hash':checks,'bundle_hash':bundle,'zip_hash':zips},indent=2))
    print('PROMOTION_PUSHED',run('git','rev-parse','HEAD').stdout.strip())
if __name__=='__main__': main()
