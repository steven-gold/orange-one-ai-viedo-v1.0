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
CONTRACT_ROOT = RUN / '04_PAGE_FUNCTIONAL_CONTRACT'
EVIDENCE = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
PROBLEM_REGISTER = CONTRACT_ROOT / 'CURRENT_PROBLEM_REGISTER.yaml'
DENOMINATOR = CONTRACT_ROOT / 'DENOMINATOR_SNAPSHOT.yaml'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
REGISTRY = ROOT / 'governance/specifications/REGISTRY.yaml'
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
        obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception as exc:
        die(f'YAML_PARSE:{path.relative_to(ROOT)}:{exc!r}')
    if not isinstance(obj, dict):
        die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj


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


def evidence_gap_rows(evidence: dict):
    rows = []
    for page_uid in sorted(PAGES):
        scan = (((evidence.get('pages') or {}).get(page_uid) or {}).get('functional_chain_fresh_scan') or {})
        gaps = scan.get('gaps') or []
        if int(scan.get('gap_count') or 0) != len(gaps):
            die(f'PAGE_GAP_COUNT_DRIFT:{page_uid}')
        for gap in gaps:
            rows.append((page_uid, gap.get('uid'), gap.get('category'), gap.get('class'), gap.get('detail'), gap.get('gap_owner')))
    return rows


def problem_rows(problem: dict):
    rows = []
    for item in problem.get('problems') or []:
        rows.append((item.get('page_uid'), item.get('target_uid'), item.get('category'), item.get('gap_class'), item.get('detail'), item.get('gap_owner')))
    return rows


if subprocess.run([sys.executable, str(MATERIAL_VALIDATOR)], cwd=str(ROOT), text=True).returncode != 0:
    die('MATERIALIZED_STAGE02_STRUCTURAL_ROOT_INVALID')
if not EVIDENCE.is_file():
    die('CURRENT_STAGE02_EVIDENCE_MISSING')
evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
state = load_yaml(STATE)
registry = load_yaml(REGISTRY)
problem = load_yaml(PROBLEM_REGISTER)
denominator = load_yaml(DENOMINATOR)
active = state.get('stage02_active_attempt') or {}
current_governance_uid = (registry.get('active_specification') or {}).get('governance_uid')
attempt_uid = active.get('attempt_uid')

if evidence.get('result') != 'BLOCKED':
    die(f'CURRENT_STAGE02_RESULT_NOT_BLOCKED:{evidence.get("result")!r}')
if evidence.get('closure_blocker_total') != 0:
    die(f'CLASSIFIER_REQUIRES_STRUCTURAL_BLOCKERS_ZERO:{evidence.get("closure_blocker_total")!r}')
if evidence.get('prior_stage2_results_used') is not False or evidence.get('prior_stage2_counts_used_as_scan_input') is not False:
    die('CURRENT_EVIDENCE_NOT_FRESH')
if not current_governance_uid or state.get('specification_uid') != current_governance_uid:
    die('CURRENT_GOVERNANCE_UID_DRIFT')
if active.get('frozen_governance_uid') != current_governance_uid or evidence.get('frozen_governance_uid') != current_governance_uid:
    die('CURRENT_EVIDENCE_GOVERNANCE_UID_DRIFT')
if not attempt_uid or evidence.get('attempt_uid') != attempt_uid:
    die('CURRENT_ATTEMPT_UID_DRIFT')

current_denominator = int(evidence.get('fresh_functional_gap_total') or 0)
if current_denominator <= 0:
    die(f'CURRENT_FRESH_FUNCTIONAL_DENOMINATOR_INVALID:{current_denominator}')
if problem.get('current_governance_uid') != current_governance_uid or problem.get('attempt_uid') != attempt_uid:
    die('CURRENT_PROBLEM_REGISTER_IDENTITY_DRIFT')
if denominator.get('current_governance_uid') != current_governance_uid or denominator.get('attempt_uid') != attempt_uid:
    die('CURRENT_DENOMINATOR_SNAPSHOT_IDENTITY_DRIFT')
if int(problem.get('fresh_physical_problem_count') or 0) != current_denominator:
    die('CURRENT_PROBLEM_REGISTER_DENOMINATOR_DRIFT')
if int(problem.get('open_problem_count') or 0) != current_denominator or int(problem.get('resolved_problem_count') or 0) != 0:
    die('CURRENT_PROBLEM_REGISTER_OPEN_RESOLVED_DRIFT')
if len(problem.get('problems') or []) != current_denominator:
    die('CURRENT_PROBLEM_REGISTER_ROW_COUNT_DRIFT')
if int(denominator.get('fresh_functional_gap_total') or 0) != current_denominator:
    die('CURRENT_DENOMINATOR_SNAPSHOT_COUNT_DRIFT')
if denominator.get('hardcoded_or_historical_denominator_used') is not False:
    die('CURRENT_DENOMINATOR_SNAPSHOT_MUST_BE_PHYSICAL')

evidence_rows = evidence_gap_rows(evidence)
if len(evidence_rows) != current_denominator:
    die(f'CURRENT_EVIDENCE_ROW_COUNT_DRIFT:{len(evidence_rows)}:{current_denominator}')
if sorted(evidence_rows, key=lambda x: tuple(str(v) for v in x)) != sorted(problem_rows(problem), key=lambda x: tuple(str(v) for v in x)):
    die('CURRENT_PROBLEM_REGISTER_NOT_EXACT_EVIDENCE_PROJECTION')

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

if len(records) != current_denominator:
    die(f'CLASSIFIED_GAP_DENOMINATOR_DRIFT:{len(records)}:{current_denominator}')
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
    'schema_version': 2,
    'artifact_type': 'STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'cycle': 'R2_CLASSIFICATION',
    'source_head_sha': head,
    'current_governance_uid': current_governance_uid,
    'attempt_uid': attempt_uid,
    'current_fresh_evidence_ref': 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json',
    'current_problem_register_ref': '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/CURRENT_PROBLEM_REGISTER.yaml',
    'denominator_snapshot_ref': '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/DENOMINATOR_SNAPSHOT.yaml',
    'fresh_functional_gap_denominator': current_denominator,
    'closure_blocker_denominator': 0,
    'denominator_source': 'CURRENT_PHYSICAL_EVIDENCE_PROBLEM_REGISTER_AND_DENOMINATOR_SNAPSHOT_EXACT_AGREEMENT',
    'hardcoded_historical_denominator_used': False,
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
print(f'STAGE02_REMEDIABILITY_TOTAL={current_denominator}')
for key in ('BOUNDED_COMPLETION_ADMISSIBLE', 'EXACT_EXTERNAL_AUTHORITY_REQUIRED', 'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS'):
    print(f'{key}={summary.get(key, 0)}')
print('PASS: every current fresh Stage-02 functional gap classified with exact UID and bounded-completion disposition')
print('PASS: classifier denominator is derived from exact agreement of fresh evidence, Current Problem Register, and Denominator Snapshot')
print('PASS: Stage-02 product output was not used to self-authorize completion')
