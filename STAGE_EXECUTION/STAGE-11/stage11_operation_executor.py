#!/usr/bin/env python3
"""STAGE-11 CLOSURE_OPERATIONS per-operation executor (PYTHON_STAGE_OPERATION_V1).

Producer operations materialize the terminal stage outputs:
  * OP-54-FINAL_PRODUCTION_ACCEPTANCE   -> FINAL_PRODUCTION_ACCEPTANCE_RESULT
  * GOVERNED_UNIT_CLOSURE               -> GOVERNED_UNIT_CLOSED
  * NEXT_GOVERNED_UNIT_ELIGIBILITY_EVALUATE -> NEXT_GOVERNED_UNIT_ELIGIBILITY

Monitoring, backup and rollback are proven by real runtime scripts and live
HTTP smoke. Child-gate FAIL fail-closes receipts, artifacts and closure.
"""
from __future__ import annotations
import argparse
import os
import subprocess
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_shared'))
from fail_closed import as_status, run_backup, run_live_smoke, run_monitor, run_probe, run_rollback

EXECUTOR_REL = 'STAGE_EXECUTION/STAGE-11/stage11_operation_executor.py'
GOVERNED = 'GLOBAL-HOME-SHELL-NAVIGATION'

WORK_DIR: Path | None = None
PRODUCT_ROOT: Path | None = None


def _read(rel: str) -> str:
    p = PRODUCT_ROOT / rel
    return p.read_text(encoding='utf-8') if p.is_file() else ''


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
        'artifact_uid': f'{atype}-STAGE-11-{GOVERNED}', 'artifact_type': atype,
        'stage_uid': 'STAGE-11', 'work_unit_uid': _wu(), 'governed_unit_uid': GOVERNED,
        'governance_uid': _gov(), **extra, 'status': status, 'product_completion_credit': 0,
    }


def _ops_doc_path() -> Path:
    return WORK_DIR / 'EVIDENCE' / 'OPERATIONS_EVIDENCE.yaml'


def _merge_ops(**fields) -> dict:
    current = _read_yaml(_ops_doc_path())
    checks = dict(current.get('operations_checks') or {})
    incoming = fields.pop('operations_checks', {}) or {}
    checks.update(incoming)
    monitoring = fields.get('monitoring_state', current.get('monitoring_state') or 'FAIL')
    backup = fields.get('backup_state', current.get('backup_state') or 'FAIL')
    rollback = fields.get('rollback_state', current.get('rollback_state') or 'FAIL')
    proven = [state for state in (monitoring, backup, rollback) if state in ('PASS', 'FAIL')]
    ok = bool(proven) and all(state == 'PASS' for state in (monitoring, backup, rollback))
    doc = _base('OPERATIONS_EVIDENCE', {
        'monitoring_state': monitoring,
        'backup_state': backup,
        'rollback_state': rollback,
        'operations_checks': checks,
        'status': as_status(ok),
    })
    _write_yaml(_ops_doc_path(), doc)
    return doc


def _snapshot_path() -> str:
    path = WORK_DIR / 'EVIDENCE' / 'ops' / 'runtime-snapshot.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def _op_monitoring() -> dict:
    worker = PRODUCT_ROOT / 'apps/api/src/workers/auditWorker.ts'
    runner = PRODUCT_ROOT / 'apps/api/src/ops/runMonitor.ts'
    monitor = run_monitor(PRODUCT_ROOT)
    smoke = run_live_smoke(PRODUCT_ROOT, {'ACPOS_DEPLOYMENT_ENV': 'production'})
    ok = (
        worker.is_file()
        and runner.is_file()
        and bool(monitor.get('ok'))
        and int(monitor.get('drained') or 0) >= 0
        and bool(smoke.get('ok'))
        and bool((smoke.get('checks') or {}).get('health'))
        and bool((smoke.get('checks') or {}).get('ready'))
    )
    return _merge_ops(
        monitoring_state=as_status(ok),
        backup_state='FAIL',
        rollback_state='FAIL',
        operations_checks={
            'monitoring_audit_worker_present': worker.is_file(),
            'monitor_runner_present': runner.is_file(),
            'monitor_ok': bool(monitor.get('ok')),
            'monitor_drained': int(monitor.get('drained') or 0),
            'live_health': bool((smoke.get('checks') or {}).get('health')),
            'live_ready': bool((smoke.get('checks') or {}).get('ready')),
        },
    )


def _op_backup() -> dict:
    backup_mod = PRODUCT_ROOT / 'apps/api/src/ops/backup.ts'
    runner = PRODUCT_ROOT / 'apps/api/src/ops/runBackup.ts'
    snapshot = _snapshot_path()
    result = run_backup(PRODUCT_ROOT, snapshot)
    ok = (
        backup_mod.is_file()
        and runner.is_file()
        and Path(snapshot).is_file()
        and bool(result.get('ok'))
        and int(result.get('itemCount') or 0) >= 18
        and int(result.get('assignmentCount') or 0) >= 1
    )
    return _merge_ops(
        backup_state=as_status(ok),
        operations_checks={
            'backup_module_present': backup_mod.is_file(),
            'backup_runner_present': runner.is_file(),
            'backup_ok': bool(result.get('ok')),
            'backup_item_count': int(result.get('itemCount') or 0),
            'backup_assignment_count': int(result.get('assignmentCount') or 0),
            'backup_snapshot_present': Path(snapshot).is_file(),
        },
    )


def _op_rollback() -> dict:
    rollback_mod = PRODUCT_ROOT / 'apps/api/src/ops/rollback.ts'
    runner = PRODUCT_ROOT / 'apps/api/src/ops/runRollback.ts'
    snapshot = _snapshot_path()
    if not Path(snapshot).is_file():
        run_backup(PRODUCT_ROOT, snapshot)
    result = run_rollback(PRODUCT_ROOT, snapshot)
    probe = run_probe(PRODUCT_ROOT)
    ok = (
        rollback_mod.is_file()
        and runner.is_file()
        and Path(snapshot).is_file()
        and bool(result.get('ok'))
        and int(result.get('itemCount') or 0) >= 18
        and bool(probe.get('ok'))
    )
    return _merge_ops(
        rollback_state=as_status(ok),
        operations_checks={
            'rollback_module_present': rollback_mod.is_file(),
            'rollback_runner_present': runner.is_file(),
            'rollback_ok': bool(result.get('ok')),
            'rollback_item_count': int(result.get('itemCount') or 0),
            'probe_ok': bool(probe.get('ok')),
        },
    )


def _head() -> str:
    proc = subprocess.run(
        ['git', '-C', str(PRODUCT_ROOT), 'rev-parse', 'HEAD'],
        text=True,
        capture_output=True,
    )
    return (proc.stdout or '').strip()


def _op_final_audit_matrix() -> dict:
    delivered = PRODUCT_ROOT / 'apps/web/dist'
    api = PRODUCT_ROOT / 'apps/api/src/app.ts'
    identity = _input_yaml('CURRENT_RELEASE_IDENTITY')
    head = _head()
    store = _read('apps/api/src/storage/runtimeStore.ts')
    persist_bound = 'persistGetAssignment' in store
    identity_ok = identity.get('status') == 'PASS'
    smoke = run_live_smoke(PRODUCT_ROOT, {'ACPOS_DEPLOYMENT_ENV': 'production'})
    ok = (
        api.is_file()
        and persist_bound
        and identity_ok
        and bool(head)
        and bool(smoke.get('ok'))
    )
    constituents = [
        str((WORK_DIR / 'FINAL_PRODUCTION_ACCEPTANCE_RESULT.yaml').relative_to(PRODUCT_ROOT)),
        str((WORK_DIR / 'GOVERNED_UNIT_CLOSED.yaml').relative_to(PRODUCT_ROOT)),
        str((WORK_DIR / 'NEXT_GOVERNED_UNIT_ELIGIBILITY.yaml').relative_to(PRODUCT_ROOT)),
    ]
    doc = _base('FINAL_AUDIT_EVIDENCE', {
        'post_audit_remediation_state': as_status(ok),
        'audit_reconciliation_state': 'RECONCILED' if ok else 'UNRECONCILED',
        'release_delivered': delivered.is_dir(),
        'api_entry_present': api.is_file(),
        'persist_bound': persist_bound,
        'fresh_head': head,
        'release_identity_status': identity.get('status') or 'MISSING',
        'live_smoke_ok': bool(smoke.get('ok')),
        'constituents': constituents,
        'status': as_status(ok),
    })
    _write_yaml(WORK_DIR / 'EVIDENCE' / 'FINAL_AUDIT_EVIDENCE.yaml', doc)
    _write_yaml(WORK_DIR / 'EVIDENCE' / 'REQUIRED' / 'FINAL_AUDIT_EVIDENCE.yaml', doc)
    return doc


def _op_final_acceptance() -> dict:
    audit = _read_yaml(WORK_DIR / 'EVIDENCE' / 'FINAL_AUDIT_EVIDENCE.yaml')
    ops = _read_yaml(WORK_DIR / 'EVIDENCE' / 'OPERATIONS_EVIDENCE.yaml')
    acceptance = _input_yaml('PRODUCTION_ACCEPTANCE_RESULT')
    smoke = run_live_smoke(PRODUCT_ROOT, {'ACPOS_DEPLOYMENT_ENV': 'production'})
    checks = {
        'post_audit_remediation': audit.get('post_audit_remediation_state') == 'PASS',
        'operations_ready': (
            ops.get('monitoring_state') == 'PASS'
            and ops.get('backup_state') == 'PASS'
            and ops.get('rollback_state') == 'PASS'
        ),
        'production_acceptance_closed': acceptance.get('production_acceptance_state') == 'PASS',
        'live_smoke': bool(smoke.get('ok')),
    }
    ok = all(bool(v) for v in checks.values())
    doc = _base('FINAL_PRODUCTION_ACCEPTANCE_RESULT', {
        'final_production_acceptance_state': as_status(ok),
        'final_acceptance_checklist_state': 'COMPLETE' if ok else 'INCOMPLETE',
        'checks': checks,
        'status': as_status(ok),
    })
    _write_yaml(WORK_DIR / 'FINAL_PRODUCTION_ACCEPTANCE_RESULT.yaml', doc)
    return doc


def _op_governed_unit_closure() -> dict:
    final = _read_yaml(WORK_DIR / 'FINAL_PRODUCTION_ACCEPTANCE_RESULT.yaml')
    complete = final.get('final_production_acceptance_state') == 'PASS' and final.get('status') == 'PASS'
    doc = _base('GOVERNED_UNIT_CLOSED', {
        'project_complete_state': 'COMPLETE' if complete else 'INCOMPLETE',
        'execution_scope_authority_state': 'AUTHORIZED' if complete else 'BLOCKED',
        'dynamic_denominator_state': 'RECONCILED' if complete else 'UNRECONCILED',
        'ownership_portability_audit_result': as_status(complete),
        'status': as_status(complete),
    })
    _write_yaml(WORK_DIR / 'GOVERNED_UNIT_CLOSED.yaml', doc)
    return doc


def _op_next_eligibility() -> dict:
    closed = _read_yaml(WORK_DIR / 'GOVERNED_UNIT_CLOSED.yaml')
    complete = closed.get('project_complete_state') == 'COMPLETE' and closed.get('status') == 'PASS'
    doc = _base('NEXT_GOVERNED_UNIT_ELIGIBILITY', {
        'successor_input_readiness_state': 'PREPARED' if complete else 'BLOCKED',
        'cross_stage_handoff_state': 'READY' if complete else 'BLOCKED',
        'false_completion_audit_result': as_status(complete),
        'next_governed_unit_eligibility_state': 'SCOPE_COMPLETE' if complete else 'PENDING',
        'status': as_status(complete),
    })
    _write_yaml(WORK_DIR / 'NEXT_GOVERNED_UNIT_ELIGIBILITY.yaml', doc)
    return doc


def _write_receipt(op: str, result_owner: str, extra: dict) -> None:
    rec = {
        'artifact_type': 'OPERATION_EXECUTION_RECEIPT', 'stage_uid': 'STAGE-11',
        'work_unit_uid': _wu(), 'operation_uid': op,
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
    if a.operation == 'OP-50-MONITORING_VERIFICATION':
        extra['result'] = _op_monitoring()
        gate = extra['result'].get('monitoring_state') or 'FAIL'
    elif a.operation == 'OP-51-BACKUP_VERIFICATION':
        extra['result'] = _op_backup()
        gate = extra['result'].get('backup_state') or 'FAIL'
    elif a.operation == 'OP-52-ROLLBACK_VERIFICATION':
        extra['result'] = _op_rollback()
        gate = extra['result'].get('rollback_state') or 'FAIL'
    elif a.operation == 'OP-53-FINAL_AUDIT_MATRIX_RECONCILIATION':
        extra['result'] = _op_final_audit_matrix()
        gate = extra['result'].get('status') or 'FAIL'
    elif a.operation == 'OP-54-FINAL_PRODUCTION_ACCEPTANCE':
        extra['result'] = _op_final_acceptance()
        gate = extra['result'].get('status') or 'FAIL'
    elif a.operation == 'GOVERNED_UNIT_CLOSURE':
        extra['result'] = _op_governed_unit_closure()
        gate = extra['result'].get('status') or 'FAIL'
    elif a.operation == 'NEXT_GOVERNED_UNIT_ELIGIBILITY_EVALUATE':
        extra['result'] = _op_next_eligibility()
        gate = extra['result'].get('status') or 'FAIL'
    elif a.operation == 'FINAL_AUDIT_EVIDENCE_COMPILE':
        extra['result'] = _op_final_audit_matrix()
        gate = extra['result'].get('status') or 'FAIL'

    extra['gate_status'] = gate
    _write_receipt(a.operation, result_owner, extra)
    if gate != 'PASS':
        raise SystemExit('OPERATION_FAIL_CLOSED:' + a.operation)
    print('OK', a.operation)


if __name__ == '__main__':
    main()
