#!/usr/bin/env python3
from __future__ import annotations
import contextlib, importlib.util, io, json, subprocess, sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
META=ROOT/'governance/source-successor/SOURCE_PACKAGE_CANDIDATE.yaml'
TESTS=SOURCE/'09_TESTS/governance'
REGISTRY=ROOT/'governance/specifications/REGISTRY.yaml'
sys.path.insert(0,str(TESTS))
def imp(name):
    p=TESTS/f'{name}.py'; spec=importlib.util.spec_from_file_location('sp_'+name,p)
    if spec is None or spec.loader is None: raise RuntimeError('IMPORT_FAILED:'+name)
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

def validate_toolchain_bindings():
    registry=yaml.safe_load(REGISTRY.read_text(encoding='utf-8')) or {}
    contract=registry.get('candidate_validation_contract') or {}
    failures=[]
    if contract.get('source_package_validation_toolchain_binding_mode')!='GIT_BLOB_SHA1_EXACT_SET_V1':
        failures.append('SOURCE_VALIDATION_TOOLCHAIN_BINDING_MODE_DRIFT')
    if contract.get('source_package_validation_toolchain_missing_extra_or_blob_drift')!='BLOCK':
        failures.append('SOURCE_VALIDATION_TOOLCHAIN_FAIL_CLOSED_POLICY_DRIFT')
    expected=contract.get('source_package_validation_toolchain_blob_bindings') or {}
    if not isinstance(expected,dict) or not expected:
        return {'status':'BLOCKED','expected_count':0,'observed_count':0,'missing':[],'extra':[],'blob_drift':[],'failures':failures+['SOURCE_VALIDATION_TOOLCHAIN_BINDINGS_MISSING']}
    expected={str(k):str(v) for k,v in expected.items()}
    exact_paths=set(map(str,contract.get('source_package_validation_toolchain_exact_paths') or []))
    prefixes=tuple(map(str,contract.get('source_package_validation_toolchain_subtree_prefixes') or []))
    expected_count=int(contract.get('source_package_validation_toolchain_exact_file_count') or 0)
    try:
        raw=subprocess.check_output(['git','ls-tree','-r','HEAD'],cwd=ROOT,text=True)
    except Exception as exc:
        return {'status':'BLOCKED','expected_count':expected_count,'observed_count':0,'missing':[],'extra':[],'blob_drift':[],'failures':failures+['SOURCE_VALIDATION_TOOLCHAIN_GIT_TREE_UNAVAILABLE:'+type(exc).__name__]}
    all_blobs={}
    for line in raw.splitlines():
        if '\t' not in line:
            continue
        meta,path=line.split('\t',1)
        parts=meta.split()
        if len(parts)==3 and parts[1]=='blob':
            all_blobs[path]=parts[2]
    observed={path:sha for path,sha in all_blobs.items() if path in exact_paths or any(path.startswith(prefix) for prefix in prefixes)}
    if expected_count!=len(expected):
        failures.append(f'SOURCE_VALIDATION_TOOLCHAIN_REGISTERED_COUNT_DRIFT:{len(expected)}!={expected_count}')
    if len(observed)!=expected_count:
        failures.append(f'SOURCE_VALIDATION_TOOLCHAIN_OBSERVED_COUNT_DRIFT:{len(observed)}!={expected_count}')
    missing=sorted(set(expected)-set(observed))
    extra=sorted(set(observed)-set(expected))
    drift=sorted(path for path in set(expected)&set(observed) if expected[path]!=observed[path])
    if missing:
        failures.append('SOURCE_VALIDATION_TOOLCHAIN_MISSING:'+','.join(missing))
    if extra:
        failures.append('SOURCE_VALIDATION_TOOLCHAIN_EXTRA:'+','.join(extra))
    if drift:
        failures.append('SOURCE_VALIDATION_TOOLCHAIN_BLOB_DRIFT:'+','.join(drift))
    return {
      'status':'PASS' if not failures else 'BLOCKED',
      'expected_count':expected_count,
      'observed_count':len(observed),
      'missing':missing,
      'extra':extra,
      'blob_drift':drift,
      'failures':failures,
    }
def main():
    registry=yaml.safe_load(REGISTRY.read_text(encoding='utf-8')) or {}
    current_branch=str(registry.get('branch') or '')
    meta=yaml.safe_load(META.read_text(encoding='utf-8')) or {}
    failures=[]
    if not current_branch: failures.append('CURRENT_GOVERNANCE_BRANCH_MISSING')
    if meta.get('status')!='INTEGRATED_CURRENT_WORKLINE': failures.append('SOURCE_INTEGRATION_STATUS_DRIFT')
    if meta.get('current_authority') is not True: failures.append('INTEGRATED_SOURCE_CURRENT_AUTHORITY_MISSING')
    if str(meta.get('branch') or '')!=current_branch: failures.append('INTEGRATED_SOURCE_BRANCH_DRIFT')
    if ((meta.get('integration') or {}).get('mode'))!='SINGLE_BRANCH_INTEGRATED': failures.append('SOURCE_INTEGRATION_MODE_DRIFT')
    if ((meta.get('external_trust') or {}).get('status'))!='RETIRED_BY_SINGLE_BRANCH_CONSOLIDATION': failures.append('SOURCE_EXTERNAL_TRUST_RETIREMENT_DRIFT')
    if ((meta.get('external_trust') or {}).get('candidate_self_sign'))!='FORBIDDEN': failures.append('SOURCE_CANDIDATE_SELF_SIGN_NOT_FORBIDDEN')
    toolchain=validate_toolchain_bindings()
    checks=[
      {'check_id':'validation_toolchain_exact_bindings',**toolchain},
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
      [sys.executable,str(ROOT/'governance/source-successor/refresh_source_checksums.py'),'--check'],
      cwd=ROOT,text=True,capture_output=True
    )
    if checksum_proc.returncode!=0:
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
      'toolchain_binding_validation':toolchain,
      'stdout_contract':'SINGLE_JSON_OBJECT_ONLY',
      'checksum_validator_diagnostics':(checksum_proc.stdout+checksum_proc.stderr).strip()[-4000:],
    }
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    return 0 if result['status']=='PASS_INTEGRATED_SOURCE' else 1
if __name__=='__main__': raise SystemExit(main())
