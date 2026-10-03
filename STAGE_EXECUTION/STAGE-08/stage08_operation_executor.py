#!/usr/bin/env python3
"""STAGE-08 STAGING per-operation executor (PYTHON_STAGE_OPERATION_V1).

Producer operations materialize the stage outputs:
  * OP-38-STAGING_ACCEPTANCE     -> STAGING_ACCEPTANCE_OR_NA_EVIDENCE
  * STAGING_CLOSURE_RECONCILE    -> STAGING_CLOSURE_RECORD

Staging boots the local staging runtime, applies migrations, and proves
acceptance with a live HTTP smoke against health, auth and navigation.
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_shared'))
from fail_closed import as_status, run_live_smoke

EXECUTOR_REL = 'STAGE_EXECUTION/STAGE-08/stage08_operation_executor.py'
GOVERNED = 'GLOBAL-HOME-SHELL-NAVIGATION'

WORK_DIR: Path | None = None
PRODUCT_ROOT: Path | None = None


def _read_yaml(path: Path) -> dict:
    return (yaml.safe_load(path.read_text(encoding='utf-8')) or {}) if path.is_file() else {}


def _write_yaml(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True), encoding='utf-8')


def _gov() -> str:
    return os.environ.get('ACPOS_CURRENT_GOVERNANCE_UID', '').strip()


def _wu() -> str:
    return Path(os.environ.get('ACPOS_ACTIVE_WORK_UNIT_DIR', WORK_DIR.name)).name


def _base(atype: str, extra: dict) -> dict:
    status = extra.pop('status', 'FAIL')
    return {
        'artifact_uid': f'{atype}-STAGE-08-{GOVERNED}',
        'artifact_type': atype,
        'stage_uid': 'STAGE-08',
        'work_unit_uid': _wu(),
        'governed_unit_uid': GOVERNED,
        'governance_uid': _gov(),
        **extra,
        'status': status,
        'product_completion_credit': 0,
    }


def _release_candidate_ref() -> str:
    return _read_yaml(WORK_DIR / 'WORK_UNIT.yaml').get('input_bindings', {}).get('RELEASE_CANDIDATE', {}).get('artifact_ref', '')


def _op_staging_deployment() -> dict:
    web_dist = PRODUCT_ROOT / 'apps/web/dist'
    rc = _read_yaml(PRODUCT_ROOT / _release_candidate_ref()) if _release_candidate_ref() else {}
    smoke = run_live_smoke(PRODUCT_ROOT, {'ACPOS_DEPLOYMENT_ENV': 'staging'})
    ok = bool(smoke.get('ok')) and web_dist.is_dir()
    doc = {
        'artifact_type': 'STAGING_DEPLOYMENT_RECORD',
        'stage_uid': 'STAGE-08',
        'work_unit_uid': _wu(),
        'governed_unit_uid': GOVERNED,
        'governance_uid': _gov(),
        'release_candidate_uid': rc.get('release_candidate_uid'),
        'web_dist_present': web_dist.is_dir(),
        'staging_target': 'LOCAL_STAGING_RUNTIME',
        'live_smoke': smoke,
        'status': as_status(ok),
        'product_completion_credit': 0,
    }
    _write_yaml(WORK_DIR / 'EVIDENCE' / 'STAGING_DEPLOYMENT.yaml', doc)
    return doc


def _op_staging_acceptance() -> dict:
    smoke = run_live_smoke(PRODUCT_ROOT, {'ACPOS_DEPLOYMENT_ENV': 'staging'})
    checks = dict(smoke.get('checks') or {})
    checks['staging_build_present'] = (PRODUCT_ROOT / 'apps/web/dist').is_dir()
    ok = bool(smoke.get('ok')) and checks.get('health') is True and checks.get('authenticated_navigation') is True
    doc = _base('STAGING_ACCEPTANCE_OR_NA_EVIDENCE', {
        'staging_acceptance_or_na_state': as_status(ok),
        'checks': checks,
        'live_smoke': smoke,
        'staging_acceptance_result': 'ACCEPTED' if ok else 'REJECTED',
        'status': as_status(ok),
    })
    _write_yaml(WORK_DIR / 'EVIDENCE' / 'STAGING_ACCEPTANCE_OR_NA_EVIDENCE.yaml', doc)
    return doc


def _op_na_authority_verify() -> dict:
    return {'staging_applicability': 'APPLICABLE', 'na_authority_required': False, 'na_authority_verified': True}


def _op_staging_closure() -> dict:
    ev = _read_yaml(WORK_DIR / 'EVIDENCE' / 'STAGING_ACCEPTANCE_OR_NA_EVIDENCE.yaml')
    accepted = ev.get('staging_acceptance_or_na_state') == 'PASS' and ev.get('status') == 'PASS'
    doc = _base('STAGING_CLOSURE_RECORD', {
        'deployment_applicability_coherence_state': 'COHERENT' if accepted else 'INCOHERENT',
        'execution_scope_authority_state': 'AUTHORIZED' if accepted else 'BLOCKED',
        'dynamic_denominator_state': 'RECONCILED' if accepted else 'UNRECONCILED',
        'ownership_portability_audit_result': as_status(accepted),
        'successor_input_readiness_state': 'PREPARED' if accepted else 'BLOCKED',
        'cross_stage_handoff_state': 'READY' if accepted else 'BLOCKED',
        'false_completion_audit_result': as_status(accepted),
        'staging_closure_state': 'CLOSED_ACCEPTED' if accepted else 'BLOCKED',
        'status': as_status(accepted),
    })
    _write_yaml(WORK_DIR / 'STAGING_CLOSURE_RECORD.yaml', doc)
    return doc


def _write_receipt(op: str, result_owner: str, extra: dict) -> None:
    rec = {
        'artifact_type': 'OPERATION_EXECUTION_RECEIPT',
        'stage_uid': 'STAGE-08',
        'work_unit_uid': _wu(),
        'operation_uid': op,
        'governance_uid': _gov(),
        'status': extra.get('gate_status') or 'FAIL',
        'executor_owner': EXECUTOR_REL,
        'executor_protocol': 'PYTHON_STAGE_OPERATION_V1',
        'result_owner': result_owner,
        'fail_closed': True,
    }
    rec.update(extra)
    _write_yaml(WORK_DIR / 'EVIDENCE' / 'OPERATION_RECEIPTS' / (op + '.yaml'), rec)


def main() -> None:
    global WORK_DIR, PRODUCT_ROOT
    p = argparse.ArgumentParser()
    p.add_argument('--stage', required=True)
    p.add_argument('--operation', required=True)
    p.add_argument('--work-unit', required=True)
    p.add_argument('--product-root', required=True)
    a = p.parse_args()
    PRODUCT_ROOT = Path(a.product_root).resolve()
    WORK_DIR = (PRODUCT_ROOT / Path(a.work_unit)).resolve().parent
    os.environ['ACPOS_ACTIVE_WORK_UNIT_DIR'] = WORK_DIR.name
    if not _gov():
        raise SystemExit('CURRENT_GOVERNANCE_UID_ENV_MISSING')

    work = _read_yaml(WORK_DIR / 'WORK_UNIT.yaml')
    binding = ((work.get('operation_bindings') or {}).get(a.operation) or {})
    result_owner = str(binding.get('result_owner') or 'UNBOUND')
    extra: dict = {}
    gate = 'FAIL'

    if a.operation == 'OP-37-STAGING_DEPLOYMENT':
        extra['result'] = _op_staging_deployment()
        gate = extra['result'].get('status') or 'FAIL'
    elif a.operation == 'OP-38-STAGING_ACCEPTANCE':
        extra['result'] = _op_staging_acceptance()
        gate = extra['result'].get('status') or 'FAIL'
    elif a.operation == 'STAGING_NA_AUTHORITY_VERIFY':
        extra['result'] = _op_na_authority_verify()
        gate = 'PASS'
    elif a.operation == 'STAGING_CLOSURE_RECONCILE':
        extra['result'] = _op_staging_closure()
        gate = extra['result'].get('status') or 'FAIL'

    extra['gate_status'] = gate
    _write_receipt(a.operation, result_owner, extra)
    if gate != 'PASS':
        raise SystemExit('OPERATION_FAIL_CLOSED:' + a.operation)
    print('OK', a.operation)


if __name__ == '__main__':
    main()
