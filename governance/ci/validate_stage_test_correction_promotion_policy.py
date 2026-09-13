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
if len(promotions) != 1:
    die('exactly one verified rule promotion expected for this cycle')
rule = promotions[0]
if rule.get('rule_uid') != 'STAGE-TEST-RULE-SHALLOW-CHECKOUT-001':
    die('shallow-checkout rule missing')
if rule.get('source_failure_run') != 34783557535 or rule.get('source_failure_job') != 103794818355:
    die('source failure receipt drift')
if rule.get('verified_fix_commit') != '397b5d62e0330fd74de84c1d4a9bfd489e48c29e':
    die('verified fix commit drift')
if rule.get('verification_runs') != [34783656176, 34784187024]:
    die('verification receipts drift')

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

if E.get('status') != 'INTERMEDIATE_FIX_VERIFICATION_COMPLETE_FINAL_CROSS_STAGE_RETEST_NOT_EXECUTED':
    die('test evidence must remain intermediate before post-policy cross-stage retest')
final_retest = E.get('final_cross_stage_retest') or {}
if final_retest.get('required') is not True or final_retest.get('start_boundary') != 'STAGE-01':
    die('cross-stage retest boundary drift')
if final_retest.get('status') != 'NOT_EXECUTED_AFTER_POLICY_PROMOTION' or final_retest.get('terminal_receipt') is not None:
    die('final retest must not be pre-claimed')
if (E.get('test_cycle_decision') or {}).get('stage_test_cycle_complete') is not False:
    die('stage test cycle must remain incomplete before cross-stage retest')

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
    'verified_rule_promotion_count': 1,
    'stage2_completeness_requirement_count': len(required_sections),
    'known_functional_gap_total_preserved': 167,
    'known_async_unresolved_preserved': 14,
    'sealed_v212_package_unchanged': True,
    'current_r4_projection_unchanged': True,
    'final_cross_stage_retest_required': True,
    'final_cross_stage_retest_executed': False,
    'retest_start_boundary': 'STAGE-01',
    'stage_test_cycle_complete': False,
}
Path('stage_test_correction_promotion_policy_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('PASS: verified Stage-02 test correction promoted into enforceable v2.1.12 operational policy')
print('PASS: eight Stage-02 completeness requirement families are now explicit governance requirements')
print('PASS: sealed v2.1.12 package and R4 Current truth bytes remain unchanged')
print('PASS: final retest remains forbidden until policy enforcement is installed, then must start at Stage-01')
