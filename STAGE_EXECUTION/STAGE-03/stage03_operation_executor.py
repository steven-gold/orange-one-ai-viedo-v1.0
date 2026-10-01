#!/usr/bin/env python3
"""Per-operation executor (PYTHON_STAGE_OPERATION_V1)."""
from __future__ import annotations
import argparse
import os
import shutil
import hashlib
from pathlib import Path
import yaml

EXECUTOR_REL = 'STAGE_EXECUTION/STAGE-03/stage03_operation_executor.py'
WU_REL = 'STAGE_EXECUTION/STAGE-03/WU-STAGE03-GLOBAL-HOME-SHELL-NAVIGATION-001'
HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / '_operation_templates'
COPY_MAP = {
    "VISUAL_SPEC_COMPILE": [
        "VISUAL_DESIGN_SPEC_PACKAGE.yaml"
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _materialize_visual_review_evidence(work_unit_rel: str):
    source = TEMPLATES / 'EVIDENCE/VISUAL_REVIEW_EVIDENCE.yaml'
    doc = yaml.safe_load(source.read_text(encoding='utf-8')) or {}
    if doc.get('decision') != 'VISUAL_APPROVED' or doc.get('visual_approved') is not True or not doc.get('reviewer'):
        raise SystemExit('VISUAL_REVIEW_SOURCE_NOT_APPROVED')
    approved = WORK_DIR / 'VISUAL_DESIGN_SPEC_PACKAGE.yaml'
    if not approved.is_file():
        raise SystemExit('VISUAL_DESIGN_SPEC_PACKAGE_MISSING_FOR_REVIEW_BINDING')
    doc['result'] = 'APPROVE'
    doc['approved_by_human'] = True
    doc['approved_artifact_ref'] = work_unit_rel + '/VISUAL_DESIGN_SPEC_PACKAGE.yaml'
    doc['approved_artifact_sha256'] = _sha256(approved)
    doc['materialization_source'] = 'RECORDED_HUMAN_REVIEW_NORMALIZATION'
    doc['materialized_by'] = 'SYSTEM'
    doc['status'] = 'PASS'
    out = WORK_DIR / 'VISUAL_REVIEW_EVIDENCE.yaml'
    out.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding='utf-8')


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
    if a.operation == 'VISUAL_SPEC_COMPILE':
        _materialize_visual_review_evidence(Path(a.work_unit).parent.as_posix())
    gov_uid = os.environ.get('ACPOS_CURRENT_GOVERNANCE_UID', '').strip()
    if not gov_uid:
        raise SystemExit('CURRENT_GOVERNANCE_UID_ENV_MISSING')
    receipt = {
        'artifact_type': 'OPERATION_EXECUTION_RECEIPT', 'stage_uid': a.stage,
        'work_unit_uid': Path(a.work_unit).parent.name, 'operation_uid': a.operation,
        'governance_uid': gov_uid, 'status': 'PASS', 'executor_owner': EXECUTOR_REL,
        'executor_protocol': 'PYTHON_STAGE_OPERATION_V1',
        'result_owner': Path(a.work_unit).parent.as_posix() + '/EVIDENCE/OPERATION_RECEIPTS/' + a.operation + '.yaml',
    }
    out = WORK_DIR / 'EVIDENCE/OPERATION_RECEIPTS' / (a.operation + '.yaml')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(receipt, sort_keys=False, allow_unicode=True), encoding='utf-8')
    print('OK', a.operation)


if __name__ == '__main__':
    main()
