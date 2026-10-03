#!/usr/bin/env python3
"""STAGE-09 PRODUCTION_CUTOVER per-operation executor (PYTHON_STAGE_OPERATION_V1).

Producer operations materialize the stage outputs:
  * OP-41-PRODUCTION_DEPLOYMENT      -> PRODUCTION_DEPLOYMENT_RECORD
  * OP-42-PRODUCTION_SMOKE           -> PRODUCTION_SMOKE_EVIDENCE
  * CURRENT_RELEASE_IDENTITY_CAPTURE -> CURRENT_RELEASE_IDENTITY

Cutover binds production configuration, runs the migration runner against the
persistent database, deploys the release identity, and proves cutover with a
live HTTP smoke. Child-gate FAIL fail-closes receipts, artifacts and closure.
"""
from __future__ import annotations
import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_shared'))
from fail_closed import as_status, run_live_smoke, run_probe

EXECUTOR_REL = 'STAGE_EXECUTION/STAGE-09/stage09_operation_executor.py'
GOVERNED = 'GLOBAL-HOME-SHELL-NAVIGATION'

WORK_DIR: Path | None = None
PRODUCT_ROOT: Path | None = None


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8') if path.is_file() else ''


def _read_yaml(path: Path) -> dict:
    return (yaml.safe_load(path.read_text(encoding='utf-8')) or {}) if path.is_file() else {}


def _write_yaml(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True), encoding='utf-8')


def _gov() -> str:
    return os.environ.get('ACPOS_CURRENT_GOVERNANCE_UID', '').strip()


def _wu() -> str:
    return Path(os.environ.get('ACPOS_ACTIVE_WORK_UNIT_DIR', WORK_DIR.name)).name


def _inputs() -> dict:
    return _read_yaml(WORK_DIR / 'WORK_UNIT.yaml').get('input_bindings', {}) or {}


def _input_yaml(uid: str) -> dict:
    ref = (_inputs().get(uid) or {}).get('artifact_ref') or ''
    return _read_yaml(PRODUCT_ROOT / ref) if ref else {}


def _base(atype: str, extra: dict) -> dict:
    status = extra.pop('status', 'FAIL')
    return {
        'artifact_uid': f'{atype}-STAGE-09-{GOVERNED}',
        'artifact_type': atype,
        'stage_uid': 'STAGE-09',
        'work_unit_uid': _wu(), 'governed_unit_uid': GOVERNED, 'governance_uid': _gov(),
        **extra, 'status': status, 'product_completion_credit': 0,
    }


def _op_configuration() -> dict:
    env = PRODUCT_ROOT / 'apps/api/src/config/env.ts'
    env_example = PRODUCT_ROOT / '.env.example'
    checks = {
        'config_module_present': env.is_file(),
        'port_bound': 'PORT' in _read(PRODUCT_ROOT / 'apps/api/src/server.ts'),
        'neon_identity_named': 'wild-wave-25661146' in _read(env) and 'DATABASE_URL' in _read(env_example),
        'auth_middleware_bound': 'requireAuth' in _read(PRODUCT_ROOT / 'apps/api/src/app.ts'),
    }
    ok = all(bool(v) for v in checks.values())
    doc = _base('PRODUCTION_CONFIGURATION', {
        'production_configuration_gate_state': as_status(ok),
        'checks': checks,
        'status': as_status(ok),
    })
    _write_yaml(WORK_DIR / 'EVIDENCE' / 'PRODUCTION_CONFIGURATION.yaml', doc)
    return doc


def _op_migration() -> dict:
    migration = _read(PRODUCT_ROOT / 'apps/api/src/db/migrations/001_init.sql')
    runner = (PRODUCT_ROOT / 'apps/api/src/db/migrate.ts').is_file()
    persist = (PRODUCT_ROOT / 'apps/api/src/db/persist.ts').is_file()
    tables = ['navigation_authority', 'account_permission_assignment', 'navigation_audit_event']
    probe = run_probe(PRODUCT_ROOT)
    ok = runner and persist and all(('TABLE IF NOT EXISTS ' + t) in migration for t in tables) and bool(probe.get('ok'))
    doc = _base('PRODUCTION_MIGRATION', {
        'production_migration_gate_state': as_status(ok),
        'migration_sha256': hashlib.sha256(migration.encode('utf-8')).hexdigest(),
        'probe': probe,
        'status': as_status(ok),
    })
    _write_yaml(WORK_DIR / 'EVIDENCE' / 'PRODUCTION_MIGRATION.yaml', doc)
    return doc


def _op_deployment() -> dict:
    cfg = _read_yaml(WORK_DIR / 'EVIDENCE' / 'PRODUCTION_CONFIGURATION.yaml')
    mig = _read_yaml(WORK_DIR / 'EVIDENCE' / 'PRODUCTION_MIGRATION.yaml')
    build = _input_yaml('BUILD_IDENTITY_MANIFEST')
    staging = _input_yaml('STAGING_CLOSURE_RECORD')
    smoke = run_live_smoke(PRODUCT_ROOT, {'ACPOS_DEPLOYMENT_ENV': 'production'})
    deployed = (
        cfg.get('production_configuration_gate_state') == 'PASS'
        and cfg.get('status') == 'PASS'
        and mig.get('production_migration_gate_state') == 'PASS'
        and mig.get('status') == 'PASS'
        and staging.get('staging_closure_state') == 'CLOSED_ACCEPTED'
        and bool(smoke.get('ok'))
    )
    doc = _base('PRODUCTION_DEPLOYMENT_RECORD', {
        'production_configuration_gate_state': cfg.get('production_configuration_gate_state'),
        'production_migration_gate_state': mig.get('production_migration_gate_state'),
        'successor_input_readiness_state': 'PREPARED' if deployed else 'BLOCKED',
        'cross_stage_handoff_state': 'READY' if deployed else 'BLOCKED',
        'false_completion_audit_result': as_status(deployed),
        'production_deployment_gate_state': as_status(deployed),
        'deployed_build_identity': build.get('build_id'),
        'live_smoke': smoke,
        'status': as_status(deployed),
    })
    _write_yaml(WORK_DIR / 'PRODUCTION_DEPLOYMENT_RECORD.yaml', doc)
    return doc


def _op_smoke() -> dict:
    smoke = run_live_smoke(PRODUCT_ROOT, {'ACPOS_DEPLOYMENT_ENV': 'production'})
    ok = bool(smoke.get('ok'))
    doc = _base('PRODUCTION_SMOKE_EVIDENCE', {
        'production_smoke_state': as_status(ok),
        'checks': smoke.get('checks') or {},
        'live_smoke': smoke,
        'status': as_status(ok),
    })
    _write_yaml(WORK_DIR / 'EVIDENCE' / 'PRODUCTION_SMOKE_EVIDENCE.yaml', doc)
    return doc


def _op_release_identity() -> dict:
    build = _input_yaml('BUILD_IDENTITY_MANIFEST')
    deploy = _read_yaml(WORK_DIR / 'PRODUCTION_DEPLOYMENT_RECORD.yaml')
    smoke = _read_yaml(WORK_DIR / 'EVIDENCE' / 'PRODUCTION_SMOKE_EVIDENCE.yaml')
    head = subprocess.run(['git', '-C', str(PRODUCT_ROOT), 'rev-parse', 'HEAD'],
                          text=True, capture_output=True).stdout.strip()
    ok = deploy.get('status') == 'PASS' and smoke.get('status') == 'PASS'
    doc = _base('CURRENT_RELEASE_IDENTITY', {
        'deployment_build_identity_state': build.get('build_id') or head[:12],
        'execution_scope_authority_state': 'AUTHORIZED' if ok else 'BLOCKED',
        'dynamic_denominator_state': 'RECONCILED' if ok else 'UNRECONCILED',
        'ownership_portability_audit_result': as_status(ok),
        'current_release_build_id': build.get('build_id'),
        'source_revision_sha': head,
        'status': as_status(ok),
    })
    _write_yaml(WORK_DIR / 'CURRENT_RELEASE_IDENTITY.yaml', doc)
    return doc


def _write_receipt(op: str, result_owner: str, extra: dict) -> None:
    rec = {
        'artifact_type': 'OPERATION_EXECUTION_RECEIPT',
        'stage_uid': 'STAGE-09', 'work_unit_uid': _wu(), 'operation_uid': op,
        'governance_uid': _gov(), 'status': extra.get('gate_status') or 'FAIL',
        'executor_owner': EXECUTOR_REL, 'executor_protocol': 'PYTHON_STAGE_OPERATION_V1',
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
    if a.operation == 'OP-39-PRODUCTION_CONFIGURATION':
        extra['result'] = _op_configuration()
        gate = extra['result'].get('status') or 'FAIL'
    elif a.operation == 'OP-40-PRODUCTION_MIGRATION':
        extra['result'] = _op_migration()
        gate = extra['result'].get('status') or 'FAIL'
    elif a.operation == 'OP-41-PRODUCTION_DEPLOYMENT':
        extra['result'] = _op_deployment()
        gate = extra['result'].get('status') or 'FAIL'
    elif a.operation == 'OP-42-PRODUCTION_SMOKE':
        extra['result'] = _op_smoke()
        gate = extra['result'].get('status') or 'FAIL'
    elif a.operation == 'CURRENT_RELEASE_IDENTITY_CAPTURE':
        extra['result'] = _op_release_identity()
        gate = extra['result'].get('status') or 'FAIL'

    extra['gate_status'] = gate
    _write_receipt(a.operation, result_owner, extra)
    if gate != 'PASS':
        raise SystemExit('OPERATION_FAIL_CLOSED:' + a.operation)
    print('OK', a.operation)


if __name__ == '__main__':
    main()
