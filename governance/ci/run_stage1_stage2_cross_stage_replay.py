#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
from typing import Any

import yaml

ROOT = Path('.')
MAIN_WORKFLOW = ROOT / '.github/workflows/rebuild-governance-gate.yml'
POLICY = ROOT / 'governance/STAGE_TEST_CORRECTION_PROMOTION_POLICY_V1.yaml'
EVIDENCE = ROOT / '11_EVIDENCE/audit/STAGE2_FULL_TEST_CYCLE_R1.yaml'
BLOCKER = ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/BLOCKER_LEDGER_R4.yaml'
OUT = ROOT / 'stage1_stage2_cross_stage_replay_result.json'

STAGE1 = 'governance/ci/validate_current_stage1_closure.py'
SUCCESSOR = 'governance/ci/validate_current_stage1_stage2_successor.py'
POLICY_VALIDATOR = 'governance/ci/validate_stage_test_correction_promotion_policy.py'
EXPECTED_MAIN_JOB_COUNT = 44
EXPECTED_BUGS = {'STAGE2-TEST-BUG-001', 'STAGE2-TEST-BUG-002'}
EXPECTED_RULES = {
    'STAGE-TEST-RULE-SHALLOW-CHECKOUT-001',
    'STAGE-TEST-RULE-EVIDENCE-LIFECYCLE-STATE-002',
}
EXPECTED_ARCH = {
    'STATE_TRANSITION_LEDGER_FIELD_MISSING': 50,
    'FAILURE_STATE_ERROR_BINDING_MISSING': 44,
    'POST_ACTION_VALIDATION_NODE_MISSING': 18,
    'AUDIT_EVENT_NODE_MISSING': 13,
    'SUCCESS_NEXT_STATE_BINDING_MISSING': 7,
    'ACTION_WITHOUT_CONTROL_OR_TRIGGER': 1,
}
PY_VALIDATOR_RE = re.compile(r'(?m)(?:^|\s)python(?:3)?\s+(governance/ci/[A-Za-z0-9_./-]+\.py)(?=\s|$)')


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise RuntimeError(f'mapping required: {path}')
    return data


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8', errors='replace')).hexdigest()


def tail(text: str, limit: int = 2500) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def run_validator(phase: str, command_path: str, job_name: str | None = None) -> dict[str, Any]:
    cmd = [sys.executable, command_path]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
    )
    stdout = proc.stdout or ''
    stderr = proc.stderr or ''
    return {
        'phase': phase,
        'job_name': job_name,
        'validator': command_path,
        'command': f'{sys.executable} {command_path}',
        'return_code': proc.returncode,
        'status': 'PASS' if proc.returncode == 0 else 'FAIL',
        'stdout_sha256': sha256_text(stdout),
        'stderr_sha256': sha256_text(stderr),
        'stdout_tail': tail(stdout),
        'stderr_tail': tail(stderr),
    }


def extract_main_validators() -> list[dict[str, str]]:
    wf = load_yaml(MAIN_WORKFLOW)
    jobs = wf.get('jobs')
    if not isinstance(jobs, dict):
        raise RuntimeError('main workflow jobs mapping missing')
    if len(jobs) != EXPECTED_MAIN_JOB_COUNT:
        raise RuntimeError(f'main workflow job denominator drift: {len(jobs)} != {EXPECTED_MAIN_JOB_COUNT}')

    rows: list[dict[str, str]] = []
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            raise RuntimeError(f'malformed workflow job: {job_name}')
        steps = job.get('steps') or []
        found: list[str] = []
        for step in steps:
            if not isinstance(step, dict):
                continue
            run = step.get('run')
            if not isinstance(run, str):
                continue
            found.extend(PY_VALIDATOR_RE.findall(run))
        # Current governance contract: every main job must expose exactly one
        # executable governance/ci Python validator. This makes sequential replay
        # coverage machine-auditable instead of relying on job names or semantics.
        if len(found) != 1:
            raise RuntimeError(f'workflow job must map to exactly one governance validator: {job_name} -> {found}')
        rows.append({'job_name': str(job_name), 'validator': found[0]})
    return rows


def validate_findings_accounted() -> dict[str, Any]:
    evidence = load_yaml(EVIDENCE)
    policy = load_yaml(POLICY)
    blocker = load_yaml(BLOCKER)

    findings = evidence.get('findings') or {}
    bugs = findings.get('test_or_validator_bugs') or []
    bug_uids = {row.get('bug_uid') for row in bugs if isinstance(row, dict)}
    if bug_uids != EXPECTED_BUGS:
        raise RuntimeError(f'discovered bug universe drift: {sorted(bug_uids)}')
    for row in bugs:
        if not isinstance(row, dict):
            continue
        if row.get('correction_status') != 'FIXED_VERIFIED_AND_PROMOTED_TO_CURRENT_OPERATIONAL_POLICY':
            raise RuntimeError(f'bug not fully promoted: {row.get("bug_uid")}')
        if not row.get('promoted_rule_uid'):
            raise RuntimeError(f'bug missing promoted governance rule: {row.get("bug_uid")}')

    rules = policy.get('verified_rule_promotions') or []
    rule_uids = {row.get('rule_uid') for row in rules if isinstance(row, dict)}
    if rule_uids != EXPECTED_RULES:
        raise RuntimeError(f'promoted rule universe drift: {sorted(rule_uids)}')

    evidence_gaps = findings.get('unresolved_product_or_authority_gaps') or {}
    if evidence_gaps.get('functional_gap_total') != 167:
        raise RuntimeError('functional gap truth drift')
    if evidence_gaps.get('architecture_gap_total') != 133:
        raise RuntimeError('architecture gap truth drift')
    if evidence_gaps.get('architecture_gap_categories') != EXPECTED_ARCH:
        raise RuntimeError('architecture category truth drift')
    if evidence_gaps.get('input_source_gap_total') != 34:
        raise RuntimeError('input-source gap truth drift')
    if evidence_gaps.get('functional_authority_gap_total') != 0:
        raise RuntimeError('functional authority gap truth drift')
    if evidence_gaps.get('async_provider_unresolved_lifecycle_binding_total') != 14:
        raise RuntimeError('async lifecycle truth drift')
    if evidence_gaps.get('open_blocker_count') != 3:
        raise RuntimeError('open blocker truth drift')
    if evidence_gaps.get('authorized_automatic_gap_removals') != 0:
        raise RuntimeError('unauthorized automatic gap removal detected')

    baseline = policy.get('stage2_current_known_gap_baseline') or {}
    expected_baseline = {
        'functional_gap_total': 167,
        'architecture_gap_total': 133,
        'input_source_gap_total': 34,
        'functional_authority_gap_total': 0,
        'async_provider_unresolved_lifecycle_binding_total': 14,
    }
    for key, value in expected_baseline.items():
        if baseline.get(key) != value:
            raise RuntimeError(f'policy baseline drift: {key}')
    if baseline.get('architecture_categories') != EXPECTED_ARCH:
        raise RuntimeError('policy architecture category baseline drift')

    summary = blocker.get('summary') or {}
    if summary.get('open_blocker_count') != 3:
        raise RuntimeError('R4 blocker count drift')
    if summary.get('blocked_functional_gap_total') != 167:
        raise RuntimeError('R4 blocked functional gap total drift')
    if summary.get('architecture_contract_gap_count') != 133:
        raise RuntimeError('R4 architecture gap total drift')
    if summary.get('input_contract_gap_count') != 34:
        raise RuntimeError('R4 input gap total drift')
    if summary.get('async_provider_unresolved_lifecycle_binding_count') != 14:
        raise RuntimeError('R4 async lifecycle total drift')
    if summary.get('stage2_exit_gate') != 'BLOCKED':
        raise RuntimeError('Stage-02 exit gate must remain BLOCKED')
    if summary.get('website_construction_allowed') is not False or summary.get('deployment_allowed') is not False:
        raise RuntimeError('website/deployment must remain forbidden while Stage-02 is blocked')

    final_retest = evidence.get('final_cross_stage_retest') or {}
    if final_retest.get('start_boundary') != 'STAGE-01':
        raise RuntimeError('final replay boundary must be STAGE-01')
    if final_retest.get('status') != 'NOT_EXECUTED_AFTER_POLICY_PROMOTION':
        raise RuntimeError('pre-replay evidence state drift')
    if final_retest.get('terminal_receipt') is not None:
        raise RuntimeError('pre-replay evidence may not contain terminal replay receipt')

    cycle = evidence.get('test_cycle_decision') or {}
    if cycle.get('test_infrastructure_bug_count_found') != 2:
        raise RuntimeError('bug count drift')
    if cycle.get('test_infrastructure_bug_count_fixed') != 2:
        raise RuntimeError('fixed bug count drift')
    if cycle.get('verified_fix_promoted_to_policy_count') != 2:
        raise RuntimeError('policy promotion count drift')
    if cycle.get('stage_test_cycle_complete') is not False:
        raise RuntimeError('test cycle may not be pre-closed before replay')

    return {
        'discovered_bug_count': 2,
        'fixed_bug_count': 2,
        'promoted_rule_count': 2,
        'functional_gap_total_preserved': 167,
        'architecture_gap_total_preserved': 133,
        'input_source_gap_total_preserved': 34,
        'functional_authority_gap_total_preserved': 0,
        'async_provider_unresolved_lifecycle_binding_total_preserved': 14,
        'open_blocker_count_preserved': 3,
        'authorized_automatic_gap_removals': 0,
        'stage2_exit_gate': 'BLOCKED',
        'website_construction_allowed': False,
        'deployment_allowed': False,
        'all_previous_findings_accounted_for': True,
    }


def tracked_tree_clean() -> bool:
    a = subprocess.run(['git', 'diff', '--quiet'], cwd=ROOT).returncode
    b = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=ROOT).returncode
    return a == 0 and b == 0


def write_result(result: dict[str, Any]) -> None:
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main() -> int:
    result: dict[str, Any] = {
        'artifact_type': 'STAGE1_STAGE2_CROSS_STAGE_REPLAY_RESULT',
        'governance_overlay': 'v2.1.12',
        'start_boundary': 'STAGE-01',
        'current_stage': 'STAGE-02',
        'execution_semantics': 'STRICT_SEQUENTIAL_PREVIOUS_STAGE_TO_CURRENT_STAGE_REPLAY',
        'status': 'RUNNING',
        'conclusion': None,
        'phases': [],
        'main_workflow_job_denominator_expected': EXPECTED_MAIN_JOB_COUNT,
        'tracked_tree_clean_before': tracked_tree_clean(),
    }
    if not result['tracked_tree_clean_before']:
        result['status'] = 'FAILED'
        result['conclusion'] = 'FAILURE'
        result['failure_reason'] = 'tracked worktree dirty before replay'
        write_result(result)
        return 1

    try:
        main_rows = extract_main_validators()
        result['main_workflow_validator_count_discovered'] = len(main_rows)
        if len(main_rows) != EXPECTED_MAIN_JOB_COUNT:
            raise RuntimeError('main workflow validator count mismatch')

        explicit = [
            ('PHASE_1_STAGE1_CLOSURE', STAGE1, 'current-stage1-closure-gate'),
            ('PHASE_2_STAGE1_TO_STAGE2_SUCCESSOR', SUCCESSOR, 'current-stage1-stage2-successor-gate'),
            ('PHASE_3_POLICY_ENFORCEMENT', POLICY_VALIDATOR, 'current-stage-test-correction-promotion-policy-gate'),
        ]
        for phase, validator, job_name in explicit:
            record = run_validator(phase, validator, job_name)
            result['phases'].append(record)
            if record['return_code'] != 0:
                raise RuntimeError(f'{phase} failed: {validator}')

        skip = {STAGE1, SUCCESSOR}
        phase4_rows = [row for row in main_rows if row['validator'] not in skip]
        result['stage2_main_replay_validator_count'] = len(phase4_rows)
        result['stage1_validators_removed_from_phase4'] = len(main_rows) - len(phase4_rows)
        if result['stage1_validators_removed_from_phase4'] != 2:
            raise RuntimeError('expected exactly two Stage-01 boundary validators to be replayed before Phase 4')

        for row in phase4_rows:
            record = run_validator('PHASE_4_STAGE2_FULL_CURRENT_GOVERNANCE', row['validator'], row['job_name'])
            result['phases'].append(record)
            if record['return_code'] != 0:
                raise RuntimeError(f'Phase 4 failed: {row["job_name"]} -> {row["validator"]}')

        result['findings_comparison'] = validate_findings_accounted()
        result['phases'].append({
            'phase': 'PHASE_5_COMPARE_ALL_PREVIOUS_FINDINGS',
            'status': 'PASS',
            'return_code': 0,
            **result['findings_comparison'],
        })
        result['tracked_tree_clean_after_validators'] = tracked_tree_clean()
        if not result['tracked_tree_clean_after_validators']:
            raise RuntimeError('tracked worktree mutated by replay validators')

        result['validator_execution_count'] = sum(1 for row in result['phases'] if row.get('validator'))
        result['all_validator_executions_passed'] = all(
            row.get('status') == 'PASS' for row in result['phases']
        )
        result['status'] = 'COMPLETED'
        result['conclusion'] = 'SUCCESS'
        result['stage_test_cycle_may_transition_to_complete_after_external_terminal_receipt'] = True
        result['stage2_product_completion'] = False
        result['stage2_product_status'] = 'BLOCKED_BY_TRUE_PRODUCT_OR_AUTHORITY_GAPS'
        write_result(result)
        print('PASS: sequential cross-stage replay started from STAGE-01 and reached Stage-02 under updated policy')
        print(f'PASS: replayed {result["validator_execution_count"]} validator executions in strict sequence')
        print('PASS: 2 discovered test/governance bugs are fixed and promoted into 2 enforced governance rules')
        print('PASS: all prior true gaps remain accounted for: 167 functional + 14 async lifecycle; no unauthorized removals')
        print('PASS: replay success closes only the testing feedback loop after external terminal receipt; Stage-02 product remains BLOCKED')
        return 0
    except Exception as exc:
        result['status'] = 'FAILED'
        result['conclusion'] = 'FAILURE'
        result['failure_reason'] = str(exc)
        result['tracked_tree_clean_at_failure'] = tracked_tree_clean()
        result['stage_test_cycle_may_transition_to_complete_after_external_terminal_receipt'] = False
        result['stage2_product_completion'] = False
        write_result(result)
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
