#!/usr/bin/env python3
"""STAGE-04 operation executor: BASIC_DESIGN_PACKAGE_COMPILE.

Preapproval-allowed operation. Compiles the Basic Design Package by binding
each governed Basic Design domain to already-frozen upstream artifacts. This
operation must not consume the human approval (that is the successor
DESIGN_FREEZE_VALIDATE operation).
"""
from __future__ import annotations

import argparse
import sys

from stage04_operation_lib import (
    compile_basic_design_package,
    guard_operation,
    write_operation_receipt,
)

OPERATION = "BASIC_DESIGN_PACKAGE_COMPILE"


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
    pkg = compile_basic_design_package(root, wu, work["current_governance_uid"])
    ref = write_operation_receipt(root, wu, OPERATION, work["current_governance_uid"])
    print(f"PASS: {OPERATION} for {wu} package={pkg['artifact_uid']} receipt={ref}")


if __name__ == "__main__":
    sys.exit(main())
