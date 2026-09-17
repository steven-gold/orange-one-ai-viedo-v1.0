#!/usr/bin/env python3
from __future__ import annotations

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
    r"((?:governance/(?:ci|test)|\.github/governance-source)/[A-Za-z0-9_./-]+\.py)"
)
LOCAL_WORKFLOW_REF = re.compile(r"uses:\s*\./(\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml)")
SEMVER_LOCATOR = re.compile(r"governance/(?:current|specifications)/v\d+(?:\.\d+)+")
UNSAFE_TERMINAL_TOKENS = ("PASS_EXECUTION_SOURCE_HEAD", "CLOSED_VERIFIED")
CURRENT_STATE_TOKENS = ("governance/test/ACTIVE_STATE.yaml", "ACTIVE_STATE.yaml")
RUN_ID_TOKENS = ("GITHUB_RUN_ID", "github.run_id")


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


def executable_refs(text: str) -> set[str]:
    return {m.group(1) for m in EXEC_REF.finditer(text)}


def unsafe_preterminal_current_projection(text: str) -> bool:
    return (
        any(t in text for t in CURRENT_STATE_TOKENS)
        and any(t in text for t in RUN_ID_TOKENS)
        and any(t in text for t in UNSAFE_TERMINAL_TOKENS)
    )


def classify_projectors(registry: dict, current_uid: str, errors: list[str]) -> dict[str, object]:
    cfg = registry.get("active_consumer_reference_integrity") or {}
    inventory = cfg.get("projector_inventory")
    if not isinstance(inventory, list) or not inventory:
        errors.append("PROJECTOR_INVENTORY_MISSING_OR_EMPTY")
        return {}

    active_state = load_yaml(ROOT / "governance/test/ACTIVE_STATE.yaml")
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
        try:
            data = load_yaml(path)
            value = deep_get(data, yaml_path)
        except (OSError, yaml.YAMLError, KeyError) as exc:
            errors.append(f"PROJECTOR_PARSE_OR_PATH_MISSING:{owner}#{yaml_path}:{exc}")
            continue

        label = f"{owner}#{yaml_path}"
        if kind == "GOVERNANCE_UID":
            projectors[label] = value
            if value != current_uid:
                errors.append(
                    f"ACTIVE_GOVERNANCE_PROJECTOR_STALE:{label}:expected={current_uid}:actual={value}"
                )
        elif kind == "STAGE02_CURRENT_EXECUTION_CROSSCHECK":
            projectors[label] = {
                "attempt_uid": value.get("attempt_uid") if isinstance(value, dict) else None,
                "state": value.get("state") if isinstance(value, dict) else None,
            }
            if not isinstance(value, dict):
                errors.append(f"CURRENT_STAGE02_PROJECTOR_INVALID:{label}")
                continue
            expected_attempt = (active_state.get("stage02_active_attempt") or {}).get("attempt_uid")
            expected_result = (active_state.get("execution") or {}).get("stage2", {}).get("result")
            expected_gaps = (active_state.get("stage02_current_problem_state") or {}).get("fresh_functional_gap_total")
            expected_next = (active_state.get("resume_control") or {}).get("parent_resume_point")
            checks = {
                "attempt_uid": (value.get("attempt_uid"), expected_attempt),
                "state": (value.get("state"), expected_result),
                "current_functional_gap_count": (value.get("current_functional_gap_count"), expected_gaps),
            }
            for field, (actual, expected) in checks.items():
                if actual != expected:
                    errors.append(
                        f"CURRENT_STAGE02_PROJECTOR_DRIFT:{label}:{field}:expected={expected}:actual={actual}"
                    )
        elif kind == "STAGE02_CURRENT_FINDINGS_CROSSCHECK":
            projectors[label] = {
                "attempt_uid": value.get("attempt_uid") if isinstance(value, dict) else None,
                "fresh_functional_gap_total": value.get("fresh_functional_gap_total") if isinstance(value, dict) else None,
            }
            if not isinstance(value, dict):
                errors.append(f"CURRENT_FINDINGS_PROJECTOR_INVALID:{label}")
                continue
            expected_attempt = (active_state.get("stage02_active_attempt") or {}).get("attempt_uid")
            expected_gaps = (active_state.get("stage02_current_problem_state") or {}).get("fresh_functional_gap_total")
            if value.get("attempt_uid") != expected_attempt:
                errors.append(f"CURRENT_FINDINGS_ATTEMPT_DRIFT:{label}")
            if value.get("fresh_functional_gap_total") != expected_gaps:
                errors.append(f"CURRENT_FINDINGS_GAP_DRIFT:{label}")
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
        for wf_ref in LOCAL_WORKFLOW_REF.findall(text):
            if not (ROOT / wf_ref).is_file():
                missing_workflows.append(wf_ref)
                errors.append(f"MISSING_REUSABLE_WORKFLOW_TARGET:{wf_ref}<-{rel(workflow)}")
        for script_rel in executable_refs(text):
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
        for child in executable_refs(text):
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
    print("PASS: complete projector inventory resolved from Registry and cross-ledger checks passed")
    print("PASS: no same-run preterminal Current closure PASS projection remains")
    print("PASS: terminal-result negative regressions blocked")
    print("PASS: ACTIVE_CONSUMER_REFERENCE_INTEGRITY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
