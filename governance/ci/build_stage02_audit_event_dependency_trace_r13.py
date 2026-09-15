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


def evidence(path: Path, node_path, proof: str, value=None):
    out = {"path": str(path.relative_to(ROOT)), "node_path": ".".join(node_path) if node_path else "$", "proof": proof}
    if value is not None:
        out["value"] = value
    return out


def exact_dicts(doc, key: str, value):
    return [(p, n) for p, n in walk(doc) if isinstance(n, dict) and n.get(key) == value]


def event_uids(node):
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in EVENT_UID_KEYS and isinstance(value, str) and value.strip():
                found.append((key, value.strip()))
            if isinstance(value, (dict, list)):
                found.extend(event_uids(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(event_uids(value))
    return found


def parse_method_path(text):
    if not isinstance(text, str):
        return None, None
    m = re.search(r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+([^\s:]+)", text)
    return (m.group(1), m.group(2)) if m else (None, None)


def parse_operation_id_from_ref(text):
    if not isinstance(text, str):
        return None
    _, sep, right = text.rpartition(":")
    token = right.strip() if sep else ""
    return token if re.fullmatch(r"[A-Za-z0-9_.-]+", token) else None


def normalize_materialized(raw_path: str) -> Path:
    p = Path(raw_path)
    if p.parts and p.parts[0] == "04_PAGE_FUNCTIONAL_CONTRACT":
        return FRESH / p
    if str(p).startswith("00_SOURCE_INTAKE/fresh_run_003/"):
        return ROOT / p
    die(f"R13_UNSUPPORTED_MATERIALIZED_PATH:{raw_path}")


def current_external_sources():
    doc = load(EXT_EVIDENCE)
    sources, provenance = [], []
    for gap_uid, entry in (doc.get("materialized_authorities") or {}).items():
        if not isinstance(entry, dict) or entry.get("manifest_current") is not True:
            continue
        status = entry.get("authority_identity_status")
        if status not in {"EXACT_MATCH", "EXACT_CHAIN_LOCATED"}:
            die(f"R13_EXTERNAL_AUTHORITY_IDENTITY_NOT_EXACT:{gap_uid}:{status}")
        items = ([entry] if entry.get("materialized_path") else []) + [x for x in (entry.get("authority_chain") or []) if isinstance(x, dict) and x.get("materialized_path")]
        for item in items:
            path = normalize_materialized(item["materialized_path"])
            if not path.is_file():
                die(f"R13_CURRENT_EXTERNAL_AUTHORITY_MISSING:{path.relative_to(ROOT)}")
            expected = item.get("git_blob_sha")
            if expected:
                actual = subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()
                if actual != expected:
                    die(f"R13_EXTERNAL_AUTHORITY_BLOB_DRIFT:{path.relative_to(ROOT)}:{actual}:{expected}")
            sources.append((gap_uid, path, load(path)))
            provenance.append({"gap_uid": gap_uid, "path": str(path.relative_to(ROOT)), "manifest_current": True, "authority_identity_status": status, "git_blob_sha": expected})
    if not sources:
        die("R13_NO_CURRENT_ADMISSIBLE_EXTERNAL_AUTHORITY_SOURCES")
    return sources, provenance


def action_trace(scope: str, target_uid: str):
    chain_path = FUNCTIONAL_CHAIN[scope]
    chain = load(chain_path)
    actions = [(p, n) for p, n in exact_dicts(chain, "action_uid", target_uid) if isinstance(n.get("runtime_binding"), dict)]
    if len(actions) != 1:
        die(f"R13_ACTION_NODE_NOT_UNIQUE:{target_uid}:{len(actions)}")
    action_path, action = actions[0]
    rb = action["runtime_binding"]
    ports = sorted({rb.get(k) for k in ("port_uid", "persist_via_port_uid", "source_port_uid") if isinstance(rb.get(k), str) and rb.get(k)})
    if len(ports) != 1:
        die(f"R13_EXACT_SINGLE_PORT_REQUIRED:{target_uid}:{ports}")
    port_uid = ports[0]
    port_nodes = [(p, n) for p, n in exact_dicts(chain, "port_uid", port_uid) if any(n.get(k) for k in ("registered_operation", "operation_ref", "method_effective_path", "state_event"))]
    if not port_nodes:
        die(f"R13_PORT_CONTRACT_NODE_MISSING:{target_uid}:{port_uid}")

    registered_ops = sorted({n.get("registered_operation") for _, n in port_nodes if isinstance(n.get("registered_operation"), str) and n.get("registered_operation")})
    operation_refs = sorted({n.get("operation_ref") for _, n in port_nodes if isinstance(n.get("operation_ref"), str) and n.get("operation_ref")})
    method_paths = sorted({n.get("method_effective_path") for _, n in port_nodes if isinstance(n.get("method_effective_path"), str) and n.get("method_effective_path")})
    state_events = sorted({n.get("state_event") for _, n in port_nodes if isinstance(n.get("state_event"), str) and n.get("state_event")})
    if len(registered_ops) > 1 or len(operation_refs) > 1 or len(method_paths) > 1 or len(state_events) != 1:
        die(f"R13_PORT_IDENTITY_NOT_UNIQUE:{target_uid}:registered={registered_ops}:refs={operation_refs}:paths={method_paths}:state={state_events}")

    operation_id = registered_ops[0] if registered_ops else (parse_operation_id_from_ref(operation_refs[0]) if operation_refs else None)
    method, route = parse_method_path(method_paths[0] if method_paths else (operation_refs[0] if operation_refs else None))
    if not operation_id and not (method and route):
        die(f"R13_OPERATION_IDENTITY_MISSING:{target_uid}:{port_uid}")
    return {
        "action_uid": target_uid,
        "action_binding_evidence": evidence(chain_path, action_path, "EXACT_ACTION_RUNTIME_BINDING", rb),
        "port_uid": port_uid,
        "port_contract_evidence": [evidence(chain_path, p, "EXACT_PORT_CONTRACT", {"registered_operation": n.get("registered_operation"), "operation_ref": n.get("operation_ref"), "method_effective_path": n.get("method_effective_path"), "state_event": n.get("state_event")}) for p, n in port_nodes],
        "registered_operation": operation_id,
        "operation_ref": operation_refs[0] if operation_refs else None,
        "method_effective_path": method_paths[0] if method_paths else None,
        "method": method,
        "path": route,
        "state_event": state_events[0],
    }


def identity_match(node_path, node, trace):
    proofs = []
    if node.get("action_uid") == trace["action_uid"]:
        proofs.append("EXACT_ACTION_UID")
    if node.get("port_uid") == trace["port_uid"]:
        proofs.append("EXACT_PORT_UID")
    if trace.get("operation_ref") and node.get("operation_ref") == trace["operation_ref"]:
        proofs.append("EXACT_OPERATION_REF")
    op_id = trace.get("registered_operation")
    if op_id and (node.get("registered_operation") == op_id or node.get("operation_id") == op_id or (node_path and node_path[-1] == op_id)):
        proofs.append("EXACT_REGISTERED_OPERATION")
    method, route = trace.get("method"), trace.get("path")
    if method and route:
        node_route = node.get("path") if isinstance(node.get("path"), str) else node.get("route")
        node_method = node.get("method")
        methods = node.get("methods")
        if node_route == route and (node_method == method or (isinstance(methods, list) and method in methods)):
            proofs.append("EXACT_METHOD_AND_PATH")
        if node.get("method_effective_path") == f"{method} {route}":
            proofs.append("EXACT_METHOD_EFFECTIVE_PATH")
    return proofs


def search_bindings(scope: str, trace: dict, external_sources):
    sources = [("CURRENT_PAGE_AUTHORITY_EXACT_CAPTURE", RAW_PAGE[scope], load(RAW_PAGE[scope]))]
    sources.extend((f"CURRENT_EXTERNAL_AUTHORITY:{gap_uid}", path, doc) for gap_uid, path, doc in external_sources)
    matches, bindings = [], []
    for kind, path, doc in sources:
        for node_path, node in walk(doc):
            if not isinstance(node, dict):
                continue
            proofs = identity_match(node_path, node, trace)
            if not proofs:
                continue
            matches.append(evidence(path, node_path, "+".join(proofs), {"source_kind": kind}))
            for key, event_uid in event_uids(node):
                bindings.append({"event_uid": event_uid, "event_uid_key": key, "path": str(path.relative_to(ROOT)), "node_path": ".".join(node_path) if node_path else "$", "identity_proof": proofs, "source_kind": kind})
    return matches, bindings


def main() -> None:
    r12 = load(R12)
    candidates = [r for r in (r12.get("records") or []) if r.get("category") == "AUDIT_EVENT_NODE_MISSING"]
    if len(candidates) != 13:
        die(f"R13_REQUIRES_EXACT_13_AUDIT_EVENT_IDENTITIES:{len(candidates)}")
    if any(r.get("classification") != "UNRESOLVED_FUNCTIONAL_CONTRACT_GAP" for r in candidates):
        die("R13_REQUIRES_R12_UNRESOLVED_AUDIT_EVENT_BASELINE")

    external_sources, provenance = current_external_sources()
    rows, counts, scopes = [], Counter(), Counter()
    for source in candidates:
        scope, target = source["scope"], source["target_uid"]
        trace = action_trace(scope, target)
        matched, bindings = search_bindings(scope, trace, external_sources)
        events = sorted({x["event_uid"] for x in bindings})
        if len(events) == 1:
            cls, reason, candidate = "EXACT_EVENT_DEPENDENCY_FOUND", "UNIQUE_EVENT_UID_PHYSICALLY_BOUND_TO_EXACT_ACTION_PORT_OPERATION_IDENTITY_IN_CURRENT_ADMISSIBLE_SOURCE", True
        elif len(events) > 1:
            cls, reason, candidate = "CONFLICTING_EXACT_EVENT_DEPENDENCY", "MULTIPLE_EVENT_UIDS_PHYSICALLY_BOUND_TO_THE_SAME_EXACT_OPERATION_IDENTITY", False
        else:
            cls, reason, candidate = "CURRENT_FROZEN_EVENT_CONTRACT_MISSING", "NO_EVENT_UID_PHYSICALLY_BOUND_TO_EXACT_ACTION_PORT_OPERATION_IDENTITY_IN_CURRENT_PAGE_OR_CURRENT_ADMISSIBLE_EXTERNAL_AUTHORITY", False
        counts[cls] += 1
        scopes[scope] += 1
        rows.append({
            "blocker_uid": source["blocker_uid"], "scope": scope, "category": "AUDIT_EVENT_NODE_MISSING", "target_uid": target,
            "r12_identity_ref": source["blocker_uid"], "r12_classification_used_as_authority": False,
            "trace": trace, "current_identity_matches": matched, "exact_event_binding_evidence": bindings, "unique_exact_event_uids": events,
            "classification": cls, "classification_reason": reason,
            "semantic_event_name_inference_used": False, "event_uid_invention_used": False, "historical_non_current_authority_used": False,
            "materialization_candidate": candidate, "blocker_reduction_credit": 0,
            "next_action": "SEPARATE_BOUNDED_STAGE02_EVENT_BINDING_MATERIALIZATION_THEN_FRESH_REEXECUTION" if candidate else "KEEP_UNRESOLVED_AND_CONTINUE_CATEGORY_TRACE_WITHOUT_PRODUCT_AUTHORITY_PROMOTION",
        })
    if scopes != Counter({"ASSET-01": 9, "CORE-01": 4}):
        die(f"R13_SCOPE_DENOMINATOR_DRIFT:{dict(scopes)}")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    doc = {
        "schema_version": 1, "artifact_type": "NON_NORMATIVE_STAGE02_AUDIT_EVENT_DEPENDENCY_TRACE_R13", "normative_authority": False,
        "stage_uid": "STAGE-02", "cycle": "AUDIT_EVENT_EXACT_DEPENDENCY_TRACE_R13", "source_head_sha": head,
        "source_contracts": {
            "r12_identity_source": str(R12.relative_to(ROOT)), "r12_classification_accepted_as_authority": False,
            "functional_chain_sources": {k: str(v.relative_to(ROOT)) for k, v in FUNCTIONAL_CHAIN.items()},
            "current_page_authority_exact_captures": {k: str(v.relative_to(ROOT)) for k, v in RAW_PAGE.items()},
            "external_authority_materialization_evidence": str(EXT_EVIDENCE.relative_to(ROOT)), "current_admissible_external_sources": provenance,
        },
        "trace_contract": {
            "required_chain": "ACTION_UID -> EXACT_RUNTIME_PORT_UID -> EXACT_REGISTERED_OPERATION_OR_METHOD_PATH -> CURRENT_ADMISSIBLE_EXACT_IDENTITY_MATCH -> PHYSICAL_EVENT_UID",
            "registered_operation_and_method_effective_path_are_frozen_exact_port_identity": True,
            "operation_id_parse_is_syntactic_not_semantic": True, "semantic_similarity_may_supply_event_uid": False,
            "invented_event_uid_allowed": False, "classification_alone_may_reduce_blocker": False,
        },
        "denominators": {
            "audit_event_gaps_traced": 13, "scope_counts": dict(scopes),
            "exact_event_dependency_found": counts.get("EXACT_EVENT_DEPENDENCY_FOUND", 0),
            "conflicting_exact_event_dependency": counts.get("CONFLICTING_EXACT_EVENT_DEPENDENCY", 0),
            "current_frozen_event_contract_missing": counts.get("CURRENT_FROZEN_EVENT_CONTRACT_MISSING", 0),
            "effective_stage02_blocker_reduction_claimed": 0,
        },
        "records": rows, "stage02_status": "BLOCKED",
        "stage02_effective_blocker_count_before_any_materialization_and_fresh_reexecution": 150,
        "stage03_allowed": False, "website_construction_allowed": False, "deployment_allowed": False,
        "formal_next_execution_point": "MATERIALIZE_ONLY_EXACT_R13_EVENT_CANDIDATES_IF_ANY_OTHERWISE_CONTINUE_TO_NEXT_FUNCTIONAL_CONTRACT_CATEGORY",
    }
    OUT.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(f"PASS: R13 traced exact 13 audit-event gaps classifications={dict(counts)}")
    print("PASS: registered_operation/method_effective_path treated as exact frozen port identity; no semantic naming")
    print("PASS: no historical authority and no blocker reduction")


if __name__ == "__main__":
    main()
