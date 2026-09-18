#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "00_SOURCE_INTAKE/fresh_run_003"
OUT = RUN / "04_PAGE_FUNCTIONAL_CONTRACT"
STATE = ROOT / "governance/test/ACTIVE_STATE.yaml"
FREEZE = ROOT / "governance/test/stage02/STAGE02_STAGE_FROZEN_GOVERNANCE_RECEIPT.yaml"
EVIDENCE = ROOT / "governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json"
RECEIPT = ROOT / "governance/test/stage02/STAGE02_MATERIAL_REMEDIATION_RECEIPT_R1.yaml"

PAGES = {
    "CORE-01": {
        "raw": RUN / "00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml",
        "blueprint": RUN / "02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml",
        "ai_continuity_required": True,
    },
    "ASSET-01": {
        "raw": RUN / "00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml",
        "blueprint": RUN / "02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml",
        "ai_continuity_required": False,
    },
}

PAGE_ARTIFACTS = [
    "BUSINESS_ENTITY_INVENTORY.yaml",
    "BUSINESS_ENTITY_OPERATION_MATRIX.yaml",
    "ENTITY_HIERARCHY_MATRIX.yaml",
    "FUNCTIONAL_WORKBENCH_CONTRACT.yaml",
    "INTERACTION_TOPOLOGY_SPEC.yaml",
    "FUNCTION_VISUAL_IMPACT_MATRIX.yaml",
    "FUNCTIONAL_CHAIN_SPEC.yaml",
    "PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml",
]
SHARED_ARTIFACTS = ["DEPENDENCY_MAP.yaml", "ASYNC_PROVIDER_CONTRACT.yaml", "SHARED_OWNER_PORT_MAP.yaml"]
EXPECTED_GAPS = {f"GAP-{i:03}" for i in range(1, 9)}


def die(msg: str) -> None:
    print("BLOCK:", msg, file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> dict:
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    try:
        obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        die(f"PARSE:{path.relative_to(ROOT)}:{exc!r}")
    if not isinstance(obj, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def dump(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=140), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def index(items, key):
    return {x.get(key): x for x in (items or []) if isinstance(x, dict) and x.get(key)}


def git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()


def external_refs(blueprint: dict):
    refs = []
    for ref in blueprint.get("unresolved_external_authority_refs") or []:
        refs.append({
            "gap_uid": ref.get("gap_uid"),
            "authority_ref": ref.get("authority_ref"),
            "resolved": False,
            "satisfied": False,
            "auto_filled": False,
            "inferred": False,
            "source_evidence_ref": ref.get("authority_evidence_ref"),
        })
    return refs


def port_refs(action: dict):
    rb = action.get("runtime_binding") or {}
    result = []
    for field in ("port_uid", "persist_via_port_uid", "execute_port_uid", "decision_port_uid"):
        value = rb.get(field)
        if value:
            result.append({"field": field, "port_uid": value})
    return result


state = load(STATE)
freeze = load(FREEZE)
evidence = load(EVIDENCE)
execution = state.get("execution") or {}
active = state.get("stage02_active_attempt") or {}
if execution.get("current_stage") != "STAGE-02-TESTED-BLOCKED":
    die(f"CURRENT_STAGE_NOT_STAGE02_TESTED_BLOCKED:{execution.get('current_stage')!r}")
if (execution.get("stage2") or {}).get("result") != "TEST_EXECUTED_BLOCKED":
    die("STAGE02_RESULT_NOT_TEST_EXECUTED_BLOCKED")
if freeze.get("stage_uid") != "STAGE-02" or not freeze.get("frozen_governance_uid"):
    die("FROZEN_GOVERNANCE_RECEIPT_INVALID")
if evidence.get("stage_uid") != "STAGE-02" or evidence.get("result") != "BLOCKED" or evidence.get("stage_exit_allowed") is not False:
    die("CURRENT_STAGE02_EVIDENCE_NOT_BLOCKED")
if not active:
    die("CURRENT_STAGE02_ACTIVE_ATTEMPT_MISSING")
if freeze.get("attempt_uid") != active.get("attempt_uid"):
    die(f"CURRENT_ATTEMPT_FREEZE_DRIFT:freeze={freeze.get('attempt_uid')!r}:active={active.get('attempt_uid')!r}")
if freeze.get("frozen_governance_uid") != active.get("frozen_governance_uid"):
    die("CURRENT_GOVERNANCE_FREEZE_DRIFT")
if active.get("frozen_governance_uid") != state.get("specification_uid"):
    die("CURRENT_ACTIVE_ATTEMPT_GOVERNANCE_UID_DRIFT")
if evidence.get("source_head_sha") != active.get("source_execution_sha"):
    die(f"CURRENT_EVIDENCE_SOURCE_SHA_DRIFT:evidence={evidence.get('source_head_sha')!r}:active={active.get('source_execution_sha')!r}")

target_page_uids = list(evidence.get("target_pages") or execution.get("target_pages") or [])
if not target_page_uids or len(target_page_uids) != len(set(target_page_uids)):
    die(f"CURRENT_TARGET_PAGE_SCOPE_INVALID:{target_page_uids!r}")
unknown_target_pages = sorted(set(target_page_uids) - set(PAGES))
if unknown_target_pages:
    die(f"CURRENT_TARGET_PAGE_SCOPE_UNKNOWN:{unknown_target_pages!r}")
target_pages = {uid: PAGES[uid] for uid in target_page_uids}
expected_closure_blockers = sum(7 if cfg["ai_continuity_required"] else 6 for cfg in target_pages.values())
expected_external = set(evidence.get("preserved_external_authority_union_gap_uids") or [])
if not expected_external or not expected_external.issubset(EXPECTED_GAPS):
    die(f"CURRENT_EXTERNAL_AUTHORITY_SCOPE_INVALID:{sorted(expected_external)!r}")

before_functional_gaps = int(evidence.get("fresh_functional_gap_total") or 0)
before_closure_blockers = int(evidence.get("closure_blocker_total") or 0)
if before_functional_gaps != int(active.get("fresh_functional_gap_total") or 0):
    die("CURRENT_FUNCTIONAL_GAP_COUNT_DRIFT")
if before_closure_blockers != int(active.get("fresh_closure_blocker_total") or 0):
    die("CURRENT_CLOSURE_BLOCKER_COUNT_DRIFT")
if before_closure_blockers != expected_closure_blockers:
    die(f"STRUCTURAL_MATERIALIZATION_DENOMINATOR_DRIFT:expected={expected_closure_blockers}:actual={before_closure_blockers}")
if OUT.exists():
    die("STAGE02_PRODUCT_ROOT_ALREADY_EXISTS_REFUSE_OVERWRITE")
if RECEIPT.exists():
    die("REMEDIATION_RECEIPT_ALREADY_EXISTS_REFUSE_OVERWRITE")

head = git_head()
all_external = set()
page_summaries = {}
shared_owner_rows = []
provider_rows = []
dependency_pages = []

for page_uid, cfg in target_pages.items():
    raw = load(cfg["raw"])
    blueprint = load(cfg["blueprint"])
    authority = raw.get("authority") or {}
    if authority.get("page_uid") != page_uid:
        die(f"{page_uid}:RAW_PAGE_UID_DRIFT")
    if blueprint.get("page_uid") != page_uid or blueprint.get("stage_uid") != "STAGE-01":
        die(f"{page_uid}:BLUEPRINT_IDENTITY_DRIFT")

    reg = raw.get("registries") or {}
    sections = index(reg.get("sections"), "section_uid")
    components = index(reg.get("components"), "component_uid")
    visuals = index(reg.get("visuals"), "visual_uid")
    actions = index(reg.get("actions"), "action_uid")
    controls = index(reg.get("controls"), "control_uid")
    gates = index(reg.get("gates"), "gate_uid")
    permissions = index(reg.get("permissions"), "permission_uid")
    objects = index(reg.get("objects_refs"), "object_uid")
    ports = index(reg.get("integration_ports"), "port_uid")
    stages = index(reg.get("stages"), "stage_uid")
    transitions = index(reg.get("stage_transitions"), "transition_uid")
    events = index(reg.get("events"), "event_uid")

    refs = external_refs(blueprint)
    all_external.update(x["gap_uid"] for x in refs)
    controls_by_action = defaultdict(list)
    components_by_section = defaultdict(list)
    controls_by_section = defaultdict(list)
    for component in components.values():
        components_by_section[component.get("section_uid")].append(component.get("component_uid"))
    for control in controls.values():
        controls_by_action[control.get("action_uid")].append(control)
        controls_by_section[control.get("section_uid")].append(control.get("control_uid"))

    page_dir = OUT / page_uid

    entity_entries = []
    for object_uid, obj in objects.items():
        entity_entries.append({
            "object_uid": object_uid,
            "entity": obj.get("entity"),
            "owner": obj.get("owner"),
            "required_content": obj.get("required_content"),
            "source_kind": "registries.objects_refs",
        })
    dump(page_dir / "BUSINESS_ENTITY_INVENTORY.yaml", {
        "schema_version": 1,
        "artifact_type": "BUSINESS_ENTITY_INVENTORY",
        "stage_uid": "STAGE-02",
        "page_uid": page_uid,
        "source_authority_id": authority.get("id"),
        "source_file_sha256": sha256(cfg["raw"]),
        "derivation": "EXACT_OBJECT_REGISTRY_PROJECTION_NO_NEW_ENTITY",
        "entity_count": len(entity_entries),
        "entities": entity_entries,
        "unresolved_external_authority_refs": refs,
    })

    operation_rows = []
    for action_uid, action in actions.items():
        rb = action.get("runtime_binding") or {}
        bound_controls = controls_by_action.get(action_uid, [])
        operation_rows.append({
            "action_uid": action_uid,
            "label": action.get("label"),
            "effect_type": action.get("effect_type"),
            "gate_uid": action.get("gate_uid"),
            "permission_uid": action.get("permission_uid"),
            "runtime_binding_kind": rb.get("binding_kind"),
            "port_refs": port_refs(action),
            "shared_authority_id": rb.get("shared_authority_id"),
            "shared_operation_id": rb.get("shared_operation_id"),
            "control_uids": [c.get("control_uid") for c in bound_controls],
            "section_uids": sorted({c.get("section_uid") for c in bound_controls if c.get("section_uid")}),
            "component_uids": sorted({c.get("component_uid") for c in bound_controls if c.get("component_uid")}),
            "visual_uids": sorted({c.get("visual_uid") for c in bound_controls if c.get("visual_uid")}),
            "object_uid_bindings": [],
            "object_binding_status": "NO_EXACT_ACTION_OBJECT_UID_BINDING_DECLARED_IN_SOURCE",
        })
        if rb.get("binding_kind") == "SHARED_OPERATION_REFERENCE":
            shared_owner_rows.append({
                "page_uid": page_uid,
                "action_uid": action_uid,
                "shared_authority_id": rb.get("shared_authority_id"),
                "shared_operation_id": rb.get("shared_operation_id"),
                "resolution_status": "PRESERVED_EXTERNAL_AUTHORITY_REFERENCE",
            })
    dump(page_dir / "BUSINESS_ENTITY_OPERATION_MATRIX.yaml", {
        "schema_version": 1,
        "artifact_type": "BUSINESS_ENTITY_OPERATION_MATRIX",
        "stage_uid": "STAGE-02",
        "page_uid": page_uid,
        "derivation": "EXACT_ACTION_CONTROL_PORT_GATE_PERMISSION_PROJECTION",
        "semantic_entity_join_used": False,
        "operation_count": len(operation_rows),
        "operations": operation_rows,
    })

    hierarchy_rows = []
    for object_uid, obj in objects.items():
        hierarchy_rows.append({
            "object_uid": object_uid,
            "entity": obj.get("entity"),
            "owner": obj.get("owner"),
            "parent_object_uid": None,
            "hierarchy_status": "ROOT_OR_NO_EXACT_PARENT_OBJECT_UID_DECLARED",
            "required_content_exact": obj.get("required_content"),
        })
    dump(page_dir / "ENTITY_HIERARCHY_MATRIX.yaml", {
        "schema_version": 1,
        "artifact_type": "ENTITY_HIERARCHY_MATRIX",
        "stage_uid": "STAGE-02",
        "page_uid": page_uid,
        "derivation": "EXACT_OBJECT_AND_OWNER_PROJECTION_PARENT_UID_NEVER_INFERRED",
        "semantic_parent_inference_used": False,
        "row_count": len(hierarchy_rows),
        "rows": hierarchy_rows,
    })

    workbenches = []
    for section_uid, section in sections.items():
        workbenches.append({
            "workbench_uid": f"{page_uid}-WB-{section_uid}",
            "workbench_class": "SAME_SURFACE_CLUSTER",
            "classification_basis": "EXACT_SECTION_UID_MEMBERSHIP",
            "section_uid": section_uid,
            "section_name": section.get("name"),
            "section_responsibility": section.get("responsibility"),
            "visual_uid": section.get("visual_uid"),
            "component_uids": sorted(components_by_section.get(section_uid, [])),
            "control_uids": sorted(controls_by_section.get(section_uid, [])),
        })
    dump(page_dir / "FUNCTIONAL_WORKBENCH_CONTRACT.yaml", {
        "schema_version": 1,
        "artifact_type": "FUNCTIONAL_WORKBENCH_CONTRACT",
        "stage_uid": "STAGE-02",
        "page_uid": page_uid,
        "derivation": "EXACT_SECTION_COMPONENT_CONTROL_MEMBERSHIP",
        "workbench_count": len(workbenches),
        "workbenches": workbenches,
    })

    nodes = {
        "sections": sorted(sections),
        "components": sorted(components),
        "controls": sorted(controls),
        "actions": sorted(actions),
        "gates": sorted(gates),
        "permissions": sorted(permissions),
        "visuals": sorted(visuals),
    }
    edges = []
    for component_uid, component in components.items():
        if component.get("section_uid"):
            edges.append({"from": component.get("section_uid"), "to": component_uid, "relation": "SECTION_HAS_COMPONENT"})
    for control_uid, control in controls.items():
        if control.get("component_uid"):
            edges.append({"from": control.get("component_uid"), "to": control_uid, "relation": "COMPONENT_HAS_CONTROL"})
        if control.get("action_uid"):
            edges.append({"from": control_uid, "to": control.get("action_uid"), "relation": "CONTROL_TRIGGERS_ACTION"})
        if control.get("gate_uid"):
            edges.append({"from": control_uid, "to": control.get("gate_uid"), "relation": "CONTROL_REQUIRES_GATE"})
        if control.get("permission_uid"):
            edges.append({"from": control_uid, "to": control.get("permission_uid"), "relation": "CONTROL_REQUIRES_PERMISSION"})
        if control.get("visual_uid"):
            edges.append({"from": control_uid, "to": control.get("visual_uid"), "relation": "CONTROL_RENDERED_IN_VISUAL"})
    dump(page_dir / "INTERACTION_TOPOLOGY_SPEC.yaml", {
        "schema_version": 1,
        "artifact_type": "INTERACTION_TOPOLOGY_MATRIX",
        "stage_uid": "STAGE-02",
        "page_uid": page_uid,
        "derivation": "EXACT_REGISTRY_UID_EDGES_ONLY",
        "semantic_edge_inference_used": False,
        "nodes": nodes,
        "edge_count": len(edges),
        "edges": edges,
    })

    visual_rows = []
    for action_uid, action in actions.items():
        bindings = []
        for control in controls_by_action.get(action_uid, []):
            bindings.append({
                "control_uid": control.get("control_uid"),
                "section_uid": control.get("section_uid"),
                "component_uid": control.get("component_uid"),
                "visual_uid": control.get("visual_uid"),
            })
        visual_rows.append({
            "action_uid": action_uid,
            "effect_type": action.get("effect_type"),
            "bindings": bindings,
            "visual_binding_status": "EXACT_CONTROL_VISUAL_BINDINGS" if bindings else "NO_REGISTERED_CONTROL_VISUAL_BINDING",
        })
    dump(page_dir / "FUNCTION_VISUAL_IMPACT_MATRIX.yaml", {
        "schema_version": 1,
        "artifact_type": "FUNCTION_VISUAL_IMPACT_MATRIX",
        "stage_uid": "STAGE-02",
        "page_uid": page_uid,
        "derivation": "EXACT_CONTROL_TO_ACTION_AND_VISUAL_BINDING",
        "action_count": len(visual_rows),
        "rows": visual_rows,
    })

    if cfg["ai_continuity_required"]:
        conversation_policy = raw.get("conversation_policy")
        if not isinstance(conversation_policy, dict):
            die(f"{page_uid}:AI_CONTINUITY_REQUIRED_BUT_CONVERSATION_POLICY_MISSING")
        dump(page_dir / "AI_INTERACTION_CONTINUITY_CONTRACT.yaml", {
            "schema_version": 1,
            "artifact_type": "AI_INTERACTION_CONTINUITY_CONTRACT",
            "stage_uid": "STAGE-02",
            "page_uid": page_uid,
            "activation_profile": "AI_ASSISTED_WORKSPACE",
            "derivation": "EXACT_CONVERSATION_POLICY_PROJECTION",
            "conversation_policy": conversation_policy,
            "unresolved_external_authority_refs": [x for x in refs if x["gap_uid"] in {"GAP-007", "GAP-008"}],
            "raw_ai_output_formalization": "FORBIDDEN_BY_SOURCE_AUTHORITY",
            "silent_context_reset": "BLOCK",
            "semantic_ai_route_completion_used": False,
        })

    dump(page_dir / "FUNCTIONAL_CHAIN_SPEC.yaml", {
        "schema_version": 1,
        "artifact_type": "FUNCTIONAL_CHAIN_SPEC",
        "stage_uid": "STAGE-02",
        "page_uid": page_uid,
        "source_authority_id": authority.get("id"),
        "source_blueprint_uid": blueprint.get("blueprint_uid"),
        "source_projection": {
            "actions": list(actions.values()),
            "controls": list(controls.values()),
            "stages": list(stages.values()),
            "stage_transitions": list(transitions.values()),
            "events": list(events.values()),
            "integration_ports": list(ports.values()),
        },
        "unresolved_external_authority_refs": refs,
        "source_registry_values_mutated": False,
        "missing_exact_contract_fields_auto_filled": False,
    })

    included = list(PAGE_ARTIFACTS)
    if cfg["ai_continuity_required"]:
        included.append("AI_INTERACTION_CONTINUITY_CONTRACT.yaml")
    dump(page_dir / "PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml", {
        "schema_version": 1,
        "artifact_type": "PAGE_CONSTRUCTION_SPEC_PACKAGE",
        "stage_uid": "STAGE-02",
        "page_uid": page_uid,
        "frozen_governance_uid": freeze.get("frozen_governance_uid"),
        "source_blueprint_uid": blueprint.get("blueprint_uid"),
        "included_artifacts": included,
        "external_authority_resolution_performed": False,
        "ai_autofill_used": False,
        "semantic_inference_used": False,
        "stage_exit_claimed": False,
    })

    for port_uid, port in ports.items():
        provider_rows.append({
            "page_uid": page_uid,
            "port_uid": port_uid,
            "boundary": port.get("boundary"),
            "operation": port.get("operation") or port.get("registered_operation"),
            "method_path": port.get("method_path") or port.get("method_effective_path"),
            "permission": port.get("permission") or port.get("registered_permission"),
            "state_event": port.get("state_event"),
            "exposure": port.get("exposure"),
        })

    dependency_pages.append({
        "page_uid": page_uid,
        "blueprint_uid": blueprint.get("blueprint_uid"),
        "blueprint_hash": blueprint.get("blueprint_hash"),
        "source_authority_id": authority.get("id"),
        "unresolved_external_authority_refs": refs,
    })
    page_summaries[page_uid] = {
        "entity_count": len(objects),
        "action_count": len(actions),
        "control_count": len(controls),
        "section_count": len(sections),
        "component_count": len(components),
        "visual_count": len(visuals),
        "stage_transition_count": len(transitions),
        "integration_port_count": len(ports),
        "ai_continuity_contract_materialized": cfg["ai_continuity_required"],
    }

if all_external != expected_external:
    die(f"EXTERNAL_AUTHORITY_UNION_DRIFT:expected={sorted(expected_external)} actual={sorted(all_external)}")

dump(OUT / "DEPENDENCY_MAP.yaml", {
    "schema_version": 1,
    "artifact_type": "DEPENDENCY_MAP",
    "stage_uid": "STAGE-02",
    "derivation": "EXACT_STAGE1_BLUEPRINT_AND_AUTHORITY_REFERENCE_PROJECTION",
    "pages": dependency_pages,
    "external_authority_union": sorted(all_external),
    "external_authority_auto_resolution": False,
})

dump(OUT / "ASYNC_PROVIDER_CONTRACT.yaml", {
    "schema_version": 1,
    "artifact_type": "ASYNC_PROVIDER_CONTRACT",
    "stage_uid": "STAGE-02",
    "derivation": "EXACT_INTEGRATION_PORT_REGISTRY_PROJECTION",
    "provider_route_inference_used": False,
    "port_count": len(provider_rows),
    "ports": provider_rows,
    "unresolved_provider_authority_gaps": ["GAP-005", "GAP-008"],
})

dump(OUT / "SHARED_OWNER_PORT_MAP.yaml", {
    "schema_version": 1,
    "artifact_type": "SHARED_OWNER_PORT_MAP",
    "stage_uid": "STAGE-02",
    "derivation": "EXACT_SHARED_OPERATION_REFERENCE_PROJECTION",
    "shared_owner_binding_count": len(shared_owner_rows),
    "bindings": shared_owner_rows,
    "external_authority_resolution_performed": False,
})

materialized_blockers = {}
for page_uid, cfg in target_pages.items():
    blockers = [
        "MISSING_BUSINESS_ENTITY_INVENTORY",
        "MISSING_BUSINESS_ENTITY_OPERATION_MATRIX",
        "MISSING_ENTITY_HIERARCHY_MATRIX",
        "MISSING_FUNCTIONAL_WORKBENCH_CONTRACT",
        "MISSING_INTERACTION_TOPOLOGY_SPEC",
        "MISSING_FUNCTION_VISUAL_IMPACT_MATRIX",
    ]
    if cfg["ai_continuity_required"]:
        blockers.append("MISSING_AI_INTERACTION_CONTINUITY_CONTRACT")
    materialized_blockers[page_uid] = blockers
materialized_blocker_count = sum(len(v) for v in materialized_blockers.values())
dump(RECEIPT, {
    "schema_version": 1,
    "artifact_type": "MATERIAL_REMEDIATION_RECEIPT",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "attempt_uid": freeze.get("attempt_uid"),
    "frozen_governance_uid": freeze.get("frozen_governance_uid"),
    "source_execution_sha": head,
    "owning_layer": "CURRENT_STAGE_PRODUCT_OR_CONTRACT_OUTPUT",
    "changed_artifact_root": "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT",
    "before_state": {"fresh_functional_gaps": before_functional_gaps, "closure_blockers": before_closure_blockers},
    "materialized_missing_artifact_blockers": materialized_blockers,
    "materialized_missing_artifact_blocker_count": materialized_blocker_count,
    "claimed_legal_elimination_before_fresh_reexecution": 0,
    "functional_gap_elimination_claimed": 0,
    "external_authority_union_preserved_unresolved": sorted(all_external),
    "target_pages": target_page_uids,
    "excluded_pages": sorted(set(PAGES) - set(target_page_uids)),
    "current_specification_mutated": False,
    "stage1_immutable_inputs_mutated": False,
    "ai_autofill_used": False,
    "semantic_inference_for_missing_authority_used": False,
    "page_summaries": page_summaries,
    "required_next_action": "VALIDATE_MATERIALIZATION_THEN_CLEAN_REEXECUTION_EVIDENCE_RUN_FULL_LINE_AND_FRESH_STAGE02_REEXECUTION",
    "status": "MATERIALIZED_PENDING_FRESH_REEXECUTION_PROOF",
})

print(f"MATERIALIZED_STAGE02_ROOT={OUT.relative_to(ROOT)}")
print(f"MATERIALIZATION_BEFORE_FUNCTIONAL_GAPS={before_functional_gaps}")
print(f"MATERIALIZATION_BEFORE_CLOSURE_BLOCKERS={before_closure_blockers}")
print(f"MATERIALIZED_MISSING_ARTIFACT_BLOCKERS={materialized_blocker_count}")
print("FUNCTIONAL_GAP_ELIMINATION_CLAIMED=0")
print("EXTERNAL_AUTHORITY_UNION=" + ",".join(sorted(all_external)))
print("PASS: Stage-02 structural remediation artifacts materialized from exact Stage-01 registries without Current Specification mutation")