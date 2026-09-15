#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "governance/test/stage02"
R12 = BASE / "STAGE02_AUTHORITY_DEPENDENCY_RECLASSIFICATION_R12.yaml"
R19 = BASE / "STAGE02_FUNCTIONAL_CONTRACT_REMEDIATION_PROBLEM_REGISTER_R19.yaml"
EXPECTED = Counter({
    "FAILURE_STATE_ERROR_BINDING_MISSING": 44,
    "POST_ACTION_VALIDATION_NODE_MISSING": 18,
    "PAYLOAD_INPUT_CONTRACT_MISSING": 34,
    "ACTION_WITHOUT_CONTROL_OR_TRIGGER": 1,
    "AUDIT_EVENT_NODE_MISSING": 13,
    "STATE_TRANSITION_LEDGER_FIELD_MISSING": 40,
})


def die(msg):
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def base_identity(row):
    return (row.get("blocker_uid"), row.get("scope"), row.get("category"), row.get("target_uid"), row.get("missing_field_or_relation"))


def problem_identity(row):
    return (row.get("blocker_uid"), row.get("scope"), row.get("category"), row.get("target_uid"), row.get("missing_field_or_relation"))


def main():
    r12, r19 = load(R12), load(R19)
    if r19.get("artifact_type") != "NON_NORMATIVE_STAGE02_FUNCTIONAL_CONTRACT_REMEDIATION_PROBLEM_REGISTER_R19" or r19.get("normative_authority") is not False:
        die("R19_ARTIFACT_IDENTITY")
    baseline = r12.get("records") or []
    problems = r19.get("problems") or []
    if len(baseline) != 150 or len(problems) != 150:
        die(f"R19_DENOMINATOR:{len(baseline)}:{len(problems)}")
    if {base_identity(x) for x in baseline} != {problem_identity(x) for x in problems} or len({problem_identity(x) for x in problems}) != 150:
        die("R19_EXACT_IDENTITY_COVERAGE_DRIFT")
    if Counter(p.get("scope") for p in problems) != Counter({"ASSET-01": 110, "CORE-01": 40}):
        die("R19_SCOPE_DRIFT")
    if Counter(p.get("category") for p in problems) != EXPECTED:
        die("R19_CATEGORY_DRIFT")
    if len({p.get("problem_uid") for p in problems}) != 150:
        die("R19_PROBLEM_UID_NOT_UNIQUE")

    for p in problems:
        uid = p.get("problem_uid")
        if p.get("problem_status") != "OPEN_FUNCTIONAL_CONTRACT_REMEDIATION_REQUIRED":
            die(f"R19_BAD_STATUS:{uid}")
        if p.get("product_authority_gap_proven") is not False or p.get("deterministic_materialization_candidate") is not False:
            die(f"R19_FALSE_AUTHORITY_OR_CANDIDATE:{uid}")
        if p.get("owning_layer") != "STAGE02_PAGE_FUNCTIONAL_CONTRACT" or not p.get("owning_contract") or not p.get("required_definition"):
            die(f"R19_OWNING_LAYER_INCOMPLETE:{uid}")
        if not isinstance(p.get("forbidden_substitutions"), list) or not p.get("forbidden_substitutions"):
            die(f"R19_FORBIDDEN_SUBSTITUTIONS_MISSING:{uid}")
        ref = p.get("trace_ref") or {}
        if not ref.get("trace_revision") or not ref.get("trace_path"):
            die(f"R19_TRACE_REF_MISSING:{uid}")
        summary = p.get("trace_evidence_summary") or {}
        if not summary.get("trace_classification"):
            die(f"R19_TRACE_CLASSIFICATION_MISSING:{uid}")
        for key in ("current_specification_mutation_allowed", "historical_non_current_authority_allowed", "ai_invented_contract_value_allowed"):
            if p.get(key) is not False:
                die(f"R19_SAFETY_FLAG:{uid}:{key}")
        if p.get("blocker_reduction_credit") != 0:
            die(f"R19_FALSE_REDUCTION:{uid}")
        if "FRESH_STAGE02_REEXECUTION" not in p.get("closure_requirement", "") or "SIGNATURE_ZERO" not in p.get("closure_requirement", ""):
            die(f"R19_CLOSURE_REQUIREMENT_INCOMPLETE:{uid}")

    den = r19.get("denominators") or {}
    if den.get("total_registered_problems") != 150 or den.get("scope_counts") != {"ASSET-01": 110, "CORE-01": 40} or den.get("category_counts") != dict(EXPECTED):
        die("R19_DENOMINATOR_DRIFT")
    if sum((den.get("trace_classification_counts") or {}).values()) != 150:
        die("R19_TRACE_CLASSIFICATION_TOTAL_DRIFT")
    if den.get("deterministic_materialization_candidates") != 0 or den.get("product_authority_gaps_proven") != 0 or den.get("effective_stage02_blocker_reduction_claimed") != 0:
        die("R19_FALSE_CLOSURE_CREDIT")

    contract = r19.get("registration_contract") or {}
    if contract.get("trace_classification_is_not_normative_authority") is not True or contract.get("absence_alone_proves_product_authority") is not False or contract.get("ai_may_define_missing_contract_value") is not False or contract.get("historical_non_current_authority_may_fill_gap") is not False or contract.get("current_specification_may_mutate_mid_stage") is not False or contract.get("problem_registration_reduces_blocker") is not False:
        die("R19_REGISTRATION_SAFETY_CONTRACT")
    if r19.get("stage02_status") != "BLOCKED" or r19.get("stage02_effective_blocker_count") != 150 or r19.get("next_execution_gate") != "FUNCTIONAL_CONTRACT_OWNING_LAYER_REMEDIATION_INPUT_REQUIRED":
        die("R19_STAGE_STATUS_DRIFT")
    if r19.get("stage03_allowed") is not False or r19.get("website_construction_allowed") is not False or r19.get("deployment_allowed") is not False:
        die("R19_DOWNSTREAM_FALSE_ALLOW")

    print("PASS: R19 exact 150 remediation problems cover R12 identities with 110 ASSET / 40 CORE")
    print(f"PASS: exact category counts={dict(EXPECTED)}")
    print("PASS: no Product Authority promotion, no invented values, no blocker reduction")


if __name__ == "__main__":
    main()
