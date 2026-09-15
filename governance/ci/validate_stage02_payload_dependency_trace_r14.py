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
R14 = ROOT / "governance/test/stage02/STAGE02_PAYLOAD_DEPENDENCY_TRACE_R14.yaml"
EXT_EVIDENCE = STAGE2 / "EXTERNAL_AUTHORITY/STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE.yaml"
ALLOWED = {
    "EXACT_STRUCTURED_PAYLOAD_SCHEMA_FOUND",
    "CONFLICTING_STRUCTURED_PAYLOAD_SCHEMAS",
    "FROZEN_PAYLOAD_RULE_ONLY",
    "CURRENT_FROZEN_PAYLOAD_CONTRACT_MISSING",
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
    die(f"R14_BAD_EXTERNAL_PATH:{raw_path}")


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
        if not path.startswith("00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/"):
            die(f"R14_BAD_FUNCTIONAL_CHAIN_EVIDENCE:{uid}:{path}")
    elif kind == "CURRENT_PAGE_AUTHORITY_EXACT_CAPTURE":
        if not path.startswith("00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/"):
            die(f"R14_BAD_PAGE_AUTHORITY_EVIDENCE:{uid}:{path}")
    elif kind.startswith("CURRENT_EXTERNAL_AUTHORITY:"):
        if path not in allowed_external:
            die(f"R14_NON_CURRENT_EXTERNAL_EVIDENCE:{uid}:{path}")
    else:
        die(f"R14_UNKNOWN_EVIDENCE_KIND:{uid}:{kind}")


def main():
    r12, r14 = load(R12), load(R14)
    if r14.get("artifact_type") != "NON_NORMATIVE_STAGE02_PAYLOAD_DEPENDENCY_TRACE_R14" or r14.get("normative_authority") is not False:
        die("R14_ARTIFACT_IDENTITY")
    if r14.get("source_contracts", {}).get("r12_classification_accepted_as_authority") is not False:
        die("R14_R12_CLASSIFICATION_AUTHORITY_LEAK")
    old = [r for r in (r12.get("records") or []) if r.get("category") == "PAYLOAD_INPUT_CONTRACT_MISSING"]
    rows = r14.get("records") or []
    if len(old) != 34 or len(rows) != 34:
        die(f"R14_DENOMINATOR:{len(old)}:{len(rows)}")
    if {identity(r) for r in old} != {identity(r) for r in rows} or len({identity(r) for r in rows}) != 34:
        die("R14_IDENTITY_COVERAGE_DRIFT")
    if Counter(r.get("scope") for r in rows) != Counter({"ASSET-01": 18, "CORE-01": 16}):
        die("R14_SCOPE_DRIFT")

    allowed_external = current_external_paths()
    counts = Counter()
    for row in rows:
        uid, cls = row.get("blocker_uid"), row.get("classification")
        if cls not in ALLOWED:
            die(f"R14_BAD_CLASS:{uid}:{cls}")
        counts[cls] += 1
        for key in ("r12_classification_used_as_authority", "semantic_field_inference_used", "invented_payload_field_used", "historical_non_current_authority_used"):
            if row.get(key) is not False:
                die(f"R14_SAFETY_FLAG:{uid}:{key}:{row.get(key)}")
        if row.get("blocker_reduction_credit") != 0:
            die(f"R14_FALSE_REDUCTION:{uid}")
        trace = row.get("trace") or {}
        if trace.get("action_uid") != row.get("target_uid"):
            die(f"R14_ACTION_TRACE_MISMATCH:{uid}")
        if not isinstance(trace.get("port_uid"), str) or not trace.get("port_uid"):
            die(f"R14_PORT_MISSING:{uid}")
        if not trace.get("operation_id") and not (trace.get("method") and trace.get("path")):
            die(f"R14_OPERATION_IDENTITY_MISSING:{uid}")

        schemas = row.get("structured_payload_schema_evidence") or []
        rules = row.get("frozen_payload_rule_evidence") or []
        for item in schemas + rules:
            validate_evidence_path(uid, item, allowed_external)
        count = row.get("unique_structured_schema_count")
        if cls == "EXACT_STRUCTURED_PAYLOAD_SCHEMA_FOUND":
            if count != 1 or not schemas or row.get("materialization_candidate") is not True:
                die(f"R14_EXACT_SCHEMA_INVALID:{uid}:{count}")
        elif cls == "CONFLICTING_STRUCTURED_PAYLOAD_SCHEMAS":
            if not isinstance(count, int) or count < 2 or not schemas or row.get("materialization_candidate") is not False:
                die(f"R14_CONFLICT_INVALID:{uid}:{count}")
        elif cls == "FROZEN_PAYLOAD_RULE_ONLY":
            if count != 0 or schemas or not rules or row.get("materialization_candidate") is not False:
                die(f"R14_RULE_ONLY_INVALID:{uid}")
        else:
            if count != 0 or schemas or rules or row.get("materialization_candidate") is not False:
                die(f"R14_MISSING_INVALID:{uid}")

    den = r14.get("denominators") or {}
    expected = {
        "exact_structured_payload_schema_found": counts["EXACT_STRUCTURED_PAYLOAD_SCHEMA_FOUND"],
        "conflicting_structured_payload_schemas": counts["CONFLICTING_STRUCTURED_PAYLOAD_SCHEMAS"],
        "frozen_payload_rule_only": counts["FROZEN_PAYLOAD_RULE_ONLY"],
        "current_frozen_payload_contract_missing": counts["CURRENT_FROZEN_PAYLOAD_CONTRACT_MISSING"],
    }
    if den.get("payload_input_gaps_traced") != 34 or sum(expected.values()) != 34:
        die("R14_TOTAL_NOT_34")
    for key, value in expected.items():
        if den.get(key) != value:
            die(f"R14_COUNT_DRIFT:{key}:{den.get(key)}:{value}")
    if den.get("effective_stage02_blocker_reduction_claimed") != 0:
        die("R14_FALSE_GLOBAL_REDUCTION")
    if r14.get("stage02_status") != "BLOCKED" or r14.get("stage03_allowed") is not False or r14.get("website_construction_allowed") is not False or r14.get("deployment_allowed") is not False:
        die("R14_DOWNSTREAM_FALSE_ALLOW")
    if r14.get("trace_contract", {}).get("payload_rule_is_structured_schema") is not False:
        die("R14_PAYLOAD_RULE_FALSE_PROMOTION")
    print(f"PASS: R14 exact 34 payload identities verified classifications={dict(counts)}")
    print("PASS: frozen payload rules are evidence but never promoted to structured request schema")
    print("PASS: no inferred fields, no historical authority, zero blocker reduction")


if __name__ == "__main__":
    main()
