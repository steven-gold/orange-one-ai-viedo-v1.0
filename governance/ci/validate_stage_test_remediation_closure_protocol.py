#!/usr/bin/env python3
from pathlib import Path
import sys

from governance_resolver import resolve

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "governance/specifications/current/STAGE_TEST_REMEDIATION_CLOSURE_PROTOCOL.yaml"
MANIFEST = ROOT / "governance/specifications/current/SPECIFICATION_MANIFEST.yaml"
REGISTRY = ROOT / "governance/specifications/REGISTRY.yaml"
STATE = ROOT / "governance/test/ACTIVE_STATE.yaml"

errors = []

for path in (PROTOCOL, MANIFEST, REGISTRY, STATE):
    if not path.is_file():
        errors.append(f"MISSING_REQUIRED_FILE:{path.relative_to(ROOT)}")

if errors:
    for error in errors:
        print("BLOCK:", error, file=sys.stderr)
    raise SystemExit(1)

protocol = PROTOCOL.read_text(encoding="utf-8")
manifest = MANIFEST.read_text(encoding="utf-8")
registry = REGISTRY.read_text(encoding="utf-8")
state = STATE.read_text(encoding="utf-8")
resolved = resolve()
uid = resolved["governance_uid"]

required_protocol_tokens = (
    "artifact_uid: GOV-COMP-STAGE-TEST-REMEDIATION-CLOSURE-PROTOCOL",
    "normative_status: ACTIVE_CURRENT_GOVERNANCE_COMPONENT",
    "single_rule_set: true",
    "governance_calibration_uses_same_execution_rules_as_later_pages: true",
    "alternate_lifecycle_rule_set_for_scale_out: FORBIDDEN",
    "required_at_stage_entry: true",
    "current_specification_registry_and_manifest_are_immutable_during_stage: true",
    "ordinary_mid_stage_normative_promotion: FORBIDDEN",
    "candidate_may_change_current_specification_mid_stage: false",
    "audit_or_diagnosis_only: NOT_REMEDIATION",
    "legal_elimination_count_zero_with_reproducible_remediable_gap: BLOCK_CLOSURE",
    "every_previous_remediable_defect_signature_must_reproduce_count: 0",
    "classification: REMEDIATION_FAILURE",
    "stage_end_governance_consolidation_review:",
    "mandatory_for_every_stage_attempt_after_known_defects_reach_zero_and_hidden_sweep_passes: true",
    "max_atomic_promotion_transactions_per_stage_attempt: 1",
    "promotion_may_occur_before_stage_end_review: false",
    "single_atomic_promotion_commit_required: true",
    "all_required_candidates_for_that_stage_attempt_must_be_consolidated_together: true",
    "previous_stage_attempt_may_close_after_promotion_without_restart: false",
    "post_promotion_restart:",
    "required_when_consolidated_normative_promotion_occurs: true",
    "RESTART_STAGE_FROM_FIRST_MANDATORY_STEP",
    "fatal_specification_contradiction_exception:",
    "may_interrupt_stage_only_when_current_specification_baseline_is_proven_invalid: true",
    "exception_may_be_used_to_bypass_owning_layer_remediation: false",
    "OBTAIN_NEW_EXPLICIT_USER_SPECIFICATION_CHANGE_AUTHORIZATION",
    "stage_execution_used_one_final_governance_uid_from_freeze_through_closure: REQUIRED",
    "pilot_must_complete_all_required_lifecycle_stages_before_scale_out: true",
    "other_pages_may_directly_consume_same_active_governance: true",
    "alternate_execution_rule_set_for_other_pages: FORBIDDEN",
)
for token in required_protocol_tokens:
    if token not in protocol:
        errors.append("PROTOCOL_TOKEN_MISSING:" + token)

expected_steps = [
    "STAGE_CURRENT_SPECIFICATION_BASELINE_FREEZE",
    "CLEAN_PREDECESSOR_BASELINE_RESET",
    "FULL_LINE_MULTIDIRECTIONAL_HIGH_PRESSURE_SYSTEM_GATE",
    "FRESH_PHYSICAL_FILE_STAGE_EXECUTION",
    "DEFECT_AND_GAP_ROOT_CAUSE_CLASSIFICATION_AND_LEDGER",
    "MATERIAL_REMEDIATION_AT_OWNING_LAYER",
    "EXECUTION_OUTPUT_AND_RUNTIME_EVIDENCE_CLEAN_RESET",
    "FULL_LINE_MULTIDIRECTIONAL_HIGH_PRESSURE_SYSTEM_REGRESSION",
    "FRESH_PHYSICAL_FILE_STAGE_REEXECUTION",
    "KNOWN_DEFECT_SIGNATURE_ZERO_REPRODUCTION_CHECK",
    "HIDDEN_DEFECT_MULTIDIRECTIONAL_SWEEP",
    "STAGE_END_GOVERNANCE_CONSOLIDATION_REVIEW",
    "CONSOLIDATED_NORMATIVE_PROMOTION_IF_AUTHORIZED_AND_REQUIRED",
    "POST_PROMOTION_FULL_LINE_AND_STAGE_RESTART_IF_PROMOTED",
    "STAGE_CLOSURE_DECISION",
]

lines = protocol.splitlines()
actual_steps = []
cycle_idx = None
ordered_idx = None
for i, line in enumerate(lines):
    if line == "mandatory_stage_cycle:":
        cycle_idx = i
        break
if cycle_idx is not None:
    for i in range(cycle_idx + 1, len(lines)):
        line = lines[i]
        if line == "  ordered_steps:":
            ordered_idx = i
            break
        if line and not line.startswith("  "):
            break
if ordered_idx is None:
    errors.append("MANDATORY_STAGE_CYCLE_ORDER_MISSING")
else:
    for line in lines[ordered_idx + 1:]:
        if line.startswith("    - "):
            actual_steps.append(line[len("    - "):].strip())
            continue
        break
    if actual_steps != expected_steps:
        errors.append(f"MANDATORY_STAGE_CYCLE_ORDER_DRIFT:{actual_steps!r}")

if manifest.count("file: STAGE_TEST_REMEDIATION_CLOSURE_PROTOCOL.yaml") != 1:
    errors.append("MANIFEST_PROTOCOL_COMPONENT_BINDING_DENOMINATOR")
if "uid: GOV-COMP-STAGE-TEST-REMEDIATION-CLOSURE-PROTOCOL" not in manifest:
    errors.append("MANIFEST_PROTOCOL_UID_MISSING")
if f"artifact_uid: {uid}" not in manifest:
    errors.append("MANIFEST_ACTIVE_UID_MISMATCH")
if "normative_status: ACTIVE_CURRENT_GOVERNANCE" not in manifest:
    errors.append("MANIFEST_MODE_NEUTRAL_ACTIVE_STATUS_MISSING")

# v2.1.15 keeps REGISTRY as the compact stable locator/policy projection. Detailed
# closure semantics remain canonical in the bound Current Manifest + Protocol and
# must not be duplicated into REGISTRY solely to satisfy a validator.
if "component_ref: governance/specifications/current/STAGE_TEST_REMEDIATION_CLOSURE_PROTOCOL.yaml" not in registry:
    errors.append("REGISTRY_PROTOCOL_COMPONENT_REF_MISSING")
registry_required = (
    "status: ACTIVE_CURRENT_GOVERNANCE",
    "stage_current_specification_freeze_required: true",
    "ordinary_mid_stage_promotion: FORBIDDEN",
    "stage_end_consolidated_promotion_only: true",
    "single_canonical_execution_rule_set: true",
    "promotion_requires_new_uid_and_same_stage_restart_from_clean_predecessor_baseline: true",
)
for token in registry_required:
    if token not in registry:
        errors.append("REGISTRY_TOKEN_MISSING:" + token)

manifest_required = (
    "single_canonical_execution_rule_set: true",
    "stage_specification_uid_must_remain_frozen_during_stage: true",
    "required_stage_candidates_consolidated_in_single_atomic_promotion: true",
    "stage_restart_under_new_uid_required_after_promotion: true",
    "pilot_full_lifecycle_required_before_other_page_scale_out: true",
    "later_pages_must_use_same_active_governance_after_calibration: true",
)
for token in manifest_required:
    if token not in manifest:
        errors.append("MANIFEST_PROTOCOL_PROJECTION_TOKEN_MISSING:" + token)

if f"specification_uid: {uid}" not in state:
    errors.append("ACTIVE_STATE_SPECIFICATION_UID_STALE")
state_required = (
    "canonical_execution_rule_set: true",
    "stage_specification_freeze_required: true",
    "ordinary_mid_stage_normative_promotion: BLOCK",
    "candidate_may_be_active_rule_during_stage: false",
    "stage_end_governance_consolidation_review_required: true",
    "max_atomic_normative_promotions_per_stage_attempt: 1",
    "post_promotion_same_stage_restart_required: true",
    "later_pages_must_use_same_active_governance_after_calibration: true",
)
for token in state_required:
    if token not in state:
        errors.append("ACTIVE_STATE_TOKEN_MISSING:" + token)

pre_stage02 = (
    "current_stage: STAGE-01-CLOSED" in state
    and "result: NOT_EXECUTED" in state
)
if pre_stage02:
    if "frozen_specification_uid:" in state:
        errors.append("PRE_STAGE02_FROZEN_UID_MUST_NOT_EXIST_BEFORE_STAGE_ENTRY")
    if "next_stage02_attempt_frozen_governance_uid: null" not in state:
        errors.append("PRE_STAGE02_PENDING_FREEZE_MARKER_MISSING")
else:
    if f"frozen_specification_uid: {uid}" not in state:
        errors.append("ACTIVE_ENTERED_STAGE_FROZEN_UID_MISSING_OR_STALE")

if errors:
    for error in errors:
        print("BLOCK:", error, file=sys.stderr)
    raise SystemExit(1)

print(f"PASS: active governance UID {uid} binds the canonical stage execution-remediation-closure protocol")
print("PASS: mandatory 15-step stage cycle is exact and cannot skip owning-layer remediation")
if pre_stage02:
    print("PASS: Stage-02 is not entered; no frozen Stage-02 UID is fabricated before Stage entry")
else:
    print("PASS: entered Stage is frozen to the active governance UID")
print("PASS: Current Specification is frozen during ordinary stage execution and candidates remain non-normative")
print("PASS: Stage-End consolidated promotion is single-transaction, explicitly authorized, and forces same-stage restart under the new UID")
print("PASS: fatal specification contradiction path is fail-closed and cannot replace ordinary owning-layer remediation")
print("PASS: known defects must reach zero, hidden-defect sweep must pass, and pilot full lifecycle must close before scale-out")
print("PASS: governance calibration and later pages consume one canonical active governance rule set")
