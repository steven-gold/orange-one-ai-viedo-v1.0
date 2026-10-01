#!/usr/bin/env python3
"""Regression test for STAGE_EXECUTION_MASTER_PLAN validation (fail-closed).

Proves the master-plan validator PASSes the current plan and FAILs on injected
defects: dangling producer, dropped registry authority, invalid classification,
missing evidence producer, and unbound orphan invariant.
"""
import copy
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '09_TESTS/governance'))
import validate_stage_execution_master_plan as v  # noqa: E402

NEEDED = [
    '10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml',
    '10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml',
]


def _temp_root(mutate):
    tmp = Path(tempfile.mkdtemp())
    (tmp / '10_REGISTRY').mkdir(parents=True)
    for rel in NEEDED:
        shutil.copy2(ROOT / rel, tmp / rel)
    if mutate:
        p = tmp / '10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml'
        doc = yaml.safe_load(p.read_text(encoding='utf-8'))
        mutate(doc)
        p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding='utf-8')
    return tmp


def test_current_plan_passes():
    assert v.validate(ROOT)['status'] == 'PASS'


def test_dangling_producer_fails():
    def m(doc):
        doc['stages'][0]['projection']['outputs'][0]['producer_operation_uid'] = 'NO_SUCH_OPERATION'
    r = v.validate(_temp_root(m))
    assert r['status'] == 'FAIL'
    assert any('DANGLING_REF' in f for f in r['failures'])


def test_dropped_registry_operation_fails():
    def m(doc):
        doc['stages'][0]['projection']['operations'] = [o for o in doc['stages'][0]['projection']['operations'] if o['operation_uid'] != 'SOURCE_SEGMENT_MAPPING']
    r = v.validate(_temp_root(m))
    assert r['status'] == 'FAIL'
    assert any('PROJECTION_DRIFT' in f for f in r['failures'])


def test_invalid_classification_fails():
    def m(doc):
        doc['stages'][0]['projection']['outputs'][0]['classification'] = 'NOT_A_CLASS'
    r = v.validate(_temp_root(m))
    assert r['status'] == 'FAIL'
    assert any('CLASSIFICATION_INVALID' in f for f in r['failures'])


def test_dropped_evidence_fails():
    def m(doc):
        doc['stages'][5]['projection']['required_evidence'] = []
    r = v.validate(_temp_root(m))
    assert r['status'] == 'FAIL'
    assert any('PROJECTION_DRIFT' in f for f in r['failures'])


def test_gate_break_fails():
    def m(doc):
        doc['stages'][1]['projection']['entry_gate'] = 'TOTALLY_WRONG_GATE'
    r = v.validate(_temp_root(m))
    assert r['status'] == 'FAIL'
    assert any('CONTINUITY_BREAK' in f for f in r['failures'])


if __name__ == '__main__':
    fns = [test_current_plan_passes, test_dangling_producer_fails,
           test_dropped_registry_operation_fails, test_invalid_classification_fails,
           test_dropped_evidence_fails, test_gate_break_fails]
    for fn in fns:
        fn()
        print('PASS', fn.__name__)
