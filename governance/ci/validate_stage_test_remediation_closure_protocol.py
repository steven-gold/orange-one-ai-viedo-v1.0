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
    "audit_pass_with_product_gap_still_present_is_remediation_success: false",
    "repeated_audit_blocked_loop_counts_as_progress: false",
    "discovered_remediable_gap_may_be_left_for_later_stage: false",
    "required_before_first_test_and_every_retest: true",
    "required_before_every_fresh_physical_stage_test_or_retest: true",
    "audit_or_diagnosis_only: NOT_REMEDIATION",
    "evidence_only_without_owning_layer_change: NOT_REMEDIATION",
    "legal_elimination_count_zero_with_reproducible_remediable_gap: BLOCK_CLOSURE",
    "every_previous_remediable_defect_signature_must_reproduce_count: 0",
    "same_signature_reappears_after_claimed_fix:",
    "classification: REMEDIATION_FAILURE",
    "hidden_defect_sweep:",
    "pilot_must_complete_all_required_lifecycle_stages_before_scale_out: true",
    "other_pages_may_consume_completed_governance_before_pilot_full_lifecycle_closure: false",
    "explicit_user_specification_change_directive_required: true",
)
for token in required_protocol_tokens:
    if token not in protocol:
        errors.append("PROTOCOL_TOKEN_MISSING:" + token)

expected_steps = [
    "CLEAN_PREDECESSOR_BASELINE_RESET",
    "FULL_LINE_MULTIDIRECTIONAL_HIGH_PRESSURE_SYSTEM_GATE",
    "FRESH_PHYSICAL_FILE_STAGE_TEST",
    "DEFECT_AND_GAP_ROOT_CAUSE_CLASSIFICATION",
    "MATERIAL_REMEDIATION_AT_OWNING_LAYER",
    "REUSABLE_GOVERNANCE_RULE_PROMOTION_WHEN_REQUIRED",
    "TEST_OUTPUT_AND_RUNTIME_EVIDENCE_CLEAN_RESET",
    "FULL_LINE_MULTIDIRECTIONAL_HIGH_PRESSURE_SYSTEM_REGRESSION",
    "FRESH_PHYSICAL_FILE_STAGE_RETEST",
    "KNOWN_DEFECT_SIGNATURE_ZERO_REPRODUCTION_CHECK",
    "HIDDEN_DEFECT_MULTIDIRECTIONAL_SWEEP",
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
if "component_ref: governance/specifications/current/STAGE_TEST_REMEDIATION_CLOSURE_PROTOCOL.yaml" not in registry:
    errors.append("REGISTRY_PROTOCOL_COMPONENT_REF_MISSING")
if "audit_only_blocked_loop_is_progress: false" not in registry:
    errors.append("REGISTRY_AUDIT_ONLY_PROGRESS_GUARD_MISSING")
if "material_remediation_required_for_remediable_gap: true" not in registry:
    errors.append("REGISTRY_MATERIAL_REMEDIATION_GUARD_MISSING")
if "pilot_full_lifecycle_before_other_page_scale_out: true" not in registry:
    errors.append("REGISTRY_PILOT_SCALEOUT_GUARD_MISSING")

if f"specification_uid: {uid}" not in state:
    errors.append("ACTIVE_STATE_SPECIFICATION_UID_STALE")
if "specification_ref: governance/specifications/current/STAGE_TEST_REMEDIATION_CLOSURE_PROTOCOL.yaml" not in state:
    errors.append("ACTIVE_STATE_PROTOCOL_BINDING_MISSING")
if "audit_only_blocked_loop_may_count_as_progress: false" not in state:
    errors.append("ACTIVE_STATE_AUDIT_LOOP_GUARD_MISSING")

if errors:
    for error in errors:
        print("BLOCK:", error, file=sys.stderr)
    raise SystemExit(1)

print(f"PASS: active governance UID {uid} binds the stage test remediation closure protocol")
print("PASS: mandatory stage cycle order is exact and cannot skip remediation")
print("PASS: audit-only BLOCKED loops cannot count as remediation or progress")
print("PASS: previously discovered remediable defect signatures must reach zero on fresh retest")
print("PASS: hidden-defect sweep and pilot-before-scale-out gates are enforced")
