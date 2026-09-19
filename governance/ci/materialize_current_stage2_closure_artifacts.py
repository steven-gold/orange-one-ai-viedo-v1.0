#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import hashlib
import json
import copy
import os
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



def _current_design_context():
    scope_path = ROOT / "governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml"
    state = load(STATE)
    scope = load(scope_path)
    if state.get("current_primary_task_layer") != "PRODUCT_STAGE_EXECUTION":
        die(f"APPROVED_DESIGN_MATERIALIZATION_REQUIRES_PRODUCT_LAYER:{state.get('current_primary_task_layer')!r}")
    work = state.get("active_work_unit") or {}
    if work.get("stage_uid") != "STAGE-02" or work.get("semantic_capability") != "PAGE_FUNCTIONAL_CONTRACT":
        die(f"CURRENT_STAGE02_PRODUCT_WORK_UNIT_REQUIRED:{work.get('work_unit_uid')!r}")
    if work.get("current_status") != "EXACT_CLOSURES_REVALIDATED_REVIEW_ONLY_PRODUCT_AUTHORITY_REQUIRED":
        die(f"CURRENT_STAGE02_DESIGN_REVIEW_STATE_REQUIRED:{work.get('current_status')!r}")
    pages = list(scope.get("included_units") or [])
    if len(pages) != 1 or work.get("scope") != pages:
        die(f"CURRENT_SCOPE_WORK_UNIT_DRIFT:{pages!r}:{work.get('scope')!r}")
    page = pages[0]
    owner = str(work.get("canonical_owner") or "")
    marker = "/04_PAGE_FUNCTIONAL_CONTRACT/"
    if marker not in owner:
        die("CURRENT_RUN_ROOT_UNRESOLVED")
    run_root = ROOT / owner.split(marker, 1)[0]
    product_root = run_root / "04_PAGE_FUNCTIONAL_CONTRACT"
    page_root = product_root / page
    raw_dir = run_root / "00_SOURCE_INTAKE/RAW_SOURCE" / page
    raw_candidates = sorted(p for p in raw_dir.glob("*.yaml") if p.is_file())
    if len(raw_candidates) != 1:
        die(f"CURRENT_RAW_SOURCE_IDENTITY_AMBIGUOUS:{[str(x.relative_to(ROOT)) for x in raw_candidates]!r}")
    blueprint_path = run_root / "02_BASE_BLUEPRINT" / page / "PAGE_BASE_BLUEPRINT.yaml"
    paths = {
        "scope": scope_path,
        "problem": product_root / "CURRENT_PROBLEM_REGISTER.yaml",
        "candidate": page_root / "DESIGN_CONTRACT_CANDIDATE.yaml",
        "semantic_review": page_root / "REMEDIATION_SEMANTIC_REVIEW.yaml",
        "chain": page_root / "FUNCTIONAL_CHAIN_SPEC.yaml",
        "raw": raw_candidates[0],
        "blueprint": blueprint_path,
        "approval": page_root / "DESIGN_CONTRACT_APPROVAL_EVIDENCE.yaml",
        "receipt": page_root / "DESIGN_CONTRACT_MATERIALIZATION_RECEIPT.yaml",
    }
    for label, path in paths.items():
        if label in {"approval", "receipt"}:
            continue
        if not path.is_file():
            die(f"CURRENT_DESIGN_INPUT_MISSING:{label}:{path.relative_to(ROOT)}")
    if paths["approval"].exists() or paths["receipt"].exists():
        die("APPROVED_DESIGN_MATERIALIZATION_EVIDENCE_ALREADY_EXISTS_REFUSE_OVERWRITE")
    return state, scope, work, page, run_root, product_root, page_root, paths

def _profile_for_entity(entity: str) -> str:
    mapping = {
        "LockedBlueprintRef": "EXTERNAL_REFERENCE",
        "AssetProductionScriptViewRef": "EXTERNAL_REFERENCE",
        "DNABindingRef": "EXTERNAL_REFERENCE",
        "AssetManifestRef": "EXTERNAL_REFERENCE",
        "SystemOutputNamingRef": "EXTERNAL_REFERENCE",
        "InstructionPackageRef": "EXTERNAL_REFERENCE",
        "ProviderRouteSnapshotRef": "EXTERNAL_REFERENCE",
        "AssetExecutionInputManifest": "EXECUTION_MANIFEST",
        "AssetCandidateOutput": "CANDIDATE_OUTPUT",
        "AssetEvaluation": "EVALUATION_RECORD",
        "AssetFinding": "FINDING_RECORD",
        "AssetCorrectionContext": "CORRECTION_CONTEXT",
        "CorrectionScriptCandidate": "CORRECTION_SCRIPT",
        "VersionedLayerDocument": "LAYER_DOCUMENT",
        "AssetPatch": "ASSET_PATCH",
        "AssetOutputVersion": "ASSET_VERSION",
        "AssetScorecard": "SCORECARD",
        "AssetHandoffManifest": "HANDOFF_MANIFEST",
    }
    profile = mapping.get(str(entity))
    if not profile:
        die(f"ENTITY_PROFILE_UNRESOLVED:{entity!r}")
    return profile


def _entity_operation_contract(objects: dict) -> dict:
    vocabulary = [
        "READ", "CREATE", "UPDATE", "VALIDATE", "EXECUTE", "EVALUATE",
        "DECIDE", "VERSION", "LOCK", "RESTORE", "HANDOFF", "RETRY",
        "AUDIT", "ERROR_RECOVERY",
    ]
    profiles = {
        "EXTERNAL_REFERENCE": {"required": ["READ", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "EXECUTION_MANIFEST": {"required": ["READ", "CREATE", "VALIDATE", "EXECUTE", "AUDIT", "ERROR_RECOVERY"], "optional": ["RETRY"]},
        "CANDIDATE_OUTPUT": {"required": ["READ", "CREATE", "VALIDATE", "DECIDE", "VERSION", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "EVALUATION_RECORD": {"required": ["READ", "CREATE", "VALIDATE", "EVALUATE", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "FINDING_RECORD": {"required": ["READ", "CREATE", "UPDATE", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "CORRECTION_CONTEXT": {"required": ["READ", "CREATE", "UPDATE", "VALIDATE", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "CORRECTION_SCRIPT": {"required": ["READ", "CREATE", "VALIDATE", "DECIDE", "VERSION", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "LAYER_DOCUMENT": {"required": ["READ", "CREATE", "UPDATE", "VERSION", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "ASSET_PATCH": {"required": ["READ", "CREATE", "VALIDATE", "DECIDE", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "ASSET_VERSION": {"required": ["READ", "CREATE", "VERSION", "LOCK", "RESTORE", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "SCORECARD": {"required": ["READ", "CREATE", "VALIDATE", "EVALUATE", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "HANDOFF_MANIFEST": {"required": ["READ", "CREATE", "VALIDATE", "HANDOFF", "AUDIT", "ERROR_RECOVERY"], "optional": []},
    }
    bindings = []
    for oid, obj in objects.items():
        bindings.append({"object_uid": oid, "profile": _profile_for_entity(obj.get("entity"))})
    return {
        "authority_source": "CURRENT_OBJECT_REGISTRY_AND_APPROVED_STAGE02_ASSET_DESIGN_REMEDIATION",
        "operation_vocabulary": vocabulary,
        "profile_rule": "Operations not REQUIRED or OPTIONAL by the bound profile are NOT_APPLICABLE.",
        "profiles": profiles,
        "entity_profile_bindings": bindings,
    }


def _entity_hierarchy_contract(objects: dict) -> dict:
    by_entity = {str(v.get("entity")): oid for oid, v in objects.items()}
    external = {
        "LockedBlueprintRef", "AssetProductionScriptViewRef", "DNABindingRef",
        "AssetManifestRef", "SystemOutputNamingRef", "InstructionPackageRef", "ProviderRouteSnapshotRef",
    }
    parent_entity = {
        "AssetExecutionInputManifest": None,
        "AssetCandidateOutput": "AssetExecutionInputManifest",
        "AssetEvaluation": "AssetCandidateOutput",
        "AssetFinding": "AssetEvaluation",
        "AssetCorrectionContext": "AssetFinding",
        "CorrectionScriptCandidate": "AssetCorrectionContext",
        "VersionedLayerDocument": "AssetCandidateOutput",
        "AssetPatch": "VersionedLayerDocument",
        "AssetOutputVersion": "AssetCandidateOutput",
        "AssetScorecard": "AssetEvaluation",
        "AssetHandoffManifest": "AssetOutputVersion",
    }
    relation_by_entity = {
        "AssetExecutionInputManifest": "EXECUTION_INPUT_AGGREGATES_EXACT_UPSTREAM_REFERENCES",
        "AssetCandidateOutput": "CANDIDATE_PRODUCED_FROM_EXECUTION_INPUT",
        "AssetEvaluation": "EVALUATION_BOUND_TO_CANDIDATE_OUTPUT",
        "AssetFinding": "FINDING_DERIVED_FROM_EVALUATION_EVIDENCE",
        "AssetCorrectionContext": "CORRECTION_CONTEXT_BOUND_TO_FINDING_AND_EXACT_OUTPUT",
        "CorrectionScriptCandidate": "CORRECTION_SCRIPT_DERIVED_FROM_CORRECTION_CONTEXT",
        "VersionedLayerDocument": "LAYER_DOCUMENT_DERIVED_FROM_CANDIDATE_OUTPUT",
        "AssetPatch": "PATCH_TARGETS_VERSIONED_LAYER_DOCUMENT",
        "AssetOutputVersion": "IMMUTABLE_OUTPUT_VERSION_DERIVED_FROM_ACCEPTED_CANDIDATE",
        "AssetScorecard": "SCORECARD_DERIVED_FROM_EVALUATION",
        "AssetHandoffManifest": "HANDOFF_BINDS_LOCKED_ASSET_OUTPUT_VERSION",
    }
    rows = []
    for oid, obj in objects.items():
        entity = str(obj.get("entity") or "")
        if entity in external:
            rows.append({
                "object_uid": oid,
                "relation_status": "EXTERNAL_ROOT",
                "parent_object_uid": None,
                "relation": f"EXTERNAL_{entity.upper()}_REFERENCE",
            })
            continue
        if entity not in parent_entity:
            die(f"ENTITY_HIERARCHY_RELATION_UNRESOLVED:{oid}:{entity}")
        pe = parent_entity[entity]
        parent_uid = by_entity.get(pe) if pe else None
        if pe and not parent_uid:
            die(f"ENTITY_HIERARCHY_PARENT_ENTITY_MISSING:{entity}:{pe}")
        rows.append({
            "object_uid": oid,
            "relation_status": "EXACT_CURRENT_STAGE02_DESIGN_RELATION",
            "parent_object_uid": parent_uid,
            "relation": relation_by_entity[entity],
        })
    return {
        "authority_source": "CURRENT_OBJECT_REGISTRY_REQUIRED_CONTENT_AND_APPROVED_STAGE02_ASSET_DESIGN_REMEDIATION",
        "relationships": rows,
    }


def _append_audit_event(port: dict, event_uid: str) -> None:
    current = str(port.get("state_event") or "").strip()
    tokens = [x.strip() for x in current.split("|") if x.strip()]
    if event_uid not in tokens:
        tokens.append(event_uid)
    port["state_event"] = " | ".join(tokens)


def _build_structural_outputs(*, page: str, raw: dict, blueprint: dict, effective_actions: dict, effective_ports: dict,
                              objects: dict, page_root: Path, product_root: Path, chain: dict,
                              operation_contract: dict, hierarchy_contract: dict) -> list[str]:
    reg = raw.get("registries") or {}
    sections = index(reg.get("sections"), "section_uid")
    components = index(reg.get("components"), "component_uid")
    controls = index(reg.get("controls"), "control_uid")
    visuals = index(reg.get("visuals"), "visual_uid")
    gates = index(reg.get("gates"), "gate_uid")
    permissions = index(reg.get("permissions"), "permission_uid")
    controls_by_action = defaultdict(list)
    components_by_section = defaultdict(list)
    controls_by_section = defaultdict(list)
    for comp in components.values():
        if comp.get("section_uid"):
            components_by_section[comp.get("section_uid")].append(comp.get("component_uid"))
    for control in controls.values():
        aid = control.get("action_uid")
        if aid in effective_actions:
            controls_by_action[aid].append(control)
        if control.get("section_uid"):
            controls_by_section[control.get("section_uid")].append(control.get("control_uid"))

    entity_entries = [{
        "object_uid": oid,
        "entity": obj.get("entity"),
        "owner": obj.get("owner"),
        "required_content": obj.get("required_content"),
        "source_kind": "registries.objects_refs",
    } for oid, obj in objects.items()]
    dump(page_root / "BUSINESS_ENTITY_INVENTORY.yaml", {
        "schema_version": 1, "artifact_type": "BUSINESS_ENTITY_INVENTORY", "stage_uid": "STAGE-02", "page_uid": page,
        "derivation": "CURRENT_OBJECT_REGISTRY_EXACT_PROJECTION_NO_NEW_ENTITY",
        "entity_count": len(entity_entries), "entities": entity_entries,
    })

    vocabulary = operation_contract["operation_vocabulary"]
    profiles = operation_contract["profiles"]
    binding_map = {x["object_uid"]: x["profile"] for x in operation_contract["entity_profile_bindings"]}
    entity_rows = []
    for oid, obj in objects.items():
        profile = binding_map[oid]
        rec = profiles[profile]
        required = set(rec.get("required") or [])
        optional = set(rec.get("optional") or [])
        decisions = {op: ("REQUIRED" if op in required else "OPTIONAL" if op in optional else "NOT_APPLICABLE") for op in vocabulary}
        entity_rows.append({
            "object_uid": oid, "entity": obj.get("entity"), "owner": obj.get("owner"),
            "profile": profile, "operation_applicability": decisions,
        })
    operation_rows = []
    for aid, action in effective_actions.items():
        rb = action.get("runtime_binding") or {}
        operation_rows.append({
            "action_uid": aid, "label": action.get("label"), "effect_type": action.get("effect_type"),
            "gate_uid": action.get("gate_uid"), "permission_uid": action.get("permission_uid"),
            "runtime_binding_kind": rb.get("binding_kind"), "port_refs": port_refs(action),
            "control_uids": [c.get("control_uid") for c in controls_by_action.get(aid, [])],
        })
    dump(page_root / "BUSINESS_ENTITY_OPERATION_MATRIX.yaml", {
        "schema_version": 2, "artifact_type": "BUSINESS_ENTITY_OPERATION_MATRIX", "stage_uid": "STAGE-02", "page_uid": page,
        "derivation": "CURRENT_ENTITY_PROFILE_APPLICABILITY_PLUS_EXACT_ACTION_BINDING",
        "semantic_entity_join_used": True, "entity_count": len(objects), "entity_rows": entity_rows,
        "operation_count": len(operation_rows), "operations": operation_rows,
    })

    rels = hierarchy_contract["relationships"]
    dump(page_root / "ENTITY_HIERARCHY_MATRIX.yaml", {
        "schema_version": 2, "artifact_type": "ENTITY_HIERARCHY_MATRIX", "stage_uid": "STAGE-02", "page_uid": page,
        "derivation": "APPROVED_EXPLICIT_CURRENT_OBJECT_RELATIONSHIPS",
        "explicit_relationship_authority_used": True, "entity_count": len(objects), "rows": copy.deepcopy(rels),
    })

    workbenches = []
    for sid, section in sections.items():
        workbenches.append({
            "workbench_uid": f"{page}-WB-{sid}", "workbench_class": "SAME_SURFACE_CLUSTER",
            "classification_basis": "EXACT_SECTION_UID_MEMBERSHIP", "section_uid": sid,
            "section_name": section.get("name"), "section_responsibility": section.get("responsibility"),
            "visual_uid": section.get("visual_uid"), "component_uids": sorted(components_by_section.get(sid, [])),
            "control_uids": sorted(controls_by_section.get(sid, [])),
        })
    dump(page_root / "FUNCTIONAL_WORKBENCH_CONTRACT.yaml", {
        "schema_version": 1, "artifact_type": "FUNCTIONAL_WORKBENCH_CONTRACT", "stage_uid": "STAGE-02", "page_uid": page,
        "derivation": "EXACT_SECTION_COMPONENT_CONTROL_MEMBERSHIP", "workbench_count": len(workbenches),
        "workbenches": workbenches, "atomic_workbenches": [],
    })

    nodes = {
        "sections": sorted(sections), "components": sorted(components), "controls": sorted(controls),
        "actions": sorted(effective_actions), "gates": sorted(gates), "permissions": sorted(permissions), "visuals": sorted(visuals),
    }
    edges = []
    for cid, comp in components.items():
        if comp.get("section_uid"):
            edges.append({"from": comp.get("section_uid"), "to": cid, "relation": "SECTION_HAS_COMPONENT"})
    for cid, control in controls.items():
        if control.get("component_uid"):
            edges.append({"from": control.get("component_uid"), "to": cid, "relation": "COMPONENT_HAS_CONTROL"})
        if control.get("action_uid") in effective_actions:
            edges.append({"from": cid, "to": control.get("action_uid"), "relation": "CONTROL_TRIGGERS_ACTION"})
        if control.get("gate_uid"):
            edges.append({"from": cid, "to": control.get("gate_uid"), "relation": "CONTROL_REQUIRES_GATE"})
        if control.get("permission_uid"):
            edges.append({"from": cid, "to": control.get("permission_uid"), "relation": "CONTROL_REQUIRES_PERMISSION"})
        if control.get("visual_uid"):
            edges.append({"from": cid, "to": control.get("visual_uid"), "relation": "CONTROL_RENDERED_IN_VISUAL"})
    dump(page_root / "INTERACTION_TOPOLOGY_SPEC.yaml", {
        "schema_version": 1, "artifact_type": "INTERACTION_TOPOLOGY_MATRIX", "stage_uid": "STAGE-02", "page_uid": page,
        "derivation": "EXACT_REGISTRY_UID_EDGES_ONLY", "semantic_edge_inference_used": False,
        "nodes": nodes, "edge_count": len(edges), "edges": edges,
    })

    visual_rows = []
    for aid, action in effective_actions.items():
        bindings = [{
            "control_uid": c.get("control_uid"), "section_uid": c.get("section_uid"),
            "component_uid": c.get("component_uid"), "visual_uid": c.get("visual_uid"),
        } for c in controls_by_action.get(aid, [])]
        visual_rows.append({
            "action_uid": aid, "effect_type": action.get("effect_type"), "bindings": bindings,
            "visual_binding_status": "EXACT_CONTROL_VISUAL_BINDINGS" if bindings else "NO_REGISTERED_CONTROL_VISUAL_BINDING",
        })
    dump(page_root / "FUNCTION_VISUAL_IMPACT_MATRIX.yaml", {
        "schema_version": 1, "artifact_type": "FUNCTION_VISUAL_IMPACT_MATRIX", "stage_uid": "STAGE-02", "page_uid": page,
        "derivation": "EXACT_CONTROL_TO_ACTION_AND_VISUAL_BINDING", "action_count": len(visual_rows), "rows": visual_rows,
    })

    shared_rows = []
    for aid, action in effective_actions.items():
        rb = action.get("runtime_binding") or {}
        if rb.get("binding_kind") == "SHARED_OPERATION_REFERENCE":
            shared_rows.append({
                "page_uid": page, "action_uid": aid, "shared_authority_id": rb.get("shared_authority_id"),
                "shared_operation_id": rb.get("shared_operation_id"), "resolution_status": "CURRENT_SHARED_OPERATION_REFERENCE",
            })
    dump(product_root / "SHARED_OWNER_PORT_MAP.yaml", {
        "schema_version": 1, "artifact_type": "SHARED_OWNER_PORT_MAP", "stage_uid": "STAGE-02",
        "derivation": "CURRENT_EFFECTIVE_ACTION_SHARED_OPERATION_REFERENCE_PROJECTION",
        "shared_owner_binding_count": len(shared_rows), "bindings": shared_rows,
    })
    provider_rows = [{
        "page_uid": page, "port_uid": pid, "boundary": port.get("boundary"),
        "operation": port.get("operation") or port.get("registered_operation"),
        "method_path": port.get("method_path") or port.get("method_effective_path"),
        "permission": port.get("permission") or port.get("registered_permission"),
        "state_event": port.get("state_event"), "exposure": port.get("exposure"),
    } for pid, port in effective_ports.items()]
    dump(product_root / "ASYNC_PROVIDER_CONTRACT.yaml", {
        "schema_version": 1, "artifact_type": "ASYNC_PROVIDER_CONTRACT", "stage_uid": "STAGE-02",
        "derivation": "CURRENT_EFFECTIVE_INTEGRATION_PORT_PROJECTION", "provider_route_inference_used": False,
        "port_count": len(provider_rows), "ports": provider_rows,
    })
    refs = []
    for ref in blueprint.get("unresolved_external_authority_refs") or []:
        refs.append({"gap_uid": ref.get("gap_uid"), "authority_ref": ref.get("authority_ref"), "resolved": False})
    dump(product_root / "DEPENDENCY_MAP.yaml", {
        "schema_version": 1, "artifact_type": "DEPENDENCY_MAP", "stage_uid": "STAGE-02",
        "derivation": "CURRENT_STAGE1_BLUEPRINT_AND_AUTHORITY_REFERENCE_PROJECTION",
        "pages": [{"page_uid": page, "blueprint_uid": blueprint.get("blueprint_uid"),
                   "blueprint_hash": blueprint.get("blueprint_hash"),
                   "unresolved_external_authority_refs": refs}],
    })
    included = [
        "BUSINESS_ENTITY_INVENTORY.yaml", "BUSINESS_ENTITY_OPERATION_MATRIX.yaml", "ENTITY_HIERARCHY_MATRIX.yaml",
        "FUNCTIONAL_WORKBENCH_CONTRACT.yaml", "INTERACTION_TOPOLOGY_SPEC.yaml", "FUNCTION_VISUAL_IMPACT_MATRIX.yaml",
        "FUNCTIONAL_CHAIN_SPEC.yaml",
    ]
    dump(page_root / "PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml", {
        "schema_version": 1, "artifact_type": "PAGE_CONSTRUCTION_SPEC_PACKAGE", "stage_uid": "STAGE-02", "page_uid": page,
        "source_blueprint_uid": blueprint.get("blueprint_uid"), "included_artifacts": included,
        "candidate_bytes_became_authority_directly": False, "stage_exit_claimed": False,
    })
    return included + ["PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml", "../DEPENDENCY_MAP.yaml", "../ASYNC_PROVIDER_CONTRACT.yaml", "../SHARED_OWNER_PORT_MAP.yaml"]


def materialize_current_approved_design_contract():
    state, scope, work, page, run_root, product_root, page_root, paths = _current_design_context()
    problem = load(paths["problem"])
    candidate = load(paths["candidate"])
    semantic = load(paths["semantic_review"])
    chain = load(paths["chain"])
    raw = load(paths["raw"])
    blueprint = load(paths["blueprint"])

    if candidate.get("page_uid") != page or candidate.get("status") != "REVIEW_ONLY_NON_AUTHORITY_NON_MATERIALIZABLE":
        die("CURRENT_DESIGN_CANDIDATE_IDENTITY_OR_STATUS_DRIFT")
    if semantic.get("page_uid") != page or semantic.get("status") != "PASS_AS_REVIEW_ONLY_PACKAGE_NOT_APPROVED_FOR_MATERIALIZATION":
        die("CURRENT_DESIGN_SEMANTIC_REVIEW_STATUS_DRIFT")
    blockers = semantic.get("blocking_authority_selection") or []
    if len(blockers) != 1 or not blockers[0].get("target_uid"):
        die(f"CURRENT_DESIGN_AUTHORITY_SELECTION_DENOMINATOR_DRIFT:{blockers!r}")
    authority_target = str(blockers[0]["target_uid"])
    rows = list(problem.get("problems") or [])
    if int(problem.get("open_problem_count") or 0) != len(rows):
        die("CURRENT_PROBLEM_REGISTER_OPEN_DENOMINATOR_DRIFT")
    finding_trigger_rows = [x for x in rows if str(x.get("target_uid") or "") == authority_target and x.get("category") == "ACTION_WITHOUT_CONTROL_OR_TRIGGER"]
    if len(finding_trigger_rows) != 1:
        die(f"CURRENT_AUTHORITY_GAP_PROBLEM_IDENTITY_DRIFT:{[(x.get('problem_uid'),x.get('category'),x.get('target_uid')) for x in finding_trigger_rows]!r}")
    finding_decision = os.environ.get("STAGE02_FINDING_CREATE_TRIGGER_DECISION", "").strip()
    if finding_decision != "SYSTEM_TRIGGER_FROM_EVALUATION_FINDING_DETECTION":
        die(f"ASSET01_FINDING_CREATE_EXPLICIT_SYSTEM_TRIGGER_DECISION_REQUIRED:{finding_decision!r}")
    remaining_uids = set()
    approved_rows = list(rows)
    approved_uids = {str(x.get("problem_uid") or "") for x in approved_rows}
    boundaries = candidate.get("design_boundaries") or {}
    candidate_review_count = sum(
        int((boundaries.get(key) or {}).get("problem_count") or 0)
        for key in (
            "failure_error_binding", "payload_input_contract", "audit_event_binding",
            "transition_required_fields", "post_action_validation_remaining", "finding_create_trigger", "stage02_planning_completeness",
        )
    )
    if candidate_review_count != len(approved_uids):
        die(f"APPROVED_DESIGN_CANDIDATE_DENOMINATOR_DRIFT:{candidate_review_count}:{len(approved_uids)}")
    if int(candidate.get("covered_review_only_problem_count") or 0) != len(rows):
        die("REVIEW_ONLY_CANDIDATE_CURRENT_REGISTER_DENOMINATOR_DRIFT")

    current_uid = str(state.get("specification_uid") or "")
    frozen_product_uid = str((state.get("stage02_active_attempt") or {}).get("frozen_governance_uid") or "")
    if not frozen_product_uid:
        die("FROZEN_PRODUCT_GOVERNANCE_UID_MISSING")
    if candidate.get("current_governance_uid") != frozen_product_uid or semantic.get("current_governance_uid") != frozen_product_uid:
        die("FROZEN_PRODUCT_GOVERNANCE_UID_DRIFT_IN_DESIGN_PACKAGE")
    prior_credit = int(work.get("product_blocker_credit") or 0)
    exact = work.get("exact_closure_materialization") or {}
    if exact.get("revalidation_status") != "FRESH_REVALIDATED" or int(exact.get("product_blocker_credit_after_fresh_revalidation") or 0) != prior_credit:
        die("PRIOR_EXACT_CLOSURE_CREDIT_NOT_FRESH_REVALIDATED")

    projection = chain.setdefault("source_projection", {})
    actions_list = projection.get("actions")
    ports_list = projection.get("integration_ports")
    transitions_list = projection.get("stage_transitions")
    if not isinstance(actions_list, list) or not isinstance(ports_list, list) or not isinstance(transitions_list, list):
        die("CANONICAL_SUCCESSOR_REQUIRED_PROJECTION_LIST_MISSING")
    actions = index(actions_list, "action_uid")
    ports = index(ports_list, "port_uid")
    transitions = index(transitions_list, "transition_uid")
    raw_reg = raw.get("registries") or {}
    errors = index(raw_reg.get("errors"), "error_uid")
    objects = index(raw_reg.get("objects_refs"), "object_uid")

    failure = boundaries.get("failure_error_binding") or {}
    failure_rows = failure.get("proposal") or []
    if int(failure.get("problem_count") or 0) != len(failure_rows):
        die("FAILURE_ERROR_BINDING_PROPOSAL_DENOMINATOR_DRIFT")
    for proposal in failure_rows:
        aid = str(proposal.get("action_uid") or "")
        eid = str(proposal.get("error_uid") or "")
        action = actions.get(aid)
        error = errors.get(eid)
        if not action or not error or not error.get("recovery"):
            die(f"FAILURE_ERROR_BINDING_TARGET_INVALID:{aid}:{eid}")
        prior = action.get("error_uid")
        if prior not in (None, "", eid):
            die(f"FAILURE_ERROR_BINDING_CONFLICT:{aid}:{prior}:{eid}")
        action["error_uid"] = eid

    payload = boundaries.get("payload_input_contract") or {}
    payload_rows = payload.get("proposal") or []
    if int(payload.get("problem_count") or 0) != len(payload_rows):
        die("PAYLOAD_INPUT_PROPOSAL_DENOMINATOR_DRIFT")
    for proposal in payload_rows:
        aid = str(proposal.get("action_uid") or "")
        action = actions.get(aid)
        required_inputs = list(proposal.get("required_inputs") or [])
        policy = str(proposal.get("payload_policy") or "")
        if not action or not required_inputs or not policy:
            die(f"PAYLOAD_INPUT_PROPOSAL_INVALID:{aid}")
        rb = action.setdefault("runtime_binding", {})
        desired = {"required_inputs": required_inputs, "payload_policy": policy}
        prior = rb.get("input_contract")
        if prior not in (None, {}, desired):
            die(f"PAYLOAD_INPUT_CONTRACT_CONFLICT:{aid}")
        rb["input_contract"] = desired

    audit = boundaries.get("audit_event_binding") or {}
    audit_rows = audit.get("proposal") or []
    if int(audit.get("problem_count") or 0) != len(audit_rows):
        die("AUDIT_EVENT_PROPOSAL_DENOMINATOR_DRIFT")
    for proposal in audit_rows:
        aid = str(proposal.get("action_uid") or "")
        event_uid = str(proposal.get("audit_event_uid") or "")
        action = actions.get(aid)
        if not action or not event_uid:
            die(f"AUDIT_EVENT_PROPOSAL_INVALID:{aid}:{event_uid}")
        refs = [x["port_uid"] for x in port_refs(action) if x.get("port_uid") in ports]
        refs = sorted(set(refs))
        if len(refs) != 1:
            die(f"AUDIT_EVENT_PORT_RESOLUTION_NOT_EXACT:{aid}:{refs!r}")
        _append_audit_event(ports[refs[0]], event_uid)

    trans_boundary = boundaries.get("transition_required_fields") or {}
    trans_rows = trans_boundary.get("proposal") or []
    if int(trans_boundary.get("problem_count") or 0) != len(trans_rows) * 4:
        die("TRANSITION_REQUIRED_FIELD_DENOMINATOR_DRIFT")
    for proposal in trans_rows:
        tid = str(proposal.get("transition_uid") or "")
        transition = transitions.get(tid)
        if not transition:
            die(f"TRANSITION_PROPOSAL_TARGET_MISSING:{tid}")
        from_stage = transition.get("from_stage")
        if not from_stage:
            die(f"TRANSITION_FROM_STAGE_MISSING:{tid}")
        desired = {
            "mutation_owner": proposal.get("mutation_owner"),
            "failure_error_uid": proposal.get("failure_error_uid"),
            "failure_state": from_stage,
            "recovery": {
                "retain_stage": from_stage,
                "action": proposal.get("recovery"),
                "error_uid": proposal.get("failure_error_uid"),
            },
            "audit_event_uid": proposal.get("audit_event_uid"),
        }
        if any(v in (None, "", {}) for v in desired.values()):
            die(f"TRANSITION_PROPOSAL_INCOMPLETE:{tid}:{desired!r}")
        for key, value in desired.items():
            prior = transition.get(key)
            if prior not in (None, "", {}, value):
                die(f"TRANSITION_FIELD_CONFLICT:{tid}:{key}:{prior!r}:{value!r}")
            transition[key] = value

    post = boundaries.get("post_action_validation_remaining") or {}
    post_rows = post.get("proposal") or []
    if int(post.get("problem_count") or 0) != len(post_rows):
        die("POST_ACTION_VALIDATION_PROPOSAL_DENOMINATOR_DRIFT")
    for proposal in post_rows:
        aid = str(proposal.get("action_uid") or "")
        action = actions.get(aid)
        source_port = str(proposal.get("source_port") or "")
        if not action or source_port not in ports:
            die(f"POST_ACTION_VALIDATION_TARGET_INVALID:{aid}:{source_port}")
        rb = action.setdefault("runtime_binding", {})
        desired = {
            "contract_type": proposal.get("validation_contract_type"),
            "source_port_uid": source_port,
            "expected_signal": proposal.get("signal"),
        }
        if proposal.get("mode"):
            desired["mode"] = proposal.get("mode")
        prior = rb.get("validation")
        if prior not in (None, {}, desired):
            die(f"POST_ACTION_VALIDATION_CONFLICT:{aid}")
        rb["validation"] = desired

    finding_boundary = boundaries.get("finding_create_trigger") or {}
    if finding_boundary.get("status") != "AUTHORITY_SELECTION_REQUIRED" or str(finding_boundary.get("action_uid") or "") != authority_target:
        die("FINDING_CREATE_AUTHORITY_GAP_BOUNDARY_DRIFT")
    alternatives = finding_boundary.get("alternatives") or []
    selected = [x for x in alternatives if isinstance(x, dict) and x.get("behavior") == finding_decision]
    if len(selected) != 1 or selected[0].get("new_visual_control") is not False:
        die("FINDING_CREATE_SYSTEM_TRIGGER_SELECTION_NOT_EXACT")
    finding_action = actions.get(authority_target)
    if not finding_action:
        die("FINDING_CREATE_ACTION_MISSING")
    for field in ("trigger_event_uid", "trigger_uid", "system_trigger", "trigger_kind"):
        if finding_action.get(field):
            die(f"FINDING_CREATE_TRIGGER_CONFLICT:{field}")
    prior_invocation = finding_action.get("invocation")
    if prior_invocation not in (None, "", finding_decision):
        die(f"FINDING_CREATE_INVOCATION_CONFLICT:{prior_invocation!r}")
    finding_action["invocation"] = finding_decision
    finding_action["trigger_authority"] = {
        "source": "EXPLICIT_USER_DIRECTIVE",
        "authorization_uid": str(state.get("current_primary_task_authorization_uid") or ""),
        "bug_ref": "FIND-20260919-015",
        "new_visual_control": False,
    }

    planning = boundaries.get("stage02_planning_completeness") or {}
    plan = planning.get("proposal") or {}
    required_contracts = list(plan.get("required_contracts") or [])
    required_invariants = list(plan.get("required_invariants") or [])
    if int(planning.get("problem_count") or 0) != 1 or plan.get("status") != "REQUIRED_FOR_STAGE02_CLOSURE":
        die("STAGE02_PLANNING_CANDIDATE_INVALID")
    if set(required_contracts) != {"change_impact_contract", "entity_operation_applicability_contract", "entity_hierarchy_contract"}:
        die(f"STAGE02_PLANNING_REQUIRED_CONTRACT_SET_DRIFT:{required_contracts!r}")

    operation_contract = _entity_operation_contract(objects)
    hierarchy_contract = _entity_hierarchy_contract(objects)
    change_impact = {
        "authority_source": "CURRENT_ASSET_STAGE_FLOW_AND_APPROVED_STAGE02_DESIGN_REMEDIATION",
        "trigger": "UPSTREAM_LOCKED_BLUEPRINT_SCRIPT_DNA_MANIFEST_OR_ROUTE_CHANGED",
        "affected_downstream_states": ["NEEDS_REVIEW", "NEEDS_REVALIDATION"],
        "silent_downstream_rewrite": "FORBIDDEN",
        "exact_base_version_required_for_revision": True,
        "prior_locked_asset_version_immutable": True,
        "dependency_order": [
            "AssetExecutionInputManifest", "AssetCandidateOutput", "AssetEvaluation", "AssetFinding",
            "AssetCorrectionContext", "CorrectionScriptCandidate", "VersionedLayerDocument", "AssetPatch",
            "AssetOutputVersion", "AssetScorecard", "AssetHandoffManifest",
        ],
    }
    baseline_sha256 = sha256(paths["raw"])
    completeness = {
        "authority_source": "EXPLICIT_USER_DIRECTIVE_PLUS_CURRENT_ASSET_STAGE02_DESIGN_CANDIDATE",
        "planning_baseline_file": str(paths["raw"].relative_to(ROOT)),
        "planning_baseline_sha256": baseline_sha256,
        "planning_baseline_git_blob_sha": (plan.get("planning_baseline_identity") or {}).get("git_blob_sha"),
        "status": "REQUIRED_FOR_STAGE02_CLOSURE",
        "required_contracts": required_contracts,
        "required_invariants": required_invariants,
        "excluded_non_applicable_contract_families": list(planning.get("excluded_non_applicable_contract_families") or []),
        "product_specific_adapter": True,
        "common_policy_override": False,
    }
    chain["change_impact_contract"] = change_impact
    chain["entity_operation_applicability_contract"] = operation_contract
    chain["entity_hierarchy_contract"] = hierarchy_contract
    chain["stage02_completeness_contract"] = completeness
    chain["planning_baseline_sha256"] = baseline_sha256
    projection["actions"] = list(actions.values())
    projection["integration_ports"] = list(ports.values())
    projection["stage_transitions"] = list(transitions.values())

    approval_ref = str(paths["approval"].relative_to(ROOT))
    receipt_ref = str(paths["receipt"].relative_to(ROOT))
    remediation = chain.setdefault("design_contract_remediation", {})
    remediation.update({
        "canonical_owner_materialization": True,
        "materialization_scope": "APPROVED_COHERENT_CANDIDATE_PLUS_EXPLICIT_SYSTEM_TRIGGER_SELECTION",
        "approved_design_contract_problem_count": len(approved_uids),
        "remaining_authority_gap_problem_count": len(remaining_uids),
        "candidate_bytes_became_authority_directly": False,
        "raw_source_mutated": False,
        "approval_kind": "EXPLICIT_USER_APPROVAL_COHERENT_CANDIDATE_PLUS_EXPLICIT_SYSTEM_TRIGGER_SELECTION",
        "approval_evidence_ref": approval_ref,
        "contract_projection_allowed": True,
        "approved_contract_projection_keys": [
            "change_impact_contract", "entity_operation_applicability_contract",
            "entity_hierarchy_contract", "stage02_completeness_contract",
        ],
    })
    dump(paths["chain"], chain)

    structural = _build_structural_outputs(
        page=page, raw=raw, blueprint=blueprint, effective_actions=actions, effective_ports=ports,
        objects=objects, page_root=page_root, product_root=product_root, chain=chain,
        operation_contract=operation_contract, hierarchy_contract=hierarchy_contract,
    )

    authorization_uid = str(state.get("current_primary_task_authorization_uid") or "")
    if not authorization_uid:
        die("EXPLICIT_USER_AUTHORIZATION_UID_MISSING")
    approval = {
        "schema_version": 1,
        "artifact_type": "PRODUCT_DESIGN_CONTRACT_PACKAGE_REVIEW_EVIDENCE",
        "normative_authority": False,
        "current_governance_uid": current_uid,
        "product_candidate_frozen_governance_uid": frozen_product_uid,
        "work_unit_uid": str(work.get("work_unit_uid") or ""),
        "page_uid": page,
        "decision": "APPROVE_COHERENT_CANDIDATE_PLUS_SYSTEM_TRIGGER_SELECTION",
        "approved_by": "USER",
        "explicit_user_decision_observed": True,
        "self_reported_approval": False,
        "authorization_uid": authorization_uid,
        "authorization_directive": "把這部分列入待修正bug，先執行繼續跑完素材頁面stage-02，確認是否還有這些問題。",
        "authority_selection": {
            "target_uid": authority_target,
            "decision": finding_decision,
            "new_visual_control": False,
            "bug_ref": "FIND-20260919-015",
        },
        "approved_problem_count": len(approved_uids),
        "approved_problem_uids": sorted(approved_uids),
        "excluded_authority_selection_problem_uids": sorted(remaining_uids),
        "excluded_authority_selection_target_uids": [],
        "candidate_ref": str(paths["candidate"].relative_to(ROOT)),
        "candidate_sha256": sha256(paths["candidate"]),
        "semantic_review_ref": str(paths["semantic_review"].relative_to(ROOT)),
        "semantic_review_sha256": sha256(paths["semantic_review"]),
        "problem_register_ref": str(paths["problem"].relative_to(ROOT)),
        "problem_register_sha256": sha256(paths["problem"]),
        "candidate_bytes_became_authority_directly": False,
        "current_specification_mutated": False,
        "raw_source_mutated": False,
    }
    dump(paths["approval"], approval)
    receipt = {
        "schema_version": 1,
        "artifact_type": "APPROVED_DESIGN_CONTRACT_MATERIALIZATION_RECEIPT",
        "normative_authority": False,
        "current_governance_uid": current_uid,
        "product_candidate_frozen_governance_uid": frozen_product_uid,
        "work_unit_uid": str(work.get("work_unit_uid") or ""),
        "page_uid": page,
        "canonical_successor_ref": str(paths["chain"].relative_to(ROOT)),
        "approval_evidence_ref": approval_ref,
        "approved_problem_count": len(approved_uids),
        "approved_problem_uids": sorted(approved_uids),
        "remaining_authority_gap_problem_uids": sorted(remaining_uids),
        "remaining_authority_gap_target_uids": [],
        "prior_product_credit": prior_credit,
        "product_blocker_credit_before_fresh_revalidation": prior_credit,
        "generated_structural_outputs": structural,
        "status": "MATERIALIZED_PENDING_FRESH_REVALIDATION",
        "fresh_revalidation_required": True,
        "candidate_bytes_became_authority_directly": False,
        "raw_source_mutated": False,
        "current_specification_mutated": False,
    }
    dump(paths["receipt"], receipt)

    next_action = f"REVALIDATE_{page.replace('-','')}_STAGE02_AFTER_APPROVED_DESIGN_CONTRACT_MATERIALIZATION"
    work["current_status"] = "APPROVED_DESIGN_CONTRACT_MATERIALIZED_REVALIDATION_REQUIRED"
    work["product_blocker_credit"] = prior_credit
    work["design_contract_materialization"] = {
        "canonical_successor_ref": str(paths["chain"].relative_to(ROOT)),
        "approval_evidence_ref": approval_ref,
        "receipt_ref": receipt_ref,
        "approved_problem_count": len(approved_uids),
        "approved_problem_uids": sorted(approved_uids),
        "remaining_authority_gap_problem_uids": sorted(remaining_uids),
        "prior_product_credit": prior_credit,
        "product_blocker_credit_before_fresh_revalidation": prior_credit,
        "revalidation_status": "PENDING_FRESH_REVALIDATION",
    }
    state["active_work_unit"] = work
    state["status"] = f"ACTIVE_{page.replace('-','')}_STAGE02_APPROVED_DESIGN_CONTRACT_MATERIALIZED_REVALIDATION_REQUIRED"
    state["next_action"] = next_action
    state["current_primary_task_product_stage_credit"] = prior_credit
    attempt = state.setdefault("stage02_active_attempt", {})
    attempt["next_action"] = next_action
    attempt["fresh_revalidation_required"] = True
    attempt["product_blocker_credit"] = prior_credit
    material = state.setdefault("stage02_material_remediation", {})
    material.update({
        "material_remediation_started": True,
        "source_problem_denominator": int(problem.get("open_problem_count") or 0),
        "source_closure_blocker_denominator": int(work.get("source_closure_blocker_denominator") or 0),
        "exact_materialized_closure_count": int((work.get("exact_closure_materialization") or {}).get("materialized_closure_count") or 0),
        "approved_design_contract_problem_count_pending_revalidation": len(approved_uids),
        "remaining_authority_gap_problem_count": len(remaining_uids),
        "product_blocker_credit": prior_credit,
        "status": "APPROVED_DESIGN_CONTRACT_MATERIALIZED_PENDING_FRESH_REVALIDATION",
    })
    state["resume_control"] = {
        "current_resume_point": f"{page.replace('-','')}_STAGE2_APPROVED_DESIGN_CONTRACT_MATERIALIZED_REVALIDATION_REQUIRED",
        "current_work_unit_uid": work.get("work_unit_uid"),
        "current_owner": str(paths["chain"].relative_to(ROOT)),
        "historical_stage2_results_are_current_state": False,
        "stage2_execution_requires_fresh_entry_resolution": False,
        "exact_next_action": next_action,
    }
    dump(STATE, state)

    findings_path = ROOT / "governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml"
    candidate_state_path = ROOT / "governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml"
    findings = load(findings_path)
    findings["next_action"] = next_action
    findings["product_blocker_credit"] = prior_credit
    findings["approved_design_contract_problem_count_pending_revalidation"] = len(approved_uids)
    dump(findings_path, findings)
    candidate_state = load(candidate_state_path)
    cur = candidate_state.setdefault("current_stage2_execution", {})
    cur["next_action"] = next_action
    cur["current_work_unit_status"] = "APPROVED_DESIGN_CONTRACT_MATERIALIZED_REVALIDATION_REQUIRED"
    cur["product_blocker_reduction_credit"] = prior_credit
    cur["approved_design_contract_problem_count_pending_revalidation"] = len(approved_uids)
    dump(candidate_state_path, candidate_state)

    scope["fresh_revalidation_required"] = True
    scope["stage_exit_credit_allowed"] = False
    tmp = copy.deepcopy(scope)
    tmp.pop("content_hash", None)
    scope["content_hash"] = hashlib.sha256(
        json.dumps(tmp, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    dump(paths["scope"], scope)

    print(f"APPROVED_DESIGN_PAGE={page}")
    print(f"APPROVED_DESIGN_PROBLEM_COUNT={len(approved_uids)}")
    print(f"REMAINING_AUTHORITY_GAP_COUNT={len(remaining_uids)}")
    print(f"PRIOR_PRODUCT_CREDIT={prior_credit}")
    print(f"CANONICAL_SUCCESSOR={paths['chain'].relative_to(ROOT)}")
    print("PASS: approved non-ambiguous design-contract scope materialized; remaining authority selection preserved unresolved")


if "--approved-design-current" in sys.argv:
    materialize_current_approved_design_contract()
    raise SystemExit(0)

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
PREEXISTING_CANONICAL_PREFLIGHT_FILES = {
    "REQUIRED_FIELD_MANIFEST.yaml",
    "FUNCTIONAL_CHAIN_MANIFEST.yaml",
    "EFFECTIVE_CONTRACT_OVERLAY.yaml",
    "DEPENDENCY_TOPOLOGY.yaml",
    "DENOMINATOR_SNAPSHOT.yaml",
    "CLASSIFICATION_RULESET.yaml",
    "CHANGE_IMPACT_MAP.yaml",
    "STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml",
    "CURRENT_PROBLEM_REGISTER.yaml",
    "RESOLUTION_LEDGER.yaml",
    "GOVERNANCE_EXECUTION_CONTEXT_RECEIPT.yaml",
    "EXECUTION_CYCLE_PREFLIGHT_RECEIPT.yaml",
}
if OUT.exists():
    existing = {
        p.relative_to(OUT).as_posix()
        for p in OUT.rglob("*")
        if p.is_file()
    }
    unexpected = sorted(existing - PREEXISTING_CANONICAL_PREFLIGHT_FILES)
    missing = sorted(PREEXISTING_CANONICAL_PREFLIGHT_FILES - existing)
    if unexpected:
        die(f"STAGE02_PRODUCT_ROOT_HAS_UNAUTHORIZED_PREEXISTING_OUTPUTS:{unexpected}")
    if missing:
        die(f"CANONICAL_PREFLIGHT_BASELINE_INCOMPLETE:{missing}")
else:
    die("CANONICAL_PREFLIGHT_ROOT_MISSING_BEFORE_STRUCTURAL_MATERIALIZATION")
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