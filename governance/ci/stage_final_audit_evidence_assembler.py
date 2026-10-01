#!/usr/bin/env python3
from __future__ import annotations
import argparse
from stage_runtime_common import *

CONSTITUENTS=[
 'EVIDENCE/PAGE_LIFECYCLE_AUDIT.yaml',
 'EVIDENCE/REQUIRED/OPERATIONS_EVIDENCE.yaml',
 'OUTPUTS/FINAL_PRODUCTION_ACCEPTANCE_RESULT.yaml',
 'OUTPUTS/GOVERNED_UNIT_CLOSED.yaml',
 'OUTPUTS/NEXT_GOVERNED_UNIT_ELIGIBILITY.yaml',
]

def assemble(stage_uid='STAGE-11',work_ref=None,root_arg=None):
    if stage_uid!='STAGE-11': fail('FINAL_AUDIT_ASSEMBLER_STAGE11_ONLY')
    root=execution_root(root_arg); root,wp,work,sp,scope,statep,state=work_unit_context(stage_uid,work_ref,root)
    rows=[]
    for rel in CONSTITUENTS:
        p=wp.parent/rel; required_file(p,'FINAL_AUDIT_CONSTITUENT:'+rel)
        rows.append({'ref':str(p.relative_to(root)),'sha256':sha256_file(p)})
    doc={'artifact_type':'FINAL_AUDIT_EVIDENCE','stage_uid':'STAGE-11','work_unit_uid':work.get('work_unit_uid'),'governed_unit_uid':work.get('governed_unit_uid'),'governance_uid':work.get('governance_uid'),'assembler_owner':'governance/ci/stage_final_audit_evidence_assembler.py','constituents':rows,'validator_results_used_as_input':False,'status':'PASS','product_completion_credit':0}
    atomic_yaml(wp.parent/'EVIDENCE/REQUIRED/FINAL_AUDIT_EVIDENCE.yaml',doc); return doc

def main():
    p=argparse.ArgumentParser(); p.add_argument('--stage',default='STAGE-11'); p.add_argument('--work-unit'); p.add_argument('--execution-root'); a=p.parse_args()
    try:
        assemble(a.stage,a.work_unit,a.execution_root); print('PASS: final audit evidence assembled')
    except RuntimeContractError as e:
        print('BLOCK: '+str(e)); raise SystemExit(1)
if __name__=='__main__': main()
