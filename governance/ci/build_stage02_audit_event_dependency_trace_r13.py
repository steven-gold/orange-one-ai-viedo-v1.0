#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
FRESH = ROOT / "00_SOURCE_INTAKE/fresh_run_003"
STAGE2 = FRESH / "04_PAGE_FUNCTIONAL_CONTRACT"
RAW = FRESH / "00_SOURCE_INTAKE/RAW_SOURCE"
R12 = ROOT / "governance/test/stage02/STAGE02_AUTHORITY_DEPENDENCY_RECLASSIFICATION_R12.yaml"
EXT_EVIDENCE = STAGE2 / "EXTERNAL_AUTHORITY/STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE.yaml"
OUT = ROOT / "governance/test/stage02/STAGE02_AUDIT_EVENT_DEPENDENCY_TRACE_R13.yaml"

FUNCTIONAL_CHAIN = {
    "CORE-01": STAGE2 / "CORE-01/FUNCTIONAL_CHAIN_SPEC.yaml",
    "ASSET-01": STAGE2 / "ASSET-01/FUNCTIONAL_CHAIN_SPEC.yaml",
}
RAW_PAGE = {
    "CORE-01": RAW / "CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml",
    "ASSET-01": RAW / "ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml",
}
EVENT_UID_KEYS = {"event_uid", "audit_event_uid", "integration_event_uid", "state_event_uid"}
METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


def die(msg: str) -> None:
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {} if obj is None else obj


def walk(obj, path=()):
    if isinstance(obj, dict):
        yield path, obj
        for key, value in obj.items():
            yield from walk(value, path + (str(key),))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from walk(value, path + (str(idx),))


def node_evidence(path: Path, node_path, proof: str, value=None):
    item = {
        "path": str(path.relative_to(ROOT)),
        "node_path": ".".join(node_path) if node_path else "$",
        "proof": proof,
    }
    if value is not None:
        item["value"] = value
    return item


def exact_dicts(doc, key: str, value):
    return [(p, n) for p, n in walk(doc) if isinstance(n, dict) and n.get(key) == value]


def recursively_collect_event_uids(node):
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in EVENT_UID_KEYS and isinstance(value, str) and value.strip():
                found.append((key, value.strip()))
            if isinstance(value, (dict, list)):
                found.extend(recursively_collect_event_uids(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(recursively_collect_event_uids(value))
    return found


def parse_operation_ref(operation_ref: str):
    result = {"raw": operation_ref, "operation_id": None, "method": None, "path": None}
    if not isinstance(operation_ref, str):
        return result
    left, sep, right = operation_ref.rpartition(":")
    if sep:
        token = right.strip()
        if re.fullmatch(r"[A-Za-z0-9_.-]+", token):
            result["operation_id"] = token
    m = re.search(r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+([^\s:]+)", operation_ref)
    if m:
        result["method"] = m.group(1)
        result["path"] = m.group(2)
    return result


def normalize_materialized_path(raw_path: str) -> Path:
    p = Path(raw_path)
    if p.parts and p.parts[0] == "04_PAGE_FUNCTIONAL_CONTRACT":
        return FRESH / p
    if str(p).startswith("00_SOURCE_INTAKE/fresh_run_003/"):
        return ROOT / p
    die(f"R13_UNSUPPORTED_MATERIALIZED_PATH:{raw_path}")


def current_external_authority_sources():
    evidence = load(EXT_EVIDENCE)
    sources = []
    provenance = []
    for gap_uid, entry in (evidence.get("materialized_authorities") or {}).items():
        if not isinstance(entry, dict) or entry.get("manifest_current") is not True:
            continue
        status = entry.get("authority_identity_status")
        if status not in {"EXACT_MATCH", "EXACT_CHAIN_LOCATED"}:
            die(f"R13_EXTERNAL_AUTHORITY_IDENTITY_NOT_EXACT:{gap_uid}:{status}")
        items = []
        if entry.get("materialized_path"):
            items.append(entry)
        for chain_item in entry.get("authority_chain") or []:
            if isinstance(chain_item, dict) and chain_item.get("materialized_path"):
                items.append(chain_item)
        for item in items:
            path = normalize_materialized_path(item["materialized_path"])
            if not path.is_file():
                die(f"R13_CURRENT_EXTERNAL_AUTHORITY_MISSING:{path.relative_to(ROOT)}")
            expected_blob = item.get("git_blob_sha")
            if expected_blob:
                actual_blob = subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()
                if actual_blob != expected_blob:
                    die(f"R13_EXTERNAL_AUTHORITY_BLOB_DRIFT:{path.relative_to(ROOT)}:{actual_blob}:{expected_blob}")
            sources.append((gap_uid, path, load(path)))
            provenance.append({
                "gap_uid": gap_uid,
                "path": str(path.relative_to(ROOT)),
                "manifest_current": True,
                "authority_identity_status": status,
                "git_blob_sha": expected_blob,
            })
    if not sources:
        die("R13_NO_CURRENT_ADMISSIBLE_EXTERNAL_AUTHORITY_SOURCES")
    return sources, provenance


def action_trace(scope: str, target_uid: str):
    chain_path = FUNCTIONAL_CHAIN[scope]
    chain = load(chain_path)
    action_matches = exact_dicts(chain, "action_uid", target_uid)
    action_nodes = [(p, n) for p, n in action_matches if isinstance(n.get("runtime_binding"), dict)]
    if len(action_nodes) != 1:
        die(f"R13_ACTION_NODE_NOT_UNIQUE:{target_uid}:{len(action_nodes)}")
    action_path, action = action_nodes[0]
    rb = action["runtime_binding"]
    port_uids = []
    for key in ("port_uid", "persist_via_port_uid", "source_port_uid"):
        value = rb.get(key)
        if isinstance(value, str) and value:
            port_uids.append(value)
    port_uids = sorted(set(port_uids))
    if len(port_uids) != 1:
        die(f"R13_EXACT_SINGLE_PORT_REQUIRED:{target_uid}:{port_uids}")
    port_uid = port_uids[0]
    port_matches = exact_dicts(chain, "port_uid", port_uid)
    port_nodes = [(p, n) for p, n in port_matches if n.get("operation_ref") or n.get("state_event")]
    if not port_nodes:
        die(f"R13_PORT_CONTRACT_NODE_MISSING:{target_uid}:{port_uid}")
    op_refs = sorted({n.get("operation_ref") for _, n in port_nodes if isinstance(n.get("operation_ref"), str) and n.get("operation_ref")})
    state_events = sorted({n.get("state_event") for _, n in port_nodes if isinstance(n.get("state_event"), str) and n.get("state_event")})
    if len(op_refs) != 1:
        die(f"R13_OPERATION_REF_NOT_UNIQUE:{target_uid}:{op_refs}")
    if len(state_events) != 1:
        die(f"R13_STATE_EVENT_NOT_UNIQUE:{target_uid}:{state_events}")
    operation_ref = op_refs[0]
    parsed = parse_operation_ref(operation_ref)
    return {
        "action_uid": target_uid,
        "action_binding_evidence": node_evidence(chain_path, action_path, "EXACT_ACTION_RUNTIME_BINDING", rb),
        "port_uid": port_uid,
        "port_contract_evidence": [node_evidence(chain_path, p, "EXACT_PORT_CONTRACT", {"operation_ref": n.get("operation_ref"), "state_event": n.get("state_event")}) for p, n in port_nodes],
        "operation_ref": operation_ref,
        "parsed_operation_identity": parsed,
        "state_event": state_events[0],
    }


def identity_match(node_path, node, target_uid: str, port_uid: str, operation_ref: str, parsed: dict):
    proofs = []
    if node.get("action_uid") == target_uid:
        proofs.append("EXACT_ACTION_UID")
    if node.get("port_uid") == port_uid:
        proofs.append("EXACT_PORT_UID")
    if node.get("operation_ref") == operation_ref:
        proofs.append("EXACT_OPERATION_REF")
    op_id = parsed.get("operation_id")
    if op_id and (node.get("operation_id") == op_id or (node_path and node_path[-1] == op_id)):
        proofs.append("EXACT_OPERATION_ID")
    method, route = parsed.get("method"), parsed.get("path")
    if method and route:
        node_route = node.get("path") if isinstance(node.get("path"), str) else node.get("route")
        methods = node.get("methods")
        node_method = node.get("method")
        method_exact = node_method == method or (isinstance(methods, list) and method in methods)
        if node_route == route and method_exact:
            proofs.append("EXACT_METHOD_AND_PATH")
    return proofs


def search_exact_event_bindings(scope: str, trace: dict, external_sources):
    sources = [("CURRENT_PAGE_AUTHORITY_EXACT_CAPTURE", RAW_PAGE[scope], load(RAW_PAGE[scope]))]
    sources.extend((f"CURRENT_EXTERNAL_AUTHORITY:{gap_uid}", path, doc) for gap_uid, path, doc in external_sources)
    matched_identity_nodes = []
    event_bindings = []
    for source_kind, path, doc in sources:
        for node_path, node in walk(doc):
            if not isinstance(node, dict):
                continue
            proofs = identity_match(node_path, node, trace["action_uid"], trace["port_uid"], trace["operation_ref"], trace["parsed_operation_identity"])
            if not proofs:
                continue
            matched_identity_nodes.append(node_evidence(path, node_path, "+".join(proofs), {"source_kind": source_kind}))
            for key, event_uid in recursively_collect_event_uids(node):
                event_bindings.append({
                    "event_uid": event_uid,
                    "event_uid_key": key,
                    "path": str(path.relative_to(ROOT)),
                    "node_path": ".".join(node_path) if node_path else "$",
                    "identity_proof": proofs,
                    "source_kind": source_kind,
                })
    return matched_identity_nodes, event_bindings


def main() -> None:
    r12 = load(R12)
    candidates = [r for r in (r12.get("records") or []) if r.get("category") == "AUDIT_EVENT_NODE_MISSING"]
    if len(candidates) != 13:
        die(f"R13_REQUIRES_EXACT_13_AUDIT_EVENT_IDENTITIES:{len(candidates)}")
    if any(r.get("classification") != "UNRESOLVED_FUNCTIONAL_CONTRACT_GAP" for r in candidates):
        die("R13_REQUIRES_R12_UNRESOLVED_AUDIT_EVENT_BASELINE")

    external_sources, external_provenance = current_external_authority_sources()
    records = []
    counts = Counter()
    scopes = Counter()
    for source_row in candidates:
        scope = source_row["scope"]
        target_uid = source_row["target_uid"]
        trace = action_trace(scope, target_uid)
        matched_nodes, bindings = search_exact_event_bindings(scope, trace, external_sources)
        unique_events = sorted({b["event_uid"] for b in bindings})
        if len(unique_events) == 1:
            classification = "EXACT_EVENT_DEPENDENCY_FOUND"
            reason = "UNIQUE_EVENT_UID_PHYSICALLY_BOUND_TO_EXACT_ACTION_PORT_OPERATION_IDENTITY_IN_CURRENT_ADMISSIBLE_SOURCE"
            materialization_candidate = True
        elif len(unique_events) > 1:
            classification = "CONFLICTING_EXACT_EVENT_DEPENDENCY"
            reason = "MULTIPLE_EVENT_UIDS_PHYSICALLY_BOUND_TO_THE_SAME_EXACT_OPERATION_IDENTITY"
            materialization_candidate = False
        else:
            classification = "CURRENT_FROZEN_EVENT_CONTRACT_MISSING"
            reason = "NO_EVENT_UID_PHYSICALLY_BOUND_TO_EXACT_ACTION_PORT_OPERATION_IDENTITY_IN_CURRENT_PAGE_OR_CURRENT_ADMISSIBLE_EXTERNAL_AUTHORITY"
            materialization_candidate = False
        counts[classification] += 1
        scopes[scope] += 1
        records.append({
            "blocker_uid": source_row["blocker_uid"],
            "scope": scope,
            "category": "AUDIT_EVENT_NODE_MISSING",
            "target_uid": target_uid,
            "r12_identity_ref": source_row["blocker_uid"],
            "r12_classification_used_as_authority": False,
            "trace": trace,
            "current_identity_matches": matched_nodes,
            "exact_event_binding_evidence": bindings,
            "unique_exact_event_uids": unique_events,
            "classification": classification,
            "classification_reason": reason,
            "semantic_event_name_inference_used": False,
            "event_uid_invention_used": False,
            "historical_non_current_authority_used": False,
            "materialization_candidate": materialization_candidate,
            "blocker_reduction_credit": 0,
            "next_action": "SEPARATE_BOUNDED_STAGE02_EVENT_BINDING_MATERIALIZATION_THEN_FRESH_REEXECUTION" if materialization_candidate else "KEEP_UNRESOLVED_AND_CONTINUE_CATEGORY_TRACE_WITHOUT_PRODUCT_AUTHORITY_PROMOTION",
        })

    if scopes != Counter({"ASSET-01": 9, "CORE-01": 4}):
        die(f"R13_SCOPE_DENOMINATOR_DRIFT:{dict(scopes)}")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    doc = {
        "schema_version": 1,
        "artifact_type": "NON_NORMATIVE_STAGE02_AUDIT_EVENT_DEPENDENCY_TRACE_R13",
        "normative_authority": False,
        "stage_uid": "STAGE-02",
        "cycle": "AUDIT_EVENT_EXACT_DEPENDENCY_TRACE_R13",
        "source_head_sha": head,
        "source_contracts": {
            "r12_identity_source": str(R12.relative_to(ROOT)),
            "r12_classification_accepted_as_authority": False,
            "functional_chain_sources": {k: str(v.relative_to(ROOT)) for k, v in FUNCTIONAL_CHAIN.items()},
            "current_page_authority_exact_captures": {k: str(v.relative_to(ROOT)) for k, v in RAW_PAGE.items()},
            "external_authority_materialization_evidence": str(EXT_EVIDENCE.relative_to(ROOT)),
            "current_admissible_external_sources": external_provenance,
        },
        "trace_contract": {
            "required_chain": "ACTION_UID -> EXACT_RUNTIME_PORT_UID -> EXACT_OPERATION_REF -> CURRENT_ADMISSIBLE_EXACT_IDENTITY_MATCH -> PHYSICAL_EVENT_UID",
            "operation_id_parse_is_syntactic_not_semantic": True,
            "semantic_similarity_may_supply_event_uid": False,
            "invented_event_uid_allowed": False,
            "classification_alone_may_reduce_blocker": False,
        },
        "denominators": {
            "audit_event_gaps_traced": 13,
            "scope_counts": dict(scopes),
            "exact_event_dependency_found": counts.get("EXACT_EVENT_DEPENDENCY_FOUND", 0),
            "conflicting_exact_event_dependency": counts.get("CONFLICTING_EXACT_EVENT_DEPENDENCY", 0),
            "current_frozen_event_contract_missing": counts.get("CURRENT_FROZEN_EVENT_CONTRACT_MISSING", 0),
            "effective_stage02_blocker_reduction_claimed": 0,
        },
        "records": records,
        "stage02_status": "BLOCKED",
        "stage02_effective_blocker_count_before_any_materialization_and_fresh_reexecution": 150,
        "stage03_allowed": False,
        "website_construction_allowed": False,
        "deployment_allowed": False,
        "formal_next_execution_point": "MATERIALIZE_ONLY_EXACT_R13_EVENT_CANDIDATES_IF_ANY_OTHERWISE_CONTINUE_TO_NEXT_FUNCTIONAL_CONTRACT_CATEGORY",
    }
    OUT.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(f"PASS: R13 traced exact 13 audit-event gaps classifications={dict(counts)}")
    print("PASS: no semantic event naming, no historical authority, no blocker reduction")


if __name__ == "__main__":
    main()
