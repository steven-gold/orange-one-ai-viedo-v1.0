#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / 'GOVERNANCE_CURRENT.yaml'
BINDING = ROOT / 'governance/test/SELECTED_PROFILE_HISTORY_BINDING.yaml'


def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        die('MISSING_REQUIRED_FILE:' + path.relative_to(ROOT).as_posix())
    try:
        return yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception as exc:
        die(f'YAML_PARSE:{path.relative_to(ROOT)}:{exc!r}')


def artifact_overlay(path: Path):
    text = path.read_text(encoding='utf-8')
    if text.lstrip().startswith('{'):
        try:
            return json.loads(text).get('governance_overlay')
        except Exception as exc:
            die(f'ARTIFACT_JSON_PARSE:{path.relative_to(ROOT)}:{exc!r}')
    m = re.search(r'^governance_overlay:\s*([^\s#]+)', text, re.MULTILINE)
    return m.group(1) if m else None


current = load_yaml(CURRENT)
binding = load_yaml(BINDING)
selected = current.get('selected_execution_profile') or {}
binding_profile = binding.get('selected_execution_profile') or {}

if binding.get('artifact_type') != 'PROFILE_SPECIFIC_HISTORICAL_ARTIFACT_BINDING':
    die('PROFILE_HISTORY_BINDING_TYPE_INVALID')
if binding.get('normative_authority') is not False:
    die('PROFILE_HISTORY_BINDING_MUST_BE_NON_NORMATIVE')
if binding.get('global_governance_projector') is not False:
    die('PROFILE_HISTORY_BINDING_MUST_NOT_PROJECT_GLOBAL_GOVERNANCE')
if 'current_governance_resolution' in binding:
    die('PROFILE_HISTORY_BINDING_MUST_NOT_COPY_CURRENT_GOVERNANCE_RESOLUTION')
if binding_profile.get('owner_ref') != 'GOVERNANCE_CURRENT.yaml':
    die('PROFILE_HISTORY_BINDING_OWNER_INVALID')
if binding_profile.get('profile_uid') != selected.get('profile_uid'):
    die('PROFILE_HISTORY_BINDING_PROFILE_UID_DRIFT')
if binding_profile.get('registry_ref') != selected.get('registry'):
    die('PROFILE_HISTORY_BINDING_PROFILE_REGISTRY_DRIFT')
if binding_profile.get('global_normative_authority') is not False:
    die('PROFILE_HISTORY_BINDING_PROFILE_AUTHORITY_INVALID')

profile_path = ROOT / str(selected.get('registry') or '')
profile = load_yaml(profile_path)
if profile.get('artifact_type') != 'EXECUTION_PROFILE_REGISTRY':
    die('SELECTED_PROFILE_REGISTRY_TYPE_INVALID')
if profile.get('layer_classification') != 'EXECUTION_PROFILE':
    die('SELECTED_PROFILE_REGISTRY_LAYER_INVALID')
if profile.get('global_normative_authority') is not False:
    die('SELECTED_PROFILE_REGISTRY_GLOBAL_AUTHORITY_INVALID')
valid_steps = {str(x.get('stage_uid')) for x in (profile.get('stages') or []) if x.get('stage_uid')}

scope = binding.get('scope') or {}
if not scope:
    die('PROFILE_HISTORY_BINDING_SCOPE_EMPTY')
artifact_count = 0
for scope_uid, rec in scope.items():
    if not isinstance(rec, dict):
        die(f'PROFILE_HISTORY_SCOPE_INVALID:{scope_uid}')
    step_uid = str(rec.get('profile_step_uid') or '')
    if step_uid not in valid_steps:
        die(f'PROFILE_HISTORY_STEP_NOT_IN_SELECTED_PROFILE:{scope_uid}:{step_uid}')
    artifacts = rec.get('artifacts') or []
    if not artifacts:
        die(f'PROFILE_HISTORY_ARTIFACTS_EMPTY:{scope_uid}')
    for artifact in artifacts:
        rel = str(artifact.get('artifact_ref') or '')
        expected = artifact.get('creation_governance_overlay')
        if not rel or expected is None:
            die(f'PROFILE_HISTORY_ARTIFACT_RECORD_INVALID:{scope_uid}')
        path = ROOT / rel
        if not path.is_file():
            die(f'PROFILE_HISTORY_ARTIFACT_MISSING:{rel}')
        actual = artifact_overlay(path)
        if actual != expected:
            die(f'PROFILE_HISTORY_PROVENANCE_DRIFT:{rel}:expected={expected}:actual={actual}')
        artifact_count += 1

print(f'PASS: selected-profile historical artifact binding scopes={len(scope)} artifacts={artifact_count}')
print('PASS: historical profile step identities remain profile-local evidence, not Current Governance projectors')
