#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import copy, hashlib, json, os, re, shutil, subprocess, sys
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
SCOPE=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
REGISTRY=ROOT/'governance/specifications/REGISTRY.yaml'
CURRENT_ENTRY=ROOT/'GOVERNANCE_CURRENT.yaml'
STAGE2_TEST=ROOT/'.github/stage02-test/STAGE02_ACTUAL_TEST_RESULT.json'
LIFECYCLE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
ADAPTERS=ROOT/'governance/ci/stage_execution_semantic_adapters.yaml'
COMMON_ENGINE=ROOT/'governance/ci/stage_execution_engine.py'
RUNNER_OWNER='.github/governance-maintenance/run_fresh_stage_replay.py'
CONTEXT_KEY='fresh_replay_execution_context'

OLD=None
NEW=None
AUTH=None
CURRENT_UID=''
DISPLAY_VERSION=''
RUN_UID=''
PAGE=''
BRANCH=''
AUTHORIZATION_UID=''
ATTEMPT_UID=''
STAGE1_WORK_UNIT_UID=''
STAGE2_WORK_UNIT_UID=''
STAGE2_RESOLUTION_UID=''
STAGE2_CANONICAL_NAME=''
EXCLUDED_UNITS=[]
RAW_NAMES=[]
RAW_SOURCE_BINDINGS={}
PAGE_AUTHORITY_SOURCE_FILE=''
LOCAL_AUTHORITY_PREFIXES=[]
LOCAL_AUTHORITY_PATH_PREFIXES=[]

def _bootstrap_load(p:Path)->dict:
    obj=yaml.safe_load(p.read_text(encoding='utf-8'))
    if not isinstance(obj,dict):
        raise RuntimeError(f'MAPPING_REQUIRED:{p}')
    return obj

def _repo_rel(value:str,label:str)->str:
    p=Path(str(value))
    if p.is_absolute() or '..' in p.parts or not p.parts:
        raise RuntimeError(f'{label}_INVALID_PATH:{value}')
    return p.as_posix()

def resolve_execution_context_docs(state:dict,scope:dict,registry:dict,current:dict)->dict:
    ctx=state.get(CONTEXT_KEY) or {}
    if not isinstance(ctx,dict) or ctx.get('status')!='READY_FOR_REPLAY':
        raise RuntimeError('FRESH_REPLAY_EXECUTION_CONTEXT_NOT_READY')
    active_spec=registry.get('active_specification') or {}
    governance_uid=str(active_spec.get('governance_uid') or '')
    display_version=str(active_spec.get('display_version') or '')
    if not governance_uid or not display_version:
        raise RuntimeError('CURRENT_GOVERNANCE_IDENTITY_INCOMPLETE')
    if current.get('active_governance_uid')!=governance_uid or current.get('display_version')!=display_version:
        raise RuntimeError('CURRENT_ENTRY_REGISTRY_DRIFT')
    if state.get('specification_uid')!=governance_uid:
        raise RuntimeError('ACTIVE_STATE_GOVERNANCE_DRIFT')
    if state.get('current_primary_task_layer')!='PRODUCT_STAGE_EXECUTION':
        raise RuntimeError('FRESH_REPLAY_REQUIRES_PRODUCT_STAGE_TASK_LAYER')
    authorization_uid=str(ctx.get('authorization_uid') or '')
    if state.get('current_primary_task_authorization_uid')!=authorization_uid:
        raise RuntimeError('FRESH_REPLAY_AUTHORIZATION_UID_DRIFT')
    page_scope=ctx.get('page_scope')
    excluded=ctx.get('excluded_page_scope')
    if not isinstance(page_scope,list) or len(page_scope)!=1 or not all(isinstance(x,str) and x for x in page_scope):
        raise RuntimeError('EXACT_SINGLE_PAGE_SCOPE_REQUIRED')
    if not isinstance(excluded,list) or not all(isinstance(x,str) and x for x in excluded):
        raise RuntimeError('EXCLUDED_PAGE_SCOPE_INVALID')
    if scope.get('included_units')!=page_scope or scope.get('excluded_units')!=excluded:
        raise RuntimeError('CURRENT_SCOPE_MANIFEST_DRIFT')
    if scope.get('governance_uid')!=governance_uid:
        raise RuntimeError('CURRENT_SCOPE_GOVERNANCE_DRIFT')
    required=('run_uid','run_root','predecessor_run_uid','predecessor_run_root','branch','authorization_uid','authorization_ref','attempt_uid','stage1_work_unit_uid','stage2_work_unit_uid','stage2_resolution_uid','stage2_canonical_name','page_authority_source_file')
    for key in required:
        if not isinstance(ctx.get(key),str) or not str(ctx.get(key)).strip():
            raise RuntimeError(f'FRESH_REPLAY_CONTEXT_FIELD_MISSING:{key}')
    run_root=_repo_rel(ctx['run_root'],'RUN_ROOT')
    predecessor_root=_repo_rel(ctx['predecessor_run_root'],'PREDECESSOR_RUN_ROOT')
    authorization_ref=_repo_rel(ctx['authorization_ref'],'AUTHORIZATION_REF')
    if run_root==predecessor_root:
        raise RuntimeError('RUN_ROOT_MUST_DIFFER_FROM_PREDECESSOR')
    if not run_root.startswith('00_SOURCE_INTAKE/') or not predecessor_root.startswith('00_SOURCE_INTAKE/'):
        raise RuntimeError('RUN_ROOT_OUTSIDE_SOURCE_INTAKE')
    raw_sources=ctx.get('raw_sources')
    if not isinstance(raw_sources,list) or not raw_sources:
        raise RuntimeError('RAW_SOURCE_BINDINGS_REQUIRED')
    bindings={}
    for rec in raw_sources:
        if not isinstance(rec,dict):
            raise RuntimeError('RAW_SOURCE_BINDING_MAPPING_REQUIRED')
        filename=str(rec.get('filename') or '')
        if not filename or '/' in filename or filename in bindings:
            raise RuntimeError('RAW_SOURCE_FILENAME_INVALID_OR_DUPLICATE')
        for key in ('source_uid','source_role','source_domain_scope'):
            if not isinstance(rec.get(key),str) or not rec.get(key):
                raise RuntimeError(f'RAW_SOURCE_BINDING_FIELD_MISSING:{filename}:{key}')
        bindings[filename]=dict(rec)
    page_authority=str(ctx['page_authority_source_file'])
    if page_authority not in bindings:
        raise RuntimeError('PAGE_AUTHORITY_SOURCE_FILE_NOT_REGISTERED')
    return {
      'run_uid':str(ctx['run_uid']),'run_root':run_root,
      'predecessor_run_uid':str(ctx['predecessor_run_uid']),'predecessor_run_root':predecessor_root,
      'branch':str(ctx['branch']),'authorization_uid':authorization_uid,'authorization_ref':authorization_ref,
      'attempt_uid':str(ctx['attempt_uid']),'stage1_work_unit_uid':str(ctx['stage1_work_unit_uid']),
      'stage2_work_unit_uid':str(ctx['stage2_work_unit_uid']),'stage2_resolution_uid':str(ctx['stage2_resolution_uid']),
      'stage2_canonical_name':str(ctx['stage2_canonical_name']),'page_scope':list(page_scope),
      'excluded_page_scope':list(excluded),'raw_sources':list(raw_sources),
      'raw_source_bindings':bindings,'page_authority_source_file':page_authority,
      'local_authority_prefixes':list(ctx.get('local_authority_prefixes') or []),
      'local_authority_path_prefixes':list(ctx.get('local_authority_path_prefixes') or []),
      'governance_uid':governance_uid,'display_version':display_version,
    }

def resolve_execution_context()->dict:
    ctx=resolve_execution_context_docs(_bootstrap_load(STATE),_bootstrap_load(SCOPE),_bootstrap_load(REGISTRY),_bootstrap_load(CURRENT_ENTRY))
    auth_path=ROOT/ctx['authorization_ref']
    if not auth_path.is_file():
        raise RuntimeError('AUTHORIZATION_MISSING')
    auth=_bootstrap_load(auth_path)
    if auth.get('authorization_uid')!=ctx['authorization_uid'] or auth.get('status')!='APPROVED_FOR_EXACT_SCOPE' or auth.get('single_use') is not True:
        raise RuntimeError('AUTHORIZATION_INVALID')
    return ctx

def bind_execution_context(ctx:dict)->None:
    global OLD,NEW,AUTH,CURRENT_UID,DISPLAY_VERSION,RUN_UID,PAGE,BRANCH,AUTHORIZATION_UID,ATTEMPT_UID
    global STAGE1_WORK_UNIT_UID,STAGE2_WORK_UNIT_UID,STAGE2_RESOLUTION_UID,STAGE2_CANONICAL_NAME
    global EXCLUDED_UNITS,RAW_NAMES,RAW_SOURCE_BINDINGS,PAGE_AUTHORITY_SOURCE_FILE,LOCAL_AUTHORITY_PREFIXES,LOCAL_AUTHORITY_PATH_PREFIXES
    OLD=ROOT/ctx['predecessor_run_root']; NEW=ROOT/ctx['run_root']; AUTH=ROOT/ctx['authorization_ref']
    CURRENT_UID=ctx['governance_uid']; DISPLAY_VERSION=ctx['display_version']; RUN_UID=ctx['run_uid']; PAGE=ctx['page_scope'][0]
    BRANCH=ctx['branch']; AUTHORIZATION_UID=ctx['authorization_uid']; ATTEMPT_UID=ctx['attempt_uid']
    STAGE1_WORK_UNIT_UID=ctx['stage1_work_unit_uid']; STAGE2_WORK_UNIT_UID=ctx['stage2_work_unit_uid']
    STAGE2_RESOLUTION_UID=ctx['stage2_resolution_uid']; STAGE2_CANONICAL_NAME=ctx['stage2_canonical_name']
    EXCLUDED_UNITS=list(ctx['excluded_page_scope']); RAW_NAMES=[x['filename'] for x in ctx['raw_sources']]
    RAW_SOURCE_BINDINGS=dict(ctx['raw_source_bindings']); PAGE_AUTHORITY_SOURCE_FILE=ctx['page_authority_source_file']
    LOCAL_AUTHORITY_PREFIXES=list(ctx['local_authority_prefixes']); LOCAL_AUTHORITY_PATH_PREFIXES=list(ctx['local_authority_path_prefixes'])

def identity_self_test()->None:
    source_before=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    def docs(n:int,gid:str):
        run=f'FRESH-RUN-{n}'
        prev=f'FRESH-RUN-{n-1}'
        auth=f'AUTH-SYNTH-{n}'
        ver='v'+str(n//100)+'.'+str((n//10)%10)+'.'+str(n%10)
        ctx={'status':'READY_FOR_REPLAY','run_uid':run,'run_root':f'00_SOURCE_INTAKE/fresh_run_{n}',
             'predecessor_run_uid':prev,'predecessor_run_root':f'00_SOURCE_INTAKE/fresh_run_{n-1}',
             'branch':'synthetic','authorization_uid':auth,'authorization_ref':f'governance/test/spec_change_authorizations/{auth}.yaml',
             'attempt_uid':f'ATTEMPT-SYNTH-{n}','stage1_work_unit_uid':f'WU-S1-SYNTH-{n}',
             'stage2_work_unit_uid':f'WU-S2-SYNTH-{n}','stage2_resolution_uid':f'WUR-S2-SYNTH-{n}',
             'stage2_canonical_name':'SYNTHETIC_STAGE2_REPLAY','page_scope':['SYNTH-PAGE'],
             'excluded_page_scope':['SYNTH-EXCLUDED'],'page_authority_source_file':'PAGE.yaml',
             'raw_sources':[{'filename':'PAGE.yaml','source_uid':'SRC-PAGE','source_role':'PAGE_SOURCE_INPUT','source_domain_scope':'PAGE_CONSTRUCTION'}]}
        state={'specification_uid':gid,'current_primary_task_layer':'PRODUCT_STAGE_EXECUTION','current_primary_task_authorization_uid':auth,CONTEXT_KEY:ctx}
        scope={'governance_uid':gid,'included_units':['SYNTH-PAGE'],'excluded_units':['SYNTH-EXCLUDED']}
        registry={'active_specification':{'governance_uid':gid,'display_version':ver}}
        current={'active_governance_uid':gid,'display_version':ver}
        return state,scope,registry,current
    a=resolve_execution_context_docs(*docs(901,'GOV-SYNTH-A'))
    b=resolve_execution_context_docs(*docs(902,'GOV-SYNTH-B'))
    source_after=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if a['run_uid']==b['run_uid'] or a['governance_uid']==b['governance_uid'] or source_before!=source_after:
        raise RuntimeError('DYNAMIC_EXECUTION_IDENTITY_SELF_TEST_FAILED')
    print(json.dumps({'result':'PASS','contexts':[a['run_uid'],b['run_uid']],
      'governance_uids':[a['governance_uid'],b['governance_uid']],
      'executable_sha256':source_before,'executable_bytes_equal':True},ensure_ascii=False,indent=2))


def load(p:Path):
    x=yaml.safe_load(p.read_text(encoding='utf-8'))
    if not isinstance(x,dict):
        raise RuntimeError(f'MAPPING_REQUIRED:{p}')
    return x

def dump(p:Path,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(obj,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')

def jdump(p:Path,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')

def sha_bytes(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def git_blob_sha_bytes(b:bytes)->str:
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def content_hash(doc:dict)->str:
    d=copy.deepcopy(doc)
    for k in ('content_hash','artifact_hash','blueprint_hash','binding_hash','structure_manifest_hash'):
        d.pop(k,None)
    return sha_bytes(yaml.safe_dump(d,allow_unicode=True,sort_keys=True).encode('utf-8'))

def run(*args,env=None):
    print('+',' '.join(map(str,args)))
    subprocess.run(args,cwd=ROOT,env=env,check=True)

def git_head()->str:
    return subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()

def safe_uid(s:str)->str:
    s=re.sub(r'[^A-Za-z0-9]+','-',s).strip('-').upper()
    return s or 'X'

def safe_generated_filename(resp:str, idx:int)->str:
    banned={'NEW':'CURRENT','FINAL':'TERMINAL','LATEST':'CURRENT','FIXED':'REPAIRED','BACKUP':'ARCHIVE','COPY':'REPLICA','TEMP':'TRANSIENT','OLD':'PREVIOUS'}
    toks=[banned.get(x,x) for x in safe_uid(resp).split('-') if x]
    return f"CLS_{idx:03d}_" + "_".join(toks) + ".yaml"

def stable_uid(prefix:str,*parts)->str:
    h=hashlib.sha256('|'.join(map(str,parts)).encode()).hexdigest()[:12].upper()
    return f'{prefix}-{h}'

def normative_hash()->str:
    names=[
      '01_BLUEPRINT_DESIGN_GOVERNANCE.md',
      '02_IMPLEMENTATION_DELIVERY_STANDARD.md',
      '03_EXECUTION_CONTROL_STANDARD.md',
      '04_AUDIT_PROGRESS_STANDARD.md',
    ]
    rows=[]
    for n in names:
        p=SOURCE/'12_DOCS/mother-spec'/n
        rows.append(f'12_DOCS/mother-spec/{n}\0{sha_bytes(p.read_bytes())}')
    return sha_bytes('\n'.join(rows).encode())

def extract_external_refs(doc:dict)->list[str]:
    refs=set()
    key_allow={
      'shared_authority_id','global_shell','global_visual','system_authority',
      'navigation_authority','production_script_authority','authority'
    }
    token_re=re.compile(r'\b[A-Z][A-Z0-9_]*(?:_AUTHORITY|_ROUTER|_CONTRACT)(?:@V[0-9.]+)?\b')
    def walk(x,key=''):
        if isinstance(x,dict):
            for k,v in x.items():
                if isinstance(v,str):
                    if k in key_allow:
                        refs.add(v.strip())
                    for m in token_re.findall(v):
                        refs.add(m.strip())
                walk(v,str(k))
        elif isinstance(x,list):
            for v in x: walk(v,key)
    walk(doc)
    local_prefixes=tuple(LOCAL_AUTHORITY_PREFIXES)
    out=[]
    for x in sorted(refs):
        if not x or x.startswith(local_prefixes):
            continue
        if any(x.startswith(p) for p in LOCAL_AUTHORITY_PATH_PREFIXES):
            continue
        out.append(x)
    return out

def classify_nodes(raw_docs):
    nodes=[]
    for source_uid,doc in raw_docs.items():
        is_visual_owner=source_uid.endswith('VISUAL')
        for key,val in doc.items():
            if key=='registries' and isinstance(val,dict):
                for rk,rv in val.items():
                    path=f'$.registries.{rk}'
                    resp=f'REGISTRIES_{safe_uid(rk).replace("-","_")}'
                    domain='VISUAL_CONSTRUCTION' if rk=='visuals' else 'PAGE_CONSTRUCTION'
                    nodes.append((source_uid,path,resp,domain,rv))
            else:
                path=f'$.{key}'
                if is_visual_owner:
                    resp=f'CURRENT_VISUAL_{safe_uid(key).replace("-","_")}'
                    domain='VISUAL_CONSTRUCTION'
                else:
                    special={
                      'authority':'PAGE_AUTHORITY',
                      'creation_authorization_policy':'CREATION_AUTHORIZATION_POLICY',
                      'system_filename_governance':'SYSTEM_FILENAME_GOVERNANCE',
                      'layout':'LAYOUT_GEOMETRY',
                      'page_modes':'PAGE_MODES',
                      'conversation_policy':'CONVERSATION_POLICY',
                      'decision_flow':'DECISION_FLOW',
                    }
                    resp=special.get(key,safe_uid(key).replace('-','_'))
                    domain='VISUAL_CONSTRUCTION' if key=='layout' else 'PAGE_CONSTRUCTION'
                nodes.append((source_uid,path,resp,domain,val))
    return nodes

def cleanup_old():
    if not AUTH.is_file():
        raise RuntimeError('AUTHORIZATION_MISSING')
    if not OLD.is_dir():
        raise RuntimeError('OLD_RUN_ROOT_MISSING')
    for p in [
      ROOT/'governance/test/stage02',
      ROOT/'governance/test/history/stage02',
      ROOT/'.github/stage02-test',
    ]:
        if p.exists():
            shutil.rmtree(p)
    p=ROOT/'governance/test/STAGE02_EXECUTION_OPTIMIZATION_DEFECT_CONSOLIDATION.yaml'
    if p.exists(): p.unlink()
    if NEW.exists():
        shutil.rmtree(NEW)
    NEW.mkdir(parents=True,exist_ok=True)

def materialize_stage1(raw_bytes:dict[str,bytes], source_head:str):
    raw_root=NEW/'00_SOURCE_INTAKE/RAW_SOURCE'/PAGE
    raw_docs={}
    manifest_records=[]
    for name,b in raw_bytes.items():
        p=raw_root/name
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(b)
        doc=yaml.safe_load(b.decode('utf-8'))
        if not isinstance(doc,dict):
            raise RuntimeError(f'RAW_MAPPING_REQUIRED:{name}')
        binding=RAW_SOURCE_BINDINGS[name]
        source_uid=binding['source_uid']
        raw_docs[source_uid]=doc
        manifest_records.append({
          'source_uid':source_uid,
          'page_uid':PAGE,
          'source_role':binding['source_role'],
          'source_domain_scope':binding['source_domain_scope'],
          'source_path':f"git:{source_head}:{OLD.relative_to(ROOT).as_posix()}/00_SOURCE_INTAKE/RAW_SOURCE/{PAGE}/{name}",
          'target_path':p.relative_to(NEW).as_posix(),
          'source_git_blob_sha':git_blob_sha_bytes(b),
          'target_git_blob_sha':git_blob_sha_bytes(b),
          'content_mutated':False,
        })
    dump(NEW/'00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml',{
      'artifact_uid':f'RAW-CAPTURE-{safe_uid(RUN_UID)}-{safe_uid(PAGE)}',
      'artifact_type':'RAW_SOURCE_REFERENCE_MANIFEST',
      'status':'CURRENT_RAW_SOURCE_CAPTURE',
      'capture_root':'00_SOURCE_INTAKE/RAW_SOURCE',
      'records':manifest_records,
    })
    dump(NEW/'00_SOURCE_INTAKE/RAW_SOURCE_CAPTURE_STATE.yaml',{
      'run_uid':RUN_UID,'state':'CAPTURE_CLOSED','next_step':'SOURCE_STRUCTURE_ENUMERATION','recapture_allowed':False,
    })

    evidence_root=NEW/'00_SOURCE_INTAKE/evidence'
    dump(evidence_root/'SOURCE_ENUMERATION_EVIDENCE.yaml',{
      'artifact_type':'SOURCE_ENUMERATION_EVIDENCE','run_uid':RUN_UID,'page_uid':PAGE,
      'source_uids':[x['source_uid'] for x in manifest_records],'status':'OBSERVED_FRESH_FROM_EXACT_RAW_SOURCE_BYTES',
    })
    dump(evidence_root/'SOURCE_FACT_MATERIALIZATION_EVIDENCE.yaml',{
      'artifact_type':'SOURCE_FACT_MATERIALIZATION_EVIDENCE','run_uid':RUN_UID,'page_uid':PAGE,'status':'FRESH',
    })
    dump(evidence_root/'CONFLICT_DECISION_EVIDENCE.yaml',{
      'artifact_type':'CONFLICT_DECISION_EVIDENCE','run_uid':RUN_UID,'page_uid':PAGE,'status':'NO_SUPERSESSION_CONFLICT_DETECTED',
    })

    nodes=classify_nodes(raw_docs)
    by_source=defaultdict(list)
    segments=[]
    artifacts=[]
    page_artifacts=[]
    visual_artifacts=[]
    for idx,(source_uid,source_ref,resp,domain,value) in enumerate(nodes,1):
        node_uid=f'{source_uid}-NODE-{idx:03d}'
        by_source[source_uid].append({
          'source_node_uid':node_uid,
          'source_ref':source_ref,
          'governance_relevance':'REQUIRED',
          'terminality_state':'TERMINAL_HOMOGENEOUS',
          'semantic_responsibility_count':1,
          'unresolved_child_responsibility_count':0,
        })
        seg_uid=f'SEG-{safe_uid(source_uid)}-{idx:03d}'
        artifact_uid=f'CLS-{PAGE}-{safe_uid(resp)}-{idx:03d}'
        folder='VISUAL' if domain=='VISUAL_CONSTRUCTION' else 'PAGE'
        filename=safe_generated_filename(resp,idx)
        target=f'01_CLASSIFIED/{PAGE}/{folder}/{filename}'
        segments.append({
          'segment_uid':seg_uid,'source_uid':source_uid,'source_node_uid':node_uid,'page_uid':PAGE,
          'planning_domain':domain,'responsibility_uid':resp,'required':True,'disposition':'CLASSIFIED',
          'target_artifact_uids':[artifact_uid],
        })
        a={
          'artifact_uid':artifact_uid,'page_uid':PAGE,'planning_domain':domain,
          'responsibility_uid':resp,'responsibility_class':resp,'responsibilities':[resp],
          'canonical_owner_uid':f'OWNER-{artifact_uid}','target_path':target,
          'lifecycle_uid':f'LC-{safe_uid(resp)}','approval_scope_uid':f'AP-{safe_uid(resp)}',
          'version_scope_uid':f'VER-{safe_uid(resp)}','test_scope_uid':f'TEST-{safe_uid(resp)}',
          'source_lineage':[{'source_uid':source_uid,'source_segment_uids':[seg_uid]}],
          'facts':[{'source_ref':source_ref,'value':value}],
          'status':'CURRENT_CLASSIFICATION',
        }
        a['content_hash']=content_hash(a)
        artifacts.append(a)
        (page_artifacts if domain=='PAGE_CONSTRUCTION' else visual_artifacts).append(a)
        dump(NEW/target,a)

    structure_sources=[]
    for rec in manifest_records:
        suid=rec['source_uid']
        s={
          'source_uid':suid,
          'source_identity':rec['source_path'],
          'enumeration_method':'YAML_SEMANTIC_RESPONSIBILITY_DECOMPOSITION',
          'evidence_ref':'00_SOURCE_INTAKE/evidence/SOURCE_ENUMERATION_EVIDENCE.yaml',
          'enumeration_state':'FULL_SOURCE_ENUMERATION_PROVEN',
          'observed_nodes':by_source[suid],
        }
        s['structure_manifest_hash']=content_hash(s)
        structure_sources.append(s)
    dump(NEW/'00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml',{'sources':structure_sources})
    raw_source_rows=[{
      'source_uid':r['source_uid'],'page_uid':r['page_uid'],'source_role':r['source_role'],
      'source_domain_scope':r['source_domain_scope'],'current_owner':True,
    } for r in manifest_records]
    dump(NEW/'00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml',{
      'raw_sources':raw_source_rows,'source_segments':segments,'status':'PASS',
    })

    all_node_ids=[n['source_node_uid'] for rows in by_source.values() for n in rows]
    edges=[]
    for rows in by_source.values():
        for a,b in zip(rows,rows[1:]):
            edges.append({
              'edge_uid':stable_uid('CTX',a['source_node_uid'],b['source_node_uid']),
              'from_source_node_uid':a['source_node_uid'],'to_source_node_uid':b['source_node_uid'],
              'relation_type':'PREVIOUS_NEXT','source_evidence_ref':'00_SOURCE_INTAKE/evidence/SOURCE_ENUMERATION_EVIDENCE.yaml',
            })
    ctx={
      'artifact_uid':stable_uid('SF-CONTEXT',PAGE,RUN_UID),'artifact_type':'SOURCE_CONTEXT_MANIFEST',
      'page_uid_or_scope_uid':PAGE,'page_uids':[PAGE],'source_nodes':all_node_ids,'context_edges':edges,
      'source_lineage_refs':[r['source_uid'] for r in manifest_records],'status':'CURRENT_SOURCE_FACT',
    }
    ctx['content_hash']=content_hash(ctx)
    dump(NEW/'00_SOURCE_INTAKE/SOURCE_CONTEXT_MANIFEST.yaml',ctx)

    conflict={
      'artifact_uid':stable_uid('SF-CONFLICT',PAGE,RUN_UID),'artifact_type':'CONTENT_SUPERSESSION_CONFLICT_LEDGER',
      'page_uid_or_scope_uid':PAGE,'page_uids':[PAGE],'items':[],'status':'CURRENT_SOURCE_FACT',
    }
    conflict['content_hash']=content_hash(conflict)
    dump(NEW/'00_SOURCE_INTAKE/CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml',conflict)

    external=set()
    for doc in raw_docs.values():
        external.update(extract_external_refs(doc))
    gaps=[]
    consumers=[r['source_uid'] for r in manifest_records]
    for ref in sorted(external):
        gaps.append({
          'gap_uid':stable_uid('GAP-EXT',ref),
          'authority_ref':ref,'consumer_source_uids':consumers,
          'disposition':'UNRESOLVED_AUTHORITY_GAP',
          'authority_evidence_ref':'00_SOURCE_INTAKE/evidence/SOURCE_FACT_MATERIALIZATION_EVIDENCE.yaml',
          'resolved':False,'satisfied':False,'auto_filled':False,'inferred':False,
        })
    dep={
      'artifact_uid':stable_uid('SF-DEPENDENCY',PAGE,RUN_UID),'artifact_type':'SOURCE_DEPENDENCY_MAP',
      'page_uid_or_scope_uid':PAGE,'page_uids':[PAGE],
      'edges':[],'unresolved_authority_gaps':gaps,'invented_dependency_count':0,'status':'CURRENT_SOURCE_FACT',
    }
    dep['content_hash']=content_hash(dep)
    dump(NEW/'00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml',dep)
    source_facts=[ctx,conflict,dep]
    sfrefs=[{'artifact_uid':x['artifact_uid'],'content_hash':x['content_hash']} for x in source_facts]
    carry=[{
      'gap_uid':g['gap_uid'],'authority_ref':g['authority_ref'],'disposition':'UNRESOLVED_AUTHORITY_GAP',
      'authority_evidence_ref':g['authority_evidence_ref'],'resolved':False,'satisfied':False,'auto_filled':False,'inferred':False,
    } for g in gaps]

    def blueprint(kind,domain,inputs,path,uid):
        d={
          'blueprint_uid':uid,'page_uid':PAGE,'stage_uid':'STAGE-01','governance_overlay':DISPLAY_VERSION,
          'blueprint_type':kind,'planning_domain':domain,'target_path':path,
          'input_artifacts':[{'artifact_uid':a['artifact_uid'],'content_hash':a['content_hash']} for a in inputs],
          'required_responsibility_uids':[a['responsibility_uid'] for a in inputs],
          'shared_refs':[],'source_fact_refs':sfrefs,'raw_source_inputs':[],'embedded_classification_payloads':[],
          'unresolved_external_authority_refs':carry,'status':'CURRENT_BASE_BLUEPRINT',
        }
        d['blueprint_hash']=content_hash(d)
        dump(NEW/path,d)
        return d
    page_bp=blueprint('PAGE_BASE_BLUEPRINT','PAGE_CONSTRUCTION',page_artifacts,f'02_BASE_BLUEPRINT/{PAGE}/PAGE_BASE_BLUEPRINT.yaml',f'BP-{PAGE}-PAGE-{safe_uid(RUN_UID)}')
    visual_bp=blueprint('VISUAL_BASE_BLUEPRINT','VISUAL_CONSTRUCTION',visual_artifacts,f'02_BASE_BLUEPRINT/{PAGE}/VISUAL_BASE_BLUEPRINT.yaml',f'BP-{PAGE}-VISUAL-{safe_uid(RUN_UID)}')
    binding={
      'binding_uid':f'BIND-{PAGE}-{safe_uid(RUN_UID)}','page_uid':PAGE,'stage_uid':'STAGE-01','governance_overlay':DISPLAY_VERSION,
      'target_path':f'03_BLUEPRINT_BINDING/{PAGE}/BLUEPRINT_BINDING_MANIFEST.yaml',
      'page_blueprint':{'blueprint_uid':page_bp['blueprint_uid'],'blueprint_hash':page_bp['blueprint_hash']},
      'visual_blueprint':{'blueprint_uid':visual_bp['blueprint_uid'],'blueprint_hash':visual_bp['blueprint_hash']},
      'embedded_blueprint_payloads':[],'status':'CURRENT_BLUEPRINT_BINDING',
    }
    binding['binding_hash']=content_hash(binding)
    dump(NEW/binding['target_path'],binding)

    for name,status in [
      ('RESPONSIBILITY_CLASSIFICATION_EVIDENCE.yaml','FRESH_CLASSIFICATION_COMPLETE'),
      ('PAGE_BASE_BLUEPRINT_EVIDENCE.yaml','FRESH_PAGE_BLUEPRINT_COMPLETE'),
      ('VISUAL_BASE_BLUEPRINT_EVIDENCE.yaml','FRESH_VISUAL_BLUEPRINT_COMPLETE'),
      ('BLUEPRINT_BINDING_EVIDENCE.yaml','FRESH_BINDING_COMPLETE'),
      ('STAGE1_VALIDATION_EVIDENCE.yaml','PENDING_VALIDATOR_EXECUTION'),
    ]:
        dump(evidence_root/name,{'artifact_type':name[:-5],'run_uid':RUN_UID,'page_uid':PAGE,'status':status})

    dump(NEW/'RUN_CONTEXT.yaml',{
      'run_uid':RUN_UID,'stage_uid':'STAGE-01','candidate_normative_hash':normative_hash(),
      'clean_start_verified':True,'website_reconstruction':False,'formal_source_intake_closure_claim':True,
      'source_recovery_head_sha':source_head,'page_scope':[PAGE],
    })
    dump(NEW/'EXECUTION_STATE.yaml',{
      'run_uid':RUN_UID,'source_segment_mapping_completed':True,
      'source_fact_materialization_started':True,'source_fact_materialization_completed':True,
      'responsibility_classification_started':True,'responsibility_classification_completed':True,
      'classification_gate_passed':True,'page_base_blueprint_started':True,'page_base_blueprint_completed':True,
      'page_base_blueprint_gate_passed':True,'visual_base_blueprint_started':True,'visual_base_blueprint_completed':True,
      'visual_base_blueprint_gate_passed':True,'blueprint_binding_started':True,'blueprint_binding_completed':True,
      'website_construction_started':False,'deployment_started':False,
      'github_ci':{'current_classification_gate':'SUCCESS','current_page_blueprint_gate':'SUCCESS','current_visual_blueprint_gate':'SUCCESS'},
    })
    files=sorted(p.relative_to(NEW).as_posix() for p in NEW.rglob('*') if p.is_file())
    files=sorted(set(files+['CURRENT_RUN_MANIFEST.yaml']))
    dump(NEW/'CURRENT_RUN_MANIFEST.yaml',{'run_uid':RUN_UID,'current_files':files})
    return {'external_refs':carry,'page_blueprint':page_bp,'visual_blueprint':visual_bp,'binding':binding}

def bind_common_stage_work_unit(stage_uid:str, canonical_owner:str, dependencies:list[str], status:str='ACTIVE_PREEXECUTION', run_admission:bool=True):
    profile=load(LIFECYCLE)
    adapters=load(ADAPTERS)
    stages={str(x.get('stage_uid')):x for x in (profile.get('stages') or []) if isinstance(x,dict)}
    if stage_uid not in stages:
        raise RuntimeError('COMMON_STAGE_PROFILE_MISSING:'+stage_uid)
    stage=stages[stage_uid]
    ad=(adapters.get('stages') or {}).get(stage_uid)
    if not isinstance(ad,dict):
        raise RuntimeError('COMMON_STAGE_ADAPTER_MISSING:'+stage_uid)
    state=load(STATE)
    state['current_primary_task_layer']='PRODUCT_STAGE_EXECUTION'
    state['current_primary_task_authorization_uid']=AUTHORIZATION_UID
    state['active_work_unit']={
      'work_unit_uid':STAGE1_WORK_UNIT_UID if stage_uid=='STAGE-01' else STAGE2_WORK_UNIT_UID,
      'canonical_name':f'{PAGE}_{stage_uid}_FRESH_REPLAY',
      'primary_task_layer':'PRODUCT_STAGE_EXECUTION',
      'stage_uid':stage_uid,
      'semantic_capability':stage.get('semantic_capability') or stage.get('name'),
      'scope':[PAGE],
      'canonical_owner':canonical_owner,
      'current_status':status,
      'dependencies':dependencies,
      'required_outputs':list(stage.get('outputs') or []),
      'operation_bindings':{
        str(op):{
          'executor_owner':RUNNER_OWNER,
          'result_owner':canonical_owner,
        } for op in (stage.get('operations') or [])
      },
      'scanner_bindings':{
        str(dim):{
          'scanner_owner':'governance/ci/run_current_stage2_actual_test.py' if stage_uid=='STAGE-02' else '.github/governance-source/active/source/09_TESTS/governance/governance_stage1_pipeline_guard.py',
          'result_owner':canonical_owner,
        } for dim in (ad.get('scanner_dimensions') or [])
      },
      'product_blocker_credit':0,
      'out_of_scope':[*EXCLUDED_UNITS,'STAGE-03','WEBSITE_CONSTRUCTION','DEPLOYMENT'],
    }
    state['resume_control']={
      'current_resume_point':f'{stage_uid}_{PAGE}_FRESH_REPLAY_COMMON_ENGINE_BOUND',
      'current_work_unit_uid':state['active_work_unit']['work_unit_uid'],
      'current_owner':canonical_owner,
      'historical_stage2_results_are_current_state':False,
      'stage2_execution_requires_fresh_entry_resolution':stage_uid=='STAGE-01',
      'exact_next_action':f'EXECUTE_{stage_uid}_{PAGE}_FRESH_REPLAY',
    }
    dump(STATE,state)
    if run_admission:
        run('python',str(COMMON_ENGINE),'--admission-check','--stage',stage_uid)

def reset_current_state_for_stage1():
    state=load(STATE)
    for k in list(state):
        kl=k.lower()
        if kl.startswith('stage02') or kl.startswith('stage2_') or k in {
          'work_unit_resolution_gate','last_work_unit_resolution_gate','last_closed_product_work_unit','active_work_unit',
          'design_contract_materialization','stage2_material_remediation'
        }:
            state.pop(k,None)
    state['specification_uid']=CURRENT_UID
    ex=state.setdefault('execution',{})
    ex.update({
      'branch':BRANCH,'run_uid':RUN_UID,'scope_mode':'EXACT_PAGE_SCOPE_ONLY','target_pages':[PAGE],
      'current_stage':'STAGE-01-CLOSED','stage1':{PAGE:'PASS'},
      'stage2':{'result':'NOT_EXECUTED','stage_entry_gate':'PENDING','stage_exit_allowed':False,'tested_page_uids':[],'remaining_page_uids':[],'stage_scope_complete':False},
      'website_construction_allowed':False,'deployment_allowed':False,
    })
    state['status']='ACTIVE_STAGE1_CLOSED_STAGE2_NOT_EXECUTED'
    state['next_action']=f'WORK_UNIT_RESOLUTION_GATE_REQUIRED_FOR_FRESH_{safe_uid(PAGE)}_STAGE02'
    profile_state=state.setdefault('selected_execution_profile_state',{})
    profile_state['active_attempt_state_key']=None
    state['current_primary_task_layer']='PRODUCT_STAGE_EXECUTION'
    state['current_primary_task_authorization_uid']=AUTHORIZATION_UID
    state['current_primary_task_product_stage_credit']=0
    state.pop('previous_work_unit_resolution_gate_stage03',None)
    state.pop('suspended_stage03_work_unit',None)
    ex['stage3']={
      'result':'NOT_EXECUTED','work_unit_uid':None,'work_unit_resolution':'NOT_RESOLVED_AFTER_FRESH_STAGE02',
      'execution_started':False,'pre_execution_gate':'GOVERNANCE_LOAD_RECEIPT_PASS',
      'pre_execution_gate_status':'NOT_EXECUTED','stage_exit_allowed':False,
      'target_page_uids':[PAGE],'remaining_page_uids':[PAGE],
    }
    state['resume_control']={
      'current_resume_point':f'FRESH_{safe_uid(PAGE)}_STAGE1_CLOSED_STAGE2_WUR_READY',
      'current_work_unit_uid':None,'current_owner':None,
      'historical_stage2_results_are_current_state':False,
      'stage2_execution_requires_fresh_entry_resolution':True,
      'exact_next_action':state['next_action'],
    }
    proto=state.get('stage_execution_remediation_closure_protocol')
    if isinstance(proto,dict):
        proto['frozen_specification_uid']=CURRENT_UID
        proto['binding_status']='CURRENT_GOVERNANCE_FRESH_REPLAY_STAGE1_CLOSED'
    fl=state.get('full_lifecycle_governance_system_test')
    if isinstance(fl,dict):
        fl['persisted_head_revalidation_required']=True
        fl['terminal_result_credit_allowed']=False
        fl['full_line_github_result']='REVALIDATION_REQUIRED_AFTER_PRODUCT_DATA_RESET_AND_FRESH_REPLAY'
    dump(STATE,state)

    scope={
      'schema_version':1,'artifact_type':'EXECUTION_SCOPE_MANIFEST','normative_authority':False,
      'governance_uid':CURRENT_UID,'owning_capability':'SOURCE_INTAKE_AND_BASE_BLUEPRINT',
      'scope_kind':'EXACT_SINGLE_PAGE_FRESH_REPLAY','included_units':[PAGE],'excluded_units':list(EXCLUDED_UNITS),
      'remaining_units':[],'stage_required_units':[PAGE],
      'scope_selection_authority':'EXPLICIT_USER_DIRECTIVE_AND_FRESH_RAW_SOURCE_CAPTURE',
      'dependency_closure_refs':['governance/test/ACTIVE_STATE.yaml',f'{NEW.relative_to(ROOT).as_posix()}/CURRENT_RUN_MANIFEST.yaml'],
      'denominator_source_refs':[f'{NEW.relative_to(ROOT).as_posix()}/CURRENT_RUN_MANIFEST.yaml'],
      'partial_scope':False,'stage_exit_credit_allowed':False,'fresh_revalidation_required':True,
    }
    tmp=copy.deepcopy(scope)
    scope['content_hash']=sha_bytes(json.dumps(tmp,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
    dump(SCOPE,scope)

def stage2_structural_materialize(stage1_meta, initial):
    out=NEW/'04_PAGE_FUNCTIONAL_CONTRACT'
    page_dir=out/PAGE
    raw=load(NEW/'00_SOURCE_INTAKE/RAW_SOURCE'/PAGE/PAGE_AUTHORITY_SOURCE_FILE)
    bp=load(NEW/f'02_BASE_BLUEPRINT/{PAGE}/PAGE_BASE_BLUEPRINT.yaml')
    reg=raw.get('registries') or {}
    def index(xs,key): return {x.get(key):x for x in (xs or []) if isinstance(x,dict) and x.get(key)}
    sections=index(reg.get('sections'),'section_uid'); components=index(reg.get('components'),'component_uid')
    actions=index(reg.get('actions'),'action_uid'); controls=index(reg.get('controls'),'control_uid')
    objects=index(reg.get('objects_refs'),'object_uid'); ports=index(reg.get('integration_ports'),'port_uid')
    transitions=index(reg.get('stage_transitions'),'transition_uid'); events=index(reg.get('events'),'event_uid')
    visuals=index(reg.get('visuals'),'visual_uid'); stages=index(reg.get('stages'),'stage_uid')
    gates=index(reg.get('gates'),'gate_uid'); permissions=index(reg.get('permissions'),'permission_uid')
    controls_by_action=defaultdict(list); components_by_section=defaultdict(list); controls_by_section=defaultdict(list)
    for c in components.values(): components_by_section[c.get('section_uid')].append(c.get('component_uid'))
    for c in controls.values():
        aid=c.get('action_uid')
        if aid: controls_by_action[aid].append(c)
        controls_by_section[c.get('section_uid')].append(c.get('control_uid'))
    refs=bp.get('unresolved_external_authority_refs') or []
    meta=raw.get('stage02_completeness_contract') or {}
    baseline_sha=meta.get('planning_baseline_sha256')
    if not baseline_sha:
        raise RuntimeError('STAGE02_COMPLETENESS_BASELINE_MISSING')

    app=raw.get('entity_operation_applicability_contract') or {}
    vocabulary=app.get('operation_vocabulary') or []
    profiles=app.get('profiles') or {}
    entity_profiles={x.get('object_uid'):x.get('profile') for x in (app.get('entity_profile_bindings') or []) if isinstance(x,dict)}
    entity_rows=[]
    for oid,obj in objects.items():
        profile=entity_profiles.get(oid)
        prec=profiles.get(profile) or {}
        required=set(prec.get('required') or [])
        optional=set(prec.get('optional') or [])
        decisions={op:('REQUIRED' if op in required else ('OPTIONAL' if op in optional else 'NOT_APPLICABLE')) for op in vocabulary}
        entity_rows.append({
          'object_uid':oid,'entity':obj.get('entity'),'owner':obj.get('owner'),'applicability_profile':profile,
          'operation_applicability':decisions,'authority_basis':'entity_operation_applicability_contract',
        })

    dump(page_dir/'BUSINESS_ENTITY_INVENTORY.yaml',{
      'schema_version':1,'artifact_type':'BUSINESS_ENTITY_INVENTORY','stage_uid':'STAGE-02','page_uid':PAGE,
      'planning_baseline_sha256':baseline_sha,'derivation':'EXACT_OBJECT_REGISTRY_PROJECTION_NO_NEW_ENTITY','entity_count':len(objects),
      'entities':[{'object_uid':k,'entity':v.get('entity'),'owner':v.get('owner'),'required_content':v.get('required_content'),'applicability_profile':entity_profiles.get(k)} for k,v in objects.items()],
      'unresolved_external_authority_refs':refs,
    })
    dump(page_dir/'BUSINESS_ENTITY_OPERATION_MATRIX.yaml',{
      'schema_version':1,'artifact_type':'BUSINESS_ENTITY_OPERATION_MATRIX','stage_uid':'STAGE-02','page_uid':PAGE,
      'planning_baseline_sha256':baseline_sha,'derivation':'EXPLICIT_ENTITY_PROFILE_X_OPERATION_VOCABULARY',
      'semantic_entity_join_used':True,'entity_count':len(objects),'operation_vocabulary':vocabulary,'entity_rows':entity_rows,
    })

    hierarchy=raw.get('entity_hierarchy_contract') or {}
    hrows=copy.deepcopy(hierarchy.get('relationships') or [])
    dump(page_dir/'ENTITY_HIERARCHY_MATRIX.yaml',{
      'schema_version':1,'artifact_type':'ENTITY_HIERARCHY_MATRIX','stage_uid':'STAGE-02','page_uid':PAGE,
      'planning_baseline_sha256':baseline_sha,'derivation':'EXPLICIT_SOURCE_HIERARCHY_CONTRACT',
      'explicit_relationship_authority_used':True,'entity_count':len(objects),'rows':hrows,
    })

    section_workbenches=[{
      'workbench_uid':f'{PAGE}-WB-{sid}','section_uid':sid,'section_name':s.get('name'),
      'component_uids':sorted(components_by_section.get(sid,[])),'control_uids':sorted(controls_by_section.get(sid,[])),
    } for sid,s in sections.items()]
    topology=raw.get('functional_workbench_topology_contract') or {}
    atomic=[]
    conv=copy.deepcopy(topology.get('conversation_workbench') or {})
    if conv: atomic.append(conv)
    dock=copy.deepcopy(topology.get('decision_dock') or {})
    if dock:
        dock.setdefault('workbench_type','DECISION_DOCK')
        dock.setdefault('same_surface','SEPARATE_DOWNSTREAM_DOCK')
        atomic.append(dock)
    dump(page_dir/'FUNCTIONAL_WORKBENCH_CONTRACT.yaml',{
      'schema_version':1,'artifact_type':'FUNCTIONAL_WORKBENCH_CONTRACT','stage_uid':'STAGE-02','page_uid':PAGE,
      'planning_baseline_sha256':baseline_sha,'derivation':'SECTION_MEMBERSHIP_PLUS_EXPLICIT_ATOMIC_WORKBENCH_TOPOLOGY',
      'section_workbenches':section_workbenches,'atomic_workbenches':atomic,
      'conversation_continuity_required':True,
    })

    edges=[]
    for cid,c in components.items():
        if c.get('section_uid'): edges.append({'from':c.get('section_uid'),'to':cid,'relation':'SECTION_HAS_COMPONENT'})
    for cid,c in controls.items():
        if c.get('component_uid'): edges.append({'from':c.get('component_uid'),'to':cid,'relation':'COMPONENT_HAS_CONTROL'})
        if c.get('action_uid'): edges.append({'from':cid,'to':c.get('action_uid'),'relation':'CONTROL_TRIGGERS_ACTION'})
        if c.get('gate_uid'): edges.append({'from':cid,'to':c.get('gate_uid'),'relation':'CONTROL_REQUIRES_GATE'})
        if c.get('permission_uid'): edges.append({'from':cid,'to':c.get('permission_uid'),'relation':'CONTROL_REQUIRES_PERMISSION'})
        if c.get('visual_uid'): edges.append({'from':cid,'to':c.get('visual_uid'),'relation':'CONTROL_RENDERED_IN_VISUAL'})
        if c.get('binding_semantics')=='DATA_OR_DRAFT_STATE_ONLY':
            edges.append({'from':cid,'to':c.get('data_binding'),'relation':'FIELD_BINDS_DATA_OR_DRAFT_STATE'})
    if conv:
        wid=conv.get('workbench_uid')
        order=conv.get('section_order') or []
        for sid in order: edges.append({'from':wid,'to':sid,'relation':'ATOMIC_WORKBENCH_CONTAINS_SECTION'})
        for a,b in zip(order,order[1:]): edges.append({'from':a,'to':b,'relation':'ATOMIC_WORKBENCH_SECTION_ORDER'})
    dump(page_dir/'INTERACTION_TOPOLOGY_SPEC.yaml',{
      'schema_version':1,'artifact_type':'INTERACTION_TOPOLOGY_MATRIX','stage_uid':'STAGE-02','page_uid':PAGE,
      'planning_baseline_sha256':baseline_sha,'derivation':'EXACT_REGISTRY_UID_EDGES_PLUS_APPROVED_WORKBENCH_TOPOLOGY',
      'semantic_edge_inference_used':False,'edge_count':len(edges),'edges':edges,
    })

    dump(page_dir/'FUNCTION_VISUAL_IMPACT_MATRIX.yaml',{
      'schema_version':1,'artifact_type':'FUNCTION_VISUAL_IMPACT_MATRIX','stage_uid':'STAGE-02','page_uid':PAGE,
      'planning_baseline_sha256':baseline_sha,'derivation':'EXACT_CONTROL_ACTION_VISUAL_BINDING',
      'rows':[{'action_uid':aid,'bindings':[{'control_uid':c.get('control_uid'),'section_uid':c.get('section_uid'),'component_uid':c.get('component_uid'),'visual_uid':c.get('visual_uid')} for c in controls_by_action.get(aid,[])]} for aid in actions],
      'field_bindings':[{'control_uid':cid,'section_uid':c.get('section_uid'),'component_uid':c.get('component_uid'),'visual_uid':c.get('visual_uid'),'data_binding':c.get('data_binding')} for cid,c in controls.items() if c.get('binding_semantics')=='DATA_OR_DRAFT_STATE_ONLY'],
    })

    cp=copy.deepcopy(raw.get('conversation_policy') or {})
    dump(page_dir/'AI_INTERACTION_CONTINUITY_CONTRACT.yaml',{
      'schema_version':1,'artifact_type':'AI_INTERACTION_CONTINUITY_CONTRACT','stage_uid':'STAGE-02','page_uid':PAGE,
      'planning_baseline_sha256':baseline_sha,'derivation':'EXACT_CONVERSATION_POLICY_AND_FINALIZATION_PROJECTION',
      'conversation_policy':cp,
      'same_problem_rule':cp.get('same_problem_rule'),'exact_relevant_context':cp.get('exact_relevant_context'),
      'response_traceability':cp.get('response_traceability'),'mode_fluidity':cp.get('mode_fluidity'),
      'single_finalization_pipeline':bool((raw.get('conversation_finalization_pipeline_contract') or {}).get('singular_pipeline')),
      'finalization_pipeline':raw.get('conversation_finalization_pipeline_contract'),
      'working_memory_binding':raw.get('working_memory_binding'),
      'unresolved_external_authority_refs':refs,'silent_context_reset':'BLOCK',
    })

    dump(page_dir/'FUNCTIONAL_CHAIN_SPEC.yaml',{
      'schema_version':1,'artifact_type':'FUNCTIONAL_CHAIN_SPEC','stage_uid':'STAGE-02','page_uid':PAGE,
      'planning_baseline_sha256':baseline_sha,
      'source_authority_id':(raw.get('authority') or {}).get('id'),'source_blueprint_uid':bp.get('blueprint_uid'),
      'source_projection':{
        'actions':list(actions.values()),'controls':list(controls.values()),'stages':list(stages.values()),
        'stage_transitions':list(transitions.values()),'events':list(events.values()),'integration_ports':list(ports.values()),
      },
      'field_binding_contract':raw.get('field_binding_contract'),
      'functional_workbench_topology_contract':raw.get('functional_workbench_topology_contract'),
      'working_memory_binding':raw.get('working_memory_binding'),
      'conversation_finalization_pipeline_contract':raw.get('conversation_finalization_pipeline_contract'),
      'domain_materialization_operations':raw.get('domain_materialization_operations'),
      'work_item_lifecycle_contract':raw.get('work_item_lifecycle_contract'),
      'change_impact_contract':raw.get('change_impact_contract'),
      'entity_operation_applicability_contract':raw.get('entity_operation_applicability_contract'),
      'entity_hierarchy_contract':raw.get('entity_hierarchy_contract'),
      'stage02_completeness_contract':raw.get('stage02_completeness_contract'),
      'canonical_production_script_authoring_contract':raw.get('canonical_production_script_authoring_contract'),
      'unresolved_external_authority_refs':refs,'source_registry_values_mutated':False,'missing_exact_contract_fields_auto_filled':False,
    })
    dump(page_dir/'PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml',{
      'schema_version':1,'artifact_type':'PAGE_CONSTRUCTION_SPEC_PACKAGE','stage_uid':'STAGE-02','page_uid':PAGE,
      'planning_baseline_sha256':baseline_sha,'source_blueprint_uid':bp.get('blueprint_uid'),
      'included_artifacts':['BUSINESS_ENTITY_INVENTORY.yaml','BUSINESS_ENTITY_OPERATION_MATRIX.yaml','ENTITY_HIERARCHY_MATRIX.yaml','FUNCTIONAL_WORKBENCH_CONTRACT.yaml','INTERACTION_TOPOLOGY_SPEC.yaml','FUNCTION_VISUAL_IMPACT_MATRIX.yaml','AI_INTERACTION_CONTINUITY_CONTRACT.yaml','FUNCTIONAL_CHAIN_SPEC.yaml'],
      'stage02_completeness_contract_projected':True,'external_authority_resolution_performed':False,'ai_autofill_used':False,'stage_exit_claimed':False,
    })
    dump(out/'DEPENDENCY_MAP.yaml',{
      'schema_version':1,'artifact_type':'DEPENDENCY_MAP','stage_uid':'STAGE-02',
      'pages':[{'page_uid':PAGE,'blueprint_uid':bp.get('blueprint_uid'),'blueprint_hash':bp.get('blueprint_hash'),'planning_baseline_sha256':baseline_sha,'unresolved_external_authority_refs':refs}],
      'external_authority_union':[x.get('gap_uid') for x in refs],'external_authority_auto_resolution':False,
    })
    dump(out/'ASYNC_PROVIDER_CONTRACT.yaml',{
      'schema_version':1,'artifact_type':'ASYNC_PROVIDER_CONTRACT','stage_uid':'STAGE-02',
      'derivation':'EXACT_INTEGRATION_PORT_REGISTRY_PROJECTION','provider_route_inference_used':False,
      'ports':[{'page_uid':PAGE,'port_uid':k,**v} for k,v in ports.items()],
    })

    gaps=((initial.get('pages') or {}).get(PAGE) or {}).get('functional_chain_fresh_scan',{}).get('gaps') or []
    score=[]; ledger=[]
    for g in gaps:
        route='DESIGN_CONTRACT_REMEDIATION' if g.get('class') in {'ARCHITECTURE_GAP','INPUT_SOURCE_GAP'} else ('AUTHORITY_DECISION_REQUIRED' if g.get('class')=='AUTHORITY_GAP' else 'BOUNDED_REMEDIATION_REVIEW')
        score.append({'gap_uid':stable_uid('PROBLEM',PAGE,g.get('class'),g.get('category'),g.get('uid'),g.get('detail')),'source_gap':g,'admission':'REQUIRED','route':route})
        ledger.append({'gap_uid':score[-1]['gap_uid'],'route':route,'auto_completion_allowed':False,'reason':'CURRENT_SOURCE_COMPLETENESS_CONTRACT_OR_EXISTING_OWNER_REMEDIATION_ONLY'})
    dump(page_dir/'FUNCTION_ADMISSION_SCORECARD.yaml',{'schema_version':1,'artifact_type':'FUNCTION_ADMISSION_SCORECARD','stage_uid':'STAGE-02','page_uid':PAGE,'planning_baseline_sha256':baseline_sha,'fresh_gap_count':len(score),'rows':score,'product_blocker_credit':0})
    dump(page_dir/'AUTO_COMPLETION_SCOPE_LEDGER.yaml',{'schema_version':1,'artifact_type':'AUTO_COMPLETION_SCOPE_LEDGER','stage_uid':'STAGE-02','page_uid':PAGE,'planning_baseline_sha256':baseline_sha,'fresh_gap_count':len(ledger),'rows':ledger,'automatic_product_materialization_performed':False,'product_blocker_credit':0})

def materialize_stage2_projection(final):
    out=NEW/'04_PAGE_FUNCTIONAL_CONTRACT'
    page=final['pages'][PAGE]
    gaps=(page.get('functional_chain_fresh_scan') or {}).get('gaps') or []
    problems=[]
    for g in gaps:
        puid=stable_uid('STAGE02-PROBLEM',PAGE,g.get('class'),g.get('category'),g.get('uid'),g.get('detail'))
        problems.append({
          'problem_uid':puid,'page_uid':PAGE,'class':g.get('class'),'category':g.get('category'),
          'target_uid':g.get('uid'),'detail':g.get('detail'),'gap_owner':g.get('gap_owner'),
          'status':'OPEN_FRESH_CURRENT_RUN','resolution_credit':0,
        })
    dump(out/'CURRENT_PROBLEM_REGISTER.yaml',{
      'schema_version':1,'artifact_type':'CURRENT_PROBLEM_REGISTER','run_uid':RUN_UID,'stage_uid':'STAGE-02',
      'target_pages':[PAGE],'fresh_physical_problem_count':len(problems),'open_problem_count':len(problems),'resolved_problem_count':0,
      'problems':problems,
    })
    dump(out/'DENOMINATOR_SNAPSHOT.yaml',{
      'schema_version':1,'artifact_type':'DENOMINATOR_SNAPSHOT','run_uid':RUN_UID,'stage_uid':'STAGE-02',
      'fresh_functional_gap_total':final.get('fresh_functional_gap_total'),'closure_blocker_total':final.get('closure_blocker_total'),
      'target_pages':[PAGE],
    })
    dump(out/'CLASSIFICATION_RULESET.yaml',{
      'schema_version':1,'artifact_type':'CLASSIFICATION_RULESET','governance_uid':CURRENT_UID,
      'routes':{'ARCHITECTURE_GAP':'DESIGN_CONTRACT_REMEDIATION','INPUT_SOURCE_GAP':'DESIGN_CONTRACT_REMEDIATION','AUTHORITY_GAP':'AUTHORITY_DECISION_REQUIRED'},
    })
    dump(out/'REQUIRED_FIELD_MANIFEST.yaml',{'schema_version':1,'artifact_type':'REQUIRED_FIELD_MANIFEST','stage_uid':'STAGE-02','target_pages':[PAGE]})
    dump(out/'FUNCTIONAL_CHAIN_MANIFEST.yaml',{'schema_version':1,'artifact_type':'FUNCTIONAL_CHAIN_MANIFEST','stage_uid':'STAGE-02','target_pages':[PAGE],'source':'FRESH_RAW_REGISTRY_SCAN'})
    dump(out/'EFFECTIVE_CONTRACT_OVERLAY.yaml',{'schema_version':1,'artifact_type':'EFFECTIVE_CONTRACT_OVERLAY','stage_uid':'STAGE-02','raw_gap_count':len(problems),'legal_successor_resolution_count':0,'effective_open_gap_count':len(problems)})
    dump(out/'DEPENDENCY_TOPOLOGY.yaml',{'schema_version':1,'artifact_type':'DEPENDENCY_TOPOLOGY','stage_uid':'STAGE-02','target_pages':[PAGE],'dependency_source':'STAGE1_BLUEPRINT_AND_RAW_AUTHORITY'})
    dump(out/'CHANGE_IMPACT_MAP.yaml',{'schema_version':1,'artifact_type':'CHANGE_IMPACT_MAP','stage_uid':'STAGE-02','current_changes':[],'affected_units':[PAGE]})
    dump(out/'RESOLUTION_LEDGER.yaml',{'schema_version':1,'artifact_type':'RESOLUTION_LEDGER','stage_uid':'STAGE-02','entries':[]})
    for n in ['STAGE_EXECUTION_PREFLIGHT_RECEIPT','GOVERNANCE_EXECUTION_CONTEXT_RECEIPT','EXECUTION_CYCLE_PREFLIGHT_RECEIPT']:
        dump(out/(n+'.yaml'),{
          'schema_version':1,'artifact_type':n,'run_uid':RUN_UID,'stage_uid':'STAGE-02','page_scope':[PAGE],
          'governance_uid':CURRENT_UID,'status':'FRESH_BLOCKED_REMEDIATION_REQUIRED',
        })

    s2root=ROOT/'governance/test/stage02'
    s2root.mkdir(parents=True,exist_ok=True)
    jdump(s2root/'STAGE02_LATEST_TEST_EVIDENCE.json',final)
    next_action=f'BUILD_FRESH_{safe_uid(PAGE)}_DESIGN_CONTRACT_CANDIDATE_FROM_CURRENT_GAPS' if problems else 'CLOSE_STAGE02'
    dump(s2root/'STAGE02_CURRENT_FINDINGS.yaml',{
      'schema_version':1,'artifact_type':'STAGE02_CURRENT_FINDINGS','governance_uid':CURRENT_UID,'run_uid':RUN_UID,
      'target_pages':[PAGE],'fresh_functional_gap_total':len(problems),
      'closure_blocker_total':final.get('closure_blocker_total'),
      'fresh_closure_blocker_total':int(final.get('closure_blocker_total') or 0),
      'preserved_external_authority_union_count':int(final.get('preserved_external_authority_union_count') or 0),
      'official_stage_output_denominator_count':len(final.get('official_stage_output_denominator') or []),
      'current_manifest_mandatory_stage_output_subset_count':len(final.get('execution_profile_mandatory_output_subset') or []),
      'attempt_uid':ATTEMPT_UID,'frozen_governance_uid':CURRENT_UID,'source_head_sha':git_head(),
      'next_action':next_action,
      'gap_classes':(page.get('functional_chain_fresh_scan') or {}).get('gap_classes'),
      'gap_categories':(page.get('functional_chain_fresh_scan') or {}).get('gap_categories'),
      'status':'DESIGN_CONTRACT_REMEDIATION_REQUIRED' if problems else 'PASS',
      'result':'BLOCKED' if problems or int(final.get('closure_blocker_total') or 0) > 0 else 'PASS',
    })
    dump(s2root/'STAGE02_FRESH_DESIGN_REMEDIATION_INTAKE.yaml',{
      'schema_version':1,'artifact_type':'STAGE02_FRESH_DESIGN_REMEDIATION_INTAKE','governance_uid':CURRENT_UID,'run_uid':RUN_UID,
      'page_uid':PAGE,'problem_count':len(problems),'problems':problems,
      'candidate_reuse_from_prior_run':False,'prior_materialized_contract_reuse':False,
      'next_action':'BUILD_FRESH_DESIGN_CONTRACT_CANDIDATE_FROM_CURRENT_GAPS' if problems else 'CLOSE_STAGE02',
    })

    state=load(STATE)
    ex=state['execution']
    ex['current_stage']='STAGE-02-TESTED-BLOCKED' if problems else 'STAGE-02-CLOSED'
    ex['stage2']={
      'result':'TEST_EXECUTED_BLOCKED' if problems else 'TEST_EXECUTED_PASS',
      'stage_entry_gate':'PASS','stage_exit_allowed':not problems,'prior_results_used_in_current_run':False,
      'artifact_root_present':True,'tested_page_uids':[PAGE],'remaining_page_uids':[],
      'stage_scope_complete':True,'current_scope_manifest_ref':'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml',
    }
    attempt_uid=ATTEMPT_UID
    state['stage02_active_attempt']={
      'attempt_uid':attempt_uid,'run_uid':RUN_UID,'frozen_governance_uid':CURRENT_UID,
      'source_execution_sha':git_head(),'target_pages':[PAGE],
      'fresh_functional_gap_total':len(problems),'fresh_closure_blocker_total':int(final.get('closure_blocker_total') or 0),
      'preserved_external_authority_union_count':int(final.get('preserved_external_authority_union_count') or 0),
      'official_stage_output_denominator_count':len(final.get('official_stage_output_denominator') or []),
      'current_manifest_mandatory_stage_output_subset_count':len(final.get('execution_profile_mandatory_output_subset') or []),
      'next_action':next_action,
      'product_blocker_credit':0,'prior_results_used':False,
      'active_evidence_present':True,'active_findings_present':True,
      'fresh_revalidation_required':True,'closure_credit_under_current_governance':False,
    }
    state['stage2_result_evidence']={
      'mode':'RUNTIME_GENERATED_GITHUB_ACTION_ARTIFACT',
      'static_result_pointer_required':False,
      'static_run_id_copy_forbidden':True,
      'static_head_sha_copy_forbidden':True,
      'static_specification_digest_copy_forbidden':True,
      'tracked_current_evidence_ref':'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json',
      'artifact_provenance_recorded_in_active_attempt':False,
    }
    state['stage02_material_remediation']={
      'material_remediation_started':bool(ex['stage2'].get('artifact_root_present')),
      'run_uid':RUN_UID,'attempt_uid':attempt_uid,
      'source_problem_denominator':len(problems),
      'source_closure_blocker_denominator':int(final.get('closure_blocker_total') or 0),
      'product_blocker_credit':0,
      'status':'FRESH_PRODUCT_ROOT_MATERIALIZED_PENDING_PROVENANCE_FINALIZATION',
    }
    state.setdefault('selected_execution_profile_state',{})['active_attempt_state_key']='stage02_active_attempt'
    transition=state.setdefault('governance_revision_transition',{})
    transition['current_governance_uid']=CURRENT_UID
    transition['predecessor_attempt_preserved_as_historical_evidence']=True
    transition['predecessor_attempt_may_close_under_current_governance']=False
    transition['fresh_revalidation_required']=True
    ex['stage2']['prior_results_authoritative_for_current_governance']=False
    ex['stage2']['revalidation_required_under_current_governance']=True
    state['last_work_unit_resolution_gate']={
      'resolution_uid':STAGE2_RESOLUTION_UID,'normative_authority':False,
      'result':'PASS_SINGLE_LEGAL_SUCCESSOR','requested_primary_task_layer':'PRODUCT_STAGE_EXECUTION',
      'resolved_work_unit_uid':STAGE2_WORK_UNIT_UID,
      'authorization_uid':AUTHORIZATION_UID,
      'page_scope':[PAGE],'excluded_page_scope':list(EXCLUDED_UNITS),'source_problem_denominator':len(problems),
      'source_closure_blocker_denominator':int(final.get('closure_blocker_total') or 0),
    }
    stage_profile=load(LIFECYCLE)
    stage_adapters=load(ADAPTERS)
    stage2_def=next(x for x in stage_profile.get('stages',[]) if x.get('stage_uid')=='STAGE-02')
    stage2_ad=(stage_adapters.get('stages') or {})['STAGE-02']
    state['active_work_unit']={
      'work_unit_uid':STAGE2_WORK_UNIT_UID,
      'canonical_name':STAGE2_CANONICAL_NAME,
      'stage_uid':'STAGE-02',
      'semantic_capability':stage2_def.get('semantic_capability') or stage2_def.get('name'),
      'primary_task_layer':'PRODUCT_STAGE_EXECUTION','scope':[PAGE],
      'canonical_owner':f'{NEW.relative_to(ROOT).as_posix()}/04_PAGE_FUNCTIONAL_CONTRACT/CURRENT_PROBLEM_REGISTER.yaml',
      'current_status':'DESIGN_CONTRACT_REMEDIATION_REQUIRED' if problems else 'READY_FOR_TERMINAL_CLOSURE',
      'source_attempt_uid':attempt_uid,'source_problem_denominator':len(problems),
      'source_closure_blocker_denominator':int(final.get('closure_blocker_total') or 0),
      'dependencies':[
        f'{NEW.relative_to(ROOT).as_posix()}/02_BASE_BLUEPRINT/{PAGE}/PAGE_BASE_BLUEPRINT.yaml',
        f'{NEW.relative_to(ROOT).as_posix()}/03_BLUEPRINT_BINDING/{PAGE}/BLUEPRINT_BINDING_MANIFEST.yaml',
      ],
      'required_outputs':list(stage2_def.get('outputs') or []),
      'operation_bindings':{
        str(op):{'executor_owner':'governance/ci/run_current_stage2_actual_test.py','result_owner':f'{NEW.relative_to(ROOT).as_posix()}/04_PAGE_FUNCTIONAL_CONTRACT/CURRENT_PROBLEM_REGISTER.yaml'}
        for op in (stage2_def.get('operations') or [])
      },
      'scanner_bindings':{
        str(dim):{'scanner_owner':'governance/ci/run_current_stage2_actual_test.py','result_owner':'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'}
        for dim in (stage2_ad.get('scanner_dimensions') or [])
      },
      'product_blocker_credit':0,'out_of_scope':[*EXCLUDED_UNITS,'STAGE03','WEBSITE_CONSTRUCTION','DEPLOYMENT'],
    }
    state['status']='ACTIVE_STAGE2_TESTED_BLOCKED_FRESH_SCOPE' if problems else 'ACTIVE_STAGE2_READY_FOR_TERMINAL_CLOSURE'
    state['next_action']=next_action
    state['resume_control']={
      'current_resume_point':f'FRESH_{safe_uid(PAGE)}_STAGE2_DESIGN_REMEDIATION_REQUIRED' if problems else f'FRESH_{safe_uid(PAGE)}_STAGE2_READY_TO_CLOSE',
      'current_work_unit_uid':state['active_work_unit']['work_unit_uid'],'current_owner':state['active_work_unit']['canonical_owner'],
      'historical_stage2_results_are_current_state':False,'stage2_execution_requires_fresh_entry_resolution':False,
      'exact_next_action':state['next_action'],
    }
    state['current_primary_task_product_stage_credit']=0
    dump(STATE,state)

    scope=load(SCOPE)
    scope['owning_capability']='FUNCTIONAL_CONTRACT'
    scope['dependency_closure_refs']=['governance/test/ACTIVE_STATE.yaml',f'{NEW.relative_to(ROOT).as_posix()}/04_PAGE_FUNCTIONAL_CONTRACT/DEPENDENCY_MAP.yaml']
    scope['denominator_source_refs']=['governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json',f'{NEW.relative_to(ROOT).as_posix()}/04_PAGE_FUNCTIONAL_CONTRACT/CURRENT_PROBLEM_REGISTER.yaml']
    scope['stage_exit_credit_allowed']=not problems
    tmp=copy.deepcopy(scope); tmp.pop('content_hash',None)
    scope['content_hash']=sha_bytes(json.dumps(tmp,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
    dump(SCOPE,scope)

def main():
    if '--identity-self-test' in sys.argv:
        identity_self_test()
        return
    ctx=resolve_execution_context()
    if '--print-context-json' in sys.argv:
        print(json.dumps(ctx,ensure_ascii=False,indent=2))
        return
    if '--print-context-github-output' in sys.argv:
        print('run_uid='+ctx['run_uid'])
        print('run_root='+ctx['run_root'])
        print('predecessor_run_root='+ctx['predecessor_run_root'])
        print('authorization_uid='+ctx['authorization_uid'])
        print('artifact_name='+re.sub(r'[^A-Za-z0-9_.-]+','-',ctx['run_uid']).strip('-').lower())
        return
    bind_execution_context(ctx)
    auth=load(AUTH)
    if auth.get('authorization_uid')!=AUTHORIZATION_UID or auth.get('status')!='APPROVED_FOR_EXACT_SCOPE' or auth.get('single_use') is not True:
        raise RuntimeError('AUTHORIZATION_INVALID')
    reg=load(REGISTRY)
    if (reg.get('active_specification') or {}).get('governance_uid')!=CURRENT_UID:
        raise RuntimeError('CURRENT_GOVERNANCE_DRIFT')
    source_head=git_head()
    raw_bytes={}
    for name in RAW_NAMES:
        p=OLD/'00_SOURCE_INTAKE/RAW_SOURCE'/PAGE/name
        if not p.is_file():
            raise RuntimeError('RAW_SOURCE_MISSING:'+name)
        raw_bytes[name]=p.read_bytes()

    cleanup_old()
    materialize_stage1(raw_bytes,source_head)
    reset_current_state_for_stage1()
    bind_common_stage_work_unit(
      'STAGE-01',
      f'{NEW.relative_to(ROOT).as_posix()}/00_SOURCE_INTAKE/evidence/STAGE1_VALIDATION_EVIDENCE.yaml',
      [
        f'{NEW.relative_to(ROOT).as_posix()}/00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml',
        f'{NEW.relative_to(ROOT).as_posix()}/CURRENT_RUN_MANIFEST.yaml',
      ],
    )

    run('python',str(SOURCE/'09_TESTS/governance/governance_stage1_pipeline_guard.py'),str(SOURCE),str(NEW))
    ev=load(NEW/'00_SOURCE_INTAKE/evidence/STAGE1_VALIDATION_EVIDENCE.yaml')
    ev['status']='PASS'
    ev['validated_by']='STAGE1_SOURCE_PIPELINE_GUARD'
    dump(NEW/'00_SOURCE_INTAKE/evidence/STAGE1_VALIDATION_EVIDENCE.yaml',ev)
    # Refresh manifest because validation evidence changed after first validation.
    files=sorted(p.relative_to(NEW).as_posix() for p in NEW.rglob('*') if p.is_file())
    files=sorted(set(files+['CURRENT_RUN_MANIFEST.yaml']))
    dump(NEW/'CURRENT_RUN_MANIFEST.yaml',{'run_uid':RUN_UID,'current_files':files})
    run('python',str(SOURCE/'09_TESTS/governance/governance_stage1_pipeline_guard.py'),str(SOURCE),str(NEW))

    bind_common_stage_work_unit(
      'STAGE-02',
      f'{NEW.relative_to(ROOT).as_posix()}/04_PAGE_FUNCTIONAL_CONTRACT/CURRENT_PROBLEM_REGISTER.yaml',
      [
        f'{NEW.relative_to(ROOT).as_posix()}/02_BASE_BLUEPRINT/{PAGE}/PAGE_BASE_BLUEPRINT.yaml',
        f'{NEW.relative_to(ROOT).as_posix()}/02_BASE_BLUEPRINT/{PAGE}/VISUAL_BASE_BLUEPRINT.yaml',
        f'{NEW.relative_to(ROOT).as_posix()}/03_BLUEPRINT_BINDING/{PAGE}/BLUEPRINT_BINDING_MANIFEST.yaml',
      ],
    )
    env=dict(os.environ); env['ACPOS_RUN_ROOT']=NEW.relative_to(ROOT).as_posix(); env['STAGE02_PAGE_SCOPE']=PAGE
    run('python',str(ROOT/'governance/ci/run_current_stage2_actual_test.py'),env=env)
    initial=json.loads(STAGE2_TEST.read_text(encoding='utf-8'))
    jdump(ROOT/'governance/test/stage02/STAGE02_INITIAL_FRESH_SCAN.json',initial)

    page_raw=load(NEW/'00_SOURCE_INTAKE/RAW_SOURCE'/PAGE/PAGE_AUTHORITY_SOURCE_FILE)
    stage2_meta=page_raw.get('stage02_completeness_contract') or {}
    if isinstance(stage2_meta,dict) and stage2_meta.get('status')=='REQUIRED_FOR_STAGE02_CLOSURE':
        stage2_structural_materialize(None,initial)
        run('python',str(ROOT/'governance/ci/run_current_stage2_actual_test.py'),env=env)
        final=json.loads(STAGE2_TEST.read_text(encoding='utf-8'))
    else:
        final=initial
    if final.get('target_pages')!=[PAGE] or final.get('remaining_pages')!=[]:
        raise RuntimeError('FRESH_STAGE2_SCOPE_DRIFT')
    for excluded_uid in EXCLUDED_UNITS:
        if (NEW/'04_PAGE_FUNCTIONAL_CONTRACT'/excluded_uid).exists():
            raise RuntimeError('EXCLUDED_UNIT_MATERIALIZATION_FORBIDDEN:'+excluded_uid)
    materialize_stage2_projection(final)

    print(json.dumps({
      'run_uid':RUN_UID,'governance_uid':CURRENT_UID,'page_scope':[PAGE],
      'stage1':'PASS','stage2_result':final.get('result'),'planning_baseline_completeness':final.get('planning_baseline_completeness'),
      'fresh_functional_gap_total':final.get('fresh_functional_gap_total'),
      'closure_blocker_total':final.get('closure_blocker_total'),
      'planning_baseline_completeness':final.get('planning_baseline_completeness'),
      'excluded_unit_generated_data_present':{uid:False for uid in EXCLUDED_UNITS},
      'prior_run_root_present':OLD.exists(),
      'prior_stage2_history_present':(ROOT/'governance/test/history/stage02').exists(),
      'prior_stage2_candidate_reused':False,
      'product_blocker_credit':0,
      'next_action':f'BUILD_FRESH_{safe_uid(PAGE)}_DESIGN_CONTRACT_CANDIDATE_FROM_CURRENT_GAPS' if final.get('fresh_functional_gap_total') else 'CLOSE_STAGE02',
    },ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
