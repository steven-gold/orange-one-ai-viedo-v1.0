#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
FRESH = ROOT / "00_SOURCE_INTAKE/fresh_run_003"
STAGE2 = FRESH / "04_PAGE_FUNCTIONAL_CONTRACT"
R12 = ROOT / "governance/test/stage02/STAGE02_AUTHORITY_DEPENDENCY_RECLASSIFICATION_R12.yaml"
R17 = ROOT / "governance/test/stage02/STAGE02_STATE_TRANSITION_LEDGER_DEPENDENCY_TRACE_R17.yaml"
EXT_EVIDENCE = STAGE2 / "EXTERNAL_AUTHORITY/STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE.yaml"
ALLOWED = {
    "EXACT_TRANSITION_LEDGER_FIELD_FOUND",
    "CONFLICTING_TRANSITION_LEDGER_FIELD_VALUES",
    "FROZEN_TRANSITION_IDENTITY_ONLY_FIELD_MISSING",
    "CURRENT_FROZEN_TRANSITION_LEDGER_CONTRACT_MISSING",
}
EXPECTED_FIELDS = Counter({"mutation_owner": 10, "failure_state": 10, "recovery": 10, "audit_event_uid": 10})


def die(msg: str) -> None:
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def normalize(raw_path: str) -> str:
    if raw_path.startswith("04_PAGE_FUNCTIONAL_CONTRACT/"):
        return str((FRESH / raw_path).relative_to(ROOT))
    if raw_path.startswith("00_SOURCE_INTAKE/fresh_run_003/"):
        return raw_path
    die(f"R17_BAD_EXTERNAL_PATH:{raw_path}")


def current_external_paths():
    doc = load(EXT_EVIDENCE)
    paths = set()
    for _, entry in (doc.get("materialized_authorities") or {}).items():
        if not isinstance(entry, dict) or entry.get("manifest_current") is not True:
            continue
        if entry.get("authority_identity_status") not in {"EXACT_MATCH", "EXACT_CHAIN_LOCATED"}:
            continue
        if entry.get("materialized_path"):
            paths.add(normalize(entry["materialized_path"]))
        for item in entry.get("authority_chain") or []:
            if isinstance(item, dict) and item.get("materialized_path"):
                paths.add(normalize(item["materialized_path"]))
    return paths


def identity(row):
    return (
        row.get("blocker_uid"), row.get("scope"), row.get("category"),
        row.get("target_uid"), row.get("missing_field_or_relation"),
    )


def validate_evidence_path(uid, item, allowed_external):
    path = item.get("path", "")
    kind = item.get("source_kind", "")
    if kind == "FROZEN_FUNCTIONAL_CHAIN":
        if path not in {
            "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/ASSET-01/FUNCTIONAL_CHAIN_SPEC.yaml",
            "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/CORE-01/FUNCTIONAL_CHAIN_SPEC.yaml",
        }:
            die(f"R17_BAD_FUNCTIONAL_CHAIN_EVIDENCE:{uid}:{path}")
    elif kind == "CURRENT_PAGE_AUTHORITY_EXACT_CAPTURE":
        if path not in {
            "00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml",
            "00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml",
        }:
            die(f"R17_BAD_PAGE_AUTHORITY_EVIDENCE:{uid}:{path}")
    elif kind.startswith("CURRENT_EXTERNAL_AUTHORITY:"):
        if path not in allowed_external:
            die(f"R17_NON_CURRENT_EXTERNAL_EVIDENCE:{uid}:{path}")
    else:
        die(f"R17_UNKNOWN_EVIDENCE_KIND:{uid}:{kind}")


def main():
    r12, r17 = load(R12), load(R17)
    if r17.get("artifact_type") != "NON_NORMATIVE_STAGE02_STATE_TRANSITION_LEDGER_DEPENDENCY_TRACE_R17" or r17.get("normative_authority") is not False:
        die("R17_ARTIFACT_IDENTITY")
    if r17.get("source_contracts", {}).get("r12_classification_accepted_as_authority") is not False:
        die("R17_R12_CLASSIFICATION_AUTHORITY_LEAK")

    old = [r for r in (r12.get("records") or []) if r.get("category") == "STATE_TRANSITION_LEDGER_FIELD_MISSING"]
    rows = r17.get("records") or []
    if len(old) != 40 or len(rows) != 40:
        die(f"R17_DENOMINATOR:{len(old)}:{len(rows)}")
    if {identity(r) for r in old} != {identity(r) for r in rows} or len({identity(r) for r in rows}) != 40:
        die("R17_IDENTITY_COVERAGE_DRIFT")
    if Counter(r.get("scope") for r in rows) != Counter({"ASSET-01": 20, "CORE-01": 20}):
        die("R17_SCOPE_DRIFT")
    if Counter(r.get("missing_field_or_relation") for r in rows) != EXPECTED_FIELDS:
        die("R17_FIELD_DRIFT")
    if len({r.get("target_uid") for r in rows}) != 10:
        die("R17_TRANSITION_COUNT_DRIFT")

    allowed_external = current_external_paths()
    counts = Counter()
    for row in rows:
        uid, cls = row.get("blocker_uid"), row.get("classification")
        if cls not in ALLOWED:
            die(f"R17_BAD_CLASS:{uid}:{cls}")
        counts[cls] += 1
        for key in (
            "r12_classification_used_as_authority",
            "cross_node_field_inference_used",
            "action_owner_promoted_to_mutation_owner",
            "error_uid_promoted_to_failure_state",
            "state_event_promoted_to_audit_event_uid",
            "semantic_recovery_inference_used",
            "historical_non_current_authority_used",
        ):
            if row.get(key) is not False:
                die(f"R17_SAFETY_FLAG:{uid}:{key}:{row.get(key)}")
        if row.get("blocker_reduction_credit") != 0:
            die(f"R17_FALSE_REDUCTION:{uid}")

        ident = row.get("transition_identity") or {}
        if ident.get("transition_uid") != row.get("target_uid") or not ident.get("from_stage") or not ident.get("to_stage"):
            die(f"R17_TRANSITION_IDENTITY_INVALID:{uid}")
        evidence = row.get("exact_transition_ledger_field_evidence") or []
        signals = row.get("transition_identity_or_signal_evidence") or []
        for item in evidence + signals:
            validate_evidence_path(uid, item, allowed_external)
        missing = row.get("missing_field_or_relation")
        if any(item.get("key") != missing for item in evidence):
            die(f"R17_WRONG_FIELD_EVIDENCE:{uid}:{missing}")
        n = row.get("unique_exact_field_value_count")
        if cls == "EXACT_TRANSITION_LEDGER_FIELD_FOUND":
            if n != 1 or not evidence or row.get("materialization_candidate") is not True:
                die(f"R17_EXACT_FIELD_INVALID:{uid}:{n}")
        elif cls == "CONFLICTING_TRANSITION_LEDGER_FIELD_VALUES":
            if not isinstance(n, int) or n < 2 or not evidence or row.get("materialization_candidate") is not False:
                die(f"R17_CONFLICT_INVALID:{uid}:{n}")
        elif cls == "FROZEN_TRANSITION_IDENTITY_ONLY_FIELD_MISSING":
            if n != 0 or evidence or not signals or row.get("materialization_candidate") is not False:
                die(f"R17_IDENTITY_ONLY_INVALID:{uid}")
        else:
            if n != 0 or evidence or signals or row.get("materialization_candidate") is not False:
                die(f"R17_MISSING_INVALID:{uid}")

    den = r17.get("denominators") or {}
    expected = {
        "exact_transition_ledger_field_found": counts["EXACT_TRANSITION_LEDGER_FIELD_FOUND"],
        "conflicting_transition_ledger_field_values": counts["CONFLICTING_TRANSITION_LEDGER_FIELD_VALUES"],
        "frozen_transition_identity_only_field_missing": counts["FROZEN_TRANSITION_IDENTITY_ONLY_FIELD_MISSING"],
        "current_frozen_transition_ledger_contract_missing": counts["CURRENT_FROZEN_TRANSITION_LEDGER_CONTRACT_MISSING"],
    }
    if den.get("state_transition_ledger_field_gaps_traced") != 40 or den.get("unique_transition_count") != 10 or sum(expected.values()) != 40:
        die("R17_TOTAL_DENOMINATOR_DRIFT")
    if den.get("scope_counts") != {"ASSET-01": 20, "CORE-01": 20}:
        die("R17_SCOPE_DENOMINATOR_DRIFT")
    if den.get("missing_field_counts") != dict(EXPECTED_FIELDS):
        die(f"R17_FIELD_COUNT_DRIFT:{den.get('missing_field_counts')}")
    for key, value in expected.items():
        if den.get(key) != value:
            die(f"R17_COUNT_DRIFT:{key}:{den.get(key)}:{value}")
    if den.get("effective_stage02_blocker_reduction_claimed") != 0:
        die("R17_FALSE_GLOBAL_REDUCTION")

    contract = r17.get("trace_contract") or {}
    required_false = (
        "action_owner_may_supply_mutation_owner",
        "error_uid_may_supply_failure_state",
        "state_event_may_supply_audit_event_uid",
        "semantic_recovery_inference_allowed",
        "cross_node_field_inference_allowed",
        "classification_alone_may_reduce_blocker",
    )
    if any(contract.get(k) is not False for k in required_false):
        die("R17_INFERENCE_OR_FALSE_PROMOTION_ALLOWED")
    if contract.get("field_must_be_physically_present_on_same_exact_transition_uid") is not True:
        die("R17_SAME_TRANSITION_RULE_MISSING")
    if r17.get("stage02_status") != "BLOCKED" or r17.get("stage03_allowed") is not False or r17.get("website_construction_allowed") is not False or r17.get("deployment_allowed") is not False:
        die("R17_DOWNSTREAM_FALSE_ALLOW")

    print(f"PASS: R17 exact 40 transition-ledger field identities verified classifications={dict(counts)}")
    print("PASS: all four ledger fields require physical same-transition-UID evidence; cross-node inference rejected")
    print("PASS: zero blocker reduction until separate bounded materialization and fresh reexecution")


if __name__ == "__main__":
    main()
