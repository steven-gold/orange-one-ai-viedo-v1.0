#!/usr/bin/env python3
from pathlib import Path
import ast
import sys

ROOT = Path(__file__).resolve().parents[2]
SCANNER = ROOT / "governance/ci/run_current_stage2_actual_test.py"


def die(msg):
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)

if not SCANNER.is_file():
    die("R29_SCANNER_MISSING")
text = SCANNER.read_text(encoding="utf-8")
required_tokens = [
    "failure_recovery_not_applicable = (",
    "not is_effectful",
    "kind == 'CLIENT_STATE_OR_VIEW_NO_API_REQUIRED'",
    "rb.get('api_required') is False",
    "and not transitions_by_action.get(aid)",
    "elif not failure_recovery_not_applicable and not any((transitions.get(tid) or {}).get('recovery')",
]
for token in required_tokens:
    if text.count(token) != 1:
        die(f"R29_REQUIRED_TOKEN_DENOMINATOR:{token}:{text.count(token)}")
if "elif not any((transitions.get(tid) or {}).get('recovery') for tid in transitions_by_action.get(aid, [])):\n            add(gaps, page, 'ARCHITECTURE_GAP', 'FAILURE_STATE_ERROR_BINDING_MISSING'" in text:
    die("R29_OLD_UNCONDITIONAL_FAILURE_RULE_STILL_PRESENT")
if text.count("if err not in errors:") != 1 or text.count("RECOVERY_CONTRACT_MISSING") != 1:
    die("R29_EXPLICIT_ERROR_VALIDATION_DRIFT")
try:
    tree = ast.parse(text, filename=str(SCANNER))
except SyntaxError as exc:
    die(f"R29_SCANNER_SYNTAX_ERROR:{exc}")
fresh = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "fresh_scan"]
if len(fresh) != 1:
    die(f"R29_FRESH_SCAN_DENOMINATOR:{len(fresh)}")
print("PASS: R29 canonical scanner contains one exact applicability guard")
print("PASS: old unconditional failure/recovery emission removed; explicit error_uid validation preserved")
