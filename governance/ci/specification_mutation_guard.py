#!/usr/bin/env python3
from pathlib import Path
import re
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
PROTECTED_PREFIXES = ("governance/specifications/current/",)
PROTECTED_EXACT = {"governance/specifications/REGISTRY.yaml", "GOVERNANCE_CURRENT.yaml"}
AUTH_ROOT = "governance/test/spec_change_authorizations"
_PREWRITE_TRUE_FIELDS = (
    "relevant_scope_read_complete",
    "canonical_owner_resolution_complete",
    "existing_semantics_comparison_complete",
    "duplicate_search_complete",
    "conflict_search_complete",
    "second_system_search_complete",
    "gap_proven_before_write",
)
_PREWRITE_DECISIONS = {"MODIFY_EXISTING_CANONICAL_OWNER", "CREATE_NEW_ONLY_AFTER_NO_EXISTING_OWNER_PROVEN"}

_ALLOWED_MUTATION_BOUNDARIES = {
    "STAGE_END_CONSOLIDATION_AFTER_TERMINAL_CYCLE",
    "FATAL_SPEC_CONTRADICTION_AFTER_TERMINAL_BLOCK",
    "OUTSIDE_GOVERNED_EXECUTION_CYCLE",
}
_TERMINAL_WORK_UNIT_TOKENS = ("CLOSED", "BLOCKED", "TERMINATED", "CANCELLED")



def git(*args, check=True):
    cp = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    if check and cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr.strip()}")
    return cp.stdout


def protected(path):
    return path in PROTECTED_EXACT or any(path.startswith(p) for p in PROTECTED_PREFIXES)


def trailer(message, key):
    prefix = key + ":"
    values = [line[len(prefix):].strip() for line in message.splitlines() if line.startswith(prefix)]
    if len(values) != 1 or not values[0]:
        return None
    return values[0]


def scalar(text: str, key: str):
    match = re.search(r"(?m)^\s*" + re.escape(key) + r":\s*([^#\n]+?)\s*$", text)
    return match.group(1).strip().strip("\"'") if match else None


def prewrite_context_errors(receipt_text: str) -> list[str]:
    errors = []
    if "pre_write_context_verification:" not in receipt_text:
        errors.append("PREWRITE_CONTEXT_SECTION_MISSING")
    for field in _PREWRITE_TRUE_FIELDS:
        if scalar(receipt_text, field) != "true":
            errors.append("PREWRITE_CONTEXT_NOT_PROVEN:" + field)
    for field in ("reviewed_authority_ref_count", "reviewed_existing_owner_ref_count"):
        raw = scalar(receipt_text, field)
        try:
            count = int(raw) if raw is not None else 0
        except ValueError:
            count = 0
        if count < 1:
            errors.append("PREWRITE_CONTEXT_REFERENCE_COUNT_INVALID:" + field)
    if scalar(receipt_text, "write_disposition") not in _PREWRITE_DECISIONS:
        errors.append("PREWRITE_CONTEXT_WRITE_DISPOSITION_INVALID:" + str(scalar(receipt_text, "write_disposition")))
    if scalar(receipt_text, "comparison_result") != "NO_UNRESOLVED_DUPLICATE_CONFLICT_OR_SECOND_SYSTEM":
        errors.append("PREWRITE_CONTEXT_COMPARISON_RESULT_INVALID")
    return errors


def prior_authorization_use_exists(auth_uid):
    current = git("rev-parse", "HEAD").strip()
    marker = f"Spec-Change-Authorization: {auth_uid}"
    records = git("log", "--all", "--format=%H%x1f%B%x1e")
    for record in records.split("\x1e"):
        record = record.strip("\n")
        if not record or "\x1f" not in record:
            continue
        sha, body = record.split("\x1f", 1)
        if sha.strip() == current:
            continue
        if marker in body:
            return True, sha.strip()
    return False, None


def verify_receipt_identity_lock(parent_auth: str) -> list[str]:
    errors = []
    baseline = scalar(parent_auth, "baseline_commit_sha")
    baseline_tree = scalar(parent_auth, "baseline_tree_sha")
    if not baseline or not baseline_tree:
        return ["EXECUTION_CONTEXT_BASELINE_IDENTITY_MISSING"]
    grandparent = git("rev-parse", "HEAD^^", check=False).strip()
    if not grandparent or grandparent != baseline:
        errors.append(
            f"EXECUTION_CONTEXT_HEAD_DRIFT expected_baseline={baseline} "
            f"actual_pre_authorization_parent={grandparent or 'MISSING'}"
        )
    actual_tree = git("rev-parse", f"{baseline}^{{tree}}", check=False).strip()
    if not actual_tree or actual_tree != baseline_tree:
        errors.append(
            f"EXECUTION_CONTEXT_TREE_DRIFT expected={baseline_tree} actual={actual_tree or 'MISSING'}"
        )
    parent_registry = git("show", "HEAD^:governance/specifications/REGISTRY.yaml", check=False)
    expected_uid = scalar(parent_auth, "current_governance_uid")
    if parent_registry and expected_uid:
        data = yaml.safe_load(parent_registry) or {}
        actual_uid = ((data.get("active_specification") or {}).get("governance_uid"))
        if actual_uid != expected_uid:
            errors.append(
                f"EXECUTION_CONTEXT_GOVERNANCE_UID_DRIFT expected={expected_uid} actual={actual_uid}"
            )
    else:
        errors.append("EXECUTION_CONTEXT_PARENT_REGISTRY_OR_UID_MISSING")
    return errors


def current_uid_binding_errors() -> list[str]:
    errors = []
    try:
        registry = yaml.safe_load((ROOT / "governance/specifications/REGISTRY.yaml").read_text()) or {}
        manifest = yaml.safe_load((ROOT / "governance/specifications/current/SPECIFICATION_MANIFEST.yaml").read_text()) or {}
        current = yaml.safe_load((ROOT / "GOVERNANCE_CURRENT.yaml").read_text()) or {}
        active = yaml.safe_load((ROOT / "governance/test/ACTIVE_STATE.yaml").read_text()) or {}
    except Exception as exc:
        return [f"POSTWRITE_CURRENT_BINDING_PARSE_FAILED:{exc}"]

    values = {
        "REGISTRY": (registry.get("active_specification") or {}).get("governance_uid"),
        "MANIFEST": manifest.get("artifact_uid"),
        "GOVERNANCE_CURRENT": current.get("active_governance_uid"),
        "ACTIVE_STATE": active.get("specification_uid"),
        "ACTIVE_STATE_TRANSITION": (active.get("governance_revision_transition") or {}).get("current_governance_uid"),
    }
    expected = values["REGISTRY"]
    if not expected:
        errors.append("POSTWRITE_CURRENT_UID_MISSING:REGISTRY")
        return errors
    for owner, value in values.items():
        if value != expected:
            errors.append(f"POSTWRITE_CURRENT_UID_DRIFT:{owner}:expected={expected}:actual={value}")

    parent_registry_text = git("show", "HEAD^:governance/specifications/REGISTRY.yaml", check=False)
    if parent_registry_text:
        parent_registry = yaml.safe_load(parent_registry_text) or {}
        old_uid = (parent_registry.get("active_specification") or {}).get("governance_uid")
        if old_uid == expected:
            errors.append("NORMATIVE_MUTATION_WITHOUT_NEW_IMMUTABLE_GOVERNANCE_UID")
    return errors


def post_write_reconciliation_errors(parent_auth: str) -> list[str]:
    errors = current_uid_binding_errors()
    if "duplicate_and_residual_cleanup_required: true" in parent_auth:
        validator = ROOT / "governance/ci/validate_active_consumer_reference_integrity.py"
        if not validator.is_file():
            errors.append("POSTWRITE_ACTIVE_CONSUMER_VALIDATOR_MISSING")
        else:
            cp = subprocess.run(
                [sys.executable, str(validator)],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            if cp.returncode != 0:
                tail = (cp.stderr or cp.stdout).strip().replace("\n", " | ")
                errors.append(f"POSTWRITE_ACTIVE_CONSUMER_RECONCILIATION_FAILED:{tail[:1200]}")
    protocol = ROOT / "governance/specifications/current/VALIDATION_REMEDIATION_CLOSURE_PROTOCOL.yaml"
    if "one_canonical_execution_closure_model_required: true" in parent_auth:
        text = protocol.read_text(encoding="utf-8") if protocol.is_file() else ""
        required_tokens = (
            "POST_WRITE_RECONCILIATION",
            "REBUILD_COMPLETE_REGISTERED_CURRENT_PROJECTOR_SET",
            "VERIFY_TERMINAL_RUN_CONCLUSION",
            "inner_step_pass_is_terminal_run_pass: false",
            "unknown_residual_disposition: BLOCK",
        )
        for token in required_tokens:
            if token not in text:
                errors.append(f"POSTWRITE_CLOSURE_PROTOCOL_TOKEN_MISSING:{token}")
    return errors



def _nonterminal_work_unit(work_unit: dict) -> bool:
    if not isinstance(work_unit, dict) or not work_unit:
        return False
    status = str(work_unit.get("current_status") or work_unit.get("status") or "").upper()
    if not status:
        return True
    return not any(token in status for token in _TERMINAL_WORK_UNIT_TOKENS)


def cycle_boundary_errors(receipt_text: str, baseline_state_text: str, parent_state_text: str) -> list[str]:
    """Enforce the frozen-cycle boundary before any protected policy mutation.

    The pre-authorization baseline must not contain an active non-governance
    execution Work Unit. The authorization parent must explicitly switch to one
    governance-maintenance Work Unit. A legal authorization never overrides an
    active product/test/deployment cycle.
    """
    errors: list[str] = []
    try:
        baseline = yaml.safe_load(baseline_state_text) or {}
        parent = yaml.safe_load(parent_state_text) or {}
    except Exception as exc:
        return [f"EXECUTION_CYCLE_BOUNDARY_STATE_PARSE_FAILED:{exc}"]

    boundary = scalar(receipt_text, "governance_mutation_boundary")
    if boundary not in _ALLOWED_MUTATION_BOUNDARIES:
        errors.append(f"GOVERNANCE_MUTATION_BOUNDARY_INVALID:{boundary or 'MISSING'}")

    baseline_primary = str(baseline.get("current_primary_task_layer") or "")
    baseline_resume_uid = str((baseline.get("resume_control") or {}).get("current_work_unit_uid") or "")
    baseline_active = baseline.get("active_work_unit") or {}
    baseline_suspended = baseline.get("suspended_product_work_unit") or {}

    if (
        baseline_primary
        and baseline_primary != "GOVERNANCE_MAINTENANCE"
        and (baseline_resume_uid or _nonterminal_work_unit(baseline_active))
    ):
        errors.append(
            "PROTECTED_POLICY_MUTATION_DURING_ACTIVE_NON_GOVERNANCE_EXECUTION_CYCLE:"
            + baseline_primary
        )
    if _nonterminal_work_unit(baseline_suspended):
        errors.append("PROTECTED_POLICY_MUTATION_WITH_SUSPENDED_NONTERMINAL_PRODUCT_WORK_UNIT")

    parent_primary = str(parent.get("current_primary_task_layer") or "")
    parent_active = parent.get("active_work_unit") or {}
    parent_active_layer = str(parent_active.get("primary_task_layer") or "")
    parent_active_uid = str(parent_active.get("work_unit_uid") or "")
    parent_resume_uid = str((parent.get("resume_control") or {}).get("current_work_unit_uid") or "")
    if parent_primary != "GOVERNANCE_MAINTENANCE":
        errors.append(f"PARENT_PRIMARY_TASK_LAYER_NOT_GOVERNANCE_MAINTENANCE:{parent_primary or 'MISSING'}")
    if parent_active_layer != "GOVERNANCE_MAINTENANCE" or not parent_active_uid:
        errors.append("PARENT_ACTIVE_GOVERNANCE_MAINTENANCE_WORK_UNIT_MISSING")
    if parent_active_uid and parent_resume_uid != parent_active_uid:
        errors.append(
            f"PARENT_GOVERNANCE_WORK_UNIT_RESUME_DRIFT:active={parent_active_uid}:resume={parent_resume_uid or 'MISSING'}"
        )

    if boundary in {
        "STAGE_END_CONSOLIDATION_AFTER_TERMINAL_CYCLE",
        "FATAL_SPEC_CONTRADICTION_AFTER_TERMINAL_BLOCK",
    }:
        if scalar(receipt_text, "predecessor_execution_cycle_terminal") != "true":
            errors.append("PREDECESSOR_EXECUTION_CYCLE_TERMINAL_NOT_PROVEN")
        disposition = str(scalar(receipt_text, "predecessor_execution_cycle_terminal_disposition") or "").upper()
        if not disposition:
            errors.append("PREDECESSOR_EXECUTION_CYCLE_TERMINAL_DISPOSITION_MISSING")
        if not scalar(receipt_text, "predecessor_execution_cycle_evidence_ref"):
            errors.append("PREDECESSOR_EXECUTION_CYCLE_EVIDENCE_REF_MISSING")
        if boundary == "STAGE_END_CONSOLIDATION_AFTER_TERMINAL_CYCLE":
            if disposition and not any(token in disposition for token in ("CLOSED", "TERMINATED", "STAGE_END")):
                errors.append("STAGE_END_BOUNDARY_WITHOUT_TERMINAL_CLOSED_DISPOSITION")
        else:
            if scalar(receipt_text, "fatal_specification_contradiction_proven") != "true":
                errors.append("FATAL_SPECIFICATION_CONTRADICTION_NOT_PROVEN")
            if disposition and not any(token in disposition for token in ("BLOCKED", "TERMINATED")):
                errors.append("FATAL_SPEC_BOUNDARY_WITHOUT_BLOCKED_OR_TERMINATED_DISPOSITION")

    return errors


def execution_cycle_boundary_errors(parent_auth: str) -> list[str]:
    baseline = scalar(parent_auth, "baseline_commit_sha")
    if not baseline:
        return ["EXECUTION_CYCLE_BOUNDARY_BASELINE_MISSING"]
    baseline_state = git("show", f"{baseline}:governance/test/ACTIVE_STATE.yaml", check=False)
    parent_state = git("show", "HEAD^:governance/test/ACTIVE_STATE.yaml", check=False)
    if not baseline_state:
        return ["EXECUTION_CYCLE_BOUNDARY_BASELINE_STATE_MISSING"]
    if not parent_state:
        return ["EXECUTION_CYCLE_BOUNDARY_PARENT_STATE_MISSING"]
    return cycle_boundary_errors(parent_auth, baseline_state, parent_state)


def main():
    if not (ROOT / ".git").exists():
        print("BLOCK: SPEC_MUTATION_GUARD_REQUIRES_GIT_CHECKOUT", file=sys.stderr)
        return 2
    if subprocess.run(["git", "rev-parse", "HEAD^"], cwd=ROOT, capture_output=True).returncode != 0:
        print("BLOCK: SPEC_MUTATION_GUARD_REQUIRES_PARENT_COMMIT", file=sys.stderr)
        return 2

    changed = [p for p in git("diff", "--name-only", "HEAD^", "HEAD").splitlines() if p]
    protected_changed = [p for p in changed if protected(p)]
    if not protected_changed:
        print("PASS: no Current Specification / Registry / compatibility-entrypoint mutation in this commit")
        return 0

    message = git("log", "-1", "--pretty=%B")
    auth_uid = trailer(message, "Spec-Change-Authorization")
    scope = trailer(message, "Spec-Change-Scope")
    if not auth_uid or not scope:
        print(
            "BLOCK: protected governance mutation without explicit "
            "Spec-Change-Authorization and Spec-Change-Scope trailers",
            file=sys.stderr,
        )
        return 1

    auth_rel = f"{AUTH_ROOT}/{auth_uid}.yaml"
    parent_auth = git("show", f"HEAD^:{auth_rel}", check=False)
    if not parent_auth:
        print(f"BLOCK: authorization {auth_uid} did not exist in parent commit", file=sys.stderr)
        return 1

    required = (
        f"authorization_uid: {auth_uid}",
        "artifact_type: SPECIFICATION_CHANGE_AUTHORIZATION_RECEIPT",
        "normative_authority: false",
        "authority_source: EXPLICIT_USER_DIRECTIVE",
        "single_use: true",
        "status: APPROVED_FOR_EXACT_SCOPE",
        "ai_may_expand_scope: false",
        "ai_may_reuse_authorization: false",
    )
    missing = [token for token in required if token not in parent_auth]
    if missing:
        print("BLOCK: authorization receipt missing required fail-closed fields", file=sys.stderr)
        for token in missing:
            print("MISSING:", token, file=sys.stderr)
        return 1

    errors = prewrite_context_errors(parent_auth) + verify_receipt_identity_lock(parent_auth) + execution_cycle_boundary_errors(parent_auth)
    if errors:
        print("BLOCK: authorization receipt / execution context lock invalid", file=sys.stderr)
        for error in errors:
            print("MISSING_OR_INVALID:", error, file=sys.stderr)
        return 1

    reused, prior_sha = prior_authorization_use_exists(auth_uid)
    if reused:
        print(
            f"BLOCK: single-use authorization already consumed: {auth_uid} prior_commit={prior_sha}",
            file=sys.stderr,
        )
        return 1

    forbidden_claims = (
        "AUTO_AUTHORIZED_BY_TEST_FAILURE",
        "AUTO_AUTHORIZED_BY_CONSTRUCTION",
        "AUTO_AUTHORIZED_BY_IMPLEMENTATION",
        "AUTO_AUTHORIZED_BY_VERSION_BUMP",
    )
    if any(token in message for token in forbidden_claims):
        print("BLOCK: invalid automatic specification-change authority claim", file=sys.stderr)
        return 1

    post_errors = post_write_reconciliation_errors(parent_auth)
    if post_errors:
        print("BLOCK: atomic promotion post-write reconciliation failed", file=sys.stderr)
        for error in post_errors:
            print("POSTWRITE:", error, file=sys.stderr)
        return 1

    print(f"PASS: protected governance mutation authorized by pre-existing explicit user directive {auth_uid}")
    print("PASS: execution context identity lock matches pre-authorization parent commit/tree and parent governance UID")
    print("PASS: pre-write context verification proves read/owner/duplicate/conflict/second-system/gap checks")
    print("PASS: protected policy mutation occurs only outside an active non-governance execution cycle and under an explicit governance-maintenance boundary")
    print("PASS: post-write Current UID/projector/consumer reconciliation is part of the same promotion transaction")
    print("PASS: content-semantic residual cleanup is machine-gated; count-only closure is rejected")
    print(f"PASS: authorization scope trailer={scope}")
    print("PASS: protected changed paths:")
    for path in protected_changed:
        print("-", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
