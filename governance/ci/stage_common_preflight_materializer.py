#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from stage_runtime_common import *

ARTIFACTS = [
 'REQUIRED_FIELD_MANIFEST','FUNCTIONAL_CHAIN_MANIFEST','EFFECTIVE_CONTRACT_OVERLAY','DEPENDENCY_TOPOLOGY',
 'DENOMINATOR_SNAPSHOT','CLASSIFICATION_RULESET','CHANGE_IMPACT_MAP','STAGE_EXECUTION_PREFLIGHT_RECEIPT',
 'CURRENT_PROBLEM_REGISTER','RESOLUTION_LEDGER'
]
GOVERNED_CYCLE={'CURRENT_PROBLEM_REGISTER','RESOLUTION_LEDGER'}

def _matrix_rows(work_dir:Path, work:dict):
    ref=str(work.get('normative_execution_matrix_ref') or '')
    p=safe_ref(execution_root(),ref) if ref else work_dir/'NORMATIVE_EXECUTION_MATRIX.yaml'
    m=load_yaml(p)
    rows=m.get('rows') or m.get('matrix_rows') or []
    if not isinstance(rows,list): fail('NORMATIVE_MATRIX_ROWS_INVALID')
    return p,m,rows

def _common_doc(uid,stage_uid,work,scope,rows):
    base={'artifact_type':uid,'stage_uid':stage_uid,'work_unit_uid':work.get('work_unit_uid'),'governed_unit_uid':work.get('governed_unit_uid'),'governance_uid':work.get('governance_uid'),'product_completion_credit':0}
    if uid=='REQUIRED_FIELD_MANIFEST':
        base['required_fields']=[{'matrix_row_uid':r.get('matrix_row_uid'),'artifact_ref':r.get('artifact_ref'),'field_path':r.get('field_path'),'applicability':r.get('applicability')} for r in rows if isinstance(r,dict) and r.get('applicability')=='REQUIRED']
    elif uid=='FUNCTIONAL_CHAIN_MANIFEST':
        base['requirements']=[{'requirement_uid':r.get('requirement_uid'),'row_identity':r.get('row_identity'),'artifact_ref':r.get('artifact_ref')} for r in rows if isinstance(r,dict) and r.get('applicability')=='REQUIRED']
    elif uid=='EFFECTIVE_CONTRACT_OVERLAY':
        base['input_bindings']=work.get('input_bindings') or {}; base['dependencies']=work.get('dependencies') or []
    elif uid=='DEPENDENCY_TOPOLOGY':
        base['dependencies']=work.get('dependencies') or []; base['forward_edges']=work.get('dependencies') or []; base['reverse_closure_status']='DERIVED_FROM_CURRENT_WORK_UNIT'
    elif uid=='DENOMINATOR_SNAPSHOT':
        required_ops=[k for k,v in (work.get('operation_bindings') or {}).items() if isinstance(v,dict) and v.get('applicability')=='REQUIRED']
        base.update({'required_operation_uids':required_ops,'required_operation_count':len(required_ops),'scope_included_units':scope.get('included_units') or [work.get('governed_unit_uid')],'partial_scope':bool(scope.get('partial_scope',False))})
        base['denominator_sha256']=sha256_obj({'ops':required_ops,'scope':base['scope_included_units']})
    elif uid=='CLASSIFICATION_RULESET':
        base['allowed_applicability']=['REQUIRED','AUTHORIZED_NOT_APPLICABLE']; base['unclassified_disposition']='BLOCK'
    elif uid=='CHANGE_IMPACT_MAP':
        base['dependency_refs']=work.get('dependencies') or []; base['affected_descendants']=[]; base['reentry_owner']='CURRENT_STAGE_CAPABILITY'
    elif uid=='STAGE_EXECUTION_PREFLIGHT_RECEIPT':
        base['resolved_artifacts']=ARTIFACTS[:-3]+['CURRENT_PROBLEM_REGISTER','RESOLUTION_LEDGER']; base['status']='PASS'
    elif uid=='CURRENT_PROBLEM_REGISTER':
        base['problems']=[]; base['open_problem_total']=0; base['closure_blocker_total']=0; base['status']='CURRENT'
    elif uid=='RESOLUTION_LEDGER':
        base['entries']=[]; base['append_only']=True; base['status']='CURRENT'
    return base

def materialize(stage_uid:str,work_ref:str|None=None,root_arg:str|None=None):
    root=execution_root(root_arg)
    root,wp,work,sp,scope,statep,state=work_unit_context(stage_uid,work_ref,root)
    stage=stage_definition(stage_uid); outputs=set(map(str,stage.get('outputs') or []))
    mp,matrix,rows=_matrix_rows(wp.parent,work)
    resolutions=[]
    for uid in ARTIFACTS:
        path=wp.parent/(uid+'.yaml')
        if uid in outputs:
            mode='REGISTERED_STAGE_OUTPUT'
            producer=str((stage.get('output_producers') or {}).get(uid) or '')
            if not producer: fail('REGISTERED_OUTPUT_PRODUCER_MISSING:'+uid)
            status='PASS' if path.is_file() else 'PENDING_REGISTERED_PRODUCER'
            if path.is_file(): required_file(path,'REGISTERED_OUTPUT:'+uid)
        else:
            mode='CURRENT_GOVERNED_CYCLE_ARTIFACT' if uid in GOVERNED_CYCLE else 'COMMON_PREFLIGHT_ARTIFACT'
            producer='governance/ci/stage_common_preflight_materializer.py'
            if not path.exists(): atomic_yaml(path,_common_doc(uid,stage_uid,work,scope,rows))
            required_file(path,'COMMON_PREFLIGHT:'+uid); status='PASS'
        resolutions.append({'artifact_uid':uid,'resolution_mode':mode,'physical_ref':str(path.relative_to(root)),'producer_owner':producer,'status':status,'product_completion_credit':0})
    out={'artifact_type':'COMMON_PREFLIGHT_RESOLUTION','stage_uid':stage_uid,'work_unit_uid':work.get('work_unit_uid'),'governance_uid':work.get('governance_uid'),'resolutions':resolutions,'status':'PASS' if all(r['status'] in {'PASS','PENDING_REGISTERED_PRODUCER'} for r in resolutions) else 'BLOCKED'}
    atomic_yaml(wp.parent/'EVIDENCE/COMMON_PREFLIGHT_RESOLUTION.yaml',out)
    return out

def main():
    p=argparse.ArgumentParser(); p.add_argument('--stage',required=True); p.add_argument('--work-unit'); p.add_argument('--execution-root'); a=p.parse_args()
    try:
        out=materialize(a.stage,a.work_unit,a.execution_root); print(out['status']+': common preflight resolved '+a.stage)
    except RuntimeContractError as e:
        print('BLOCK: '+str(e)); raise SystemExit(1)
if __name__=='__main__': main()
