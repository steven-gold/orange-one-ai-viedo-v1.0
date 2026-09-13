#!/usr/bin/env python3
from pathlib import Path
from collections import defaultdict
import json, subprocess, yaml

root = Path('.')
base = root / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
gap_path = base / 'FUNCTIONAL_CHAIN_GAP_LEDGER_R4.yaml'
asset_path = base / 'EXTERNAL_AUTHORITY/ASYNC_REMAINING/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'
detector_path = root / 'governance/ci/validate_current_stage2_functional_chain_preflight.py'

LOCKED = {
    gap_path: '29855a6aa9940b6ea64ca75d355c60acda3d2b94',
    asset_path: '9668e2307c722ea4cf64f93f07c92da1b3abcc28',
    detector_path: '0fd730c141d4104bfdcb97e0899aa1a5841d643e',
}


def die(msg):
    raise SystemExit(msg)


def load(path):
    doc = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(doc, dict):
        die('mapping required: ' + str(path))
    return doc


def gitobj(path):
    r = subprocess.run(['git', 'rev-parse', 'HEAD:' + str(path)], text=True, capture_output=True)
    if r.returncode:
        die('git object missing: ' + str(path))
    return r.stdout.strip()


def idx(items, key):
    return {x.get(key): x for x in (items or []) if isinstance(x, dict) and x.get(key)}


for path, blob in LOCKED.items():
    if gitobj(path) != blob:
        die('locked source/detector drift: ' + str(path))

G = load(gap_path)
A = load(asset_path)
reg = A.get('registries') or {}
actions = idx(reg.get('actions'), 'action_uid')
errors = idx(reg.get('errors'), 'error_uid')
transitions = idx(reg.get('stage_transitions'), 'transition_uid')

if len(actions) != 44:
    die(f'ASSET action universe drift: expected 44 got {len(actions)}')
if len(errors) != 17:
    die(f'ASSET error registry drift: expected 17 got {len(errors)}')
if len(transitions) != 5:
    die(f'ASSET transition universe drift: expected 5 got {len(transitions)}')

cat = (G.get('category_groups') or {}).get('FAILURE_STATE_ERROR_BINDING_MISSING') or {}
if cat.get('class') != 'ARCHITECTURE_GAP':
    die('failure-state category class drift')
row = cat.get('ASSET-01') or {}
gap_actions = row.get('action_uids') or []
if len(gap_actions) != 44 or row.get('expanded_gap_count') != 44:
    die('R4 failure-state gap universe must remain exact 44')
if set(gap_actions) != set(actions):
    die('R4 failure-state gap universe no longer equals exact ASSET action universe')
if ((G.get('summary') or {}).get('categories') or {}).get('FAILURE_STATE_ERROR_BINDING_MISSING') != 44:
    die('R4 failure-state category count drift')

transitions_by_action = defaultdict(list)
for tid, t in transitions.items():
    trig = t.get('action_uid') or t.get('trigger_event_uid') or t.get('trigger')
    if trig in actions:
        transitions_by_action[trig].append((tid, t))

rows = []
resolved = []
for aid in gap_actions:
    a = actions.get(aid)
    if not a:
        die('gap action missing from ASSET action registry: ' + aid)
    err_uid = a.get('error_uid')
    err = errors.get(err_uid) if err_uid else None
    err_recovery = err.get('recovery') if isinstance(err, dict) else None
    transition_rows = transitions_by_action.get(aid, [])
    transition_recoveries = [
        {'transition_uid': tid, 'recovery': t.get('recovery')}
        for tid, t in transition_rows
        if t.get('recovery') not in (None, '', [], {})
    ]
    direct_valid = bool(err_uid and err is not None and err_recovery not in (None, '', [], {}))
    transition_valid = bool(transition_recoveries)
    detector_resolved = direct_valid or transition_valid
    if detector_resolved:
        resolved.append(aid)
    rows.append({
        'action_uid': aid,
        'direct_error_uid': err_uid,
        'direct_error_ref_exists': err is not None,
        'direct_error_recovery': err_recovery,
        'direct_error_recovery_valid': direct_valid,
        'triggered_transition_uids': [tid for tid, _ in transition_rows],
        'transition_recovery_bindings': transition_recoveries,
        'transition_recovery_valid': transition_valid,
        'detector_resolution_available': detector_resolved,
        'gap_status': 'OPEN' if not detector_resolved else 'RESOLVABLE_FROM_EXISTING_PAGE_AUTHORITY',
    })

# The R4 ledger was generated from the same immutable page blob using the locked detector rule.
# Any resolvable row here therefore means the ledger/detector evidence has drifted and must fail closed.
if resolved:
    die('R4 failure-state gap ledger contradicts exact current page bindings: ' + ','.join(resolved))

summary = {
    'gap_action_total': 44,
    'asset_action_total': len(actions),
    'asset_error_registry_total': len(errors),
    'asset_transition_total': len(transitions),
    'actions_with_direct_error_uid': sum(1 for r in rows if r['direct_error_uid']),
    'actions_with_valid_direct_error_recovery': sum(1 for r in rows if r['direct_error_recovery_valid']),
    'actions_with_triggered_transition': sum(1 for r in rows if r['triggered_transition_uids']),
    'actions_with_transition_recovery': sum(1 for r in rows if r['transition_recovery_valid']),
    'detector_resolvable_gap_count': len(resolved),
    'unresolved_gap_count': 44 - len(resolved),
    'inventory_changes_current_gap_count': False,
    'current_failure_state_error_binding_gap_count': 44,
    'current_architecture_gap_total': 133,
    'current_functional_gap_total': 167,
}

out = {
    'schema_version': 1,
    'artifact_type': 'FAILURE_STATE_ERROR_BINDING_INVENTORY_RESULT',
    'artifact_uid': 'FRESH-RUN-003-STAGE2-FAILURE-STATE-ERROR-BINDING-INVENTORY-V212-R1',
    'governance_overlay': 'v2.1.12',
    'run_uid': 'FRESH-RUN-003',
    'stage_uid': 'STAGE-02',
    'source_gap_ledger_git_blob': LOCKED[gap_path],
    'source_asset_page_authority_git_blob': LOCKED[asset_path],
    'source_detector_git_blob': LOCKED[detector_path],
    'detector_rule': 'Resolve only when action.error_uid references an existing error with non-empty recovery, or an exact transition triggered by that action has non-empty recovery.',
    'rows': rows,
    'summary': summary,
    'functional_completion_claim': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
}
Path('stage2_failure_state_error_binding_inventory.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
)
print('PASS: exact R4 failure-state/error-binding universe = 44 ASSET actions')
print('PASS: inventory recomputes locked detector resolution from direct error_uid/error recovery or exact transition recovery only')
print('PASS: no R4 gap is removed by this inventory; Current architecture=133, functional=167, site/deploy blocked')
print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
