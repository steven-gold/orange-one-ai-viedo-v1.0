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
R16 = ROOT / "governance/test/stage02/STAGE02_FAILURE_ERROR_RECOVERY_DEPENDENCY_TRACE_R16.yaml"
EXT_EVIDENCE = STAGE2 / "EXTERNAL_AUTHORITY/STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE.yaml"
ALLOWED = {
    "EXACT_FAILURE_ERROR_RECOVERY_BINDING_FOUND",
    "CONFLICTING_FAILURE_ERROR_RECOVERY_BINDINGS",
    "FROZEN_RESULT_OR_STATE_SIGNAL_ONLY",
    "CURRENT_FROZEN_FAILURE_ERROR_RECOVERY_BINDING_MISSING",
}
IDENTITY_SHAPES = {"ACTION_ONLY_NO_RUNTIME_API", "ACTION_TO_PORT_OPERATION", "ACTION_TO_SHARED_OPERATION"}


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
    die(f"R16_BAD_EXTERNAL_PATH:{raw_path}")


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
            die(f"R16_BAD_FUNCTIONAL_CHAIN_EVIDENCE:{uid}:{path}")
    elif kind == "CURRENT_PAGE_AUTHORITY_EXACT_CAPTURE":
        if path != "00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml":
            die(f"R16_BAD_PAGE_AUTHORITY_EVIDENCE:{uid}:{path}")
    elif kind.startswith("CURRENT_EXTERNAL_AUTHORITY:"):
        if path not in allowed_external:
            die(f"R16_NON_CURRENT_EXTERNAL_EVIDENCE:{uid}:{path}")
    else:
        die(f"R16_UNKNOWN_EVIDENCE_KIND:{uid}:{kind}")


def main():
    r12, r16 = load(R12), load(R16)
    if r16.get("artifact_type") != "NON_NORMATIVE_STAGE02_FAILURE_ERROR_RECOVERY_DEPENDENCY_TRACE_R16" or r16.get("normative_authority") is not False:
        die("R16_ARTIFACT_IDENTITY")
    if r16.get("source_contracts", {}).get("r12_classification_accepted_as_authority") is not False:
        die("R16_R12_CLASSIFICATION_AUTHORITY_LEAK")

    old = [r for r in (r12.get("records") or []) if r.get("category") == "FAILURE_STATE_ERROR_BINDING_MISSING"]
    rows = r16.get("records") or []
    if len(old) != 44 or len(rows) != 44:
        die(f"R16_DENOMINATOR:{len(old)}:{len(rows)}")
    if {identity(r) for r in old} != {identity(r) for r in rows} or len({identity(r) for r in rows}) != 44:
        die("R16_IDENTITY_COVERAGE_DRIFT")
    if Counter(r.get("scope") for r in rows) != Counter({"ASSET-01": 44}):
        die("R16_SCOPE_DRIFT")

    allowed_external = current_external_paths()
    counts = Counter()
    identity_counts = Counter()
    for row in rows:
        uid, cls = row.get("blocker_uid"), row.get("classification")
        if cls not in ALLOWED:
            die(f"R16_BAD_CLASS:{uid}:{cls}")
        counts[cls] += 1
        for key in (
            "r12_classification_used_as_authority",
            "semantic_error_or_recovery_inference_used",
            "invented_error_or_recovery_binding_used",
            "historical_non_current_authority_used",
        ):
            if row.get(key) is not False:
                die(f"R16_SAFETY_FLAG:{uid}:{key}:{row.get(key)}")
        if row.get("blocker_reduction_credit") != 0:
            die(f"R16_FALSE_REDUCTION:{uid}")

        trace = row.get("trace") or {}
        if trace.get("action_uid") != row.get("target_uid"):
            die(f"R16_ACTION_TRACE_MISMATCH:{uid}")
        shape = trace.get("identity_kind")
        if shape not in IDENTITY_SHAPES:
            die(f"R16_BAD_IDENTITY_SHAPE:{uid}:{shape}")
        identity_counts[shape] += 1
        if shape == "ACTION_TO_PORT_OPERATION" and not trace.get("port_uid"):
            die(f"R16_PORT_SHAPE_WITHOUT_PORT:{uid}")
        if shape == "ACTION_TO_SHARED_OPERATION" and not trace.get("shared_operation_id"):
            die(f"R16_SHARED_SHAPE_WITHOUT_OPERATION:{uid}")

        bindings = row.get("failure_error_recovery_binding_evidence") or []
        signals = row.get("result_or_state_signal_evidence") or []
        for item in bindings + signals:
            validate_evidence_path(uid, item, allowed_external)
        key_counts = row.get("binding_key_value_counts") or {}
        conflicts = row.get("conflicting_binding_keys") or []
        if any(not isinstance(v, int) or v < 1 for v in key_counts.values()):
            die(f"R16_BAD_BINDING_KEY_COUNTS:{uid}")
        derived_conflicts = sorted(k for k, v in key_counts.items() if v > 1)
        if conflicts != derived_conflicts:
            die(f"R16_CONFLICT_KEY_DRIFT:{uid}:{conflicts}:{derived_conflicts}")

        if cls == "EXACT_FAILURE_ERROR_RECOVERY_BINDING_FOUND":
            if not bindings or conflicts or row.get("materialization_candidate") is not True:
                die(f"R16_EXACT_BINDING_INVALID:{uid}")
        elif cls == "CONFLICTING_FAILURE_ERROR_RECOVERY_BINDINGS":
            if not bindings or not conflicts or row.get("materialization_candidate") is not False:
                die(f"R16_CONFLICT_INVALID:{uid}")
        elif cls == "FROZEN_RESULT_OR_STATE_SIGNAL_ONLY":
            if bindings or not signals or conflicts or row.get("materialization_candidate") is not False:
                die(f"R16_SIGNAL_ONLY_INVALID:{uid}")
        else:
            if bindings or signals or conflicts or row.get("materialization_candidate") is not False:
                die(f"R16_MISSING_INVALID:{uid}")

    den = r16.get("denominators") or {}
    expected = {
        "exact_failure_error_recovery_binding_found": counts["EXACT_FAILURE_ERROR_RECOVERY_BINDING_FOUND"],
        "conflicting_failure_error_recovery_bindings": counts["CONFLICTING_FAILURE_ERROR_RECOVERY_BINDINGS"],
        "frozen_result_or_state_signal_only": counts["FROZEN_RESULT_OR_STATE_SIGNAL_ONLY"],
        "current_frozen_failure_error_recovery_binding_missing": counts["CURRENT_FROZEN_FAILURE_ERROR_RECOVERY_BINDING_MISSING"],
    }
    if den.get("failure_error_recovery_gaps_traced") != 44 or sum(expected.values()) != 44:
        die("R16_TOTAL_NOT_44")
    if den.get("scope_counts") != {"ASSET-01": 44}:
        die("R16_SCOPE_DENOMINATOR_DRIFT")
    if den.get("identity_shape_counts") != dict(identity_counts):
        die(f"R16_IDENTITY_COUNT_DRIFT:{den.get('identity_shape_counts')}:{dict(identity_counts)}")
    for key, value in expected.items():
        if den.get(key) != value:
            die(f"R16_COUNT_DRIFT:{key}:{den.get(key)}:{value}")
    if den.get("effective_stage02_blocker_reduction_claimed") != 0:
        die("R16_FALSE_GLOBAL_REDUCTION")

    contract = r16.get("trace_contract") or {}
    if contract.get("result_or_state_signal_is_error_or_recovery_binding") is not False:
        die("R16_SIGNAL_FALSE_PROMOTION")
    if contract.get("semantic_error_or_recovery_inference_allowed") is not False or contract.get("invented_error_or_recovery_binding_allowed") is not False:
        die("R16_INFERENCE_OR_INVENTION_ALLOWED")
    if r16.get("stage02_status") != "BLOCKED" or r16.get("stage03_allowed") is not False or r16.get("website_construction_allowed") is not False or r16.get("deployment_allowed") is not False:
        die("R16_DOWNSTREAM_FALSE_ALLOW")

    print(f"PASS: R16 exact 44 failure/error/recovery identities verified classifications={dict(counts)} identity_shapes={dict(identity_counts)}")
    print("PASS: action-only, port/operation, and shared-operation identities stay exact and current-admissible")
    print("PASS: no inferred recovery, no historical authority, zero blocker reduction")


if __name__ == "__main__":
    main()
