#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / 'governance/specifications/REGISTRY.yaml'


def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        die('MISSING_REQUIRED_FILE:' + path.relative_to(ROOT).as_posix())
    try:
        value = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception as exc:
        die(f'YAML_PARSE:{path.relative_to(ROOT)}:{exc!r}')
    if not isinstance(value, dict):
        die('MAPPING_REQUIRED:' + path.relative_to(ROOT).as_posix())
    return value


registry = load_yaml(REGISTRY)
rules_root = registry.get('rules_root')
lifecycle_rel = registry.get('lifecycle_registry')
if not isinstance(rules_root, str) or not rules_root:
    die('REGISTRY_RULES_ROOT_MISSING')
if not isinstance(lifecycle_rel, str) or not lifecycle_rel:
    die('REGISTRY_LIFECYCLE_REGISTRY_MISSING')
manifest = load_yaml(ROOT / rules_root / 'SPECIFICATION_MANIFEST.yaml')
profile_path = ROOT / lifecycle_rel
profile = load_yaml(profile_path)

if manifest.get('policy_scope') != 'PRODUCT_SYSTEM_AND_EXECUTION_PROFILE_NEUTRAL':
    die('CURRENT_POLICY_SCOPE_NOT_PROFILE_NEUTRAL')
if profile.get('artifact_type') != 'EXECUTION_PROFILE_REGISTRY':
    die('SELECTED_PROFILE_REGISTRY_TYPE_INVALID')
if profile.get('layer_classification') != 'EXECUTION_PROFILE':
    die('SELECTED_PROFILE_REGISTRY_LAYER_INVALID')
if profile.get('global_normative_authority') is not False:
    die('SELECTED_PROFILE_REGISTRY_GLOBAL_AUTHORITY_INVALID')
if profile.get('profile_may_weaken_common_policy') is not False:
    die('SELECTED_PROFILE_MAY_NOT_WEAKEN_COMMON_POLICY')
if not profile.get('profile_uid'):
    die('SELECTED_PROFILE_UID_MISSING')

stages = profile.get('stages') or []
if int(profile.get('profile_local_denominator') or -1) != len(stages):
    die('SELECTED_PROFILE_DENOMINATOR_DRIFT')
step_uids = [str(x.get('stage_uid')) for x in stages if isinstance(x, dict) and x.get('stage_uid')]
if len(step_uids) != len(stages) or len(step_uids) != len(set(step_uids)):
    die('SELECTED_PROFILE_STAGE_UID_DUPLICATE_OR_MISSING')
stage_by_uid = {str(x.get('stage_uid')): x for x in stages}

required_scalars = ('stage_uid', 'name', 'scope_mode', 'entry_gate', 'exit_gate', 'next_stage_uid', 'pre_execution_gate')
for step in stages:
    if not isinstance(step, dict):
        die('SELECTED_PROFILE_STAGE_RECORD_INVALID')
    uid = str(step.get('stage_uid') or '')
    for field in required_scalars:
        if step.get(field) in (None, ''):
            die(f'SELECTED_PROFILE_STAGE_FIELD_MISSING:{uid}:{field}')
    inputs = step.get('inputs') or []
    origins = step.get('input_origins') or {}
    operations = step.get('operations') or []
    outputs = step.get('outputs') or []
    producers = step.get('output_producers') or {}
    validators = step.get('validators') or []
    evidence = step.get('required_evidence') or []
    refs = step.get('required_normative_section_uids') or []
    for name, rows in (
        ('inputs', inputs), ('operations', operations), ('outputs', outputs),
        ('validators', validators), ('required_evidence', evidence),
        ('required_normative_section_uids', refs),
    ):
        if not isinstance(rows, list) or not rows or len(rows) != len(set(map(str, rows))):
            die(f'SELECTED_PROFILE_STAGE_LIST_INVALID:{uid}:{name}')
    if not isinstance(origins, dict) or set(origins) != set(inputs):
        die(f'SELECTED_PROFILE_INPUT_ORIGIN_COVERAGE_INVALID:{uid}')
    if not isinstance(producers, dict) or set(producers) != set(outputs):
        die(f'SELECTED_PROFILE_OUTPUT_PRODUCER_COVERAGE_INVALID:{uid}')
    missing_producers = sorted({str(v) for v in producers.values()} - {str(v) for v in operations})
    if missing_producers:
        die(f'SELECTED_PROFILE_OUTPUT_PRODUCER_NOT_OPERATION:{uid}:{missing_producers}')
    if step.get('pre_execution_gate') != 'GOVERNANCE_LOAD_RECEIPT_PASS':
        die(f'SELECTED_PROFILE_PREEXECUTION_GATE_DRIFT:{uid}')

for step in stages:
    uid = str(step.get('stage_uid'))
    nxt = str(step.get('next_stage_uid') or '')
    if nxt in stage_by_uid:
        predecessor_exit = str(step.get('exit_gate') or '')
        successor_entry = str(stage_by_uid[nxt].get('entry_gate') or '')
        exact_or_stricter = successor_entry == predecessor_exit or successor_entry.startswith(predecessor_exit + '_AND_')
        if not exact_or_stricter:
            die(f'SELECTED_PROFILE_SUCCESSOR_GATE_MISMATCH:{uid}->{nxt}:{predecessor_exit}:{successor_entry}')

scope_contract = profile.get('execution_scope_contract') or {}
if scope_contract.get('current_scope_artifact') != 'PRODUCT_STAGE_EXECUTION_CURRENT_SCOPE_MANIFEST':
    die('CURRENT_SCOPE_ARTIFACT_NOT_PRODUCT_OWNED')
if scope_contract.get('current_scope_owner_layer') != 'PRODUCT_EXECUTION_WORKLINE':
    die('CURRENT_SCOPE_OWNER_LAYER_DRIFT')
if scope_contract.get('governance_branch_may_persist_current_product_scope') is not False:
    die('GOVERNANCE_BRANCH_PRODUCT_SCOPE_PERSISTENCE_NOT_BLOCKED')
if registry.get('product_execution_branch') != '0921acpos':
    die('PRODUCT_EXECUTION_BRANCH_DRIFT')
for forbidden in ('ACTIVE_WORK_UNIT', 'CURRENT_EXECUTION_SCOPE', 'PRODUCT_EXECUTION_EVIDENCE', 'PREEXECUTION_RECEIPT'):
    if forbidden not in (registry.get('forbidden_in_ruleset_branch') or []):
        die('RULESET_BRANCH_FORBIDDEN_PRODUCT_STATE_MISSING:' + forbidden)

print(f"PASS: selected execution profile {profile.get('profile_uid')} resolves from Current Registry as non-global execution profile")
print(f'PASS: selected profile local denominator={len(stages)} structural contracts complete')
print('PASS: Current product scope/run-state ownership is isolated to product execution workline')
print('PASS: governance branch resolves Current exclusively from Registry and contains no product run-state root')
