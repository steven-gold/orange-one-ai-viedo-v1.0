#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "governance/test/stage02"
R12 = BASE / "STAGE02_AUTHORITY_DEPENDENCY_RECLASSIFICATION_R12.yaml"
OUT = BASE / "STAGE02_FUNCTIONAL_CONTRACT_REMEDIATION_PROBLEM_REGISTER_R19.yaml"
TRACES = {
    "AUDIT_EVENT_NODE_MISSING": (BASE / "STAGE02_AUDIT_EVENT_DEPENDENCY_TRACE_R13.yaml", "R13"),
    "PAYLOAD_INPUT_CONTRACT_MISSING": (BASE / "STAGE02_PAYLOAD_DEPENDENCY_TRACE_R14.yaml", "R14"),
    "POST_ACTION_VALIDATION_NODE_MISSING": (BASE / "STAGE02_POST_ACTION_VALIDATION_DEPENDENCY_TRACE_R15.yaml", "R15"),
    "FAILURE_STATE_ERROR_BINDING_MISSING": (BASE / "STAGE02_FAILURE_ERROR_RECOVERY_DEPENDENCY_TRACE_R16.yaml", "R16"),
    "STATE_TRANSITION_LEDGER_FIELD_MISSING": (BASE / "STAGE02_STATE_TRANSITION_LEDGER_DEPENDENCY_TRACE_R17.yaml", "R17"),
    "ACTION_WITHOUT_CONTROL_OR_TRIGGER": (BASE / "STAGE02_ACTION_CONTROL_TRIGGER_DEPENDENCY_TRACE_R18.yaml", "R18"),
}
REMEDIATION = {
    "AUDIT_EVENT_NODE_MISSING": {
        "owning_contract": "PAGE_ACTION_PORT_EVENT_BINDING",
        "required_definition": "Bind an explicit audit/event UID to the exact action/port/operation identity at the Stage-02 owning functional-contract layer.",
        "forbidden_substitutions": ["state_event prose", "action-name-derived event UID", "historical non-current event"],
    },
    "PAYLOAD_INPUT_CONTRACT_MISSING": {
        "owning_contract": "PAGE_OPERATION_REQUEST_PAYLOAD_SCHEMA",
        "required_definition": "Define the structured request/input schema for the exact action/port/operation identity at the Stage-02 owning functional-contract layer.",
        "forbidden_substitutions": ["payload_rule prose as schema", "route/path as schema", "AI-inferred fields"],
    },
    "POST_ACTION_VALIDATION_NODE_MISSING": {
        "owning_contract": "PAGE_OPERATION_POST_ACTION_VALIDATION",
        "required_definition": "Define explicit post-action validation/success/evaluation criteria for the exact action/operation identity.",
        "forbidden_substitutions": ["state_event as validation", "result text as validation", "precondition gate as postcondition"],
    },
    "FAILURE_STATE_ERROR_BINDING_MISSING": {
        "owning_contract": "PAGE_ACTION_OPERATION_FAILURE_ERROR_RECOVERY",
        "required_definition": "Define exact failure/error/recovery binding for the action, exact port/operation, or exact shared operation identity as applicable.",
        "forbidden_substitutions": ["state/result signal as recovery", "semantic error inference", "historical non-current recovery rule"],
    },
    "STATE_TRANSITION_LEDGER_FIELD_MISSING": {
        "owning_contract": "PAGE_STAGE_TRANSITION_LEDGER",
        "required_definition": "Define the missing ledger field physically on the same exact transition_uid at the Stage-02 owning functional-contract layer.",
        "forbidden_substitutions": ["action owner as mutation_owner", "error_uid as failure_state", "state_event as audit_event_uid", "cross-node recovery inference"],
    },
    "ACTION_WITHOUT_CONTROL_OR_TRIGGER": {
        "owning_contract": "PAGE_CONTROL_OR_REGISTERED_TRIGGER_BINDING",
        "required_definition": "Bind the action to an exact UI control or exact registered stage/system trigger.",
        "forbidden_substitutions": ["integration-port exposure as trigger", "operation existence as control", "semantic trigger inference"],
    },
}


def die(msg: str):
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def identity(row):
    return (
        row.get("blocker_uid"), row.get("scope"), row.get("category"),
        row.get("target_uid"), row.get("missing_field_or_relation"),
    )


def evidence_summary(category: str, row: dict):
    if category == "AUDIT_EVENT_NODE_MISSING":
        return {
            "trace_classification": row.get("classification"),
            "exact_event_uid_count": len(row.get("unique_exact_event_uids") or []),
            "current_identity_match_count": len(row.get("current_identity_matches") or []),
        }
    if category == "PAYLOAD_INPUT_CONTRACT_MISSING":
        return {
            "trace_classification": row.get("classification"),
            "structured_schema_evidence_count": len(row.get("structured_payload_schema_evidence") or []),
            "frozen_payload_rule_evidence_count": len(row.get("frozen_payload_rule_evidence") or []),
            "current_identity_match_count": len(row.get("current_identity_matches") or []),
        }
    if category == "POST_ACTION_VALIDATION_NODE_MISSING":
        return {
            "trace_classification": row.get("classification"),
            "validation_contract_evidence_count": len(row.get("post_action_validation_contract_evidence") or []),
            "result_or_state_signal_count": len(row.get("result_or_state_signal_evidence") or []),
            "current_identity_match_count": len(row.get("current_identity_matches") or []),
        }
    if category == "FAILURE_STATE_ERROR_BINDING_MISSING":
        return {
            "trace_classification": row.get("classification"),
            "failure_error_recovery_binding_count": len(row.get("failure_error_recovery_binding_evidence") or []),
            "result_or_state_signal_count": len(row.get("result_or_state_signal_evidence") or []),
            "identity_kind": (row.get("trace") or {}).get("identity_kind"),
        }
    if category == "STATE_TRANSITION_LEDGER_FIELD_MISSING":
        return {
            "trace_classification": row.get("classification"),
            "exact_field_evidence_count": len(row.get("exact_transition_ledger_field_evidence") or []),
            "transition_identity_or_signal_count": len(row.get("transition_identity_or_signal_evidence") or []),
            "unique_exact_field_value_count": row.get("unique_exact_field_value_count"),
        }
    return {
        "trace_classification": row.get("classification"),
        "exact_control_binding_count": len(row.get("exact_control_binding_evidence") or []),
        "exact_trigger_binding_count": len(row.get("exact_trigger_binding_evidence") or []),
        "nonqualifying_lineage_count": len(row.get("nonqualifying_lineage_evidence") or []),
    }


def main():
    r12 = load(R12)
    baseline = r12.get("records") or []
    if len(baseline) != 150 or any(r.get("classification") != "UNRESOLVED_FUNCTIONAL_CONTRACT_GAP" for r in baseline):
        die("R19_REQUIRES_EXACT_R12_150_UNRESOLVED_BASELINE")

    trace_rows = {}
    trace_meta = {}
    for category, (path, revision) in TRACES.items():
        doc = load(path)
        rows = doc.get("records") or []
        for row in rows:
            key = identity(row)
            if key in trace_rows:
                die(f"R19_DUPLICATE_TRACE_IDENTITY:{key}")
            trace_rows[key] = row
            trace_meta[key] = {"trace_revision": revision, "trace_path": str(path.relative_to(ROOT))}

    if len(trace_rows) != 150:
        die(f"R19_TRACE_TOTAL_NOT_150:{len(trace_rows)}")
    base_ids = {identity(r) for r in baseline}
    if base_ids != set(trace_rows):
        missing = sorted(base_ids - set(trace_rows))[:10]
        extra = sorted(set(trace_rows) - base_ids)[:10]
        die(f"R19_TRACE_COVERAGE_DRIFT:missing={missing}:extra={extra}")

    problems = []
    categories = Counter()
    scopes = Counter()
    trace_classes = Counter()
    for base in baseline:
        key = identity(base)
        trace = trace_rows[key]
        category = base["category"]
        if trace.get("materialization_candidate") is not False:
            die(f"R19_UNEXPECTED_MATERIALIZATION_CANDIDATE:{base['blocker_uid']}:{trace.get('classification')}")
        if trace.get("blocker_reduction_credit") != 0:
            die(f"R19_FALSE_TRACE_REDUCTION:{base['blocker_uid']}")
        categories[category] += 1
        scopes[base["scope"]] += 1
        trace_classes[trace.get("classification")] += 1
        rule = REMEDIATION[category]
        problems.append({
            "problem_uid": f"STAGE02-FUNCTIONAL-REMEDIATION-{len(problems)+1:03d}",
            "blocker_uid": base["blocker_uid"],
            "scope": base["scope"],
            "category": category,
            "target_uid": base["target_uid"],
            "missing_field_or_relation": base.get("missing_field_or_relation"),
            "problem_status": "OPEN_FUNCTIONAL_CONTRACT_REMEDIATION_REQUIRED",
            "product_authority_gap_proven": False,
            "deterministic_materialization_candidate": False,
            "owning_layer": "STAGE02_PAGE_FUNCTIONAL_CONTRACT",
            "owning_contract": rule["owning_contract"],
            "required_definition": rule["required_definition"],
            "forbidden_substitutions": rule["forbidden_substitutions"],
            "trace_ref": trace_meta[key],
            "trace_evidence_summary": evidence_summary(category, trace),
            "current_specification_mutation_allowed": False,
            "historical_non_current_authority_allowed": False,
            "ai_invented_contract_value_allowed": False,
            "blocker_reduction_credit": 0,
            "closure_requirement": "OWNING_LAYER_CONTRACT_DEFINITION_OR_CURRENT_ADMISSIBLE_EXACT_EVIDENCE -> BOUNDED_MATERIALIZATION -> CLEAN_RESET -> FULL_LINE_GATE -> FRESH_STAGE02_REEXECUTION -> SIGNATURE_ZERO",
        })

    expected_categories = Counter({
        "FAILURE_STATE_ERROR_BINDING_MISSING": 44,
        "POST_ACTION_VALIDATION_NODE_MISSING": 18,
        "PAYLOAD_INPUT_CONTRACT_MISSING": 34,
        "ACTION_WITHOUT_CONTROL_OR_TRIGGER": 1,
        "AUDIT_EVENT_NODE_MISSING": 13,
        "STATE_TRANSITION_LEDGER_FIELD_MISSING": 40,
    })
    if categories != expected_categories or scopes != Counter({"ASSET-01": 110, "CORE-01": 40}):
        die(f"R19_DENOMINATOR_DRIFT:categories={dict(categories)}:scopes={dict(scopes)}")

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    doc = {
        "schema_version": 1,
        "artifact_type": "NON_NORMATIVE_STAGE02_FUNCTIONAL_CONTRACT_REMEDIATION_PROBLEM_REGISTER_R19",
        "normative_authority": False,
        "stage_uid": "STAGE-02",
        "cycle": "FUNCTIONAL_CONTRACT_REMEDIATION_PROBLEM_REGISTRATION_R19",
        "source_head_sha": head,
        "source_contracts": {
            "r12_identity_baseline": str(R12.relative_to(ROOT)),
            "exact_trace_sources": {cat: {"path": str(path.relative_to(ROOT)), "revision": rev} for cat, (path, rev) in TRACES.items()},
        },
        "registration_contract": {
            "purpose": "Register verified Stage-02 functional-contract gaps as remediation problems without promoting them to Product Authority gaps or inventing missing values.",
            "trace_classification_is_not_normative_authority": True,
            "absence_alone_proves_product_authority": False,
            "ai_may_define_missing_contract_value": False,
            "historical_non_current_authority_may_fill_gap": False,
            "current_specification_may_mutate_mid_stage": False,
            "problem_registration_reduces_blocker": False,
        },
        "denominators": {
            "total_registered_problems": 150,
            "scope_counts": dict(scopes),
            "category_counts": dict(categories),
            "trace_classification_counts": dict(trace_classes),
            "deterministic_materialization_candidates": 0,
            "product_authority_gaps_proven": 0,
            "effective_stage02_blocker_reduction_claimed": 0,
        },
        "problems": problems,
        "stage02_status": "BLOCKED",
        "stage02_effective_blocker_count": 150,
        "next_execution_gate": "FUNCTIONAL_CONTRACT_OWNING_LAYER_REMEDIATION_INPUT_REQUIRED",
        "stage03_allowed": False,
        "website_construction_allowed": False,
        "deployment_allowed": False,
    }
    OUT.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"PASS: R19 registered exact 150 verified functional-contract remediation problems categories={dict(categories)}")
    print(f"PASS: trace classifications aggregated without authority promotion classes={dict(trace_classes)}")
    print("PASS: 0 deterministic candidates, 0 proven Product Authority gaps, 0 blocker reduction")


if __name__ == "__main__":
    main()
