#!/usr/bin/env python3
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / 'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
FINDING_UID = 'FIND-20260915-016'

doc = yaml.safe_load(LEDGER.read_text(encoding='utf-8')) or {}
findings = doc.setdefault('findings', [])
if not any(isinstance(x, dict) and x.get('finding_uid') == FINDING_UID for x in findings):
    findings.append({
        'finding_uid': FINDING_UID,
        'class': 'TEST_HARNESS_OR_VALIDATOR_BUG',
        'title': 'Stage-02 R2 remediability classifier accepted same-UID neighboring fields as proof of the missing functional field',
        'evidence': (
            'GitHub run 34892089735 classified 21/171 as BOUNDED_COMPLETION_ADMISSIBLE. '
            'Review of STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION_R2.yaml and immutable CORE/ASSET raw authority showed 11 EXACT_CURRENT_AUTHORITY_BINDING '
            'records where candidate evidence did not prove the missing field itself: three AUDIT_EVENT_NODE_MISSING records matched generic state_event values, '
            'one ACTION_WITHOUT_CONTROL_OR_TRIGGER record matched action_uid existence only, and seven SUCCESS_NEXT_STATE_BINDING_MISSING records matched action/control action_uid only. '
            'These records must not be materialized until a category-specific exact-field or exact deterministic UID join proves the required value.'
        ),
        'disposition': 'OPEN_CLASSIFIER_REMEDIATION',
        'specification_change_required': False,
        'formal_specification_mutated_for_fix': False,
        'current_specification_may_be_modified_from_this_finding_alone': False,
        'root_cause': 'R2 used broad candidate-key matching on any node mentioning the target UID instead of requiring evidence for the exact missing field and relation semantics.',
        'required_fix': (
            'Replace broad same-UID candidate matching with category-specific proof. '
            'AUDIT_EVENT requires an explicit event/audit value; ACTION trigger requires an exact control/transition/system-trigger relation; '
            'SUCCESS_NEXT_STATE requires exact state_effect or deterministic action runtime_binding port_uid -> integration_port state_event provenance. '
            'Keep illegal_transition_tests generation limited to exact authorized transitions.'
        ),
        'stage03_may_advance_before_fix': False,
    })
LEDGER.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=160), encoding='utf-8')
print('PASS: FIND-20260915-016 recorded before classifier repair')
