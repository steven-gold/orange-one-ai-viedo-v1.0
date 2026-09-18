#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
PROBLEMS = BASE / 'CURRENT_PROBLEM_REGISTER.yaml'
CLASSIFICATION = ROOT / 'governance/test/stage02/STAGE02_FUNCTIONAL_REMEDIABILITY_CLASSIFICATION_R2.yaml'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
FINDINGS = ROOT / 'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
CANDIDATES = ROOT / 'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
REGISTRY = ROOT / 'governance/specifications/REGISTRY.yaml'
OUT = ROOT / 'governance/test/stage02/STAGE02_PRODUCT_DESIGN_AUTHORITY_REQUEST_R5.yaml'


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


def dump(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')


def signature(row: dict) -> tuple[str, str, str, str]:
    return (
        str(row.get('page_uid') or ''),
        str(row.get('category') or ''),
        str(row.get('uid') or row.get('target_uid') or ''),
        str(row.get('detail') or ''),
    )


def authority_requirement(category: str, detail: str) -> dict:
    table = {
        'PAYLOAD_INPUT_CONTRACT_MISSING': (
            'EXACT_PAYLOAD_OR_INPUT_SCHEMA_BINDING',
            ['explicit action payload/input/request schema OR exact runtime/port payload/input/request schema bound to the same action_uid'],
            ['operation name', 'route identity', 'port identity alone', 'semantic similarity', 'AI-inferred request fields'],
        ),
        'AUDIT_EVENT_NODE_MISSING': (
            'EXACT_REGISTERED_AUDIT_EVENT_BINDING',
            ['exact event_uid/audit_event_uid bound to the same action or exact resolved port and present in the governed event registry'],
            ['state text', 'trigger text', 'semantic event guess', 'invented event UID'],
        ),
        'FAILURE_STATE_ERROR_BINDING_MISSING': (
            'EXACT_FAILURE_ERROR_RECOVERY_BINDING',
            ['same action_uid explicitly binds failure_state + recovery OR same action_uid explicitly binds a registered error_uid whose governed error entry supplies recovery'],
            ['generic page error registry', 'nearest error by meaning', 'AI-selected recovery'],
        ),
        'POST_ACTION_VALIDATION_NODE_MISSING': (
            'EXACT_POST_ACTION_VALIDATION_BINDING',
            ['same action_uid explicitly binds success_contract/validation_contract/validator_uid OR the exact runtime/port binding supplies the exact validation relation'],
            ['operation response label', 'route response wording', 'gate similarity', 'AI-generated validator'],
        ),
        'ACTION_WITHOUT_CONTROL_OR_TRIGGER': (
            'EXACT_ACTION_ADMISSION_TRIGGER_RELATION',
            ['registered control.action_uid equals this action_uid OR exact stage-transition trigger/action_uid equals this action_uid OR the action has an explicit governed trigger identity'],
            ['neighboring control', 'label similarity', 'route identity', 'inferred system trigger'],
        ),
        'STATE_TRANSITION_LEDGER_FIELD_MISSING': (
            'EXACT_TRANSITION_FIELD_BINDING',
            [f'exact non-empty governed transition value satisfying the missing relation: {detail}'],
            ['trigger/gate/action/error/owner similarity', 'value copied from sibling transition', 'AI-inferred value'],
        ),
        'SUCCESS_NEXT_STATE_BINDING_MISSING': (
            'EXACT_SUCCESS_OR_NEXT_STATE_BINDING',
            ['same action_uid or exact governed transition explicitly binds the required success/next-state relation'],
            ['neighboring transition', 'semantic success wording', 'AI-inferred next state'],
        ),
    }
    if category not in table:
        die(f'UNSUPPORTED_LOCAL_CATEGORY:{category}')
    kind, required, forbidden = table[category]
    return {
        'required_authority_kind': kind,
        'required_exact_fields_or_relation': required,
        'not_acceptable_as_authority': forbidden,
    }


problem = load(PROBLEMS)
classification = load(CLASSIFICATION)
state = load(STATE)
findings = load(FINDINGS)
candidates = load(CANDIDATES)
registry = load(REGISTRY)

governance_uid = (registry.get('active_specification') or {}).get('governance_uid')
attempt_uid = (state.get('stage02_active_attempt') or {}).get('attempt_uid')
current_n = int(problem.get('fresh_physical_problem_count') or 0)
open_n = int(problem.get('open_problem_count') or 0)
class_n = int(classification.get('fresh_functional_gap_denominator') or 0)
if not governance_uid or problem.get('current_governance_uid') != governance_uid or classification.get('current_governance_uid') != governance_uid:
    die('CURRENT_GOVERNANCE_UID_DRIFT')
if not attempt_uid or problem.get('attempt_uid') != attempt_uid or classification.get('attempt_uid') != attempt_uid:
    die('CURRENT_ATTEMPT_UID_DRIFT')
if findings.get('frozen_governance_uid') != governance_uid or findings.get('attempt_uid') != attempt_uid:
    die('CURRENT_FINDINGS_IDENTITY_DRIFT')
if current_n <= 0 or open_n != current_n or class_n != current_n:
    die(f'CURRENT_DENOMINATOR_DRIFT:problem={current_n}:open={open_n}:classification={class_n}')
if ((state.get('execution') or {}).get('stage2') or {}).get('stage_exit_allowed') is not False:
    die('STAGE02_EXIT_MUST_REMAIN_BLOCKED')
if (state.get('resume_control') or {}).get('current_resume_point') != 'STAGE2_TESTED_BLOCKED_FUNCTIONAL_REMEDIATION':
    die('CURRENT_RESUME_POINT_DRIFT')

problems = problem.get('problems') or []
records = classification.get('records') or []
if len(problems) != current_n or len(records) != current_n:
    die(f'CURRENT_RECORD_DENOMINATOR_DRIFT:problems={len(problems)}:classification={len(records)}:expected={current_n}')
problem_by_sig = {signature(p): p for p in problems}
record_by_sig = {signature(r): r for r in records}
if len(problem_by_sig) != current_n or len(record_by_sig) != current_n:
    die('DUPLICATE_CURRENT_SIGNATURE')
if set(problem_by_sig) != set(record_by_sig):
    die(f'CURRENT_PROBLEM_CLASSIFICATION_SIGNATURE_DRIFT:missing_in_classifier={len(set(problem_by_sig)-set(record_by_sig))}:missing_in_register={len(set(record_by_sig)-set(problem_by_sig))}')

summary = Counter(r.get('disposition') for r in records)
if summary.get('BOUNDED_COMPLETION_ADMISSIBLE', 0) != 0:
    die(f'R5_AUTHORITY_REQUEST_REQUIRES_ZERO_AUTO_COMPLETION_CANDIDATES:{dict(summary)}')
local_n = int(summary.get('NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS', 0))
external_n = int(summary.get('EXACT_EXTERNAL_AUTHORITY_REQUIRED', 0))
if local_n + external_n != current_n:
    die(f'R5_CLASSIFICATION_PARTITION_DRIFT:{dict(summary)}')

local_requests = []
external_requests = []
for sig in sorted(problem_by_sig):
    p = problem_by_sig[sig]
    r = record_by_sig[sig]
    if p.get('status') != 'OPEN' or int(p.get('resolution_credit') or 0) != 0:
        die(f'R5_PROBLEM_NOT_OPEN_ZERO_CREDIT:{p.get("problem_uid")}')
    if r.get('authorized_for_auto_completion') is not False or r.get('gap_class_policy') != 'AI_AUTO_FILL_BLOCK':
        die(f'R5_CLASSIFICATION_POLICY_DRIFT:{sig}')
    common = {
        'problem_uid': p.get('problem_uid'),
        'scope': p.get('page_uid'),
        'category': p.get('category'),
        'gap_class': p.get('gap_class'),
        'gap_owner': p.get('gap_owner'),
        'target_uid': p.get('target_uid'),
        'missing_field_or_relation': p.get('detail'),
        'classification_disposition': r.get('disposition'),
        'completion_basis': r.get('completion_basis'),
        'reason': 'CURRENT_CANONICAL_PREFLIGHT_AND_POLICY_CORRECT_R2_CLASSIFIER_PROVIDE_NO_AUTHORIZED_AUTOMATIC_CLOSURE_FOR_THIS_OPEN_PROBLEM',
        'impact': 'STAGE02_REMAINS_BLOCKED; STAGE03_WEBSITE_CONSTRUCTION_AND_DEPLOYMENT_REMAIN_FAIL_CLOSED',
        'source_problem_register_ref': str(PROBLEMS.relative_to(ROOT)),
        'source_classification_ref': str(CLASSIFICATION.relative_to(ROOT)),
        'authority_value_supplied_by_ai': False,
        'request_is_authority': False,
        'blocker_reduction_credit': 0,
    }
    if r.get('disposition') == 'NO_AUTHORIZED_BOUNDED_COMPLETION_BASIS':
        if p.get('gap_owner') != 'PAGE_FUNCTIONAL_CONTRACT':
            die(f'R5_LOCAL_OWNER_DRIFT:{sig}:{p.get("gap_owner")}')
        gap_class = str(p.get('gap_class') or '')
        if gap_class in {'INPUT_SOURCE_GAP', 'ARCHITECTURE_GAP'}:
            routing = 'REVIEW_ONLY_DESIGN_CONTRACT_REMEDIATION_REQUIRED'
            unlock = 'BOUNDED_DESIGN_REMEDIATION_PACKAGE_IS_REVIEWED_AND_APPROVED_CONTENT_IS_MATERIALIZED_TO_THE_SINGLE_CURRENT_CANONICAL_PRODUCT_CONTRACT_OWNER'
        elif gap_class == 'AUTHORITY_GAP':
            routing = 'EXPLICIT_PRODUCT_AUTHORITY_SELECTION_REQUIRED'
            unlock = 'EXPLICIT_PRODUCT_AUTHORITY_SELECTS_THE_MATERIALLY_DISTINCT_PRODUCT_BEHAVIOR_AND_APPROVED_CONTENT_IS_MATERIALIZED_TO_THE_SINGLE_CURRENT_CANONICAL_PRODUCT_CONTRACT_OWNER'
        else:
            routing = 'SEPARATELY_APPROVED_PRODUCT_AUTHORITY_REQUIRED'
            unlock = 'SEPARATELY_APPROVED_CURRENT_ADMISSIBLE_PRODUCT_AUTHORITY_SUPPLIES_THE_EXACT_MISSING_BINDING_AND_VALIDATION_ACCEPTS_IT_WITHOUT_SEMANTIC_INFERENCE'
        local_requests.append({
            **common,
            'request_uid': f'R5::{p.get("problem_uid")}',
            'routing_disposition': routing,
            'authority_request': authority_requirement(str(p.get('category')), str(p.get('detail'))),
            'unlock_condition': unlock,
        })
    elif r.get('disposition') == 'EXACT_EXTERNAL_AUTHORITY_REQUIRED':
        if p.get('gap_owner') != 'EXTERNAL_AUTHORITY' or p.get('category') != 'SHARED_OWNER_AUTHORITY_UNRESOLVED':
            die(f'R5_EXTERNAL_OWNER_DRIFT:{sig}:{p.get("gap_owner")}:{p.get("category")}')
        external_requests.append({
            **common,
            'request_uid': f'R5-EXTERNAL::{p.get("problem_uid")}',
            'authority_request': {
                'required_authority_kind': 'EXACT_REFERENCED_EXTERNAL_SHARED_OWNER_AUTHORITY',
                'required_exact_fields_or_relation': ['authoritative source for GAP-006 / ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY resolving the exact target operation, or formal non-applicability authority'],
                'not_acceptable_as_authority': ['AI inference', 'same-name local operation', 'historical non-current snapshot', 'request package itself'],
            },
            'unlock_condition': 'AUTHORITATIVE_EXTERNAL_SOURCE_IS_PROVIDED_AND_EXACTLY_RESOLVES_THE_REFERENCED_SHARED_OPERATION_OR_FORMAL_NON_APPLICABILITY_IS_AUTHORIZED',
        })
    else:
        die(f'R5_UNEXPECTED_DISPOSITION:{r.get("disposition")}:{sig}')

if len(local_requests) != local_n or len(external_requests) != external_n:
    die(f'R5_REQUEST_DENOMINATOR_DRIFT:local={len(local_requests)}/{local_n}:external={len(external_requests)}/{external_n}')

head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
out = {
    'schema_version': 2,
    'artifact_uid': 'STAGE02-PRODUCT-DESIGN-AUTHORITY-REQUEST-CURRENT-R5',
    'artifact_type': 'NON_NORMATIVE_CURRENT_AUTHORITY_REQUEST_AND_BLOCKER_PACKAGE',
    'normative_authority': False,
    'request_is_product_authority': False,
    'stage_uid': 'STAGE-02',
    'current_governance_uid': governance_uid,
    'attempt_uid': attempt_uid,
    'source_head_sha': head,
    'source_problem_register_ref': str(PROBLEMS.relative_to(ROOT)),
    'source_classification_ref': str(CLASSIFICATION.relative_to(ROOT)),
    'purpose': 'REQUEST_ONLY_EXACT_AUTHORITY_NEEDED_FOR_CURRENT_OPEN_STAGE02_PROBLEMS_WITHOUT_AI_INVENTION_OR_HISTORICAL_DENOMINATOR_REUSE',
    'safety': {
        'contains_product_authority_values': False,
        'may_be_used_as_authority_input': False,
        'may_auto_resolve_any_problem': False,
        'current_specification_mutated': False,
        'stage1_immutable_source_mutated': False,
        'product_materialization_performed': False,
        'blocker_reduction_claimed': 0,
        'stage03_allowed': False,
        'website_construction_allowed': False,
        'deployment_allowed': False,
    },
    'denominators': {
        'current_open_problems': current_n,
        'product_design_authority_requests': local_n,
        'external_authority_requests': external_n,
        'bounded_completion_admissible': 0,
        'materializable_from_current_authority_now': 0,
    },
    'category_counts': dict(sorted(Counter(p.get('category') for p in problems).items())),
    'product_design_authority_requests': local_requests,
    'external_authority_requests': external_requests,
    'intake_rule': {
        'approved_authority_must_be_separate_from_this_request': True,
        'request_package_itself_is_not_authority': True,
        'approved_input_must_resolve_exact_problem_uid_and_signature': True,
        'approved_input_must_name_current_admissible_canonical_owner_and_provenance': True,
        'ai_may_not_fill_product_or_external_authority_values': True,
        'historical_non_current_output_may_not_supply_current_authority': True,
        'materialization_requires_separate_approval_and_exact_validation': True,
        'fresh_stage02_reexecution_required_before_any_blocker_reduction_credit': True,
    },
    'resume_control': {
        'current_resume_point_preserved': 'STAGE2_TESTED_BLOCKED_FUNCTIONAL_REMEDIATION',
        'exact_next_action': f'INGEST_SEPARATELY_APPROVED_CURRENT_PRODUCT_AUTHORITY_FOR_{local_n}_LOCAL_REQUESTS_OR_EXTERNAL_AUTHORITY_FOR_{external_n}_REFERENCED_GAPS; OTHERWISE_REMAIN_BLOCKED',
    },
    'status': f'OPEN_AWAITING_{local_n}_PRODUCT_AUTHORITY_BINDINGS_AND_{external_n}_EXTERNAL_AUTHORITY_RESOLUTIONS',
}
dump(OUT, out)

state['next_action'] = 'BUILD_AND_REVIEW_BOUNDED_NON_NORMATIVE_DESIGN_REMEDIATION_PACKAGE_FOR_LOCAL_INPUT_SOURCE_AND_ARCHITECTURE_GAPS; ROUTE_ONLY_TRUE_AUTHORITY_GAPS_TO_EXPLICIT_SELECTION; DO_NOT_R7_MATERIALIZE_REVIEW_ONLY_CANDIDATES'
resume = state.setdefault('resume_control', {})
resume['exact_next_action'] = state['next_action']
attempt = state.setdefault('stage02_active_attempt', {})
attempt['authority_request_package_ref'] = str(OUT.relative_to(ROOT))
attempt['authority_request_product_count'] = local_n
attempt['authority_request_external_count'] = external_n
attempt['authority_request_is_authority'] = False
attempt['new_authority_required_before_more_material_remediation'] = True
attempt['next_action'] = state['next_action']
dump(STATE, state)

findings['next_action'] = state['next_action']
dump(FINDINGS, findings)

current = candidates.setdefault('current_stage2_execution', {})
current['next_action'] = state['next_action']
current['authority_request_package_ref'] = str(OUT.relative_to(ROOT))
current['authority_request_product_count'] = local_n
current['authority_request_external_count'] = external_n
current['authority_request_is_authority'] = False
dump(CANDIDATES, candidates)

print(f'STAGE02_R5_CURRENT_OPEN_PROBLEMS={current_n}')
print(f'STAGE02_R5_PRODUCT_AUTHORITY_REQUESTS={local_n}')
print(f'STAGE02_R5_EXTERNAL_AUTHORITY_REQUESTS={external_n}')
print('STAGE02_R5_MATERIALIZABLE_NOW=0')
print('PASS: R5 consumes the one Current Problem Register and policy-correct Current R2 classification')
print('PASS: request package contains no invented product/external authority values and claims zero blocker reduction')
