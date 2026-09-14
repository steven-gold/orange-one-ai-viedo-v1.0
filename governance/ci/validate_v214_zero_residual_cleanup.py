#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]

forbidden_files = [
    'GOVERNANCE_CURRENT_R3.yaml',
    'GOVERNANCE_CURRENT_R4.yaml',
    'REBUILD_BRANCH_BASELINE.yaml',
    'REBUILD_BRANCH_BASELINE_R3.yaml',
    'REBUILD_BRANCH_BASELINE_R4.yaml',
    'governance/STAGE_TEST_CORRECTION_PROMOTION_POLICY_V1.yaml',
    'governance/BRANCH_RECOVERY_TRIGGER_2026-09-14.txt',
    'governance/current/v2.1.14/CANDIDATE_STATUS.yaml',
    '.github/workflows/stage-test-correction-promotion-policy.yml',
    '.github/workflows/rebuild-governance-gate.yml',
    '.github/workflows/temporary-governance-reference-scan.yml',
    'governance/ci/validate_stage_test_correction_promotion_policy.py',
    'governance/ci/run_stage1_stage2_cross_stage_replay.py',
    'governance/ci/validate_current_stage2_current_ledger_sync.py',
    'governance/ci/validate_current_stage2_current_ledger_sync_r4.py',
    'governance/ci/validate_sealed_v216_runtime.py',
    'governance/ci/validate_current_v217_upstream_projection.py',
    'governance/ci/validate_current_v218_upstream_projection.py',
]

errors=[]
for rel in forbidden_files:
    if (ROOT/rel).exists():
        errors.append(f'RESIDUAL_FILE:{rel}')

for rel in ('governance/test-runtime','governance/test-temporary','governance/candidates'):
    p=ROOT/rel
    if p.exists():
        files=[x for x in p.rglob('*') if x.is_file()]
        if files:
            errors.append(f'RESIDUAL_DIRECTORY:{rel}:{len(files)}')
        else:
            errors.append(f'EMPTY_RESIDUAL_DIRECTORY:{rel}')

root_current=sorted(p.name for p in ROOT.glob('GOVERNANCE_CURRENT*.yaml'))
if root_current != ['GOVERNANCE_CURRENT.yaml']:
    errors.append(f'CURRENT_POINTER_UNIVERSE:{root_current}')

current_dir=ROOT/'governance/current/v2.1.14'
component=current_dir/'TEST_FEEDBACK_TEMPORARY_ARTIFACT_LIFECYCLE_DELTA.yaml'
manifest=current_dir/'EFFECTIVE_TEST_GOVERNANCE_MANIFEST.yaml'
status=current_dir/'CURRENT_TEST_GOVERNANCE_STATUS.yaml'
for p,code in ((component,'V214_TEST_FEEDBACK_COMPONENT_MISSING'),(manifest,'V214_MANIFEST_MISSING'),(status,'V214_CURRENT_STATUS_MISSING')):
    if not p.is_file(): errors.append(code)
if manifest.is_file():
    text=manifest.read_text(encoding='utf-8')
    for token,code in (
      ('TEST_FEEDBACK_TEMPORARY_ARTIFACT_LIFECYCLE_DELTA.yaml','V214_MANIFEST_COMPONENT_BINDING_MISSING'),
      ('CURRENT_TEST_GOVERNANCE_STATUS.yaml','V214_CURRENT_STATUS_BINDING_MISSING'),
      ('standalone_operational_policy_outside_v214: FORBIDDEN','V214_SINGLE_GOVERNANCE_GUARD_MISSING'),
      ('applicability_must_be_proven_before_missing_output_is_counted_as_blocker: true','V214_APPLICABILITY_GUARD_MISSING')):
        if token not in text: errors.append(code)

if errors:
    for e in errors: print('BLOCK:',e,file=sys.stderr)
    raise SystemExit(1)
print('PASS: v2.1.14 is the only active test-governance rule layer for the targeted rerun')
print('PASS: legacy Current aliases, standalone correction policy, retired runtime shards, candidate duplicates/status, and temporary scan artifacts are absent')
print('PASS: no temporary correction directory remains after governance promotion')
