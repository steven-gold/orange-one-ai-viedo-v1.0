#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
EVIDENCE = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
OUT = ROOT / 'governance/test/stage02/STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION_R2.yaml'
MATERIAL_VALIDATOR = ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py'

PAGES = {
    'CORE-01': {
        'raw': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
        'blueprint': RUN / '02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml',
        'binding_dir': RUN / '03_BLUEPRINT_BINDING/CORE-01',
    },
    'ASSET-01': {
        'raw': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
        'blueprint': RUN / '02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml',
        'binding_dir': RUN / '03_BLUEPRINT_BINDING/ASSET-01',
    },
}
SHARED_INPUTS = [
    RUN / '00_SOURCE_INTAKE/SOURCE_CONTEXT_MANIFEST.yaml',
    RUN / '00_SOURCE_INTAKE/CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml',
    RUN / '00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml',
]
EXTERNAL_AUTHORITY_GAPS = {'SHARED_OWNER_AUTHORITY_UNRESOLVED'}
CANDIDATE_KEYS = {
    'PAYLOAD_INPUT_CONTRACT_MISSING': {'payload', 'payload_rule', 'payload_mode', 'input_contract', 'request_contract', 'request_schema'},
    'AUDIT_EVENT_NODE_MISSING': {'audit_event_uid', 'event_uid', 'state_event'},
    'FAILURE_STATE_ERROR_BINDING_MISSING': {'error_uid', 'failure_state', 'recovery'},
    'POST_ACTION_VALIDATION_NODE_MISSING': {'success_contract', 'validation_contract', 'validator_uid', 'validation', 'validation_rule', 'evaluation_rule'},
    'ACTION_WITHOUT_CONTROL_OR_TRIGGER': {'trigger_event_uid', 'trigger_uid', 'invocation', 'system_trigger', 'trigger_kind', 'action_uid'},
    'SUCCESS_NEXT_STATE_BINDING_MISSING': {'state_effect', 'from_stage', 'to_stage', 'state_event', 'action_uid'},
}


def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path):
    if not path.is_file():
        die(f'MISSING_INPUT:{path.relative_to(ROOT)}')
    try:
        return yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception as exc:
        die(f'YAML_PARSE:{path.relative_to(ROOT)}:{exc!r}')


def scalar_equal(value, uid: str) -> bool:
    return isinstance(value, (str, int, float, bool)) and str(value) == uid


def node_mentions_uid(node, uid: str) -> bool:
    if isinstance(node, dict):
        return any(scalar_equal(v, uid) for v in node.values() if not isinstance(v, (dict, list)))
    return False


def walk(node, path='$'):
    yield path, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk(value, f'{path}.{key}')
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from walk(value, f'{path}[{i}]')


def nonempty(value) -> bool:
    return value not in (None, '', [], {})


def evidence_candidates(uid: str, category: str, detail: str, corpus):
    keys = set(CANDIDATE_KEYS.get(category, set()))
    if category == 'STATE_TRANSITION_LEDGER_FIELD_MISSING':
        keys = {detail}
    found = []
    for source_path, doc in corpus:
        for node_path, node in walk(doc):
            if not isinstance(node, dict) or not node_mentions_uid(node, uid):
                continue
            matched = {}
            for key in keys:
                if key in node and nonempty(node.get(key)):
                    matched[key] = node.get(key)
            if matched:
                found.append({
                    'source_ref': str(source_path.relative_to(ROOT)),
                    'node_path': node_path,
                    'matched_fields': matched,
                })
    return found


def unique_candidate_values(candidates):
    normalized = set()
    for item in candidates:
        normalized.add(json.dumps(item.get('matched_fields') or {}, ensure_ascii=False, sort_keys=True, default=str))
    return normalized


def transition_by_uid(raw: dict, uid: str):
    for item in ((raw.get('registries') or {}).get('stage_transitions') or []):
        if isinstance(item, dict) and item.get('transition_uid') == uid:
            return item
    return None


def classify_gap(gap: dict, raw: dict, corpus):
    category = gap.get('category')
    uid = str(gap.get('uid'))
    detail = str(gap.get('detail') or '')

    if category in EXTERNAL_AUTHORITY_GAPS or gap.get('gap_owner') == 'EXTERNAL_AUTHORITY':
        return {
            'disposition': 'EXACT_EXTERNAL_AUTHORITY_REQUIRED',
            'completion_basis': 'EXTERNAL_OR_SHARED_AUTHORITY',
            'candidate_evidence': [],
            'authorized_for_auto_completion': False,
        }

    # One deliberately narrow deterministic dependency is admitted: the negative-test
    # obligation for an already-authorized exact transition. The transition itself,
    # its from/to states and trigger/gate remain unchanged; only the required negative
    # test cases can be generated from those exact values.
    if category == 'STATE_TRANSITION_LEDGER_FIELD_MISSING' and detail == 'illegal_transition_tests':
        transition = transition_by_uid(raw, uid)
        if transition:
            required = ('from_stage', 'to_stage')
            if all(nonempty(transition.get(k)) for k in required) and nonempty(transition.get('trigger') or transition.get('action_uid') or transition.get('trigger_event_uid')):
                return {
                    'disposition': 'BOUNDED_COMPLETION_ADMISSIBLE',
                    'completion_basis': 'DETERMINISTIC_REQUIRED_DEPENDENCY',
                    'candidate_evidence': [{
                        'source_ref': 'RAW_SOURCE::registries.stage_transitions',
                        'transition_uid': uid,
                        'from_stage': transition.get('from_stage'),
                        'to_stage': transition.get('to_stage'),
                        'trigger': transition.get('trigger') or transition.get('action_uid') or transition.get('trigger_event_uid'),
                        'gate': transition.get('gate_uid') or transition.get('gate'),
                    }],
                    'authorized_for_auto_completion': True,
                    'bounded_output': 'GENERATE_NEGATIVE_TESTS_ONLY_NO_STATE_OR_AUTHORITY_VALUE_INVENTION',
                }

    candidates = evidence_candidates(uid, category, detail, corpus)
    unique_values = unique_candidate_values(candidates)
    if len(unique_values) == 1 and candidates:
        return {
            'disposition': 'BOUNDED_COMPLETION_ADMISSIBLE',
            'completion_basis': 'EXACT_CURRENT_AUTHORITY_BINDING',
            'candidate_evidence': candidates,
            'authorized_for_auto_completion': True,
            'bounded_output': 'COPY_EXACT_MATCHED_FIELDS_ONLY',
        }
    if len(unique_values) > 1:
        return {
            'disposition': 'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS',
            'completion_basis': 'CONFLICTING_EXACT_CANDIDATE_VALUES',
            'candidate_evidence': candidates,
            'authorized_for_auto_completion': False,
        }
    return {
        'disposition': 'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS',
        'completion_basis': 'NO_EXACT_CURRENT_AUTHORITY_OR_UNIQUE_DETERMINISTIC_DEPENDENCY',
        'candidate_evidence': [],
        'authorized_for_auto_completion': False,
    }


if subprocess.run([sys.executable, str(MATERIAL_VALIDATOR)], cwd=str(ROOT), text=True).returncode != 0:
    die('MATERIALIZED_STAGE02_STRUCTURAL_ROOT_INVALID')
if not EVIDENCE.is_file():
    die('CURRENT_STAGE02_EVIDENCE_MISSING')
evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
if evidence.get('result') != 'BLOCKED':
    die(f'CURRENT_STAGE02_RESULT_NOT_BLOCKED:{evidence.get("result")!r}')
if evidence.get('closure_blocker_total') != 0:
    die(f'CLASSIFIER_REQUIRES_STRUCTURAL_BLOCKERS_ZERO:{evidence.get("closure_blocker_total")!r}')
if evidence.get('fresh_functional_gap_total') != 171:
    die(f'CURRENT_FRESH_FUNCTIONAL_DENOMINATOR_DRIFT:{evidence.get("fresh_functional_gap_total")!r}')
if evidence.get('prior_stage2_results_used') is not False or evidence.get('prior_stage2_counts_used_as_scan_input') is not False:
    die('CURRENT_EVIDENCE_NOT_FRESH')

shared_corpus = [(p, load_yaml(p)) for p in SHARED_INPUTS]
records = []
for page_uid, cfg in PAGES.items():
    raw = load_yaml(cfg['raw'])
    corpus = [(cfg['raw'], raw), (cfg['blueprint'], load_yaml(cfg['blueprint']))] + shared_corpus
    if cfg['binding_dir'].is_dir():
        for p in sorted(cfg['binding_dir'].rglob('*.yaml')):
            corpus.append((p, load_yaml(p)))
    page_gaps = (((evidence.get('pages') or {}).get(page_uid) or {}).get('functional_chain_fresh_scan') or {}).get('gaps') or []
    for gap in page_gaps:
        rec = {
            'page_uid': page_uid,
            'class': gap.get('class'),
            'category': gap.get('category'),
            'uid': gap.get('uid'),
            'detail': gap.get('detail'),
            'gap_owner': gap.get('gap_owner'),
        }
        rec.update(classify_gap(gap, raw, corpus))
        records.append(rec)

if len(records) != 171:
    die(f'CLASSIFIED_GAP_DENOMINATOR_DRIFT:{len(records)}')
summary = Counter(r['disposition'] for r in records)
basis = Counter(r['completion_basis'] for r in records)
by_category = {}
for category in sorted({r['category'] for r in records}):
    subset = [r for r in records if r['category'] == category]
    by_category[category] = {
        'total': len(subset),
        'BOUNDED_COMPLETION_ADMISSIBLE': sum(r['disposition'] == 'BOUNDED_COMPLETION_ADMISSIBLE' for r in subset),
        'EXACT_EXTERNAL_AUTHORITY_REQUIRED': sum(r['disposition'] == 'EXACT_EXTERNAL_AUTHORITY_REQUIRED' for r in subset),
        'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS': sum(r['disposition'] == 'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS' for r in subset),
    }

head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
out = {
    'schema_version': 1,
    'artifact_type': 'STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'cycle': 'R2_CLASSIFICATION',
    'source_head_sha': head,
    'current_fresh_evidence_ref': 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json',
    'fresh_functional_gap_denominator': 171,
    'closure_blocker_denominator': 0,
    'authority_corpus_policy': {
        'official_stage2_inputs_only': True,
        'stage2_current_product_output_may_self_authorize_completion': False,
        'semantic_similarity_used': False,
        'sibling_symmetry_used': False,
        'generic_crud_expansion_used': False,
        'external_authority_auto_resolution_used': False,
    },
    'classification_summary': dict(summary),
    'completion_basis_summary': dict(basis),
    'by_category': by_category,
    'records': records,
    'next_action': 'MATERIALIZE_ONLY_BOUNDED_COMPLETION_ADMISSIBLE_RECORDS_THEN_DUAL_LAYER_REEXECUTION',
    'stage03_allowed': False,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=160), encoding='utf-8')
print('STAGE02_REMEDIABILITY_TOTAL=171')
for key in ('BOUNDED_COMPLETION_ADMISSIBLE', 'EXACT_EXTERNAL_AUTHORITY_REQUIRED', 'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS'):
    print(f'{key}={summary.get(key, 0)}')
print('PASS: every current fresh Stage-02 functional gap classified with exact UID and bounded-completion disposition')
print('PASS: Stage-02 product output was not used to self-authorize completion')
