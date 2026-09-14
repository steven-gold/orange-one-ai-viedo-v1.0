#!/usr/bin/env python3
from pathlib import Path
import json,yaml
ROOT=Path(__file__).resolve().parents[2]
EXPECTED_STAGES=[f'STAGE-{i:02d}' for i in range(1,12)]
EXPECTED_LEDGERS=['EXECUTION_STATE','RUN_MANIFEST','ARTIFACT_PLAN','GOVERNANCE_CURRENT','BRANCH_BASELINE','GOVERNANCE_STAGE_LOCK','SEALED_GOVERNANCE_TEST_BASELINE','STAGE_EVIDENCE','DEPENDENCY_INDEX','REVERSE_DEPENDENCY_INDEX']
EXPECTED_SYNC=['CURRENT_PHASE','ARTIFACT_COUNT','AUTHORITATIVE_HASH','UNRESOLVED_AUTHORITY_IDENTITY','GATE_STATUS','NEXT_LEGAL_TRANSITION','PREDECESSOR_PROOF']
EXPECTED_RECEIPT=['provider','repository_or_project','head_sha','run_id','job_denominator','conclusion']
EXPECTED_AUTHORITY_TUPLE=['gap_uid','authority_ref','disposition','authority_evidence_ref']

def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}

def validate(root=ROOT):
    root=Path(root); failures=[]
    life=load(root/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml')
    bp=load(root/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml')
    idx=load(root/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml')
    s1=load(root/'10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml')
    doc=(root/'12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md').read_text(encoding='utf-8')
    ver=(root/'VERSIONING_RULE.md').read_text(encoding='utf-8')
    inv=((life.get('cross_stage_invariants') or {}).get('closure_evidence_continuity') or {})
    if inv.get('invariant_uid')!='GOV-INV-CLOSURE-EVIDENCE-CONTINUITY-001': failures.append('continuity_invariant_uid_missing')
    if inv.get('normative_section_uid')!='WEB-GOV-03-S058': failures.append('continuity_normative_section_wrong')
    if inv.get('applies_to_stages')!=EXPECTED_STAGES: failures.append('continuity_not_all_stages')
    if inv.get('closure_mutation_semantics')!='MERGE_APPEND_OR_EXPLICIT_SUPERSEDE': failures.append('closure_mutation_not_monotonic')
    if inv.get('legal_successor_presence')!='ALLOW': failures.append('legal_successor_not_allowed')
    if inv.get('retroactive_predecessor_invalidation')!='FORBIDDEN': failures.append('retroactive_invalidation_not_forbidden')
    ps=inv.get('predecessor_validator_successor_state_contract') or {}
    expected_ps={
      'current_state_exact_predecessor_terminal_equality_as_pass_condition':'FORBIDDEN',
      'successor_started_false_as_permanent_pass_condition':'FORBIDDEN',
      'registered_legal_successor_presence':'ALLOW_IF_PREDECESSOR_INVARIANTS_HOLD',
      'illegal_successor_or_stage_skip':'BLOCK',
      'predecessor_completion_must_remain_true':True,
      'predecessor_proof_identity_must_remain_resolvable':True,
      'predecessor_authority_identity_must_remain_stable':True,
      'predecessor_terminal_receipt_must_remain_stable':True,
      'phase_order_owner':'PHASE_BOUNDARY_GATE',
      'validator_scope':'PREDECESSOR_CLOSURE_INVARIANTS_NOT_GLOBAL_CURRENT_STATE',
      'registered_successor_edge_coverage_required':True,
    }
    for k,v in expected_ps.items():
        if ps.get(k)!=v: failures.append('predecessor_successor_state_contract_drift:'+k)
    rei=((life.get('cross_stage_invariants') or {}).get('required_evidence_integrity') or {})
    if rei.get('invariant_uid')!='GOV-INV-REQUIRED-EVIDENCE-INTEGRITY-001': failures.append('required_evidence_integrity_uid_missing')
    if rei.get('applies_to_stages')!=EXPECTED_STAGES: failures.append('required_evidence_integrity_not_all_stages')
    if rei.get('presence_only_acceptance')!='FORBIDDEN' or rei.get('parser_validation_before_materialized_or_closed') is not True or rei.get('schema_or_required_field_validation_before_materialized_or_closed') is not True: failures.append('required_evidence_integrity_contract_incomplete')
    if rei.get('malformed_required_evidence')!='BLOCK' or rei.get('unparseable_required_evidence')!='BLOCK' or rei.get('required_evidence_validator_failure')!='BLOCK': failures.append('required_evidence_integrity_not_fail_closed')
    if inv.get('established_predecessor_fact_deletion')!='BLOCK' or inv.get('established_predecessor_fact_reversion')!='BLOCK': failures.append('predecessor_fact_loss_not_blocked')
    reqfacts=['START_PROOF','COMPLETION_PROOF','SOURCE_OR_CHECKPOINT_IDENTITY','GATE_RESULT','REPLAY_OR_CONTENT_AUDIT_PROOF','RUN_OR_EVIDENCE_IDENTITY']
    if inv.get('required_predecessor_fact_classes')!=reqfacts: failures.append('predecessor_fact_class_set_drift')
    if inv.get('current_ledger_synchronization_required') is not True: failures.append('current_ledger_sync_not_required')
    if inv.get('current_ledgers')!=EXPECTED_LEDGERS: failures.append('current_ledger_set_drift')
    if inv.get('synchronization_dimensions')!=EXPECTED_SYNC: failures.append('sync_dimension_set_drift')
    if inv.get('synchronization_drift')!='BLOCK': failures.append('sync_drift_not_blocked')
    tr=inv.get('terminal_ci_receipt') or {}
    if tr.get('model')!='EXTERNAL_IMMUTABLE_RECEIPT': failures.append('terminal_receipt_model_wrong')
    if tr.get('materialization_and_terminal_receipt_are_distinct') is not True: failures.append('materialization_terminal_not_distinct')
    if tr.get('self_write_same_commit_run_identity')!='FORBIDDEN': failures.append('terminal_receipt_self_write_not_forbidden')
    if tr.get('required_fields')!=EXPECTED_RECEIPT: failures.append('terminal_receipt_field_set_drift')
    if tr.get('receipt_must_bind_exact_head') is not True or tr.get('later_reference_creates_new_head_and_must_not_relabel_prior_receipt') is not True: failures.append('terminal_receipt_head_binding_invalid')
    ua=inv.get('unresolved_authority_identity') or {}
    if ua.get('canonical_tuple_fields')!=EXPECTED_AUTHORITY_TUPLE or ua.get('carry_forward_exact_tuple_required') is not True: failures.append('authority_identity_tuple_contract_drift')
    if ua.get('count_only_or_uid_only_validation')!='BLOCK' or ua.get('authority_evidence_ref_required') is not True or ua.get('explicit_supersession_required_for_tuple_change') is not True: failures.append('authority_identity_fail_closed_contract_drift')
    if tr.get('canonical_projection_required') is not True or tr.get('ledger_projection_required_fields')!=EXPECTED_RECEIPT or tr.get('alias_field_substitution')!='BLOCK' or tr.get('abbreviated_jobs_or_result_is_not_canonical_receipt') is not True: failures.append('terminal_receipt_canonical_projection_contract_drift')
    if inv.get('downstream_revalidation_required') is not True: failures.append('downstream_revalidation_not_required')
    stages=life.get('stages') or []
    if [s.get('stage_uid') for s in stages]!=EXPECTED_STAGES: failures.append('stage_set_drift')
    for st in stages:
        g=st.get('closure_evidence_continuity_gate') or {}
        if g!={'mode':'REQUIRED','invariant_uid':'GOV-INV-CLOSURE-EVIDENCE-CONTINUITY-001','normative_section_uid':'WEB-GOV-03-S058'}:
            failures.append('stage_continuity_gate_missing:'+str(st.get('stage_uid')))
    common=((idx.get('mandatory_common_normative_bundles') or {}).get('BUNDLE-GOV-COMMON-CORE') or {}).get('section_uids') or []
    if 'WEB-GOV-03-S058' not in common: failures.append('continuity_not_loaded_by_common_bundle')
    ab=bp.get('closure_evidence_continuity_contract') or {}
    if ab.get('required') is not True or ab.get('validator_uid')!='VAL-GOV-034' or ab.get('validator_path')!='09_TESTS/governance/validate_closure_evidence_continuity.py': failures.append('acceptance_continuity_validator_binding_missing')
    if ab.get('applies_to_stages')!=EXPECTED_STAGES: failures.append('acceptance_continuity_not_all_stages')
    for k in ('destructive_closure_rewrite','cross_ledger_drift','predecessor_proof_loss','terminal_ci_self_reference'):
        if ab.get(k)!='BLOCK': failures.append('acceptance_fail_closed_missing:'+k)
    if ab.get('external_terminal_receipt_required_fields')!=EXPECTED_RECEIPT: failures.append('acceptance_terminal_field_set_drift')
    if ab.get('unresolved_authority_canonical_identity_fields')!=EXPECTED_AUTHORITY_TUPLE or ab.get('count_only_or_uid_only_authority_validation')!='BLOCK': failures.append('acceptance_authority_tuple_contract_drift')
    if ab.get('terminal_receipt_canonical_projection_required') is not True or ab.get('terminal_receipt_alias_substitution')!='BLOCK' or ab.get('ledger_terminal_receipt_required_fields')!=EXPECTED_RECEIPT: failures.append('acceptance_terminal_projection_contract_drift')
    if ab.get('predecessor_validator_current_state_lock')!='BLOCK' or ab.get('legal_successor_presence_may_not_retroactively_fail_predecessor') is not True or ab.get('phase_order_owner')!='PHASE_BOUNDARY_GATE' or ab.get('registered_successor_edge_coverage_required') is not True: failures.append('acceptance_successor_state_contract_incomplete')
    rei_ab=bp.get('required_evidence_integrity_contract') or {}
    if rei_ab.get('required') is not True or rei_ab.get('applies_to_stages')!=EXPECTED_STAGES or rei_ab.get('presence_only_acceptance')!='BLOCK' or rei_ab.get('parser_validation_required') is not True or rei_ab.get('schema_or_required_field_validation_required') is not True or rei_ab.get('malformed_or_unparseable_required_evidence')!='BLOCK': failures.append('acceptance_required_evidence_integrity_contract_incomplete')
    sc=s1.get('closure_evidence_continuity_contract') or {}
    if sc.get('normative_section_uid')!='WEB-GOV-03-S058' or sc.get('predecessor_started_completed_proofs_monotonic') is not True or sc.get('replay_and_content_audit_proofs_monotonic') is not True or sc.get('destructive_current_ledger_rewrite')!='BLOCK' or sc.get('current_ledger_synchronization_required') is not True or sc.get('terminal_ci_receipt_model')!='EXTERNAL_IMMUTABLE_RECEIPT': failures.append('stage1_continuity_contract_incomplete')
    if sc.get('unresolved_authority_exact_tuple_required') is not True or sc.get('unresolved_authority_canonical_tuple_fields')!=EXPECTED_AUTHORITY_TUPLE or sc.get('terminal_receipt_canonical_projection_required') is not True or sc.get('terminal_receipt_required_fields')!=EXPECTED_RECEIPT or sc.get('terminal_receipt_alias_substitution')!='BLOCK': failures.append('stage1_authority_receipt_projection_contract_incomplete')
    if sc.get('predecessor_validator_current_state_lock')!='FORBIDDEN' or sc.get('legal_successor_must_not_retroactively_fail_predecessor') is not True or sc.get('phase_order_owner')!='PHASE_BOUNDARY_GATE': failures.append('stage1_successor_state_contract_incomplete')
    s1p=s1.get('predecessor_validator_successor_policy') or {}
    if s1p.get('current_state_exact_predecessor_terminal_equality_as_pass_condition')!='FORBIDDEN' or s1p.get('successor_started_false_as_permanent_pass_condition')!='FORBIDDEN' or s1p.get('registered_legal_successor_presence')!='ALLOW_IF_PREDECESSOR_INVARIANTS_HOLD' or s1p.get('illegal_successor_or_phase_skip')!='BLOCK' or s1p.get('phase_order_owner')!='PHASE_BOUNDARY_GATE': failures.append('stage1_predecessor_successor_policy_incomplete')
    s1e=s1.get('required_evidence_integrity_contract') or {}
    if s1e.get('presence_only_acceptance')!='FORBIDDEN' or s1e.get('parser_validation_required_before_materialized_or_closed') is not True or s1e.get('schema_or_required_field_validation_required_before_materialized_or_closed') is not True or s1e.get('malformed_or_unparseable_required_evidence')!='BLOCK': failures.append('stage1_required_evidence_integrity_contract_incomplete')
    up=s1.get('unresolved_external_authority_preservation_contract') or {}
    if up.get('blueprint_carry_must_preserve_exact_identity_fields')!=EXPECTED_AUTHORITY_TUPLE or up.get('count_only_or_uid_only_validation')!='BLOCK' or up.get('authority_evidence_ref_identity_drift')!='BLOCK': failures.append('stage1_authority_exact_tuple_guard_incomplete')
    tokens=['WEB-GOV-03-S058','MERGE_APPEND_OR_EXPLICIT_SUPERSEDE','CURRENT_LEDGER_SYNCHRONIZATION_DRIFT','external immutable receipt','infinite self-reference loop','`STAGE-01` through `STAGE-11`','canonical tuple `gap_uid`, `authority_ref`, `disposition`, and `authority_evidence_ref`','canonical six fields `provider`, `repository_or_project`, `head_sha`, `run_id`, `job_denominator`, and `conclusion`','global Current phase/state to remain exactly equal','Required Evidence is not valid merely because a file/path exists.','Presence-only acceptance is forbidden.']
    for tok in tokens:
        if tok not in doc: failures.append('normative_continuity_text_missing:'+tok)
    for tok in ['v2.1.12','common invariant layer','Count-only, GAP-UID-only','six fields `provider`','Materialization CI evidence and terminal closure CI receipt are distinct','hard-code global Current state equality','Required Evidence presence is not acceptance']:
        if tok not in ver: failures.append('versioning_continuity_rule_missing:'+tok)
    return {'status':'PASS' if not failures else 'FAIL','stage_count':len(stages),'ledger_count':len(inv.get('current_ledgers') or []),'sync_dimensions':len(inv.get('synchronization_dimensions') or []),'terminal_receipt_fields':len(tr.get('required_fields') or []),'failures':failures}

def validate_transition(previous,current):
    """Generic destructive-closure stress model used only by regression tests."""
    failures=[]
    prevfacts=previous.get('predecessor_facts') or {}; curfacts=current.get('predecessor_facts') or {}
    for k,v in prevfacts.items():
        if v in (True,'PASS','SUCCESS') or (v is not None and k.endswith(('_id','_sha','_hash','_proof','_checkpoint'))):
            if k not in curfacts: failures.append('predecessor_fact_deleted:'+k)
            elif curfacts.get(k) in (False,None,'FAIL','BLOCKED','') and curfacts.get(k)!=v: failures.append('predecessor_fact_reverted:'+k)
    # exact immutable identities may only change with explicit supersession
    superseded=set(current.get('explicitly_superseded_facts') or [])
    for k,v in prevfacts.items():
        if k in curfacts and curfacts[k]!=v and k not in superseded and k.endswith(('_id','_sha','_hash','_checkpoint','_proof')):
            failures.append('predecessor_identity_drift:'+k)
    dims=['current_phase','artifact_count','authority_identity','gate_status','next_transition','predecessor_proof']
    ledgers=current.get('ledgers') or {}
    for dim in dims:
        vals={name:(data or {}).get(dim) for name,data in ledgers.items()}
        concrete={v for v in vals.values() if v is not None}
        if len(concrete)>1: failures.append('cross_ledger_drift:'+dim)
    mat=current.get('materialization_evidence') or {}; term=current.get('terminal_receipt') or {}
    if term:
        for f in EXPECTED_RECEIPT:
            if term.get(f) in (None,''): failures.append('terminal_receipt_field_missing:'+f)
        if term.get('head_sha')==current.get('receipt_reference_commit_sha') and current.get('receipt_reference_commit_sha'):
            failures.append('terminal_receipt_self_reference')
        if mat.get('run_id')==term.get('run_id') and mat.get('head_sha')==term.get('head_sha') and current.get('requires_distinct_terminal_receipt') is True:
            failures.append('materialization_terminal_receipt_not_distinct')
    prev_auth=previous.get('unresolved_authority_records') or []
    cur_auth=current.get('unresolved_authority_records') or []
    if prev_auth:
        prev_tuples={tuple(x.get(f) for f in EXPECTED_AUTHORITY_TUPLE) for x in prev_auth}
        cur_tuples={tuple(x.get(f) for f in EXPECTED_AUTHORITY_TUPLE) for x in cur_auth}
        superseded=set(current.get('explicitly_superseded_authority_tuples') or [])
        if prev_tuples!=cur_tuples and not superseded: failures.append('unresolved_authority_identity_tuple_drift')
        for x in cur_auth:
            if any(x.get(f) in (None,'') for f in EXPECTED_AUTHORITY_TUPLE): failures.append('unresolved_authority_identity_field_missing')
    projections=current.get('terminal_receipt_projections') or {}
    if projections:
        canonical=None
        for name,rec in projections.items():
            for f in EXPECTED_RECEIPT:
                if (rec or {}).get(f) in (None,''): failures.append('terminal_receipt_projection_field_missing:'+str(name)+':'+f)
            vals=tuple((rec or {}).get(f) for f in EXPECTED_RECEIPT)
            if canonical is None: canonical=vals
            elif vals!=canonical: failures.append('terminal_receipt_projection_drift:'+str(name))
            if ('jobs' in (rec or {}) or 'result' in (rec or {})) and any((rec or {}).get(f) in (None,'') for f in EXPECTED_RECEIPT): failures.append('terminal_receipt_alias_substitution:'+str(name))
    return {'status':'PASS' if not failures else 'FAIL','failures':failures}


def validate_predecessor_successor_state(previous,current,legal_successor_edges):
    """Common model: predecessor closure invariants stay valid across a registered legal successor."""
    failures=[]
    pstage=previous.get('stage_uid'); cstage=current.get('current_stage_uid')
    legal=set(tuple(x) for x in legal_successor_edges)
    if cstage!=pstage and (pstage,cstage) not in legal:
        failures.append('illegal_successor_or_stage_skip')
    if previous.get('completed') is not True or current.get('predecessor_completed') is not True:
        failures.append('predecessor_completion_reverted')
    for key in ('proof_identity','authority_identity','terminal_receipt'):
        if current.get(key)!=previous.get(key):
            failures.append('predecessor_'+key+'_drift')
    # Deliberately do not require current_state == predecessor terminal_state and do not require successor_started == false.
    return {'status':'PASS' if not failures else 'FAIL','failures':failures}

def validate_required_evidence_bytes(text,format_name='yaml',required_fields=None):
    """Required Evidence exact bytes must parse and satisfy applicable required fields."""
    failures=[]
    required_fields=list(required_fields or [])
    try:
        if format_name.lower()=='json': data=json.loads(text)
        elif format_name.lower() in ('yaml','yml'): data=yaml.safe_load(text)
        else:
            data=None; failures.append('unsupported_required_evidence_parser')
    except Exception:
        data=None; failures.append('required_evidence_parse_failure')
    if not failures:
        if not isinstance(data,dict): failures.append('required_evidence_root_not_mapping')
        else:
            for f in required_fields:
                if data.get(f) in (None,''): failures.append('required_evidence_field_missing:'+f)
    return {'status':'PASS' if not failures else 'FAIL','failures':failures}

if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
