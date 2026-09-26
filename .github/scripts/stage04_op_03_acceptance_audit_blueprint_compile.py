#!/usr/bin/env python3
"""STAGE-04 operation executor: ACCEPTANCE_AUDIT_BLUEPRINT_COMPILE.

Compiles the acceptance/audit blueprint from the frozen Basic Design Package
domains. Every acceptance item resolves to the exact bound evidence refs.
"""
from __future__ import annotations

import argparse
import sys

from stage04_operation_lib import (
    compile_acceptance_audit_blueprint,
    guard_operation,
    write_operation_receipt,
)

OPERATION = "ACCEPTANCE_AUDIT_BLUEPRINT_COMPILE"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", required=True)
    p.add_argument("--operation", required=True)
    p.add_argument("--work-unit", required=True)
    p.add_argument("--product-root", required=True)
    a = p.parse_args()
    if a.operation != OPERATION:
        raise SystemExit(f"BLOCK:OPERATION_MISMATCH:{a.operation}")
    root, wu, work, _ = guard_operation(a.stage, a.operation, a.work_unit, a.product_root)
    blueprint = compile_acceptance_audit_blueprint(root, wu)
    ref = write_operation_receipt(root, wu, OPERATION, work["current_governance_uid"])
    print(f"PASS: {OPERATION} for {wu} blueprint={blueprint['artifact_uid']} receipt={ref}")


if __name__ == "__main__":
    sys.exit(main())
