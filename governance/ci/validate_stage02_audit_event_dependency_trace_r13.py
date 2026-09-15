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
R13 = ROOT / "governance/test/stage02/STAGE02_AUDIT_EVENT_DEPENDENCY_TRACE_R13.yaml"
EXT_EVIDENCE = STAGE2 / "EXTERNAL_AUTHORITY/STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE.yaml"
ALLOWED = {"EXACT_EVENT_DEPENDENCY_FOUND", "CONFLICTING_EXACT_EVENT_DEPENDENCY", "CURRENT_FROZEN_EVENT_CONTRACT_MISSING"}


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
    die(f"R13_BAD_EXTERNAL_PATH:{raw_path}")


def current_external_paths():
    evidence = load(EXT_EVIDENCE)
    allowed = set()
    for _, entry in (evidence.get("materialized_authorities") or {}).items():
        if not isinstance(entry, dict) or entry.get("manifest_current") is not True:
            continue
        if entry.get("authority_identity_status") not in {"EXACT_MATCH", "EXACT_CHAIN_LOCATED"}:
            continue
        if entry.get("materialized_path"):
            allowed.add(normalize(entry["materialized_path"]))
        for item in entry.get("authority_chain") or []:
            if isinstance(item, dict) and item.get("materialized_path"):
                allowed.add(normalize(item["materialized_path"]))
    return allowed


def identity(row):
    return (row.get("blocker_uid"), row.get("scope"), row.get("category"), row.get("target_uid"))


def main() -> None:
    r12, r13 = load(R12), load(R13)
    if r13.get("artifact_type") != "NON_NORMATIVE_STAGE02_AUDIT_EVENT_DEPENDENCY_TRACE_R13" or r13.get("normative_authority") is not False:
        die("R13_ARTIFACT_IDENTITY")
    if r13.get("source_contracts", {}).get("r12_classification_accepted_as_authority") is not False:
        die("R13_R12_CLASSIFICATION_AUTHORITY_LEAK")
    old = [r for r in (r12.get("records") or []) if r.get("category") == "AUDIT_EVENT_NODE_MISSING"]
    rows = r13.get("records") or []
    if len(old) != 13 or len(rows) != 13 or {identity(r) for r in old} != {identity(r) for r in rows} or len({identity(r) for r in rows}) != 13:
        die("R13_IDENTITY_OR_DENOMINATOR_DRIFT")

    allowed_external = current_external_paths()
    counts, scopes = Counter(), Counter()
    for row in rows:
        uid, cls = row.get("blocker_uid"), row.get("classification")
        if cls not in ALLOWED:
            die(f"R13_BAD_CLASS:{uid}:{cls}")
        counts[cls] += 1
        scopes[row.get("scope")] += 1
        for key in ("r12_classification_used_as_authority", "semantic_event_name_inference_used", "event_uid_invention_used", "historical_non_current_authority_used"):
            if row.get(key) is not False:
                die(f"R13_SAFETY_FLAG:{uid}:{key}:{row.get(key)}")
        if row.get("blocker_reduction_credit") != 0:
            die(f"R13_FALSE_REDUCTION:{uid}")

        trace = row.get("trace") or {}
        if trace.get("action_uid") != row.get("target_uid"):
            die(f"R13_ACTION_TRACE_MISMATCH:{uid}")
        if not isinstance(trace.get("port_uid"), str) or not trace.get("port_uid"):
            die(f"R13_PORT_MISSING:{uid}")
        has_registered_operation = isinstance(trace.get("registered_operation"), str) and bool(trace.get("registered_operation"))
        has_operation_ref = isinstance(trace.get("operation_ref"), str) and bool(trace.get("operation_ref"))
        has_method_path = isinstance(trace.get("method"), str) and bool(trace.get("method")) and isinstance(trace.get("path"), str) and bool(trace.get("path"))
        if not (has_registered_operation or has_operation_ref or has_method_path):
            die(f"R13_EXACT_OPERATION_IDENTITY_MISSING:{uid}")
        if not isinstance(trace.get("state_event"), str) or not trace.get("state_event"):
            die(f"R13_STATE_EVENT_MISSING:{uid}")

        events = row.get("unique_exact_event_uids") or []
        bindings = row.get("exact_event_binding_evidence") or []
        for item in bindings:
            path, source_kind = item.get("path", ""), item.get("source_kind", "")
            if source_kind.startswith("CURRENT_EXTERNAL_AUTHORITY:"):
                if path not in allowed_external:
                    die(f"R13_NON_CURRENT_EXTERNAL_EVENT_EVIDENCE:{uid}:{path}")
            elif source_kind == "CURRENT_PAGE_AUTHORITY_EXACT_CAPTURE":
                if not path.startswith("00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/"):
                    die(f"R13_BAD_PAGE_AUTHORITY_EVIDENCE:{uid}:{path}")
            else:
                die(f"R13_UNKNOWN_EVENT_EVIDENCE_KIND:{uid}:{source_kind}")

        if cls == "EXACT_EVENT_DEPENDENCY_FOUND":
            if len(events) != 1 or not bindings or row.get("materialization_candidate") is not True:
                die(f"R13_EXACT_EVENT_NOT_UNIQUE_OR_UNPROVEN:{uid}:{events}")
        elif cls == "CONFLICTING_EXACT_EVENT_DEPENDENCY":
            if len(events) < 2 or not bindings or row.get("materialization_candidate") is not False:
                die(f"R13_CONFLICT_INVALID:{uid}:{events}")
        else:
            if events or bindings or row.get("materialization_candidate") is not False:
                die(f"R13_MISSING_CLASS_HAS_BINDING_OR_CANDIDATE:{uid}:{events}")

    if scopes != Counter({"ASSET-01": 9, "CORE-01": 4}):
        die(f"R13_SCOPE_DRIFT:{dict(scopes)}")
    den = r13.get("denominators") or {}
    expected = {
        "exact_event_dependency_found": counts["EXACT_EVENT_DEPENDENCY_FOUND"],
        "conflicting_exact_event_dependency": counts["CONFLICTING_EXACT_EVENT_DEPENDENCY"],
        "current_frozen_event_contract_missing": counts["CURRENT_FROZEN_EVENT_CONTRACT_MISSING"],
    }
    if den.get("audit_event_gaps_traced") != 13 or sum(expected.values()) != 13:
        die("R13_TOTAL_NOT_13")
    for key, value in expected.items():
        if den.get(key) != value:
            die(f"R13_COUNT_DRIFT:{key}:{den.get(key)}:{value}")
    if den.get("effective_stage02_blocker_reduction_claimed") != 0:
        die("R13_FALSE_GLOBAL_REDUCTION")
    if r13.get("stage02_status") != "BLOCKED" or r13.get("stage03_allowed") is not False or r13.get("website_construction_allowed") is not False or r13.get("deployment_allowed") is not False:
        die("R13_DOWNSTREAM_FALSE_ALLOW")
    print(f"PASS: R13 exact 13 audit-event identities verified classifications={dict(counts)}")
    print("PASS: exact-event candidates require physical Current-admissible event UID evidence")
    print("PASS: registered_operation/method_effective_path accepted as exact frozen identity; no semantic naming or false blocker reduction")


if __name__ == "__main__":
    main()
