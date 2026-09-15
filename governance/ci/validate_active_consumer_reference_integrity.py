#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = ROOT / '.github' / 'workflows'
PY_REF = re.compile(r"python(?:3)?\s+(governance/ci/[A-Za-z0-9_.-]+\.py)")
SEMVER_LOCATOR = re.compile(r"governance/(?:current|specifications)/v\d+(?:\.\d+)+")
REPORT = ROOT / 'governance' / 'test' / 'ACTIVE_CONSUMER_REFERENCE_INTEGRITY_REPORT.json'


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


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

    report = {
        'artifact_type': 'NON_NORMATIVE_ACTIVE_CONSUMER_REFERENCE_INTEGRITY_REPORT',
        'workflow_count': workflow_count,
        'direct_governance_python_target_count': len(referenced_by),
        'missing_targets': missing,
        'semver_locator_consumers': semver_consumers,
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
    print('PASS: ACTIVE_CONSUMER_REFERENCE_INTEGRITY')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
