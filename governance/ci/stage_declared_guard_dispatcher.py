#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from stage_runtime_common import *

GUARDS={
'VAL-GOV-001':'ACCEPTANCE_BLUEPRINT_CURRENT_AND_COMPLETE','VAL-GOV-004':'DEPENDENCY_CONTINUITY_EXACT',
'VAL-GOV-005':'DEPLOYMENT_IDENTITY_MATCH','VAL-GOV-006':'DESIGN_FREEZE_COMPLETE','VAL-GOV-007':'FINAL_PRODUCTION_ACCEPTANCE_COMPLETE',
'VAL-GOV-008':'FUNCTIONAL_CONTRACT_COMPLETE','VAL-GOV-010':'IMPLEMENTATION_CONTRACT_COMPLETE','VAL-GOV-013':'MIGRATION_COMPATIBILITY_PASS',
'VAL-GOV-014':'PRODUCTION_ACCEPTANCE_DIMENSIONS_COMPLETE','VAL-GOV-015':'PRODUCTION_CUTOVER_COMPLETE','VAL-GOV-016':'GOVERNED_UNIT_CLOSURE_COMPLETE',
'VAL-GOV-017':'PRODUCTION_RENDER_IDENTITY_MATCH','VAL-GOV-019':'PROGRAM_PROFILE_COMPLIANT','VAL-GOV-020':'QA_ACCEPTANCE_COMPLETE',
'VAL-GOV-022':'RELEASE_CANDIDATE_COMPLETE','VAL-GOV-024':'SECURITY_FRESHNESS_CURRENT','VAL-GOV-025':'SOURCE_FACT_CONTRACT_COMPLETE',
'VAL-GOV-027':'STAGING_ACCEPTANCE_COMPLETE','VAL-GOV-028':'STAGING_APPLICABILITY_RESOLVED','VAL-GOV-029':'VISUAL_DOMAIN_COMPLETE',
'VAL-GOV-030':'VISUAL_GEOMETRY_VALID','VAL-GOV-031':'WORK_UNIT_CLOSURE_VALID'}

def _out(work_dir,uid):
    a=work_dir/(uid+'.yaml'); b=work_dir/'OUTPUTS'/(uid+'.yaml')
    return a if a.is_file() else b

def _identity(uid):
    rr=load_yaml(REFERENCE_RULES)
    for row in rr.get('validator_identities') or []:
        if isinstance(row,dict) and row.get('validator_uid')==uid: return row
    fail('VALIDATOR_IDENTITY_NOT_REGISTERED:'+uid)

def evaluate(stage_uid,validator_uid,phase,work_ref=None,root_arg=None):
    if validator_uid not in GUARDS: fail('DECLARED_GUARD_NOT_DISPATCHABLE:'+validator_uid)
    ident=_identity(validator_uid)
    if ident.get('identity_mode')!='DECLARED_STAGE_GUARD' or ident.get('implementation_path') not in {None,''}: fail('VALIDATOR_IDENTITY_MODE_DRIFT:'+validator_uid)
    root=execution_root(root_arg); root,wp,work,sp,scope,statep,state=work_unit_context(stage_uid,work_ref,root); stage=stage_definition(stage_uid)
    if validator_uid not in set(map(str,stage.get('validators') or [])): fail('VALIDATOR_NOT_OWNED_BY_STAGE:'+validator_uid)
    findings=[]
    for uid in map(str,stage.get('inputs') or []):
        row=(work.get('input_bindings') or {}).get(uid)
        if not isinstance(row,dict): findings.append('INPUT_BINDING_MISSING:'+uid); continue
        st=row.get('status')
        if st=='MATERIALIZED':
            try: required_file(safe_ref(root,str(row.get('artifact_ref') or '')),'INPUT:'+uid)
            except RuntimeContractError as e: findings.append(str(e))
        elif st=='AUTHORIZED_NOT_APPLICABLE':
            if not row.get('authority_evidence_ref'): findings.append('INPUT_NA_AUTHORITY_MISSING:'+uid)
        elif st!='EXTERNAL_RECEIPT': findings.append('INPUT_NOT_READY:'+uid+':'+str(st))
    for op in map(str,stage.get('operations') or []):
        ref=str(((work.get('operation_bindings') or {}).get(op) or {}).get('operation_receipt_ref') or '')
        try:
            d=load_yaml(safe_ref(root,ref))
            if d.get('status') not in {'PASS','NOT_APPLICABLE_WITH_PROOF'}: findings.append('OPERATION_NOT_PASS:'+op)
        except RuntimeContractError as e: findings.append(str(e))
    for uid in map(str,stage.get('outputs') or []):
        try: required_file(_out(wp.parent,uid),'OUTPUT:'+uid)
        except RuntimeContractError as e: findings.append(str(e))
    for dim,b in (work.get('scanner_bindings') or {}).items():
        try:
            d=load_yaml(safe_ref(root,str((b or {}).get('result_owner') or '')))
            if d.get('status')!='PASS': findings.append('SCANNER_NOT_PASS:'+str(dim))
        except RuntimeContractError as e: findings.append(str(e))
    try:
        m=load_yaml(wp.parent/'REQUIRED_EVIDENCE_BINDING_MANIFEST.yaml')
        binds={str(x.get('evidence_uid')):x for x in m.get('bindings') or [] if isinstance(x,dict)}
        expected=set(map(str,stage.get('required_evidence') or []))
        if set(binds)!=expected: findings.append('REQUIRED_EVIDENCE_DENOMINATOR_DRIFT')
        for uid in expected:
            st=str((binds.get(uid) or {}).get('status') or '')
            if phase=='PRE_CLOSE_CANDIDATE' and stage_uid in {'STAGE-03','STAGE-04'} and uid in {'VISUAL_REVIEW_EVIDENCE','DESIGN_APPROVAL_EVIDENCE'} and st in {'PENDING_HUMAN','BLOCKED'}: continue
            if st!='PASS': findings.append('REQUIRED_EVIDENCE_NOT_PASS:'+uid+':'+st)
    except RuntimeContractError as e: findings.append(str(e))
    try:
        pr=load_yaml(wp.parent/'CURRENT_PROBLEM_REGISTER.yaml')
        if int(pr.get('open_problem_total',0)) or int(pr.get('closure_blocker_total',0)): findings.append('OPEN_PROBLEM_OR_BLOCKER')
    except Exception as e: findings.append('CURRENT_PROBLEM_REGISTER_INVALID:'+str(e))
    status=str(state.get('status') or '')
    if phase=='POST_CLOSE_FINAL':
        if status!='CLOSED_PASS': findings.append('STATE_NOT_CLOSED_PASS:'+status)
    else:
        allowed={'EXECUTION_COMPLETE_CLOSURE_PENDING'}
        if stage_uid in {'STAGE-03','STAGE-04'}: allowed.add('BLOCKED')
        if status not in allowed: findings.append('STATE_NOT_PRE_CLOSE:'+status)
    return {'artifact_type':'VALIDATOR_RESULT','validator_uid':validator_uid,'guard_contract_id':GUARDS[validator_uid],'stage_uid':stage_uid,'work_unit_uid':work.get('work_unit_uid'),'validation_phase':phase,'status':'PASS' if not findings else 'FAIL','findings':findings,'read_only':True}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--stage',required=True); p.add_argument('--validator',required=True); p.add_argument('--validation-phase',choices=['PRE_CLOSE_CANDIDATE','POST_CLOSE_FINAL'],default='PRE_CLOSE_CANDIDATE'); p.add_argument('--work-unit'); p.add_argument('--execution-root'); a=p.parse_args()
    try:
        out=evaluate(a.stage,a.validator,a.validation_phase,a.work_unit,a.execution_root); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
    except RuntimeContractError as e:
        print(json.dumps({'artifact_type':'VALIDATOR_RESULT','validator_uid':a.validator,'stage_uid':a.stage,'status':'FAIL','findings':[str(e)],'read_only':True},ensure_ascii=False,indent=2)); raise SystemExit(1)
if __name__=='__main__': main()
