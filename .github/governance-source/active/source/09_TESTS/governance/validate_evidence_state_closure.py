#!/usr/bin/env python3
from pathlib import Path
import json,yaml
ROOT=Path(__file__).resolve().parents[2]

def load_yaml(path):
    return yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}

def validate(root=ROOT):
    root=Path(root); failures=[]
    readme=(root/'README.md').read_text(encoding='utf-8')
    review=load_yaml(root/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml')
    bp=load_yaml(root/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml')
    stage=load_yaml(root/'10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml')
    bdoc=(root/'12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md').read_text(encoding='utf-8')
    idoc=(root/'12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md').read_text(encoding='utf-8')
    edoc=(root/'12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md').read_text(encoding='utf-8')
    adoc=(root/'12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md').read_text(encoding='utf-8')
    repo=root.parents[3]
    regp=repo/'governance/specifications/REGISTRY.yaml'
    if not regp.is_file():
        return {'status':'FAIL','failures':['current_registry_missing']}
    reg=load_yaml(regp); ident=reg.get('governance_identity') or {}; vc=reg.get('candidate_validation_contract') or {}

    if 'GITHUB PRIOR-PHASE REPLAY PENDING' in readme.upper():
        failures.append('readme_superseded_github_replay_pending')
    retired=[
      '11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml',
      '11_EVIDENCE/audit/GOVERNANCE_DEFECT_LEDGER.yaml',
      '11_EVIDENCE/audit/GITHUB_REPLAY_CLOSURE_RESULT.yaml',
      '11_EVIDENCE/audit/HIGH_PRESSURE_HARDENING_RESULT.yaml',
      '11_EVIDENCE/audit/REFERENCE_SEMANTIC_REPAIR_RESULT.yaml',
    ]
    present=[x for x in retired if (root/x).exists()]
    if present:
        failures.append('retired_evidence_reappeared_as_current:'+repr(present))

    if reg.get('registry_role')!='GOVERNANCE_REVISION_CANDIDATE_ENTRYPOINT' or ident.get('status')!='CANDIDATE' or ident.get('released_immutable_identity') is not False:
        failures.append('current_candidate_truth_invalid')
    for key in ('exact_candidate_head_required','required_workflows_run_on_every_candidate_push','live_branch_head_must_equal_validation_head','live_branch_head_recheck_after_evidence_validation_required'):
        if vc.get(key) is not True:
            failures.append('current_exact_head_contract_missing:'+key)
    if vc.get('prior_head_workflow_result_may_credit_successor_head') is not False or vc.get('zero_required_workflow_runs_on_successor_head')!='BLOCK':
        failures.append('current_exact_head_credit_guard_invalid')

    human=review.get('required_review_plan') or []
    if len(human)!=1 or human[0].get('status')!='PENDING':
        failures.append('human_formal_review_not_pending')
    if (review.get('progress') or {}).get('approved')!=0:
        failures.append('human_formal_review_auto_approved')

    sync=bp.get('current_test_evidence_sync_contract') or {}
    if sync.get('superseded_pending_state_drift')!='BLOCK' or sync.get('exact_head_required_workflow_receipts_required') is not True:
        failures.append('evidence_state_closure_contract_missing')
    if sync.get('current_validation_truth_source')!='EXACT_HEAD_REQUIRED_WORKFLOW_RECEIPTS':
        failures.append('evidence_state_current_truth_source_invalid')
    if sync.get('retired_candidate_state_required_for_current_validation') is not False or sync.get('retired_github_replay_closure_required_for_current_validation') is not False:
        failures.append('retired_evidence_required_by_current_contract')

    stages={x.get('stage_uid'):x for x in stage.get('stages') or []}
    s2=stages.get('STAGE-02') or {}
    if s2.get('name')!='PAGE_FUNCTIONAL_CONTRACT':
        failures.append('stage02_identity_missing')
    need_ops={'FUNCTIONAL_CHAIN_COMPILE','DEPENDENCY_MAP_COMPILE','PAGE_CONSTRUCTION_SPEC_COMPILE','ASYNC_PROVIDER_CONTRACT_COMPILE','SHARED_OWNER_PORT_RESOLVE'}
    if not need_ops.issubset(set(s2.get('operations') or [])):
        failures.append('stage02_logic_operations_incomplete')
    need_out={'FUNCTIONAL_CHAIN_SPEC','DEPENDENCY_MAP','PAGE_CONSTRUCTION_SPEC_PACKAGE','ASYNC_PROVIDER_CONTRACT','SHARED_OWNER_PORT_MAP'}
    if not need_out.issubset(set(s2.get('outputs') or [])):
        failures.append('stage02_logic_outputs_incomplete')
    need_val={'FUNCTIONAL_CONTRACT_GUARD','DEPENDENCY_CONTINUITY_GUARD'}
    if not need_val.issubset(set(s2.get('validator_names') or [])):
        failures.append('stage02_logic_validators_incomplete')

    chain='Business Intent -> Preconditions -> Entry -> Operator/System Input Source -> Control/Trigger -> Gate -> Permission -> Action -> Validation -> Payload -> API/Entry -> Runtime Owner -> Repository/Data/Provider -> Audit Event -> Response -> UI/Caller Feedback -> Success State -> Next State -> Next Step -> Next Gate -> Failure State -> Retry/Recovery/Rollback -> Terminal Outcome'
    if chain not in bdoc:
        failures.append('functional_chain_full_logic_contract_missing')
    for token in ('AUTO_REMEDIABLE','IMPLEMENTATION_GAP','INPUT_SOURCE_GAP','AUTHORITY_GAP','ARCHITECTURE_GAP','STATE_TRANSITION_LEDGER'):
        if token not in bdoc: failures.append('functional_gap_or_transition_rule_missing:'+token)
    for token in ('SECOND_SYSTEM_GUARD','Entry -> UI -> Control -> Action -> Validation -> Permission -> Runtime -> Data/Provider -> Audit -> Response -> Feedback -> Test -> Evidence -> Closure'):
        if token not in edoc: failures.append('execution_system_guard_missing:'+token)
    for token in ('Cross-page / System Logic Slice Test','Permission Continuity','State Transition','Data Consistency','Navigation / Routing','Error / Retry / Resume','Audit Continuity'):
        if token not in idoc: failures.append('cross_page_system_logic_slice_missing:'+token)
    if 'Critical Orphan = 0' not in idoc:
        failures.append('critical_orphan_zero_rule_missing')
    if 'superseded `PENDING`' not in adoc:
        failures.append('audit_stale_pending_closure_rule_missing')

    return {
      'status':'PASS' if not failures else 'FAIL',
      'failures':failures,
      'current_truth_source':'governance/specifications/REGISTRY.yaml + exact-head workflow receipts',
      'retired_evidence_present':present,
      'stage02_logic_detector':{
        'functional_chain':True,'dependency':True,'permission_runtime_data':True,
        'cross_page_system_slice':True,'error_retry_resume':True,'second_system_guard':True,'orphan_guard':True
      }
    }

if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
