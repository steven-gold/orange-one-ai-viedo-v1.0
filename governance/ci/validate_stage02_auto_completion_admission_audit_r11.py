#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R10 = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_AUTHORITY_APPROVAL_DOCKET_R10.yaml'
R11 = ROOT / 'governance/test/stage02/STAGE02_AUTO_COMPLETION_ADMISSION_AUDIT_R11.yaml'
ACTIVE_ROOT = ROOT / '.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'
ACTIVE_INVARIANTS = ROOT / '.github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'


def die(msg: str) -> None:
    print(f'BLOCK: {msg}', file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> dict:
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(obj, dict):
        die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj


def main() -> None:
    r10 = load(R10)
    r11 = load(R11)
    manifest = load(ACTIVE_ROOT)
    invariants = load(ACTIVE_INVARIANTS)

    revision = manifest.get('governance_revision')
    if r11.get('active_governance_revision') != revision or not str(revision).startswith('v2.1.14'):
        die('R11_ACTIVE_GOVERNANCE_REVISION_DRIFT')

    inv = invariants.get('invariants', invariants)
    fa = inv.get('FUNCTION_ADMISSION_NECESSITY_AND_UTILITY') or {}
    auto = (fa.get('decision_classes') or {}).get('REQUIRED_AUTO_COMPLETION_ELIGIBLE') or {}
    bfc = inv.get('BOUNDED_FUNCTIONAL_COMPLETION') or {}
    if auto.get('requires_zero_authority_gap') is not True:
        die('R11_ZERO_AUTHORITY_GAP_PRECONDITION_DRIFT')
    if fa.get('score_may_override_authority_gap') is not False:
        die('R11_SCORE_AUTHORITY_PRECEDENCE_DRIFT')
    if bfc.get('completion_may_expand_product_scope') is not False:
        die('R11_PRODUCT_SCOPE_EXPANSION_GUARD_DRIFT')

    if r11.get('artifact_type') != 'NON_NORMATIVE_STAGE02_AUTO_COMPLETION_ADMISSION_AUDIT_R11':
        die('R11_WRONG_ARTIFACT_TYPE')
    if r11.get('normative_authority') is not False or r11.get('stage_uid') != 'STAGE-02':
        die('R11_NORMATIVE_OR_STAGE_DRIFT')

    r10_records = r10.get('records') or []
    r11_records = r11.get('records') or []
    if len(r10_records) != 150 or len(r11_records) != 150:
        die(f'R11_RECORD_COUNT_DRIFT:{len(r10_records)}:{len(r11_records)}')

    expected = {r.get('blocker_uid'): r for r in r10_records}
    actual = {r.get('blocker_uid'): r for r in r11_records}
    if len(expected) != 150 or len(actual) != 150 or set(expected) != set(actual):
        die('R11_BLOCKER_UID_COVERAGE_DRIFT')

    scopes = Counter()
    categories = Counter()
    for uid, base in expected.items():
        rec = actual[uid]
        for field in ('scope', 'category', 'target_uid', 'missing_field_or_relation', 'verified_review_ref'):
            if rec.get(field) != base.get(field):
                die(f'R11_IDENTITY_DRIFT:{uid}:{field}')
        if base.get('approval_state') != 'PENDING_EXPLICIT_PRODUCT_AUTHORITY':
            die(f'R11_R10_RECORD_NO_LONGER_PENDING:{uid}')
        decision = base.get('authority_decision_required') or {}
        if any(v not in (None, '', [], {}) for v in decision.values()):
            die(f'R11_R10_PARTIAL_AUTHORITY_VALUE_PRESENT:{uid}')
        if rec.get('authority_gap_present') is not True or rec.get('authority_gap_zero') is not False:
            die(f'R11_AUTHORITY_GAP_CLASSIFICATION_DRIFT:{uid}')
        if rec.get('necessity_score') is not None or rec.get('score_disposition') != 'NOT_SCORED_AUTHORITY_GAP_PRECEDENCE':
            die(f'R11_SCORE_PRECEDENCE_VIOLATION:{uid}')
        if rec.get('auto_completion_decision') != 'BLOCK_AUTO_COMPLETION_AUTHORITY_GAP' or rec.get('auto_completion_eligible') is not False:
            die(f'R11_AUTO_COMPLETION_FALSE_ALLOW:{uid}')
        if rec.get('bounded_completion_seed_evaluation') != 'NOT_REACHED_AUTHORITY_GAP_PRECONDITION_FAILED':
            die(f'R11_BOUNDED_COMPLETION_PRECONDITION_DRIFT:{uid}')
        if rec.get('minimal_closure_expansion_allowed') is not False or rec.get('product_scope_expansion_allowed') is not False:
            die(f'R11_SCOPE_EXPANSION_FALSE_ALLOW:{uid}')
        if rec.get('authority_value_supplied_by_ai') is not False:
            die(f'R11_AI_AUTHORITY_VALUE_FORBIDDEN:{uid}')
        if rec.get('r7_materialization_allowed') is not False or rec.get('blocker_reduction_credit') != 0:
            die(f'R11_FALSE_MATERIALIZATION_OR_REDUCTION:{uid}')
        if rec.get('next_legal_action') != 'EXPLICIT_PRODUCT_AUTHORITY_DECISION_THEN_R7_INGESTION':
            die(f'R11_NEXT_ACTION_DRIFT:{uid}')
        scopes[rec.get('scope')] += 1
        categories[rec.get('category')] += 1

    den = r11.get('denominators') or {}
    if den.get('r10_product_authority_decisions') != 150:
        die('R11_DENOMINATOR_NOT_150')
    if den.get('auto_completion_eligible') != 0 or den.get('blocked_by_authority_gap') != 150:
        die('R11_AUTO_COMPLETION_COUNTS_INVALID')
    if den.get('not_scored_due_authority_gap_precedence') != 150:
        die('R11_SCORE_PRECEDENCE_COUNT_INVALID')
    if den.get('r7_materializable') != 0 or den.get('effective_stage02_blocker_reduction_claimed') != 0:
        die('R11_FALSE_REDUCTION_COUNT')
    if den.get('scope_counts') != dict(scopes):
        die('R11_SCOPE_COUNTS_DRIFT')
    if den.get('category_counts') != dict(categories):
        die('R11_CATEGORY_COUNTS_DRIFT')
    if dict(scopes) != {'ASSET-01': 110, 'CORE-01': 40}:
        die(f'R11_SCOPE_DENOMINATOR_WRONG:{dict(scopes)}')

    safety = r11.get('safety') or {}
    for key in ('audit_is_product_authority', 'audit_is_approval_evidence', 'audit_may_fill_product_values', 'necessity_score_may_be_used_to_override_authority_gap', 'historical_non_current_authority_may_fill_values', 'semantic_inference_may_fill_values', 'current_specification_mutated', 'stage01_source_mutated', 'stage02_product_output_mutated'):
        if safety.get(key) is not False:
            die(f'R11_SAFETY_FLAG_DRIFT:{key}')

    if r11.get('stage02_status') != 'BLOCKED' or r11.get('stage03_allowed') is not False or r11.get('website_construction_allowed') is not False or r11.get('deployment_allowed') is not False:
        die('R11_STAGE_BOUNDARY_FALSE_CLOSURE')

    print('PASS: R11 validates exact 150/150 R10 blocker identities with no omissions or duplicates')
    print('PASS: active v2.1.14 zero-authority-gap precondition blocks auto-completion for all 150')
    print('PASS: necessity scoring cannot override Product Authority; no materialization or blocker reduction is credited')


if __name__ == '__main__':
    main()
