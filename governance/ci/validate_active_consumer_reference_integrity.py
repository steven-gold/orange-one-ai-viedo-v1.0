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
STALE_EXECUTION_RUN_ROOT_LITERAL = re.compile(
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
LEGACY_EXECUTION_STATE_ROOT = ROOT / "governance" / "test"


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
    for literal in sorted(set(STALE_EXECUTION_RUN_ROOT_LITERAL.findall(text))):
        out.append(f"STALE_EXECUTION_RUN_ROOT_LITERAL:{path_rel}:{literal}")
    return out


def main() -> int:
    errors: list[str] = []
    registry = load_yaml(REGISTRY)

    roles = registry.get("branch_role_contract") or {}
    governance_branch = str(registry.get("branch") or "")
    governance_role = roles.get(governance_branch)
    if governance_role != "CURRENT_GOVERNANCE_WORKLINE":
        errors.append("GOVERNANCE_BRANCH_IDENTITY_OR_ROLE_DRIFT")
    binding_rel = str(registry.get("execution_environment_binding") or "")
    if not binding_rel:
        errors.append("EXECUTION_ENVIRONMENT_BINDING_MISSING")
    else:
        binding_path = ROOT / binding_rel
        if not binding_path.is_file():
            errors.append("EXECUTION_ENVIRONMENT_BINDING_TARGET_MISSING:" + binding_rel)
        else:
            binding = load_yaml(binding_path)
            if binding.get("artifact_type") != "EXECUTION_ENVIRONMENT_BINDING" or binding.get("normative_authority") is not False:
                errors.append("EXECUTION_ENVIRONMENT_BINDING_AUTHORITY_INVALID")
            if binding.get("common_stage_definition_credit") != 0 or binding.get("common_stage_completion_credit") != 0:
                errors.append("EXECUTION_ENVIRONMENT_BINDING_COMMON_STAGE_CREDIT_NONZERO")
            ruleset = binding.get("rules") or {}
            if ruleset.get("values_may_enter_reusable_stage_semantics") is not False or ruleset.get("values_may_define_common_stage_denominator") is not False:
                errors.append("EXECUTION_ENVIRONMENT_BINDING_STAGE_ISOLATION_INVALID")

    forbidden_branch_items = set(registry.get("forbidden_in_ruleset_branch") or [])
    required_forbidden = {
        "ACTIVE_WORK_UNIT","CURRENT_EXECUTION_SCOPE","PREEXECUTION_RECEIPT"
    }
    if not required_forbidden.issubset(forbidden_branch_items):
        errors.append("RULESET_BRANCH_FORBIDDEN_ITEM_SET_INCOMPLETE")

    # Execution run-state/history must not physically exist on Current Governance branch.
    if LEGACY_EXECUTION_STATE_ROOT.exists():
        errors.append("GOVERNANCE_TEST_EXECUTION_STATE_ROOT_FORBIDDEN:governance/test")

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

    validation_contract = registry.get("current_validation_contract") or {}
    required_workflow_names=set(map(str,validation_contract.get("required_workflow_names") or []))
    workflow_by_name={}
    for workflow in workflows:
        workflow_text=workflow.read_text(encoding="utf-8")
        m=re.search(r"(?m)^name:\\s*(.+?)\\s*$",workflow_text)
        if m:
            workflow_by_name[m.group(1).strip()]=(workflow,workflow_text)

    missing_names=sorted(required_workflow_names-set(workflow_by_name))
    for name in missing_names:
        errors.append("CURRENT_REQUIRED_WORKFLOW_MISSING:"+name)

    bindings=validation_contract.get("required_workflow_bindings") or {}
    for name in required_workflow_names & set(workflow_by_name):
        wf,wf_text=workflow_by_name[name]
        row=bindings.get(name) or {}
        if str(row.get("path") or "")!=rel(wf):
            errors.append("CURRENT_REQUIRED_WORKFLOW_PATH_DRIFT:"+name)
        if row.get("event")!="push":
            errors.append("CURRENT_REQUIRED_WORKFLOW_EVENT_DRIFT:"+name)
        if governance_branch not in wf_text:
            errors.append("CURRENT_REQUIRED_WORKFLOW_BRANCH_NOT_WIRED:"+name+":"+governance_branch)

    if validation_contract.get("mother_neutrality_and_portability_required") is not True:
        errors.append("CURRENT_MOTHER_NEUTRALITY_PORTABILITY_NOT_REQUIRED")
    if validation_contract.get("active_consumer_reverse_validation_required") is not True:
        errors.append("CURRENT_ACTIVE_CONSUMER_REVERSE_VALIDATION_NOT_REQUIRED")
    if validation_contract.get("exact_current_head_required") is not True:
        errors.append("CURRENT_EXACT_HEAD_VALIDATION_NOT_REQUIRED")
    if validation_contract.get("prior_head_workflow_result_may_credit_current_head") is not False:
        errors.append("CURRENT_PRIOR_HEAD_CREDIT_NOT_BLOCKED")
    if validation_contract.get("historical_pass_substitution")!="FORBIDDEN":
        errors.append("CURRENT_HISTORICAL_PASS_SUBSTITUTION_NOT_BLOCKED")
    if validation_contract.get("authority_model")!="WORD_DERIVED_INTERNAL_VALIDATION":
        errors.append("CURRENT_WORD_DERIVED_AUTHORITY_MODEL_DRIFT")
    for key in (
        "external_human_or_account_evidence_required",
        "external_auditor_required",
        "external_signer_required",
        "detached_external_trust_required",
        "promotion_required_before_product_stage_execution",
        "released_governance_selection_required",
    ):
        if validation_contract.get(key) is not False:
            errors.append("NON_WORD_EXTERNAL_GATE_REINTRODUCED:"+key)

    if validation_contract.get("source_package_integration_mode")=="SINGLE_BRANCH_INTEGRATED":
        if validation_contract.get("source_package_integrated_branch")!=governance_branch:
            errors.append("SINGLE_BRANCH_SOURCE_INTEGRATED_BRANCH_DRIFT")
        source_validator=str(validation_contract.get("source_package_integrated_validator") or "")
        if not source_validator or not (ROOT/source_validator).is_file():
            errors.append("SINGLE_BRANCH_SOURCE_INTEGRATED_VALIDATOR_MISSING:"+source_validator)
        if (registry.get("mutation_policy") or {}).get("branch_fanout_without_explicit_user_authorization")!="FORBIDDEN":
            errors.append("SINGLE_BRANCH_FANOUT_GUARD_MISSING")

    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")
        path_rel = rel(workflow)
        errors.extend(current_runtime_token_findings(path_rel, text))
        if path_rel == COMMON_STAGE_WORKFLOW and "stage_execution_engine.py --execute --stage" in text:
            errors.append("GOVERNANCE_BRANCH_EFFECTFUL_EXECUTE_MODE_FORBIDDEN")
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

    # Generic current engine must remain execution-context neutral; detect concrete bound environment identities dynamically.
    current_engine_text = (ROOT / "governance/ci/stage_execution_engine.py").read_text(encoding="utf-8")
    binding_rel = str(registry.get("execution_environment_binding") or "")
    binding = load_yaml(ROOT / binding_rel) if binding_rel else {}
    environment_literals = {
        str(value)
        for group in ("governance_workline", "execution_workline")
        for value in ((binding.get(group) or {}).get("repository"), (binding.get(group) or {}).get("branch"))
        if isinstance(value, str) and value
    }
    for literal in sorted(environment_literals):
        if literal in current_engine_text:
            errors.append("BOUND_ENVIRONMENT_IDENTITY_IN_COMMON_ENGINE:" + literal)

    neutrality = registry.get("stage_core_neutrality_contract") or {}
    if neutrality.get("status") != "REQUIRED":
        errors.append("STAGE_CORE_NEUTRALITY_CONTRACT_MISSING")
    semantic_paths=set(map(str,neutrality.get("reusable_stage_semantic_paths") or []))
    rules_root_rel=str(registry.get("rules_root") or "")
    rules_root=ROOT/rules_root_rel if rules_root_rel else None
    if rules_root and rules_root.is_dir():
        semantic_paths.update(rel(p) for p in rules_root.glob("*.yaml") if p.is_file())
    instance_uid=re.compile(r"(?<![A-Z0-9_])(?:CORE|ASSET|VIDEO|EDIT|VOICE|QA|IAM|ERP|AIAPI|WB)-\d+(?![A-Z0-9_])")
    forbidden_stage_tokens=(
        "page_uid_sticky_from_stage","page_uid_sticky_through_stage",
        "business_entity_gate_required:",
        "NEXT_PAGE_ELIGIBILITY","NEXT_PAGE_STAGE05_OR_PROJECT_COMPLETE",
        "PRODUCTION_PAGE_CLOSURE","PRODUCTION_PAGE_CLOSED",
    )
    external_admission_tokens=(
        "PRODUCT_SELECTED_GOVERNANCE_RELEASE","GOVERNANCE_REVISION_TRANSITION_RECEIPT",
        "APPLICATION_BASELINE_ADMISSION_MANIFEST","APPLICATION_BASELINE_MATERIALIZATION_RECEIPT",
        "APPLICATION_BASELINE_SNAPSHOT","WEB-EXT-ADMISSION",
    )
    stage_denominator_paths={
        ".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml",
        ".github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml",
        ".github/governance-source/active/source/10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml",
        "governance/ci/stage_execution_semantic_adapters.yaml",
        "governance/ci/stage_execution_engine.py",
    }
    for path_rel in sorted(semantic_paths):
        path=ROOT/path_rel
        if not path.is_file():
            errors.append("STAGE_CORE_NEUTRALITY_PATH_MISSING:"+path_rel)
            continue
        txt=path.read_text(encoding="utf-8")
        for literal in sorted(environment_literals):
            if literal and literal in txt:
                errors.append("BOUND_ENVIRONMENT_IDENTITY_IN_REUSABLE_SEMANTICS:"+path_rel+":"+literal)
        if path_rel.startswith("governance/specifications/current/") and "https://github.com/" in txt:
            errors.append("CONCRETE_GITHUB_AUTHORITY_REF_IN_CURRENT_RULESET:"+path_rel)
        for m in sorted(set(instance_uid.findall(txt))):
            errors.append("FIXED_GOVERNED_UNIT_INSTANCE_IN_REUSABLE_SEMANTICS:"+path_rel+":"+m)
        if path_rel in stage_denominator_paths:
            for tok in forbidden_stage_tokens:
                if tok in txt:
                    errors.append("NON_NEUTRAL_STAGE_TOKEN:"+path_rel+":"+tok)
            for tok in external_admission_tokens:
                if tok in txt:
                    errors.append("EXTERNAL_ADMISSION_TOKEN_IN_STAGE_CORE:"+path_rel+":"+tok)

    # Derived profile projection and common-invariant history neutrality guards.
    baseline_path=ROOT/'.github/governance-source/active/source/10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'
    lifecycle_path=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
    invariant_path=ROOT/'.github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'
    if baseline_path.is_file() and lifecycle_path.is_file():
        baseline_doc=yaml.safe_load(baseline_path.read_text(encoding='utf-8')) or {}
        lifecycle_doc=yaml.safe_load(lifecycle_path.read_text(encoding='utf-8')) or {}
        if baseline_doc.get('selected_profile_uid')!=lifecycle_doc.get('profile_uid'):
            errors.append('DERIVED_SELECTED_PROFILE_UID_DRIFT')
    if invariant_path.is_file():
        invariant_doc=yaml.safe_load(invariant_path.read_text(encoding='utf-8')) or {}
        for key in invariant_doc:
            if str(key).lower().endswith('_observed_defect_mapping'):
                errors.append('HISTORICAL_OBSERVED_DEFECT_MAPPING_IN_COMMON_INVARIANT:'+str(key))
        pcs=((invariant_doc.get('invariants') or {}).get('PRODUCER_CONSUMER_SCHEMA_IDENTITY') or {})
        stage_specific_bug_keys=[str(k) for k in pcs if re.match(r'^stage\d+_',str(k),re.I)]
        if stage_specific_bug_keys:
            errors.append('STAGE_SPECIFIC_BUG_EXAMPLE_IN_COMMON_SCHEMA_INVARIANT:'+','.join(sorted(stage_specific_bug_keys)))

    if errors:
        for error in sorted(set(errors)):
            print("BLOCK:", error, file=sys.stderr)
        return 1

    print(f"PASS: Current workflows scanned={len(workflows)}")
    print(f"PASS: active/transitive executable targets={len(visited)} all resolve")
    print("PASS: governance/test execution run-state root absent")
    print("PASS: retired profile compatibility wrapper/module absent")
    print("PASS: profile-specific scope schema is delegated to selected-profile validation")
    print("PASS: Governance branch has no effectful execute mode")
    print("PASS: no stale fixed execution run root or retired compatibility token in active consumers")
    print("PASS: Current Word-derived validation workflow denominator and exact-head wiring complete")
    print("PASS: ACTIVE_CONSUMER_REFERENCE_INTEGRITY_CURRENT_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
