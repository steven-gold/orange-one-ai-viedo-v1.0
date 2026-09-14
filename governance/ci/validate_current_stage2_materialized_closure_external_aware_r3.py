#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
LEGACY = ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py'
EXTERNAL = ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/EXTERNAL_AUTHORITY'
EXTERNAL_VALIDATOR = ROOT / 'governance/ci/validate_current_stage2_external_authority_resolution_r3.py'


def die(msg):
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)

if EXTERNAL.exists():
    cp = subprocess.run([sys.executable, str(EXTERNAL_VALIDATOR)], cwd=str(ROOT), text=True)
    if cp.returncode != 0:
        die('EXTERNAL_AUTHORITY_TREE_PRESENT_BUT_EXACT_R3_VALIDATION_FAILED')

source = LEGACY.read_text(encoding='utf-8')
old = '''if (OUT / "EXTERNAL_AUTHORITY").exists():\n    errors.append("STALE_EXTERNAL_AUTHORITY_MATERIALIZATION_FORBIDDEN")'''
new = '''if (OUT / "EXTERNAL_AUTHORITY").exists():\n    pass  # Exact external Authority tree was prevalidated by external-aware R3 wrapper.'''
if source.count(old) != 1:
    die('LEGACY_STRUCTURAL_EXTERNAL_AUTHORITY_RULE_DRIFT')
source = source.replace(old, new, 1)
old_print = 'print("PASS: GAP-001..GAP-008 remain unresolved and no stale EXTERNAL_AUTHORITY tree was restored")'
new_print = 'print("PASS: Stage-01 external Authority reference union remains preserved; any Stage-02 EXTERNAL_AUTHORITY tree passed exact R3 validation")'
if source.count(old_print) != 1:
    die('LEGACY_STRUCTURAL_STATUS_MESSAGE_DRIFT')
source = source.replace(old_print, new_print, 1)
ns = {'__name__': '__main__', '__file__': str(LEGACY)}
exec(compile(source, str(LEGACY), 'exec'), ns, ns)
print('PASS: external-aware structural wrapper preserved legacy structural checks and replaced only the stale directory-existence rejection')
