#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from stage_runtime_common import *

STAGE_ORDER=[f'STAGE-{i:02d}' for i in range(1,12)]

def build_denominator(governed_unit_uid):
    _,stages=lifecycle_stages(); rows=[]
    for sid in STAGE_ORDER:
        st=stages.get(sid)
        if not st: fail('LIFECYCLE_STAGE_MISSING:'+sid)
        for op in map(str,st.get('operations') or []):
            rows.append({'stage_uid':sid,'operation_uid':op,'applicability':'REQUIRED'})
    return rows

def audit(root_arg,governed_unit_uid,stage_work_units,final=False):
    root=execution_root(root_arg); rows=build_denominator(governed_unit_uid); out=[]
    for row in rows:
        sid=row['stage_uid']; wref=stage_work_units.get(sid)
        if not wref:
            out.append({**row,'status':'MISSING_WORK_UNIT','upstream_evidence_ref':'','downstream_evidence_ref':'','step_revision':'','skipped':False,'skip_reason':''}); continue
        wp=safe_ref(root,wref); work=load_yaml(wp)
        b=(work.get('operation_bindings') or {}).get(row['operation_uid']) or {}; rref=str(b.get('operation_receipt_ref') or '')
        try:
            rp=safe_ref(root,rref); rec=load_yaml(rp); status='PASS' if rec.get('status') in {'PASS','NOT_APPLICABLE_WITH_PROOF'} else 'FAIL'; digest=sha256_file(rp)
        except RuntimeContractError:
            status='MISSING_RECEIPT'; digest=''
        out.append({**row,'status':status,'upstream_evidence_ref':rref,'downstream_evidence_ref':'','step_revision':digest,'skipped':False,'skip_reason':''})
    passed=sum(1 for r in out if r['status']=='PASS'); total=len(out)
    return {'artifact_type':'PAGE_LIFECYCLE_AUDIT' if final else 'PAGE_LIFECYCLE_AUDIT_CANDIDATE','governed_unit_uid':governed_unit_uid,'denominator_source':'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml#stages[*].operations','ordered_rows':out,'total_required_lifecycle_steps':total,'passed_required_lifecycle_steps':passed,'status':'PASS' if passed==total else 'BLOCKED','product_completion_credit':0}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--execution-root',required=True); p.add_argument('--governed-unit',required=True); p.add_argument('--stage-work-unit',action='append',default=[]); p.add_argument('--output',required=True); p.add_argument('--final',action='store_true'); a=p.parse_args()
    m={}
    for item in a.stage_work_unit:
        if '=' not in item: raise SystemExit('stage-work-unit must be STAGE-XX=path')
        k,v=item.split('=',1); m[k]=v
    try:
        doc=audit(a.execution_root,a.governed_unit,m,a.final); atomic_yaml(Path(a.output),doc); print(doc['status']+f": page lifecycle {doc['passed_required_lifecycle_steps']}/{doc['total_required_lifecycle_steps']}")
    except RuntimeContractError as e:
        print('BLOCK: '+str(e)); raise SystemExit(1)
if __name__=='__main__': main()
