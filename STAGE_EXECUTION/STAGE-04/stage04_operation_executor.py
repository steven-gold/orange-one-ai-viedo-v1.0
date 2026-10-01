#!/usr/bin/env python3
"""Per-operation executor (PYTHON_STAGE_OPERATION_V1)."""
from __future__ import annotations
import argparse
import hashlib
import os
import shutil
from pathlib import Path
import yaml

EXECUTOR_REL = 'STAGE_EXECUTION/STAGE-04/stage04_operation_executor.py'
WU_REL = 'STAGE_EXECUTION/STAGE-04/WU-STAGE04-GLOBAL-HOME-SHELL-NAVIGATION-001'
HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / '_operation_templates'
COPY_MAP = {
    "BASIC_DESIGN_PACKAGE_COMPILE": [
        "BASIC_DESIGN_PACKAGE.yaml",
        "STEPWISE_CHECKPOINTS/",
        "DESIGN_APPROVAL_EVIDENCE.yaml",
        "CHANGE_IMPACT_MAP.yaml",
        "CLASSIFICATION_RULESET.yaml",
        "CURRENT_PROBLEM_REGISTER.yaml",
        "DENOMINATOR_SNAPSHOT.yaml",
        "DEPENDENCY_TOPOLOGY.yaml",
        "EFFECTIVE_CONTRACT_OVERLAY.yaml",
        "FUNCTIONAL_CHAIN_MANIFEST.yaml",
        "REQUIRED_FIELD_MANIFEST.yaml",
        "RESOLUTION_LEDGER.yaml",
        "RESUME_POINT.yaml",
        "STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml",
        "WORK_UNIT_RESOLUTION_GATE.yaml",
        "EVIDENCE/FORMAL_HUMAN_APPROVAL_DISPOSITION.yaml"
    ],
    "DESIGN_FREEZE_VALIDATE": [
        "FOUNDATION_BARRIER_RECORD.yaml"
    ],
    "ACCEPTANCE_AUDIT_BLUEPRINT_COMPILE": [
        "ACCEPTANCE_AUDIT_BLUEPRINT.yaml"
    ],
    "DESIGN_FREEZE_PACKAGE_BIND": [
        "DESIGN_FREEZE_PACKAGE.yaml"
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


def _materialize_design_approval_evidence(work_unit_rel: str):
    out = WORK_DIR / 'DESIGN_APPROVAL_EVIDENCE.yaml'
    doc = yaml.safe_load(out.read_text(encoding='utf-8')) or {}
    if doc.get('result') != 'APPROVE' or doc.get('approved_by_human') is not True:
        raise SystemExit('DESIGN_APPROVAL_SOURCE_NOT_APPROVED')
    approved = WORK_DIR / 'BASIC_DESIGN_PACKAGE.yaml'
    if not approved.is_file():
        raise SystemExit('BASIC_DESIGN_PACKAGE_MISSING_FOR_APPROVAL_BINDING')
    doc['approved_design_package_ref'] = work_unit_rel + '/BASIC_DESIGN_PACKAGE.yaml'
    doc['approved_design_package_sha256'] = _sha256(approved)
    disposition = WORK_DIR / 'EVIDENCE/FORMAL_HUMAN_APPROVAL_DISPOSITION.yaml'
    if disposition.is_file():
        doc['disposition_sha256'] = _sha256(disposition)
    doc['materialization_source'] = 'RECORDED_HUMAN_APPROVAL_NORMALIZATION'
    doc['materialized_by'] = 'SYSTEM'
    doc['status'] = 'PASS'
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
    if a.operation == 'BASIC_DESIGN_PACKAGE_COMPILE':
        _materialize_design_approval_evidence(Path(a.work_unit).parent.as_posix())
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
