#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R10 = ROOT / "governance/test/stage02/STAGE02_PRODUCT_AUTHORITY_APPROVAL_DOCKET_R10.yaml"
OUT = ROOT / "governance/test/stage02/STAGE02_AUTHORITY_DEPENDENCY_RECLASSIFICATION_R12.yaml"
FINDING = ROOT / "governance/test/stage02/FIND-20260915-024_PRODUCT_AUTHORITY_CIRCULAR_CLASSIFICATION.yaml"
STAGE2 = ROOT / "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT"
RAW = ROOT / "00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE"

PAGE_FILES = {
    "CORE-01": [
        RAW / "CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml",
        STAGE2 / "CORE-01/FUNCTIONAL_CHAIN_SPEC.yaml",
        STAGE2 / "CORE-01/BUSINESS_ENTITY_OPERATION_MATRIX.yaml",
        STAGE2 / "CORE-01/INTERACTION_TOPOLOGY_SPEC.yaml",
        STAGE2 / "CORE-01/FUNCTION_VISUAL_IMPACT_MATRIX.yaml",
        STAGE2 / "CORE-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml",
        STAGE2 / "DEPENDENCY_MAP.yaml",
    ],
    "ASSET-01": [
        RAW / "ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml",
        STAGE2 / "ASSET-01/FUNCTIONAL_CHAIN_SPEC.yaml",
        STAGE2 / "ASSET-01/BUSINESS_ENTITY_OPERATION_MATRIX.yaml",
        STAGE2 / "ASSET-01/INTERACTION_TOPOLOGY_SPEC.yaml",
        STAGE2 / "ASSET-01/FUNCTION_VISUAL_IMPACT_MATRIX.yaml",
        STAGE2 / "ASSET-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml",
        STAGE2 / "DEPENDENCY_MAP.yaml",
    ],
}

ALLOWED_CLASSES = {
    "DETERMINISTIC_REQUIRED_DEPENDENCY",
    "TRUE_PRODUCT_AUTHORITY_GAP",
    "UNRESOLVED_FUNCTIONAL_CONTRACT_GAP",
}
AUTHORITY_MARKER_KEYS = {
    "requires_product_authority", "product_authority_required", "authority_decision_required",
    "requires_authority_decision", "product_decision_required",
}
PAYLOAD_KEYS = {
    "payload_schema", "request_schema", "input_schema", "payload_fields", "request_fields", "input_fields",
    "payload_contract", "request_contract", "input_contract",
}
VALIDATION_KEYS = {
    "success_contract", "validation_contract", "validator_uid", "post_action_validation", "validation_rule", "evaluation_rule",
}
AUDIT_KEYS = {"audit_event_uid", "event_uid", "audit_event"}


def die(msg: str) -> None:
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {} if obj is None else obj


def nonempty(value) -> bool:
    return value not in (None, "", [], {})


def stable(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def walk(obj, path=()):
    if isinstance(obj, dict):
        yield path, obj
        for key, value in obj.items():
            yield from walk(value, path + (str(key),))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from walk(value, path + (str(idx),))


def immediate_mentions(node: dict, uid: str) -> bool:
    for value in node.values():
        if value == uid:
            return True
        if isinstance(value, list) and uid in value:
            return True
    return False


def recursive_values(node, keys: set[str], prefix=()):
    out = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = prefix + (str(key),)
            if key in keys and nonempty(value):
                out.append((here, value))
            if isinstance(value, (dict, list)):
                out.extend(recursive_values(value, keys, here))
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            out.extend(recursive_values(value, keys, prefix + (str(idx),)))
    return out


def load_page_docs(scope: str):
    return [(path, load(path)) for path in PAGE_FILES[scope]]


def matching_nodes(docs, uid: str):
    matches = []
    for path, doc in docs:
        for node_path, node in walk(doc):
            if immediate_mentions(node, uid):
                matches.append((path, node_path, node))
    return matches


def evidence(path: Path, node_path, key_path=None, value=None, proof=None):
    item = {"path": str(path.relative_to(ROOT)), "node_path": ".".join(node_path) if node_path else "$"}
    if key_path is not None:
        item["key_path"] = ".".join(key_path)
    if value is not None:
        item["value"] = value
    if proof is not None:
        item["proof"] = proof
    return item


def exact_field_evidence(nodes, keys: set[str]):
    out = []
    for path, node_path, node in nodes:
        for key_path, value in recursive_values(node, keys):
            out.append(evidence(path, node_path, key_path, value))
    return out


def unique_values(items):
    vals = {}
    for item in items:
        if "value" in item:
            vals[stable(item["value"])] = item["value"]
    return vals


def exact_bound_uids(nodes, keys: set[str]):
    values = []
    for _, _, node in nodes:
        for _, value in recursive_values(node, keys):
            if isinstance(value, str) and value:
                values.append(value)
    return sorted(set(values))


def explicit_authority_evidence(nodes):
    out = []
    for path, node_path, node in nodes:
        for key_path, value in recursive_values(node, AUTHORITY_MARKER_KEYS):
            truthy = value is True or (isinstance(value, str) and value.strip().upper() not in {"", "FALSE", "NO", "NONE", "NOT_REQUIRED"})
            if truthy:
                out.append(evidence(path, node_path, key_path, value, "EXPLICIT_PRODUCT_AUTHORITY_REQUIREMENT"))
    return out


def registered_event_uids(docs):
    vals = set()
    for _, doc in docs:
        for _, node in walk(doc):
            for _, value in recursive_values(node, {"event_uid", "audit_event_uid"}):
                if isinstance(value, str) and value:
                    vals.add(value)
    return vals


def state_event_token_evidence(nodes, registry):
    out = []
    for path, node_path, node in nodes:
        for key_path, value in recursive_values(node, {"state_event"}):
            if not isinstance(value, str) or "|" not in value:
                continue
            token = value.split("|")[-1].strip()
            if token in registry:
                out.append(evidence(path, node_path, key_path, token, "REGISTERED_STATE_EVENT_TOKEN"))
    return out


def bound_port_nodes(docs, action_nodes):
    port_uids = exact_bound_uids(action_nodes, {"port_uid", "persist_via_port_uid", "source_port_uid"})
    matches = []
    for uid in port_uids:
        matches.extend(matching_nodes(docs, uid))
    return port_uids, matches


def error_nodes(docs, error_uids):
    matches = []
    for uid in error_uids:
        matches.extend(matching_nodes(docs, uid))
    return matches


def classify_record(rec, docs):
    uid = rec.get("target_uid")
    category = rec.get("category")
    detail = rec.get("missing_field_or_relation")
    nodes = matching_nodes(docs, uid)
    authority_ev = explicit_authority_evidence(nodes)
    base = {
        "blocker_uid": rec.get("blocker_uid"), "scope": rec.get("scope"), "category": category,
        "target_uid": uid, "missing_field_or_relation": detail, "r10_identity_only": True,
        "r10_approval_state_used_as_evidence": False, "r10_authority_decision_used_as_evidence": False,
        "semantic_inference_used": False, "historical_non_current_authority_used": False,
        "blocker_reduction_credit": 0,
    }
    if authority_ev:
        base.update({
            "classification": "TRUE_PRODUCT_AUTHORITY_GAP",
            "classification_reason": "EXPLICIT_CURRENT_OR_FROZEN_EVIDENCE_REQUIRES_PRODUCT_AUTHORITY_DECISION",
            "authority_requirement_evidence": authority_ev[:8], "deterministic_dependency_evidence": [],
            "unique_minimal_dependency": False, "scope_ambiguity_zero": False, "materialization_candidate": False,
            "next_action": "EXPLICIT_PRODUCT_AUTHORITY_DECISION_REQUIRED",
        })
        return base

    det, conflict = [], []
    if category == "ACTION_WITHOUT_CONTROL_OR_TRIGGER":
        for path, node_path, node in nodes:
            rel = node.get("relation")
            if node.get("to") == uid and isinstance(rel, str) and rel in {"CONTROL_TRIGGERS_ACTION", "TRIGGER_INVOKES_ACTION", "SYSTEM_TRIGGERS_ACTION"}:
                det.append(evidence(path, node_path, value={"from": node.get("from"), "to": uid, "relation": rel}, proof="EXACT_REGISTERED_TRIGGER_EDGE"))
            if node.get("action_uid") == uid and nonempty(node.get("control_uid")):
                det.append(evidence(path, node_path, value={"control_uid": node.get("control_uid"), "action_uid": uid}, proof="EXACT_CONTROL_ACTION_BINDING"))

    elif category == "PAYLOAD_INPUT_CONTRACT_MISSING":
        direct = exact_field_evidence(nodes, PAYLOAD_KEYS)
        _, ports = bound_port_nodes(docs, nodes)
        candidates = direct + exact_field_evidence(ports, PAYLOAD_KEYS)
        vals = unique_values(candidates)
        if len(vals) == 1: det = candidates
        elif len(vals) > 1: conflict = candidates

    elif category == "AUDIT_EVENT_NODE_MISSING":
        direct = exact_field_evidence(nodes, AUDIT_KEYS)
        _, ports = bound_port_nodes(docs, nodes)
        registry = registered_event_uids(docs)
        candidates = direct + exact_field_evidence(ports, AUDIT_KEYS) + state_event_token_evidence(nodes + ports, registry)
        vals = unique_values(candidates)
        if len(vals) == 1: det = candidates
        elif len(vals) > 1: conflict = candidates

    elif category == "FAILURE_STATE_ERROR_BINDING_MISSING":
        failure = exact_field_evidence(nodes, {"failure_state"})
        recovery = exact_field_evidence(nodes, {"recovery"})
        if failure and recovery:
            pairs = {(stable(x["value"]), stable(y["value"])) for x in failure for y in recovery}
            if len(pairs) == 1: det = failure + recovery
            else: conflict = failure + recovery
        else:
            error_uids = exact_bound_uids(nodes, {"error_uid"})
            errors = error_nodes(docs, error_uids)
            recoveries = exact_field_evidence(errors, {"recovery"})
            if len(error_uids) == 1 and recoveries and len(unique_values(recoveries)) == 1:
                det = exact_field_evidence(nodes, {"error_uid"}) + recoveries
            elif len(error_uids) > 1 or len(unique_values(recoveries)) > 1:
                conflict = exact_field_evidence(nodes, {"error_uid"}) + recoveries

    elif category == "POST_ACTION_VALIDATION_NODE_MISSING":
        direct = exact_field_evidence(nodes, VALIDATION_KEYS)
        _, ports = bound_port_nodes(docs, nodes)
        candidates = direct + exact_field_evidence(ports, VALIDATION_KEYS)
        vals = unique_values(candidates)
        if len(vals) == 1: det = candidates
        elif len(vals) > 1: conflict = candidates

    elif category == "STATE_TRANSITION_LEDGER_FIELD_MISSING":
        field = str(detail or "").strip()
        if field in {"mutation_owner", "failure_state", "recovery", "audit_event_uid"}:
            candidates = exact_field_evidence(nodes, {field})
            vals = unique_values(candidates)
            if len(vals) == 1: det = candidates
            elif len(vals) > 1: conflict = candidates

    if det:
        base.update({
            "classification": "DETERMINISTIC_REQUIRED_DEPENDENCY",
            "classification_reason": "UNIQUE_EXACT_FROZEN_REGISTERED_DEPENDENCY_PROOF_FOUND",
            "authority_requirement_evidence": [], "deterministic_dependency_evidence": det[:12],
            "unique_minimal_dependency": True, "authority_gap_zero_for_this_derivation": True,
            "scope_ambiguity_zero": True, "materialization_candidate": True,
            "next_action": "BOUNDED_STAGE02_MATERIALIZATION_CANDIDATE_REQUIRES_SEPARATE_VALIDATION",
        })
        return base

    reason = "NO_EXPLICIT_PRODUCT_AUTHORITY_REQUIREMENT_AND_NO_UNIQUE_EXACT_DETERMINISTIC_BINDING_PROVEN"
    if conflict:
        reason = "MULTIPLE_OR_CONFLICTING_EXACT_DEPENDENCY_VALUES_REQUIRE_RESOLUTION_BEFORE_CLASSIFICATION"
    base.update({
        "classification": "UNRESOLVED_FUNCTIONAL_CONTRACT_GAP", "classification_reason": reason,
        "authority_requirement_evidence": [], "deterministic_dependency_evidence": [],
        "conflicting_dependency_evidence": conflict[:12], "unique_minimal_dependency": False,
        "authority_gap_zero_for_this_derivation": False, "scope_ambiguity_zero": False if conflict else None,
        "materialization_candidate": False,
        "next_action": "CONTINUE_EXACT_CURRENT_FROZEN_DEPENDENCY_TRACE_OR_REOPEN_DESIGN_ONLY_IF_TRUE_AUTHORITY_NEED_IS_PROVEN",
    })
    return base


def main() -> None:
    r10 = load(R10)
    finding = load(FINDING)
    records = r10.get("records") or []
    if len(records) != 150:
        die(f"R12_REQUIRES_EXACT_150_IDENTITIES:{len(records)}")
    if finding.get("finding_uid") != "FIND-20260915-024":
        die("R12_FINDING_024_MISSING_OR_WRONG")
    docs = {scope: load_page_docs(scope) for scope in PAGE_FILES}
    output = []
    for rec in records:
        scope = rec.get("scope")
        if scope not in docs:
            die(f"UNKNOWN_SCOPE:{scope}")
        output.append(classify_record(rec, docs[scope]))
    classes = Counter(row["classification"] for row in output)
    scopes = Counter(row["scope"] for row in output)
    categories = Counter(row["category"] for row in output)
    if set(classes) - ALLOWED_CLASSES:
        die(f"UNEXPECTED_CLASS:{set(classes) - ALLOWED_CLASSES}")
    if scopes != Counter({"ASSET-01": 110, "CORE-01": 40}):
        die(f"SCOPE_DRIFT:{dict(scopes)}")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    doc = {
        "schema_version": 1,
        "artifact_type": "NON_NORMATIVE_STAGE02_AUTHORITY_DEPENDENCY_RECLASSIFICATION_R12",
        "normative_authority": False, "stage_uid": "STAGE-02",
        "cycle": "AUTHORITY_VS_DETERMINISTIC_DEPENDENCY_RECLASSIFICATION_R12",
        "source_head_sha": head, "finding_ref": str(FINDING.relative_to(ROOT)),
        "source_contracts": {
            "r10_identity_source_only": str(R10.relative_to(ROOT)),
            "r10_product_authority_conclusion_accepted_as_evidence": False,
            "substantive_evidence_roots": [
                "00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/{PAGE}",
                "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/{PAGE}/FUNCTIONAL_CHAIN_SPEC.yaml",
                "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/{PAGE}/BUSINESS_ENTITY_OPERATION_MATRIX.yaml",
                "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/{PAGE}/INTERACTION_TOPOLOGY_SPEC.yaml",
                "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/{PAGE}/FUNCTION_VISUAL_IMPACT_MATRIX.yaml",
                "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/{PAGE}/AUTO_COMPLETION_SCOPE_LEDGER.yaml",
                "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/DEPENDENCY_MAP.yaml",
            ],
        },
        "classification_contract": {
            "deterministic_required_dependency": "REQUIRES_UNIQUE_EXACT_FROZEN_REGISTERED_DEPENDENCY_PROOF_AND_ZERO_SCOPE_AMBIGUITY",
            "true_product_authority_gap": "REQUIRES_EXPLICIT_CURRENT_OR_FROZEN_EVIDENCE_THAT_PRODUCT_AUTHORITY_DECISION_IS_REQUIRED",
            "unresolved_functional_contract_gap": "DEFAULT_WHEN_NEITHER_TRUE_AUTHORITY_NOR_UNIQUE_DETERMINISTIC_DEPENDENCY_IS_PROVEN",
            "absence_of_field_alone_proves_product_authority": False,
            "classification_alone_reduces_blocker": False,
        },
        "denominators": {
            "total_reclassified": 150,
            "deterministic_required_dependency": classes.get("DETERMINISTIC_REQUIRED_DEPENDENCY", 0),
            "true_product_authority_gap_proven": classes.get("TRUE_PRODUCT_AUTHORITY_GAP", 0),
            "unresolved_functional_contract_gap": classes.get("UNRESOLVED_FUNCTIONAL_CONTRACT_GAP", 0),
            "effective_stage02_blocker_reduction_claimed": 0,
            "scope_counts": dict(scopes), "category_counts": dict(categories),
        },
        "records": output,
        "supersession": {
            "r5_r10_r11_all_150_product_authority_interpretation": "SUPERSEDED_FOR_CLASSIFICATION_BY_R12",
            "r5_r10_r11_retained_as_historical_non_normative_evidence": True,
        },
        "stage02_status": "BLOCKED",
        "stage02_effective_blocker_count_before_materialization_and_fresh_reexecution": 150,
        "stage03_allowed": False, "website_construction_allowed": False, "deployment_allowed": False,
        "formal_next_execution_point": "VALIDATE_AND_MATERIALIZE_ONLY_R12_DETERMINISTIC_CANDIDATES_THEN_CLEAN_RESET_FULL_LINE_AND_FRESH_STAGE02_REEXECUTION",
    }
    OUT.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=180), encoding="utf-8")
    print(f"PASS: R12 reclassified 150 records classes={dict(classes)}")
    print("PASS: R10 used for blocker identity only; its Product Authority conclusion was not accepted as substantive evidence")
    print("PASS: classification alone claims zero blocker reduction")


if __name__ == "__main__":
    main()
