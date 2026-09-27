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

FORBIDDEN_CURRENT_RUNTIME_TOKENS = (
    "HISTORICAL_GOVERNANCE_TEST_STATE_ONLY",
    "stage_execution_adapters.stage02_functional_contract",
    "compile_stage_execution_preflight.py",
    "governance/test/ACTIVE_STATE.yaml",
    "governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml",
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

    roles = registry.get("branch_role_contract") or {}
    governance_branch = str(registry.get("branch") or "")
    governance_role = roles.get(governance_branch)
    if governance_role not in {"IMMUTABLE_GOVERNANCE_RULESET", "GOVERNANCE_REVISION_CANDIDATE"}:
        errors.append("GOVERNANCE_BRANCH_IDENTITY_OR_ROLE_DRIFT")
    product_branch = str(registry.get("product_execution_branch") or "")
    if not product_branch or roles.get(product_branch) != "PRODUCT_EXECUTION_WORKLINE":
        errors.append("PRODUCT_EXECUTION_BRANCH_IDENTITY_OR_ROLE_DRIFT")
    if governance_branch == product_branch:
        errors.append("GOVERNANCE_AND_PRODUCT_BRANCH_MUST_BE_DISTINCT")

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

    # Profile-specific stage schema is validated by the selected-profile validator.
    # This global consumer-integrity validator remains profile-neutral and only
    # verifies that the registered adapter surface exists and is parseable.
    adapters = load_yaml(ADAPTERS)
    if not isinstance(adapters.get("stages") or {}, dict):
        errors.append("STAGE_ADAPTER_REGISTRY_INVALID")

    referenced_by: dict[str, set[str]] = defaultdict(set)
    queue: deque[str] = deque()
    workflows = sorted([*WORKFLOW_ROOT.glob("*.yml"), *WORKFLOW_ROOT.glob("*.yaml")])
    if not workflows:
        errors.append("CURRENT_WORKFLOW_SET_EMPTY")

    validation_contract = registry.get("candidate_validation_contract") or {}
    if governance_role == "GOVERNANCE_REVISION_CANDIDATE":
        required_workflow_names=set(map(str,validation_contract.get("required_workflow_names") or []))
        workflow_by_name={}
        for workflow in workflows:
            workflow_text=workflow.read_text(encoding="utf-8")
            m=re.search(r"(?m)^name:\s*(.+?)\s*$",workflow_text)
            if m:
                workflow_by_name[m.group(1).strip()]=(workflow,workflow_text)
        missing_names=sorted(required_workflow_names-set(workflow_by_name))
        for name in missing_names:
            errors.append("CANDIDATE_REQUIRED_WORKFLOW_MISSING:"+name)
        for name in required_workflow_names & set(workflow_by_name):
            wf,wf_text=workflow_by_name[name]
            if governance_branch not in wf_text:
                errors.append("CANDIDATE_REQUIRED_WORKFLOW_BRANCH_NOT_WIRED:"+name+":"+governance_branch)
            if validation_contract.get("required_workflows_run_on_every_candidate_push") is not True:
                errors.append("CANDIDATE_REQUIRED_WORKFLOW_EVERY_PUSH_POLICY_MISSING")
            if validation_contract.get("candidate_required_workflow_path_filter")!="FORBIDDEN":
                errors.append("CANDIDATE_REQUIRED_WORKFLOW_PATH_FILTER_POLICY_DRIFT")
            if re.search(r"(?m)^\s+paths(?:-ignore)?:\s*$",wf_text):
                errors.append("CANDIDATE_REQUIRED_WORKFLOW_PATH_FILTER_PRESENT:"+name)
        cleanup=workflow_by_name.get("Current Governance Cleanup Validation")
        if cleanup:
            _,cleanup_text=cleanup
            for command in map(str,validation_contract.get("current_cleanup_required_commands") or []):
                if command not in cleanup_text:
                    errors.append("CANDIDATE_CURRENT_CLEANUP_REQUIRED_COMMAND_MISSING:"+command)
        if validation_contract.get("mother_neutrality_and_portability_required") is not True:
            errors.append("CANDIDATE_MOTHER_NEUTRALITY_PORTABILITY_NOT_REQUIRED")
        if validation_contract.get("active_consumer_reverse_validation_required") is not True:
            errors.append("CANDIDATE_ACTIVE_CONSUMER_REVERSE_VALIDATION_NOT_REQUIRED")
        if validation_contract.get("core_validation_pass_may_substitute_full_preformal_regression") is not False:
            errors.append("CANDIDATE_FULL_PREFORMAL_SUBSTITUTION_NOT_BLOCKED")
        if validation_contract.get("formal_promotion_requires_all_required_workflows_exact_head_success") is not True:
            errors.append("CANDIDATE_EXACT_HEAD_WORKFLOW_SUCCESS_NOT_REQUIRED")
        if validation_contract.get("formal_promotion_requires_independent_auditor_evidence") is not True:
            errors.append("CANDIDATE_FORMAL_AUDITOR_EVIDENCE_NOT_REQUIRED")
        readiness=str(validation_contract.get("promotion_readiness_validator") or "")
        if not readiness or not (ROOT/readiness).is_file():
            errors.append("CANDIDATE_PROMOTION_READINESS_VALIDATOR_MISSING:"+readiness)
        if validation_contract.get("promotion_readiness_mode")!="READ_ONLY_FAIL_CLOSED":
            errors.append("CANDIDATE_PROMOTION_READINESS_MODE_DRIFT")
        if validation_contract.get("promotion_readiness_may_mutate_or_promote") is not False:
            errors.append("CANDIDATE_PROMOTION_READINESS_MUTATION_NOT_BLOCKED")
        if validation_contract.get("candidate_rule_bundle_release_state")!="CANDIDATE_NOT_PROMOTED":
            errors.append("CANDIDATE_REGISTRY_RELEASE_STATE_DRIFT")
        if validation_contract.get("candidate_rule_bundle_released_current_authority") is not False:
            errors.append("CANDIDATE_REGISTRY_RELEASE_AUTHORITY_LEAK")
        if validation_contract.get("live_branch_head_must_equal_validation_head") is not True:
            errors.append("CANDIDATE_LIVE_BRANCH_HEAD_BINDING_NOT_REQUIRED")
        if validation_contract.get("live_branch_head_recheck_after_evidence_validation_required") is not True:
            errors.append("CANDIDATE_LIVE_BRANCH_HEAD_RECHECK_NOT_REQUIRED")
        trust_materializer=str(validation_contract.get("predecessor_source_trust_materializer") or "")
        if not trust_materializer or not (ROOT/trust_materializer).is_file():
            errors.append("CANDIDATE_PREDECESSOR_TRUST_MATERIALIZER_MISSING:"+trust_materializer)
        if validation_contract.get("predecessor_source_trust_generation_from_current_bytes")!="FORBIDDEN":
            errors.append("CANDIDATE_CURRENT_SELF_SIGN_TRUST_NOT_FORBIDDEN")
        if cleanup:
            _,cleanup_text=cleanup
            if trust_materializer and trust_materializer not in cleanup_text:
                errors.append("CANDIDATE_PREDECESSOR_TRUST_MATERIALIZER_NOT_WIRED")
            if "WEB_GOVERNANCE_TRUST_ROOT" not in cleanup_text:
                errors.append("CANDIDATE_EXTERNAL_TRUST_ENV_NOT_WIRED")

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

    # Generic current engine must remain product-neutral; detect concrete product
    # identities generically instead of naming a profile step or one product page.
    current_engine_text = (ROOT / "governance/ci/stage_execution_engine.py").read_text(encoding="utf-8")
    fixed_product_identity = re.compile(r"['\"](?:CORE|ASSET|VIDEO|EDIT|VOICE|QA|IAM|ERP|AIAPI)-\\d+['\"]")
    for match in sorted(set(fixed_product_identity.findall(current_engine_text))):
        errors.append("FIXED_PRODUCT_SCOPE_IN_COMMON_ENGINE:" + match)

    if errors:
        for error in sorted(set(errors)):
            print("BLOCK:", error, file=sys.stderr)
        return 1

    print(f"PASS: Current workflows scanned={len(workflows)}")
    print(f"PASS: active/transitive executable targets={len(visited)} all resolve")
    print("PASS: governance/test product run-state root absent")
    print("PASS: retired profile compatibility wrapper/module absent")
    print("PASS: profile-specific scope schema is delegated to selected-profile validation")
    print("PASS: Governance branch has no product effectful execute mode")
    print("PASS: no stale fixed product run root or retired compatibility token in active consumers")
    if governance_role == "GOVERNANCE_REVISION_CANDIDATE":
        print("PASS: candidate validation workflow denominator and full preformal regression wiring complete")
    print("PASS: ACTIVE_CONSUMER_REFERENCE_INTEGRITY_CURRENT_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
