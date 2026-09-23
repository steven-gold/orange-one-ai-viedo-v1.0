#!/usr/bin/env python3
from pathlib import Path
import json,yaml,re
ROOT=Path(__file__).resolve().parents[2]

def load_yaml(path):
    return yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}

def validate(root=ROOT):
    root=Path(root); failures=[]
    readme=(root/'README.md').read_text(encoding='utf-8')
    state=load_yaml(root/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml')
    defects=load_yaml(root/'11_EVIDENCE/audit/GOVERNANCE_DEFECT_LEDGER.yaml')
    closure=load_yaml(root/'11_EVIDENCE/audit/GITHUB_REPLAY_CLOSURE_RESULT.yaml')
    review=load_yaml(root/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml')
    bp=load_yaml(root/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml')
    stage=load_yaml(root/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml')
    bdoc=(root/'12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md').read_text(encoding='utf-8')
    idoc=(root/'12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md').read_text(encoding='utf-8')
    edoc=(root/'12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md').read_text(encoding='utf-8')
    adoc=(root/'12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md').read_text(encoding='utf-8')

    if 'GITHUB PRIOR-PHASE REPLAY PENDING' in readme.upper(): failures.append('readme_superseded_github_replay_pending')

    pe=state.get('preformal_execution') or {}
    if pe.get('github_prior_phase_replay')!='SUCCESS' or pe.get('github_prior_phase_replay_run_id')!=34734265713:
        failures.append('candidate_prior_phase_replay_not_closed')
    if pe.get('github_successor_replay')!='SUCCESS' or pe.get('github_successor_replay_run_id')!=34734730080:
        failures.append('candidate_successor_replay_not_closed')
    if pe.get('github_page_replay_content_audit')!='SUCCESS' or pe.get('github_page_replay_content_audit_run_id')!=34734730080:
        failures.append('candidate_content_audit_not_closed')
    if state.get('formal_test_started') is not False: failures.append('formal_test_started')
    claim=str(state.get('completion_claim',''))
    if not claim.startswith('PREFORMAL_V') or 'FORMAL_FREEZE' in claim or 'PRODUCTION_RELEASE' in claim:
        failures.append('candidate_completion_claim_invalid')

    bad=[]
    for rec in defects.get('defects') or []:
        uid=str(rec.get('defect_uid','')); st=str(rec.get('status',''))
        # This predecessor validator owns only the v2.1.8/v2.1.9 evidence-state closure lineage.
        # Later legal successor defects may legitimately remain pending their own GitHub replay.
        if uid.startswith(('DEF-V218-','DEF-V219-')) and ('GITHUB_REPLAY_PENDING' in st or 'FIXED_PREFORMAL_REVERIFY_PENDING' in st):
            bad.append((uid,st))
    if bad: failures.append('superseded_defect_pending_states:'+str(bad))
    v219=[x for x in defects.get('defects') or [] if x.get('defect_uid')=='DEF-V219-IMMUTABLE-PACKAGE-EVIDENCE-STATE-DRIFT-001']
    if len(v219)!=1 or v219[0].get('status')!='FIXED_PREFORMAL_VERIFIED':
        failures.append('v219_defect_record_missing_or_wrong_status')

    if closure.get('status')!='PASS': failures.append('github_replay_closure_evidence_not_pass')
    ev=closure.get('evidence') or {}
    expected={
      'v218_successor_linkage_final':(34733833659,'SUCCESS_6_OF_6'),
      'pre_page_replay':(34734265713,'SUCCESS_5_OF_5'),
      'page_blueprint_replay_after_hash_correction':(34734528373,'SUCCESS_6_OF_6'),
      'page_replay_content_audit_closure':(34734730080,'SUCCESS_7_OF_7'),
    }
    for k,(rid,res) in expected.items():
        rec=ev.get(k) or {}
        if rec.get('run_id')!=rid or rec.get('result')!=res or not rec.get('head_sha'):
            failures.append('closure_evidence_identity_drift:'+k)
    ss=closure.get('stale_state_closure') or {}
    if ss.get('github_replay_pending_remaining')!=0 or ss.get('fixed_preformal_reverify_pending_remaining')!=0:
        failures.append('closure_stale_state_count_nonzero')
    if ss.get('human_formal_review_pending_preserved') is not True:
        failures.append('closure_human_review_pending_not_preserved')
    if ss.get('formal_test_executed') is not False or ss.get('formal_freeze_claimed') is not False or ss.get('production_release_claimed') is not False:
        failures.append('closure_overclaims_formal_or_release')

    human=review.get('required_review_plan') or []
    if len(human)!=1 or human[0].get('status')!='PENDING':
        failures.append('human_formal_review_not_pending')
    if (review.get('progress') or {}).get('approved')!=0:
        failures.append('human_formal_review_auto_approved')

    sync=(bp.get('current_test_evidence_sync_contract') or {})
    if sync.get('superseded_pending_state_drift')!='BLOCK' or sync.get('github_replay_closure_evidence_required') is not True:
        failures.append('evidence_state_closure_contract_missing')

    stages={x.get('stage_uid'):x for x in stage.get('stages') or []}
    s2=stages.get('STAGE-02') or {}
    if s2.get('name')!='PAGE_FUNCTIONAL_CONTRACT': failures.append('stage02_identity_missing')
    need_ops={'FUNCTIONAL_CHAIN_COMPILE','DEPENDENCY_MAP_COMPILE','PAGE_CONSTRUCTION_SPEC_COMPILE','ASYNC_PROVIDER_CONTRACT_COMPILE','SHARED_OWNER_PORT_RESOLVE'}
    if not need_ops.issubset(set(s2.get('operations') or [])): failures.append('stage02_logic_operations_incomplete')
    need_out={'FUNCTIONAL_CHAIN_SPEC','DEPENDENCY_MAP','PAGE_CONSTRUCTION_SPEC_PACKAGE','ASYNC_PROVIDER_CONTRACT','SHARED_OWNER_PORT_MAP'}
    if not need_out.issubset(set(s2.get('outputs') or [])): failures.append('stage02_logic_outputs_incomplete')
    need_val={'FUNCTIONAL_CONTRACT_GUARD','DEPENDENCY_CONTINUITY_GUARD'}
    if not need_val.issubset(set(s2.get('validator_names') or [])): failures.append('stage02_logic_validators_incomplete')

    chain='Business Intent -> Preconditions -> Entry -> Operator/System Input Source -> Control/Trigger -> Gate -> Permission -> Action -> Validation -> Payload -> API/Entry -> Runtime Owner -> Repository/Data/Provider -> Audit Event -> Response -> UI/Caller Feedback -> Success State -> Next State -> Next Step -> Next Gate -> Failure State -> Retry/Recovery/Rollback -> Terminal Outcome'
    if chain not in bdoc: failures.append('functional_chain_full_logic_contract_missing')
    for token in ('AUTO_REMEDIABLE','IMPLEMENTATION_GAP','INPUT_SOURCE_GAP','AUTHORITY_GAP','ARCHITECTURE_GAP','STATE_TRANSITION_LEDGER'):
        if token not in bdoc: failures.append('functional_gap_or_transition_rule_missing:'+token)
    for token in ('SECOND_SYSTEM_GUARD','Entry -> UI -> Control -> Action -> Validation -> Permission -> Runtime -> Data/Provider -> Audit -> Response -> Feedback -> Test -> Evidence -> Closure'):
        if token not in edoc: failures.append('execution_system_guard_missing:'+token)
    for token in ('Cross-page / System Logic Slice Test','Permission Continuity','State Transition','Data Consistency','Navigation / Routing','Error / Retry / Resume','Audit Continuity'):
        if token not in idoc: failures.append('cross_page_system_logic_slice_missing:'+token)
    if 'Critical Orphan = 0' not in idoc: failures.append('critical_orphan_zero_rule_missing')
    if 'superseded `PENDING`' not in adoc and 'superseded `PENDING`' not in adoc.replace('`','`'):
        failures.append('audit_stale_pending_closure_rule_missing')

    return {'status':'PASS' if not failures else 'FAIL','failures':failures,
            'stage02_logic_detector':{
              'functional_chain':True,'dependency':True,'permission_runtime_data':True,
              'cross_page_system_slice':True,'error_retry_resume':True,'second_system_guard':True,'orphan_guard':True
            }}

if __name__=='__main__':
    out=validate()
    print(json.dumps(out,ensure_ascii=False,indent=2))
    raise SystemExit(0 if out['status']=='PASS' else 1)
