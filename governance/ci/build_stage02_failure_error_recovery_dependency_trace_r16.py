#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
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
OUT = ROOT / "governance/test/stage02/STAGE02_FAILURE_ERROR_RECOVERY_DEPENDENCY_TRACE_R16.yaml"
CHAIN = STAGE2 / "ASSET-01/FUNCTIONAL_CHAIN_SPEC.yaml"
RAW_PAGE = RAW / "ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml"

BINDING_KEYS = {
    "error_uid", "error_code", "error_codes", "error_contract",
    "failure_contract", "failure_state", "error_state",
    "recovery_contract", "recovery_action_uid", "recovery_action", "recovery_state",
    "retry_contract", "retry_policy", "on_error", "on_failure",
    "failure_transition", "recovery_transition", "dead_letter_policy",
}
SIGNAL_KEYS = {"state_event", "state_effect", "result"}


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


def stable(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def ev(path, node_path, proof, key=None, value=None, source_kind=None):
    item = {"path": str(path.relative_to(ROOT)), "node_path": ".".join(node_path) if node_path else "$", "proof": proof}
    if key is not None:
        item["key"] = key
    if value is not None:
        item["value"] = value
    if source_kind is not None:
        item["source_kind"] = source_kind
    return item


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
        die(f"R16_{label}_NOT_UNIQUE:{target}:{vals}")
    return vals[0] if vals else None


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


def normalize_materialized(raw_path):
    p = Path(raw_path)
    if p.parts and p.parts[0] == "04_PAGE_FUNCTIONAL_CONTRACT":
        return FRESH / p
    if str(p).startswith("00_SOURCE_INTAKE/fresh_run_003/"):
        return ROOT / p
    die(f"R16_UNSUPPORTED_MATERIALIZED_PATH:{raw_path}")


def current_external_sources():
    doc = load(EXT_EVIDENCE)
    sources, provenance = [], []
    for gap_uid, entry in (doc.get("materialized_authorities") or {}).items():
        if not isinstance(entry, dict) or entry.get("manifest_current") is not True:
            continue
        status = entry.get("authority_identity_status")
        if status not in {"EXACT_MATCH", "EXACT_CHAIN_LOCATED"}:
            die(f"R16_EXTERNAL_IDENTITY_NOT_EXACT:{gap_uid}:{status}")
        items = []
        if entry.get("materialized_path"):
            items.append(entry)
        items.extend(x for x in (entry.get("authority_chain") or []) if isinstance(x, dict) and x.get("materialized_path"))
        for item in items:
            path = normalize_materialized(item["materialized_path"])
            if not path.is_file():
                die(f"R16_EXTERNAL_SOURCE_MISSING:{path.relative_to(ROOT)}")
            expected = item.get("git_blob_sha")
            if expected:
                actual = subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()
                if actual != expected:
                    die(f"R16_EXTERNAL_BLOB_DRIFT:{path.relative_to(ROOT)}:{actual}:{expected}")
            sources.append((gap_uid, path, load(path)))
            provenance.append({"gap_uid": gap_uid, "path": str(path.relative_to(ROOT)), "manifest_current": True, "authority_identity_status": status, "git_blob_sha": expected})
    return sources, provenance


def action_trace(target):
    chain = load(CHAIN)
    actions = [(p, n) for p, n in exact_dicts(chain, "action_uid", target) if isinstance(n.get("runtime_binding"), dict)]
    if len(actions) != 1:
        die(f"R16_ACTION_NODE_NOT_UNIQUE:{target}:{len(actions)}")
    action_path, action = actions[0]
    rb = action["runtime_binding"]
    ports = sorted({rb.get(k) for k in ("port_uid", "persist_via_port_uid", "source_port_uid") if isinstance(rb.get(k), str) and rb.get(k)})
    if len(ports) > 1:
        die(f"R16_PORT_NOT_UNIQUE:{target}:{ports}")
    port_uid = ports[0] if ports else None
    shared_operation_id = rb.get("shared_operation_id") if isinstance(rb.get("shared_operation_id"), str) and rb.get("shared_operation_id") else None

    port_nodes = []
    if port_uid:
        keys = {"operation", "registered_operation", "operation_ref", "method_path", "method_effective_path", "state_event"}
        port_nodes = [(p, n) for p, n in exact_dicts(chain, "port_uid", port_uid) if any(n.get(k) for k in keys)]
        if not port_nodes:
            die(f"R16_PORT_CONTRACT_NODE_MISSING:{target}:{port_uid}")

    operation = first_unique((n.get("operation") for _, n in port_nodes), "OPERATION", target)
    registered = first_unique((n.get("registered_operation") for _, n in port_nodes), "REGISTERED_OPERATION", target)
    op_ref = first_unique((n.get("operation_ref") for _, n in port_nodes), "OPERATION_REF", target)
    method_path = first_unique((n.get("method_path") for _, n in port_nodes), "METHOD_PATH", target)
    effective_path = first_unique((n.get("method_effective_path") for _, n in port_nodes), "METHOD_EFFECTIVE_PATH", target)
    op_id = operation or registered or parse_operation_id_from_ref(op_ref) or shared_operation_id
    method, route = parse_method_path(method_path or effective_path or op_ref)

    local_bindings, local_signals = [], []
    for rel, key, value in collect_keyed(action, BINDING_KEYS):
        local_bindings.append(ev(CHAIN, action_path + rel, "EXACT_FROZEN_ACTION_FAILURE_ERROR_RECOVERY_BINDING", key, value, "FROZEN_FUNCTIONAL_CHAIN"))
    for rel, key, value in collect_keyed(action, SIGNAL_KEYS):
        local_signals.append(ev(CHAIN, action_path + rel, "EXACT_FROZEN_ACTION_RESULT_OR_STATE_SIGNAL", key, value, "FROZEN_FUNCTIONAL_CHAIN"))
    for p, node in port_nodes:
        for rel, key, value in collect_keyed(node, BINDING_KEYS):
            local_bindings.append(ev(CHAIN, p + rel, "EXACT_FROZEN_PORT_FAILURE_ERROR_RECOVERY_BINDING", key, value, "FROZEN_FUNCTIONAL_CHAIN"))
        for rel, key, value in collect_keyed(node, SIGNAL_KEYS):
            local_signals.append(ev(CHAIN, p + rel, "EXACT_FROZEN_PORT_RESULT_OR_STATE_SIGNAL", key, value, "FROZEN_FUNCTIONAL_CHAIN"))

    identity_kind = "ACTION_ONLY_NO_RUNTIME_API"
    if shared_operation_id and not port_uid:
        identity_kind = "ACTION_TO_SHARED_OPERATION"
    elif port_uid:
        identity_kind = "ACTION_TO_PORT_OPERATION"

    return {
        "action_uid": target,
        "identity_kind": identity_kind,
        "port_uid": port_uid,
        "shared_operation_id": shared_operation_id,
        "operation_id": op_id,
        "operation": operation,
        "registered_operation": registered,
        "operation_ref": op_ref,
        "method_path": method_path,
        "method_effective_path": effective_path,
        "method": method,
        "path": route,
        "frozen_failure_error_recovery_bindings": local_bindings,
        "frozen_result_or_state_signals": local_signals,
    }


def identity_match(node_path, node, trace):
    proofs = []
    if node.get("action_uid") == trace["action_uid"]:
        proofs.append("EXACT_ACTION_UID")
    if trace.get("port_uid") and node.get("port_uid") == trace["port_uid"]:
        proofs.append("EXACT_PORT_UID")
    op_id = trace.get("operation_id")
    if op_id and (
        node.get("operation") == op_id or node.get("registered_operation") == op_id or node.get("operation_id") == op_id
        or node.get("shared_operation_id") == op_id or (node_path and node_path[-1] == op_id)
    ):
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


def search_binding_evidence(trace, external_sources):
    sources = [("CURRENT_PAGE_AUTHORITY_EXACT_CAPTURE", RAW_PAGE, load(RAW_PAGE))]
    sources.extend((f"CURRENT_EXTERNAL_AUTHORITY:{gap}", path, doc) for gap, path, doc in external_sources)
    matches = []
    bindings = list(trace["frozen_failure_error_recovery_bindings"])
    signals = list(trace["frozen_result_or_state_signals"])
    for kind, path, doc in sources:
        for node_path, node in walk(doc):
            if not isinstance(node, dict):
                continue
            proofs = identity_match(node_path, node, trace)
            if not proofs:
                continue
            matches.append(ev(path, node_path, "+".join(proofs), source_kind=kind))
            for rel, key, value in collect_keyed(node, BINDING_KEYS):
                bindings.append(ev(path, node_path + rel, "+".join(proofs) + "+FAILURE_ERROR_RECOVERY_BINDING", key, value, kind))
            for rel, key, value in collect_keyed(node, SIGNAL_KEYS):
                signals.append(ev(path, node_path + rel, "+".join(proofs) + "+RESULT_OR_STATE_SIGNAL", key, value, kind))
    return matches, bindings, signals


def binding_conflicts(bindings):
    by_key = defaultdict(set)
    for item in bindings:
        by_key[item.get("key")].add(stable(item.get("value")))
    return {key: len(values) for key, values in by_key.items()}, sorted(key for key, values in by_key.items() if len(values) > 1)


def main():
    r12 = load(R12)
    candidates = [r for r in (r12.get("records") or []) if r.get("category") == "FAILURE_STATE_ERROR_BINDING_MISSING"]
    if len(candidates) != 44:
        die(f"R16_REQUIRES_EXACT_44_FAILURE_IDENTITIES:{len(candidates)}")
    if Counter(r.get("scope") for r in candidates) != Counter({"ASSET-01": 44}):
        die("R16_SCOPE_BASELINE_DRIFT")
    if any(r.get("classification") != "UNRESOLVED_FUNCTIONAL_CONTRACT_GAP" for r in candidates):
        die("R16_REQUIRES_R12_UNRESOLVED_BASELINE")

    external_sources, provenance = current_external_sources()
    rows, counts = [], Counter()
    identity_kinds = Counter()
    for source in candidates:
        trace = action_trace(source["target_uid"])
        identity_kinds[trace["identity_kind"]] += 1
        matches, bindings, signals = search_binding_evidence(trace, external_sources)
        key_counts, conflicting_keys = binding_conflicts(bindings)
        if conflicting_keys:
            cls, candidate = "CONFLICTING_FAILURE_ERROR_RECOVERY_BINDINGS", False
        elif bindings:
            cls, candidate = "EXACT_FAILURE_ERROR_RECOVERY_BINDING_FOUND", True
        elif signals:
            cls, candidate = "FROZEN_RESULT_OR_STATE_SIGNAL_ONLY", False
        else:
            cls, candidate = "CURRENT_FROZEN_FAILURE_ERROR_RECOVERY_BINDING_MISSING", False
        counts[cls] += 1
        rows.append({
            "blocker_uid": source["blocker_uid"],
            "scope": source["scope"],
            "category": "FAILURE_STATE_ERROR_BINDING_MISSING",
            "target_uid": source["target_uid"],
            "r12_identity_ref": source["blocker_uid"],
            "r12_classification_used_as_authority": False,
            "trace": trace,
            "current_identity_matches": matches,
            "failure_error_recovery_binding_evidence": bindings,
            "result_or_state_signal_evidence": signals,
            "binding_key_value_counts": key_counts,
            "conflicting_binding_keys": conflicting_keys,
            "classification": cls,
            "materialization_candidate": candidate,
            "semantic_error_or_recovery_inference_used": False,
            "invented_error_or_recovery_binding_used": False,
            "historical_non_current_authority_used": False,
            "blocker_reduction_credit": 0,
            "next_action": "SEPARATE_BOUNDED_STAGE02_FAILURE_ERROR_RECOVERY_MATERIALIZATION_THEN_FRESH_REEXECUTION" if candidate else "KEEP_UNRESOLVED_UNTIL_EXACT_FAILURE_ERROR_RECOVERY_BINDING_IS_PROVEN",
        })

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    doc = {
        "schema_version": 1,
        "artifact_type": "NON_NORMATIVE_STAGE02_FAILURE_ERROR_RECOVERY_DEPENDENCY_TRACE_R16",
        "normative_authority": False,
        "stage_uid": "STAGE-02",
        "cycle": "FAILURE_ERROR_RECOVERY_EXACT_DEPENDENCY_TRACE_R16",
        "source_head_sha": head,
        "source_contracts": {
            "r12_identity_source": str(R12.relative_to(ROOT)),
            "r12_classification_accepted_as_authority": False,
            "functional_chain_source": str(CHAIN.relative_to(ROOT)),
            "current_page_authority_exact_capture": str(RAW_PAGE.relative_to(ROOT)),
            "external_authority_materialization_evidence": str(EXT_EVIDENCE.relative_to(ROOT)),
            "current_admissible_external_sources": provenance,
        },
        "trace_contract": {
            "explicit_failure_error_recovery_binding_keys": sorted(BINDING_KEYS),
            "result_or_state_signal_keys": sorted(SIGNAL_KEYS),
            "supported_identity_shapes": ["ACTION_ONLY_NO_RUNTIME_API", "ACTION_TO_PORT_OPERATION", "ACTION_TO_SHARED_OPERATION"],
            "result_or_state_signal_is_error_or_recovery_binding": False,
            "semantic_error_or_recovery_inference_allowed": False,
            "invented_error_or_recovery_binding_allowed": False,
            "classification_alone_may_reduce_blocker": False,
        },
        "denominators": {
            "failure_error_recovery_gaps_traced": 44,
            "scope_counts": {"ASSET-01": 44},
            "identity_shape_counts": dict(identity_kinds),
            "exact_failure_error_recovery_binding_found": counts["EXACT_FAILURE_ERROR_RECOVERY_BINDING_FOUND"],
            "conflicting_failure_error_recovery_bindings": counts["CONFLICTING_FAILURE_ERROR_RECOVERY_BINDINGS"],
            "frozen_result_or_state_signal_only": counts["FROZEN_RESULT_OR_STATE_SIGNAL_ONLY"],
            "current_frozen_failure_error_recovery_binding_missing": counts["CURRENT_FROZEN_FAILURE_ERROR_RECOVERY_BINDING_MISSING"],
            "effective_stage02_blocker_reduction_claimed": 0,
        },
        "records": rows,
        "stage02_status": "BLOCKED",
        "stage02_effective_blocker_count_before_any_materialization_and_fresh_reexecution": 150,
        "stage03_allowed": False,
        "website_construction_allowed": False,
        "deployment_allowed": False,
    }
    OUT.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"PASS: R16 traced 44 failure/error/recovery gaps classifications={dict(counts)} identity_shapes={dict(identity_kinds)}")
    print("PASS: action-only, port/operation, and shared-operation frozen identities are handled without semantic inference")
    print("PASS: zero blocker reduction until separate bounded materialization and fresh reexecution")


if __name__ == "__main__":
    main()
