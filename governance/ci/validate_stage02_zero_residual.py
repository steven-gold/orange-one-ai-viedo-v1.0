#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
ENTRY_RECEIPTS = {
    'governance/test/stage02/STAGE02_STAGE_FROZEN_GOVERNANCE_RECEIPT.yaml',
    'governance/test/stage02/STAGE02_CLEAN_BASELINE_RESET_RECEIPT.yaml',
}
FORBIDDEN = [
    '.github/stage02-test',
    '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT',
    '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/evidence/PAGE_FUNCTIONAL_REVIEW_EVIDENCE.yaml',
    '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/evidence/PAGE_FUNCTIONAL_REVIEW_EVIDENCE_R2.yaml',
    '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/evidence/STAGE2_FUNCTIONAL_CHAIN_PREFLIGHT_EVIDENCE.yaml',
    '00_SOURCE_INTAKE/fresh_run_003/ARTIFACT_PLAN_R3.yaml',
    '00_SOURCE_INTAKE/fresh_run_003/ARTIFACT_PLAN_R4.yaml',
    '00_SOURCE_INTAKE/fresh_run_003/EXECUTION_STATE_R3.yaml',
    '00_SOURCE_INTAKE/fresh_run_003/EXECUTION_STATE_R4.yaml',
    '00_SOURCE_INTAKE/fresh_run_003/RUN_MANIFEST_R3.yaml',
    '00_SOURCE_INTAKE/fresh_run_003/RUN_MANIFEST_R4.yaml',
    '11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK_R3.yaml',
    '11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK_R4.yaml',
    '11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE_R3.yaml',
    '11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE_R4.yaml',
    '11_EVIDENCE/audit/STAGE2_FULL_TEST_CYCLE_R1.yaml',
]
EXPECTED_STAGE1_BLOBS = {
    '00_SOURCE_INTAKE/fresh_run_003/ARTIFACT_PLAN.yaml': 'c64ab04846b228c14978c07f88164a8d02a22f0d',
    '00_SOURCE_INTAKE/fresh_run_003/EXECUTION_STATE.yaml': '4f2bf558f5807a03d081f848184334ba16901fb1',
    '00_SOURCE_INTAKE/fresh_run_003/RUN_MANIFEST.yaml': '110e672114aa244279ad5af932c83d169fdebfe5',
    '11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml': '96d9e64940f24154cf086fdd26ee0e6d4e0653ef',
    '11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml': 'a75551629448349732c08e34d252fee8fb040e94',
}

def git(*args):
    cp = subprocess.run(['git', *args], cwd=ROOT, text=True, capture_output=True)
    if cp.returncode != 0: raise RuntimeError(cp.stderr.strip())
    return cp.stdout.strip()

def fail(msg):
    print(f'BLOCK: {msg}', file=sys.stderr)
    return 1

def main():
    tracked = set(git('ls-files').splitlines())
    stage2_current = {p for p in tracked if p.startswith('governance/test/stage02/')}
    unexpected_stage2_current = sorted(stage2_current - ENTRY_RECEIPTS)
    if unexpected_stage2_current:
        return fail('STAGE2_CURRENT_RUNTIME_RESIDUAL_TRACKED:' + ','.join(unexpected_stage2_current))
    for path in FORBIDDEN:
        if path in tracked or any(p.startswith(path.rstrip('/') + '/') for p in tracked):
            return fail(f'STAGE2_RESIDUAL_TRACKED:{path}')
    stage02_workflows = sorted(p for p in tracked if p.startswith('.github/workflows/stage02-') and p.endswith(('.yml', '.yaml')))
    if stage02_workflows:
        return fail('STAGE2_WORKFLOW_RESIDUAL_TRACKED:' + ','.join(stage02_workflows))
    for path, expected in EXPECTED_STAGE1_BLOBS.items():
        actual = git('rev-parse', f'HEAD:{path}')
        if actual != expected:
            return fail(f'STAGE1_RESET_BLOB_MISMATCH:{path}:expected={expected}:actual={actual}')
    state = (ROOT / '00_SOURCE_INTAKE/fresh_run_003/EXECUTION_STATE.yaml').read_text(encoding='utf-8')
    if 'state: STAGE1_VALIDATION_COMPLETED_CI_PASS' not in state: return fail('EXECUTION_STATE_NOT_STAGE1_CI_PASS')
    if 'stage2_started: false' not in state: return fail('EXECUTION_STATE_STAGE2_NOT_FALSE')
    if 'stage2_current:' in state or 'current_stage2:' in state: return fail('EXECUTION_STATE_CONTAINS_STAGE2_CURRENT_PROJECTION')
    active = (ROOT / 'governance/test/ACTIVE_STATE.yaml').read_text(encoding='utf-8')
    for token in ('current_stage: STAGE-01-CLOSED','result: NOT_EXECUTED','prior_results_authoritative_for_next_run: false','status: ACTIVE_STAGE1_CLOSED_STAGE2_CLEARED'):
        if token not in active: return fail(f'ACTIVE_STATE_RESET_TOKEN_MISSING:{token}')
    print(f'PASS: Stage-02 current runtime/evidence/product residual count = 0; entry_receipts={len(stage2_current)}')
    print('PASS: five current ledgers restored to exact Stage-01 CI-PASS blobs')
    print('PASS: Stage-01 remains closed; Stage-02 is NOT_EXECUTED')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
