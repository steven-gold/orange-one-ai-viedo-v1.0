#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / 'governance/ci/prepare_stage02_external_authority_reexecution_clean_baseline_r3.py'


def die(msg):
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)

source = TARGET.read_text(encoding='utf-8')
structural_old = "ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py'"
structural_new = "ROOT / 'governance/ci/validate_current_stage2_materialized_closure_external_aware_r3.py'"
continuity_old = "ROOT / 'governance/ci/validate_stage02_remediation_reset_continuity_r3.py'"
continuity_new = "ROOT / 'governance/ci/validate_stage02_remediation_reset_continuity_external_aware_r3.py'"

if source.count(structural_old) != 1:
    die('R3_PREP_STRUCTURAL_VALIDATOR_REFERENCE_COUNT_DRIFT:' + str(source.count(structural_old)))
if source.count(continuity_old) != 2:
    die('R3_PREP_CONTINUITY_VALIDATOR_REFERENCE_COUNT_DRIFT:' + str(source.count(continuity_old)))

source = source.replace(structural_old, structural_new, 1)
source = source.replace(continuity_old, continuity_new, 2)

if source.count(structural_old) != 0 or source.count(continuity_old) != 0:
    die('R3_PREP_OLD_VALIDATOR_REFERENCE_RESIDUAL')
if source.count(structural_new) != 1:
    die('R3_PREP_EXTERNAL_AWARE_STRUCTURAL_REFERENCE_COUNT_DRIFT')
if source.count(continuity_new) != 2:
    die('R3_PREP_EXTERNAL_AWARE_CONTINUITY_REFERENCE_COUNT_DRIFT')

ns = {'__name__': '__main__', '__file__': str(TARGET)}
exec(compile(source, str(TARGET), 'exec'), ns, ns)
