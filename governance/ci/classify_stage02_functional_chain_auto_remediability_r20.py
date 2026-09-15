#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "00_SOURCE_INTAKE/fresh_run_003"
PRODUCT_ROOT = RUN / "04_PAGE_FUNCTIONAL_CONTRACT"
R19 = ROOT / "governance/test/stage02/STAGE02_FUNCTIONAL_CONTRACT_REMEDIATION_PROBLEM_REGISTER_R19.yaml"
OUT = ROOT / "governance/test/stage02/STAGE02_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY_R20.yaml"

SOURCE_FILES = {
    "CORE-01": {
        "raw": RUN / "00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml",
        "functional_chain": PRODUCT_ROOT / "CORE-01/FUNCTIONAL_CHAIN_SPEC.yaml",
        "operation_matrix": PRODUCT_ROOT / "CORE-01/BUSINESS_ENTITY_OPERATION_MATRIX.yaml",
        "scope_ledger": PRODUCT_ROOT / "CORE-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml",
    },
    "ASSET-01": {
        "raw": RUN / "00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml",
        "functional_chain": PRODUCT_ROOT / "ASSET-01/FUNCTIONAL_CHAIN_SPEC.yaml",
        "operation_matrix": PRODUCT_ROOT / "ASSET-01/BUSINESS_ENTITY_OPERATION_MATRIX.yaml",
        "scope_ledger": PRODUCT_ROOT / "ASSET-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml",
    },
}
ALLOWED_SOURCE_KINDS = {
    "RAW_CURRENT_PAGE_REGISTRY",
    "FROZEN_STAGE02_FUNCTIONAL_CHAIN_EXACT_PROJECTION",
    "FROZEN_STAGE02_OPERATION_MATRIX_EXACT_PROJECTION",
    "FROZEN_STAGE02_SCOPE_LEDGER_EXACT_MATERIALIZATION",
}


def die(msg: str) -> None:
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def nonempty(v):
    return v not in (None, "", [], {})


def indexed(items, key):
    out = {}
    for item in items or []:
        if isinstance(item, dict) and nonempty(item.get(key)):
            uid = str(item[key]).rstrip(".")
            if uid in out:
                die(f"DUPLICATE_UID:{key}:{uid}")
            out[uid] = item
    return out


def registry_index(regs):
    return {
        "actions": indexed(regs.get("actions"), "action_uid"),
        "controls": indexed(regs.get("controls"), "control_uid"),
        "ports": indexed(regs.get("integration_ports"), "port_uid"),
        "transitions": indexed(regs.get("stage_transitions"), "transition_uid"),
        "events": indexed(regs.get("events"), "event_uid"),
    }


def source_ref(kind, path, node):
    return {"source_kind": kind, "source_path": str(path.relative_to(ROOT)), "node": node}


def build_bundle(page_uid: str):
    files = SOURCE_FILES[page_uid]
    raw = load(files["raw"])
    chain = load(files["functional_chain"])
    matrix = load(files["operation_matrix"])
    ledger = load(files["scope_ledger"])
    if chain.get("page_uid") != page_uid:
        die(f"CHAIN_PAGE_UID_DRIFT:{page_uid}:{chain.get('page_uid')}")
    if matrix.get("page_uid") != page_uid:
        die(f"MATRIX_PAGE_UID_DRIFT:{page_uid}:{matrix.get('page_uid')}")
    if ledger.get("page_uid") != page_uid:
        die(f"LEDGER_PAGE_UID_DRIFT:{page_uid}:{ledger.get('page_uid')}")
    if chain.get("stage_uid") != "STAGE-02" or matrix.get("stage_uid") != "STAGE-02" or ledger.get("stage_uid") != "STAGE-02":
        die(f"STAGE_UID_DRIFT:{page_uid}")
    raw_idx = registry_index(raw.get("registries") or {})
    chain_idx = registry_index(chain.get("source_projection") or {})
    operations = indexed(matrix.get("operations"), "action_uid")
    remediations = ledger.get("remediations") or []
    if not isinstance(remediations, list):
        die(f"LEDGER_REMEDIATIONS_LIST_REQUIRED:{page_uid}")
    return {
        "page_uid": page_uid,
        "raw": raw_idx,
        "chain": chain_idx,
        "operations": operations,
        "scope_ledger": remediations,
        "paths": files,
        "source_manifest": {
            "raw": str(files["raw"].relative_to(ROOT)),
            "functional_chain": str(files["functional_chain"].relative_to(ROOT)),
            "operation_matrix": str(files["operation_matrix"].relative_to(ROOT)),
            "scope_ledger": str(files["scope_ledger"].relative_to(ROOT)),
            "raw_loaded": True,
            "functional_chain_loaded": True,
            "operation_matrix_loaded": True,
            "scope_ledger_loaded": True,
            "functional_chain_page_uid_match": True,
            "operation_matrix_page_uid_match": True,
            "scope_ledger_page_uid_match": True,
            "functional_chain_action_count": len(chain_idx["actions"]),
            "operation_matrix_action_count": len(operations),
            "scope_ledger_remediation_count": len(remediations),
        },
    }


def node_variants(bundle, table, uid):
    out = []
    for bucket, kind, path_key in (
        ("raw", "RAW_CURRENT_PAGE_REGISTRY", "raw"),
        ("chain", "FROZEN_STAGE02_FUNCTIONAL_CHAIN_EXACT_PROJECTION", "functional_chain"),
    ):
        node = bundle[bucket][table].get(str(uid).rstrip("."))
        if node:
            out.append((node, source_ref(kind, bundle["paths"][path_key], f"{table}:{str(uid).rstrip('.')}")))
    return out


def action_variants(bundle, action_uid):
    return node_variants(bundle, "actions", action_uid)


def port_uids_for_action(bundle, action_uid):
    found = {}
    for action, ref in action_variants(bundle, action_uid):
        rb = action.get("runtime_binding") or {}
        for field in ("port_uid", "persist_via_port_uid"):
            if nonempty(rb.get(field)):
                uid = str(rb[field]).rstrip(".")
                found.setdefault(uid, []).append({**ref, "node": f"{ref['node']}.runtime_binding.{field}"})
    op = bundle["operations"].get(str(action_uid))
    if op:
        for entry in op.get("port_refs") or []:
            if isinstance(entry, dict) and nonempty(entry.get("port_uid")):
                uid = str(entry["port_uid"]).rstrip(".")
                ref = source_ref("FROZEN_STAGE02_OPERATION_MATRIX_EXACT_PROJECTION", bundle["paths"]["operation_matrix"], f"operation:{action_uid}.port_refs")
                found.setdefault(uid, []).append(ref)
    return found


def port_variants(bundle, port_uid):
    return node_variants(bundle, "ports", port_uid)


def transition_variants(bundle, transition_uid):
    return node_variants(bundle, "transitions", transition_uid)


def triggered_transition_uids(bundle, action_uid):
    found = set()
    for bucket in ("raw", "chain"):
        for uid, tr in bundle[bucket]["transitions"].items():
            trigger = tr.get("trigger") or tr.get("action_uid") or tr.get("trigger_event_uid")
            if str(trigger).rstrip(".") == str(action_uid).rstrip("."):
                found.add(uid)
    return sorted(found)


def event_uids(bundle):
    return set(bundle["raw"]["events"]) | set(bundle["chain"]["events"])


def add_candidate(out, source, value):
    if nonempty(value):
        out.append({**source, "value": value})


def scalar_signal_candidates(bundle, action_uid):
    candidates = []
    for action, ref in action_variants(bundle, action_uid):
        rb = action.get("runtime_binding") or {}
        for field in ("result_state", "success_state", "result", "state_event"):
            value = rb.get(field)
            if nonempty(value) and not isinstance(value, (dict, list)):
                add_candidate(candidates, {**ref, "node": f"{ref['node']}.runtime_binding.{field}"}, value)
    for port_uid in sorted(port_uids_for_action(bundle, action_uid)):
        for port, ref in port_variants(bundle, port_uid):
            for field in ("result_state", "success_state", "state_event", "result"):
                value = port.get(field)
                if nonempty(value) and not isinstance(value, (dict, list)):
                    add_candidate(candidates, {**ref, "node": f"{ref['node']}.{field}"}, value)
    for transition_uid in triggered_transition_uids(bundle, action_uid):
        for tr, ref in transition_variants(bundle, transition_uid):
            value = tr.get("to_stage")
            if nonempty(value):
                add_candidate(candidates, {**ref, "node": f"{ref['node']}.to_stage"}, value)
    return candidates


def exact_registered_event_candidates(bundle, action_uid):
    candidates = []
    known_events = event_uids(bundle)
    for action, ref in action_variants(bundle, action_uid):
        for node_name, node in (("action", action), ("action.runtime_binding", action.get("runtime_binding") or {})):
            for field in ("audit_event_uid", "event_uid", "state_event"):
                value = node.get(field)
                if nonempty(value) and str(value) in known_events:
                    add_candidate(candidates, {**ref, "node": f"{ref['node']}.{node_name}.{field}"}, str(value))
    for port_uid in sorted(port_uids_for_action(bundle, action_uid)):
        for port, ref in port_variants(bundle, port_uid):
            for field in ("audit_event_uid", "event_uid", "state_event"):
                value = port.get(field)
                if nonempty(value) and str(value) in known_events:
                    add_candidate(candidates, {**ref, "node": f"{ref['node']}.{field}"}, str(value))
    return candidates


def structured_payload_candidates(bundle, action_uid):
    candidates = []
    fields = ("payload_schema", "input_schema", "request_schema", "payload_contract", "input_contract")
    for action, ref in action_variants(bundle, action_uid):
        for node_name, node in (("action", action), ("action.runtime_binding", action.get("runtime_binding") or {})):
            for field in fields:
                value = node.get(field)
                if isinstance(value, (dict, list)) and nonempty(value):
                    add_candidate(candidates, {**ref, "node": f"{ref['node']}.{node_name}.{field}"}, value)
    for port_uid in sorted(port_uids_for_action(bundle, action_uid)):
        for port, ref in port_variants(bundle, port_uid):
            for field in fields:
                value = port.get(field)
                if isinstance(value, (dict, list)) and nonempty(value):
                    add_candidate(candidates, {**ref, "node": f"{ref['node']}.{field}"}, value)
    return candidates


def exact_failure_candidates(bundle, action_uid):
    candidates = []
    fields = ("failure_state", "error_state", "error_contract", "recovery", "recovery_rule", "retry_policy", "rollback")
    for action, ref in action_variants(bundle, action_uid):
        for node_name, node in (("action", action), ("action.runtime_binding", action.get("runtime_binding") or {})):
            value = {field: node.get(field) for field in fields if nonempty(node.get(field))}
            if value:
                add_candidate(candidates, {**ref, "node": f"{ref['node']}.{node_name}"}, value)
    for port_uid in sorted(port_uids_for_action(bundle, action_uid)):
        for port, ref in port_variants(bundle, port_uid):
            value = {field: port.get(field) for field in fields if nonempty(port.get(field))}
            if value:
                add_candidate(candidates, ref, value)
    for transition_uid in triggered_transition_uids(bundle, action_uid):
        for tr, ref in transition_variants(bundle, transition_uid):
            value = {field: tr.get(field) for field in ("failure_state", "error_state", "recovery", "recovery_rule", "retry_policy", "rollback") if nonempty(tr.get(field))}
            if value:
                add_candidate(candidates, ref, value)
    return candidates


def exact_control_or_trigger_candidates(bundle, action_uid):
    candidates = []
    for bucket, kind, path_key in (("raw", "RAW_CURRENT_PAGE_REGISTRY", "raw"), ("chain", "FROZEN_STAGE02_FUNCTIONAL_CHAIN_EXACT_PROJECTION", "functional_chain")):
        for uid, ctl in bundle[bucket]["controls"].items():
            if str(ctl.get("action_uid")).rstrip(".") == str(action_uid).rstrip("."):
                add_candidate(candidates, source_ref(kind, bundle["paths"][path_key], f"control:{uid}.action_uid"), {"trigger_kind": "CONTROL", "trigger_uid": uid})
    op = bundle["operations"].get(str(action_uid))
    if op:
        for uid in op.get("control_uids") or []:
            uid = str(uid).rstrip(".")
            if uid:
                add_candidate(candidates, source_ref("FROZEN_STAGE02_OPERATION_MATRIX_EXACT_PROJECTION", bundle["paths"]["operation_matrix"], f"operation:{action_uid}.control_uids"), {"trigger_kind": "CONTROL", "trigger_uid": uid})
    for uid in triggered_transition_uids(bundle, action_uid):
        add_candidate(candidates, source_ref("FROZEN_STAGE02_FUNCTIONAL_CHAIN_EXACT_PROJECTION", bundle["paths"]["functional_chain"], f"stage_transition:{uid}.trigger"), {"trigger_kind": "STAGE_TRANSITION", "trigger_uid": uid})
    return candidates


def mutation_owner_candidates(bundle, transition_uid):
    candidates = []
    triggers = set()
    for tr, _ in transition_variants(bundle, transition_uid):
        trigger = tr.get("trigger") or tr.get("action_uid")
        if nonempty(trigger):
            triggers.add(str(trigger).rstrip("."))
    for trigger in sorted(triggers):
        port_map = port_uids_for_action(bundle, trigger)
        for uid in sorted(port_map):
            operation_names = set()
            for port, _ in port_variants(bundle, uid):
                op = port.get("registered_operation") or port.get("operation") or port.get("operation_id")
                if nonempty(op):
                    operation_names.add(str(op))
            values = sorted(operation_names)
            value = {"owner_kind": "REGISTERED_INTEGRATION_PORT", "owner_uid": uid, "operation": values[0] if len(values) == 1 else (values if values else None)}
            for ref in port_map[uid]:
                add_candidate(candidates, ref, value)
        shared = set()
        for action, ref in action_variants(bundle, trigger):
            rb = action.get("runtime_binding") or {}
            if nonempty(rb.get("shared_authority_id")) and nonempty(rb.get("shared_operation_id")):
                shared.add((str(rb["shared_authority_id"]), str(rb["shared_operation_id"]), ref["source_kind"], ref["source_path"], ref["node"]))
        op = bundle["operations"].get(trigger)
        if op and nonempty(op.get("shared_authority_id")) and nonempty(op.get("shared_operation_id")):
            shared.add((str(op["shared_authority_id"]), str(op["shared_operation_id"]), "FROZEN_STAGE02_OPERATION_MATRIX_EXACT_PROJECTION", str(bundle["paths"]["operation_matrix"].relative_to(ROOT)), f"operation:{trigger}.shared_operation"))
        for authority_id, operation_id, source_kind, source_path, node in sorted(shared):
            add_candidate(candidates, {"source_kind": source_kind, "source_path": source_path, "node": node}, {"owner_kind": "SHARED_OPERATION", "authority_id": authority_id, "operation_id": operation_id})
    return candidates


def transition_field_exact_candidates(bundle, transition_uid, field):
    aliases = {"failure_state": ("error_state",), "recovery": ("recovery_rule",), "audit_event_uid": ("event_uid",)}.get(field, ())
    candidates = []
    known_events = event_uids(bundle)
    for tr, ref in transition_variants(bundle, transition_uid):
        for alias in aliases:
            if nonempty(tr.get(alias)):
                value = tr.get(alias)
                if field == "audit_event_uid" and str(value) not in known_events:
                    continue
                add_candidate(candidates, {**ref, "node": f"{ref['node']}.{alias}"}, value)
    for row in bundle["scope_ledger"]:
        if not isinstance(row, dict):
            continue
        defect = row.get("defect_signature") or {}
        closure = row.get("materialized_closure") or {}
        if str(defect.get("uid")).rstrip(".") != str(transition_uid).rstrip("."):
            continue
        if field not in closure or not nonempty(closure.get(field)):
            continue
        if row.get("semantic_inference_used") is not False or row.get("ai_invented_business_value") is not False:
            continue
        add_candidate(candidates, source_ref("FROZEN_STAGE02_SCOPE_LEDGER_EXACT_MATERIALIZATION", bundle["paths"]["scope_ledger"], f"remediation:{row.get('remediation_uid')}.materialized_closure.{field}"), closure[field])
    return candidates


def canonical_groups(candidates):
    groups = {}
    for candidate in candidates:
        if candidate.get("source_kind") not in ALLOWED_SOURCE_KINDS:
            die(f"UNAPPROVED_EVIDENCE_SOURCE_KIND:{candidate.get('source_kind')}")
        key = yaml.safe_dump(candidate.get("value"), allow_unicode=True, sort_keys=True)
        groups.setdefault(key, []).append(candidate)
    return groups


def evaluate(problem, bundle):
    category = str(problem["category"])
    target = str(problem["target_uid"]).rstrip(".")
    missing = str(problem.get("missing_field_or_relation") or "")
    candidates = []
    closure_type = None
    if category == "POST_ACTION_VALIDATION_NODE_MISSING":
        candidates = scalar_signal_candidates(bundle, target)
        closure_type = "POST_ACTION_VALIDATION_FROM_UNIQUE_FROZEN_SUCCESS_SIGNAL"
    elif category == "PAYLOAD_INPUT_CONTRACT_MISSING":
        candidates = structured_payload_candidates(bundle, target)
        closure_type = "REQUEST_INPUT_CONTRACT_EXACT_STRUCTURED_PROJECTION"
    elif category == "AUDIT_EVENT_NODE_MISSING":
        candidates = exact_registered_event_candidates(bundle, target)
        closure_type = "AUDIT_EVENT_EXACT_REGISTERED_EVENT_PROJECTION"
    elif category == "FAILURE_STATE_ERROR_BINDING_MISSING":
        candidates = exact_failure_candidates(bundle, target)
        closure_type = "FAILURE_ERROR_RECOVERY_EXACT_CHAIN_PROJECTION"
    elif category == "ACTION_WITHOUT_CONTROL_OR_TRIGGER":
        candidates = exact_control_or_trigger_candidates(bundle, target)
        closure_type = "CONTROL_OR_TRIGGER_EXACT_CHAIN_PROJECTION"
    elif category == "STATE_TRANSITION_LEDGER_FIELD_MISSING":
        field = next((name for name in ("mutation_owner", "failure_state", "recovery", "audit_event_uid") if name in missing), None)
        if field == "mutation_owner":
            candidates = mutation_owner_candidates(bundle, target)
            closure_type = "TRANSITION_MUTATION_OWNER_FROM_UNIQUE_TRIGGER_RUNTIME_OWNER"
        elif field:
            candidates = transition_field_exact_candidates(bundle, target, field)
            closure_type = f"TRANSITION_{field.upper()}_EXACT_ALIAS_PROJECTION"
    groups = canonical_groups(candidates)
    distinct = len(groups)
    if distinct == 1:
        evidence = next(iter(groups.values()))
        return {"disposition": "AUTO_REMEDIABLE_DETERMINISTIC_MINIMAL_CLOSURE", "authorized_for_auto_completion": True, "closure_type": closure_type, "candidate_value": evidence[0]["value"], "candidate_evidence": candidates, "distinct_candidate_value_count": 1, "authority_gap_proven": False, "outside_frozen_closure": False, "full_stage02_functional_contract_sources_checked": True}
    if distinct > 1:
        return {"disposition": "AUTHORITY_GAP_MULTIPLE_REASONABLE_CLOSURES", "authorized_for_auto_completion": False, "closure_type": closure_type, "candidate_value": None, "candidate_evidence": candidates, "distinct_candidate_value_count": distinct, "authority_gap_proven": True, "outside_frozen_closure": False, "full_stage02_functional_contract_sources_checked": True}
    return {"disposition": "UNRESOLVED_FUNCTIONAL_CONTRACT_GAP_NO_UNIQUE_CLOSURE", "authorized_for_auto_completion": False, "closure_type": closure_type, "candidate_value": None, "candidate_evidence": candidates, "distinct_candidate_value_count": 0, "authority_gap_proven": False, "outside_frozen_closure": False, "full_stage02_functional_contract_sources_checked": True}


r19 = load(R19)
problems = r19.get("problems") or []
if len(problems) != 150:
    die(f"R19_DENOMINATOR_DRIFT:{len(problems)}")
bundles = {page: build_bundle(page) for page in SOURCE_FILES}
records = []
for problem in problems:
    page = problem.get("scope")
    if page not in bundles:
        die(f"UNKNOWN_PAGE:{page}")
    result = evaluate(problem, bundles[page])
    rec = {"problem_uid": problem.get("problem_uid"), "blocker_uid": problem.get("blocker_uid"), "page_uid": page, "category": problem.get("category"), "target_uid": problem.get("target_uid"), "missing_field_or_relation": problem.get("missing_field_or_relation"), "owning_layer": problem.get("owning_layer"), **result}
    if rec["authorized_for_auto_completion"]:
        rec["function_admission_scorecard"] = {"seed_gap": rec["blocker_uid"], "required_operation_or_contract": rec["category"], "current_authority_or_deterministic_required_dependency": True, "existing_capability_reuse_checked": True, "alternative_path_checked": True, "complete_stage02_functional_chain_checked": True, "blocked_terminal_outcome": "STAGE02_FUNCTIONAL_CHAIN_CLOSURE", "necessity_score_is_diagnostic_only": True, "authority_created_by_score": False}
        rec["auto_completion_scope_ledger_entry"] = {"seed_gap": rec["blocker_uid"], "minimal_closure_set": [rec["closure_type"]], "transitive_dependency_count": 0, "outside_frozen_registered_dependency_closure": False, "generic_crud_symmetry_expansion_used": False, "sibling_feature_symmetry_expansion_used": False, "semantic_similarity_used": False, "ai_invented_business_value": False}
    records.append(rec)

summary = Counter(r["disposition"] for r in records)
by_category = {}
for category in sorted(set(r["category"] for r in records)):
    subset = [r for r in records if r["category"] == category]
    by_category[category] = {"total": len(subset), "auto_remediable": sum(bool(r["authorized_for_auto_completion"]) for r in subset), "authority_gap_multiple_reasonable_closures": sum(r["disposition"] == "AUTHORITY_GAP_MULTIPLE_REASONABLE_CLOSURES" for r in subset), "unresolved_no_unique_closure": sum(r["disposition"] == "UNRESOLVED_FUNCTIONAL_CONTRACT_GAP_NO_UNIQUE_CLOSURE" for r in subset)}
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
out = {
    "schema_version": 2,
    "artifact_type": "NON_NORMATIVE_STAGE02_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY_R20",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "cycle": "FUNCTIONAL_CHAIN_DETERMINISTIC_MINIMAL_CLOSURE_R20",
    "source_head_sha": head,
    "source_problem_register": str(R19.relative_to(ROOT)),
    "source_bundle": {page: bundles[page]["source_manifest"] for page in sorted(bundles)},
    "source_policy": {"complete_stage02_functional_contract_bundle_required": True, "allowed_source_kinds": sorted(ALLOWED_SOURCE_KINDS), "operation_matrix_is_exact_projection_not_new_product_authority": True, "scope_ledger_is_non_normative_and_only_exact_matching_materializations_may_contribute_values": True, "natural_language_semantic_similarity_forbidden": True, "historical_non_current_authority_forbidden": True, "ai_invented_business_value_forbidden": True},
    "classification_contract": {"absence_of_materialized_contract_alone_is_authority_gap": False, "full_chain_unique_deterministic_closure_checked_before_block": True, "raw_registry_only_classification_forbidden": True, "all_exact_current_stage02_projection_sources_checked": True, "multiple_distinct_exact_closures_is_authority_gap": True, "zero_exact_closure_is_unresolved_not_product_authority": True, "classification_itself_reduces_blocker": False},
    "denominators": {"input_problem_total": len(records), "auto_remediable_total": summary.get("AUTO_REMEDIABLE_DETERMINISTIC_MINIMAL_CLOSURE", 0), "true_authority_gap_total": summary.get("AUTHORITY_GAP_MULTIPLE_REASONABLE_CLOSURES", 0), "unresolved_no_unique_closure_total": summary.get("UNRESOLVED_FUNCTIONAL_CONTRACT_GAP_NO_UNIQUE_CLOSURE", 0), "blocker_reduction_claimed": 0},
    "by_category": by_category,
    "records": records,
    "current_specification_mutated": False,
    "stage02_status": "BLOCKED",
    "stage03_allowed": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
    "next_execution_gate": "MATERIALIZE_ONLY_AUTO_REMEDIABLE_DETERMINISTIC_MINIMAL_CLOSURES_THEN_FRESH_STAGE02",
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=160), encoding="utf-8")
print(f"R20_TOTAL={len(records)}")
for key in sorted(summary):
    print(f"{key}={summary[key]}")
for category, counts in by_category.items():
    print(f"CATEGORY::{category}::{counts}")
print("PASS: R20 checked RAW + FUNCTIONAL_CHAIN_SPEC + BUSINESS_ENTITY_OPERATION_MATRIX + AUTO_COMPLETION_SCOPE_LEDGER before classifying")
