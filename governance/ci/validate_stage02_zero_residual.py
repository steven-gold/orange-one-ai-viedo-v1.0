#!/usr/bin/env python3
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
ENTRY_RECEIPTS = {
    'governance/test/stage02/STAGE02_STAGE_FROZEN_GOVERNANCE_RECEIPT.yaml',
    'governance/test/stage02/STAGE02_CLEAN_BASELINE_RESET_RECEIPT.yaml',
}
CANONICAL_ENTRY_WORKFLOW = '.github/workflows/stage02-actual-test.yml'
STALE_RUN_ROOT = re.compile(r'^00_SOURCE_INTAKE/(?:fresh_run_\d+|run_[^/]+)(?:/|$)')
STALE_STAGE2_FILE = re.compile(r'(?:^|/)(?:ARTIFACT_PLAN|EXECUTION_STATE|RUN_MANIFEST)_R\d+\.yaml$')
STALE_AUDIT_FILE = re.compile(r'^11_EVIDENCE/audit/(?:GOVERNANCE_STAGE_LOCK|SEALED_GOVERNANCE_TEST_BASELINE)_R\d+\.yaml$|^11_EVIDENCE/audit/STAGE2_FULL_TEST_CYCLE_R\d+\.yaml$')

def git(*args):
    cp = subprocess.run(['git', *args], cwd=ROOT, text=True, capture_output=True)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip())
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

    stale_roots = sorted(p for p in tracked if STALE_RUN_ROOT.match(p))
    if stale_roots:
        return fail('STALE_PRODUCT_RUN_ROOT_TRACKED:' + ','.join(stale_roots))

    stale_stage_files = sorted(p for p in tracked if STALE_STAGE2_FILE.search(p) or STALE_AUDIT_FILE.search(p))
    if stale_stage_files:
        return fail('STALE_STAGE_EXECUTION_RESIDUAL_TRACKED:' + ','.join(stale_stage_files))

    if '.github/stage02-test' in tracked or any(p.startswith('.github/stage02-test/') for p in tracked):
        return fail('LEGACY_STAGE02_TEST_ROOT_TRACKED')

    stage02_workflows = sorted(p for p in tracked if p.startswith('.github/workflows/stage02-') and p.endswith(('.yml', '.yaml')))
    allowed_workflows = [CANONICAL_ENTRY_WORKFLOW] if ENTRY_RECEIPTS.issubset(tracked) else []
    if stage02_workflows != allowed_workflows:
        return fail('STAGE2_WORKFLOW_SET_INVALID:expected=' + ','.join(allowed_workflows) + ':actual=' + ','.join(stage02_workflows))

    print(f'PASS: Stage-02 current runtime/evidence/product residual count = 0; entry_receipts={len(stage2_current)}')
    print(f'PASS: canonical Stage-02 execution workflow set={stage02_workflows}')
    print('PASS: no fixed historical run root, historical blob baseline, or versioned Stage-02 residue is used by this guard')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
