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

_PROHIBITION_OR_META = re.compile(
    r'(?i)(?:\bmust[_ ]?not\b|\bmay[_ ]?not\b|\bforbidden\b|\bforbid\b|'
    r'\bblock(?:ed)?\b|\bmay_not_define\b|\bmust_not\b|\bwithout requiring\b|'
    r'\bdoes not require\b|\bdo not require\b|禁止|不得|不可|不應|不能)'
)
_POLICY_SENTINELS = {'BLOCK', 'FORBIDDEN', 'DENY', 'FALSE', 'TRUE', 'NOT_APPLICABLE'}
_CONCRETE_BY_LEXICAL_FORM = {
    'FIXED_WORK_UNIT_ID',
    'FIXED_WORK_UNIT_DENOMINATOR',
    'REMEDIATION_ROUND_ID',
}


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


def _line_context(text: str, start: int, end: int) -> tuple[str, int, int]:
    line_start = text.rfind('\n', 0, start) + 1
    line_end = text.find('\n', end)
    if line_end < 0:
        line_end = len(text)
    return text[line_start:line_end], start - line_start, end - line_start


def _is_confirmed_policy_binding(semantic_type: str, line: str, local_start: int, local_end: int) -> bool:
    # Lexical hints are discovery only. A prohibition/definition of a forbidden semantic
    # type is not itself a forbidden binding.
    if _PROHIBITION_OR_META.search(line):
        return False

    if semantic_type in _CONCRETE_BY_LEXICAL_FORM:
        return True

    tail = line[local_end:]
    assignment = re.match(r'\s*[:=]\s*(.+?)\s*$', tail)
    if assignment:
        value = assignment.group(1).strip().strip("\"'")
        if value and value.upper() not in _POLICY_SENTINELS:
            return True

    # Free-form Mother prose can still contain a concrete implementation binding.
    if semantic_type == 'IMPLEMENTATION_PATH':
        return bool(re.search(r'(?i)(?:\.github/|governance/|[A-Za-z0-9_.-]+/)[A-Za-z0-9_./-]+\.(?:ya?ml|py|ts|tsx|js|jsx)\b', tail))
    if semantic_type in {'RUN_ID', 'ATTEMPT_ID', 'EXECUTION_TOOL_ID'}:
        return bool(re.search(r'''[`"']?[A-Z][A-Z0-9_.:/-]{3,}[`"']?''', tail))

    return False


def scan_policy_text(text: str) -> list[dict]:
    """Return only confirmed reusable-POLICY bindings.

    Registry lexical hints nominate candidates. They do not become violations until
    context confirms a concrete binding; this keeps lexical matching secondary to
    semantic/layer enforcement as required by the canonical registry.
    """
    data = load_registry()
    findings = []
    for semantic_type, spec in (data.get('semantic_types') or {}).items():
        if 'POLICY' not in (spec.get('forbidden_layers') or []):
            continue
        for pattern in spec.get('lexical_hints') or []:
            for match in re.finditer(pattern, text):
                line, local_start, local_end = _line_context(text, match.start(), match.end())
                if not _is_confirmed_policy_binding(semantic_type, line, local_start, local_end):
                    continue
                findings.append({
                    'semantic_type': semantic_type,
                    'match': match.group(0),
                    'pattern': pattern,
                    'context': line.strip(),
                })
                break
            if findings and findings[-1].get('semantic_type') == semantic_type:
                break
    return findings


def required_rule_uids() -> set[str]:
    return set((load_registry().get('binding_contract') or {}).get('required_rule_uids') or [])
