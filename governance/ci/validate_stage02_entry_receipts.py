#!/usr/bin/env python3
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
import yaml

from governance_resolver import resolve

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / 'governance/test/stage02/STAGE02_STAGE_FROZEN_GOVERNANCE_RECEIPT.yaml'
BASELINE = ROOT / 'governance/test/stage02/STAGE02_CLEAN_BASELINE_RESET_RECEIPT.yaml'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
ZERO = ROOT / 'governance/ci/validate_stage02_zero_residual.py'
EXPECTED_ATTEMPT = 'STAGE02-FRESH-20260915-002'
EXPECTED_STAGE1_BLOBS = {
    '00_SOURCE_INTAKE/fresh_run_003/ARTIFACT_PLAN.yaml': 'c64ab04846b228c14978c07f88164a8d02a22f0d',
    '00_SOURCE_INTAKE/fresh_run_003/EXECUTION_STATE.yaml': '4f2bf558f5807a03d081f848184334ba16901fb1',
    '00_SOURCE_INTAKE/fresh_run_003/RUN_MANIFEST.yaml': '110e672114aa244279ad5af932c83d169fdebfe5',
    '11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml': '96d9e64940f24154cf086fdd26ee0e6d4e0653ef',
    '11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml': 'a75551629448349732c08e34d252fee8fb040e94',
}

def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)

def load(path: Path):
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    try:
        obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception as exc:
        die(f'PARSE:{path.relative_to(ROOT)}:{exc!r}')
    if not isinstance(obj, dict):
        die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj

def git(*args: str) -> str:
    cp = subprocess.run(['git', *args], cwd=ROOT, text=True, capture_output=True)
    if cp.returncode != 0:
        die(f'GIT_FAILED:{args!r}:{cp.stderr.strip()}')
    return cp.stdout.strip()

freeze = load(FREEZE)
baseline = load(BASELINE)
state = load(STATE)
uid = resolve()['governance_uid']
parent = git('rev-parse', 'HEAD^')

if freeze.get('artifact_type') != 'STAGE_FROZEN_GOVERNANCE_RECEIPT':
    die('FREEZE_RECEIPT_TYPE')
if freeze.get('stage_uid') != 'STAGE-02' or freeze.get('attempt_uid') != EXPECTED_ATTEMPT:
    die('FREEZE_RECEIPT_IDENTITY')
if freeze.get('frozen_governance_uid') != uid:
    die(f'FREEZE_UID_MISMATCH:expected={uid}:actual={freeze.get("frozen_governance_uid")}')
if freeze.get('preparation_parent_commit') != parent:
    die(f'FREEZE_PARENT_MISMATCH:expected={parent}:actual={freeze.get("preparation_parent_commit")}')
if freeze.get('prior_stage2_results_authoritative') is not False or freeze.get('prior_stage2_results_used') is not False:
    die('FREEZE_PRIOR_RESULT_CONTAMINATION')
if freeze.get('current_specification_mutation_allowed_during_stage') is not False:
    die('FREEZE_SPEC_MUTATION_NOT_BLOCKED')
if freeze.get('ai_autofill_allowed') is not False or freeze.get('semantic_inference_without_registered_authority_allowed') is not False:
    die('FREEZE_AI_INFERENCE_NOT_BLOCKED')

if baseline.get('artifact_type') != 'CLEAN_BASELINE_RESET_RECEIPT':
    die('BASELINE_RECEIPT_TYPE')
if baseline.get('stage_uid') != 'STAGE-02' or baseline.get('attempt_uid') != EXPECTED_ATTEMPT:
    die('BASELINE_RECEIPT_IDENTITY')
if baseline.get('baseline_parent_commit') != parent:
    die(f'BASELINE_PARENT_MISMATCH:expected={parent}:actual={baseline.get("baseline_parent_commit")}')
if baseline.get('predecessor_state') != 'STAGE1_VALIDATION_COMPLETED_CI_PASS':
    die('BASELINE_PREDECESSOR_STATE')
if baseline.get('stage2_started_in_predecessor') is not False:
    die('BASELINE_STAGE2_ALREADY_STARTED')
if baseline.get('expected_stage1_blobs') != EXPECTED_STAGE1_BLOBS:
    die('BASELINE_DECLARED_BLOBS_DRIFT')
for path, expected in EXPECTED_STAGE1_BLOBS.items():
    actual = git('rev-parse', f'HEAD:{path}')
    if actual != expected:
        die(f'BASELINE_BLOB_MISMATCH:{path}:expected={expected}:actual={actual}')

execution = state.get('execution') or {}
if execution.get('current_stage') != 'STAGE-01-CLOSED':
    die('ACTIVE_STATE_NOT_CLEAN_PRE_STAGE02')
if (execution.get('stage2') or {}).get('result') != 'NOT_EXECUTED':
    die('ACTIVE_STATE_STAGE2_NOT_NOT_EXECUTED')
if (state.get('stage02_active_attempt') or {}).get('active_evidence_present') is not False:
    die('ACTIVE_STATE_STALE_EVIDENCE')
if (state.get('stage02_active_attempt') or {}).get('active_findings_present') is not False:
    die('ACTIVE_STATE_STALE_FINDINGS')

cp = subprocess.run([sys.executable, str(ZERO)], cwd=ROOT, text=True)
if cp.returncode != 0:
    die('ZERO_RESIDUAL_VALIDATION_FAILED')

print(f'PASS: Stage-02 entry freeze receipt locks governance UID {uid}')
print(f'PASS: Stage-02 clean predecessor receipt binds parent {parent}')
print('PASS: five Stage-01 predecessor blobs are exact and Stage-02 active residual is zero')
print('PASS: prior Stage-02 results are non-authoritative and unused for this fresh attempt')
