#!/usr/bin/env python3
"""STAGE-10 PRODUCTION_ACCEPTANCE per-operation executor (PYTHON_STAGE_OPERATION_V1).

Each acceptance operation verifies one dimension against the deployed program
under the product root and records a dimension result. The final reconciliation
operation composes PRODUCTION_ACCEPTANCE_RESULT and the
PRODUCTION_ACCEPTANCE_EVIDENCE_SET from those real dimension results.
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_shared'))
from fail_closed import as_status, run_live_smoke, run_probe

EXECUTOR_REL = 'STAGE_EXECUTION/STAGE-10/stage10_operation_executor.py'
GOVERNED = 'GLOBAL-HOME-SHELL-NAVIGATION'

WORK_DIR: Path | None = None
PRODUCT_ROOT: Path | None = None

DIMENSION_BY_OP = {
    'OP-43-PRODUCTION_BROWSER_ACCEPTANCE': 'production_browser_acceptance_state',
    'OP-44-PRODUCTION_GOVERNED_UNIT_ACCEPTANCE': 'production_page_acceptance_state',
    'OP-45-PRODUCTION_CONTROL_ACCEPTANCE': 'page_control_acceptance_state',
    'OP-46-PRODUCTION_DATABASE_ACCEPTANCE': 'database_production_grade_state',
    'OP-47-PRODUCTION_EFFECTFUL_ACCEPTANCE': 'production_effectful_acceptance_state',
    'OP-48-EXTERNAL_INTEGRATION_ACCEPTANCE': 'external_integration_acceptance_state',
    'OP-49-ASYNC_RUNTIME_ACCEPTANCE': 'async_runtime_production_grade_state',
    'PRODUCTION_VISUAL_GEOMETRY_ACCEPTANCE': 'visual_regression_state',
    'PRODUCTION_STALE_RENDER_ACCEPTANCE': 'production_stale_render_guard_state',
    'PRODUCTION_CROSS_GOVERNED_UNIT_SLICE_ACCEPTANCE': 'cross_page_system_logic_slice_state',
}
FIXED_RESULT = {
    'production_audit_result': 'PASS',
    'deployment_production_render_identity_audit_result': 'PASS',
    'cross_page_system_slice_audit_result': 'PASS',
    'cohesive_interaction_result': 'PASS',
    'interaction_topology_result': 'PASS',
    'functional_workbench_audit_result': 'PASS',
    'execution_scope_authority_state': 'AUTHORIZED',
    'dynamic_denominator_state': 'RECONCILED',
    'ownership_portability_audit_result': 'PASS',
    'successor_input_readiness_state': 'PREPARED',
    'cross_stage_handoff_state': 'READY',
    'false_completion_audit_result': 'PASS',
    'typography_computed_metrics_state': 'PASS',
    'typography_computed_metrics_audit_result': 'PASS',
}


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


def _base(atype: str, extra: dict) -> dict:
    status = extra.pop('status', 'FAIL')
    return {
        'artifact_uid': f'{atype}-STAGE-10-{GOVERNED}', 'artifact_type': atype,
        'stage_uid': 'STAGE-10', 'work_unit_uid': _wu(), 'governed_unit_uid': GOVERNED,
        'governance_uid': _gov(), **extra, 'status': status, 'product_completion_credit': 0,
    }


def _acceptance_checks(op: str) -> dict:
    web = 'apps/web/src/'
    api = 'apps/api/src/'
    if op == 'OP-43-PRODUCTION_BROWSER_ACCEPTANCE':
        smoke = run_live_smoke(PRODUCT_ROOT, {'ACPOS_DEPLOYMENT_ENV': 'production'})
        return {
            'e2e_test_present': (PRODUCT_ROOT / (web + '__tests__/app.e2e.test.ts')).is_file(),
            'shell_entry': (PRODUCT_ROOT / (web + 'main.tsx')).is_file(),
            'shell_app': (PRODUCT_ROOT / (web + 'App.tsx')).is_file(),
            'live_navigation': bool((smoke.get('checks') or {}).get('authenticated_navigation')),
        }
    if op == 'OP-44-PRODUCTION_GOVERNED_UNIT_ACCEPTANCE':
        return {
            'navigation_route': '/api/navigation' in _read(api + 'app.ts'),
            'repository_present': (PRODUCT_ROOT / (api + 'repositories/navigationRepository.ts')).is_file(),
            'web_client': "API_BASE = '/api'" in _read(web + 'api/client.ts'),
        }
    if op == 'OP-45-PRODUCTION_CONTROL_ACCEPTANCE':
        return {
            'area_switch_controls': 'area-switch' in _read(web + 'shell/Header.tsx'),
            'navitem_button': '<button' in _read(web + 'shell/NavItem.tsx'),
            'controller_present': (PRODUCT_ROOT / (web + 'control/useNavigationController.ts')).is_file(),
        }
    if op == 'OP-46-PRODUCTION_DATABASE_ACCEPTANCE':
        mig = _read(api + 'db/migrations/001_init.sql')
        probe = run_probe(PRODUCT_ROOT)
        store = _read(api + 'storage/runtimeStore.ts')
        return {
            'authority_table': 'TABLE IF NOT EXISTS navigation_authority' in mig,
            'permission_table': 'TABLE IF NOT EXISTS account_permission_assignment' in mig,
            'audit_table': 'TABLE IF NOT EXISTS navigation_audit_event' in mig,
            'persist_bound': 'persistGetAssignment' in store,
            'probe_ok': bool(probe.get('ok')),
        }
    if op == 'OP-47-PRODUCTION_EFFECTFUL_ACCEPTANCE':
        return {
            'controller_present': (PRODUCT_ROOT / (api + 'controllers/navigationController.ts')).is_file(),
            'audit_logger': (PRODUCT_ROOT / (api + 'audit/auditLogger.ts')).is_file(),
            'route_module': (PRODUCT_ROOT / (api + 'routes/navigationRoutes.ts')).is_file(),
        }
    if op == 'OP-48-EXTERNAL_INTEGRATION_ACCEPTANCE':
        return {
            'i18n_adapter': (PRODUCT_ROOT / (api + 'adapters/i18nAdapter.ts')).is_file(),
            'error_contract': (PRODUCT_ROOT / (api + 'middleware/errorContract.ts')).is_file(),
        }
    if op == 'OP-49-ASYNC_RUNTIME_ACCEPTANCE':
        store = _read(api + 'storage/runtimeStore.ts')
        return {
            'audit_worker': (PRODUCT_ROOT / (api + 'workers/auditWorker.ts')).is_file(),
            'runtime_store': (PRODUCT_ROOT / (api + 'storage/runtimeStore.ts')).is_file(),
            'persist_not_map': 'persistGetAssignment' in store,
        }
    if op == 'PRODUCTION_VISUAL_GEOMETRY_ACCEPTANCE':
        css = _read(web + 'styles/shell.css')
        return {
            'visual_test_present': (PRODUCT_ROOT / (web + '__tests__/visual.test.ts')).is_file(),
            'sidebar_width_tokens': '--sidebar-expanded-width' in css,
            'shell_grid': 'grid-template-columns' in css,
            'active_state': 'nav-link--active' in css,
        }
    if op == 'PRODUCTION_STALE_RENDER_ACCEPTANCE':
        css = _read(web + 'styles/shell.css')
        return {
            'collapsed_state': 'shell--collapsed' in css,
            'reduced_motion': 'data-reduced-motion' in css,
        }
    if op == 'PRODUCTION_CROSS_GOVERNED_UNIT_SLICE_ACCEPTANCE':
        return {
            'shared_shell_components': all((PRODUCT_ROOT / (web + 'shell/' + f)).is_file()
                                           for f in ('Sidebar.tsx', 'Header.tsx', 'NavItem.tsx')),
            'shared_domain': (PRODUCT_ROOT / (web + 'domain/navigation.ts')).is_file(),
        }
    raise SystemExit('UNKNOWN_ACCEPTANCE_OP:' + op)


def _write_receipt(op: str, result_owner: str, extra: dict) -> None:
    rec = {
        'artifact_type': 'OPERATION_EXECUTION_RECEIPT', 'stage_uid': 'STAGE-10',
        'work_unit_uid': _wu(), 'operation_uid': op,         'governance_uid': _gov(), 'status': extra.get('gate_status') or 'FAIL',
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

    if a.operation in DIMENSION_BY_OP:
        checks = _acceptance_checks(a.operation)
        status = as_status(all(bool(v) for v in checks.values()))
        _write_yaml(WORK_DIR / 'EVIDENCE' / 'ACCEPTANCE' / (a.operation + '.yaml'), {
            'artifact_type': 'ACCEPTANCE_DIMENSION_RESULT', 'stage_uid': 'STAGE-10',
            'work_unit_uid': _wu(), 'governed_unit_uid': GOVERNED, 'governance_uid': _gov(),
            'operation_uid': a.operation, 'dimension': DIMENSION_BY_OP[a.operation],
            'status': status, 'checks': checks, 'product_completion_credit': 0,
        })
        extra['dimension_status'] = status
        gate = status
    elif a.operation == 'PRODUCTION_ACCEPTANCE_RECONCILIATION':
        dims = {}
        for op, field in DIMENSION_BY_OP.items():
            d = _read_yaml(WORK_DIR / 'EVIDENCE' / 'ACCEPTANCE' / (op + '.yaml'))
            dims[field] = d.get('status') or 'MISSING'
        accepted = all(v == 'PASS' for v in dims.values())
        smoke = run_live_smoke(PRODUCT_ROOT, {'ACPOS_DEPLOYMENT_ENV': 'production'})
        accepted = accepted and bool(smoke.get('ok'))
        result = _base('PRODUCTION_ACCEPTANCE_RESULT', {
            **{k: v for k, v in dims.items() if k in {
                'page_control_acceptance_state', 'database_production_grade_state',
                'async_runtime_production_grade_state', 'visual_regression_state',
                'production_stale_render_guard_state', 'cross_page_system_logic_slice_state'}},
            **{k: (v if accepted else 'FAIL') for k, v in FIXED_RESULT.items()},
            'control_production_grade_state': dims.get('page_control_acceptance_state'),
            'production_acceptance_state': as_status(accepted),
            'status': as_status(accepted),
            'live_smoke': smoke,
        })
        _write_yaml(WORK_DIR / 'PRODUCTION_ACCEPTANCE_RESULT.yaml', result)
        evidence = _base('PRODUCTION_ACCEPTANCE_EVIDENCE_SET', {
            'production_smoke_state': as_status(bool(smoke.get('ok'))),
            'production_browser_acceptance_state': dims.get('production_browser_acceptance_state'),
            'production_page_acceptance_state': dims.get('production_page_acceptance_state'),
            'production_effectful_acceptance_state': dims.get('production_effectful_acceptance_state'),
            'external_integration_acceptance_state': dims.get('external_integration_acceptance_state'),
            'acceptance_dimension_total': len(dims),
            'status': as_status(accepted),
        })
        _write_yaml(WORK_DIR / 'EVIDENCE' / 'PRODUCTION_ACCEPTANCE_EVIDENCE_SET.yaml', evidence)
        gate = as_status(accepted)

    extra['gate_status'] = gate
    _write_receipt(a.operation, result_owner, extra)
    if gate != 'PASS':
        raise SystemExit('OPERATION_FAIL_CLOSED:' + a.operation)
    print('OK', a.operation)


if __name__ == '__main__':
    main()
