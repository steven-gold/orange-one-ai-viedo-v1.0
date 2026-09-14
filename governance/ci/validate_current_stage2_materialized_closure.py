#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "00_SOURCE_INTAKE/fresh_run_003"
OUT = RUN / "04_PAGE_FUNCTIONAL_CONTRACT"
RECEIPT = ROOT / "governance/test/stage02/STAGE02_MATERIAL_REMEDIATION_RECEIPT_R1.yaml"
PAGES = {
    "CORE-01": {
        "raw": RUN / "00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml",
        "blueprint": RUN / "02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml",
        "ai": True,
    },
    "ASSET-01": {
        "raw": RUN / "00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml",
        "blueprint": RUN / "02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml",
        "ai": False,
    },
}
REQUIRED_PAGE_FILES = [
    "BUSINESS_ENTITY_INVENTORY.yaml",
    "BUSINESS_ENTITY_OPERATION_MATRIX.yaml",
    "ENTITY_HIERARCHY_MATRIX.yaml",
    "FUNCTIONAL_WORKBENCH_CONTRACT.yaml",
    "INTERACTION_TOPOLOGY_SPEC.yaml",
    "FUNCTION_VISUAL_IMPACT_MATRIX.yaml",
    "FUNCTIONAL_CHAIN_SPEC.yaml",
    "PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml",
]
REQUIRED_ROOT_FILES = ["DEPENDENCY_MAP.yaml", "ASYNC_PROVIDER_CONTRACT.yaml", "SHARED_OWNER_PORT_MAP.yaml"]
EXPECTED_GAPS = {f"GAP-{i:03}" for i in range(1, 9)}
errors = []


def load(path: Path):
    if not path.is_file():
        errors.append(f"MISSING_FILE:{path.relative_to(ROOT)}")
        return {}
    try:
        obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        errors.append(f"PARSE_ERROR:{path.relative_to(ROOT)}:{exc!r}")
        return {}
    if not isinstance(obj, dict):
        errors.append(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
        return {}
    return obj


def uidset(items, key):
    return {x.get(key) for x in (items or []) if isinstance(x, dict) and x.get(key)}


if not OUT.is_dir():
    errors.append("STAGE02_PRODUCT_ROOT_MISSING")

all_blueprint_gaps = set()
expected_shared = set()
expected_ports = set()
for page_uid, cfg in PAGES.items():
    raw = load(cfg["raw"])
    blueprint = load(cfg["blueprint"])
    reg = raw.get("registries") or {}
    raw_objects = uidset(reg.get("objects_refs"), "object_uid")
    raw_actions = uidset(reg.get("actions"), "action_uid")
    raw_controls = uidset(reg.get("controls"), "control_uid")
    raw_sections = uidset(reg.get("sections"), "section_uid")
    raw_components = uidset(reg.get("components"), "component_uid")
    raw_visuals = uidset(reg.get("visuals"), "visual_uid")
    raw_gates = uidset(reg.get("gates"), "gate_uid")
    raw_permissions = uidset(reg.get("permissions"), "permission_uid")
    raw_ports = uidset(reg.get("integration_ports"), "port_uid")
    expected_ports |= {(page_uid, x) for x in raw_ports}
    refs = blueprint.get("unresolved_external_authority_refs") or []
    bp_gaps = {x.get("gap_uid") for x in refs if isinstance(x, dict) and x.get("gap_uid")}
    all_blueprint_gaps |= bp_gaps

    for action in reg.get("actions") or []:
        if not isinstance(action, dict):
            continue
        rb = action.get("runtime_binding") or {}
        if rb.get("binding_kind") == "SHARED_OPERATION_REFERENCE":
            expected_shared.add((page_uid, action.get("action_uid"), rb.get("shared_authority_id"), rb.get("shared_operation_id")))

    page_dir = OUT / page_uid
    for name in REQUIRED_PAGE_FILES:
        if not (page_dir / name).is_file():
            errors.append(f"{page_uid}:MISSING_REQUIRED_STAGE2_ARTIFACT:{name}")
    ai_file = page_dir / "AI_INTERACTION_CONTINUITY_CONTRACT.yaml"
    if cfg["ai"] and not ai_file.is_file():
        errors.append(f"{page_uid}:AI_CONTINUITY_CONTRACT_MISSING")
    if not cfg["ai"] and ai_file.exists():
        errors.append(f"{page_uid}:NON_AI_PAGE_MUST_NOT_HAVE_AI_CONTINUITY_CONTRACT")

    inventory = load(page_dir / "BUSINESS_ENTITY_INVENTORY.yaml")
    inv_objects = uidset(inventory.get("entities"), "object_uid")
    if inv_objects != raw_objects:
        errors.append(f"{page_uid}:ENTITY_INVENTORY_UID_DRIFT:expected={len(raw_objects)} actual={len(inv_objects)}")
    if inventory.get("entity_count") != len(raw_objects):
        errors.append(f"{page_uid}:ENTITY_INVENTORY_COUNT_DRIFT")
    inv_gaps = {x.get("gap_uid") for x in inventory.get("unresolved_external_authority_refs") or [] if isinstance(x, dict)}
    if inv_gaps != bp_gaps:
        errors.append(f"{page_uid}:ENTITY_INVENTORY_EXTERNAL_GAP_DRIFT")
    for ref in inventory.get("unresolved_external_authority_refs") or []:
        if any(ref.get(k) is not False for k in ("resolved", "satisfied", "auto_filled", "inferred")):
            errors.append(f"{page_uid}:FALSE_EXTERNAL_AUTHORITY_RESOLUTION:{ref.get('gap_uid')}")

    op = load(page_dir / "BUSINESS_ENTITY_OPERATION_MATRIX.yaml")
    op_actions = uidset(op.get("operations"), "action_uid")
    if op_actions != raw_actions:
        errors.append(f"{page_uid}:OPERATION_MATRIX_ACTION_UID_DRIFT")
    if op.get("semantic_entity_join_used") is not False:
        errors.append(f"{page_uid}:SEMANTIC_ENTITY_JOIN_MUST_BE_FALSE")
    for row in op.get("operations") or []:
        if set(row.get("control_uids") or []) - raw_controls:
            errors.append(f"{page_uid}:OPERATION_MATRIX_UNKNOWN_CONTROL:{row.get('action_uid')}")
        if set(row.get("section_uids") or []) - raw_sections:
            errors.append(f"{page_uid}:OPERATION_MATRIX_UNKNOWN_SECTION:{row.get('action_uid')}")
        if set(row.get("component_uids") or []) - raw_components:
            errors.append(f"{page_uid}:OPERATION_MATRIX_UNKNOWN_COMPONENT:{row.get('action_uid')}")
        if set(row.get("visual_uids") or []) - raw_visuals:
            errors.append(f"{page_uid}:OPERATION_MATRIX_UNKNOWN_VISUAL:{row.get('action_uid')}")
        if row.get("object_uid_bindings") not in ([], None):
            errors.append(f"{page_uid}:OPERATION_MATRIX_INVENTED_OBJECT_BINDING:{row.get('action_uid')}")

    hierarchy = load(page_dir / "ENTITY_HIERARCHY_MATRIX.yaml")
    hierarchy_objects = uidset(hierarchy.get("rows"), "object_uid")
    if hierarchy_objects != raw_objects:
        errors.append(f"{page_uid}:HIERARCHY_OBJECT_UID_DRIFT")
    if hierarchy.get("semantic_parent_inference_used") is not False:
        errors.append(f"{page_uid}:HIERARCHY_SEMANTIC_INFERENCE_MUST_BE_FALSE")
    for row in hierarchy.get("rows") or []:
        if row.get("parent_object_uid") is not None:
            errors.append(f"{page_uid}:PARENT_OBJECT_UID_NOT_AUTHORIZED:{row.get('object_uid')}")

    workbench = load(page_dir / "FUNCTIONAL_WORKBENCH_CONTRACT.yaml")
    wb_sections = {x.get("section_uid") for x in workbench.get("workbenches") or [] if isinstance(x, dict)}
    if wb_sections != raw_sections:
        errors.append(f"{page_uid}:WORKBENCH_SECTION_DENOMINATOR_DRIFT")
    for row in workbench.get("workbenches") or []:
        if row.get("workbench_class") != "SAME_SURFACE_CLUSTER" or row.get("classification_basis") != "EXACT_SECTION_UID_MEMBERSHIP":
            errors.append(f"{page_uid}:WORKBENCH_UNBOUNDED_CLASSIFICATION:{row.get('section_uid')}")
        if set(row.get("component_uids") or []) - raw_components:
            errors.append(f"{page_uid}:WORKBENCH_UNKNOWN_COMPONENT:{row.get('section_uid')}")
        if set(row.get("control_uids") or []) - raw_controls:
            errors.append(f"{page_uid}:WORKBENCH_UNKNOWN_CONTROL:{row.get('section_uid')}")

    topology = load(page_dir / "INTERACTION_TOPOLOGY_SPEC.yaml")
    nodes = topology.get("nodes") or {}
    expected_nodes = {
        "sections": raw_sections,
        "components": raw_components,
        "controls": raw_controls,
        "actions": raw_actions,
        "gates": raw_gates,
        "permissions": raw_permissions,
        "visuals": raw_visuals,
    }
    for kind, expected in expected_nodes.items():
        if set(nodes.get(kind) or []) != expected:
            errors.append(f"{page_uid}:TOPOLOGY_{kind.upper()}_DRIFT")
    if topology.get("semantic_edge_inference_used") is not False:
        errors.append(f"{page_uid}:TOPOLOGY_SEMANTIC_INFERENCE_MUST_BE_FALSE")

    visual = load(page_dir / "FUNCTION_VISUAL_IMPACT_MATRIX.yaml")
    if uidset(visual.get("rows"), "action_uid") != raw_actions:
        errors.append(f"{page_uid}:VISUAL_IMPACT_ACTION_DENOMINATOR_DRIFT")
    for row in visual.get("rows") or []:
        for binding in row.get("bindings") or []:
            if binding.get("control_uid") not in raw_controls:
                errors.append(f"{page_uid}:VISUAL_IMPACT_UNKNOWN_CONTROL:{row.get('action_uid')}")
            if binding.get("visual_uid") not in raw_visuals:
                errors.append(f"{page_uid}:VISUAL_IMPACT_UNKNOWN_VISUAL:{row.get('action_uid')}")

    chain = load(page_dir / "FUNCTIONAL_CHAIN_SPEC.yaml")
    projection = chain.get("source_projection") or {}
    if uidset(projection.get("actions"), "action_uid") != raw_actions:
        errors.append(f"{page_uid}:FUNCTIONAL_CHAIN_ACTION_DRIFT")
    if uidset(projection.get("controls"), "control_uid") != raw_controls:
        errors.append(f"{page_uid}:FUNCTIONAL_CHAIN_CONTROL_DRIFT")
    if uidset(projection.get("integration_ports"), "port_uid") != raw_ports:
        errors.append(f"{page_uid}:FUNCTIONAL_CHAIN_PORT_DRIFT")
    if chain.get("missing_exact_contract_fields_auto_filled") is not False:
        errors.append(f"{page_uid}:FUNCTIONAL_CHAIN_AUTOFILL_MUST_BE_FALSE")

    package = load(page_dir / "PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml")
    if package.get("frozen_governance_uid") is None:
        errors.append(f"{page_uid}:PACKAGE_FROZEN_UID_MISSING")
    if package.get("stage_exit_claimed") is not False:
        errors.append(f"{page_uid}:PACKAGE_MUST_NOT_CLAIM_STAGE_EXIT")
    if package.get("external_authority_resolution_performed") is not False:
        errors.append(f"{page_uid}:PACKAGE_EXTERNAL_AUTHORITY_RESOLUTION_FORBIDDEN")

    if cfg["ai"]:
        ai = load(ai_file)
        if ai.get("conversation_policy") != raw.get("conversation_policy"):
            errors.append(f"{page_uid}:AI_CONTINUITY_POLICY_NOT_EXACT_COPY")
        if ai.get("semantic_ai_route_completion_used") is not False:
            errors.append(f"{page_uid}:AI_ROUTE_INFERENCE_MUST_BE_FALSE")

for name in REQUIRED_ROOT_FILES:
    if not (OUT / name).is_file():
        errors.append(f"MISSING_REQUIRED_STAGE2_ROOT_ARTIFACT:{name}")

dep = load(OUT / "DEPENDENCY_MAP.yaml")
if set(dep.get("external_authority_union") or []) != EXPECTED_GAPS:
    errors.append("DEPENDENCY_MAP_EXTERNAL_GAP_UNION_DRIFT")
if dep.get("external_authority_auto_resolution") is not False:
    errors.append("DEPENDENCY_MAP_EXTERNAL_AUTOREsolve_FORBIDDEN")

async_contract = load(OUT / "ASYNC_PROVIDER_CONTRACT.yaml")
actual_ports = {(x.get("page_uid"), x.get("port_uid")) for x in async_contract.get("ports") or [] if isinstance(x, dict)}
if actual_ports != expected_ports:
    errors.append(f"ASYNC_PROVIDER_PORT_DENOMINATOR_DRIFT:expected={len(expected_ports)} actual={len(actual_ports)}")
if async_contract.get("provider_route_inference_used") is not False:
    errors.append("ASYNC_PROVIDER_ROUTE_INFERENCE_MUST_BE_FALSE")

shared = load(OUT / "SHARED_OWNER_PORT_MAP.yaml")
actual_shared = {(x.get("page_uid"), x.get("action_uid"), x.get("shared_authority_id"), x.get("shared_operation_id")) for x in shared.get("bindings") or [] if isinstance(x, dict)}
if actual_shared != expected_shared:
    errors.append(f"SHARED_OWNER_BINDING_DRIFT:expected={len(expected_shared)} actual={len(actual_shared)}")
if shared.get("external_authority_resolution_performed") is not False:
    errors.append("SHARED_OWNER_EXTERNAL_RESOLUTION_FORBIDDEN")

if all_blueprint_gaps != EXPECTED_GAPS:
    errors.append(f"BLUEPRINT_EXTERNAL_AUTHORITY_UNION_DRIFT:{sorted(all_blueprint_gaps)}")

receipt = load(RECEIPT)
if receipt.get("materialized_missing_artifact_blocker_count") != 13:
    errors.append("REMEDIATION_RECEIPT_BLOCKER_DENOMINATOR_DRIFT")
if receipt.get("claimed_legal_elimination_before_fresh_reexecution") != 0:
    errors.append("REMEDIATION_RECEIPT_PREMATURE_ELIMINATION_CLAIM")
if receipt.get("functional_gap_elimination_claimed") != 0:
    errors.append("REMEDIATION_RECEIPT_PREMATURE_FUNCTIONAL_GAP_CLAIM")
if set(receipt.get("external_authority_union_preserved_unresolved") or []) != EXPECTED_GAPS:
    errors.append("REMEDIATION_RECEIPT_EXTERNAL_GAP_UNION_DRIFT")
for field in ("current_specification_mutated", "stage1_immutable_inputs_mutated", "ai_autofill_used", "semantic_inference_for_missing_authority_used"):
    if receipt.get(field) is not False:
        errors.append(f"REMEDIATION_RECEIPT_FORBIDDEN_FLAG:{field}")

if (OUT / "EXTERNAL_AUTHORITY").exists():
    errors.append("STALE_EXTERNAL_AUTHORITY_MATERIALIZATION_FORBIDDEN")

if errors:
    for error in errors:
        print("BLOCK:", error, file=sys.stderr)
    raise SystemExit(1)

print("PASS: Stage-02 materialized structural product root is present and source-bounded")
print("PASS: entity/action/control/section/component/visual/port denominators match immutable Stage-01 registries")
print("PASS: 13 missing-artifact blockers have owning-layer artifacts; zero legal elimination is claimed before fresh reexecution")
print("PASS: GAP-001..GAP-008 remain unresolved and no stale EXTERNAL_AUTHORITY tree was restored")
print("PASS: no semantic authority completion, AI autofill, or invented object-parent binding is present")
