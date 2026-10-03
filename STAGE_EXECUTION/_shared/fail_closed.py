"""Fail-closed helpers for stage operation executors.

Any child gate that is not PASS forces the operation receipt, owned artifact
status and downstream closure fields to FAIL. Receipts never default to PASS.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

TERMINAL_PASS = {'PASS', 'NOT_APPLICABLE_WITH_PROOF'}


def as_status(ok: bool) -> str:
    return 'PASS' if ok else 'FAIL'


def all_pass(values: list[Any]) -> bool:
    return bool(values) and all(value in TERMINAL_PASS or value is True for value in values)


def checks_ok(checks: dict[str, Any]) -> bool:
    if not checks:
        return False

    def _ok(value: Any) -> bool:
        if value is True or value in TERMINAL_PASS:
            return True
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value >= 1
        if isinstance(value, (list, dict)):
            return not value
        return False

    return all(_ok(value) for value in checks.values())


def write_yaml(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True), encoding='utf-8')


def artifact_base(
    *,
    artifact_type: str,
    stage_uid: str,
    work_unit_uid: str,
    governed_unit_uid: str,
    governance_uid: str,
    extra: dict,
    ok: bool,
) -> dict:
    status = as_status(ok)
    doc = {
        'artifact_uid': f'{artifact_type}-{stage_uid}-{governed_unit_uid}',
        'artifact_type': artifact_type,
        'stage_uid': stage_uid,
        'work_unit_uid': work_unit_uid,
        'governed_unit_uid': governed_unit_uid,
        'governance_uid': governance_uid,
        **extra,
        'status': status,
        'product_completion_credit': 0,
    }
    return doc


def run_live_smoke(product_root: Path, extra_env: dict | None = None) -> dict:
    import json
    import subprocess

    env = dict(os.environ)
    env.setdefault('ACPOS_DATABASE_PATH', str(product_root / 'apps/api/data/acpos.sqlite'))
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        ['node', 'scripts/live-smoke.mjs'],
        cwd=str(product_root),
        text=True,
        capture_output=True,
        timeout=120,
        env=env,
    )
    payload: dict = {}
    try:
        payload = json.loads(proc.stdout.strip() or '{}')
    except Exception:
        payload = {'ok': False, 'parse_error': True, 'stdout_tail': (proc.stdout or '')[-2000:]}
    payload['exit_code'] = proc.returncode
    payload['ok'] = bool(payload.get('ok')) and proc.returncode == 0
    payload['stderr_tail'] = (proc.stderr or '')[-2000:]
    return payload


def run_api_script(
    product_root: Path,
    script: str,
    extra_args: list[str] | None = None,
    extra_env: dict | None = None,
    timeout: int = 120,
) -> dict:
    import json
    import subprocess

    env = dict(os.environ)
    env.setdefault('ACPOS_DATABASE_PATH', str(product_root / 'apps/api/data/acpos.sqlite'))
    if extra_env:
        env.update(extra_env)
    cmd = ['npm', '--workspace', '@acpos/api', 'run', script]
    if extra_args:
        cmd.extend(['--', *extra_args])
    proc = subprocess.run(
        cmd,
        cwd=str(product_root),
        text=True,
        capture_output=True,
        timeout=timeout,
        env=env,
    )
    payload: dict = {}
    try:
        lines = [line for line in (proc.stdout or '').splitlines() if line.startswith('{')]
        payload = json.loads(lines[-1]) if lines else {}
    except Exception:
        payload = {'ok': False, 'parse_error': True, 'stdout_tail': (proc.stdout or '')[-2000:]}
    payload['exit_code'] = proc.returncode
    payload['ok'] = bool(payload.get('ok')) and proc.returncode == 0
    payload['stderr_tail'] = (proc.stderr or '')[-2000:]
    return payload


def run_probe(product_root: Path) -> dict:
    return run_api_script(product_root, 'probe')


def run_backup(product_root: Path, snapshot_path: str) -> dict:
    return run_api_script(product_root, 'backup', extra_args=[snapshot_path])


def run_rollback(product_root: Path, snapshot_path: str) -> dict:
    return run_api_script(product_root, 'rollback', extra_args=[snapshot_path])


def run_monitor(product_root: Path) -> dict:
    return run_api_script(product_root, 'monitor')


def write_receipt(
    *,
    path: Path,
    stage_uid: str,
    work_unit_uid: str,
    operation_uid: str,
    governance_uid: str,
    executor_owner: str,
    result_owner: str,
    ok: bool,
    extra: dict | None = None,
) -> dict:
    status = as_status(ok)
    rec = {
        'artifact_type': 'OPERATION_EXECUTION_RECEIPT',
        'stage_uid': stage_uid,
        'work_unit_uid': work_unit_uid,
        'operation_uid': operation_uid,
        'governance_uid': governance_uid,
        'status': status,
        'executor_owner': executor_owner,
        'executor_protocol': 'PYTHON_STAGE_OPERATION_V1',
        'result_owner': result_owner,
        'fail_closed': True,
        'gate_status': status,
    }
    if extra:
        rec.update(extra)
    write_yaml(path, rec)
    return rec
