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
OUT = ROOT / "governance/test/stage02/STAGE02_POST_ACTION_VALIDATION_DEPENDENCY_TRACE_R15.yaml"
CHAIN = STAGE2 / "ASSET-01/FUNCTIONAL_CHAIN_SPEC.yaml"
RAW_PAGE = RAW / "ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml"

CONTRACT_KEYS = {
    "success_contract",
    "validation_contract",
    "evaluation_contract",
    "post_action_validation",
    "post_action_validation_contract",
    "postcondition",
    "postconditions",
    "success_criteria",
    "acceptance_criteria",
    "validation_rule",
    "result_validation",
    "output_validation",
    "completion_criteria",
}
SIGNAL_KEYS = {
    "result",
    "state_event",
    "state_effect",
    "result_state",
    "completion_state",
}


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
    item = {
        "path": str(path.relative_to(ROOT)),
        "node_path": ".".join(node_path) if node_path else "$",
        "proof": proof,
    }
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
        die(f"R15_{label}_NOT_UNIQUE:{target}:{vals}")
    return vals[0] if vals else None


def normalize_materialized(raw_path):
    p = Path(raw_path)
    if p.parts and p.parts[0] == "04_PAGE_FUNCTIONAL_CONTRACT":
        return FRESH / p
    if str(p).startswith("00_SOURCE_INTAKE/fresh_run_003/"):
        return ROOT / p
    die(f"R15_UNSUPPORTED_MATERIALIZED_PATH:{raw_path}")


def current_external_sources():
    doc = load(EXT_EVIDENCE)
    sources, provenance = [], []
    for gap_uid, entry in (doc.get("materialized_authorities") or {}).items():
        if not isinstance(entry, dict) or entry.get("manifest_current") is not True:
            continue
        status = entry.get("authority_identity_status")
        if status not in {"EXACT_MATCH", "EXACT_CHAIN_LOCATED"}:
            die(f"R15_EXTERNAL_IDENTITY_NOT_EXACT:{gap_uid}:{status}")
        items = []
        if entry.get("materialized_path"):
            items.append(entry)
        items.extend(x for x in (entry.get("authority_chain") or []) if isinstance(x, dict) and x.get("materialized_path"))
        for item in items:
            path = normalize_materialized(item["materialized_path"])
            if not path.is_file():
                die(f"R15_EXTERNAL_SOURCE_MISSING:{path.relative_to(ROOT)}")
            expected = item.get("git_blob_sha")
            if expected:
                actual = subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()
                if actual != expected:
                    die(f"R15_EXTERNAL_BLOB_DRIFT:{path.relative_to(ROOT)}:{actual}:{expected}")
            sources.append((gap_uid, path, load(path)))
            provenance.append({
                "gap_uid": gap_uid,
                "path": str(path.relative_to(ROOT)),
                "manifest_current": True,
                "authority_identity_status": status,
                "git_blob_sha": expected,
            })
    return sources, provenance


def action_trace(target):
    chain = load(CHAIN)
    actions = [(p, n) for p, n in exact_dicts(chain, "action_uid", target) if isinstance(n.get("runtime_binding"), dict)]
    if len(actions) != 1:
        die(f"R15_ACTION_NODE_NOT_UNIQUE:{target}:{len(actions)}")
    action_path, action = actions[0]
    rb = action["runtime_binding"]
    ports = sorted({rb.get(k) for k in ("port_uid", "persist_via_port_uid", "source_port_uid") if isinstance(rb.get(k), str) and rb.get(k)})
    if len(ports) != 1:
        die(f"R15_EXACT_SINGLE_PORT_REQUIRED:{target}:{ports}")
    port_uid = ports[0]
    keys = {"operation", "registered_operation", "operation_ref", "method_path", "method_effective_path", "state_event"}
    port_nodes = [(p, n) for p, n in exact_dicts(chain, "port_uid", port_uid) if any(n.get(k) for k in keys)]
    if not port_nodes:
        die(f"R15_PORT_CONTRACT_NODE_MISSING:{target}:{port_uid}")

    operation = first_unique((n.get("operation") for _, n in port_nodes), "OPERATION", target)
    registered = first_unique((n.get("registered_operation") for _, n in port_nodes), "REGISTERED_OPERATION", target)
    op_ref = first_unique((n.get("operation_ref") for _, n in port_nodes), "OPERATION_REF", target)
    method_path = first_unique((n.get("method_path") for _, n in port_nodes), "METHOD_PATH", target)
    effective_path = first_unique((n.get("method_effective_path") for _, n in port_nodes), "METHOD_EFFECTIVE_PATH", target)
    state_event = first_unique((n.get("state_event") for _, n in port_nodes), "STATE_EVENT", target)
    op_id = operation or registered or parse_operation_id_from_ref(op_ref)
    method, route = parse_method_path(method_path or effective_path or op_ref)
    if not op_id and not (method and route):
        die(f"R15_OPERATION_IDENTITY_MISSING:{target}:{port_uid}")

    local_contracts, local_signals = [], []
    for key, value in action.items():
        if key in CONTRACT_KEYS and value not in (None, "", [], {}):
            local_contracts.append(ev(CHAIN, action_path, "EXACT_FROZEN_ACTION_VALIDATION_CONTRACT", key, value, "FROZEN_FUNCTIONAL_CHAIN"))
    for key, value in rb.items():
        if key in CONTRACT_KEYS and value not in (None, "", [], {}):
            local_contracts.append(ev(CHAIN, action_path + ("runtime_binding",), "EXACT_FROZEN_RUNTIME_VALIDATION_CONTRACT", key, value, "FROZEN_FUNCTIONAL_CHAIN"))
        if key in SIGNAL_KEYS and value not in (None, "", [], {}):
            local_signals.append(ev(CHAIN, action_path + ("runtime_binding",), "EXACT_FROZEN_RUNTIME_RESULT_SIGNAL", key, value, "FROZEN_FUNCTIONAL_CHAIN"))
    if state_event:
        for p, n in port_nodes:
            if n.get("state_event") == state_event:
                local_signals.append(ev(CHAIN, p, "EXACT_FROZEN_PORT_STATE_SIGNAL", "state_event", state_event, "FROZEN_FUNCTIONAL_CHAIN"))

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
        "state_event": state_event,
        "frozen_validation_contracts": local_contracts,
        "frozen_result_signals": local_signals,
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


def search_validation_evidence(trace, external_sources):
    sources = [("CURRENT_PAGE_AUTHORITY_EXACT_CAPTURE", RAW_PAGE, load(RAW_PAGE))]
    sources.extend((f"CURRENT_EXTERNAL_AUTHORITY:{gap}", path, doc) for gap, path, doc in external_sources)
    identity_matches = []
    contracts = list(trace["frozen_validation_contracts"])
    signals = list(trace["frozen_result_signals"])
    for kind, path, doc in sources:
        for node_path, node in walk(doc):
            if not isinstance(node, dict):
                continue
            proofs = identity_match(node_path, node, trace)
            if not proofs:
                continue
            identity_matches.append(ev(path, node_path, "+".join(proofs), source_kind=kind))
            for key_path, key, value in collect_keyed(node, CONTRACT_KEYS):
                contracts.append(ev(path, node_path + key_path, "+".join(proofs) + "+EXPLICIT_POST_ACTION_VALIDATION_CONTRACT", key, value, kind))
            for key_path, key, value in collect_keyed(node, SIGNAL_KEYS):
                signals.append(ev(path, node_path + key_path, "+".join(proofs) + "+RESULT_OR_STATE_SIGNAL", key, value, kind))
    return identity_matches, contracts, signals


def main():
    r12 = load(R12)
    candidates = [r for r in (r12.get("records") or []) if r.get("category") == "POST_ACTION_VALIDATION_NODE_MISSING"]
    if len(candidates) != 18:
        die(f"R15_REQUIRES_EXACT_18_VALIDATION_IDENTITIES:{len(candidates)}")
    if Counter(r.get("scope") for r in candidates) != Counter({"ASSET-01": 18}):
        die("R15_SCOPE_BASELINE_DRIFT")
    if any(r.get("classification") != "UNRESOLVED_FUNCTIONAL_CONTRACT_GAP" for r in candidates):
        die("R15_REQUIRES_R12_UNRESOLVED_BASELINE")

    external_sources, provenance = current_external_sources()
    rows, counts = [], Counter()
    for source in candidates:
        trace = action_trace(source["target_uid"])
        matches, contracts, signals = search_validation_evidence(trace, external_sources)
        unique_contracts = {stable(x.get("value")) for x in contracts}
        if len(unique_contracts) == 1:
            cls, candidate = "EXACT_POST_ACTION_VALIDATION_CONTRACT_FOUND", True
        elif len(unique_contracts) > 1:
            cls, candidate = "CONFLICTING_POST_ACTION_VALIDATION_CONTRACTS", False
        elif signals:
            cls, candidate = "FROZEN_RESULT_OR_STATE_SIGNAL_ONLY", False
        else:
            cls, candidate = "CURRENT_FROZEN_POST_ACTION_VALIDATION_CONTRACT_MISSING", False
        counts[cls] += 1
        rows.append({
            "blocker_uid": source["blocker_uid"],
            "scope": source["scope"],
            "category": "POST_ACTION_VALIDATION_NODE_MISSING",
            "target_uid": source["target_uid"],
            "r12_identity_ref": source["blocker_uid"],
            "r12_classification_used_as_authority": False,
            "trace": trace,
            "current_identity_matches": matches,
            "post_action_validation_contract_evidence": contracts,
            "result_or_state_signal_evidence": signals,
            "unique_validation_contract_count": len(unique_contracts),
            "classification": cls,
            "materialization_candidate": candidate,
            "semantic_validation_inference_used": False,
            "invented_validation_rule_used": False,
            "historical_non_current_authority_used": False,
            "blocker_reduction_credit": 0,
            "next_action": "SEPARATE_BOUNDED_STAGE02_POST_ACTION_VALIDATION_MATERIALIZATION_THEN_FRESH_REEXECUTION" if candidate else "KEEP_UNRESOLVED_UNTIL_EXACT_POST_ACTION_VALIDATION_CONTRACT_IS_PROVEN",
        })

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    doc = {
        "schema_version": 1,
        "artifact_type": "NON_NORMATIVE_STAGE02_POST_ACTION_VALIDATION_DEPENDENCY_TRACE_R15",
        "normative_authority": False,
        "stage_uid": "STAGE-02",
        "cycle": "POST_ACTION_VALIDATION_EXACT_DEPENDENCY_TRACE_R15",
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
            "explicit_validation_contract_keys": sorted(CONTRACT_KEYS),
            "result_or_state_signal_keys": sorted(SIGNAL_KEYS),
            "result_or_state_signal_is_validation_contract": False,
            "precondition_gate_is_post_action_validation": False,
            "semantic_validation_inference_allowed": False,
            "invented_validation_rule_allowed": False,
            "classification_alone_may_reduce_blocker": False,
        },
        "denominators": {
            "post_action_validation_gaps_traced": 18,
            "scope_counts": {"ASSET-01": 18},
            "exact_post_action_validation_contract_found": counts["EXACT_POST_ACTION_VALIDATION_CONTRACT_FOUND"],
            "conflicting_post_action_validation_contracts": counts["CONFLICTING_POST_ACTION_VALIDATION_CONTRACTS"],
            "frozen_result_or_state_signal_only": counts["FROZEN_RESULT_OR_STATE_SIGNAL_ONLY"],
            "current_frozen_post_action_validation_contract_missing": counts["CURRENT_FROZEN_POST_ACTION_VALIDATION_CONTRACT_MISSING"],
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
    print(f"PASS: R15 traced 18 post-action validation gaps classifications={dict(counts)}")
    print("PASS: result/state signals preserved as evidence but not promoted to validation contracts")
    print("PASS: zero blocker reduction until separate bounded materialization and fresh reexecution")


if __name__ == "__main__":
    main()
