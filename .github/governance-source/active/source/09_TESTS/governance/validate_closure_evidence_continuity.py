#!/usr/bin/env python3
from pathlib import Path
import json,yaml
ROOT=Path(__file__).resolve().parents[2]
EXPECTED_STAGES=[f'STAGE-{i:02d}' for i in range(1,12)]
EXPECTED_AUTHORITY_TUPLE=['gap_uid','authority_ref','disposition','authority_evidence_ref']
def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def validate(root=ROOT):
    root=Path(root); failures=[]
    life=load(root/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml')
    bp=load(root/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml')
    s1=load(root/'10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml')
    doc=(root/'12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md').read_text(encoding='utf-8')
    inv=((life.get('cross_stage_invariants') or {}).get('closure_evidence_continuity') or {})
    if inv.get('invariant_uid')!='GOV-INV-CLOSURE-EVIDENCE-CONTINUITY-001': failures.append('continuity_invariant_uid_missing')
    if inv.get('normative_section_uid')!='WEB-GOV-03-S058': failures.append('continuity_normative_section_wrong')
    if inv.get('applies_to_stages')!=EXPECTED_STAGES: failures.append('continuity_not_all_stages')
    if inv.get('closure_mutation_semantics')!='MERGE_APPEND_OR_EXPLICIT_SUPERSEDE': failures.append('closure_mutation_not_monotonic')
    if inv.get('established_predecessor_fact_deletion')!='BLOCK' or inv.get('established_predecessor_fact_reversion')!='BLOCK': failures.append('predecessor_fact_loss_not_blocked')
    if inv.get('current_state_authority')!='EXECUTION_STATE' or inv.get('parallel_mutable_current_state_authority')!='FORBIDDEN': failures.append('single_current_state_contract_missing')
    if inv.get('cross_ledger_state_synchronization_required') is not False: failures.append('cross_ledger_state_sync_not_removed')
    if inv.get('terminal_ci_receipt_required_for_stage_closure') is not False or inv.get('terminal_ci_receipt_role')!='OPTIONAL_TRANSPORT_ATTESTATION': failures.append('terminal_ci_still_closure_authority')
    facts=set(inv.get('content_closure_required_facts') or [])
    expected={'REQUIRED_OPERATION_RESULTS','REQUIRED_OUTPUTS_AND_FIELDS','REQUIRED_SCANNER_RESULTS','REQUIRED_VALIDATOR_RESULTS','REQUIRED_EVIDENCE','ZERO_REQUIRED_GAPS_AND_BLOCKERS','REGISTERED_HUMAN_GATE_IF_APPLICABLE'}
    if facts!=expected: failures.append('content_closure_denominator_incomplete')
    ua=inv.get('unresolved_authority_identity') or {}
    if ua.get('canonical_tuple_fields')!=EXPECTED_AUTHORITY_TUPLE or ua.get('count_only_or_uid_only_validation')!='BLOCK': failures.append('authority_identity_tuple_contract_drift')
    ps=inv.get('predecessor_validator_successor_state_contract') or {}
    if ps.get('registered_legal_successor_presence')!='ALLOW_IF_PREDECESSOR_CONTENT_INVARIANTS_HOLD' or ps.get('illegal_successor_or_stage_skip')!='BLOCK': failures.append('successor_continuity_contract_incomplete')
    ab=bp.get('closure_evidence_continuity_contract') or {}
    if ab.get('current_state_authority')!='EXECUTION_STATE' or ab.get('parallel_mutable_current_state_authority')!='FORBIDDEN': failures.append('acceptance_single_state_missing')
    if ab.get('terminal_ci_receipt_required_for_product_stage_closure') is not False: failures.append('acceptance_terminal_ci_still_required')
    if ab.get('unresolved_authority_canonical_identity_fields')!=EXPECTED_AUTHORITY_TUPLE: failures.append('acceptance_authority_tuple_contract_drift')
    sc=s1.get('closure_evidence_continuity_contract') or {}
    if sc.get('current_state_authority')!='EXECUTION_STATE' or sc.get('parallel_mutable_current_state_authority')!='FORBIDDEN': failures.append('stage1_single_state_missing')
    if sc.get('cross_ledger_state_synchronization_required') is not False or sc.get('terminal_ci_receipt_required_for_stage_closure') is not False: failures.append('stage1_old_ledger_or_ci_gate_remains')
    marker='<!-- SECTION_UID: WEB-GOV-03-S058 -->'
    section=(doc.split(marker,1)[1].split('<!-- SECTION_UID:',1)[0] if marker in doc else '')
    for tok in ['EXECUTION_STATE','only mutable Current execution-state authority','MUST_NOT be required to prove Product Stage content closure','content closure PASS']:
        if tok not in section: failures.append('normative_content_closure_text_missing:'+tok)
    return {'status':'PASS' if not failures else 'FAIL','stage_count':len(life.get('stages') or []),'failures':failures}
def validate_predecessor_successor_state(previous,current,legal_edges):
    failures=[]
    pstage=str(previous.get('stage_uid') or '')
    cstage=str(current.get('current_stage_uid') or '')
    legal=set((str(a),str(b)) for a,b in legal_edges)
    if (pstage,cstage) not in legal:
        failures.append('illegal_successor_or_stage_skip')
    if current.get('predecessor_completed') is not True:
        failures.append('predecessor_completion_reverted')
    if str(current.get('proof_identity') or '')!=str(previous.get('proof_identity') or ''):
        failures.append('predecessor_proof_identity_drift')
    if str(current.get('authority_identity') or '')!=str(previous.get('authority_identity') or ''):
        failures.append('predecessor_authority_identity_drift')
    # Terminal CI receipt is optional transport provenance, not Product Stage closure truth.
    return {'status':'PASS' if not failures else 'FAIL','failures':failures}

def validate_required_evidence_bytes(text,fmt,required_fields):
    failures=[]
    if not isinstance(text,str) or not text.strip():
        return {'status':'FAIL','failures':['required_evidence_empty']}
    try:
        if fmt=='yaml':
            obj=yaml.safe_load(text)
        elif fmt=='json':
            obj=json.loads(text)
        else:
            return {'status':'FAIL','failures':['required_evidence_parser_unsupported']}
    except Exception:
        return {'status':'FAIL','failures':['required_evidence_parse_failed']}
    if not isinstance(obj,dict):
        failures.append('required_evidence_mapping_required')
    else:
        for field in required_fields:
            if field not in obj:
                failures.append('required_evidence_field_missing:'+str(field))
    return {'status':'PASS' if not failures else 'FAIL','failures':failures}

def validate_transition(previous,current):
    failures=[]; prev=previous.get('predecessor_facts') or {}; cur=current.get('predecessor_facts') or {}
    for k,v in prev.items():
        if k not in cur: failures.append('predecessor_fact_deleted:'+k)
        elif cur.get(k)!=v and k not in set(current.get('explicitly_superseded_facts') or []): failures.append('predecessor_fact_drift:'+k)
    if current.get('parallel_state_authority') not in (None,False): failures.append('parallel_state_authority_detected')
    if current.get('terminal_ci_required_for_closure') is True: failures.append('terminal_ci_reintroduced_as_closure_gate')
    return {'status':'PASS' if not failures else 'FAIL','failures':failures}
if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
