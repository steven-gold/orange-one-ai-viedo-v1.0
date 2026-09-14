#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / 'governance/ci/run_current_stage2_external_authority_reexecution_r3.py'


def die(msg):
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)

source = RUNNER.read_text(encoding='utf-8')
old = "ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py'"
new = "ROOT / 'governance/ci/validate_current_stage2_materialized_closure_external_aware_r3.py'"
if source.count(old) != 1:
    die('R3_RUNNER_STRUCTURAL_VALIDATOR_BINDING_DRIFT')
source = source.replace(old, new, 1)
ns = {'__name__': '__main__', '__file__': str(RUNNER)}
exec(compile(source, str(RUNNER), 'exec'), ns, ns)
