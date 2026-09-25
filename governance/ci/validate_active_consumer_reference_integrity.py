#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"
REGISTRY = ROOT / "governance" / "specifications" / "REGISTRY.yaml"
ADAPTERS = ROOT / "governance" / "ci" / "stage_execution_semantic_adapters.yaml"
COMMON_STAGE_WORKFLOW = ".github/workflows/common-stage-execution-engine.yml"

EXEC_REF = re.compile(
    r"python(?:3)?\s+(?:-m\s+)?"
    r"((?:governance/ci|\.github/governance-source)/[A-Za-z0-9_./-]+\.py)"
)
LOCAL_WORKFLOW_REF = re.compile(r"uses:\s*\./(\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml)")
SEMVER_LOCATOR = re.compile(r"governance/(?:current|specifications)/v\d+(?:\.\d+)+")
STALE_PRODUCT_RUN_ROOT_LITERAL = re.compile(
    r"00_SOURCE_INTAKE/(?:fresh_run_\d+|run_[A-Za-z0-9]+_[0-9a-f]{8,}(?:_[A-Za-z0-9-]+)?)"
)

_RETIRED_COMPAT_STAGE_DIR = "stage" + "02"

FORBIDDEN_CURRENT_RUNTIME_TOKENS = (
    "HISTORICAL_GOVERNANCE_TEST_STATE_ONLY",
    "stage_execution_adapters." + _RETIRED_COMPAT_STAGE_DIR + "_functional_contract",
    "compile_stage_execution_preflight.py",
    "governance/test/ACTIVE_STATE.yaml",
    "governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml",
    "governance/test/" + _RETIRED_COMPAT_STAGE_DIR + "/STAGE02_CURRENT_FINDINGS.yaml",
)
RETIRED_PATHS = (
    "governance/ci/compile_stage_execution_preflight.py",
    "governance/ci/stage_execution_adapters/stage02_functional_contract.py",
)
PRODUCT_STATE_ROOT = ROOT / "governance" / "test"


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path.relative_to(ROOT).as_posix())
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj, dict):
        raise ValueError(f"MAPPING_REQUIRED:{path.relative_to(ROOT).as_posix()}")
    return obj


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


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
    allowed = re.compile(r"^((?:governance/ci|\.github/governance-source)/[A-Za-z0-9_./-]+\.py)$")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        literals: list[str] = []
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


def current_runtime_token_findings(path_rel: str, text: str) -> list[str]:
    out = []
    for token in FORBIDDEN_CURRENT_RUNTIME_TOKENS:
        if token in text:
            out.append(f"RETIRED_CURRENT_RUNTIME_TOKEN:{path_rel}:{token}")
    if SEMVER_LOCATOR.search(text):
        out.append(f"SEMVER_LOCATOR_IN_CURRENT_CONSUMER:{path_rel}")
    for literal in sorted(set(STALE_PRODUCT_RUN_ROOT_LITERAL.findall(text))):
        out.append(f"STALE_PRODUCT_RUN_ROOT_LITERAL:{path_rel}:{literal}")
    return out


def main() -> int:
    errors: list[str] = []
    registry = load_yaml(REGISTRY)

    if registry.get("branch") != "rebuild-v2.1.1":
        errors.append("GOVERNANCE_BRANCH_IDENTITY_DRIFT")
    if registry.get("product_execution_branch") != "0921acpos":
        errors.append("PRODUCT_EXECUTION_BRANCH_DRIFT")
    roles = registry.get("branch_role_contract") or {}
    if roles.get("rebuild-v2.1.1") != "IMMUTABLE_GOVERNANCE_RULESET":
        errors.append("GOVERNANCE_BRANCH_ROLE_DRIFT")
    if roles.get("0921acpos") != "PRODUCT_EXECUTION_WORKLINE":
        errors.append("PRODUCT_BRANCH_ROLE_DRIFT")

    forbidden_branch_items = set(registry.get("forbidden_in_ruleset_branch") or [])
    required_forbidden = {
        "PRODUCT_STAGE_RUNNER","ACTIVE_WORK_UNIT","CURRENT_EXECUTION_SCOPE",
        "PRODUCT_EXECUTION_EVIDENCE","PREEXECUTION_RECEIPT","PRODUCT_HISTORY"
    }
    if not required_forbidden.issubset(forbidden_branch_items):
        errors.append("RULESET_BRANCH_FORBIDDEN_ITEM_SET_INCOMPLETE")

    # Product run-state/history must not physically exist on Current Governance branch.
    if PRODUCT_STATE_ROOT.exists():
        errors.append("GOVERNANCE_TEST_PRODUCT_STATE_ROOT_FORBIDDEN:governance/test")

    for retired in RETIRED_PATHS:
        if (ROOT / retired).exists():
            errors.append("RETIRED_COMPATIBILITY_PATH_STILL_PRESENT:" + retired)

    adapters = load_yaml(ADAPTERS)
    stage_contracts = adapters.get("stages") or {}
    for stage_uid, stage_contract in stage_contracts.items():
        stage_contract = stage_contract or {}
        if stage_contract.get("scanner_mode") != "NORMALIZED_COMMON_EVIDENCE_CONTRACT":
            errors.append("STAGE_SCANNER_MODE_NOT_CURRENT_NORMALIZED:" + str(stage_uid))
        for field in (
            "python_compatibility_module",
            "compatibility_current_execution_authority",
            "compatibility_may_resolve_current_scope",
            "compatibility_state_source",
        ):
            if field in stage_contract:
                errors.append("STAGE_RETIRED_COMPATIBILITY_FIELD_PRESENT:" + str(stage_uid) + ":" + field)
        declared_source = stage_contract.get("current_execution_state_source")
        if declared_source is not None and declared_source != "PRODUCT_STAGE_EXECUTION_CURRENT_SCOPE_AND_RESUME":
            errors.append("STAGE_CURRENT_EXECUTION_STATE_SOURCE_DRIFT:" + str(stage_uid))

    referenced_by: dict[str, set[str]] = defaultdict(set)
    queue: deque[str] = deque()
    workflows = sorted([*WORKFLOW_ROOT.glob("*.yml"), *WORKFLOW_ROOT.glob("*.yaml")])
    if not workflows:
        errors.append("CURRENT_WORKFLOW_SET_EMPTY")

    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")
        path_rel = rel(workflow)
        if path_rel != ".github/workflows/current-governance-cleanup-validation.yml":
            errors.extend(current_runtime_token_findings(path_rel, text))
        if path_rel == COMMON_STAGE_WORKFLOW and "stage_execution_engine.py --execute --stage" in text:
            errors.append("GOVERNANCE_BRANCH_PRODUCT_EFFECTFUL_EXECUTE_MODE_FORBIDDEN")
        for wf_ref in LOCAL_WORKFLOW_REF.findall(text):
            if not (ROOT / wf_ref).is_file():
                errors.append(f"MISSING_REUSABLE_WORKFLOW_TARGET:{wf_ref}<-{path_rel}")
        for script_rel in workflow_executable_refs(text):
            referenced_by[script_rel].add(path_rel)
            queue.append(script_rel)

    visited: set[str] = set()
    while queue:
        script_rel = queue.popleft()
        if script_rel in visited:
            continue
        visited.add(script_rel)
        script = ROOT / script_rel
        if not script.is_file():
            errors.append(
                "MISSING_ACTIVE_OR_TRANSITIVE_CONSUMER_TARGET:"
                + script_rel
                + "<-"
                + ",".join(sorted(referenced_by[script_rel]))
            )
            continue
        text = script.read_text(encoding="utf-8")
        try:
            ast.parse(text)
        except SyntaxError as exc:
            errors.append(f"ACTIVE_CONSUMER_PYTHON_PARSE_ERROR:{script_rel}:{exc.lineno}:{exc.offset}")
            continue
        is_runtime_consumer = (
            not Path(script_rel).name.startswith("test_")
            and script_rel != "governance/ci/validate_active_consumer_reference_integrity.py"
        )
        if is_runtime_consumer:
            errors.extend(current_runtime_token_findings(script_rel, text))
        for child in python_executable_refs(text):
            referenced_by[child].add(script_rel)
            if child not in visited:
                queue.append(child)

    # Generic current engine must remain product-neutral; no fixed page/product selection.
    current_engine_text = (ROOT / "governance/ci/stage_execution_engine.py").read_text(encoding="utf-8")
    for token in ("target_pages=['CORE-01']", 'target_pages=["CORE-01"]', "CURRENT_STAGE2_TARGET_CORE01"):
        if token in current_engine_text:
            errors.append("FIXED_PRODUCT_SCOPE_IN_COMMON_ENGINE:" + token)

    if errors:
        for error in sorted(set(errors)):
            print("BLOCK:", error, file=sys.stderr)
        return 1

    print(f"PASS: Current workflows scanned={len(workflows)}")
    print(f"PASS: active/transitive executable targets={len(visited)} all resolve")
    print("PASS: governance/test product run-state root absent")
    print("PASS: retired compatibility wrapper/module absent")
    print("PASS: stage scope source is Product Current Scope/Resume only")
    print("PASS: Governance branch has no product effectful execute mode")
    print("PASS: no stale fixed product run root or retired compatibility token in active consumers")
    print("PASS: ACTIVE_CONSUMER_REFERENCE_INTEGRITY_CURRENT_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
