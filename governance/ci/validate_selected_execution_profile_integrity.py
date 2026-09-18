#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / 'GOVERNANCE_CURRENT.yaml'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
REVIEW = ROOT / '.github/governance-source/active/source/10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml'
STAGE02_WORKFLOW = ROOT / '.github/workflows/stage02-actual-test.yml'


def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        die('MISSING_REQUIRED_FILE:' + path.relative_to(ROOT).as_posix())
    try:
        return yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception as exc:
        die(f'YAML_PARSE:{path.relative_to(ROOT)}:{exc!r}')


current = load_yaml(CURRENT)
state = load_yaml(STATE)
selected = current.get('selected_execution_profile') or {}
profile_state = state.get('selected_execution_profile_state') or {}

if current.get('policy_scope') != 'PRODUCT_SYSTEM_AND_EXECUTION_PROFILE_NEUTRAL':
    die('CURRENT_POLICY_SCOPE_NOT_PROFILE_NEUTRAL')
if not selected.get('profile_uid') or not selected.get('registry'):
    die('SELECTED_EXECUTION_PROFILE_INCOMPLETE')
if selected.get('layer_classification') != 'EXECUTION_PROFILE':
    die('SELECTED_PROFILE_LAYER_INVALID')
if selected.get('global_normative_authority') is not False:
    die('SELECTED_PROFILE_MUST_NOT_HAVE_GLOBAL_NORMATIVE_AUTHORITY')
if selected.get('may_weaken_common_policy') is not False:
    die('SELECTED_PROFILE_MAY_NOT_WEAKEN_COMMON_POLICY')

profile_path = ROOT / str(selected['registry'])
profile = load_yaml(profile_path)
stages = profile.get('stages') or []
step_uids = {str(x.get('stage_uid')) for x in stages if isinstance(x, dict) and x.get('stage_uid')}
if profile.get('artifact_type') != 'EXECUTION_PROFILE_REGISTRY':
    die('SELECTED_PROFILE_REGISTRY_TYPE_INVALID')
if profile.get('layer_classification') != 'EXECUTION_PROFILE':
    die('SELECTED_PROFILE_REGISTRY_LAYER_INVALID')
if profile.get('global_normative_authority') is not False:
    die('SELECTED_PROFILE_REGISTRY_GLOBAL_AUTHORITY_INVALID')
if profile.get('profile_uid') != selected.get('profile_uid'):
    die('SELECTED_PROFILE_UID_MISMATCH')
if int(profile.get('profile_local_denominator') or -1) != len(stages):
    die('SELECTED_PROFILE_DENOMINATOR_DRIFT')
if int(selected.get('profile_local_denominator') or -1) != len(stages):
    die('CURRENT_SELECTED_PROFILE_DENOMINATOR_DRIFT')

# A selected profile is executable only when every declared step has a complete
# structural contract. This proves a legal downstream path exists before execution;
# it does not invent missing product Authority or guarantee external systems succeed.
if len(step_uids) != len(stages):
    die('SELECTED_PROFILE_STAGE_UID_DUPLICATE_OR_MISSING')
stage_by_uid = {str(x.get('stage_uid')): x for x in stages if isinstance(x, dict) and x.get('stage_uid')}
required_scalars = ('stage_uid', 'name', 'scope_mode', 'entry_gate', 'exit_gate', 'next_stage_uid', 'pre_execution_gate')
for step in stages:
    if not isinstance(step, dict):
        die('SELECTED_PROFILE_STAGE_RECORD_INVALID')
    uid = str(step.get('stage_uid') or '')
    for field in required_scalars:
        if step.get(field) in (None, ''):
            die(f'SELECTED_PROFILE_STAGE_FIELD_MISSING:{uid}:{field}')
    inputs = step.get('inputs') or []
    origins = step.get('input_origins') or {}
    operations = step.get('operations') or []
    outputs = step.get('outputs') or []
    producers = step.get('output_producers') or {}
    validators = step.get('validators') or []
    evidence = step.get('required_evidence') or []
    refs = step.get('required_normative_section_uids') or []
    for name, rows in (
        ('inputs', inputs), ('operations', operations), ('outputs', outputs),
        ('validators', validators), ('required_evidence', evidence),
        ('required_normative_section_uids', refs),
    ):
        if not isinstance(rows, list) or not rows or len(rows) != len(set(map(str, rows))):
            die(f'SELECTED_PROFILE_STAGE_LIST_INVALID:{uid}:{name}')
    if not isinstance(origins, dict) or set(origins) != set(inputs):
        die(f'SELECTED_PROFILE_INPUT_ORIGIN_COVERAGE_INVALID:{uid}')
    if not isinstance(producers, dict) or set(producers) != set(outputs):
        die(f'SELECTED_PROFILE_OUTPUT_PRODUCER_COVERAGE_INVALID:{uid}')
    missing_producers = sorted({str(v) for v in producers.values()} - {str(v) for v in operations})
    if missing_producers:
        die(f'SELECTED_PROFILE_OUTPUT_PRODUCER_NOT_OPERATION:{uid}:{missing_producers}')
    if step.get('pre_execution_gate') != 'GOVERNANCE_LOAD_RECEIPT_PASS':
        die(f'SELECTED_PROFILE_PREEXECUTION_GATE_DRIFT:{uid}')
for step in stages:
    uid = str(step.get('stage_uid'))
    nxt = str(step.get('next_stage_uid') or '')
    if nxt in stage_by_uid:
        predecessor_exit = str(step.get('exit_gate') or '')
        successor_entry = str(stage_by_uid[nxt].get('entry_gate') or '')
        exact_or_stricter = (
            successor_entry == predecessor_exit
            or successor_entry.startswith(predecessor_exit + '_AND_')
        )
        if not exact_or_stricter:
            die(f'SELECTED_PROFILE_SUCCESSOR_GATE_MISMATCH:{uid}->{nxt}:{predecessor_exit}:{successor_entry}')

if profile_state.get('owner_ref') != 'GOVERNANCE_CURRENT.yaml':
    die('PROFILE_STATE_OWNER_INVALID')
if profile_state.get('profile_uid') != selected.get('profile_uid'):
    die('PROFILE_STATE_UID_DRIFT')
if profile_state.get('profile_step_identities_are_global_governance') is not False:
    die('PROFILE_STEP_IDENTITIES_WRONGLY_GLOBAL')
if profile_state.get('global_normative_authority') is not False:
    die('PROFILE_STATE_WRONGLY_NORMATIVE')

execution = state.get('execution') or {}
current_label = str(execution.get('current_stage') or '')
if current_label:
    m = re.match(r'^([A-Z]+-\d+)(?:-|$)', current_label)
    if not m or m.group(1) not in step_uids:
        die(f'PROFILE_CURRENT_STEP_NOT_IN_SELECTED_PROFILE:{current_label}')

history_ref = profile_state.get('history_binding_ref')
if not history_ref or not (ROOT / str(history_ref)).is_file():
    die('PROFILE_HISTORY_BINDING_REF_INVALID')

review = load_yaml(REVIEW)
review_rows = [
    row for row in (review.get('required_review_plan') or [])
    if isinstance(row, dict) and row.get('review_item_uid') == 'REV-GOV-001'
]
if len(review_rows) != 1:
    die(f'PREFORMAL_REVIEW_ITEM_COUNT:{len(review_rows)}')
review_item = review_rows[0]
if review_item.get('reviewer_role') != 'USER_OR_AUTHORIZED_GOVERNANCE_REVIEWER':
    die('PREFORMAL_REVIEW_ROLE_DRIFT')
if review_item.get('status') not in {'PENDING', 'APPROVED'}:
    die(f'PREFORMAL_REVIEW_STATUS_INVALID:{review_item.get("status")!r}')
if review_item.get('status') == 'PENDING':
    current_step = (execution.get('stage2') or {})
    if execution.get('current_stage') != 'STAGE-01-CLOSED' or current_step.get('result') != 'NOT_EXECUTED':
        die('PREFORMAL_PENDING_MUST_KEEP_STAGE02_NOT_EXECUTED')
    if profile_state.get('active_attempt_state_key') or state.get('stage02_active_attempt'):
        die('PREFORMAL_PENDING_MUST_NOT_HAVE_STAGE02_ACTIVE_ATTEMPT')

workflow_text = STAGE02_WORKFLOW.read_text(encoding='utf-8')
ordered_commands = [
    'python governance/ci/validate_stage02_entry_receipts.py',
    'python governance/ci/compile_stage_execution_preflight.py --admission-check',
    'python .github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py',
    'python governance/ci/run_current_stage2_actual_test.py',
]
positions = [workflow_text.find(command) for command in ordered_commands]
if any(pos < 0 for pos in positions):
    die(f'STAGE_EXECUTION_ADMISSION_COMMAND_MISSING:{positions}')
if positions != sorted(positions) or len(set(positions)) != len(positions):
    die(f'STAGE_EXECUTION_ADMISSION_ORDER_INVALID:{positions}')

validators = profile_state.get('profile_validator_refs') or []
if not validators or len(validators) != len(set(validators)):
    die('PROFILE_VALIDATOR_REFS_EMPTY_OR_DUPLICATE')
for rel in validators:
    path = ROOT / str(rel)
    if not path.is_file():
        die(f'PROFILE_VALIDATOR_MISSING:{rel}')
    cp = subprocess.run([sys.executable, str(path)], cwd=str(ROOT), text=True)
    if cp.returncode != 0:
        die(f'PROFILE_VALIDATOR_FAILED:{rel}')

print(f"PASS: selected execution profile {selected.get('profile_uid')} resolves as non-global execution profile")
print(f'PASS: selected profile local denominator={len(stages)} and profile-local validators={len(validators)}')
print(f'PASS: selected profile structural execution contracts={len(stages)}/{len(stages)} complete before execution')
print('PASS: fixed profile step identities are isolated from reusable Current Governance')
print(f"PASS: preformal review boundary status={review_item.get('status')} and Stage-02 admission ordering is fail-closed before actual execution")
