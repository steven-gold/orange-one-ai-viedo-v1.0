#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
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
OUT = ROOT / "governance/test/stage02/STAGE02_PAYLOAD_DEPENDENCY_TRACE_R14.yaml"
FUNCTIONAL_CHAIN = {
    "CORE-01": STAGE2 / "CORE-01/FUNCTIONAL_CHAIN_SPEC.yaml",
    "ASSET-01": STAGE2 / "ASSET-01/FUNCTIONAL_CHAIN_SPEC.yaml",
}
RAW_PAGE = {
    "CORE-01": RAW / "CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml",
    "ASSET-01": RAW / "ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml",
}
STRUCTURED_SCHEMA_KEYS = {
    "payload_schema", "request_schema", "input_schema", "body_schema",
    "payload_fields", "request_fields", "input_fields", "required_fields",
    "payload_contract", "request_contract", "input_contract", "request_body_schema",
}
RULE_KEYS = {"payload_rule", "payload_mode"}


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


def exact_dicts(doc, key, value):
    return [(p, n) for p, n in walk(doc) if isinstance(n, dict) and n.get(key) == value]


def ev(path, node_path, proof, key=None, value=None, source_kind=None):
    item = {"path": str(path.relative_to(ROOT)), "node_path": ".".join(node_path) if node_path else "$", "proof": proof}
    if key is not None:
        item["key"] = key
    if value is not None:
        item["value"] = value
    if source_kind is not None:
        item["source_kind"] = source_kind
    return item


def stable(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


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


def first_unique(values, label, target):
    vals = sorted({v for v in values if isinstance(v, str) and v})
    if len(vals) > 1:
        die(f"R14_{label}_NOT_UNIQUE:{target}:{vals}")
    return vals[0] if vals else None


def normalize_materialized(raw_path):
    p = Path(raw_path)
    if p.parts and p.parts[0] == "04_PAGE_FUNCTIONAL_CONTRACT":
        return FRESH / p
    if str(p).startswith("00_SOURCE_INTAKE/fresh_run_003/"):
        return ROOT / p
    die(f"R14_UNSUPPORTED_MATERIALIZED_PATH:{raw_path}")


def current_external_sources():
    doc = load(EXT_EVIDENCE)
    sources, provenance = [], []
    for gap_uid, entry in (doc.get("materialized_authorities") or {}).items():
        if not isinstance(entry, dict) or entry.get("manifest_current") is not True:
            continue
        status = entry.get("authority_identity_status")
        if status not in {"EXACT_MATCH", "EXACT_CHAIN_LOCATED"}:
            die(f"R14_EXTERNAL_IDENTITY_NOT_EXACT:{gap_uid}:{status}")
        items = []
        if entry.get("materialized_path"):
            items.append(entry)
        items.extend(x for x in (entry.get("authority_chain") or []) if isinstance(x, dict) and x.get("materialized_path"))
        for item in items:
            path = normalize_materialized(item["materialized_path"])
            if not path.is_file():
                die(f"R14_EXTERNAL_SOURCE_MISSING:{path.relative_to(ROOT)}")
            expected = item.get("git_blob_sha")
            if expected:
                actual = subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()
                if actual != expected:
                    die(f"R14_EXTERNAL_BLOB_DRIFT:{path.relative_to(ROOT)}:{actual}:{expected}")
            sources.append((gap_uid, path, load(path)))
            provenance.append({"gap_uid": gap_uid, "path": str(path.relative_to(ROOT)), "manifest_current": True, "authority_identity_status": status, "git_blob_sha": expected})
    return sources, provenance


def action_trace(scope, target):
    chain_path = FUNCTIONAL_CHAIN[scope]
    chain = load(chain_path)
    actions = [(p, n) for p, n in exact_dicts(chain, "action_uid", target) if isinstance(n.get("runtime_binding"), dict)]
    if len(actions) != 1:
        die(f"R14_ACTION_NODE_NOT_UNIQUE:{target}:{len(actions)}")
    action_path, action = actions[0]
    rb = action["runtime_binding"]
    ports = sorted({rb.get(k) for k in ("port_uid", "persist_via_port_uid", "source_port_uid") if isinstance(rb.get(k), str) and rb.get(k)})
    if len(ports) != 1:
        die(f"R14_EXACT_SINGLE_PORT_REQUIRED:{target}:{ports}")
    port_uid = ports[0]
    keys = {"operation", "registered_operation", "operation_ref", "method_path", "method_effective_path", "state_event"}
    port_nodes = [(p, n) for p, n in exact_dicts(chain, "port_uid", port_uid) if any(n.get(k) for k in keys)]
    if not port_nodes:
        die(f"R14_PORT_CONTRACT_NODE_MISSING:{target}:{port_uid}")
    operation = first_unique((n.get("operation") for _, n in port_nodes), "OPERATION", target)
    registered = first_unique((n.get("registered_operation") for _, n in port_nodes), "REGISTERED_OPERATION", target)
    op_ref = first_unique((n.get("operation_ref") for _, n in port_nodes), "OPERATION_REF", target)
    method_path = first_unique((n.get("method_path") for _, n in port_nodes), "METHOD_PATH", target)
    effective_path = first_unique((n.get("method_effective_path") for _, n in port_nodes), "METHOD_EFFECTIVE_PATH", target)
    op_id = operation or registered or parse_operation_id_from_ref(op_ref)
    method, route = parse_method_path(method_path or effective_path or op_ref)
    if not op_id and not (method and route):
        die(f"R14_OPERATION_IDENTITY_MISSING:{target}:{port_uid}")
    frozen_rules = []
    for key in RULE_KEYS:
        value = rb.get(key)
        if value not in (None, "", [], {}):
            frozen_rules.append(ev(chain_path, action_path + ("runtime_binding",), "EXACT_FROZEN_ACTION_PAYLOAD_RULE", key, value, "FROZEN_FUNCTIONAL_CHAIN"))
    return {
        "action_uid": target,
        "port_uid": port_uid,
        "operation_id": op_id,
        "operation": operation,
        "registered_operation": registered,
        "operation_ref": op_ref,
        "method_path": method_path,
        "method_effective_path": effective_path,
        "method": method,
        "path": route,
        "frozen_payload_rules": frozen_rules,
    }


def identity_match(node_path, node, trace):
    proofs = []
    if node.get("action_uid") == trace["action_uid"]:
        proofs.append("EXACT_ACTION_UID")
    if node.get("port_uid") == trace["port_uid"]:
        proofs.append("EXACT_PORT_UID")
    op_id = trace.get("operation_id")
    if op_id and (node.get("operation") == op_id or node.get("registered_operation") == op_id or node.get("operation_id") == op_id or (node_path and node_path[-1] == op_id)):
        proofs.append("EXACT_OPERATION_ID")
    if trace.get("operation_ref") and node.get("operation_ref") == trace["operation_ref"]:
        proofs.append("EXACT_OPERATION_REF")
    method, route = trace.get("method"), trace.get("path")
    if method and route:
        exact = f"{method} {route}"
        if node.get("method_path") == exact:
            proofs.append("EXACT_METHOD_PATH")
        if node.get("method_effective_path") == exact:
            proofs.append("EXACT_METHOD_EFFECTIVE_PATH")
        node_route = node.get("path") if isinstance(node.get("path"), str) else node.get("route")
        node_method = node.get("method")
        methods = node.get("methods")
        if node_route == route and (node_method == method or (isinstance(methods, list) and method in methods)):
            proofs.append("EXACT_METHOD_AND_PATH")
    return proofs


def collect_keyed(node, keys, prefix=()):
    out = []
    if isinstance(node, dict):
        for key, value in node.items():
            path = prefix + (str(key),)
            if key in keys and value not in (None, "", [], {}):
                out.append((path, key, value))
            if isinstance(value, (dict, list)):
                out.extend(collect_keyed(value, keys, path))
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            out.extend(collect_keyed(value, keys, prefix + (str(idx),)))
    return out


def search_payload_evidence(scope, trace, external_sources):
    sources = [("CURRENT_PAGE_AUTHORITY_EXACT_CAPTURE", RAW_PAGE[scope], load(RAW_PAGE[scope]))]
    sources.extend((f"CURRENT_EXTERNAL_AUTHORITY:{gap}", path, doc) for gap, path, doc in external_sources)
    identity_matches, schemas, rules = [], [], list(trace["frozen_payload_rules"])
    for kind, path, doc in sources:
        for node_path, node in walk(doc):
            if not isinstance(node, dict):
                continue
            proofs = identity_match(node_path, node, trace)
            if not proofs:
                continue
            identity_matches.append(ev(path, node_path, "+".join(proofs), source_kind=kind))
            for key_path, key, value in collect_keyed(node, STRUCTURED_SCHEMA_KEYS):
                schemas.append(ev(path, node_path + key_path, "+".join(proofs) + "+STRUCTURED_PAYLOAD_CONTRACT", key, value, kind))
            for key_path, key, value in collect_keyed(node, RULE_KEYS):
                rules.append(ev(path, node_path + key_path, "+".join(proofs) + "+FROZEN_PAYLOAD_RULE", key, value, kind))
    return identity_matches, schemas, rules


def main():
    r12 = load(R12)
    candidates = [r for r in (r12.get("records") or []) if r.get("category") == "PAYLOAD_INPUT_CONTRACT_MISSING"]
    if len(candidates) != 34:
        die(f"R14_REQUIRES_EXACT_34_PAYLOAD_IDENTITIES:{len(candidates)}")
    if Counter(r.get("scope") for r in candidates) != Counter({"ASSET-01": 18, "CORE-01": 16}):
        die("R14_SCOPE_BASELINE_DRIFT")
    external_sources, provenance = current_external_sources()
    rows, counts = [], Counter()
    for source in candidates:
        trace = action_trace(source["scope"], source["target_uid"])
        identity_matches, schemas, rules = search_payload_evidence(source["scope"], trace, external_sources)
        unique_schemas = {stable(x.get("value")) for x in schemas}
        if len(unique_schemas) == 1:
            cls, candidate = "EXACT_STRUCTURED_PAYLOAD_SCHEMA_FOUND", True
        elif len(unique_schemas) > 1:
            cls, candidate = "CONFLICTING_STRUCTURED_PAYLOAD_SCHEMAS", False
        elif rules:
            cls, candidate = "FROZEN_PAYLOAD_RULE_ONLY", False
        else:
            cls, candidate = "CURRENT_FROZEN_PAYLOAD_CONTRACT_MISSING", False
        counts[cls] += 1
        rows.append({
            "blocker_uid": source["blocker_uid"], "scope": source["scope"], "category": "PAYLOAD_INPUT_CONTRACT_MISSING", "target_uid": source["target_uid"],
            "r12_identity_ref": source["blocker_uid"], "r12_classification_used_as_authority": False,
            "trace": trace, "current_identity_matches": identity_matches,
            "structured_payload_schema_evidence": schemas, "frozen_payload_rule_evidence": rules,
            "unique_structured_schema_count": len(unique_schemas), "classification": cls,
            "materialization_candidate": candidate, "semantic_field_inference_used": False, "invented_payload_field_used": False,
            "historical_non_current_authority_used": False, "blocker_reduction_credit": 0,
            "next_action": "SEPARATE_BOUNDED_STAGE02_PAYLOAD_MATERIALIZATION_THEN_FRESH_REEXECUTION" if candidate else "KEEP_UNRESOLVED_UNTIL_EXACT_STRUCTURED_PAYLOAD_CONTRACT_IS_PROVEN",
        })
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    doc = {
        "schema_version": 1,
        "artifact_type": "NON_NORMATIVE_STAGE02_PAYLOAD_DEPENDENCY_TRACE_R14",
        "normative_authority": False,
        "stage_uid": "STAGE-02",
        "cycle": "PAYLOAD_INPUT_EXACT_DEPENDENCY_TRACE_R14",
        "source_head_sha": head,
        "source_contracts": {
            "r12_identity_source": str(R12.relative_to(ROOT)),
            "r12_classification_accepted_as_authority": False,
            "functional_chain_sources": {k: str(v.relative_to(ROOT)) for k, v in FUNCTIONAL_CHAIN.items()},
            "current_page_authority_exact_captures": {k: str(v.relative_to(ROOT)) for k, v in RAW_PAGE.items()},
            "external_authority_materialization_evidence": str(EXT_EVIDENCE.relative_to(ROOT)),
            "current_admissible_external_sources": provenance,
        },
        "trace_contract": {
            "structured_schema_keys": sorted(STRUCTURED_SCHEMA_KEYS),
            "frozen_rule_keys": sorted(RULE_KEYS),
            "payload_rule_is_structured_schema": False,
            "semantic_field_inference_allowed": False,
            "invented_payload_fields_allowed": False,
            "classification_alone_may_reduce_blocker": False,
        },
        "denominators": {
            "payload_input_gaps_traced": 34,
            "scope_counts": {"ASSET-01": 18, "CORE-01": 16},
            "exact_structured_payload_schema_found": counts["EXACT_STRUCTURED_PAYLOAD_SCHEMA_FOUND"],
            "conflicting_structured_payload_schemas": counts["CONFLICTING_STRUCTURED_PAYLOAD_SCHEMAS"],
            "frozen_payload_rule_only": counts["FROZEN_PAYLOAD_RULE_ONLY"],
            "current_frozen_payload_contract_missing": counts["CURRENT_FROZEN_PAYLOAD_CONTRACT_MISSING"],
            "effective_stage02_blocker_reduction_claimed": 0,
        },
        "records": rows,
        "stage02_status": "BLOCKED",
        "stage02_effective_blocker_count_before_any_materialization_and_fresh_reexecution": 150,
        "stage03_allowed": False,
        "website_construction_allowed": False,
        "deployment_allowed": False,
        "formal_next_execution_point": "MATERIALIZE_ONLY_EXACT_STRUCTURED_R14_CANDIDATES_IF_ANY_OTHERWISE_CONTINUE_TO_NEXT_FUNCTIONAL_CONTRACT_CATEGORY",
    }
    OUT.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(f"PASS: R14 traced exact 34 payload/input gaps classifications={dict(counts)}")
    print("PASS: frozen payload_rule is recorded separately and never promoted to structured schema")
    print("PASS: no semantic field inference, no historical authority, no blocker reduction")


if __name__ == "__main__":
    main()
