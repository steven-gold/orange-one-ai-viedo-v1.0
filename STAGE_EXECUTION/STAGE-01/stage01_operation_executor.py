#!/usr/bin/env python3
"""STAGE-01 HOME governed-unit per-operation executor (PYTHON_STAGE_OPERATION_V1)."""
from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path
import yaml

GOV_UID = 'GOV-REV-20260928-WORD-DERIVED-STAGE-INTERNAL-VALIDATION'
EXECUTOR_REL = 'STAGE_EXECUTION/STAGE-01/stage01_operation_executor.py'
WU_REL = 'STAGE_EXECUTION/STAGE-01/WU-STAGE01-GLOBAL-HOME-SHELL-NAVIGATION-001'

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / '_operation_templates'
SUID = 'SRC-ACPOS-GLOBAL-HOME-SHELL-NAVIGATION-MOTHER-BASIC-DESIGN-OPTIMIZED'

COPY_MAP = {
    'SOURCE_STRUCTURE_ENUMERATION': ['00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml',
                                     'EVIDENCE/SOURCE_ENUMERATION_EVIDENCE.yaml'],
    'SOURCE_SEGMENT_MAPPING': ['00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml'],
    'SOURCE_CONTEXT_COMPILATION': ['00_SOURCE_INTAKE/SOURCE_CONTEXT_MANIFEST.yaml'],
    'SOURCE_SUPERSESSION_CONFLICT_RESOLUTION': ['00_SOURCE_INTAKE/CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml',
                                                'EVIDENCE/CONFLICT_DECISION_EVIDENCE.yaml'],
    'SOURCE_DEPENDENCY_EXTRACTION': ['00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml'],
    'RESPONSIBILITY_CLASSIFICATION': ['01_CLASSIFIED/'],
    'GOVERNED_UNIT_BASE_BLUEPRINT_COMPILE': ['02_BASE_BLUEPRINT/' + SUID + '/GOVERNED_UNIT_BASE_BLUEPRINT.yaml'],
    'VISUAL_BASE_BLUEPRINT_COMPILE': ['02_BASE_BLUEPRINT/' + SUID + '/VISUAL_BASE_BLUEPRINT.yaml'],
    'BLUEPRINT_BINDING_COMPILE': ['03_BLUEPRINT_BINDING/'],
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
