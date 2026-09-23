#!/usr/bin/env python3
from pathlib import Path
import configparser
import yaml

ROOT=Path(__file__).resolve().parents[2]
MARKER='GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION'

def load_yaml(rel):
    return yaml.safe_load((ROOT/rel).read_text(encoding='utf-8')) or {}

def test_pytest_collection_isolated_from_standalone_regressions():
    bp=load_yaml('10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml')
    c=bp.get('test_runner_isolation_contract') or {}
    assert c.get('required') is True
    assert c.get('mandatory_regression_runner')=='STANDALONE_SUBPROCESS_JSON'
    assert c.get('generic_pytest_collection_of_standalone_regressions')=='FORBIDDEN'
    assert c.get('collector_triggered_system_exit')=='BLOCK'
    assert c.get('pytest_internal_error')=='BLOCK'
    assert c.get('collection_result_is_acceptance_evidence') is False
    cfg=configparser.ConfigParser()
    cfg.read(ROOT/'pytest.ini',encoding='utf-8')
    assert cfg['pytest']['python_files'].strip()=='test_pytest_collection_contract.py'
    sem=load_yaml('10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml')
    assets=sem.get('mandatory_regression_assets') or []
    assert assets, 'mandatory_regression_assets must not be empty'
    assert len({rec.get('path') for rec in assets})==len(assets), 'mandatory regression paths must be unique'
    for rec in assets:
        p=ROOT/rec['path']
        assert p.exists(), rec['path']
        text=p.read_text(encoding='utf-8')
        assert MARKER in text, rec['path']

if __name__=='__main__':
    test_pytest_collection_isolated_from_standalone_regressions()
    print('PASS')
