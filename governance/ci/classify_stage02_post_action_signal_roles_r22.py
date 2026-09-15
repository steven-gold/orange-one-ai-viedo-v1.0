#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R20 = ROOT / "governance/test/stage02/STAGE02_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY_R20.yaml"
OUT = ROOT / "governance/test/stage02/STAGE02_POST_ACTION_SIGNAL_ROLE_RECLASSIFICATION_R22.yaml"
EXPECTED_TARGETS = {
    "ASSET-01-ACT-FLOW-START",
    "ASSET-01-ACT-CANDIDATE-CONFIRM",
    "ASSET-01-ACT-CORRECTION-EXECUTE",
}


def die(msg: str) -> None:
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> dict:
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def role(ev: dict) -> str:
    node = str(ev.get("node") or "")
    if ".runtime_binding.result" in node or ".runtime_binding.result_state" in node or ".runtime_binding.success_state" in node:
        return "ACTION_RESULT_SIGNAL"
    if node.startswith("ports:") and any(node.endswith("." + suffix) for suffix in ("state_event", "result", "result_state", "success_state")):
        return "BOUND_PORT_RESULT_OR_STATE_SIGNAL"
    if node.startswith("transitions:") and node.endswith(".to_stage"):
        return "FLOW_TRANSITION_DESTINATION_NON_VALIDATION_ROLE"
    return "OTHER_UNCLASSIFIED_SIGNAL_ROLE"


def canonical(groups_input: list[dict]) -> dict[str, list[dict]]:
    groups = {}
    for ev in groups_input:
        key = yaml.safe_dump(ev.get("value"), allow_unicode=True, sort_keys=True)
        groups.setdefault(key, []).append(ev)
    return groups


r20 = load(R20)
if r20.get("schema_version") != 2:
    die("R20_SCHEMA_VERSION_2_REQUIRED")
records = [
    r for r in (r20.get("records") or [])
    if r.get("category") == "POST_ACTION_VALIDATION_NODE_MISSING"
    and r.get("disposition") == "AUTHORITY_GAP_MULTIPLE_REASONABLE_CLOSURES"
]
if len(records) != 3:
    die(f"R20_POST_ACTION_AUTHORITY_GAP_DENOMINATOR:{len(records)}")
if {str(r.get("target_uid")) for r in records} != EXPECTED_TARGETS:
    die(f"R20_POST_ACTION_AUTHORITY_GAP_TARGET_DRIFT:{sorted(str(r.get('target_uid')) for r in records)}")

out_records = []
for rec in records:
    evidence = rec.get("candidate_evidence") or []
    classified = []
    admissible = []
    excluded = []
    for ev in evidence:
        item = dict(ev)
        item["signal_role"] = role(ev)
        item["scanner_validation_role_admissible"] = item["signal_role"] in {"ACTION_RESULT_SIGNAL", "BOUND_PORT_RESULT_OR_STATE_SIGNAL"}
        classified.append(item)
        if item["scanner_validation_role_admissible"]:
            admissible.append(item)
        else:
            excluded.append(item)
    if any(x["signal_role"] == "OTHER_UNCLASSIFIED_SIGNAL_ROLE" for x in classified):
        die(f"UNCLASSIFIED_R20_SIGNAL_ROLE:{rec.get('blocker_uid')}")
    if not any(x["signal_role"] == "FLOW_TRANSITION_DESTINATION_NON_VALIDATION_ROLE" for x in excluded):
        die(f"EXPECTED_TRANSITION_ROLE_NOT_FOUND:{rec.get('blocker_uid')}")
    groups = canonical(admissible)
    if len(groups) == 1:
        only = next(iter(groups.values()))
        disposition = "AUTO_REMEDIABLE_AFTER_SIGNAL_ROLE_CORRECTION"
        candidate_value = only[0].get("value")
        authorized = True
        authority_gap = False
    elif len(groups) > 1:
        disposition = "AUTHORITY_GAP_MULTIPLE_ACTION_RESULT_SIGNALS_AFTER_ROLE_CORRECTION"
        candidate_value = None
        authorized = False
        authority_gap = True
    else:
        disposition = "UNRESOLVED_NO_ADMISSIBLE_VALIDATION_SIGNAL_AFTER_ROLE_CORRECTION"
        candidate_value = None
        authorized = False
        authority_gap = False
    out_records.append({
        "problem_uid": rec.get("problem_uid"),
        "blocker_uid": rec.get("blocker_uid"),
        "page_uid": rec.get("page_uid"),
        "category": rec.get("category"),
        "target_uid": rec.get("target_uid"),
        "missing_field_or_relation": rec.get("missing_field_or_relation"),
        "prior_r20_disposition": rec.get("disposition"),
        "disposition": disposition,
        "authorized_for_auto_completion": authorized,
        "authority_gap_proven": authority_gap,
        "candidate_value": candidate_value,
        "admissible_candidate_value_count": len(groups),
        "admissible_validation_evidence": admissible,
        "excluded_non_validation_role_evidence": excluded,
        "all_classified_evidence": classified,
        "closure_type": "POST_ACTION_VALIDATION_FROM_ROLE_CORRECT_UNIQUE_FROZEN_RESULT_SIGNAL" if authorized else None,
        "semantic_similarity_used": False,
        "ai_invented_business_value": False,
        "outside_frozen_registered_dependency_closure": False,
    })

counts = Counter(r["disposition"] for r in out_records)
if counts.get("AUTO_REMEDIABLE_AFTER_SIGNAL_ROLE_CORRECTION", 0) != 2:
    die(f"R22_AUTO_EXPECTED_2:{dict(counts)}")
if counts.get("AUTHORITY_GAP_MULTIPLE_ACTION_RESULT_SIGNALS_AFTER_ROLE_CORRECTION", 0) != 1:
    die(f"R22_AUTHORITY_GAP_EXPECTED_1:{dict(counts)}")
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
out = {
    "schema_version": 1,
    "artifact_type": "NON_NORMATIVE_STAGE02_POST_ACTION_SIGNAL_ROLE_RECLASSIFICATION_R22",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "source_head_sha": head,
    "source_r20_ref": str(R20.relative_to(ROOT)),
    "correction_basis": {
        "fresh_scanner_rule": "POST_ACTION_VALIDATION accepts action success/validation fields, runtime validation/evaluation fields, or bound-port validation fields; stage transition destination is not a validation node.",
        "transition_destination_role": "FLOW_PROGRESSION_NOT_POST_ACTION_VALIDATION",
        "action_result_role": "ACTION_RESULT_SIGNAL",
        "bound_port_state_event_role": "BOUND_PORT_RESULT_OR_STATE_SIGNAL",
        "no_source_precedence_invented": True,
        "multiple_admissible_result_signals_remain_authority_gap": True,
    },
    "denominators": {
        "input_r20_post_action_authority_gap_total": 3,
        "auto_remediable_after_role_correction": 2,
        "authority_gap_after_role_correction": 1,
        "blocker_reduction_claimed_before_materialization": 0,
    },
    "records": out_records,
    "current_specification_mutated": False,
    "immutable_stage1_source_mutated": False,
    "stage02_status": "BLOCKED",
    "stage03_allowed": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
}
OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=180), encoding="utf-8")
print("PASS: R22 reclassified exactly 3 R20 post-action signal-role conflicts")
print("PASS: excluded transition.to_stage from post-action validation role without deleting transition evidence")
print("PASS: auto-remediable after role correction=2; true multiple result-signal authority gap=1")
print("PASS: no blocker reduction claimed before materialization/reexecution")
