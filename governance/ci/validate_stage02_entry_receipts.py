#!/usr/bin/env python3
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path
import yaml

from governance_resolver import resolve

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "governance/test/stage02/STAGE02_STAGE_FROZEN_GOVERNANCE_RECEIPT.yaml"
BASELINE = ROOT / "governance/test/stage02/STAGE02_CLEAN_BASELINE_RESET_RECEIPT.yaml"
STATE = ROOT / "governance/test/ACTIVE_STATE.yaml"
REVIEW = ROOT / ".github/governance-source/active/source/10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml"
ZERO = ROOT / "governance/ci/validate_stage02_zero_residual.py"
SUCCESSOR = ROOT / "governance/ci/validate_stage02_successor_integrity.py"
WORKFLOW = ROOT / ".github/workflows/stage02-actual-test.yml"


def die(msg: str) -> None:
    print("BLOCK:", msg, file=sys.stderr)
    raise SystemExit(1)


def load(path: Path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    try:
        obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        die(f"PARSE:{path.relative_to(ROOT)}:{exc!r}")
    if not isinstance(obj, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def git(*args: str) -> str:
    cp = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    if cp.returncode != 0:
        die(f"GIT_FAILED:{args!r}:{cp.stderr.strip()}")
    return cp.stdout.strip()


state = load(STATE)
execution = state.get("execution") or {}
stage2_result = (execution.get("stage2") or {}).get("result")

if stage2_result in {"TEST_EXECUTED_BLOCKED", "TEST_EXECUTED_PASS"}:
    if not SUCCESSOR.is_file():
        die("SUCCESSOR_INTEGRITY_VALIDATOR_MISSING")
    cp = subprocess.run([sys.executable, str(SUCCESSOR)], cwd=ROOT, text=True)
    if cp.returncode != 0:
        die("SUCCESSOR_INTEGRITY_VALIDATION_FAILED")
    print("PASS: entry-receipt validator NOT_APPLICABLE after Stage-02 execution; delegated to canonical successor integrity owner")
    raise SystemExit(0)
if stage2_result != "NOT_EXECUTED":
    die(f"ENTRY_RECEIPT_VALIDATOR_DOMAIN_UNRESOLVED:{stage2_result!r}")

review = load(REVIEW)
review_items = [
    row for row in (review.get("required_review_plan") or [])
    if isinstance(row, dict) and row.get("review_item_uid") == "REV-GOV-001"
]
if len(review_items) != 1:
    die(f"MOTHER_PREFORMAL_REVIEW_ITEM_COUNT:{len(review_items)}")
review_item = review_items[0]
if review_item.get("reviewer_role") != "USER_OR_AUTHORIZED_GOVERNANCE_REVIEWER":
    die("MOTHER_PREFORMAL_REVIEW_ROLE_DRIFT")
if review_item.get("status") not in {"PENDING", "APPROVED"}:
    die("MOTHER_PREFORMAL_REVIEW_PLAN_STATUS_INVALID")
pending_review = state.get("pending_governance_review") or {}
if pending_review.get("review_item_uid") != "REV-GOV-001":
    die("ACTIVE_STATE_PREFORMAL_REVIEW_IDENTITY_DRIFT")
if pending_review.get("status") != "APPROVED":
    die("ACTIVE_STATE_PREFORMAL_REVIEW_NOT_APPROVED")
if pending_review.get("approval_source") != "EXPLICIT_USER_DIRECTIVE" or pending_review.get("explicit_user_decision_observed") is not True:
    die("ACTIVE_STATE_PREFORMAL_REVIEW_USER_EVIDENCE_MISSING")
if pending_review.get("target_governance_uid") != resolve()["governance_uid"]:
    die("ACTIVE_STATE_PREFORMAL_REVIEW_TARGET_UID_DRIFT")
root_manifest = ".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml"
if pending_review.get("target_root_manifest_git_blob_sha") != git("rev-parse", f"HEAD:{root_manifest}"):
    die("ACTIVE_STATE_PREFORMAL_REVIEW_TARGET_HASH_DRIFT")

workflow_text = WORKFLOW.read_text(encoding="utf-8")
ordered_commands = [
    "python governance/ci/validate_stage02_entry_receipts.py",
    "python governance/ci/compile_stage_execution_preflight.py --admission-check",
    "python .github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py",
    "python governance/ci/run_current_stage2_actual_test.py",
]
positions = [workflow_text.find(command) for command in ordered_commands]
if any(pos < 0 for pos in positions):
    die(f"STAGE02_ADMISSION_COMMAND_MISSING:{positions}")
if positions != sorted(positions) or len(set(positions)) != len(positions):
    die(f"STAGE02_ADMISSION_ORDER_INVALID:{positions}")

freeze = load(FREEZE)
baseline = load(BASELINE)
uid = resolve()["governance_uid"]
parent = git("rev-parse", "HEAD^")
attempt = freeze.get("attempt_uid")
if not isinstance(attempt, str) or not re.fullmatch(r"STAGE02-FRESH-\d{8}-\d{3}", attempt):
    die(f"FRESH_ATTEMPT_UID_INVALID:{attempt!r}")
if baseline.get("attempt_uid") != attempt:
    die("ENTRY_RECEIPT_ATTEMPT_IDENTITY_MISMATCH")
expected_scope = execution.get("target_pages") or []
if not isinstance(expected_scope, list) or not expected_scope or not all(isinstance(x, str) and x for x in expected_scope):
    die(f"ACTIVE_STATE_STAGE02_SCOPE_INVALID:{expected_scope!r}")
if freeze.get("target_pages") != expected_scope or baseline.get("target_pages") != expected_scope:
    die("ENTRY_RECEIPT_PAGE_SCOPE_DRIFT")

if freeze.get("artifact_type") != "STAGE_FROZEN_GOVERNANCE_RECEIPT": die("FREEZE_RECEIPT_TYPE")
if freeze.get("stage_uid") != "STAGE-02": die("FREEZE_RECEIPT_IDENTITY")
if freeze.get("frozen_governance_uid") != uid: die(f"FREEZE_UID_MISMATCH:expected={uid}:actual={freeze.get('frozen_governance_uid')}")
if freeze.get("preparation_parent_commit") != parent: die(f"FREEZE_PARENT_MISMATCH:expected={parent}:actual={freeze.get('preparation_parent_commit')}")
if freeze.get("prior_stage2_results_authoritative") is not False or freeze.get("prior_stage2_results_used") is not False: die("FREEZE_PRIOR_RESULT_CONTAMINATION")
if freeze.get("current_specification_mutation_allowed_during_stage") is not False: die("FREEZE_SPEC_MUTATION_NOT_BLOCKED")
if freeze.get("ai_autofill_allowed") is not False or freeze.get("semantic_inference_without_registered_authority_allowed") is not False: die("FREEZE_AI_INFERENCE_NOT_BLOCKED")

if baseline.get("artifact_type") != "CLEAN_BASELINE_RESET_RECEIPT": die("BASELINE_RECEIPT_TYPE")
if baseline.get("stage_uid") != "STAGE-02": die("BASELINE_RECEIPT_IDENTITY")
if baseline.get("baseline_parent_commit") != parent: die(f"BASELINE_PARENT_MISMATCH:expected={parent}:actual={baseline.get('baseline_parent_commit')}")
if baseline.get("predecessor_state") != "STAGE1_VALIDATION_COMPLETED_CI_PASS": die("BASELINE_PREDECESSOR_STATE")
if baseline.get("stage2_started_in_predecessor") is not False: die("BASELINE_STAGE2_ALREADY_STARTED")
expected_blobs = baseline.get("expected_stage1_blobs")
if not isinstance(expected_blobs, dict) or not expected_blobs:
    die("BASELINE_EXPECTED_STAGE1_BLOBS_MISSING")
run_root = str(__import__("os").environ.get("ACPOS_RUN_ROOT") or "")
if not run_root:
    die("ACPOS_RUN_ROOT_MISSING")
if not any(str(path).startswith(run_root + "/") for path in expected_blobs):
    die("BASELINE_EXPECTED_BLOBS_DO_NOT_BIND_CURRENT_RUN_ROOT")
for path, expected in expected_blobs.items():
    if not isinstance(path, str) or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{40}", expected):
        die(f"BASELINE_BLOB_RECORD_INVALID:{path}:{expected}")
    actual = git("rev-parse", f"HEAD:{path}")
    if actual != expected: die(f"BASELINE_BLOB_MISMATCH:{path}:expected={expected}:actual={actual}")

if execution.get("current_stage") != "STAGE-01-CLOSED": die("ACTIVE_STATE_NOT_CLEAN_PRE_STAGE02")
profile_state = state.get("selected_execution_profile_state") or {}
active_attempt_state_key = profile_state.get("active_attempt_state_key")
if active_attempt_state_key or state.get("stage02_active_attempt"): die("NOT_EXECUTED_STAGE_MUST_NOT_PERSIST_ACTIVE_ATTEMPT_POINTER")

cp = subprocess.run([sys.executable, str(ZERO)], cwd=ROOT, text=True)
if cp.returncode != 0: die("ZERO_RESIDUAL_VALIDATION_FAILED")

print(f"PASS: Stage-02 fresh entry receipts agree on attempt {attempt}")
print(f"PASS: Stage-02 entry freeze receipt locks governance UID {uid}")
print(f"PASS: Stage-02 clean predecessor receipt binds parent {parent}")
print(f"PASS: Stage-01 predecessor blob denominator is receipt-owned and exact count={len(expected_blobs)}; no active attempt/evidence/findings are persisted before execution")
print("PASS: REV-GOV-001 human/authorized preformal approval is persisted before Stage-02 entry")
print("PASS: Stage-02 workflow ordering is entry review -> completion-path admission -> Full-Line -> actual execution")
