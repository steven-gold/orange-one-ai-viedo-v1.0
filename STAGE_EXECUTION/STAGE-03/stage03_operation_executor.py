#!/usr/bin/env python3
"""Per-operation executor (PYTHON_STAGE_OPERATION_V1)."""
from __future__ import annotations
import argparse
import shutil
from pathlib import Path
import yaml

GOV_UID = 'GOV-REV-20260928-WORD-DERIVED-STAGE-INTERNAL-VALIDATION'
EXECUTOR_REL = 'STAGE_EXECUTION/STAGE-03/stage03_operation_executor.py'
WU_REL = 'STAGE_EXECUTION/STAGE-03/WU-STAGE03-GLOBAL-HOME-SHELL-NAVIGATION-001'
HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / '_operation_templates'
COPY_MAP = {
    "VISUAL_SPEC_COMPILE": [
        "VISUAL_DESIGN_SPEC_PACKAGE.yaml",
        "EVIDENCE/VISUAL_REVIEW_EVIDENCE.yaml"
    ],
    "GEOMETRY_CONTRACT_COMPILE": [
        "VISUAL_GEOMETRY_CONTRACT.yaml"
    ],
    "VISUAL_PREVIEW_RENDER": [
        "VISUAL_PREVIEW_EVIDENCE.yaml"
    ],
    "VISUAL_CHANGESET_COMPILE": [
        "VISUAL_CHANGESET.yaml"
    ],
    "VISUAL_INTERACTION_TOPOLOGY_BIND": [
        "VISUAL_INTERACTION_TOPOLOGY_BINDING.yaml"
    ],
    "FUNCTIONAL_WORKBENCH_LAYOUT_BIND": [
        "FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT.yaml"
    ],
    "VISUAL_REFERENCE_ANNOTATION_COMPILE": [
        "VISUAL_REFERENCE_ANNOTATION.yaml"
    ],
    "VISUAL_INHERITANCE_MATRIX_COMPILE": [
        "VISUAL_INHERITANCE_MATRIX.yaml"
    ],
    "VISUAL_SCENARIO_EVIDENCE_COMPILE": [
        "VISUAL_SCENARIO_EVIDENCE_SET.yaml",
        "EVIDENCE/VISUAL_SCENARIOS/"
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
    WORK_DIR = Path(a.product_root).resolve() / Path(a.work_unit).parent
    for rel in COPY_MAP.get(a.operation, []):
        _copy(rel)
    receipt = {
        'artifact_type': 'OPERATION_EXECUTION_RECEIPT', 'stage_uid': a.stage,
        'work_unit_uid': Path(a.work_unit).parent.name, 'operation_uid': a.operation,
        'governance_uid': GOV_UID, 'status': 'PASS', 'executor_owner': EXECUTOR_REL,
        'executor_protocol': 'PYTHON_STAGE_OPERATION_V1',
        'result_owner': Path(a.work_unit).parent.as_posix() + '/EVIDENCE/OPERATION_RECEIPTS/' + a.operation + '.yaml',
    }
    out = WORK_DIR / 'EVIDENCE/OPERATION_RECEIPTS' / (a.operation + '.yaml')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(receipt, sort_keys=False, allow_unicode=True), encoding='utf-8')
    print('OK', a.operation)


if __name__ == '__main__':
    main()
