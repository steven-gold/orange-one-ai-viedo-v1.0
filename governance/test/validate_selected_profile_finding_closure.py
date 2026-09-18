#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "governance/specifications/REGISTRY.yaml"
LEDGER = ROOT / "governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml"
LIFECYCLE = ROOT / "governance/specifications/current/EVIDENCE_FEEDBACK_ARTIFACT_LIFECYCLE.yaml"
MUTATION = ROOT / "governance/specifications/current/SPECIFICATION_MUTATION_CONTROL.yaml"
RAW_RUNNER = ROOT / "governance/ci/run_current_stage2_actual_test.py"
SUCCESSOR = ROOT / "governance/ci/validate_stage02_successor_integrity.py"
MATERIAL = ROOT / "governance/ci/validate_current_stage2_materialized_closure.py"
CLASSIFIER = ROOT / "governance/ci/classify_current_stage2_functional_remediability_r3.py"
ACTIVE_REF_GATE = ROOT / "governance/ci/validate_active_consumer_reference_integrity.py"
FULL_LINE_WORKFLOW = ROOT / ".github/workflows/governance-full-line-system-gate.yml"
REPORT = ROOT / "governance/test/FINDING_CLOSURE_READINESS.json"

TARGETS = {
    "FIND-20260915-015": ("IMPLEMENTATION_REMEDIATED", "governance/ci/validate_stage02_successor_integrity.py"),
    "FIND-20260915-016": ("IMPLEMENTATION_REMEDIATED", "governance/ci/classify_current_stage2_functional_remediability_r3.py"),
    "FIND-20260915-027": ("ABSORBED_INTO_CANONICAL_OWNER", "governance/specifications/current/SPECIFICATION_MUTATION_CONTROL.yaml"),
}
TERMINAL = {"IMPLEMENTATION_REMEDIATED", "ABSORBED_INTO_CANONICAL_OWNER", "CLOSED_NO_SPEC_CHANGE_REQUIRED", "SUPERSEDED"}
REQUIRED_TERMINAL_FIELDS = {
    "resolution_type", "target_path", "resolution_commit", "validation_run",
    "evidence_ref", "resolved_at", "reopen_condition",
}


def die(msg: str) -> None:
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        die(f"PARSE:{path.relative_to(ROOT)}:{exc!r}")
    if not isinstance(data, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return data


def require(condition: bool, msg: str) -> None:
    if not condition:
        die(msg)


registry = load_yaml(REGISTRY)
ledger = load_yaml(LEDGER)
lifecycle = load_yaml(LIFECYCLE)
mutation = load_yaml(MUTATION)
current_uid = (registry.get("active_specification") or {}).get("governance_uid")
require(isinstance(current_uid, str) and current_uid, "CURRENT_GOVERNANCE_UID_MISSING")
findings = {x.get("finding_uid"): x for x in ledger.get("findings") or [] if isinstance(x, dict) and x.get("finding_uid")}
for uid in TARGETS:
    require(uid in findings, f"FINDING_MISSING:{uid}")

terminal_policy = lifecycle.get("finding_terminalization") or {}
require(set(terminal_policy.get("terminal_required_fields") or []) == REQUIRED_TERMINAL_FIELDS, "TERMINAL_REQUIRED_FIELDS_POLICY_DRIFT")
fresh = terminal_policy.get("fresh_evidence_integrity") or {}
for key in (
    "persisted_current_head_validation_required",
    "validation_governance_uid_must_equal_current_registry_uid",
    "exact_finding_signature_to_remediation_relation_required",
    "exact_remediation_target_evidence_required",
):
    require(fresh.get(key) is True, f"FRESH_TERMINALIZATION_POLICY_MISSING:{key}")

# 015: immutable raw discovery remains raw-only; owning-layer remediation is separately source-bounded and fail-closed.
# Validate the runner structurally rather than pinning one source-code spelling/signature.
# Reusable governance validation MUST survive scope-parametric refactors that preserve the same semantic invariant.
raw_text = RAW_RUNNER.read_text(encoding="utf-8")
successor_text = SUCCESSOR.read_text(encoding="utf-8")
material_text = MATERIAL.read_text(encoding="utf-8")
try:
    raw_tree = ast.parse(raw_text, filename=str(RAW_RUNNER))
except SyntaxError as exc:
    die(f"015_RAW_RUNNER_PARSE_FAILED:{exc}")

fresh_scan_calls = [
    node for node in ast.walk(raw_tree)
    if isinstance(node, ast.Call)
    and isinstance(node.func, ast.Name)
    and node.func.id == "fresh_scan"
]
require(fresh_scan_calls, "015_RAW_DISCOVERY_FRESH_SCAN_CALL_MISSING")

# Current policy separates immutable Raw discovery from effective-contract truth.
# Accept the direct legacy binding only when present; otherwise require an explicit
# page+raw -> effective_page_contract -> effective_raw -> fresh_scan chain.
direct_raw_binding = any(
    len(call.args) >= 2
    and isinstance(call.args[0], ast.Name) and call.args[0].id == "page"
    and isinstance(call.args[1], ast.Name) and call.args[1].id == "raw"
    for call in fresh_scan_calls
)
effective_binding = False
effective_assign = False
for node in ast.walk(raw_tree):
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        value = node.value
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "effective_page_contract"
            and len(value.args) >= 2
            and isinstance(value.args[0], ast.Name) and value.args[0].id == "page"
            and isinstance(value.args[1], ast.Name) and value.args[1].id == "raw"
        ):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, (ast.Tuple, ast.List)):
                    if any(isinstance(elt, ast.Name) and elt.id == "effective_raw" for elt in target.elts):
                        effective_assign = True
                elif isinstance(target, ast.Name) and target.id == "effective_raw":
                    effective_assign = True
for call in fresh_scan_calls:
    if (
        len(call.args) >= 2
        and isinstance(call.args[0], ast.Name) and call.args[0].id == "page"
        and isinstance(call.args[1], ast.Name) and call.args[1].id == "effective_raw"
    ):
        effective_binding = True
require(
    direct_raw_binding or (effective_assign and effective_binding),
    "015_RAW_PLUS_EFFECTIVE_CONTRACT_SCAN_BINDING_MISSING",
)

prior_false = False
for node in ast.walk(raw_tree):
    if isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values):
            if (
                isinstance(key, ast.Constant)
                and key.value == "prior_stage2_results_used"
                and isinstance(value, ast.Constant)
                and value.value is False
            ):
                prior_false = True
                break
    if prior_false:
        break
require(prior_false, "015_PRIOR_STAGE2_RESULTS_FALSE_GUARD_MISSING")
for token in ("MATERIAL_VALIDATOR", "PENDING_REMEDIATION_PRODUCT_ROOT_INVALID"):
    require(token in successor_text, f"015_SUCCESSOR_GUARD_MISSING:{token}")
for token in (
    "raw_actions", "raw_controls", "raw_sections", "raw_components", "raw_ports",
    "OPERATION_MATRIX_ACTION_UID_DRIFT", "FUNCTIONAL_CHAIN_ACTION_DRIFT", "FUNCTIONAL_CHAIN_PORT_DRIFT",
    "SEMANTIC_INFERENCE_MUST_BE_FALSE", "EXTERNAL_AUTHORITY",
):
    require(token in material_text, f"015_SOURCE_BOUNDED_MATERIAL_GUARD_MISSING:{token}")

# 016: execute the current classifier helper against exact negative/positive relation probes.
classifier_text = CLASSIFIER.read_text(encoding="utf-8")
prefix = classifier_text.split("if subprocess.run(", 1)[0]
require(prefix != classifier_text, "016_CLASSIFIER_PROBE_BOUNDARY_MISSING")
ns = {"__file__": str(CLASSIFIER), "__name__": "_closure_probe_"}
exec(compile(prefix, str(CLASSIFIER), "exec"), ns, ns)
classify = ns.get("classify")
require(callable(classify), "016_CLASSIFY_HELPER_MISSING")


def idx(actions=None, controls=None, ports=None, transitions=None, events=None):
    return {"actions": actions or {}, "controls": controls or {}, "ports": ports or {}, "transitions": transitions or {}, "events": events or {}}


audit_gap = {"category": "AUDIT_EVENT_NODE_MISSING", "uid": "A", "detail": "missing", "gap_owner": "PAGE_FUNCTIONAL_CONTRACT"}
require(classify(audit_gap, idx(actions={"A": {"action_uid": "A", "state_event": "neighbor.value"}}))["authorized_for_auto_completion"] is False, "016_AUDIT_NEIGHBOR_FALSE_ADMISSION")
audit_ok = classify(audit_gap, idx(actions={"A": {"action_uid": "A", "audit_event_uid": "EVT-A"}}))
require(audit_ok["authorized_for_auto_completion"] is True and audit_ok["proof"]["field"] == "audit_event_uid", "016_AUDIT_EXACT_FIELD_REJECTED")

trigger_gap = {"category": "ACTION_WITHOUT_CONTROL_OR_TRIGGER", "uid": "B", "detail": "missing", "gap_owner": "PAGE_FUNCTIONAL_CONTRACT"}
require(classify(trigger_gap, idx(actions={"B": {"action_uid": "B", "label": "same uid only"}}))["authorized_for_auto_completion"] is False, "016_TRIGGER_NEIGHBOR_FALSE_ADMISSION")
trigger_ok = classify(trigger_gap, idx(actions={"B": {"action_uid": "B"}}, controls={"CTL-B": {"control_uid": "CTL-B", "action_uid": "B"}}))
require(trigger_ok["proof"]["proof_kind"] == "REGISTERED_CONTROL_ACTION_BINDING", "016_CONTROL_TRIGGER_EXACT_RELATION_REJECTED")

state_gap = {"category": "SUCCESS_NEXT_STATE_BINDING_MISSING", "uid": "C", "detail": "missing", "gap_owner": "PAGE_FUNCTIONAL_CONTRACT"}
require(classify(state_gap, idx(actions={"C": {"action_uid": "C", "label": "same uid only"}}))["authorized_for_auto_completion"] is False, "016_STATE_NEIGHBOR_FALSE_ADMISSION")
state_ok = classify(state_gap, idx(actions={"C": {"action_uid": "C", "runtime_binding": {"port_uid": "P-C"}}}, ports={"P-C": {"port_uid": "P-C", "state_event": "READY -> DONE | event.done"}}))
require(state_ok["proof"]["proof_kind"] == "DETERMINISTIC_ACTION_PORT_STATE_EFFECT_PROJECTION" and state_ok["proof"]["port_uid"] == "P-C", "016_ACTION_PORT_STATE_EXACT_JOIN_REJECTED")

illegal_gap = {"category": "STATE_TRANSITION_LEDGER_FIELD_MISSING", "uid": "T-1", "detail": "illegal_transition_tests", "gap_owner": "PAGE_FUNCTIONAL_CONTRACT"}
transition_ok = classify(illegal_gap, idx(transitions={"T-1": {"transition_uid": "T-1", "from_stage": "S-1", "to_stage": "S-2", "trigger_event_uid": "E-1", "gate_uid": "G-1"}}))
proof = transition_ok.get("proof") or {}
require(
    transition_ok.get("authorized_for_auto_completion") is True
    and (proof.get("transition_uid"), proof.get("from_stage"), proof.get("to_stage"), proof.get("trigger"), proof.get("gate")) == ("T-1", "S-1", "S-2", "E-1", "G-1")
    and proof.get("bounded_output") == "GENERATE_NEGATIVE_TESTS_ONLY_NO_STATE_OR_AUTHORITY_VALUE_INVENTION",
    "016_ILLEGAL_TRANSITION_EXACT_PROVENANCE_REJECTED",
)
require(classify(illegal_gap, idx(transitions={"T-1": {"transition_uid": "T-1", "from_stage": "S-1", "to_stage": "S-2"}}))["authorized_for_auto_completion"] is False, "016_INCOMPLETE_TRANSITION_FALSE_ADMISSION")

# 027: canonical Current owner must require complete active-consumer inventory + atomic projection/reference migration + fresh persisted-head validation.
consolidated = mutation.get("consolidated_promotion_control") or {}
for key in ("active_consumer_inventory_required", "stale_predecessor_pin_scan_required", "projection_atomicity_required", "fresh_reverification_required"):
    require(consolidated.get(key) is True, f"027_PROMOTION_CONTROL_MISSING:{key}")
migration = mutation.get("reference_migration_atomicity_control") or {}
for key in (
    "complete_active_reverse_consumer_set_required",
    "all_affected_active_references_must_migrate_in_same_atomic_commit",
    "persisted_head_reference_integrity_gate_required",
    "full_line_regression_required_after_reference_migration",
    "zero_stale_or_broken_current_reference_required",
):
    require(migration.get(key) is True, f"027_REFERENCE_MIGRATION_CONTROL_MISSING:{key}")
classes = set(migration.get("required_inventory_classes") or [])
for cls in ("ACTIVE_WORKFLOW_REFERENCES", "DERIVED_TRUST_IDENTITY_CONSUMERS", "AUTHORITATIVE_DENOMINATOR_CONSUMERS", "LIFECYCLE_OUTPUT_EXPECTATION_CONSUMERS", "ACTIVE_PROJECTORS"):
    require(cls in classes, f"027_ACTIVE_CONSUMER_CLASS_MISSING:{cls}")
require(subprocess.run([sys.executable, str(ACTIVE_REF_GATE)], cwd=str(ROOT), text=True).returncode == 0, "027_ACTIVE_CONSUMER_REFERENCE_GATE_FAILED")
workflow_text = FULL_LINE_WORKFLOW.read_text(encoding="utf-8")
require("governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml" in workflow_text, "FINDING_LEDGER_NOT_BOUND_TO_FULL_LINE")
require("validate_selected_profile_finding_closure.py" in workflow_text, "CLOSURE_GATE_NOT_BOUND_TO_FULL_LINE")

# Once terminalized, enforce the exact terminal schema on every subsequent persisted-head run.
dispositions = {}
for uid, (expected_state, expected_target) in TARGETS.items():
    finding = findings[uid]
    disposition = finding.get("disposition")
    dispositions[uid] = disposition
    if disposition in TERMINAL:
        require(disposition == expected_state, f"TERMINAL_STATE_UNEXPECTED:{uid}:{disposition}")
        for field in REQUIRED_TERMINAL_FIELDS:
            require(finding.get(field) not in (None, "", [], {}), f"TERMINAL_FIELD_MISSING:{uid}:{field}")
        require(finding.get("target_path") == expected_target, f"TERMINAL_TARGET_PATH_DRIFT:{uid}")
        require(finding.get("semantic_fingerprint") not in (None, ""), f"SEMANTIC_FINGERPRINT_MISSING:{uid}")
        if disposition == "ABSORBED_INTO_CANONICAL_OWNER":
            require(finding.get("canonical_owner_uid") not in (None, ""), f"CANONICAL_OWNER_UID_MISSING:{uid}")
            require(finding.get("canonical_rule_uid") not in (None, ""), f"CANONICAL_RULE_UID_MISSING:{uid}")

head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
report = {
    "schema_version": 1,
    "artifact_type": "NON_NORMATIVE_FINDING_CLOSURE_READINESS_EVIDENCE",
    "normative_authority": False,
    "current_governance_uid": current_uid,
    "validated_head_sha": head,
    "historical_evidence_used_as_current_closure_credit": False,
    "finding_results": {
        "FIND-20260915-015": {"status": "PASS", "signature": "RAW_DISCOVERY_VS_STAGE02_OWNING_LAYER_REMEDIATION", "remediation_target": TARGETS["FIND-20260915-015"][1]},
        "FIND-20260915-016": {"status": "PASS", "signature": "SAME_UID_NEIGHBORING_FIELD_FALSE_ADMISSION", "remediation_target": TARGETS["FIND-20260915-016"][1], "exact_behavior_probes": 8},
        "FIND-20260915-027": {"status": "PASS", "signature": "PROMOTION_DERIVED_CONSUMER_PROJECTION_ATOMICITY", "remediation_target": TARGETS["FIND-20260915-027"][1], "active_consumer_reference_gate": "PASS"},
    },
    "ledger_dispositions_at_validation": dispositions,
    "all_target_findings_ready": True,
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"PASS: current governance uid={current_uid}")
print(f"PASS: persisted checkout head={head}")
print("PASS: FIND-20260915-015 exact dual-layer discovery/remediation separation")
print("PASS: FIND-20260915-016 exact missing-field classifier behavior probes")
print("PASS: FIND-20260915-027 canonical promotion projection atomicity + active-consumer gate")
print(f"PASS: report={REPORT.relative_to(ROOT)}")
