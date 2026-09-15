#!/usr/bin/env python3
from __future__ import annotations

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
OUT = ROOT / "governance/test/stage02/STAGE02_ACTION_CONTROL_TRIGGER_DEPENDENCY_TRACE_R18.yaml"
CHAIN = STAGE2 / "ASSET-01/FUNCTIONAL_CHAIN_SPEC.yaml"
RAW_PAGE = RAW / "ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml"
TARGET = "ASSET-01-ACT-FINDING-CREATE"
UID_TOKEN = re.compile(r"\b[A-Z0-9]+(?:-[A-Z0-9]+)+\b")


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


def ev(path: Path, node_path, proof, value=None, source_kind=None):
    item = {
        "path": str(path.relative_to(ROOT)),
        "node_path": ".".join(node_path) if node_path else "$",
        "proof": proof,
    }
    if value is not None:
        item["value"] = value
    if source_kind:
        item["source_kind"] = source_kind
    return item


def exact_uid_tokens(value):
    if not isinstance(value, str):
        return []
    return UID_TOKEN.findall(value)


def relations(path: Path, doc, source_kind: str):
    controls, triggers, nonqualifying = [], [], []
    for node_path, node in walk(doc):
        if not isinstance(node, dict):
            continue
        if isinstance(node.get("control_uid"), str) and node.get("action_uid") == TARGET:
            controls.append(ev(path, node_path, "EXACT_CONTROL_UID_DIRECT_ACTION_BINDING", {
                "control_uid": node.get("control_uid"), "action_uid": TARGET,
            }, source_kind))
        if isinstance(node.get("transition_uid"), str) and (node.get("trigger") == TARGET or node.get("trigger_action_uid") == TARGET):
            triggers.append(ev(path, node_path, "EXACT_STAGE_TRANSITION_ACTION_TRIGGER", {
                "transition_uid": node.get("transition_uid"),
                "trigger": node.get("trigger"),
                "trigger_action_uid": node.get("trigger_action_uid"),
            }, source_kind))
        trigger_identity = node.get("trigger_uid") or node.get("system_trigger_uid") or node.get("event_trigger_uid")
        direct_action = node.get("action_uid") == TARGET or node.get("trigger_action_uid") == TARGET or node.get("action_ref") == TARGET
        if isinstance(trigger_identity, str) and trigger_identity and direct_action:
            triggers.append(ev(path, node_path, "EXACT_REGISTERED_SYSTEM_TRIGGER_DIRECT_ACTION_BINDING", {
                "trigger_uid": trigger_identity,
                "action_uid": node.get("action_uid"),
                "trigger_action_uid": node.get("trigger_action_uid"),
                "action_ref": node.get("action_ref"),
            }, source_kind))
        exposure = node.get("exposure")
        exposure_tokens = exact_uid_tokens(exposure)
        if TARGET in exposure_tokens and (node.get("port_uid") or node.get("registered_operation")):
            nonqualifying.append(ev(path, node_path, "EXACT_UID_TOKEN_IN_PORT_EXPOSURE_NOT_CONTROL_OR_TRIGGER", {
                "port_uid": node.get("port_uid"),
                "registered_operation": node.get("registered_operation"),
                "exposure_raw": exposure,
                "exposure_uid_tokens": exposure_tokens,
                "matched_action_uid": TARGET,
            }, source_kind))
    return controls, triggers, nonqualifying


def main():
    r12 = load(R12)
    candidates = [r for r in (r12.get("records") or []) if r.get("category") == "ACTION_WITHOUT_CONTROL_OR_TRIGGER"]
    if len(candidates) != 1:
        die(f"R18_REQUIRES_EXACT_ONE_ACTION_GAP:{len(candidates)}")
    source = candidates[0]
    if source.get("scope") != "ASSET-01" or source.get("target_uid") != TARGET or source.get("classification") != "UNRESOLVED_FUNCTIONAL_CONTRACT_GAP":
        die(f"R18_BASELINE_IDENTITY_DRIFT:{source}")

    chain = load(CHAIN)
    raw = load(RAW_PAGE)
    action_nodes = [(p, n) for p, n in walk(chain) if isinstance(n, dict) and n.get("action_uid") == TARGET and isinstance(n.get("runtime_binding"), dict)]
    if len(action_nodes) != 1:
        die(f"R18_ACTION_NODE_NOT_UNIQUE:{len(action_nodes)}")
    action_path, action = action_nodes[0]

    c1, t1, nq1 = relations(CHAIN, chain, "FROZEN_FUNCTIONAL_CHAIN")
    c2, t2, nq2 = relations(RAW_PAGE, raw, "CURRENT_PAGE_AUTHORITY_EXACT_CAPTURE")
    controls = c1 + c2
    triggers = t1 + t2
    nonqualifying = nq1 + nq2

    if controls and triggers:
        classification = "EXACT_CONTROL_AND_TRIGGER_FOUND"
        candidate = True
    elif controls:
        classification = "EXACT_CONTROL_BINDING_FOUND"
        candidate = True
    elif triggers:
        classification = "EXACT_TRIGGER_BINDING_FOUND"
        candidate = True
    elif nonqualifying:
        classification = "EXACT_PORT_EXPOSURE_ONLY_CONTROL_TRIGGER_MISSING"
        candidate = False
    else:
        classification = "CURRENT_FROZEN_CONTROL_TRIGGER_CONTRACT_MISSING"
        candidate = False

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    doc = {
        "schema_version": 1,
        "artifact_type": "NON_NORMATIVE_STAGE02_ACTION_CONTROL_TRIGGER_DEPENDENCY_TRACE_R18",
        "normative_authority": False,
        "stage_uid": "STAGE-02",
        "cycle": "ACTION_CONTROL_TRIGGER_EXACT_DEPENDENCY_TRACE_R18",
        "source_head_sha": head,
        "source_contracts": {
            "r12_identity_source": str(R12.relative_to(ROOT)),
            "r12_classification_accepted_as_authority": False,
            "functional_chain_source": str(CHAIN.relative_to(ROOT)),
            "current_page_authority_exact_capture": str(RAW_PAGE.relative_to(ROOT)),
        },
        "trace_contract": {
            "control_requires_same_node_control_uid_and_direct_action_uid": True,
            "stage_trigger_requires_transition_uid_and_direct_trigger_action": True,
            "system_trigger_requires_trigger_identity_and_direct_action_reference": True,
            "port_exposure_uid_is_extracted_syntactically_not_semantically": True,
            "port_exposure_is_control_or_trigger": False,
            "semantic_trigger_inference_allowed": False,
            "invented_control_or_trigger_allowed": False,
            "classification_alone_may_reduce_blocker": False,
        },
        "denominators": {
            "action_without_control_or_trigger_gaps_traced": 1,
            "scope_counts": {"ASSET-01": 1},
            "exact_control_binding_count": len(controls),
            "exact_trigger_binding_count": len(triggers),
            "nonqualifying_port_exposure_count": len(nonqualifying),
            "materialization_candidates": 1 if candidate else 0,
            "effective_stage02_blocker_reduction_claimed": 0,
        },
        "records": [{
            "blocker_uid": source["blocker_uid"],
            "scope": "ASSET-01",
            "category": "ACTION_WITHOUT_CONTROL_OR_TRIGGER",
            "target_uid": TARGET,
            "missing_field_or_relation": source.get("missing_field_or_relation"),
            "r12_identity_ref": source["blocker_uid"],
            "r12_classification_used_as_authority": False,
            "action_identity_evidence": ev(CHAIN, action_path, "EXACT_ACTION_RUNTIME_NODE", {
                "action_uid": TARGET,
                "runtime_binding": action.get("runtime_binding"),
            }, "FROZEN_FUNCTIONAL_CHAIN"),
            "exact_control_binding_evidence": controls,
            "exact_trigger_binding_evidence": triggers,
            "nonqualifying_lineage_evidence": nonqualifying,
            "classification": classification,
            "materialization_candidate": candidate,
            "port_exposure_promoted_to_control_or_trigger": False,
            "semantic_trigger_inference_used": False,
            "invented_control_or_trigger_used": False,
            "historical_non_current_authority_used": False,
            "blocker_reduction_credit": 0,
            "next_action": "SEPARATE_BOUNDED_STAGE02_CONTROL_TRIGGER_MATERIALIZATION_THEN_FRESH_REEXECUTION" if candidate else "KEEP_UNRESOLVED_UNTIL_EXACT_CONTROL_OR_REGISTERED_TRIGGER_IS_PROVEN",
        }],
        "stage02_status": "BLOCKED",
        "stage02_effective_blocker_count_before_any_materialization_and_fresh_reexecution": 150,
        "stage03_allowed": False,
        "website_construction_allowed": False,
        "deployment_allowed": False,
    }
    OUT.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"PASS: R18 traced {TARGET} classification={classification} controls={len(controls)} triggers={len(triggers)} port_exposures={len(nonqualifying)}")
    print("PASS: exact UID token extraction preserves punctuated port exposure as lineage without promoting it to a control/trigger")
    print("PASS: zero blocker reduction until separate bounded materialization and fresh reexecution")


if __name__ == "__main__":
    main()
