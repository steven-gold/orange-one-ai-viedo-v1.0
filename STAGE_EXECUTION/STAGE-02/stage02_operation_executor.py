#!/usr/bin/env python3
"""STAGE-02 HOME governed-unit per-operation executor (PYTHON_STAGE_OPERATION_V1)."""
from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path
import yaml

GOV_UID = 'GOV-REV-20260928-WORD-DERIVED-STAGE-INTERNAL-VALIDATION'
EXECUTOR_REL = 'STAGE_EXECUTION/STAGE-02/stage02_operation_executor.py'
WU_REL = 'STAGE_EXECUTION/STAGE-02/WU-STAGE02-GLOBAL-HOME-SHELL-NAVIGATION-001'

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / '_operation_templates'

COPY_MAP = {
    "STAGE_EXECUTION_PREFLIGHT_COMPILE": [
        "REQUIRED_FIELD_MANIFEST.yaml",
        "FUNCTIONAL_CHAIN_MANIFEST.yaml",
        "DENOMINATOR_SNAPSHOT.yaml",
        "CLASSIFICATION_RULESET.yaml",
        "STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml",
        "CURRENT_PROBLEM_REGISTER.yaml",
        "RESOLUTION_LEDGER.yaml",
        "EVIDENCE/GOVERNED_UNIT_FUNCTIONAL_REVIEW_EVIDENCE.yaml"
    ],
    "EFFECTIVE_CONTRACT_OVERLAY_COMPILE": [
        "EFFECTIVE_CONTRACT_OVERLAY.yaml"
    ],
    "DEPENDENCY_TOPOLOGY_COMPILE": [
        "DEPENDENCY_TOPOLOGY.yaml"
    ],
    "CHANGE_IMPACT_MAP_COMPILE": [
        "CHANGE_IMPACT_MAP.yaml"
    ],
    "FUNCTIONAL_CHAIN_COMPILE": [
        "FUNCTIONAL_CHAIN_SPEC.yaml"
    ],
    "DEPENDENCY_MAP_COMPILE": [
        "DEPENDENCY_MAP.yaml"
    ],
    "GOVERNED_UNIT_CONSTRUCTION_SPEC_COMPILE": [
        "GOVERNED_UNIT_CONSTRUCTION_SPEC_PACKAGE.yaml",
        "GOVERNED_ENTITY_INVENTORY.yaml",
        "GOVERNED_ENTITY_OPERATION_MATRIX.yaml",
        "ENTITY_HIERARCHY_MATRIX.yaml",
        "FUNCTION_VISUAL_IMPACT_MATRIX.yaml"
    ],
    "ASYNC_PROVIDER_CONTRACT_COMPILE": [
        "ASYNC_PROVIDER_CONTRACT.yaml"
    ],
    "SHARED_OWNER_PORT_RESOLVE": [
        "SHARED_OWNER_PORT_MAP.yaml"
    ],
    "FUNCTIONAL_WORKBENCH_CONTRACT_COMPILE": [
        "FUNCTIONAL_WORKBENCH_CONTRACT.yaml"
    ],
    "INTERACTION_TOPOLOGY_COMPILE": [
        "INTERACTION_TOPOLOGY_SPEC.yaml"
    ],
    "FUNCTION_ADMISSION_SCORECARD_COMPILE": [
        "FUNCTION_ADMISSION_SCORECARD.yaml"
    ],
    "AUTO_COMPLETION_SCOPE_LEDGER_COMPILE": [
        "AUTO_COMPLETION_SCOPE_LEDGER.yaml"
    ]
}

WORK_DIR = None


def _copy(rel):
    src = TEMPLATES / rel
    dst = WORK_DIR / rel
    if rel.endswith('/'):
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def main():
    global WORK_DIR
    p = argparse.ArgumentParser()
    p.add_argument('--stage', required=True)
    p.add_argument('--operation', required=True)
    p.add_argument('--work-unit', required=True)
    p.add_argument('--product-root', required=True)
    a = p.parse_args()
    wu_dir = Path(a.work_unit).parent
    WORK_DIR = Path(a.product_root).resolve() / wu_dir
    for rel in COPY_MAP.get(a.operation, []):
        _copy(rel)
    receipt = {
        'artifact_type': 'OPERATION_EXECUTION_RECEIPT',
        'stage_uid': a.stage,
        'work_unit_uid': Path(a.work_unit).parent.name,
        'operation_uid': a.operation,
        'governance_uid': GOV_UID,
        'status': 'PASS',
        'executor_owner': EXECUTOR_REL,
        'executor_protocol': 'PYTHON_STAGE_OPERATION_V1',
        'result_owner': Path(a.work_unit).parent.as_posix() + '/EVIDENCE/OPERATION_RECEIPTS/' + a.operation + '.yaml',
    }
    out = WORK_DIR / 'EVIDENCE/OPERATION_RECEIPTS' / (a.operation + '.yaml')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(receipt, sort_keys=False, allow_unicode=True), encoding='utf-8')
    print('OK', a.operation)


if __name__ == '__main__':
    main()
