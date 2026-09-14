#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import argparse
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_stage02_approved_product_authority_r7 import validate, repo_path  # noqa: E402

STAGE2 = ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
DEFAULT_APPROVED = ROOT / 'governance/test/stage02/STAGE02_APPROVED_PRODUCT_AUTHORITY_BINDINGS_R7.yaml'
RECEIPT = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_AUTHORITY_MATERIALIZATION_R7_RECEIPT.yaml'
ALLOWED_PAGES = {'CORE-01', 'ASSET-01'}


def die(msg: str) -> None:
    print(f'BLOCK: {msg}', file=sys.stderr)
    raise SystemExit(1)


def load(path: Path):
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def dump(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')


def head_sha() -> str:
    return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('approved_input', nargs='?', default=str(DEFAULT_APPROVED.relative_to(ROOT)))
    args = ap.parse_args()
    approved_rel, approved_path = repo_path(args.approved_input, 'approved_input')

    # Critical ordering invariant: perform full validation before any owning-layer write.
    approved, records = validate(approved_path)

    by_page: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        page = rec.get('scope')
        if page not in ALLOWED_PAGES:
            die(f'R7_UNSUPPORTED_SCOPE:{page}')
        inp = rec['authority_input']
        by_page[page].append({
            'remediation_uid': f"R7::{rec['blocker_uid']}",
            'blocker_uid': rec['blocker_uid'],
            'defect_signature': {
                'category': rec['category'],
                'uid': rec['target_uid'],
                'detail': rec['missing_field_or_relation'],
            },
            'owning_layer': 'STAGE-02_PAGE_FUNCTIONAL_CONTRACT',
            'required_authority_kind': rec['required_authority_kind'],
            'canonical_owner_uid': inp['canonical_owner_uid'],
            'canonical_owner_file': inp['canonical_owner_file'],
            'authority_revision': inp['authority_revision'],
            'authority_source_path': inp['authority_source_path'],
            'authority_content_sha256': inp['authority_content_sha256'],
            'materialized_closure': inp['exact_binding'],
            'approval': {
                'approved_by': inp['approved_by'],
                'approved_at': inp['approved_at'],
                'approval_evidence_ref': inp['approval_evidence_ref'],
            },
            'semantic_inference_used': False,
            'ai_invented_business_value': False,
            'historical_non_current_authority_used': False,
        })

    changed = []
    for page, new_rows in sorted(by_page.items()):
        ledger_path = STAGE2 / page / 'PRODUCT_AUTHORITY_MATERIALIZATION_LEDGER_R7.yaml'
        existing_rows = []
        if ledger_path.is_file():
            prior = load(ledger_path)
            if prior.get('artifact_type') != 'PRODUCT_AUTHORITY_MATERIALIZATION_LEDGER_R7':
                die(f'R7_EXISTING_LEDGER_TYPE_DRIFT:{page}')
            existing_rows = prior.get('remediations') or []

        merged = {row.get('blocker_uid'): row for row in existing_rows}
        if None in merged:
            die(f'R7_EXISTING_LEDGER_MISSING_BLOCKER_UID:{page}')
        for row in new_rows:
            uid = row['blocker_uid']
            if uid in merged and merged[uid] != row:
                die(f'R7_EXISTING_REMEDIATION_CONFLICT:{uid}')
            merged[uid] = row

        ledger = {
            'schema_version': 1,
            'artifact_type': 'PRODUCT_AUTHORITY_MATERIALIZATION_LEDGER_R7',
            'normative_authority': False,
            'stage_uid': 'STAGE-02',
            'page_uid': page,
            'source_approved_binding_set': approved_rel,
            'materialized_remediation_count': len(merged),
            'remediations': [merged[k] for k in sorted(merged)],
            'fresh_reexecution_required_before_blocker_reduction_claim': True,
            'stage_exit_claimed': False,
        }
        dump(ledger_path, ledger)
        changed.append(str(ledger_path.relative_to(ROOT)))

        package_path = STAGE2 / page / 'PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml'
        package = load(package_path)
        included = package.setdefault('included_artifacts', [])
        name = 'PRODUCT_AUTHORITY_MATERIALIZATION_LEDGER_R7.yaml'
        if name not in included:
            included.append(name)
        package['stage_exit_claimed'] = False
        dump(package_path, package)
        changed.append(str(package_path.relative_to(ROOT)))

    total = len(records)
    receipt = {
        'schema_version': 1,
        'artifact_type': 'PRODUCT_AUTHORITY_MATERIAL_REMEDIATION_RECEIPT_R7',
        'normative_authority': False,
        'stage_uid': 'STAGE-02',
        'cycle': 'PRODUCT_DESIGN_AUTHORITY_MATERIALIZATION_R7',
        'source_head_sha': head_sha(),
        'source_approved_binding_set': approved_rel,
        'owning_layer': 'CURRENT_STAGE_PRODUCT_OR_CONTRACT_OUTPUT',
        'materialized_now': {
            'total': total,
            'CORE-01': len(by_page.get('CORE-01', [])),
            'ASSET-01': len(by_page.get('ASSET-01', [])),
        },
        'changed_artifacts': changed,
        'before_effective_stage02_blockers': 150,
        'after_state_claim_before_fresh_reexecution': 'NOT_CLAIMED',
        'expected_remaining_only_if_fresh_reexecution_accepts_all_materialized_signatures': 150 - total,
        'current_specification_mutated': False,
        'immutable_stage1_source_mutated': False,
        'ai_invented_business_value': False,
        'fresh_reexecution_required': True,
        'stage03_allowed': False,
        'website_construction_allowed': False,
        'deployment_allowed': False,
    }
    dump(RECEIPT, receipt)
    print(f'PASS: R7 materially wrote approved authority-backed closures total={total}')
    print('PASS: no blocker reduction is claimed before fresh Stage-02 reexecution')
    print('PASS: Current Specification and immutable Stage-01 Raw Source are not mutation targets')


if __name__ == '__main__':
    main()
