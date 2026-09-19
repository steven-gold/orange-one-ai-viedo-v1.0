#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"
REPORT = ROOT / "governance" / "test" / "ACTIVE_CONSUMER_REFERENCE_INTEGRITY_REPORT.json"
REGISTRY = ROOT / "governance/specifications/REGISTRY.yaml"
NEGATIVE_MATRIX = ROOT / "governance/test/EXECUTION_CLOSURE_NEGATIVE_REGRESSION_MATRIX.yaml"

EXEC_REF = re.compile(
    r"python(?:3)?\s+(?:-m\s+)?"
    r"((?:governance/(?:ci|test)|\.github/(?:governance-source|governance-maintenance))/[A-Za-z0-9_./-]+\.py)"
)
LOCAL_WORKFLOW_REF = re.compile(r"uses:\s*\./(\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml)")
SEMVER_LOCATOR = re.compile(r"governance/(?:current|specifications)/v\d+(?:\.\d+)+")
UNSAFE_TERMINAL_TOKENS = ("PASS_EXECUTION_SOURCE_HEAD", "CLOSED_VERIFIED")
CURRENT_STATE_TOKENS = ("governance/test/ACTIVE_STATE.yaml", "ACTIVE_STATE.yaml")
RUN_ID_TOKENS = ("GITHUB_RUN_ID", "github.run_id")
DYNAMIC_REPLAY_EXECUTABLES = (
    ".github/workflows/fresh-stage-replay.yml",
    ".github/governance-maintenance/run_fresh_stage_replay.py",
    ".github/governance-maintenance/finalize_fresh_stage_replay.py",
    "governance/ci/run_current_stage2_actual_test.py",
)
FIXED_REPLAY_IDENTITY_PATTERNS = {
    "RUN_ROOT": re.compile(r"\bfresh_run_\d+\b"),
    "RUN_UID": re.compile(r"\bFRESH-RUN-\d+\b"),
    "GOVERNANCE_UID": re.compile(r"\bGOV-REV-\d{8}-[A-Z0-9-]+\b"),
    "DISPLAY_VERSION": re.compile(r"(?<![A-Za-z0-9_-])v\d+\.\d+\.\d+\b"),
    "ROUND_LABEL": re.compile(r"\bR\d+\b"),
    "PRODUCT_UID": re.compile(r"\b(?:CORE|ASSET|VIDEO|EDIT|VOICE|QA|SYS|ERP|AIAPI)-\d+\b", re.IGNORECASE),
    "COMPACT_PRODUCT_UID": re.compile(r"\b(?:CORE|ASSET|VIDEO|EDIT|VOICE|QA|SYS|ERP|AIAPI)\d+\b", re.IGNORECASE),
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(rel(path))
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def deep_get(data, dotted: str):
    if dotted == "ROOT":
        return data
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(dotted)
        cur = cur[part]
    return cur


def workflow_executable_refs(text: str) -> set[str]:
    return {m.group(1) for m in EXEC_REF.finditer(text)}


def _string_constants(node: ast.AST) -> list[str]:
    out: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            out.append(child.value)
    return out


def python_executable_refs(text: str) -> set[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    refs: set[str] = set()
    allowed = re.compile(
        r"^((?:governance/(?:ci|test)|\.github/(?:governance-source|governance-maintenance))/[A-Za-z0-9_./-]+\.py)$"
    )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        literals = []
        for arg in node.args:
            literals.extend(_string_constants(arg))
        for kw in node.keywords:
            literals.extend(_string_constants(kw.value))
        for lit in literals:
            for match in EXEC_REF.finditer(lit):
                refs.add(match.group(1))
            m = allowed.fullmatch(lit.strip())
            if m and any(x in {"python", "python3"} for x in literals):
                refs.add(m.group(1))
    return refs


def _yaml_scalar_strings(text: str) -> list[str]:
    try:
        obj = yaml.load(text, Loader=yaml.BaseLoader)
    except yaml.YAMLError:
        return []
    out: list[str] = []
    def walk(value) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                walk(k)
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
        elif isinstance(value, str):
            out.append(value)
    walk(obj)
    return out


def fixed_dynamic_replay_identities(path_rel: str, text: str) -> list[str]:
    if path_rel not in DYNAMIC_REPLAY_EXECUTABLES:
        return []
    if path_rel.endswith((".yml", ".yaml")):
        strings = _yaml_scalar_strings(text)
    else:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return ["PYTHON_PARSE_ERROR"]
        strings = [
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
    findings: list[str] = []
    for value in strings:
        for kind, pattern in FIXED_REPLAY_IDENTITY_PATTERNS.items():
            if pattern.search(value):
                findings.append(f"{kind}:{value}")
    return sorted(set(findings))


def unsafe_preterminal_current_projection(text: str) -> bool:
    return (
        any(t in text for t in CURRENT_STATE_TOKENS)
        and any(t in text for t in RUN_ID_TOKENS)
        and any(t in text for t in UNSAFE_TERMINAL_TOKENS)
    )


def resolve_profile_bound_state(active_state: dict, errors: list[str]) -> tuple[dict, dict]:
    profile_state = active_state.get("selected_execution_profile_state") or {}
    attempt_key = str(profile_state.get("active_attempt_state_key") or "")
    execution_key = str(profile_state.get("execution_state_key") or "")
    step_key = str(profile_state.get("current_step_state_key") or "")
    if not execution_key or not step_key:
        errors.append("PROFILE_BOUND_PROJECTOR_STATE_KEYS_INCOMPLETE")
        return {}, {}
    execution = active_state.get(execution_key)
    if not isinstance(execution, dict):
        errors.append(f"PROFILE_BOUND_EXECUTION_STATE_MISSING:{execution_key}")
        execution = {}
    step = execution.get(step_key)
    if not isinstance(step, dict):
        errors.append(f"PROFILE_BOUND_CURRENT_STEP_STATE_MISSING:{execution_key}.{step_key}")
        step = {}
    # A NOT_EXECUTED profile step must not require or materialize an active-attempt projector.
    # Once the step is executed, the active-attempt key and mapping become mandatory.
    if step.get("result") == "NOT_EXECUTED":
        if attempt_key:
            attempt = active_state.get(attempt_key)
            if isinstance(attempt, dict) and attempt:
                errors.append(f"NOT_EXECUTED_PROFILE_ACTIVE_ATTEMPT_MUST_BE_ABSENT:{attempt_key}")
        return {}, step
    if not attempt_key:
        errors.append("PROFILE_BOUND_ACTIVE_ATTEMPT_STATE_KEY_MISSING")
        return {}, step
    attempt = active_state.get(attempt_key)
    if not isinstance(attempt, dict):
        errors.append(f"PROFILE_BOUND_ACTIVE_ATTEMPT_STATE_MISSING:{attempt_key}")
        attempt = {}
    return attempt, step


def classify_projectors(registry: dict, current_uid: str, errors: list[str]) -> dict[str, object]:
    cfg = registry.get("active_consumer_reference_integrity") or {}
    inventory = cfg.get("projector_inventory")
    if not isinstance(inventory, list) or not inventory:
        errors.append("PROJECTOR_INVENTORY_MISSING_OR_EMPTY")
        return {}

    active_state = load_yaml(ROOT / "governance/test/ACTIVE_STATE.yaml")
    active_attempt, current_step = resolve_profile_bound_state(active_state, errors)
    projectors: dict[str, object] = {}
    seen = set()

    for item in inventory:
        if not isinstance(item, dict):
            errors.append("PROJECTOR_INVENTORY_ENTRY_INVALID")
            continue
        owner = str(item.get("owner") or "")
        kind = str(item.get("kind") or "")
        yaml_path = str(item.get("yaml_path") or "")
        key = (owner, kind, yaml_path)
        if key in seen:
            errors.append(f"PROJECTOR_INVENTORY_DUPLICATE:{owner}#{yaml_path}")
            continue
        seen.add(key)
        path = ROOT / owner
        label = f"{owner}#{yaml_path}"
        # Current findings are an executed-step projector. In the canonical NOT_EXECUTED
        # clean-reset state they must be absent; requiring them would contradict the
        # selected-profile zero-residual contract.
        if kind.endswith("_CURRENT_FINDINGS_CROSSCHECK") and current_step.get("result") == "NOT_EXECUTED":
            present = path.is_file()
            projectors[label] = {
                "applicability": "NOT_APPLICABLE_WHILE_NOT_EXECUTED",
                "present": present,
            }
            if present:
                errors.append(f"NOT_EXECUTED_PROFILE_FINDINGS_PROJECTOR_MUST_BE_ABSENT:{label}")
            continue
        try:
            data = load_yaml(path)
            value = deep_get(data, yaml_path)
        except (OSError, yaml.YAMLError, KeyError) as exc:
            errors.append(f"PROJECTOR_PARSE_OR_PATH_MISSING:{owner}#{yaml_path}:{exc}")
            continue

        if kind == "GOVERNANCE_UID":
            projectors[label] = value
            if value != current_uid:
                errors.append(
                    f"ACTIVE_GOVERNANCE_PROJECTOR_STALE:{label}:expected={current_uid}:actual={value}"
                )
        elif kind.endswith("_CURRENT_EXECUTION_CROSSCHECK"):
            projectors[label] = {
                "attempt_uid": value.get("attempt_uid") if isinstance(value, dict) else None,
                "state": value.get("state") if isinstance(value, dict) else None,
            }
            if not isinstance(value, dict):
                errors.append(f"CURRENT_PROFILE_EXECUTION_PROJECTOR_INVALID:{label}")
                continue
            checks = {
                "attempt_uid": (value.get("attempt_uid"), active_attempt.get("attempt_uid")),
                "state": (value.get("state"), current_step.get("result")),
                "current_functional_gap_count": (
                    value.get("current_functional_gap_count"),
                    active_attempt.get("effective_functional_gap_total")
                    if active_attempt.get("effective_functional_gap_total") is not None
                    else active_attempt.get("fresh_functional_gap_total"),
                ),
            }
            for field, (actual, expected) in checks.items():
                if actual != expected:
                    errors.append(
                        f"CURRENT_PROFILE_EXECUTION_PROJECTOR_DRIFT:{label}:{field}:expected={expected}:actual={actual}"
                    )
        elif kind.endswith("_CURRENT_FINDINGS_CROSSCHECK"):
            projectors[label] = {
                "attempt_uid": value.get("attempt_uid") if isinstance(value, dict) else None,
                "fresh_functional_gap_total": value.get("fresh_functional_gap_total") if isinstance(value, dict) else None,
            }
            if not isinstance(value, dict):
                errors.append(f"CURRENT_PROFILE_FINDINGS_PROJECTOR_INVALID:{label}")
                continue
            if value.get("attempt_uid") != active_attempt.get("attempt_uid"):
                errors.append(f"CURRENT_PROFILE_FINDINGS_ATTEMPT_DRIFT:{label}")
            if value.get("fresh_functional_gap_total") != active_attempt.get("fresh_functional_gap_total"):
                errors.append(f"CURRENT_PROFILE_FINDINGS_GAP_DRIFT:{label}")
        else:
            errors.append(f"PROJECTOR_KIND_UNKNOWN:{label}:{kind}")

    return projectors


def run_negative_regressions(errors: list[str]) -> dict[str, bool]:
    try:
        matrix = load_yaml(NEGATIVE_MATRIX)
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f"NEGATIVE_REGRESSION_MATRIX_MISSING_OR_INVALID:{exc}")
        return {}
    cases = matrix.get("cases") or []
    if not isinstance(cases, list) or len(cases) < 4:
        errors.append("NEGATIVE_REGRESSION_MATRIX_INCOMPLETE")
        return {}
    results: dict[str, bool] = {}
    for case in cases:
        uid = str((case or {}).get("case_uid") or "")
        expected = str((case or {}).get("expected") or "")
        if not uid or not expected:
            errors.append("NEGATIVE_REGRESSION_CASE_IDENTITY_INCOMPLETE")
            continue
        if expected == "BLOCK_PRETERMINAL_CURRENT_CLOSURE_PROJECTION":
            caught = unsafe_preterminal_current_projection(str(case.get("synthetic_workflow_text") or ""))
        elif expected == "BLOCK_BY_TERMINAL_RESULT_SEMANTICS":
            protocol = load_yaml(ROOT / "governance/specifications/current/VALIDATION_REMEDIATION_CLOSURE_PROTOCOL.yaml")
            semantics = protocol.get("historical_failure_semantics") or {}
            caught = (
                semantics.get("historical_failed_evidence_may_receive_current_authority_credit") is False
                and semantics.get("historical_failed_evidence_may_receive_current_closure_credit") is False
            )
        elif expected == "BLOCK_BY_CONTENT_SEMANTIC_RESIDUAL_CLASSIFICATION":
            protocol = load_yaml(ROOT / "governance/specifications/current/VALIDATION_REMEDIATION_CLOSURE_PROTOCOL.yaml")
            residual = protocol.get("residual_classification") or {}
            persist = protocol.get("persistence_transaction") or {}
            caught = (
                residual.get("semantic_content_review_required") is True
                and residual.get("count_is_summary_not_classification") is True
                and persist.get("unknown_residual_disposition") == "BLOCK"
            )
        else:
            caught = False
        results[uid] = caught
        if not caught:
            errors.append(f"NEGATIVE_REGRESSION_ESCAPED:{uid}")
    return results


def main() -> int:
    errors: list[str] = []
    referenced_by: dict[str, set[str]] = defaultdict(set)
    workflow_count = 0
    unsafe_workflows: list[str] = []
    missing_workflows: list[str] = []

    registry = load_yaml(REGISTRY)
    current_uid = (registry.get("active_specification") or {}).get("governance_uid")
    if not current_uid:
        errors.append("REGISTRY_ACTIVE_GOVERNANCE_UID_MISSING")

    workflows = sorted([*WORKFLOW_ROOT.glob("*.yml"), *WORKFLOW_ROOT.glob("*.yaml")])
    queue: deque[str] = deque()
    for workflow in workflows:
        workflow_count += 1
        text = workflow.read_text(encoding="utf-8")
        if SEMVER_LOCATOR.search(text):
            errors.append(f"SEMVER_LOCATOR_IN_ACTIVE_WORKFLOW:{rel(workflow)}")
        if unsafe_preterminal_current_projection(text):
            unsafe_workflows.append(rel(workflow))
            errors.append(f"PRETERMINAL_CURRENT_CLOSURE_PROJECTION_FORBIDDEN:{rel(workflow)}")
        for finding in fixed_dynamic_replay_identities(rel(workflow), text):
            errors.append(f"FIXED_EXECUTION_IDENTITY_IN_DYNAMIC_REPLAY:{rel(workflow)}:{finding}")
        for wf_ref in LOCAL_WORKFLOW_REF.findall(text):
            if not (ROOT / wf_ref).is_file():
                missing_workflows.append(wf_ref)
                errors.append(f"MISSING_REUSABLE_WORKFLOW_TARGET:{wf_ref}<-{rel(workflow)}")
        for script_rel in workflow_executable_refs(text):
            referenced_by[script_rel].add(rel(workflow))
            queue.append(script_rel)

    visited: set[str] = set()
    while queue:
        script_rel = queue.popleft()
        if script_rel in visited:
            continue
        visited.add(script_rel)
        script = ROOT / script_rel
        if not script.is_file():
            continue
        text = script.read_text(encoding="utf-8")
        if SEMVER_LOCATOR.search(text):
            errors.append(f"SEMVER_LOCATOR_IN_ACTIVE_CONSUMER:{script_rel}")
        for finding in fixed_dynamic_replay_identities(script_rel, text):
            errors.append(f"FIXED_EXECUTION_IDENTITY_IN_DYNAMIC_REPLAY:{script_rel}:{finding}")
        for child in python_executable_refs(text):
            referenced_by[child].add(script_rel)
            if child not in visited:
                queue.append(child)

    missing: dict[str, list[str]] = {}
    for script_rel, consumers in sorted(referenced_by.items()):
        if not (ROOT / script_rel).is_file():
            missing[script_rel] = sorted(consumers)
            errors.append(
                f"MISSING_ACTIVE_OR_TRANSITIVE_CONSUMER_TARGET:{script_rel}<-{','.join(sorted(consumers))}"
            )

    projector_values = {}
    if current_uid:
        try:
            projector_values = classify_projectors(registry, current_uid, errors)
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"PROJECTOR_INVENTORY_RESOLUTION_FAILED:{exc}")

    required = (
        ROOT / ".github/workflows/governance-selected-profile-integrity.yml",
        ROOT / ".github/workflows/governance-full-line-system-gate.yml",
    )
    gate_ref = "governance/ci/validate_active_consumer_reference_integrity.py"
    gate_presence = {}
    for workflow in required:
        present = workflow.is_file() and gate_ref in workflow.read_text(encoding="utf-8")
        gate_presence[rel(workflow)] = present
        if not present:
            errors.append(f"REFERENCE_INTEGRITY_GATE_MISSING_FROM_REQUIRED_REGRESSION:{rel(workflow)}")

    negative = run_negative_regressions(errors)

    report = {
        "artifact_type": "NON_NORMATIVE_ACTIVE_CONSUMER_REFERENCE_INTEGRITY_REPORT",
        "workflow_count": workflow_count,
        "direct_and_transitive_governance_python_target_count": len(referenced_by),
        "missing_targets": missing,
        "missing_reusable_workflows": sorted(set(missing_workflows)),
        "unsafe_preterminal_current_projection_workflows": unsafe_workflows,
        "dynamic_replay_executable_set": list(DYNAMIC_REPLAY_EXECUTABLES),
        "dynamic_replay_fixed_identity_guard": "ENFORCED",
        "active_governance_projectors": projector_values,
        "projector_inventory_source": "governance/specifications/REGISTRY.yaml",
        "required_regression_gate_presence": gate_presence,
        "negative_regressions": negative,
        "result": "PASS" if not errors else "FAIL",
        "errors": errors,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if errors:
        for error in errors:
            print("BLOCK:", error, file=sys.stderr)
        return 1

    print(f"PASS: active workflows scanned={workflow_count}")
    print(f"PASS: direct+transitive executable targets={len(referenced_by)} all exist")
    print("PASS: complete projector inventory resolved from Registry and profile-bound state keys")
    print("PASS: no same-run preterminal Current closure PASS projection remains")
    print("PASS: terminal-result negative regressions blocked")
    print("PASS: ACTIVE_CONSUMER_REFERENCE_INTEGRITY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
