#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "governance/test/stage02/STAGE02_CURRENT_AUTHORITY_PAYLOAD_CLOSURE_R23.yaml"
SHARED = ROOT / "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/EXTERNAL_AUTHORITY/GAP-006/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml"
MANIFEST = ROOT / "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/EXTERNAL_AUTHORITY/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml"
EXPECTED_SHARED_SOURCE = "authority/runtime/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml"
EXPECTED_SHARED_MATERIALIZED = "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/EXTERNAL_AUTHORITY/GAP-006/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml"


def die(msg):
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def flatten(node):
    out = []
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, list):
        for x in node:
            out.extend(flatten(x))
    elif isinstance(node, dict):
        for x in node.values():
            out.extend(flatten(x))
    return out


doc = load(OUT)
if doc.get("artifact_type") != "NON_NORMATIVE_STAGE02_CURRENT_AUTHORITY_PAYLOAD_CLOSURE_R23" or doc.get("stage_uid") != "STAGE-02" or doc.get("normative_authority") is not False:
    die("R23_ARTIFACT_IDENTITY_DRIFT")
if doc.get("current_specification_mutated") is not False or doc.get("immutable_stage1_source_mutated") is not False:
    die("R23_MUTATION_FLAG_DRIFT")
policy = doc.get("source_policy") or {}
required_policy = {
    "manifest_listed_current_authority_only": True,
    "operation_registry_may_support_identity_but_not_create_payload_contract": True,
    "required_payload_is_copied_exactly_from_current_runtime_authority": True,
    "page_action_operation_method_path_identity_must_match": True,
    "zero_exact_intersection_is_valid_audited_outcome": True,
    "semantic_field_inference_forbidden": True,
    "historical_non_current_authority_forbidden": True,
    "ai_invented_payload_fields_forbidden": True,
    "classification_itself_reduces_blocker": False,
}
for key, value in required_policy.items():
    if policy.get(key) is not value:
        die(f"R23_POLICY_DRIFT:{key}:{policy.get(key)}")

den = doc.get("denominators") or {}
if den.get("parent_effective_gap_total") != 129 or den.get("parent_payload_gap_total") != 34 or den.get("payload_gaps_evaluated") != 34:
    die(f"R23_PARENT_DENOMINATOR_DRIFT:{den}")
auto_total = den.get("auto_remediable_current_authority_payload_total")
if not isinstance(auto_total, int) or auto_total < 0 or auto_total > 4:
    die(f"R23_AUTO_DENOMINATOR_INVALID:{auto_total}")
if den.get("authority_gap_multiple_contract_total") != 0:
    die("R23_MULTIPLE_CURRENT_PAYLOAD_CONTRACTS_NOT_ZERO")
if den.get("unresolved_no_exact_current_payload_total") != 34 - auto_total:
    die("R23_UNRESOLVED_DENOMINATOR_ARITHMETIC")
if den.get("blocker_reduction_claimed_before_materialization") != 0:
    die("R23_PREMATURE_BLOCKER_REDUCTION")

manifest = load(MANIFEST)
if EXPECTED_SHARED_SOURCE not in flatten(manifest.get("current_authority_set") or {}):
    die("R23_SHARED_RUNTIME_NOT_MANIFEST_CURRENT")
if (manifest.get("load_policy") or {}).get("only_listed_files_are_current_authority") is not True:
    die("R23_MANIFEST_LOAD_POLICY_DRIFT")
shared = load(SHARED)
if shared.get("authority_id") != "ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY" or shared.get("status") != "CURRENT_CONTRACT":
    die("R23_SHARED_RUNTIME_IDENTITY_DRIFT")
operations = shared.get("operations") or {}

records = doc.get("records") or []
if len(records) != 34:
    die(f"R23_RECORD_DENOMINATOR:{len(records)}")
seen = set()
auto = []
for row in records:
    sig = (row.get("page_uid"), row.get("category"), row.get("target_uid"), row.get("gap_detail"))
    if sig in seen:
        die(f"R23_DUPLICATE_RECORD:{sig}")
    seen.add(sig)
    if row.get("category") != "PAYLOAD_INPUT_CONTRACT_MISSING":
        die(f"R23_CATEGORY_DRIFT:{sig}")
    if row.get("semantic_inference_used") is not False or row.get("ai_invented_business_value") is not False or row.get("historical_non_current_authority_used") is not False:
        die(f"R23_SAFETY_FLAG_DRIFT:{sig}")
    if row.get("operation_registry_used_as_payload_authority") is not False or row.get("outside_frozen_registered_dependency_closure") is not False:
        die(f"R23_AUTHORITY_BOUNDARY_DRIFT:{sig}")
    if row.get("authorized_for_auto_completion") is True:
        auto.append(row)
        evidence = row.get("candidate_evidence") or []
        if len(evidence) != 1:
            die(f"R23_AUTO_NOT_EXACTLY_ONE_EVIDENCE:{sig}:{len(evidence)}")
        ev = evidence[0]
        if ev.get("source_kind") != "CURRENT_MANIFEST_LISTED_RUNTIME_AUTHORITY" or ev.get("source_path") != EXPECTED_SHARED_MATERIALIZED:
            die(f"R23_AUTO_SOURCE_DRIFT:{sig}")
        if ev.get("page_uid") != row.get("page_uid") or ev.get("action_uid") != row.get("target_uid"):
            die(f"R23_AUTO_BINDING_DRIFT:{sig}")
        op_id = ev.get("operation_id")
        op = operations.get(op_id)
        if not isinstance(op, dict):
            die(f"R23_AUTO_OPERATION_MISSING:{op_id}")
        binding = ((op.get("page_bindings") or {}).get(row.get("page_uid")) or {})
        if binding.get("action_uid") != row.get("target_uid"):
            die(f"R23_AUTO_AUTHORITY_ACTION_MISMATCH:{sig}")
        required_payload = op.get("required_payload")
        if not isinstance(required_payload, list) or not required_payload or required_payload != ev.get("required_payload"):
            die(f"R23_AUTO_REQUIRED_PAYLOAD_DRIFT:{sig}")
        value = row.get("candidate_value") or {}
        if value.get("operation_id") != op_id or value.get("method") != str(op.get("method")).upper() or value.get("route") != op.get("route") or value.get("required_fields") != required_payload:
            die(f"R23_AUTO_CANDIDATE_VALUE_DRIFT:{sig}")
        required_proof = {"CURRENT_MANIFEST_LISTED", "GAP006_EXACT_MATERIALIZATION", "PAGE_BINDING_ACTION_UID_EXACT", "R14_OPERATION_ID_EXACT"}
        if not required_proof.issubset(set(ev.get("identity_proof") or [])):
            die(f"R23_AUTO_IDENTITY_PROOF_INCOMPLETE:{sig}")
        if row.get("authority_gap_proven") is not False or row.get("disposition") != "AUTO_REMEDIABLE_CURRENT_AUTHORITY_REQUIRED_PAYLOAD":
            die(f"R23_AUTO_DISPOSITION_DRIFT:{sig}")
    else:
        if row.get("candidate_value") is not None:
            die(f"R23_NONAUTO_HAS_CANDIDATE_VALUE:{sig}")
        if row.get("disposition") not in {"UNRESOLVED_NO_EXACT_CURRENT_AUTHORITY_REQUIRED_PAYLOAD", "AUTHORITY_GAP_MULTIPLE_CURRENT_REQUIRED_PAYLOAD_CONTRACTS"}:
            die(f"R23_NONAUTO_DISPOSITION_UNKNOWN:{sig}")

if len(auto) != auto_total:
    die(f"R23_AUTO_COUNT_DRIFT:{len(auto)}:{auto_total}")
if sorted(doc.get("auto_targets") or []) != sorted(x.get("target_uid") for x in auto):
    die("R23_AUTO_TARGET_LIST_DRIFT")
if len(set(doc.get("auto_targets") or [])) != auto_total:
    die("R23_AUTO_TARGET_DUPLICATE")
if auto_total == 0 and doc.get("next_execution_gate") != "CURRENT_AUTHORITY_REQUIRED_PAYLOAD_SCAN_EXHAUSTED_NO_NEW_CLOSURE":
    die("R23_ZERO_RESULT_NEXT_GATE_DRIFT")
print(f"PASS: R23 payload closure records=34 auto={auto_total} unresolved={34-auto_total}")
print("PASS: zero exact intersection is legal and does not create a product closure")
