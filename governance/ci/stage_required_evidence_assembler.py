#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from stage_runtime_common import *

HUMAN={'VISUAL_REVIEW_EVIDENCE','DESIGN_APPROVAL_EVIDENCE'}
FINAL_AUDIT='FINAL_AUDIT_EVIDENCE'
SOURCE_OPS={
 'SOURCE_ENUMERATION_EVIDENCE':['SOURCE_STRUCTURE_ENUMERATION','SOURCE_SEGMENT_MAPPING'],
 'CONFLICT_DECISION_EVIDENCE':['SOURCE_SUPERSESSION_CONFLICT_RESOLUTION'],
 'OPERATIONS_EVIDENCE':['OP-50-MONITORING_VERIFICATION','OP-51-BACKUP_VERIFICATION','OP-52-ROLLBACK_VERIFICATION'],
}

def _receipt(root,work,op):
    b=(work.get('operation_bindings') or {}).get(op) or {}
    ref=str(b.get('operation_receipt_ref') or '')
    if not ref: fail('OPERATION_RECEIPT_BINDING_MISSING:'+op)
    p=safe_ref(root,ref); required_file(p,'OPERATION_RECEIPT:'+op); d=load_yaml(p)
    if d.get('operation_uid')!=op or d.get('status') not in {'PASS','NOT_APPLICABLE_WITH_PROOF'}: fail('OPERATION_RECEIPT_INVALID:'+op)
    return ref,sha256_file(p),d

def _human_path(work_dir,uid):
    direct=work_dir/(uid+'.yaml'); req=work_dir/'EVIDENCE/REQUIRED'/(uid+'.yaml')
    return direct if direct.is_file() else req

def assemble(stage_uid,work_ref=None,root_arg=None):
    root=execution_root(root_arg); root,wp,work,sp,scope,statep,state=work_unit_context(stage_uid,work_ref,root)
    stage=stage_definition(stage_uid); required=list(map(str,stage.get('required_evidence') or []))
    bindings=[]; outdir=wp.parent/'EVIDENCE/REQUIRED'; outdir.mkdir(parents=True,exist_ok=True)
    for uid in required:
        if uid in HUMAN:
            p=_human_path(wp.parent,uid)
            if p.is_file():
                required_file(p,'HUMAN_EVIDENCE:'+uid); d=load_yaml(p)
                ok=(d.get('status')=='PASS' or d.get('result') in {'APPROVE','PASS'}) and d.get('approved_by_human',True) is not False
                status='PASS' if ok else 'BLOCKED'; digest=sha256_file(p)
            else:
                status='PENDING_HUMAN'; digest=''
            bindings.append({'evidence_uid':uid,'producer_class':'HUMAN_GATE_EVIDENCE','physical_ref':str(p.relative_to(root)),'source_operations':[],'prerequisites':[],'assembler_owner':None,'status':status,'sha256':digest,'authority_evidence_ref':''})
            continue
        if uid==FINAL_AUDIT:
            p=outdir/(uid+'.yaml'); status='PASS' if p.is_file() else 'PENDING_FINAL_AUDIT_ASSEMBLY'
            bindings.append({'evidence_uid':uid,'producer_class':'FINAL_AUDIT_EVIDENCE_ASSEMBLER','physical_ref':str(p.relative_to(root)),'source_operations':list(map(str,stage.get('operations') or [])),'prerequisites':['PAGE_LIFECYCLE_AUDIT','OPERATIONS_EVIDENCE'],'assembler_owner':'governance/ci/stage_final_audit_evidence_assembler.py','status':status,'sha256':sha256_file(p) if p.is_file() else '','authority_evidence_ref':''})
            continue
        ops=SOURCE_OPS.get(uid) or list(map(str,stage.get('operations') or [])); recs=[]
        for op in ops:
            ref,h,d=_receipt(root,work,op); recs.append({'operation_uid':op,'receipt_ref':ref,'sha256':h,'status':d.get('status')})
        p=outdir/(uid+'.yaml')
        atomic_yaml(p,{'artifact_type':uid,'evidence_uid':uid,'stage_uid':stage_uid,'work_unit_uid':work.get('work_unit_uid'),'governed_unit_uid':work.get('governed_unit_uid'),'governance_uid':work.get('governance_uid'),'producer_class':'COMMON_REQUIRED_EVIDENCE_ASSEMBLER','source_operation_receipts':recs,'status':'PASS','product_completion_credit':0})
        bindings.append({'evidence_uid':uid,'producer_class':'COMMON_REQUIRED_EVIDENCE_ASSEMBLER','physical_ref':str(p.relative_to(root)),'source_operations':ops,'prerequisites':[],'assembler_owner':'governance/ci/stage_required_evidence_assembler.py','status':'PASS','sha256':sha256_file(p),'authority_evidence_ref':''})
    manifest={'artifact_type':'REQUIRED_EVIDENCE_BINDING_MANIFEST','stage_uid':stage_uid,'work_unit_uid':work.get('work_unit_uid'),'governance_uid':work.get('governance_uid'),'denominator_source':'.github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml#stages[*].required_evidence','bindings':bindings,'required_evidence_count':len(required),'status':'PASS' if all(b['status']=='PASS' for b in bindings) else 'BLOCKED'}
    atomic_yaml(wp.parent/'REQUIRED_EVIDENCE_BINDING_MANIFEST.yaml',manifest); return manifest

def main():
    p=argparse.ArgumentParser(); p.add_argument('--stage',required=True); p.add_argument('--work-unit'); p.add_argument('--execution-root'); a=p.parse_args()
    try:
        out=assemble(a.stage,a.work_unit,a.execution_root); print(out['status']+': required evidence bindings '+a.stage)
    except RuntimeContractError as e:
        print('BLOCK: '+str(e)); raise SystemExit(1)
if __name__=='__main__': main()
