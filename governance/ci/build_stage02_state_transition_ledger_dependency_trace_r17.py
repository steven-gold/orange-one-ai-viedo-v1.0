#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
FRESH = ROOT / "00_SOURCE_INTAKE/fresh_run_003"
STAGE2 = FRESH / "04_PAGE_FUNCTIONAL_CONTRACT"
RAW = FRESH / "00_SOURCE_INTAKE/RAW_SOURCE"
R12 = ROOT / "governance/test/stage02/STAGE02_AUTHORITY_DEPENDENCY_RECLASSIFICATION_R12.yaml"
EXT_EVIDENCE = STAGE2 / "EXTERNAL_AUTHORITY/STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE.yaml"
OUT = ROOT / "governance/test/stage02/STAGE02_STATE_TRANSITION_LEDGER_DEPENDENCY_TRACE_R17.yaml"
CHAIN = {
    "CORE-01": STAGE2 / "CORE-01/FUNCTIONAL_CHAIN_SPEC.yaml",
    "ASSET-01": STAGE2 / "ASSET-01/FUNCTIONAL_CHAIN_SPEC.yaml",
}
RAW_PAGE = {
    "CORE-01": RAW / "CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml",
    "ASSET-01": RAW / "ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml",
}
REQUIRED_FIELDS = {"mutation_owner", "failure_state", "recovery", "audit_event_uid"}
RELATED_SIGNAL_KEYS = {
    "from_stage", "to_stage", "trigger", "trigger_event_uid", "gate", "gate_uid",
    "state_event", "state_effect", "error_uid", "owner",
}


def die(msg: str) -> None:
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def walk(obj, path=()):
    if isinstance(obj, dict):
        yield path, obj
        for key, value in obj.items():
            yield from walk(value, path + (str(key),))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from walk(value, path + (str(idx),))


def exact_nodes(doc, key, value):
    return [(p, n) for p, n in walk(doc) if isinstance(n, dict) and n.get(key) == value]


def stable(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, default=str)


def ev(path: Path, node_path, proof, key=None, value=None, source_kind=None):
    item = {"path": str(path.relative_to(ROOT)), "node_path": ".".join(node_path) if node_path else "$", "proof": proof}
    if key is not None:
        item["key"] = key
    if value is not None:
        item["value"] = value
    if source_kind is not None:
        item["source_kind"] = source_kind
    return item


def normalize_materialized(raw_path: str) -> Path:
    p = Path(raw_path)
    if p.parts and p.parts[0] == "04_PAGE_FUNCTIONAL_CONTRACT":
        return FRESH / p
    if str(p).startswith("00_SOURCE_INTAKE/fresh_run_003/"):
        return ROOT / p
    die(f"R17_UNSUPPORTED_MATERIALIZED_PATH:{raw_path}")


def current_external_sources():
    doc = load(EXT_EVIDENCE)
    sources, provenance = [], []
    for gap_uid, entry in (doc.get("materialized_authorities") or {}).items():
        if not isinstance(entry, dict) or entry.get("manifest_current") is not True:
            continue
        status = entry.get("authority_identity_status")
        if status not in {"EXACT_MATCH", "EXACT_CHAIN_LOCATED"}:
            die(f"R17_EXTERNAL_IDENTITY_NOT_EXACT:{gap_uid}:{status}")
        items = []
        if entry.get("materialized_path"):
            items.append(entry)
        items.extend(x for x in (entry.get("authority_chain") or []) if isinstance(x, dict) and x.get("materialized_path"))
        for item in items:
            path = normalize_materialized(item["materialized_path"])
            if not path.is_file():
                die(f"R17_EXTERNAL_SOURCE_MISSING:{path.relative_to(ROOT)}")
            expected = item.get("git_blob_sha")
            if expected:
                actual = subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()
                if actual != expected:
                    die(f"R17_EXTERNAL_BLOB_DRIFT:{path.relative_to(ROOT)}:{actual}:{expected}")
            sources.append((gap_uid, path, load(path)))
            provenance.append({"gap_uid": gap_uid, "path": str(path.relative_to(ROOT)), "manifest_current": True, "authority_identity_status": status, "git_blob_sha": expected})
    return sources, provenance


def transition_trace(scope: str, transition_uid: str):
    path = CHAIN[scope]
    doc = load(path)
    nodes = exact_nodes(doc, "transition_uid", transition_uid)
    if len(nodes) != 1:
        die(f"R17_TRANSITION_NODE_NOT_UNIQUE:{transition_uid}:{len(nodes)}")
    node_path, node = nodes[0]
    identity = {k: node.get(k) for k in ("transition_uid", "from_stage", "to_stage", "trigger", "trigger_event_uid", "gate", "gate_uid") if node.get(k) not in (None, "")}
    if not identity.get("from_stage") or not identity.get("to_stage"):
        die(f"R17_TRANSITION_ENDPOINTS_MISSING:{transition_uid}")
    signals = []
    for k in RELATED_SIGNAL_KEYS:
        if node.get(k) not in (None, "", [], {}):
            signals.append(ev(path, node_path, "EXACT_FROZEN_TRANSITION_IDENTITY_OR_SIGNAL", k, node.get(k), "FROZEN_FUNCTIONAL_CHAIN"))
    fields = []
    for k in REQUIRED_FIELDS:
        if node.get(k) not in (None, "", [], {}):
            fields.append(ev(path, node_path, "EXACT_FROZEN_TRANSITION_LEDGER_FIELD", k, node.get(k), "FROZEN_FUNCTIONAL_CHAIN"))
    return identity, fields, signals


def identity_matches_transition(node, identity):
    if node.get("transition_uid") == identity["transition_uid"]:
        return ["EXACT_TRANSITION_UID"]
    return []


def search_field(scope: str, identity: dict, missing_field: str, external_sources):
    sources = [("CURRENT_PAGE_AUTHORITY_EXACT_CAPTURE", RAW_PAGE[scope], load(RAW_PAGE[scope]))]
    sources.extend((f"CURRENT_EXTERNAL_AUTHORITY:{gap}", path, doc) for gap, path, doc in external_sources)
    matches, fields, signals = [], [], []
    for kind, path, doc in sources:
        for node_path, node in walk(doc):
            if not isinstance(node, dict):
                continue
            proofs = identity_matches_transition(node, identity)
            if not proofs:
                continue
            matches.append(ev(path, node_path, "+".join(proofs), source_kind=kind))
            value = node.get(missing_field)
            if value not in (None, "", [], {}):
                fields.append(ev(path, node_path, "+".join(proofs) + "+EXACT_LEDGER_FIELD", missing_field, value, kind))
            for key in RELATED_SIGNAL_KEYS:
                signal = node.get(key)
                if signal not in (None, "", [], {}):
                    signals.append(ev(path, node_path, "+".join(proofs) + "+TRANSITION_IDENTITY_OR_SIGNAL", key, signal, kind))
    return matches, fields, signals


def main():
    r12 = load(R12)
    rows0 = [r for r in (r12.get("records") or []) if r.get("category") == "STATE_TRANSITION_LEDGER_FIELD_MISSING"]
    if len(rows0) != 40:
        die(f"R17_REQUIRES_EXACT_40_TRANSITION_FIELD_IDENTITIES:{len(rows0)}")
    scopes = Counter(r.get("scope") for r in rows0)
    if scopes != Counter({"ASSET-01": 20, "CORE-01": 20}):
        die(f"R17_SCOPE_BASELINE_DRIFT:{dict(scopes)}")
    fields = Counter(r.get("missing_field_or_relation") for r in rows0)
    if fields != Counter({"mutation_owner": 10, "failure_state": 10, "recovery": 10, "audit_event_uid": 10}):
        die(f"R17_FIELD_BASELINE_DRIFT:{dict(fields)}")
    if any(r.get("classification") != "UNRESOLVED_FUNCTIONAL_CONTRACT_GAP" for r in rows0):
        die("R17_REQUIRES_R12_UNRESOLVED_BASELINE")

    external_sources, provenance = current_external_sources()
    out_rows, counts = [], Counter()
    transition_ids = set()
    for source in rows0:
        scope = source["scope"]
        target = source["target_uid"]
        missing = source["missing_field_or_relation"]
        identity, frozen_fields, frozen_signals = transition_trace(scope, target)
        transition_ids.add(target)
        local_field = [x for x in frozen_fields if x.get("key") == missing]
        matches, external_fields, external_signals = search_field(scope, identity, missing, external_sources)
        evidence = local_field + external_fields
        signals = frozen_signals + external_signals
        values = {stable(x.get("value")) for x in evidence}
        if len(values) == 1:
            cls, candidate = "EXACT_TRANSITION_LEDGER_FIELD_FOUND", True
        elif len(values) > 1:
            cls, candidate = "CONFLICTING_TRANSITION_LEDGER_FIELD_VALUES", False
        elif signals:
            cls, candidate = "FROZEN_TRANSITION_IDENTITY_ONLY_FIELD_MISSING", False
        else:
            cls, candidate = "CURRENT_FROZEN_TRANSITION_LEDGER_CONTRACT_MISSING", False
        counts[cls] += 1
        out_rows.append({
            "blocker_uid": source["blocker_uid"],
            "scope": scope,
            "category": "STATE_TRANSITION_LEDGER_FIELD_MISSING",
            "target_uid": target,
            "missing_field_or_relation": missing,
            "r12_identity_ref": source["blocker_uid"],
            "r12_classification_used_as_authority": False,
            "transition_identity": identity,
            "current_transition_identity_matches": matches,
            "exact_transition_ledger_field_evidence": evidence,
            "transition_identity_or_signal_evidence": signals,
            "unique_exact_field_value_count": len(values),
            "classification": cls,
            "materialization_candidate": candidate,
            "cross_node_field_inference_used": False,
            "action_owner_promoted_to_mutation_owner": False,
            "error_uid_promoted_to_failure_state": False,
            "state_event_promoted_to_audit_event_uid": False,
            "semantic_recovery_inference_used": False,
            "historical_non_current_authority_used": False,
            "blocker_reduction_credit": 0,
            "next_action": "SEPARATE_BOUNDED_STAGE02_TRANSITION_LEDGER_FIELD_MATERIALIZATION_THEN_FRESH_REEXECUTION" if candidate else "KEEP_UNRESOLVED_UNTIL_EXACT_SAME_TRANSITION_UID_LEDGER_FIELD_IS_PROVEN",
        })

    if len(transition_ids) != 10:
        die(f"R17_EXPECTED_10_TRANSITIONS:{len(transition_ids)}")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    doc = {
        "schema_version": 1,
        "artifact_type": "NON_NORMATIVE_STAGE02_STATE_TRANSITION_LEDGER_DEPENDENCY_TRACE_R17",
        "normative_authority": False,
        "stage_uid": "STAGE-02",
        "cycle": "STATE_TRANSITION_LEDGER_EXACT_DEPENDENCY_TRACE_R17",
        "source_head_sha": head,
        "source_contracts": {
            "r12_identity_source": str(R12.relative_to(ROOT)),
            "r12_classification_accepted_as_authority": False,
            "functional_chain_sources": {k: str(v.relative_to(ROOT)) for k, v in CHAIN.items()},
            "current_page_authority_exact_captures": {k: str(v.relative_to(ROOT)) for k, v in RAW_PAGE.items()},
            "external_authority_materialization_evidence": str(EXT_EVIDENCE.relative_to(ROOT)),
            "current_admissible_external_sources": provenance,
        },
        "trace_contract": {
            "required_exact_ledger_fields": sorted(REQUIRED_FIELDS),
            "field_must_be_physically_present_on_same_exact_transition_uid": True,
            "action_owner_may_supply_mutation_owner": False,
            "error_uid_may_supply_failure_state": False,
            "state_event_may_supply_audit_event_uid": False,
            "semantic_recovery_inference_allowed": False,
            "cross_node_field_inference_allowed": False,
            "classification_alone_may_reduce_blocker": False,
        },
        "denominators": {
            "state_transition_ledger_field_gaps_traced": 40,
            "unique_transition_count": 10,
            "scope_counts": dict(scopes),
            "missing_field_counts": dict(fields),
            "exact_transition_ledger_field_found": counts["EXACT_TRANSITION_LEDGER_FIELD_FOUND"],
            "conflicting_transition_ledger_field_values": counts["CONFLICTING_TRANSITION_LEDGER_FIELD_VALUES"],
            "frozen_transition_identity_only_field_missing": counts["FROZEN_TRANSITION_IDENTITY_ONLY_FIELD_MISSING"],
            "current_frozen_transition_ledger_contract_missing": counts["CURRENT_FROZEN_TRANSITION_LEDGER_CONTRACT_MISSING"],
            "effective_stage02_blocker_reduction_claimed": 0,
        },
        "records": out_rows,
        "stage02_status": "BLOCKED",
        "stage02_effective_blocker_count_before_any_materialization_and_fresh_reexecution": 150,
        "stage03_allowed": False,
        "website_construction_allowed": False,
        "deployment_allowed": False,
    }
    OUT.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"PASS: R17 traced 40 transition-ledger field gaps across 10 transitions classifications={dict(counts)}")
    print("PASS: field evidence is accepted only when physically present on the same exact transition_uid")
    print("PASS: no cross-node inference and zero blocker reduction until separate materialization + fresh reexecution")


if __name__ == "__main__":
    main()
