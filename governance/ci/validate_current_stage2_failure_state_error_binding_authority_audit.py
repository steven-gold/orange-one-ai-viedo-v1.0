#!/usr/bin/env python3
from pathlib import Path
from collections import defaultdict
import json, subprocess, yaml

root = Path('.')
base = root / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
gap_path = base / 'FUNCTIONAL_CHAIN_GAP_LEDGER_R4.yaml'
manifest_path = base / 'EXTERNAL_AUTHORITY/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml'

sources = {
    'CURRENT_AUTHORITY_MANIFEST': manifest_path,
    'CORE_PAGE_AUTHORITY': base / 'EXTERNAL_AUTHORITY/ASYNC_REMAINING/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml',
    'ASSET_PAGE_AUTHORITY': base / 'EXTERNAL_AUTHORITY/ASYNC_REMAINING/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml',
    'SYSTEM_AUTHORITY': base / 'EXTERNAL_AUTHORITY/GAP-008/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml',
    'AIAPI_AUTHORITY': base / 'EXTERNAL_AUTHORITY/GAP-008/ACPOS_AIAPI-01_FINAL_LOCKED_ENCODING.yaml',
    'OPERATION_REGISTRY': base / 'EXTERNAL_AUTHORITY/GAP-008/operation_registry.yaml',
    'SHARED_RUNTIME_OPERATION_AUTHORITY': base / 'EXTERNAL_AUTHORITY/GAP-006/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml',
    'ASYNC_QUEUE_RUNTIME_AUTHORITY': base / 'EXTERNAL_AUTHORITY/ASYNC/ACPOS_PRODUCTION_ASYNC_QUEUE_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml',
    'PROVIDER_ADAPTER_AUTHORITY': base / 'EXTERNAL_AUTHORITY/GAP-005/ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT_FINAL_LOCKED_V1.3.yaml',
}

LOCKED = {
    gap_path: '29855a6aa9940b6ea64ca75d355c60acda3d2b94',
    sources['CURRENT_AUTHORITY_MANIFEST']: '465329b6fb19b8e44c3083a9f280015ee95cc55c',
    sources['CORE_PAGE_AUTHORITY']: '9490f3bcc28c5511bc04d6c3ce53c026e3c4667f',
    sources['ASSET_PAGE_AUTHORITY']: '9668e2307c722ea4cf64f93f07c92da1b3abcc28',
    sources['SYSTEM_AUTHORITY']: 'b09b7ca50313172ea021d9da0c8d57f2942f7b19',
    sources['AIAPI_AUTHORITY']: 'dd9f05e295af57cc833e90d1a12030c8198580c6',
    sources['OPERATION_REGISTRY']: '7d234cc2f2f831b82f2007403c71d4008b46a012',
    sources['SHARED_RUNTIME_OPERATION_AUTHORITY']: '12dbdf59a60df5b1cb3d3b18666209c05bb0c0a3',
    sources['ASYNC_QUEUE_RUNTIME_AUTHORITY']: 'ac3619b3bc547ce06f244c239fa69d3cac78da76',
    sources['PROVIDER_ADAPTER_AUTHORITY']: '12ef6d233e09f84571dd5d694ae8e3789ae70502',
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


def walk(obj, path=()):
    if isinstance(obj, dict):
        yield path, obj
        for k, v in obj.items():
            yield from walk(v, path + (str(k),))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, path + (str(i),))


def nonempty(v):
    return v not in (None, '', [], {})


for path, blob in LOCKED.items():
    if gitobj(path) != blob:
        die('locked bounded Authority/source drift: ' + str(path))

G = load(gap_path)
manifest = load(manifest_path)
if ((manifest.get('load_policy') or {}).get('only_listed_files_are_current_authority') is not True or
        (manifest.get('load_policy') or {}).get('unlisted_authority_or_spec_file') != 'DO_NOT_LOAD_FOR_CURRENT_CONSTRUCTION'):
    die('Current Authority manifest load policy drift')

cat = (G.get('category_groups') or {}).get('FAILURE_STATE_ERROR_BINDING_MISSING') or {}
if cat.get('class') != 'ARCHITECTURE_GAP':
    die('failure-state category class drift')
asset_group = cat.get('ASSET-01') or {}
gap_actions = asset_group.get('action_uids') or []
if len(gap_actions) != 44 or asset_group.get('expanded_gap_count') != 44:
    die('R4 failure-state universe must remain exact 44')
if ((G.get('summary') or {}).get('categories') or {}).get('FAILURE_STATE_ERROR_BINDING_MISSING') != 44:
    die('R4 failure-state category count drift')
if ((G.get('summary') or {}).get('classes') or {}).get('ARCHITECTURE_GAP') != 133 or (G.get('summary') or {}).get('total') != 167:
    die('R4 architecture/functional totals drift')

source_docs = {role: load(path) for role, path in sources.items()}

# Same-source exact error registries: an action may only consume a recovery by explicit error_uid reference.
source_error_recovery = {}
for role, doc in source_docs.items():
    reg = {}
    for _, node in walk(doc):
        euid = node.get('error_uid') if isinstance(node, dict) else None
        rec = node.get('recovery') if isinstance(node, dict) else None
        if euid and nonempty(rec):
            reg[euid] = rec
    source_error_recovery[role] = reg

rows = []
authorized_actions = []
for aid in gap_actions:
    candidates = []
    authorized = []
    for role, doc in source_docs.items():
        for pth, node in walk(doc):
            if node.get('action_uid') != aid:
                continue
            error_uid = node.get('error_uid')
            direct_recovery = node.get('recovery')
            failure_state = node.get('failure_state')
            linked_error_recovery = source_error_recovery[role].get(error_uid) if error_uid else None
            exact_failure_recovery = nonempty(failure_state) and nonempty(direct_recovery)
            exact_error_recovery = bool(error_uid and (nonempty(direct_recovery) or nonempty(linked_error_recovery)))
            is_authorized = exact_failure_recovery or exact_error_recovery
            candidate = {
                'source_role': role,
                'node_path': '/'.join(pth),
                'error_uid': error_uid,
                'failure_state': failure_state,
                'direct_recovery': direct_recovery,
                'linked_error_recovery': linked_error_recovery,
                'exact_binding_authorized': is_authorized,
            }
            candidates.append(candidate)
            if is_authorized:
                authorized.append(candidate)
    if authorized:
        authorized_actions.append(aid)
    rows.append({
        'action_uid': aid,
        'exact_action_nodes_found': len(candidates),
        'candidate_nodes': candidates,
        'authorized_exact_failure_bindings': authorized,
        'authorized_for_gap_removal': bool(authorized),
        'gap_status_after_audit': 'RESOLVABLE_BY_EXACT_CURRENT_AUTHORITY' if authorized else 'OPEN',
    })

summary = {
    'gap_action_total': 44,
    'bounded_authority_source_count': len(sources),
    'actions_with_any_exact_action_node': sum(1 for r in rows if r['exact_action_nodes_found'] > 0),
    'exact_action_node_total': sum(r['exact_action_nodes_found'] for r in rows),
    'actions_with_exact_failure_binding_authorized_for_removal': len(authorized_actions),
    'authorized_action_uids': authorized_actions,
    'unresolved_gap_count_after_audit': 44 - len(authorized_actions),
    'audit_changes_current_gap_count': False,
    'current_failure_state_error_binding_gap_count': 44,
    'current_architecture_gap_total': 133,
    'current_functional_gap_total': 167,
}

out = {
    'schema_version': 1,
    'artifact_type': 'FAILURE_STATE_ERROR_BINDING_AUTHORITY_AUDIT_RESULT',
    'artifact_uid': 'FRESH-RUN-003-STAGE2-FAILURE-STATE-ERROR-BINDING-AUTHORITY-AUDIT-V212-R1',
    'governance_overlay': 'v2.1.12',
    'run_uid': 'FRESH-RUN-003',
    'stage_uid': 'STAGE-02',
    'source_gap_ledger_git_blob': LOCKED[gap_path],
    'bounded_authority_sources': [
        {'role': role, 'ref': str(path.relative_to(root)), 'git_blob': LOCKED[path]}
        for role, path in sources.items()
    ],
    'acceptance_rule': {
        'exact_action_uid_required': True,
        'accepted_failure_contracts': [
            'same mapping node contains exact action_uid + failure_state + recovery',
            'same mapping node contains exact action_uid + error_uid, with recovery on same node or exact same-source error_uid registry entry',
        ],
        'generic_error_recovery_join': 'FORBIDDEN',
        'operation_route_or_runtime_owner_as_failure_contract': 'FORBIDDEN',
        'cross_source_semantic_join': 'FORBIDDEN',
        'ai_guess_or_default_substitution': 'FORBIDDEN',
    },
    'rows': rows,
    'summary': summary,
    'functional_completion_claim': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
}
Path('stage2_failure_state_error_binding_authority_audit.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
)
print('PASS: bounded Current Authority failure-state audit scanned exact 44-action gap universe')
print('PASS: exact action binding is necessary; generic error/recovery, route, runtime owner or cross-source semantic joins are forbidden')
print('PASS: this audit classifies candidates only and never mutates Current gap totals')
print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
