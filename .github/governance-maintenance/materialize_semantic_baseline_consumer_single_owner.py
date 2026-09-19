#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import ast
import copy
import hashlib
import io
import json
import lzma
import re
import subprocess
import tarfile
import zipfile
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
GOVTEST=SOURCE/'09_TESTS/governance'
PROGRAM_GUARD=GOVTEST/'program_artifact_instance_guard.py'
SEMANTIC_VALIDATOR=GOVTEST/'validate_reference_semantics.py'
SEMANTIC_BASELINE=SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'
ROOT_MANIFEST=SOURCE/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'
OLD_UID='GOV-REV-20260919-STRUCTURED-MUTATION-SELECTOR-HARDENING'
NEW_UID='GOV-REV-20260919-SEMANTIC-BASELINE-CONSUMER-SINGLE-OWNER-HARDENING'
DISPLAY_VERSION='v2.2.9'
SOURCE_REVISION='v2.2.8-structured-mutation-selector-hardening-consumer-single-owner-r2'
AUTH_UID='USR-DIRECTIVE-20260919-SEMANTIC-BASELINE-CONSUMER-SINGLE-OWNER-R2'
AUTH=ROOT/f'governance/test/spec_change_authorizations/{AUTH_UID}.yaml'
PACKAGE_FILENAME='AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.9_SEMANTIC_BASELINE_CONSUMER_SINGLE_OWNER_LOCAL_VERIFIED.zip'
EXPECTED_SEMANTIC_HASH='446007aa22777d490ba50f04cc764232872a5d9a6f497a4c7e681bdf02d5d0e8'

def load_yaml(path:Path):
    d=yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(d,dict): raise RuntimeError('MAPPING_REQUIRED:'+str(path))
    return d

def dump_yaml(path:Path,d):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')

def sha_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def sha(path:Path)->str: return sha_bytes(path.read_bytes())

def run(*args,cwd=ROOT):
    print('+',' '.join(map(str,args)))
    subprocess.run(args,cwd=cwd,check=True)

def top_assignment(tree:ast.Module,name:str):
    out=[]
    for node in tree.body:
        if isinstance(node,ast.Assign):
            targets=node.targets
        elif isinstance(node,ast.AnnAssign):
            targets=[node.target]
        else:
            continue
        for target in targets:
            if isinstance(target,ast.Name) and target.id==name:
                out.append(node)
    return out

def patch_program_guard():
    src=PROGRAM_GUARD.read_text(encoding='utf-8')
    tree=ast.parse(src,filename=str(PROGRAM_GUARD))
    assigns=top_assignment(tree,'SEMANTIC_BASELINE_CONTENT_HASH')
    if len(assigns)!=1: raise RuntimeError(f'PROGRAM_GUARD_SEMANTIC_ASSIGNMENT_COUNT:{len(assigns)}')
    node=assigns[0]
    if not isinstance(node.value,ast.Constant) or node.value.value!='0c87e5c9a8d81cf608c270ae7298dd4d80735376eef63039671c38dbe580a590':
        raise RuntimeError('PROGRAM_GUARD_EXPECTED_STALE_HASH_NOT_FOUND')
    lines=src.splitlines()
    imports=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
    if not imports: raise RuntimeError('PROGRAM_GUARD_IMPORT_BLOCK_MISSING')
    if not any(isinstance(n,ast.Import) and any(a.name=='ast' for a in n.names) for n in imports):
        insert_at=max(n.end_lineno or n.lineno for n in imports)
        lines.insert(insert_at,'import ast')
        offset=1 if insert_at < node.lineno else 0
    else:
        offset=0
    start=node.lineno-1+offset
    end=(node.end_lineno or node.lineno)+offset
    replacement=[
      "def _resolve_semantic_baseline_content_hash():",
      "    owner=Path(__file__).resolve().parent/'validate_reference_semantics.py'",
      "    tree=ast.parse(owner.read_text(encoding='utf-8'),filename=str(owner))",
      "    values=[]",
      "    for candidate in tree.body:",
      "        targets=candidate.targets if isinstance(candidate,ast.Assign) else ([candidate.target] if isinstance(candidate,ast.AnnAssign) else [])",
      "        if any(isinstance(t,ast.Name) and t.id=='SEMANTIC_BASELINE_CONTENT_HASH' for t in targets):",
      "            value=getattr(candidate,'value',None)",
      "            if isinstance(value,ast.Constant) and isinstance(value.value,str): values.append(value.value)",
      "    if len(values)!=1 or not re.fullmatch(r'[0-9a-f]{64}',values[0]):",
      "        raise RuntimeError(f'SEMANTIC_BASELINE_LITERAL_OWNER_INVALID:{len(values)}')",
      "    return values[0]",
      "",
      "SEMANTIC_BASELINE_CONTENT_HASH=_resolve_semantic_baseline_content_hash()",
    ]
    lines[start:end]=replacement
    PROGRAM_GUARD.write_text('\n'.join(lines)+'\n',encoding='utf-8')

def patch_semantic_validator():
    src=SEMANTIC_VALIDATOR.read_text(encoding='utf-8')
    tree=ast.parse(src,filename=str(SEMANTIC_VALIDATOR))
    assigns=top_assignment(tree,'SEMANTIC_BASELINE_CONTENT_HASH')
    if len(assigns)!=1 or not isinstance(assigns[0].value,ast.Constant) or assigns[0].value.value!=EXPECTED_SEMANTIC_HASH:
        raise RuntimeError('CANONICAL_SEMANTIC_LITERAL_OWNER_DRIFT')
    lines=src.splitlines()
    imports=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
    if not any(isinstance(n,ast.Import) and any(a.name=='ast' for a in n.names) for n in imports):
        insert_at=max(n.end_lineno or n.lineno for n in imports)
        lines.insert(insert_at,'import ast')
    candidate='\n'.join(lines)+'\n'
    tree2=ast.parse(candidate,filename=str(SEMANTIC_VALIDATOR))
    validate_nodes=[n for n in tree2.body if isinstance(n,ast.FunctionDef) and n.name=='validate']
    if len(validate_nodes)!=1: raise RuntimeError('VALIDATE_FUNCTION_COUNT_DRIFT')
    validate_node=validate_nodes[0]
    first_failure=None
    for n in validate_node.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='failures' for t in n.targets):
            first_failure=n
            break
    if first_failure is None: raise RuntimeError('VALIDATE_FAILURES_INITIALIZER_MISSING')
    helper=[
      "def semantic_hash_literal_owner_errors(root=ROOT):",
      "    errors=[]; owners=[]",
      "    test_root=root/'09_TESTS/governance'",
      "    for path in sorted(test_root.glob('*.py')):",
      "        try: tree=ast.parse(path.read_text(encoding='utf-8'),filename=str(path))",
      "        except SyntaxError as exc:",
      "            errors.append(f'semantic_hash_owner_python_parse_failed:{path.name}:{exc.lineno}'); continue",
      "        for node in tree.body:",
      "            targets=node.targets if isinstance(node,ast.Assign) else ([node.target] if isinstance(node,ast.AnnAssign) else [])",
      "            if not any(isinstance(t,ast.Name) and t.id=='SEMANTIC_BASELINE_CONTENT_HASH' for t in targets): continue",
      "            value=getattr(node,'value',None)",
      "            if isinstance(value,ast.Constant) and isinstance(value.value,str): owners.append((path.name,value.value))",
      "    if owners!=[('validate_reference_semantics.py',SEMANTIC_BASELINE_CONTENT_HASH)]:",
      "        errors.append('semantic_baseline_literal_owner_not_exactly_one_canonical:'+repr(owners))",
      "    return errors",
      "",
    ]
    insert_idx=validate_node.lineno-1
    lines2=candidate.splitlines()
    lines2[insert_idx:insert_idx]=helper
    candidate2='\n'.join(lines2)+'\n'
    tree3=ast.parse(candidate2,filename=str(SEMANTIC_VALIDATOR))
    validate3=next(n for n in tree3.body if isinstance(n,ast.FunctionDef) and n.name=='validate')
    failure_line=None
    for n in validate3.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='failures' for t in n.targets):
            failure_line=n.end_lineno or n.lineno
            break
    if failure_line is None: raise RuntimeError('VALIDATE_FAILURES_INITIALIZER_MISSING_AFTER_HELPER')
    lines3=candidate2.splitlines()
    lines3.insert(failure_line,"    failures += semantic_hash_literal_owner_errors(root)")
    SEMANTIC_VALIDATOR.write_text('\n'.join(lines3)+'\n',encoding='utf-8')

def assert_single_owner():
    owners=[]
    for path in sorted(GOVTEST.glob('*.py')):
        tree=ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
        for node in tree.body:
            targets=node.targets if isinstance(node,ast.Assign) else ([node.target] if isinstance(node,ast.AnnAssign) else [])
            if any(isinstance(t,ast.Name) and t.id=='SEMANTIC_BASELINE_CONTENT_HASH' for t in targets):
                value=getattr(node,'value',None)
                if isinstance(value,ast.Constant) and isinstance(value.value,str): owners.append((path.name,value.value))
    if owners!=[('validate_reference_semantics.py',EXPECTED_SEMANTIC_HASH)]:
        raise RuntimeError('SINGLE_LITERAL_OWNER_ASSERTION_FAILED:'+repr(owners))
    print('PASS: verified-source semantic baseline literal owner exactly 1/1 canonical')

def refresh_source_identity():
    run('python',str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'),cwd=SOURCE/'09_TESTS/governance')
    cp=SOURCE/'CHECKSUMS.sha256'
    files=sorted((p for p in SOURCE.rglob('*') if p.is_file() and p!=cp),key=lambda p:p.relative_to(SOURCE).as_posix())
    if len(files)!=74: raise RuntimeError(f'CHECKSUM_TARGET_DENOMINATOR_DRIFT:{len(files)}')
    cp.write_text(''.join(f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in files),encoding='utf-8')
    checksum=sha(cp)
    identity=sorted(files+[cp],key=lambda p:p.relative_to(SOURCE).as_posix())
    tb=io.BytesIO()
    with tarfile.open(fileobj=tb,mode='w',format=tarfile.PAX_FORMAT) as tf:
        for p in identity:
            rel=p.relative_to(SOURCE).as_posix(); info=tf.gettarinfo(str(p),arcname=rel)
            info.uid=0; info.gid=0; info.uname=''; info.gname=''; info.mtime=0
            with p.open('rb') as fh: tf.addfile(info,fh)
    bundle=sha_bytes(lzma.compress(tb.getvalue(),format=lzma.FORMAT_XZ,preset=9))
    zb=io.BytesIO()
    with zipfile.ZipFile(zb,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for p in identity:
            rel=p.relative_to(SOURCE).as_posix(); zi=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0))
            zi.compress_type=zipfile.ZIP_DEFLATED; zi.create_system=3
            mode=0o755 if (p.stat().st_mode & 0o111) else 0o644; zi.external_attr=(mode&0xffff)<<16
            zf.writestr(zi,p.read_bytes())
    return checksum,bundle,sha_bytes(zb.getvalue())

def update_python_assignments(path:Path,updates:dict[str,str]):
    src=path.read_text(encoding='utf-8'); tree=ast.parse(src,filename=str(path)); lines=src.splitlines(); found={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in updates:
            name=node.targets[0].id
            if name in found or (node.end_lineno or node.lineno)!=node.lineno: raise RuntimeError('PY_ASSIGN_AMBIGUOUS:'+name)
            found[name]=node.lineno-1
    if set(found)!=set(updates): raise RuntimeError('PY_ASSIGN_MISSING:'+repr(sorted(set(updates)-set(found))))
    for name,idx in found.items(): lines[idx]=f"{name} = {updates[name]!r}"
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')

def patch_external_identity(checksum,bundle,zhash):
    update_python_assignments(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py',{
      'EXPECTED_BUNDLE_SHA256':bundle,'EXPECTED_SOURCE_ZIP_SHA256':zhash,
    })
    update_python_assignments(ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py',{
      'EXPECTED_CHECKSUMS_SHA256':checksum,'EXPECTED_SOURCE_ZIP_SHA256':zhash,'EXPECTED_BUNDLE_SHA256':bundle,
    })

def patch_projectors(checksum,bundle,zhash):
    regp=ROOT/'governance/specifications/REGISTRY.yaml'; reg=load_yaml(regp)
    old=copy.deepcopy(reg.get('active_specification') or {})
    if old.get('governance_uid')!=OLD_UID: raise RuntimeError('REGISTRY_UID_DRIFT')
    reg['immediate_predecessor']={'governance_uid':OLD_UID,'display_version':old.get('display_version'),'version_role':'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY','status':'SUPERSEDED_HISTORY_ONLY_AFTER_SEMANTIC_BASELINE_CONSUMER_SINGLE_OWNER_HARDENING'}
    reg['active_specification']['governance_uid']=NEW_UID; reg['active_specification']['display_version']=DISPLAY_VERSION
    aliases=reg['active_specification'].setdefault('aliases',[])
    if 'semantic-baseline-consumer-single-owner-hardening' not in aliases: aliases.append('semantic-baseline-consumer-single-owner-hardening')
    dump_yaml(regp,reg)

    mp=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'; man=load_yaml(mp)
    man['artifact_uid']=NEW_UID; man['display_version']=DISPLAY_VERSION
    sl=man.setdefault('source_lineage',{})
    sl.update({'predecessor_governance_uid':OLD_UID,'promotion_authorization_uid':AUTH_UID,'verified_package_filename':PACKAGE_FILENAME,'verified_package_sha256':zhash,'deterministic_source_bundle_sha256':bundle,'checksum_manifest_sha256':checksum,'semantic_authority_content_hash':EXPECTED_SEMANTIC_HASH,'verified_source_revision':SOURCE_REVISION,'source_bytes_changed_by_this_successor':True,'source_identity_reused_only_because_source_bytes_are_unchanged':False})
    dump_yaml(mp,man)

    cp=ROOT/'GOVERNANCE_CURRENT.yaml'; cur=load_yaml(cp)
    cur['active_governance_uid']=NEW_UID; cur['display_version']=DISPLAY_VERSION
    si=cur.setdefault('source_identity',{})
    si.update({'verified_package_sha256':zhash,'deterministic_source_bundle_sha256':bundle,'checksum_manifest_sha256':checksum,'semantic_authority_content_hash':EXPECTED_SEMANTIC_HASH,'verified_source_revision':SOURCE_REVISION,'source_bytes_changed_by_current_successor':True})
    dump_yaml(cp,cur)

    scopep=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'; scope=load_yaml(scopep)
    scope['predecessor_governance_uid']=OLD_UID; scope['governance_uid']=NEW_UID; scope['fresh_revalidation_required']=True; scope['stage_exit_credit_allowed']=False
    tmp=copy.deepcopy(scope); tmp.pop('content_hash',None)
    scope['content_hash']=sha_bytes(json.dumps(tmp,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
    dump_yaml(scopep,scope)

    statep=ROOT/'governance/test/ACTIVE_STATE.yaml'; state=load_yaml(statep)
    state['specification_uid']=NEW_UID
    state['status']='GOVERNANCE_SEMANTIC_BASELINE_SINGLE_OWNER_PROMOTED_FULL_LINE_REVERIFY_REQUIRED'
    state['next_action']='EXACT_HEAD_FULL_LINE_REVERIFY_THEN_FRESH_CORE01_STAGE01_STAGE02'
    state['current_primary_task_authorization_uid']=AUTH_UID
    proto=state.get('stage_execution_remediation_closure_protocol') or {}; proto['frozen_specification_uid']=NEW_UID; proto['binding_status']='CURRENT_V2_2_9_PRODUCT_REVERIFY_REQUIRED'; state['stage_execution_remediation_closure_protocol']=proto
    ex=state.get('execution') or {}; s2=ex.get('stage2') or {}; s2['stage_exit_allowed']=False; s2['revalidation_required_under_current_governance']=True; s2['prior_results_authoritative_for_current_governance']=False; ex['stage2']=s2; state['execution']=ex
    tr=state.get('governance_revision_transition') or {}; tr['predecessor_governance_uid']=OLD_UID; tr['current_governance_uid']=NEW_UID; tr['fresh_revalidation_required']=True; tr['fresh_revalidation_scope']='CORE01_STAGE01_STAGE02_AND_AFFECTED_REUSABLE_CONSUMERS'; state['governance_revision_transition']=tr
    rc=state.get('resume_control') or {}; rc['current_resume_point']='POST_SEMANTIC_BASELINE_SINGLE_OWNER_PROMOTION_FULL_LINE_REVERIFY'; rc['current_work_unit_uid']='WU-GOV-SEMANTIC-BASELINE-CONSUMER-SINGLE-OWNER-001'; rc['current_owner']='.github/governance-source/active/source/09_TESTS/governance/validate_reference_semantics.py'; rc['exact_next_action']='EXACT_HEAD_FULL_LINE_REVERIFY_THEN_FRESH_CORE01_STAGE01_STAGE02'; state['resume_control']=rc
    wu=state.get('active_work_unit') or {}; wu['current_status']='PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED'; wu['promoted_governance_uid']=NEW_UID; state['active_work_unit']=wu
    state['semantic_baseline_consumer_single_owner_successor']={'authorization_uid':AUTH_UID,'predecessor_governance_uid':OLD_UID,'current_governance_uid':NEW_UID,'semantic_hash':EXPECTED_SEMANTIC_HASH,'literal_owner_count':1,'canonical_literal_owner':'.github/governance-source/active/source/09_TESTS/governance/validate_reference_semantics.py','program_artifact_guard_resolver':'AST_BOUNDED_CANONICAL_OWNER_RESOLUTION','product_stage_credit':0,'status':'PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED'}
    fl=state.get('full_lifecycle_governance_system_test') or {}; fl['deterministic_source_bundle_sha256']=bundle; fl['persisted_head_revalidation_required']=True; fl['full_line_github_result']='REVALIDATION_REQUIRED_AFTER_SEMANTIC_BASELINE_CONSUMER_SINGLE_OWNER_PROMOTION'; fl['terminal_run_conclusion']='REVALIDATION_REQUIRED'; fl['terminal_result_credit_allowed']=False; state['full_lifecycle_governance_system_test']=fl
    dump_yaml(statep,state)

    candp=ROOT/'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'; cand=load_yaml(candp)
    cur2=cand.setdefault('current_stage2_execution',{}); cur2['current_governance_uid']=NEW_UID; cur2['fresh_revalidation_required_under_current_governance']=True; cur2['closure_credit_under_current_governance']=False; cur2['stage_exit_allowed']=False; cur2['next_action']='FRESH_CORE01_STAGE01_STAGE02_REVERIFY_AFTER_EXACT_HEAD_GOVERNANCE_PASS'
    for f in cand.get('findings') or []:
        if isinstance(f,dict) and f.get('finding_uid')=='FIND-20260919-014':
            f['blocking_state']='PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED'; f['disposition']='IMPLEMENTATION_REMEDIATED_PENDING_EXACT_HEAD_VALIDATION'; f['resolving_governance_uid']=NEW_UID
    dump_yaml(candp,cand)

def validate():
    checks=[
      ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py',
      ROOT/'governance/ci/governance_resolver.py',
      ROOT/'governance/ci/validate_governance_portability.py',
      ROOT/'governance/ci/validate_validation_remediation_closure_protocol.py',
      ROOT/'governance/ci/validate_active_consumer_reference_integrity.py',
      ROOT/'governance/ci/validate_structured_mutation_safety.py',
      SOURCE/'09_TESTS/governance/validate_reference_semantics.py',
      SOURCE/'09_TESTS/governance/program_artifact_instance_guard.py',
      ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py',
    ]
    for p in checks: run('python',str(p))
    run('python',str(ROOT/'governance/ci/validate_structured_mutation_safety.py'),'--self-test')
    run('git','diff','--check')

def main():
    auth=load_yaml(AUTH)
    if auth.get('status')!='APPROVED_FOR_EXACT_SCOPE' or auth.get('single_use') is not True: raise RuntimeError('AUTH_INVALID')
    if auth.get('baseline_commit_sha')!='52f1c3d1351eceda8a3554aafe3a9c60e3b10440' or auth.get('baseline_tree_sha')!='6efc9f7166d3f6422d0a56f272668a5b3142fcf5': raise RuntimeError('AUTH_BASELINE_DRIFT')
    if load_yaml(ROOT/'governance/specifications/REGISTRY.yaml').get('active_specification',{}).get('governance_uid')!=OLD_UID: raise RuntimeError('CURRENT_GOVERNANCE_DRIFT')
    if load_yaml(SEMANTIC_BASELINE).get('content_hash')!=EXPECTED_SEMANTIC_HASH: raise RuntimeError('SEMANTIC_BASELINE_HASH_DRIFT')
    patch_program_guard()
    patch_semantic_validator()
    assert_single_owner()
    checksum,bundle,zhash=refresh_source_identity()
    patch_external_identity(checksum,bundle,zhash)
    patch_projectors(checksum,bundle,zhash)
    validate()
    print(json.dumps({'new_governance_uid':NEW_UID,'display_version':DISPLAY_VERSION,'source_revision':SOURCE_REVISION,'semantic_hash_unchanged':EXPECTED_SEMANTIC_HASH,'checksum_manifest_sha256':checksum,'deterministic_source_bundle_sha256':bundle,'source_zip_sha256':zhash,'literal_semantic_hash_owner_count':1,'mother_changed':False,'product_stage_credit':0},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
