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
ZERO = ROOT / "governance/ci/validate_stage02_zero_residual.py"
SUCCESSOR = ROOT / "governance/ci/validate_stage02_successor_integrity.py"
EXPECTED_STAGE1_BLOBS = {
    "00_SOURCE_INTAKE/fresh_run_003/ARTIFACT_PLAN.yaml": "c64ab04846b228c14978c07f88164a8d02a22f0d",
    "00_SOURCE_INTAKE/fresh_run_003/EXECUTION_STATE.yaml": "4f2bf558f5807a03d081f848184334ba16901fb1",
    "00_SOURCE_INTAKE/fresh_run_003/RUN_MANIFEST.yaml": "110e672114aa244279ad5af932c83d169fdebfe5",
    "11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml": "96d9e64940f24154cf086fdd26ee0e6d4e0653ef",
    "11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml": "a75551629448349732c08e34d252fee8fb040e94",
}


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

freeze = load(FREEZE)
baseline = load(BASELINE)
uid = resolve()["governance_uid"]
parent = git("rev-parse", "HEAD^")
attempt = freeze.get("attempt_uid")
if not isinstance(attempt, str) or not re.fullmatch(r"STAGE02-FRESH-\d{8}-\d{3}", attempt):
    die(f"FRESH_ATTEMPT_UID_INVALID:{attempt!r}")
if baseline.get("attempt_uid") != attempt:
    die("ENTRY_RECEIPT_ATTEMPT_IDENTITY_MISMATCH")

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
if baseline.get("expected_stage1_blobs") != EXPECTED_STAGE1_BLOBS: die("BASELINE_DECLARED_BLOBS_DRIFT")
for path, expected in EXPECTED_STAGE1_BLOBS.items():
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
print("PASS: five Stage-01 predecessor blobs are exact; no active attempt/evidence/findings are persisted before execution")
