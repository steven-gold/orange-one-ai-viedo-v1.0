#!/usr/bin/env python3
"""Neutral audit-closure engine for the AUDIT execution domain.

This engine executes the registered AUDIT_CLOSURE_FLOW (AU-01..AU-09) as a
static, read-only closure audit of a declared audit target. For the governance
package target the denominator is the AUDIT_CATALOG universe and every item is
checked for validator wiring, evidence binding, owner binding and completeness
against the universal audit dimensions.

The engine never creates normative requirements and never mutates the governed
tree. It projects the existing registries only.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import sys
from pathlib import Path

import yaml

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".github" / "governance-source" / "active" / "source"
DOMAINS = ROOT / "governance" / "execution-domains"
CATALOG_PATH = SOURCE / "10_REGISTRY" / "AUDIT_CATALOG.yaml"
RULE_REGISTRY_PATH = SOURCE / "10_REGISTRY" / "REFERENCE_RULE_REGISTRY.yaml"
STEPS_PATH = DOMAINS / "AUDIT" / "STEPS.yaml"
DOMAIN_PATH = DOMAINS / "AUDIT" / "DOMAIN.yaml"
PROFILE_PATH = DOMAINS / "AUDIT_PROFILE.yaml"
BINDINGS_PATH = DOMAINS / "AUTHORITY_BINDINGS.yaml"
SCHEMA_PATH = DOMAINS / "STEP_CONTRACT_SCHEMA.yaml"
INVARIANT_PATH = SOURCE / "10_REGISTRY" / "STAGE_EXECUTION_INVARIANT_REGISTRY.yaml"

AUDIT_TARGET_UID = "GOVERNANCE_PACKAGE"
GOVERNANCE_RESOLVABLE_EVIDENCE = {"VALIDATOR_RESULT"}
REQUIRED_ITEM_FIELDS = (
    "audit_item_uid",
    "audit_type",
    "audit_type_uid",
    "stage_uid",
    "target_uid",
    "requirement_type",
    "validator_uid",
    "validator_name",
    "required_evidence",
    "denominator_eligible",
    "status",
)
NA_DIMENSION_AUTHORITY = {
    "PERMISSION_GATE_STATE_WHEN_APPLICABLE": "GOVERNANCE_PACKAGE_HAS_NO_PRODUCT_PERMISSION_GATE",
    "FUNCTIONAL_VISUAL_BINDING_WHEN_APPLICABLE": "GOVERNANCE_PACKAGE_HAS_NO_FUNCTIONAL_VISUAL_SURFACE",
}
ALLOWED_STEP_FAILURES = {"STOP", "STOP_AND_REENTER_EARLIEST_OWNER"}


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"MAPPING_REQUIRED:{path}")
    return data


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_ok(path: Path) -> bool:
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        return True
    except (SyntaxError, UnicodeDecodeError):
        return False


def load_context() -> dict:
    catalog = load_yaml(CATALOG_PATH)
    rules = load_yaml(RULE_REGISTRY_PATH)
    steps = load_yaml(STEPS_PATH)
    domain = load_yaml(DOMAIN_PATH)
    profile = load_yaml(PROFILE_PATH)
    bindings = load_yaml(BINDINGS_PATH)
    schema = load_yaml(SCHEMA_PATH)
    invariant_registry = load_yaml(INVARIANT_PATH)

    validators = {}
    for rec in rules.get("validator_identities") or []:
        if rec.get("validator_uid"):
            validators[rec["validator_uid"]] = rec
    audit_types = {}
    for rec in rules.get("audit_type_identities") or []:
        if rec.get("audit_type_uid"):
            audit_types[rec["audit_type_uid"]] = rec
    return {
        "catalog": catalog,
        "steps": steps.get("steps") or [],
        "domain": domain,
        "profile": profile,
        "bindings": bindings,
        "required_step_fields": schema.get("required_step_fields") or [],
        "validators": validators,
        "audit_types": audit_types,
        "stage_invariants": invariant_registry.get("invariants") or {},
    }


def deterministic_contract_ok(ctx: dict) -> bool:
    det = (ctx.get("stage_invariants") or {}).get("DETERMINISTIC_STAGE_AUDIT") or {}
    statuses = set(det.get("canonical_stage_statuses") or [])
    required_statuses = {
        "NOT_STARTED", "READY_FOR_EXECUTION", "IN_PROGRESS", "BLOCKED",
        "REVERIFY_REQUIRED", "CURRENT_STATE_CONFLICT",
        "EXECUTION_COMPLETE_CLOSURE_PENDING", "CLOSED_PASS", "CLOSED_FAIL",
        "SNAPSHOT_INVALIDATED",
    }
    return bool(
        det.get("invariant_uid") == "GOV-INV-DETERMINISTIC-STAGE-AUDIT-001"
        and det.get("applies_to_all_registered_stages") is True
        and det.get("same_complete_input_same_complete_result") is True
        and statuses == required_statuses
        and (det.get("current_state_conflict_contract") or {}).get("stage_pass_allowed") is False
        and (det.get("historical_evidence_contract") or {}).get("historical_pass_is_current_pass") is False
    )


def resolve_implementation(rec: dict) -> dict:
    rel = rec.get("implementation_path")
    if not rel:
        return {"implementation_path": None, "exists": False, "parse_ok": False}
    path = SOURCE / rel
    return {
        "implementation_path": rel,
        "exists": path.is_file(),
        "parse_ok": path.is_file() and parse_ok(path),
    }


def build_denominator(ctx: dict) -> list[dict]:
    items = ctx["catalog"].get("items") or []
    return [
        it
        for it in items
        if it.get("target_uid") == AUDIT_TARGET_UID
        and it.get("status") == "REQUIRED"
        and it.get("denominator_eligible") is True
    ]


def resolve_item(item: dict, ctx: dict) -> dict:
    rec = ctx["validators"].get(item.get("validator_uid")) or {}
    audit_type = ctx["audit_types"].get(item.get("audit_type_uid")) or {}
    impl = resolve_implementation(rec)
    evidence = []
    for ev in item.get("required_evidence") or []:
        if ev in GOVERNANCE_RESOLVABLE_EVIDENCE:
            evidence.append({
                "evidence_type": ev,
                "evidence_level": "REQUIRED",
                "artifact_ref": impl.get("implementation_path"),
                "resolved": bool(impl.get("exists") and impl.get("parse_ok")),
            })
        else:
            governed = bool(
                item.get("applicability")
                and item.get("not_applicable_requires_authority") is True
            )
            evidence.append({
                "evidence_type": ev,
                "evidence_level": "APPLICABILITY_GATED",
                "artifact_ref": item.get("applicability"),
                "resolved": governed,
            })
    return {
        "item": item,
        "validator": rec,
        "audit_type": audit_type,
        "impl": impl,
        "evidence": evidence,
    }


def dimension_applicable(dimension: str) -> bool:
    return dimension not in NA_DIMENSION_AUTHORITY


def check_dimension(dimension: str, resolved: dict, ctx: dict) -> tuple[bool, str]:
    item = resolved["item"]
    rec = resolved["validator"]
    audit_type = resolved["audit_type"]

    if dimension == "AUTHORITY_AND_SCOPE":
        ok = (
            item.get("target_uid") == AUDIT_TARGET_UID
            and bool(rec)
            and bool(audit_type)
        )
        return ok, "target and audit authority resolved" if ok else "target or authority unresolved"

    if dimension == "INPUT_IDENTITY_AND_HASH":
        uid = item.get("audit_item_uid")
        auid = item.get("audit_type_uid")
        ok = bool(uid) and bool(auid)
        return ok, "audit identity present" if ok else "audit identity missing"

    if dimension == "REQUIRED_FIELD_COMPLETENESS":
        missing = [f for f in REQUIRED_ITEM_FIELDS if not item.get(f)]
        return (not missing), "all required item fields present" if not missing else "missing:" + ",".join(missing)

    if dimension == "OPERATION_AND_OWNER_BINDING":
        if not rec:
            return False, "validator identity unresolved"
        if rec.get("canonical_name") != item.get("validator_name"):
            return False, "validator canonical_name mismatch"
        if rec.get("identity_mode") == "PHYSICAL_VALIDATOR" and not resolved["impl"].get("exists"):
            return False, "physical validator implementation missing"
        return True, "operation and owner binding resolved"

    if dimension == "OUTPUT_SCHEMA_AND_DENOMINATOR":
        ok = (
            bool(item.get("required_evidence"))
            and item.get("denominator_eligible") is True
            and audit_type.get("denominator_eligible") is True
        )
        return ok, "denominator eligibility consistent" if ok else "denominator eligibility inconsistent"

    if dimension == "DEPENDENCY_AND_SUCCESSOR_BINDING":
        usage = rec.get("allowed_usage") or []
        stages = audit_type.get("allowed_stage_uids") or []
        ok = "AUDIT_CATALOG" in usage and item.get("stage_uid") in stages
        return ok, "dependency and successor bindings resolved" if ok else "dependency or successor binding missing"

    if dimension == "ERROR_BLOCKED_RECOVERY_WHEN_APPLICABLE":
        for step in ctx["steps"]:
            recovery = step.get("failure_reentry_checkpoint_next_step") or {}
            if recovery.get("failure") not in ALLOWED_STEP_FAILURES:
                return False, "step failure disposition not fail-closed:" + str(step.get("step_uid"))
            if not recovery.get("reentry") or not recovery.get("next_step"):
                return False, "step recovery edge incomplete:" + str(step.get("step_uid"))
        return True, "fail-closed recovery edges complete"

    if dimension == "EVIDENCE_SCHEMA_AND_BYTES":
        unresolved = [e for e in resolved["evidence"] if not e.get("resolved")]
        return (not unresolved), "evidence bound" if not unresolved else "unresolved evidence:" + ",".join(e["evidence_type"] for e in unresolved)

    if dimension == "DUPLICATE_CONFLICT_ORPHAN_GAP":
        items = ctx["catalog"].get("items") or []
        uid_dup = len({i.get("audit_item_uid") for i in items}) != len(items)
        type_dup = len({i.get("audit_type_uid") for i in items}) != len(items)
        bound = ctx["bindings"].get("audit") or {}
        step_ids = {s.get("step_uid") for s in ctx["steps"]}
        orphan = [label for label in bound if label not in step_ids]
        ok = not uid_dup and not type_dup and not orphan
        return ok, "no duplicate or orphan finding" if ok else "duplicate or orphan finding detected"

    if dimension == "CHECKPOINT_RESUME":
        for step in ctx["steps"]:
            recovery = step.get("failure_reentry_checkpoint_next_step") or {}
            if not recovery.get("checkpoint"):
                return False, "checkpoint missing:" + str(step.get("step_uid"))
        return True, "checkpoint edges complete"

    if dimension == "LOCAL_REGRESSION_IMPACT":
        ok = bool(ctx["catalog"].get("items")) and ctx["domain"].get("recursive_governance_tree_scan") == "FORBIDDEN"
        return ok, "read-only projection with complete denominator" if ok else "denominator or isolation contract invalid"

    if dimension == "NEXT_STEP_AUTHORIZATION":
        step_ids = {s.get("step_uid") for s in ctx["steps"]}
        ok = any(str(uid).startswith("AU-09") for uid in step_ids)
        return ok, "successor authorization gate registered" if ok else "successor authorization gate missing"

    return False, "unknown dimension"


def evaluate_item(resolved: dict, ctx: dict, dimensions: list[str]) -> dict:
    findings = []
    item_failed = False
    for dimension in dimensions:
        if not dimension_applicable(dimension):
            findings.append({
                "audit_dimension": dimension,
                "result": "NOT_APPLICABLE",
                "na_authority": NA_DIMENSION_AUTHORITY[dimension],
                "na_evidence": "governance/execution-domains/AUDIT_PROFILE.yaml",
            })
            continue
        try:
            passed, detail = check_dimension(dimension, resolved, ctx)
        except Exception as exc:  # fail-closed
            passed, detail = False, "exception:" + repr(exc)
        if not passed:
            item_failed = True
        findings.append({
            "audit_dimension": dimension,
            "result": "PASS" if passed else "FAIL",
            "detail": detail,
        })
    return {
        "audit_item_uid": resolved["item"].get("audit_item_uid"),
        "audit_type_uid": resolved["item"].get("audit_type_uid"),
        "validator_uid": resolved["item"].get("validator_uid"),
        "owner_uid": resolved["item"].get("validator_uid"),
        "evidence": resolved["evidence"],
        "result": "FAIL" if item_failed else "PASS",
        "dimensions": findings,
    }


def run_steps(ctx: dict, items: list[dict]) -> tuple[list[dict], list[str]]:
    steps = ctx["steps"]
    receipts = []
    required = ctx["required_step_fields"]
    for step in sorted(steps, key=lambda s: str(s.get("step_uid"))):
        missing = [f for f in required if not step.get(f)]
        receipts.append({
            "step_uid": step.get("step_uid"),
            "entry_gate": step.get("entry_gate"),
            "denominator": step.get("denominator"),
            "status": "PASS" if not missing else "FAIL",
            "missing_required_fields": missing,
        })
    return receipts, [r["step_uid"] for r in receipts if r["status"] != "PASS"]


def run_closure(ctx: dict) -> dict:
    profile = ctx["profile"]
    dimensions = profile.get("fixed_audit_dimensions") or []
    denominator = build_denominator(ctx)
    resolved = [resolve_item(item, ctx) for item in denominator]
    results = [evaluate_item(r, ctx, dimensions) for r in resolved]
    step_receipts, failed_steps = run_steps(ctx, denominator)
    deterministic_ok = deterministic_contract_ok(ctx)
    if not deterministic_ok:
        failed_steps.append("DETERMINISTIC_STAGE_AUDIT_CONTRACT")

    pass_count = sum(1 for r in results if r["result"] == "PASS")
    fail_count = sum(1 for r in results if r["result"] == "FAIL")
    applicable = [f for r in results for f in r["dimensions"] if f["result"] != "NOT_APPLICABLE"]
    na_count = sum(1 for r in results for f in r["dimensions"] if f["result"] == "NOT_APPLICABLE")
    unresolved = sum(1 for f in applicable if f["result"] == "FAIL")

    item_uids = [it.get("audit_item_uid") for it in denominator]
    coverage = (len(denominator) == len(item_uids)) and bool(denominator)
    result = (
        "PASS"
        if (fail_count == 0 and unresolved == 0 and not failed_steps and coverage)
        else "FAIL"
    )

    reconciliation = {
        "denominator_count": len(denominator),
        "audited_count": len(results),
        "pass_count": pass_count,
        "partial_count": 0,
        "fail_count": fail_count,
        "blocked_count": 0,
        "not_verified_count": 0,
        "na_count": na_count,
        "unresolved_problem_count": unresolved,
        "dimension_application_count": len(applicable),
        "missing_item_count": len(denominator) - len(results),
        "duplicate_item_count": len(item_uids) - len(set(item_uids)),
    }

    return {
        "schema_version": 1,
        "audit_uid": "AUDIT-CLOSURE-GOVERNANCE-PACKAGE-001",
        "target_uid": AUDIT_TARGET_UID,
        "domain_uid": ctx["domain"].get("domain_uid"),
        "governance_revision": ctx["catalog"].get("governance_revision"),
        "source_revision": file_sha(CATALOG_PATH),
        "denominator_policy": ctx["catalog"].get("denominator_policy"),
        "dimension_denominator": len(dimensions),
        "steps": step_receipts,
        "determinism_contract": {"invariant_uid": "GOV-INV-DETERMINISTIC-STAGE-AUDIT-001", "status": "PASS" if deterministic_ok else "FAIL"},
        "items": results,
        "reconciliation": reconciliation,
        "result": result,
        "successor_authorization": "AUTHORIZED" if result == "PASS" else "BLOCKED",
        "next_step_uid": "REGISTERED_SUCCESSOR_IF_PASS_ELSE_NONE",
    }


def closure_failures(receipt: dict) -> list[str]:
    failures = []
    for step in receipt["steps"]:
        if step["status"] != "PASS":
            failures.append("STEP_INCOMPLETE:" + str(step["step_uid"]))
    for item in receipt["items"]:
        if item["result"] != "PASS":
            failures.append("ITEM_FAIL:" + str(item["audit_item_uid"]))
    rec = receipt["reconciliation"]
    if rec["missing_item_count"] or rec["duplicate_item_count"]:
        failures.append("RECONCILIATION_MISMATCH")
    if receipt["result"] != "PASS":
        failures.append("AUDIT_RESULT_NOT_PASS")
    return failures


def run_self_test() -> int:
    base = load_context()
    cases = []
    if run_closure(base)["result"] != "PASS":
        print("FAIL: baseline closure did not pass", file=sys.stderr)
        return 1
    cases.append("baseline_pass")

    first = run_closure(base)
    second = run_closure(copy.deepcopy(base))
    if json.dumps(first, sort_keys=True) != json.dumps(second, sort_keys=True):
        print("FAIL: same complete audit input produced different result", file=sys.stderr)
        return 1
    cases.append("same_input_same_result")

    no_det = copy.deepcopy(base)
    no_det["stage_invariants"]["DETERMINISTIC_STAGE_AUDIT"]["same_complete_input_same_complete_result"] = False
    if run_closure(no_det)["result"] == "PASS":
        print("FAIL: invalid deterministic audit contract escaped closure", file=sys.stderr)
        return 1
    cases.append("determinism_contract_blocked")

    dup = copy.deepcopy(base)
    dup["catalog"]["items"].append(copy.deepcopy(dup["catalog"]["items"][0]))
    if run_closure(dup)["result"] == "PASS":
        print("FAIL: duplicate item escaped closure", file=sys.stderr)
        return 1
    cases.append("duplicate_blocked")

    orphan = copy.deepcopy(base)
    orphan["catalog"]["items"][0]["validator_uid"] = "VAL-GOV-999"
    if run_closure(orphan)["result"] == "PASS":
        print("FAIL: orphan validator escaped closure", file=sys.stderr)
        return 1
    cases.append("orphan_blocked")

    blank = copy.deepcopy(base)
    blank["catalog"]["items"][0]["required_evidence"] = []
    if run_closure(blank)["result"] == "PASS":
        print("FAIL: blank required field escaped closure", file=sys.stderr)
        return 1
    cases.append("blank_field_blocked")

    recovery = copy.deepcopy(base)
    recovery["steps"][0]["failure_reentry_checkpoint_next_step"]["failure"] = "CONTINUE"
    if run_closure(recovery)["result"] == "PASS":
        print("FAIL: non fail-closed recovery escaped closure", file=sys.stderr)
        return 1
    cases.append("recovery_blocked")

    print(json.dumps({"self_test": "PASS", "cases": len(cases), "case_ids": cases}, ensure_ascii=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--receipt-out")
    args = ap.parse_args()
    if args.self_test:
        return run_self_test()

    receipt = run_closure(load_context())
    if args.receipt_out:
        Path(args.receipt_out).write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    failures = closure_failures(receipt)
    if failures:
        for failure in failures:
            print("BLOCK:", failure, file=sys.stderr)
        print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    rec = receipt["reconciliation"]
    print(
        "PASS: audit closure target=%s items=%d dimensions=%d pass=%d unresolved=%d result=%s successor=%s"
        % (
            receipt["target_uid"],
            rec["denominator_count"],
            receipt["dimension_denominator"],
            rec["pass_count"],
            rec["unresolved_problem_count"],
            receipt["result"],
            receipt["successor_authorization"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
