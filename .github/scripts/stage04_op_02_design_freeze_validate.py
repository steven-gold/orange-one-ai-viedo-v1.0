#!/usr/bin/env python3
"""STAGE-04 operation executor: DESIGN_FREEZE_VALIDATE.

Approval-consumption operation. Normalizes the recorded human design approval
into the Stage-04 FORMAL_APPROVAL disposition, freezes the Basic Design
Package, materializes DESIGN_APPROVAL_EVIDENCE and emits the
FOUNDATION_BARRIER_RECORD. The human decision is never authored here.
"""
from __future__ import annotations

import argparse
import sys

from stage04_operation_lib import (
    consume_design_approval_and_freeze,
    guard_operation,
    write_operation_receipt,
)

OPERATION = "DESIGN_FREEZE_VALIDATE"


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
    barrier = consume_design_approval_and_freeze(root, wu, work["current_governance_uid"])
    ref = write_operation_receipt(root, wu, OPERATION, work["current_governance_uid"])
    print(f"PASS: {OPERATION} for {wu} barrier={barrier['artifact_uid']} receipt={ref}")


if __name__ == "__main__":
    sys.exit(main())
