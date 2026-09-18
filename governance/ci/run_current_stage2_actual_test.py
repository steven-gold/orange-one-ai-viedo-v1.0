#!/usr/bin/env python3
from __future__ import annotations
from collections import Counter, defaultdict
import json
import os
import re
import subprocess
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
STAGE_REGISTRY = ROOT / '.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
RESULT = ROOT / '.github/stage02-test/STAGE02_ACTUAL_TEST_RESULT.json'
OLD_STAGE2_ROOT = RUN / '04_PAGE_FUNCTIONAL_CONTRACT'

def resolve_page(page_uid: str):
    raw_dir = RUN / '00_SOURCE_INTAKE/RAW_SOURCE' / page_uid
    blueprint = RUN / '02_BASE_BLUEPRINT' / page_uid / 'PAGE_BASE_BLUEPRINT.yaml'
    if not raw_dir.is_dir() or not blueprint.is_file():
        die(f'PAGE_SCOPE_OWNER_MISSING:{page_uid}')
    candidates = []
    for path in sorted(raw_dir.glob('*.yaml')):
        try:
            obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        except Exception:
            continue
        if (obj.get('authority') or {}).get('page_uid') == page_uid and isinstance(obj.get('registries'), dict):
            candidates.append(path)
    if len(candidates) != 1:
        die(f'PAGE_RAW_OWNER_DENOMINATOR:{page_uid}:{len(candidates)}')
    return {'raw': candidates[0], 'blueprint': blueprint}


def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)

def load(path: Path):
    try:
        obj = yaml.safe_load(path.read_text(encoding='utf-8'))
    except Exception as exc:
        die(f'PARSE_ERROR:{path.relative_to(ROOT)}:{exc!r}')
    if not isinstance(obj, dict):
        die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj

def idx(items, key):
    return {x.get(key): x for x in (items or []) if isinstance(x, dict) and x.get(key)}

def present(obj, *names):
    return any(isinstance(obj, dict) and obj.get(name) not in (None, '', [], {}) for name in names)

def event_token(text: str):
    text = str(text or '')
    if '|' in text:
        tail = text.split('|', 1)[1].strip()
        if tail and tail.lower() not in {'event none', 'none'}:
            return tail
    m = re.search(r'\b[a-z][a-z0-9_]*\.[a-z0-9_.]+\b', text)
    return m.group(0) if m else None

def has_transition(text: str):
    text = str(text or '')
    return '→' in text or '->' in text

def add(gaps, page, klass, category, uid, detail, owner='PAGE_FUNCTIONAL_CONTRACT'):
    gaps.append({'page_uid': page, 'class': klass, 'category': category, 'uid': uid, 'detail': detail, 'gap_owner': owner})

def fresh_scan(page: str, raw: dict, unresolved_authority_by_ref: dict):
    reg = raw.get('registries') or {}
    actions = idx(reg.get('actions'), 'action_uid')
    controls = idx(reg.get('controls'), 'control_uid')
    permissions = idx(reg.get('permissions'), 'permission_uid')
    gates = idx(reg.get('gates'), 'gate_uid')
    errors = idx(reg.get('errors'), 'error_uid')
    ports = idx(reg.get('integration_ports'), 'port_uid')
    stages = idx(reg.get('stages'), 'stage_uid')
    events = idx(reg.get('events'), 'event_uid')
    transitions = idx(reg.get('stage_transitions'), 'transition_uid')
    controls_by_action = defaultdict(list)
    transitions_by_action = defaultdict(list)
    gaps = []

    for cid, control in controls.items():
        aid = control.get('action_uid')
        if aid:
            controls_by_action[aid].append(cid)
        if not aid or aid not in actions:
            add(gaps, page, 'IMPLEMENTATION_GAP', 'CONTROL_WITHOUT_VALID_ACTION', cid, str(aid))
        if control.get('gate_uid') and control.get('gate_uid') not in gates:
            add(gaps, page, 'IMPLEMENTATION_GAP', 'CONTROL_GATE_REF_MISSING', cid, str(control.get('gate_uid')))
        if control.get('permission_uid') and control.get('permission_uid') not in permissions:
            add(gaps, page, 'IMPLEMENTATION_GAP', 'CONTROL_PERMISSION_REF_MISSING', cid, str(control.get('permission_uid')))

    for tid, transition in transitions.items():
        trigger = transition.get('action_uid') or transition.get('trigger_event_uid') or transition.get('trigger')
        if trigger in actions:
            transitions_by_action[trigger].append(tid)

    effectful = 0
    runtime_refs = 0
    for aid, action in actions.items():
        effect = action.get('effect_type')
        is_effectful = effect not in {'READ_ONLY', 'UI_ONLY', 'CONTEXT_STATE'}
        effectful += int(is_effectful)
        if not action.get('label'):
            add(gaps, page, 'IMPLEMENTATION_GAP', 'BUSINESS_INTENT_MISSING', aid, 'action label/intent absent')
        for field, registry, category in (
            ('permission_uid', permissions, 'ACTION_PERMISSION_REF_MISSING'),
            ('gate_uid', gates, 'ACTION_GATE_REF_MISSING'),
        ):
            ref = action.get(field)
            if not ref or ref not in registry:
                add(gaps, page, 'IMPLEMENTATION_GAP', category, aid, str(ref))
        rb = action.get('runtime_binding') or {}
        kind = rb.get('binding_kind')
        failure_recovery_not_applicable = (
            not is_effectful
            and kind == 'CLIENT_STATE_OR_VIEW_NO_API_REQUIRED'
            and rb.get('api_required') is False
            and not transitions_by_action.get(aid)
        )
        err = action.get('error_uid')
        if err:
            if err not in errors:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'ACTION_ERROR_REF_MISSING', aid, str(err))
            elif not errors[err].get('recovery'):
                add(gaps, page, 'IMPLEMENTATION_GAP', 'RECOVERY_CONTRACT_MISSING', aid, str(err))
        elif not failure_recovery_not_applicable and not any((transitions.get(tid) or {}).get('recovery') for tid in transitions_by_action.get(aid, [])):
            add(gaps, page, 'ARCHITECTURE_GAP', 'FAILURE_STATE_ERROR_BINDING_MISSING', aid, 'no exact action->error/recovery or transition recovery binding')

        explicit_trigger = present(action, 'trigger_event_uid', 'trigger_uid', 'invocation', 'system_trigger', 'trigger_kind') or bool(transitions_by_action.get(aid))
        if not controls_by_action.get(aid) and not explicit_trigger:
            add(gaps, page, 'ARCHITECTURE_GAP', 'ACTION_WITHOUT_CONTROL_OR_TRIGGER', aid, 'no registered control or exact transition/system trigger')
        if not kind:
            add(gaps, page, 'IMPLEMENTATION_GAP', 'RUNTIME_BINDING_MISSING', aid, 'runtime_binding.binding_kind absent')
            continue
        resolved_ports = []
        for field in ('port_uid', 'persist_via_port_uid', 'execute_port_uid', 'decision_port_uid'):
            puid = rb.get(field)
            if not puid:
                continue
            port = ports.get(puid)
            if not port:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'RUNTIME_PORT_REF_MISSING', aid, f'{field}={puid}')
            else:
                resolved_ports.append((puid, port))
                runtime_refs += 1

        if kind == 'CLIENT_STATE_OR_VIEW_NO_API_REQUIRED':
            if rb.get('api_required') is not False:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'CLIENT_ACTION_API_NA_CONTRACT_MISSING', aid, 'api_required must be false')
        elif kind == 'SHARED_OPERATION_REFERENCE':
            auth = rb.get('shared_authority_id')
            op = rb.get('shared_operation_id')
            if not auth or not op:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'SHARED_OWNER_REFERENCE_INCOMPLETE', aid, str((auth, op)))
            elif auth in unresolved_authority_by_ref:
                add(gaps, page, 'AUTHORITY_GAP', 'SHARED_OWNER_AUTHORITY_UNRESOLVED', aid, f'{unresolved_authority_by_ref[auth]}: {auth}', 'EXTERNAL_AUTHORITY')
        else:
            if not resolved_ports:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'RUNTIME_ENTRY_OR_PORT_MISSING', aid, str(kind))
            for puid, port in resolved_ports:
                operation = port.get('operation') or port.get('registered_operation')
                method = port.get('method_path') or port.get('method_effective_path')
                permission = port.get('permission') or port.get('registered_permission')
                if not operation:
                    add(gaps, page, 'IMPLEMENTATION_GAP', 'PORT_OPERATION_MISSING', aid, puid)
                if not method:
                    add(gaps, page, 'IMPLEMENTATION_GAP', 'API_ENTRY_MISSING', aid, puid)
                if not permission:
                    add(gaps, page, 'IMPLEMENTATION_GAP', 'PORT_PERMISSION_MISSING', aid, puid)

        if is_effectful and kind != 'SHARED_OPERATION_REFERENCE':
            port = resolved_ports[0][1] if resolved_ports else {}
            if not (present(action, 'success_contract', 'validation_contract', 'validator_uid') or present(rb, 'validation', 'validation_rule', 'evaluation_rule') or present(port, 'validation', 'validation_rule', 'validator_uid')):
                add(gaps, page, 'ARCHITECTURE_GAP', 'POST_ACTION_VALIDATION_NODE_MISSING', aid, 'no explicit success/validation/evaluation contract')
            if not (present(action, 'payload', 'payload_rule', 'input_contract', 'request_contract') or present(rb, 'payload', 'payload_rule', 'payload_mode', 'input_contract', 'request_contract') or present(port, 'payload', 'payload_rule', 'input_contract', 'request_contract', 'request_schema')):
                add(gaps, page, 'INPUT_SOURCE_GAP', 'PAYLOAD_INPUT_CONTRACT_MISSING', aid, 'no explicit payload/input contract or schema')
            state_event = str(port.get('state_event') or '')
            if not event_token(state_event):
                add(gaps, page, 'ARCHITECTURE_GAP', 'AUDIT_EVENT_NODE_MISSING', aid, 'registered port has no explicit audit/event UID in state_event')
            if not (has_transition(state_event) or bool(transitions_by_action.get(aid)) or action.get('state_effect')):
                add(gaps, page, 'ARCHITECTURE_GAP', 'SUCCESS_NEXT_STATE_BINDING_MISSING', aid, 'no state_effect, state transition, or port state_event transition')

    for tid, transition in transitions.items():
        if transition.get('from_stage') not in stages or transition.get('to_stage') not in stages:
            add(gaps, page, 'IMPLEMENTATION_GAP', 'TRANSITION_STAGE_REF_MISSING', tid, str((transition.get('from_stage'), transition.get('to_stage'))))
        trigger = transition.get('action_uid') or transition.get('trigger_event_uid') or transition.get('trigger')
        if not trigger:
            add(gaps, page, 'ARCHITECTURE_GAP', 'TRANSITION_TRIGGER_MISSING', tid, 'trigger/action absent')
        elif transition.get('trigger_event_uid') and events and transition.get('trigger_event_uid') not in events:
            add(gaps, page, 'IMPLEMENTATION_GAP', 'TRANSITION_EVENT_REF_MISSING', tid, str(transition.get('trigger_event_uid')))
        gate = transition.get('gate_uid') or transition.get('gate')
        if not gate:
            add(gaps, page, 'ARCHITECTURE_GAP', 'TRANSITION_GATE_PRECONDITION_MISSING', tid, 'gate/preconditions absent')
        elif transition.get('gate_uid') and transition.get('gate_uid') not in gates:
            add(gaps, page, 'IMPLEMENTATION_GAP', 'TRANSITION_GATE_REF_MISSING', tid, str(transition.get('gate_uid')))
        for required in ('mutation_owner', 'failure_state', 'recovery', 'audit_event_uid', 'illegal_transition_tests'):
            if transition.get(required) in (None, '', [], {}):
                add(gaps, page, 'ARCHITECTURE_GAP', 'STATE_TRANSITION_LEDGER_FIELD_MISSING', tid, required)

    unique, seen = [], set()
    for gap in gaps:
        key = (gap['page_uid'], gap['class'], gap['category'], gap['uid'], gap['detail'])
        if key not in seen:
            seen.add(key)
            unique.append(gap)
    classes = Counter(x['class'] for x in unique)
    categories = Counter(x['category'] for x in unique)
    return {
        'registry_denominator': {
            'actions': len(actions), 'controls': len(controls), 'permissions': len(permissions),
            'gates': len(gates), 'errors': len(errors), 'integration_ports': len(ports),
            'stages': len(stages), 'events': len(events), 'stage_transitions': len(transitions),
            'effectful_actions': effectful,
        },
        'registered_runtime_reference_count': runtime_refs,
        'gap_count': len(unique),
        'gap_classes': dict(sorted(classes.items())),
        'gap_categories': dict(sorted(categories.items())),
        'gaps': unique,
        'functional_completion': len(unique) == 0,
    }

state = load(STATE)
execution = state.get('execution') or {}
if execution.get('current_stage') != 'STAGE-01-CLOSED':
    die(f'STAGE02_ADMISSION_CURRENT_STAGE:{execution.get("current_stage")!r}')
if (execution.get('stage2') or {}).get('result') != 'NOT_EXECUTED':
    die('STAGE02_ADMISSION_REQUIRES_NOT_EXECUTED')
stage1_state = execution.get('stage1') or {}
if not isinstance(stage1_state, dict) or not stage1_state or any(v != 'PASS' for v in stage1_state.values()):
    die(f'STAGE02_ADMISSION_STAGE1_NOT_CLOSED:{stage1_state!r}')
required_page_uids = list(stage1_state)

registry = load(STAGE_REGISTRY)
stage2_records = [x for x in (registry.get('stages') or []) if x.get('stage_uid') == 'STAGE-02']
if len(stage2_records) != 1:
    die('STAGE02_REGISTRY_RECORD_DENOMINATOR')
stage2_contract = stage2_records[0]
if stage2_contract.get('name') != 'PAGE_FUNCTIONAL_CONTRACT' or stage2_contract.get('entry_gate') != 'ALL_REQUIRED_PAGES_STAGE1_CLOSED':
    die('STAGE02_CONTRACT_IDENTITY_DRIFT')
stage2_outputs = stage2_contract.get('outputs') or []
if not isinstance(stage2_outputs, list) or not stage2_outputs or any(not isinstance(x, str) or not x.strip() for x in stage2_outputs):
    die(f'STAGE02_OUTPUT_SET_EMPTY_OR_INVALID:{stage2_outputs!r}')
if len(stage2_outputs) != len(set(stage2_outputs)):
    die(f'STAGE02_OUTPUT_SET_DUPLICATE:{stage2_outputs!r}')
mandatory_stage2_outputs = ((stage2_contract.get('required_output_applicability') or {}).get('always_for_target_scope') or [])
if not isinstance(mandatory_stage2_outputs, list) or not mandatory_stage2_outputs:
    die('STAGE02_PROFILE_MANDATORY_OUTPUT_SET_EMPTY')
if len(mandatory_stage2_outputs) != len(set(mandatory_stage2_outputs)):
    die(f'STAGE02_PROFILE_MANDATORY_OUTPUT_SET_DUPLICATE:{mandatory_stage2_outputs!r}')
missing_mandatory = sorted(set(mandatory_stage2_outputs) - set(stage2_outputs))
if missing_mandatory:
    die(f'STAGE02_MANDATORY_OUTPUTS_MISSING_FROM_LIFECYCLE_REGISTRY:{missing_mandatory!r}')
if stage2_contract.get('exit_gate') != 'ALL_REQUIRED_PAGES_STAGE2_CLOSED':
    die('STAGE02_EXIT_GATE_DRIFT')

scope = os.environ.get('STAGE02_PAGE_SCOPE', 'ALL_REQUIRED_PAGES').strip()
if scope == 'ALL_REQUIRED_PAGES':
    target_page_uids = list(required_page_uids)
else:
    target_page_uids = [x.strip() for x in scope.split(',') if x.strip()]
    if not target_page_uids or len(target_page_uids) != len(set(target_page_uids)):
        die(f'INVALID_STAGE02_PAGE_SCOPE:{scope!r}')
    unknown = sorted(set(target_page_uids) - set(required_page_uids))
    if unknown:
        die(f'STAGE02_PAGE_SCOPE_OUTSIDE_STAGE1:{unknown!r}')
target_pages = {page: resolve_page(page) for page in target_page_uids}
remaining_page_uids = [page for page in required_page_uids if page not in target_page_uids]
scope_complete = not remaining_page_uids

pages = {}
external = {}
union_gap_uids = set()
for page, paths in target_pages.items():
    blueprint = load(paths['blueprint'])
    raw = load(paths['raw'])
    if blueprint.get('page_uid') != page or blueprint.get('stage_uid') != 'STAGE-01':
        die(f'{page}:BLUEPRINT_IDENTITY_DRIFT')
    refs = blueprint.get('unresolved_external_authority_refs') or []
    for ref in refs:
        gid = ref.get('gap_uid')
        union_gap_uids.add(gid)
        if ref.get('resolved') is not False or ref.get('satisfied') is not False or ref.get('auto_filled') is not False or ref.get('inferred') is not False:
            die(f'{page}:EXTERNAL_AUTHORITY_FALSE_RESOLUTION:{gid}')
        external.setdefault(gid, {'authority_ref': ref.get('authority_ref'), 'consumers': []})['consumers'].append(page)

    unresolved_authority_by_ref = {str(x.get('authority_ref')): x.get('gap_uid') for x in refs if isinstance(x, dict) and x.get('authority_ref') and x.get('gap_uid')}
    scan = fresh_scan(page, raw, unresolved_authority_by_ref)
    responsibilities = set(blueprint.get('required_responsibility_uids') or [])
    ai_profile_active = 'CONVERSATION_POLICY' in responsibilities
    page_dir = OLD_STAGE2_ROOT / page
    closure_defs = [
        ('BUSINESS_ENTITY_INVENTORY.yaml', 'MISSING_BUSINESS_ENTITY_INVENTORY'),
        ('BUSINESS_ENTITY_OPERATION_MATRIX.yaml', 'MISSING_BUSINESS_ENTITY_OPERATION_MATRIX'),
        ('ENTITY_HIERARCHY_MATRIX.yaml', 'MISSING_ENTITY_HIERARCHY_MATRIX'),
        ('FUNCTIONAL_WORKBENCH_CONTRACT.yaml', 'MISSING_FUNCTIONAL_WORKBENCH_CONTRACT'),
        ('INTERACTION_TOPOLOGY_SPEC.yaml', 'MISSING_INTERACTION_TOPOLOGY_SPEC'),
        ('FUNCTION_VISUAL_IMPACT_MATRIX.yaml', 'MISSING_FUNCTION_VISUAL_IMPACT_MATRIX'),
    ]
    closure = [code for filename, code in closure_defs if not (page_dir / filename).is_file()]
    if ai_profile_active and not (page_dir / 'AI_INTERACTION_CONTINUITY_CONTRACT.yaml').is_file():
        closure.append('MISSING_AI_INTERACTION_CONTINUITY_CONTRACT')
    if scan.get('gap_count', 0) > 0:
        if not (page_dir / 'FUNCTION_ADMISSION_SCORECARD.yaml').is_file():
            closure.append('MISSING_FUNCTION_ADMISSION_SCORECARD')
        if not (page_dir / 'AUTO_COMPLETION_SCOPE_LEDGER.yaml').is_file():
            closure.append('MISSING_AUTO_COMPLETION_SCOPE_LEDGER')
    pages[page] = {
        'blueprint_uid': blueprint.get('blueprint_uid'),
        'ai_interaction_profile_active': ai_profile_active,
        'unresolved_external_authority_ref_count': len(refs),
        'functional_chain_fresh_scan': scan,
        'closure_blockers': closure,
        'closure_blocker_count': len(closure),
        'function_admission_scorecard': 'PRESENT' if (page_dir / 'FUNCTION_ADMISSION_SCORECARD.yaml').is_file() else 'REQUIRED_WHEN_GAP_ANALYSIS_EXISTS',
        'automatic_completion_scope': 'PRESENT' if (page_dir / 'AUTO_COMPLETION_SCOPE_LEDGER.yaml').is_file() else 'REQUIRED_WHEN_GAP_ANALYSIS_EXISTS',
    }

if any(not gid for gid in union_gap_uids):
    die('EXTERNAL_AUTHORITY_GAP_UID_MISSING')

head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
functional_total = sum(x['functional_chain_fresh_scan']['gap_count'] for x in pages.values())
closure_total = sum(x['closure_blocker_count'] for x in pages.values())
stage_exit_allowed = scope_complete and functional_total == 0 and closure_total == 0
result = {
    'schema_version': 1,
    'artifact_type': 'NON_NORMATIVE_STAGE02_ACTUAL_TEST_EVIDENCE',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'stage_name': 'PAGE_FUNCTIONAL_CONTRACT',
    'source_head_sha': head,
    'test_mode': 'FRESH_FROM_STAGE1_IMMUTABLE_INPUTS_NO_PRIOR_STAGE2_RESULT_REUSE',
    'actual_product_stage_test_started': True,
    'actual_product_stage_test_completed': True,
    'stage_entry_gate': 'PASS',
    'scope_mode': 'EXACT_PAGE_SCOPE_ONLY' if not scope_complete else 'ALL_REQUIRED_PAGES',
    'requested_page_scope': scope,
    'target_pages': target_page_uids,
    'remaining_pages': remaining_page_uids,
    'stage_scope_complete': scope_complete,
    'stage_exit_allowed': stage_exit_allowed,
    'result': 'PASS' if stage_exit_allowed else 'BLOCKED',
    'official_stage_output_denominator': sorted(stage2_outputs),
    'execution_profile_mandatory_output_subset': sorted(mandatory_stage2_outputs),
    'physical_stage2_product_artifact_root_present': OLD_STAGE2_ROOT.is_dir(),
    'pages': pages,
    'fresh_functional_gap_total': functional_total,
    'closure_blocker_total': closure_total,
    'preserved_external_authorities': dict(sorted(external.items())),
    'preserved_external_authority_union_count': len(union_gap_uids),
    'preserved_external_authority_union_gap_uids': sorted(union_gap_uids),
    'current_specification_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'prior_stage2_results_used': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
    'notes': [
        'BLOCKED is a valid Stage-02 product-test outcome and does not mean the test runner failed.',
        'External authority references are preserved unresolved; they are neither dropped nor auto-resolved.',
        'No Current Specification file is modified by this test.',
        'A page-scoped test does not grant Stage-02 exit credit until every required page has fresh evidence.',
    ],
}
RESULT.parent.mkdir(parents=True, exist_ok=True)
RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print('STAGE02_SOURCE_HEAD=' + head)
for page, rec in pages.items():
    scan = rec['functional_chain_fresh_scan']
    print(f'STAGE02_PAGE|{page}|functional_gaps={scan["gap_count"]}|closure_blockers={rec["closure_blocker_count"]}|ai_profile={rec["ai_interaction_profile_active"]}')
    print('STAGE02_GAP_CATEGORIES|' + page + '|' + json.dumps(scan['gap_categories'], ensure_ascii=False, sort_keys=True))
print('STAGE02_EXTERNAL_AUTHORITY_UNION=' + ','.join(sorted(union_gap_uids)))
print('STAGE02_RESULT=' + result['result'])
print('PASS: Stage-02 actual test executed from Stage-01 immutable inputs; prior Stage-02 results were not used')
