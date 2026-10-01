#!/usr/bin/env python3
from __future__ import annotations
import ast, json
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
CI=ROOT/'governance/ci'
LIFE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
REF=ROOT/'.github/governance-source/active/source/10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'
FILES=[
 'stage_runtime_common.py','stage_common_preflight_materializer.py','stage_required_evidence_assembler.py',
 'stage_declared_guard_dispatcher.py','stage_page_lifecycle_audit.py','stage_final_audit_evidence_assembler.py',
 'stage_lifecycle_orchestrator.py','stage_execution_engine.py'
]
TEN={'REQUIRED_FIELD_MANIFEST','FUNCTIONAL_CHAIN_MANIFEST','EFFECTIVE_CONTRACT_OVERLAY','DEPENDENCY_TOPOLOGY','DENOMINATOR_SNAPSHOT','CLASSIFICATION_RULESET','CHANGE_IMPACT_MAP','STAGE_EXECUTION_PREFLIGHT_RECEIPT','CURRENT_PROBLEM_REGISTER','RESOLUTION_LEDGER'}
DECLARED={'VAL-GOV-001','VAL-GOV-004','VAL-GOV-005','VAL-GOV-006','VAL-GOV-007','VAL-GOV-008','VAL-GOV-010','VAL-GOV-013','VAL-GOV-014','VAL-GOV-015','VAL-GOV-016','VAL-GOV-017','VAL-GOV-019','VAL-GOV-020','VAL-GOV-022','VAL-GOV-024','VAL-GOV-025','VAL-GOV-027','VAL-GOV-028','VAL-GOV-029','VAL-GOV-030','VAL-GOV-031'}

def y(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def main():
    failures=[]
    texts={}
    for name in FILES:
        p=CI/name
        if not p.is_file(): failures.append('missing_runtime:'+name); continue
        src=p.read_text(encoding='utf-8'); texts[name]=src
        try: ast.parse(src,filename=name)
        except SyntaxError as e: failures.append('syntax:'+name+':'+str(e))
    pre=texts.get('stage_common_preflight_materializer.py','')
    for uid in sorted(TEN):
        if uid not in pre: failures.append('preflight_identity_missing:'+uid)
    disp=texts.get('stage_declared_guard_dispatcher.py','')
    for uid in sorted(DECLARED):
        if uid not in disp: failures.append('declared_guard_missing:'+uid)
    rr=y(REF)
    current_declared={str(r.get('validator_uid')) for r in rr.get('validator_identities') or [] if isinstance(r,dict) and r.get('identity_mode')=='DECLARED_STAGE_GUARD'}
    if DECLARED-current_declared: failures.append('declared_guard_registry_drift:'+repr(sorted(DECLARED-current_declared)))
    life=y(LIFE); stages=life.get('stages') or []
    if isinstance(stages,dict): stage_rows=list(stages.values())
    else: stage_rows=stages
    if len(stage_rows)!=11: failures.append('stage_denominator:'+str(len(stage_rows)))
    evid=set()
    for st in stage_rows:
        if isinstance(st,dict): evid.update(map(str,st.get('required_evidence') or []))
    if len(evid)!=13: failures.append('required_evidence_identity_denominator:'+str(len(evid))+':'+repr(sorted(evid)))
    engine=texts.get('stage_execution_engine.py','')
    for token in ['PRE_CLOSE_CANDIDATE','POST_CLOSE_FINAL','terminal_disposition','governance_load_receipt_ref']:
        if token not in engine: failures.append('engine_contract_token_missing:'+token)
    orch=texts.get('stage_lifecycle_orchestrator.py','')
    # Stage-1 physical guard and its runtime context must hash the four Mother files
    # with the exact same byte separators: NUL between path/hash and LF between rows.
    # A double-escaped separator hashes literal backslash characters and will always
    # drift from governance_stage1_pipeline_guard.py.
    if '}\\\\0{' in orch: failures.append('stage1_normative_hash_literal_backslash_nul')
    if '"\\\\n".join(rows)' in orch: failures.append('stage1_normative_hash_literal_backslash_newline')
    if '}\\0{' not in orch: failures.append('stage1_normative_hash_nul_separator_missing')
    if '"\\n".join(rows)' not in orch: failures.append('stage1_normative_hash_newline_separator_missing')
    for token in ['SUCCESSOR_MATERIALIZATION_INTENT','CLOSURE_COMMIT_CANDIDATE','EXTERNAL_APPROVAL_REQUIRED','WORK_UNIT_RESOLUTION_REQUIRED','governance_head']:
        if token not in orch: failures.append('orchestrator_contract_token_missing:'+token)
    if "ACPOS_CURRENT_GOVERNANCE_UID" not in engine or "ACPOS_CURRENT_GOVERNANCE_HEAD" not in engine:
        failures.append('executor_current_governance_environment_binding_missing')
    result={'artifact_type':'THREE_LAYER_CONTRACT_VALIDATION','stage_count':len(stage_rows),'required_evidence_identity_count':len(evid),'declared_guard_count':len(DECLARED),'runtime_file_count':len(FILES),'failures':failures,'status':'PASS' if not failures else 'FAIL'}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if not failures else 1)
if __name__=='__main__': main()
