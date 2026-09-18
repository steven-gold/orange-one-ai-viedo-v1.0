#!/usr/bin/env python3
import yaml
from specification_mutation_guard import cycle_boundary_errors

def dump(obj):
    return yaml.safe_dump(obj, sort_keys=False)

def receipt(boundary, disposition="CLOSED_VERIFIED", fatal=False):
    return "\n".join([
        f"governance_mutation_boundary: {boundary}",
        "predecessor_execution_cycle_terminal: true",
        f"predecessor_execution_cycle_terminal_disposition: {disposition}",
        "predecessor_execution_cycle_evidence_ref: governance/test/terminal-evidence.yaml",
        f"fatal_specification_contradiction_proven: {'true' if fatal else 'false'}",
    ]) + "\n"

def gov_parent():
    return {
        "current_primary_task_layer": "GOVERNANCE_MAINTENANCE",
        "resume_control": {"current_work_unit_uid": "WU-GOV-001"},
        "active_work_unit": {
            "work_unit_uid": "WU-GOV-001",
            "primary_task_layer": "GOVERNANCE_MAINTENANCE",
            "current_status": "ACTIVE",
        },
    }

active_product = {
    "current_primary_task_layer": "PRODUCT_STAGE_EXECUTION",
    "resume_control": {"current_work_unit_uid": "WU-PRODUCT-001"},
    "active_work_unit": {
        "work_unit_uid": "WU-PRODUCT-001",
        "primary_task_layer": "PRODUCT_STAGE_EXECUTION",
        "current_status": "ACTIVE_PREEXECUTION",
    },
}
errs = cycle_boundary_errors(
    receipt("STAGE_END_CONSOLIDATION_AFTER_TERMINAL_CYCLE"),
    dump(active_product),
    dump(gov_parent()),
)
assert any("ACTIVE_NON_GOVERNANCE_EXECUTION_CYCLE" in x for x in errs), errs

suspended_product = {
    "current_primary_task_layer": "GOVERNANCE_MAINTENANCE",
    "resume_control": {"current_work_unit_uid": "WU-GOV-OLD"},
    "active_work_unit": {
        "work_unit_uid": "WU-GOV-OLD",
        "primary_task_layer": "GOVERNANCE_MAINTENANCE",
        "current_status": "ACTIVE",
    },
    "suspended_product_work_unit": {
        "work_unit_uid": "WU-PRODUCT-SUSPENDED",
        "primary_task_layer": "PRODUCT_STAGE_EXECUTION",
        "current_status": "ACTIVE_PREEXECUTION",
    },
}
errs = cycle_boundary_errors(
    receipt("STAGE_END_CONSOLIDATION_AFTER_TERMINAL_CYCLE"),
    dump(suspended_product),
    dump(gov_parent()),
)
assert "PROTECTED_POLICY_MUTATION_WITH_SUSPENDED_NONTERMINAL_PRODUCT_WORK_UNIT" in errs, errs

terminal_baseline = {
    "current_primary_task_layer": "PRODUCT_STAGE_EXECUTION",
    "resume_control": {"current_work_unit_uid": None},
    "status": "STAGE_END_CLOSED_VERIFIED",
}
errs = cycle_boundary_errors(
    receipt("STAGE_END_CONSOLIDATION_AFTER_TERMINAL_CYCLE"),
    dump(terminal_baseline),
    dump(gov_parent()),
)
assert errs == [], errs

errs = cycle_boundary_errors(
    receipt("FATAL_SPEC_CONTRADICTION_AFTER_TERMINAL_BLOCK", disposition="CLOSED_VERIFIED", fatal=False),
    dump(terminal_baseline),
    dump(gov_parent()),
)
assert "FATAL_SPECIFICATION_CONTRADICTION_NOT_PROVEN" in errs, errs
assert "FATAL_SPEC_BOUNDARY_WITHOUT_BLOCKED_OR_TERMINATED_DISPOSITION" in errs, errs

not_gov_parent = {
    "current_primary_task_layer": "PRODUCT_STAGE_EXECUTION",
    "resume_control": {"current_work_unit_uid": None},
}
errs = cycle_boundary_errors(
    receipt("OUTSIDE_GOVERNED_EXECUTION_CYCLE"),
    dump(terminal_baseline),
    dump(not_gov_parent),
)
assert any("PARENT_PRIMARY_TASK_LAYER_NOT_GOVERNANCE_MAINTENANCE" in x for x in errs), errs

errs = cycle_boundary_errors("", dump(terminal_baseline), dump(gov_parent()))
assert any("GOVERNANCE_MUTATION_BOUNDARY_INVALID" in x for x in errs), errs

print("PASS: specification mutation cycle-boundary negative regression 6/6")
