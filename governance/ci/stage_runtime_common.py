#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, tempfile
from pathlib import Path
from typing import Any
import yaml

GOV_ROOT = Path(__file__).resolve().parents[2]
LIFECYCLE = GOV_ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
INVARIANTS = GOV_ROOT/'.github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'
REFERENCE_RULES = GOV_ROOT/'.github/governance-source/active/source/10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'
REGISTRY = GOV_ROOT/'governance/specifications/REGISTRY.yaml'
ADAPTERS = GOV_ROOT/'governance/ci/stage_execution_semantic_adapters.yaml'
ROOT_MANIFEST = GOV_ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'
ACCEPTANCE_BLUEPRINT = GOV_ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'

class RuntimeContractError(RuntimeError):
    pass

def fail(msg: str):
    raise RuntimeContractError(msg)

def execution_root(explicit: str|None=None) -> Path:
    raw=(explicit or os.environ.get('STAGE_EXECUTION_ROOT') or '').strip()
    root=Path(raw).resolve() if raw else GOV_ROOT
    if not root.is_dir(): fail('EXECUTION_ROOT_MISSING:'+str(root))
    return root

def load_yaml(path: Path) -> dict:
    if not path.is_file(): fail('MISSING_FILE:'+str(path))
    obj=yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(obj,dict): fail('MAPPING_REQUIRED:'+str(path))
    return obj

def load_json(path: Path) -> dict:
    if not path.is_file(): fail('MISSING_FILE:'+str(path))
    obj=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj,dict): fail('MAPPING_REQUIRED:'+str(path))
    return obj

def sha256_file(path: Path) -> str:
    if not path.is_file(): fail('HASH_TARGET_MISSING:'+str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sha256_obj(obj: Any) -> str:
    data=yaml.safe_dump(obj,sort_keys=True,allow_unicode=True).encode('utf-8')
    return hashlib.sha256(data).hexdigest()

def safe_ref(root: Path, ref: str) -> Path:
    rp=Path(str(ref or ''))
    if not ref or rp.is_absolute() or '..' in rp.parts: fail('INVALID_RELATIVE_REF:'+str(ref))
    out=(root/rp).resolve()
    try: out.relative_to(root.resolve())
    except ValueError: fail('REF_ESCAPES_ROOT:'+str(ref))
    return out

def atomic_text(path: Path, text: str):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as fh:
            fh.write(text); fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def atomic_yaml(path: Path, obj: dict):
    atomic_text(path,yaml.safe_dump(obj,sort_keys=False,allow_unicode=True))

def atomic_json(path: Path, obj: dict):
    atomic_text(path,json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=False)+'\n')

def governance_identity() -> tuple[dict,str]:
    reg=load_yaml(REGISTRY)
    ident=reg.get('governance_identity') or {}
    uid=str(ident.get('governance_uid') or '')
    if not uid: fail('CURRENT_GOVERNANCE_UID_MISSING')
    return reg,uid

def _stage_map(rows) -> dict:
    if isinstance(rows,dict): return {str(k):v for k,v in rows.items() if isinstance(v,dict)}
    out={}
    if isinstance(rows,list):
        for r in rows:
            if not isinstance(r,dict): continue
            uid=str(r.get('stage_uid') or r.get('uid') or '')
            if uid: out[uid]=r
    return out

def lifecycle_stages() -> tuple[dict,dict]:
    doc=load_yaml(LIFECYCLE)
    if isinstance(doc.get('stages'),(list,dict)):
        return doc,_stage_map(doc.get('stages'))
    raw=doc.get('profiles') or doc.get('execution_profiles') or {}
    if isinstance(raw,dict):
        for profile in raw.values():
            if isinstance(profile,dict) and isinstance(profile.get('stages'),(list,dict)):
                return doc,_stage_map(profile.get('stages'))
    fail('LIFECYCLE_STAGE_SET_UNRESOLVED')

def stage_definition(stage_uid: str) -> dict:
    _,stages=lifecycle_stages()
    if stage_uid not in stages: fail('UNKNOWN_STAGE:'+stage_uid)
    return stages[stage_uid]

def work_unit_context(stage_uid: str, work_unit_ref: str|None=None, root: Path|None=None):
    root=root or execution_root()
    ref=(work_unit_ref or os.environ.get('STAGE_ACTIVE_WORK_UNIT') or '').strip()
    if not ref: fail('STAGE_ACTIVE_WORK_UNIT_MISSING')
    wp=safe_ref(root,ref)
    work=load_yaml(wp)
    if str(work.get('stage_uid') or '')!=stage_uid: fail('WORK_UNIT_STAGE_DRIFT')
    scope_ref=(os.environ.get('STAGE_CURRENT_SCOPE') or '').strip()
    sp=safe_ref(root,scope_ref) if scope_ref else wp.parent/'CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
    scope=load_yaml(sp)
    state=load_yaml(wp.parent/'EXECUTION_STATE.yaml')
    uid=str(work.get('work_unit_uid') or '')
    if not uid or scope.get('work_unit_uid')!=uid or state.get('work_unit_uid')!=uid: fail('WORK_SCOPE_STATE_IDENTITY_DRIFT')
    return root,wp,work,sp,scope,wp.parent/'EXECUTION_STATE.yaml',state

def required_file(path: Path, label: str):
    if not path.is_file(): fail(label+'_MISSING:'+str(path))
    if path.stat().st_size<=0: fail(label+'_EMPTY:'+str(path))
    if path.suffix.lower() in {'.yaml','.yml'}: load_yaml(path)
    elif path.suffix.lower()=='.json': load_json(path)
    return path

def registered_output_paths(root: Path, work_dir: Path, work: dict, output_uid: str) -> list[Path]:
    """Resolve a lifecycle output to its registered physical artifact(s).

    The Current Normative Execution Matrix is authoritative for product-specific
    physical output placement. Top-level/OUTPUTS naming is only a compatibility
    fallback when no REQUIRED matrix row binds this output identity.
    """
    matrix_ref=str(work.get('normative_execution_matrix_ref') or '')
    paths=[]
    if matrix_ref:
        matrix_path=safe_ref(root,matrix_ref)
        matrix=load_yaml(matrix_path)
        rows=matrix.get('rows') or matrix.get('matrix_rows') or []
        if not isinstance(rows,list):
            fail('NORMATIVE_MATRIX_ROWS_INVALID')
        refs=[]
        for row in rows:
            if not isinstance(row,dict): continue
            if str(row.get('required_artifact_type') or '')!=str(output_uid): continue
            if str(row.get('applicability') or '')!='REQUIRED': continue
            ref=str(row.get('artifact_ref') or '').strip()
            if not ref: fail('REGISTERED_OUTPUT_ARTIFACT_REF_MISSING:'+str(output_uid))
            if ref not in refs: refs.append(ref)
        for ref in refs:
            p=safe_ref(root,ref)
            try: p.resolve().relative_to(work_dir.resolve())
            except ValueError: fail('REGISTERED_OUTPUT_ESCAPES_WORK_UNIT:'+str(output_uid)+':'+ref)
            required_file(p,'OUTPUT:'+str(output_uid))
            paths.append(p)
        if paths:
            return paths
    for p in (work_dir/(str(output_uid)+'.yaml'),work_dir/'OUTPUTS'/(str(output_uid)+'.yaml')):
        if p.is_file():
            required_file(p,'OUTPUT:'+str(output_uid))
            return [p]
    fail('REGISTERED_OUTPUT_BINDING_MISSING:'+str(output_uid))

def current_git_identity(root: Path) -> dict:
    import subprocess
    def run(*args):
        p=subprocess.run(['git','-C',str(root),*args],text=True,capture_output=True)
        return p.stdout.strip() if p.returncode==0 else ''
    return {'repository_root':str(root),'branch':run('rev-parse','--abbrev-ref','HEAD'),'head':run('rev-parse','HEAD'),'tree':run('rev-parse','HEAD^{tree}')}

def dependency_hashes(root: Path, work: dict) -> dict:
    out={}
    for row in work.get('dependencies') or []:
        ref=row if isinstance(row,str) else ((row.get('ref') or row.get('path') or row.get('source_ref')) if isinstance(row,dict) else '')
        if not ref: continue
        p=safe_ref(root,str(ref)); required_file(p,'DEPENDENCY')
        out[str(ref)]=sha256_file(p)
    return out
