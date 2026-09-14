#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import yaml
import sys

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
STAGE2 = RUN / '04_PAGE_FUNCTIONAL_CONTRACT'
R3 = ROOT / 'governance/test/stage02/STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION_R3.yaml'
PAGES = ('CORE-01','ASSET-01')


def die(msg):
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load(path):
    if not path.is_file(): die(f'MISSING:{path.relative_to(ROOT)}')
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}

r3 = load(R3)
admitted = [r for r in r3.get('records', []) if r.get('disposition') == 'BOUNDED_COMPLETION_ADMISSIBLE']
blocked = [r for r in r3.get('records', []) if r.get('disposition') == 'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS']
external = [r for r in r3.get('records', []) if r.get('disposition') == 'EXACT_EXTERNAL_AUTHORITY_REQUIRED']
if (len(admitted), len(blocked), len(external)) != (17,150,4):
    die(f'R3_CLASSIFICATION_DRIFT:{len(admitted)}/{len(blocked)}/{len(external)}')
expected = {(r['page_uid'], r['category'], r['uid'], r.get('detail')): r for r in admitted}
actual = {}

for page in PAGES:
    ledger_path = STAGE2 / page / 'AUTO_COMPLETION_SCOPE_LEDGER.yaml'
    ledger = load(ledger_path)
    if ledger.get('artifact_type') != 'AUTO_COMPLETION_SCOPE_LEDGER': die(f'WRONG_ARTIFACT:{page}')
    if ledger.get('page_uid') != page: die(f'PAGE_UID_MISMATCH:{page}')
    if ledger.get('stage_exit_claimed') is not False: die(f'STAGE_EXIT_CLAIMED:{page}')
    bc = ledger.get('bounded_completion') or {}
    required_false = ('generic_crud_symmetry_expansion_used','sibling_feature_symmetry_expansion_used','semantic_similarity_used','external_authority_auto_resolution_used')
    if bc.get('minimal_closure_set') is not True or bc.get('seed_gap_or_required_operation_required') is not True:
        die(f'BOUNDED_RULE_MISSING:{page}')
    for field in required_false:
        if bc.get(field) is not False: die(f'FORBIDDEN_EXPANSION:{page}:{field}')
    if ledger.get('unresolved_external_authority_refs_preserved') != [f'GAP-{i:03d}' for i in range(1,9)]:
        die(f'EXTERNAL_REF_SET_DRIFT:{page}')
    rems = ledger.get('remediations') or []
    if ledger.get('materialized_remediation_count') != len(rems): die(f'COUNT_MISMATCH:{page}')
    package = load(STAGE2 / page / 'PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml')
    if 'AUTO_COMPLETION_SCOPE_LEDGER.yaml' not in (package.get('included_artifacts') or []):
        die(f'PACKAGE_NOT_BINDING_LEDGER:{page}')
    for rem in rems:
        sig = rem.get('defect_signature') or {}
        key = (page, sig.get('category'), sig.get('uid'), sig.get('detail'))
        if key in actual: die(f'DUPLICATE_REMEDIATION:{key}')
        if key not in expected: die(f'UNAUTHORIZED_REMEDIATION:{key}')
        if rem.get('semantic_inference_used') is not False or rem.get('ai_invented_business_value') is not False or rem.get('external_authority_resolution_performed') is not False:
            die(f'FORBIDDEN_COMPLETION_METHOD:{key}')
        exp = expected[key]
        if rem.get('completion_basis') != exp.get('completion_basis'):
            die(f'BASIS_MISMATCH:{key}')
        if rem.get('exact_proof') != exp.get('proof'):
            die(f'PROOF_MISMATCH:{key}')
        closure = rem.get('materialized_closure') or {}
        if sig.get('category') == 'STATE_TRANSITION_LEDGER_FIELD_MISSING':
            proof = exp['proof']
            if closure.get('closure_type') != 'ILLEGAL_TRANSITION_NEGATIVE_TESTS': die(f'WRONG_CLOSURE_TYPE:{key}')
            if closure.get('transition_uid') != sig.get('uid'): die(f'TRANSITION_UID_MISMATCH:{key}')
            tests = closure.get('illegal_transition_tests') or []
            if len(tests) not in (2,3): die(f'NEGATIVE_TEST_DENOMINATOR:{key}:{len(tests)}')
            conds = {t.get('condition') for t in tests}
            required = {f"current_stage != {proof['from_stage']}", f"observed_trigger != {proof['trigger']}"}
            if proof.get('gate') not in (None,'',[],{}): required.add(f"gate_not_satisfied: {proof['gate']}")
            if conds != required: die(f'NEGATIVE_TEST_SEMANTICS_DRIFT:{key}')
            if any(t.get('expected') != 'BLOCK_TRANSITION' or t.get('invented_business_value') is not False for t in tests):
                die(f'NEGATIVE_TEST_INVALID:{key}')
        elif sig.get('category') == 'SUCCESS_NEXT_STATE_BINDING_MISSING':
            proof = exp['proof']
            if closure.get('closure_type') != 'SUCCESS_NEXT_STATE_BINDING': die(f'WRONG_SUCCESS_CLOSURE:{key}')
            if closure.get('action_uid') != sig.get('uid'): die(f'ACTION_UID_MISMATCH:{key}')
            if closure.get('source_port_uid') != proof.get('port_uid'): die(f'PORT_UID_MISMATCH:{key}')
            if closure.get('success_state_effect') != proof.get('state_event'): die(f'STATE_EFFECT_NOT_EXACT_COPY:{key}')
            if closure.get('projection_rule') != 'EXACT_COPY_FROM_REGISTERED_ACTION_PORT_STATE_EVENT': die(f'PROJECTION_RULE_INVALID:{key}')
        else:
            die(f'UNEXPECTED_ADMITTED_CATEGORY:{key}')
        actual[key] = rem

if set(actual) != set(expected):
    missing = sorted(set(expected)-set(actual))
    extra = sorted(set(actual)-set(expected))
    die(f'REMEDIATION_SET_MISMATCH:missing={missing}:extra={extra}')
if len(actual) != 17: die(f'REMEDIATION_TOTAL_NOT_17:{len(actual)}')
if sum(k[1] == 'STATE_TRANSITION_LEDGER_FIELD_MISSING' for k in actual) != 10: die('TRANSITION_REMEDIATION_NOT_10')
if sum(k[1] == 'SUCCESS_NEXT_STATE_BINDING_MISSING' for k in actual) != 7: die('SUCCESS_REMEDIATION_NOT_7')
print('PASS: R3 Stage-02 owning-layer remediation set is exact 17/17')
print('PASS: transition negative tests 10/10 are deterministic and source-bounded')
print('PASS: success-next-state bindings 7/7 are exact action-port-state_event projections')
print('PASS: 150 no-basis + 4 external-authority gaps remain unmaterialized')
print('PASS: GAP-001..GAP-008 preserved unresolved')
