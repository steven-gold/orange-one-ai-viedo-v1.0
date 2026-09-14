#!/usr/bin/env python3
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / 'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
UID = 'FIND-20260915-015'

obj = yaml.safe_load(LEDGER.read_text(encoding='utf-8')) or {}
findings = obj.setdefault('findings', [])
if any(isinstance(x, dict) and x.get('finding_uid') == UID for x in findings):
    print('PASS: finding already recorded')
    raise SystemExit(0)

findings.append({
    'finding_uid': UID,
    'class': 'TEST_HARNESS_OR_VALIDATOR_BUG',
    'title': 'Stage-02 remediation reexecution functional detector rescans immutable Stage-01 raw authority only and cannot recognize legal Stage-02 owning-layer remediation',
    'evidence': 'GitHub run 34890864792 freshly reexecuted Stage-02 after materializing and validating the Stage-02 product root. It correctly proved structural closure blockers 13 -> 0, but functional evaluation invoked the exact original raw-only fresh_scan implementation and therefore reported the same 171 raw-source gaps without evaluating whether a bounded Stage-02 functional contract could legally satisfy any of them.',
    'disposition': 'OPEN_HARNESS_REMEDIATION',
    'specification_change_required': False,
    'formal_specification_mutated_for_fix': False,
    'current_specification_may_be_modified_from_this_finding_alone': False,
    'root_cause': 'Discovery scanner and remediation-closure validator are conflated. Stage-01 immutable authority must remain the authorization baseline, while Stage-02 owning-layer contracts must be evaluated as the legal materialization layer under bounded functional completion rules.',
    'required_fix': 'Add a dual-layer Stage-02 remediation validator that requires exact Stage-01 seed/required-operation provenance, bounded minimal closure, zero authority-gap override, and source-linked Stage-02 contract evidence before a raw discovery gap can count as eliminated. Preserve the raw-only scanner as the immutable discovery/regression baseline.',
    'stage03_may_advance_before_fix': False,
})
LEDGER.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=140), encoding='utf-8')
print('PASS: recorded FIND-20260915-015 before validator remediation')
