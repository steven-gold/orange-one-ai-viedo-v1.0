#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import ast
import copy
import hashlib
import io
import json
import lzma
import subprocess
import tarfile
import zipfile
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
OLD_UID='GOV-REV-20260919-PROFILE-TOKEN-DECONTAMINATION-HARDENING'
NEW_UID='GOV-REV-20260919-STRUCTURED-MUTATION-SELECTOR-HARDENING'
DISPLAY_VERSION='v2.2.8'
SOURCE_REVISION='v2.2.8-structured-mutation-selector-hardening'
AUTH_UID='USR-DIRECTIVE-20260919-STRUCTURED-MUTATION-SELECTOR-HARDENING-R1'
PACKAGE_FILENAME='AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.8_STRUCTURED_MUTATION_SELECTOR_HARDENING_LOCAL_VERIFIED.zip'
AUTH=ROOT/f'governance/test/spec_change_authorizations/{AUTH_UID}.yaml'
M3=SOURCE/'12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md'
M4=SOURCE/'12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md'
SECTION_REG=SOURCE/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'
SEMANTIC=SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'
REFERENCE_RULES=SOURCE/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'
SPEC_MUT=ROOT/'governance/specifications/current/SPECIFICATION_MUTATION_CONTROL.yaml'

M3_SECTION_UID='WEB-GOV-03-S070'
M3_HEADING='## 70. Structured Mutation Selector / Bounded Write-Set Safety'
M3_BODY="""Any mutation of a structured governance artifact, run-state artifact, registry, manifest, evidence record, structured Product/Project source, or executable source MUST resolve a bounded structural target before writing. The primary selector MUST be a typed identity, registered path, schema field, parser node, syntax-tree node, or exact registered section boundary that belongs to the Current Work Unit and canonical owner.

Whole-document raw text search, replacement, occurrence count, regular-expression match, or lexical token equality MAY be used only as a secondary diagnostic or precondition. It MUST_NOT be the primary write selector, and it MUST_NOT assert global uniqueness unless Current schema or Registry Authority explicitly guarantees uniqueness for that exact identity in that exact structural scope. Zero matches, ambiguous multiple candidates, cross-section matches, or selector drift MUST block before write; first-match, nearest-match, and silent fallback are forbidden.

Structured documents MUST be parsed successfully before mutation and reparsed after mutation. The executor MUST verify the selected node identity, required parent/sibling context, schema or required-field constraints, expected pre-write hash when applicable, exact write-set, and preservation of unrelated structural siblings. Semantic mutation of executable source MUST use a syntax-tree, concrete-syntax-tree, parser-backed, or equivalently bounded semantic selector; raw source spelling alone MUST_NOT define semantic identity.

After mutation, the executor MUST verify the exact intended structural delta, rerun affected reverse consumers, and prove that no unrelated Current owner, sibling node, denominator, reference, or execution state was changed. Selector ambiguity or parser failure is a mutation blocker, not permission to weaken the selector."""
M4_SECTION_UID='WEB-GOV-04-S084'
M4_HEADING='## 84. Structured Mutation Selector / Write-Set Integrity Audit'
M4_BODY="""Audit MUST prove every structured mutation selected its write target through a bounded structural identity rather than an unscoped whole-document lexical assumption. If uniqueness was relied on, Audit MUST identify the schema, Registry, or structural scope that guarantees that uniqueness; a raw token occurring once in one observed file is not uniqueness Authority.

Audit MUST verify successful parse before mutation and reparse after mutation; exact selected node identity and parent context; expected pre-write identity/hash when applicable; exact intended write-set; preservation of unrelated siblings and owners; and reverse-consumer revalidation for the changed structural identity. Zero-match and multi-match ambiguity MUST be shown to fail closed.

For executable-source semantic mutation, Audit MUST require syntax-tree, concrete-syntax-tree, parser-backed, or equivalently bounded semantic selection and MUST reject raw source spelling as the sole semantic identity. Destructive regression MUST include at least one case where the same legitimate lexical token appears in multiple structural scopes and prove the bounded selector changes only the authorized target without false global-uniqueness failure or cross-scope mutation.

A structured-mutation safety PASS is governance/test integrity evidence only and receives zero product completion or blocker-reduction credit unless independent fresh product-owner evidence changes the product denominator."""

def load_yaml(path:Path):
    data=yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(data,dict):
        raise RuntimeError(f'MAPPING_REQUIRED:{path}')
    return data

def dump_yaml(path:Path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(yaml.safe_dump(data,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')

def sha_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def sha(path:Path)->str:
    return sha_bytes(path.read_bytes())

def content_hash_yaml(data:dict)->str:
    tmp=copy.deepcopy(data)
    tmp.pop('content_hash',None)
    return sha_bytes(yaml.safe_dump(tmp,allow_unicode=True,sort_keys=True,width=180).encode())

def run(*args,cwd=ROOT):
    print('+',' '.join(map(str,args)))
    subprocess.run(args,cwd=cwd,check=True)

def parse_sections(text:str):
    lines=text.splitlines()
    sections=[]
    for i,line in enumerate(lines):
        if line.startswith('<!-- SECTION_UID: ') and line.endswith(' -->'):
            uid=line[len('<!-- SECTION_UID: '):-len(' -->')]
            if i+1>=len(lines) or not lines[i+1].startswith('## '):
                raise RuntimeError(f'SECTION_HEADING_MISSING:{uid}')
            sections.append((uid,i,lines[i+1]))
    if len([x[0] for x in sections])!=len(set(x[0] for x in sections)):
        raise RuntimeError('DUPLICATE_SECTION_UID_IN_MOTHER')
    return lines,sections

def append_mother_section(path:Path,uid:str,heading:str,body:str,expected_previous_uid:str):
    text=path.read_text(encoding='utf-8')
    lines,sections=parse_sections(text)
    if any(x[0]==uid for x in sections):
        raise RuntimeError(f'SECTION_ALREADY_EXISTS:{uid}')
    if not sections or sections[-1][0]!=expected_previous_uid:
        raise RuntimeError(f'LAST_SECTION_DRIFT:{path.name}:{sections[-1][0] if sections else "NONE"}')
    additions=['',f'<!-- SECTION_UID: {uid} -->',heading,'']+body.splitlines()
    path.write_text('\n'.join(lines+additions).rstrip()+'\n',encoding='utf-8')

def binding_hash(uid:str,document_id:str,path:str,heading:str)->str:
    return sha_bytes(f'{uid}\n{document_id}\n{path}\n{heading}\n'.encode())

def add_section_registry_entry(document_id:str,uid:str,number:str,title:str,heading:str,path:str):
    d=load_yaml(SECTION_REG)
    docs=d.get('documents')
    if not isinstance(docs,list):
        raise RuntimeError('SECTION_REGISTRY_DOCUMENTS_INVALID')
    matches=[x for x in docs if isinstance(x,dict) and x.get('document_id')==document_id]
    if len(matches)!=1:
        raise RuntimeError(f'SECTION_DOCUMENT_ID_COUNT:{document_id}:{len(matches)}')
    doc=matches[0]
    sections=doc.get('sections')
    if not isinstance(sections,list):
        raise RuntimeError(f'SECTION_LIST_INVALID:{document_id}')
    if any(x.get('section_uid')==uid for x in sections if isinstance(x,dict)):
        raise RuntimeError(f'SECTION_UID_ALREADY_REGISTERED:{uid}')
    if any(str(x.get('canonical_number'))==number for x in sections if isinstance(x,dict)):
        raise RuntimeError(f'SECTION_NUMBER_ALREADY_REGISTERED:{document_id}:{number}')
    sections.append({
      'section_uid':uid,'level':2,'canonical_number':number,'title':title,'heading':heading,
      'path':path,'binding_sha256':binding_hash(uid,document_id,path,heading),
    })
    d['governance_revision']=SOURCE_REVISION
    dump_yaml(SECTION_REG,d)

def update_python_string_assignments(path:Path,updates:dict[str,str]):
    source=path.read_text(encoding='utf-8')
    tree=ast.parse(source)
    lines=source.splitlines()
    found={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            name=node.targets[0].id
            if name in updates:
                if name in found:
                    raise RuntimeError(f'DUPLICATE_PY_ASSIGN:{path}:{name}')
                if node.lineno!=node.end_lineno:
                    raise RuntimeError(f'MULTILINE_PY_ASSIGN_UNSUPPORTED:{path}:{name}')
                found[name]=node.lineno-1
    missing=set(updates)-set(found)
    if missing:
        raise RuntimeError(f'PY_ASSIGN_MISSING:{path}:{sorted(missing)}')
    for name,idx in found.items():
        lines[idx]=f"{name} = {updates[name]!r}"
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')

def patch_current_spec_control():
    d=load_yaml(SPEC_MUT)
    d['schema_version']=max(int(d.get('schema_version') or 0),7)
    d['structured_mutation_selector_control']={
      'applies_to':['GOVERNANCE_POLICY','RUN_STATE','REGISTRY','MANIFEST','EVIDENCE','STRUCTURED_SOURCE','EXECUTABLE_SOURCE'],
      'typed_structural_selector_required':True,
      'whole_document_raw_text_primary_selector':'FORBIDDEN',
      'lexical_match_may_be_secondary_precondition_only':True,
      'global_uniqueness_claim_requires_schema_or_registry_guarantee':True,
      'zero_match':'BLOCK','ambiguous_multiple_match':'BLOCK','first_or_nearest_match_fallback':'FORBIDDEN',
      'parse_before_mutation':True,'reparse_after_mutation':True,'exact_write_set_required':True,
      'unrelated_sibling_preservation_required':True,
      'executable_semantic_mutation_requires_ast_cst_parser_or_equivalent_bounded_selector':True,
      'raw_source_spelling_is_semantic_authority':False,
      'impacted_reverse_consumer_revalidation_required':True,
      'governance_test_integrity_pass_product_stage_credit':0,
      'required_machine_gate':'governance/ci/validate_structured_mutation_safety.py',
    }
    dump_yaml(SPEC_MUT,d)

def update_reference_rule_bundles():
    ref=load_yaml(REFERENCE_RULES)
    bundles=ref.get('common_bundle_reference_rules') or {}
    required=[
      ('BUNDLE-GOV-CONSTRUCTION-BASE',M3_SECTION_UID),
      ('BUNDLE-GOV-AUDIT-BASE',M4_SECTION_UID),
    ]
    for bundle_uid,section_uid in required:
        b=bundles.get(bundle_uid)
        if not isinstance(b,dict) or not isinstance(b.get('exact_section_uids'),list):
            raise RuntimeError(f'REFERENCE_BUNDLE_MISSING:{bundle_uid}')
        if section_uid in b['exact_section_uids']:
            raise RuntimeError(f'REFERENCE_BUNDLE_SECTION_ALREADY_PRESENT:{bundle_uid}:{section_uid}')
        b['exact_section_uids'].append(section_uid)
    ref['governance_revision']=SOURCE_REVISION
    dump_yaml(REFERENCE_RULES,ref)

def update_source_revision_and_semantic():
    for path in sorted((SOURCE/'10_REGISTRY').glob('*.yaml')):
        d=load_yaml(path)
        if 'governance_revision' in d:
            d['governance_revision']=SOURCE_REVISION
            dump_yaml(path,d)
    update_reference_rule_bundles()
    sem=load_yaml(SEMANTIC)
    sem['governance_revision']=SOURCE_REVISION
    bundles=((sem.get('semantic_snapshot') or {}).get('common_bundle_reference_rules') or {})
    for bundle_uid,section_uid in [('BUNDLE-GOV-CONSTRUCTION-BASE',M3_SECTION_UID),('BUNDLE-GOV-AUDIT-BASE',M4_SECTION_UID)]:
        b=bundles.get(bundle_uid)
        if not isinstance(b,dict) or not isinstance(b.get('exact_section_uids'),list):
            raise RuntimeError(f'SEMANTIC_BUNDLE_MISSING:{bundle_uid}')
        if section_uid not in b['exact_section_uids']:
            b['exact_section_uids'].append(section_uid)
    sem['content_hash']=content_hash_yaml(sem)
    dump_yaml(SEMANTIC,sem)
    update_python_string_assignments(
      SOURCE/'09_TESTS/governance/validate_reference_semantics.py',
      {'SEMANTIC_BASELINE_CONTENT_HASH':sem['content_hash']},
    )
    return sem['content_hash']

def update_candidate_state():
    p=SOURCE/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'
    d=load_yaml(p)
    d['candidate']='v2.2.8_STRUCTURED_MUTATION_SELECTOR_HARDENING_CANDIDATE'
    fresh=d.setdefault('fresh_revalidation',{})
    fresh.update({
      'required':True,'current_source_revision':SOURCE_REVISION,'current_closure_credit':False,
      'predecessor_evidence_current_closure_credit':False,'persisted_head_full_line_required':True,
      'historical_evidence_may_close_successor':False,
    })
    dump_yaml(p,d)

def deterministic_hashes():
    checksum_path=SOURCE/'CHECKSUMS.sha256'
    files=sorted((p for p in SOURCE.rglob('*') if p.is_file() and p!=checksum_path),key=lambda p:p.relative_to(SOURCE).as_posix())
    if len(files)!=74:
        raise RuntimeError(f'CHECKSUM_TARGET_DENOMINATOR_DRIFT:{len(files)}')
    checksum_path.write_text(''.join(f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in files),encoding='utf-8')
    checksum=sha(checksum_path)
    identity=sorted(files+[checksum_path],key=lambda p:p.relative_to(SOURCE).as_posix())
    tb=io.BytesIO()
    with tarfile.open(fileobj=tb,mode='w',format=tarfile.PAX_FORMAT) as tf:
        for p in identity:
            rel=p.relative_to(SOURCE).as_posix()
            info=tf.gettarinfo(str(p),arcname=rel)
            info.uid=0; info.gid=0; info.uname=''; info.gname=''; info.mtime=0
            with p.open('rb') as fh:
                tf.addfile(info,fh)
    bundle=sha_bytes(lzma.compress(tb.getvalue(),format=lzma.FORMAT_XZ,preset=9))
    zb=io.BytesIO()
    with zipfile.ZipFile(zb,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for p in identity:
            rel=p.relative_to(SOURCE).as_posix()
            zi=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0))
            zi.compress_type=zipfile.ZIP_DEFLATED
            zi.create_system=3
            mode=0o755 if (p.stat().st_mode & 0o111) else 0o644
            zi.external_attr=(mode & 0xffff)<<16
            zf.writestr(zi,p.read_bytes())
    return checksum,bundle,sha_bytes(zb.getvalue())

def patch_identity_consumers(checksum:str,bundle:str,zhash:str,semantic_hash:str):
    update_python_string_assignments(
      ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py',
      {'EXPECTED_BUNDLE_SHA256':bundle,'EXPECTED_SOURCE_ZIP_SHA256':zhash},
    )
    update_python_string_assignments(
      ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py',
      {
        'EXPECTED_CHECKSUMS_SHA256':checksum,
        'EXPECTED_SEMANTIC_CONTENT_HASH':semantic_hash,
        'EXPECTED_SOURCE_ZIP_SHA256':zhash,
        'EXPECTED_BUNDLE_SHA256':bundle,
      },
    )

def update_scope(new_uid:str):
    p=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
    d=load_yaml(p)
    d['governance_uid']=new_uid
    d['predecessor_governance_uid']=OLD_UID
    d['fresh_revalidation_required']=True
    d['stage_exit_credit_allowed']=False
    tmp=copy.deepcopy(d); tmp.pop('content_hash',None)
    d['content_hash']=sha_bytes(json.dumps(tmp,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
    dump_yaml(p,d)

def patch_projectors(checksum:str,bundle:str,zhash:str,semantic_hash:str):
    p=ROOT/'governance/specifications/REGISTRY.yaml'
    d=load_yaml(p)
    old_active=copy.deepcopy(d.get('active_specification') or {})
    if old_active.get('governance_uid')!=OLD_UID:
        raise RuntimeError('REGISTRY_CURRENT_UID_DRIFT')
    d['immediate_predecessor']={
      'governance_uid':OLD_UID,'display_version':old_active.get('display_version'),
      'version_role':'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY',
      'status':'SUPERSEDED_HISTORY_ONLY_AFTER_STRUCTURED_MUTATION_SELECTOR_HARDENING',
    }
    active=d['active_specification']
    active['governance_uid']=NEW_UID
    active['display_version']=DISPLAY_VERSION
    aliases=active.setdefault('aliases',[])
    if 'structured-mutation-selector-hardening' not in aliases:
        aliases.append('structured-mutation-selector-hardening')
    active['status']='ACTIVE_CURRENT_GOVERNANCE'
    dump_yaml(p,d)

    p=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'
    d=load_yaml(p)
    d['artifact_uid']=NEW_UID
    d['display_version']=DISPLAY_VERSION
    sl=d.setdefault('source_lineage',{})
    sl.update({
      'predecessor_governance_uid':OLD_UID,'promotion_authorization_uid':AUTH_UID,
      'verified_package_filename':PACKAGE_FILENAME,'verified_package_sha256':zhash,
      'deterministic_source_bundle_sha256':bundle,'checksum_manifest_sha256':checksum,
      'semantic_authority_content_hash':semantic_hash,'verified_source_revision':SOURCE_REVISION,
      'source_bytes_changed_by_this_successor':True,'source_identity_reused_only_because_source_bytes_are_unchanged':False,
    })
    dump_yaml(p,d)

    p=ROOT/'GOVERNANCE_CURRENT.yaml'
    d=load_yaml(p)
    d['active_governance_uid']=NEW_UID
    d['display_version']=DISPLAY_VERSION
    si=d.setdefault('source_identity',{})
    si.update({
      'verified_package_sha256':zhash,'deterministic_source_bundle_sha256':bundle,
      'checksum_manifest_sha256':checksum,'semantic_authority_content_hash':semantic_hash,
      'verified_source_revision':SOURCE_REVISION,'source_bytes_changed_by_current_successor':True,
    })
    dump_yaml(p,d)

    update_scope(NEW_UID)

    p=ROOT/'governance/test/ACTIVE_STATE.yaml'
    a=load_yaml(p)
    a['specification_uid']=NEW_UID
    a['status']='GOVERNANCE_PROMOTED_STRUCTURED_MUTATION_HARDENING_PRODUCT_REVERIFY_REQUIRED'
    a['next_action']='FRESH_REVERIFY_CORE01_STAGE01_STAGE02_UNDER_CURRENT_GOVERNANCE'
    a['current_primary_task_layer']='GOVERNANCE_MAINTENANCE'
    a['current_primary_task_authorization_uid']=AUTH_UID
    a['current_primary_task_product_stage_credit']=0
    rc=a.setdefault('resume_control',{})
    rc.update({
      'current_resume_point':'POST_STRUCTURED_MUTATION_GOVERNANCE_PROMOTION_CORE01_REVERIFY_REQUIRED',
      'current_work_unit_uid':'WU-GOV-STRUCTURED-MUTATION-SELECTOR-HARDENING-001',
      'current_owner':'governance/ci/validate_structured_mutation_safety.py',
      'historical_stage2_results_are_current_state':False,
      'stage2_execution_requires_fresh_entry_resolution':True,
      'exact_next_action':'FRESH_REVERIFY_CORE01_STAGE01_STAGE02_UNDER_CURRENT_GOVERNANCE',
    })
    tr=a.setdefault('governance_revision_transition',{})
    tr.update({
      'predecessor_governance_uid':OLD_UID,'current_governance_uid':NEW_UID,
      'predecessor_attempt_preserved_as_historical_evidence':True,
      'predecessor_attempt_may_close_under_current_governance':False,
      'fresh_revalidation_required':True,
      'fresh_revalidation_scope':'CORE01_STAGE01_STAGE02_AND_AFFECTED_REUSABLE_CONSUMERS',
      'website_construction_remains_blocked':True,'deployment_remains_blocked':True,
    })
    attempt=a.get('stage02_active_attempt')
    if isinstance(attempt,dict):
        attempt['fresh_revalidation_required']=True
        attempt['closure_credit_under_current_governance']=False
    ex=a.setdefault('execution',{})
    s2=ex.setdefault('stage2',{})
    s2['revalidation_required_under_current_governance']=True
    s2['prior_results_authoritative_for_current_governance']=False
    s2['stage_exit_allowed']=False
    s3=ex.setdefault('stage3',{})
    s3['result']='NOT_EXECUTED'; s3['execution_started']=False; s3['stage_exit_allowed']=False
    ex['website_construction_allowed']=False; ex['deployment_allowed']=False
    proto=a.get('stage_execution_remediation_closure_protocol')
    if isinstance(proto,dict):
        proto['frozen_specification_uid']=NEW_UID
        proto['binding_status']='CURRENT_V2_2_8_PRODUCT_REVERIFY_REQUIRED'
    fl=a.setdefault('full_lifecycle_governance_system_test',{})
    fl.update({
      'deterministic_source_bundle_sha256':bundle,
      'persisted_head_revalidation_required':True,
      'full_line_github_result':'REVALIDATION_REQUIRED_AFTER_STRUCTURED_MUTATION_GOVERNANCE_PROMOTION',
      'terminal_run_conclusion':'REVALIDATION_REQUIRED',
      'terminal_result_credit_allowed':False,
    })
    a['structured_mutation_selector_successor']={
      'authorization_uid':AUTH_UID,'predecessor_governance_uid':OLD_UID,'current_governance_uid':NEW_UID,
      'source_revision':SOURCE_REVISION,'product_stage_credit':0,
      'mother_execution_rule_uid':M3_SECTION_UID,'mother_audit_rule_uid':M4_SECTION_UID,
      'status':'GOVERNANCE_PROMOTED_PRODUCT_REVERIFY_REQUIRED',
    }
    dump_yaml(p,a)

    p=ROOT/'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
    d=load_yaml(p)
    cur=d.setdefault('current_stage2_execution',{})
    cur['current_governance_uid']=NEW_UID
    cur['fresh_revalidation_required_under_current_governance']=True
    cur['closure_credit_under_current_governance']=False
    cur['stage_exit_allowed']=False
    cur['next_action']='FRESH_REVERIFY_CORE01_STAGE01_STAGE02_UNDER_CURRENT_GOVERNANCE'
    for f in d.get('findings') or []:
        if isinstance(f,dict) and f.get('finding_uid')=='FIND-20260919-006':
            f['blocking_state']='PROMOTED_REVALIDATION_REQUIRED'
            f['disposition']='CANONICAL_POLICY_PROMOTED_REVALIDATION_REQUIRED'
            f['formal_specification_mutated_for_fix']=True
            f['resolving_governance_uid']=NEW_UID
        if isinstance(f,dict) and f.get('finding_uid') in {'FIND-20260919-007','FIND-20260919-008','FIND-20260919-009'}:
            f['blocking_state']='RESOLVED_PRE_PROMOTION'
            f['disposition']='IMPLEMENTATION_REMEDIATED'
            f['resolving_governance_uid']=NEW_UID
    dump_yaml(p,d)

    p=ROOT/'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
    if p.is_file():
        d=load_yaml(p)
        d['current_governance_revalidation_required']=True
        d['closure_credit_under_current_governance']=False
        d['next_action']='FRESH_REVERIFY_CORE01_STAGE01_STAGE02_UNDER_CURRENT_GOVERNANCE'
        dump_yaml(p,d)

def validate_local():
    checks=[
      [ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py'],
      [ROOT/'governance/ci/governance_resolver.py'],
      [ROOT/'governance/ci/validate_canonical_rule_registry.py'],
      [ROOT/'governance/ci/validate_governance_portability.py'],
      [ROOT/'governance/ci/validate_validation_remediation_closure_protocol.py'],
      [SOURCE/'09_TESTS/governance/validate_section_registry.py'],
      [SOURCE/'09_TESTS/governance/validate_reference_semantics.py'],
      [ROOT/'governance/ci/validate_active_consumer_reference_integrity.py'],
      [ROOT/'governance/ci/validate_structured_mutation_safety.py'],
    ]
    for cmd in checks:
        run('python',str(cmd[0]))
    run('python',str(ROOT/'governance/ci/validate_structured_mutation_safety.py'),'--self-test')
    run('git','diff','--check')

def main():
    auth=load_yaml(AUTH)
    if auth.get('artifact_type')!='SPECIFICATION_CHANGE_AUTHORIZATION_RECEIPT' or auth.get('status')!='APPROVED_FOR_EXACT_SCOPE':
        raise RuntimeError('AUTHORIZATION_RECEIPT_INVALID')
    if auth.get('baseline_commit_sha')!='31833f1362a72337fc7923c3b1c4e76d3e50e1a4' or auth.get('baseline_tree_sha')!='fca75b2497ffdb2a84133fd6d28a1cba96b05628':
        raise RuntimeError('AUTHORIZATION_BASELINE_DRIFT')
    reg=load_yaml(ROOT/'governance/specifications/REGISTRY.yaml')
    if (reg.get('active_specification') or {}).get('governance_uid')!=OLD_UID:
        raise RuntimeError('CURRENT_GOVERNANCE_DRIFT')

    append_mother_section(
      M3,M3_SECTION_UID,M3_HEADING,M3_BODY,'WEB-GOV-03-S069'
    )
    append_mother_section(
      M4,M4_SECTION_UID,M4_HEADING,M4_BODY,'WEB-GOV-04-S083'
    )
    add_section_registry_entry(
      'WEB-GOV-03',M3_SECTION_UID,'70','Structured Mutation Selector / Bounded Write-Set Safety',
      M3_HEADING,'12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md'
    )
    add_section_registry_entry(
      'WEB-GOV-04',M4_SECTION_UID,'84','Structured Mutation Selector / Write-Set Integrity Audit',
      M4_HEADING,'12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md'
    )
    patch_current_spec_control()
    semantic_hash=update_source_revision_and_semantic()
    update_candidate_state()

    run('python',str(SOURCE/'09_TESTS/governance/compile_governance_baseline.py'),cwd=SOURCE/'09_TESTS/governance')
    run('python',str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'),cwd=SOURCE/'09_TESTS/governance')
    checksum,bundle,zhash=deterministic_hashes()
    patch_identity_consumers(checksum,bundle,zhash,semantic_hash)
    patch_projectors(checksum,bundle,zhash,semantic_hash)
    validate_local()

    print(json.dumps({
      'new_governance_uid':NEW_UID,'display_version':DISPLAY_VERSION,'source_revision':SOURCE_REVISION,
      'semantic_authority_content_hash':semantic_hash,'checksum_manifest_sha256':checksum,
      'deterministic_source_bundle_sha256':bundle,'deterministic_source_zip_sha256':zhash,
      'new_mother_sections':[M3_SECTION_UID,M4_SECTION_UID],'product_stage_credit':0,
    },ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
