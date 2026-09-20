#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
import yaml
from content_integrity_engine import ContentIntegrityEngine, nonempty, unique_rows, set_differences

LOCAL_EFFECTS = {"UI_ONLY", "CONTEXT_STATE"}

def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def ts_string_array(source: str, name: str):
    match = re.search(rf"export\s+const\s+{re.escape(name)}\s*=\s*\[(.*?)\]\s*as\s+const", source, re.S)
    if not match:
        return None
    return re.findall(r'["\']([^"\']+)["\']', match.group(1))

def ts_action_port_map(source: str):
    match = re.search(r"export\s+const\s+CORE_ACTION_PORT[^=]*=\s*\{(.*?)\}\s*as\s+const", source, re.S)
    if not match:
        match = re.search(r"CORE_ACTION_PORT[^=]*=\s*\{(.*?)\};", source, re.S)
    if not match:
        return None
    return dict(re.findall(r'["\']([^"\']+)["\']\s*:\s*["\']([^"\']+)["\']', match.group(1)))

def ts_port_method_path(source: str):
    match = re.search(r"CORE_PORT_METHOD_PATH[^=]*=\s*\{(.*?)\}\s*as\s+const", source, re.S)
    if not match:
        match = re.search(r"CORE_PORT_METHOD_PATH[^=]*=\s*\{(.*?)\};", source, re.S)
    if not match:
        return None
    out = {}
    for port, method, path in re.findall(
        r'["\']([^"\']+)["\']\s*:\s*\{\s*method:\s*["\']([^"\']+)["\']\s*,\s*path:\s*["\']([^"\']+)["\']\s*\}',
        match.group(1),
        re.S,
    ):
        out[port] = {"method": method, "path": path}
    return out

def flatten_current_authority_set(manifest):
    current = manifest.get("current_authority_set") or {}
    rows = []
    for category, values in current.items():
        if not isinstance(values, list):
            continue
        for value in values:
            rows.append((str(category), str(value)))
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product-root", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    root = Path(args.product_root).resolve()
    report_path = Path(args.report).resolve()
    common_engine = ContentIntegrityEngine("CORE-01")
    findings = common_engine.findings
    checks = common_engine.checks
    chain_rows = []
    record = common_engine.record

    manifest_path = root / "authority/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml"
    page_path = root / "authority/pages/workspace/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml"
    canonical_visual_path = root / "authority/pages/workspace/CORE-01/CORE_CURRENT_CANONICAL_VISUAL_FINAL_LOCKED_V1.0.yaml"
    runtime_contract_path = root / "src/domain/core/coreRuntimeContract.ts"
    visual_impl_path = root / "src/components/pages/CoreVisual.tsx"
    core_route_factory_path = root / "src/server/core/coreRouteFactory.ts"
    core_runtime_path = root / "src/server/core/coreRuntime.ts"
    production_runtime_path = root / "src/server/core/productionCoreGovernedRuntime.ts"
    identity_runtime_path = root / "src/server/shared/identityPageCommandRuntime.ts"
    operation_registry_path = root / "03_api/operation_registry.yaml"

    required_files = [
        manifest_path, page_path, canonical_visual_path, runtime_contract_path, visual_impl_path,
        core_route_factory_path, core_runtime_path, production_runtime_path, identity_runtime_path,
        operation_registry_path,
    ]
    for p in required_files:
        record(
            "CI-FILE-" + p.name.upper().replace(".", "-"),
            p.is_file(),
            "PHYSICAL_MATERIALIZATION",
            f"Required content file {p.relative_to(root) if p.exists() else p} must physically exist",
        )

    if findings:
        payload = {
            "artifact_type": "NON_NORMATIVE_CORE01_SOURCE_CONTENT_INTEGRITY_REPORT",
            "content_complete": False,
            "result": "BLOCKED",
            "checks": checks,
            "findings": findings,
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(2)

    manifest = load_yaml(manifest_path)
    page = load_yaml(page_path)
    canonical_visual = load_yaml(canonical_visual_path)
    regs = page.get("registries") or {}

    # Manifest/category integrity: denominator must be scoped, not lexical.
    current = manifest.get("current_authority_set") or {}
    pages = list(map(str, current.get("pages") or []))
    registries = list(map(str, current.get("registries") or []))
    declared_page_count = manifest.get("current_page_count")
    front_count = manifest.get("front_l1_count")
    admin_count = manifest.get("admin_l1_count")

    record("CI-MAN-001", isinstance(declared_page_count, int), "MANIFEST_DENOMINATOR", "current_page_count is an integer", declared_page_count)
    record("CI-MAN-002", len(pages) == declared_page_count, "MANIFEST_DENOMINATOR", "current_authority_set.pages equals current_page_count", {"actual": len(pages), "declared": declared_page_count})
    record("CI-MAN-003", len(set(pages)) == len(pages), "MANIFEST_DENOMINATOR", "Page authority paths are unique", pages)
    record("CI-MAN-004", isinstance(front_count, int) and isinstance(admin_count, int) and front_count + admin_count == declared_page_count, "MANIFEST_DENOMINATOR", "front_l1_count + admin_l1_count equals current_page_count", {"front": front_count, "admin": admin_count, "pages": declared_page_count})
    record("CI-MAN-005", str(page_path.relative_to(root)) in pages, "MANIFEST_CLASSIFICATION", "CORE page Authority is classified in pages")
    record("CI-MAN-006", str(canonical_visual_path.relative_to(root)) in registries, "MANIFEST_CLASSIFICATION", "CORE canonical visual identity owner is classified in registries")
    record("CI-MAN-007", str(canonical_visual_path.relative_to(root)) not in pages, "MANIFEST_CLASSIFICATION", "CORE canonical visual identity owner is not misclassified as a page Authority")

    authority_rows = flatten_current_authority_set(manifest)
    path_categories = {}
    for category, rel in authority_rows:
        path_categories.setdefault(rel, []).append(category)
        record("CI-MAT-" + str(len(checks) + 1), (root / rel).is_file(), "CURRENT_AUTHORITY_MATERIALIZATION", f"Current Authority entry {rel} physically exists", {"category": category, "path": rel})
    duplicate_category_paths = {p: cats for p, cats in path_categories.items() if len(cats) > 1}
    record("CI-MAN-008", not duplicate_category_paths, "MANIFEST_CLASSIFICATION", "One physical Authority path is not independently classified into multiple current_authority_set categories", duplicate_category_paths)

    # Core registry content denominators and required fields.
    registry_specs = {
        "sections": ("section_uid", ["section_uid", "name", "responsibility", "visual_uid"]),
        "visuals": ("visual_uid", ["visual_uid", "geometry"]),
        "components": ("component_uid", ["component_uid", "section_uid", "name"]),
        "permissions": ("permission_uid", ["permission_uid", "backend_scope", "purpose"]),
        "gates": ("gate_uid", ["gate_uid", "condition"]),
        "errors": ("error_uid", ["error_uid", "context", "recovery"]),
        "actions": ("action_uid", ["action_uid", "label", "permission_uid", "gate_uid", "effect_type", "owner", "success_contract", "error_uid", "state_effect", "runtime_binding"]),
        "controls": ("control_uid", ["control_uid", "section_uid", "component_uid", "visual_uid", "type", "label", "action_uid", "gate_uid", "permission_uid"]),
        "integration_ports": ("port_uid", ["port_uid", "boundary", "operation", "method_path", "permission", "state_event", "exposure"]),
    }
    parsed = {}
    for name, (uid_key, required_fields) in registry_specs.items():
        rows = regs.get(name) or []
        parsed[name] = rows
        record(f"CI-REG-{name}-001", isinstance(rows, list) and bool(rows), "AUTHORITY_CONTENT", f"{name} registry is non-empty", len(rows) if isinstance(rows, list) else None)
        record(f"CI-REG-{name}-002", unique_rows(rows, uid_key), "AUTHORITY_CONTENT", f"{name} registry has unique non-empty {uid_key}", len(rows) if isinstance(rows, list) else None)
        missing = []
        for row in rows:
            if not isinstance(row, dict):
                missing.append({"row": row, "missing": required_fields})
                continue
            miss = [field for field in required_fields if not nonempty(row.get(field))]
            if miss:
                missing.append({"uid": row.get(uid_key), "missing": miss})
        record(f"CI-REG-{name}-003", not missing, "AUTHORITY_CONTENT", f"{name} rows contain all required semantic fields", missing)

    acceptance = page.get("acceptance") or []
    acceptance_missing = []
    for row in acceptance:
        if not isinstance(row, dict):
            acceptance_missing.append({"row": row})
            continue
        miss = [k for k in ("acceptance_uid", "item", "condition") if not nonempty(row.get(k))]
        if miss:
            acceptance_missing.append({"uid": row.get("acceptance_uid"), "missing": miss})
    record("CI-ACC-001", bool(acceptance) and not acceptance_missing and unique_rows(acceptance, "acceptance_uid"), "AUTHORITY_CONTENT", "Acceptance matrix has unique UID/item/condition content", acceptance_missing)

    sections = parsed["sections"]
    visuals = parsed["visuals"]
    components = parsed["components"]
    permissions = parsed["permissions"]
    gates = parsed["gates"]
    errors = parsed["errors"]
    actions = parsed["actions"]
    controls = parsed["controls"]
    ports = parsed["integration_ports"]

    section_ids = {str(x.get("section_uid")) for x in sections}
    visual_ids = {str(x.get("visual_uid")) for x in visuals}
    component_ids = {str(x.get("component_uid")) for x in components}
    permission_ids = {str(x.get("permission_uid")) for x in permissions}
    gate_ids = {str(x.get("gate_uid")) for x in gates}
    error_ids = {str(x.get("error_uid")) for x in errors}
    action_ids = {str(x.get("action_uid")) for x in actions}
    port_ids = {str(x.get("port_uid")) for x in ports}

    bad_sections = [x.get("section_uid") for x in sections if str(x.get("visual_uid")) not in visual_ids]
    bad_components = [x.get("component_uid") for x in components if str(x.get("section_uid")) not in section_ids]
    bad_controls = []
    for row in controls:
        refs = {
            "section_uid": section_ids,
            "component_uid": component_ids,
            "visual_uid": visual_ids,
            "action_uid": action_ids,
            "gate_uid": gate_ids,
            "permission_uid": permission_ids,
        }
        misses = [key for key, universe in refs.items() if str(row.get(key)) not in universe]
        if misses:
            bad_controls.append({"control_uid": row.get("control_uid"), "unresolved": misses})
    record("CI-REF-001", not bad_sections, "REFERENTIAL_INTEGRITY", "All section visual refs resolve", bad_sections)
    record("CI-REF-002", not bad_components, "REFERENTIAL_INTEGRITY", "All component section refs resolve", bad_components)
    record("CI-REF-003", not bad_controls, "REFERENTIAL_INTEGRITY", "All control section/component/visual/action/gate/permission refs resolve", bad_controls)

    effect_defs = {str(x.get("effect_type")) for x in regs.get("action_effect_types") or [] if isinstance(x, dict)}
    action_ref_failures = []
    action_port_map_authority = {}
    for row in actions:
        uid = str(row.get("action_uid"))
        unresolved = []
        if str(row.get("permission_uid")) not in permission_ids: unresolved.append("permission_uid")
        if str(row.get("gate_uid")) not in gate_ids: unresolved.append("gate_uid")
        if str(row.get("error_uid")) not in error_ids: unresolved.append("error_uid")
        effect = str(row.get("effect_type"))
        if effect not in effect_defs: unresolved.append("effect_type")
        binding = row.get("runtime_binding")
        if not isinstance(binding, dict) or not binding:
            unresolved.append("runtime_binding")
        else:
            if effect in LOCAL_EFFECTS:
                if binding.get("api_required") is not False:
                    unresolved.append("local_effect_api_required_false")
            else:
                port = str(binding.get("port_uid") or "")
                if port not in port_ids:
                    unresolved.append("runtime_binding.port_uid")
                else:
                    action_port_map_authority[uid] = port
                if str(binding.get("binding_kind") or "").startswith("PORT_WITH") and not nonempty(binding.get("payload_rule")):
                    unresolved.append("payload_rule")
        if unresolved:
            action_ref_failures.append({"action_uid": uid, "unresolved": unresolved})
    record("CI-REF-004", not action_ref_failures, "REFERENTIAL_INTEGRITY", "All actions resolve gate/permission/error/effect/runtime bindings with legal N/A evidence", action_ref_failures)

    action_controls = {uid: [] for uid in action_ids}
    for row in controls:
        action_controls.setdefault(str(row.get("action_uid")), []).append(str(row.get("control_uid")))
    unexposed_actions = sorted(uid for uid in action_ids if not action_controls.get(uid))
    record("CI-REF-005", not unexposed_actions, "PAGE_EXPOSURE", "Every page action is exposed by at least one governed control", unexposed_actions)

    port_exposures = []
    used_ports = set(action_port_map_authority.values())
    for port in ports:
        uid = str(port.get("port_uid"))
        if uid == "CORE-01-PORT-PROJECTION":
            continue
        if uid not in used_ports:
            port_exposures.append(uid)
    record("CI-REF-006", not port_exposures, "PAGE_EXPOSURE", "Every non-projection Authority port is consumed by an Authority action runtime binding", port_exposures)

    # Derived self-summary must match physical current content.
    gap = page.get("final_gap_closure") or {}
    derived = (page.get("derived_validation") or {}).get("final_gap_closure") or {}
    count_mismatches = {}
    expected_pairs = [
        ("final_gap_closure.action_runtime_binding_count", gap.get("action_runtime_binding_count"), len(actions)),
        ("final_gap_closure.control_count", gap.get("control_count"), len(controls)),
        ("derived.source_action_count", derived.get("source_action_count"), len(actions)),
        ("derived.source_control_count", derived.get("source_control_count"), len(controls)),
    ]
    for label, claimed, actual in expected_pairs:
        if claimed != actual:
            count_mismatches[label] = {"claimed": claimed, "actual": actual}
    record("CI-DEN-001", not count_mismatches, "DENOMINATOR_INTEGRITY", "Derived/current denominators equal physical Authority rows", count_mismatches)
    record("CI-DEN-002", derived.get("unresolved_control_action_refs") == 0 and derived.get("unbound_actions") == 0, "DENOMINATOR_INTEGRITY", "Authority derived unresolved refs/unbound actions are zero", {"unresolved_control_action_refs": derived.get("unresolved_control_action_refs"), "unbound_actions": derived.get("unbound_actions")})
    record("CI-DEN-003", str(derived.get("action_runtime_binding_coverage")) == f"{len(actions)}/{len(actions)}", "DENOMINATOR_INTEGRITY", "Action runtime coverage denominator matches physical actions", derived.get("action_runtime_binding_coverage"))
    record("CI-DEN-004", str(derived.get("control_runtime_binding_coverage")) == f"{len(controls)}/{len(controls)}", "DENOMINATOR_INTEGRITY", "Control runtime coverage denominator matches physical controls", derived.get("control_runtime_binding_coverage"))

    # Canonical visual content is independently owned and must exactly bind the child visual universe.
    current_visual = canonical_visual.get("current_canonical_visual") or {}
    visual_refs = set(map(str, current_visual.get("visual_registry_refs") or []))
    child_contract = canonical_visual.get("child_visual_contract") or {}
    record("CI-VIS-001", visual_refs == visual_ids, "VISUAL_CONTENT", "Canonical visual baseline refs exactly equal page visual registry UIDs", {"baseline": sorted(visual_refs), "page": sorted(visual_ids)})
    record("CI-VIS-002", child_contract.get("count") == len(visuals), "VISUAL_CONTENT", "Canonical visual child count equals physical visual registry count", {"claimed": child_contract.get("count"), "actual": len(visuals)})
    if not (current_visual.get("current_visual_assets") or []):
        record("CI-VIS-003", str(current_visual.get("asset_binding_status")) == "NOT_APPLICABLE_NO_PAGE_LEVEL_STATIC_VISUAL_ASSET", "VISUAL_CONTENT", "Empty page-level visual asset set has explicit Authority N/A evidence", current_visual.get("asset_binding_status"))

    # Implementation symmetry.
    contract_source = text(runtime_contract_path)
    impl_sets = {
        "actions": ts_string_array(contract_source, "CORE_ACTION_UIDS"),
        "gates": ts_string_array(contract_source, "CORE_GATE_UIDS"),
        "permissions": ts_string_array(contract_source, "CORE_PERMISSION_UIDS"),
        "ports": ts_string_array(contract_source, "CORE_PORT_UIDS"),
    }
    auth_sets = {
        "actions": action_ids,
        "gates": gate_ids,
        "permissions": permission_ids,
        "ports": port_ids,
    }
    for kind, impl in impl_sets.items():
        record(f"CI-IMPL-{kind}-PARSE", impl is not None, "IMPLEMENTATION_ENCODING", f"Parse {kind} implementation registry from coreRuntimeContract.ts")
        if impl is None:
            continue
        impl_set = set(map(str, impl))
        missing = sorted(auth_sets[kind] - impl_set)
        extra = sorted(impl_set - auth_sets[kind])
        record(f"CI-IMPL-{kind}-MISS", not missing, "AUTHORITY_TO_IMPLEMENTATION", f"Every Authority {kind} UID exists in implementation registry", missing)
        record(f"CI-IMPL-{kind}-EXTRA", not extra, "IMPLEMENTATION_TO_AUTHORITY", f"Implementation {kind} registry contains no unlisted CORE page capability", extra)

    impl_action_port = ts_action_port_map(contract_source)
    impl_method_path = ts_port_method_path(contract_source)
    record("CI-IMPL-MAP-001", impl_action_port is not None, "IMPLEMENTATION_ENCODING", "CORE_ACTION_PORT mapping parses")
    record("CI-IMPL-MAP-002", impl_method_path is not None, "IMPLEMENTATION_ENCODING", "CORE_PORT_METHOD_PATH mapping parses")
    if impl_action_port is not None:
        mapping_fail = []
        for action_uid, port_uid in action_port_map_authority.items():
            if impl_action_port.get(action_uid) != port_uid:
                mapping_fail.append({"action_uid": action_uid, "authority_port": port_uid, "implementation_port": impl_action_port.get(action_uid)})
        extra_action_map = sorted(set(impl_action_port) - action_ids)
        record("CI-IMPL-MAP-003", not mapping_fail, "AUTHORITY_TO_IMPLEMENTATION", "Effectful/read Authority action-to-port mappings exactly match implementation", mapping_fail)
        record("CI-IMPL-MAP-004", not extra_action_map, "IMPLEMENTATION_TO_AUTHORITY", "Implementation action-to-port map has no unlisted page actions", extra_action_map)

    port_by_uid = {str(x.get("port_uid")): x for x in ports}
    if impl_method_path is not None:
        method_path_fail = []
        for uid, row in port_by_uid.items():
            method_path = str(row.get("method_path") or "")
            parts = method_path.split(" ", 1)
            expected = {"method": parts[0], "path": parts[1]} if len(parts) == 2 else None
            if expected is None or impl_method_path.get(uid) != expected:
                method_path_fail.append({"port_uid": uid, "authority": expected, "implementation": impl_method_path.get(uid)})
        record("CI-IMPL-MAP-005", not method_path_fail, "AUTHORITY_TO_IMPLEMENTATION", "Authority port method/path exactly matches runtime contract", method_path_fail)

    # UI physical materialization.
    visual_source = text(visual_impl_path)
    missing_control_dom = sorted(uid for uid in {str(x.get("control_uid")) for x in controls} if uid not in visual_source)
    record("CI-UI-001", not missing_control_dom, "PHYSICAL_UI_CONTENT", "Every Authority control UID is physically represented in CoreVisual implementation", missing_control_dom)

    # Route physical materialization for every Authority integration port.
    route_files = list((root / "src/app/v1").rglob("route.ts"))
    route_texts = {str(p.relative_to(root)): text(p) for p in route_files}
    route_fail = []
    for uid, row in port_by_uid.items():
        method = str(row.get("method_path") or "").split(" ", 1)[0]
        operation = str(row.get("operation") or "")
        if uid == "CORE-01-PORT-PROJECTION":
            rel = "src/app/v1/ui-projections/[pageUid]/route.ts"
            source = route_texts.get(rel, "")
            if not source or "getUiProjection" not in source or f"export async function {method}" not in source:
                route_fail.append({"port_uid": uid, "expected_route": rel, "reason": "PROJECTION_ROUTE_NOT_MATERIALIZED"})
            continue
        candidates = [(rel, src) for rel, src in route_texts.items() if uid in src]
        if not candidates:
            route_fail.append({"port_uid": uid, "reason": "NO_ROUTE_REFERENCES_PORT"})
            continue
        if not any((f"createCore{method.title()}Route" in src or f"export async function {method}" in src or f"export const {method}" in src) for _, src in candidates):
            route_fail.append({"port_uid": uid, "routes": [rel for rel, _ in candidates], "reason": "HTTP_METHOD_NOT_EXPORTED"})
        if not operation:
            route_fail.append({"port_uid": uid, "reason": "OPERATION_EMPTY"})
    record("CI-ROUTE-001", not route_fail, "API_PHYSICAL_MATERIALIZATION", "Every Authority integration port has a physical HTTP route with the required method", route_fail)

    # Shared transport/runtime enforcement used by every CORE route.
    route_factory = text(core_route_factory_path)
    core_runtime = text(core_runtime_path)
    production_runtime = text(production_runtime_path)
    identity_runtime = text(identity_runtime_path)
    server_corpus = "\n".join(
        text(p) for p in (root / "src/server").rglob("*.ts")
        if p.is_file()
    )
    record("CI-RUNTIME-001", all(tok in route_factory for tok in ("x-correlation-id", "executeCorePort", "INVALID_JSON_PAYLOAD", "ACTION_PORT_BINDING_MISMATCH")), "RUNTIME_CHAIN", "Core route boundary validates correlation, JSON and action/port binding")
    record("CI-RUNTIME-002", all(tok in core_runtime for tok in ('outcome: "DENIED"', 'outcome: "ALLOWED"', 'outcome: "SUCCESS"', 'outcome: "ERROR"', "runtime.authorize", "runtime.execute", "runtime.audit")), "AUDIT_CHAIN", "Core runtime wraps authorization/execution with DENIED/ALLOWED/SUCCESS/ERROR audit outcomes")
    record("CI-RUNTIME-003", "account_permission_assignments" in identity_runtime and "permission_resources" in identity_runtime and "PERMISSION_OR_SCOPE_DENIED" in identity_runtime, "PERMISSION_CHAIN", "Production identity runtime resolves permission resources and fails closed")
    record("CI-RUNTIME-004", "runRlsActorTransaction" in production_runtime or "runRlsActorQuery" in production_runtime, "DATA_CHAIN", "Production CORE runtime uses session-bound RLS data owner")
    record("CI-RUNTIME-005", "TEST_ONLY" not in production_runtime, "DATA_CHAIN", "Production CORE runtime does not embed TEST_ONLY fixture payloads")

    # Each action receives a functional content chain row; incomplete rows block.
    errors_by_uid = {str(x.get("error_uid")): x for x in errors}
    controls_by_action = {}
    for control in controls:
        controls_by_action.setdefault(str(control.get("action_uid")), []).append(str(control.get("control_uid")))
    for action in actions:
        uid = str(action.get("action_uid"))
        effect = str(action.get("effect_type"))
        binding = action.get("runtime_binding") or {}
        port_uid = str(binding.get("port_uid") or "")
        port = port_by_uid.get(port_uid)
        error = errors_by_uid.get(str(action.get("error_uid"))) or {}
        is_local = effect in LOCAL_EFFECTS
        operation = str((port or {}).get("operation") or "")
        nodes = {
            "control": bool(controls_by_action.get(uid)),
            "gate": str(action.get("gate_uid")) in gate_ids,
            "permission": str(action.get("permission_uid")) in permission_ids,
            "action": nonempty(action.get("label")) and nonempty(action.get("owner")),
            "validation": nonempty(next((g.get("condition") for g in gates if str(g.get("gate_uid")) == str(action.get("gate_uid"))), None)),
            "payload": bool(binding.get("api_required") is False) if is_local else (nonempty(binding.get("payload_rule")) or bool(port)),
            "api_entry": bool(binding.get("api_required") is False) if is_local else bool(port),
            "runtime_owner": bool(binding.get("api_required") is False) if is_local else (operation in server_corpus),
            "repository_data_provider": bool(binding.get("api_required") is False) if is_local else (operation in server_corpus and ("runRlsActor" in server_corpus or "executeProductionConversationTurn" in server_corpus)),
            "audit_event": bool(binding.get("api_required") is False) if is_local else ("runtime.audit" in core_runtime and "correlation_id" in route_factory),
            "response": nonempty(action.get("success_contract")),
            "ui_feedback": nonempty(action.get("state_effect")),
            "success_state": nonempty(action.get("success_contract")),
            "next_state": nonempty(action.get("state_effect")) and (is_local or nonempty((port or {}).get("state_event"))),
            "failure_state": nonempty(error.get("context")),
            "retry_recovery_rollback": nonempty(error.get("recovery")),
        }
        incomplete = sorted(k for k, ok in nodes.items() if not ok)
        chain_rows.append({
            "action_uid": uid,
            "effect_type": effect,
            "control_uids": controls_by_action.get(uid) or [],
            "port_uid": port_uid or None,
            "operation": operation or None,
            "nodes": nodes,
            "complete": not incomplete,
            "incomplete_nodes": incomplete,
        })
    incomplete_chains = [x for x in chain_rows if not x["complete"]]
    record("CI-CHAIN-001", not incomplete_chains, "FUNCTIONAL_CHAIN_CONTENT", "Every Authority action has a complete semantic chain or exact local N/A evidence", incomplete_chains)

    # Page hard lock and known materialization contract must not be contradicted by implementation.
    authority_text = text(page_path)
    record("CI-HARDLOCK-001", "No unlisted Section/Component/Control/Action/State/Gate/Permission/Port/Business Sample Data." in authority_text, "AUTHORITY_HARD_LOCK", "CORE Authority explicitly forbids unlisted governed units")
    authoring = page.get("canonical_production_script_authoring_contract") or {}
    candidate_binding = authoring.get("candidate_and_materialization_binding") or {}
    if candidate_binding:
        no_new_ui = candidate_binding.get("new_ui_action") is False
        no_new_endpoint = candidate_binding.get("new_endpoint_in_this_authority") is False
        record("CI-CANON-001", no_new_ui and no_new_endpoint, "CANONICAL_SCRIPT_AUTHORITY", "Canonical Script materialization contract explicitly forbids new page UI action/endpoint", {"new_ui_action": candidate_binding.get("new_ui_action"), "new_endpoint_in_this_authority": candidate_binding.get("new_endpoint_in_this_authority")})
        impl_actions = set(impl_sets.get("actions") or [])
        impl_ports = set(impl_sets.get("ports") or [])
        contradiction = []
        if "CORE-01-ACT-CANONICAL-SCRIPT-CREATE" in impl_actions and no_new_ui:
            contradiction.append("CORE-01-ACT-CANONICAL-SCRIPT-CREATE")
        if "CORE-01-PORT-CANONICAL-SCRIPT-CREATE" in impl_ports and no_new_endpoint:
            contradiction.append("CORE-01-PORT-CANONICAL-SCRIPT-CREATE")
        record("CI-CANON-002", not contradiction, "IMPLEMENTATION_TO_AUTHORITY", "Canonical Script implementation does not create page action/endpoint forbidden by Current page Authority", contradiction)

    page_source_path = root / "src/app/core/page.tsx"
    if page_source_path.is_file():
        page_source = text(page_source_path)
        hard_counts = {}
        ma = re.search(r"CORE_ACTION_UIDS\.length\s*!==\s*(\d+)", page_source)
        mp = re.search(r"CORE_PORT_UIDS\.length\s*!==\s*(\d+)", page_source)
        if ma: hard_counts["actions"] = int(ma.group(1))
        if mp: hard_counts["ports"] = int(mp.group(1))
        mismatches = {}
        if "actions" in hard_counts and hard_counts["actions"] != len(actions):
            mismatches["actions"] = {"hardcoded": hard_counts["actions"], "authority": len(actions)}
        if "ports" in hard_counts and hard_counts["ports"] != len(ports):
            mismatches["ports"] = {"hardcoded": hard_counts["ports"], "authority": len(ports)}
        record("CI-DEN-005", not mismatches, "CONSUMER_LOCAL_DENOMINATOR", "Page implementation does not preserve a stale hardcoded Authority denominator", mismatches)

    blocker_findings = [x for x in findings if x.get("severity") == "BLOCKER"]
    payload = {
        "artifact_type": "NON_NORMATIVE_CORE01_SOURCE_CONTENT_INTEGRITY_REPORT",
        "page_uid": "CORE-01",
        "content_complete": not blocker_findings,
        "result": "PASS" if not blocker_findings else "BLOCKED",
        "check_total": len(checks),
        "pass_total": sum(1 for x in checks if x["result"] == "PASS"),
        "fail_total": len(findings),
        "blocker_total": len(blocker_findings),
        "content_denominators": {
            "manifest_pages": len(pages),
            "manifest_registries": len(registries),
            "sections": len(sections),
            "visuals": len(visuals),
            "components": len(components),
            "permissions": len(permissions),
            "gates": len(gates),
            "errors": len(errors),
            "actions": len(actions),
            "controls": len(controls),
            "integration_ports": len(ports),
            "acceptance_items": len(acceptance),
            "functional_chains": len(chain_rows),
            "functional_chains_complete": sum(1 for x in chain_rows if x["complete"]),
            "functional_chains_incomplete": len(incomplete_chains),
        },
        "bidirectional_set_differences": {kind: set_differences(auth_sets[kind], impl_sets.get(kind) or []) for kind in auth_sets},
        "functional_chains": chain_rows,
        "checks": checks,
        "findings": findings,
        "product_stage_credit": 0,
        "product_authority_mutated": False,
        "mother_mutated": False,
        "current_specification_mutated": False,
        "common_content_integrity_engine": "governance/ci/content_integrity_engine.py",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": payload["result"],
        "content_complete": payload["content_complete"],
        "check_total": payload["check_total"],
        "pass_total": payload["pass_total"],
        "blocker_total": payload["blocker_total"],
        "functional_chains": payload["content_denominators"]["functional_chains"],
        "functional_chains_complete": payload["content_denominators"]["functional_chains_complete"],
    }, ensure_ascii=False, indent=2))
    if blocker_findings:
        for item in blocker_findings:
            print("CONTENT_BLOCKER", item["check_uid"], item["category"], json.dumps(item.get("evidence"), ensure_ascii=False))
        raise SystemExit(2)

if __name__ == "__main__":
    main()
