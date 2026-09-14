#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / 'governance/ci/prepare_stage02_external_authority_reexecution_clean_baseline_r3.py'


def die(msg):
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)

source = TARGET.read_text(encoding='utf-8')
replacements = [
    ("ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py'", "ROOT / 'governance/ci/validate_current_stage2_materialized_closure_external_aware_r3.py'"),
    ("ROOT / 'governance/ci/validate_stage02_remediation_reset_continuity_r3.py'", "ROOT / 'governance/ci/validate_stage02_remediation_reset_continuity_external_aware_r3.py'"),
]
for old, new in replacements:
    if source.count(old) != 1:
        die('R3_PREP_VALIDATOR_BINDING_DRIFT:' + old)
    source = source.replace(old, new, 1)
old_post = "ROOT / 'governance/ci/validate_stage02_remediation_reset_continuity_r3.py'"
new_post = "ROOT / 'governance/ci/validate_stage02_remediation_reset_continuity_external_aware_r3.py'"
if source.count(old_post) != 1:
    die('R3_PREP_POST_RESET_CONTINUITY_BINDING_DRIFT')
source = source.replace(old_post, new_post, 1)
ns = {'__name__': '__main__', '__file__': str(TARGET)}
exec(compile(source, str(TARGET), 'exec'), ns, ns)
