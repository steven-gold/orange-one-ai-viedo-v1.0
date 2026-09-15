#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = ROOT / '.github' / 'workflows'
PY_REF = re.compile(r"python(?:3)?\s+(governance/ci/[A-Za-z0-9_.-]+\.py)")
SEMVER_LOCATOR = re.compile(r"governance/(?:current|specifications)/v\d+(?:\.\d+)+")
REPORT = ROOT / 'governance' / 'test' / 'ACTIVE_CONSUMER_REFERENCE_INTEGRITY_REPORT.json'

REGISTRY = ROOT / 'governance/specifications/REGISTRY.yaml'
MANIFEST = ROOT / 'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'
CURRENT = ROOT / 'GOVERNANCE_CURRENT.yaml'
ACTIVE_STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
TARGETED_WORKFLOW = ROOT / '.github/workflows/governance-selected-profile-integrity.yml'
FULL_LINE_WORKFLOW = ROOT / '.github/workflows/governance-full-line-system-gate.yml'
REQUIRED_REGRESSION_CONSUMERS = (TARGETED_WORKFLOW, FULL_LINE_WORKFLOW)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(rel(path))
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def main() -> int:
    errors: list[str] = []
    referenced_by: dict[str, set[str]] = defaultdict(set)
    workflow_count = 0

    if not WORKFLOW_ROOT.is_dir():
        print('BLOCK: WORKFLOW_ROOT_MISSING', file=sys.stderr)
        return 1

    workflows = sorted([*WORKFLOW_ROOT.glob('*.yml'), *WORKFLOW_ROOT.glob('*.yaml')])
    for workflow in workflows:
        workflow_count += 1
        text = workflow.read_text(encoding='utf-8')
        if SEMVER_LOCATOR.search(text):
            errors.append(f'SEMVER_LOCATOR_IN_ACTIVE_WORKFLOW:{rel(workflow)}')
        for match in PY_REF.finditer(text):
            referenced_by[match.group(1)].add(rel(workflow))

    missing: dict[str, list[str]] = {}
    semver_consumers: dict[str, list[str]] = {}
    for script_rel, consumers in sorted(referenced_by.items()):
        script = ROOT / script_rel
        if not script.is_file():
            names = sorted(consumers)
            missing[script_rel] = names
            errors.append(f"MISSING_ACTIVE_CONSUMER_TARGET:{script_rel}<-{','.join(names)}")
            continue
        text = script.read_text(encoding='utf-8')
        if SEMVER_LOCATOR.search(text):
            names = sorted(consumers)
            semver_consumers[script_rel] = names
            errors.append(f"SEMVER_LOCATOR_IN_ACTIVE_CONSUMER:{script_rel}<-{','.join(names)}")

    projector_values: dict[str, str | None] = {}
    selected_profile: dict = {}
    try:
        registry = load_yaml(REGISTRY)
        manifest = load_yaml(MANIFEST)
        current = load_yaml(CURRENT)
        active_state = load_yaml(ACTIVE_STATE)
        current_uid = (registry.get('active_specification') or {}).get('governance_uid')
        if not current_uid:
            errors.append('REGISTRY_ACTIVE_GOVERNANCE_UID_MISSING')
        projector_values = {
            rel(MANIFEST): manifest.get('artifact_uid'),
            rel(CURRENT): current.get('active_governance_uid'),
            rel(ACTIVE_STATE): active_state.get('specification_uid'),
            rel(ACTIVE_STATE) + '#transition': ((active_state.get('governance_revision_transition') or {}).get('current_governance_uid')),
        }
        for owner, value in projector_values.items():
            if current_uid and value != current_uid:
                errors.append(f'ACTIVE_GOVERNANCE_PROJECTOR_STALE:{owner}:expected={current_uid}:actual={value}')

        selected_profile = current.get('selected_execution_profile') or {}
        profile_ref = selected_profile.get('registry')
        if not profile_ref:
            errors.append('SELECTED_EXECUTION_PROFILE_REGISTRY_MISSING')
        else:
            profile_path = ROOT / str(profile_ref)
            profile = load_yaml(profile_path)
            if profile.get('artifact_type') != 'EXECUTION_PROFILE_REGISTRY':
                errors.append('SELECTED_EXECUTION_PROFILE_TYPE_INVALID')
            if profile.get('layer_classification') != 'EXECUTION_PROFILE':
                errors.append('SELECTED_EXECUTION_PROFILE_LAYER_INVALID')
            if profile.get('global_normative_authority') is not False:
                errors.append('SELECTED_EXECUTION_PROFILE_GLOBAL_AUTHORITY_INVALID')
            if profile.get('profile_uid') != selected_profile.get('profile_uid'):
                errors.append('SELECTED_EXECUTION_PROFILE_UID_DRIFT')
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f'ACTIVE_PROJECTOR_PARSE_OR_MISSING:{exc}')

    required_regression_gate_presence: dict[str, bool] = {}
    gate_ref = 'governance/ci/validate_active_consumer_reference_integrity.py'
    for workflow in REQUIRED_REGRESSION_CONSUMERS:
        present = workflow.is_file() and gate_ref in workflow.read_text(encoding='utf-8')
        required_regression_gate_presence[rel(workflow)] = present
        if not present:
            errors.append(f'REFERENCE_INTEGRITY_GATE_MISSING_FROM_REQUIRED_REGRESSION:{rel(workflow)}')

    report = {
        'artifact_type': 'NON_NORMATIVE_ACTIVE_CONSUMER_REFERENCE_INTEGRITY_REPORT',
        'workflow_count': workflow_count,
        'direct_governance_python_target_count': len(referenced_by),
        'missing_targets': missing,
        'semver_locator_consumers': semver_consumers,
        'active_governance_projectors': projector_values,
        'selected_execution_profile': {
            'profile_uid': selected_profile.get('profile_uid'),
            'registry': selected_profile.get('registry'),
            'global_normative_authority': selected_profile.get('global_normative_authority'),
        },
        'required_regression_gate_presence': required_regression_gate_presence,
        'result': 'PASS' if not errors else 'FAIL',
        'errors': errors,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    if errors:
        for error in errors:
            print('BLOCK:', error, file=sys.stderr)
        return 1

    print(f'PASS: active workflows scanned={workflow_count}')
    print(f'PASS: direct governance python targets={len(referenced_by)} all exist')
    print('PASS: no active workflow/direct-consumer semver governance locator')
    print('PASS: Registry, Manifest, Current entrypoint, and Active State project one immutable governance UID')
    print('PASS: selected execution profile is explicitly non-global and resolves through its profile registry')
    print('PASS: active-consumer reference-integrity gate is present in targeted and Full-Line required regressions')
    print('PASS: ACTIVE_CONSUMER_REFERENCE_INTEGRITY')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
