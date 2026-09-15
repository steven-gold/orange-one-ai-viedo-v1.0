#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / 'governance/specifications/current/CANONICAL_RULE_REGISTRY.yaml'
EXPECTED_REGISTRY_UID = 'GOV-CANONICAL-RULE-REGISTRY-001'


def _canonical_digest(data: dict) -> str:
    scope = {k: data.get(k) for k in data.get('registry_digest_scope') or []}
    payload = json.dumps(scope, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def load_registry() -> dict:
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding='utf-8')) or {}
    if data.get('registry_uid') != EXPECTED_REGISTRY_UID:
        raise RuntimeError('CANONICAL_RULE_REGISTRY_UID_MISMATCH')
    actual = _canonical_digest(data)
    expected = data.get('registry_digest')
    if actual != expected:
        raise RuntimeError(f'CANONICAL_RULE_REGISTRY_DIGEST_MISMATCH expected={expected} actual={actual}')
    if data.get('consumer_contract', {}).get('lexical_hints_role') != 'SECONDARY_DEFENSE_ONLY':
        raise RuntimeError('LEXICAL_HINT_ROLE_DRIFT')
    if data.get('consumer_contract', {}).get('local_regex_or_synonym_taxonomy') != 'FORBIDDEN_WHEN_DUPLICATING_REGISTRY':
        raise RuntimeError('LOCAL_RULE_FORK_POLICY_DRIFT')
    return data


def scan_policy_text(text: str) -> list[dict]:
    data = load_registry()
    findings = []
    for semantic_type, spec in (data.get('semantic_types') or {}).items():
        if 'POLICY' not in (spec.get('forbidden_layers') or []):
            continue
        for pattern in spec.get('lexical_hints') or []:
            match = re.search(pattern, text)
            if match:
                findings.append({'semantic_type': semantic_type, 'match': match.group(0), 'pattern': pattern})
                break
    return findings


def required_rule_uids() -> set[str]:
    return set((load_registry().get('binding_contract') or {}).get('required_rule_uids') or [])
