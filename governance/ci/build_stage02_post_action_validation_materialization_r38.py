#!/usr/bin/env python3
from __future__ import annotations

import ast
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
R37 = ROOT / 'governance/test/stage02/STAGE02_POST_ACTION_VALIDATION_CANDIDATE_AUTHORING_R37.yaml'
R35 = ROOT / 'governance/test/stage02/STAGE02_INDEPENDENT_DENOMINATOR_RECOMPUTATION_R35.yaml'
SCANNER = ROOT / 'governance/ci/run_current_stage2_actual_test.py'
ASSET_LEDGER = RUN / '04_PAGE_FUNCTIONAL_CONTRACT/ASSET-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml'
CORE_LEDGER = RUN / '04_PAGE_FUNCTIONAL_CONTRACT/CORE-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml'
GAP006 = RUN / '04_PAGE_FUNCTIONAL_CONTRACT/SHARED_OWNER_PORT_MAP_R3.yaml'
OUT = ROOT / 'governance/test/stage02/STAGE02_POST_ACTION_VALIDATION_MATERIALIZATION_R38.yaml'
RAW = {
    'CORE-01': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
    'ASSET-01': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
}
DETAIL = 'no explicit success/validation/evaluation contract'
GAP006_DETAIL = 'GAP-006: ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY'
R37_REF = 'governance/test/stage02/STAGE02_POST_ACTION_VALIDATION_CANDIDATE_AUTHORING_R37.yaml'


def die(msg: str) -> None:
    print(f'BLOCK: {msg}', file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path):
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    obj = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(obj, dict):
        die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj


def head() -> str:
    return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()


def scanner_fn():
    tree = ast.parse(SCANNER.read_text(encoding='utf-8'), filename=str(SCANNER))
    keep = {'idx', 'present', 'event_token', 'has_transition', 'add', 'fresh_scan'}
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and 'KNOWN_AUTHORITIES' in {t.id for t in node.targets if isinstance(t, ast.Name)}:
            selected.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in keep:
            selected.append(node)
    found = {n.name for n in selected if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if found != keep:
        die(f'SCANNER_EXTRACTION_DRIFT:{sorted(found)}')
    mod = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(mod)
    ns = {'Counter': Counter, 'defaultdict': defaultdict, 're': re}
    exec(compile(mod, str(SCANNER), 'exec'), ns, ns)
    return ns['fresh_scan']


def sig(page: str, gap: dict):
    return (page, gap.get('category'), str(gap.get('uid')), gap.get('detail'))


def defect_sig(page: str, rem: dict):
    ds = rem.get('defect_signature') or {}
    return (page, ds.get('category'), str(ds.get('uid')), ds.get('detail'))


r37 = load_yaml(R37)
r35 = load_yaml(R35)
ledger = load_yaml(ASSET_LEDGER)
if ledger.get('artifact_type') != 'AUTO_COMPLETION_SCOPE_LEDGER' or ledger.get('page_uid') != 'ASSET-01':
    die('ASSET_LEDGER_IDENTITY_DRIFT')
if ledger.get('materialized_remediation_count') != len(ledger.get('remediations') or []):
    die('ASSET_LEDGER_SELF_COUNT_DRIFT')
if len(ledger.get('remediations') or []) != 12:
    die(f'R38_EXPECTED_PREEXISTING_ASSET_REMEDIATIONS_12:{len(ledger.get("remediations") or [])}')

candidates = [x for x in (r37.get('records') or []) if x.get('classification') == 'UNIQUE_ROLE_SAFE_VALIDATION_CANDIDATE']
if len(candidates) != int((r37.get('denominators') or {}).get('candidate_count', -1)) or len(candidates) != 15:
    die(f'R38_R37_CANDIDATE_DENOMINATOR:{len(candidates)}')
if any(x.get('scope') != 'ASSET-01' for x in candidates):
    die('R38_NON_ASSET_CANDIDATE_PRESENT')

existing = {defect_sig('ASSET-01', rem): rem for rem in ledger.get('remediations') or []}
if len(existing) != len(ledger.get('remediations') or []):
    die('R38_PREEXISTING_DUPLICATE_SIGNATURE')
new_rows = []
for rec in sorted(candidates, key=lambda x: str(x.get('action_uid'))):
    action_uid = str(rec.get('action_uid'))
    blocker_uid = rec.get('blocker_uid')
    candidate = rec.get('candidate') or {}
    if candidate.get('derivation') != 'MECHANICAL_WRAPPER_AROUND_ONE_EXACT_FROZEN_SIGNAL_NO_NEW_BUSINESS_VALUE':
        die(f'R38_CANDIDATE_DERIVATION_DRIFT:{action_uid}')
    signature = ('ASSET-01', 'POST_ACTION_VALIDATION_NODE_MISSING', action_uid, DETAIL)
    if signature in existing:
        die(f'R38_SIGNATURE_ALREADY_MATERIALIZED:{signature}')
    signal_key = candidate.get('signal_key')
    expected_signal = candidate.get('expected_signal')
    if signal_key in (None, '') or expected_signal in (None, ''):
        die(f'R38_CANDIDATE_SIGNAL_MISSING:{action_uid}')
    row = {
        'remediation_uid': f'R38::ASSET-01::POST_ACTION_VALIDATION_NODE_MISSING::{action_uid}::{DETAIL}',
        'defect_signature': {
            'category': 'POST_ACTION_VALIDATION_NODE_MISSING',
            'uid': action_uid,
            'detail': DETAIL,
        },
        'owning_layer': 'STAGE-02_PAGE_FUNCTIONAL_CONTRACT',
        'registered_seed_authority': '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
        'source_candidate_authoring_ref': R37_REF,
        'source_blocker_uid': blocker_uid,
        'completion_basis': 'DETERMINISTIC_EXACT_FROZEN_SUCCESS_SIGNAL_VALIDATION_WRAPPER',
        'exact_proof': {
            'proof_kind': 'DETERMINISTIC_EXACT_FROZEN_SUCCESS_SIGNAL_VALIDATION_WRAPPER',
            'action_uid': action_uid,
            'source_port_uid': rec.get('port_uid'),
            'operation_id': rec.get('operation_id'),
            'method_effective_path': rec.get('method_effective_path'),
            'signal_key': signal_key,
            'expected_signal': expected_signal,
            'bounded_output': 'WRAP_ONE_EXACT_FROZEN_SUCCESS_SIGNAL_AS_FAIL_CLOSED_POST_ACTION_ASSERTION_ONLY',
        },
        'materialized_closure': {
            'closure_type': 'POST_ACTION_VALIDATION_CONTRACT',
            'action_uid': action_uid,
            'validation_contract': {
                'validation_contract_type': candidate.get('validation_contract_type'),
                'signal_key': signal_key,
                'expected_signal': expected_signal,
                'assertion': candidate.get('assertion'),
                'timing_boundary': candidate.get('timing_boundary'),
                'failure_behavior': candidate.get('failure_behavior'),
                'derivation': candidate.get('derivation'),
            },
        },
        'semantic_inference_used': False,
        'ai_invented_business_value': False,
        'precondition_promoted_to_postcondition': False,
        'external_authority_resolution_performed': False,
    }
    new_rows.append(row)
    existing[signature] = row

ledger['remediations'] = list(ledger.get('remediations') or []) + new_rows
ledger['materialized_remediation_count'] = len(ledger['remediations'])
ledger.setdefault('source_candidate_authoring_refs', [])
if R37_REF not in ledger['source_candidate_authoring_refs']:
    ledger['source_candidate_authoring_refs'].append(R37_REF)
ledger['latest_bounded_completion_cycle'] = 'R38_POST_ACTION_VALIDATION_EXACT_SIGNAL_WRAPPER_MATERIALIZATION'
ASSET_LEDGER.write_text(yaml.safe_dump(ledger, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')

# Fresh physical scan from immutable Raw using the canonical scanner function.
scan = scanner_fn()
raw_gaps = {}
raw_categories = Counter()
for page, path in RAW.items():
    result = scan(page, load_yaml(path))
    raw_gaps[page] = result.get('gaps') or []
    raw_categories.update(g.get('category') for g in raw_gaps[page])
raw_signatures = {sig(page, gap) for page, gaps in raw_gaps.items() for gap in gaps}
if len(raw_signatures) != sum(len(v) for v in raw_gaps.values()):
    die('R38_RAW_SIGNATURE_DUPLICATION')

# Validate and apply all legal product successor signatures from both page ledgers.
product_signatures = {}
for page, path in {'CORE-01': CORE_LEDGER, 'ASSET-01': ASSET_LEDGER}.items():
    l = load_yaml(path)
    if l.get('page_uid') != page or l.get('materialized_remediation_count') != len(l.get('remediations') or []):
        die(f'R38_PRODUCT_LEDGER_DRIFT:{page}')
    for rem in l.get('remediations') or []:
        key = defect_sig(page, rem)
        if key in product_signatures:
            die(f'R38_DUPLICATE_PRODUCT_SIGNATURE:{key}')
        if key not in raw_signatures:
            die(f'R38_PRODUCT_SIGNATURE_NOT_IN_FRESH_RAW:{key}')
        product_signatures[key] = rem.get('remediation_uid')

# Apply exact GAP-006 external authority resolutions.
gap006 = load_yaml(GAP006)
external_signatures = {}
for row in gap006.get('consumers') or []:
    key = ('ASSET-01', 'SHARED_OWNER_AUTHORITY_UNRESOLVED', str(row.get('action_uid')), GAP006_DETAIL)
    if key in external_signatures:
        die(f'R38_DUPLICATE_GAP006_SIGNATURE:{key}')
    if key not in raw_signatures:
        die(f'R38_GAP006_SIGNATURE_NOT_IN_FRESH_RAW:{key}')
    external_signatures[key] = 'GAP-006'
if set(product_signatures) & set(external_signatures):
    die('R38_PRODUCT_EXTERNAL_ELIMINATION_OVERLAP')

remaining = []
for page, gaps in raw_gaps.items():
    for gap in gaps:
        key = sig(page, gap)
        if key in product_signatures or key in external_signatures:
            continue
        remaining.append({'page_uid': page, **gap})
effective_categories = Counter(x.get('category') for x in remaining)

new_signatures = {
    ('ASSET-01', 'POST_ACTION_VALIDATION_NODE_MISSING', str(x.get('action_uid')), DETAIL)
    for x in candidates
}
if len(new_signatures) != 15:
    die('R38_NEW_SIGNATURE_DENOMINATOR_DRIFT')
if not new_signatures <= raw_signatures:
    die(f'R38_NEW_SIGNATURE_NOT_ALL_IN_RAW:{sorted(new_signatures - raw_signatures)}')
if not new_signatures <= set(product_signatures):
    die(f'R38_NEW_SIGNATURE_NOT_ALL_MATERIALIZED:{sorted(new_signatures - set(product_signatures))}')
remaining_signatures = {sig(x['page_uid'], x) for x in remaining}
if new_signatures & remaining_signatures:
    die(f'R38_NEW_SIGNATURE_SURVIVED_EFFECTIVE_RECONCILIATION:{sorted(new_signatures & remaining_signatures)}')

prior_effective = int(r35.get('effective_gap_total', -1))
expected_effective = prior_effective - len(new_signatures)
if len(remaining) != expected_effective:
    die(f'R38_EFFECTIVE_DELTA_NOT_EXACTLY_NEW_MATERIALIZATIONS:{len(remaining)}:{expected_effective}')
prior_post = int((r35.get('effective_gap_categories') or {}).get('POST_ACTION_VALIDATION_NODE_MISSING', -1))
if effective_categories.get('POST_ACTION_VALIDATION_NODE_MISSING', 0) != prior_post - len(new_signatures):
    die('R38_POST_ACTION_EFFECTIVE_DELTA_DRIFT')

out = {
    'schema_version': 1,
    'artifact_uid': 'STAGE02-POST-ACTION-VALIDATION-MATERIALIZATION-R38',
    'artifact_type': 'NON_NORMATIVE_STAGE02_MATERIAL_REMEDIATION_EVIDENCE',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'source_head_sha': head(),
    'owning_layer_mutated': '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/ASSET-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml',
    'candidate_source_ref': R37_REF,
    'materialization_contract': {
        'candidate_count': len(candidates),
        'new_materialization_count': len(new_rows),
        'closure_type': 'POST_ACTION_VALIDATION_CONTRACT',
        'exact_signal_value_preserved': True,
        'new_business_value_introduced': False,
        'precondition_promoted_to_postcondition': False,
        'semantic_similarity_used': False,
        'raw_source_mutated': False,
        'current_specification_mutated': False,
    },
    'fresh_physical_reexecution': {
        'canonical_scanner_ref': str(SCANNER.relative_to(ROOT)),
        'raw_gap_total': len(raw_signatures),
        'raw_gap_categories': dict(sorted(raw_categories.items())),
        'validated_product_successor_signature_count': len(product_signatures),
        'validated_gap006_signature_count': len(external_signatures),
        'effective_gap_total': len(remaining),
        'effective_gap_categories': dict(sorted(effective_categories.items())),
        'new_r38_signatures_present_in_raw_count': len(new_signatures & raw_signatures),
        'new_r38_signatures_eliminated_from_effective_count': len(new_signatures - remaining_signatures),
        'new_r38_signatures_remaining_effective_count': len(new_signatures & remaining_signatures),
    },
    'baseline_comparison': {
        'prior_effective_gap_total_r35': prior_effective,
        'current_effective_gap_total': len(remaining),
        'proven_blocker_reduction_this_cycle': prior_effective - len(remaining),
        'prior_post_action_validation_gap_total': prior_post,
        'current_post_action_validation_gap_total': effective_categories.get('POST_ACTION_VALIDATION_NODE_MISSING', 0),
    },
    'materialized_actions': [
        {
            'action_uid': x.get('action_uid'),
            'blocker_uid': x.get('blocker_uid'),
            'signal_key': (x.get('candidate') or {}).get('signal_key'),
            'expected_signal': (x.get('candidate') or {}).get('expected_signal'),
        }
        for x in sorted(candidates, key=lambda x: str(x.get('action_uid')))
    ],
    'stage02_status': 'BLOCKED' if remaining else 'PASS',
    'stage03_allowed': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
    'next_execution_gate': 'REBUILD_CURRENT_PROBLEM_REGISTER_AND_OWNING_LAYER_INPUT_PACKET_FROM_R38_EFFECTIVE_DENOMINATOR',
}
OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')
print(f"PASS: R38 materialized {len(new_rows)} validation contracts in existing ASSET owner")
print(f"PASS: fresh raw={len(raw_signatures)} product_successors={len(product_signatures)} GAP006={len(external_signatures)} effective={len(remaining)}")
print(f"PASS: post-action validation effective={effective_categories.get('POST_ACTION_VALIDATION_NODE_MISSING', 0)}; proven reduction={prior_effective-len(remaining)}")
