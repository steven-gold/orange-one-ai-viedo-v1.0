#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LEGACY = ROOT / 'governance/ci/validate_stage02_successor_integrity.py'


def die(msg):
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)

source = LEGACY.read_text(encoding='utf-8')
old = "MATERIAL_VALIDATOR = ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py'"
new = "MATERIAL_VALIDATOR = ROOT / 'governance/ci/validate_current_stage2_materialized_closure_external_aware_r3.py'"
if source.count(old) != 1:
    die('LEGACY_SUCCESSOR_MATERIAL_VALIDATOR_BINDING_DRIFT')
source = source.replace(old, new, 1)
ns = {'__name__': '__main__', '__file__': str(LEGACY)}
exec(compile(source, str(LEGACY), 'exec'), ns, ns)
print('PASS: successor integrity used external-aware structural validator while preserving all legacy successor-state checks')
