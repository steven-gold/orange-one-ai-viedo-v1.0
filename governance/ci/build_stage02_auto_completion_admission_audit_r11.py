#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R10 = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_AUTHORITY_APPROVAL_DOCKET_R10.yaml'
ACTIVE_ROOT = ROOT / '.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'
ACTIVE_INVARIANTS = ROOT / '.github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'
OUT = ROOT / 'governance/test/stage02/STAGE02_AUTO_COMPLETION_ADMISSION_AUDIT_R11.yaml'


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
    manifest = load(ACTIVE_ROOT)
    invariants = load(ACTIVE_INVARIANTS)

    revision = manifest.get('governance_revision')
    if not isinstance(revision, str) or not revision.startswith('v2.1.14'):
        die(f'R11_REQUIRES_V2_1_14_ACTIVE_GOVERNANCE:{revision}')

    fa = invariants.get('invariants', invariants).get('FUNCTION_ADMISSION_NECESSITY_AND_UTILITY')
    if not isinstance(fa, dict):
        die('R11_FUNCTION_ADMISSION_INVARIANT_MISSING')
    auto = (fa.get('decision_classes') or {}).get('REQUIRED_AUTO_COMPLETION_ELIGIBLE') or {}
    if fa.get('required_for_every_auto_or_ai_proposed_functional_addition') is not True:
        die('R11_FUNCTION_ADMISSION_NOT_REQUIRED_FOR_AI_AUTO_ADDITION')
    if auto.get('requires_zero_authority_gap') is not True:
        die('R11_ZERO_AUTHORITY_GAP_PRECONDITION_MISSING')
    if fa.get('score_may_override_authority_gap') is not False:
        die('R11_SCORE_CAN_OVERRIDE_AUTHORITY_GAP')

    den = r10.get('denominators') or {}
    records = r10.get('records') or []
    if den.get('total_product_authority_decisions') != 150 or len(records) != 150:
        die(f'R11_R10_DENOMINATOR_DRIFT:{den.get("total_product_authority_decisions")}:{len(records)}')

    out_records = []
    scope_counts = Counter()
    category_counts = Counter()
    for rec in records:
        uid = rec.get('blocker_uid')
        if rec.get('approval_state') != 'PENDING_EXPLICIT_PRODUCT_AUTHORITY':
            die(f'R11_NON_PENDING_RECORD_REQUIRES_REEVALUATION:{uid}')
        decision = rec.get('authority_decision_required') or {}
        if any(v not in (None, '', [], {}) for v in decision.values()):
            die(f'R11_PARTIAL_AUTHORITY_VALUE_PRESENT_REQUIRES_REEVALUATION:{uid}')
        if rec.get('r7_materialization_allowed') is not False or rec.get('blocker_reduction_credit') != 0:
            die(f'R11_R10_FALSE_MATERIALIZATION_OR_REDUCTION:{uid}')

        scope = rec.get('scope')
        category = rec.get('category')
        scope_counts[scope] += 1
        category_counts[category] += 1
        out_records.append({
            'blocker_uid': uid,
            'scope': scope,
            'category': category,
            'target_uid': rec.get('target_uid'),
            'missing_field_or_relation': rec.get('missing_field_or_relation'),
            'verified_review_ref': rec.get('verified_review_ref'),
            'authority_gap_present': True,
            'authority_gap_zero': False,
            'necessity_score': None,
            'score_disposition': 'NOT_SCORED_AUTHORITY_GAP_PRECEDENCE',
            'auto_completion_decision': 'BLOCK_AUTO_COMPLETION_AUTHORITY_GAP',
            'auto_completion_eligible': False,
            'bounded_completion_seed_evaluation': 'NOT_REACHED_AUTHORITY_GAP_PRECONDITION_FAILED',
            'minimal_closure_expansion_allowed': False,
            'product_scope_expansion_allowed': False,
            'authority_value_supplied_by_ai': False,
            'r7_materialization_allowed': False,
            'blocker_reduction_credit': 0,
            'next_legal_action': 'EXPLICIT_PRODUCT_AUTHORITY_DECISION_THEN_R7_INGESTION',
        })

    expected_categories = den.get('category_counts') or {}
    if dict(category_counts) != expected_categories:
        die(f'R11_CATEGORY_DENOMINATOR_DRIFT:{dict(category_counts)}:{expected_categories}')
    if dict(scope_counts) != {'ASSET-01': 110, 'CORE-01': 40}:
        die(f'R11_SCOPE_DENOMINATOR_DRIFT:{dict(scope_counts)}')

    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    doc = {
        'schema_version': 1,
        'artifact_type': 'NON_NORMATIVE_STAGE02_AUTO_COMPLETION_ADMISSION_AUDIT_R11',
        'normative_authority': False,
        'stage_uid': 'STAGE-02',
        'cycle': 'AUTO_COMPLETION_ADMISSION_AUDIT_R11',
        'source_head_sha': head,
        'active_governance_revision': revision,
        'source_contracts': {
            'product_authority_docket_r10': str(R10.relative_to(ROOT)),
            'active_governance_root_manifest': str(ACTIVE_ROOT.relative_to(ROOT)),
            'active_stage_execution_invariants': str(ACTIVE_INVARIANTS.relative_to(ROOT)),
            'r7_ingestion_validator': 'governance/ci/validate_stage02_approved_product_authority_r7.py',
        },
        'governing_rule': {
            'function_admission_required_for_auto_or_ai_proposed_addition': True,
            'required_auto_completion_eligible_requires_zero_authority_gap': True,
            'score_may_override_authority_gap': False,
            'bounded_completion_may_expand_product_scope': False,
        },
        'purpose': 'PROVE_THE_150_OPEN_STAGE02_PRODUCT_AUTHORITY_DECISIONS_ARE_NOT_LEGAL_AUTO_COMPLETION_TARGETS_UNDER_ACTIVE_V2_1_14_GOVERNANCE',
        'status': 'AUTO_COMPLETION_BLOCKED_FOR_ALL_150_PENDING_EXPLICIT_PRODUCT_AUTHORITY',
        'denominators': {
            'r10_product_authority_decisions': 150,
            'auto_completion_eligible': 0,
            'blocked_by_authority_gap': 150,
            'not_scored_due_authority_gap_precedence': 150,
            'r7_materializable': 0,
            'effective_stage02_blocker_reduction_claimed': 0,
            'scope_counts': dict(scope_counts),
            'category_counts': dict(category_counts),
        },
        'safety': {
            'audit_is_product_authority': False,
            'audit_is_approval_evidence': False,
            'audit_may_fill_product_values': False,
            'necessity_score_may_be_used_to_override_authority_gap': False,
            'historical_non_current_authority_may_fill_values': False,
            'semantic_inference_may_fill_values': False,
            'current_specification_mutated': False,
            'stage01_source_mutated': False,
            'stage02_product_output_mutated': False,
        },
        'records': out_records,
        'stage02_status': 'BLOCKED',
        'stage03_allowed': False,
        'website_construction_allowed': False,
        'deployment_allowed': False,
        'formal_next_execution_point': 'EXPLICIT_PRODUCT_AUTHORITY_DECISION_FOR_R10_RECORDS_THEN_R7_VALIDATE_AND_MATERIALIZE',
    }
    OUT.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')
    print(f'PASS: R11 auto-completion admission audit built records={len(out_records)}')
    print('PASS: 150/150 are blocked from auto-completion because active governance requires zero authority gap')
    print('PASS: no necessity score was used to override Product Authority and blocker reduction remains zero')


if __name__ == '__main__':
    main()
