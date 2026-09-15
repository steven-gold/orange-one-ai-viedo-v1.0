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
R15 = ROOT / "governance/test/stage02/STAGE02_POST_ACTION_VALIDATION_DEPENDENCY_TRACE_R15.yaml"
EXT_EVIDENCE = STAGE2 / "EXTERNAL_AUTHORITY/STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE.yaml"
ALLOWED = {
    "EXACT_POST_ACTION_VALIDATION_CONTRACT_FOUND",
    "CONFLICTING_POST_ACTION_VALIDATION_CONTRACTS",
    "FROZEN_RESULT_OR_STATE_SIGNAL_ONLY",
    "CURRENT_FROZEN_POST_ACTION_VALIDATION_CONTRACT_MISSING",
}


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
    die(f"R15_BAD_EXTERNAL_PATH:{raw_path}")


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
    return (row.get("blocker_uid"), row.get("scope"), row.get("category"), row.get("target_uid"))


def validate_evidence_path(uid, item, allowed_external):
    path = item.get("path", "")
    kind = item.get("source_kind", "")
    if kind == "FROZEN_FUNCTIONAL_CHAIN":
        if path != "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/ASSET-01/FUNCTIONAL_CHAIN_SPEC.yaml":
            die(f"R15_BAD_FUNCTIONAL_CHAIN_EVIDENCE:{uid}:{path}")
    elif kind == "CURRENT_PAGE_AUTHORITY_EXACT_CAPTURE":
        if path != "00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml":
            die(f"R15_BAD_PAGE_AUTHORITY_EVIDENCE:{uid}:{path}")
    elif kind.startswith("CURRENT_EXTERNAL_AUTHORITY:"):
        if path not in allowed_external:
            die(f"R15_NON_CURRENT_EXTERNAL_EVIDENCE:{uid}:{path}")
    else:
        die(f"R15_UNKNOWN_EVIDENCE_KIND:{uid}:{kind}")


def main():
    r12, r15 = load(R12), load(R15)
    if r15.get("artifact_type") != "NON_NORMATIVE_STAGE02_POST_ACTION_VALIDATION_DEPENDENCY_TRACE_R15" or r15.get("normative_authority") is not False:
        die("R15_ARTIFACT_IDENTITY")
    if r15.get("source_contracts", {}).get("r12_classification_accepted_as_authority") is not False:
        die("R15_R12_CLASSIFICATION_AUTHORITY_LEAK")

    old = [r for r in (r12.get("records") or []) if r.get("category") == "POST_ACTION_VALIDATION_NODE_MISSING"]
    rows = r15.get("records") or []
    if len(old) != 18 or len(rows) != 18:
        die(f"R15_DENOMINATOR:{len(old)}:{len(rows)}")
    if {identity(r) for r in old} != {identity(r) for r in rows} or len({identity(r) for r in rows}) != 18:
        die("R15_IDENTITY_COVERAGE_DRIFT")
    if Counter(r.get("scope") for r in rows) != Counter({"ASSET-01": 18}):
        die("R15_SCOPE_DRIFT")

    allowed_external = current_external_paths()
    counts = Counter()
    for row in rows:
        uid, cls = row.get("blocker_uid"), row.get("classification")
        if cls not in ALLOWED:
            die(f"R15_BAD_CLASS:{uid}:{cls}")
        counts[cls] += 1
        for key in (
            "r12_classification_used_as_authority",
            "semantic_validation_inference_used",
            "invented_validation_rule_used",
            "historical_non_current_authority_used",
        ):
            if row.get(key) is not False:
                die(f"R15_SAFETY_FLAG:{uid}:{key}:{row.get(key)}")
        if row.get("blocker_reduction_credit") != 0:
            die(f"R15_FALSE_REDUCTION:{uid}")

        trace = row.get("trace") or {}
        if trace.get("action_uid") != row.get("target_uid"):
            die(f"R15_ACTION_TRACE_MISMATCH:{uid}")
        if not isinstance(trace.get("port_uid"), str) or not trace.get("port_uid"):
            die(f"R15_PORT_MISSING:{uid}")
        if not trace.get("operation_id") and not (trace.get("method") and trace.get("path")):
            die(f"R15_OPERATION_IDENTITY_MISSING:{uid}")

        contracts = row.get("post_action_validation_contract_evidence") or []
        signals = row.get("result_or_state_signal_evidence") or []
        for item in contracts + signals:
            validate_evidence_path(uid, item, allowed_external)
        count = row.get("unique_validation_contract_count")
        if cls == "EXACT_POST_ACTION_VALIDATION_CONTRACT_FOUND":
            if count != 1 or not contracts or row.get("materialization_candidate") is not True:
                die(f"R15_EXACT_CONTRACT_INVALID:{uid}:{count}")
        elif cls == "CONFLICTING_POST_ACTION_VALIDATION_CONTRACTS":
            if not isinstance(count, int) or count < 2 or not contracts or row.get("materialization_candidate") is not False:
                die(f"R15_CONFLICT_INVALID:{uid}:{count}")
        elif cls == "FROZEN_RESULT_OR_STATE_SIGNAL_ONLY":
            if count != 0 or contracts or not signals or row.get("materialization_candidate") is not False:
                die(f"R15_SIGNAL_ONLY_INVALID:{uid}")
        else:
            if count != 0 or contracts or signals or row.get("materialization_candidate") is not False:
                die(f"R15_MISSING_INVALID:{uid}")

    den = r15.get("denominators") or {}
    expected = {
        "exact_post_action_validation_contract_found": counts["EXACT_POST_ACTION_VALIDATION_CONTRACT_FOUND"],
        "conflicting_post_action_validation_contracts": counts["CONFLICTING_POST_ACTION_VALIDATION_CONTRACTS"],
        "frozen_result_or_state_signal_only": counts["FROZEN_RESULT_OR_STATE_SIGNAL_ONLY"],
        "current_frozen_post_action_validation_contract_missing": counts["CURRENT_FROZEN_POST_ACTION_VALIDATION_CONTRACT_MISSING"],
    }
    if den.get("post_action_validation_gaps_traced") != 18 or sum(expected.values()) != 18:
        die("R15_TOTAL_NOT_18")
    if den.get("scope_counts") != {"ASSET-01": 18}:
        die("R15_SCOPE_DENOMINATOR_DRIFT")
    for key, value in expected.items():
        if den.get(key) != value:
            die(f"R15_COUNT_DRIFT:{key}:{den.get(key)}:{value}")
    if den.get("effective_stage02_blocker_reduction_claimed") != 0:
        die("R15_FALSE_GLOBAL_REDUCTION")

    trace_contract = r15.get("trace_contract") or {}
    if trace_contract.get("result_or_state_signal_is_validation_contract") is not False:
        die("R15_SIGNAL_FALSE_PROMOTION")
    if trace_contract.get("precondition_gate_is_post_action_validation") is not False:
        die("R15_PRECONDITION_FALSE_PROMOTION")
    if trace_contract.get("semantic_validation_inference_allowed") is not False or trace_contract.get("invented_validation_rule_allowed") is not False:
        die("R15_INFERENCE_OR_INVENTION_ALLOWED")
    if r15.get("stage02_status") != "BLOCKED" or r15.get("stage03_allowed") is not False or r15.get("website_construction_allowed") is not False or r15.get("deployment_allowed") is not False:
        die("R15_DOWNSTREAM_FALSE_ALLOW")

    print(f"PASS: R15 exact 18 post-action validation identities verified classifications={dict(counts)}")
    print("PASS: result/state signals and precondition gates are not promoted to post-action validation contracts")
    print("PASS: no inferred validation, no historical authority, zero blocker reduction")


if __name__ == "__main__":
    main()
