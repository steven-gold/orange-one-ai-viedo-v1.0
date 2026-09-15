#!/usr/bin/env python3
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R12 = ROOT / "governance/test/stage02/STAGE02_AUTHORITY_DEPENDENCY_RECLASSIFICATION_R12.yaml"
R18 = ROOT / "governance/test/stage02/STAGE02_ACTION_CONTROL_TRIGGER_DEPENDENCY_TRACE_R18.yaml"
TARGET = "ASSET-01-ACT-FINDING-CREATE"
ALLOWED = {
    "EXACT_CONTROL_AND_TRIGGER_FOUND",
    "EXACT_CONTROL_BINDING_FOUND",
    "EXACT_TRIGGER_BINDING_FOUND",
    "EXACT_PORT_EXPOSURE_ONLY_CONTROL_TRIGGER_MISSING",
    "CURRENT_FROZEN_CONTROL_TRIGGER_CONTRACT_MISSING",
}


def die(msg):
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def main():
    r12, r18 = load(R12), load(R18)
    if r18.get("artifact_type") != "NON_NORMATIVE_STAGE02_ACTION_CONTROL_TRIGGER_DEPENDENCY_TRACE_R18" or r18.get("normative_authority") is not False:
        die("R18_ARTIFACT_IDENTITY")
    if r18.get("source_contracts", {}).get("r12_classification_accepted_as_authority") is not False:
        die("R18_R12_CLASSIFICATION_AUTHORITY_LEAK")
    old = [r for r in (r12.get("records") or []) if r.get("category") == "ACTION_WITHOUT_CONTROL_OR_TRIGGER"]
    rows = r18.get("records") or []
    if len(old) != 1 or len(rows) != 1:
        die(f"R18_DENOMINATOR:{len(old)}:{len(rows)}")
    row, src = rows[0], old[0]
    for key in ("blocker_uid", "scope", "category", "target_uid", "missing_field_or_relation"):
        if row.get(key) != src.get(key):
            die(f"R18_IDENTITY_DRIFT:{key}:{row.get(key)}:{src.get(key)}")
    if row.get("target_uid") != TARGET or row.get("scope") != "ASSET-01":
        die("R18_TARGET_DRIFT")
    if row.get("classification") not in ALLOWED:
        die(f"R18_BAD_CLASS:{row.get('classification')}")
    for key in (
        "r12_classification_used_as_authority",
        "port_exposure_promoted_to_control_or_trigger",
        "semantic_trigger_inference_used",
        "invented_control_or_trigger_used",
        "historical_non_current_authority_used",
    ):
        if row.get(key) is not False:
            die(f"R18_SAFETY_FLAG:{key}:{row.get(key)}")
    if row.get("blocker_reduction_credit") != 0:
        die("R18_FALSE_REDUCTION")

    controls = row.get("exact_control_binding_evidence") or []
    triggers = row.get("exact_trigger_binding_evidence") or []
    exposures = row.get("nonqualifying_lineage_evidence") or []
    cls = row.get("classification")
    if cls == "EXACT_CONTROL_AND_TRIGGER_FOUND":
        valid = bool(controls and triggers and row.get("materialization_candidate") is True)
    elif cls == "EXACT_CONTROL_BINDING_FOUND":
        valid = bool(controls and not triggers and row.get("materialization_candidate") is True)
    elif cls == "EXACT_TRIGGER_BINDING_FOUND":
        valid = bool(triggers and not controls and row.get("materialization_candidate") is True)
    elif cls == "EXACT_PORT_EXPOSURE_ONLY_CONTROL_TRIGGER_MISSING":
        valid = bool(exposures and not controls and not triggers and row.get("materialization_candidate") is False)
    else:
        valid = bool(not exposures and not controls and not triggers and row.get("materialization_candidate") is False)
    if not valid:
        die(f"R18_CLASS_EVIDENCE_MISMATCH:{cls}")

    den = r18.get("denominators") or {}
    if den.get("action_without_control_or_trigger_gaps_traced") != 1 or den.get("scope_counts") != {"ASSET-01": 1}:
        die("R18_DENOMINATOR_DRIFT")
    if den.get("exact_control_binding_count") != len(controls) or den.get("exact_trigger_binding_count") != len(triggers) or den.get("nonqualifying_port_exposure_count") != len(exposures):
        die("R18_EVIDENCE_COUNT_DRIFT")
    if den.get("materialization_candidates") != (1 if row.get("materialization_candidate") else 0):
        die("R18_CANDIDATE_COUNT_DRIFT")
    if den.get("effective_stage02_blocker_reduction_claimed") != 0:
        die("R18_FALSE_GLOBAL_REDUCTION")

    contract = r18.get("trace_contract") or {}
    if contract.get("port_exposure_is_control_or_trigger") is not False or contract.get("semantic_trigger_inference_allowed") is not False or contract.get("invented_control_or_trigger_allowed") is not False or contract.get("classification_alone_may_reduce_blocker") is not False:
        die("R18_UNSAFE_TRACE_CONTRACT")
    if r18.get("stage02_status") != "BLOCKED" or r18.get("stage03_allowed") is not False or r18.get("website_construction_allowed") is not False or r18.get("deployment_allowed") is not False:
        die("R18_DOWNSTREAM_FALSE_ALLOW")

    print(f"PASS: R18 exact single action/control/trigger gap verified classification={cls}")
    print("PASS: port exposure remains non-qualifying lineage; only exact control or registered trigger can close relation")
    print("PASS: zero blocker reduction until separate bounded materialization and fresh reexecution")


if __name__ == "__main__":
    main()
