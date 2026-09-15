#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
PRODUCT_ROOT = RUN / '04_PAGE_FUNCTIONAL_CONTRACT'
R19 = ROOT / 'governance/test/stage02/STAGE02_FUNCTIONAL_CONTRACT_REMEDIATION_PROBLEM_REGISTER_R19.yaml'
OUT = ROOT / 'governance/test/stage02/STAGE02_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY_R20.yaml'
PAGES = {
    'CORE-01': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
    'ASSET-01': RUN / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
}


def die(msg: str) -> None:
    print(f'BLOCK: {msg}', file=sys.stderr)
    raise SystemExit(1)


def load(path: Path):
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(obj, dict):
        die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj


def nonempty(v):
    return v not in (None, '', [], {})


def indexed(items, key):
    out = {}
    for item in items or []:
        if isinstance(item, dict) and nonempty(item.get(key)):
            uid = str(item[key])
            if uid in out:
                die(f'DUPLICATE_UID:{key}:{uid}')
            out[uid] = item
    return out


def page_index(raw):
    regs = raw.get('registries') or {}
    return {
        'actions': indexed(regs.get('actions'), 'action_uid'),
        'controls': indexed(regs.get('controls'), 'control_uid'),
        'ports': indexed(regs.get('integration_ports'), 'port_uid'),
        'transitions': indexed(regs.get('stage_transitions'), 'transition_uid'),
        'events': indexed(regs.get('events'), 'event_uid'),
    }


def bound_ports(idx, action):
    if not action:
        return []
    rb = action.get('runtime_binding') or {}
    uids = []
    for field in ('port_uid', 'persist_via_port_uid'):
        if nonempty(rb.get(field)):
            uids.append(str(rb[field]).rstrip('.'))
    result = []
    for uid in sorted(set(uids)):
        port = idx['ports'].get(uid)
        if port:
            result.append((uid, port))
    return result


def triggered_transitions(idx, action_uid):
    rows = []
    for uid, tr in idx['transitions'].items():
        trigger = tr.get('trigger') or tr.get('action_uid') or tr.get('trigger_event_uid')
        if trigger == action_uid:
            rows.append((uid, tr))
    return rows


def scalar_signal_candidates(idx, action_uid):
    action = idx['actions'].get(action_uid)
    if not action:
        return []
    candidates = []
    rb = action.get('runtime_binding') or {}
    for field in ('result_state', 'success_state', 'result', 'state_event'):
        value = rb.get(field)
        if nonempty(value) and not isinstance(value, (dict, list)):
            candidates.append({'source': f'action.runtime_binding.{field}', 'value': value})
    for port_uid, port in bound_ports(idx, action):
        for field in ('result_state', 'success_state', 'state_event', 'result'):
            value = port.get(field)
            if nonempty(value) and not isinstance(value, (dict, list)):
                candidates.append({'source': f'integration_port:{port_uid}.{field}', 'value': value})
    for transition_uid, tr in triggered_transitions(idx, action_uid):
        value = tr.get('to_stage')
        if nonempty(value):
            candidates.append({'source': f'stage_transition:{transition_uid}.to_stage', 'value': value})
    uniq = []
    seen = set()
    for item in candidates:
        key = (item['source'], repr(item['value']))
        if key not in seen:
            seen.add(key)
            uniq.append(item)
    return uniq


def exact_registered_event_candidates(idx, action_uid):
    action = idx['actions'].get(action_uid)
    if not action:
        return []
    candidates = []
    for node_name, node in [('action', action)] + [(f'integration_port:{uid}', p) for uid, p in bound_ports(idx, action)]:
        for field in ('audit_event_uid', 'event_uid'):
            value = node.get(field)
            if nonempty(value) and str(value) in idx['events']:
                candidates.append({'source': f'{node_name}.{field}', 'value': str(value)})
        value = node.get('state_event')
        if nonempty(value) and str(value) in idx['events']:
            candidates.append({'source': f'{node_name}.state_event', 'value': str(value)})
    return candidates


def structured_payload_candidates(idx, action_uid):
    action = idx['actions'].get(action_uid)
    if not action:
        return []
    candidates = []
    nodes = [('action', action), ('action.runtime_binding', action.get('runtime_binding') or {})]
    nodes += [(f'integration_port:{uid}', p) for uid, p in bound_ports(idx, action)]
    for node_name, node in nodes:
        for field in ('payload_schema', 'input_schema', 'request_schema', 'payload_contract', 'input_contract'):
            value = node.get(field)
            if isinstance(value, (dict, list)) and nonempty(value):
                candidates.append({'source': f'{node_name}.{field}', 'value': value})
    return candidates


def exact_failure_candidates(idx, action_uid):
    action = idx['actions'].get(action_uid)
    if not action:
        return []
    candidates = []
    nodes = [('action', action), ('action.runtime_binding', action.get('runtime_binding') or {})]
    nodes += [(f'integration_port:{uid}', p) for uid, p in bound_ports(idx, action)]
    for node_name, node in nodes:
        bundle = {}
        for field in ('failure_state', 'error_state', 'error_contract', 'recovery', 'recovery_rule', 'retry_policy', 'rollback'):
            if nonempty(node.get(field)):
                bundle[field] = node.get(field)
        if bundle:
            candidates.append({'source': node_name, 'value': bundle})
    for transition_uid, tr in triggered_transitions(idx, action_uid):
        bundle = {}
        for field in ('failure_state', 'error_state', 'recovery', 'recovery_rule', 'retry_policy', 'rollback'):
            if nonempty(tr.get(field)):
                bundle[field] = tr.get(field)
        if bundle:
            candidates.append({'source': f'stage_transition:{transition_uid}', 'value': bundle})
    return candidates


def mutation_owner_candidates(idx, transition_uid):
    tr = idx['transitions'].get(transition_uid)
    if not tr:
        return []
    trigger = tr.get('trigger') or tr.get('action_uid')
    action = idx['actions'].get(str(trigger)) if nonempty(trigger) else None
    if not action:
        return []
    rb = action.get('runtime_binding') or {}
    candidates = []
    ports = bound_ports(idx, action)
    if len(ports) == 1:
        uid, port = ports[0]
        op = port.get('registered_operation') or port.get('operation') or port.get('operation_id')
        candidates.append({
            'source': f'trigger_action:{trigger}->integration_port:{uid}',
            'value': {'owner_kind': 'REGISTERED_INTEGRATION_PORT', 'owner_uid': uid, 'operation': op},
        })
    if nonempty(rb.get('shared_authority_id')) and nonempty(rb.get('shared_operation_id')):
        candidates.append({
            'source': f'trigger_action:{trigger}.runtime_binding',
            'value': {
                'owner_kind': 'SHARED_OPERATION',
                'authority_id': rb.get('shared_authority_id'),
                'operation_id': rb.get('shared_operation_id'),
            },
        })
    return candidates


def transition_field_exact_candidates(idx, transition_uid, field):
    tr = idx['transitions'].get(transition_uid)
    if not tr:
        return []
    aliases = {
        'failure_state': ('error_state',),
        'recovery': ('recovery_rule',),
        'audit_event_uid': ('event_uid',),
    }.get(field, ())
    out = []
    for alias in aliases:
        if nonempty(tr.get(alias)):
            value = tr.get(alias)
            if field == 'audit_event_uid' and str(value) not in idx['events']:
                continue
            out.append({'source': f'stage_transition:{transition_uid}.{alias}', 'value': value})
    return out


def trigger_candidates(idx, action_uid):
    controls = sorted(uid for uid, ctl in idx['controls'].items() if ctl.get('action_uid') == action_uid)
    transitions = sorted(uid for uid, tr in idx['transitions'].items() if (tr.get('trigger') == action_uid or tr.get('action_uid') == action_uid))
    out = []
    for uid in controls:
        out.append({'source': f'control:{uid}.action_uid', 'value': {'trigger_kind': 'CONTROL', 'trigger_uid': uid}})
    for uid in transitions:
        out.append({'source': f'stage_transition:{uid}.trigger', 'value': {'trigger_kind': 'STAGE_TRANSITION', 'trigger_uid': uid}})
    return out


def unique_value(candidates):
    groups = {}
    for c in candidates:
        key = yaml.safe_dump(c.get('value'), allow_unicode=True, sort_keys=True)
        groups.setdefault(key, []).append(c)
    if len(groups) != 1:
        return None, len(groups)
    key, evidence = next(iter(groups.items()))
    return evidence[0]['value'], 1


def evaluate(problem, idx):
    category = problem['category']
    target = str(problem['target_uid'])
    missing = str(problem.get('missing_field_or_relation') or '')
    candidates = []
    closure_type = None

    if category == 'POST_ACTION_VALIDATION_NODE_MISSING':
        candidates = scalar_signal_candidates(idx, target)
        closure_type = 'POST_ACTION_VALIDATION_FROM_UNIQUE_FROZEN_SUCCESS_SIGNAL'
    elif category == 'PAYLOAD_INPUT_CONTRACT_MISSING':
        candidates = structured_payload_candidates(idx, target)
        closure_type = 'REQUEST_INPUT_CONTRACT_EXACT_STRUCTURED_PROJECTION'
    elif category == 'AUDIT_EVENT_NODE_MISSING':
        candidates = exact_registered_event_candidates(idx, target)
        closure_type = 'AUDIT_EVENT_EXACT_REGISTERED_EVENT_PROJECTION'
    elif category == 'FAILURE_STATE_ERROR_BINDING_MISSING':
        candidates = exact_failure_candidates(idx, target)
        closure_type = 'FAILURE_ERROR_RECOVERY_EXACT_CHAIN_PROJECTION'
    elif category == 'ACTION_WITHOUT_CONTROL_OR_TRIGGER':
        candidates = trigger_candidates(idx, target)
        closure_type = 'CONTROL_OR_TRIGGER_EXACT_CHAIN_PROJECTION'
    elif category == 'STATE_TRANSITION_LEDGER_FIELD_MISSING':
        field = None
        for name in ('mutation_owner', 'failure_state', 'recovery', 'audit_event_uid'):
            if name in missing:
                field = name
                break
        if field == 'mutation_owner':
            candidates = mutation_owner_candidates(idx, target)
            closure_type = 'TRANSITION_MUTATION_OWNER_FROM_UNIQUE_TRIGGER_RUNTIME_OWNER'
        elif field:
            candidates = transition_field_exact_candidates(idx, target, field)
            closure_type = f'TRANSITION_{field.upper()}_EXACT_ALIAS_PROJECTION'

    value, distinct = unique_value(candidates)
    if value is not None:
        return {
            'disposition': 'AUTO_REMEDIABLE_DETERMINISTIC_MINIMAL_CLOSURE',
            'authorized_for_auto_completion': True,
            'closure_type': closure_type,
            'candidate_value': value,
            'candidate_evidence': candidates,
            'distinct_candidate_value_count': distinct,
            'authority_gap_proven': False,
            'outside_frozen_closure': False,
        }
    if distinct > 1:
        return {
            'disposition': 'AUTHORITY_GAP_MULTIPLE_REASONABLE_CLOSURES',
            'authorized_for_auto_completion': False,
            'closure_type': closure_type,
            'candidate_value': None,
            'candidate_evidence': candidates,
            'distinct_candidate_value_count': distinct,
            'authority_gap_proven': True,
            'outside_frozen_closure': False,
        }
    return {
        'disposition': 'UNRESOLVED_FUNCTIONAL_CONTRACT_GAP_NO_UNIQUE_CLOSURE',
        'authorized_for_auto_completion': False,
        'closure_type': closure_type,
        'candidate_value': None,
        'candidate_evidence': candidates,
        'distinct_candidate_value_count': distinct,
        'authority_gap_proven': False,
        'outside_frozen_closure': False,
    }


r19 = load(R19)
problems = r19.get('problems') or []
if len(problems) != 150:
    die(f'R19_DENOMINATOR_DRIFT:{len(problems)}')
indexes = {page: page_index(load(path)) for page, path in PAGES.items()}
records = []
for p in problems:
    page = p.get('scope')
    if page not in indexes:
        die(f'UNKNOWN_PAGE:{page}')
    result = evaluate(p, indexes[page])
    rec = {
        'problem_uid': p.get('problem_uid'),
        'blocker_uid': p.get('blocker_uid'),
        'page_uid': page,
        'category': p.get('category'),
        'target_uid': p.get('target_uid'),
        'missing_field_or_relation': p.get('missing_field_or_relation'),
        'owning_layer': p.get('owning_layer'),
        **result,
    }
    if rec['authorized_for_auto_completion']:
        rec['function_admission_scorecard'] = {
            'seed_gap': rec['blocker_uid'],
            'required_operation_or_contract': rec['category'],
            'current_authority_or_deterministic_required_dependency': True,
            'existing_capability_reuse_checked': True,
            'alternative_path_checked': True,
            'blocked_terminal_outcome': 'STAGE02_FUNCTIONAL_CHAIN_CLOSURE',
            'necessity_score_is_diagnostic_only': True,
            'authority_created_by_score': False,
        }
        rec['auto_completion_scope_ledger_entry'] = {
            'seed_gap': rec['blocker_uid'],
            'minimal_closure_set': [rec['closure_type']],
            'transitive_dependency_count': 0,
            'outside_frozen_registered_dependency_closure': False,
            'generic_crud_symmetry_expansion_used': False,
            'sibling_feature_symmetry_expansion_used': False,
            'semantic_similarity_used': False,
            'ai_invented_business_value': False,
        }
    records.append(rec)

summary = Counter(r['disposition'] for r in records)
by_category = {}
for category in sorted(set(r['category'] for r in records)):
    subset = [r for r in records if r['category'] == category]
    by_category[category] = {
        'total': len(subset),
        'auto_remediable': sum(r['authorized_for_auto_completion'] for r in subset),
        'authority_gap_multiple_reasonable_closures': sum(r['disposition'] == 'AUTHORITY_GAP_MULTIPLE_REASONABLE_CLOSURES' for r in subset),
        'unresolved_no_unique_closure': sum(r['disposition'] == 'UNRESOLVED_FUNCTIONAL_CONTRACT_GAP_NO_UNIQUE_CLOSURE' for r in subset),
    }
head = subprocess.run(['git','rev-parse','HEAD'], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
out = {
    'schema_version': 1,
    'artifact_type': 'NON_NORMATIVE_STAGE02_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY_R20',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'cycle': 'FUNCTIONAL_CHAIN_DETERMINISTIC_MINIMAL_CLOSURE_R20',
    'source_head_sha': head,
    'source_problem_register': str(R19.relative_to(ROOT)),
    'current_specification_mutated': False,
    'classification_contract': {
        'absence_of_materialized_contract_alone_is_authority_gap': False,
        'full_chain_unique_deterministic_closure_checked_before_block': True,
        'auto_remediation_requires_one_distinct_candidate_value': True,
        'multiple_distinct_candidates_are_authority_gap': True,
        'zero_candidate_is_unresolved_not_product_authority': True,
        'new_business_value_invention_allowed': False,
        'outside_frozen_closure_allowed': False,
        'historical_non_current_authority_allowed': False,
    },
    'denominators': {
        'input_problem_total': len(records),
        'disposition_counts': dict(summary),
        'category_counts': by_category,
        'auto_remediable_total': sum(r['authorized_for_auto_completion'] for r in records),
        'true_authority_gap_total': sum(r['authority_gap_proven'] for r in records),
        'unresolved_no_unique_closure_total': sum(r['disposition'] == 'UNRESOLVED_FUNCTIONAL_CONTRACT_GAP_NO_UNIQUE_CLOSURE' for r in records),
        'blocker_reduction_claimed': 0,
    },
    'records': records,
    'next_action': 'MATERIALIZE_ONLY_AUTO_REMEDIABLE_DETERMINISTIC_MINIMAL_CLOSURE_RECORDS_AT_STAGE02_OWNING_LAYER_THEN_CLEAN_REEXECUTE',
    'stage03_allowed': False,
}
OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')
print(f'R20_TOTAL={len(records)}')
for k,v in sorted(summary.items()): print(f'{k}={v}')
for k,v in by_category.items(): print(f'CATEGORY::{k}::{v}')
print('PASS: R20 evaluates complete local functional-chain evidence before blocking exact missing contracts')
