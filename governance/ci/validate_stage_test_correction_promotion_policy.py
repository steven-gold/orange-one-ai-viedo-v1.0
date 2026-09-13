#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, yaml

ROOT = Path('.')
POLICY = ROOT / 'governance/STAGE_TEST_CORRECTION_PROMOTION_POLICY_V1.yaml'
EVIDENCE = ROOT / '11_EVIDENCE/audit/STAGE2_FULL_TEST_CYCLE_R1.yaml'
WORKFLOW = ROOT / '.github/workflows/rebuild-governance-gate.yml'
FIXED_VALIDATOR = ROOT / 'governance/ci/validate_current_stage2_architecture_unresolved_evidence.py'
FULL_PACKAGE_LOCK = ROOT / 'governance/current/v2.1.12/FULL_PACKAGE_LOCK.yaml'
GOV_R4 = ROOT / 'GOVERNANCE_CURRENT_R4.yaml'
BLOCKER_R4 = ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/BLOCKER_LEDGER_R4.yaml'
EXPECTED_PACKAGE_BLOB = '1efcb2fb31bdb8d5efa61265ba8b73a1003a7617'
EXPECTED_GOV_R4_BLOB = '901a4c997cea41b6a15de2b1378916ebad611d0b'
EXPECTED_BLOCKER_R4_BLOB = 'e675cc68b0eb6bfd7c484e860eef3b5ebc146890'

INTERMEDIATE_STATE = 'INTERMEDIATE_FIX_VERIFICATION_COMPLETE_FINAL_CROSS_STAGE_RETEST_NOT_EXECUTED'
POLICY_PROMOTED_STATE = 'POLICY_PROMOTION_COMPLETE_FINAL_CROSS_STAGE_RETEST_NOT_EXECUTED'
FINAL_RETEST_STATE = 'POLICY_PROMOTION_AND_FINAL_CROSS_STAGE_RETEST_COMPLETE'
LEGAL_EVIDENCE_STATES = {INTERMEDIATE_STATE, POLICY_PROMOTED_STATE, FINAL_RETEST_STATE}


def die(msg):
    raise SystemExit(msg)


def load_yaml(path):
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        die(f'mapping required: {path}')
    return data


def git_blob(path):
    r = subprocess.run(['git', 'rev-parse', f'HEAD:{path.as_posix()}'], text=True, capture_output=True)
    if r.returncode != 0:
        die(f'git object missing: {path}')
    return r.stdout.strip()


for p in (POLICY, EVIDENCE, WORKFLOW, FIXED_VALIDATOR, FULL_PACKAGE_LOCK, GOV_R4, BLOCKER_R4):
    if not p.is_file():
        die(f'required file missing: {p}')

P = load_yaml(POLICY)
E = load_yaml(EVIDENCE)

if P.get('artifact_uid') != 'ACPOS-STAGE-TEST-CORRECTION-PROMOTION-POLICY-V1':
    die('policy uid drift')
if P.get('artifact_type') != 'CURRENT_OPERATIONAL_GOVERNANCE_POLICY':
    die('policy type drift')
if P.get('governance_overlay') != 'v2.1.12' or P.get('policy_status') != 'CURRENT_OPERATIONAL':
    die('policy governance/status drift')

versioning = P.get('versioning') or {}
if versioning.get('sealed_governance_package_mutated') is not False:
    die('sealed package must remain unmodified')
if versioning.get('current_r4_projection_mutated') is not False:
    die('R4 truth projection must remain unmodified')

expected_sequence = [
    'RUN_CURRENT_STAGE_TO_DISCOVERY_EXHAUSTION',
    'RECORD_ALL_TEST_BUGS_AND_TRUE_PRODUCT_OR_AUTHORITY_GAPS',
    'CLASSIFY_TEST_HARNESS_BUG_VS_PRODUCT_GAP_VS_AUTHORITY_GAP',
    'APPLY_ONLY_AUTHORIZED_CORRECTIONS',
    'VERIFY_EACH_CORRECTION_WITH_EXECUTION_EVIDENCE',
    'PROMOTE_EVERY_VERIFIED_CORRECTION_TO_GOVERNANCE_RULE',
    'COMPLETE_POLICY_ENFORCEMENT_BEFORE_FINAL_RETEST',
    'RETURN_TO_IMMEDIATELY_PREVIOUS_STAGE_BOUNDARY',
    'REPLAY_PREVIOUS_STAGE_CLOSURE_AND_SUCCESSOR_TRANSITION',
    'RERUN_CURRENT_STAGE_UNDER_UPDATED_RULES',
    'COMPARE_NEW_OUTPUTS_AGAINST_ALL_PREVIOUS_FINDINGS',
    'CLOSE_STAGE_TEST_CYCLE_ONLY_IF_NO_UNACCOUNTED_REGRESSION_OR_RULE_GAP_REMAINS',
]
loop = P.get('stage_test_feedback_loop') or {}
if loop.get('required_sequence') != expected_sequence:
    die('stage feedback-loop sequence drift')
for key in (
    'premature_final_retest_before_policy_promotion',
    'mark_stage_test_complete_from_same_stage_only_regression',
    'treat_green_ci_as_product_gap_resolution',
    'treat_test_harness_bug_as_product_truth_change',
):
    if loop.get(key) != 'FORBIDDEN':
        die(f'feedback-loop fail-closed rule drift: {key}')

promotions = P.get('verified_rule_promotions') or []
if not isinstance(promotions, list) or not promotions:
    die('at least one verified rule promotion required')
rule_by_uid = {r.get('rule_uid'): r for r in promotions if isinstance(r, dict) and r.get('rule_uid')}
if len(rule_by_uid) != len(promotions):
    die('duplicate or malformed verified rule promotion')
rule1 = rule_by_uid.get('STAGE-TEST-RULE-SHALLOW-CHECKOUT-001')
if not rule1:
    die('shallow-checkout rule missing')
if rule1.get('source_failure_run') != 34783557535 or rule1.get('source_failure_job') != 103794818355:
    die('source failure receipt drift for rule 001')
if rule1.get('verified_fix_commit') != '397b5d62e0330fd74de84c1d4a9bfd489e48c29e':
    die('verified fix commit drift for rule 001')
if rule1.get('verification_runs') != [34783656176, 34784187024]:
    die('verification receipts drift for rule 001')

rule2 = rule_by_uid.get('STAGE-TEST-RULE-EVIDENCE-LIFECYCLE-STATE-002')
if rule2:
    if rule2.get('source_failure_run') != 34784673972 or rule2.get('source_failure_job') != 103797862524:
        die('source failure receipt drift for rule 002')
    if not rule2.get('verified_fix_commit'):
        die('verified fix commit missing for rule 002')
    verification_runs = rule2.get('verification_runs') or []
    if not isinstance(verification_runs, list) or not verification_runs:
        die('verification run required for rule 002')
    if rule2.get('rule') != 'lifecycle_evidence_validator_must_accept_legal_forward_states_and_reject_regressions_or_impossible_state_receipt_combinations':
        die('rule 002 text drift')
    if loop.get('lifecycle_evidence_validator_state_machine') != 'REQUIRED':
        die('rule 002 enforcement flag missing')

req = P.get('stage2_contract_completeness_requirements') or {}
required_sections = [
    'payload_input_contract',
    'state_transition_contract',
    'failure_state_error_binding',
    'post_action_validation',
    'audit_event_binding',
    'success_next_state_binding',
    'action_control_or_trigger_binding',
    'async_provider_lifecycle',
]
if sorted(req.keys()) != sorted(required_sections):
    die('Stage-02 completeness requirement universe drift')
transition_fields = (req.get('state_transition_contract') or {}).get('required_fields') or []
if transition_fields != ['mutation_owner', 'failure_state', 'recovery', 'audit_event_uid', 'illegal_transition_tests']:
    die('state transition required fields drift')
async_fields = (req.get('async_provider_lifecycle') or {}).get('required_fields_per_page') or []
expected_async = [
    'request_identity', 'input_fingerprint', 'idempotency', 'queued', 'running', 'succeeded',
    'failed', 'retry_eligibility', 'cancel', 'callback_result_provenance', 'output_persistence', 'audit_correlation'
]
if async_fields != expected_async:
    die('async lifecycle required field universe drift')

baseline = P.get('stage2_current_known_gap_baseline') or {}
if baseline.get('functional_gap_total') != 167 or baseline.get('architecture_gap_total') != 133 or baseline.get('input_source_gap_total') != 34:
    die('functional/architecture/input baseline drift')
if baseline.get('functional_authority_gap_total') != 0 or baseline.get('async_provider_unresolved_lifecycle_binding_total') != 14:
    die('authority/async baseline drift')
expected_categories = {
    'STATE_TRANSITION_LEDGER_FIELD_MISSING': 50,
    'FAILURE_STATE_ERROR_BINDING_MISSING': 44,
    'POST_ACTION_VALIDATION_NODE_MISSING': 18,
    'AUDIT_EVENT_NODE_MISSING': 13,
    'SUCCESS_NEXT_STATE_BINDING_MISSING': 7,
    'ACTION_WITHOUT_CONTROL_OR_TRIGGER': 1,
}
if baseline.get('architecture_categories') != expected_categories:
    die('architecture category baseline drift')

# Evidence lifecycle is a monotonic state machine. Validators must accept legal
# forward progression instead of hard-coding one temporary lifecycle state.
evidence_state = E.get('status')
if evidence_state not in LEGAL_EVIDENCE_STATES:
    die(f'illegal evidence lifecycle state: {evidence_state}')
final_retest = E.get('final_cross_stage_retest') or {}
if final_retest.get('required') is not True or final_retest.get('start_boundary') != 'STAGE-01':
    die('cross-stage retest boundary drift')
cycle = E.get('test_cycle_decision') or {}

if evidence_state == INTERMEDIATE_STATE:
    if (E.get('required_policy_promotion') or {}).get('status') not in ('REQUIRED_BEFORE_FINAL_RETEST', 'COMPLETE'):
        die('intermediate state must require or record policy promotion')
    if final_retest.get('status') != 'NOT_EXECUTED_AFTER_POLICY_PROMOTION' or final_retest.get('terminal_receipt') is not None:
        die('intermediate state may not claim final retest')
    if cycle.get('stage_test_cycle_complete') is not False:
        die('intermediate state may not close stage test cycle')
elif evidence_state == POLICY_PROMOTED_STATE:
    promotion = E.get('policy_promotion') or {}
    if promotion.get('status') != 'COMPLETE_AND_ENFORCED':
        die('policy-promoted state requires enforced policy receipt')
    policy_gate = promotion.get('policy_gate_receipt') or {}
    main_gate = promotion.get('same_sha_stage2_main_regression') or {}
    if policy_gate.get('conclusion') != 'success' or main_gate.get('conclusion') != 'success':
        die('policy-promoted state requires passing policy and same-sha main receipts')
    if policy_gate.get('exact_head_sha') != main_gate.get('exact_head_sha'):
        die('policy and main enforcement receipts must share exact SHA')
    if final_retest.get('status') != 'NOT_EXECUTED_AFTER_POLICY_PROMOTION' or final_retest.get('terminal_receipt') is not None:
        die('policy-promoted pre-retest state may not claim final retest')
    if cycle.get('stage_test_cycle_complete') is not False:
        die('policy-promoted pre-retest state may not close stage test cycle')
else:
    receipt = final_retest.get('terminal_receipt')
    if final_retest.get('status') != 'COMPLETED_AFTER_POLICY_PROMOTION' or not isinstance(receipt, dict):
        die('final retest state requires completed terminal receipt')
    if receipt.get('conclusion') != 'success':
        die('final retest terminal receipt must be success')
    if cycle.get('stage_test_cycle_complete') is not True:
        die('final retest state requires stage_test_cycle_complete true')

# If the evidence records the lifecycle-state validator failure, policy rule 002
# must already exist; this prevents a discovered governance bug from being fixed
# ad hoc without promotion into the governance system.
bugs = ((E.get('findings') or {}).get('test_or_validator_bugs') or [])
bug_uids = {b.get('bug_uid') for b in bugs if isinstance(b, dict)}
if 'STAGE2-TEST-BUG-002' in bug_uids and not rule2:
    die('recorded lifecycle-state validator bug requires promoted rule 002')

workflow_text = WORKFLOW.read_text(encoding='utf-8')
required_workflow_bindings = [
    'current-stage1-closure-gate:',
    'python governance/ci/validate_current_stage1_closure.py',
    'current-stage1-stage2-successor-gate:',
    'python governance/ci/validate_current_stage1_stage2_successor.py',
    'current-stage2-functional-chain-preflight-gate:',
    'python governance/ci/validate_current_stage2_functional_chain_preflight.py',
]
for token in required_workflow_bindings:
    if token not in workflow_text:
        die(f'cross-stage workflow binding missing: {token}')

fixed_text = FIXED_VALIDATOR.read_text(encoding='utf-8')
if "['git','cat-file'" in fixed_text or "['git', 'cat-file'" in fixed_text:
    die('fixed validator reintroduced shallow local historical-object dependency')
if 'Do not require\n# historical receipt commits to exist in the runner\'s local object database' not in fixed_text:
    die('shallow-checkout-safe invariant comment missing from fixed validator')

if git_blob(FULL_PACKAGE_LOCK) != EXPECTED_PACKAGE_BLOB:
    die('sealed v2.1.12 package lock bytes changed')
if git_blob(GOV_R4) != EXPECTED_GOV_R4_BLOB:
    die('GOVERNANCE_CURRENT_R4 bytes changed')
if git_blob(BLOCKER_R4) != EXPECTED_BLOCKER_R4_BLOB:
    die('BLOCKER_LEDGER_R4 bytes changed')

result = {
    'artifact_type': 'STAGE_TEST_CORRECTION_PROMOTION_POLICY_VALIDATION_RESULT',
    'policy_uid': P['artifact_uid'],
    'governance_overlay': 'v2.1.12',
    'policy_status': 'CURRENT_OPERATIONAL',
    'verified_rule_promotion_count': len(promotions),
    'stage2_completeness_requirement_count': len(required_sections),
    'known_functional_gap_total_preserved': 167,
    'known_async_unresolved_preserved': 14,
    'sealed_v212_package_unchanged': True,
    'current_r4_projection_unchanged': True,
    'evidence_lifecycle_state': evidence_state,
    'evidence_lifecycle_state_machine_valid': True,
    'final_cross_stage_retest_required': True,
    'final_cross_stage_retest_executed': evidence_state == FINAL_RETEST_STATE,
    'retest_start_boundary': 'STAGE-01',
    'stage_test_cycle_complete': cycle.get('stage_test_cycle_complete') is True,
}
Path('stage_test_correction_promotion_policy_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('PASS: Stage test correction-promotion policy is current and enforceable')
print(f'PASS: evidence lifecycle state is legal and monotonic: {evidence_state}')
print(f'PASS: {len(promotions)} verified correction rule(s) are represented by policy')
print('PASS: eight Stage-02 completeness requirement families are explicit governance requirements')
print('PASS: sealed v2.1.12 package and R4 Current truth bytes remain unchanged')
