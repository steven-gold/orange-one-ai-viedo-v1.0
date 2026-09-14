#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / 'governance/ci/run_current_stage2_external_authority_reexecution_r3.py'


def die(msg):
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)

source = RUNNER.read_text(encoding='utf-8')
structural_old = "ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py'"
structural_new = "ROOT / 'governance/ci/validate_current_stage2_materialized_closure_external_aware_r3.py'"
continuity_old = "ROOT / 'governance/ci/validate_stage02_remediation_reset_continuity_r3.py'"
continuity_new = "ROOT / 'governance/ci/validate_stage02_remediation_reset_continuity_external_aware_r3.py'"

if source.count(structural_old) != 1:
    die('R3_RUNNER_STRUCTURAL_VALIDATOR_REFERENCE_COUNT_DRIFT:' + str(source.count(structural_old)))
if source.count(continuity_old) != 1:
    die('R3_RUNNER_CONTINUITY_VALIDATOR_REFERENCE_COUNT_DRIFT:' + str(source.count(continuity_old)))

source = source.replace(structural_old, structural_new, 1)
source = source.replace(continuity_old, continuity_new, 1)

if source.count(structural_old) != 0 or source.count(continuity_old) != 0:
    die('R3_RUNNER_LEGACY_VALIDATOR_REFERENCE_RESIDUAL')
if source.count(structural_new) != 1 or source.count(continuity_new) != 1:
    die('R3_RUNNER_EXTERNAL_AWARE_VALIDATOR_BINDING_DRIFT')

ns = {'__name__': '__main__', '__file__': str(RUNNER)}
exec(compile(source, str(RUNNER), 'exec'), ns, ns)
