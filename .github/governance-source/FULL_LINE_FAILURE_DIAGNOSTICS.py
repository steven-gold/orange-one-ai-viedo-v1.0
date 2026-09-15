#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".github/governance-source/active/source"
GOV = SOURCE / "09_TESTS/governance"
RESULT = ROOT / ".github/governance-source/FULL_LINE_SYSTEM_GATE_RESULT.json"
OUT = ROOT / ".github/governance-source/FULL_LINE_FAILURE_DIAGNOSTICS.json"
TRUST_ROOT = Path("/tmp/acpos-governance-external-trust-root.json")


def emit(obj: object) -> None:
    print(json.dumps(obj, ensure_ascii=False, sort_keys=True))


diagnostic = {
    "artifact_type": "NON_NORMATIVE_FULL_LINE_FAILURE_DIAGNOSTICS",
    "normative_authority": False,
    "source_result_ref": RESULT.relative_to(ROOT).as_posix(),
    "failed_preformal_checks": [],
    "failed_suite_reexecutions": [],
    "diagnostic_status": "NOT_REQUIRED",
}

if not RESULT.is_file():
    diagnostic["diagnostic_status"] = "BLOCKED_RESULT_MISSING"
    diagnostic["error"] = "FULL_LINE_SYSTEM_GATE_RESULT_MISSING"
else:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    if result.get("result") == "PASS":
        diagnostic["diagnostic_status"] = "NOT_REQUIRED_FULL_LINE_PASS"
    else:
        diagnostic["diagnostic_status"] = "CAPTURED"
        preformal = result.get("preformal") or {}
        for check in preformal.get("checks") or []:
            if check.get("status") != "PASS":
                diagnostic["failed_preformal_checks"].append(check)
                emit({"FULL_LINE_FAILED_CHECK_DETAIL": check})

        mandatory = next(
            (c for c in (preformal.get("checks") or [])
             if c.get("check_id") == "mandatory_regression_and_package_integrity"),
            {},
        )
        failed_suite_names = [
            rec.get("suite")
            for rec in (mandatory.get("suites") or [])
            if rec.get("ok") is not True and rec.get("suite")
        ]

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPYCACHEPREFIX"] = "/tmp/acpos-governance-pycache"
        env["WEB_GOVERNANCE_PREFORMAL_SUITE_CHILD"] = "1"
        env["WEB_GOVERNANCE_TRUST_ROOT"] = str(TRUST_ROOT)

        if not TRUST_ROOT.is_file():
            diagnostic["trust_root_warning"] = "EXTERNAL_TRUST_ROOT_NOT_PRESENT_AFTER_FULL_LINE_RUN"

        for name in failed_suite_names:
            path = GOV / name
            rec = {"suite": name, "path": path.relative_to(ROOT).as_posix()}
            if not path.is_file():
                rec["status"] = "MISSING"
                diagnostic["failed_suite_reexecutions"].append(rec)
                emit({"FULL_LINE_FAILED_SUITE_DETAIL": rec})
                continue
            try:
                cp = subprocess.run(
                    [sys.executable, str(path)],
                    cwd=str(GOV),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                rec["returncode"] = cp.returncode
                rec["stderr_tail"] = cp.stderr[-4000:]
                try:
                    rec["parsed"] = json.loads(cp.stdout)
                except Exception as exc:
                    rec["parse_error"] = repr(exc)
                    rec["stdout_tail"] = cp.stdout[-8000:]
            except subprocess.TimeoutExpired:
                rec["status"] = "TIMEOUT"
            diagnostic["failed_suite_reexecutions"].append(rec)
            emit({"FULL_LINE_FAILED_SUITE_DETAIL": rec})

OUT.write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("PASS: Full-Line failure diagnostics persisted")
