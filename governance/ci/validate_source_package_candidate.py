#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, subprocess, sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
META=ROOT/'governance/source-successor/SOURCE_PACKAGE_CANDIDATE.yaml'
TESTS=SOURCE/'09_TESTS/governance'
sys.path.insert(0,str(TESTS))
def imp(name):
    p=TESTS/f'{name}.py'; spec=importlib.util.spec_from_file_location('sp_'+name,p)
    if spec is None or spec.loader is None: raise RuntimeError('IMPORT_FAILED:'+name)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def check(name,fn):
    try:
        out=fn(SOURCE); return {'check_id':name,**out}
    except Exception as exc: return {'check_id':name,'status':'FAIL','failures':['exception:'+repr(exc)]}
def main():
    meta=yaml.safe_load(META.read_text(encoding='utf-8')) or {}
    failures=[]
    if meta.get('status')!='INTEGRATED_CURRENT_WORKLINE': failures.append('SOURCE_INTEGRATION_STATUS_DRIFT')
    if meta.get('current_authority') is not True: failures.append('INTEGRATED_SOURCE_CURRENT_AUTHORITY_MISSING')
    if meta.get('branch')!='rebuild-v2.1.1': failures.append('INTEGRATED_SOURCE_BRANCH_DRIFT')
    if ((meta.get('integration') or {}).get('mode'))!='SINGLE_BRANCH_INTEGRATED': failures.append('SOURCE_INTEGRATION_MODE_DRIFT')
    if ((meta.get('external_trust') or {}).get('status'))!='RETIRED_BY_SINGLE_BRANCH_CONSOLIDATION': failures.append('SOURCE_EXTERNAL_TRUST_RETIREMENT_DRIFT')
    if ((meta.get('external_trust') or {}).get('candidate_self_sign'))!='FORBIDDEN': failures.append('SOURCE_CANDIDATE_SELF_SIGN_NOT_FORBIDDEN')
    checks=[
      check('section_registry',imp('validate_section_registry').validate),
      check('execution_governance_load',imp('validate_execution_governance_load').validate_definition),
      check('lifecycle_stage_contract',imp('governance_lifecycle_stage_contract_guard').validate),
      check('management_contract',imp('governance_management_contract_guard').validate),
      check('reference_semantics',imp('validate_reference_semantics').validate),
      check('stage_execution_invariants',imp('validate_stage_execution_invariants').validate),
      check('test_feedback_spec_evolution',imp('validate_test_feedback_spec_evolution').validate),
      check('product_neutral_entity_lifecycle',imp('validate_product_neutral_entity_lifecycle').validate),
    ]
    gov=imp('validate_governance')
    checks.extend([
      check('acceptance_blueprint_compiled_baseline',gov.baseline_guard),
      check('root_manifest',gov.root_manifest_guard),
      check('mandatory_regression_and_package_integrity',gov.mandatory_regression_guard),
    ])
    if subprocess.run([sys.executable,str(ROOT/'governance/source-successor/refresh_source_checksums.py'),'--check'],cwd=ROOT).returncode!=0:
        failures.append('SOURCE_CHECKSUM_LEDGER_STALE')
    bad=[x for x in checks if x.get('status')!='PASS']
    result={
      'artifact_type':'GOVERNANCE_SOURCE_PACKAGE_CANDIDATE_VALIDATION',
      'status':'PASS_INTEGRATED_SOURCE' if not failures and not bad else 'FAIL',
      'single_branch_integrated':True,
      'external_trust_status':'RETIRED_BY_SINGLE_BRANCH_CONSOLIDATION',
      'external_trust_credit':0,
      'current_authority_credit':1,
      'promotion_credit':0,
      'checks_total':len(checks),
      'pass_count':len(checks)-len(bad),
      'failures':failures,
      'checks':checks,
    }
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    return 0 if result['status']=='PASS_INTEGRATED_SOURCE' else 1
if __name__=='__main__': raise SystemExit(main())
