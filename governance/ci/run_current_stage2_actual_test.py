#!/usr/bin/env python3
from __future__ import annotations
from collections import Counter, defaultdict
from copy import deepcopy
import json
import os
import re
import subprocess
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT_ENV = os.environ.get('ACPOS_RUN_ROOT', '').strip()
if not RUN_ROOT_ENV:
    raise SystemExit('BLOCK: ACPOS_RUN_ROOT_REQUIRED')
RUN = ROOT / RUN_ROOT_ENV
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

def effective_page_contract(page: str, raw: dict):
    """Compose immutable Stage-01 source facts with an approved Stage-02 canonical successor.

    Review-only candidate bytes are never consumed here. The overlay is eligible only after
    the candidate has been materialized into the page's single canonical FUNCTIONAL_CHAIN_SPEC
    owner with explicit approval provenance and an immutable-Raw guarantee.
    """
    spec_path = OLD_STAGE2_ROOT / page / 'FUNCTIONAL_CHAIN_SPEC.yaml'
    if not spec_path.is_file():
        return raw, {'applied': False, 'reason': 'NO_STAGE2_CANONICAL_SUCCESSOR'}
    spec = load(spec_path)
    meta = spec.get('design_contract_remediation') or {}
    if meta.get('canonical_owner_materialization') is not True:
        return raw, {'applied': False, 'reason': 'NO_APPROVED_CANONICAL_MATERIALIZATION'}
    if spec.get('page_uid') != page:
        die(f'{page}:FUNCTIONAL_CHAIN_PAGE_UID_DRIFT')
    if meta.get('candidate_bytes_became_authority_directly') is not False:
        die(f'{page}:CANDIDATE_BYTES_MASQUERADE_AS_AUTHORITY')
    if meta.get('raw_source_mutated') is not False:
        die(f'{page}:STAGE1_RAW_SOURCE_MUTATION_FORBIDDEN')
    approval_ref = str(meta.get('approval_evidence_ref') or '').strip()
    if not approval_ref or not (ROOT / approval_ref).is_file():
        die(f'{page}:APPROVAL_EVIDENCE_MISSING_FOR_CANONICAL_SUCCESSOR')
    projection = spec.get('source_projection')
    if not isinstance(projection, dict):
        die(f'{page}:FUNCTIONAL_CHAIN_SOURCE_PROJECTION_MISSING')

    merged = deepcopy(raw)
    reg = merged.setdefault('registries', {})
    if not isinstance(reg, dict):
        die(f'{page}:RAW_REGISTRY_INVALID')
    overlay_keys = ('actions', 'controls', 'stages', 'stage_transitions', 'events', 'integration_ports')
    applied = []
    for key in overlay_keys:
        if key not in projection:
            continue
        value = projection.get(key)
        if not isinstance(value, list):
            die(f'{page}:FUNCTIONAL_CHAIN_PROJECTION_INVALID:{key}')
        reg[key] = deepcopy(value)
        applied.append(key)
    if not applied:
        die(f'{page}:FUNCTIONAL_CHAIN_PROJECTION_EMPTY')
    return merged, {
        'applied': True,
        'canonical_owner_ref': str(spec_path.relative_to(ROOT)),
        'approval_evidence_ref': approval_ref,
        'overlay_registry_keys': applied,
        'raw_source_mutated': False,
    }



def declared_stage02_completeness_gaps(page: str, raw: dict, controls: dict, objects: dict, gaps: list[dict]):
    meta = raw.get('stage02_completeness_contract')
    if not isinstance(meta, dict) or meta.get('status') != 'REQUIRED_FOR_STAGE02_CLOSURE':
        add(gaps, page, 'ARCHITECTURE_GAP', 'STAGE02_PLANNING_COMPLETENESS_CONTRACT_MISSING', page, 'required Stage-02 planning completeness contract absent')
        return
    baseline = str(meta.get('planning_baseline_sha256') or '')
    if not re.fullmatch(r'[0-9a-f]{64}', baseline):
        add(gaps, page, 'ARCHITECTURE_GAP', 'PLANNING_BASELINE_IDENTITY_MISSING', page, baseline or 'missing sha256')
    for key in meta.get('required_contracts') or []:
        if not isinstance(raw.get(str(key)), (dict, list)):
            add(gaps, page, 'ARCHITECTURE_GAP', 'DECLARED_COMPLETENESS_CONTRACT_MISSING', str(key), 'required top-level contract missing')

    field_contract = raw.get('field_binding_contract') or {}
    declared_fields = field_contract.get('fields') or []
    for row in declared_fields:
        if not isinstance(row, dict) or not row.get('control_uid'):
            add(gaps, page, 'ARCHITECTURE_GAP', 'FIELD_BINDING_DECLARATION_INVALID', page, str(row))
            continue
        cid = str(row['control_uid'])
        control = controls.get(cid)
        if not control:
            add(gaps, page, 'IMPLEMENTATION_GAP', 'DECLARED_FIELD_CONTROL_MISSING', cid, 'field binding control absent')
            continue
        if control.get('action_uid') not in (None, '', 'NONE_FIELD_BINDING'):
            add(gaps, page, 'ARCHITECTURE_GAP', 'FIELD_MASQUERADES_AS_ACTION', cid, str(control.get('action_uid')))
        if control.get('binding_semantics') != 'DATA_OR_DRAFT_STATE_ONLY':
            add(gaps, page, 'ARCHITECTURE_GAP', 'FIELD_BINDING_SEMANTICS_MISSING', cid, str(control.get('binding_semantics')))
        if not control.get('data_binding') or control.get('data_binding') != row.get('data_binding'):
            add(gaps, page, 'ARCHITECTURE_GAP', 'FIELD_DATA_BINDING_DRIFT', cid, str(control.get('data_binding')))
    send = field_contract.get('send_binding') or {}
    send_action = send.get('action_uid')
    send_control = send.get('send_control_uid')
    owners = sorted(cid for cid, control in controls.items() if control.get('action_uid') == send_action)
    if send_action and owners != [send_control]:
        add(gaps, page, 'ARCHITECTURE_GAP', 'SEND_ACTION_NOT_UNIQUELY_OWNED_BY_SEND_CONTROL', str(send_action), str(owners))

    wb = raw.get('functional_workbench_topology_contract') or {}
    conv = wb.get('conversation_workbench') or {}
    section_registry = idx((raw.get('registries') or {}).get('sections'), 'section_uid')
    required_sections = conv.get('section_order') or []
    valid_section_order = isinstance(required_sections, list) and bool(required_sections) and all(str(x) in section_registry for x in required_sections)
    if (not conv.get('workbench_uid') or conv.get('workbench_type') != 'ATOMIC_WORKBENCH' or conv.get('same_surface') != 'REQUIRED'
            or not valid_section_order or conv.get('split_into_independent_surfaces') != 'FORBIDDEN'):
        add(gaps, page, 'ARCHITECTURE_GAP', 'CONVERSATION_ATOMIC_WORKBENCH_CONTRACT_INCOMPLETE', str(conv.get('workbench_uid') or page), str(conv))

    lifecycle = raw.get('work_item_lifecycle_contract') or {}
    declared_items = {}
    for row in (lifecycle.get('project_core_order') or []) + (lifecycle.get('topic_production_order') or []):
        if isinstance(row, dict) and row.get('work_item'):
            declared_items[str(row['work_item'])] = row
    modes = raw.get('page_modes') or {}
    expected_items = []
    for mode_record in modes.values() if isinstance(modes, dict) else []:
        if isinstance(mode_record, dict):
            expected_items.extend(mode_record.get('editable_work_items') or [])
    if set(declared_items) != set(expected_items):
        add(gaps, page, 'ARCHITECTURE_GAP', 'WORK_ITEM_LIFECYCLE_DENOMINATOR_DRIFT', page, str({'expected':sorted(expected_items),'actual':sorted(declared_items)}))
    domain_ops = {str(x.get('operation_uid')): x for x in (raw.get('domain_materialization_operations') or []) if isinstance(x, dict) and x.get('operation_uid')}
    actions = idx((raw.get('registries') or {}).get('actions'), 'action_uid')
    for wi, row in declared_items.items():
        if not row.get('formal_output'):
            add(gaps, page, 'ARCHITECTURE_GAP', 'WORK_ITEM_FORMAL_OUTPUT_MISSING', wi, 'formal_output')
        op = row.get('finalization_operation_uid')
        action = row.get('finalization_action_uid')
        actions_list = row.get('finalization_action_uids') or []
        if op:
            rec = domain_ops.get(str(op))
            if not rec:
                add(gaps, page, 'ARCHITECTURE_GAP', 'WORK_ITEM_DOMAIN_FINALIZATION_OPERATION_MISSING', wi, str(op))
            else:
                for required in ('runtime_owner','persistence_owner','required_inputs','validation','audit_event_uid','failure_state','recovery','resulting_state','transport_surface'):
                    if rec.get(required) in (None,'',[],{}):
                        add(gaps, page, 'ARCHITECTURE_GAP', 'DOMAIN_FINALIZATION_FIELD_MISSING', str(op), required)
                if 'PAGE_LOCAL_API' in str(rec.get('transport_surface')) and 'NOT_PAGE_LOCAL_API' not in str(rec.get('transport_surface')):
                    add(gaps, page, 'ARCHITECTURE_GAP', 'PAGE_LOCAL_FINALIZATION_API_FORBIDDEN', str(op), str(rec.get('transport_surface')))
        elif action:
            if action not in actions:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'WORK_ITEM_FINALIZATION_ACTION_MISSING', wi, str(action))
        elif actions_list:
            missing = [x for x in actions_list if x not in actions]
            if missing:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'WORK_ITEM_FINALIZATION_ACTION_SET_INCOMPLETE', wi, str(missing))
        else:
            add(gaps, page, 'ARCHITECTURE_GAP', 'WORK_ITEM_FINALIZATION_BINDING_MISSING', wi, 'no operation/action binding')
    if lifecycle.get('known_authority_gaps_open') not in ([], None):
        add(gaps, page, 'AUTHORITY_GAP', 'KNOWN_WORK_ITEM_AUTHORITY_GAP_STILL_OPEN', page, str(lifecycle.get('known_authority_gaps_open')))

    memory = raw.get('working_memory_binding') or {}
    if not memory.get('owner') or memory.get('page_local_second_service') != 'FORBIDDEN' or memory.get('formal_truth') is not False:
        add(gaps, page, 'ARCHITECTURE_GAP', 'WORKING_MEMORY_OWNER_BINDING_INCOMPLETE', page, str(memory))

    cp = raw.get('conversation_policy') or {}
    required_context = ['Project','Topic if applicable','Work Item','Thread','Attachment refs','Reference refs','Context Package']
    if not cp.get('same_problem_rule') or cp.get('exact_relevant_context') != required_context or not cp.get('response_traceability') or not cp.get('finalization_reentry'):
        add(gaps, page, 'ARCHITECTURE_GAP', 'MULTI_AI_SAME_QUESTION_EXACT_CONTEXT_INCOMPLETE', page, str(cp))

    impact = raw.get('change_impact_contract') or {}
    states = set(impact.get('affected_downstream_states') or [])
    if not {'NEEDS_REVIEW','NEEDS_REVALIDATION'}.issubset(states) or impact.get('silent_downstream_rewrite') != 'FORBIDDEN' or impact.get('exact_base_version_required_for_revision') is not True:
        add(gaps, page, 'ARCHITECTURE_GAP', 'UPSTREAM_CHANGE_IMPACT_REVALIDATION_INCOMPLETE', page, str(impact))

    op_contract = raw.get('entity_operation_applicability_contract') or {}
    vocabulary = op_contract.get('operation_vocabulary') or []
    profiles = op_contract.get('profiles') or {}
    bindings = op_contract.get('entity_profile_bindings') or []
    binding_map = {str(x.get('object_uid')): str(x.get('profile')) for x in bindings if isinstance(x, dict) and x.get('object_uid')}
    if set(binding_map) != set(objects):
        add(gaps, page, 'ARCHITECTURE_GAP', 'BUSINESS_ENTITY_OPERATION_APPLICABILITY_DENOMINATOR_DRIFT', page, str({'entity_count':len(objects),'binding_count':len(binding_map)}))
    if not vocabulary or not profiles:
        add(gaps, page, 'ARCHITECTURE_GAP', 'BUSINESS_ENTITY_OPERATION_APPLICABILITY_AUTHORITY_MISSING', page, 'vocabulary/profiles absent')
    for oid, profile in binding_map.items():
        rec = profiles.get(profile)
        if not isinstance(rec, dict):
            add(gaps, page, 'ARCHITECTURE_GAP', 'BUSINESS_ENTITY_OPERATION_PROFILE_MISSING', oid, profile)
            continue
        required = rec.get('required') or []
        optional = rec.get('optional') or []
        if any(x not in vocabulary for x in required + optional):
            add(gaps, page, 'ARCHITECTURE_GAP', 'BUSINESS_ENTITY_OPERATION_PROFILE_UNKNOWN_OPERATION', oid, profile)

    hierarchy = raw.get('entity_hierarchy_contract') or {}
    rels = hierarchy.get('relationships') or []
    rel_map = {str(x.get('object_uid')): x for x in rels if isinstance(x, dict) and x.get('object_uid')}
    if set(rel_map) != set(objects):
        add(gaps, page, 'ARCHITECTURE_GAP', 'ENTITY_HIERARCHY_DENOMINATOR_DRIFT', page, str({'entity_count':len(objects),'relationship_count':len(rel_map)}))
    for oid, row in rel_map.items():
        if not row.get('relation_status') or not row.get('relation'):
            add(gaps, page, 'ARCHITECTURE_GAP', 'ENTITY_HIERARCHY_RELATION_INCOMPLETE', oid, str(row))
        parent = row.get('parent_object_uid')
        if parent and parent not in objects:
            add(gaps, page, 'IMPLEMENTATION_GAP', 'ENTITY_HIERARCHY_PARENT_REF_MISSING', oid, str(parent))

    pipeline = raw.get('conversation_finalization_pipeline_contract') or {}
    steps = pipeline.get('steps') or []
    orders = [x.get('order') for x in steps if isinstance(x,dict)]
    if pipeline.get('singular_pipeline') is not True or not orders or orders != list(range(1,len(orders)+1)):
        add(gaps, page, 'ARCHITECTURE_GAP', 'SINGULAR_FINALIZATION_PIPELINE_INCOMPLETE', page, str(pipeline.get('singular_pipeline')))


def materialized_stage02_completeness_blockers(page_dir: Path, raw: dict) -> list[str]:
    meta = raw.get('stage02_completeness_contract')
    if not isinstance(meta, dict) or meta.get('status') != 'REQUIRED_FOR_STAGE02_CLOSURE':
        return ['STAGE02_PLANNING_COMPLETENESS_CONTRACT_MISSING']
    blockers = []
    baseline = meta.get('planning_baseline_sha256')
    reg = raw.get('registries') or {}
    objects = idx(reg.get('objects_refs'), 'object_uid')
    field_contract = raw.get('field_binding_contract') or {}
    declared_field_uids = {str(x.get('control_uid')) for x in (field_contract.get('fields') or []) if isinstance(x,dict) and x.get('control_uid')}

    def doc(name):
        path = page_dir / name
        return load(path) if path.is_file() else {}

    opm = doc('BUSINESS_ENTITY_OPERATION_MATRIX.yaml')
    if opm.get('semantic_entity_join_used') is not True or opm.get('entity_count') != len(objects):
        blockers.append('BUSINESS_ENTITY_OPERATION_MATRIX_SEMANTIC_JOIN_MISSING')
    vocabulary = (raw.get('entity_operation_applicability_contract') or {}).get('operation_vocabulary') or []
    rows = opm.get('entity_rows') or []
    if len(rows) != len(objects):
        blockers.append('BUSINESS_ENTITY_OPERATION_MATRIX_ENTITY_DENOMINATOR_DRIFT')
    else:
        for row in rows:
            decisions = row.get('operation_applicability') or {}
            if set(decisions) != set(vocabulary) or any(v not in {'REQUIRED','OPTIONAL','NOT_APPLICABLE'} for v in decisions.values()):
                blockers.append('BUSINESS_ENTITY_OPERATION_MATRIX_APPLICABILITY_INCOMPLETE')
                break

    hm = doc('ENTITY_HIERARCHY_MATRIX.yaml')
    if hm.get('explicit_relationship_authority_used') is not True or hm.get('entity_count') != len(objects) or len(hm.get('rows') or []) != len(objects):
        blockers.append('ENTITY_HIERARCHY_RELATIONSHIPS_MISSING')
    elif any(not x.get('relation_status') or not x.get('relation') for x in (hm.get('rows') or [])):
        blockers.append('ENTITY_HIERARCHY_RELATIONSHIPS_INCOMPLETE')

    wb = doc('FUNCTIONAL_WORKBENCH_CONTRACT.yaml')
    atomics = {str(x.get('workbench_uid')): x for x in (wb.get('atomic_workbenches') or []) if isinstance(x,dict)}
    source_conv = ((raw.get('functional_workbench_topology_contract') or {}).get('conversation_workbench') or {})
    source_conv_uid = str(source_conv.get('workbench_uid') or '')
    conv = atomics.get(source_conv_uid) or {}
    if (not source_conv_uid or conv.get('workbench_type') != source_conv.get('workbench_type')
            or conv.get('same_surface') != source_conv.get('same_surface')
            or conv.get('section_order') != source_conv.get('section_order')):
        blockers.append('CONVERSATION_ATOMIC_WORKBENCH_MISSING')

    topo = doc('INTERACTION_TOPOLOGY_SPEC.yaml')
    illegal = [x for x in (topo.get('edges') or []) if x.get('relation') == 'CONTROL_TRIGGERS_ACTION' and x.get('from') in declared_field_uids]
    if illegal:
        blockers.append('FIELD_ACTION_TOPOLOGY_DRIFT')
    send = field_contract.get('send_binding') or {}
    send_edges = [x for x in (topo.get('edges') or []) if x.get('relation') == 'CONTROL_TRIGGERS_ACTION' and x.get('to') == send.get('action_uid')]
    if sorted(x.get('from') for x in send_edges) != [send.get('send_control_uid')]:
        blockers.append('SEND_ACTION_TOPOLOGY_NOT_UNIQUE')

    ai = doc('AI_INTERACTION_CONTINUITY_CONTRACT.yaml')
    source_conversation = raw.get('conversation_policy') or {}
    source_pipeline = raw.get('conversation_finalization_pipeline_contract') or {}
    if source_conversation and (ai.get('same_problem_rule') != source_conversation.get('same_problem_rule') or ai.get('exact_relevant_context') != source_conversation.get('exact_relevant_context')):
        blockers.append('AI_SAME_QUESTION_CONTEXT_CONTINUITY_MISSING')
    if source_pipeline and ai.get('single_finalization_pipeline') is not bool(source_pipeline.get('singular_pipeline')):
        blockers.append('AI_SAME_QUESTION_CONTEXT_CONTINUITY_MISSING')

    chain = doc('FUNCTIONAL_CHAIN_SPEC.yaml')
    required_projected = [
        'field_binding_contract','functional_workbench_topology_contract','working_memory_binding',
        'conversation_finalization_pipeline_contract','domain_materialization_operations',
        'work_item_lifecycle_contract','change_impact_contract','entity_operation_applicability_contract',
        'entity_hierarchy_contract','stage02_completeness_contract'
    ]
    if any(key not in chain for key in required_projected):
        blockers.append('FUNCTIONAL_CHAIN_PLANNING_CONTRACT_PROJECTION_INCOMPLETE')
    if chain.get('planning_baseline_sha256') != baseline:
        blockers.append('FUNCTIONAL_CHAIN_PLANNING_BASELINE_IDENTITY_DRIFT')

    return sorted(set(blockers))

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
        is_data_field = control.get('binding_semantics') == 'DATA_OR_DRAFT_STATE_ONLY'
        if is_data_field:
            if aid not in (None, '', 'NONE_FIELD_BINDING'):
                add(gaps, page, 'ARCHITECTURE_GAP', 'FIELD_MASQUERADES_AS_ACTION', cid, str(aid))
            if not control.get('data_binding'):
                add(gaps, page, 'ARCHITECTURE_GAP', 'FIELD_DATA_BINDING_MISSING', cid, 'data_binding absent')
        else:
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

    declared_stage02_completeness_gaps(page, raw, controls, idx(reg.get('objects_refs'), 'object_uid'), gaps)

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
    effective_raw, effective_contract = effective_page_contract(page, raw)
    scan = fresh_scan(page, effective_raw, unresolved_authority_by_ref)
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
    closure.extend(materialized_stage02_completeness_blockers(page_dir, effective_raw))
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
        'effective_contract_input': effective_contract,
        'planning_baseline_completeness': 'PASS' if not materialized_stage02_completeness_blockers(page_dir, effective_raw) else 'BLOCKED',
        'closure_blockers': sorted(set(closure)),
        'closure_blocker_count': len(set(closure)),
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
    'planning_baseline_completeness': 'PASS' if all(x.get('planning_baseline_completeness') == 'PASS' for x in pages.values()) else 'BLOCKED',
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
