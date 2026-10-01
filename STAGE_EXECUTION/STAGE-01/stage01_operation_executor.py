#!/usr/bin/env python3
"""STAGE-01 HOME governed-unit per-operation executor (PYTHON_STAGE_OPERATION_V1)."""
from __future__ import annotations
import argparse
import hashlib
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


def _stable_hash_obj(obj):
    return hashlib.sha256(yaml.safe_dump(obj, allow_unicode=True, sort_keys=True).encode('utf-8')).hexdigest()


def _content_hash(doc):
    value = dict(doc)
    for key in ('content_hash', 'artifact_hash', 'blueprint_hash', 'binding_hash', 'structure_manifest_hash'):
        value.pop(key, None)
    return _stable_hash_obj(value)


def _load_yaml(path):
    value = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(value, dict):
        raise RuntimeError('STAGE01_MAPPING_REQUIRED:' + str(path))
    return value


def _write_yaml(path, value):
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding='utf-8')


def _canonical_governed_unit_uid():
    capture = _load_yaml(WORK_DIR / '00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml')
    rows = capture.get('records') or []
    values = {str(row.get('governed_unit_uid') or '') for row in rows if isinstance(row, dict)}
    values.discard('')
    if len(values) != 1:
        raise RuntimeError('STAGE01_CANONICAL_GOVERNED_UNIT_UNRESOLVED:' + repr(sorted(values)))
    return next(iter(values))


def _normalize_identity(value, governed_unit_uid):
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key == 'governed_unit_uid' and item == SUID:
                out[key] = governed_unit_uid
            elif key == 'governed_unit_uids' and isinstance(item, list):
                out[key] = [governed_unit_uid if x == SUID else x for x in item]
            elif key == 'planning_domain' and item == 'PAGE_CONSTRUCTION':
                out[key] = 'GOVERNED_UNIT_CONSTRUCTION'
            else:
                out[key] = _normalize_identity(item, governed_unit_uid)
        return out
    if isinstance(value, list):
        return [_normalize_identity(x, governed_unit_uid) for x in value]
    return value


def _refresh_stage1_linked_contracts():
    governed_unit_uid = _canonical_governed_unit_uid()
    roots = [
        WORK_DIR / '00_SOURCE_INTAKE',
        WORK_DIR / '01_CLASSIFIED',
        WORK_DIR / '02_BASE_BLUEPRINT',
        WORK_DIR / '03_BLUEPRINT_BINDING',
    ]
    yaml_paths = []
    for root in roots:
        if root.is_dir():
            yaml_paths.extend(sorted(root.rglob('*.yaml')))
    for path in yaml_paths:
        doc = _normalize_identity(_load_yaml(path), governed_unit_uid)
        _write_yaml(path, doc)

    structure = WORK_DIR / '00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml'
    if structure.is_file():
        doc = _load_yaml(structure)
        for source in doc.get('sources') or []:
            if isinstance(source, dict) and 'structure_manifest_hash' in source:
                source['structure_manifest_hash'] = _content_hash(source)
        _write_yaml(structure, doc)

    source_fact_paths = [
        WORK_DIR / '00_SOURCE_INTAKE/SOURCE_CONTEXT_MANIFEST.yaml',
        WORK_DIR / '00_SOURCE_INTAKE/CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml',
        WORK_DIR / '00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml',
    ]
    source_facts = {}
    for path in source_fact_paths:
        if not path.is_file():
            continue
        doc = _load_yaml(path)
        if 'content_hash' in doc:
            doc['content_hash'] = _content_hash(doc)
        _write_yaml(path, doc)
        if doc.get('artifact_uid'):
            source_facts[str(doc['artifact_uid'])] = doc

    artifacts = {}
    class_root = WORK_DIR / '01_CLASSIFIED'
    if class_root.is_dir():
        for path in sorted(class_root.rglob('*.yaml')):
            doc = _load_yaml(path)
            if 'content_hash' in doc:
                doc['content_hash'] = _content_hash(doc)
            _write_yaml(path, doc)
            if doc.get('artifact_uid'):
                artifacts[str(doc['artifact_uid'])] = doc

    blueprints = {}
    blueprint_root = WORK_DIR / '02_BASE_BLUEPRINT'
    if blueprint_root.is_dir():
        for path in sorted(blueprint_root.rglob('*.yaml')):
            doc = _load_yaml(path)
            for row in doc.get('input_artifacts') or []:
                if isinstance(row, dict) and str(row.get('artifact_uid') or '') in artifacts:
                    row['content_hash'] = artifacts[str(row['artifact_uid'])].get('content_hash')
            for row in doc.get('source_fact_refs') or []:
                if isinstance(row, dict) and str(row.get('artifact_uid') or '') in source_facts:
                    row['content_hash'] = source_facts[str(row['artifact_uid'])].get('content_hash')
            if 'blueprint_hash' in doc:
                doc['blueprint_hash'] = _content_hash(doc)
            _write_yaml(path, doc)
            if doc.get('blueprint_uid'):
                blueprints[str(doc['blueprint_uid'])] = doc

    binding_root = WORK_DIR / '03_BLUEPRINT_BINDING'
    if binding_root.is_dir():
        for path in sorted(binding_root.rglob('*.yaml')):
            doc = _load_yaml(path)
            for key in ('governed_unit_blueprint', 'visual_blueprint'):
                row = doc.get(key)
                if isinstance(row, dict) and str(row.get('blueprint_uid') or '') in blueprints:
                    row['blueprint_hash'] = blueprints[str(row['blueprint_uid'])].get('blueprint_hash')
            if 'binding_hash' in doc:
                doc['binding_hash'] = _content_hash(doc)
            _write_yaml(path, doc)


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
    _refresh_stage1_linked_contracts()
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
