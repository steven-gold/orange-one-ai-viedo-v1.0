#!/usr/bin/env python3
from __future__ import annotations
import contextlib, importlib.util, io, json, subprocess, sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
META=ROOT/'governance/source-package/CURRENT_SOURCE_PACKAGE_INTEGRATION.yaml'
TESTS=SOURCE/'09_TESTS/governance'
REGISTRY=ROOT/'governance/specifications/REGISTRY.yaml'
sys.path.insert(0,str(TESTS))

def imp(name):
    p=TESTS/f'{name}.py'
    spec=importlib.util.spec_from_file_location('sp_'+name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError('IMPORT_FAILED:'+name)
    m=importlib.util.module_from_spec(spec)
    out=io.StringIO(); err=io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        spec.loader.exec_module(m)
    return m

def check(name,fn):
    out_buf=io.StringIO(); err_buf=io.StringIO()
    try:
        with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
            out=fn(SOURCE)
        row={'check_id':name,**out}
    except Exception as exc:
        row={'check_id':name,'status':'FAIL','failures':['exception:'+repr(exc)]}
    diagnostics=(out_buf.getvalue()+err_buf.getvalue()).strip()
    if diagnostics:
        row['diagnostics']=diagnostics[-4000:]
    return row

def main():
    registry=yaml.safe_load(REGISTRY.read_text(encoding='utf-8')) or {}
    contract=registry.get('current_validation_contract') or {}
    current_branch=str(registry.get('branch') or '')
    meta=yaml.safe_load(META.read_text(encoding='utf-8')) or {}
    failures=[]

    if not current_branch:
        failures.append('CURRENT_GOVERNANCE_BRANCH_MISSING')
    if contract.get('authority_model')!='WORD_DERIVED_INTERNAL_VALIDATION':
        failures.append('WORD_DERIVED_AUTHORITY_MODEL_DRIFT')
    if contract.get('source_package_integration_mode')!='SINGLE_BRANCH_INTEGRATED':
        failures.append('SOURCE_INTEGRATION_MODE_DRIFT')
    if contract.get('source_package_integrated_branch')!=current_branch:
        failures.append('SOURCE_INTEGRATION_BRANCH_DRIFT')
    if contract.get('unregistered_non_word_execution_prerequisite')!='BLOCK':
        failures.append('UNREGISTERED_NON_WORD_EXECUTION_PREREQUISITE_NOT_BLOCKED')

    if meta.get('artifact_type')!='GOVERNANCE_SOURCE_PACKAGE_INTEGRATION_RECORD':
        failures.append('SOURCE_INTEGRATION_ARTIFACT_TYPE_DRIFT')
    if meta.get('status')!='INTEGRATED_CURRENT_WORKLINE':
        failures.append('SOURCE_INTEGRATION_STATUS_DRIFT')
    if meta.get('current_authority') is not True:
        failures.append('INTEGRATED_SOURCE_CURRENT_AUTHORITY_MISSING')
    integ=meta.get('integration') or {}
    if integ.get('mode')!='SINGLE_BRANCH_INTEGRATED':
        failures.append('SOURCE_INTEGRATION_RECORD_MODE_DRIFT')
    if integ.get('separate_source_branch_required') is not False or integ.get('separate_governance_candidate_branch_required') is not False:
        failures.append('SEPARATE_SOURCE_OR_CANDIDATE_BRANCH_REINTRODUCED')
    if integ.get('branch_fanout_without_explicit_user_authorization')!='FORBIDDEN':
        failures.append('SOURCE_BRANCH_FANOUT_GUARD_MISSING')

    integrity=meta.get('source_integrity') or {}
    for key in ('word_or_registered_source_integrity_required','deterministic_hash_validation_required','exact_head_internal_validation_required'):
        if integrity.get(key) is not True:
            failures.append('SOURCE_INTEGRITY_FLAG_MISSING:'+key)
    if integrity.get('unregistered_non_word_execution_prerequisite')!='BLOCK':
        failures.append('SOURCE_UNREGISTERED_NON_WORD_EXECUTION_PREREQUISITE_NOT_BLOCKED')

    admission=meta.get('admission') or {}
    if admission.get('integrated_source_validation_required') is not True or admission.get('source_integrity_required_for_current') is not True:
        failures.append('SOURCE_CURRENT_ADMISSION_INTEGRITY_DRIFT')
    if admission.get('unregistered_non_word_execution_prerequisite')!='BLOCK':
        failures.append('SOURCE_ADMISSION_UNREGISTERED_NON_WORD_EXECUTION_PREREQUISITE_NOT_BLOCKED')

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

    checksum_proc=subprocess.run(
      [sys.executable,str(ROOT/'governance/source-package/refresh_source_checksums.py'),'--check'],
      cwd=ROOT,text=True,capture_output=True
    )
    if checksum_proc.returncode!=0:
        failures.append('SOURCE_CHECKSUM_LEDGER_STALE')

    bad=[x for x in checks if x.get('status')!='PASS']
    result={
      'artifact_type':'CURRENT_INTEGRATED_GOVERNANCE_SOURCE_VALIDATION',
      'status':'PASS_INTEGRATED_SOURCE' if not failures and not bad else 'FAIL',
      'single_branch_integrated':True,
      'word_or_registered_source_integrity_required':True,
      'unregistered_non_word_execution_prerequisite':'BLOCK',
      'current_authority_credit':1 if not failures and not bad else 0,
      'product_completion_credit':0,
      'checks_total':len(checks),
      'pass_count':len(checks)-len(bad),
      'failures':failures,
      'checks':checks,
      'stdout_contract':'SINGLE_JSON_OBJECT_ONLY',
      'checksum_validator_diagnostics':(checksum_proc.stdout+checksum_proc.stderr).strip()[-4000:],
    }
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    return 0 if result['status']=='PASS_INTEGRATED_SOURCE' else 1

if __name__=='__main__':
    raise SystemExit(main())
