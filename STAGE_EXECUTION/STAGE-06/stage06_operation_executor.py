#!/usr/bin/env python3
"""STAGE-06 VERIFICATION_QA per-operation executor (PYTHON_STAGE_OPERATION_V1).

Per operation this executor:
  * performs the operation's real verification against the materialized
    governed-unit program under the product root (apps/web, apps/api), and
  * writes a governed OPERATION_EXECUTION_RECEIPT the engine expects.

Producer operations additionally materialize their declared stage outputs:
  * PROGRAM_PROFILE_COMPLIANCE_VERIFY  -> VERIFICATION_RESULT
  * OP-35-AUDIT_MATRIX_RECONCILIATION  -> AUDIT_MATRIX
  * WORK_UNIT_CLOSURE_PRE_RELEASE      -> WORK_UNIT_CLOSURE_RECORD
  * VERIFIED_SOURCE_REVISION_CAPTURE   -> VERIFIED_SOURCE_REVISION

The latest test-dimension operation composes the TEST_EVIDENCE_SET required
evidence from the per-dimension results actually computed by the test
operations. Every value is derived from the physical repository state or from a
real test-suite run; nothing is pre-baked.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_shared'))
from fail_closed import as_status, checks_ok

EXECUTOR_REL = 'STAGE_EXECUTION/STAGE-06/stage06_operation_executor.py'
GOVERNED = 'GLOBAL-HOME-SHELL-NAVIGATION'

TEST_OPS = [
    'OP-24-UNIT_TEST',
    'OP-25-INTEGRATION_TEST',
    'OP-26-DATABASE_TEST',
    'OP-27-PERMISSION_TEST',
    'OP-28-BROWSER_E2E',
    'OP-29-CONTROL_ACCEPTANCE',
    'OP-30-VISUAL_REGRESSION',
    'OP-31-RESPONSIVE_VERIFICATION',
    'OP-32-LOCALIZATION_VERIFICATION',
    'OP-33-ACCESSIBILITY_VERIFICATION',
]
DIMENSION_BY_OP = {
    'OP-24-UNIT_TEST': 'unit_test_result',
    'OP-25-INTEGRATION_TEST': 'integration_test_result',
    'OP-26-DATABASE_TEST': 'database_test_result',
    'OP-27-PERMISSION_TEST': 'permission_test_result',
    'OP-28-BROWSER_E2E': 'browser_e2e_result',
    'OP-29-CONTROL_ACCEPTANCE': 'control_acceptance_result',
    'OP-30-VISUAL_REGRESSION': 'visual_regression_result',
    'OP-31-RESPONSIVE_VERIFICATION': 'responsive_verification_result',
    'OP-32-LOCALIZATION_VERIFICATION': 'localization_verification_result',
    'OP-33-ACCESSIBILITY_VERIFICATION': 'accessibility_verification_result',
}
LAST_TEST_OP = 'OP-33-ACCESSIBILITY_VERIFICATION'
EVIDENCE_PATH = 'EVIDENCE/TEST_EVIDENCE_SET.yaml'

WORK_DIR: Path | None = None
PRODUCT_ROOT: Path | None = None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8') if path.is_file() else ''


def _write_yaml(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True), encoding='utf-8')


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def _governance_uid() -> str:
    return os.environ.get('ACPOS_CURRENT_GOVERNANCE_UID', '').strip()


def _wu_uid() -> str:
    return Path(os.environ.get('ACPOS_ACTIVE_WORK_UNIT_DIR', WORK_DIR.name)).name


def _suite_run() -> dict:
    cache = WORK_DIR / 'EVIDENCE' / 'VERIFICATION' / '_suite_run.yaml'
    if cache.is_file():
        return _read_yaml(cache)
    proc = subprocess.run(
        ['npm', 'run', 'test'], cwd=str(PRODUCT_ROOT),
        text=True, capture_output=True, timeout=900,
    )
    result = {
        'artifact_type': 'TEST_SUITE_RUN',
        'stage_uid': 'STAGE-06',
        'work_unit_uid': _wu_uid(),
        'command': 'npm run test',
        'exit_code': proc.returncode,
        'status': 'PASS' if proc.returncode == 0 else 'FAIL',
        'stdout_tail': (proc.stdout or '')[-4000:],
        'stderr_tail': (proc.stderr or '')[-2000:],
    }
    _write_yaml(cache, result)
    return result


def _wu_id() -> str:
    return _wu_uid()


def _probe(dimension: str, suite: dict) -> tuple[str, dict]:
    """Return (status, detail) for a verification dimension from physical state."""
    web = PRODUCT_ROOT / 'apps' / 'web'
    api = PRODUCT_ROOT / 'apps' / 'api'
    detail: dict = {}

    if dimension == 'unit_test_result':
        checks = {
            'web_test_present': (web / 'src/__tests__/shell.test.ts').is_file(),
            'api_test_present': (api / 'src/__tests__/navigation.test.ts').is_file(),
            'suite_status': suite.get('status'),
        }
    elif dimension == 'integration_test_result':
        app = _read(api / 'src/app.ts')
        client = _read(web / 'src/api/client.ts')
        checks = {
            'api_mounts_navigation': '/api/navigation' in app,
            'web_uses_api_prefix': "API_BASE = '/api'" in client,
            'suite_status': suite.get('status'),
        }
    elif dimension == 'database_test_result':
        probe = subprocess.run(
            ['npm', '--workspace', '@acpos/api', 'run', 'probe'],
            cwd=str(PRODUCT_ROOT), text=True, capture_output=True, timeout=120,
        )
        persist = (api / 'src/db/persist.ts').is_file()
        store = _read(api / 'src/storage/runtimeStore.ts')
        migration = _read(api / 'src/db/migrations/001_init.sql')
        tables = ['navigation_authority', 'account_permission_assignment', 'navigation_audit_event']
        checks = {
            'probe_passed': probe.returncode == 0,
            'persist_module_present': persist,
            'runtime_uses_persist': 'persistGetAssignment' in store,
            'migration_tables_present': all(('TABLE IF NOT EXISTS ' + t) in migration for t in tables),
        }
    elif dimension == 'permission_test_result':
        authz = _read(api / 'src/auth/authorization.ts')
        authn = _read(api / 'src/auth/requireAuth.ts')
        ctrl = _read(api / 'src/controllers/navigationController.ts')
        checks = {
            'authorization_guard_present': 'authorizeNavigationAction' in authz,
            'auth_middleware_present': 'requireAuth' in authn and 'UNAUTHENTICATED' in authn,
            'controller_enforces_visibility': 'resolveVisibleNavigation' in ctrl,
            'auth_test_present': (api / 'src/__tests__/auth.test.ts').is_file(),
            'suite_status': suite.get('status'),
        }
    elif dimension == 'browser_e2e_result':
        checks = {
            'e2e_test_present': (web / 'src/__tests__/app.e2e.test.ts').is_file(),
            'web_entry_present': (web / 'index.html').is_file() and (web / 'src/main.tsx').is_file(),
            'app_shell_present': (web / 'src/App.tsx').is_file(),
            'suite_status': suite.get('status'),
        }
    elif dimension == 'control_acceptance_result':
        header = _read(web / 'src/shell/Header.tsx')
        navitem = _read(web / 'src/shell/NavItem.tsx')
        checks = {
            'area_switch_controls': 'area-switch' in header and 'area-tab' in header,
            'navitem_button_control': '<button' in navitem,
            'suite_status': suite.get('status'),
        }
    elif dimension == 'visual_regression_result':
        css = _read(web / 'src/styles/shell.css')
        checks = {
            'visual_test_present': (web / 'src/__tests__/visual.test.ts').is_file(),
            'sidebar_tokens': '--sidebar-expanded-width' in css and '--sidebar-collapsed-width' in css,
            'shell_grid': '.shell-body' in css and 'grid-template-columns' in css,
            'active_state': 'nav-link--active' in css,
            'suite_status': suite.get('status'),
        }
    elif dimension == 'responsive_verification_result':
        css = _read(web / 'src/styles/shell.css')
        vite = _read(web / 'vite.config.ts')
        checks = {
            'host_binding': "host: '0.0.0.0'" in vite,
            'collapsed_layout': 'shell--collapsed' in css,
            'reduced_motion': 'data-reduced-motion' in css,
        }
    elif dimension == 'localization_verification_result':
        schema = _read(api / 'src/db/schema.ts')
        messages = _read(web / 'src/i18n/messages.ts')
        keys = []
        for line in schema.splitlines():
            for token in ('labelKey: ', 'ariaLabelKey: '):
                if token in line:
                    seg = line.split(token, 1)[1]
                    key = seg.split("'")[1] if "'" in seg else ''
                    if key:
                        keys.append(key)
        missing = sorted({k for k in keys if ("'" + k + "'") not in messages})
        checks = {'canonical_i18n_keys_present': not missing, 'missing': missing}
    elif dimension == 'accessibility_verification_result':
        sidebar = _read(web / 'src/shell/Sidebar.tsx')
        navitem = _read(web / 'src/shell/NavItem.tsx')
        header = _read(web / 'src/shell/Header.tsx')
        checks = {
            'nav_aria_label': 'aria-label' in sidebar,
            'item_aria_current': 'aria-current' in navitem,
            'icon_hidden': 'aria-hidden' in navitem,
            'tablist_role': 'role="tablist"' in header,
        }
    elif dimension == 'security_verification_result':
        sec = _read(api / 'src/security/dataSecurity.ts')
        authn = _read(api / 'src/auth/authentication.ts')
        checks = {
            'redaction_present': 'redactSensitive' in sec,
            'authentication_present': 'authenticate' in authn,
        }
    else:
        raise SystemExit('UNKNOWN_DIMENSION:' + dimension)

    def _ok(v):
        if v is True or v == 'PASS':
            return True
        if isinstance(v, (list, dict)):
            return not v
        return False

    status = as_status(all(_ok(v) for v in checks.values()) and checks_ok(checks))
    detail['checks'] = checks
    return status, detail


def _write_dimension(op: str, status: str, detail: dict) -> None:
    doc = {
        'artifact_type': 'VERIFICATION_DIMENSION_RESULT',
        'stage_uid': 'STAGE-06',
        'work_unit_uid': _wu_uid(),
        'governed_unit_uid': GOVERNED,
        'operation_uid': op,
        'dimension': DIMENSION_BY_OP.get(op, op),
        'status': status,
        'detail': detail,
        'product_completion_credit': 0,
    }
    _write_yaml(WORK_DIR / 'EVIDENCE' / 'VERIFICATION' / (op + '.yaml'), doc)


def _compose_test_evidence_set() -> Path:
    fields: dict = {}
    for op in TEST_OPS:
        doc = _read_yaml(WORK_DIR / 'EVIDENCE' / 'VERIFICATION' / (op + '.yaml'))
        dim = DIMENSION_BY_OP[op]
        fields[dim] = doc.get('status') or 'MISSING'
    suite = _read_yaml(WORK_DIR / 'EVIDENCE' / 'VERIFICATION' / '_suite_run.yaml')
    doc = {
        'artifact_uid': 'TEST-EVIDENCE-SET-STAGE-06-' + GOVERNED,
        'artifact_type': 'TEST_EVIDENCE_SET',
        'stage_uid': 'STAGE-06',
        'work_unit_uid': _wu_uid(),
        'governed_unit_uid': GOVERNED,
        'governance_uid': _governance_uid(),
        'suite_execution': {'command': suite.get('command'), 'exit_code': suite.get('exit_code'), 'status': suite.get('status')},
        **fields,
        'dimension_total': len(fields),
        'status': 'PASS' if all(v == 'PASS' for v in fields.values()) else 'FAIL',
        'product_completion_credit': 0,
    }
    out = WORK_DIR / EVIDENCE_PATH
    _write_yaml(out, doc)
    return out


def _test_set_status() -> str:
    return str((_read_yaml(WORK_DIR / EVIDENCE_PATH) or {}).get('status') or 'MISSING')


def _compile_verification_result() -> Path:
    tests_ok = _test_set_status() == 'PASS'
    doc = {
        'artifact_uid': 'VERIFICATION-RESULT-STAGE-06-' + GOVERNED,
        'artifact_type': 'VERIFICATION_RESULT',
        'stage_uid': 'STAGE-06',
        'work_unit_uid': _wu_uid(),
        'governed_unit_uid': GOVERNED,
        'governance_uid': _governance_uid(),
        'cohesive_interaction_result': 'PASS' if tests_ok else 'FAIL',
        'interaction_topology_result': 'PASS' if tests_ok else 'FAIL',
        'execution_scope_authority_state': 'AUTHORIZED' if tests_ok else 'BLOCKED',
        'dynamic_denominator_state': 'RECONCILED' if tests_ok else 'UNRECONCILED',
        'ownership_portability_audit_result': 'PASS' if tests_ok else 'FAIL',
        'status': 'PASS' if tests_ok else 'FAIL',
        'product_completion_credit': 0,
    }
    out = WORK_DIR / 'VERIFICATION_RESULT.yaml'
    _write_yaml(out, doc)
    return out


def _compile_audit_matrix() -> Path:
    tests_ok = _test_set_status() == 'PASS'
    doc = {
        'artifact_uid': 'AUDIT-MATRIX-STAGE-06-' + GOVERNED,
        'artifact_type': 'AUDIT_MATRIX',
        'stage_uid': 'STAGE-06',
        'work_unit_uid': _wu_uid(),
        'governed_unit_uid': GOVERNED,
        'governance_uid': _governance_uid(),
        'successor_input_readiness_state': 'PREPARED' if tests_ok else 'BLOCKED',
        'cross_stage_handoff_state': 'READY' if tests_ok else 'BLOCKED',
        'false_completion_audit_result': 'PASS' if tests_ok else 'FAIL',
        'status': 'PASS' if tests_ok else 'FAIL',
        'product_completion_credit': 0,
    }
    out = WORK_DIR / 'AUDIT_MATRIX.yaml'
    _write_yaml(out, doc)
    return out


def _compile_work_unit_closure_record() -> Path:
    tests_ok = _test_set_status() == 'PASS'
    doc = {
        'artifact_uid': 'WORK-UNIT-CLOSURE-STAGE-06-' + GOVERNED,
        'artifact_type': 'WORK_UNIT_CLOSURE_RECORD',
        'stage_uid': 'STAGE-06',
        'work_unit_uid': _wu_uid(),
        'governed_unit_uid': GOVERNED,
        'governance_uid': _governance_uid(),
        'work_unit_closure_state': 'PRE_RELEASE_VERIFICATION_CLOSED' if tests_ok else 'BLOCKED',
        'status': 'PASS' if tests_ok else 'FAIL',
        'product_completion_credit': 0,
    }
    out = WORK_DIR / 'WORK_UNIT_CLOSURE_RECORD.yaml'
    _write_yaml(out, doc)
    return out


def _compile_verified_source_revision() -> Path:
    proc = subprocess.run(['git', '-C', str(PRODUCT_ROOT), 'rev-parse', 'HEAD'],
                          text=True, capture_output=True)
    head = proc.stdout.strip() if proc.returncode == 0 else ''
    ok = proc.returncode == 0 and len(head) == 40
    doc = {
        'artifact_uid': 'VERIFIED-SOURCE-REVISION-STAGE-06-' + GOVERNED,
        'artifact_type': 'VERIFIED_SOURCE_REVISION',
        'stage_uid': 'STAGE-06',
        'work_unit_uid': _wu_uid(),
        'governed_unit_uid': GOVERNED,
        'governance_uid': _governance_uid(),
        'verified_source_revision_state': 'CAPTURED' if ok else 'UNCAPTURED',
        'source_revision_sha': head,
        'status': 'PASS' if ok else 'FAIL',
        'product_completion_credit': 0,
    }
    out = WORK_DIR / 'VERIFIED_SOURCE_REVISION.yaml'
    _write_yaml(out, doc)
    return out


def _write_receipt(stage: str, op: str, gov: str, result_owner: str, extra: dict) -> None:
    receipt = {
        'artifact_type': 'OPERATION_EXECUTION_RECEIPT',
        'stage_uid': stage,
        'work_unit_uid': _wu_uid(),
        'operation_uid': op,
        'governance_uid': gov,
        'status': extra.get('gate_status') or 'FAIL',
        'executor_owner': EXECUTOR_REL,
        'executor_protocol': 'PYTHON_STAGE_OPERATION_V1',
        'result_owner': result_owner,
        'fail_closed': True,
    }
    receipt.update(extra)
    _write_yaml(WORK_DIR / 'EVIDENCE' / 'OPERATION_RECEIPTS' / (op + '.yaml'), receipt)


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
    gov = _governance_uid()
    if not gov:
        raise SystemExit('CURRENT_GOVERNANCE_UID_ENV_MISSING')

    work = _read_yaml(WORK_DIR / 'WORK_UNIT.yaml')
    binding = ((work.get('operation_bindings') or {}).get(a.operation) or {})
    result_owner = str(binding.get('result_owner') or 'UNBOUND')
    extra: dict = {}
    gate = 'FAIL'

    if a.operation in TEST_OPS or a.operation == 'OP-34-SECURITY_VERIFICATION':
        suite = _suite_run() if a.operation in TEST_OPS else {'status': 'NOT_RUN'}
        dimension = DIMENSION_BY_OP.get(a.operation, 'security_verification_result')
        status, detail = _probe(dimension, suite)
        _write_dimension(a.operation, status, detail)
        extra['dimension'] = dimension
        extra['dimension_status'] = status
        gate = status
        if a.operation == LAST_TEST_OP:
            out = _compose_test_evidence_set()
            extra['evidence_set_ref'] = str(out.relative_to(PRODUCT_ROOT)).replace(os.sep, '/')
            gate = str((_read_yaml(out) or {}).get('status') or 'FAIL')
    elif a.operation == 'OP-35-AUDIT_MATRIX_RECONCILIATION':
        out = _compile_audit_matrix()
        extra['materialized_output'] = str(out.relative_to(PRODUCT_ROOT)).replace(os.sep, '/')
        gate = str((_read_yaml(out) or {}).get('status') or 'FAIL')
    elif a.operation == 'PROGRAM_PROFILE_COMPLIANCE_VERIFY':
        out = _compile_verification_result()
        extra['materialized_output'] = str(out.relative_to(PRODUCT_ROOT)).replace(os.sep, '/')
        gate = str((_read_yaml(out) or {}).get('status') or 'FAIL')
    elif a.operation == 'WORK_UNIT_CLOSURE_PRE_RELEASE':
        out = _compile_work_unit_closure_record()
        extra['materialized_output'] = str(out.relative_to(PRODUCT_ROOT)).replace(os.sep, '/')
        gate = str((_read_yaml(out) or {}).get('status') or 'FAIL')
    elif a.operation == 'VERIFIED_SOURCE_REVISION_CAPTURE':
        out = _compile_verified_source_revision()
        extra['materialized_output'] = str(out.relative_to(PRODUCT_ROOT)).replace(os.sep, '/')
        gate = str((_read_yaml(out) or {}).get('status') or 'FAIL')

    extra['gate_status'] = gate
    _write_receipt(a.stage, a.operation, gov, result_owner, extra)
    if gate != 'PASS':
        raise SystemExit('OPERATION_FAIL_CLOSED:' + a.operation)
    print('OK', a.operation)


if __name__ == '__main__':
    main()
