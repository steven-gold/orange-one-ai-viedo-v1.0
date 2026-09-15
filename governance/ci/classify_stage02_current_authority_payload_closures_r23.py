#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
PRODUCT_ROOT = ROOT / "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT"
R14 = ROOT / "governance/test/stage02/STAGE02_PAYLOAD_DEPENDENCY_TRACE_R14.yaml"
R22_RESULT = ROOT / ".github/stage02-test/STAGE02_R22_EFFECTIVE_REEXECUTION_RESULT.json"
MANIFEST = PRODUCT_ROOT / "EXTERNAL_AUTHORITY/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml"
MATERIALIZATION = PRODUCT_ROOT / "EXTERNAL_AUTHORITY/STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE.yaml"
SHARED = PRODUCT_ROOT / "EXTERNAL_AUTHORITY/GAP-006/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml"
OUT = ROOT / "governance/test/stage02/STAGE02_CURRENT_AUTHORITY_PAYLOAD_CLOSURE_R23.yaml"
EXPECTED_SHARED_SOURCE = "authority/runtime/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml"
EXPECTED_SHARED_MATERIALIZED = "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/EXTERNAL_AUTHORITY/GAP-006/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml"


def die(msg: str) -> None:
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def load_json(path: Path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        die(f"JSON_MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def nonempty(value):
    return value not in (None, "", [], {})


def flatten(node):
    out = []
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, list):
        for item in node:
            out.extend(flatten(item))
    elif isinstance(node, dict):
        for value in node.values():
            out.extend(flatten(value))
    return out


def trace_ops(trace):
    out = set()
    for key in ("operation_id", "registered_operation", "operation", "operation_ref", "shared_operation_id"):
        value = trace.get(key)
        if nonempty(value) and not isinstance(value, (dict, list)):
            out.add(str(value))
    return out


def exact_method_path(trace, operation):
    method = str(operation.get("method") or "").upper()
    route = str(operation.get("route") or "")
    if not method or not route:
        return False, []
    proof = []
    if nonempty(trace.get("method")):
        if str(trace["method"]).upper() != method:
            return False, []
        proof.append("METHOD_EXACT")
    if nonempty(trace.get("path")):
        if str(trace["path"]) != route:
            return False, []
        proof.append("PATH_EXACT")
    effective = trace.get("method_effective_path") or trace.get("method_path")
    if nonempty(effective):
        if str(effective).strip() != f"{method} {route}":
            return False, []
        proof.append("METHOD_EFFECTIVE_PATH_EXACT")
    return True, proof


r22 = load_json(R22_RESULT)
if r22.get("fresh_functional_gap_total") != 129:
    die(f"R22_PARENT_DENOMINATOR_DRIFT:{r22.get('fresh_functional_gap_total')}")
if (r22.get("effective_gap_categories") or {}).get("PAYLOAD_INPUT_CONTRACT_MISSING") != 34:
    die("R22_PARENT_PAYLOAD_DENOMINATOR_DRIFT")

remaining = []
for page_uid, page in (r22.get("pages") or {}).items():
    for gap in ((page.get("functional_chain_effective_r22_scan") or {}).get("gaps") or []):
        if gap.get("category") == "PAYLOAD_INPUT_CONTRACT_MISSING":
            remaining.append({"page_uid": page_uid, **gap})
if len(remaining) != 34:
    die(f"R22_PAYLOAD_GAP_EXTRACTION_DRIFT:{len(remaining)}")
if len({(x["page_uid"], x.get("uid"), x.get("detail")) for x in remaining}) != 34:
    die("R22_PAYLOAD_GAP_SIGNATURE_DUPLICATE")

r14 = load_yaml(R14)
r14_rows = [x for x in (r14.get("records") or []) if x.get("category") == "PAYLOAD_INPUT_CONTRACT_MISSING"]
if len(r14_rows) != 34:
    die(f"R14_PAYLOAD_DENOMINATOR_DRIFT:{len(r14_rows)}")
r14_index = {}
for row in r14_rows:
    key = (row.get("scope"), str(row.get("target_uid")))
    if key in r14_index:
        die(f"R14_DUPLICATE_IDENTITY:{key}")
    r14_index[key] = row

manifest = load_yaml(MANIFEST)
auth = manifest.get("authority") or {}
if auth.get("id") != "ACPOS_CURRENT_AUTHORITY_MANIFEST" or auth.get("status") != "FINAL_LOCKED" or auth.get("current_only") is not True:
    die("CURRENT_AUTHORITY_MANIFEST_IDENTITY_DRIFT")
if EXPECTED_SHARED_SOURCE not in flatten(manifest.get("current_authority_set") or {}):
    die("SHARED_RUNTIME_NOT_IN_CURRENT_AUTHORITY_SET")
if (manifest.get("load_policy") or {}).get("only_listed_files_are_current_authority") is not True:
    die("CURRENT_AUTHORITY_LOAD_POLICY_DRIFT")

mat = load_yaml(MATERIALIZATION)
gap006 = ((mat.get("materialized_authorities") or {}).get("GAP-006") or {})
if gap006.get("source_path") != EXPECTED_SHARED_SOURCE or gap006.get("manifest_current") is not True or gap006.get("authority_identity_status") != "EXACT_MATCH":
    die("GAP006_CURRENT_MATERIALIZATION_IDENTITY_DRIFT")
if (mat.get("policy") or {}).get("authority_payload_rewritten") is not False:
    die("EXTERNAL_AUTHORITY_PAYLOAD_REWRITE_POLICY_DRIFT")

shared = load_yaml(SHARED)
if shared.get("authority_id") != "ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY" or str(shared.get("version")) != "1.0" or shared.get("status") != "CURRENT_CONTRACT":
    die("SHARED_RUNTIME_AUTHORITY_IDENTITY_DRIFT")
operations = shared.get("operations") or {}
if not isinstance(operations, dict):
    die("SHARED_RUNTIME_OPERATIONS_MAPPING_REQUIRED")

sources = ((r14.get("source_contracts") or {}).get("current_admissible_external_sources") or [])
shared_source = [x for x in sources if isinstance(x, dict) and x.get("path") == EXPECTED_SHARED_MATERIALIZED]
if len(shared_source) != 1 or shared_source[0].get("manifest_current") is not True or shared_source[0].get("authority_identity_status") != "EXACT_MATCH":
    die("R14_SHARED_RUNTIME_CURRENT_SOURCE_NOT_PROVEN")

records = []
for gap in sorted(remaining, key=lambda x: (x["page_uid"], str(x.get("uid")))):
    page_uid = gap["page_uid"]
    target = str(gap.get("uid"))
    row = r14_index.get((page_uid, target))
    if not row:
        die(f"R14_IDENTITY_MISSING:{page_uid}:{target}")
    trace = row.get("trace") or {}
    ops = trace_ops(trace)
    candidates = []
    rejected = []
    for operation_id, operation in sorted(operations.items()):
        if not isinstance(operation, dict):
            continue
        binding = ((operation.get("page_bindings") or {}).get(page_uid) or {})
        if str(binding.get("action_uid") or "") != target:
            continue
        ok, method_path_proof = exact_method_path(trace, operation)
        if operation_id not in ops or not ok:
            rejected.append({"operation_id": operation_id, "reason": "R14_OPERATION_OR_METHOD_PATH_IDENTITY_MISMATCH", "trace_operation_values": sorted(ops)})
            continue
        payload = operation.get("required_payload")
        if not isinstance(payload, list) or not payload or any(not isinstance(x, str) or not x.strip() for x in payload):
            rejected.append({"operation_id": operation_id, "reason": "CURRENT_AUTHORITY_REQUIRED_PAYLOAD_NOT_EXPLICIT_NONEMPTY_FIELD_LIST"})
            continue
        if len(payload) != len(set(payload)):
            die(f"DUPLICATE_REQUIRED_PAYLOAD_FIELD:{operation_id}")
        candidates.append({
            "source_kind": "CURRENT_MANIFEST_LISTED_RUNTIME_AUTHORITY",
            "source_path": EXPECTED_SHARED_MATERIALIZED,
            "authority_id": shared.get("authority_id"),
            "authority_version": shared.get("version"),
            "operation_id": operation_id,
            "page_uid": page_uid,
            "action_uid": target,
            "control_uid": binding.get("control_uid"),
            "method": str(operation.get("method")).upper(),
            "route": operation.get("route"),
            "required_payload": list(payload),
            "canonical_owner": operation.get("canonical_owner"),
            "identity_proof": ["CURRENT_MANIFEST_LISTED", "GAP006_EXACT_MATERIALIZATION", "PAGE_BINDING_ACTION_UID_EXACT", "R14_OPERATION_ID_EXACT", *method_path_proof],
        })
    if len(candidates) == 1:
        disposition = "AUTO_REMEDIABLE_CURRENT_AUTHORITY_REQUIRED_PAYLOAD"
        authorized = True
        authority_gap = False
        candidate_value = {"operation_id": candidates[0]["operation_id"], "method": candidates[0]["method"], "route": candidates[0]["route"], "required_fields": candidates[0]["required_payload"]}
    elif len(candidates) > 1:
        disposition = "AUTHORITY_GAP_MULTIPLE_CURRENT_REQUIRED_PAYLOAD_CONTRACTS"
        authorized = False
        authority_gap = True
        candidate_value = None
    else:
        disposition = "UNRESOLVED_NO_EXACT_CURRENT_AUTHORITY_REQUIRED_PAYLOAD"
        authorized = False
        authority_gap = False
        candidate_value = None
    records.append({
        "page_uid": page_uid,
        "category": "PAYLOAD_INPUT_CONTRACT_MISSING",
        "target_uid": target,
        "gap_detail": gap.get("detail"),
        "blocker_uid": row.get("blocker_uid"),
        "r14_trace_operation_values": sorted(ops),
        "r14_method": trace.get("method"),
        "r14_path": trace.get("path"),
        "r14_method_effective_path": trace.get("method_effective_path") or trace.get("method_path"),
        "disposition": disposition,
        "authorized_for_auto_completion": authorized,
        "authority_gap_proven": authority_gap,
        "candidate_value": candidate_value,
        "candidate_evidence": candidates,
        "rejected_current_authority_bindings": rejected,
        "semantic_inference_used": False,
        "ai_invented_business_value": False,
        "historical_non_current_authority_used": False,
        "operation_registry_used_as_payload_authority": False,
        "outside_frozen_registered_dependency_closure": False,
    })

summary = Counter(x["disposition"] for x in records)
auto = [x for x in records if x["authorized_for_auto_completion"]]
if any(x["page_uid"] != "ASSET-01" for x in auto):
    die("R23_AUTO_SCOPE_OUTSIDE_ASSET01")
if len(auto) > 4:
    die(f"R23_AUTO_DENOMINATOR_EXCEEDS_SHARED_RUNTIME_CONSUMERS:{len(auto)}")
if summary.get("AUTHORITY_GAP_MULTIPLE_CURRENT_REQUIRED_PAYLOAD_CONTRACTS", 0):
    die("R23_MULTIPLE_CURRENT_PAYLOAD_CONTRACTS_REQUIRE_STOP")

head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
next_gate = "MATERIALIZE_R23_EXACT_REQUIRED_PAYLOAD_CLOSURES_THEN_FRESH_STAGE02_REEXECUTION" if auto else "CURRENT_AUTHORITY_REQUIRED_PAYLOAD_SCAN_EXHAUSTED_NO_NEW_CLOSURE"
out = {
    "schema_version": 2,
    "artifact_type": "NON_NORMATIVE_STAGE02_CURRENT_AUTHORITY_PAYLOAD_CLOSURE_R23",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "cycle": "CURRENT_MANIFEST_LISTED_REQUIRED_PAYLOAD_EXACT_CLOSURE_R23",
    "source_head_sha": head,
    "parent_r22_result": str(R22_RESULT.relative_to(ROOT)),
    "source_r14_trace": str(R14.relative_to(ROOT)),
    "current_authority_manifest": str(MANIFEST.relative_to(ROOT)),
    "external_authority_materialization_evidence": str(MATERIALIZATION.relative_to(ROOT)),
    "current_shared_runtime_authority": str(SHARED.relative_to(ROOT)),
    "source_policy": {
        "manifest_listed_current_authority_only": True,
        "operation_registry_may_support_identity_but_not_create_payload_contract": True,
        "required_payload_is_copied_exactly_from_current_runtime_authority": True,
        "page_action_operation_method_path_identity_must_match": True,
        "zero_exact_intersection_is_valid_audited_outcome": True,
        "semantic_field_inference_forbidden": True,
        "historical_non_current_authority_forbidden": True,
        "ai_invented_payload_fields_forbidden": True,
        "classification_itself_reduces_blocker": False,
    },
    "denominators": {
        "parent_effective_gap_total": 129,
        "parent_payload_gap_total": 34,
        "payload_gaps_evaluated": len(records),
        "auto_remediable_current_authority_payload_total": len(auto),
        "authority_gap_multiple_contract_total": summary.get("AUTHORITY_GAP_MULTIPLE_CURRENT_REQUIRED_PAYLOAD_CONTRACTS", 0),
        "unresolved_no_exact_current_payload_total": summary.get("UNRESOLVED_NO_EXACT_CURRENT_AUTHORITY_REQUIRED_PAYLOAD", 0),
        "blocker_reduction_claimed_before_materialization": 0,
    },
    "auto_targets": [x["target_uid"] for x in auto],
    "records": records,
    "current_specification_mutated": False,
    "immutable_stage1_source_mutated": False,
    "stage02_status": "BLOCKED",
    "stage03_allowed": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
    "next_execution_gate": next_gate,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=180), encoding="utf-8")
print(f"R23_PAYLOAD_GAPS_EVALUATED={len(records)}")
print(f"R23_AUTO_REMEDIABLE_CURRENT_AUTHORITY_PAYLOAD={len(auto)}")
print(f"R23_AUTO_TARGETS={','.join(x['target_uid'] for x in auto)}")
print(f"R23_UNRESOLVED_PAYLOAD={summary.get('UNRESOLVED_NO_EXACT_CURRENT_AUTHORITY_REQUIRED_PAYLOAD', 0)}")
print("PASS: zero exact intersection is a valid audited result; no closure is invented")
