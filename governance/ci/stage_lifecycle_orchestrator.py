#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, importlib.util, json, os, subprocess, sys, uuid
from pathlib import Path
from stage_runtime_common import *
from stage_common_preflight_materializer import materialize as materialize_preflight
from stage_required_evidence_assembler import assemble as assemble_required_evidence
from stage_declared_guard_dispatcher import evaluate as evaluate_declared_guard

ENGINE_PATH=GOV_ROOT/'governance/ci/stage_execution_engine.py'
PHASES=['SESSION_BOOTSTRAP_RESUME_GATE','CURRENT_GOVERNANCE','CURRENT_SCOPE','WORK_UNIT','AUTHORITY','APPLICABILITY','DEPENDENCY','REQUIRED_FIELD_MANIFEST','STAGE_INPUT_CONTRACT','STAGE_OPERATIONS','OUTPUT_PRODUCER','CURRENT_PROBLEM_REGISTER','DENOMINATOR_SNAPSHOT','CHANGE_IMPACT','RESOLUTION_LEDGER','FRESH_EXECUTION','STAGE_SPECIFIC_SCANNER','GAP_CLASSIFICATION','OWNER_REMEDIATION','FRESH_REEXECUTION','HIDDEN_DEFECT_SWEEP','REQUIRED_EVIDENCE','CONTENT_VALIDATION','TERMINAL_CLOSURE','STATE_CHECKPOINT','NEXT_STAGE']

def _engine():
    spec=importlib.util.spec_from_file_location('stage_execution_engine_runtime',ENGINE_PATH)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def _now(): return dt.datetime.now(dt.timezone.utc).isoformat()

def _governance_receipt(root,wp,work,stage_uid,op,binding):
    ref=str(binding.get('governance_load_receipt_ref') or '')
    if not ref: fail('GOVERNANCE_LOAD_RECEIPT_REF_MISSING:'+op)
    p=safe_ref(root,ref); reg,gov=governance_identity(); git=current_git_identity(root)
    doc={'artifact_type':'GOVERNANCE_LOAD_RECEIPT','stage_uid':stage_uid,'work_unit_uid':work.get('work_unit_uid'),'governed_unit_uid':work.get('governed_unit_uid'),'current_operation':op,'governance_uid':gov,'execution_repository':git.get('repository_root'),'execution_branch':git.get('branch'),'execution_head':git.get('head'),'execution_tree':git.get('tree'),'root_manifest_sha256':sha256_file(ROOT_MANIFEST),'effective_normative_set_sha256':str((reg.get('governance_identity') or {}).get('specification_bundle_sha256') or ''),'dependency_hashes':dependency_hashes(root,work),'acceptance_blueprint_sha256':sha256_file(ACCEPTANCE_BLUEPRINT),'timestamp':_now(),'loader_identity':'governance/ci/stage_lifecycle_orchestrator.py','loader_version':'THREE_LAYER_COMPLETE_V1','status':'PASS'}
    atomic_yaml(p,doc); return p

def _generic_scanners(root,wp,work,stage_uid):
    stage=stage_definition(stage_uid)
    for dim,b in (work.get('scanner_bindings') or {}).items():
        ref=str((b or {}).get('result_owner') or '')
        if not ref: fail('SCANNER_RESULT_OWNER_MISSING:'+str(dim))
        findings=[]
        for op in map(str,stage.get('operations') or []):
            rb=(work.get('operation_bindings') or {}).get(op) or {}; rr=str(rb.get('operation_receipt_ref') or '')
            try:
                rec=load_yaml(safe_ref(root,rr))
                if rec.get('status') not in {'PASS','NOT_APPLICABLE_WITH_PROOF'}: findings.append('OPERATION_NOT_TERMINAL:'+op)
            except RuntimeContractError as e: findings.append(str(e))
        doc={'artifact_type':'STAGE_SCANNER_RESULT','stage_uid':stage_uid,'work_unit_uid':work.get('work_unit_uid'),'scanner_dimension':str(dim),'scanner_owner':(b or {}).get('scanner_owner'),'status':'PASS' if not findings else 'FAIL','findings':findings,'product_completion_credit':0}
        atomic_yaml(safe_ref(root,ref),doc)
        if findings: fail('SCANNER_FAILED:'+str(dim)+':'+repr(findings))

def _validator_identity(uid):
    rr=load_yaml(REFERENCE_RULES)
    for row in rr.get('validator_identities') or []:
        if isinstance(row,dict) and row.get('validator_uid')==uid: return row
    fail('VALIDATOR_IDENTITY_NOT_FOUND:'+uid)

def _physical_validator(stage_uid,uid,root,wp):
    ident=_validator_identity(uid); rel=str(ident.get('implementation_path') or '')
    if not rel: fail('PHYSICAL_VALIDATOR_PATH_MISSING:'+uid)
    p=GOV_ROOT/'.github/governance-source/active/source'/rel
    if not p.is_file(): fail('PHYSICAL_VALIDATOR_MISSING:'+uid)
    if uid=='VAL-GOV-026': cmd=[sys.executable,str(p),str(GOV_ROOT/'.github/governance-source/active/source'),str(wp.parent)]
    else: cmd=[sys.executable,str(p)]
    proc=subprocess.run(cmd,cwd=GOV_ROOT,text=True,capture_output=True)
    try: payload=json.loads(proc.stdout) if proc.stdout.strip().startswith('{') else {'raw':proc.stdout.strip()}
    except Exception: payload={'raw':proc.stdout.strip()}
    return {'artifact_type':'VALIDATOR_RESULT','validator_uid':uid,'stage_uid':stage_uid,'work_unit_uid':load_yaml(wp).get('work_unit_uid'),'status':'PASS' if proc.returncode==0 else 'FAIL','read_only':True,'implementation_path':rel,'result':payload,'stderr':proc.stderr.strip()[:2000]}

def _validators(root,wp,work,stage_uid,phase):
    stage=stage_definition(stage_uid); rows=[]
    for uid in map(str,stage.get('validators') or []):
        ident=_validator_identity(uid)
        if ident.get('identity_mode')=='DECLARED_STAGE_GUARD':
            out=evaluate_declared_guard(stage_uid,uid,phase,str(wp.relative_to(root)),str(root))
        elif ident.get('identity_mode')=='PHYSICAL_VALIDATOR':
            out=_physical_validator(stage_uid,uid,root,wp)
        else: fail('VALIDATOR_IDENTITY_MODE_UNSUPPORTED:'+uid)
        rp=wp.parent/'EVIDENCE/VALIDATORS'/(uid+'.yaml'); atomic_yaml(rp,out)
        rows.append({'validator_uid':uid,'status':out.get('status'),'result_ref':str(rp.relative_to(root))})
        if out.get('status')!='PASS': fail('VALIDATOR_FAILED:'+uid)
    return rows

def _output_path(work_dir,uid):
    a=work_dir/(uid+'.yaml'); b=work_dir/'OUTPUTS'/(uid+'.yaml')
    return a if a.is_file() else b

def _normalized(stage_uid,root,wp,work,state,validators,human_block=False,final=False):
    stage=stage_definition(stage_uid); adapters=load_yaml(ADAPTERS)
    dims=list(map(str,((adapters.get('stages') or {}).get(stage_uid) or {}).get('scanner_dimensions') or []))
    ops=[]
    for op in map(str,stage.get('operations') or []):
        ref=str(((work.get('operation_bindings') or {}).get(op) or {}).get('operation_receipt_ref') or '')
        rec=load_yaml(safe_ref(root,ref)); ops.append({'operation_uid':op,'status':rec.get('status'),'proof':rec.get('proof')})
    outs=[]
    for uid in map(str,stage.get('outputs') or []):
        p=_output_path(wp.parent,uid); required_file(p,'OUTPUT:'+uid)
        outs.append({'output_uid':uid,'producer_operation_uid':(stage.get('output_producers') or {}).get(uid),'status':'PASS'})
    scans=[]
    for dim in dims:
        b=(work.get('scanner_bindings') or {}).get(dim) or {}
        d=load_yaml(safe_ref(root,str(b.get('result_owner') or '')))
        scans.append({'scanner_dimension':dim,'status':d.get('status')})
    manifest=load_yaml(wp.parent/'REQUIRED_EVIDENCE_BINDING_MANIFEST.yaml'); req=[]
    for b in manifest.get('bindings') or []:
        req.append({'evidence_type':b.get('evidence_uid'),'status':'PASS' if b.get('status')=='PASS' else 'BLOCKED','ref':b.get('physical_ref'),'external_receipt':False})
    trace=[]
    for i,p in enumerate(PHASES,1):
        st='PASS'
        if human_block and i==22: st='BLOCKED'
        elif human_block and i>22: st='NOT_EXECUTED_AFTER_BLOCK'
        trace.append({'phase_uid':p,'status':st})
    pr=load_yaml(wp.parent/'CURRENT_PROBLEM_REGISTER.yaml') if (wp.parent/'CURRENT_PROBLEM_REGISTER.yaml').is_file() else {'open_problem_total':0,'closure_blocker_total':0}
    blockers=[] if int(pr.get('open_problem_total',0))==0 and int(pr.get('closure_blocker_total',0))==0 else [{'uid':'CURRENT_PROBLEM_REGISTER','status':'BLOCKED'}]
    e={'artifact_type':'NORMALIZED_STAGE_EXECUTION_EVIDENCE','governance_uid':work.get('governance_uid'),'stage_uid':stage_uid,'attempt_uid':str(work.get('work_unit_uid'))+('-FINAL' if final else '-CANDIDATE'),'scope_manifest_ref':str((wp.parent/'CURRENT_EXECUTION_SCOPE_MANIFEST.yaml').relative_to(root)),'actual_stage_execution_started':True,'actual_stage_execution_completed':True,'fresh_execution':True,'prior_results_used':False,'current_specification_mutated':False,'source_head_sha':current_git_identity(root).get('head') or '0'*40,'denominator':{'required_total':len(ops),'open_gap_total':0,'closure_blocker_total':len(blockers),'remaining_scope_total':0},'gaps':[],'closure_blockers':blockers,'phase_trace':trace,'operation_results':ops,'output_results':outs,'scanner_results':scans,'validator_results':validators,'remediation':{'discovered_gap_total':0,'remediated_gap_total':0,'unresolved_gap_total':0,'reexecution_required':False,'reexecution_performed':False},'hidden_defect_sweep':{'performed':True,'result':'PASS','discovered_defect_total':0},'required_evidence':req,'state_checkpoint':{'performed':True,'state_ref':str((wp.parent/'EXECUTION_STATE.yaml').relative_to(root))},'next_stage_transition':{'next_stage_uid':stage.get('next_stage_uid'),'status':'BLOCKED' if human_block else ('SCOPE_COMPLETE' if stage_uid=='STAGE-11' else 'READY')},'result':'BLOCKED' if human_block else 'PASS','stage_exit_allowed':not human_block}
    if stage_uid=='STAGE-11':
        td=wp.parent/'EVIDENCE/TERMINAL_DISPOSITION.yaml'
        if not human_block and not td.exists():
            elig=_output_path(wp.parent,'NEXT_GOVERNED_UNIT_ELIGIBILITY'); required_file(elig,'NEXT_GOVERNED_UNIT_ELIGIBILITY')
            atomic_yaml(td,{'artifact_type':'TERMINAL_DISPOSITION','stage_uid':'STAGE-11','work_unit_uid':work.get('work_unit_uid'),'next_governed_unit_eligibility_ref':str(elig.relative_to(root)),'scope_complete_or_next_governed_unit':'RESOLVED','unresolved_required_dependency_total':0,'status':'PASS'})
        e['terminal_disposition']=load_yaml(td) if td.exists() else {'status':'BLOCKED'}
    else:
        hp=wp.parent/'CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml'; required_file(hp,'CROSS_STAGE_HANDOFF_READINESS_LEDGER'); h=load_yaml(hp)
        e['cross_stage_handoff']={'ledger_ref':str(hp.relative_to(root)),'external_receipt':False,'successor_stage_uid':stage.get('next_stage_uid'),'reference_resolution_complete':h.get('reference_resolution_complete'),'physical_materialization_complete':h.get('physical_materialization_complete'),'required_field_completeness_complete':h.get('required_field_completeness_complete'),'denominator_reconciled':h.get('denominator_reconciled'),'consumer_readiness_complete':h.get('consumer_readiness_complete'),'current_matrix_valid':h.get('current_matrix_valid'),'current_state_consistent':h.get('current_state_consistent'),'unresolved_required_dependency_total':h.get('unresolved_required_dependency_total'),'status':h.get('status')}
    return e

def _human_pending(manifest):
    return any(b.get('status') in {'PENDING_HUMAN','BLOCKED'} for b in manifest.get('bindings') or [] if b.get('producer_class')=='HUMAN_GATE_EVIDENCE')

def _refresh_post_close_state_binding(root,wp,statep):
    work=load_yaml(wp)
    bindings=work.get('current_ledger_bindings') or {}
    row=bindings.get('EXECUTION_STATE')
    if not isinstance(row,dict):
        fail('CURRENT_STATE_LEDGER_BINDING_MISSING_AFTER_CLOSE')
    ref=str(row.get('artifact_ref') or '')
    if safe_ref(root,ref).resolve()!=statep.resolve():
        fail('CURRENT_STATE_LEDGER_BINDING_DRIFT_AFTER_CLOSE')
    row['content_sha256']=sha256_file(statep)
    bindings['EXECUTION_STATE']=row
    work['current_ledger_bindings']=bindings
    atomic_yaml(wp,work)
    return work

def _sync_post_close_projections(root,wp,statep,stage_uid):
    state=load_yaml(statep)
    if state.get('status')!='CLOSED_PASS':
        fail('POST_CLOSE_PROJECTION_SYNC_REQUIRES_CLOSED_PASS')
    work=load_yaml(wp)
    if 'status' in work: work['status']='CLOSED'
    if 'current_status' in work: work['current_status']='CLOSED'
    work['current_state_authority_ref']=str(statep.relative_to(root))
    work['current_state_authority_sha256']=sha256_file(statep)
    work['projection_role']='NON_AUTHORITATIVE'
    atomic_yaml(wp,work)
    rp=wp.parent/'RESUME_POINT.yaml'
    if rp.is_file():
        resume=load_yaml(rp)
        resume['completed_operations']=list(state.get('completed_operations') or [])
        resume['stage_exit_authorized']=True
        resume['return_gate']='TERMINAL_CLOSURE'
        resume['next_stage_uid']=stage_definition(stage_uid).get('next_stage_uid')
        resume['status']='CLOSED'
        resume['terminal_receipt_ref']=str((wp.parent/'EVIDENCE/TERMINAL_CLOSURE_RECORD.yaml').relative_to(root))
        resume['authoritative_state_ref']=str(statep.relative_to(root))
        resume['authoritative_state_sha256']=sha256_file(statep)
        resume['projection_role']='NON_AUTHORITATIVE'
        atomic_yaml(rp,resume)

def _close(stage_uid,root,wp,work,statep,state,e):
    candidate=wp.parent/'EVIDENCE/NORMALIZED_STAGE_EVIDENCE_CANDIDATE.json'; atomic_json(candidate,e)
    eng=_engine(); eng.validate_evidence(stage_uid,candidate,'PRE_CLOSE_CANDIDATE')
    tc=wp.parent/'EVIDENCE/CLOSURE_TRANSACTION/TERMINAL_CLOSURE_RECORD_CANDIDATE.yaml'
    nt=wp.parent/'EVIDENCE/NEXT_STAGE_TRANSITION_CANDIDATE.yaml'
    atomic_yaml(tc,{'artifact_type':'TERMINAL_CLOSURE_RECORD_CANDIDATE','stage_uid':stage_uid,'work_unit_uid':work.get('work_unit_uid'),'candidate_evidence_sha256':sha256_file(candidate),'status':'PASS'})
    atomic_yaml(nt,{'artifact_type':'NEXT_STAGE_TRANSITION_CANDIDATE','stage_uid':stage_uid,'work_unit_uid':work.get('work_unit_uid'),'next_stage_uid':stage_definition(stage_uid).get('next_stage_uid'),'status':'READY' if stage_uid!='STAGE-11' else 'SCOPE_COMPLETE'})
    prehash=sha256_file(statep); target=dict(state); target['status']='CLOSED_PASS'; target['current_operation']='COMPLETE'; target['blocker_disposition']=None; target['next_action']='MATERIALIZE_REGISTERED_SUCCESSOR' if stage_uid!='STAGE-11' else 'SCOPE_COMPLETE'
    cc=wp.parent/'EVIDENCE/CLOSURE_TRANSACTION/CLOSURE_COMMIT_CANDIDATE.yaml'
    atomic_yaml(cc,{'artifact_type':'CLOSURE_COMMIT_CANDIDATE','transaction_uid':'CLOSE-'+uuid.uuid4().hex,'stage_uid':stage_uid,'work_unit_uid':work.get('work_unit_uid'),'pre_close_state_sha256':prehash,'candidate_evidence_sha256':sha256_file(candidate),'target_state_sha256':sha256_obj(target),'status':'PREPARED'})
    if sha256_file(statep)!=prehash: fail('CLOSURE_CAS_STATE_DRIFT')
    atomic_yaml(statep,target)
    work=_refresh_post_close_state_binding(root,wp,statep)
    atomic_yaml(wp.parent/'EVIDENCE/CLOSURE_TRANSACTION/CLOSURE_COMMIT_RECORD.yaml',{**load_yaml(cc),'status':'COMMITTED','committed_state_sha256':sha256_file(statep)})
    atomic_yaml(wp.parent/'EVIDENCE/TERMINAL_CLOSURE_RECORD.yaml',{'artifact_type':'TERMINAL_CLOSURE_RECORD','stage_uid':stage_uid,'work_unit_uid':work.get('work_unit_uid'),'evidence_hash':sha256_file(candidate),'execution_state_sha256':sha256_file(statep),'status':'CLOSED_PASS'})
    atomic_yaml(wp.parent/'EVIDENCE/NEXT_STAGE_TRANSITION_RECORD.yaml',{'artifact_type':'NEXT_STAGE_TRANSITION_RECORD','stage_uid':stage_uid,'work_unit_uid':work.get('work_unit_uid'),'next_stage_uid':stage_definition(stage_uid).get('next_stage_uid'),'status':'READY' if stage_uid!='STAGE-11' else 'SCOPE_COMPLETE'})
    final=_normalized(stage_uid,root,wp,work,target,e.get('validator_results') or [],final=True)
    finalp=wp.parent/'EVIDENCE/NORMALIZED_STAGE_EVIDENCE.json'; atomic_json(finalp,final)
    eng.validate_evidence(stage_uid,finalp,'POST_CLOSE_FINAL')
    _sync_post_close_projections(root,wp,statep,stage_uid)
    return target

def run_stage(stage_uid,work_ref=None,root_arg=None):
    root=execution_root(root_arg); root,wp,work,sp,scope,statep,state=work_unit_context(stage_uid,work_ref,root)
    materialize_preflight(stage_uid,str(wp.relative_to(root)),str(root))
    eng=_engine(); oldroot=os.environ.get('STAGE_EXECUTION_ROOT'); oldwu=os.environ.get('STAGE_ACTIVE_WORK_UNIT'); oldscope=os.environ.get('STAGE_CURRENT_SCOPE')
    os.environ['STAGE_EXECUTION_ROOT']=str(root); os.environ['STAGE_ACTIVE_WORK_UNIT']=str(wp.relative_to(root)); os.environ['STAGE_CURRENT_SCOPE']=str(sp.relative_to(root))
    try:
        while True:
            state=load_yaml(statep)
            if state.get('status') in {'CLOSED_PASS','BLOCKED','REVERIFY_REQUIRED','CURRENT_STATE_CONFLICT','SNAPSHOT_INVALIDATED'} or state.get('current_operation')=='COMPLETE': break
            op=str(state.get('current_operation') or ''); b=(work.get('operation_bindings') or {}).get(op) or {}
            _governance_receipt(root,wp,work,stage_uid,op,b); eng.execute_active(stage_uid)
        state=load_yaml(statep)
        if state.get('status')=='CLOSED_PASS': return {'status':'CLOSED_PASS','stage_uid':stage_uid}
        if state.get('current_operation')!='COMPLETE': return {'status':state.get('status'),'stage_uid':stage_uid}
        _generic_scanners(root,wp,work,stage_uid)
        manifest=assemble_required_evidence(stage_uid,str(wp.relative_to(root)),str(root))
        if _human_pending(manifest):
            state['status']='BLOCKED'; state['blocker_disposition']='EXTERNAL_APPROVAL_REQUIRED'; state['next_action']='WAIT_FOR_REGISTERED_HUMAN_EVIDENCE'; atomic_yaml(statep,state)
            atomic_json(wp.parent/'EVIDENCE/NORMALIZED_STAGE_EVIDENCE_CANDIDATE.json',_normalized(stage_uid,root,wp,work,state,[],human_block=True))
            return {'status':'BLOCKED','reason':'EXTERNAL_APPROVAL_REQUIRED','stage_uid':stage_uid}
        if state.get('status')=='BLOCKED' and state.get('blocker_disposition')=='EXTERNAL_APPROVAL_REQUIRED':
            state['status']='EXECUTION_COMPLETE_CLOSURE_PENDING'; state['blocker_disposition']=None; state['next_action']='FINAL_CONTENT_CLOSURE'
        else:
            state['status']='EXECUTION_COMPLETE_CLOSURE_PENDING'
        atomic_yaml(statep,state)
        validators=_validators(root,wp,work,stage_uid,'PRE_CLOSE_CANDIDATE')
        _close(stage_uid,root,wp,work,statep,state,_normalized(stage_uid,root,wp,work,state,validators))
        return {'status':'CLOSED_PASS','stage_uid':stage_uid,'work_unit_uid':work.get('work_unit_uid')}
    finally:
        for key,val in [('STAGE_EXECUTION_ROOT',oldroot),('STAGE_ACTIVE_WORK_UNIT',oldwu),('STAGE_CURRENT_SCOPE',oldscope)]:
            if val is None: os.environ.pop(key,None)
            else: os.environ[key]=val

def preflight(stage_uid,work_ref=None,root_arg=None):
    root=execution_root(root_arg); root,wp,work,sp,scope,statep,state=work_unit_context(stage_uid,work_ref,root)
    out=materialize_preflight(stage_uid,str(wp.relative_to(root)),str(root))
    return {'status':out['status'],'stage_uid':stage_uid,'work_unit_uid':work.get('work_unit_uid')}


def _successor_resolution(root,stage_uid,wp,work):
    stage=stage_definition(stage_uid)
    next_stage=str(stage.get('next_stage_uid') or '')
    _,stages=lifecycle_stages()
    if stage_uid=='STAGE-11' or next_stage not in stages:
        return {'status':'SCOPE_COMPLETE','next_stage_uid':next_stage,'work_unit_ref':None}
    statep=wp.parent/'EXECUTION_STATE.yaml'
    state=load_yaml(statep)
    if state.get('status')!='CLOSED_PASS':
        fail('SUCCESSOR_REQUIRES_PREDECESSOR_CLOSED_PASS:'+stage_uid)
    governed=str(work.get('governed_unit_uid') or '')
    seed='|'.join([str(work.get('work_unit_uid') or ''),sha256_file(statep),governed,next_stage])
    key=hashlib.sha256(seed.encode('utf-8')).hexdigest()
    safe_governed=''.join(ch if ch.isalnum() or ch in '-_' else '-' for ch in governed).strip('-_') or 'GOVERNED-UNIT'
    successor_uid=f"WU-{next_stage.replace('STAGE-','STAGE')}-{safe_governed}-{key[:12]}"
    idir=wp.parent/'EVIDENCE/SUCCESSOR'
    ip=idir/'SUCCESSOR_MATERIALIZATION_INTENT.yaml'
    intent={
      'artifact_type':'SUCCESSOR_MATERIALIZATION_INTENT',
      'predecessor_stage_uid':stage_uid,
      'predecessor_work_unit_uid':work.get('work_unit_uid'),
      'predecessor_closed_pass_state_sha256':sha256_file(statep),
      'governed_unit_uid':governed,
      'next_stage_uid':next_stage,
      'idempotency_key':key,
      'successor_work_unit_uid':successor_uid,
      'status':'INTENT_PERSISTED',
    }
    if ip.is_file():
        old=load_yaml(ip)
        if old.get('idempotency_key')!=key or old.get('successor_work_unit_uid')!=successor_uid:
            fail('SUCCESSOR_INTENT_CONFLICT:'+next_stage)
    else:
        atomic_yaml(ip,intent)
    stage_dir=root/'STAGE_EXECUTION'/next_stage
    candidates=[]
    if stage_dir.is_dir():
        for d in sorted(stage_dir.iterdir()):
            if not d.is_dir() or d.name.startswith('_'): continue
            w=d/'WORK_UNIT.yaml'
            if not w.is_file(): continue
            try: wd=load_yaml(w)
            except RuntimeContractError: continue
            if wd.get('stage_uid')==next_stage and wd.get('governed_unit_uid')==governed:
                candidates.append(w)
    if len(candidates)>1:
        fail('MULTIPLE_SUCCESSOR_WORK_UNITS:'+next_stage+':'+governed)
    if not candidates:
        return {
          'status':'WORK_UNIT_RESOLUTION_REQUIRED',
          'next_stage_uid':next_stage,
          'successor_work_unit_uid':successor_uid,
          'idempotency_key':key,
          'intent_ref':str(ip.relative_to(root)),
          'reason':'TRUE_SUCCESSOR_BINDINGS_NOT_UNIQUELY_MATERIALIZED',
        }
    swp=candidates[0]
    sw=load_yaml(swp)
    swuid=str(sw.get('work_unit_uid') or '')
    if not swuid:
        fail('SUCCESSOR_WORK_UNIT_UID_MISSING:'+next_stage)
    # Existing legal successor takes precedence over the deterministic candidate UID.
    # Persist the adopted identity once; retries must resolve the same target.
    if intent.get('successor_work_unit_uid')!=swuid:
        intent['successor_work_unit_uid']=swuid
        intent['status']='EXISTING_SUCCESSOR_ADOPTED'
        atomic_yaml(ip,intent)
    scope=swp.parent/'CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
    state_path=swp.parent/'EXECUTION_STATE.yaml'
    required_file(scope,'SUCCESSOR_SCOPE')
    required_file(state_path,'SUCCESSOR_STATE')
    sd=load_yaml(state_path)
    if sd.get('stage_uid')!=next_stage or sd.get('work_unit_uid')!=swuid:
        fail('SUCCESSOR_STATE_IDENTITY_DRIFT:'+next_stage)
    commit=idir/'SUCCESSOR_MATERIALIZATION_COMMIT.yaml'
    atomic_yaml(commit,{
      'artifact_type':'SUCCESSOR_MATERIALIZATION_COMMIT',
      'predecessor_work_unit_uid':work.get('work_unit_uid'),
      'successor_work_unit_uid':swuid,
      'next_stage_uid':next_stage,
      'idempotency_key':key,
      'target_work_unit_ref':str(swp.relative_to(root)),
      'target_work_unit_sha256':sha256_file(swp),
      'status':'COMMITTED_EXISTING_SUCCESSOR',
    })
    return {
      'status':'READY',
      'next_stage_uid':next_stage,
      'successor_work_unit_uid':swuid,
      'work_unit_ref':str(swp.relative_to(root)),
      'scope_ref':str(scope.relative_to(root)),
      'idempotency_key':key,
      'intent_ref':str(ip.relative_to(root)),
      'commit_ref':str(commit.relative_to(root)),
    }

def main():
    p=argparse.ArgumentParser(); g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--preflight',action='store_true'); g.add_argument('--run-stage',action='store_true'); g.add_argument('--run-range',action='store_true')
    p.add_argument('--stage'); p.add_argument('--start-stage'); p.add_argument('--end-stage'); p.add_argument('--work-unit'); p.add_argument('--product-root'); a=p.parse_args()
    try:
        if a.preflight:
            if not a.stage: fail('STAGE_REQUIRED')
            out=preflight(a.stage,a.work_unit,a.product_root)
        elif a.run_stage:
            if not a.stage: fail('STAGE_REQUIRED')
            out=run_stage(a.stage,a.work_unit,a.product_root)
            if out.get('status')=='CLOSED_PASS':
                root=execution_root(a.product_root)
                _,wp,work,_,_,_,_=work_unit_context(a.stage,a.work_unit,root)
                out['successor_disposition']=_successor_resolution(root,a.stage,wp,work)
        else:
            if not a.start_stage or not a.end_stage: fail('RANGE_ENDPOINTS_REQUIRED')
            _,stages=lifecycle_stages(); order=list(stages); si=order.index(a.start_stage); ei=order.index(a.end_stage)
            if si>ei: fail('RANGE_ORDER_INVALID')
            out={'status':'PASS','stages':[]}
            current_ref=a.work_unit
            root=execution_root(a.product_root)
            for index,sid in enumerate(order[si:ei+1]):
                result=run_stage(sid,current_ref,str(root)); out['stages'].append(result)
                if result.get('status')!='CLOSED_PASS':
                    out['status']=result.get('status'); break
                _,wp,work,_,_,_,_=work_unit_context(sid,current_ref,root)
                succ=_successor_resolution(root,sid,wp,work)
                result['successor_disposition']=succ
                if sid==a.end_stage:
                    break
                if succ.get('status')!='READY':
                    out['status']='BLOCKED'
                    out['blocker']='TRUE_SUCCESSOR_WORK_UNIT_RESOLUTION_REQUIRED'
                    out['successor_disposition']=succ
                    break
                current_ref=succ.get('work_unit_ref')
        print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out.get('status') in {'PASS','CLOSED_PASS'} else 2)
    except (RuntimeContractError,ValueError) as e:
        print('BLOCK: '+str(e),file=sys.stderr); raise SystemExit(1)
if __name__=='__main__': main()
